"""Baseline comparison: structure, layout, word-level body text, form fields,
annotations, drawings, images, and span-level formatting (strikeout etc.)."""

import difflib
from collections import Counter
from typing import List, Optional, Tuple

from .utils import block_is_form_content, normalise_label, truncate, widget_values

POSITION_TOLERANCE = 20.0
PARAGRAPH_GAP = 18.0
LABEL_MAX_WORDS = 4
CONTEXT_WORDS = 2

# Annotation subtypes — same split as checks.py
_MARKUP_ANNOTS  = {"StrikeOut", "Highlight", "Underline", "Squiggly"}
_DRAWING_ANNOTS = {"Ink", "Line", "Square", "Circle", "Polygon", "PolyLine",
                   "FreeText", "Stamp", "FileAttachment", "Text"}
_ALL_ANNOTS = _MARKUP_ANNOTS | _DRAWING_ANNOTS


def compare(extracted: dict, baseline: dict) -> dict:
    issues, allowed = [], []
    up_pages, base_pages = extracted.get("pages", []), baseline.get("pages", [])
    page_match = extracted.get("page_count", 0) == baseline.get("page_count", 0)

    if not page_match:
        issues.append(
            f"Page count mismatch: baseline {baseline.get('page_count', 0)}, "
            f"upload {extracted.get('page_count', 0)}"
        )

    up_labels   = _field_labels(extracted)
    base_labels = _field_labels(baseline)
    up_fills    = widget_values(extracted)
    # Text that only appears as a form fill is not a removed static label.
    missing = sorted(base_labels - up_labels - up_fills)
    added   = sorted(up_labels - base_labels - up_fills)
    for f in missing:
        issues.append(f"Expected field missing from upload: '{f}'")
    for f in added:
        issues.append(f"Unexpected field added to upload: '{f}'")

    moved, word_score, visual_score = [], 0, 0
    for i in range(min(len(up_pages), len(base_pages))):
        pr = _compare_page(base_pages[i], up_pages[i], i + 1)
        moved.extend(pr["moved"])
        issues.extend(pr["issues"])
        allowed.extend(pr.get("allowed_changes", []))
        word_score   += pr.get("word_score_delta", 0)
        visual_score += pr.get("visual_score_delta", 0)

    score = (
        _structural_score(page_match, missing, added, moved)
        + min(word_score, 40)
        + min(visual_score, 40)
    )
    return {
        "page_count_match": page_match,
        "missing_fields":   missing,
        "added_fields":     added,
        "moved_fields":     moved,
        "issues":           issues,
        "allowed_changes":  allowed,
        "score_delta":      score,
    }


def _field_labels(extracted: dict) -> set[str]:
    """Short static text blocks (<60 chars) — excludes user input inside form fields."""
    labels = set()
    for page in extracted.get("pages", []):
        fields = page.get("form_fields", [])
        for block in page.get("text_blocks", []):
            if block_is_form_content(block, fields):
                continue
            text = block.get("text", "").strip()
            if len(text) >= 60:
                continue
            norm = normalise_label(text)
            if norm:
                labels.add(norm)
    return labels


def _structural_score(ok_pages, missing, added, moved) -> int:
    s = 0 if ok_pages else 40
    s += min(len(missing) * 10, 30)
    s += min(len(added)   * 5,  20)
    s += min(len(moved)   * 5,  20)
    return s


# ---------------------------------------------------------------------------
# Per-page comparison
# ---------------------------------------------------------------------------

