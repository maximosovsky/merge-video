# Roadmap — Merge Video

## Текущее состояние (25.02.2026)

```
  ✅ DNS             ✅ SSL             ✅ OAuth redirect
       │                  │                    │
  ┌────▼──────────────────▼────────────────────▼────┐
  │          ECS: 47.84.36.115 (Singapore)          │
  │   nginx :443 (SSL) → FastAPI :8000 → site/ + API│
  │   .env: BASE_URL = https://merge-video.osovsky.com│
  │   fail2ban + UFW (22/80/443) + SSH key-only     │
  └─────────────────────────────────────────────────┘

  ┌─────────────────────┐
  │  Telegram Bot (Fly)  │  ✅ BACKEND_URL set
  │  Polling mode        │
  └─────────────────────┘
```

## Целевая схема

```
  Пользователь
       │
       ├──── https://merge-video.osovsky.com ────┐
       │     (сайт + API)                        │
       │                                         ▼
       │                              ┌──────────────────┐
       │                              │   GoDaddy DNS     │
       │                              │  A → 47.84.36.115 │
       │                              └────────┬─────────┘
       │                                       ▼
       │                              ┌──────────────────┐
       │                              │  ECS Singapore    │
       │                              │  nginx :443 (SSL) │
       │                              │  → FastAPI :8000  │
       │                              │  → site/          │
       │                              └──────┬───────────┘
       │                                     │
       │    ┌────────────────────────────────┤
       │    ▼                                ▼
  ┌────────────┐                    ┌────────────────┐
  │ Google OAuth│                    │  Telegram Bot   │
  │ redirect:  │                    │  (Fly.io)       │
  │ /auth/...  │                    │  → POST /merge  │
  │ callback   │                    │  → GET /status   │
  └────────────┘                    └────────────────┘
```

## 25.02.2026 — Связать всё вместе

| # | Что | Где | Действие |
|---|-----|-----|----------|
| 1 | **DNS** | GoDaddy | A-запись `merge-video` → `47.84.36.115` |
| 2 | **SSL** | SSH на сервер | `certbot --nginx -d merge-video.osovsky.com` |
| 3 | **Backend .env** | SSH на сервер | `BASE_URL` и `GOOGLE_REDIRECT_URI` → `https://merge-video.osovsky.com` |
| 4 | **Google Console** | console.cloud.google.com | Redirect URI → `https://merge-video.osovsky.com/auth/youtube/callback` |
| 5 | **Telegram Bot** | Fly.io | `fly secrets set BACKEND_URL=https://merge-video.osovsky.com` |
| 6 | **Тест** | Браузер | Сайт → Google Sign-In → загрузка → мерж → YouTube upload |

- [x] DNS
- [x] SSL
- [x] Backend .env
- [x] Google Console
- [x] Telegram Bot
- [x] Server hardening (fail2ban, UFW, SSH key-only, rate limiting)
- [x] E2E тест (OAuth + merge + upload) ✅ 25.02.2026
- [x] Frankfurt VPC — `node deploy/cleanup.js`

## UX-улучшения

- [x] После отправки на мерж — модальное окно: «Go grab a coffee ☕» + email notification reminder + close button
- [x] Email: показывать только количество файлов, без размера

## Скачивание с YouTube — результаты тестов

Проблема: datacenter IP (47.84.36.115, Alibaba Cloud Singapore) заблокирован YouTube. Node.js установлен, cookies валидны, yt-dlp актуален — блокирует именно IP.

| # | Вариант | Стоимость | Результат | Причина отказа |
|---|---------|-----------|-----------|----------------|
| 1 | **yt-dlp с сервера** | $0 | ❌ | Datacenter IP заблокирован |
| 2 | **Residential proxy (Decodo)** | $6/GB (2 GB план $12/мес) | ✅ | **Работает!** SOCKS5h через gate.decodo.com:7000 |
| 3 | **VPN-контейнер** | ~$5/мес | — | Не нужен (proxy работает) |
| 4 | **Self-hosted Cobalt** | $0 | ❌ | `Failed to extract signature decipher algorithm` |
| 5 | **Cobalt public API** | $0 | ❌ | JWT/Turnstile auth |
| — | **RapidAPI YTStream** | $0 | ❌ | CDN URL привязан к IP сервиса → 403 |
| — | **savefrom.net** | $0 | ❌ | `CLIENT_NOT_RECOGNIZED` |

### Что работает
- ✅ **yt-dlp с сервера + Decodo proxy** — SOCKS5h residential IP → скачивание работает
- ✅ **yt-dlp с локального ПК** — Firefox cookies + Node.js + EJS → 16.81 MiB за 3:47
- ✅ **ffmpeg merge на Alibaba** — 2170x скорость
- ✅ **YouTube upload с Alibaba** — OAuth2 настроен

### Следующие шаги
- [x] Интегрировать Decodo proxy в `video.py` (expand_urls + download_videos)
- [x] Установить PySocks в venv на сервере
- [x] E2E тест Режим 1: YouTube URLs → proxy download → merge → YouTube upload → email

### E2E тест — 25.02.2026

| Этап | Результат |
|------|-----------|
| Скачивание 2 видео через Decodo | ✅ 872 MB (17 мин + 26 мин) |
| Трафик proxy зафиксирован | 872.63 MB из 2 GB плана |
| ffmpeg нормализация (1920×1080) | ✅ ~60 мин (2 vCPU) |
| ffmpeg concat | ✅ |
| YouTube upload | ✅ 980 MB, 1920×1080 |
| Email уведомление | ✅ "Dorob Holding -1-2" |
