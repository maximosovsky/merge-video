---
title: "6 Ways to Get YouTube Cookies for yt-dlp in 2025 — Only 1 Works"
published: false
description: I tried DPAPI, CDP, rookiepy, OAuth2, and Bearer tokens to extract Chrome cookies. All failed. Firefox solved it in 10 lines of Python.
tags: python, chrome, security, buildinpublic
cover_image: https://raw.githubusercontent.com/maximosovsky/merge-video/master/assets/mergevideo-1.jpg
---

## The Hypothesis

I have a self-hosted video merging service — [Merge Video](https://github.com/maximosovsky/merge-video). It downloads YouTube videos with [yt-dlp](https://github.com/yt-dlp/yt-dlp), merges them with [ffmpeg](https://ffmpeg.org/), and uploads the result back to YouTube.

On localhost everything worked. On a cloud server:

```
ERROR: Sign in to confirm you're not a bot.
Use --cookies-from-browser or --cookies for authentication.
```

YouTube detected the datacenter IP and blocked downloads. The fix seemed obvious: extract cookies from Chrome, upload to server, done.

**My hypothesis:** extracting cookies is a solved problem. Dozens of tools exist. Should take 10 minutes.

**Reality:** I spent 3 hours trying 6 different methods. Only one worked — and it wasn't Chrome.

---

## What Debugging Cookies Taught Me About Strategy

I run [strategic sessions](https://osovsky.medium.com/schem-b1810498982d) — 6-to-10-hour workshops where teams map complex systems before making decisions. We draw the object of management, analyze its place in a larger system, do hindsight and foresight, and only then build a plan. Over 150 sessions so far.

The cookie debugging was the exact opposite of this process.

I had an AI coding assistant — [Antigravity](https://blog.google/technology/google-deepmind/) by Google DeepMind — writing scripts, testing APIs, trying approaches. It's incredibly fast. But here's what happened: we burned through 6 attempts in 3 hours because **neither of us stopped to map the system first**.

The moment I paused and asked: *"What's the plan? Pros, cons, risks, options?"* — the answer became obvious in minutes:

| Without strategy | With strategy |
|-----------------|--------------|
| Try DPAPI → fail | Map the landscape: Chrome encrypts, Firefox doesn't |
| Try rookiepy → fail | Identify constraints: app-bound encryption since July 2024 |
| Try CDP → fail | Evaluate options: only 2 viable paths (Firefox or proxies) |
| Try OAuth → fail | Choose: Firefox = free, proxies = $1.50/GB |
| Try Bearer token → fail | Execute: 10 lines of Python, done |
| Try Firefox → works | |
| **6 attempts, 3 hours** | **1 attempt, 5 minutes** |

This is the pattern I see in every strategic session: teams that jump to solutions before mapping the system waste time on dead ends. Teams that invest 30 minutes in analysis often find the answer without trying a single wrong approach.

AI tools are powerful executors. They'll write any script you ask for in seconds. But they'll also happily execute 5 wrong approaches before someone asks: *"Wait — what are we actually dealing with?"*

The human's job isn't to write code. It's to bring **strategy** — to ask the right questions before the first line of code is written.

---

## ⚠️ First, a Security Warning

Before you Google "export Chrome cookies" — read this.

When I first asked Antigravity to help extract cookies, its very first suggestion was to install a popular Chrome extension — **Get cookies.txt**. Quick, easy, thousands of users. I didn't install it — something felt off about giving a third-party extension access to all my browser sessions.

Good instinct. That extension [turned out to be malware](https://www.reddit.com/r/youtubedl/comments/10ar7o7/if_youve_been_using_the_get_cookiestxt_chrome/). It was silently sending **all your cookies** — login sessions, banking tokens, everything — to its developer. Google removed it from the Chrome Web Store and flagged it as malware.

This isn't an isolated case. Any browser extension with cookie access permissions can steal your sessions. Cookie-stealing malware like [Raccoon](https://malpedia.caad.fkie.fraunhofer.de/details/win.raccoon), [RedLine](https://malpedia.caad.fkie.fraunhofer.de/details/win.redline_stealer), and [Vidar](https://malpedia.caad.fkie.fraunhofer.de/details/win.vidar) has been doing exactly this for years.

**The rule:** never install a third-party extension to export cookies. Use built-in tools or read the database directly.

---

## Attempt #1: DPAPI Decryption Script

Chrome encrypts cookies with [DPAPI](https://learn.microsoft.com/en-us/windows/win32/seccrypto/cng-dpapi) + AES-256-GCM on Windows. I wrote a Python script to call `CryptUnprotectData` via `ctypes`:

```python
class DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", ctypes.wintypes.DWORD),
                 ("pbData", ctypes.POINTER(ctypes.c_char))]

result = ctypes.windll.crypt32.CryptUnprotectData(
    ctypes.byref(input_blob), None, None, None, None, 0,
    ctypes.byref(output_blob)
)
```

**Result:** `CryptUnprotectData failed`

**Why:** [Chrome 127+](https://security.googleblog.com/2024/07/improving-security-of-chrome-cookies-on.html) (July 2024) introduced **app-bound encryption**. The decryption key is now bound to the Chrome binary itself. External programs — even running as the same user — can't decrypt cookies anymore.

---

## Attempt #2: rookiepy

[rookiepy](https://github.com/thewh1teazt3c/rookie) is a Rust-based Python library built specifically for extracting browser cookies. It handles modern Chrome encryption:

```python
import rookiepy
cookies = rookiepy.chrome([".youtube.com", ".google.com"])
```

Ran it as Administrator. 

**Result:** `RuntimeError: decrypt_encrypted_value failed`

**Why:** Same app-bound encryption. Even with admin privileges, no external process can access Chrome's cookie encryption key on Chrome 127+.

---

## Attempt #3: Chrome DevTools Protocol (CDP)

If you can't decrypt cookies externally, maybe ask Chrome directly. Chrome's [DevTools Protocol](https://chromedevtools.github.io/devtools-protocol/) has `Network.getAllCookies`:

```python
ws.send(json.dumps({"id": 1, "method": "Network.getAllCookies"}))
cookies = json.loads(ws.recv())["result"]["cookies"]
```

This requires starting Chrome with `--remote-debugging-port=9222`.

**Result:** `TCP connect to (127.0.0.1 : 9222) failed`

**Why:** On Windows, if Chrome is already running, a new instance with the debug flag opens as a window in the existing process — without the debugging port. I killed Chrome, restarted with the flag. Chrome still wouldn't bind to port 9222. Possibly Windows Defender or a Chrome policy blocking it.

---

## Attempt #4: yt-dlp Native OAuth2

[yt-dlp](https://github.com/yt-dlp/yt-dlp) added native [OAuth2 support](https://github.com/yt-dlp/yt-dlp/wiki/Extractors#logging-in-with-oauth) in 2024. It uses YouTube TV's device code flow:

```bash
yt-dlp --username oauth2 --password '' https://youtu.be/...
# Go to google.com/device and enter code: XXXX-XXXX
```

**Result:** `Login with OAuth is no longer supported`

**Why:** YouTube deprecated this authentication method. It worked for a few months, then Google killed it. The [yt-dlp wiki](https://github.com/yt-dlp/yt-dlp/wiki/FAQ) now says: "Use --cookies instead."

---

## Attempt #5: Per-User OAuth Bearer Token

My app already had [Google OAuth](https://developers.google.com/identity/protocols/oauth2) for YouTube uploads. Users sign in, I get their `access_token`. Why not pass it to yt-dlp?

```python
cmd.extend(["--add-header", f"Authorization:Bearer {access_token}"])
```

**Result:** `Request had insufficient authentication scopes`

**Why:** yt-dlp uses YouTube's **InnerTube API** internally, not the [YouTube Data API v3](https://developers.google.com/youtube/v3). They're completely different authentication systems:

| API | Authentication | Used by |
|-----|---------------|---------|
| YouTube Data API v3 | OAuth2 Bearer token | App uploads |
| YouTube InnerTube API | Session cookies | yt-dlp downloads |

A Data API token simply can't authenticate InnerTube requests.

---

## Attempt #6: Firefox 🏆

After 5 failures with Chrome, I tried Firefox.

**Firefox doesn't encrypt cookies.**

Firefox stores cookies in a plain [SQLite](https://www.sqlite.org/) database at `%APPDATA%/Mozilla/Firefox/Profiles/*/cookies.sqlite`. No DPAPI. No AES-GCM. No app-bound encryption. Just SQL:

```python
import sqlite3, shutil, glob, os

profiles = os.path.join(os.environ["APPDATA"], "Mozilla", "Firefox", "Profiles")
db = max(glob.glob(f"{profiles}/*/cookies.sqlite"), key=os.path.getsize)

shutil.copy2(db, "tmp.sqlite")  # Copy — Firefox locks the file
conn = sqlite3.connect("tmp.sqlite")

rows = conn.execute(
    "SELECT host, name, value, path, expiry, isSecure "
    "FROM moz_cookies WHERE host LIKE '%youtube%' OR host LIKE '%google%'"
).fetchall()

print(f"✅ {len(rows)} cookies extracted")
```

**Result:** `✅ 67 cookies saved`

10 lines of Python. No admin rights. No encryption libraries. No fighting the browser.

---

## The Scoreboard

| # | Method | Blocked by | Time |
|---|--------|-----------|------|
| 1 | DPAPI + AES-GCM | Chrome 127+ app-bound encryption | 30 min |
| 2 | [rookiepy](https://github.com/thewh1teazt3c/rookie) (Rust lib) | Same encryption, even as admin | 15 min |
| 3 | Chrome DevTools Protocol | Port 9222 wouldn't bind | 40 min |
| 4 | [yt-dlp](https://github.com/yt-dlp/yt-dlp) OAuth2 | Deprecated by YouTube | 20 min |
| 5 | Per-User Bearer token | Wrong API (InnerTube ≠ Data API) | 30 min |
| **6** | **Firefox SQLite** | **Nothing** | **5 min** |

---

## Hypothesis vs Reality

| What I expected | What actually happened |
|----------------|----------------------|
| Cookie extraction is a solved problem | Chrome made it unsolvable in July 2024 |
| Admin rights bypass any protection | App-bound encryption ignores admin |
| OAuth tokens work across Google APIs | InnerTube ≠ Data API |
| yt-dlp has built-in auth | YouTube deprecated it |
| Chrome extensions export cookies safely | The most popular one was malware |
| It should take 10 minutes | It took 3 hours |

---

## Why Chrome Does This

Chrome's [app-bound encryption](https://security.googleblog.com/2024/07/improving-security-of-chrome-cookies-on.html) exists for a good reason: protecting users from cookie-stealing malware. Before Chrome 127, any program running as the same Windows user could read all Chrome cookies — login sessions, banking tokens, everything.

Google's fix: bind the decryption key to the Chrome binary. Only Chrome's own process can decrypt cookies. This blocks Raccoon, RedLine, Vidar, and all similar stealers.

**The collateral damage:** legitimate tools like yt-dlp, password managers, and cookie exporters also break.

Firefox took a different approach: cookies are plain SQLite, and security relies on **OS-level protections** — file permissions and user isolation. Neither approach is objectively better. Chrome prioritizes defense against same-user malware. Firefox prioritizes interoperability.

---

## The Deployment

After extracting cookies, deployment was straightforward:

```bash
# Extract on local machine (Windows)
python extract_cookies.py
# → cookies.txt (67 YouTube/Google cookies, Netscape format)

# Upload to server
scp cookies.txt user@server:/opt/app/backend/
```

yt-dlp uses them automatically:

```python
COOKIES_FILE = Path(__file__).parent / "cookies.txt"

cmd = ["yt-dlp", "-f", "bestvideo+bestaudio", ...]
if COOKIES_FILE.exists():
    cmd.extend(["--cookies", str(COOKIES_FILE)])
```

**Trade-off:** Cookies expire in ~2 weeks. When they do: open Firefox, visit YouTube, close Firefox, re-run the script. 60 seconds.

---

## Key Takeaways

1. **Start with Firefox.** Chrome's encryption makes external cookie extraction impossible since July 2024.

2. **Never install cookie-export extensions.** The popular "Get cookies.txt" was literal malware. Read the SQLite database directly.

3. **Check the timeline.** Any cookie extraction tutorial from before Chrome 127 (mid-2024) won't work on modern Chrome.

4. **InnerTube ≠ Data API.** If you're building around yt-dlp, Google OAuth tokens from your app won't help — yt-dlp needs browser cookies, not API tokens.

5. **Don't fight the browser.** When a browser actively resists external access, use a browser that doesn't.

---

## Where It Stands Now

| Component | Status |
|-----------|--------|
| Cookie extraction (Firefox) | ✅ Working |
| yt-dlp downloads with cookies | ✅ Working |
| Server deployment | ✅ Deployed |
| YouTube upload after merge | ✅ OAuth2 |
| Cookie auto-refresh | ❌ Manual (every ~2 weeks) |

The extraction script and the full project are open source: [**github.com/maximosovsky/merge-video**](https://github.com/maximosovsky/merge-video)

---

*This is part of a series about building [Merge Video](https://github.com/maximosovsky/merge-video) — a self-hosted video merging service. Previous: [I Tried to Merge 52 Video Files Automatically](https://dev.to/osovsky/i-tried-to-merge-52-video-files-automatically-here-are-3-bugs-that-almost-killed-the-project-oon).*

Building in public, one utility at a time. Follow the journey: [LinkedIn](https://www.linkedin.com/in/osovsky/) · [GitHub](https://github.com/maximosovsky)
