"""Locate and load trusted baseline PDFs."""

from pathlib import Path

from .classifier import classify_document
from .extractor import extract_pdf
from .utils import body_text_key, text_similarity

TEMPLATES = Path(__file__).resolve().parent.parent.parent.parent / "templates"
BASELINES_DOC = TEMPLATES / "baselines" / "documents"
TRAVEL_BASELINE = "Travel_Authorization_Request_Form_EN.pdf"

# Upload filename stem (lowercase) -> baseline filename
UPLOAD_BASELINE_MAP = {
    "travel_fa": TRAVEL_BASELINE,
    "travel_authorization_request_form_en (1)": TRAVEL_BASELINE,
}

TYPE_FOLDERS = {
    "invoice": "invoices",
    "bank_statement": "bank_statements",
    "travel_authorization": "documents",
    "document": "documents",
}

# Only these suffixes mean "tampered copy" — NOT every file with "travel" in the name
TAMPERED_SUFFIXES = ("_fa", "_tampered", "_modified", "_altered", "_copy", "_upload", " (1)")

# Minimum score (0–100) to auto-pick a baseline from templates/baselines/documents/
MIN_CATALOG_MATCH_SCORE = 20.0


def load_baseline(doc_type, issuer, upload_path=None, baseline_path=None, extracted=None):
    upload = Path(upload_path).resolve() if upload_path else None
    path = None

    if baseline_path:
        path = Path(baseline_path).resolve()
        if not path.exists():
            raise RuntimeError(f"Baseline not found: {path}")
    elif upload is not None:
        path = _baseline_for_upload(upload)
        if path is None and extracted is not None:
            path = _best_from_catalog(upload, extracted, doc_type, issuer)
        if path is None:
            path = _by_type(doc_type, issuer)
    else:
        path = _by_type(doc_type, issuer)

    if path is None:
        return None

    if upload and not baseline_path and path.resolve() == upload.resolve():
        return None

    data = extract_pdf(str(path))
    data["baseline_pdf_path"] = str(path.resolve())
    return data


def _baseline_for_upload(upload: Path) -> Path | None:
    """Map known tampered uploads to a trusted baseline by filename."""
    if not BASELINES_DOC.exists():
        return None

    stem = upload.stem.lower()
    mapped = UPLOAD_BASELINE_MAP.get(stem)
    if mapped:
        candidate = BASELINES_DOC / mapped
        if candidate.exists() and candidate.resolve() != upload.resolve():
            return candidate.resolve()

    for suffix in TAMPERED_SUFFIXES:
        if stem.endswith(suffix.lower()):
            candidate = BASELINES_DOC / TRAVEL_BASELINE
            if candidate.exists() and candidate.resolve() != upload.resolve():
                return candidate.resolve()

    return None


def _best_from_catalog(upload: Path, extracted: dict, doc_type: str, issuer: str) -> Path | None:
    """Pick the closest baseline in templates/baselines/documents/ for this upload."""
    if not BASELINES_DOC.exists():
        return None

    candidates = [
        p for p in BASELINES_DOC.glob("*.pdf")
        if p.resolve() != upload.resolve()
    ]
    if not candidates:
        return None

    best_path, best_score = None, -1.0
    for candidate in candidates:
        score = _score_baseline_candidate(extracted, candidate, doc_type, issuer)
        if score > best_score:
            best_score, best_path = score, candidate

    if best_path is None or best_score < MIN_CATALOG_MATCH_SCORE:
        return None
    return best_path.resolve()


def _score_baseline_candidate(
    upload_extracted: dict, baseline_path: Path, doc_type: str, issuer: str
) -> float:
    """Score how well a catalog baseline matches the upload (higher is better)."""
    try:
        base_extracted = extract_pdf(str(baseline_path))
    except Exception:
        return -1.0

    base_clf = classify_document(base_extracted)
    score = 0.0

    sim = text_similarity(body_text_key(upload_extracted), body_text_key(base_extracted))
    score += sim * 80.0

    if doc_type != "unknown" and doc_type == base_clf["doc_type"]:
        score += 25.0

    if issuer != "unknown_issuer" and issuer == base_clf["issuer"]:
        score += 15.0

    if upload_extracted.get("page_count") == base_extracted.get("page_count"):
        score += 5.0

    return score


def _by_type(doc_type, issuer) -> Path | None:
    paths = []
    sub = TYPE_FOLDERS.get(doc_type)
    if sub:
        paths += [
            TEMPLATES / sub / f"{issuer}.pdf",
            TEMPLATES / "baselines" / sub / f"{issuer}.pdf",
        ]
    paths += [
        TEMPLATES / "documents" / f"{issuer}.pdf",
        BASELINES_DOC / f"{issuer}.pdf",
    ]
    if doc_type in ("travel_authorization", "document") or issuer == "lao":
        paths.append(BASELINES_DOC / TRAVEL_BASELINE)

    seen = set()
    for p in paths:
        try:
            resolved = p.resolve()
        except OSError:
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        if p.exists():
            return resolved
    return None
