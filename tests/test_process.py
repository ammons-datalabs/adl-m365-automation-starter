from fastapi.testclient import TestClient
from src.api.main import app
from src.core.config import settings
from src.services.storage import approval_tracker
import io
import respx
import httpx

client = TestClient(app)


def test_process_high_confidence_auto_approve():
    """Test that high confidence invoices are auto-approved"""
    # Disable Azure DI for tests - use mock fallback (confidence = 0.92)
    original_endpoint = settings.az_di_endpoint
    original_key = settings.az_di_api_key
    settings.az_di_endpoint = None
    settings.az_di_api_key = None

    approval_tracker._approvals.clear()

    try:
        pdf_bytes = b"%PDF-1.4 sample invoice"
        files = {"file": ("invoice.pdf", io.BytesIO(pdf_bytes), "application/pdf")}

        # Mock returns confidence 0.92, threshold default is 0.85
        r = client.post("/invoices/process", files=files)
        assert r.status_code == 200

        data = r.json()
        assert data["status"] == "auto_approved"
        assert "auto-approved" in data["message"].lower()
        assert "approval_id" in data
        assert data["invoice_data"]["confidence"] == 0.92

        # Verify it was recorded as approved
        approvals = approval_tracker.list_all()
        assert len(approvals) == 1
        assert approvals[0]["status"] == "approved"
        assert approvals[0]["decided_by"] == "system-auto"

    finally:
        settings.az_di_endpoint = original_endpoint
        settings.az_di_api_key = original_key


def test_process_low_confidence_sends_to_teams():
    """Test that low confidence invoices go to Teams"""
    # Disable Azure DI for tests
    original_endpoint = settings.az_di_endpoint
    original_key = settings.az_di_api_key
    settings.az_di_endpoint = None
    settings.az_di_api_key = None
    settings.teams_webhook_url = "https://example.com/webhook"

    approval_tracker._approvals.clear()

    try:
        with respx.mock:
            respx.post("https://example.com/webhook").mock(return_value=httpx.Response(200))

            pdf_bytes = b""  # Empty file = confidence 0.0
            files = {"file": ("invoice.pdf", io.BytesIO(pdf_bytes), "application/pdf")}

            # Set a high threshold so 0.0 confidence will trigger Teams
            r = client.post("/invoices/process?confidence_threshold=0.5", files=files)
            assert r.status_code == 200

            data = r.json()
            assert data["status"] == "pending_approval"
            assert "sent to teams" in data["message"].lower()
            assert "approval_id" in data
            assert data["invoice_data"]["confidence"] == 0.0

            # Verify it's pending (not auto-approved)
            approvals = approval_tracker.list_all()
            assert len(approvals) == 1
            assert approvals[0]["status"] == "pending"

    finally:
        settings.az_di_endpoint = original_endpoint
        settings.az_di_api_key = original_key


def test_process_custom_threshold():
    """Test custom confidence threshold"""
    original_endpoint = settings.az_di_endpoint
    original_key = settings.az_di_api_key
    settings.az_di_endpoint = None
    settings.az_di_api_key = None
    settings.teams_webhook_url = "https://example.com/webhook"

    approval_tracker._approvals.clear()

    try:
        with respx.mock:
            respx.post("https://example.com/webhook").mock(return_value=httpx.Response(200))

            pdf_bytes = b"%PDF-1.4 invoice"  # Will get 0.92 confidence
            files = {"file": ("invoice.pdf", io.BytesIO(pdf_bytes), "application/pdf")}

            # Set threshold higher than 0.92 - should require human approval
            r = client.post("/invoices/process?confidence_threshold=0.95", files=files)
            assert r.status_code == 200

            data = r.json()
            assert data["status"] == "pending_approval"  # Should go to Teams
            assert data["invoice_data"]["confidence"] == 0.92

    finally:
        settings.az_di_endpoint = original_endpoint
        settings.az_di_api_key = original_key
