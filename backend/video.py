"""Video processing: download, merge, upload to YouTube."""

import subprocess
import uuid
import shutil
from pathlib import Path

from config import TEMP_DIR, MAX_VIDEO_DURATION_SEC


async def expand_urls(urls: list[str]) -> list[str]:
    """Expand playlist URLs into individual video URLs using yt-dlp.
    Regular video URLs pass through unchanged."""
    expanded = []
    for url in urls:
        url = url.strip()
        if not url:
            continue
        # Detect playlist URLs
        if "list=" in url or "/playlist" in url:
            cmd = [
                "yt-dlp", "--flat-playlist",
                "--print", "url",
                "--no-warnings",
            ]
            cmd.extend(["--username", "oauth2", "--password", ""])
            cmd.append(url)
            proc = await _run(cmd)
            if proc.returncode == 0 and proc.stdout.strip():
                playlist_urls = [u.strip() for u in proc.stdout.strip().split("\n") if u.strip()]
                expanded.extend(playlist_urls)
            else:
                # Fallback: treat as single video
                expanded.append(url)
        else:
            expanded.append(url)
    return expanded


async def download_videos(urls: list[str], job_dir: Path) -> list[Path]:
    """Download YouTube videos using yt-dlp. Returns list of file paths."""
    files = []
    for i, url in enumerate(urls):
        output_path = job_dir / f"{i:03d}.mp4"
        cmd = [
            "yt-dlp",
            "-f", "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best",
            "--merge-output-format", "mp4",
            "--max-filesize", "500M",
            "--socket-timeout", "30",
            "-o", str(output_path),
        ]
        cmd.extend(["--username", "oauth2", "--password", ""])
        cmd.append(url)
        proc = await _run(cmd)
        if proc.returncode != 0:
            raise RuntimeError(f"yt-dlp failed for {url}: {proc.stderr}")
        # yt-dlp may add suffix, find the actual file
        actual = _find_downloaded(job_dir, f"{i:03d}")
        files.append(actual)
    return files


def _probe_has_audio(filepath: Path) -> bool:
    """Check if a video file has an audio stream using ffprobe."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-select_streams", "a",
             "-show_entries", "stream=codec_type", "-of", "csv=p=0",
             str(filepath)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        return bool(result.stdout.strip())
    except Exception:
        return True  # assume audio exists if probe fails


async def merge_videos(files: list[Path], job_dir: Path, mode: str = "compact",
                       target_w: int = 0, target_h: int = 0) -> Path:
    """Merge video files using ffmpeg. Returns merged file path.
    mode='compact'     — CRF 23, smaller file size
    mode='highquality' — CRF 18, close to original quality
    mode='lossless'    — concat demuxer, no re-encoding (1:1 quality)
    target_w/target_h  — output resolution (0 = auto 1920x1080)
    """
    if len(files) == 1:
        return files[0]

    output = job_dir / "merged.mp4"

    # Determine target resolution
    w = target_w if target_w > 0 else 1920
    h = target_h if target_h > 0 else 1080
    print(f"🎬 Merging {len(files)} files → {w}×{h} ({mode})")

    if mode == "lossless":
        # Concat demuxer: no re-encoding, fast, preserves quality
        list_file = job_dir / "filelist.txt"
        with open(list_file, "w", encoding="utf-8") as f:
            for p in files:
                f.write(f"file '{p.resolve()}'\n")
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(list_file),
            "-c", "copy",
            "-movflags", "+faststart",
            str(output),
        ]
    else:
        # Two-pass: 1) normalize each file, 2) concat demuxer
        crf = "18" if mode == "highquality" else "23"
        norm_dir = job_dir / "normalized"
        norm_dir.mkdir(exist_ok=True)
        normalized_files = []

        for i, f in enumerate(files):
            norm_out = norm_dir / f"part_{i:04d}.mp4"
            has_audio = _probe_has_audio(f)

            # Build filter: scale video
            vf = (
                f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
                f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black,setsar=1,format=yuv420p"
            )

            cmd = ["ffmpeg", "-y", "-i", str(f)]

            if not has_audio:
                # Add silent audio source
                cmd.extend(["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"])

            cmd.extend([
                "-vf", vf,
                "-c:v", "libx264", "-preset", "fast", "-crf", crf,
            ])

            if not has_audio:
                cmd.extend(["-map", "0:v:0", "-map", "1:a:0", "-shortest"])

            cmd.extend([
                "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
                "-movflags", "+faststart",
                str(norm_out),
            ])

            print(f"  📦 Normalizing {i+1}/{len(files)}: {f.name}")
            proc = await _run(cmd)
            if proc.returncode != 0:
                raise RuntimeError(f"ffmpeg normalize failed for {f.name}: {proc.stderr[-500:]}")
            normalized_files.append(norm_out)

        # Pass 2: concat demuxer (no re-encoding, all files already normalized)
        list_file = job_dir / "filelist.txt"
        with open(list_file, "w", encoding="utf-8") as lf:
            for nf in normalized_files:
                lf.write(f"file '{nf.resolve()}'\n")

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(list_file),
            "-c", "copy",
            "-movflags", "+faststart",
            str(output),
        ]

    proc = await _run(cmd)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg merge failed: {proc.stderr}")
    return output


def upload_to_youtube(filepath: Path, credentials, title: str, description: str = "") -> str:
    """Upload video to YouTube using authenticated credentials. Returns video URL."""
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    youtube = build("youtube", "v3", credentials=credentials)

    body = {
        "snippet": {
            "title": title,
            "description": description or "Merged with merge-video.osovsky.com",
            "categoryId": "22",  # People & Blogs
        },
        "status": {
            "privacyStatus": "unlisted",
        },
    }

    media = MediaFileUpload(str(filepath), mimetype="video/mp4", resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        _, response = request.next_chunk()

    video_id = response["id"]
    return f"https://www.youtube.com/watch?v={video_id}"


def create_job_dir() -> tuple[str, Path]:
    """Create a unique temp directory for a merge job."""
    job_id = uuid.uuid4().hex[:12]
    job_dir = TEMP_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    return job_id, job_dir


def cleanup_job(job_dir: Path):
    """Remove temp directory after job is done."""
    if job_dir.exists():
        shutil.rmtree(job_dir, ignore_errors=True)


def _find_downloaded(job_dir: Path, prefix: str) -> Path:
    """Find the actual downloaded file (yt-dlp may change extension)."""
    for f in job_dir.iterdir():
        if f.stem.startswith(prefix) and f.is_file():
            return f
    raise FileNotFoundError(f"No file with prefix {prefix} in {job_dir}")


async def _run(cmd: list[str], cwd: str | None = None) -> subprocess.CompletedProcess:
    """Run a subprocess asynchronously (Windows-compatible).
    Redirects stdout/stderr to temp files to avoid MemoryError on large outputs.
    """
    import asyncio
    import tempfile

    def _sync_run():
        with tempfile.TemporaryFile(mode='w+', encoding='utf-8', errors='replace') as out_f, \
             tempfile.TemporaryFile(mode='w+', encoding='utf-8', errors='replace') as err_f:
            result = subprocess.run(cmd, stdout=out_f, stderr=err_f, cwd=cwd)
            # Read only last 4KB of stderr for error messages
            err_f.seek(0, 2)  # seek to end
            size = err_f.tell()
            err_f.seek(max(0, size - 4096))
            stderr_tail = err_f.read()
            return subprocess.CompletedProcess(cmd, result.returncode, stdout="", stderr=stderr_tail)

    return await asyncio.to_thread(_sync_run)
