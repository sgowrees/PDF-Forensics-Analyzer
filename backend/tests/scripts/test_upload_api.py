import json
import sys
import urllib.request
from pathlib import Path

backend = Path(__file__).resolve().parents[2]
pdf = backend / "templates/documents/test.pdf"
if not pdf.exists():
    pdf = backend / "templates/baselines/documents/file-sample_150kB.pdf"

boundary = "----boundary"
body = (
    f"--{boundary}\r\n"
    f'Content-Disposition: form-data; name="file"; filename="{pdf.name}"\r\n'
    "Content-Type: application/pdf\r\n\r\n"
).encode() + pdf.read_bytes() + f"\r\n--{boundary}--\r\n".encode()

req = urllib.request.Request(
    "http://127.0.0.1:8000/api/documents/upload/",
    data=body,
    method="POST",
    headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
)
try:
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode())
        print("status", resp.status)
        print("risk", data["risk"], "score", data["score"])
        print("baseline", data.get("baseline_pdf_path"))
        print("reasons", len(data["reasons"]))
except urllib.error.HTTPError as exc:
    print("error", exc.code, exc.read().decode())
    sys.exit(1)