def _compare_page(base_page: dict, up_page: dict, page_num: int) -> dict:
    issues, allowed, moved = [], [], []
    visual_score = 0

    up_blocks = [
        b for b in up_page.get("text_blocks", [])
        if b.get("text", "").strip() and not b.get("is_widget")
    ]
    used_up: set[int] = set()

    for bb in base_page.get("text_blocks", []):
        key = bb.get("text", "").strip().lower()
        if not key or bb.get("is_widget"):
            continue
        ub_idx = _nearest_text_block(bb, up_blocks, used_up)
        if ub_idx is None:
            continue
        used_up.add(ub_idx)
        ub = up_blocks[ub_idx]
        xd = abs(bb["x0"] - ub["x0"])
        yd = abs(bb["y0"] - ub["y0"])
        if xd > POSITION_TOLERANCE or yd > POSITION_TOLERANCE:
            moved.append(key[:50])
            issues.append(
                f"Page {page_num}: text block moved '{truncate(key, 40)}' "
                f"(x {xd:.0f}pt, y {yd:.0f}pt)"
            )

    # ── Word-level text diff ─────────────────────────────────────────────────
    wd = _word_diff(
        base_page.get("text_blocks", []),
        up_page.get("text_blocks", []),
        page_num,
        base_page.get("form_fields", []),
        up_page.get("form_fields", []),
    )
    issues.extend(wd["issues"])
    allowed.extend(wd.get("allowed_changes", []))

    # ── Span formatting diff (strikeout, bold, italic, underline) ────────────
    fd = _format_diff(base_page.get("text_blocks", []),
                      up_page.get("text_blocks", []),
                      page_num)
    issues.extend(fd["issues"])
    visual_score += fd["score_delta"]

    # ── Annotation diff ──────────────────────────────────────────────────────
    ad = _annotation_diff(base_page, up_page, page_num)
    issues.extend(ad["issues"])
    visual_score += ad["score_delta"]

    # ── Drawing diff ─────────────────────────────────────────────────────────
    dd = _drawing_diff(base_page, up_page, page_num)
    issues.extend(dd["issues"])
    visual_score += dd["score_delta"]

    # ── Image diff ───────────────────────────────────────────────────────────
    id_ = _image_diff(base_page, up_page, page_num)
    issues.extend(id_["issues"])
    visual_score += id_["score_delta"]

    return {
        "moved":              moved,
        "issues":             issues,
        "allowed_changes":    allowed,
        "word_score_delta":   wd.get("score_delta", 0),
        "visual_score_delta": visual_score,
    }


# ---------------------------------------------------------------------------
# Annotation diff
# ---------------------------------------------------------------------------

def _annotation_diff(base_page: dict, up_page: dict, page_num: int) -> dict:
    """
    Compare annotation counts per subtype between baseline and upload pages.
    Uses the stored extracted dicts — checks.py re-reads from fitz when a
    pdf_path is available; here we work with whatever was extracted.
    """
    issues, score = [], 0

    base_counts: Counter = Counter(
        a["subtype"] if isinstance(a, dict) else str(a)
        for a in base_page.get("annotations", [])
    )
    up_counts: Counter = Counter(
        a["subtype"] if isinstance(a, dict) else str(a)
        for a in up_page.get("annotations", [])
    )

    for subtype in set(up_counts) | set(base_counts):
        extra = up_counts.get(subtype, 0) - base_counts.get(subtype, 0)
        if extra <= 0:
            continue
        if subtype in _DRAWING_ANNOTS:
            issues.append(
                f"Page {page_num}: {extra} new '{subtype}' annotation(s) added"
            )
            score += extra * 6
        elif subtype in _MARKUP_ANNOTS:
            issues.append(
                f"Page {page_num}: {extra} new '{subtype}' markup annotation(s)"
            )
            score += extra * 4

    return {"issues": issues, "score_delta": score}


# ---------------------------------------------------------------------------
# Drawing diff
# ---------------------------------------------------------------------------

def _drawing_diff(base_page: dict, up_page: dict, page_num: int) -> dict:
    """
    Compare vector drawing counts (content-stream paths, not annotations).

    The stored drawing_count / drawings list was produced by extractor.py
    which already filters out drawings that fall inside form field widget
    boundaries (checkbox marks, radio-button fills, etc.).  So this diff
    is automatically clean — no extra filtering needed here.
    """
    issues, score = [], 0

    base_count = base_page.get("drawing_count", len(base_page.get("drawings", [])))
    up_count   = up_page.get("drawing_count",   len(up_page.get("drawings",   [])))

    extra = up_count - base_count
    if extra > 0:
        issues.append(
            f"Page {page_num}: {extra} new vector drawing(s)/scribble(s) vs baseline"
        )
        score += extra * 4

    return {"issues": issues, "score_delta": score}


