"""
Integration tests using real sample invoice PDFs with Azure Document Intelligence.

These tests require Azure Document Intelligence to be configured:
- Set AZ_DI_ENDPOINT in .env
- Set AZ_DI_API_KEY in .env

If not configured, tests will be skipped.
"""

import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from src.api.main import app
from src.core.config import settings

client = TestClient(app)

# Check if Azure DI is configured
AZURE_DI_CONFIGURED = bool(settings.az_di_endpoint and settings.az_di_api_key)
skip_if_no_azure_di = pytest.mark.skipif(
    not AZURE_DI_CONFIGURED,
    reason="Azure Document Intelligence not configured (set AZ_DI_ENDPOINT and AZ_DI_API_KEY)",
)

SAMPLES_DIR = Path(__file__).parent.parent / "samples" / "invoices"


@skip_if_no_azure_di
@pytest.mark.integration
@pytest.mark.parametrize(
    "invoice_file",
    [
        "invoice-CONTOSO-8890.pdf",
        "invoice-FOXRIVER-0421.pdf",
        "simple-invoice-below-500.pdf",
        "invoice_ctrl_04.pdf",
    ],
)
def test_extract_real_invoice_clean_scans(invoice_file):
    """Test extraction with clean, well-formatted invoice PDFs"""
    pdf_path = SAMPLES_DIR / invoice_file

    if not pdf_path.exists():
        pytest.skip(f"Sample file not found: {pdf_path}")

    with open(pdf_path, "rb") as f:
        files = {"file": (invoice_file, f, "application/pdf")}
        response = client.post("/invoices/extract", files=files)

    assert response.status_code == 200, f"Failed to extract {invoice_file}: {response.text}"

    data = response.json()

    # Verify all expected fields are present
    assert "vendor" in data
    assert "invoice_number" in data
    assert "invoice_date" in data
    assert "total" in data
    assert "currency" in data
    assert "confidence" in data

    # Clean scans should have high confidence
    assert data["confidence"] > 0.7, f"Low confidence for clean scan: {data['confidence']}"

    # Should extract non-empty vendor
    assert (
        data["vendor"] and data["vendor"] != "Unknown"
    ), f"Failed to extract vendor from {invoice_file}"

    # Should extract a total amount
    assert data["total"] > 0, f"Failed to extract total from {invoice_file}"

    print(f"\n✓ {invoice_file}:")
    print(f"  Vendor: {data['vendor']}")
    print(f"  Invoice #: {data['invoice_number']}")
    print(f"  Total: {data['currency']} {data['total']}")
    print(f"  Confidence: {data['confidence']:.1%}")
    print(f"  Bill To: {data.get('bill_to', 'N/A')}")

    # Verify OCR content was extracted
    assert "content" in data, "OCR content should be extracted"
    assert data["content"], "OCR content should not be empty"
    print(f"  Content Length: {len(data['content'])} characters")

    # Note: Validation testing is covered by unit tests in test_approval_rules.py
    # These integration tests focus on extraction accuracy


@skip_if_no_azure_di
@pytest.mark.integration
def test_extract_quote_should_be_rejected():
    """Test that quotes are detected and rejected (lack obligation cues)"""
    pdf_path = SAMPLES_DIR / "quote_006_design.pdf"

    if not pdf_path.exists():
        pytest.skip(f"Sample file not found: {pdf_path}")

    with open(pdf_path, "rb") as f:
        files = {"file": ("quote_006_design.pdf", f, "application/pdf")}
        response = client.post("/invoices/extract", files=files)

    # Should still return 200 and extract fields
    assert response.status_code == 200
    data = response.json()

    print(f"\n✓ quote_006_design.pdf (quote):")
    print(f"  Vendor: {data['vendor']}")
    print(f"  Total: {data['currency']} {data['total']}")
    print(f"  Confidence: {data['confidence']:.1%}")

    # Verify OCR content was extracted
    assert "content" in data, "OCR content should be extracted"
    print(f"  Content extracted: {len(data.get('content', ''))} characters")

    # Test validation - quotes should be rejected (lack obligation cues)
    validate_response = client.post(
        "/invoices/validate",
        json={
            "amount": data["total"],
            "confidence": data["confidence"],
            "content": data.get("content", ""),
            "vendor": data["vendor"],
            "bill_to": data.get("bill_to"),
        },
    )

    assert validate_response.status_code == 200
    validation = validate_response.json()

    print(f"\n  📋 Validation Result:")
    print(f"     Approved: {validation['approved']}")
    print(f"     Reason: {validation['reason']}")
    print(f"     Checks: {validation['checks']}")

    # Quote should be rejected (lacks obligation cues like "amount due", "please remit")
    assert validation["approved"] is False, "Quote should require manual review"
    assert (
        validation["checks"]["document_type_is_invoice"] is False
    ), "Quote should not be classified as invoice"
    print(f"  ✅ CORRECTLY REJECTED: Quote lacks invoice obligation cues")


