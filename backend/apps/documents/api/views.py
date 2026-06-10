from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.documents.api.serializers import (
    DocumentDetailSerializer,
    DocumentListSerializer,
    DocumentUploadSerializer,
)
from apps.documents.models import Document
from apps.documents.services import AnalysisService


class DocumentUploadView(APIView):
    """POST /api/documents/upload/ — upload a PDF and return the forensics report."""

    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = DocumentUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        document = AnalysisService.create_from_upload(serializer.validated_data["file"])

        try:
            report = AnalysisService.analyze_document(document)
        except Exception as exc:
            document.status = Document.AnalysisStatus.FAILED
            document.save(update_fields=["status", "updated_at"])
            return Response(
                {"error": f"Analysis failed: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            AnalysisService.to_response(document, report),
            status=status.HTTP_201_CREATED,
        )


class DocumentListView(ListAPIView):
    serializer_class = DocumentListSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    def get_queryset(self):
        return Document.objects.select_related("analysis").all()


class DocumentDetailView(RetrieveAPIView):
    serializer_class = DocumentDetailSerializer
    lookup_field = "id"
    permission_classes = [AllowAny]
    authentication_classes = []

    def get_queryset(self):
        return Document.objects.select_related("analysis").all()
