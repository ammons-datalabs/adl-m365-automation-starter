
from fastapi import APIRouter, UploadFile, File, HTTPException
from ..deps import ExtractResponse
from ...services.form_recognizer import extract_invoice_fields
from ...services.graph import post_approval_card
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

@router.post("/approve")
async def approve(req: ApprovalRequest):
    # Post a card to Teams via incoming webhook (demo path)
    result = await post_approval_card(req.model_dump())
    return {"result": result}
