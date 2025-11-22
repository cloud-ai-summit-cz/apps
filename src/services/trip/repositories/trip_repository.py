"""Repository for trip data access in Cosmos DB.

This module uses the async Azure Cosmos SDK (azure.cosmos.aio) which is designed
for use with async frameworks like FastAPI. The async SDK provides native async/await
support without blocking the event loop.
"""
import logging
import time
from typing import Any
from uuid import UUID

from azure.cosmos.aio import ContainerProxy, CosmosClient, DatabaseProxy
from azure.cosmos import exceptions
from azure.identity.aio import DefaultAzureCredential

from models import Trip, TripDocument, GalleryImage
from shared.observability.instrumentation import get_azure_metrics_meter, get_metric_attributes

logger = logging.getLogger(__name__)


class TripRepository:
    """Repository for trip CRUD operations in Cosmos DB."""

    def __init__(self, cosmos_endpoint: str, database_name: str, container_name: str):
        """
        Initialize the trip repository.

        Args:
            cosmos_endpoint: Cosmos DB account endpoint URL
            database_name: Name of the database
            container_name: Name of the container (collection)
        """
        self.cosmos_endpoint = cosmos_endpoint
        self.database_name = database_name
        self.container_name = container_name
        self._client: CosmosClient | None = None
        self._database: DatabaseProxy | None = None
        self._container: ContainerProxy | None = None
        
        # Azure metrics (manual instrumentation because Python SDK doesn't emit semantic spans)
        self.cosmos_ops, self.cosmos_duration, self.cosmos_ru, _, _ = get_azure_metrics_meter()
    
    def _record_cosmos_metrics(self, operation: str, start_time: float, status: str = "success", method: str = None) -> None:
        """Record Cosmos DB operation metrics with user context from baggage."""
        duration = time.time() - start_time
        base_attrs = {"operation": operation, "container": self.container_name}
        if status != "success":
            base_attrs["status"] = status
        if method:
            base_attrs["method"] = method
        
        attrs = get_metric_attributes(base_attrs)
        self.cosmos_ops.add(1, attrs)
        self.cosmos_duration.record(duration, attrs)
        
        # Log actual duration for debugging metrics issues
        logger.debug(f"Cosmos {operation} took {duration:.4f}s (attrs: {attrs})")

    async def _ensure_initialized(self) -> ContainerProxy:
        """
        Ensure Cosmos client, database, and container are initialized.

        Returns:
            ContainerProxy instance ready for operations
        """
        if self._container is not None:
            return self._container

        # Initialize async client with managed identity
        # Exclude shared token cache to prevent home tenant confusion in multi-tenant scenarios
        # Local: Uses Azure CLI (logged in with correct tenant)
        # AKS: Uses Workload Identity / Managed Identity (federated identity)
        credential = DefaultAzureCredential(exclude_shared_token_cache_credential=True)
        self._client = CosmosClient(self.cosmos_endpoint, credential=credential)

        # Get existing database (created via Bicep)
        self._database = self._client.get_database_client(self.database_name)
        logger.info(f"Connected to database '{self.database_name}'")

        # Get existing container (created via Bicep)
        self._container = self._database.get_container_client(self.container_name)
        logger.info(f"Connected to container '{self.container_name}'")

        return self._container

    async def create(self, trip: Trip) -> Trip:
        """
        Create a new trip in the database.

        Args:
            trip: Trip instance to create

        Returns:
            Created Trip with server-assigned timestamps

        Raises:
            exceptions.CosmosResourceExistsError: If trip with same ID already exists
        """
        container = await self._ensure_initialized()
        doc = TripDocument.from_trip(trip)
        item = doc.model_dump(by_alias=False, mode="json")

        # Cosmos DB needs both "id" (document ID) and "trip_id" (partition key)
        # They should have the same value
        item["id"] = str(trip.id)
        item["trip_id"] = str(trip.id)

        start = time.time()
        try:
            created_item = await container.create_item(body=item)
            
            # Record metrics
            self._record_cosmos_metrics("create_item", start)
            
            logger.info(f"Created trip: {created_item['id']} for toy {trip.toy_id}")
            return TripDocument(**created_item).to_trip()
        except Exception as e:
            self._record_cosmos_metrics("create_item", start, "error")
            raise

    async def get_by_id(self, trip_id: UUID) -> Trip | None:
        """
        Retrieve a trip by ID.

        Args:
            trip_id: UUID of the trip

        Returns:
            Trip if found, None otherwise
        """
        container = await self._ensure_initialized()
        trip_id_str = str(trip_id)

        start = time.time()
        try:
            item = await container.read_item(item=trip_id_str, partition_key=trip_id_str)
            
            # Record metrics
            self._record_cosmos_metrics("read_item", start)
            
            return TripDocument(**item).to_trip()
        except exceptions.CosmosResourceNotFoundError:
            self._record_cosmos_metrics("read_item", start, "not_found")
            logger.debug(f"Trip not found: {trip_id_str}")
            return None
        except Exception as e:
            self._record_cosmos_metrics("read_item", start, "error")
            raise

    async def list_by_toy(self, toy_id: UUID, limit: int = 20, offset: int = 0) -> tuple[list[Trip], int]:
        """
        List trips for a specific toy with pagination.

        Args:
            toy_id: UUID of the toy
            limit: Maximum number of items to return
            offset: Number of items to skip

        Returns:
            Tuple of (list of trips, total count)
        """
        container = await self._ensure_initialized()
        toy_id_str = str(toy_id)

        query = "SELECT * FROM c WHERE c.toy_id = @toy_id ORDER BY c.created_at DESC"
        parameters = [{"name": "@toy_id", "value": toy_id_str}]

        start = time.time()
        try:
            items = [item async for item in container.query_items(
                query=query,
                parameters=parameters,
            )]
            
            # Record metrics
            self._record_cosmos_metrics("query_items", start)

            total = len(items)
            paginated_items = items[offset : offset + limit]

            trips = [TripDocument(**item).to_trip() for item in paginated_items]
            logger.debug(f"Listed {len(trips)} trips for toy {toy_id_str} (total: {total})")

            return trips, total
        except Exception as e:
            self._record_cosmos_metrics("query_items", start, "error")
            raise

    async def list_by_owner(self, owner_oid: str, limit: int = 20, offset: int = 0) -> tuple[list[Trip], int]:
        """
        List trips for a specific owner with pagination.

        Args:
            owner_oid: Entra object ID of the owner
            limit: Maximum number of items to return
            offset: Number of items to skip

        Returns:
            Tuple of (list of trips, total count)
        """
        container = await self._ensure_initialized()

        query = "SELECT * FROM c WHERE c.owner_oid = @owner_oid ORDER BY c.created_at DESC"
        parameters = [{"name": "@owner_oid", "value": owner_oid}]

        start = time.time()
        try:
            items = [item async for item in container.query_items(
                query=query,
                parameters=parameters,
            )]
            
            # Record metrics
            self._record_cosmos_metrics("query_items", start)

            total = len(items)
            paginated_items = items[offset : offset + limit]

            trips = [TripDocument(**item).to_trip() for item in paginated_items]
            logger.debug(f"Listed {len(trips)} trips for owner {owner_oid} (total: {total})")

            return trips, total
        except Exception as e:
            self._record_cosmos_metrics("query_items", start, "error")
            raise

    async def update(self, trip_id: UUID, updates: dict[str, Any]) -> Trip | None:
        """
        Update a trip with partial data.

        Args:
            trip_id: UUID of the trip to update
            updates: Dictionary of fields to update

        Returns:
            Updated Trip if found, None otherwise
        """
        container = await self._ensure_initialized()
        trip_id_str = str(trip_id)

        start = time.time()
        try:
            # Read current item
            item = await container.read_item(item=trip_id_str, partition_key=trip_id_str)

            # Apply updates
            for key, value in updates.items():
                if key not in {"id", "trip_id", "toy_id", "owner_oid", "created_at"}:  # Immutable fields
                    item[key] = value

            # Update timestamp
            from datetime import datetime, UTC
            item["updated_at"] = datetime.now(UTC).isoformat()

            # Replace item
            updated_item = await container.replace_item(item=item, body=item)
            
            # Record metrics
            self._record_cosmos_metrics("replace_item", start)
            
            logger.info(f"Updated trip: {trip_id_str}")
            return TripDocument(**updated_item).to_trip()

        except exceptions.CosmosResourceNotFoundError:
            self._record_cosmos_metrics("replace_item", start, "not_found")
            logger.debug(f"Trip not found for update: {trip_id_str}")
            return None
        except Exception as e:
            self._record_cosmos_metrics("replace_item", start, "error")
            raise

    async def delete(self, trip_id: UUID) -> bool:
        """
        Delete a trip.

        Args:
            trip_id: UUID of the trip to delete

        Returns:
            True if deleted, False if not found
        """
        container = await self._ensure_initialized()
        trip_id_str = str(trip_id)

        start = time.time()
        try:
            await container.delete_item(item=trip_id_str, partition_key=trip_id_str)
            
            # Record metrics
            self._record_cosmos_metrics("delete_item", start)
            
            logger.info(f"Deleted trip: {trip_id_str}")
            return True
        except exceptions.CosmosResourceNotFoundError:
            self._record_cosmos_metrics("delete_item", start, "not_found")
            logger.debug(f"Trip not found for deletion: {trip_id_str}")
            return False
        except Exception as e:
            self._record_cosmos_metrics("delete_item", start, "error")
            raise

    async def add_gallery_image(self, trip_id: UUID, image: GalleryImage) -> Trip | None:
        """
        Add an image to the trip gallery.

        Args:
            trip_id: UUID of the trip
            image: GalleryImage to add

        Returns:
            Updated Trip if found, None otherwise
        """
        container = await self._ensure_initialized()
        trip_id_str = str(trip_id)

        start = time.time()
        try:
            # Read current item
            item = await container.read_item(item=trip_id_str, partition_key=trip_id_str)

            # Add image to gallery
            if "gallery" not in item:
                item["gallery"] = []

            item["gallery"].append(image.model_dump(mode="json"))

            # Update timestamp
            from datetime import datetime, UTC
            item["updated_at"] = datetime.now(UTC).isoformat()

            # Replace item
            updated_item = await container.replace_item(item=item, body=item)
            
            # Record metrics
            self._record_cosmos_metrics("replace_item", start, method="add_gallery_image")
            
            logger.info(f"Added gallery image to trip: {trip_id_str}")
            return TripDocument(**updated_item).to_trip()

        except exceptions.CosmosResourceNotFoundError:
            self._record_cosmos_metrics("replace_item", start, "not_found")
            logger.debug(f"Trip not found for adding gallery image: {trip_id_str}")
            return None
        except Exception as e:
            self._record_cosmos_metrics("replace_item", start, "error")
            raise

    async def remove_gallery_image(self, trip_id: UUID, image_id: UUID) -> Trip | None:
        """
        Remove an image from the trip gallery.

        Args:
            trip_id: UUID of the trip
            image_id: UUID of the image to remove

        Returns:
            Updated Trip if found, None otherwise
        """
        container = await self._ensure_initialized()
        trip_id_str = str(trip_id)
        image_id_str = str(image_id)

        start = time.time()
        try:
            # Read current item
            item = await container.read_item(item=trip_id_str, partition_key=trip_id_str)

            # Remove image from gallery
            if "gallery" in item:
                item["gallery"] = [img for img in item["gallery"] if img.get("image_id") != image_id_str]

            # Update timestamp
            from datetime import datetime, UTC
            item["updated_at"] = datetime.now(UTC).isoformat()

            # Replace item
            updated_item = await container.replace_item(item=item, body=item)
            
            # Record metrics
            self._record_cosmos_metrics("replace_item", start, method="remove_gallery_image")
            
            logger.info(f"Removed gallery image {image_id_str} from trip: {trip_id_str}")
            return TripDocument(**updated_item).to_trip()

        except exceptions.CosmosResourceNotFoundError:
            self._record_cosmos_metrics("replace_item", start, "not_found")
            logger.debug(f"Trip not found for removing gallery image: {trip_id_str}")
            return None
        except Exception as e:
            self._record_cosmos_metrics("replace_item", start, "error")
            raise



    async def close(self):
        """Close underlying Cosmos DB client if initialized.

        Safe to call multiple times; logs and suppresses any close errors.
        """
        if self._client:
            try:
                await self._client.close()
                logger.info("Cosmos client closed")
            except Exception as e:
                logger.warning(f"Failed to close Cosmos client: {e}")
