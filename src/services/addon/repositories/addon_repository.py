"""Repository for addon order data access in Cosmos DB."""
import logging
import time
from typing import Any
from uuid import UUID

from azure.cosmos.aio import ContainerProxy, CosmosClient, DatabaseProxy
from azure.cosmos import exceptions, PartitionKey
from azure.identity.aio import DefaultAzureCredential

from models import AddonOrder, AddonOrderDocument
from shared.observability.instrumentation import get_azure_metrics_meter, get_metric_attributes

logger = logging.getLogger(__name__)


class AddonRepository:
    """Repository for addon order CRUD operations in Cosmos DB."""

    def __init__(self, cosmos_endpoint: str, database_name: str, container_name: str):
        """
        Initialize the addon repository.

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
        
        # Azure metrics
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
        
        logger.debug(f"Cosmos {operation} took {duration:.4f}s (attrs: {attrs})")

    async def _ensure_initialized(self) -> ContainerProxy:
        """
        Ensure Cosmos client, database, and container are initialized.

        Returns:
            ContainerProxy instance ready for operations
        """
        if self._container is not None:
            return self._container

        credential = DefaultAzureCredential(exclude_shared_token_cache_credential=True)
        self._client = CosmosClient(self.cosmos_endpoint, credential=credential)

        self._database = self._client.get_database_client(self.database_name)
        logger.info(f"Connected to database '{self.database_name}'")

        self._container = self._database.get_container_client(self.container_name)
        logger.info(f"Connected to container '{self.container_name}'")

        return self._container

    async def create(self, order: AddonOrder) -> AddonOrder:
        """
        Create a new addon order in the database.

        Args:
            order: AddonOrder instance to create

        Returns:
            Created AddonOrder

        Raises:
            exceptions.CosmosResourceExistsError: If order with same ID already exists
        """
        container = await self._ensure_initialized()
        
        start_time = time.time()
        try:
            doc = AddonOrderDocument.from_order(order)
            doc_dict = doc.model_dump(by_alias=True, exclude_none=False)
            
            # Hierarchical partition key: [owner_id, trip_id]
            partition_key = [order.owner_id, str(order.trip_id)]
            
            result = await container.create_item(
                body=doc_dict,
                partition_key=partition_key
            )
            
            self._record_cosmos_metrics("create", start_time, method="create_item")
            logger.info(f"Created addon order {order.id} for trip {order.trip_id}")
            
            created_doc = AddonOrderDocument(**result)
            return created_doc.to_order()
        
        except exceptions.CosmosResourceExistsError:
            self._record_cosmos_metrics("create", start_time, status="conflict", method="create_item")
            raise
        except Exception as e:
            self._record_cosmos_metrics("create", start_time, status="error", method="create_item")
            logger.error(f"Failed to create addon order: {e}")
            raise

    async def get_by_id(self, order_id: str, owner_id: str, trip_id: UUID) -> AddonOrder | None:
        """
        Get an addon order by ID.

        Args:
            order_id: Order ID
            owner_id: Owner ID (for partition key)
            trip_id: Trip ID (for partition key)

        Returns:
            AddonOrder if found, None otherwise
        """
        container = await self._ensure_initialized()
        
        start_time = time.time()
        try:
            partition_key = [owner_id, str(trip_id)]
            
            result = await container.read_item(
                item=order_id,
                partition_key=partition_key
            )
            
            self._record_cosmos_metrics("read", start_time, method="read_item")
            
            doc = AddonOrderDocument(**result)
            return doc.to_order()
        
        except exceptions.CosmosResourceNotFoundError:
            self._record_cosmos_metrics("read", start_time, status="not_found", method="read_item")
            return None
        except Exception as e:
            self._record_cosmos_metrics("read", start_time, status="error", method="read_item")
            logger.error(f"Failed to read addon order {order_id}: {e}")
            raise

    async def get_by_idempotency_key(self, idempotency_key: str, owner_id: str, trip_id: UUID) -> AddonOrder | None:
        """
        Find an order by idempotency key within a trip.

        Args:
            idempotency_key: Idempotency key to search for
            owner_id: Owner ID (for partition key)
            trip_id: Trip ID (for partition key)

        Returns:
            AddonOrder if found, None otherwise
        """
        container = await self._ensure_initialized()
        
        start_time = time.time()
        try:
            # Query within the specific partition (owner_id, trip_id)
            query = """
                SELECT * FROM c 
                WHERE c.idempotency_key = @idempotency_key
            """
            
            partition_key = [owner_id, str(trip_id)]
            
            items = container.query_items(
                query=query,
                parameters=[
                    {"name": "@idempotency_key", "value": idempotency_key}
                ],
                partition_key=partition_key,
                enable_cross_partition_query=False
            )
            
            results = [item async for item in items]
            
            self._record_cosmos_metrics("query", start_time, method="query_items")
            
            if results:
                doc = AddonOrderDocument(**results[0])
                return doc.to_order()
            
            return None
        
        except Exception as e:
            self._record_cosmos_metrics("query", start_time, status="error", method="query_items")
            logger.error(f"Failed to query by idempotency key: {e}")
            raise

    async def list_by_trip(self, trip_id: UUID, owner_id: str, limit: int = 100, offset: int = 0) -> tuple[list[AddonOrder], int]:
        """
        List addon orders for a trip.

        Args:
            trip_id: Trip ID to filter by
            owner_id: Owner ID (for partition key)
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            Tuple of (list of orders, total count)
        """
        container = await self._ensure_initialized()
        
        start_time = time.time()
        try:
            # Query within the specific partition (owner_id, trip_id)
            query = """
                SELECT * FROM c 
                ORDER BY c.requested_at DESC
                OFFSET @offset LIMIT @limit
            """
            
            partition_key = [owner_id, str(trip_id)]
            
            items = container.query_items(
                query=query,
                parameters=[
                    {"name": "@offset", "value": offset},
                    {"name": "@limit", "value": limit}
                ],
                partition_key=partition_key,
                enable_cross_partition_query=False
            )
            
            results = [AddonOrderDocument(**item).to_order() async for item in items]
            
            # Get total count
            count_query = "SELECT VALUE COUNT(1) FROM c"
            count_items = container.query_items(
                query=count_query,
                partition_key=partition_key,
                enable_cross_partition_query=False
            )
            total = [count async for count in count_items][0] if results or offset == 0 else 0
            
            self._record_cosmos_metrics("query", start_time, method="query_items")
            
            return results, total
        
        except Exception as e:
            self._record_cosmos_metrics("query", start_time, status="error", method="query_items")
            logger.error(f"Failed to list addon orders for trip {trip_id}: {e}")
            raise

    async def update_status(
        self,
        order_id: str,
        owner_id: str,
        trip_id: UUID,
        status: str,
        fulfilled_at: Any = None,
        error_message: str | None = None,
        media_ref: dict | None = None
    ) -> AddonOrder | None:
        """
        Update the status of an addon order.

        Args:
            order_id: Order ID
            owner_id: Owner ID (for partition key)
            trip_id: Trip ID (for partition key)
            status: New status
            fulfilled_at: Fulfillment timestamp (optional)
            error_message: Error message if failed (optional)
            media_ref: Media reference if fulfilled (optional)

        Returns:
            Updated AddonOrder if found, None otherwise
        """
        container = await self._ensure_initialized()
        
        start_time = time.time()
        try:
            partition_key = [owner_id, str(trip_id)]
            
            # Read current document
            result = await container.read_item(
                item=order_id,
                partition_key=partition_key
            )
            
            # Update fields
            result['status'] = status
            if fulfilled_at is not None:
                result['fulfilled_at'] = fulfilled_at.isoformat() if hasattr(fulfilled_at, 'isoformat') else fulfilled_at
            if error_message is not None:
                result['error_message'] = error_message
            if media_ref is not None:
                result['media_ref'] = media_ref
            
            # Replace document
            updated = await container.replace_item(
                item=order_id,
                body=result,
                partition_key=partition_key
            )
            
            self._record_cosmos_metrics("update", start_time, method="replace_item")
            logger.info(f"Updated addon order {order_id} status to {status}")
            
            doc = AddonOrderDocument(**updated)
            return doc.to_order()
        
        except exceptions.CosmosResourceNotFoundError:
            self._record_cosmos_metrics("update", start_time, status="not_found", method="replace_item")
            return None
        except Exception as e:
            self._record_cosmos_metrics("update", start_time, status="error", method="replace_item")
            logger.error(f"Failed to update addon order {order_id}: {e}")
            raise

    async def close(self):
        """Close the Cosmos client connection."""
        if self._client:
            await self._client.close()
            logger.info("Closed Cosmos DB client")
