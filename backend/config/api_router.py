from django.urls import path, include

urlpatterns = [
    path("users/", include("apps.users.api.urls")),
    path("documents/", include("apps.documents.api.urls"))
]