"""Aggregate module scores into final risk report."""

RISK_LOW, RISK_HIGH = 30, 60
MODULES = ("comparison", "signatures", "images", "layout", "text", "metadata")


def calculate_score(module_results: dict) -> dict:
    total, reasons, breakdown = 0, [], {}
    clf = module_results.get("classifier", {})

    for name in MODULES:
        r = module_results.get(name, {})
        delta = r.get("score_delta", 0)
        total += delta
        reasons.extend(r.get("issues", []))
        if name == "comparison":
            reasons.extend(r.get("allowed_changes", []))
        breakdown[name] = delta

    score = max(0, min(100, total))
    risk = "LOW" if score <= RISK_LOW else ("MEDIUM" if score <= RISK_HIGH else "HIGH")

    return {
        "score": score,
        "risk": risk,
        "reasons": reasons,
        "breakdown": breakdown,
        "doc_type": clf.get("doc_type", "unknown"),
        "issuer": clf.get("issuer_display", "unknown"),
        "issuer_slug": clf.get("issuer", "unknown"),
        "classification_confidence": clf.get("confidence", 0.0),
    }