# ---------------------------------------------------------------------------
# Image diff
# ---------------------------------------------------------------------------

def _image_diff(base_page: dict, up_page: dict, page_num: int) -> dict:
    """Compare embedded image counts and flag suspicious geometry."""
    issues, score = [], 0

    base_count = base_page.get("image_count", len(base_page.get("images", [])))
    up_images  = up_page.get("images", [])
    up_count   = up_page.get("image_count", len(up_images))

    extra = up_count - base_count
    if extra > 0:
        issues.append(f"Page {page_num}: {extra} unexpected image(s) vs baseline")
        score += extra * 5

    # Geometry checks on every upload image regardless of baseline delta
    pw = up_page.get("width", 1)
    ph = up_page.get("height", 1)
    area = pw * ph or 1
    text_blocks = up_page.get("text_blocks", [])

    for img in up_images:
        iw, ih = img.get("width", 0), img.get("height", 0)
        if iw * ih / area >= 0.85:
            issues.append(
                f"Page {page_num}: near-full-page image "
                "(possible screenshot/content replacement)"
            )
            score += 10
        if iw > pw * 0.6 and 5 < ih < 30:
            issues.append(f"Page {page_num}: suspicious covering-strip image")
            score += 5
        if iw < 10 or ih < 10:
            continue
        for block in text_blocks:
            if _bbox_overlap(img, block):
                issues.append(
                    f"Page {page_num}: image overlaps text "
                    f"'{truncate(block.get('text', ''))}'"
                )
                score += 8
                break

    return {"issues": issues, "score_delta": score}


def _bbox_overlap(a: dict, b: dict) -> bool:
    return not (
        a["x1"] <= b["x0"] or b["x1"] <= a["x0"]
        or a["y1"] <= b["y0"] or b["y1"] <= a["y0"]
    )


# ---------------------------------------------------------------------------
# Span formatting diff (strikeout, bold, italic, underline)
# ---------------------------------------------------------------------------

def _format_diff(base_blocks: list, up_blocks: list, page_num: int) -> dict:
    """
    Compares span-level formatting between baseline and upload using the
    'spans' lists stored by the extractor on each text block.

    A formatting fingerprint is (truncated_text, bold, italic, strikeout, underline).
    Any fingerprint present in upload but absent from baseline is flagged.
    """
    issues, score = [], 0

    base_fps = _span_fingerprints(base_blocks)
    up_fps   = _span_fingerprints(up_blocks)

    for fp in up_fps - base_fps:
        text, bold, italic, strikeout, underline = fp
        tags = [
            name for name, flag in (
                ("bold",      bold),
                ("italic",    italic),
                ("strikeout", strikeout),
                ("underline", underline),
            )
            if flag
        ]
        if tags:
            issues.append(
                f"Page {page_num}: text '{text}' has unexpected "
                f"formatting ({', '.join(tags)}) not in baseline"
            )
            score += 4

    return {"issues": issues, "score_delta": score}


def _span_fingerprints(blocks: list) -> set[tuple]:
    """Return a set of (text, bold, italic, strikeout, underline) for formatted spans."""
    fps = set()
    for block in blocks:
        for span in block.get("spans", []):
            bold      = bool(span.get("bold"))
            italic    = bool(span.get("italic"))
            strikeout = bool(span.get("strikeout"))
            underline = bool(span.get("underline"))
            if not any((bold, italic, strikeout, underline)):
                continue
            text = span.get("text", "").strip()
            if not text:
                continue
            fps.add((truncate(text, 60), bold, italic, strikeout, underline))
    return fps


