from pathlib import Path
import os
from urllib.parse import urlparse

from config import config

BASE_DIR = Path(__file__).resolve().parent

SECRET_KEY = config.jwt_secret
DEBUG = config.debug

def _normalize_origin(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    if not raw.startswith(("http://", "https://")):
        raw = f"https://{raw}"
    parsed = urlparse(raw)
    if not parsed.hostname:
        return ""
    return f"{parsed.scheme}://{parsed.hostname}".rstrip("/")


def _extract_host(value: str) -> str:
    origin = _normalize_origin(value)
    if not origin:
        return ""
    return urlparse(origin).hostname or ""


def _parse_allowed_hosts(raw: str) -> list[str]:
    hosts: list[str] = []
    for item in (raw or "").split(","):
        candidate = item.strip().lower().rstrip(".")
        if not candidate:
            continue
        if candidate.startswith(("http://", "https://")):
            candidate = _extract_host(candidate)
        if candidate and ":" in candidate and not candidate.startswith("["):
            candidate = candidate.split(":", 1)[0]
        if candidate:
            hosts.append(candidate)
    return hosts


# SEC-P1-4: in production host checks must be explicit and deterministic.
VIRTUAL_HOST = _normalize_origin(config.app_base_url)
APP_URL = _normalize_origin(os.getenv("APP_URL", ""))
PUBLIC_APP_URL = _normalize_origin(os.getenv("NUXT_PUBLIC_APP_URL", ""))
EXTRA_ALLOWED_HOSTS = _parse_allowed_hosts(os.getenv("ALLOWED_HOSTS", ""))

trusted_origins = [origin for origin in [VIRTUAL_HOST, APP_URL, PUBLIC_APP_URL] if origin]
derived_hosts = [
    host for host in [
        _extract_host(VIRTUAL_HOST),
        _extract_host(APP_URL),
        _extract_host(PUBLIC_APP_URL),
    ] if host
]
derived_hosts.extend(EXTRA_ALLOWED_HOSTS)
derived_hosts.extend(["localhost", "127.0.0.1", "api-python"])

# Timeweb App Platform technical domains can change between redeploys.
if any(host.endswith(".twc1.net") for host in derived_hosts):
    derived_hosts.append(".twc1.net")

ALLOWED_HOSTS = sorted(set(derived_hosts))
CSRF_TRUSTED_ORIGINS = sorted(set(trusted_origins))

if not DEBUG and (not CSRF_TRUSTED_ORIGINS or not ALLOWED_HOSTS):
    raise RuntimeError(
        "Host configuration is incomplete. Set VIRTUAL_HOST/APP_URL and optionally ALLOWED_HOSTS."
    )

# Stateless: no DB, no admin, no sessions, no contrib auth.
INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "corsheaders",
    "main",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
            ],
        },
    },
]

WSGI_APPLICATION = "wsgi.application"
ASGI_APPLICATION = "asgi.application"

# Stateless backend — no database. Django still requires the key, so use the
# in-memory dummy engine to keep manage.py working without psycopg2.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.dummy",
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "api/static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# SEC-P1-3: restrict CORS to our app host and Bitrix24 portals.
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
else:
    CORS_ALLOW_ALL_ORIGINS = False
    CORS_ALLOWED_ORIGINS = CSRF_TRUSTED_ORIGINS
    CORS_ALLOWED_ORIGIN_REGEXES = [
        r"^https://[a-z0-9-]+\.bitrix24\.[a-z]{2,3}$",
        r"^https://[a-z0-9-]+\.bitrix\.[a-z]{2,3}$",
    ]
CORS_ALLOW_CREDENTIALS = True

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "console": {
            "format": "%(asctime)s %(levelname)s [%(name)s] %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "console",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
    "loggers": {
        "approval": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "main.utils.decorators.log_errors": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.security.DisallowedHost": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
