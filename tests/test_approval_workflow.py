from fastapi.testclient import TestClient
from src.api.main import app
from src.core.config import settings
from src.services.storage import approval_tracker
import respx
import httpx

client = TestClient(app)


def test_approval_workflow_end_to_end():
    """Test complete approval workflow"""
    # Set webhook for test
    settings.teams_webhook_url = "https://example.com/webhook"

    # Clear any existing approvals
    approval_tracker._approvals.clear()

    with respx.mock:
        respx.post("https://example.com/webhook").mock(return_value=httpx.Response(200))

        # Step 1: Request approval
        payload = {
            "vendor": "Test Corp",
            "invoice_number": "INV-999",
            "invoice_date": "2025-10-21",
            "total": 250.50,
            "currency": "USD",
            "confidence": 0.98,
        }
        r = client.post("/invoices/request-approval", json=payload)
        assert r.status_code == 200
        assert "approval_id" in r.json()
        approval_id = r.json()["approval_id"]

        # Step 2: Check approval was created
        r = client.get("/invoices/approvals")
        assert r.status_code == 200
        approvals = r.json()["approvals"]
        assert len(approvals) == 1
        assert approvals[0]["status"] == "pending"
        assert approvals[0]["invoice_data"]["vendor"] == "Test Corp"

        # Step 3: Approve the invoice
        r = client.get(f"/invoices/approval/{approval_id}/approve")
        assert r.status_code == 200
        assert "Invoice Approved" in r.text

        # Step 4: Verify approval was recorded
        r = client.get("/invoices/approvals")
        approvals = r.json()["approvals"]
        assert approvals[0]["status"] == "approved"
        assert approvals[0]["decided_by"] == "user"


def test_reject_workflow():
    """Test rejection workflow"""
    settings.teams_webhook_url = "https://example.com/webhook"
    approval_tracker._approvals.clear()

    with respx.mock:
        respx.post("https://example.com/webhook").mock(return_value=httpx.Response(200))

        # Create approval
        payload = {"vendor": "Reject Corp", "total": 100.0}
        r = client.post("/invoices/request-approval", json=payload)
        approval_id = r.json()["approval_id"]

        # Reject it
        r = client.get(f"/invoices/approval/{approval_id}/reject")
        assert r.status_code == 200
        assert "Invoice Rejected" in r.text

        # Verify rejection
        r = client.get("/invoices/approvals")
        approvals = r.json()["approvals"]
        assert approvals[0]["status"] == "rejected"


def test_duplicate_approval_prevented():
    """Test that duplicate approvals are prevented"""
    settings.teams_webhook_url = "https://example.com/webhook"
    approval_tracker._approvals.clear()

    with respx.mock:
        respx.post("https://example.com/webhook").mock(return_value=httpx.Response(200))

        # Create and approve
        payload = {"vendor": "Duplicate Test", "total": 50.0}
        r = client.post("/invoices/request-approval", json=payload)
        approval_id = r.json()["approval_id"]

        # First approval
        r = client.get(f"/invoices/approval/{approval_id}/approve")
        assert r.status_code == 200

        # Try to approve again
        r = client.get(f"/invoices/approval/{approval_id}/approve")
        assert r.status_code == 200
        assert "Already Processed" in r.text


def test_nonexistent_approval_returns_404():
    """Test that nonexistent approval returns 404"""
    r = client.get("/invoices/approval/nonexistent-id/approve")
    assert r.status_code == 404


def test_list_empty_approvals():
    """Test listing when no approvals exist"""
    approval_tracker._approvals.clear()
    r = client.get("/invoices/approvals")
    assert r.status_code == 200
    assert r.json()["approvals"] == []


def test_approval_tracker_methods():
    """Test approval tracker edge cases"""
    approval_tracker._approvals.clear()

    # Test approve on non-existent
    result = approval_tracker.approve("fake-id")
    assert result is False

    # Test reject on non-existent
    result = approval_tracker.reject("fake-id")
    assert result is False

    # Test get on non-existent
    result = approval_tracker.get_approval("fake-id")
    assert result is None

    # Create, then test operations
    approval_id = approval_tracker.create_approval({"vendor": "Test"})
    assert approval_id is not None

    # Approve it
    result = approval_tracker.approve(approval_id, "testuser")
    assert result is True

    # Check it was approved
    approval = approval_tracker.get_approval(approval_id)
    assert approval["status"] == "approved"
    assert approval["decided_by"] == "testuser"


def test_list_approved_invoices():
    """Test listing approved invoices with filtering"""
    approval_tracker._approvals.clear()

    # Create mix of approved, rejected, and pending
    id1 = approval_tracker.create_approval({"vendor": "Auto Corp", "confidence": 0.95})
    approval_tracker.approve(id1, "system-auto")

    id2 = approval_tracker.create_approval({"vendor": "Manual Corp", "confidence": 0.75})
    approval_tracker.approve(id2, "user")

    id3 = approval_tracker.create_approval({"vendor": "Rejected Corp", "confidence": 0.60})
    approval_tracker.reject(id3, "user")

    id4 = approval_tracker.create_approval({"vendor": "Pending Corp", "confidence": 0.80})

    # Test the endpoint
    r = client.get("/invoices/approvals/approved")
    assert r.status_code == 200
    data = r.json()

    # Should only show approved (not rejected or pending)
    assert data["total_approved"] == 2

    # Check details
    invoices = data["invoices"]
    assert len(invoices) == 2

    # Find the auto-approved one
    auto = next(inv for inv in invoices if inv["vendor"] == "Auto Corp")
    assert auto["approval_type"] == "AI Auto-Approved"
    assert auto["approved_by"] == "system-auto"

    # Find the human-approved one
    manual = next(inv for inv in invoices if inv["vendor"] == "Manual Corp")
    assert manual["approval_type"] == "Human Approved"
    assert manual["approved_by"] == "user"
