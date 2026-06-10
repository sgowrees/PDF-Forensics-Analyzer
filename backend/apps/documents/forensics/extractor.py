"""Extract PDF structure (text, images, form fields, annotations, drawings) via PyMuPDF."""

import fitz

from .utils import rect_overlap_ratio

FILLABLE = {
    fitz.PDF_WIDGET_TYPE_TEXT,
    fitz.PDF_WIDGET_TYPE_COMBOBOX,
    fitz.PDF_WIDGET_TYPE_LISTBOX,
    fitz.PDF_WIDGET_TYPE_CHECKBOX,
    fitz.PDF_WIDGET_TYPE_RADIOBUTTON,
}

# Span flag bits (PyMuPDF)
_FLAG_SUPERSCRIPT = 1 << 0   # 1
_FLAG_ITALIC      = 1 << 1   # 2
_FLAG_BOLD        = 1 << 4   # 16
_FLAG_STRIKEOUT   = 1 << 7   # 128
_FLAG_UNDERLINE   = 1 << 2   # 4

# Annotation subtypes we care about
_ANNOTATION_TYPES = {
    "Ink", "Line", "Square", "Circle", "Polygon", "PolyLine",
    "Highlight", "Underline", "StrikeOut", "Squiggly",
    "Stamp", "FreeText", "FileAttachment", "Text",
}


def extract_pdf(pdf_path: str) -> dict:
    doc = fitz.open(pdf_path)
    result = {"page_count": len(doc), "pages": [], "raw_text": "", "fonts": set()}
    for i in range(len(doc)):
        page_data = _extract_page(doc[i])
        result["pages"].append(page_data)
        result["raw_text"] += page_data["raw_text"] + "\n"
        result["fonts"].update(page_data["fonts"])
    doc.close()
    # Always serialise fonts to a sorted list — sets are not JSON-serialisable
    # and cause silent failures when the extracted dict is cached or compared.
    result["fonts"] = sorted(result["fonts"])
    return result


def _extract_page(page: fitz.Page) -> dict:
    w, h = page.rect.width, page.rect.height
    text_blocks, raw_parts, fonts = [], [], set()

    for block in page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE).get("blocks", []):
        if block.get("type") != 0:
            continue
        parts = []
        spans_data = []
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                t = span.get("text", "").strip()
                if t:
                    parts.append(t)
                    font = span.get("font", "unknown")
                    fonts.add(font)
                    flags = span.get("flags", 0)
                    spans_data.append({
                        "text":      t,
                        "font":      font,
                        "size":      round(span.get("size", 0), 1),
                        "flags":     flags,
                        "bold":         bool(flags & _FLAG_BOLD),
                        "italic":       bool(flags & _FLAG_ITALIC),
                        "strikeout":    bool(flags & _FLAG_STRIKEOUT),
                        "superscript":  bool(flags & _FLAG_SUPERSCRIPT),
                        "underline":    bool(flags & _FLAG_UNDERLINE),
                        "color":        span.get("color", 0),
                    })
        text = " ".join(parts).strip()
        if not text:
            continue
        bbox = block.get("bbox", (0, 0, 0, 0))
        text_blocks.append({
            "text":   text,
            "x0": bbox[0], "y0": bbox[1], "x1": bbox[2], "y1": bbox[3],
            "width":  bbox[2] - bbox[0],
            "height": bbox[3] - bbox[1],
            "spans":  spans_data,
        })
        raw_parts.append(text)

    form_fields = _form_fields(page)
    for block in text_blocks:
        for field in form_fields:
            if field.get("is_fillable") and rect_overlap_ratio(block, field) >= 0.25:
                block["is_widget"] = True
                block["widget_name"] = field.get("name", "")
                break

    images      = _extract_images(page)
    annotations = _extract_annotations(page)
    drawings    = _extract_drawings(page, form_fields)

    return {
        "width":       w,
        "height":      h,
        "text_blocks": text_blocks,
        "form_fields": form_fields,
        "images":      images,
        "annotations": annotations,
        "drawings":    drawings,
        "annotation_count": len(annotations),
        "drawing_count":    len(drawings),
        "image_count":      len(images),
        "raw_text":    " ".join(raw_parts),
        "fonts":       sorted(fonts),
    }


