# Merge Video — Chat Exports Summary

Summary of 3 chat sessions covering the full development lifecycle of the Merge Video project.

---

## Chat 78: Project Creation from Scratch

**Scope:** First session — building the entire project from zero.

### What was built
- **Backend** (FastAPI + uvicorn): `/merge` endpoint, job queue with background worker, Google OAuth for YouTube/Gmail, email notifications (start/success/error)
- **Telegram Bot** (aiogram): URL collection via FSM, merge quality selection (Compact/High/Lossless), job polling with progress updates, YouTube upload integration
- **Website** (single-file SPA): Hero section, social links, Google Sign-In, merge modal
- **Video engine** (`video.py`): Two-pass ffmpeg merge, smart resolution detection, three quality modes (CRF 23 / CRF 18 / concat demuxer)

### Key technical challenges solved
| Problem | Solution |
|---------|----------|
| Windows `asyncio` + `subprocess` crash | `asyncio.to_thread()` with `subprocess.run` instead of `asyncio.create_subprocess_exec` |
| `MemoryError` on large ffmpeg stderr | Redirect stderr to temp files instead of `PIPE` |
| ffmpeg fails on mixed codecs/resolutions | Two-pass: normalize all to same resolution/codec first, then concat |
| Wrong ffmpeg arch (ARM binary on x64 Windows) | Reinstalled via `winget install Gyan.FFmpeg` |
| aiogram/aiohttp version conflict | Pinned `aiohttp<3.11` in bot requirements |

### Stress test results
- Successfully merged **52 YouTube videos** (varied resolutions/codecs)
- Tested **13 GB local file upload** via HTTP multipart

---

## Chat 79: Deployment & UI Revamp

**Scope:** Oracle Cloud deployment attempts, GitHub repo creation, site UI overhaul.

### Oracle Cloud — Full Failure Sequence
1. **VM creation** — Milan region (A1.Flex ARM): Oracle limited to **1 OCPU + 6 GB RAM** instead of advertised 4+24
2. **Public IPv4** — checkbox wouldn't enable due to subnet config issues; had to edit networking manually
3. **200 GB disk** — configured successfully
4. **Second account attempt** — Oracle blocked `myemail+oci2@gmail.com` alias format; user tried second Gmail + Regus office address in Tilburg, NL + second phone → Oracle blocked by **credit card fingerprint**
5. **Result**: 2+ hours wasted, zero usable servers

> This became the basis for the dev.to Part 2 article: *"3 Deployment Fails"*

### Deploy architecture discussion
| Option | Verdict |
|--------|---------|
| Oracle Cloud Free (all-in-one) | Recommended but failed on capacity |
| Vercel + Upstash Redis + QStash | Bot rewrite needed; can't run ffmpeg on serverless |
| Fly.io | Best free option for bot only (chosen later in separate session) |
| Alibaba/AWS spot workers | Deferred — for scale-up phase |

### UI improvements (site)
- **DeployBridge-style modal** — macOS dots (🔴🟡🟢), gradient Merge button, modern inputs
- **Avatar dropdown** — light purple background, name + email + Sign Out, Lato font
- **Google avatar** — rainbow border on hover (conic-gradient with Google colors)
- **MIT badge** — `🛡 Open Source · MIT License` in hero section
- **Header** — removed sticky/fixed positioning, removed shadow

### Infrastructure
- Created GitHub repo `maximosovsky/merge-video` via PowerShell GraphQL script
- Added deploy configs: `nginx.conf`, systemd units, `setup.sh`
- Implemented YouTube auth via Telegram (webhook + aiohttp server on :8081)

### Discovered gotchas
- PowerShell curly quotes in `.ps1` files from `write_to_file` — added to Known Gotchas in `.context.md`

---

## Chat 80: Dev.to Articles & Site Polish

**Scope:** Writing 2 articles, extensive modal UI refinement, mobile-first redesign, full site rewrite.

### Dev.to Articles

**Part 1** — *"How I Built a Video Merge Service"*
- Project origin story, technical challenges (ffmpeg, asyncio, MemoryError)
- Build-in-public angle, strategy session photos
- SEO: author name in alt text, proper cover image

**Part 2** — *"3 Deployment Fails"*
- Oracle Cloud frustrations: Milan capacity limits, second account blocked
- Scorecard: "2 hours, 0 servers"
- Fly.io comparison: 10 minutes vs 2 hours
- Free tier philosophy: *"at prototype stage, free tier makes the most sense"*

**Publishing fixes:**
- Branch name mismatch (`main` vs `master`) broke all image URLs
- Dev.to aggressive image caching required renaming files
- Added workflow rule: always check `git branch` before writing URLs
- Changed workflow to publish articles with `published: true` by default

### Modal UI refinements (detailed)
- Quality buttons (🗜️⚖️💎) — horizontal row, emoji 48px left + text right
- Tab switching — fixed height (`min-height: 220px`) to prevent modal jumping
- ⓘ info button — replaced Unicode with inline SVG, placed next to "Upload to YouTube"
- Toggle switch — replaced checkbox with styled toggle for "Upload to YouTube"
- Output Title — inline gray prefix "Output Title:" that turns black on hover/focus
- DEV.to social icon — replaced WebP with SVG (`fill="currentColor"`) for consistent hover

### Google avatar fix
- Issue: `lh3.googleusercontent.com` images blocked by referrer policy
- Fix: added `referrerpolicy="no-referrer"` to avatar `<img>`

### Mobile-first redesign → Full site rewrite
1. First attempt: added `@media (max-width: 600px)` to existing code
2. Problem: Umso framework CSS (`margin-bottom: 50px` at `max-width: 760px`) couldn't be overridden
3. Changed breakpoint to `768px` — still failed
4. **Decision: rewrote entire site from scratch**
   - Saved old file as `index_old.html`
   - Created separate `style.css` (no more Umso framework dependency)
   - Added `/style.css` route to backend `main.py`
   - Clean semantic HTML, all JS preserved
   - Mobile: burger menu (later removed), compact feature blocks, hero CTA buttons

---

## Cross-Session Patterns

| Pattern | Details |
|---------|---------|
| **PowerShell gotchas** | No `&&`, no heredoc, curly quotes in `.ps1`, `<`/`>` reserved operators |
| **Git branch** | Project uses `master`, not `main` — constant URL breakage |
| **Umso framework** | Source of all CSS override battles; eventually removed entirely |
| **Google OAuth** | App in "Testing" mode — only registered test users can sign in |
| **In-memory stores** | `_profile_store` / `_token_store` lost on server restart (`reload=True`) |
| **Build-in-public** | Central theme: articles include personal photos, honest frustration, real timelines |

## Current State (after all 3 sessions)
- ✅ Backend API functional (FastAPI)
- ✅ Telegram bot functional (aiogram)
- ✅ Website rewritten (clean HTML/CSS/JS, no Umso)
- ✅ GitHub repo: `maximosovsky/merge-video`
- ✅ 2 dev.to articles published
- ✅ Bot deployed to Fly.io (separate session)
- ⏳ Backend deployment pending (Oracle failed, alternative TBD)
- ⏳ Google OAuth verification needed for >100 users
- ⏳ Large file upload optimization (>13 GB)
