"""
Tests for the /invoices/validate endpoint.

This endpoint centralizes approval logic that was previously embedded in Logic Apps.
"""

from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


def test_validate_approved_invoice():
    """Test validation of an invoice that should be auto-approved"""
    payload = {
        "amount": 450.00,
        "confidence": 0.92,
        "content": "INVOICE\nVendor: ACME Corp\nTotal: $450.00",
        "vendor": "ACME Corp"
    }

    response = client.post("/invoices/validate", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["approved"] is True
    assert "auto-approved" in data["reason"].lower()
    assert data["checks"]["amount_within_limit"] is True
    assert data["checks"]["confidence_sufficient"] is True
    assert data["checks"]["contains_invoice_keyword"] is True
    assert data["checks"]["does_not_contain_receipt_keyword"] is True


def test_validate_rejected_high_amount():
    """Test validation rejects invoice above threshold"""
    payload = {
        "amount": 600.00,  # Above $500 threshold
        "confidence": 0.95,
        "content": "INVOICE\nVendor: Big Corp\nTotal: $600.00",
        "vendor": "Big Corp"
    }

    response = client.post("/invoices/validate", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["approved"] is False
    assert "exceeds limit" in data["reason"].lower()
    assert data["checks"]["amount_within_limit"] is False


def test_validate_rejected_low_confidence():
    """Test validation rejects invoice with low confidence"""
    payload = {
        "amount": 200.00,
        "confidence": 0.70,  # Below 0.85 threshold
        "content": "INVOICE\nVendor: Some Corp\nTotal: $200.00",
        "vendor": "Some Corp"
    }

    response = client.post("/invoices/validate", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["approved"] is False
    assert "confidence" in data["reason"].lower()
    assert data["checks"]["confidence_sufficient"] is False


def test_validate_rejected_receipt():
    """Test validation rejects documents containing 'receipt'"""
    payload = {
        "amount": 100.00,
        "confidence": 0.95,
        "content": "RECEIPT\nVendor: Coffee Shop\nTotal: $100.00",  # Contains "receipt"
        "vendor": "Coffee Shop"
    }

    response = client.post("/invoices/validate", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["approved"] is False
    assert "receipt" in data["reason"].lower()
    assert data["checks"]["does_not_contain_receipt_keyword"] is False


def test_validate_rejected_no_invoice_keyword():
    """Test validation rejects documents without 'invoice' keyword"""
    payload = {
        "amount": 100.00,
        "confidence": 0.95,
        "content": "Bill\nVendor: Some Corp\nTotal: $100.00",  # No "invoice"
        "vendor": "Some Corp"
    }

    response = client.post("/invoices/validate", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["approved"] is False
    assert data["checks"]["contains_invoice_keyword"] is False


def test_validate_rejected_multiple_failures():
    """Test validation with multiple rule violations"""
    payload = {
        "amount": 800.00,  # Too high
        "confidence": 0.75,  # Too low
        "content": "RECEIPT\nVendor: Big Corp\nTotal: $800.00",  # Receipt, not invoice
        "vendor": "Big Corp"
    }

    response = client.post("/invoices/validate", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["approved"] is False

    # Should fail multiple checks
    assert data["checks"]["amount_within_limit"] is False
    assert data["checks"]["confidence_sufficient"] is False
    assert data["checks"]["does_not_contain_receipt_keyword"] is False

    # Reason should mention multiple issues
    reason = data["reason"].lower()
    assert "exceeds" in reason or "amount" in reason
    assert "confidence" in reason
    assert "receipt" in reason


def test_validate_metadata_included():
    """Test that metadata is included in response"""
    payload = {
        "amount": 300.00,
        "confidence": 0.90,
        "content": "INVOICE\nVendor: Test Corp\nTotal: $300.00",
        "vendor": "Test Corp"
    }

    response = client.post("/invoices/validate", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert "metadata" in data
    assert data["metadata"]["amount"] == 300.00
    assert data["metadata"]["confidence"] == 0.90
    assert data["metadata"]["vendor"] == "Test Corp"
    assert "config" in data["metadata"]


def test_validate_edge_case_exactly_500():
    """Test validation at exact threshold boundary"""
    payload = {
        "amount": 500.00,  # Exactly at threshold
        "confidence": 0.85,  # Exactly at threshold
        "content": "INVOICE\nVendor: Edge Corp\nTotal: $500.00",
        "vendor": "Edge Corp"
    }

    response = client.post("/invoices/validate", json=payload)
    assert response.status_code == 200

    data = response.json()
    # Should be approved (≤ 500, not < 500)
    assert data["approved"] is True
    assert data["checks"]["amount_within_limit"] is True
    assert data["checks"]["confidence_sufficient"] is True