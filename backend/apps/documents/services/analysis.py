"""Document upload and forensic analysis orchestration."""

from __future__ import annotations

from typing import Any

from django.core.files.uploadedfile import UploadedFile

from apps.documents.forensics import analyze
from apps.documents.models import AnalysisResult, Document


class AnalysisService:
    """Coordinates PDF persistence, forensics pipeline, and API payloads."""

    @staticmethod
    def create_from_upload(uploaded_file: UploadedFile) -> Document:
        document = Document(
            original_filename=uploaded_file.name,
            status=Document.AnalysisStatus.PENDING,
        )
        document.file = uploaded_file
        document.save()
        return document

    @classmethod
    def analyze_document(cls, document: Document) -> dict[str, Any]:
        document.status = Document.AnalysisStatus.PROCESSING
        document.save(update_fields=["status", "updated_at"])

        report = analyze(document.file_path)
        cls._apply_report(document, report)
        return report

    @staticmethod
    def to_response(document: Document, report: dict[str, Any]) -> dict[str, Any]:
        return {
            "document_id": str(document.id),
            "status": document.status,
            "filename": document.original_filename,
            "doc_type": report.get("doc_type", "unknown"),
            "issuer": report.get("issuer", "unknown"),
            "issuer_slug": report.get("issuer_slug", "unknown"),
            "score": report["score"],
            "risk": report["risk"],
            "reasons": report.get("reasons", []),
            "score_breakdown": report.get("breakdown", {}),
            "baseline_available": report.get("baseline_available", False),
            "baseline_pdf_path": report.get("baseline_pdf_path"),
            "classification_confidence": round(
                report.get("classification_confidence", 0.0), 3
            ),
        }

    @classmethod
    def _apply_report(cls, document: Document, report: dict[str, Any]) -> None:
        document.doc_type = cls._map_doc_type(report.get("doc_type", "unknown"))
        document.issuer = report.get("issuer", "")
        document.issuer_slug = report.get("issuer_slug", "")
        document.status = Document.AnalysisStatus.COMPLETE
        document.save(
            update_fields=["doc_type", "issuer", "issuer_slug", "status", "updated_at"]
        )

        AnalysisResult.objects.update_or_create(
            document=document,
            defaults={
                "score": report["score"],
                "risk": report["risk"],
                "baseline_available": report.get("baseline_available", False),
                "reasons": report.get("reasons", []),
                "score_breakdown": report.get("breakdown", {}),
                "classification_confidence": report.get("classification_confidence", 0.0),
            },
        )

    @staticmethod
    def _map_doc_type(doc_type: str) -> str:
        allowed = {choice.value for choice in Document.DocumentType}
        return doc_type if doc_type in allowed else Document.DocumentType.UNKNOWN
