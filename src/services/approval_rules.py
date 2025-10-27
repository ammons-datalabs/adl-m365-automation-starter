"""
Business rules for invoice approval decisions.

Centralizes approval logic that can be tested, versioned, and reused
across different automation tools (Logic Apps, Power Automate, etc.)
"""

from loguru import logger
from typing import Dict, Any, Literal
from pydantic import BaseModel


def classify_document_type(text: str) -> Literal["receipt", "invoice", "unknown"]:
    """
    Classify document based on payment obligation intent using weighted scoring.

    This mimics human reasoning: "Does this document require payment action?"

    Key decision factors:
    1. Obligation cues (+): "amount due", "please remit", bank details, future due date
    2. Confirmation cues (-): "thank you for payment", "paid on", card details, $0.00 balance
    3. Contextual layout: invoice headers vs receipt formatting

    Positive score = Invoice (action required)
    Negative score = Receipt (already paid)
    Near zero = Unknown/ambiguous

    Args:
        text: Full OCR text content from document

    Returns:
        "receipt", "invoice", or "unknown"
    """
    if not text:
        return "unknown"

    t = text.lower()
    score = 0

    # ========== OBLIGATION CUES (+) ==========
    # These indicate payment is still owed

    # Strong obligation phrases (+3 each)
    if "amount due" in t and "$0.00" not in t:
        score += 3
    if "balance due" in t and "$0.00" not in t and "balance due 0" not in t:
        score += 3
    if "total due" in t and "$0.00" not in t:
        score += 3
    if "please remit" in t or "please pay" in t or "payment required" in t:
        score += 3

    # Payment terms indicate future payment (+4)
    if "due date" in t or "payment due" in t:
        score += 4
    if "net 30" in t or "net 60" in t or "due upon receipt" in t or "payment terms" in t:
        score += 4

    # Remittance/banking instructions (+3)
    if "remit to" in t or "remit payment" in t or "make payment to" in t:
        score += 3
    if "bank details" in t or "bsb" in t or "account number" in t or "eft details" in t:
        score += 3
    if "wire transfer" in t or "bpay" in t or "direct deposit" in t:
        score += 3

    # Invoice identification (+2)
    if "invoice" in t and "receipt" not in t:
        score += 2
    if "invoice number" in t or "invoice #" in t or "invoice no" in t or "invoice id" in t:
        score += 2

    # ========== CONFIRMATION CUES (-) ==========
    # These indicate payment already completed

    # Payment confirmation phrases (-3 each)
    if "thank you for your payment" in t or "payment received" in t:
        score -= 3
    if "amount paid" in t or "paid on" in t or "date paid" in t:
        score -= 3
    if "payment history" in t or "transaction history" in t:
        score -= 3
    if "your order is complete" in t or "we appreciate your business" in t:
        score -= 3

    # Zero balance confirmation (-4)
    if "$0.00" in t or "balance due 0" in t or "balance: $0.00" in t or "no payment required" in t:
        score -= 4
    if "balance due: $0.00" in t or "amount due: $0.00" in t:
        score -= 4

    # Payment method shown (-3) - indicates completed transaction
    if "visa" in t and ("****" in t or "ending" in t):
        score -= 3
    if "mastercard" in t and ("****" in t or "ending" in t):
        score -= 3
    if "direct debit" in t or "auto-recharge" in t or "autopay" in t:
        score -= 3
    if "paypal" in t or "stripe" in t or "square" in t:
        score -= 3

    # Receipt identification (-2)
    if "receipt" in t and "invoice" not in t:
        score -= 2
    if "receipt number" in t or "receipt #" in t or "receipt no" in t:
        score -= 2
    if "tax invoice / receipt" in t or "tax receipt" in t:
        score -= 2

    # ========== CLASSIFICATION ==========

    logger.debug(
        "Document obligation scoring",
        score=score,
        interpretation="invoice" if score > 2 else "receipt" if score < -2 else "unclear"
    )

    # Clear obligation (score > 2) = Invoice
    if score > 2:
        return "invoice"
    # Clear confirmation (score < -2) = Receipt
    elif score < -2:
        return "receipt"
    # Ambiguous
    else:
        return "unknown"


class ApprovalDecision(BaseModel):
    """Result of an approval decision with explanation"""
    approved: bool
    reason: str
    checks: Dict[str, bool]
    metadata: Dict[str, Any] = {}


class ApprovalRulesConfig(BaseModel):
    """Configuration for approval rules (loaded from environment)"""
    amount_threshold: float = 500.0
    min_confidence: float = 0.85
    require_invoice_keyword: bool = True
    reject_receipt_keyword: bool = True
    allowed_bill_to_names: list[str] = []  # Whitelist of company names


