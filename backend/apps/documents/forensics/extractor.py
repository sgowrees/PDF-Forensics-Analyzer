"""Extract PDF structure (text, images, form fields) via PyMuPDF."""

import fitz

from .utils import rect_overlap_ratio

FILLABLE = {
    fitz.PDF_WIDGET_TYPE_TEXT,
    fitz.PDF_WIDGET_TYPE_COMBOBOX,
    fitz.PDF_WIDGET_TYPE_LISTBOX,
    fitz.PDF_WIDGET_TYPE_CHECKBOX,
    fitz.PDF_WIDGET_TYPE_RADIOBUTTON,
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
    result["fonts"] = sorted(result["fonts"])
    return result


def _extract_page(page: fitz.Page) -> dict:
    w, h = page.rect.width, page.rect.height
    text_blocks, raw_parts, fonts = [], [], set()

    for block in page.get_text("dict").get("blocks", []):
        if block.get("type") != 0:
            continue
        parts = []
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                t = span.get("text", "").strip()
                if t:
                    parts.append(t)
                    fonts.add(span.get("font", "unknown"))
        text = " ".join(parts).strip()
        if not text:
            continue
        bbox = block.get("bbox", (0, 0, 0, 0))
        text_blocks.append({
            "text": text,
            "x0": bbox[0], "y0": bbox[1], "x1": bbox[2], "y1": bbox[3],
            "width": bbox[2] - bbox[0], "height": bbox[3] - bbox[1],
        })
        raw_parts.append(text)

    form_fields = _form_fields(page)
    for block in text_blocks:
        for field in form_fields:
            if field.get("is_fillable") and rect_overlap_ratio(block, field) >= 0.25:
                block["is_widget"] = True
                block["widget_name"] = field.get("name", "")
                break

    images = []
    for xref, *_ in page.get_images(full=True):
        for rect in page.get_image_rects(xref):
            images.append({
                "xref": xref, "width": rect.width, "height": rect.height,
                "x0": rect.x0, "y0": rect.y0, "x1": rect.x1, "y1": rect.y1,
            })

    return {
        "width": w, "height": h,
        "text_blocks": text_blocks,
        "form_fields": form_fields,
        "images": images,
        "raw_text": " ".join(raw_parts),
        "fonts": fonts,
    }


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
            "name": w.field_name or "",
            "value": w.field_value if w.field_value is not None else "",
            "field_type": ft,
            "is_fillable": ft in FILLABLE,
            "x0": r.x0, "y0": r.y0, "x1": r.x1, "y1": r.y1,
        })
    return fields
