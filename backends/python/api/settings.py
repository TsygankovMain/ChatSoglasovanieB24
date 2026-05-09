from pathlib import Path
from urllib.parse import urlparse

from config import config

BASE_DIR = Path(__file__).resolve().parent

SECRET_KEY = config.jwt_secret
DEBUG = config.debug

# SEC-P1-4: in production VIRTUAL_HOST must be set; do not fall back to "*".
VIRTUAL_HOST = (config.app_base_url or "").strip()

if VIRTUAL_HOST and not VIRTUAL_HOST.startswith(("http://", "https://")):
    VIRTUAL_HOST = f"https://{VIRTUAL_HOST}"

if VIRTUAL_HOST and VIRTUAL_HOST != "https://app_base_url":
    CSRF_TRUSTED_ORIGINS = [VIRTUAL_HOST]
    domain = urlparse(VIRTUAL_HOST).hostname or ""
    ALLOWED_HOSTS = [h for h in [domain, "localhost", "127.0.0.1", "api-python"] if h]
else:
    if not DEBUG:
        raise RuntimeError(
            "VIRTUAL_HOST is not configured. Refusing to start in production with ALLOWED_HOSTS=['*']."
        )
    CSRF_TRUSTED_ORIGINS = []
    ALLOWED_HOSTS = ["localhost", "127.0.0.1", "api-python"]

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
    CORS_ALLOWED_ORIGINS = [VIRTUAL_HOST] if VIRTUAL_HOST else []
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
    },
}
