from django.urls import path, include

urlpatterns = [
    path("documents/", include("apps.documents.api.urls")),
    path("users/", include("apps.users.urls"))
]