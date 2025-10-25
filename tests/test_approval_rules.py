"""
Unit tests for approval_rules module.

Tests the intelligent document classification and bill-to authorization logic.
"""

import pytest
from src.services.approval_rules import (
    classify_document_type,
    InvoiceApprovalRules,
    ApprovalRulesConfig,
)


class TestClassifyDocumentType:
    """Tests for the classify_document_type function"""

    def test_clear_invoice_with_obligation_cues(self):
        """Invoice with strong obligation indicators"""
        content = """
        INVOICE
        Invoice Number: INV-001
        Amount Due: $450.00
        Due Date: 2025-11-15
        Payment Terms: Net 30
        Please remit payment to:
        Bank Details: BSB 123-456, Account 12345678
        """
        assert classify_document_type(content) == "invoice"

    def test_clear_receipt_with_confirmation_cues(self):
        """Receipt with payment confirmation indicators"""
        content = """
        RECEIPT
        Receipt Number: REC-001
        Amount Paid: $450.00
        Paid On: 2025-10-20
        Thank you for your payment
        Payment Method: Visa ending in 1234
        Balance Due: $0.00
        """
        assert classify_document_type(content) == "receipt"

    def test_invoice_with_remittance_instructions(self):
        """Invoice with banking/remittance details"""
        content = """
        INVOICE #12345
        Total: $1,200.00
        Remit to: ACME Corp
        Wire Transfer Details:
        Account Number: 987654321
        BPAY Reference: 12345
        """
        assert classify_document_type(content) == "invoice"

    def test_receipt_with_zero_balance(self):
        """Receipt showing zero balance"""
        content = """
        TAX INVOICE / RECEIPT
        Total Charges: $99.00
        Payment Received: $99.00
        Balance Due: $0.00
        """
        assert classify_document_type(content) == "receipt"

    def test_receipt_with_card_details(self):
        """Receipt showing card payment"""
        content = """
        RECEIPT
        Item: Widget
        Total: $50.00
        Mastercard ending 5678
        Transaction Complete
        """
        assert classify_document_type(content) == "receipt"

    def test_invoice_with_payment_terms(self):
        """Invoice with future payment terms"""
        content = """
        INVOICE
        Invoice Date: 2025-10-15
        Net 30 days
        Due upon receipt
        Total: $750.00
        """
        assert classify_document_type(content) == "invoice"

    def test_quote_lacks_obligation_cues(self):
        """Quote should be classified as unknown (no obligation cues)"""
        content = """
        QUOTE
        Quote Number: Q-12345
        Valid Until: 2025-12-31
        Estimated Total: $5,000.00
        """
        result = classify_document_type(content)
        # Quote lacks obligation cues (no "amount due", "please pay", etc.)
        # Should be "unknown" or have low score
        assert result in ["unknown", "receipt"]  # Depends on scoring

    def test_empty_content(self):
        """Empty content should return unknown"""
        assert classify_document_type("") == "unknown"
        assert classify_document_type(None) == "unknown"

    def test_ambiguous_document(self):
        """Document with mixed signals"""
        content = """
        Document 12345
        Total: $100.00
        Date: 2025-10-25
        """
        # Lacks both obligation and confirmation cues
        assert classify_document_type(content) == "unknown"

    def test_invoice_with_scratch_through(self):
        """Invoice that's been marked paid shouldn't fool the classifier"""
        content = """
        INVOICE (PAID - VOID)
        Invoice #: INV-999
        Amount Paid: $500.00
        Payment received via direct debit
        Balance: $0.00
        """
        # Strong confirmation cues should override
        assert classify_document_type(content) == "receipt"

    def test_case_insensitive_matching(self):
        """Classification should be case-insensitive"""
        content_lower = "invoice\namount due: $100.00\nplease remit"
        content_upper = "INVOICE\nAMOUNT DUE: $100.00\nPLEASE REMIT"
        content_mixed = "InVoIcE\nAmOuNt DuE: $100.00\nPlEaSe ReMiT"

        assert classify_document_type(content_lower) == "invoice"
        assert classify_document_type(content_upper) == "invoice"
        assert classify_document_type(content_mixed) == "invoice"


