<!-- 
  Based on: https://github.com/maximosovsky/readme-guidelines
-->

<div align="center">

# 🎬 Merge Video

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![ffmpeg](https://img.shields.io/badge/ffmpeg-007808?style=for-the-badge&logo=ffmpeg&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)

**Merge multiple videos into one — from YouTube URLs or local files**

</div>

> Paste YouTube links or drag local files → get one merged video. Optionally upload the result straight to your YouTube channel.

<div align="center">
  <a href="#-quick-start">Quick Start</a> · <a href="#-features">Features</a> · <a href="#-tech-stack">Tech Stack</a> · <a href="#-roadmap">Roadmap</a>
</div>

---

## 💡 Concept

Merge Video is a self-hosted service with a **web UI**, **Telegram bot**, and **REST API**. It uses a reliable **two-pass merge** pipeline (normalize → concat) that handles mixed resolutions, codecs, and 50+ files without errors.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔗 **YouTube URLs** | Paste links — videos downloaded via yt-dlp through residential proxy and merged |
| 📁 **Local Upload** | Drag & drop files from your computer |
| 🎚️ **3 Quality Modes** | Compact (CRF 23), High Quality (CRF 18), Lossless (no re-encode) |
| 📐 **Smart Resolution** | Auto-detects minimum resolution across files, no upscaling |
| ▶️ **YouTube Upload** | Upload merged result directly to your YouTube channel via OAuth |
| 📧 **Email Notifications** | Status updates via Gmail API (start, success, error) |
| 🤖 **Telegram Bot** | Send URLs → pick quality → get result in chat |
| 📱 **Mobile-Friendly** | Responsive web UI, works on any device |

---

## 🚀 Quick Start

```bash
git clone https://github.com/maximosovsky/merge-video.git
cd merge-video/backend
cp .env.example .env
pip install -r requirements.txt
uvicorn main:app --port 8000
```

Open `http://localhost:8000` in your browser.

<details>
<summary>🤖 Run Telegram Bot</summary>

```bash
cd bot
cp .env.example .env
pip install -r requirements.txt
python main.py
```

</details>

<details>
<summary>⚙️ Environment Variables</summary>

```bash
cp .env.example .env
```

| Variable | Description | Required |
|----------|-------------|----------|
| `GOOGLE_CLIENT_ID` | OAuth2 client ID | Yes |
| `GOOGLE_CLIENT_SECRET` | OAuth2 client secret | Yes |
| `GOOGLE_REDIRECT_URI` | OAuth2 callback URL | Yes |
| `BASE_URL` | Backend public URL | Yes |
| `BOT_TOKEN` | Telegram bot token | Bot only |
| `BACKEND_URL` | Backend URL for bot API calls | Bot only |
| `PROXY_URL` | SOCKS5h residential proxy for YouTube downloads | YouTube mode |

</details>

---

## 🏗️ Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11, FastAPI, uvicorn |
| Video download | yt-dlp + PySocks (via residential proxy) |
| Video merge | ffmpeg (two-pass: normalize → concat demuxer) |
| YouTube upload | google-api-python-client, OAuth2 |
| Email | Gmail API (OAuth2) |
| TG Bot | aiogram 3 (polling mode) |
| Website | HTML, CSS, vanilla JS |
| Bot deploy | Fly.io Free Tier |
| Backend deploy | Alibaba ECS Singapore |

```
merge-video/
├── backend/
│   ├── main.py             # FastAPI app + static serving
│   ├── video.py            # Download → normalize → merge
│   ├── auth.py             # YouTube/Gmail OAuth2
│   ├── jobs.py             # Async job queue
│   └── config.py           # Environment config
├── bot/
│   ├── main.py             # Telegram bot (polling)
│   ├── Dockerfile          # Fly.io container
│   └── fly.toml            # Fly.io config
├── site/
│   ├── index.html          # Landing + merge app (SPA)
│   └── style.css           # Mobile-first styles
└── deploy/
    ├── nginx.conf          # Reverse proxy
    ├── merge-video.service # Backend systemd unit
    └── setup.sh            # VPS setup script
```

---

## 🗺️ Roadmap

- [x] Two-pass merge pipeline
- [x] YouTube upload via OAuth
- [x] Email notifications (Gmail API)
- [x] Telegram bot (Fly.io)
- [x] Backend deploy (Alibaba ECS)
- [x] DNS — `merge-video.osovsky.com`
- [x] SSL — certbot + HTTPS
- [x] Google Console — production redirect URIs
- [x] Telegram Bot — connected to production backend
- [x] Residential proxy (Decodo) for YouTube downloads
- [x] End-to-end production test (YouTube URLs → proxy → merge → upload → email)

---

## 🤝 Contributing

Fork → `feature/name` → PR

---

## 📄 License

[Maxim Osovsky](https://www.linkedin.com/in/osovsky/). Licensed under [MIT](LICENSE).