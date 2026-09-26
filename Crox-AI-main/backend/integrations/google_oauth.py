"""One-time interactive OAuth for Gmail + Sheets, backed by GOOGLE_CLIENT_ID /
GOOGLE_CLIENT_SECRET (a Desktop-app OAuth client, see README). The resulting
refresh token is cached locally (gitignored) so this only has to happen once
per machine.
"""

import json
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from config import get_settings

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
]


class GoogleOAuthNotConfigured(RuntimeError):
    pass


def _client_config() -> dict:
    settings = get_settings()
    if not settings.google_client_id or not settings.google_client_secret:
        raise GoogleOAuthNotConfigured(
            "GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set in .env before Gmail/Sheets can authenticate."
        )
    return {
        "installed": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }


def get_google_credentials() -> Credentials:
    """Returns valid credentials, refreshing a cached token if possible and
    otherwise running the one-time interactive consent flow (opens a browser,
    listens on a local port for the redirect)."""
    settings = get_settings()
    cache_path = Path(settings.google_oauth_token_cache)

    creds: Credentials | None = None
    if cache_path.exists():
        creds = Credentials.from_authorized_user_info(json.loads(cache_path.read_text()), SCOPES)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_config(_client_config(), SCOPES)
        creds = flow.run_local_server(port=0)

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(creds.to_json())
    return creds
