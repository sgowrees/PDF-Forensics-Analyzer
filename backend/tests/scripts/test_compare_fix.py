import sys
from pathlib import Path

backend = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(backend))

from apps.documents.forensics.analyzer import analyze

base = backend / "templates/baselines/documents/Travel_Authorization_Request_Form_EN.pdf"
tampered = backend / "templates/documents/Travel_Authorization_Request_Form_EN (1).pdf"

for label, path in [("baseline copy", base), ("tampered", tampered)]:
    if not path.exists():
        print(f"SKIP {label}: missing {path}")
        continue
    r = analyze(str(path), baseline_path=str(base))
    print(f"\n=== {label} ===")
    print("score:", r["score"], "risk:", r["risk"])
    print("content_matches:", r.get("content_matches_baseline"))
    print("baseline:", r.get("baseline_pdf_path"))
    print("comparison:", r["breakdown"].get("comparison"))
    print("issues:", len(r["reasons"]))
    for reason in r["reasons"][:8]:
        print(" -", reason)
