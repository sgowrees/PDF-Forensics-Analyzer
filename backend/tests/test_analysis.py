# tests/test_analysis.py
import sys
from pathlib import Path
import pytest

# Ensure the backend directory is in the system path for imports
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Import your real analyzer logic
from apps.documents.forensics.analyzer import analyze

# Define the absolute paths to your real local PDF files
BASELINE_PDF = "/home/sgowrees/Downloads/PDF-Forensics-Analyzer/backend/templates/baselines/documents/file-sample_150kB.pdf"
SAMPLE_PDF = "/home/sgowrees/Downloads/PDF-Forensics-Analyzer/backend/templates/documents/test.pdf"


def test_analyze_with_real_files():
    """Verify the real analyze function runs successfully using physical PDF files."""
    # Ensure the test files actually exist before running the test
    assert Path(SAMPLE_PDF).exists(), f"Sample PDF not found at {SAMPLE_PDF}"
    assert Path(BASELINE_PDF).exists(), f"Baseline PDF not found at {BASELINE_PDF}"

    # Act - Run the actual analysis engine
    report = analyze(
        pdf_path=SAMPLE_PDF,
        baseline_path=BASELINE_PDF
    )

    # Assert - Verify your expected keys exist in the real JSON/dict output
    assert report is not None
    assert isinstance(report, dict)
    
    # Adjust these assertions to match what your real 'analyze' function returns
    # e.g., assert "success" in report or assert report.get("success") is True
    print("\nReal Report Output:", report)