class InvoiceApprovalRules:
    """
    Encapsulates all business rules for automatic invoice approval.

    Benefits:
    - Single source of truth for approval logic
    - Easy to test (unit tests)
    - Easy to modify (change Python code or env vars, not Logic App JSON)
    - Reusable across Logic Apps, Power Automate, API clients
    - Can add complex logic (database lookups, ML models, vendor whitelists)

    Configuration:
    - Set via environment variables (see .env.example)
    - Can be overridden per request
    - Allows different rules for dev/staging/prod

    Future Enhancements:
    - TODO: Validate invoice math (line items sum to subtotal, subtotal + tax = total)
      This would catch data entry errors and potential fraud
    """

    def __init__(self, config: ApprovalRulesConfig = None):
        self.config = config or ApprovalRulesConfig()

    def evaluate(
        self,
        amount: float,
        confidence: float,
        content: str,
        vendor: str = None,
        bill_to: str = None,
        **kwargs
    ) -> ApprovalDecision:
        """
        Evaluate whether an invoice should be auto-approved.

        Args:
            amount: Invoice total amount
            confidence: Document Intelligence confidence score (0-1)
            content: Full OCR text content from the document
            vendor: Vendor name (optional, for future vendor-specific rules)
            bill_to: Customer/recipient name from invoice (critical security check)
            **kwargs: Additional fields for future rule extensions

        Returns:
            ApprovalDecision with approved flag, reason, and check details
        """
        checks = {}
        reasons = []

        # Check 1: Amount threshold
        amount_ok = amount <= self.config.amount_threshold
        checks["amount_within_limit"] = amount_ok
        if not amount_ok:
            reasons.append(
                f"Amount ${amount:.2f} exceeds limit of ${self.config.amount_threshold:.2f}"
            )

        # Check 2: Confidence threshold
        confidence_ok = confidence >= self.config.min_confidence
        checks["confidence_sufficient"] = confidence_ok
        if not confidence_ok:
            reasons.append(
                f"Confidence {confidence:.1%} below minimum {self.config.min_confidence:.1%}"
            )

        # Check 3 & 4: Document type classification using heuristic signals
        # This is more robust than simple keyword matching
        doc_type = classify_document_type(content)
        is_invoice = doc_type == "invoice"
        is_receipt = doc_type == "receipt"

        checks["document_type_is_invoice"] = is_invoice
        checks["document_type_not_receipt"] = not is_receipt

        if self.config.require_invoice_keyword and not is_invoice:
            if is_receipt:
                reasons.append(f"Document classified as receipt (not invoice)")
            else:
                reasons.append(f"Document type unclear - lacks invoice indicators")

        if self.config.reject_receipt_keyword and is_receipt:
            reasons.append("Document classified as receipt (not invoice)")

        # Check 5: Bill To verification (critical security check)
        # Verify invoice is addressed to our company (prevents fraud/misdirection)
        bill_to_ok = True  # Default to pass if no whitelist configured
        if self.config.allowed_bill_to_names:
            # Whitelist is configured - enforce it
            if not bill_to:
                # No bill_to extracted - fail check
                bill_to_ok = False
                reasons.append("Bill To field not found on invoice")
            else:
                # Check if bill_to matches any whitelisted name (case-insensitive, partial match)
                bill_to_lower = bill_to.lower()
                bill_to_ok = any(
                    allowed.lower() in bill_to_lower
                    for allowed in self.config.allowed_bill_to_names
                )
                if not bill_to_ok:
                    reasons.append(
                        f"Invoice not addressed to authorized company (found: '{bill_to}')"
                    )

        checks["bill_to_authorized"] = bill_to_ok

        # Future: Add more sophisticated checks here
        # - Vendor whitelist/blacklist
        # - Historical approval patterns
        # - Duplicate detection
        # - Required fields validation (InvoiceNumber, VendorName, etc.)
        # - PO matching

        # Determine final decision
        all_checks_passed = all([
            amount_ok,
            confidence_ok,
            (is_invoice if self.config.require_invoice_keyword else True),
            (not is_receipt if self.config.reject_receipt_keyword else True),
            bill_to_ok
        ])

        if all_checks_passed:
            reason = f"Auto-approved: ${amount:.2f}, {confidence:.1%} confidence"
        else:
            reason = "Requires manual review: " + "; ".join(reasons)

        logger.info(
            "Invoice approval decision",
            approved=all_checks_passed,
            amount=amount,
            confidence=confidence,
            vendor=vendor,
            checks=checks
        )

        return ApprovalDecision(
            approved=all_checks_passed,
            reason=reason,
            checks=checks,
            metadata={
                "amount": amount,
                "confidence": confidence,
                "vendor": vendor,
                "config": self.config.model_dump()
            }
        )


def create_approval_rules(
    amount_threshold: float = None,
    min_confidence: float = None,
    require_invoice_keyword: bool = None,
    reject_receipt_keyword: bool = None,
    allowed_bill_to_names: list[str] = None
) -> InvoiceApprovalRules:
    """
    Factory function to create approval rules with optional overrides.

    Uses environment variables as defaults, can be overridden per request.
    """
    from ..core.config import settings

    # Parse comma-separated allowed_bill_to_names from settings if not provided
    if allowed_bill_to_names is None:
        bill_to_env = getattr(settings, 'approval_allowed_bill_to_names', '')
        if bill_to_env:
            allowed_bill_to_names = [name.strip() for name in bill_to_env.split(',') if name.strip()]
        else:
            allowed_bill_to_names = []

    config = ApprovalRulesConfig(
        amount_threshold=amount_threshold if amount_threshold is not None else getattr(settings, 'approval_amount_threshold', 500.0),
        min_confidence=min_confidence if min_confidence is not None else getattr(settings, 'approval_min_confidence', 0.85),
        require_invoice_keyword=require_invoice_keyword if require_invoice_keyword is not None else getattr(settings, 'approval_require_invoice_keyword', True),
        reject_receipt_keyword=reject_receipt_keyword if reject_receipt_keyword is not None else getattr(settings, 'approval_reject_receipt_keyword', True),
        allowed_bill_to_names=allowed_bill_to_names
    )

    return InvoiceApprovalRules(config)