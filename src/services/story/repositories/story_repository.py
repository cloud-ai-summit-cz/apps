"""Repository for Story data access in Cosmos DB."""
import logging
from typing import List

from azure.cosmos import CosmosClient, PartitionKey
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from azure.identity import DefaultAzureCredential

from models.story import Story, StoryDocument

logger = logging.getLogger(__name__)


class StoryRepository:
    """
    Repository for managing Story documents in Cosmos DB.
    
    Uses hierarchical partition key (ownerId, tripId) for owner isolation
    and high cardinality to prevent hot partitions.
    """

    def __init__(
        self,
        cosmos_endpoint: str,
        database_name: str,
        container_name: str,
    ):
        """
        Initialize the Story repository.

        Args:
            cosmos_endpoint: Cosmos DB account endpoint URL
            database_name: Name of the database
            container_name: Name of the container
        """
        self.cosmos_endpoint = cosmos_endpoint
        self.database_name = database_name
        self.container_name = container_name

        # Use Managed Identity for authentication
        credential = DefaultAzureCredential()
        self.client = CosmosClient(cosmos_endpoint, credential=credential)

        self.database = self.client.get_database_client(database_name)
        self.container = self.database.get_container_client(container_name)

        logger.info(
            "StoryRepository initialized",
            extra={
                "database": database_name,
                "container": container_name,
            },
        )

    async def close(self):
        """Close the Cosmos DB client."""
        pass  # CosmosClient doesn't require explicit cleanup

    def create_story(self, story: Story) -> Story:
        """
        Create a new story document in Cosmos DB.

        Args:
            story: Story model to persist

        Returns:
            Created Story model

        Raises:
            Exception: If creation fails
        """
        doc = StoryDocument.from_story(story)
        doc_dict = doc.model_dump()

        logger.info(
            "Creating story",
            extra={
                "story_id": story.id,
                "owner_id": story.owner_id,
                "trip_id": str(story.trip_id),
            },
        )

        # Cosmos DB expects partition key as array for hierarchical keys
        created_doc = self.container.create_item(
            body=doc_dict,
            enable_automatic_id_generation=False,
        )

        return StoryDocument(**created_doc).to_story()

    def update_story(self, story: Story) -> Story:
        """
        Update an existing story document in Cosmos DB.

        Args:
            story: Story model with updated fields

        Returns:
            Updated Story model

        Raises:
            CosmosResourceNotFoundError: If story doesn't exist
        """
        doc = StoryDocument.from_story(story)
        doc_dict = doc.model_dump()

        logger.info(
            "Updating story",
            extra={
                "story_id": story.id,
                "owner_id": story.owner_id,
                "trip_id": str(story.trip_id),
            },
        )

        updated_doc = self.container.replace_item(
            item=story.id,
            body=doc_dict,
        )

        return StoryDocument(**updated_doc).to_story()

    def get_story(self, story_id: str, owner_id: str, trip_id: str) -> Story | None:
        """
        Retrieve a story by ID.

        Args:
            story_id: Unique story identifier
            owner_id: Owner ID (for partition key)
            trip_id: Trip ID (for partition key)

        Returns:
            Story model if found, None otherwise
        """
        try:
            logger.debug(
                "Fetching story",
                extra={
                    "story_id": story_id,
                    "owner_id": owner_id,
                    "trip_id": trip_id,
                },
            )

            doc = self.container.read_item(
                item=story_id,
                partition_key=[owner_id, trip_id],
            )

            return StoryDocument(**doc).to_story()

        except CosmosResourceNotFoundError:
            logger.debug("Story not found", extra={"story_id": story_id})
            return None

    def list_stories_by_trip(
        self, owner_id: str, trip_id: str, limit: int = 100
    ) -> List[Story]:
        """
        List all stories for a trip.

        Args:
            owner_id: Owner ID (for partition key)
            trip_id: Trip ID (for partition key)
            limit: Maximum number of stories to return

        Returns:
            List of Story models
        """
        logger.debug(
            "Listing stories for trip",
            extra={
                "owner_id": owner_id,
                "trip_id": trip_id,
                "limit": limit,
            },
        )

        # Query within partition (owner_id, trip_id)
        query = "SELECT * FROM c WHERE c.owner_id = @owner_id AND c.trip_id = @trip_id ORDER BY c.created_at DESC"
        parameters = [
            {"name": "@owner_id", "value": owner_id},
            {"name": "@trip_id", "value": trip_id},
        ]

        items = self.container.query_items(
            query=query,
            parameters=parameters,
            partition_key=[owner_id, trip_id],
            max_item_count=limit,
        )

        stories = [StoryDocument(**item).to_story() for item in items]

        logger.info(
            "Listed stories",
            extra={
                "owner_id": owner_id,
                "trip_id": trip_id,
                "count": len(stories),
            },
        )

        return stories
