"""
Azure Service Bus event publishing for invoice validation events.

Enables downstream systems to react to invoice processing:
- Accounting systems can ingest approved invoices
- Audit systems can track all validation decisions
- Analytics systems can monitor processing patterns
- Notification systems can alert stakeholders
"""

import json
from datetime import datetime, UTC
from typing import Optional
from dataclasses import dataclass, asdict


@dataclass
class InvoiceValidatedEvent:
    """
    Event published when an invoice is validated.

    This event contains all information needed by downstream consumers
    to process or react to invoice validation decisions.
    """

    approval_id: str
    vendor: str
    invoice_number: str
    total: float
    approved: bool
    reason: str
    confidence: float
    event_type: str = "InvoiceValidated"
    timestamp: Optional[str] = None

    def __post_init__(self):
        """Set timestamp if not provided"""
        if self.timestamp is None:
            self.timestamp = datetime.now(UTC).isoformat()

    def to_dict(self) -> dict:
        """
        Convert event to dictionary for JSON serialization.

        Returns:
            Dictionary representation suitable for Service Bus message body
        """
        return asdict(self)

    def to_json(self) -> str:
        """
        Convert event to JSON string.

        Returns:
            JSON string representation
        """
        return json.dumps(self.to_dict())


class EventPublisher:
    """
    Publishes events to Azure Service Bus (Queue or Topic).

    Usage:
        # Production with Service Bus Queue (recommended - simpler and cheaper)
        from azure.servicebus import ServiceBusClient
        client = ServiceBusClient.from_connection_string(conn_str)
        sender = client.get_queue_sender(queue_name="invoice-events")
        publisher = EventPublisher(service_bus_sender=sender)

        # Production with Service Bus Topic (for pub/sub scenarios)
        sender = client.get_topic_sender(topic_name="invoice-events")
        publisher = EventPublisher(service_bus_sender=sender)

        # Disabled mode (no Service Bus configured)
        publisher = EventPublisher(service_bus_sender=None)
    """

    def __init__(
        self,
        service_bus_sender: Optional[object] = None,
        entity_name: str = "invoice-events"
    ):
        """
        Initialize event publisher.

        Args:
            service_bus_sender: Azure Service Bus sender (ServiceBusSender) or None to disable
            entity_name: Service Bus queue or topic name (default: invoice-events)
        """
        self.service_bus_sender = service_bus_sender
        self.entity_name = entity_name

        # For backward compatibility
        self.topic_name = entity_name

    def publish_invoice_validated(self, event: InvoiceValidatedEvent) -> None:
        """
        Publish an invoice validated event to Service Bus.

        Args:
            event: InvoiceValidatedEvent to publish

        Note:
            If service_bus_sender is None, this is a no-op (disabled mode).
            Useful for local development or when Service Bus is not configured.
        """
        if self.service_bus_sender is None:
            # Disabled mode - do nothing
            return

        from azure.servicebus import ServiceBusMessage

        message_body = event.to_json()
        message = ServiceBusMessage(message_body, content_type="application/json")
        self.service_bus_sender.send_messages(message)


# Singleton instance (optional - can also use dependency injection)
# In production, initialize with real Service Bus connection string
_default_publisher = EventPublisher(service_bus_sender=None)


def get_event_publisher() -> EventPublisher:
    """
    Get the default event publisher instance.

    Returns:
        EventPublisher instance (may be disabled if Service Bus not configured)
    """
    return _default_publisher