# Bare ``settings.py`` for running tests for rest_framework_bulk

DEBUG = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": "rest_framework_bulk.sqlite",
    }
}

MIDDLEWARE = []

INSTALLED_APPS = (
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_bulk",
    "rest_framework_bulk.tests.simple_app",
)

STATIC_URL = "/static/"
SECRET_KEY = "foo"

ROOT_URLCONF = "rest_framework_bulk.tests.simple_app.urls"

# Silence auto-created primary key warnings in tests
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"
