"""
Integration tests for bill_to whitelist functionality.

Tests that the APPROVAL_ALLOWED_BILL_TO_NAMES environment variable
properly restricts invoice approvals to authorized companies.
"""

import os
import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


@pytest.fixture(autouse=False)
def set_bill_to_whitelist(monkeypatch):
    """Fixture to temporarily set bill_to whitelist for testing"""
    original_env = os.environ.get("APPROVAL_ALLOWED_BILL_TO_NAMES")

    def _set_whitelist(companies):
        if companies:
            monkeypatch.setenv("APPROVAL_ALLOWED_BILL_TO_NAMES", ",".join(companies))
        else:
            monkeypatch.delenv("APPROVAL_ALLOWED_BILL_TO_NAMES", raising=False)

        # Force reload of settings to pick up new env var
        from importlib import reload
        from src.core import config
        from src.services import approval_rules
        reload(config)
        reload(approval_rules)

    yield _set_whitelist

    # Cleanup: restore original env var
    if original_env is not None:
        os.environ["APPROVAL_ALLOWED_BILL_TO_NAMES"] = original_env
    else:
        os.environ.pop("APPROVAL_ALLOWED_BILL_TO_NAMES", None)

    # Force reload to restore original config
    from importlib import reload
    from src.core import config
    from src.services import approval_rules
    reload(config)
    reload(approval_rules)


