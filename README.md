<div align="center">

# 🎬 Merge Video

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Telegram](https://img.shields.io/badge/Telegram_Bot-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

**Merge YouTube videos into one and upload directly to your channel**

</div>

> Send YouTube URLs → download → merge via ffmpeg → upload to your YouTube via OAuth. Works through Telegram bot and web interface.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔗 YouTube URL input | Paste multiple YouTube links |
| ⬇️ yt-dlp download | Fast, reliable video downloads |
| 🎞 ffmpeg merge | Concat filter, libx264 + AAC |
| ⬆️ YouTube upload | OAuth2, uploads as unlisted |
| 🤖 Telegram bot | aiogram 3, FSM, status polling |
| 🌐 Web interface | Coming soon |
| 📊 Job queue | Async single-worker processing |

---

## 🏗 Architecture

```
├── backend/          # FastAPI server
│   ├── main.py       # API endpoints
│   ├── video.py      # yt-dlp + ffmpeg + YouTube upload
│   ├── auth.py       # YouTube OAuth2 flow
│   ├── queue.py      # Async job queue
│   └── config.py     # Configuration
├── bot/              # Telegram bot
│   └── main.py       # aiogram 3 bot
└── site/             # Web interface (coming soon)
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- [ffmpeg](https://ffmpeg.org/)
- Google Cloud project with YouTube Data API v3

### Setup

```bash
git clone https://github.com/maximosovsky/merge-video.git
cd merge-video

# Backend
cd backend
pip install -r requirements.txt
cp .env.example .env
# Fill in .env with your credentials
python main.py

# Bot (in another terminal)
cd bot
pip install -r requirements.txt
export BOT_TOKEN=your_bot_token
export API_URL=http://localhost:8000
python main.py
```

---

## 📄 License

[Maxim Osovsky](https://www.linkedin.com/in/osovsky/). Licensed under [MIT](LICENSE).
