---
title: 7 Failed Attempts to Create One Cloud Server on Alibaba Cloud
published: false
description: I needed a VPS for my video merging backend. Alibaba Cloud made me try 7 different instance/zone/disk combinations before one finally worked.
tags: devops, deployment, buildinpublic, cloud
cover_image: https://raw.githubusercontent.com/maximosovsky/merge-video/master/assets/merge-video-3.jpg
---

*This is Part 3. [Part 1](https://dev.to/osovsky/i-tried-to-merge-52-video-files-automatically-here-are-3-bugs-that-almost-killed-the-project) covered 3 bugs in the video merging engine. [Part 2](https://dev.to/osovsky/3-deployment-fails-that-made-me-quit-oracle-cloud-forever-13gk) was about Oracle Cloud's "Always Free" servers that don't exist. This one is about what happened when I tried Alibaba Cloud instead.*

---

## Why Alibaba Cloud?

I run long strategy sessions — 6 to 8 hours each — where we plan product roadmaps, discuss architecture, and make decisions on camera. Each session produces 30 to 50 short video clips that need to be merged into one continuous video.

![Maxim Osovsky during a strategy session](https://raw.githubusercontent.com/maximosovsky/merge-video/master/assets/osovsky-strategy.jpg)

I offered **$2,000** to a developer to build a service that merges videos and uploads them to YouTube. They turned it down — didn't see the problem it solved. Multiple developers refused. So I built [Merge Video](https://github.com/maximosovsky/merge-video) myself — with AI as my pair programmer, in 3 days, for $0 in development costs. The code works. Now I needed to put it on a server.

In [Part 2](https://dev.to/osovsky/3-deployment-fails-that-made-me-quit-oracle-cloud-forever-13gk) I deployed the [Telegram bot](https://t.me/MergeVideoBot) to [Fly.io](https://fly.io/) — 256 MB RAM, just enough for polling. But the backend needs [ffmpeg](https://ffmpeg.org/), [yt-dlp](https://github.com/yt-dlp/yt-dlp), and enough RAM to merge 50+ video files. It needs a real VPS.

Oracle Cloud? [Dead to me](https://dev.to/osovsky/3-deployment-fails-that-made-me-quit-oracle-cloud-forever-13gk). AWS/GCP? No free tier for what I need. Hetzner? Great, but I already had Alibaba Cloud API keys — left over from [WallPlan](https://osovsky.com/wallplan), my calendar generator that I once deployed to Alibaba Cloud OSS through [DeployBridge](https://maximosovsky.github.io/deploy-bridge/). Those keys were still active. An ECS instance with 2 vCPU and a few GB of RAM — how hard could it be?

Seven attempts hard.

### No Console. Only Terminal.

One important detail: **I never opened the Alibaba Cloud web console.** Not once. The entire process — VPC creation, Security Groups, image search, instance provisioning, IP allocation — was done through the [Alibaba Cloud ECS SDK](https://www.npmjs.com/package/@alicloud/ecs20140526) via Node.js scripts running in my terminal.

Why? Because I script my deployments. The same API keys from the [WallPlan](https://github.com/maximosovsky/wallplan) project that went through [DeployBridge](https://github.com/maximosovsky/deploy-bridge) — a deployment tool I built for moving sites from Vercel to cheaper hosting — were reused here with zero additional setup.

---

## Attempt #1: Frankfurt, Wrong Image

I picked Frankfurt (`eu-central-1`) — closest to me. Wrote a Node.js script using the [Alibaba Cloud ECS SDK](https://www.npmjs.com/package/@alicloud/ecs20140526) to automate everything: VPC, VSwitch, Security Group, instance.

The VPC and VSwitch created fine. The Security Group created fine. Then:

```
Finding Ubuntu 22.04 image...
Image: ubuntu_22_04_arm64_20G_alibase_20260119.vhd
```

Wait — **arm64**? I asked for `ecs.c6.large`, which is x86. The SDK returned the ARM image first.

```
Error: InvalidInstanceType.NotSupported
The specified instanceType is not supported by the image architecture.
```

**Lesson: Alibaba's image search doesn't filter by architecture unless you explicitly ask.**

---

## Attempt #2: Frankfurt, No Ubuntu at All

I added `architecture: 'x86_64'` to the image search. The result?

```
Error: No Ubuntu image found
```

Frankfurt has **zero** x86 Ubuntu images. Only ARM. The entire region. I listed all available images:

```
debian_12_13_x64_20G_alibase_20260120.vhd: Debian 12.13 64位
centos_stream_9_x64_20G_alibase_20260120.vhd: CentOS Stream 9
aliyun_4_x64_20G_alibase_20260120.vhd: Alibaba Cloud Linux 4
```

No Ubuntu. Fine — Debian 12 is basically Ubuntu without Canonical. I switched to Debian.

---

## Attempt #3: Frankfurt, Zone Not for Sale

```
3. Creating ECS (ecs.c6.large, 2vCPU, 4GB)...
Error: Zone.NotOnSale
The specified zone is not available for purchase.
```

**The entire Frankfurt zone doesn't sell `ecs.c6.large`.** Not out of stock — not *available for purchase*. The instance type doesn't exist there for PayAsYouGo.

That's when I abandoned Frankfurt entirely and switched to Singapore (`ap-southeast-1`).

---

## Attempt #4: Singapore, Wrong Disk

Singapore accepted my VPC, VSwitch, Security Group. Found Debian 12. Instance type available. Progress!

```
3. Creating ECS (ecs.c6.large, 2 vCPU, 4 GB)...
Error: InvalidDiskCategory.NotSupported
The specified disk category is not supported.
```

`cloud_efficiency` — not supported. Changed to `cloud_essd`. Still not supported. Changed to `cloud_ssd`. Still not supported.

**Three disk types. All rejected. For the same instance type.**

---

## Attempt #5: Singapore, Instance Doesn't Exist

I queried `DescribeAvailableResource` (should have done this from the start). The shocking result:

```
ecs.c6.large — not found in any Singapore zone
```

`ecs.c6.large` **doesn't exist in Singapore.** Not out of stock — the instance type isn't offered. Only `ecs.c6t` (trusted) and `ecs.c6r` (ARM) variants.

---

## Attempt #6: Singapore, ARM Again

I tried `ecs.c6r.large` — thinking "r" meant "regular."

```
Error: InvalidInstanceType.NotSupported
The specified instanceType is not supported by the image architecture.
```

"r" means **ARM**. My Debian image was x86. Architecture mismatch. Again.

---

## Attempt #7: Singapore, KMS Required

I switched to `ecs.c6t.large` — "t" for "trusted." Should work with x86, right?

```
Error: InvalidParameter.KmsNotEnabled
Failed to perform this operation because KMS is not activated.
```

Trusted instances require [KMS](https://www.alibabacloud.com/product/key-management-service) (Key Management Service) — a separate service that needs activation. I just wanted a Linux box.

### The scorecard after 7 attempts

| # | Region | Instance | Image | Disk | Error |
|---|--------|----------|-------|------|-------|
| 1 | Frankfurt | ecs.c6.large | Ubuntu ARM | — | Wrong architecture |
| 2 | Frankfurt | ecs.c6.large | — | — | No Ubuntu x86 exists |
| 3 | Frankfurt | ecs.c6.large | Debian x86 | cloud_efficiency | Zone not for sale |
| 4 | Singapore | ecs.c6.large | Debian x86 | cloud_* | Disk not supported |
| 5 | Singapore | ecs.c6.large | — | — | Instance type doesn't exist |
| 6 | Singapore | ecs.c6r.large | Debian x86 | — | ARM instance, x86 image |
| 7 | Singapore | ecs.c6t.large | Debian x86 | cloud_essd | KMS not activated |

**7 API calls. 7 different errors. 0 servers.**

---

## The Fix: Query First, Create Second

I finally wrote what I should have written from the start — a **probe script** that checks everything before creating anything:

```javascript
// 1. Find instance types with stock
const res = await ecs.describeAvailableResource({
  regionId: 'ap-southeast-1',
  destinationResource: 'SystemDisk',
  instanceChargeType: 'PostPaid',
  instanceType: type,
});

// 2. Find zones with stock
// 3. Find compatible disk categories
// 4. Find matching VSwitch or create one
// 5. THEN create the instance
```

The script tested 4 candidate instance types across all zones. In seconds, it found what worked:

```
FOUND: ecs.t6-c1m4.large in ap-southeast-1c with cloud_efficiency
```

`ecs.t6-c1m4.large` — a burstable type I'd never heard of. Zone C — not the default zone the SDK picked. `cloud_efficiency` — the same disk type that was *rejected* for `ecs.c6.large` two attempts earlier.

**One probe. One working combination. Instance created in 30 seconds.**

```
Instance: i-xxxxxxxxxxxxxxxxxxxx
IP:       203.0.113.42
SSH:      ssh root@203.0.113.42
```

---

## Deploying the Backend

With the server finally alive, I piped a setup script via SSH. The script creates a dedicated `deploy` user — the backend runs under that account, not root:

```powershell
# Convert CRLF → LF (Windows → Linux)
$content = [IO.File]::ReadAllText("deploy/remote-setup.sh")
$lfContent = $content -replace "`r`n", "`n"
[IO.File]::WriteAllText($temp, $lfContent)
Get-Content $temp -Raw | ssh root@203.0.113.42 "bash -s"
```

The script installed everything in 3 minutes:

```bash
apt install -y python3 python3-venv ffmpeg nginx git
python3 -m venv /opt/merge-video/venv
pip install -r backend/requirements.txt
systemctl enable merge-video
systemctl start merge-video
```

```
● merge-video.service - Merge Video Backend (FastAPI)
     Active: active (running)
     Memory: 106.1M
```

106 MB. Running. After 7 failed attempts and one working probe.

---

## What I Learned

| What I assumed | What's actually true |
|---------------|---------------------|
| `ecs.c6.large` exists everywhere | It exists in *some* regions, *some* zones |
| Ubuntu is always available | Frankfurt has **zero** x86 Ubuntu images |
| Disk types are universal | Each instance type supports different disks |
| "c6r" means regular | It means ARM |
| "c6t" means standard | It means trusted (requires KMS) |
| You can guess and retry | You **must** query `DescribeAvailableResource` first |

### The real takeaway

**Alibaba Cloud's API is a compatibility matrix, not a catalog.**

Unlike AWS where `t3.micro` works everywhere with any disk, Alibaba Cloud has **per-zone, per-type, per-disk** compatibility rules that aren't surfaced in the console or documentation. The only way to know what works is to call `DescribeAvailableResource` and cross-reference instance types, zones, disk categories, and image architectures.

One API call would have saved me 7 failed attempts.

---

## Where It Stands Now

| Component | Status |
|-----------|--------|
| Web app — merge & download | ✅ Working |
| Telegram bot | ✅ [Fly.io](https://fly.io/) (256 MB, stable) |
| Backend (FastAPI + ffmpeg) | ✅ Alibaba ECS Singapore (2 vCPU, 8 GB RAM) |
| Email notifications | ✅ [Gmail API](https://developers.google.com/gmail/api) |
| YouTube upload | ✅ OAuth2 |
| SSL + domain | ⏳ Next: `merge-video.osovsky.com` |
| YouTube auth via bot | ⏳ After backend goes public |

---

## Try It

The project is open source: [**github.com/maximosovsky/merge-video**](https://github.com/maximosovsky/merge-video)

Or send YouTube links to the Telegram bot: [@MergeVideoBot](https://t.me/MergeVideoBot)

---

This is Part 3. [Part 1](https://dev.to/osovsky/i-tried-to-merge-52-video-files-automatically-here-are-3-bugs-that-almost-killed-the-project) covered 3 bugs in the video merging engine. [Part 2](https://dev.to/osovsky/3-deployment-fails-that-made-me-quit-oracle-cloud-forever-13gk) was about Oracle Cloud. Next: connecting DNS, SSL, and YouTube auth through the bot.

*Ever had a cloud provider reject 7 different configurations in a row? I'd love to hear your worst. Comments are open.*

Building in public, one utility at a time. Follow the journey: [LinkedIn](https://www.linkedin.com/in/osovsky/) · [GitHub](https://github.com/maximosovsky)
