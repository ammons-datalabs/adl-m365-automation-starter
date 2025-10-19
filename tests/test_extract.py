from fastapi.testclient import TestClient
from src.api.main import app
import io

client = TestClient(app)

def test_extract_success_pdf_bytes():
    pdf_bytes = b"%PDF-1.4 minimal"
    files = {"file": ("sample.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    r = client.post("/invoices/extract", files=files)
    assert r.status_code == 200
    body = r.json()
    # Contract: keys present
    for k in ["vendor","invoice_number","invoice_date","total","currency","confidence"]:
        assert k in body
    assert body["confidence"] >= 0.9

def test_extract_zero_length_confidence_is_zero():
    files = {"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")}
    r = client.post("/invoices/extract", files=files)
    assert r.status_code == 200
    assert r.json()["confidence"] == 0.0

def test_extract_missing_file_returns_422():
    # 422 Unprocessable Entity
    r = client.post("/invoices/extract")
    assert r.status_code == 422