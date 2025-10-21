from fastapi.testclient import TestClient
from src.api.main import app
from src.core.config import settings
import io

client = TestClient(app)

def test_extract_success_pdf_bytes():
    # Disable Azure DI for tests - use mock fallback
    original_endpoint = settings.az_di_endpoint
    original_key = settings.az_di_api_key
    settings.az_di_endpoint = None
    settings.az_di_api_key = None

    try:
        pdf_bytes = b"%PDF-1.4 minimal"
        files = {"file": ("sample.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
        r = client.post("/invoices/extract", files=files)
        assert r.status_code == 200
        body = r.json()
        # Contract: keys present
        for k in ["vendor","invoice_number","invoice_date","total","currency","confidence"]:
            assert k in body
        assert body["confidence"] >= 0.9
    finally:
        settings.az_di_endpoint = original_endpoint
        settings.az_di_api_key = original_key

def test_extract_zero_length_confidence_is_zero():
    # Disable Azure DI for tests - use mock fallback
    original_endpoint = settings.az_di_endpoint
    original_key = settings.az_di_api_key
    settings.az_di_endpoint = None
    settings.az_di_api_key = None

    try:
        files = {"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")}
        r = client.post("/invoices/extract", files=files)
        assert r.status_code == 200
        assert r.json()["confidence"] == 0.0
    finally:
        settings.az_di_endpoint = original_endpoint
        settings.az_di_api_key = original_key

def test_extract_missing_file_returns_422():
    # 422 Unprocessable Entity
    r = client.post("/invoices/extract")
    assert r.status_code == 422