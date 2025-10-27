
from io import BytesIO
from loguru import logger
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
from .invoice_types import ExtractedInvoice
from ..core.config import settings


def extract_invoice_fields(file_bytes: bytes) -> ExtractedInvoice:
    # Check if Azure Document Intelligence is configured
    if settings.az_di_endpoint and settings.az_di_api_key:
        logger.info(
            "Using Azure Document Intelligence for invoice extraction",
            endpoint=settings.az_di_endpoint[:50] + "..." if len(settings.az_di_endpoint) > 50 else settings.az_di_endpoint
        )

        try:
            # Initialize Azure Document Intelligence client
            client = DocumentIntelligenceClient(
                endpoint=settings.az_di_endpoint,
                credential=AzureKeyCredential(settings.az_di_api_key)
            )

            # Analyze the document using the prebuilt-invoice model
            logger.info(f"Analyzing document of size {len(file_bytes)} bytes")

            poller = client.begin_analyze_document(
                "prebuilt-invoice",
                body=file_bytes,
                content_type="application/octet-stream"
            )

            result = poller.result()

            # Extract full OCR content for validation
            ocr_content = ""
            if hasattr(result, 'content') and result.content:
                ocr_content = result.content

            # Extract invoice fields from the first document
            if result.documents and len(result.documents) > 0:
                doc = result.documents[0]

                # Access fields as attributes, not dictionary
                fields = doc.fields if hasattr(doc, 'fields') else {}

                # Extract specific fields with proper attribute access
                def get_field_content(field_name):
                    if not fields or field_name not in fields:
                        return None
                    field = fields[field_name]
                    if hasattr(field, 'content'):
                        return field.content
                    elif hasattr(field, 'value'):
                        return str(field.value)
                    return None

                vendor_name = get_field_content("VendorName")
                invoice_id = get_field_content("InvoiceId")
                invoice_date = get_field_content("InvoiceDate")
                invoice_total_raw = get_field_content("InvoiceTotal")
                currency = get_field_content("CurrencyCode") or "USD"

                # Extract customer/bill-to information
                customer_name = get_field_content("CustomerName")
                billing_address_recipient = get_field_content("BillingAddressRecipient")
                # Use whichever is available
                bill_to = customer_name or billing_address_recipient

                # Parse total as float if possible
                total_amount = 0.0
                if invoice_total_raw:
                    try:
                        # Handle currency symbols, currency codes, and commas
                        # Examples: "$123.45", "USD 123.45", "123.45", "1,234.56"
                        total_str = str(invoice_total_raw)
                        # Remove currency symbols and codes
                        total_str = total_str.replace("$", "").replace(",", "")
                        # Remove common currency codes (USD, AUD, EUR, GBP, etc.)
                        for curr_code in ["USD", "AUD", "EUR", "GBP", "CAD", "JPY", "CNY"]:
                            total_str = total_str.replace(curr_code, "")
                        total_str = total_str.strip()
                        total_amount = float(total_str)
                    except (ValueError, TypeError):
                        logger.warning(f"Could not parse invoice total: {invoice_total_raw}")
                        total_amount = 0.0

                # Calculate average confidence
                confidence = doc.confidence if hasattr(doc, 'confidence') else 0.0

                logger.info(
                    "Successfully extracted invoice data from Azure DI",
                    vendor=vendor_name,
                    invoice_number=invoice_id,
                    confidence=confidence
                )

                return ExtractedInvoice(
                    vendor=vendor_name or "Unknown",
                    invoice_number=invoice_id or "N/A",
                    invoice_date=invoice_date or "N/A",
                    total=total_amount,
                    currency=currency,
                    confidence=confidence,
                    raw_chars=len(file_bytes),
                    content=ocr_content,
                    bill_to=bill_to
                )
            else:
                # No structured invoice data found - likely not an invoice document
                # Still return OCR content so our intelligent classifier can analyze it
                logger.warning(
                    "Azure DI prebuilt-invoice model found no structured invoice data. "
                    "Document may be a quote, receipt, or other non-invoice type. "
                    "Returning OCR content for intelligent classification."
                )

                return ExtractedInvoice(
                    vendor="Unknown",
                    invoice_number="N/A",
                    invoice_date="N/A",
                    total=0.0,
                    currency="USD",
                    confidence=0.0,  # Low confidence since no structured data found
                    raw_chars=len(file_bytes),
                    content=ocr_content,
                    bill_to=None
                )

        except Exception as e:
            logger.error(f"Azure DI extraction failed: {str(e)}")
            raise Exception(f"Invoice extraction failed: {str(e)}")

    else:
        logger.warning(
            "Azure Document Intelligence not configured - using MOCK data. "
            "Set AZ_DI_ENDPOINT and AZ_DI_API_KEY to use real extraction."
        )

        # Mock extraction for demo
        text_len = len(file_bytes or b"")
        conf = 0.92 if text_len > 0 else 0.0

        logger.info(
            "Returning mock invoice extraction",
            file_size_bytes=text_len,
            confidence=conf
        )

        return ExtractedInvoice(
            vendor="Contoso Pty Ltd",
            invoice_number="INV-10023",
            invoice_date="2025-09-30",
            total=385.00,
            currency="AUD",
            confidence=conf,
            raw_chars=text_len,
            content="INVOICE\nContoso Pty Ltd\nInvoice #: INV-10023\nTotal: AUD 385.00\nDue Date: 2025-10-15",
            bill_to="Ammons DataLabs"
        )