def test_no_whitelist_accepts_any_company(set_bill_to_whitelist):
    """When no whitelist is configured, any company should be accepted"""
    set_bill_to_whitelist([])  # No whitelist

    payload = {
        "amount": 100.0,
        "confidence": 0.95,
        "content": "INVOICE\nAmount Due: $100.00\nPlease remit payment",
        "vendor": "ACME Corp",
        "bill_to": "Random Company Ltd"  # Should be accepted
    }

    response = client.post("/invoices/validate", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["approved"] is True
    assert data["checks"]["bill_to_authorized"] is True


def test_whitelist_rejects_unauthorized_company(set_bill_to_whitelist):
    """Whitelist should reject invoices to unauthorized companies"""
    set_bill_to_whitelist(["My Company", "Our Organization"])

    payload = {
        "amount": 100.0,
        "confidence": 0.95,
        "content": "INVOICE\nAmount Due: $100.00\nPlease remit payment",
        "vendor": "ACME Corp",
        "bill_to": "Different Company Ltd"  # NOT in whitelist
    }

    response = client.post("/invoices/validate", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["approved"] is False
    assert data["checks"]["bill_to_authorized"] is False
    assert "not addressed to authorized company" in data["reason"].lower()
    assert "Different Company Ltd" in data["reason"]


def test_whitelist_accepts_authorized_company_exact_match(set_bill_to_whitelist):
    """Whitelist should accept exact matches"""
    set_bill_to_whitelist(["My Company Pty Ltd", "Our Organization"])

    payload = {
        "amount": 100.0,
        "confidence": 0.95,
        "content": "INVOICE\nAmount Due: $100.00\nPlease remit payment",
        "vendor": "ACME Corp",
        "bill_to": "My Company Pty Ltd"  # Exact match
    }

    response = client.post("/invoices/validate", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["approved"] is True
    assert data["checks"]["bill_to_authorized"] is True


def test_whitelist_accepts_authorized_company_partial_match(set_bill_to_whitelist):
    """Whitelist should accept partial matches (company name in longer string)"""
    set_bill_to_whitelist(["My Company"])

    payload = {
        "amount": 100.0,
        "confidence": 0.95,
        "content": "INVOICE\nAmount Due: $100.00\nPlease remit payment",
        "vendor": "ACME Corp",
        "bill_to": "My Company Pty Ltd Australia"  # Contains "My Company"
    }

    response = client.post("/invoices/validate", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["approved"] is True
    assert data["checks"]["bill_to_authorized"] is True


def test_whitelist_case_insensitive(set_bill_to_whitelist):
    """Whitelist matching should be case-insensitive"""
    set_bill_to_whitelist(["My Company"])

    # Test various case combinations
    for bill_to in ["my company pty ltd", "MY COMPANY PTY LTD", "My CoMpAnY Pty Ltd"]:
        payload = {
            "amount": 100.0,
            "confidence": 0.95,
            "content": "INVOICE\nAmount Due: $100.00\nPlease remit payment",
            "vendor": "ACME Corp",
            "bill_to": bill_to
        }

        response = client.post("/invoices/validate", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["approved"] is True, f"Failed for case: {bill_to}"
        assert data["checks"]["bill_to_authorized"] is True


def test_whitelist_multiple_authorized_companies(set_bill_to_whitelist):
    """Multiple companies in whitelist should all be accepted"""
    set_bill_to_whitelist(["Company A", "Company B", "Company C"])

    for company in ["Company A Ltd", "Company B Inc", "Company C International"]:
        payload = {
            "amount": 100.0,
            "confidence": 0.95,
            "content": "INVOICE\nAmount Due: $100.00\nPlease remit payment",
            "vendor": "ACME Corp",
            "bill_to": company
        }

        response = client.post("/invoices/validate", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["approved"] is True, f"Failed for company: {company}"
        assert data["checks"]["bill_to_authorized"] is True


def test_whitelist_rejects_missing_bill_to(set_bill_to_whitelist):
    """When whitelist is configured, missing bill_to should be rejected"""
    set_bill_to_whitelist(["My Company"])

    payload = {
        "amount": 100.0,
        "confidence": 0.95,
        "content": "INVOICE\nAmount Due: $100.00\nPlease remit payment",
        "vendor": "ACME Corp",
        "bill_to": None  # Missing
    }

    response = client.post("/invoices/validate", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["approved"] is False
    assert data["checks"]["bill_to_authorized"] is False
    assert "bill to field not found" in data["reason"].lower()


def test_whitelist_with_commas_in_company_names(set_bill_to_whitelist):
    """Whitelist should handle company names with commas (common in legal names)"""
    # Note: Company names don't typically have commas, but test edge case
    set_bill_to_whitelist(["Smith, Jones & Associates", "Another Company"])

    payload = {
        "amount": 100.0,
        "confidence": 0.95,
        "content": "INVOICE\nAmount Due: $100.00\nPlease remit payment",
        "vendor": "ACME Corp",
        "bill_to": "Smith, Jones & Associates LLP"
    }

    response = client.post("/invoices/validate", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["approved"] is True
    assert data["checks"]["bill_to_authorized"] is True


def test_whitelist_prevents_fraud_scenario(set_bill_to_whitelist):
    """Real-world fraud prevention: reject invoice to competitor/wrong company"""
    set_bill_to_whitelist(["Acme Industries", "Acme Corp"])

    # Attacker tries to get Acme to pay invoice addressed to competitor
    payload = {
        "amount": 5000.0,
        "confidence": 0.99,
        "content": "INVOICE\nAmount Due: $5000.00\nPlease remit immediately",
        "vendor": "Office Supplies Inc",
        "bill_to": "Competitor Industries Ltd"  # WRONG COMPANY - fraud attempt
    }

    response = client.post("/invoices/validate", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["approved"] is False, "Fraud attempt should be blocked!"
    assert data["checks"]["bill_to_authorized"] is False
    assert "not addressed to authorized company" in data["reason"].lower()


def test_whitelist_prevents_typosquatting(set_bill_to_whitelist):
    """Verify behavior with similar company names"""
    set_bill_to_whitelist(["Acme Industries"])

    # Test cases: (bill_to_name, should_match, reason)
    test_cases = [
        ("Acme lndustries", False, "Character substitution 'I' -> 'l'"),
        ("Acme Industriez", False, "Character substitution 's' -> 'z'"),
        ("Acme Industry", False, "Singular vs plural"),
        ("ACME Industries Inc", True, "Contains exact match (case-insensitive with suffix)"),
        ("Acme Industries Corporation", True, "Contains exact match with suffix"),
        ("The Acme Industries Company", True, "Contains exact match with prefix/suffix"),
        ("Acme Manufacturing", False, "Different company entirely"),
    ]

    for bill_to, should_match, reason in test_cases:
        payload = {
            "amount": 1000.0,
            "confidence": 0.95,
            "content": "INVOICE\nAmount Due: $1000.00\nPlease remit payment",
            "vendor": "Supplier Corp",
            "bill_to": bill_to
        }

        response = client.post("/invoices/validate", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["checks"]["bill_to_authorized"] is should_match, \
            f"Mismatch for '{bill_to}' ({reason}): expected {should_match}"


def test_whitelist_with_special_characters(set_bill_to_whitelist):
    """Handle company names with special characters"""
    set_bill_to_whitelist(["AT&T", "Johnson & Johnson", "Procter & Gamble"])

    test_cases = [
        ("AT&T Corporation", True),
        ("Johnson & Johnson Ltd", True),
        ("Procter & Gamble Co", True),
        ("Random Company", False),
    ]

    for bill_to, should_approve in test_cases:
        payload = {
            "amount": 100.0,
            "confidence": 0.95,
            "content": "INVOICE\nAmount Due: $100.00\nPlease remit payment",
            "vendor": "Supplier",
            "bill_to": bill_to
        }

        response = client.post("/invoices/validate", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["checks"]["bill_to_authorized"] is should_approve, \
            f"Mismatch for {bill_to}: expected {should_approve}, got {data['checks']['bill_to_authorized']}"


def test_whitelist_environmental_config_format(set_bill_to_whitelist):
    """Verify environment variable is parsed correctly with various formats"""
    # Test with extra spaces, mixed case, etc.
    test_configs = [
        "Company A,Company B,Company C",      # Clean
        " Company A , Company B , Company C ",  # Extra spaces
        "Company A,  Company B,Company C",    # Inconsistent spacing
    ]

    for config in test_configs:
        set_bill_to_whitelist(config.split(","))

        payload = {
            "amount": 100.0,
            "confidence": 0.95,
            "content": "INVOICE\nAmount Due: $100.00\nPlease remit payment",
            "vendor": "Supplier",
            "bill_to": "Company B Ltd"
        }

        response = client.post("/invoices/validate", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["approved"] is True, f"Failed for config: {config}"
        assert data["checks"]["bill_to_authorized"] is True
