
from .types import ExtractedInvoice
from ..core.config import settings

# NOTE: This is a stub. Wire Azure Document Intelligence SDK here.
# For demo purposes, we return a deterministic payload.

def extract_invoice_fields(file_bytes: bytes) -> ExtractedInvoice:
    # TODO: If settings.az_di_endpoint and api key are present, call Azure DI
    # Otherwise, fake an extraction for demo
    text_len = len(file_bytes or b"")
    conf = 0.92 if text_len > 0 else 0.0
    return ExtractedInvoice(
        vendor="Contoso Pty Ltd",
        invoice_number="INV-10023",
        invoice_date="2025-09-30",
        total=1234.56,
        currency="AUD",
        confidence=conf,
        raw_chars=text_len
    )
