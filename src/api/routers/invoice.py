
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse
from ..deps import ExtractResponse
from ...services.form_recognizer import extract_invoice_fields
from ...services.graph import post_approval_card
from ...services.storage import approval_tracker
from ...models.invoice import ApprovalRequest

router = APIRouter(prefix="/invoices", tags=["invoices"])

@router.post("/extract", response_model=ExtractResponse)
async def extract(file: UploadFile = File(...)):
    try:
        content = await file.read()
        extracted = extract_invoice_fields(content)
        return ExtractResponse(
            vendor=extracted.vendor,
            invoice_number=extracted.invoice_number,
            invoice_date=extracted.invoice_date,
            total=extracted.total,
            currency=extracted.currency,
            confidence=extracted.confidence,
        )
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