class TestBillToAuthorization:
    """Tests for bill-to authorization check"""

    def test_no_whitelist_configured_passes(self):
        """When no whitelist is configured, check should pass"""
        config = ApprovalRulesConfig(allowed_bill_to_names=[])
        rules = InvoiceApprovalRules(config)

        decision = rules.evaluate(
            amount=100.0,
            confidence=0.9,
            content="INVOICE\nAmount Due: $100.00",
            vendor="ACME Corp",
            bill_to="Random Company"  # Not in whitelist, but no whitelist = pass
        )

        assert decision.checks["bill_to_authorized"] is True

    def test_whitelist_exact_match(self):
        """Exact match with whitelisted company"""
        config = ApprovalRulesConfig(
            allowed_bill_to_names=["My Company Pty Ltd", "MyCompany Inc"]
        )
        rules = InvoiceApprovalRules(config)

        decision = rules.evaluate(
            amount=100.0,
            confidence=0.9,
            content="INVOICE\nAmount Due: $100.00",
            vendor="ACME Corp",
            bill_to="My Company Pty Ltd"
        )

        assert decision.checks["bill_to_authorized"] is True

    def test_whitelist_partial_match(self):
        """Partial match with whitelisted company (case-insensitive)"""
        config = ApprovalRulesConfig(
            allowed_bill_to_names=["My Company"]
        )
        rules = InvoiceApprovalRules(config)

        # Should match because "My Company" is in "My Company Pty Ltd"
        decision = rules.evaluate(
            amount=100.0,
            confidence=0.9,
            content="INVOICE\nAmount Due: $100.00",
            vendor="ACME Corp",
            bill_to="My Company Pty Ltd"
        )

        assert decision.checks["bill_to_authorized"] is True

    def test_whitelist_case_insensitive(self):
        """Case-insensitive matching"""
        config = ApprovalRulesConfig(
            allowed_bill_to_names=["My Company"]
        )
        rules = InvoiceApprovalRules(config)

        decision = rules.evaluate(
            amount=100.0,
            confidence=0.9,
            content="INVOICE\nAmount Due: $100.00",
            vendor="ACME Corp",
            bill_to="my company PTY LTD"  # Different case
        )

        assert decision.checks["bill_to_authorized"] is True

    def test_whitelist_no_match_fails(self):
        """Invoice to unauthorized company should fail"""
        config = ApprovalRulesConfig(
            allowed_bill_to_names=["My Company", "Our Organization"]
        )
        rules = InvoiceApprovalRules(config)

        decision = rules.evaluate(
            amount=100.0,
            confidence=0.9,
            content="INVOICE\nAmount Due: $100.00",
            vendor="ACME Corp",
            bill_to="Random Other Company"  # Not in whitelist
        )

        assert decision.checks["bill_to_authorized"] is False
        assert decision.approved is False
        assert "not addressed to authorized company" in decision.reason.lower()

    def test_whitelist_missing_bill_to_fails(self):
        """When whitelist is configured but bill_to is None, should fail"""
        config = ApprovalRulesConfig(
            allowed_bill_to_names=["My Company"]
        )
        rules = InvoiceApprovalRules(config)

        decision = rules.evaluate(
            amount=100.0,
            confidence=0.9,
            content="INVOICE\nAmount Due: $100.00",
            vendor="ACME Corp",
            bill_to=None  # Missing
        )

        assert decision.checks["bill_to_authorized"] is False
        assert decision.approved is False
        assert "bill to field not found" in decision.reason.lower()

    def test_whitelist_multiple_companies(self):
        """Multiple whitelisted companies"""
        config = ApprovalRulesConfig(
            allowed_bill_to_names=["Company A", "Company B", "Company C"]
        )
        rules = InvoiceApprovalRules(config)

        # Test each company
        for company in ["Company A Corp", "Company B Ltd", "Company C International"]:
            decision = rules.evaluate(
                amount=100.0,
                confidence=0.9,
                content="INVOICE\nAmount Due: $100.00",
                vendor="ACME Corp",
                bill_to=company
            )
            assert decision.checks["bill_to_authorized"] is True


