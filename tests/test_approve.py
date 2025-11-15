from fastapi.testclient import TestClient
from src.api.main import app
from src.core.config import settings
import respx
import httpx

client = TestClient(app)


def test_approve_skips_without_webhook():
    # Ensure webhook unset
    settings.teams_webhook_url = None
    r = client.post("/invoices/request-approval", json={"vendor": "Contoso"})
    assert r.status_code == 200
    assert r.json()["result"]["status"] == "skipped"


@respx.mock
def test_approve_posts_adaptive_card():
    settings.teams_webhook_url = "https://example.com/webhook"
    respx.post("https://example.com/webhook").mock(return_value=httpx.Response(200))
    payload = {
        "vendor": "Contoso",
        "invoice_number": "INV-123",
        "invoice_date": "2025-10-12",
        "total": 100.0,
        "currency": "AUD",
        "confidence": 0.95,
    }
    r = client.post("/invoices/request-approval", json=payload)
    assert r.status_code == 200
    data = r.json()["result"]
    assert data["status"] == "sent"
    assert data["http_status"] == 200
