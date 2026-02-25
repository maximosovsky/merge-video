"""Merge-Video Backend — FastAPI server."""

import asyncio
import sys
from contextlib import asynccontextmanager

# Fix Windows asyncio subprocess support
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI, HTTPException, Query, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from config import BASE_URL, HOST, PORT, MAX_VIDEOS
from auth import create_auth_url, exchange_code, save_credentials, get_credentials, get_user_info, remove_credentials, send_auth_email, send_job_received_email
from jobs import job_queue, Job, JobStatus
from video import create_job_dir, expand_urls


# --- Models ---

class MergeRequest(BaseModel):
    urls: list[str]
    title: str = "Merged Video"
    user_id: str = "web"
    merge_mode: str = "compact"


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
    return RedirectResponse("/app")


@app.post("/merge", response_model=MergeResponse)
async def merge(req: MergeRequest):
    """Start a merge job. Supports both individual URLs and playlist URLs."""
    import traceback
    try:
        creds = get_credentials(req.user_id)
        if creds is None:
            raise HTTPException(401, "YouTube not authorized. Visit /auth/youtube?user_id=... first")

        # Expand playlist URLs into individual video URLs
        expanded = await expand_urls(req.urls, access_token=creds.token or "")

        if len(expanded) < 2:
            raise HTTPException(400, "Need at least 2 videos to merge (playlist may contain only 1)")
        if len(expanded) > MAX_VIDEOS:
            raise HTTPException(400, f"Too many videos ({len(expanded)}). Maximum {MAX_VIDEOS} allowed")

        job_id, job_dir = create_job_dir()
        job = Job(
            job_id=job_id,
            urls=expanded,
            user_id=req.user_id,
            title=req.title,
            job_dir=job_dir,
            merge_mode=req.merge_mode,
        )
        await job_queue.add(job)

        return MergeResponse(
            job_id=job_id,
            status=JobStatus.QUEUED,
            message=f"Job queued ({len(expanded)} videos). Check status at /status/{job_id}",
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, f"Internal error: {str(e)}")


@app.post("/merge/upload")
async def merge_upload(
    files: list[UploadFile] = File(...),
    title: str = Form(default="Merged Video"),
    user_id: str = Form(default="web"),
    upload_to_yt: bool = Form(default=False),
    merge_mode: str = Form(default="compact"),
    target_w: int = Form(default=0),
    target_h: int = Form(default=0),
):
    """Merge uploaded local video files."""
    import traceback
    import shutil
    try:
        if len(files) < 2:
            raise HTTPException(400, "Need at least 2 files to merge")
        if len(files) > MAX_VIDEOS:
            raise HTTPException(400, f"Maximum {MAX_VIDEOS} files allowed")

        creds = None
        if upload_to_yt:
            creds = get_credentials(user_id)
            if creds is None:
                raise HTTPException(401, "YouTube not authorized")

        job_id, job_dir = create_job_dir()

        # Send "received" email before saving
        total_size_bytes = sum(f.size or 0 for f in files)
        size_str = f"{total_size_bytes / 1073741824:.1f} GB" if total_size_bytes > 1073741824 else f"{total_size_bytes / 1048576:.0f} MB"
        try:
            send_job_received_email(user_id, title, len(files), size_str)
        except Exception as e:
            print(f"📧 Received email error: {e}")

        # Save uploaded files
        print(f"📤 Saving {len(files)} files to {job_dir}...")
        saved_files = []
        for i, f in enumerate(files):
            ext = f.filename.rsplit('.', 1)[-1] if '.' in f.filename else 'mp4'
            path = job_dir / f"{i:03d}.{ext}"
            with open(path, 'wb') as out:
                shutil.copyfileobj(f.file, out)
            saved_files.append(str(path))
            fsize = path.stat().st_size
            fsize_str = f"{fsize / 1048576:.1f} MB" if fsize < 1073741824 else f"{fsize / 1073741824:.1f} GB"
            print(f"  📤 {i+1}/{len(files)}: {f.filename} ({fsize_str})")
        print(f"✅ All {len(files)} files saved")

        job = Job(
            job_id=job_id,
            urls=[],
            user_id=user_id,
            title=title,
            job_dir=job_dir,
            local_files=saved_files,
            upload_to_yt=upload_to_yt,
            merge_mode=merge_mode,
            target_w=target_w,
            target_h=target_h,
        )
        await job_queue.add(job)

        return MergeResponse(
            job_id=job_id,
            status=JobStatus.QUEUED,
            message=f"Job queued ({len(files)} files). Check status at /status/{job_id}",
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, f"Internal error: {str(e)}")


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


