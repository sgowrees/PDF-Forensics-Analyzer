from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

# ================= BASIC =================
SECRET_KEY = env("SECRET_KEY", default="dev-secret-key")
DEBUG = env.bool("DEBUG", default=True)
ALLOWED_HOSTS = ["*"]

# ================= APPS =================
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "corsheaders",
    "rest_framework_simplejwt",

    "allauth",
    "allauth.account",
    "allauth.headless",
    "allauth.socialaccount",
]

LOCAL_APPS = [
    "apps.users",
    "apps.documents",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ================= MIDDLEWARE =================
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",  # MUST BE FIRST

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

# ================= TEMPLATES =================
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
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ================= DATABASE =================
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# ================= AUTH =================
AUTH_USER_MODEL = "users.User"

AUTHENTICATION_BACKENDS = [
    "apps.users.backends.EmailBackend",
    "django.contrib.auth.backends.ModelBackend",
]

# ================= PASSWORD VALIDATION =================
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ================= INTERNATIONALIZATION =================
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ================= STATIC =================
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# ================= MEDIA =================
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ================= CORS (IMPORTANT FIX) =================
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
]

CORS_ALLOW_CREDENTIALS = True

# ================= CSRF (IMPORTANT FOR DEV) =================
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:5173",
]

# IMPORTANT: KEEP SIMPLE FOR LOCAL DEV
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SAMESITE = "Lax"

CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False

# ================= DJANGO REST FRAMEWORK =================
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
}

# ================= ALLAUTH (optional but safe) =================
SITE_ID = 1

ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_AUTHENTICATION_METHOD = "email"
ACCOUNT_EMAIL_VERIFICATION = "none"

# ================= SIMPLE JWT =================
from datetime import timedelta

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "AUTH_HEADER_TYPES": ("Bearer",),
}

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",

    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",

    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",

    # ✅ REQUIRED BY ALLAUTH (ADD THIS LINE)
    "allauth.account.middleware.AccountMiddleware",

    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

