
from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from ..deps import ExtractResponse
from ...services.form_recognizer import extract_invoice_fields
from ...services.graph import post_approval_card
from ...services.storage import approval_tracker
from ...services.approval_rules import create_approval_rules
from ...models.invoice import ApprovalRequest

router = APIRouter(prefix="/invoices", tags=["invoices"])


class ValidateRequest(BaseModel):
    """Request body for /invoices/validate endpoint"""
    amount: float
    confidence: float
    content: str
    vendor: str = None


class ValidateResponse(BaseModel):
    """Response from /invoices/validate endpoint"""
    approved: bool
    reason: str
    checks: dict
    metadata: dict

@router.post("/extract", response_model=ExtractResponse)
async def extract(request: Request, file: UploadFile = File(None)):
    """
    Extract invoice fields using Azure Document Intelligence.

    Accepts either:
    - multipart/form-data (file upload via form)
    - application/pdf or application/octet-stream (raw binary body)

    This dual-input format allows the endpoint to be called from:
    - Web forms (multipart)
    - Logic Apps/Power Automate (raw binary)
    - API clients like curl/Postman
    """
    try:
        if file:
            # Multipart form-data upload
            content = await file.read()
        else:
            # Raw binary body (e.g., from Logic Apps)
            content = await request.body()
            if not content:
                raise HTTPException(status_code=422, detail="No file provided (either multipart or raw body)")

        extracted = extract_invoice_fields(content)
        return ExtractResponse(
            vendor=extracted.vendor,
            invoice_number=extracted.invoice_number,
            invoice_date=extracted.invoice_date,
            total=extracted.total,
            currency=extracted.currency,
            confidence=extracted.confidence,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/validate", response_model=ValidateResponse)
async def validate_for_approval(req: ValidateRequest):
    """
    Validate invoice data against approval rules.

    This endpoint centralizes business logic for approval decisions,
    making it reusable from Logic Apps, Power Automate, or other clients.

    Benefits over embedding rules in Logic Apps:
    - Single source of truth for approval logic
    - Easy to test and modify
    - Supports complex rules (vendor whitelists, duplicate detection, etc.)
    - Configuration via environment variables
    - Detailed check results for debugging

    Example request:
    {
        "amount": 450.00,
        "confidence": 0.92,
        "content": "INVOICE\\nVendor: ACME Corp\\nTotal: $450.00",
        "vendor": "ACME Corp"
    }

    Example response:
    {
        "approved": true,
        "reason": "Auto-approved: $450.00, 92.0% confidence",
        "checks": {
            "amount_within_limit": true,
            "confidence_sufficient": true,
            "contains_invoice_keyword": true,
            "does_not_contain_receipt_keyword": true
        },
        "metadata": {...}
    }
    """
    try:
        rules = create_approval_rules()
        decision = rules.evaluate(
            amount=req.amount,
            confidence=req.confidence,
            content=req.content,
            vendor=req.vendor
        )

        return ValidateResponse(
            approved=decision.approved,
            reason=decision.reason,
            checks=decision.checks,
            metadata=decision.metadata
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/process")
async def process_invoice(file: UploadFile = File(...), confidence_threshold: float = 0.85):
    """
    Intelligent invoice processing with automatic approval routing.

    - If confidence >= threshold: Auto-approve and return approval status
    - If confidence < threshold: Send to Teams for human review
    """
    try:
        # Step 1: Extract invoice data
        content = await file.read()
        extracted = extract_invoice_fields(content)

        invoice_data = {
            "vendor": extracted.vendor,
            "invoice_number": extracted.invoice_number,
            "invoice_date": extracted.invoice_date,
            "total": extracted.total,
            "currency": extracted.currency,
            "confidence": extracted.confidence
        }

        # Step 2: Route based on confidence
        if extracted.confidence >= confidence_threshold:
            # High confidence - auto-approve
            approval_id = approval_tracker.create_approval(invoice_data)
            approval_tracker.approve(approval_id, approver="system-auto")

            return {
                "status": "auto_approved",
                "message": f"Invoice auto-approved (confidence: {extracted.confidence:.2%})",
                "approval_id": approval_id,
                "invoice_data": invoice_data
            }
        else:
            # Low confidence - request human approval
            approval_id = approval_tracker.create_approval(invoice_data)
            result = await post_approval_card(invoice_data, approval_id)

            return {
                "status": "pending_approval",
                "message": f"Sent to Teams for review (confidence: {extracted.confidence:.2%})",
                "approval_id": approval_id,
                "invoice_data": invoice_data,
                "teams_result": result
            }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/request-approval")
async def request_approval(req: ApprovalRequest):
    """Post an approval request card to Teams with approve/reject buttons"""
    # Create approval record and get unique ID
    approval_id = approval_tracker.create_approval(req.model_dump())

    # Post a card to Teams via incoming webhook with approval URLs
    result = await post_approval_card(req.model_dump(), approval_id)
    return {"result": result, "approval_id": approval_id}

@router.get("/approval/{approval_id}/approve", response_class=HTMLResponse)
async def approve_invoice(approval_id: str):
    """Handle approval action from Teams adaptive card"""
    approval = approval_tracker.get_approval(approval_id)

    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")

    if approval["status"] != "pending":
        return f"""
        <html>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h2>⚠️ Already Processed</h2>
                <p>This invoice was already {approval["status"]}.</p>
                <p>Decision made at: {approval["decided_at"]}</p>
            </body>
        </html>
        """

    # Mark as approved
    approval_tracker.approve(approval_id)

    invoice_data = approval["invoice_data"]
    return f"""
    <html>
        <body style="font-family: Arial; text-align: center; padding: 50px;">
            <h2>✅ Invoice Approved</h2>
            <p><strong>Vendor:</strong> {invoice_data.get("vendor", "N/A")}</p>
            <p><strong>Invoice #:</strong> {invoice_data.get("invoice_number", "N/A")}</p>
            <p><strong>Total:</strong> {invoice_data.get("currency", "")} {invoice_data.get("total", 0)}</p>
            <hr>
            <p style="color: green;">Thank you! The invoice has been approved.</p>
        </body>
    </html>
    """

@router.get("/approval/{approval_id}/reject", response_class=HTMLResponse)
async def reject_invoice(approval_id: str):
    """Handle rejection action from Teams adaptive card"""
    approval = approval_tracker.get_approval(approval_id)

    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")

    if approval["status"] != "pending":
        return f"""
        <html>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h2>⚠️ Already Processed</h2>
                <p>This invoice was already {approval["status"]}.</p>
                <p>Decision made at: {approval["decided_at"]}</p>
            </body>
        </html>
        """

    # Mark as rejected
    approval_tracker.reject(approval_id)

    invoice_data = approval["invoice_data"]
    return f"""
    <html>
        <body style="font-family: Arial; text-align: center; padding: 50px;">
            <h2>❌ Invoice Rejected</h2>
            <p><strong>Vendor:</strong> {invoice_data.get("vendor", "N/A")}</p>
            <p><strong>Invoice #:</strong> {invoice_data.get("invoice_number", "N/A")}</p>
            <p><strong>Total:</strong> {invoice_data.get("currency", "")} {invoice_data.get("total", 0)}</p>
            <hr>
            <p style="color: red;">The invoice has been rejected.</p>
        </body>
    </html>
    """

@router.get("/approvals")
async def list_approvals():
    """List all approval requests (for debugging)"""
    return {"approvals": approval_tracker.list_all()}

@router.get("/approvals/approved")
async def list_approved_invoices():
    """
    List all approved invoices with approval details.

    Shows:
    - Invoice details (vendor, number, total, etc.)
    - Approval type (human vs AI auto-approved)
    - AI confidence level
    - Timestamp and approver
    """
    all_approvals = approval_tracker.list_all()

    # Filter only approved invoices
    approved = [a for a in all_approvals if a["status"] == "approved"]

    # Format response
    result = []
    for approval in approved:
        invoice = approval["invoice_data"]
        result.append({
            "approval_id": approval["id"],
            "vendor": invoice.get("vendor", "N/A"),
            "invoice_number": invoice.get("invoice_number", "N/A"),
            "invoice_date": invoice.get("invoice_date", "N/A"),
            "total": invoice.get("total", 0),
            "currency": invoice.get("currency", "USD"),
            "confidence": invoice.get("confidence", 0),
            "approval_type": "AI Auto-Approved" if approval["decided_by"] == "system-auto" else "Human Approved",
            "approved_by": approval["decided_by"],
            "approved_at": approval["decided_at"],
            "created_at": approval["created_at"]
        })

    # Sort by approval time, most recent first
    result.sort(key=lambda x: x["approved_at"], reverse=True)

    return {
        "total_approved": len(result),
        "invoices": result
    }
