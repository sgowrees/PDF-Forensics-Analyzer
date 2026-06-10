from django.urls import path
from .views import DocumentDetailView, DocumentListView, DocumentUploadView

# All routes are mounted under /api/documents/ via config/api_router.py.
# The full URLs are:
#
#   GET  /api/documents/           → list all documents for the logged-in user
#   POST /api/documents/upload/    → upload a PDF and get back forensic findings
#   GET  /api/documents/<uuid>/    → get full findings for one specific document

urlpatterns = [
    path("",           DocumentListView.as_view(),  name="document-list"),
    path("upload/",    DocumentUploadView.as_view(), name="document-upload"),
    path("<uuid:pk>/", DocumentDetailView.as_view(), name="document-detail"),
]