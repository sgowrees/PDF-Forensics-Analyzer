"""Normalised forensics report shape for API and CLI consumers."""

from __future__ import annotations

from typing import Any


def build_report(
    *,
    score: int,
    risk: str,
    reasons: list[str],
    breakdown: dict[str, int],
    doc_type: str,
    issuer: str,
    issuer_slug: str,
    classification_confidence: float,
    baseline_available: bool,
    baseline_pdf_path: str | None,
    pdf_path: str,
) -> dict[str, Any]:
    return {
        "score": score,
        "risk": risk,
        "reasons": reasons,
        "breakdown": breakdown,
        "doc_type": doc_type,
        "issuer": issuer,
        "issuer_slug": issuer_slug,
        "classification_confidence": classification_confidence,
        "baseline_available": baseline_available,
        "baseline_pdf_path": baseline_pdf_path,
        "pdf_path": pdf_path,
    }


def fail_report(pdf_path: str, error: str) -> dict[str, Any]:
    return build_report(
        score=100,
        risk="HIGH",
        reasons=[f"PDF could not be read: {error}"],
        breakdown={},
        doc_type="unknown",
        issuer="unknown",
        issuer_slug="unknown",
        classification_confidence=0.0,
        baseline_available=False,
        baseline_pdf_path=None,
        pdf_path=pdf_path,
    )
