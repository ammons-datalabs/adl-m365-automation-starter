"""
Business rules for invoice approval decisions.

Centralizes approval logic that can be tested, versioned, and reused
across different automation tools (Logic Apps, Power Automate, etc.)
"""

from loguru import logger
from typing import Dict, Any
from pydantic import BaseModel


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
    """

    def __init__(self, config: ApprovalRulesConfig = None):
        self.config = config or ApprovalRulesConfig()

    def evaluate(
        self,
        amount: float,
        confidence: float,
        content: str,
        vendor: str = None,
        **kwargs
    ) -> ApprovalDecision:
        """
        Evaluate whether an invoice should be auto-approved.

        Args:
            amount: Invoice total amount
            confidence: Document Intelligence confidence score (0-1)
            content: Full OCR text content from the document
            vendor: Vendor name (optional, for future vendor-specific rules)
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

        # Check 3: Document type validation - must contain "invoice"
        content_lower = content.lower() if content else ""
        has_invoice = "invoice" in content_lower
        checks["contains_invoice_keyword"] = has_invoice
        if self.config.require_invoice_keyword and not has_invoice:
            reasons.append("Document does not contain 'invoice' keyword")

        # Check 4: Document type validation - must NOT contain "receipt"
        has_receipt = "receipt" in content_lower
        checks["does_not_contain_receipt_keyword"] = not has_receipt
        if self.config.reject_receipt_keyword and has_receipt:
            reasons.append("Document contains 'receipt' keyword (not an invoice)")

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
            (has_invoice if self.config.require_invoice_keyword else True),
            (not has_receipt if self.config.reject_receipt_keyword else True)
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
    reject_receipt_keyword: bool = None
) -> InvoiceApprovalRules:
    """
    Factory function to create approval rules with optional overrides.

    Uses environment variables as defaults, can be overridden per request.
    """
    from ..core.config import settings

    config = ApprovalRulesConfig(
        amount_threshold=amount_threshold if amount_threshold is not None else getattr(settings, 'approval_amount_threshold', 500.0),
        min_confidence=min_confidence if min_confidence is not None else getattr(settings, 'approval_min_confidence', 0.85),
        require_invoice_keyword=require_invoice_keyword if require_invoice_keyword is not None else getattr(settings, 'approval_require_invoice_keyword', True),
        reject_receipt_keyword=reject_receipt_keyword if reject_receipt_keyword is not None else getattr(settings, 'approval_reject_receipt_keyword', True)
    )

    return InvoiceApprovalRules(config)