@app.get("/download/{job_id}")
async def download_merged(job_id: str):
    """Download the merged video file."""
    from fastapi.responses import FileResponse
    job = job_queue.get(job_id)
    if job is None:
        raise HTTPException(404, "Job not found")
    if job.status != JobStatus.DONE:
        raise HTTPException(400, "Job not ready yet")
    merged_path = Path(job.result_url)
    if not merged_path.exists():
        raise HTTPException(404, "File not found (may have been cleaned up)")
    return FileResponse(str(merged_path), filename=f"{job.title}.mp4", media_type="video/mp4")


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
        try:
            send_auth_email(state)
        except Exception as e:
            print(f"📧 Auth email error: {e}")

        # Telegram users: show "return to Telegram" page
        if state.startswith("tg_"):
            from fastapi.responses import HTMLResponse
            profile = get_user_info(state) or {}
            name = profile.get("name", "")
            return HTMLResponse(f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Authorized — Merge Video</title>
<style>
  body {{ font-family: 'Segoe UI', Arial, sans-serif; display: flex; align-items: center;
    justify-content: center; min-height: 100vh; margin: 0; background: #f5f5ff; }}
  .card {{ text-align: center; background: #fff; border-radius: 20px; padding: 40px;
    box-shadow: 0 8px 40px rgba(99,102,241,0.12); max-width: 400px; }}
  h1 {{ font-size: 22px; color: #33334f; margin-bottom: 8px; }}
  p {{ color: #666; font-size: 15px; }}
  .btn {{ display: inline-block; margin-top: 20px; padding: 14px 32px;
    background: linear-gradient(135deg, #7c3aed, #6366f1); color: #fff; text-decoration: none;
    border-radius: 12px; font-weight: 700; font-size: 16px; transition: all 0.3s;
    box-shadow: 0 4px 15px rgba(99,102,241,0.3); }}
  .btn:hover {{ transform: translateY(-1px); box-shadow: 0 6px 20px rgba(99,102,241,0.45); }}
</style></head><body>
<div class="card">
  <h1>✅ Authorized!</h1>
  <p>{"Hi " + name + "! " if name else ""}Your YouTube is connected.</p>
  <p>You can close this page and return to Telegram.</p>
  <a class="btn" href="https://t.me/MergeVideo_bot">← Back to Telegram</a>
</div></body></html>""")

        return RedirectResponse("/app?authorized=true")
    except Exception as e:
        raise HTTPException(400, f"Auth failed: {e}")


@app.get("/auth/status")
async def auth_status(user_id: str = Query(default="web")):
    """Check if user has valid YouTube credentials."""
    creds = get_credentials(user_id)
    profile = get_user_info(user_id) or {}
    return {
        "authorized": creds is not None,
        "user_id": user_id,
        "picture": profile.get("picture", ""),
        "email": profile.get("email", ""),
        "name": profile.get("name", ""),
    }


@app.post("/auth/logout")
async def auth_logout(user_id: str = Query(default="web")):
    """Remove stored credentials for a user."""
    remove_credentials(user_id)
    return {"status": "ok", "message": "Logged out"}


# Serve static site files
from fastapi.staticfiles import StaticFiles
from pathlib import Path

site_dir = Path(__file__).parent.parent / "site"
if site_dir.exists():
    from fastapi.responses import FileResponse

    @app.get("/app")
    async def serve_app():
        return FileResponse(site_dir / "index.html")

    @app.get("/style.css")
    async def serve_style():
        return FileResponse(site_dir / "style.css", media_type="text/css")

    # Mount all static asset directories
    for subdir in ["css", "lib_hCbTwtypfRFzmFju", "lib_wfKJyoksALKsfAWv"]:
        d = site_dir / subdir
        if d.exists():
            app.mount(f"/{subdir}", StaticFiles(directory=str(d)), name=subdir)

    # Serve css-1 font file
    css1_file = site_dir / "css-1"
    if css1_file.exists():
        @app.get("/css-1")
        async def serve_css1():
            return FileResponse(css1_file, media_type="text/css")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=HOST, port=PORT, reload=True)
