from .base import *  # noqa

DEBUG = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# For development, use in-memory broker to avoid needing Redis
CELERY_BROKER_URL = "memory://"
CELERY_RESULT_BACKEND = "cache+locmem://"
CELERY_ALWAYS_EAGER = True  # Execute tasks synchronously in development
CELERY_EAGER_PROPAGATES_EXCEPTIONS = True
