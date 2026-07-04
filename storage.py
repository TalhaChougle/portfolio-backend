import os
import uuid
from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
BUCKET = "portfolio-certs"

client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def upload_file(file_bytes: bytes, filename: str, content_type: str) -> str:
    ext = filename.rsplit(".", 1)[-1] if "." in filename else "bin"
    key = f"{uuid.uuid4().hex}.{ext}"
    client.storage.from_(BUCKET).upload(
        key, file_bytes, {"content-type": content_type}
    )
    return client.storage.from_(BUCKET).get_public_url(key)


def delete_file(file_url: str):
    if not file_url:
        return
    key = file_url.rsplit("/", 1)[-1]
    try:
        client.storage.from_(BUCKET).remove([key])
    except Exception:
        pass
