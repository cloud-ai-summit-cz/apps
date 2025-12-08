"""Fulfillment worker for processing addon orders."""
import asyncio
import json
import logging
import sys
from datetime import datetime, UTC
from pathlib import Path
from uuid import UUID

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "shared"))

from azure.servicebus.aio import ServiceBusClient
from azure.servicebus import ServiceBusMessage
from azure.identity.aio import DefaultAzureCredential
from azure.storage.blob.aio import BlobServiceClient
import httpx

from shared.observability import setup_instrumentation, get_tracer, get_meter

# Import from parent package
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import settings
from repositories import AddonRepository
from models import AddonOrderStatus, FulfillmentMessage, MediaReference

# Initialize OpenTelemetry
setup_instrumentation(
    service_name=f"{settings.otel_service_name}-worker",
    service_version=settings.service_version,
    otlp_endpoint=settings.otel_exporter_otlp_endpoint,
    namespace=settings.k8s_namespace,
    pod_name=settings.k8s_pod_name,
    node_name=settings.k8s_node_name,
)

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)
meter = get_meter(__name__)

# Metrics
fulfillment_processed_counter = meter.create_counter(
    name="addon_fulfillment_processed_total",
    description="Total addon fulfillments processed",
    unit="1"
)

fulfillment_duration_histogram = meter.create_histogram(
    name="addon_fulfillment_duration_seconds",
    description="Addon fulfillment processing duration",
    unit="s"
)

worker_retries_counter = meter.create_counter(
    name="addon_worker_retries_total",
    description="Total worker retry attempts",
    unit="1"
)


