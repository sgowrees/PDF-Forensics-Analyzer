import re
import unicodedata
from collections import Counter
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

# PyMuPDF span flag bits
_FLAG_BOLD      = 1 << 4   # 16
_FLAG_ITALIC    = 1 << 1   # 2
_FLAG_STRIKEOUT = 1 << 7   # 128
_FLAG_UNDERLINE = 1 << 2   # 4
_FORMATTING_FLAGS = _FLAG_BOLD | _FLAG_ITALIC | _FLAG_STRIKEOUT | _FLAG_UNDERLINE

# Annotation subtypes that indicate hand-editing
_MARKUP_ANNOTS  = {"StrikeOut", "Highlight", "Underline", "Squiggly"}
_DRAWING_ANNOTS = {"Ink", "Line", "Square", "Circle", "Polygon", "PolyLine",
                   "FreeText", "Stamp", "FileAttachment", "Text"}
_ALL_ANNOTS     = _MARKUP_ANNOTS | _DRAWING_ANNOTS


# ---------------------------------------------------------------------------
# HELPERS — read annotations/drawings/spans directly from a PDF path
# ---------------------------------------------------------------------------

def _read_annot_counts(pdf_path: str) -> list[Counter]:
    """
    Returns a list (one Counter per page) mapping annotation subtype → count.
    Reads directly from fitz so it's never stale.
    """
    result = []
    try:
        doc = fitz.open(pdf_path)
        for page in doc:
            c: Counter = Counter()
            try:
                for annot in page.annots() or []:
                    subtype = annot.type[1]
                    if subtype in _ALL_ANNOTS:
                        c[subtype] += 1
            except Exception:
                pass
            result.append(c)
        doc.close()
    except Exception:
        pass
    return result


def _read_drawing_counts(pdf_path: str) -> list[int]:
    """
    Returns a list (one int per page) of non-trivial vector drawing path counts,
    excluding drawings that fall inside form field widget boundaries
    (e.g. checkbox checkmarks, radio-button fills).
    Reads directly from fitz.
    """
    result = []
    try:
        doc = fitz.open(pdf_path)
        for page in doc:
            try:
                # Collect widget rects so we can exclude checkbox/radio drawings
                widget_rects = []
                for w in (page.widgets() or []):
                    try:
                        wr = w.rect
                        if not wr.is_empty:
                            widget_rects.append(wr)
                    except Exception:
                        pass

                count = sum(
                    1 for p in page.get_drawings()
                    if p.get("rect")
                    and p["rect"].width >= 1
                    and p["rect"].height >= 1
                    and not any(p["rect"].intersects(wr) for wr in widget_rects)
                )
            except Exception:
                count = 0
            result.append(count)
        doc.close()
    except Exception:
        pass
    return result


def _read_formatting_from_path(pdf_path: str) -> dict[int, list[dict]]:
    """
    Opens a PDF and returns {page_index: [span_dict, ...]} for every span.
    Called on both upload and baseline so comparison is always apples-to-apples.
    """
    result: dict[int, list[dict]] = {}
    try:
        doc = fitz.open(pdf_path)
        for pi in range(len(doc)):
            spans = []
            for blk in doc[pi].get_text(
                "dict", flags=fitz.TEXT_PRESERVE_WHITESPACE
            ).get("blocks", []):
                if blk.get("type") != 0:
                    continue
                for line in blk.get("lines", []):
                    for span in line.get("spans", []):
                        flags = span.get("flags", 0)
                        text  = span.get("text", "").strip()
                        if not text:
                            continue
                        spans.append({
                            "text":      text,
                            "bold":      bool(flags & _FLAG_BOLD),
                            "italic":    bool(flags & _FLAG_ITALIC),
                            "strikeout": bool(flags & _FLAG_STRIKEOUT),
                            "underline": bool(flags & _FLAG_UNDERLINE),
                            "flags":     flags,
                        })
            result[pi] = spans
        doc.close()
    except Exception:
        pass
    return result


