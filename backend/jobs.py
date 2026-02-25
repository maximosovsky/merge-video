"""Merge job queue — async single-worker queue for video processing."""

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from pathlib import Path


class JobStatus(str, Enum):
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    MERGING = "merging"
    UPLOADING = "uploading"
    DONE = "done"
    ERROR = "error"


@dataclass
class Job:
    job_id: str
    urls: list[str]
    user_id: str
    title: str
    job_dir: Path
    status: JobStatus = JobStatus.QUEUED
    progress: str = ""
    result_url: str = ""
    error: str = ""
    local_files: list[str] = field(default_factory=list)
    upload_to_yt: bool = True
    merge_mode: str = "compact"
    target_w: int = 0
    target_h: int = 0


class JobQueue:
    def __init__(self):
        self._queue: asyncio.Queue[Job] = asyncio.Queue()
        self._jobs: dict[str, Job] = {}
        self._worker_task: Optional[asyncio.Task] = None

    def start(self):
        """Start the background worker."""
        self._worker_task = asyncio.create_task(self._worker())

    async def add(self, job: Job):
        """Add a job to the queue."""
        self._jobs[job.job_id] = job
        await self._queue.put(job)

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    async def _worker(self):
        """Process jobs one at a time."""
        from video import download_videos, merge_videos, upload_to_youtube, cleanup_job
        from auth import (get_credentials, send_result_email,
                          send_job_started_email, send_error_email)

        while True:
            job = await self._queue.get()
            try:
                # Calculate total size for email
                total_bytes = 0
                if job.local_files:
                    for f in job.local_files:
                        try: total_bytes += Path(f).stat().st_size
                        except: pass
                total_size = f"{total_bytes / 1073741824:.1f} GB" if total_bytes > 1073741824 else f"{total_bytes / 1048576:.0f} MB"
                file_count = len(job.local_files) if job.local_files else len(job.urls)

                # Send "job started" email
                try:
                    send_job_started_email(job.user_id, job.title, file_count, total_size)
                except Exception as e:
                    print(f"📧 Job start email error: {e}")

                # Get user's access token for yt-dlp auth
                access_token = ""
                creds = get_credentials(job.user_id)
                if creds:
                    access_token = creds.token or ""

                # Get files (download or use local)
                if job.local_files:
                    files = [Path(f) for f in job.local_files]
                    job.status = JobStatus.DOWNLOADING
                    job.progress = f"Using {len(files)} local files..."
                else:
                    job.status = JobStatus.DOWNLOADING
                    job.progress = f"Downloading {len(job.urls)} videos..."
                    files = await download_videos(job.urls, job.job_dir, access_token=access_token)

                # Merge
                job.status = JobStatus.MERGING
                job.progress = f"Merging {len(files)} files..."
                merged = await merge_videos(
                    files, job.job_dir, mode=job.merge_mode,
                    target_w=job.target_w, target_h=job.target_h,
                )

                # Upload to YouTube (if requested)
                if job.upload_to_yt:
                    job.status = JobStatus.UPLOADING
                    job.progress = "Uploading to YouTube..."
                    creds = get_credentials(job.user_id)
                    if creds is None:
                        raise RuntimeError("YouTube not authorized.")
                    url = upload_to_youtube(merged, creds, job.title)
                    job.result_url = url

                    # Send success email
                    try:
                        merged_size = merged.stat().st_size
                        size_str = f"{merged_size / 1073741824:.1f} GB" if merged_size > 1073741824 else f"{merged_size / 1048576:.0f} MB"
                        res_str = f"{job.target_w or 1920}×{job.target_h or 1080}"
                        send_result_email(job.user_id, job.title, url,
                                          file_size=size_str, resolution=res_str)
                    except Exception as e:
                        print(f"📧 Result email error: {e}")
                else:
                    job.result_url = str(merged)

                job.status = JobStatus.DONE
                job.progress = "Done!"

            except Exception as e:
                import traceback
                traceback.print_exc()
                job.status = JobStatus.ERROR
                job.error = str(e) or repr(e)
                job.progress = f"Error: {e}"

                # Send error email
                try:
                    send_error_email(job.user_id, job.title, str(e))
                except Exception:
                    pass

            finally:
                if job.upload_to_yt or job.status == JobStatus.ERROR:
                    cleanup_job(job.job_dir)
                elif job.status == JobStatus.DONE:
                    # Schedule cleanup after 1 hour for download-only jobs
                    asyncio.get_event_loop().call_later(
                        3600, lambda d=job.job_dir: cleanup_job(d)
                    )
                    print(f"🗑️ Temp cleanup scheduled in 1h for {job.job_dir}")
                self._queue.task_done()


# Singleton
job_queue = JobQueue()
