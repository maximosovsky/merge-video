"""Video processing: download, merge, upload to YouTube."""

import subprocess
import uuid
import shutil
from pathlib import Path

from config import TEMP_DIR, MAX_VIDEO_DURATION_SEC


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
            url,
        ]
        proc = await _run(cmd)
        if proc.returncode != 0:
            raise RuntimeError(f"yt-dlp failed for {url}: {proc.stderr}")
        # yt-dlp may add suffix, find the actual file
        actual = _find_downloaded(job_dir, f"{i:03d}")
        files.append(actual)
    return files


async def merge_videos(files: list[Path], job_dir: Path) -> Path:
    """Merge video files using ffmpeg concat filter. Returns merged file path."""
    if len(files) == 1:
        return files[0]

    output = job_dir / "merged.mp4"

    # Build ffmpeg concat filter
    inputs = []
    filter_parts = []
    for i, f in enumerate(files):
        inputs.extend(["-i", str(f)])
        filter_parts.append(f"[{i}:v:0][{i}:a:0]")

    filter_str = "".join(filter_parts) + f"concat=n={len(files)}:v=1:a=1[outv][outa]"

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_str,
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "192k",
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


async def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    """Run a subprocess asynchronously."""
    import asyncio
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    return subprocess.CompletedProcess(
        cmd, proc.returncode,
        stdout=stdout.decode(errors="replace"),
        stderr=stderr.decode(errors="replace"),
    )
