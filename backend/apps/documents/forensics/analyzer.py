"""Forensics pipeline entry point."""

from pathlib import Path

from .baseline import load_baseline
from .checks import check_images, check_layout, check_metadata, check_signatures, check_text
from .classifier import classify_document
from .compare import compare
from .extractor import extract_pdf
from .report import build_report, fail_report
from .scoring import calculate_score
from .utils import safe_run


def analyze(pdf_path: str, baseline_path: str | None = None) -> dict:
    pdf_path = str(Path(pdf_path).resolve())

    try:
        extracted = extract_pdf(pdf_path)
    except Exception as exc:
        return fail_report(pdf_path, str(exc))

    clf = classify_document(extracted)
    baseline = load_baseline(
        clf["doc_type"],
        clf["issuer"],
        upload_path=pdf_path,
        baseline_path=baseline_path,
        extracted=extracted,
    )
    has_base = baseline is not None
    comparison = (
        compare(extracted, baseline)
        if has_base
        else _no_baseline_comparison(clf["doc_type"], clf["issuer"])
    )

    modules = {
        "comparison": comparison,
        "classifier": clf,
        "metadata": safe_run(lambda: check_metadata(pdf_path), "Metadata"),
        "text": safe_run(lambda: check_text(extracted, baseline), "Text"),
        "layout": safe_run(lambda: check_layout(extracted, baseline), "Layout"),
        "images": safe_run(lambda: check_images(extracted, baseline), "Images"),
        "signatures": safe_run(lambda: check_signatures(pdf_path), "Signatures"),
    }

    scored = calculate_score(modules)
    return build_report(
        score=scored["score"],
        risk=scored["risk"],
        reasons=scored["reasons"],
        breakdown=scored["breakdown"],
        doc_type=scored["doc_type"],
        issuer=scored["issuer"],
        issuer_slug=scored["issuer_slug"],
        classification_confidence=scored["classification_confidence"],
        baseline_available=has_base,
        baseline_pdf_path=baseline.get("baseline_pdf_path") if has_base else None,
        pdf_path=pdf_path,
    )


def _no_baseline_comparison(doc_type: str, issuer: str) -> dict:
    return {
        "page_count_match": None,
        "missing_fields": [],
        "added_fields": [],
        "moved_fields": [],
        "issues": [
            f"No baseline for doc_type='{doc_type}', issuer='{issuer}'. "
            "Add a trusted PDF under templates/baselines/documents/."
        ],
        "allowed_changes": [],
        "score_delta": 0,
    }
