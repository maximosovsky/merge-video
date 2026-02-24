# Architecture — Merge Video

## Overview

Сервис для склейки видеофайлов (YouTube URLs или локальные файлы) в одно видео с возможностью загрузки на YouTube-канал пользователя и email-уведомлениями о статусе.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI, uvicorn |
| Video download | yt-dlp |
| Video merge | ffmpeg (two-pass: normalize → concat demuxer) |
| YouTube upload | google-api-python-client, OAuth2 |
| Email | Gmail API (OAuth2, send scope) |
| TG Bot | aiogram 3, aiohttp |
| Website | HTML, CSS, vanilla JS |
| Deploy | VPS (Alibaba ECS) |
| Domain | merge-video.osovsky.com |

## Project Structure

```
merge-video/
├── backend/
│   ├── main.py           # FastAPI — API endpoints + static serving
│   ├── video.py          # Download → normalize → merge → upload
│   ├── auth.py           # YouTube/Gmail OAuth2 + email notifications
│   ├── jobs.py           # Async single-worker job queue + Job model
│   ├── config.py         # Environment config (dirs, limits, keys)
│   └── .env.example      # Env template
├── bot/
│   └── main.py           # aiogram 3 Telegram bot
├── site/
│   └── index.html        # Landing + merge app (single-file SPA)
├── README.md
├── LICENSE
└── .gitignore
```

## Data Flow

### YouTube URLs
```
User → POST /merge {urls, title, merge_mode}
  → JobQueue → worker
  → yt-dlp download → temp/{job_id}/001.mp4, 002.mp4, ...
  → Two-pass merge → YouTube upload → email notification
  → Cleanup temp
```

### Local File Upload
```
User → POST /merge/upload (multipart: files[], title, merge_mode, target_w, target_h)
  → Save files to temp/{job_id}/
  → JobQueue → worker
  → Two-pass merge → email notification
  → Delayed cleanup (1 hour)
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
| Job start | ⏳ Merging: "title" (N files) |
| Success | 🎬 Merged: "title" (with size + resolution) |
| Error | ❌ Merge failed: "title" (with error excerpt) |

## Key Concepts

- **Single worker queue** — one job at a time to avoid CPU/RAM overload
- **OAuth2 per user** — YouTube upload + Gmail send, credentials in-memory
- **Two-pass merge** — reliable for any file count and mixed formats
- **Smart resolution** — auto-detect min resolution, no upscaling
- **File sorting** — alphabetical with numeric awareness (`localeCompare`)
- **Auto cleanup** — immediate on upload/error, 1-hour delay for download-only
- **Stateless frontend** — single HTML file, polls `/status/{job_id}` for progress
