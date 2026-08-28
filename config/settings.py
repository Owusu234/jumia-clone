import os
from pathlib import Path
import dj_database_url
from dotenv import load_dotenv  

load_dotenv()


PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY")
PAYSTACK_PUBLIC_KEY = os.getenv("PAYSTACK_PUBLIC_KEY")
SITE_URL = os.getenv("SITE_URL", "http://127.0.0.1:8000")

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.getenv("SECRET_KEY")

# ✅ Admin Settings
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

if os.getenv('DJANGO_DEBUG', 'False') == 'False':
    SECURE_SSL_REDIRECT = False  # ✅ Railway handles HTTPS, so Django shouldn't redirect
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True


# ✅ DEBUG: Must be False in production
DEBUG = os.getenv("DJANGO_DEBUG", "False") == "True"

# ⚠️ Security: Fail fast if credentials are missing in production
if not DEBUG and not all([ADMIN_EMAIL, ADMIN_PASSWORD, SECRET_KEY]):
    raise ValueError("❌ ADMIN_EMAIL, ADMIN_PASSWORD, and SECRET_KEY must be set in .env for production")

# Supabase Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "store",
    'chartjs',
    'corsheaders',
]

# ✅ MIDDLEWARE: Add Whitenoise for static files (right after SecurityMiddleware)
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # ✅ MUST be right after SecurityMiddleware
    'corsheaders.middleware.CorsMiddleware', 
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    'store.middleware.ProfileCompletionMiddleware',
    'store.views.AnalyticsMiddleware',
]

# ✅ CORS & CSRF: Make domains configurable via env var
CORS_ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS", "http://127.0.0.1:8000,http://localhost:8000,https://shopvibe.railway.internal,https://shopvibe.up.railway.app").split(",")

CSRF_TRUSTED_ORIGINS = os.getenv("CSRF_TRUSTED_ORIGINS", "http://127.0.0.1:8000,http://localhost:8000,https://shopvibe.railway.internal,https://shopvibe.up.railway.app").split(",")

ROOT_URLCONF = "config.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [],
    "APP_DIRS": True,
    "OPTIONS": {
        "context_processors": [
            "django.template.context_processors.debug",
            "django.template.context_processors.request",
            "django.contrib.auth.context_processors.auth",
            "django.contrib.messages.context_processors.messages",
            "store.context_processors.global_context",
        ],
    },
}]
WSGI_APPLICATION = "config.wsgi.application"

# ✅ DATABASE: Supabase via dj_database_url (works on Railway)
DATABASES = {
    'default': dj_database_url.config(
        default=os.environ.get('DATABASE_URL'),
        conn_max_age=0,  # Supabase recommends 0 for direct connections
        ssl_require=True
    )
}

# ✅ ALLOWED_HOSTS: Fixed format (no https:// prefixes)
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,shopvibe.railway.internal,shopvibe.up.railway.app").split(",")

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ✅ STATIC FILES: Whitenoise configuration for production
STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")  # ✅ Use os.path.join for reliability
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"  # ✅ Compress & cache static files

# ✅ WHITENOISE: Additional settings for production
WHITENOISE_MANIFEST_STRICT = False  # ✅ Prevent errors if a static file is missing
WHITENOISE_ROOT = os.path.join(BASE_DIR, "staticfiles")  # ✅ Explicit root for Whitenoise

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "store:home"
LOGOUT_REDIRECT_URL = "store:home"

