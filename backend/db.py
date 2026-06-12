import os
from supabase import create_client, Client


def _build_client() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set as environment variables"
        )
    return create_client(url, key)


supabase: Client = _build_client()
