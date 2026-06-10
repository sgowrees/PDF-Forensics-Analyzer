import re
import unicodedata
from datetime import datetime

import fitz

from .utils import bbox_overlap, block_is_form_content, iter_pages, module_result, truncate

SUSPICIOUS_TOOLS = (
    "smallpdf", "ilovepdf", "sejda", "pdfcandy", "pdf24", "sodapdf",
    "pdffiller", "inkscape", "gimp", "photoshop", "online2pdf",
)
INVISIBLE_WS = "\u200b\u200c\u200d\u00a0\u2060\ufeff"

MALICIOUS_PATTERNS = {
    r"/JavaScript":    ("Embedded JavaScript execution context", 35),
    r"/JS":            ("Embedded short-form JS element", 30),
    r"/OpenAction":    ("Automatic execution trigger on file open", 40),
    r"/AA":            ("Additional Action trigger (mouse-over/page-view exploit vector)", 30),
    r"/Launch":        ("Attempts to execute an external application/command", 50),
    r"/EmbeddedFiles": ("Hidden embedded files or binary payload attachments", 45),
    r"/XFA":           ("XML Forms Architecture (highly prone to structural obfuscation)", 20),
}


# ---------------------------------------------------------------------------
# METADATA
# ---------------------------------------------------------------------------

def check_metadata(pdf_path: str) -> dict:
    doc = fitz.open(pdf_path)
    meta = doc.metadata
    doc.close()
    issues, score = [], 0
    combined = f"{meta.get('creator', '')} {meta.get('producer', '')}".lower()
    if any(t in combined for t in SUSPICIOUS_TOOLS):
        issues.append("PDF metadata lists a known online editing tool")
        score += 5
    if not any(meta.get(k) for k in ("creator", "producer", "author", "creationDate")):
        issues.append("PDF has no creator/producer metadata")
        score += 3
    created, modified = meta.get("creationDate"), meta.get("modDate")
    if created and modified and created != modified:
        c, m = _pdf_date(created), _pdf_date(modified)
        if c and m and m > c:
            issues.append(
                f"PDF modified after creation ({c.date()} → {m.date()}, "
                f"{(m - c).days} day(s))"
            )
            score += 2
    return module_result(issues, score, cap=10, raw=meta)


# ---------------------------------------------------------------------------
# LAYOUT — only flags issues NEW in upload vs baseline
# ---------------------------------------------------------------------------

