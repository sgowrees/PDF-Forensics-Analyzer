from rest_framework import serializers

from apps.documents.models import Document, AnalysisResult
from apps.documents.models import TemplateDocument


MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024


# =========================
# DOCUMENT UPLOAD
# =========================
class DocumentUploadSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, value):
        if not value:
            raise serializers.ValidationError("No file provided.")

        if value.size > MAX_FILE_SIZE_BYTES:
            raise serializers.ValidationError("File too large (max 20MB).")

        content_type = getattr(value, "content_type", "")
        if content_type and "pdf" not in content_type.lower():
            raise serializers.ValidationError("Only PDF files allowed.")

        # Validate PDF header safely
        header = value.read(5)
        value.seek(0)

        if header != b"%PDF-":
            raise serializers.ValidationError("Invalid PDF file.")

        return value


# =========================
# ANALYSIS RESULT
# =========================
class AnalysisResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalysisResult
        fields = [
            "score",
            "risk",
            "baseline_available",
            "reasons",
            "score_breakdown",
            "classification_confidence",
            "created_at",
        ]


# =========================
# DOCUMENT DETAIL
# =========================
class DocumentDetailSerializer(serializers.ModelSerializer):
    analysis = AnalysisResultSerializer(read_only=True)

    class Meta:
        model = Document
        fields = [
            "id",
            "original_filename",
            "doc_type",
            "issuer",
            "issuer_slug",
            "status",
            "created_at",
            "updated_at",
            "analysis",
        ]


# =========================
# DOCUMENT LIST
# =========================
class DocumentListSerializer(serializers.ModelSerializer):
    risk = serializers.SerializerMethodField()
    score = serializers.SerializerMethodField()
    owner_email = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            "id",
            "original_filename",
            "doc_type",
            "issuer",
            "status",
            "risk",
            "score",
            "owner_email",
            "created_at",
        ]

    def get_risk(self, obj):
        return getattr(getattr(obj, "analysis", None), "risk", None)

    def get_score(self, obj):
        return getattr(getattr(obj, "analysis", None), "score", None)

    def get_owner_email(self, obj):
        return obj.owner.email if obj.owner_id else None


# =========================
# TEMPLATE DOCUMENT (ADMIN)
# =========================
class TemplateDocumentSerializer(serializers.ModelSerializer):
    filename = serializers.SerializerMethodField()
    file_size = serializers.SerializerMethodField()
    uploaded_by_email = serializers.SerializerMethodField()

    class Meta:
        model = TemplateDocument
        fields = [
            "id",
            "name",
            "filename",
            "file_size",
            "uploaded_by_email",
            "created_at",
        ]

    def get_filename(self, obj):
        return obj.file.name if obj.file else ""

    def get_file_size(self, obj):
        if not obj.file:
            return None
        try:
            return obj.file.size
        except OSError:
            return None

    def get_uploaded_by_email(self, obj):
        return obj.uploaded_by.email if obj.uploaded_by else None