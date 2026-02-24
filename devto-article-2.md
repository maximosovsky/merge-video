---
title: 3 Deployment Fails That Made Me Quit Oracle Cloud Forever
published: true
description: I tried to deploy a Telegram bot to Oracle Cloud Free Tier. After 2 hours of UI bugs, capacity errors, and a card-locked account — I switched to Fly.io and hit a new wall.
tags: devops, deployment, buildinpublic, python
cover_image: https://raw.githubusercontent.com/maximosovsky/merge-video/master/assets/merge-video-2.jpg
---

*This is Part 2. [Part 1](https://dev.to/osovsky/i-tried-to-merge-52-video-files-automatically-here-are-3-bugs-that-almost-killed-the-project) covered 3 bugs I hit while building the video merging engine. This one is about what happened when I tried to put it online.*

---

## The Plan That Looked Too Good

In [Part 1](https://dev.to/osovsky/i-tried-to-merge-52-video-files-automatically-here-are-3-bugs-that-almost-killed-the-project) I built [Merge Video](https://github.com/maximosovsky/merge-video) — a service that merges dozens of video files using [ffmpeg](https://ffmpeg.org/) and uploads the result to YouTube. I film long strategy sessions — 6 to 8 hours each — and end up with 30–50 clips per session that need to be merged into one video. It worked on my machine. Now I needed to deploy the [Telegram bot](https://core.telegram.org/bots/api) so it runs 24/7 without my laptop being open.

![Maxim Osovsky during a strategy session](https://raw.githubusercontent.com/maximosovsky/merge-video/master/assets/maxim-osovsky-strategy-session.JPG)

Two requirements:
1. **Free** — I'm not paying a monthly bill for a side project that has zero users
2. **Persistent** — a long-polling bot needs to stay alive, not sleep after 15 minutes of inactivity like [Render](https://render.com/)'s free tier

[Oracle Cloud Free Tier](https://www.oracle.com/cloud/free/) looked perfect on paper: **4 ARM CPUs, 24 GB RAM, 200 GB disk** — free forever. Not a trial. Not 12 months. *Forever.*

I signed up, picked a datacenter, and started creating a VM.

What followed was the most frustrating 2 hours I've had with any cloud provider.

---

## Fail #1: The Server That Doesn't Exist

I selected the best free shape — **VM.Standard.A1.Flex** (ARM, 4 CPUs, 24 GB RAM). Configured everything. Hit Create.

```
API Error:
Out of capacity for shape VM.Standard.A1.Flex in availability domain AD-1.
Create the instance in a different availability domain or try again later.
```

No ARM instances available. The datacenter was fully packed. All of them. Taken.

Fine — fallback plan. I switched to the weaker x86 shape: **VM.Standard.E2.1.Micro** (1 CPU, 1 GB RAM). Not great for video processing, but enough for a Telegram bot.

Same error:

```
Out of capacity for shape VM.Standard.E2.1.Micro in availability domain AD-1.
```

**Both free shapes — zero availability.** The "Always Free" tier had no servers to give me. The marketing page promises 24 GB of RAM. The reality is a queue with no ETA.

Online advice says: *"Try early morning (5–7 UTC), capacity comes in waves."* Some people write scripts that poll the Oracle API every 5 minutes, for **days**, waiting for a slot to open.

I didn't want to write a bot to get a server to run my bot.

---

## Fail #2: The Checkbox That Won't Check

Before the capacity error killed my attempt entirely, I spent **40 minutes** fighting Oracle's VM creation UI.

The problem: the **"Automatically assign public IPv4 address"** checkbox was grayed out. Without a public IP, the server is invisible to the internet — no SSH access, no Telegram connection, nothing.

I stared at it. Refreshed the page. Tried a different browser. The checkbox wouldn't budge.

The root cause? When you create a new subnet *inline* during VM creation, Oracle's UI doesn't recognize it as "public" — even though you explicitly selected **"Create new public subnet."** The UI disagrees with itself.

### The workaround I had to discover myself

1. Cancel VM creation entirely
2. Navigate to **Networking → Virtual Cloud Networks → Start VCN Wizard**
3. Run the wizard to create a VCN with internet connectivity
4. Go *back* to Compute → Create Instance
5. Select the existing VCN → existing public subnet
6. *Now* the checkbox works

Three separate pages. A wizard inside a wizard. To enable a checkbox that should have worked from the start.

I spent 40 minutes on this *before* discovering I couldn't get a server anyway.

---

## Fail #3: One Card, One Life

After getting the capacity error on *both* shapes, I thought: what if the problem is this specific datacenter? Some regions have more available servers than others.

I couldn't change regions on my existing account — Oracle locks your home region at signup. So I went all in: registered a **second account** with a different Gmail address (not even an alias — Oracle didn't accept `+` aliases). Used a Regus coworking address in Tilburg, Netherlands as my billing address. Used my second phone number for verification.

Different email. Different address. Different phone. Made it through the entire signup flow. Got to the payment verification step. Entered my card.

```
Error: You already have an account with a different email address.
Oracle allows one promotion per person.
```

This was the moment I was done.

Oracle links your identity to your **card number**. One card = one account = one datacenter = zero servers. Different email doesn't matter. Different address doesn't matter. Different phone doesn't matter. You get one shot, and if your datacenter is full — tough luck.

No retry. No workaround. No path forward.

### The scorecard after 2 hours with Oracle Cloud

| What I tried | Result |
|-------------|--------|
| ARM shape (A1.Flex, 4 CPU, 24 GB) | ❌ Out of capacity |
| x86 shape (E2.1.Micro, 1 CPU, 1 GB) | ❌ Out of capacity |
| Public IPv4 checkbox | ❌ Grayed out (UI bug) |
| Manual VCN + public subnet | ✅ Fixed the checkbox |
| VM creation after VCN fix | ❌ Still out of capacity |
| Second account (new email, new address, new phone) | ❌ Blocked by card |
| **Total time** | **2 hours** |
| **Total servers** | **0** |
| **Total RAM obtained** | **0 bytes** |

---

## The Pivot: Fly.io in 10 Minutes

I closed Oracle's console and opened [Fly.io](https://fly.io/).

No VMs. No VCN wizards. No availability domains. Just a `Dockerfile` and a CLI.

```bash
fly auth login
fly launch --no-deploy
fly secrets set BOT_TOKEN="..."
fly deploy
```

**10 minutes.** DNS verified. App live at `merge-video-bot.fly.dev`. [aiogram](https://docs.aiogram.dev/) connected to [Telegram Bot API](https://core.telegram.org/bots/api). Bot started polling.

| | Oracle Cloud | Fly.io |
|---|---|---|
| **Time to deploy** | 2 hours | 10 minutes |
| **Result** | 0 servers | 1 running bot |
| **UI complexity** | 6 pages, 2 wizards | 4 CLI commands |
| **Account tricks needed** | Second email, Regus address, second phone | GitHub login |

Everything worked.

And it's been running stable since.

---

## What I Learned

| What I expected | What actually happened |
|----------------|----------------------|
| Oracle Free Tier = free server | Free tier with **zero available servers** |
| "Always Free" means always available | Means always free *if you can get one* |
| Oracle Cloud UI is enterprise-grade | 3-page workaround for a single checkbox |
| Different email + address + phone = new account | One **card** = one account, forever |
| Deploy takes 30 minutes | Oracle: 2 hours → nothing. Fly.io: 10 minutes → working |

---

## Where It Stands Now

| Component | Status |
|-----------|--------|
| Web app — merge & download | ✅ Working |
| Telegram bot | ✅ Deployed on [Fly.io](https://fly.io/) (256 MB, stable) |
| Email notifications | ✅ [Gmail API](https://developers.google.com/gmail/api) |
| YouTube upload | ✅ OAuth2 |
| Stress test (52 files, 13 GB) | ✅ Passed |
| Large file upload via HTTP | ❌ Hangs on 13 GB |
| Backend deployment | ❌ Still localhost |
| YouTube auth via bot | ❌ Needs deployed backend |

---

## Try It

The project is open source: [**github.com/maximosovsky/merge-video**](https://github.com/maximosovsky/merge-video)

Or send YouTube links to the Telegram bot: [@MergeVideoBot](https://t.me/MergeVideoBot)

---

This is part 2. Part 1 covered [3 bugs in the video merging engine](https://dev.to/osovsky/i-tried-to-merge-52-video-files-automatically-here-are-3-bugs-that-almost-killed-the-project). Next: deploying the backend and connecting YouTube auth through the bot.

*Ever been burned by a "free" cloud? Drop your horror story in the comments.*

Building in public, one utility at a time. Follow the journey: [LinkedIn](https://www.linkedin.com/in/osovsky/) · [GitHub](https://github.com/maximosovsky)
