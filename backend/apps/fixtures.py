"""
conftest.py
-----------
WHAT THIS FILE DOES:
  Defines shared pytest fixtures used by ALL test files in the forensics
  test suite. pytest automatically discovers and loads this file — you
  never import from it directly.

WHAT A FIXTURE IS:
  A fixture is a function that sets up a piece of test infrastructure
  (a fake PDF, a temp directory, sample data) and makes it available
  to any test function that declares it as a parameter.

  Example:
    def test_something(sample_invoice_pdf):
        # sample_invoice_pdf is already a Path to a real PDF on disk
        result = analyze(str(sample_invoice_pdf))
        assert result["risk"] == "LOW"

FIXTURES DEFINED HERE:
  sample_invoice_pdf       — a minimal but real invoice PDF on disk
  sample_bank_statement_pdf — a minimal but real bank statement PDF on disk
  tampered_invoice_pdf     — an invoice with a value substituted
  temp_dir                 — a temporary directory that cleans itself up
  baseline_invoice_pdf     — the trusted baseline for comparison
"""

# pytest — the test framework. Fixtures are decorated with @pytest.fixture.
import pytest

# io — for writing PDFs to in-memory buffers before saving to disk
import io

# tempfile — for creating temp directories that clean up automatically
import tempfile

# shutil — for copying files in fixture setup
import shutil

# pathlib.Path — clean path handling throughout fixtures
from pathlib import Path

# fitz (PyMuPDF) — used to apply tampering in tampered_* fixtures
import fitz

# ReportLab — used to generate real (but fake-content) PDF files
# All fixture PDFs are generated programmatically so tests have no
# external file dependencies.
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib import colors


# ---------------------------------------------------------------------------
# TEMP DIRECTORY FIXTURE
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_dir():
    """
    WHAT THIS FIXTURE DOES:
      Creates a temporary directory for the duration of a single test,
      then deletes it and all its contents when the test finishes.

    USAGE:
      def test_something(temp_dir):
          output = temp_dir / "output.pdf"
          # write to output, test it, temp_dir cleans up automatically

    YIELD FIXTURE:
      Code before yield = setup (runs before the test).
      Code after yield  = teardown (runs after the test, even if test fails).
    """
    # Create a temporary directory using Python's tempfile module
    # mkdtemp() creates the directory and returns its path as a string
    tmp = tempfile.mkdtemp()

    # Convert to Path object for cleaner path operations
    tmp_path = Path(tmp)

    # yield hands control to the test with the temp_dir available
    yield tmp_path

    # After the test finishes (or fails), clean up the temp directory
    # rmtree() deletes the directory and everything inside it
    shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# INVOICE PDF FIXTURE
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_invoice_pdf(temp_dir):
    """
    WHAT THIS FIXTURE DOES:
      Generates a minimal but realistic invoice PDF and saves it to
      the temp directory. Returns the Path to the generated file.

    WHY WE GENERATE IT:
      Tests should never depend on external files — if a file moves or
      is deleted, tests break. Generating PDFs programmatically means
      tests are fully self-contained.

    The PDF contains:
      - Standard invoice field labels (Invoice Number, Date, etc.)
      - A line items table
      - A total/subtotal section
      These are the fields the comparator checks for.

    Returns:
      Path to the generated invoice PDF.
    """

    # Build the output path: temp_dir/invoice.pdf
    pdf_path = temp_dir / "invoice.pdf"

    # Create the PDF using ReportLab
    c = rl_canvas.Canvas(str(pdf_path), pagesize=A4)
    page_width, page_height = A4   # 595.28 × 841.89 PDF points

    # --- Header ---
    # Company name at the top
    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(colors.HexColor("#1a3c5e"))
    c.drawString(40, page_height - 50, "Acme Corporation")

    # "INVOICE" label
    c.setFont("Helvetica-Bold", 24)
    c.drawRightString(page_width - 40, page_height - 60, "INVOICE")

    # --- Invoice metadata fields ---
    # These field labels are the ones comparator.py checks for.
    # Their positions must match the baseline to avoid false positives.
    fields = [
        ("Invoice Number:", "INV-10001",          40,  page_height - 110),
        ("Invoice Date:",   "January 15, 2025",   40,  page_height - 126),
        ("Due Date:",       "February 14, 2025",  40,  page_height - 142),
        ("Payment Terms:",  "Net 30",             40,  page_height - 158),
        ("Bill To:",        "Test Customer",       40,  page_height - 200),
    ]

    for label, value, x, y in fields:
        # Draw label in grey
        c.setFillColor(colors.HexColor("#555555"))
        c.setFont("Helvetica", 9)
        c.drawString(x, y, label)

        # Draw value in black bold
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(x + 120, y, value)

    # --- Line items table header ---
    table_top = page_height - 280
    c.setFillColor(colors.HexColor("#1a3c5e"))
    c.rect(40, table_top, page_width - 80, 18, fill=1, stroke=0)

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(45,              table_top + 5, "Description")
    c.drawString(295,             table_top + 5, "Qty")
    c.drawString(360,             table_top + 5, "Unit Price")
    c.drawRightString(page_width - 40, table_top + 5, "Amount")

    # --- Line items ---
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 9)
    c.drawString(45,  table_top - 14, "Professional Services")
    c.drawString(295, table_top - 14, "40")
    c.drawString(360, table_top - 14, "125.00")
    c.drawRightString(page_width - 40, table_top - 14, "5,000.00")

    # --- Totals ---
    totals_y = table_top - 60

    c.setFont("Helvetica", 9)
    c.drawRightString(page_width - 120, totals_y,      "Subtotal:")
    c.drawRightString(page_width - 40,  totals_y,      "$ 5,000.00")

    c.drawRightString(page_width - 120, totals_y - 16, "HST (13%):")
    c.drawRightString(page_width - 40,  totals_y - 16, "$ 650.00")

    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(page_width - 120, totals_y - 32, "Total Due:")
    c.drawRightString(page_width - 40,  totals_y - 32, "CAD $ 5,650.00")

    # --- Payment details ---
    c.setFont("Helvetica", 9)
    payment_y = totals_y - 80
    c.setFont("Helvetica-Bold", 9)
    c.drawString(40, payment_y, "Payment Details")

    payment_details = [
        ("Bank Name:",     "TD Bank"),
        ("Account Number:", "****-****-1234"),
        ("Transit Number:", "00152"),
    ]
    detail_y = payment_y - 14
    for label, value in payment_details:
        c.setFont("Helvetica", 9)
        c.drawString(40, detail_y, label)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(160, detail_y, value)
        detail_y -= 13

    # Finalise and save the PDF
    c.save()

    # Return the path to the generated file for the test to use
    return pdf_path


