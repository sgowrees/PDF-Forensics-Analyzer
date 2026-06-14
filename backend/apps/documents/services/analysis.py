from __future__ import annotations

import os
import tempfile
from typing import Any

from django.core.files.uploadedfile import UploadedFile

from apps.documents.forensics import analyze
from apps.documents.models import AnalysisResult, Document


class AnalysisService:
    """In-memory forensic pipeline (no file persistence)."""

    @staticmethod
    def create_from_upload(uploaded_file: UploadedFile, owner) -> tuple[Document, bytes]:
        document = Document.objects.create(
            owner=owner,  # 🔥 REQUIRED FIX
            original_filename=uploaded_file.name,
            status=Document.AnalysisStatus.PENDING,
        )

        pdf_bytes = uploaded_file.read()
        return document, pdf_bytes

    @classmethod
    def analyze_document(cls, document: Document, pdf_bytes: bytes) -> dict[str, Any]:
        document.status = Document.AnalysisStatus.PROCESSING
        document.save(update_fields=["status", "updated_at"])

        tmp_path = None

        try:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(pdf_bytes)
                tmp_path = tmp.name

            report = analyze(tmp_path)

            cls._apply_report(document, report)
            return report

        except Exception as exc:
            document.status = Document.AnalysisStatus.FAILED
            document.save(update_fields=["status", "updated_at"])
            raise exc

        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)

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

        document.save(update_fields=[
            "doc_type",
            "issuer",
            "issuer_slug",
            "status",
            "updated_at",
        ])

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
        allowed = {c.value for c in Document.DocumentType}
        return doc_type if doc_type in allowed else Document.DocumentType.UNKNOWN