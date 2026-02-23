# Architecture — Merge Video

## Overview

Сервис для склейки YouTube-видео в одно с загрузкой на канал пользователя. Три компонента: Backend API, Telegram бот, веб-сайт.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI, uvicorn |
| Video download | yt-dlp |
| Video merge | ffmpeg (concat filter, libx264 + AAC) |
| YouTube upload | google-api-python-client, OAuth2 |
| TG Bot | aiogram 3, aiohttp |
| Website | HTML, CSS, vanilla JS |
| Deploy | VPS (Alibaba ECS) |
| Domain | merge-video.osovsky.com |

## Project Structure

```
merge-video/
├── backend/
│   ├── main.py           # FastAPI — API endpoints + static serving
│   ├── video.py          # yt-dlp download → ffmpeg merge → YouTube upload
│   ├── auth.py           # YouTube OAuth2 flow + token store
│   ├── queue.py          # Async single-worker job queue
│   ├── config.py         # Environment config
│   └── .env.example      # Env template
├── bot/
│   └── main.py           # aiogram 3 Telegram bot
├── site/
│   ├── index.html        # Landing + merge app
│   ├── css/style.css     # Dark theme, responsive
│   └── js/app.js         # Frontend logic
├── README.md
├── LICENSE
└── .gitignore
```

## Data Flow

```
User (TG Bot or Website)
  ↓
POST /merge {urls, title, user_id}
  ↓
JobQueue.add(job)
  ↓ worker picks up
yt-dlp --download → temp/{job_id}/001.mp4, 002.mp4, ...
  ↓
ffmpeg -filter_complex concat → temp/{job_id}/merged.mp4
  ↓
YouTube Data API v3 upload (OAuth2 credentials)
  ↓
Return youtube.com/watch?v=... URL
  ↓
Cleanup temp files
```

## Key Concepts

- **Single worker queue** — one job at a time to avoid CPU/RAM overload on VPS
- **OAuth2 per user** — each user authorizes their own YouTube, uploads go to their channel
- **Stateless frontend** — site stores user_id in localStorage, polls API for status
- **Bot polling** — aiogram polls for status via API, sends updates to chat
- **Static serving** — FastAPI serves site files at /app, /css, /js
