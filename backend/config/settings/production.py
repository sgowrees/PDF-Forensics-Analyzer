from .base import *  # noqa

DEBUG = False

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_HOST_USER = env("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL")

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS")

HEADLESS_FRONTEND_URLS = {
    "account_confirm_email": env("FRONTEND_URL") + "/auth/verify-email/{key}",
    "account_reset_password": env("FRONTEND_URL") + "/auth/password-reset",
    "account_reset_password_from_key": env("FRONTEND_URL") + "/auth/password-reset/{key}",
}