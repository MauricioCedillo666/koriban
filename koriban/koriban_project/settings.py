"""Configuración de Koriban (prototipo local)."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Prototipo local: no usar esta llave ni DEBUG=True en producción.
SECRET_KEY = "django-insecure-koriban-prototipo-local-cambiar-en-produccion"
DEBUG = True
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "crm",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "koriban_project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "crm.context_processors.koriban",
            ],
        },
    },
]

WSGI_APPLICATION = "koriban_project.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
]

LANGUAGE_CODE = "es-mx"
TIME_ZONE = "America/Mexico_City"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]

# Los documentos NO se publican en /media: se sirven por vistas con control de acceso.
MEDIA_ROOT = BASE_DIR / "media"
MEDIA_URL = "/media/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "crm:dashboard"
LOGOUT_REDIRECT_URL = "landing"

# Correo SIMULADO: cada correo se guarda como archivo .log en /correos_simulados
# y además queda registrado en el CRM (módulo "Correos").
EMAIL_BACKEND = "django.core.mail.backends.filebased.EmailBackend"
EMAIL_FILE_PATH = BASE_DIR / "correos_simulados"
DEFAULT_FROM_EMAIL = "Koriban Soluciones Digitales <propuestas@koriban.mx>"

# URL base para los enlaces que van dentro de los correos (cuando no hay request).
SITE_URL = "http://127.0.0.1:8000"

# Límite de tamaño para documentos PDF (MB)
DOCUMENTO_MAX_MB = 5

KORIBAN = {
    "nombre": "Koriban",
    "eslogan": "Tu sitio web y tu CRM, trabajando como uno solo.",
    "telefono": "55 1234 5678",
    "whatsapp": "5215512345678",
    "email": "contacto@koriban.mx",
    "zona": "CDMX y Área Metropolitana",
}
