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
- [ ] E2E тест (OAuth + merge + upload)
- [ ] Frankfurt VPC — повторить `node deploy/cleanup.js`
