"""Service Bus queue integration service."""
import json
import logging
from azure.servicebus.aio import ServiceBusClient, ServiceBusSender
from azure.identity.aio import DefaultAzureCredential

from models import FulfillmentMessage

logger = logging.getLogger(__name__)


class QueueService:
    """Service for interacting with Azure Service Bus queue."""

    def __init__(self, service_bus_namespace: str, queue_name: str):
        """
        Initialize the queue service.

        Args:
            service_bus_namespace: Fully qualified namespace (e.g., myns.servicebus.windows.net)
            queue_name: Name of the queue
        """
        self.service_bus_namespace = service_bus_namespace
        self.queue_name = queue_name
        self._client: ServiceBusClient | None = None
        self._sender: ServiceBusSender | None = None

    async def _ensure_initialized(self) -> ServiceBusSender:
        """
        Ensure Service Bus client and sender are initialized.

        Returns:
            ServiceBusSender instance ready for operations
        """
        if self._sender is not None:
            return self._sender

        credential = DefaultAzureCredential(exclude_shared_token_cache_credential=True)
        self._client = ServiceBusClient(
            fully_qualified_namespace=self.service_bus_namespace,
            credential=credential
        )

        self._sender = self._client.get_queue_sender(queue_name=self.queue_name)
        logger.info(f"Connected to Service Bus queue '{self.queue_name}'")

        return self._sender

    async def enqueue_fulfillment(self, message: FulfillmentMessage) -> None:
        """
        Enqueue a fulfillment message to the addon-fulfill queue.

        Args:
            message: FulfillmentMessage to enqueue

        Raises:
            Exception: If enqueueing fails
        """
        sender = await self._ensure_initialized()

        try:
            from azure.servicebus import ServiceBusMessage

            # Serialize message to JSON
            message_body = message.model_dump_json()

            # Create Service Bus message
            sb_message = ServiceBusMessage(
                body=message_body,
                content_type="application/json",
                correlation_id=message.correlation_id,
            )

            # Set partition key for ordering (by trip_id)
            sb_message.partition_key = message.trip_id

            # Send message
            await sender.send_messages(sb_message)

            logger.info(
                f"Enqueued fulfillment message for order {message.order_id}, "
                f"correlation_id={message.correlation_id}"
            )

        except Exception as e:
            logger.error(f"Failed to enqueue fulfillment message: {e}")
            raise

    async def close(self):
        """Close the Service Bus client connection."""
        if self._sender:
            await self._sender.close()
        if self._client:
            await self._client.close()
            logger.info("Closed Service Bus client")