def _formatting_fingerprints(spans: list[dict]) -> set[tuple]:
    """Fingerprint set for spans that carry at least one formatting flag."""
    fps = set()
    for span in spans:
        if any((span["bold"], span["italic"], span["strikeout"], span["underline"])):
            fps.add((
                truncate(span["text"], 60),
                span["bold"],
                span["italic"],
                span["strikeout"],
                span["underline"],
            ))
    return fps


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
# LAYOUT
# ---------------------------------------------------------------------------

def check_layout(extracted: dict, baseline: dict | None = None) -> dict:
    issues, score = [], 0

    upload_pages   = extracted.get("pages", [])
    baseline_pages = (baseline or {}).get("pages", [])

    for idx, page in enumerate(upload_pages):
        n             = idx + 1
        upload_blocks = page.get("text_blocks", [])
        base_blocks   = baseline_pages[idx].get("text_blocks", []) if idx < len(baseline_pages) else []

        if len(upload_blocks) < 2:
            continue

        up_fields   = page.get("form_fields", [])
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
                    if gap > max_base * 1.3 and gap > 30:
                        issues.append(
                            f"Page {n}: vertical gap ({gap:.0f}pt) larger than "
                            f"max baseline gap ({max_base:.0f}pt) between "
                            f"'{truncate(ordered[i-1].get('text',''))}' and "
                            f"'{truncate(ordered[i].get('text',''))}'"
                        )
                        score += 2
                else:
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
    if len(blocks) < 2:
        return []
    ordered = sorted(blocks, key=lambda b: b["y0"])
    return [
        ordered[i]["y0"] - ordered[i - 1]["y1"]
        for i in range(1, len(ordered))
        if ordered[i]["y0"] > ordered[i - 1]["y1"]
    ]


# ---------------------------------------------------------------------------
# IMAGES + ANNOTATIONS + DRAWINGS
# Reads everything directly from fitz for BOTH upload and baseline.
# ---------------------------------------------------------------------------

