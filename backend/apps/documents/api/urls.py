from django.urls import path
from .views import (
    DocumentDetailView,
    DocumentListView,
    DocumentUploadView,
    TemplateDestroyView,
    TemplateListView,
    TemplateUploadView,
)

urlpatterns = [
    path("", DocumentListView.as_view(), name="document-list"),
    path("upload/", DocumentUploadView.as_view(), name="document-upload"),
    path("<uuid:id>/", DocumentDetailView.as_view(), name="document-detail"),

    # ADMIN ONLY
    path("templates/", TemplateListView.as_view(), name="template-list"),
    path("templates/upload/", TemplateUploadView.as_view(), name="template-upload"),
    path("templates/<int:pk>/", TemplateDestroyView.as_view(), name="template-delete"),
]