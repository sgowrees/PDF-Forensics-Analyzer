"""
classifier.py
-------------
Determines WHAT TYPE of general document was uploaded (memo, agreement, report, etc.)
and WHO ISSUED IT (Company A, Company B, etc.).

This runs immediately after extraction, before any forensic checks,
because we need both pieces of information to load the right baseline template.

Strategy:
1. Document type  → keyword scanning on the raw text
2. Issuer/company → look for known company names in the text,
                    then fall back to text heuristics (first bold line, header text, title-casing)
"""

import re

# ---------------------------------------------------------------------------
# General Document type keywords
# ---------------------------------------------------------------------------
# Each document type has a list of strong indicator phrases.
# We score each type by how many of its keywords appear in the text.
DOCUMENT_TYPE_KEYWORDS = {
    "legal_agreement": [
        "agreement",
        "contract",
        "terms and conditions",
        "nda",
        "non-disclosure",
        "hereby agree",
        "memorandum of understanding",
        "mou",
        "signatory",
        "parties to this",
    ],
    "internal_report": [
        "report",
        "annual review",
        "summary of operations",
        "quarterly update",
        "project plan",
        "confidential report",
        "analysis",
        "performance indicators",
    ],
    "corporate_memo": [
        "memorandum",
        "memo",
        "to:",
        "from:",
        "date:",
        "subject:",
        "internal correspondence",
        "all staff",
        "for immediate release",
    ],
    "generic_document": [
        "document",
        "overview",
        "information sheet",
        "guidelines",
        "policy",
        "procedures",
        "appendix",
    ],
}

# ---------------------------------------------------------------------------
# Known issuers (Company profiles)
# ---------------------------------------------------------------------------
# We search for these exact strings (case-insensitive) in the document text.
# The key is the normalised issuer slug used to load the baseline JSON.
KNOWN_ISSUERS = {
    "company a": "company_a",
    "company b": "company_b",
    "company c": "company_c",
    "acme corp": "acme_corp",
    "acme corporation": "acme_corp",
    "globex": "globex",
    "initech": "initech",
    "umbrella corporation": "umbrella_corp",
}


def classify_document(extracted: dict) -> dict:
    """
    Classifies an extracted PDF into a document type and issuer company.

    Args:
        extracted: The dict returned by extractor.extract_pdf()

    Returns:
        Dict with:
            - doc_type: generic structural type string
            - issuer:   normalised issuer slug e.g. "company_a", "acme_corp"
            - issuer_display: human-readable name found in the text
            - confidence: 0.0–1.0 rough confidence score
    """
    # FIX: Maintain original casing for heuristic parsing, use clean_text for scanning
    raw_text = extracted.get("raw_text", "")
    clean_text = raw_text.lower()

    doc_type, type_confidence = _detect_document_type(clean_text)
    issuer_slug, issuer_display = _detect_issuer(raw_text, clean_text)

    return {
        "doc_type": doc_type,
        "issuer": issuer_slug,
        "issuer_display": issuer_display,
        "confidence": type_confidence,
    }


def _detect_document_type(clean_text: str) -> tuple[str, float]:
    """
    Scores each document type by counting keyword matches in the raw lowercased text.

    Returns:
        Tuple of (doc_type_string, confidence_float)
    """
    scores = {}

    for doc_type, keywords in DOCUMENT_TYPE_KEYWORDS.items():
        hit_count = sum(1 for kw in keywords if kw in clean_text)
        # Normalise score to 0.0–1.0 based on fraction of keywords matched
        scores[doc_type] = hit_count / len(keywords) if keywords else 0.0

    if not scores:
        return "generic_document", 0.0

    best_type = max(scores, key=lambda t: scores[t])
    best_score = scores[best_type]

    # If the best score is too low, fall back to generic_document
    if best_score < 0.05:  
        return "generic_document", best_score

    return best_type, best_score


def _detect_issuer(raw_text: str, clean_text: str) -> tuple[str, str]:
    """
    Searches the PDF text for any known issuer names.
    Falls back to a dynamic capitalization parser if the entity is brand new.

    Returns:
        Tuple of (issuer_slug, issuer_display_name)
    """
    # --- Step 1: Known issuer lookup ---
    for name, slug in KNOWN_ISSUERS.items():
        if name in clean_text:
            return slug, name.title()

    # --- Step 2: Heuristic fallback (Fixed to read uncased raw_text) ---
    heuristic_name = _extract_company_name_heuristic(raw_text)

    if heuristic_name:
        # Dynamically generate a valid configuration slug for an unknown entity
        slug = re.sub(r"[^a-z0-9]+", "_", heuristic_name.lower()).strip("_")
        return slug, heuristic_name

    return "unknown_issuer", "Unknown Company"


def _extract_company_name_heuristic(raw_text: str) -> str | None:
    """
    Heuristic: scan the first 600 characters of the uncased text for a likely
    company name — 2 to 5 consecutive title-cased words.
    """
    if not raw_text:
        return None

    # Target the beginning header zone where corporate letterheads reside
    header_chunk = raw_text[:600]

    # Pattern: 2–5 words each starting with an uppercase letter
    pattern = r"\b([A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+){1,4})\b"
    matches = re.findall(pattern, header_chunk)

    if matches:
        # Avoid picking up generic single-word header lines like "Date" or "Subject"
        # Return the longest string sequence (most likely to be a full entity name)
        best_match = max(matches, key=len)
        
        # Guard clause: don't match common document structure words as company names
        blacklisted_headers = {"Terms Of", "Subject:", "Memorandum", "Table Of"}
        if any(b in best_match for b in blacklisted_headers):
            return None
            
        return best_match

    return None