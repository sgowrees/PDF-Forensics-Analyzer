import uuid
from django.db import models

from apps.documents.storage import baseline_storage



class Document(models.Model):

    class DocumentType(models.TextChoices):
        DOCUMENT = "document", "Document"
        UNKNOWN = "unknown", "Unknown"

    class AnalysisStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETE = "complete", "Complete"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    owner = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="documents",
    )

    original_filename = models.CharField(max_length=255)

    doc_type = models.CharField(
        max_length=20,
        choices=DocumentType.choices,
        default=DocumentType.UNKNOWN,
    )

    issuer = models.CharField(max_length=255, blank=True, default="")
    issuer_slug = models.CharField(max_length=100, blank=True, default="")

    status = models.CharField(
        max_length=20,
        choices=AnalysisStatus.choices,
        default=AnalysisStatus.PENDING,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
class AnalysisResult(models.Model):

    class RiskLevel(models.TextChoices):
        LOW    = "LOW",    "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH   = "HIGH",   "High"

    document = models.OneToOneField(
        Document,
        on_delete=models.CASCADE,
        related_name="analysis",
    )
    score                    = models.IntegerField()
    risk                     = models.CharField(max_length=10, choices=RiskLevel.choices)
    baseline_available       = models.BooleanField(default=False)
    reasons                  = models.JSONField(default=list)
    score_breakdown          = models.JSONField(default=dict)
    classification_confidence = models.FloatField(default=0.0)
    created_at               = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = "Analysis Result"
        verbose_name_plural = "Analysis Results"

    def __str__(self):
        return f"Analysis for {self.document.original_filename}: {self.risk} ({self.score})"
    


class TemplateDocument(models.Model):
    file = models.FileField(storage=baseline_storage, upload_to="")
    name = models.CharField(max_length=255, blank=True)
    uploaded_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_templates",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name or self.file.name

    def delete(self, *args, **kwargs):
        if self.file:
            self.file.delete(save=False)
        super().delete(*args, **kwargs)