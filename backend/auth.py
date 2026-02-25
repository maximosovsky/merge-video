"""YouTube OAuth2 authentication flow."""

from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials

from config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]

# In-memory stores: {user_id: credentials / profile}
_token_store: dict[str, Credentials] = {}
_profile_store: dict[str, dict] = {}


def create_auth_url(state: str = "") -> str:
    """Generate YouTube OAuth2 authorization URL."""
    flow = _create_flow()
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=state,
    )
    return auth_url


def exchange_code(code: str) -> Credentials:
    """Exchange authorization code for credentials."""
    flow = _create_flow()
    flow.fetch_token(code=code)
    return flow.credentials


def save_credentials(user_id: str, credentials: Credentials):
    """Store credentials for a user and fetch profile."""
    _token_store[user_id] = credentials
    # Fetch Google profile info
    try:
        import requests
        r = requests.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {credentials.token}"}
        )
        if r.ok:
            info = r.json()
            _profile_store[user_id] = {
                "picture": info.get("picture", ""),
                "email": info.get("email", ""),
                "name": info.get("name", ""),
            }
    except Exception:
        pass

    # Notify Telegram bot if this is a Telegram user
    if user_id.startswith("tg_"):
        _notify_bot_auth(user_id)


def _notify_bot_auth(user_id: str):
    """Send webhook to Telegram bot about successful auth."""
    from config import BOT_API_URL
    import requests
    profile = get_user_info(user_id) or {}
    try:
        requests.post(
            f"{BOT_API_URL}/auth_notify",
            json={
                "user_id": user_id,
                "success": True,
                "name": profile.get("name", ""),
                "email": profile.get("email", ""),
            },
            timeout=5,
        )
        print(f"🔔 Bot notified: {user_id} authorized")
    except Exception as e:
        print(f"🔔 Bot notification failed: {e}")


def get_credentials(user_id: str) -> Credentials | None:
    """Get stored credentials for a user. Returns None if not found or expired."""
    creds = _token_store.get(user_id)
    if creds is None:
        return None
    if creds.expired and creds.refresh_token:
        from google.auth.transport.requests import Request
        creds.refresh(Request())
        _token_store[user_id] = creds
    return creds


def get_user_info(user_id: str) -> dict | None:
    """Get stored profile info."""
    return _profile_store.get(user_id)


def remove_credentials(user_id: str):
    """Remove stored credentials and profile for a user."""
    _token_store.pop(user_id, None)
    _profile_store.pop(user_id, None)


CC_EMAIL = "izdanie@gmail.com"


def _send_email(user_id: str, subject: str, body_html: str):
    """Send email via Gmail API with CC to izdanie@gmail.com."""
    import base64
    from email.mime.text import MIMEText
    from googleapiclient.discovery import build

    creds = get_credentials(user_id)
    profile = get_user_info(user_id)
    if not creds or not profile or not profile.get("email"):
        print(f"📧 Skip email — no credentials or email for {user_id}")
        return

    email = profile["email"]
    msg = MIMEText(body_html, "html")
    msg["to"] = email
    msg["cc"] = CC_EMAIL
    msg["subject"] = subject

    try:
        service = build("gmail", "v1", credentials=creds)
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        service.users().messages().send(userId="me", body={"raw": raw}).execute()
        print(f"📧 Email sent to {email} (cc: {CC_EMAIL}): {subject}")
    except Exception as e:
        print(f"📧 Email failed: {e}")


def _email_wrap(content: str) -> str:
    return f"""<div style="font-family:Arial,sans-serif;max-width:500px;margin:0 auto;padding:20px">
        {content}
        <p style="color:#888;font-size:12px;margin-top:24px">— Merge Video by Osovsky</p>
    </div>"""


def send_auth_email(user_id: str):
    """Send email when user authorizes."""
    profile = get_user_info(user_id) or {}
    name = profile.get("name", "")
    body = _email_wrap(f"""
        <h2>🔐 Authorized</h2>
        <p>Hi{(' ' + name) if name else ''},</p>
        <p>You have successfully authorized in <strong>Merge Video</strong>.</p>
        <p>You can now merge videos and upload them to YouTube.</p>
    """)
    _send_email(user_id, "🔐 Merge Video — Authorized", body)


def send_job_received_email(user_id: str, title: str, file_count: int):
    """Send email when merge job is received (before files are saved)."""
    body = _email_wrap(f"""
        <h2>📥 Job received</h2>
        <p>Your merge job <strong>"{title}"</strong> has been received.</p>
        <p>📎 {file_count} files</p>
        <p>Uploading files to server...</p>
    """)
    _send_email(user_id, f'📥 Received: "{title}" ({file_count} files)', body)


def send_job_started_email(user_id: str, title: str, file_count: int):
    """Send email when files are uploaded and merge begins."""
    body = _email_wrap(f"""
        <h2>📦 Files uploaded — merging</h2>
        <p>All files for <strong>"{title}"</strong> have been uploaded.</p>
        <p>📎 {file_count} files</p>
        <p>Merging has started. You'll receive an email when it's done.</p>
    """)
    _send_email(user_id, f'📦 Merging: "{title}" ({file_count} files)', body)


def send_result_email(user_id: str, title: str, result_url: str,
                      file_size: str = "", resolution: str = ""):
    """Send email when merge is complete with YouTube link."""
    stats = ""
    if file_size or resolution:
        parts = [p for p in [resolution, file_size] if p]
        stats = f'<p style="color:#555">📐 {" · ".join(parts)}</p>'
    body = _email_wrap(f"""
        <h2>🎬 Your merged video is ready!</h2>
        <p>Your video <strong>"{title}"</strong> has been merged successfully.</p>
        {stats}
        <p><a href="{result_url}" style="display:inline-block;padding:12px 24px;background:#333;color:#fff;text-decoration:none;border-radius:8px;font-weight:bold">▶ View on YouTube</a></p>
    """)
    _send_email(user_id, f'🎬 Merged: "{title}"', body)


def send_error_email(user_id: str, title: str, error: str):
    """Send email when merge fails."""
    # Truncate error
    err_short = error[:300] + "..." if len(error) > 300 else error
    body = _email_wrap(f"""
        <h2>❌ Merge failed</h2>
        <p>Your video <strong>"{title}"</strong> failed to merge.</p>
        <p style="background:#fff3f3;padding:10px;border-radius:6px;font-family:monospace;font-size:12px;color:#c00">{err_short}</p>
        <p>Please try again or contact support.</p>
    """)
    _send_email(user_id, f'❌ Merge failed: "{title}"', body)


def _create_flow() -> Flow:
    """Create OAuth2 flow from client config."""
    client_config = {
        "web": {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [GOOGLE_REDIRECT_URI],
        }
    }
    return Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri=GOOGLE_REDIRECT_URI)
