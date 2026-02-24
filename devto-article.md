---
title: I Tried to Merge 52 Video Files Automatically. Here Are 3 Bugs That Almost Killed the Project
published: false
description: How a personal pain of merging hours of strategy session recordings turned into a self-hosted video merging service — and 3 production bugs I didn't see coming.
tags: python, ffmpeg, fastapi, buildinpublic
cover_image: https://raw.githubusercontent.com/maximosovsky/merge-video/main/assets/merge-video-1.jpg
---

## The $1,500 Problem

I film long strategy sessions — 6 to 8 hours each. When you record for that long, things go wrong. The battery dies. The power goes out. And when it does, the entire file gets corrupted.

![Maxim Osovsky filming a strategy session](https://raw.githubusercontent.com/maximosovsky/merge-video/main/assets/maxim-osovsky-strategy-session.jpg)

So I set my camera to record in short segments — about 20 minutes each. Safe, but now I have **52 separate video files** after every session that I need to merge into one.

I used to outsource this. Send files to an editor, wait, pay. Over the years I've spent at least **$1,500–2,000** just on merging clips — not editing, not color grading, just *joining files together*.

In 2022 I decided to build my own service. I called it [Merge Video](https://github.com/maximosovsky/merge-video).

## The Road Here: 3 Failed Attempts

This isn't v1. I've been trying to solve this problem since 2022 — across three separate repositories:

| Version | Stack | What happened |
|---------|-------|---------------|
| [v1 — Merge-video.online](https://github.com/maximosovsky/Merge-video.online) | Node.js, Telegraf, youtube-dl, ffmpeg | Worked on AWS EC2 but died with the server. Single 424-line file |
| [Landing page](https://github.com/maximosovsky/merge-video-landing) | Umso no-code builder, GitHub Pages | Static promo page |
| [v2 — Microservices](https://github.com/maximosovsky/Merve-video.online-vol.2-) | Python, aiogram, Flask, FastAPI | Ambitious: 3 microservices, payments, Google Drive delivery. Pytube broke when YouTube changed their API |

The original idea was **fully cloud-based**: take videos from YouTube or Google Drive, merge them on the server, upload back to YouTube — without ever touching the local machine. It worked for small files, but my real problem was 52 local recordings sitting on a hard drive.

Multiple developers refused to work on this project. They didn't see the problem it solved — "just use a video editor." One developer turned down a **$2,000 offer** to automate the pipeline.

The current version — [merge-video](https://github.com/maximosovsky/merge-video) — consolidates all three repos into one and adds what was always missing: **local file upload and merge**. I rebuilt the frontend and backend in **3 days** with the help of [Antigravity](https://blog.google/technology/google-deepmind/gemini-ai-update-august-2024/), an AI coding assistant by Google DeepMind. What took months of failed outsourcing now took a weekend of focused work.

## What I Built

The idea is simple: **send links or upload files, go to sleep, wake up to a merged video on YouTube and a link in your email.**

No manual work. No editor. No waiting at the screen.

| Feature | How it works |
|---------|-------------|
| YouTube URLs | Paste links → [yt-dlp](https://github.com/yt-dlp/yt-dlp) downloads → [ffmpeg](https://ffmpeg.org/) merges |
| Local files | Drag & drop up to 100 files → server merges |
| YouTube upload | Merged result uploads to your channel via OAuth |
| Email notifications | 📧 Auth → Start → Done/Error — all sent via [Gmail API](https://developers.google.com/gmail/api) |
| Telegram bot | Send YouTube links to [@MergeVideoBot](https://t.me/MergeVideoBot) |
| 3 quality modes | Compact (CRF 23) · High Quality (CRF 18) · Lossless (concat demuxer) |

### The "Email Bot" Concept

I started with a [Telegram bot](https://core.telegram.org/bots/api) — it was the quickest way to build an interface. But I realized: not everything should live inside Telegram.

What I really wanted was an **email bot**. Not a chatbot. The idea:

1. You submit files or links through the web app
2. You close the browser and go to sleep
3. The server does everything in the background
4. You wake up to an email: `🎬 Your merged video is ready! ▶ View on YouTube`

The merge runs on the server regardless of whether the browser is open. Gmail API sends you status updates at every step — authorization, job start, completion, and errors. All from your own Gmail, to your own Gmail. No SMTP servers, no third-party email services.

### Architecture

```
Browser / Telegram Bot
        ↓
   FastAPI Backend
        ↓
  ┌─────────────┐
  │  Job Queue   │ ← async single-worker
  │  (in-memory) │
  └──────┬──────┘
         ↓
  yt-dlp → ffmpeg → YouTube API
         ↓
  Gmail API → email notification
```

**Stack:** [Python](https://www.python.org/) 3.12, [FastAPI](https://fastapi.tiangolo.com/), [ffmpeg](https://ffmpeg.org/), [yt-dlp](https://github.com/yt-dlp/yt-dlp), [aiogram](https://docs.aiogram.dev/) 3, Google OAuth2

---

## The Stress Test: 52 Files, 13 GB

Everything worked fine on small tests — 2 files, 40 MB each, merged in a minute. So I ran the real thing: **52 video files, 13 GB total**.

![52 video files loaded into Merge Video by Maxim Osovsky](https://raw.githubusercontent.com/maximosovsky/merge-video/main/assets/screenshot52.jpg)

Three things broke. Every one of them taught me something.

---

## Bug #1: ffmpeg Choked on 52 Mixed-Format Files

### What happened

I fed ffmpeg a single command with 52 inputs using `filter_complex`. Some files were 4K (3840×2160), others were 1080p, and some had no audio track. ffmpeg crashed:

```
Input link in0:v0 parameters (size 1920x1080, SAR 1:1) do not match
the corresponding output link parameters (3840x2160, SAR 1:1)
```

The concat filter requires **all inputs to have identical parameters** — same resolution, same codec, same audio format. With 52 random files, that's never the case.

### What I tried first

Added `scale` and `pad` filters to normalize everything to 1920×1080 inside the same massive `filter_complex`. Still crashed — the filter graph with 52 inputs was too complex and fragile.

### What actually worked: Two-Pass Merge

I completely changed the approach:

**Pass 1 — Normalize each file independently:**
```python
for i, f in enumerate(files):
    print(f"  📦 Normalizing {i+1}/{len(files)}: {f.name}")
    # Scale to target resolution with letterbox
    # Add silent audio if missing (detected via ffprobe)
    # Re-encode to uniform h264/aac format
```

**Pass 2 — Concat demuxer (no re-encoding):**
```python
# Write file list
for nf in normalized_files:
    list_file.write(f"file '{nf}'\n")

# Merge without re-encoding — instant
cmd = ["ffmpeg", "-f", "concat", "-safe", "0", "-i", list_path,
       "-c", "copy", str(output)]
```

This gave me a bonus I didn't expect: **visible progress**. Instead of a silent 30-minute ffmpeg run, I could see `📦 Normalizing 1/52... 2/52... 3/52...` in the terminal. Debugging became trivial — if file #37 fails, you know exactly which one.

### The lesson

> When a single-step pipeline breaks under scale, don't fix the step — **split it into stages.** Each stage is simpler, debuggable, and independently testable.

---

## Bug #2: 13 GB of stderr Crashed Python

### What happened

The merge ran for a few minutes, then:

```
Exception in thread Thread-2 (_readerthread):
MemoryError
```

This wasn't ffmpeg failing. It was **Python's `subprocess.run`** trying to read ffmpeg's stderr output into memory. When processing 13 GB of video, ffmpeg writes progress for every single frame to stderr — that's gigabytes of text output.

### Why it worked on small files

With 2 files totaling 80 MB, ffmpeg's stderr output was maybe a few kilobytes. `subprocess.PIPE` handled it fine. At 13 GB and thousands of frames? Python ran out of memory before ffmpeg even finished.

### The fix

Redirect stdout and stderr to **temp files on disk** instead of memory pipes:

```python
async def _run(cmd, cwd=None):
    def _sync_run():
        with tempfile.NamedTemporaryFile(delete=False) as out_f, \
             tempfile.NamedTemporaryFile(delete=False) as err_f:
            result = subprocess.run(cmd, cwd=cwd,
                                    stdout=out_f, stderr=err_f)
            # On error, read only the last 4KB of stderr
            if result.returncode != 0:
                err_f.seek(max(0, err_f.tell() - 4096))
                raise RuntimeError(err_f.read().decode())
    await asyncio.to_thread(_sync_run)
```

### The lesson

> `subprocess.PIPE` is a time bomb for long-running processes. If you can't predict the output size, **write to files.** This is standard in DevOps but easy to miss in application code.

---

## Bug #3: `asyncio.create_subprocess_exec` Doesn't Work on Windows

### What happened

The first time I tried to merge anything:

```
❌ Error: NotImplementedError()
```

`asyncio.create_subprocess_exec` requires `ProactorEventLoop` on Windows. But [uvicorn](https://www.uvicorn.org/) (the ASGI server running FastAPI) sets its own event loop policy and overrides mine.

### What I tried first

```python
# Tried setting the policy in main.py — uvicorn overwrites it
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
```

Didn't work. Uvicorn ignores this and uses its own loop.

### What actually worked

Gave up on `asyncio.create_subprocess_exec` entirely. Used synchronous `subprocess.run` wrapped in `asyncio.to_thread`:

```python
async def _run(cmd, cwd=None):
    def _sync_run():
        return subprocess.run(cmd, cwd=cwd, ...)
    await asyncio.to_thread(_sync_run)
```

Less elegant than native async subprocess, but **it works on every platform** without fighting the ASGI server.

### The lesson

> "Correct by documentation" ≠ "works in your stack." When two frameworks fight over the event loop, sometimes the pragmatic solution beats the elegant one.

---

## What I Learned

| What I expected | What actually happened |
|----------------|----------------------|
| ffmpeg handles any number of inputs | 52 mixed-format files = crash |
| `subprocess.PIPE` is fine for any process | 13 GB of stderr = MemoryError |
| `asyncio.create_subprocess_exec` is cross-platform | Windows + uvicorn = NotImplementedError |
| Small test = production-ready | Small test hides 3 critical bugs |

---

## Timeline

| Year | Milestone |
|------|----------|
| 2022 | [v1](https://github.com/maximosovsky/Merge-video.online) — Node.js Telegram bot on AWS EC2. Worked but fragile |
| 2023 | [v2](https://github.com/maximosovsky/Merve-video.online-vol.2-) — Python microservices, payments. External dependencies killed it |
| 2023 | [Landing page](https://github.com/maximosovsky/merge-video-landing) — Umso builder, Product Hunt links |
| 2024 | Multiple developers decline the project. $2,000 offered and refused |
| 2026 | [Current version](https://github.com/maximosovsky/merge-video) — rebuilt in 3 days with AI. FastAPI + yt-dlp + ffmpeg + Gmail + YouTube OAuth |

## Where It Stands Now

This is a build-in-public project. Some things work, some don't yet:

| Component | Status |
|-----------|--------|
| Web app — merge & download | ✅ Working |
| Telegram bot | ✅ Deployed on [Fly.io](https://fly.io/) |
| Email notifications | ✅ Gmail API |
| YouTube upload | ✅ OAuth2 |
| Stress test (52 files, 13 GB) | ✅ Passed |
| Large file upload via HTTP | ❌ Hangs on 13 GB |
| Credentials persistence | ❌ Lost on server restart |
| Backend deployment | ❌ Still localhost |

The project is open source: [**github.com/maximosovsky/merge-video**](https://github.com/maximosovsky/merge-video)

---

## Try It

```bash
git clone https://github.com/maximosovsky/merge-video.git
cd merge-video/backend
pip install -r requirements.txt
python main.py
# Open http://localhost:8000
```

Or send YouTube links to the Telegram bot: [@MergeVideoBot](https://t.me/MergeVideoBot)

---

This is part 1. The 3 bugs above were just the beginning — I've already hit new ones while deploying and stress-testing. I'll write about those next.

*Building something similar? Hit me up in the comments — I'd love to compare notes.*

Building in public, one utility at a time. Follow the journey: [LinkedIn](https://www.linkedin.com/in/osovsky/) · [GitHub](https://github.com/maximosovsky)
