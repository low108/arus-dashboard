import json
import os
import secrets
import time
from pathlib import Path
from urllib.parse import urlparse
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from app.config import PROJECT_ROOT, settings

GMAIL_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
TOKEN_PATH = PROJECT_ROOT / "backend" / "token.json"
_states: dict[str, tuple[float, str]] = {}


def oauth_configured() -> bool:
    return bool(settings.google_client_id and settings.google_client_secret and settings.google_redirect_uri)


def _client_config() -> dict:
    return {"web": {"client_id": settings.google_client_id, "client_secret": settings.google_client_secret, "auth_uri": "https://accounts.google.com/o/oauth2/auth", "token_uri": "https://oauth2.googleapis.com/token", "redirect_uris": [settings.google_redirect_uri]}}


def authorization_url() -> str:
    if not oauth_configured():
        raise RuntimeError("Google OAuth is not configured")
    state = secrets.token_urlsafe(32)
    flow = Flow.from_client_config(_client_config(), scopes=[GMAIL_SCOPE], redirect_uri=settings.google_redirect_uri)
    url, _ = flow.authorization_url(access_type="offline", include_granted_scopes="true", prompt="consent", state=state)
    if not flow.code_verifier:
        raise RuntimeError("OAuth PKCE verifier was not generated")
    _states[state] = (time.time(), flow.code_verifier)
    return url


def exchange_callback(authorization_response: str, state: str) -> None:
    pending = _states.pop(state, None)
    if pending is None or time.time() - pending[0] > 600:
        raise RuntimeError("Invalid or expired OAuth state")
    flow = Flow.from_client_config(
        _client_config(), scopes=[GMAIL_SCOPE], state=state,
        redirect_uri=settings.google_redirect_uri,
        code_verifier=pending[1], autogenerate_code_verifier=False,
    )
    if urlparse(settings.google_redirect_uri or "").hostname in {"127.0.0.1", "localhost"}:
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    flow.fetch_token(authorization_response=authorization_response)
    TOKEN_PATH.write_text(flow.credentials.to_json(), encoding="utf-8")
    os.chmod(TOKEN_PATH, 0o600)


def load_credentials() -> Credentials | None:
    if not TOKEN_PATH.exists():
        return None
    try:
        credentials = Credentials.from_authorized_user_file(str(TOKEN_PATH), [GMAIL_SCOPE])
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
            TOKEN_PATH.write_text(credentials.to_json(), encoding="utf-8")
            os.chmod(TOKEN_PATH, 0o600)
        return credentials if credentials.valid else None
    except Exception:
        return None


def gmail_service():
    credentials = load_credentials()
    return build("gmail", "v1", credentials=credentials, cache_discovery=False) if credentials else None


def connected_account() -> str | None:
    service = gmail_service()
    if not service:
        return None
    try:
        return service.users().getProfile(userId="me").execute().get("emailAddress")
    except Exception:
        return None


def disconnect() -> None:
    if TOKEN_PATH.exists():
        TOKEN_PATH.unlink()
