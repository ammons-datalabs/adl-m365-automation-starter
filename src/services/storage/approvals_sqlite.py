"""
SQLite-based approval tracking for production use.

Provides persistent storage of invoice approvals with SQL query capabilities.
"""

import sqlite3
import json
import uuid
from datetime import datetime, UTC
from typing import Optional
from pathlib import Path
from .approval_tracker_base import ApprovalTrackerBase


class SQLiteApprovalTracker(ApprovalTrackerBase):
    """
    SQLite-backed approval tracker with persistent storage.

    Features:
    - Persistent storage across application restarts
    - SQL queries for business intelligence
    - Status-based filtering
    - Thread-safe operations (via SQLite's built-in locking)
    """

    def __init__(self, db_path: str = "approvals.db"):
        """
        Initialize tracker with database path.

        Args:
            db_path: Path to SQLite database file (default: approvals.db)
        """
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Create approvals table if it doesn't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS approvals (
                id TEXT PRIMARY KEY,
                invoice_data TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL,
                decided_at TEXT,
                decided_by TEXT,
                CHECK (status IN ('pending', 'approved', 'rejected'))
            )
        """)

        # Create indexes for common queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_status
            ON approvals(status)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_created_at
            ON approvals(created_at)
        """)

        conn.commit()
        conn.close()

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def create_approval(self, invoice_data: dict) -> str:
        """
        Create a new approval request and return the approval ID.

        Args:
            invoice_data: Dictionary containing invoice details

        Returns:
            Approval ID (UUID string)
        """
        approval_id = str(uuid.uuid4())
        created_at = datetime.now(UTC).isoformat()

        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO approvals (id, invoice_data, status, created_at)
            VALUES (?, ?, 'pending', ?)
        """, (approval_id, json.dumps(invoice_data), created_at))

        conn.commit()
        conn.close()

        return approval_id

    def get_approval(self, approval_id: str) -> Optional[dict]:
        """
        Get approval details by ID.

        Args:
            approval_id: Unique approval identifier

        Returns:
            Approval dictionary or None if not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, invoice_data, status, created_at, decided_at, decided_by
            FROM approvals
            WHERE id = ?
        """, (approval_id,))

        row = cursor.fetchone()
        conn.close()

        if row is None:
            return None

        return {
            "id": row["id"],
            "invoice_data": json.loads(row["invoice_data"]),
            "status": row["status"],
            "created_at": row["created_at"],
            "decided_at": row["decided_at"],
            "decided_by": row["decided_by"]
        }

    def approve(self, approval_id: str, approver: str = "user") -> bool:
        """
        Mark an approval as approved.

        Args:
            approval_id: Unique approval identifier
            approver: User or system that approved

        Returns:
            True if successful, False if approval not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        decided_at = datetime.now(UTC).isoformat()

        cursor.execute("""
            UPDATE approvals
            SET status = 'approved',
                decided_at = ?,
                decided_by = ?
            WHERE id = ?
        """, (decided_at, approver, approval_id))

        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()

        return rows_affected > 0

    def reject(self, approval_id: str, rejector: str = "user") -> bool:
        """
        Mark an approval as rejected.

        Args:
            approval_id: Unique approval identifier
            rejector: User or system that rejected

        Returns:
            True if successful, False if approval not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        decided_at = datetime.now(UTC).isoformat()

        cursor.execute("""
            UPDATE approvals
            SET status = 'rejected',
                decided_at = ?,
                decided_by = ?
            WHERE id = ?
        """, (decided_at, rejector, approval_id))

        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()

        return rows_affected > 0

    def list_all(self) -> list:
        """
        List all approvals (ordered by creation time, newest first).

        Returns:
            List of approval dictionaries
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, invoice_data, status, created_at, decided_at, decided_by
            FROM approvals
            ORDER BY created_at DESC
        """)

        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "id": row["id"],
                "invoice_data": json.loads(row["invoice_data"]),
                "status": row["status"],
                "created_at": row["created_at"],
                "decided_at": row["decided_at"],
                "decided_by": row["decided_by"]
            }
            for row in rows
        ]

    def query_by_status(self, status: str) -> list:
        """
        Query approvals by status.

        Args:
            status: One of 'pending', 'approved', 'rejected'

        Returns:
            List of approval dictionaries matching the status
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, invoice_data, status, created_at, decided_at, decided_by
            FROM approvals
            WHERE status = ?
            ORDER BY created_at DESC
        """, (status,))

        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "id": row["id"],
                "invoice_data": json.loads(row["invoice_data"]),
                "status": row["status"],
                "created_at": row["created_at"],
                "decided_at": row["decided_at"],
                "decided_by": row["decided_by"]
            }
            for row in rows
        ]

    def query_pending_over_threshold(self, amount_threshold: float) -> list:
        """
        Query pending approvals over a given amount threshold.

        Useful for identifying high-value invoices awaiting approval.

        Args:
            amount_threshold: Minimum invoice amount to filter by

        Returns:
            List of pending approvals exceeding the threshold
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, invoice_data, status, created_at, decided_at, decided_by
            FROM approvals
            WHERE status = 'pending'
            ORDER BY created_at DESC
        """)

        rows = cursor.fetchall()
        conn.close()

        # Filter by amount (invoice_data is JSON)
        results = []
        for row in rows:
            invoice_data = json.loads(row["invoice_data"])
            if invoice_data.get("total", 0) > amount_threshold:
                results.append({
                    "id": row["id"],
                    "invoice_data": invoice_data,
                    "status": row["status"],
                    "created_at": row["created_at"],
                    "decided_at": row["decided_at"],
                    "decided_by": row["decided_by"]
                })

        return results


# Singleton instance for production use
# In production, configure db_path via environment variable
_default_db_path = Path(__file__).parent.parent.parent.parent / "approvals.db"
sqlite_approval_tracker = SQLiteApprovalTracker(str(_default_db_path))