@skip_if_no_azure_di
@pytest.mark.integration
def test_extract_receipt_ctrl_03():
    """Test that receipt_ctrl_03 is detected as receipt (not invoice)"""
    pdf_path = SAMPLES_DIR / "receipt_ctrl_03.pdf"

    if not pdf_path.exists():
        pytest.skip(f"Sample file not found: {pdf_path}")

    with open(pdf_path, "rb") as f:
        files = {"file": ("receipt_ctrl_03.pdf", f, "application/pdf")}
        response = client.post("/invoices/extract", files=files)

    assert response.status_code == 200
    data = response.json()

    print(f"\n✓ receipt_ctrl_03.pdf (receipt):")
    print(f"  Vendor: {data['vendor']}")
    print(f"  Total: {data['currency']} {data['total']}")
    print(f"  Confidence: {data['confidence']:.1%}")

    # Verify OCR content was extracted
    assert "content" in data, "OCR content should be extracted"
    print(f"  Content extracted: {len(data.get('content', ''))} characters")

    # Test validation - receipts should be rejected (have confirmation cues)
    validate_response = client.post(
        "/invoices/validate",
        json={
            "amount": data["total"],
            "confidence": data["confidence"],
            "content": data.get("content", ""),
            "vendor": data["vendor"],
            "bill_to": data.get("bill_to"),
        },
    )

    assert validate_response.status_code == 200
    validation = validate_response.json()

    print(f"\n  📋 Validation Result:")
    print(f"     Approved: {validation['approved']}")
    print(f"     Reason: {validation['reason']}")
    print(f"     Checks: {validation['checks']}")

    # Receipt should be rejected (has confirmation cues like "paid", "balance $0")
    assert validation["approved"] is False, "Receipt should require manual review"
    assert (
        validation["checks"]["document_type_not_receipt"] is False
    ), "Should be classified as receipt"
    print(f"  ✅ CORRECTLY REJECTED: Receipt has payment confirmation cues")


@skip_if_no_azure_di
@pytest.mark.integration
@pytest.mark.parametrize(
    "invoice_file",
    [
        "invoice-above-500.pdf",
    ],
)
def test_extract_high_value_invoice(invoice_file):
    """Test extraction of invoices above auto-approval threshold"""
    pdf_path = SAMPLES_DIR / invoice_file

    if not pdf_path.exists():
        pytest.skip(f"Sample file not found: {pdf_path}")

    with open(pdf_path, "rb") as f:
        files = {"file": (invoice_file, f, "application/pdf")}
        response = client.post("/invoices/extract", files=files)

    assert response.status_code == 200
    data = response.json()

    # Should extract a total > $500
    assert data["total"] > 500, f"Expected high-value invoice but got ${data['total']}"

    print(f"\n✓ {invoice_file} (high value):")
    print(f"  Total: {data['currency']} {data['total']} (> $500 threshold)")
    print(f"  Confidence: {data['confidence']:.1%}")


@skip_if_no_azure_di
@pytest.mark.integration
def test_extract_handwritten_invoice():
    """Test extraction with handwritten invoice"""
    pdf_path = SAMPLES_DIR / "handwritten-Invoice.pdf"

    if not pdf_path.exists():
        pytest.skip(f"Sample file not found: {pdf_path}")

    with open(pdf_path, "rb") as f:
        files = {"file": ("handwritten-Invoice.pdf", f, "application/pdf")}
        response = client.post("/invoices/extract", files=files)

    # Should still return 200 even if confidence is low
    assert response.status_code == 200
    data = response.json()

    # Handwritten may have lower confidence (but not zero)
    assert data["confidence"] >= 0, "Confidence should be non-negative"

    print(f"\n✓ handwritten-Invoice.pdf (handwritten):")
    print(f"  Vendor: {data['vendor']}")
    print(f"  Confidence: {data['confidence']:.1%}")
    if data["confidence"] < 0.85:
        print(f"  ⚠️  Would require manual review (confidence < 85%)")


