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
    """POST /api/documents/upload/ — analyse in memory, nothing written to disk."""

    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = DocumentUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # create_from_upload returns (document, raw_bytes) — no file saved
        document, pdf_bytes = AnalysisService.create_from_upload(serializer.validated_data["file"])

        try:
            report = AnalysisService.analyze_document(document, pdf_bytes)
        except Exception as exc:
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
    
    