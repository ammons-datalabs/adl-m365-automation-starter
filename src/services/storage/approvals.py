"""
In-memory approval tracking (for demo purposes).
In production, use a database (SQL, Cosmos DB, etc.)
"""
from datetime import datetime
from typing import Dict, Optional
import uuid


class ApprovalTracker:
    def __init__(self):
        self._approvals: Dict[str, dict] = {}

    def create_approval(self, invoice_data: dict) -> str:
        """Create a new approval request and return the approval ID"""
        approval_id = str(uuid.uuid4())
        self._approvals[approval_id] = {
            "id": approval_id,
            "invoice_data": invoice_data,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "decided_at": None,
            "decided_by": None
        }
        return approval_id

    def get_approval(self, approval_id: str) -> Optional[dict]:
        """Get approval details by ID"""
        return self._approvals.get(approval_id)

    def approve(self, approval_id: str, approver: str = "user") -> bool:
        """Mark an approval as approved"""
        if approval_id not in self._approvals:
            return False

        self._approvals[approval_id]["status"] = "approved"
        self._approvals[approval_id]["decided_at"] = datetime.utcnow().isoformat()
        self._approvals[approval_id]["decided_by"] = approver
        return True

    def reject(self, approval_id: str, rejector: str = "user") -> bool:
        """Mark an approval as rejected"""
        if approval_id not in self._approvals:
            return False

        self._approvals[approval_id]["status"] = "rejected"
        self._approvals[approval_id]["decided_at"] = datetime.utcnow().isoformat()
        self._approvals[approval_id]["decided_by"] = rejector
        return True

    def list_all(self) -> list:
        """List all approvals (for debugging)"""
        return list(self._approvals.values())


# Global instance (in production, use dependency injection)
approval_tracker = ApprovalTracker()
