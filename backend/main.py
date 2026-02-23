"""Merge-Video Backend — FastAPI server."""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from config import BASE_URL, HOST, PORT, MAX_VIDEOS
from auth import create_auth_url, exchange_code, save_credentials, get_credentials
from queue import job_queue, Job, JobStatus
from video import create_job_dir


# --- Models ---

class MergeRequest(BaseModel):
    urls: list[str]
    title: str = "Merged Video"
    user_id: str = "web"


class MergeResponse(BaseModel):
    job_id: str
    status: str
    message: str


class StatusResponse(BaseModel):
    job_id: str
    status: str
    progress: str
    result_url: str
    error: str


# --- App ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    job_queue.start()
    yield


app = FastAPI(title="Merge-Video API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Endpoints ---

@app.get("/")
async def root():
    return {"service": "merge-video", "version": "1.0.0", "docs": "/docs"}


@app.post("/merge", response_model=MergeResponse)
async def merge(req: MergeRequest):
    """Start a merge job. Requires YouTube auth first."""
    if len(req.urls) < 2:
        raise HTTPException(400, "Need at least 2 URLs to merge")
    if len(req.urls) > MAX_VIDEOS:
        raise HTTPException(400, f"Maximum {MAX_VIDEOS} videos allowed")

    creds = get_credentials(req.user_id)
    if creds is None:
        raise HTTPException(401, "YouTube not authorized. Visit /auth/youtube?user_id=... first")

    job_id, job_dir = create_job_dir()
    job = Job(
        job_id=job_id,
        urls=req.urls,
        user_id=req.user_id,
        title=req.title,
        job_dir=job_dir,
    )
    await job_queue.add(job)

    return MergeResponse(
        job_id=job_id,
        status=JobStatus.QUEUED,
        message=f"Job queued. Check status at /status/{job_id}",
    )


@app.get("/status/{job_id}", response_model=StatusResponse)
async def status(job_id: str):
    """Get the status of a merge job."""
    job = job_queue.get(job_id)
    if job is None:
        raise HTTPException(404, "Job not found")

    return StatusResponse(
        job_id=job.job_id,
        status=job.status,
        progress=job.progress,
        result_url=job.result_url,
        error=job.error,
    )


@app.get("/auth/youtube")
async def auth_youtube(user_id: str = Query(default="web")):
    """Redirect to YouTube OAuth2 consent screen."""
    url = create_auth_url(state=user_id)
    return RedirectResponse(url)


@app.get("/auth/youtube/callback")
async def auth_callback(code: str, state: str = "web"):
    """OAuth2 callback — exchange code for credentials."""
    try:
        credentials = exchange_code(code)
        save_credentials(state, credentials)
        return {"status": "ok", "message": "YouTube authorized!", "user_id": state}
    except Exception as e:
        raise HTTPException(400, f"Auth failed: {e}")


@app.get("/auth/status")
async def auth_status(user_id: str = Query(default="web")):
    """Check if user has valid YouTube credentials."""
    creds = get_credentials(user_id)
    return {"authorized": creds is not None, "user_id": user_id}


# Serve static site files
from fastapi.staticfiles import StaticFiles
from pathlib import Path

site_dir = Path(__file__).parent.parent / "site"
if site_dir.exists():
    from fastapi.responses import FileResponse

    @app.get("/site/{path:path}")
    async def serve_site(path: str):
        file = site_dir / path
        if file.is_file():
            return FileResponse(file)
        return FileResponse(site_dir / "index.html")

    # Serve index.html at root /app
    @app.get("/app")
    async def serve_app():
        return FileResponse(site_dir / "index.html")

    app.mount("/css", StaticFiles(directory=str(site_dir / "css")), name="css")
    app.mount("/js", StaticFiles(directory=str(site_dir / "js")), name="js")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=HOST, port=PORT, reload=True)
