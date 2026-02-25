# Architecture — Merge Video

## Overview

A service for merging video files (YouTube URLs or local uploads) into a single video, with optional YouTube upload to the user's channel and email notifications on job status. Accessible via web UI or Telegram bot.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, FastAPI, uvicorn |
| Video download | yt-dlp + PySocks (via Decodo residential proxy) |
| Video merge | ffmpeg (two-pass: normalize → concat demuxer) |
| YouTube upload | google-api-python-client, OAuth2 |
| Email | Gmail API (OAuth2, send scope) |
| TG Bot | aiogram 3 |
| Website | HTML, CSS, vanilla JS (no frameworks) |
| Bot deploy | Fly.io Free Tier (256 MB RAM) |
| Backend deploy | Alibaba ECS Singapore (`ecs.t6-c1m4.large`, 2 vCPU, 8 GB RAM) |
| Domain | merge-video.osovsky.com |

## Project Structure

```
merge-video/
├── backend/
│   ├── main.py             # FastAPI — API + static serving + /style.css route
│   ├── video.py            # Download → normalize → merge → upload
│   ├── auth.py             # YouTube/Gmail OAuth2 + email notifications
│   ├── jobs.py             # Async single-worker job queue + Job model
│   ├── config.py           # Environment config (dirs, limits, keys)
│   ├── requirements.txt    # Python dependencies
│   └── .env.example        # Env template
├── bot/
│   ├── main.py             # aiogram 3 Telegram bot (polling mode)
│   ├── Dockerfile          # Fly.io container image
│   ├── fly.toml            # Fly.io deployment config
│   └── requirements.txt    # Bot dependencies (aiogram, aiohttp)
├── site/
│   ├── index.html          # Landing + merge app (SPA)
│   ├── style.css           # All styles (mobile-first, no external frameworks)
│   └── lib_hCbTwtypfRFzmFju/  # Static assets (favicon, logo)
├── deploy/
│   ├── nginx.conf          # Reverse proxy config
│   ├── merge-video.service # Backend systemd unit
│   ├── merge-bot.service   # Bot systemd unit
│   └── setup.sh            # VPS setup script (Ubuntu, dependencies)
├── assets/                 # Dev.to article images
├── devto-article.md        # Part 1: "How I Built a Video Merge Service"
├── devto-article-2.md      # Part 2: "3 Deployment Fails"
├── README.md
├── LICENSE                 # MIT
└── .gitignore
```

## Data Flow

### YouTube URLs (Web)
```
User → POST /merge {urls, title, merge_mode}
  → JobQueue → worker
  → yt-dlp download via Decodo SOCKS5h proxy → temp/{job_id}/001.mp4, 002.mp4, ...
  → Two-pass merge → YouTube upload → email notification
  → Cleanup temp
```

> YouTube blocks datacenter IPs. All yt-dlp downloads are routed through a residential proxy (Decodo, SOCKS5h) configured via `PROXY_URL` in `.env`.

### Local File Upload (Web)
```
User → POST /merge/upload (multipart: files[], title, merge_mode, target_w, target_h)
  → Save files to temp/{job_id}/
  → JobQueue → worker
  → Two-pass merge → email notification
  → Delayed cleanup (1 hour)
```

### Telegram Bot
```
User → /start → sends YouTube URLs one by one
  → /done → selects quality (Compact / High Quality / Lossless)
  → Bot → POST /merge to backend
  → Polls /status/{job_id} every 10 sec
  → Sends result or error to chat
```

## Two-Pass Merge (re-encode modes)

```
Pass 1 — Normalize each file individually:
  ffmpeg -i input.mp4 -vf "scale=W:H:...,pad=W:H:..." → normalized/part_0001.mp4
  (handles mixed resolutions, missing audio, different codecs)

Pass 2 — Concat demuxer (no re-encode, instant):
  ffmpeg -f concat -i filelist.txt -c copy → merged.mp4
```

**Why two-pass?** Single-pass `filter_complex` with 50+ inputs causes ffmpeg `concat` filter reinit errors. Two-pass is reliable regardless of file count.

## Merge Modes

