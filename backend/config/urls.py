from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path("admin/", admin.site.urls),

    path("api/auth/refresh/", TokenRefreshView.as_view()),

    path("api/users/", include("apps.users.urls")),
    path("api/documents/", include("apps.documents.api.urls")),
]