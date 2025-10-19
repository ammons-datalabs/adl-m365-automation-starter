
from pydantic import BaseModel, Field

class ApprovalRequest(BaseModel):
    vendor: str | None = Field(default=None)
    invoice_number: str | None = Field(default=None)
    invoice_date: str | None = Field(default=None)
    total: float | None = Field(default=None)
    currency: str | None = Field(default=None)
    confidence: float = Field(default=0.0)
