"""
serializers.py
--------------
Django REST Framework serializers for the documents API.

Three serializers:
  1. DocumentUploadSerializer   — validates the incoming PDF upload
  2. AnalysisResultSerializer   — serialises the AnalysisResult model
  3. DocumentDetailSerializer   — serialises a Document + its nested analysis

Keep validation logic here (not in views) so it's testable and reusable.
"""

from rest_framework import serializers
from apps.documents.models import Document, AnalysisResult

# Maximum allowed PDF file size: 20 MB
# Financial documents are never this large — very large files are suspicious
MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB


class DocumentUploadSerializer(serializers.Serializer):
    """
    Validates a PDF file upload from the user.

    Expects a multipart/form-data POST with a single 'file' field.
    We validate:
      - The file is present
      - The MIME type claims to be PDF
      - The file starts with the PDF magic bytes (%PDF-)
      - The file size is within limits
    """

    file = serializers.FileField(
        help_text="The PDF file to analyse. Must be a valid PDF under 20 MB.",
    )

    def validate_file(self, value):
        """
        Custom validation for the uploaded file field.

        Django's FileField only checks that something was uploaded.
        We add content-type and magic byte checks here.

        Args:
            value: InMemoryUploadedFile or TemporaryUploadedFile from the request

        Returns:
            The validated file object (unchanged if valid)

        Raises:
            serializers.ValidationError if any check fails
        """
        # --- Size check ---
        if value.size > MAX_FILE_SIZE_BYTES:
            raise serializers.ValidationError(
                f"File too large: {value.size / 1024 / 1024:.1f} MB. "
                f"Maximum allowed size is {MAX_FILE_SIZE_BYTES / 1024 / 1024:.0f} MB."
            )

        # --- MIME type check ---
        # content_type is set by the browser and is UNTRUSTED — but it's a
        # quick first gate. The magic byte check below is the real validation.
        content_type = getattr(value, "content_type", "")
        if content_type and "pdf" not in content_type.lower():
            raise serializers.ValidationError(
                f"Invalid file type: '{content_type}'. Only PDF files are accepted."
            )

        # --- Magic byte check (PDF signature) ---
        # All valid PDF files start with the bytes: %PDF-
        # We read the first 5 bytes and check against this signature.
        # This is more reliable than trusting the content_type header.
        header = value.read(5)
        value.seek(0)  # IMPORTANT: reset the file pointer after reading

        if header != b"%PDF-":
            raise serializers.ValidationError(
                "File does not appear to be a valid PDF "
                "(missing PDF header signature '%PDF-')."
            )

        return value


class AnalysisResultSerializer(serializers.ModelSerializer):
    """
    Serialises an AnalysisResult model instance for API responses.

    Maps directly to the AnalysisResult model fields.
    """

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


class DocumentDetailSerializer(serializers.ModelSerializer):
    """
    Serialises a Document with its nested analysis result.

    Used for the GET /documents/<id>/ endpoint.
    The 'analysis' field is nested — if analysis hasn't run yet, it's null.
    """

    # Nested serialiser — uses the related_name="analysis" from the model
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
            "analysis",  # nested — null until analysis completes
        ]
        read_only_fields = fields  # everything is read-only on this serialiser


class DocumentListSerializer(serializers.ModelSerializer):
    """
    Lightweight serialiser for listing documents (GET /documents/).

    Excludes the full analysis details to keep list responses fast.
    Includes just the risk level and score as summary fields.
    """

    # Pull risk and score directly from the related analysis if it exists
    risk = serializers.SerializerMethodField()
    score = serializers.SerializerMethodField()

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
            "created_at",
        ]

    def get_risk(self, obj) -> str | None:
        """Returns the risk level from the analysis result, or None if not yet analysed."""
        if hasattr(obj, "analysis"):
            return obj.analysis.risk
        return None

    def get_score(self, obj) -> int | None:
        """Returns the tamper score from the analysis result, or None if not yet analysed."""
        if hasattr(obj, "analysis"):
            return obj.analysis.score
        return None