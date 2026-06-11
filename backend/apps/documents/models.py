"""Models — file is never persisted to disk."""

import uuid

from django.db import models


class Document(models.Model):

    class DocumentType(models.TextChoices):
        DOCUMENT = "document", "Document"
        UNKNOWN  = "unknown",  "Unknown"

    class AnalysisStatus(models.TextChoices):
        PENDING    = "pending",    "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETE   = "complete",   "Complete"
        FAILED     = "failed",     "Failed"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    original_filename = models.CharField(max_length=255)
    doc_type = models.CharField(
        max_length=20,
        choices=DocumentType.choices,
        default=DocumentType.UNKNOWN,
    )
    issuer      = models.CharField(max_length=255, blank=True, default="")
    issuer_slug = models.CharField(max_length=100, blank=True, default="")
    status      = models.CharField(
        max_length=20,
        choices=AnalysisStatus.choices,
        default=AnalysisStatus.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering      = ["-created_at"]
        verbose_name  = "Document"
        verbose_name_plural = "Documents"

    def __str__(self):
        return f"{self.original_filename} ({self.doc_type}) [{self.status}]"


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