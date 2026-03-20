import os
from pathlib import Path


# Smoke settings: cargan la configuracion base de produccion con defaults seguros
# para validar imports, apps y settings sin depender de MySQL ni storage externo.
os.environ.setdefault("SECRET_KEY_DJANGO", "smoke-secret-key-erp-2026-long-enough-for-jwt-signing")
os.environ.setdefault("DEBUG", "False")
os.environ.setdefault("ALLOWED_HOSTS", "localhost,127.0.0.1,testserver")
os.environ.setdefault("DB_NAME", "smoke")
os.environ.setdefault("DB_USER", "smoke")
os.environ.setdefault("DB_PASSWORD", "smoke")
os.environ.setdefault("DB_HOST", "127.0.0.1")
os.environ.setdefault("DB_PORT", "3306")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "smoke")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "smoke")
os.environ.setdefault("AWS_STORAGE_BUCKET_NAME", "smoke-bucket")
os.environ.setdefault("AWS_S3_ENDPOINT_URL", "https://example.invalid")
os.environ.setdefault("AWS_S3_REGION_NAME", "us-east-1")

from .settings import *  # noqa: F401,F403


BASE_DIR = Path(__file__).resolve().parent.parent

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db_smoke.sqlite3",
    }
}

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}