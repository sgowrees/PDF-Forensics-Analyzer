from rest_framework import status
from rest_framework.generics import DestroyAPIView, ListAPIView, RetrieveAPIView
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.documents.api.serializers import (
    DocumentDetailSerializer,
    DocumentListSerializer,
    DocumentUploadSerializer,
    TemplateDocumentSerializer,
)
from apps.documents.baseline_sync import sync_filesystem_baselines
from apps.documents.models import Document, TemplateDocument
from apps.documents.services import AnalysisService
from apps.users.premissions import IsAdmin


class TemplateListView(ListAPIView):
    serializer_class = TemplateDocumentSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

    def get_queryset(self):
        sync_filesystem_baselines()
        return TemplateDocument.objects.select_related("uploaded_by")


class TemplateUploadView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request):
        file = request.FILES.get("file")

        if not file:
            return Response({"detail": "No file uploaded"}, status=400)

        if TemplateDocument.objects.filter(name=file.name).exists():
            return Response(
                {"detail": f"A baseline named '{file.name}' already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        template = TemplateDocument.objects.create(
            file=file,
            name=file.name,
            uploaded_by=request.user,
        )

        return Response(TemplateDocumentSerializer(template).data, status=201)


class TemplateDestroyView(DestroyAPIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = TemplateDocument.objects.all()
    lookup_field = "pk"

class DocumentUploadView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = DocumentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        document, pdf_bytes = AnalysisService.create_from_upload(
            serializer.validated_data["file"],
            owner=request.user,
        )

        try:
            report = AnalysisService.analyze_document(document, pdf_bytes)
        except Exception as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            AnalysisService.to_response(document, report),
            status=status.HTTP_201_CREATED,
        )


class DocumentListView(ListAPIView):
    serializer_class = DocumentListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        qs = Document.objects.select_related("analysis", "owner")

        if user.role == "admin":
            return qs

        return qs.filter(owner=user)


class DocumentDetailView(RetrieveAPIView):
    serializer_class = DocumentDetailSerializer
    lookup_field = "id"
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        qs = Document.objects.select_related("analysis", "owner")

        if user.role == "admin":
            return qs

        return qs.filter(owner=user)