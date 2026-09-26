from functools import lru_cache

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    gemini_api_key: str = ""
    gemini_model: str = "gemini-flash-lite-latest"

    supabase_url: str = ""
    supabase_service_role_key: str = ""

    google_client_id: str = ""
    google_client_secret: str = ""
    google_oauth_token_cache: str = ".token_cache/google_token.json"

    # Left blank on purpose: the sheets tool creates a tracker spreadsheet on
    # first use and caches its id in google_sheets_id_cache, so nobody has to
    # go create one by hand. Set this to pin a specific existing sheet instead.
    google_sheets_spreadsheet_id: str = ""
    google_sheets_id_cache: str = ".token_cache/sheets_spreadsheet_id.txt"
    google_sheets_tab_name: str = "Sheet1"

    supabase_resumes_bucket: str = "resumes"

    slack_bot_token: str = ""

    demo_mode: bool = True

    backend_host: str = "127.0.0.1"
    backend_port: int = 8000


@lru_cache
def get_settings() -> Settings:
    return Settings()