def check_layout(extracted: dict, baseline: dict | None = None) -> dict:
    """
    Checks for layout anomalies that exist in the UPLOAD but NOT the baseline.

    The key fix: every check runs on both upload and baseline.
    Only differences are reported. If the baseline has the same gap,
    overlap, or misalignment, it is normal for that document — not a finding.

    Args:
        extracted: extractor output for the upload.
        baseline:  extractor output for the baseline (or None).
    """
    issues, score = [], 0

    upload_pages   = extracted.get("pages", [])
    baseline_pages = (baseline or {}).get("pages", [])

    for idx, page in enumerate(upload_pages):
        n             = idx + 1
        upload_blocks = page.get("text_blocks", [])
        base_blocks   = baseline_pages[idx].get("text_blocks", []) if idx < len(baseline_pages) else []

        if len(upload_blocks) < 2:
            continue

        # --- Overlapping blocks ---
        # Only flag overlaps that are present in upload but NOT in baseline
        up_fields = page.get("form_fields", [])
        base_fields = baseline_pages[idx].get("form_fields", []) if idx < len(baseline_pages) else []
        upload_overlaps = _find_overlaps(upload_blocks, up_fields)
        base_overlaps   = _find_overlaps(base_blocks, base_fields)
        new_overlaps    = [o for o in upload_overlaps if o not in base_overlaps]

        for pair in new_overlaps:
            issues.append(
                f"Page {n}: overlapping text blocks not in baseline — "
                f"'{pair[0]}' / '{pair[1]}' (text pasted over existing content)"
            )
            score += 5

        # --- Irregular vertical gaps ---
        # Only flag gaps that are LARGER than any gap in the baseline
        if len(upload_blocks) >= 5:
            upload_gaps = _get_gaps(upload_blocks)
            base_gaps   = _get_gaps(base_blocks)
            max_base    = max(base_gaps) if base_gaps else None

            ordered = sorted(upload_blocks, key=lambda b: b["y0"])
            for i in range(1, len(ordered)):
                gap = ordered[i]["y0"] - ordered[i - 1]["y1"]
                if gap <= 0:
                    continue

                if max_base is not None:
                    # Only flag if this gap is meaningfully larger than the biggest baseline gap
                    if gap > max_base * 1.3 and gap > 30:
                        issues.append(
                            f"Page {n}: vertical gap ({gap:.0f}pt) larger than "
                            f"max baseline gap ({max_base:.0f}pt) between "
                            f"'{truncate(ordered[i-1].get('text',''))}' and "
                            f"'{truncate(ordered[i].get('text',''))}'"
                        )
                        score += 2
                else:
                    # No baseline — fall back to statistical outlier detection
                    if upload_gaps:
                        med = sorted(upload_gaps)[len(upload_gaps) // 2]
                        if gap > max(med * 4, 30):
                            issues.append(
                                f"Page {n}: unusual vertical gap ({gap:.0f}pt, "
                                f"median {med:.0f}pt) — no baseline to confirm"
                            )
                            score += 2

    return module_result(issues, score, cap=25)


def _find_overlaps(blocks: list, form_fields: list | None = None) -> list[tuple]:
    """Returns list of (text_a, text_b) pairs for overlapping static blocks."""
    fields = form_fields or []
    pairs = []
    for i, a in enumerate(blocks):
        if block_is_form_content(a, fields):
            continue
        for b in blocks[i + 1:]:
            if block_is_form_content(b, fields):
                continue
            if bbox_overlap(a, b):
                ta = truncate(a.get("text", ""))
                tb = truncate(b.get("text", ""))
                pairs.append((min(ta, tb), max(ta, tb)))
    return pairs


def _get_gaps(blocks: list) -> list[float]:
    """Returns list of positive vertical gaps between sorted blocks."""
    if len(blocks) < 2:
        return []
    ordered = sorted(blocks, key=lambda b: b["y0"])
    return [
        ordered[i]["y0"] - ordered[i - 1]["y1"]
        for i in range(1, len(ordered))
        if ordered[i]["y0"] > ordered[i - 1]["y1"]
    ]


# ---------------------------------------------------------------------------
# IMAGES
# ---------------------------------------------------------------------------

def check_images(extracted: dict, baseline: dict | None = None) -> dict:
    issues, score = [], 0
    base_pages = baseline.get("pages", []) if baseline else []
    for idx, page in enumerate(extracted.get("pages", [])):
        n = idx + 1
        images, blocks = page.get("images", []), page.get("text_blocks", [])
        pw, ph = page.get("width", 595), page.get("height", 842)
        base_n = len(base_pages[idx].get("images", [])) if idx < len(base_pages) else 0
        extra = len(images) - base_n
        if extra > 0:
            issues.append(f"Page {n}: {extra} unexpected image(s) vs baseline")
            score += extra * 5
        area = pw * ph or 1
        for img in images:
            if img["width"] * img["height"] / area >= 0.85:
                issues.append(f"Page {n}: near-full-page image (possible screenshot replacement)")
                score += 10
            if img["width"] > pw * 0.6 and 5 < img["height"] < 30:
                issues.append(f"Page {n}: suspicious covering-strip image")
                score += 5
            if (img["x1"] - img["x0"]) < 10 or (img["y1"] - img["y0"]) < 10:
                continue
            for block in blocks:
                if bbox_overlap(img, block):
                    issues.append(
                        f"Page {n}: image overlaps text '{truncate(block.get('text', ''))}'"
                    )
                    score += 8
                    break
    return module_result(issues, score, cap=20)


# ---------------------------------------------------------------------------
# TEXT — only flags anomalies NEW in upload vs baseline
# ---------------------------------------------------------------------------

def check_text(extracted: dict, baseline: dict | None = None) -> dict:
    """
    Checks for text anomalies that exist in the UPLOAD but NOT the baseline.

    The key fix: we measure the same metrics on both upload and baseline,
    then only report the DIFFERENCE. If the baseline already has 6 single-char
    blocks, those are normal for this document — only extras are flagged.

    Args:
        extracted: extractor output for the upload.
        baseline:  extractor output for the baseline (or None).
    """
    issues, score = [], 0

    upload_pages   = extracted.get("pages", [])
    baseline_pages = (baseline or {}).get("pages", [])

    for idx, page in enumerate(upload_pages):
        n             = idx + 1
        upload_blocks = page.get("text_blocks", [])
        base_blocks   = baseline_pages[idx].get("text_blocks", []) if idx < len(baseline_pages) else []

        # --- Fragmentation ---
        upload_max = _max_consecutive_singles(upload_blocks)
        base_max   = _max_consecutive_singles(base_blocks)
        extra      = upload_max - base_max

        # Only flag if upload has ≥5 MORE single-char blocks than baseline
        if upload_max >= 5 and extra >= 5:
            issues.append(
                f"Page {n}: text fragmentation — {upload_max} consecutive "
                f"single-char blocks vs {base_max} in baseline "
                f"(+{extra} extra, likely manual character editing)"
            )
            score += 5

        # --- Encoding anomalies ---
        upload_bad = _encoding_anomaly_texts(upload_blocks)
        base_bad   = _encoding_anomaly_texts(base_blocks)
        new_bad    = upload_bad - base_bad   # texts in upload but not baseline

        for sample in new_bad:
            issues.append(f"Page {n}: encoding anomaly not in baseline — '{sample}'")
        if new_bad:
            score += 5

        # --- Invisible whitespace ---
        upload_ws = _invisible_whitespace_chars(upload_blocks)
        base_ws   = _invisible_whitespace_chars(base_blocks)
        new_ws    = upload_ws - base_ws   # chars in upload but not baseline

        for char_name in new_ws:
            issues.append(
                f"Page {n}: invisible character not in baseline — {char_name} "
                "(can be used to visually pad values)"
            )
        if new_ws:
            score += 3

    return module_result(issues, score, cap=15)


def _max_consecutive_singles(blocks: list) -> int:
    """Returns the maximum run of consecutive single-character text blocks."""
    max_run = current = 0
    for b in blocks:
        t = b.get("text", "").strip()
        if len(t) == 1:
            current += 1
            max_run  = max(max_run, current)
        else:
            current = 0
    return max_run


def _encoding_anomaly_texts(blocks: list) -> set[str]:
    """Returns set of truncated text snippets that have encoding anomalies."""
    bad = set()
    for b in blocks:
        text = b.get("text", "")
        count = sum(1 for ch in text if unicodedata.category(ch) in ("Cc", "Cs", "Co", "Cn"))
        if count >= 3 and count / max(len(text), 1) > 0.2:
            bad.add(truncate(text))
    return bad


def _invisible_whitespace_chars(blocks: list) -> set[str]:
    """Returns set of invisible whitespace character names found in blocks."""
    found = set()
    for b in blocks:
        text = b.get("text", "")
        for ch in INVISIBLE_WS:
            if ch in text:
                found.add(unicodedata.name(ch, f"U+{ord(ch):04X}"))
    return found


# ---------------------------------------------------------------------------
# SIGNATURES
# ---------------------------------------------------------------------------

def check_signatures(pdf_path: str) -> dict:
    doc = fitz.open(pdf_path)
    issues, score, sigs = [], 0, []
    has_sig, valid = False, None
    for pi in range(len(doc)):
        for annot in doc[pi].annots() or []:
            if annot.type[1].lower() != "widget":
                continue
            ft = getattr(annot, "field_type_string", "").lower()
            if "sig" not in ft and "signature" not in ft:
                continue
            has_sig = True
            obj = doc.xref_object(annot.xref)
            signed = "/V" in obj and "/V null" not in obj
            ok = signed and "/ByteRange" in obj
            sigs.append({"page": pi + 1, "is_signed": signed, "is_valid": ok if signed else None})
            if signed and not ok:
                valid = False
                issues.append(f"Page {pi + 1}: invalid or malformed digital signature")
                score += 40
            elif ok and valid is None:
                valid = True
                score -= 5
    doc.close()
    return module_result(
        issues, score,
        has_signature=has_sig,
        signature_valid=valid,
        signatures=sigs,
    )


# ---------------------------------------------------------------------------
# MALICIOUS
# ---------------------------------------------------------------------------

def check_malicious(pdf_path: str) -> dict:
    """Scans the PDF object structure for exploit vectors and malicious payloads."""
    issues, score = [], 0
    raw_data = {}
    try:
        with open(pdf_path, "rb") as f:
            content = f.read()
    except Exception as e:
        return module_result([f"Failed to read file for structural analysis: {str(e)}"], 50)

    content_str = content.decode("latin-1", errors="ignore")

    for pattern, (description, weight) in MALICIOUS_PATTERNS.items():
        matches = len(re.findall(pattern, content_str))
        if matches > 0:
            issues.append(f"Malicious indicator: {description} (occurrences: {matches})")
            score += weight * min(matches, 3)
            raw_data[pattern.strip("/")] = matches

    return module_result(issues, score, cap=100, raw=raw_data)


# ---------------------------------------------------------------------------
# STRUCTURE (shadow attacks, multiple roots)
# ---------------------------------------------------------------------------

def check_structure(pdf_path: str) -> dict:
    """Detects incremental update shadow attacks and parser-confusion techniques."""
    issues, score = [], 0
    try:
        with open(pdf_path, "rb") as f:
            content = f.read()
    except Exception as e:
        return module_result([f"Failed to read structural binary: {str(e)}"], 50)

    content_str = content.decode("latin-1", errors="ignore")

    eof_markers = len(re.findall(r"%%EOF", content_str))
    if eof_markers > 1:
        issues.append(
            f"Incremental updates detected: {eof_markers} structural versions "
            "(potential Shadow Attack — document may show different content to parser vs viewer)"
        )
        score += (eof_markers - 1) * 15

    roots = len(re.findall(r"/Root\s+\d+\s+\d+\s+R", content_str))
    if roots > 1:
        issues.append(
            f"Multiple document Root definitions ({roots}) — "
            "potential parser evasion (different viewers may render different content)"
        )
        score += 30

    return module_result(issues, score, cap=60, version_count=eof_markers)


# ---------------------------------------------------------------------------
# DATE HELPER
# ---------------------------------------------------------------------------

def _pdf_date(s: str) -> datetime | None:
    if not s:
        return None
    clean = s[2:] if s.startswith("D:") else s
    clean = clean.split("+")[0].split("-")[0].split("Z")[0].replace("'", "")
    for fmt in ("%Y%m%d%H%M%S", "%Y%m%d%H%M", "%Y%m%d", "%Y%m"):
        try:
            return datetime.strptime(clean[: len(fmt)], fmt)
        except ValueError:
            continue
    return None