def check_images(
    extracted: dict,
    baseline: dict | None = None,
    pdf_path: str | None = None,
    baseline_pdf_path: str | None = None,
) -> dict:
    issues, score = [], 0
    base_pages = (baseline or {}).get("pages", [])

    # Pre-read baseline annotations/drawings directly from its PDF.
    # We never trust the stored extracted dict for the baseline because it
    # may be stale or was extracted before these fields were added.
    base_annot_counts: list[Counter] = (
        _read_annot_counts(baseline_pdf_path) if baseline_pdf_path else []
    )
    base_drawing_counts: list[int] = (
        _read_drawing_counts(baseline_pdf_path) if baseline_pdf_path else []
    )

    if not pdf_path:
        # Fallback: extractor data only, no annotation/drawing detection
        upload_pages = extracted.get("pages", [])
        for idx, page in enumerate(upload_pages):
            n      = idx + 1
            images = page.get("images", [])
            base_n = len(base_pages[idx].get("images", [])) if idx < len(base_pages) else 0
            extra  = len(images) - base_n
            if extra > 0:
                issues.append(f"Page {n}: {extra} unexpected image(s) vs baseline")
                score += extra * 5
        return module_result(issues, score, cap=20)

    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        return module_result([f"Failed to open PDF: {e}"], 10)

    upload_pages = extracted.get("pages", [])

    for idx in range(len(doc)):
        page   = doc[idx]
        n      = idx + 1
        pw, ph = page.rect.width, page.rect.height
        area   = pw * ph or 1

        ext_page    = upload_pages[idx] if idx < len(upload_pages) else {}
        base_page   = base_pages[idx]   if idx < len(base_pages)   else {}
        text_blocks = ext_page.get("text_blocks", [])

        # ── Embedded images ─────────────────────────────────────────────────
        images = []
        seen   = set()
        for img_info in page.get_images(full=True):
            xref = img_info[0]
            if xref in seen:
                continue
            seen.add(xref)
            for rect in page.get_image_rects(xref):
                images.append({
                    "x0": rect.x0, "y0": rect.y0,
                    "x1": rect.x1, "y1": rect.y1,
                    "width": rect.width, "height": rect.height,
                })

        base_n = len(base_page.get("images", []))
        extra  = len(images) - base_n
        if extra > 0:
            issues.append(f"Page {n}: {extra} unexpected image(s) vs baseline")
            score += extra * 5

        for img in images:
            iw, ih = img["width"], img["height"]
            if iw * ih / area >= 0.85:
                issues.append(f"Page {n}: near-full-page image (possible screenshot replacement)")
                score += 10
            if iw > pw * 0.6 and 5 < ih < 30:
                issues.append(f"Page {n}: suspicious covering-strip image")
                score += 5
            if iw < 10 or ih < 10:
                continue
            for block in text_blocks:
                if bbox_overlap(img, block):
                    issues.append(
                        f"Page {n}: image overlaps text '{truncate(block.get('text', ''))}'"
                    )
                    score += 8
                    break

        # ── Annotations ──────────────────────────────────────────────────────
        upload_annot_counts: Counter = Counter()
        try:
            for annot in page.annots() or []:
                subtype = annot.type[1]
                if subtype in _ALL_ANNOTS:
                    upload_annot_counts[subtype] += 1
        except Exception:
            pass

        if base_annot_counts:
            base_page_annot_counts: Counter = (
                base_annot_counts[idx] if idx < len(base_annot_counts) else Counter()
            )
        else:
            base_page_annot_counts = Counter(
                a["subtype"] if isinstance(a, dict) else a
                for a in base_page.get("annotations", [])
            )

        for subtype, upload_count in upload_annot_counts.items():
            base_count  = base_page_annot_counts.get(subtype, 0)
            extra_count = upload_count - base_count
            if extra_count <= 0:
                continue
            if subtype in _DRAWING_ANNOTS:
                issues.append(
                    f"Page {n}: {extra_count} new '{subtype}' annotation(s) added (not in baseline)"
                )
                score += extra_count * 6
            elif subtype in _MARKUP_ANNOTS:
                issues.append(
                    f"Page {n}: {extra_count} new '{subtype}' markup annotation(s) (not in baseline)"
                )
                score += extra_count * 4

        # ── Vector drawings / scribbles ──────────────────────────────────────
        # Exclude drawings that overlap form field widgets (checkbox marks,
        # radio-button fills, etc.) so ticking a checkbox is never flagged.
        try:
            widget_rects = []
            for w in (page.widgets() or []):
                try:
                    wr = w.rect
                    if not wr.is_empty:
                        widget_rects.append(wr)
                except Exception:
                    pass

            upload_drawing_count = sum(
                1 for p in page.get_drawings()
                if p.get("rect")
                and p["rect"].width >= 1
                and p["rect"].height >= 1
                and not any(p["rect"].intersects(wr) for wr in widget_rects)
            )
        except Exception:
            upload_drawing_count = 0

        if base_drawing_counts:
            base_drawing_count = (
                base_drawing_counts[idx] if idx < len(base_drawing_counts) else 0
            )
        else:
            base_drawing_count = len(base_page.get("drawings", []))

        extra_drawings = upload_drawing_count - base_drawing_count
        if extra_drawings > 0:
            issues.append(
                f"Page {n}: {extra_drawings} new vector drawing(s)/scribble(s) vs baseline"
            )
            score += extra_drawings * 4

    doc.close()
    return module_result(issues, score, cap=20)


# ---------------------------------------------------------------------------
# TEXT — fragmentation, encoding, invisible chars, span formatting
# Reads formatting directly from fitz for BOTH upload and baseline.
# ---------------------------------------------------------------------------