# ---------------------------------------------------------------------------
# Word diff
# ---------------------------------------------------------------------------

def _word_diff(base_blocks, up_blocks, page_num, base_fields=None, up_fields=None) -> dict:
    issues, allowed, changes = [], [], []
    score = 0
    allowed.extend(_form_field_notes(base_fields or [], up_fields or [], page_num))

    base_paras = _paragraphs(base_blocks)
    up_paras   = _paragraphs(up_blocks)
    if not base_paras and not up_paras:
        return {"issues": [], "allowed_changes": allowed, "score_delta": 0, "changes": []}

    for idx, bp, up in _align_paragraphs(base_paras, up_paras):
        if bp is None and up:
            w = _tokens(up)
            if w:
                issues.append(
                    f"Page {page_num}, ¶{idx}: new paragraph "
                    f"'{truncate(' '.join(w), 120)}'"
                )
                score += 8 * len(w)
            continue
        if up is None and bp:
            w = _tokens(bp)
            if w:
                issues.append(
                    f"Page {page_num}, ¶{idx}: paragraph removed "
                    f"'{truncate(' '.join(w), 120)}'"
                )
                score += 10 * len(w)
            continue
        bw, uw = _tokens(bp), _tokens(up)
        if bw == uw:
            continue
        for ch in _parse_diff(list(difflib.ndiff(bw, uw))):
            phrase = " ".join(ch["words"])
            before = " ".join(ch["before"])
            after  = " ".join(ch["after"])
            kind   = ch["type"]
            if kind == "inserted":
                msg = f"Page {page_num}, ¶{idx}: extra word(s) in document text: '{phrase}'"
                pts = 8 * len(ch["words"])
            elif kind == "deleted":
                msg = f"Page {page_num}, ¶{idx}: word(s) removed from document text: '{phrase}'"
                pts = 10 * len(ch["words"])
            else:
                orig = " ".join(ch.get("original_words", []))
                msg  = f"Page {page_num}, ¶{idx}: document text changed: '{orig}' → '{phrase}'"
                pts  = 12 * len(ch["words"])
            if before:
                msg += f" — after '{before}'"
            if after:
                msg += f" before '{after}'"
            issues.append(msg)
            score += pts
            changes.append(ch)

    return {
        "issues":          issues,
        "allowed_changes": allowed,
        "score_delta":     min(score, 40),
        "changes":         changes,
    }


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _nearest_text_block(base_block: dict, up_blocks: list[dict], used: set[int]) -> int | None:
    key = base_block.get("text", "").strip().lower()
    if not key:
        return None
    bx0, by0 = base_block["x0"], base_block["y0"]
    best_idx, best_dist = None, float("inf")
    for i, ub in enumerate(up_blocks):
        if i in used or ub.get("text", "").strip().lower() != key:
            continue
        dist = (bx0 - ub["x0"]) ** 2 + (by0 - ub["y0"]) ** 2
        if dist < best_dist:
            best_dist, best_idx = dist, i
    return best_idx


def _form_field_notes(base_fields, up_fields, page_num) -> list[str]:
    notes  = []
    up_map = {f["name"]: f for f in up_fields if f.get("name")}
    seen   = set()
    for bf in base_fields:
        name = bf.get("name", "")
        if not name or name in seen or not bf.get("is_fillable", True):
            continue
        seen.add(name)
        uf = up_map.get(name)
        if not uf:
            continue
        bv = str(bf.get("value", "")).strip()
        uv = str(uf.get("value", "")).strip()
        if bv == uv:
            continue
        label = name.replace("_", " ") or "field"
        if uv:
            notes.append(
                f"Page {page_num}: Form field '{label}' filled with "
                f"'{truncate(uv)}' (OK — text box)"
            )
        else:
            notes.append(f"Page {page_num}: Form field '{label}' cleared (OK — text box)")
    for name, uf in up_map.items():
        if name in seen or not uf.get("is_fillable", True):
            continue
        uv = str(uf.get("value", "")).strip()
        if uv:
            label = name.replace("_", " ") or "field"
            notes.append(
                f"Page {page_num}: Form field '{label}' filled with "
                f"'{truncate(uv)}' (OK — text box)"
            )
    return notes


