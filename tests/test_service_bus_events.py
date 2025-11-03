"""
Tests for Service Bus event publishing.

Verifies that invoice validation events are published to Azure Service Bus
for downstream processing, integration with other systems, and audit trails.
"""

import pytest
from unittest.mock import Mock, patch
from src.services.events.event_publisher import EventPublisher, InvoiceValidatedEvent


@pytest.fixture
def mock_service_bus_sender():
    """Create a mock Service Bus sender matching Azure SDK interface"""
    return Mock()


@pytest.fixture
def event_publisher(mock_service_bus_sender):
    """Create EventPublisher with mocked Service Bus sender"""
    return EventPublisher(service_bus_sender=mock_service_bus_sender)


def test_invoice_validated_event_structure():
    """Test that InvoiceValidatedEvent has correct structure"""
    event = InvoiceValidatedEvent(
        approval_id="test-123",
        vendor="ACME Corp",
        invoice_number="INV-001",
        total=450.00,
        approved=True,
        reason="Auto-approved: $450.00, 92.0% confidence",
        confidence=0.92
    )

    assert event.approval_id == "test-123"
    assert event.vendor == "ACME Corp"
    assert event.invoice_number == "INV-001"
    assert event.total == 450.00
    assert event.approved is True
    assert event.reason == "Auto-approved: $450.00, 92.0% confidence"
    assert event.confidence == 0.92
    assert event.event_type == "InvoiceValidated"
    assert event.timestamp is not None


def test_publish_invoice_validated_event(event_publisher, mock_service_bus_sender):
    """Test publishing an invoice validated event"""
    event = InvoiceValidatedEvent(
        approval_id="test-456",
        vendor="Test Vendor",
        invoice_number="INV-002",
        total=1200.00,
        approved=False,
        reason="Manual review required: amount exceeds threshold",
        confidence=0.88
    )

    # Publish the event
    event_publisher.publish_invoice_validated(event)

    # Verify Service Bus sender was called with send_messages
    assert mock_service_bus_sender.send_messages.called
    call_args = mock_service_bus_sender.send_messages.call_args

    # Verify message content includes key fields
    message = call_args[0][0]
    assert "test-456" in str(message)
    assert "Test Vendor" in str(message)
    assert "InvoiceValidated" in str(message)


def test_publish_multiple_events(event_publisher, mock_service_bus_sender):
    """Test publishing multiple events in sequence"""
    event1 = InvoiceValidatedEvent(
        approval_id="id-1",
        vendor="Vendor A",
        invoice_number="001",
        total=100.00,
        approved=True,
        reason="Approved",
        confidence=0.95
    )

    event2 = InvoiceValidatedEvent(
        approval_id="id-2",
        vendor="Vendor B",
        invoice_number="002",
        total=200.00,
        approved=False,
        reason="Rejected",
        confidence=0.75
    )

    event_publisher.publish_invoice_validated(event1)
    event_publisher.publish_invoice_validated(event2)

    assert mock_service_bus_sender.send_messages.call_count == 2


def test_publish_with_null_service_bus_sender():
    """Test that publisher gracefully handles None sender (disabled mode)"""
    publisher = EventPublisher(service_bus_sender=None)

    event = InvoiceValidatedEvent(
        approval_id="test-789",
        vendor="Test",
        invoice_number="003",
        total=300.00,
        approved=True,
        reason="Test",
        confidence=0.90
    )

    # Should not raise an error
    publisher.publish_invoice_validated(event)


def test_event_serializes_to_json():
    """Test that event can be serialized to JSON for Service Bus"""
    event = InvoiceValidatedEvent(
        approval_id="test-abc",
        vendor="JSON Corp",
        invoice_number="JSON-001",
        total=999.99,
        approved=True,
        reason="Test serialization",
        confidence=0.99
    )

    json_data = event.to_dict()

    assert json_data["approval_id"] == "test-abc"
    assert json_data["vendor"] == "JSON Corp"
    assert json_data["invoice_number"] == "JSON-001"
    assert json_data["total"] == 999.99
    assert json_data["approved"] is True
    assert json_data["event_type"] == "InvoiceValidated"
    assert "timestamp" in json_data


def test_event_includes_metadata():
    """Test that event includes useful metadata for consumers"""
    event = InvoiceValidatedEvent(
        approval_id="meta-test",
        vendor="Metadata Inc",
        invoice_number="META-001",
        total=555.55,
        approved=True,
        reason="Metadata test",
        confidence=0.85
    )

    data = event.to_dict()

    # Should include metadata for routing/filtering
    assert "event_type" in data
    assert "timestamp" in data
    assert "approval_id" in data

    # Timestamp should be ISO format
    assert "T" in data["timestamp"]  # ISO 8601 format


def test_publisher_can_use_entity_name():
    """Test that publisher can be configured with entity name (queue or topic)"""
    mock_sender = Mock()
    publisher = EventPublisher(
        service_bus_sender=mock_sender,
        entity_name="invoice-events"
    )

    assert publisher.entity_name == "invoice-events"
    # Backward compatibility: topic_name should also work
    assert publisher.topic_name == "invoice-events"


def test_event_publisher_interface_exists():
    """Test that EventPublisher has expected interface"""
    mock_sender = Mock()
    publisher = EventPublisher(service_bus_sender=mock_sender)

    # Verify interface methods exist
    assert hasattr(publisher, 'publish_invoice_validated')
    assert callable(publisher.publish_invoice_validated)