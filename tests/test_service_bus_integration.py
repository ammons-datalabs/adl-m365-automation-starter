"""
Integration tests for Azure Service Bus event publishing.

Run these tests with a real Service Bus namespace:
    pytest tests/test_service_bus_integration.py --run-integration

Requires environment variable:
    SERVICE_BUS_CONNECTION_STRING=Endpoint=sb://...

Note: Uses Service Bus Queue (simpler and cheaper than Topics).
Create a queue named 'invoice-events' in your Service Bus namespace.
"""

import pytest
import os
from src.services.events.event_publisher import EventPublisher, InvoiceValidatedEvent


@pytest.fixture(scope="module", autouse=True)
def cleanup_queue_after_tests():
    """
    Cleanup fixture: Drains the queue after all integration tests complete.

    This prevents test message accumulation and ensures a clean state.
    Uses autouse=True so it runs automatically without explicit reference.
    """
    # Setup: nothing needed before tests
    yield

    # Teardown: drain the queue after all tests
    conn_str = os.getenv("SERVICE_BUS_CONNECTION_STRING")
    if not conn_str:
        return  # Skip cleanup if no connection string

    try:
        from azure.servicebus import ServiceBusClient

        queue_name = "invoice-events"

        with ServiceBusClient.from_connection_string(conn_str) as client:
            with client.get_queue_receiver(queue_name=queue_name, max_wait_time=2) as receiver:
                # Drain all messages from the queue
                message_count = 0
                for msg in receiver:
                    receiver.complete_message(msg)
                    message_count += 1

                if message_count > 0:
                    print(f"\n🧹 Cleanup: Removed {message_count} test message(s) from queue")
    except Exception as e:
        # Don't fail tests if cleanup fails
        print(f"\n⚠️  Cleanup warning: {e}")


@pytest.mark.integration
def test_publish_to_real_service_bus_queue():
    """
    Integration test: Publish event to real Azure Service Bus Queue.

    This test requires:
    1. SERVICE_BUS_CONNECTION_STRING environment variable
    2. Service Bus namespace with a queue named 'invoice-events'
    3. Run with: pytest tests/test_service_bus_integration.py --run-integration

    Setup:
        # Create queue via Azure CLI
        az servicebus queue create \
          --name invoice-events \
          --namespace-name <your-namespace> \
          --resource-group <your-rg>
    """
    conn_str = os.getenv("SERVICE_BUS_CONNECTION_STRING")
    if not conn_str:
        pytest.skip("SERVICE_BUS_CONNECTION_STRING not set")

    try:
        from azure.servicebus import ServiceBusClient
    except ImportError:
        pytest.skip("azure-servicebus not installed")

    queue_name = "invoice-events"

    with ServiceBusClient.from_connection_string(conn_str) as client:
        with client.get_queue_sender(queue_name=queue_name) as sender:
            # Create event publisher with real queue sender
            publisher = EventPublisher(service_bus_sender=sender, entity_name=queue_name)

            # Create test event
            event = InvoiceValidatedEvent(
                approval_id="integration-test-001",
                vendor="Integration Test Corp",
                invoice_number="INT-001",
                total=999.99,
                approved=True,
                reason="Integration test event",
                confidence=0.95
            )

            # Publish to real Service Bus Queue
            publisher.publish_invoice_validated(event)

            # If we get here without exception, it worked!
            print(f"\n✅ Successfully published event to Service Bus queue '{queue_name}'")
            assert True


@pytest.mark.integration
def test_publish_multiple_events_to_queue():
    """
    Integration test: Publish multiple events to real Service Bus Queue.
    """
    conn_str = os.getenv("SERVICE_BUS_CONNECTION_STRING")
    if not conn_str:
        pytest.skip("SERVICE_BUS_CONNECTION_STRING not set")

    try:
        from azure.servicebus import ServiceBusClient
    except ImportError:
        pytest.skip("azure-servicebus not installed")

    queue_name = "invoice-events"

    with ServiceBusClient.from_connection_string(conn_str) as client:
        with client.get_queue_sender(queue_name=queue_name) as sender:
            publisher = EventPublisher(service_bus_sender=sender, entity_name=queue_name)

            # Publish multiple events
            for i in range(3):
                event = InvoiceValidatedEvent(
                    approval_id=f"integration-test-{i:03d}",
                    vendor=f"Vendor {i}",
                    invoice_number=f"INT-{i:03d}",
                    total=100.00 * (i + 1),
                    approved=i % 2 == 0,  # Alternate approved/rejected
                    reason=f"Test event {i}",
                    confidence=0.85 + (i * 0.05)
                )
                publisher.publish_invoice_validated(event)

            print(f"\n✅ Successfully published 3 events to Service Bus queue '{queue_name}'")
            assert True


@pytest.mark.integration
def test_receive_event_from_queue():
    """
    Integration test: Receive and verify event from Service Bus Queue.

    This confirms events are correctly formatted and can be consumed.
    Note: This test may receive messages from previous test runs.
    """
    conn_str = os.getenv("SERVICE_BUS_CONNECTION_STRING")
    if not conn_str:
        pytest.skip("SERVICE_BUS_CONNECTION_STRING not set")

    try:
        from azure.servicebus import ServiceBusClient
    except ImportError:
        pytest.skip("azure-servicebus not installed")

    import json

    queue_name = "invoice-events"

    with ServiceBusClient.from_connection_string(conn_str) as client:
        # Receive any message from the queue
        with client.get_queue_receiver(queue_name=queue_name, max_wait_time=10) as receiver:
            messages = receiver.receive_messages(max_message_count=1, max_wait_time=10)

            if messages:
                msg = messages[0]
                body = str(msg)
                data = json.loads(body)

                # Verify event structure (not specific content, as it may be from previous tests)
                assert "approval_id" in data
                assert "vendor" in data
                assert "event_type" in data
                assert data["event_type"] == "InvoiceValidated"
                assert "approved" in data
                assert "total" in data
                assert "confidence" in data
                assert "timestamp" in data
                assert "reason" in data

                # Verify data types
                assert isinstance(data["total"], (int, float))
                assert isinstance(data["confidence"], (int, float))
                assert isinstance(data["approved"], bool)

                # Complete the message (remove from queue)
                receiver.complete_message(msg)

                print(f"\n✅ Successfully received and verified event structure from queue")
                print(f"   Event: {data['vendor']} - ${data['total']} - {data['event_type']}")
            else:
                pytest.fail("No messages received from queue - queue may be empty")