# ---------------------------------------------------------------------------
# BANK STATEMENT PDF FIXTURE
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_bank_statement_pdf(temp_dir):
    """
    WHAT THIS FIXTURE DOES:
      Generates a minimal bank statement PDF in the temp directory.

    Contains all the key field labels that the comparator checks:
    Account Number, Statement Period, Opening Balance, etc.

    Returns:
      Path to the generated bank statement PDF.
    """

    pdf_path = temp_dir / "bank_statement.pdf"

    # Use Letter size — common for Canadian bank statements
    c = rl_canvas.Canvas(str(pdf_path), pagesize=letter)
    page_width, page_height = letter   # 612 × 792

    # --- Bank header ---
    c.setFillColor(colors.HexColor("#008000"))   # TD green
    c.rect(0, page_height - 55, page_width, 55, fill=1, stroke=0)

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(36, page_height - 32, "TD Bank")

    c.setFont("Helvetica", 9)
    c.drawString(36, page_height - 46, "Toronto-Dominion Bank")

    # "ACCOUNT STATEMENT" label
    c.setFillColor(colors.HexColor("#008000"))
    c.setFont("Helvetica-Bold", 14)
    c.drawString(36, page_height - 75, "ACCOUNT STATEMENT")

    # --- Account summary fields ---
    summary_fields = [
        ("Account Number:",     "00152-004-1234567",         36,   page_height - 110),
        ("Account Type:",       "Personal Chequing",         36,   page_height - 124),
        ("Transit Number:",     "00152",                     36,   page_height - 138),
        ("Institution No.:",    "004",                       36,   page_height - 152),
        ("Statement Period:",   "Jan 01, 2025 – Jan 31, 2025", 316, page_height - 110),
        ("Opening Balance:",    "$ 3,421.67",                316,  page_height - 124),
        ("Total Deposits:",     "$ 4,800.00",                316,  page_height - 138),
        ("Total Withdrawals:",  "$ 2,156.43",                316,  page_height - 152),
        ("Closing Balance:",    "$ 6,065.24",                316,  page_height - 166),
        ("Available Balance:",  "$ 6,065.24",                316,  page_height - 180),
    ]

    for label, value, x, y in summary_fields:
        c.setFillColor(colors.HexColor("#555555"))
        c.setFont("Helvetica", 9)
        c.drawString(x, y, label)
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(x + 130, y, value)

    # --- Transaction table header ---
    table_top = page_height - 250

    c.setFillColor(colors.HexColor("#008000"))
    c.rect(36, table_top, page_width - 72, 18, fill=1, stroke=0)

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(41,  table_top + 5, "Date")
    c.drawString(111, table_top + 5, "Description")
    c.drawString(391, table_top + 5, "Debit")
    c.drawString(451, table_top + 5, "Credit")
    c.drawRightString(page_width - 36, table_top + 5, "Balance")

    # --- Sample transactions ---
    transactions = [
        ("Jan 01", "Opening Balance",              "",       "",         "3,421.67"),
        ("Jan 02", "Direct Deposit - Payroll",     "",       "2,400.00", "5,821.67"),
        ("Jan 03", "INTERAC Purchase - LCBO",      "45.23",  "",         "5,776.44"),
        ("Jan 05", "Pre-Auth Payment - Rogers",    "85.00",  "",         "5,691.44"),
        ("Jan 31", "Closing Balance",              "",       "",         "6,065.24"),
    ]

    row_y = table_top - 15
    for i, (date, desc, debit, credit, balance) in enumerate(transactions):
        if i % 2 == 0:
            c.setFillColor(colors.HexColor("#e8f5e8"))
            c.rect(36, row_y - 4, page_width - 72, 14, fill=1, stroke=0)

        c.setFillColor(colors.black)
        c.setFont("Helvetica", 8)
        c.drawString(41,  row_y, date)
        c.drawString(111, row_y, desc)
        c.drawString(391, row_y, debit)
        c.drawString(451, row_y, credit)
        c.drawRightString(page_width - 36, row_y, balance)
        row_y -= 14

    c.save()
    return pdf_path


