#!/usr/bin/env python3
"""
Run the PDF forensics analyzer and print JSON output.

Usage:
    python tests/scripts/run_analysis.py uploaded.pdf --pretty
    python tests/scripts/run_analysis.py uploaded.pdf --baseline baseline.pdf --pretty
"""

import argparse
import json
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="Analyze a PDF and output a forensics report"
    )

    parser.add_argument(
        "pdf",
        help="Path to PDF file to analyze",
    )

    parser.add_argument(
        "--baseline",
        help="Path to trusted baseline PDF",
        default=None,
    )

    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )

    args = parser.parse_args()

    backend_dir = Path(__file__).resolve().parent.parent.parent

    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

    try:
        from apps.documents.forensics.analyzer import analyze
    except Exception as exc:
        print(f"Failed to import analyzer: {exc}")
        sys.exit(1)

    pdf_path = Path(args.pdf)
    if not pdf_path.is_absolute():
        pdf_path = (Path.cwd() / pdf_path).resolve()

    baseline_path = None
    if args.baseline:
        baseline_path = Path(args.baseline)
        if not baseline_path.is_absolute():
            baseline_path = (Path.cwd() / baseline_path).resolve()

    try:
        report = analyze(
            str(pdf_path),
            baseline_path=str(baseline_path) if baseline_path else None,
        )
    except Exception as exc:
        print(json.dumps({
            "success": False,
            "error": str(exc)
        }))
        sys.exit(1)

    print(json.dumps(report, indent=2 if args.pretty else None))


if __name__ == "__main__":
    main()
