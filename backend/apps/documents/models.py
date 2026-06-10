import uuid
from django.db import models


def document_upload_path(instance, filename):
    return f"documents/{instance.id}/{filename}"

# Compatibility alias used by existing migrations.
upload_path = document_upload_path


class Document(models.Model):
    

    class DocumentType(models.TextChoices):
        INVOICE = "invoice", "Invoice"
        BANK_STATEMENT = "bank_statement", "Bank Statement"
        PAYSLIP = "payslip", "Payslip"
        CERTIFICATE = "certificate", "Certificate"
        UNKNOWN = "unknown", "Unknown"

    class AnalysisStatus(models.TextChoices):
        PENDING = "pending", "Pending"        # uploaded, not yet analysed
        PROCESSING = "processing", "Processing"  # analysis in progress
        COMPLETE = "complete", "Complete"     # analysis finished successfully
        FAILED = "failed", "Failed"           # analysis encountered an error

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for this document (UUID4)",
    )

    file = models.FileField(
        upload_to=document_upload_path,
        help_text="The uploaded PDF file",
    )

    original_filename = models.CharField(
        max_length=255,
        help_text="The filename as it was when the user uploaded it",
    )

    doc_type = models.CharField(
        max_length=20,
        choices=DocumentType.choices,
        default=DocumentType.UNKNOWN,
        help_text="Detected document type (set after analysis)",
    )

    issuer = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Detected issuer name e.g. 'TD Bank', 'Acme Corp'",
    )

    issuer_slug = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Normalised issuer identifier e.g. 'td_bank', 'acme_corp'",
    )

    status = models.CharField(
        max_length=20,
        choices=AnalysisStatus.choices,
        default=AnalysisStatus.PENDING,
        help_text="Current status of the forensic analysis",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]  
        verbose_name = "Document"
        verbose_name_plural = "Documents"

    def __str__(self):
        return f"{self.original_filename} ({self.doc_type}) [{self.status}]"

    @property
    def file_path(self) -> str:
        """
        Returns the absolute filesystem path to the uploaded PDF.
        Used when passing the file to the forensic analyzer.
        """
        return self.file.path


class AnalysisResult(models.Model):


    class RiskLevel(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"

    document = models.OneToOneField(
        Document,
        on_delete=models.CASCADE,
        related_name="analysis",
        help_text="The document this analysis belongs to",
    )

    score = models.IntegerField(
        help_text="Tamper risk score from 0 (clean) to 100 (definitely tampered)",
    )

    risk = models.CharField(
        max_length=10,
        choices=RiskLevel.choices,
        help_text="Risk level: LOW (0–30), MEDIUM (31–60), HIGH (61–100)",
    )

    baseline_available = models.BooleanField(
        default=False,
        help_text="True if a baseline template was found for this document type/issuer",
    )

    reasons = models.JSONField(
        default=list,
        help_text="List of human-readable reasons contributing to the tamper score",
    )

    score_breakdown = models.JSONField(
        default=dict,
        help_text="Score contribution from each forensic module",
    )

    classification_confidence = models.FloatField(
        default=0.0,
        help_text="Confidence score from the document type classifier (0.0–1.0)",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Analysis Result"
        verbose_name_plural = "Analysis Results"

    def __str__(self):
        return f"Analysis for {self.document.original_filename}: {self.risk} ({self.score})"