@skip_if_no_azure_di
@pytest.mark.integration
def test_extract_scratched_out_receipt():
    """Test that documents with 'Invoice' scratched out and replaced with 'Receipt' are detected"""
    pdf_path = SAMPLES_DIR / "handwritten-scratched-out-invoice-Reciept.pdf"

    if not pdf_path.exists():
        pytest.skip(f"Sample file not found: {pdf_path}")

    with open(pdf_path, "rb") as f:
        files = {"file": ("handwritten-scratched-out-invoice-Reciept.pdf", f, "application/pdf")}
        response = client.post("/invoices/extract", files=files)

    # Should still return 200
    assert response.status_code == 200
    data = response.json()

    print(f"\n✓ handwritten-scratched-out-invoice-Reciept.pdf (extraction):")
    print(f"  Vendor: {data['vendor']}")
    print(f"  Total: {data['currency']} {data['total']}")
    print(f"  Confidence: {data['confidence']:.1%}")

    # Now test validation - this should REJECT the document
    # First, get the OCR content by extracting again with raw binary
    with open(pdf_path, "rb") as f:
        content = f.read()

    # Verify OCR content was extracted
    assert "content" in data, "OCR content should be extracted"
    print(f"  Content extracted: {len(data.get('content', ''))} characters")

    # Test validation with actual extracted content
    validate_response = client.post(
        "/invoices/validate",
        json={
            "amount": data["total"],
            "confidence": data["confidence"],
            "content": data.get("content", ""),
            "vendor": data["vendor"],
            "bill_to": data.get("bill_to"),
        },
    )

    assert validate_response.status_code == 200
    validation = validate_response.json()

    print(f"\n  📋 Validation Result:")
    print(f"     Approved: {validation['approved']}")
    print(f"     Reason: {validation['reason']}")
    print(f"     Checks: {validation['checks']}")

    # Scratched-out documents may or may not be detected as receipts depending on OCR quality
    # The important thing is the extraction works and validation runs
    assert (
        validation["approved"] is False
    ), "Scratched/ambiguous document should require manual review"
    print(f"  ✅ CORRECTLY REQUIRES REVIEW: Ambiguous/scratched document")


@skip_if_no_azure_di
@pytest.mark.integration
def test_extract_receipt_should_detect_non_invoice():
    """Test that receipts are detected (not invoices)"""
    pdf_path = SAMPLES_DIR / "Receipt-2372-1739-1702.pdf"

    if not pdf_path.exists():
        pytest.skip(f"Sample file not found: {pdf_path}")

    with open(pdf_path, "rb") as f:
        files = {"file": ("Receipt-2372-1739-1702.pdf", f, "application/pdf")}
        response = client.post("/invoices/extract", files=files)

    assert response.status_code == 200
    data = response.json()

    # Document Intelligence may still extract fields, but confidence might be lower
    # or vendor might indicate it's not a traditional invoice
    print(f"\n✓ Receipt-2372-1739-1702.pdf:")
    print(f"  Vendor: {data['vendor']}")
    print(f"  Confidence: {data['confidence']:.1%}")
    print(f"  Note: This is a receipt, not an invoice")


@skip_if_no_azure_di
@pytest.mark.integration
def test_extract_raw_binary_with_real_invoice():
    """Test raw binary upload (Logic Apps style) with real invoice"""
    pdf_path = SAMPLES_DIR / "invoice-CONTOSO-8890.pdf"

    if not pdf_path.exists():
        pytest.skip(f"Sample file not found: {pdf_path}")

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    response = client.post(
        "/invoices/extract", content=pdf_bytes, headers={"Content-Type": "application/pdf"}
    )

    assert response.status_code == 200
    data = response.json()

    assert data["confidence"] > 0.7
    assert data["vendor"] and data["vendor"] != "Unknown"

    print(f"\n✓ Raw binary upload (Logic Apps style):")
    print(f"  Vendor: {data['vendor']}")
    print(f"  Confidence: {data['confidence']:.1%}")


def test_summary_message():
    """Display helpful message about running integration tests"""
    if not AZURE_DI_CONFIGURED:
        print("\n" + "=" * 70)
        print("⚠️  Azure Document Intelligence Integration Tests Skipped")
        print("=" * 70)
        print("\nTo run these tests, configure Azure Document Intelligence:")
        print("  1. Create a Document Intelligence resource in Azure")
        print("  2. Add to .env file:")
        print("     AZ_DI_ENDPOINT=https://your-resource.cognitiveservices.azure.com/")
        print("     AZ_DI_API_KEY=your-key-here")
        print("  3. Run: pytest tests/test_integration_real_invoices.py -v")
        print("\n" + "=" * 70 + "\n")
    else:
        print("\n" + "=" * 70)
        print("✓ Azure Document Intelligence is configured")
        print("=" * 70 + "\n")
