import os
from pathlib import Path

# Defaults seguros para ejecutar CI sin secretos de produccion.
os.environ.setdefault("SECRET_KEY_DJANGO", "ci-secret-key-erp-2026-long-enough-for-jwt-signing")
os.environ.setdefault("DEBUG", "True")
os.environ.setdefault("ALLOWED_HOSTS", "localhost,127.0.0.1,testserver")
os.environ.setdefault("DB_NAME", "ci")
os.environ.setdefault("DB_USER", "ci")
os.environ.setdefault("DB_PASSWORD", "ci")
os.environ.setdefault("DB_HOST", "127.0.0.1")
os.environ.setdefault("DB_PORT", "3306")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "ci")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "ci")
os.environ.setdefault("AWS_STORAGE_BUCKET_NAME", "ci-bucket")
os.environ.setdefault("AWS_S3_ENDPOINT_URL", "https://example.invalid")
os.environ.setdefault("AWS_S3_REGION_NAME", "us-east-1")

from .settings import *  # noqa: F401,F403

BASE_DIR = Path(__file__).resolve().parent.parent

# CI usa sqlite para evitar dependencia de servicios externos.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db_ci.sqlite3",
    }
}

# Acelera tests en CI.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

AXES_ENABLED = False
AUTH_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

# Evita dependencias de storage cloud en CI.
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}