class FulfillmentWorker:
    """Worker for processing addon fulfillment messages."""

    def __init__(self):
        """Initialize the fulfillment worker."""
        self.running = False
        self.credential = DefaultAzureCredential(exclude_shared_token_cache_credential=True)
        
        # Service Bus
        self.sb_client = ServiceBusClient(
            fully_qualified_namespace=settings.service_bus_namespace,
            credential=self.credential
        )
        
        # Cosmos DB repository
        self.addon_repo = AddonRepository(
            cosmos_endpoint=settings.cosmos_endpoint,
            database_name=settings.cosmos_database_name,
            container_name=settings.cosmos_container_name,
        )
        
        # Blob Storage
        self.blob_client = BlobServiceClient(
            account_url=settings.storage_account_url,
            credential=self.credential
        )

    async def start(self):
        """Start the worker."""
        self.running = True
        logger.info("Starting fulfillment worker...")
        
        receiver = self.sb_client.get_queue_receiver(
            queue_name=settings.service_bus_queue_name,
            max_wait_time=5
        )
        
        async with receiver:
            while self.running:
                try:
                    messages = await receiver.receive_messages(max_message_count=10, max_wait_time=5)
                    
                    for message in messages:
                        try:
                            await self._process_message(message)
                            await receiver.complete_message(message)
                            logger.info(f"Completed message {message.message_id}")
                        except Exception as e:
                            logger.error(f"Failed to process message {message.message_id}: {e}")
                            # Check delivery count for poison message handling
                            if message.delivery_count >= 3:
                                logger.error(f"Message {message.message_id} exceeded max retries, moving to dead letter")
                                await receiver.dead_letter_message(
                                    message,
                                    reason="MaxDeliveryCountExceeded",
                                    error_description=str(e)
                                )
                            else:
                                worker_retries_counter.add(1)
                                await receiver.abandon_message(message)
                
                except Exception as e:
                    logger.error(f"Error in worker loop: {e}")
                    await asyncio.sleep(5)

    async def _process_message(self, message: ServiceBusMessage):
        """
        Process a single fulfillment message.

        Args:
            message: Service Bus message to process
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Parse message body
            body = json.loads(str(message))
            fulfillment_msg = FulfillmentMessage(**body)
            
            logger.info(f"Processing fulfillment for order {fulfillment_msg.order_id}")
            
            with tracer.start_as_current_span("addon.fulfill") as span:
                span.set_attribute("order_id", fulfillment_msg.order_id)
                span.set_attribute("trip_id", fulfillment_msg.trip_id)
                span.set_attribute("addon_type", fulfillment_msg.addon_type)
                
                # Update order status to in_progress
                await self.addon_repo.update_status(
                    order_id=fulfillment_msg.order_id,
                    owner_id=fulfillment_msg.owner_id,
                    trip_id=UUID(fulfillment_msg.trip_id),
                    status=AddonOrderStatus.IN_PROGRESS.value
                )
                
                # Generate fulfillment image via Demo Media service
                image_data = await self._generate_image(
                    addon_type=fulfillment_msg.addon_type,
                    trip_id=fulfillment_msg.trip_id,
                    style=fulfillment_msg.media_style
                )
                
                # Upload to blob storage
                blob_name = await self._upload_to_storage(
                    image_data=image_data,
                    trip_id=fulfillment_msg.trip_id,
                    order_id=fulfillment_msg.order_id,
                    addon_type=fulfillment_msg.addon_type
                )
                
                # Update trip gallery
                await self._update_trip_gallery(
                    trip_id=fulfillment_msg.trip_id,
                    blob_name=blob_name,
                    addon_type=fulfillment_msg.addon_type
                )
                
                # Update order status to fulfilled
                media_ref = MediaReference(type="gallery", blob_name=blob_name)
                await self.addon_repo.update_status(
                    order_id=fulfillment_msg.order_id,
                    owner_id=fulfillment_msg.owner_id,
                    trip_id=UUID(fulfillment_msg.trip_id),
                    status=AddonOrderStatus.FULFILLED.value,
                    fulfilled_at=datetime.now(UTC),
                    media_ref=media_ref.model_dump()
                )
                
                # Record metrics
                duration = asyncio.get_event_loop().time() - start_time
                fulfillment_duration_histogram.record(duration, {
                    "addon_type": fulfillment_msg.addon_type,
                    "status": "success"
                })
                fulfillment_processed_counter.add(1, {
                    "addon_type": fulfillment_msg.addon_type,
                    "status": "success"
                })
                
                span.set_attribute("success", True)
                logger.info(f"Fulfilled order {fulfillment_msg.order_id} successfully")
        
        except Exception as e:
            logger.error(f"Failed to fulfill order: {e}")
            
            # Try to mark order as failed
            try:
                if 'fulfillment_msg' in locals():
                    await self.addon_repo.update_status(
                        order_id=fulfillment_msg.order_id,
                        owner_id=fulfillment_msg.owner_id,
                        trip_id=UUID(fulfillment_msg.trip_id),
                        status=AddonOrderStatus.FAILED.value,
                        error_message=str(e)[:1000]
                    )
                    
                    fulfillment_processed_counter.add(1, {
                        "addon_type": fulfillment_msg.addon_type if 'fulfillment_msg' in locals() else "unknown",
                        "status": "failed"
                    })
            except Exception as update_error:
                logger.error(f"Failed to update order status to failed: {update_error}")
            
            raise

    async def _generate_image(self, addon_type: str, trip_id: str, style: str | None) -> bytes:
        """
        Generate addon image via Demo Media service.

        Args:
            addon_type: Type of addon
            trip_id: Trip ID
            style: Optional style hint

        Returns:
            Image data as bytes

        Raises:
            Exception: If image generation fails
        """
        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "addon_type": addon_type,
                    "trip_id": trip_id,
                }
                if style:
                    payload["style"] = style
                
                response = await client.post(
                    f"{settings.demo_media_service_url}/generate/addon",
                    json=payload,
                    timeout=30.0,
                )
                
                if response.status_code != 200:
                    raise Exception(f"Demo Media service returned {response.status_code}: {response.text}")
                
                return response.content
        
        except httpx.RequestError as e:
            logger.error(f"Failed to reach Demo Media service: {e}")
            raise Exception(f"Demo Media service unavailable: {e}")

    async def _upload_to_storage(
        self,
        image_data: bytes,
        trip_id: str,
        order_id: str,
        addon_type: str
    ) -> str:
        """
        Upload image to blob storage.

        Args:
            image_data: Image bytes
            trip_id: Trip ID
            order_id: Order ID
            addon_type: Type of addon

        Returns:
            Blob name

        Raises:
            Exception: If upload fails
        """
        try:
            container_client = self.blob_client.get_container_client(
                settings.blob_container_fulfillment
            )
            
            # Create blob name: gallery/trip_id/addon_order_id_addon_type.png
            blob_name = f"gallery/{trip_id}/{order_id}_{addon_type}.png"
            
            blob_client = container_client.get_blob_client(blob_name)
            await blob_client.upload_blob(image_data, overwrite=True)
            
            logger.info(f"Uploaded image to {blob_name}")
            return blob_name
        
        except Exception as e:
            logger.error(f"Failed to upload image to storage: {e}")
            raise

    async def _update_trip_gallery(self, trip_id: str, blob_name: str, addon_type: str):
        """
        Update trip gallery by calling Trip Service.

        Args:
            trip_id: Trip ID
            blob_name: Blob storage reference
            addon_type: Type of addon

        Raises:
            Exception: If gallery update fails
        """
        try:
            # Use system identity to call Trip Service
            token = await self._get_system_token()
            
            async with httpx.AsyncClient() as client:
                # Create gallery image via Trip Service API
                # Note: This assumes Trip Service has an internal endpoint for system calls
                # or we need to create a multipart form upload
                
                # For now, we'll use a simplified approach - calling the existing gallery endpoint
                # In production, consider adding a dedicated internal endpoint for system calls
                
                payload = {
                    "blob_name": blob_name,
                    "caption": f"Add-on: {addon_type}",
                    "source": "addon",
                }
                
                response = await client.post(
                    f"{settings.trip_service_url}/trip/{trip_id}/gallery/internal",
                    json=payload,
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10.0,
                )
                
                if response.status_code not in [200, 201]:
                    logger.warning(f"Failed to update trip gallery: {response.status_code} - {response.text}")
                    # Don't fail the whole fulfillment if gallery update fails
                    # The image is still in storage
                else:
                    logger.info(f"Updated trip {trip_id} gallery with addon image")
        
        except Exception as e:
            logger.warning(f"Failed to update trip gallery (non-fatal): {e}")
            # Don't fail the fulfillment if gallery update fails

    async def _get_system_token(self) -> str:
        """
        Get system token for calling Trip Service.

        Returns:
            JWT token

        Raises:
            Exception: If token acquisition fails
        """
        # For system-to-system calls, use managed identity to get token
        # Target audience is the Trip Service app ID URI
        token = await self.credential.get_token(settings.app_id_uri + "/.default")
        return token.token

    async def stop(self):
        """Stop the worker."""
        self.running = False
        logger.info("Stopping fulfillment worker...")
        
        await self.sb_client.close()
        await self.addon_repo.close()
        await self.blob_client.close()
        
        logger.info("Fulfillment worker stopped")


async def main():
    """Main entry point for the worker."""
    worker = FulfillmentWorker()
    
    try:
        await worker.start()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    finally:
        await worker.stop()


if __name__ == "__main__":
    asyncio.run(main())