def _extract_images(page: fitz.Page) -> list[dict]:
    images = []
    seen_xrefs = set()
    for img_info in page.get_images(full=True):
        xref = img_info[0]
        if xref in seen_xrefs:
            continue
        seen_xrefs.add(xref)
        for rect in page.get_image_rects(xref):
            images.append({
                "xref":   xref,
                "width":  rect.width,
                "height": rect.height,
                "x0": rect.x0, "y0": rect.y0,
                "x1": rect.x1, "y1": rect.y1,
            })
    return images


def _extract_annotations(page: fitz.Page) -> list[dict]:
    """
    Extracts non-widget annotations: ink scribbles, lines, stamps,
    highlights, strikethrough marks drawn on top of the page, etc.
    These are completely separate from embedded images and text.
    """
    annotations = []
    try:
        for annot in page.annots() or []:
            subtype = annot.type[1]   # e.g. "Ink", "Line", "StrikeOut"
            if subtype not in _ANNOTATION_TYPES:
                continue
            r = annot.rect
            annotations.append({
                "subtype": subtype,
                "x0": r.x0, "y0": r.y0,
                "x1": r.x1, "y1": r.y1,
                "width":   r.width,
                "height":  r.height,
                "content": annot.info.get("content", ""),
                "author":  annot.info.get("title", ""),
                "color":   annot.colors,
            })
    except Exception:
        pass
    return annotations


def _extract_drawings(page: fitz.Page, form_fields: list[dict] | None = None) -> list[dict]:
    """
    Extracts vector drawings (lines, rectangles, curves) painted directly
    into the page content stream — not annotations, not images.
    Scribbles added by some editors show up here rather than as annotations.

    Drawings that fall inside form field widget boundaries are excluded —
    these are checkbox marks / radio-button fills, not user scribbles.
    """
    drawings = []

    # Build fitz.Rect objects for every widget on this page so we can test
    # intersection cheaply.  We only exclude drawings whose rect is fully
    # contained in (or substantially overlaps) a widget rect.
    widget_rects: list[fitz.Rect] = []
    if form_fields:
        for f in form_fields:
            try:
                wr = fitz.Rect(f["x0"], f["y0"], f["x1"], f["y1"])
                if not wr.is_empty:
                    widget_rects.append(wr)
            except Exception:
                pass

    try:
        for path in page.get_drawings():
            r = path.get("rect")
            if r is None:
                continue
            # Skip hair-thin invisible paths (e.g. layout artifacts)
            if r.width < 1 and r.height < 1:
                continue
            # Skip drawings whose bounding rect intersects a form widget —
            # these are the visual marks rendered when a checkbox/radio is
            # ticked and should never be counted as suspicious scribbles.
            if any(r.intersects(wr) for wr in widget_rects):
                continue
            drawings.append({
                "type":       path.get("type", ""),
                "x0": r.x0, "y0": r.y0,
                "x1": r.x1, "y1": r.y1,
                "width":      r.width,
                "height":     r.height,
                "fill":       path.get("fill"),
                "color":      path.get("color"),
                "line_width": path.get("width", 0),
                "items":      len(path.get("items", [])),
            })
    except Exception:
        pass
    return drawings


def _form_fields(page: fitz.Page) -> list[dict]:
    fields = []
    try:
        widgets = page.widgets() or []
    except Exception:
        return fields
    for w in widgets:
        r = w.rect
        ft = w.field_type
        fields.append({
            "name":        w.field_name or "",
            "value":       w.field_value if w.field_value is not None else "",
            "field_type":  ft,
            "is_fillable": ft in FILLABLE,
            "x0": r.x0, "y0": r.y0, "x1": r.x1, "y1": r.y1,
        })
    return fields