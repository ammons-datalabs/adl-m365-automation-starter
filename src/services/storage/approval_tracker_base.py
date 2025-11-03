"""
Abstract base class for approval tracking implementations.

Defines the interface that all approval trackers must implement,
enabling dependency injection and easy swapping of storage backends.
"""

from abc import ABC, abstractmethod
from typing import Optional


class ApprovalTrackerBase(ABC):
    """
    Abstract base class for approval tracking.

    Implementations can use:
    - In-memory storage (for testing/demo)
    - SQLite (for single-instance deployments)
    - SQL Server / PostgreSQL (for production)
    - Cosmos DB (for cloud-native Azure deployments)
    """

    @abstractmethod
    def create_approval(self, invoice_data: dict) -> str:
        """
        Create a new approval request and return the approval ID.

        Args:
            invoice_data: Dictionary containing invoice details

        Returns:
            Approval ID (unique identifier)
        """
        pass

    @abstractmethod
    def get_approval(self, approval_id: str) -> Optional[dict]:
        """
        Get approval details by ID.

        Args:
            approval_id: Unique approval identifier

        Returns:
            Approval dictionary with keys:
                - id: Approval ID
                - invoice_data: Original invoice data
                - status: One of 'pending', 'approved', 'rejected'
                - created_at: ISO timestamp
                - decided_at: ISO timestamp or None
                - decided_by: User/system identifier or None
            Returns None if not found.
        """
        pass

    @abstractmethod
    def approve(self, approval_id: str, approver: str = "user") -> bool:
        """
        Mark an approval as approved.

        Args:
            approval_id: Unique approval identifier
            approver: User or system that approved (default: "user")

        Returns:
            True if successful, False if approval not found
        """
        pass

    @abstractmethod
    def reject(self, approval_id: str, rejector: str = "user") -> bool:
        """
        Mark an approval as rejected.

        Args:
            approval_id: Unique approval identifier
            rejector: User or system that rejected (default: "user")

        Returns:
            True if successful, False if approval not found
        """
        pass

    @abstractmethod
    def list_all(self) -> list:
        """
        List all approvals.

        Returns:
            List of approval dictionaries (same format as get_approval)
        """
        pass