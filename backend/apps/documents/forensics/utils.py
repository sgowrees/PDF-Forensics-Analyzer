"""Shared helpers for forensics modules."""

import difflib
import re
from typing import Callable


def module_result(issues: list, score: int = 0, cap: int | None = None, **extra) -> dict:
    out = {"issues": issues, "score_delta": min(score, cap) if cap is not None else score, **extra}
    return out


def safe_run(fn: Callable, name: str, default: dict | None = None) -> dict:
    try:
        return fn()
    except Exception as e:
        base = default or {"score_delta": 0}
        return {**base, "issues": [f"{name} error: {e}"]}


def bbox_overlap(a: dict, b: dict) -> bool:
    return not (
        a["x1"] <= b["x0"] or b["x1"] <= a["x0"]
        or a["y1"] <= b["y0"] or b["y1"] <= a["y0"]
    )


def rect_overlap_ratio(a: dict, b: dict) -> float:
    ix0, iy0 = max(a["x0"], b["x0"]), max(a["y0"], b["y0"])
    ix1, iy1 = min(a["x1"], b["x1"]), min(a["y1"], b["y1"])
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    inter = (ix1 - ix0) * (iy1 - iy0)
    aa = max((a["x1"] - a["x0"]) * (a["y1"] - a["y0"]), 1e-6)
    ab = max((b["x1"] - b["x0"]) * (b["y1"] - b["y0"]), 1e-6)
    return inter / min(aa, ab)


def normalise_label(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower().rstrip(":.,;")).strip()


def normalise_body(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def text_similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, normalise_body(a), normalise_body(b), autojunk=False).ratio()


def truncate(text: str, n: int = 80) -> str:
    return text if len(text) <= n else text[: n - 3] + "..."


def iter_pages(extracted: dict):
    for i, page in enumerate(extracted.get("pages", [])):
        yield i + 1, page


def all_blocks(extracted: dict) -> list[dict]:
    blocks = []
    for page in extracted.get("pages", []):
        blocks.extend(page.get("text_blocks", []))
    return blocks


def widget_values(extracted: dict) -> set[str]:
    vals = set()
    for page in extracted.get("pages", []):
        for f in page.get("form_fields", []):
            v = normalise_label(str(f.get("value", "")))
            if v:
                vals.add(v)
    return vals


def block_is_form_content(block: dict, form_fields: list) -> bool:
    """True when text belongs inside a fillable field (user input), not static labels."""
    if block.get("is_widget"):
        return True
    text = normalise_label(block.get("text", ""))
    if not text:
        return False
    for field in form_fields:
        if not field.get("is_fillable"):
            continue
        value = normalise_label(str(field.get("value", "")))
        overlaps = rect_overlap_ratio(block, field) >= 0.25
        if not overlaps:
            continue
        if not value or text == value or value in text or text in value:
            return True
    return False


def body_text_key(extracted: dict) -> str:
    """Normalised static body text for quick same-document check."""
    parts = []
    skip = widget_values(extracted)
    for block in all_blocks(extracted):
        if block.get("is_widget"):
            continue
        text = block.get("text", "").strip()
        if not text:
            continue
        norm = normalise_body(text)
        if norm in skip:
            continue
        parts.append(norm)
    return " ".join(parts)


def documents_body_match(a: dict, b: dict, threshold: float = 0.995) -> bool:
    return text_similarity(body_text_key(a), body_text_key(b)) >= threshold
