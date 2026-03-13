from pathlib import Path
from decouple import config
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent

# =========================================================
# BASIC CONFIG
# =========================================================

SECRET_KEY = config("SECRET_KEY_DJANGO")

DEBUG = config("DEBUG", default=False, cast=bool)

ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="").split(",")

# =========================================================
# APPLICATIONS
# =========================================================

INSTALLED_APPS = [
    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third Party
    "rest_framework",
    "corsheaders",
    "axes",
    'storages',

    # Local Apps
    'apps.core.apps.CoreConfig',
    'apps.contactos.apps.ContactosConfig',
    'apps.presupuestos.apps.PresupuestosConfig',
    'apps.productos.apps.ProductosConfig',
    'apps.compras.apps.ComprasConfig',
    'apps.documentos.apps.DocumentosConfig',
    'apps.inventario.apps.InventarioConfig',
    'apps.auditoria.apps.AuditoriaConfig',
]

# =========================================================
# MIDDLEWARE
# =========================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.core.middleware.EmpresaMiddleware",
    "axes.middleware.AxesMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "Eldanor_ERP.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "Eldanor_ERP.wsgi.application"

# =========================================================
# DATABASE
# =========================================================

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": config("DB_NAME"),
        "USER": config("DB_USER"),
        "PASSWORD": config("DB_PASSWORD"),
        "HOST": config("DB_HOST", default="127.0.0.1"),
        "PORT": config("DB_PORT", default="3306"),
        "OPTIONS": {
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'"
        }
    }
}

# =========================================================
# AUTH
# =========================================================

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTH_USER_MODEL = "core.User"

# =========================================================
# DJANGO AXES (ANTI BRUTE FORCE)
# =========================================================

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = timedelta(hours=1)
AXES_USERNAME_FORM_FIELD = "email"
AXES_RESET_ON_SUCCESS = True
# En local evita bloqueos por pruebas repetidas; en produccion (DEBUG=False) sigue activo.
AXES_ENABLED = not DEBUG


# =========================================================
# DRF CONFIG
# =========================================================

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "apps.core.authentication.CookieJWTAuthentication",
    ),
    "EXCEPTION_HANDLER": "apps.core.api.exception_handler.custom_exception_handler",
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.URLPathVersioning",
    "DEFAULT_VERSION": "v1",
    "ALLOWED_VERSIONS": ["v1"],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        # En desarrollo el frontend dispara varias cargas de catalogos.
        "anon": config("DRF_THROTTLE_ANON_RATE", default="300/hour" if DEBUG else "30/hour"),
        "user": config("DRF_THROTTLE_USER_RATE", default="2000/hour" if DEBUG else "200/hour"),
    },
}

# =========================================================
# SIMPLE JWT
# =========================================================

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

AUTH_COOKIE_ACCESS_NAME = config("AUTH_COOKIE_ACCESS_NAME", default="erp_access")
AUTH_COOKIE_REFRESH_NAME = config("AUTH_COOKIE_REFRESH_NAME", default="erp_refresh")
AUTH_COOKIE_SECURE = config("AUTH_COOKIE_SECURE", default=not DEBUG, cast=bool)
AUTH_COOKIE_SAMESITE = config("AUTH_COOKIE_SAMESITE", default="Strict")
AUTH_COOKIE_DOMAIN = config("AUTH_COOKIE_DOMAIN", default=None)
AUTH_COOKIE_PATH = config("AUTH_COOKIE_PATH", default="/")

# Cookies/session security for production
SESSION_COOKIE_SECURE = config("SESSION_COOKIE_SECURE", default=not DEBUG, cast=bool)
CSRF_COOKIE_SECURE = config("CSRF_COOKIE_SECURE", default=not DEBUG, cast=bool)
CSRF_TRUSTED_ORIGINS = [
    origin for origin in config("CSRF_TRUSTED_ORIGINS", default="").split(",") if origin
]

# Transport/security hardening (safe defaults for production)
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=not DEBUG, cast=bool)
SECURE_HSTS_SECONDS = config("SECURE_HSTS_SECONDS", default=0 if DEBUG else 31536000, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = config("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=not DEBUG, cast=bool)
SECURE_HSTS_PRELOAD = config("SECURE_HSTS_PRELOAD", default=not DEBUG, cast=bool)
SECURE_PROXY_SSL_HEADER = (
    tuple(config("SECURE_PROXY_SSL_HEADER", cast=lambda v: tuple(x.strip() for x in v.split(","))))
    if config("SECURE_PROXY_SSL_HEADER", default="").strip()
    else None
)

# ERP purchase controls (3-way match tolerances)
ERP_OC_QTY_TOLERANCE_PCT = config("ERP_OC_QTY_TOLERANCE_PCT", default=0, cast=int)
ERP_OC_PRICE_TOLERANCE_PCT = config("ERP_OC_PRICE_TOLERANCE_PCT", default=0, cast=int)

# =========================================================
# CORS
# =========================================================

CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:5173,http://127.0.0.1:5173"
).split(",")

CORS_ALLOW_CREDENTIALS = True

# =========================================================
# INTERNATIONALIZATION
# =========================================================

LANGUAGE_CODE = "es-cl"

TIME_ZONE = "America/Santiago"

USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
# =========================================================
# STATIC FILES
# =========================================================

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"



# Configuración Cloudflare R2
AWS_ACCESS_KEY_ID = config("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = config("AWS_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = config("AWS_STORAGE_BUCKET_NAME")
AWS_S3_ENDPOINT_URL = config("AWS_S3_ENDPOINT_URL")
AWS_S3_REGION_NAME = config("AWS_S3_REGION_NAME")
_custom_domain = config("AWS_S3_CUSTOM_DOMAIN", default="").strip()
if _custom_domain.startswith("tu-dominio-configurado"):
    _custom_domain = ""
if _custom_domain.startswith("http://"):
    _custom_domain = _custom_domain[len("http://") :]
if _custom_domain.startswith("https://"):
    _custom_domain = _custom_domain[len("https://") :]
_custom_domain = _custom_domain.rstrip("/")
AWS_S3_CUSTOM_DOMAIN = _custom_domain or None
AWS_S3_FILE_OVERWRITE = True
AWS_S3_SIGNATURE_VERSION = "s3v4"
AWS_S3_ADDRESSING_STYLE = "path"

AWS_DEFAULT_ACL = None
AWS_QUERYSTRING_AUTH = False

AWS_S3_OBJECT_PARAMETERS = {
    "CacheControl": "max-age=86400, s-maxage=86400, must-revalidate",
}

# Django 6 storage configuration.
STORAGES = {
    "default": {
        "BACKEND": "apps.core.storage.tenant_storage.TenantStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}