def check_text(
    extracted: dict,
    baseline: dict | None = None,
    pdf_path: str | None = None,
    baseline_pdf_path: str | None = None,
) -> dict:
    issues, score = [], 0

    upload_pages   = extracted.get("pages", [])
    baseline_pages = (baseline or {}).get("pages", [])

    # Read span-level formatting directly from both PDFs.
    upload_fmt   = _read_formatting_from_path(pdf_path)          if pdf_path          else {}
    baseline_fmt = _read_formatting_from_path(baseline_pdf_path) if baseline_pdf_path else {}

    for idx, page in enumerate(upload_pages):
        n             = idx + 1
        upload_blocks = page.get("text_blocks", [])
        base_blocks   = baseline_pages[idx].get("text_blocks", []) if idx < len(baseline_pages) else []

        # ── Fragmentation ───────────────────────────────────────────────────
        upload_max = _max_consecutive_singles(upload_blocks)
        base_max   = _max_consecutive_singles(base_blocks)
        extra      = upload_max - base_max
        if upload_max >= 5 and extra >= 5:
            issues.append(
                f"Page {n}: text fragmentation — {upload_max} consecutive "
                f"single-char blocks vs {base_max} in baseline "
                f"(+{extra} extra, likely manual character editing)"
            )
            score += 5

        # ── Encoding anomalies ──────────────────────────────────────────────
        upload_bad = _encoding_anomaly_texts(upload_blocks)
        base_bad   = _encoding_anomaly_texts(base_blocks)
        for sample in upload_bad - base_bad:
            issues.append(f"Page {n}: encoding anomaly not in baseline — '{sample}'")
        if upload_bad - base_bad:
            score += 5

        # ── Invisible whitespace ────────────────────────────────────────────
        upload_ws = _invisible_whitespace_chars(upload_blocks)
        base_ws   = _invisible_whitespace_chars(base_blocks)
        for char_name in upload_ws - base_ws:
            issues.append(
                f"Page {n}: invisible character not in baseline — {char_name} "
                "(can be used to visually pad values)"
            )
        if upload_ws - base_ws:
            score += 3

        # ── Span formatting (bold / italic / strikethrough / underline) ─────
        upload_spans   = upload_fmt.get(idx, [])
        baseline_spans = baseline_fmt.get(idx, [])

        if baseline_spans:
            base_fps = _formatting_fingerprints(baseline_spans)
        else:
            base_fps = _formatting_fingerprints_from_blocks(base_blocks)

        for span in upload_spans:
            fp = (
                truncate(span["text"], 60),
                span["bold"],
                span["italic"],
                span["strikeout"],
                span["underline"],
            )
            if fp in base_fps:
                continue
            tags = [k for k in ("bold", "italic", "strikeout", "underline") if span[k]]
            if tags:
                issues.append(
                    f"Page {n}: text '{truncate(span['text'])}' has unexpected "
                    f"formatting ({', '.join(tags)}) not present in baseline"
                )
                score += 4

    return module_result(issues, score, cap=15)


def _formatting_fingerprints_from_blocks(blocks: list) -> set[tuple]:
    """Fallback: build formatting fingerprints from extractor block → span dicts."""
    fps = set()
    for b in blocks:
        for span in b.get("spans", []):
            text = span.get("text", "").strip()
            if not text:
                continue
            fp = (
                truncate(text, 60),
                bool(span.get("bold")),
                bool(span.get("italic")),
                bool(span.get("strikeout")),
                bool(span.get("underline")),
            )
            if any(fp[1:]):
                fps.add(fp)
    return fps


def _max_consecutive_singles(blocks: list) -> int:
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
    bad = set()
    for b in blocks:
        text = b.get("text", "")
        count = sum(1 for ch in text if unicodedata.category(ch) in ("Cc", "Cs", "Co", "Cn"))
        if count >= 3 and count / max(len(text), 1) > 0.2:
            bad.add(truncate(text))
    return bad


def _invisible_whitespace_chars(blocks: list) -> set[str]:
    found = set()
    for b in blocks:
        for ch in INVISIBLE_WS:
            if ch in b.get("text", ""):
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
            obj    = doc.xref_object(annot.xref)
            signed = "/V" in obj and "/V null" not in obj
            ok     = signed and "/ByteRange" in obj
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
    issues, score, raw_data = [], 0, {}
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
# STRUCTURE
# ---------------------------------------------------------------------------

def check_structure(pdf_path: str) -> dict:
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