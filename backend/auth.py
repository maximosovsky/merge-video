"""YouTube OAuth2 authentication flow."""

from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials

from config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

# In-memory token store: {user_id: credentials}
# MVP — for production use Redis/DB
_token_store: dict[str, Credentials] = {}


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
    """Store credentials for a user."""
    _token_store[user_id] = credentials


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
