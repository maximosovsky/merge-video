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
        from auth import get_credentials

        while True:
            job = await self._queue.get()
            try:
                # Download
                job.status = JobStatus.DOWNLOADING
                job.progress = f"Downloading {len(job.urls)} videos..."
                files = await download_videos(job.urls, job.job_dir)

                # Merge
                job.status = JobStatus.MERGING
                job.progress = f"Merging {len(files)} files..."
                merged = await merge_videos(files, job.job_dir)

                # Upload
                job.status = JobStatus.UPLOADING
                job.progress = "Uploading to YouTube..."
                creds = get_credentials(job.user_id)
                if creds is None:
                    raise RuntimeError("YouTube not authorized. Use /auth first.")
                url = upload_to_youtube(merged, creds, job.title)

                job.status = JobStatus.DONE
                job.result_url = url
                job.progress = "Done!"

            except Exception as e:
                job.status = JobStatus.ERROR
                job.error = str(e)
                job.progress = f"Error: {e}"

            finally:
                cleanup_job(job.job_dir)
                self._queue.task_done()


# Singleton
job_queue = JobQueue()