# ---------------------------------------------------------------------------
# TAMPERED INVOICE FIXTURE
# ---------------------------------------------------------------------------

@pytest.fixture
def tampered_invoice_pdf(sample_invoice_pdf, temp_dir):
    """
    WHAT THIS FIXTURE DOES:
      Creates a copy of the sample invoice and applies a value substitution.
      Used by tests that verify high-risk detection.

    Depends on sample_invoice_pdf fixture — pytest injects it automatically.

    Returns:
      Path to the tampered PDF (a separate copy from the original).
    """

    # Copy the clean invoice to a new "tampered" path
    tampered_path = temp_dir / "tampered_invoice.pdf"
    shutil.copy2(sample_invoice_pdf, tampered_path)

    # Apply value substitution using PyMuPDF
    doc = fitz.open(str(tampered_path))
    page = doc[0]

    # Get all text blocks and find a dollar amount to replace
    blocks = page.get_text("blocks")

    for block in blocks:
        x0, y0, x1, y1, text = block[0], block[1], block[2], block[3], block[4]

        # Target a block with a dollar amount
        if "5,650" in text or "5,000" in text:
            # Redact the original value
            page.add_redact_annot(fitz.Rect(x0, y0, x1, y1))
            page.apply_redactions()

            # Write fraudulent replacement
            page.insert_text(
                fitz.Point(x0, y1 - 2),
                "$ 99,999.00",
                fontsize=9,
                color=(0, 0, 0),
            )
            break   # one substitution is enough for the test

    save_path = temp_dir / "tampered_invoice_saved.pdf"
    doc.save(str(save_path))
    doc.close()

    shutil.move(str(save_path), str(tampered_path))
    return tampered_path


# ---------------------------------------------------------------------------
# BASELINE INVOICE FIXTURE
# ---------------------------------------------------------------------------

@pytest.fixture
def baseline_invoice_pdf(temp_dir):
    """
    WHAT THIS FIXTURE DOES:
      Creates a baseline invoice PDF that simulates what would be in
      templates/invoices/acme_corp.pdf.

    Used by comparator tests that need a real baseline to diff against.

    Returns:
      Path to the baseline PDF.
    """

    # The baseline is identical in layout to sample_invoice_pdf.
    # In a real scenario, the baseline is a known-good document from the issuer.
    # Here we generate it the same way as sample_invoice_pdf but at a fixed path.

    pdf_path = temp_dir / "baseline_invoice.pdf"

    c = rl_canvas.Canvas(str(pdf_path), pagesize=A4)
    page_width, page_height = A4

    # Identical layout to sample_invoice_pdf fixture
    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(colors.HexColor("#1a3c5e"))
    c.drawString(40, page_height - 50, "Acme Corporation")

    c.setFont("Helvetica-Bold", 24)
    c.drawRightString(page_width - 40, page_height - 60, "INVOICE")

    fields = [
        ("Invoice Number:", "INV-BASELINE",         40,  page_height - 110),
        ("Invoice Date:",   "January 01, 2025",     40,  page_height - 126),
        ("Due Date:",       "January 31, 2025",     40,  page_height - 142),
        ("Payment Terms:",  "Net 30",               40,  page_height - 158),
        ("Bill To:",        "Baseline Customer",    40,  page_height - 200),
    ]

    for label, value, x, y in fields:
        c.setFillColor(colors.HexColor("#555555"))
        c.setFont("Helvetica", 9)
        c.drawString(x, y, label)
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(x + 120, y, value)

    table_top = page_height - 280
    c.setFillColor(colors.HexColor("#1a3c5e"))
    c.rect(40, table_top, page_width - 80, 18, fill=1, stroke=0)

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(45, table_top + 5, "Description")
    c.drawString(295, table_top + 5, "Qty")
    c.drawString(360, table_top + 5, "Unit Price")
    c.drawRightString(page_width - 40, table_top + 5, "Amount")

    totals_y = table_top - 60
    c.setFont("Helvetica", 9)
    c.drawRightString(page_width - 120, totals_y,      "Subtotal:")
    c.drawRightString(page_width - 120, totals_y - 16, "HST (13%):")
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(page_width - 120, totals_y - 32, "Total Due:")

    c.setFont("Helvetica-Bold", 9)
    payment_y = totals_y - 80
    c.drawString(40, payment_y, "Payment Details")
    payment_y -= 14
    for label in ["Bank Name:", "Account Number:", "Transit Number:"]:
        c.setFont("Helvetica", 9)
        c.drawString(40, payment_y, label)
        payment_y -= 13

    c.save()
    return pdf_path