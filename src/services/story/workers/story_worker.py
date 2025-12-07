"""Worker for processing story generation jobs from Service Bus queue."""
import asyncio
import json
import logging
import sys
from pathlib import Path

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "shared"))

from azure.identity import DefaultAzureCredential
from azure.servicebus.aio import ServiceBusClient
from azure.servicebus import ServiceBusMessage

from shared.observability import setup_instrumentation

from config import settings
from models.story import StoryJobMessage
from repositories.story_repository import StoryRepository
from services.story_generation_service import StoryGenerationService

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


class StoryWorker:
    """
    Worker for processing story generation jobs from Service Bus queue.
    
    Consumes messages from the story-jobs queue and generates stories
    using the StoryGenerationService.
    """

    def __init__(
        self,
        service_bus_namespace: str,
        queue_name: str,
        story_repository: StoryRepository,
        story_generation_service: StoryGenerationService,
        max_concurrent_messages: int = 5,
    ):
        """
        Initialize the story worker.

        Args:
            service_bus_namespace: Service Bus namespace (FQDN)
            queue_name: Queue name to consume from
            story_repository: Repository for persisting stories
            story_generation_service: Service for generating stories
            max_concurrent_messages: Maximum concurrent message processing
        """
        self.service_bus_namespace = service_bus_namespace
        self.queue_name = queue_name
        self.story_repository = story_repository
        self.story_generation_service = story_generation_service
        self.max_concurrent_messages = max_concurrent_messages

        # Initialize Service Bus client with Managed Identity
        credential = DefaultAzureCredential()
        self.sb_client = ServiceBusClient(
            fully_qualified_namespace=service_bus_namespace,
            credential=credential,
        )

        logger.info(
            "StoryWorker initialized",
            extra={
                "namespace": service_bus_namespace,
                "queue": queue_name,
                "max_concurrent": max_concurrent_messages,
            },
        )

    async def process_message(self, message):
        """
        Process a single story generation message.

        Args:
            message: Service Bus message
        """
        try:
            body = json.loads(str(message))
            job = StoryJobMessage(**body)

            logger.info(
                "Processing story job",
                extra={
                    "owner_id": job.owner_id,
                    "trip_id": job.trip_id,
                    "story_date": job.story_date,
                    "correlation_id": job.correlation_id,
                },
            )

            # Check if story already exists (idempotency)
            story_id = f"story_{job.story_date}"
            existing_story = self.story_repository.get_story(
                story_id=story_id,
                owner_id=job.owner_id,
                trip_id=job.trip_id,
            )

            if existing_story:
                logger.info(
                    "Story already exists, skipping",
                    extra={"story_id": story_id},
                )
                return

            # Generate story
            from uuid import UUID
            story = await self.story_generation_service.generate_story(
                owner_id=job.owner_id,
                trip_id=UUID(job.trip_id),
                story_date=job.story_date,
                owner_token=None,  # Worker uses system credentials
            )

            # Persist story
            self.story_repository.create_story(story)

            logger.info(
                "Story job completed",
                extra={
                    "story_id": story_id,
                    "status": story.status.value,
                },
            )

        except Exception as e:
            logger.error(
                "Failed to process story job",
                extra={
                    "error": str(e),
                    "message_id": message.message_id,
                },
                exc_info=True,
            )
            # Re-raise to trigger message retry
            raise

    async def run(self):
        """
        Run the worker to continuously process messages.
        """
        logger.info("Starting story worker...")

        async with self.sb_client:
            receiver = self.sb_client.get_queue_receiver(
                queue_name=self.queue_name,
                max_wait_time=60,
            )

            async with receiver:
                logger.info("Worker ready to receive messages")

                while True:
                    try:
                        received_msgs = await receiver.receive_messages(
                            max_message_count=self.max_concurrent_messages,
                            max_wait_time=30,
                        )

                        if not received_msgs:
                            logger.debug("No messages received, continuing...")
                            continue

                        logger.info(
                            f"Received {len(received_msgs)} messages",
                            extra={"count": len(received_msgs)},
                        )

                        # Process messages concurrently
                        tasks = []
                        for msg in received_msgs:
                            task = self._process_and_complete(receiver, msg)
                            tasks.append(task)

                        await asyncio.gather(*tasks, return_exceptions=True)

                    except KeyboardInterrupt:
                        logger.info("Worker interrupted, shutting down...")
                        break
                    except Exception as e:
                        logger.error(
                            "Error in worker loop",
                            extra={"error": str(e)},
                            exc_info=True,
                        )
                        # Continue processing
                        await asyncio.sleep(5)

    async def _process_and_complete(self, receiver, msg):
        """
        Process a message and complete/abandon it.

        Args:
            receiver: Service Bus receiver
            msg: Service Bus message
        """
        try:
            await self.process_message(msg)
            await receiver.complete_message(msg)
            logger.debug("Message completed", extra={"message_id": msg.message_id})
        except Exception as e:
            logger.error(
                "Failed to process message, abandoning",
                extra={"message_id": msg.message_id, "error": str(e)},
            )
            await receiver.abandon_message(msg)


async def main():
    """Main entry point for the worker."""
    logger.info("Initializing story worker...")

    # Initialize repository and services
    story_repo = StoryRepository(
        cosmos_endpoint=settings.cosmos_endpoint,
        database_name=settings.cosmos_database_name,
        container_name=settings.cosmos_container_name,
    )

    story_gen_svc = StoryGenerationService(
        azure_openai_endpoint=settings.azure_openai_endpoint,
        azure_openai_deployment=settings.azure_openai_deployment,
        azure_openai_api_version=settings.azure_openai_api_version,
        trip_service_url=settings.trip_service_url,
        toy_service_url=settings.toy_service_url,
        geo_service_url=settings.geo_service_url,
    )

    # Create and run worker
    worker = StoryWorker(
        service_bus_namespace=settings.service_bus_namespace,
        queue_name=settings.story_jobs_queue_name,
        story_repository=story_repo,
        story_generation_service=story_gen_svc,
        max_concurrent_messages=settings.max_concurrent_messages,
    )

    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
