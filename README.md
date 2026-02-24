<div align="center">

# 🎬 Merge Video

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![ffmpeg](https://img.shields.io/badge/ffmpeg-007808?style=for-the-badge&logo=ffmpeg&logoColor=white)
![Telegram](https://img.shields.io/badge/Telegram_Bot-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

**Merge video files into one — upload local files or paste YouTube URLs**

</div>

> Upload local video files or paste YouTube links → merge via ffmpeg → optionally upload to your YouTube channel. Email notifications at every step. Works through web interface and Telegram bot.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 📁 Local file upload | Upload up to 100 video files (any format/resolution) |
| 🔗 YouTube URL input | Paste YouTube links or playlist URLs |
| ⬇️ yt-dlp download | Fast, reliable video downloads |
| 🎞 Two-pass merge | Normalize → concat (handles mixed formats reliably) |
| 🎯 Smart resolution | Auto-detect min resolution, no upscaling |
| ⚙️ Quality modes | Compact (CRF 23), High Quality (CRF 18), Lossless |
| ⬆️ YouTube upload | OAuth2, uploads to user's channel |
| 📧 Email notifications | Start, success (with size + resolution), error (via Gmail API) |
| 🔇 Silent audio fix | Auto-generates silent audio for files without sound |
| 🗑 Auto cleanup | Temp files deleted automatically |
| 🤖 Telegram bot | aiogram 3, FSM, status polling |
| 📊 Job queue | Async single-worker processing |

---

## 🏗 Architecture

```
├── backend/
│   ├── main.py       # FastAPI endpoints + static serving
│   ├── video.py      # Download → normalize → merge → upload
│   ├── auth.py       # OAuth2 + Gmail email notifications
│   ├── jobs.py       # Job queue + worker
│   └── config.py     # Configuration
├── bot/
│   └── main.py       # Telegram bot (aiogram 3)
└── site/
    └── index.html    # Single-file SPA (landing + app)
```

### Two-Pass Merge Pipeline

```
52 input files (mixed resolutions/formats)
  ↓
Pass 1: Normalize each file → scale to min resolution, AAC audio, yuv420p
  📦 Normalizing 1/52: video_001.mp4
  📦 Normalizing 2/52: video_002.mp4
  ...
  ↓
Pass 2: Concat demuxer → instant join (no re-encoding)
  ↓
merged.mp4 → YouTube upload → email notification
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- [ffmpeg](https://ffmpeg.org/) (with ffprobe)
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) (for YouTube downloads)
- Google Cloud project with:
  - YouTube Data API v3
  - Gmail API
  - OAuth2 credentials (web app)

### Setup

```bash
git clone https://github.com/maximosovsky/merge-video.git
cd merge-video/backend

pip install -r requirements.txt
cp .env.example .env
# Fill in .env: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI

python main.py
# Open http://localhost:8000/app
```

### Telegram Bot (optional)

```bash
cd bot
pip install -r requirements.txt
export BOT_TOKEN=your_bot_token
export API_URL=http://localhost:8000
python main.py
```

---

## 📧 Email Notifications

Sent via Gmail API after OAuth2 authorization:

| Event | Subject |
|-------|---------|
| Authorized | 🔐 Merge Video — Authorized |
| Merge started | ⏳ Merging: "title" (52 files) |
| Success | 🎬 Merged: "title" — 📐 1920×1080 · 2.3 GB |
| Error | ❌ Merge failed: "title" |

---

## 📄 License

[Maxim Osovsky](https://www.linkedin.com/in/osovsky/). Licensed under [MIT](LICENSE).
