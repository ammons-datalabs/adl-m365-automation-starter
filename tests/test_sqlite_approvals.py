"""
Tests for SQLite-based approval persistence.

This test suite verifies that the SQLite ApprovalTracker:
- Persists approvals across instances
- Supports queries by status
- Enables SQL queries for business intelligence
"""

import pytest
import sqlite3
import tempfile
import os
from datetime import datetime
from src.services.storage.approvals_sqlite import SQLiteApprovalTracker


@pytest.fixture
def db_path():
    """Create a temporary database file for testing"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    # Cleanup
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def tracker(db_path):
    """Create a fresh SQLiteApprovalTracker for each test"""
    return SQLiteApprovalTracker(db_path)


def test_create_approval_persists_to_db(tracker, db_path):
    """Test that creating an approval writes to SQLite database"""
    invoice_data = {"vendor": "ACME Corp", "total": 450.00, "invoice_number": "INV-001"}

    approval_id = tracker.create_approval(invoice_data)

    # Verify it's in the database by querying directly
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, status, invoice_data FROM approvals WHERE id = ?", (approval_id,))
    row = cursor.fetchone()
    conn.close()

    assert row is not None
    assert row[0] == approval_id
    assert row[1] == "pending"
    assert "ACME Corp" in row[2]  # JSON contains vendor


def test_get_approval_retrieves_from_db(tracker):
    """Test that get_approval fetches from database"""
    invoice_data = {"vendor": "Test Vendor", "total": 100.00}
    approval_id = tracker.create_approval(invoice_data)

    # Retrieve it
    approval = tracker.get_approval(approval_id)

    assert approval is not None
    assert approval["id"] == approval_id
    assert approval["status"] == "pending"
    assert approval["invoice_data"]["vendor"] == "Test Vendor"
    assert approval["created_at"] is not None


def test_approve_persists_status_change(tracker):
    """Test that approving updates database status"""
    invoice_data = {"vendor": "Test", "total": 200.00}
    approval_id = tracker.create_approval(invoice_data)

    # Approve it
    success = tracker.approve(approval_id, approver="manager@example.com")

    assert success is True

    # Verify status changed in database
    approval = tracker.get_approval(approval_id)
    assert approval["status"] == "approved"
    assert approval["decided_by"] == "manager@example.com"
    assert approval["decided_at"] is not None


def test_reject_persists_status_change(tracker):
    """Test that rejecting updates database status"""
    invoice_data = {"vendor": "Test", "total": 300.00}
    approval_id = tracker.create_approval(invoice_data)

    # Reject it
    success = tracker.reject(approval_id, rejector="auditor@example.com")

    assert success is True

    # Verify status changed
    approval = tracker.get_approval(approval_id)
    assert approval["status"] == "rejected"
    assert approval["decided_by"] == "auditor@example.com"


def test_list_all_returns_all_approvals(tracker):
    """Test that list_all returns all approvals from database"""
    # Create multiple approvals
    tracker.create_approval({"vendor": "Vendor A", "total": 100})
    tracker.create_approval({"vendor": "Vendor B", "total": 200})
    tracker.create_approval({"vendor": "Vendor C", "total": 300})

    all_approvals = tracker.list_all()

    assert len(all_approvals) == 3
    vendors = [a["invoice_data"]["vendor"] for a in all_approvals]
    assert "Vendor A" in vendors
    assert "Vendor B" in vendors
    assert "Vendor C" in vendors


def test_query_by_status_approved(tracker):
    """Test querying approvals by status (approved)"""
    # Create and approve some
    id1 = tracker.create_approval({"vendor": "A", "total": 100})
    id2 = tracker.create_approval({"vendor": "B", "total": 200})
    id3 = tracker.create_approval({"vendor": "C", "total": 300})

    tracker.approve(id1)
    tracker.approve(id3)
    # id2 remains pending

    approved = tracker.query_by_status("approved")

    assert len(approved) == 2
    approved_ids = [a["id"] for a in approved]
    assert id1 in approved_ids
    assert id3 in approved_ids
    assert id2 not in approved_ids


def test_query_by_status_pending(tracker):
    """Test querying approvals by status (pending)"""
    id1 = tracker.create_approval({"vendor": "A", "total": 100})
    id2 = tracker.create_approval({"vendor": "B", "total": 200})

    tracker.approve(id1)

    pending = tracker.query_by_status("pending")

    assert len(pending) == 1
    assert pending[0]["id"] == id2


def test_query_pending_over_threshold(tracker):
    """Test SQL query for pending approvals over amount threshold"""
    # Create approvals with different amounts
    tracker.create_approval({"vendor": "Small", "total": 100})
    tracker.create_approval({"vendor": "Medium", "total": 600})
    tracker.create_approval({"vendor": "Large", "total": 1200})

    # Query for pending over $500
    results = tracker.query_pending_over_threshold(500.0)

    assert len(results) == 2
    totals = [r["invoice_data"]["total"] for r in results]
    assert 600 in totals
    assert 1200 in totals
    assert 100 not in totals


def test_persistence_across_instances(db_path):
    """Test that data persists when creating new tracker instances"""
    # Create approval with first instance
    tracker1 = SQLiteApprovalTracker(db_path)
    invoice_data = {"vendor": "Persistent Vendor", "total": 999.00}
    approval_id = tracker1.create_approval(invoice_data)

    # Create new instance with same database
    tracker2 = SQLiteApprovalTracker(db_path)

    # Should be able to retrieve the approval
    approval = tracker2.get_approval(approval_id)

    assert approval is not None
    assert approval["invoice_data"]["vendor"] == "Persistent Vendor"
    assert approval["invoice_data"]["total"] == 999.00


def test_approve_nonexistent_returns_false(tracker):
    """Test that approving non-existent ID returns False"""
    success = tracker.approve("nonexistent-id-12345")
    assert success is False


def test_get_nonexistent_returns_none(tracker):
    """Test that getting non-existent approval returns None"""
    approval = tracker.get_approval("nonexistent-id-67890")
    assert approval is None
