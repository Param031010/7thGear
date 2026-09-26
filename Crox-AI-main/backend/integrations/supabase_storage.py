"""Resume attachments are uploaded to Supabase Storage (not kept as local
files) so their URLs can be stored directly in the candidate tracker sheet
and are reachable from anywhere, not just this machine.
"""

from functools import lru_cache

from database.client import get_supabase
from config import get_settings


@lru_cache
def _ensure_bucket() -> None:
    settings = get_settings()
    client = get_supabase()
    try:
        client.storage.create_bucket(settings.supabase_resumes_bucket, options={"public": True})
    except Exception:
        pass  # bucket already exists -- create_bucket has no idempotent "if not exists" flag


def upload_resume(path: str, content: bytes, content_type: str = "application/pdf") -> str:
    """Uploads resume bytes to `resumes/<path>` and returns its public URL."""
    settings = get_settings()
    _ensure_bucket()
    client = get_supabase()
    bucket = client.storage.from_(settings.supabase_resumes_bucket)
    bucket.upload(path, content, {"content-type": content_type, "upsert": "true"})
    return bucket.get_public_url(path)
