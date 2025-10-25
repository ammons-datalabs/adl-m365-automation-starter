
from pydantic import BaseModel

class ExtractResponse(BaseModel):
    vendor: str | None = None
    invoice_number: str | None = None
    invoice_date: str | None = None
    total: float | None = None
    currency: str | None = None
    confidence: float = 0.0
    content: str | None = None  # Full OCR text content for validation
    bill_to: str | None = None  # Customer/recipient name from invoice
