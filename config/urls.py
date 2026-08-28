from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from store.views import login_view, logout_view

urlpatterns = [
    # 1️⃣ Custom App Routes (MUST be first)
    path("", include("store.urls")),
    
    # 2️⃣ Custom Auth
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    
    # 3️⃣ Django Built-in Admin (LAST)
    path("admin/", admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)