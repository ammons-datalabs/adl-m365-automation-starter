
from io import BytesIO
from loguru import logger
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
from .types import ExtractedInvoice
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

                # Parse total as float if possible
                total_amount = 0.0
                if invoice_total_raw:
                    try:
                        # Handle currency symbols and commas
                        total_str = str(invoice_total_raw).replace("$", "").replace(",", "").strip()
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
                    raw_chars=len(file_bytes)
                )
            else:
                logger.warning("No documents found in Azure DI response")
                raise ValueError("No invoice data could be extracted from the document")

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
            total=1234.56,
            currency="AUD",
            confidence=conf,
            raw_chars=text_len
        )