| Mode | CRF | Description |
|------|-----|-------------|
| `compact` | 23 | Smaller file, good quality (default) |
| `highquality` | 18 | Near-original quality, larger file |
| `lossless` | — | Concat demuxer only, no re-encoding |

## Smart Resolution Detection

1. **Browser** probes each file via `<video>` element → gets `videoWidth × videoHeight`
2. **Minimum resolution** across all files → becomes target output
3. **target_w / target_h** sent to backend via FormData
4. **ffmpeg** normalizes each file to target resolution (scale + pad + letterbox)

## Email Notifications

All emails sent via Gmail API with CC to `izdanie@gmail.com`.

| Event | Subject |
|-------|---------|
| Auth | 🔐 Merge Video — Authorized |
| Job start | 📦 Merging: "title" (N files) |
| Success | 🎬 Merged: "title" (with size + resolution) |
| Error | ❌ Merge failed: "title" (with error excerpt) |

## Website Architecture

Site rewritten from scratch (no Umso framework). Single `index.html` + external `style.css`.

| Element | Implementation |
|---------|---------------|
| Header | Logo, Merge Now / Telegram Bot buttons, Google avatar with dropdown |
| Hero | Title, subtitle, MIT badge, CTA buttons (mobile-only) |
| Features | 3 blocks: Google Drive, Google Photos, YouTube |
| Modal | Tabs: YouTube URLs / Local Files, quality selector, toggle switch, output title |
| Coffee status | During processing: ☕ "Go grab a coffee!" + email reminder (replaces raw progress) |
| Footer | Copyright, social icons (GitHub, Telegram, DEV.to) |
| Auth | Google Sign-In → avatar with rainbow border, dropdown (name, email, Sign Out) |
| Mobile | Responsive `@media (max-width: 768px)`, compact feature blocks |

### Static Serving

Backend (`main.py`) serves static files:
- `/` → `site/index.html`
- `/style.css` → `site/style.css`
- `/css/*` → `site/css/`
- `/lib_*/*` → `site/lib_*/`

## Deployment

### Bot (Fly.io)
- Free Tier: 1 shared CPU, 256 MB RAM
- Polling mode (no webhook server — saves RAM)
- `fly deploy` from `bot/`

### Backend (Alibaba ECS — Singapore)
- Instance: `ecs.t6-c1m4.large` (2 vCPU, 8 GB RAM, Debian 12)
- IP: `47.84.36.115`
- Zone: `ap-southeast-1c` (Singapore)
- Billing: PayAsYouGo (~$20/mo)
- Domain: `merge-video.osovsky.com`
- Nginx reverse proxy (port 80 → 8000)
- Systemd service: `merge-video.service`

## Key Concepts

- **Single worker queue** — one job at a time to avoid CPU/RAM overload
- **OAuth2 per user** — YouTube upload + Gmail send, credentials in-memory (lost on restart)
- **Two-pass merge** — reliable for any file count and mixed formats
- **Smart resolution** — auto-detect min resolution, no upscaling
- **File sorting** — alphabetical with numeric awareness (`localeCompare`)
- **Auto cleanup** — immediate on upload/error, 1-hour delay for download-only
- **No external CSS frameworks** — plain CSS, full control over styles
- **Google OAuth in Testing mode** — only registered test users can sign in; verification needed for >100 users

## Known Limitations

| Limitation | Details |
|-----------|---------|
| In-memory stores | `_profile_store` / `_token_store` lost on server restart |
| Google OAuth | App in "Testing" — max 100 test users without verification |
| Large files | Tested up to 13 GB; >50 GB needs worker with >6 GB RAM |
| Single worker | No parallel merges; queue only |
| Bot ↔ Backend | Bot calls backend API over public internet (no internal network) |
| Proxy cost | YouTube downloads require residential proxy (~$6/GB via Decodo) |

## Stress Test Results

- ✅ 52 YouTube videos merged (varied resolutions/codecs)
- ✅ 13 GB local file upload via HTTP multipart
- ✅ E2E: 2 YouTube videos (870 MB) → Decodo proxy → merge → YouTube upload (980 MB) → email