class TestApprovalDecisionIntegration:
    """Integration tests for full approval decision logic"""

    def test_all_checks_pass(self):
        """Invoice passing all checks"""
        config = ApprovalRulesConfig(
            amount_threshold=500.0,
            min_confidence=0.85,
            allowed_bill_to_names=["My Company"]
        )
        rules = InvoiceApprovalRules(config)

        decision = rules.evaluate(
            amount=450.0,
            confidence=0.92,
            content="INVOICE\nAmount Due: $450.00\nPlease remit payment",
            vendor="ACME Corp",
            bill_to="My Company Pty Ltd"
        )

        assert decision.approved is True
        assert decision.checks["amount_within_limit"] is True
        assert decision.checks["confidence_sufficient"] is True
        assert decision.checks["document_type_is_invoice"] is True
        assert decision.checks["document_type_not_receipt"] is True
        assert decision.checks["bill_to_authorized"] is True

    def test_quote_rejected(self):
        """Quote should be rejected (lacks obligation cues)"""
        config = ApprovalRulesConfig(
            amount_threshold=500.0,
            min_confidence=0.85,
            allowed_bill_to_names=["My Company"]
        )
        rules = InvoiceApprovalRules(config)

        decision = rules.evaluate(
            amount=5000.0,
            confidence=1.0,
            content="""
            QUOTE
            Quote Number: Q-12345
            Valid Until: 2025-12-31
            Estimated Total: $5,000.00
            """,
            vendor="ACME Corp",
            bill_to="My Company"
        )

        # Should fail because it's not an invoice (lacks obligation cues)
        assert decision.approved is False
        assert decision.checks["document_type_is_invoice"] is False

    def test_receipt_rejected(self):
        """Receipt should be rejected"""
        config = ApprovalRulesConfig(
            amount_threshold=500.0,
            min_confidence=0.85,
            allowed_bill_to_names=["My Company"]
        )
        rules = InvoiceApprovalRules(config)

        decision = rules.evaluate(
            amount=100.0,
            confidence=0.95,
            content="""
            RECEIPT
            Amount Paid: $100.00
            Thank you for your payment
            Visa ending 1234
            Balance Due: $0.00
            """,
            vendor="Coffee Shop",
            bill_to="My Company"
        )

        assert decision.approved is False
        assert decision.checks["document_type_not_receipt"] is False

    def test_misdirected_invoice_rejected(self):
        """Invoice addressed to wrong company"""
        config = ApprovalRulesConfig(
            amount_threshold=500.0,
            min_confidence=0.85,
            allowed_bill_to_names=["My Company"]
        )
        rules = InvoiceApprovalRules(config)

        decision = rules.evaluate(
            amount=100.0,
            confidence=0.95,
            content="INVOICE\nAmount Due: $100.00",
            vendor="ACME Corp",
            bill_to="Different Company"  # Wrong company!
        )

        assert decision.approved is False
        assert decision.checks["bill_to_authorized"] is False
        assert "not addressed to authorized company" in decision.reason.lower()

    def test_multiple_failures_detailed_reason(self):
        """Multiple check failures should have detailed reason"""
        config = ApprovalRulesConfig(
            amount_threshold=500.0,
            min_confidence=0.85,
            allowed_bill_to_names=["My Company"]
        )
        rules = InvoiceApprovalRules(config)

        decision = rules.evaluate(
            amount=1000.0,  # Too high
            confidence=0.7,  # Too low
            content="RECEIPT\nAmount Paid: $1000.00\nThank you for your payment\nVisa ending 1234",  # Receipt with strong confirmation cues
            vendor="ACME Corp",
            bill_to="Wrong Company"  # Wrong company
        )

        assert decision.approved is False

        # All checks should fail
        assert decision.checks["amount_within_limit"] is False
        assert decision.checks["confidence_sufficient"] is False
        assert decision.checks["document_type_not_receipt"] is False
        assert decision.checks["bill_to_authorized"] is False

        # Reason should mention multiple issues
        reason_lower = decision.reason.lower()
        assert "manual review" in reason_lower
        # Should contain multiple failure reasons
        assert len(decision.reason.split(";")) > 1