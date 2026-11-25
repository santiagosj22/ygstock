"""YG Stock. Proyecto aparte de Serium, con la misma base: Django y Postgres en Render."""

import os
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
load_dotenv(BASE_DIR / ".env.local", override=True)


def _lista_env(nombre, defecto):
    crudo = os.environ.get(nombre, "")
    if crudo.strip():
        return [parte.strip() for parte in crudo.split(",") if parte.strip()]
    return list(defecto)


ENVIRONMENT = os.environ.get("DJANGO_ENVIRONMENT", "local")
SECRET_KEY = (os.environ.get("SECRET_KEY") or "").strip() or "ygstock-desarrollo-local"
if ENVIRONMENT == "production" and SECRET_KEY == "ygstock-desarrollo-local":
    raise ImproperlyConfigured("SECRET_KEY es obligatoria en producción.")

DEBUG = ENVIRONMENT != "production"

ALLOWED_HOSTS = _lista_env("ALLOWED_HOSTS", ["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = _lista_env("CSRF_TRUSTED_ORIGINS", [])
RENDER_HOST = (os.environ.get("RENDER_EXTERNAL_HOSTNAME") or "").strip()
if RENDER_HOST and RENDER_HOST not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RENDER_HOST)
if RENDER_HOST:
    origen_render = f"https://{RENDER_HOST}"
    if origen_render not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(origen_render)

if DEBUG:
    WHITENOISE_USE_FINDERS = True
    for origen in (
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:8001",
        "http://127.0.0.1:8001",
    ):
        if origen not in CSRF_TRUSTED_ORIGINS:
            CSRF_TRUSTED_ORIGINS.append(origen)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "inventario",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

# En local, SQLite. En Render, Postgres gratis de Neon (DATABASE_URL).
# Neon apaga el cómputo al quedar inactivo, así que no se reutiliza la conexión.
_database = dj_database_url.config(
    default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
    conn_max_age=0,
)
if not _database["ENGINE"].endswith("sqlite3"):
    _database.setdefault("OPTIONS", {})
    _database["OPTIONS"].setdefault("sslmode", "require")
DATABASES = {"default": _database}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es-co"
TIME_ZONE = "America/Bogota"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
DATA_UPLOAD_MAX_MEMORY_SIZE = 15 * 1024 * 1024

if ENVIRONMENT == "production":
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
    }