def _is_label(text: str) -> bool:
    words = text.split()
    if len(words) > LABEL_MAX_WORDS:
        return False
    if text.endswith(":"):
        return True
    if len(words) <= 2 and text.isupper():
        return True
    return False


def _paragraphs(blocks: list[dict]) -> list[str]:
    body = []
    for b in blocks:
        t = b.get("text", "").strip()
        if not t or b.get("is_widget") or _is_label(t):
            continue
        body.append({"text": t, "y0": b["y0"], "y1": b["y1"], "x0": b["x0"]})
    if not body:
        return []
    body.sort(key=lambda x: (x["y0"], x["x0"]))
    out, parts, prev = [], [body[0]["text"]], body[0]
    for b in body[1:]:
        if b["y0"] - prev["y1"] <= PARAGRAPH_GAP:
            parts.append(b["text"])
        else:
            out.append(" ".join(parts))
            parts = [b["text"]]
        prev = b
    out.append(" ".join(parts))
    return out


def _align_paragraphs(
    base: List[str], up: List[str]
) -> List[Tuple[int, Optional[str], Optional[str]]]:
    if not base:
        return [(i, None, p) for i, p in enumerate(up, 1)]
    if not up:
        return [(i, p, None) for i, p in enumerate(base, 1)]

    used, aligned, n = set(), [], 0
    for bp in base:
        key = " ".join(_tokens(bp))
        best_j, best_r = None, 0.55
        for j, up_p in enumerate(up):
            if j in used:
                continue
            r = difflib.SequenceMatcher(
                None, key, " ".join(_tokens(up_p)), autojunk=False
            ).ratio()
            if r > best_r:
                best_r, best_j = r, j
        n += 1
        if best_j is not None:
            used.add(best_j)
            aligned.append((n, bp, up[best_j]))
        else:
            aligned.append((n, bp, None))
    for j, up_p in enumerate(up):
        if j not in used:
            n += 1
            aligned.append((n, None, up_p))
    return aligned


def _tokens(text: str) -> List[str]:
    out = []
    for tok in text.split():
        c = tok.strip(".,;:!?\"'()[]{}").lower()
        if c:
            out.append(c)
    return out


def _parse_diff(diff: List[str]) -> List[dict]:
    tagged = []
    for e in diff:
        if e.startswith("  "):
            tagged.append(("eq",  e[2:]))
        elif e.startswith("+ "):
            tagged.append(("ins", e[2:]))
        elif e.startswith("- "):
            tagged.append(("del", e[2:]))
    changes, i, n = [], 0, len(tagged)
    while i < n:
        if tagged[i][0] == "eq":
            i += 1
            continue
        dels, ins, j = [], [], i
        while j < n and tagged[j][0] == "del":
            dels.append(tagged[j][1])
            j += 1
        while j < n and tagged[j][0] == "ins":
            ins.append(tagged[j][1])
            j += 1
        before = [
            tagged[k][1]
            for k in range(max(0, i - CONTEXT_WORDS), i)
            if tagged[k][0] == "eq"
        ][-CONTEXT_WORDS:]
        after, k = [], j
        while k < n and len(after) < CONTEXT_WORDS:
            if tagged[k][0] == "eq":
                after.append(tagged[k][1])
            k += 1
        if dels and ins:
            changes.append({
                "type": "substituted", "words": ins,
                "original_words": dels, "before": before, "after": after,
            })
        elif ins:
            changes.append({
                "type": "inserted", "words": ins,
                "original_words": [], "before": before, "after": after,
            })
        elif dels:
            changes.append({
                "type": "deleted", "words": dels,
                "original_words": dels, "before": before, "after": after,
            })
        i = j
    return changes