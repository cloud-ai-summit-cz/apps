"""Service for generating stories using Azure OpenAI."""
import logging
import asyncio
from datetime import datetime, UTC
from typing import Any, Dict
from uuid import UUID

import httpx
from azure.identity import DefaultAzureCredential
from openai import AzureOpenAI, RateLimitError, APIError

from models.story import Story, StorySection, StoryStatus

logger = logging.getLogger(__name__)


class StoryGenerationService:
    """
    Service for generating AI-powered story narratives.
    
    Fetches context from Trip, Toy, and Geo services, assembles prompts,
    and calls Azure OpenAI for story generation.
    """

    def __init__(
        self,
        azure_openai_endpoint: str,
        azure_openai_deployment: str,
        azure_openai_api_version: str,
        trip_service_url: str,
        toy_service_url: str,
        geo_service_url: str,
    ):
        """
        Initialize the Story Generation service.

        Args:
            azure_openai_endpoint: Azure OpenAI endpoint URL
            azure_openai_deployment: Deployment/model name
            azure_openai_api_version: API version
            trip_service_url: URL of the Trip service
            toy_service_url: URL of the Toy service
            geo_service_url: URL of the Geo service
        """
        self.azure_openai_endpoint = azure_openai_endpoint
        self.azure_openai_deployment = azure_openai_deployment
        self.trip_service_url = trip_service_url
        self.toy_service_url = toy_service_url
        self.geo_service_url = geo_service_url

        # Initialize Azure OpenAI client with Managed Identity
        credential = DefaultAzureCredential()
        self.openai_client = AzureOpenAI(
            azure_endpoint=azure_openai_endpoint,
            azure_deployment=azure_openai_deployment,
            api_version=azure_openai_api_version,
            azure_ad_token_provider=lambda: credential.get_token(
                "https://cognitiveservices.azure.com/.default"
            ).token,
        )

        logger.info(
            "StoryGenerationService initialized",
            extra={
                "endpoint": azure_openai_endpoint,
                "deployment": azure_openai_deployment,
            },
        )

    async def fetch_trip_context(self, trip_id: str, owner_token: str) -> Dict[str, Any] | None:
        """
        Fetch trip details from Trip service.

        Args:
            trip_id: Trip ID
            owner_token: Bearer token for authentication

        Returns:
            Trip data dict or None if not found
        """
        url = f"{self.trip_service_url}/api/trips/{trip_id}"
        headers = {"Authorization": f"Bearer {owner_token}"}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, timeout=10.0)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.warning(
                "Failed to fetch trip context",
                extra={"trip_id": trip_id, "error": str(e)},
            )
            return None

    async def fetch_toy_context(self, toy_id: str, owner_token: str) -> Dict[str, Any] | None:
        """
        Fetch toy details from Toy service.

        Args:
            toy_id: Toy ID
            owner_token: Bearer token for authentication

        Returns:
            Toy data dict or None if not found
        """
        url = f"{self.toy_service_url}/api/toys/{toy_id}"
        headers = {"Authorization": f"Bearer {owner_token}"}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, timeout=10.0)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.warning(
                "Failed to fetch toy context",
                extra={"toy_id": toy_id, "error": str(e)},
            )
            return None

    async def fetch_geo_context(self, trip_id: str, story_date: str) -> list[Dict[str, Any]]:
        """
        Fetch recent location data from Geo service.

        Args:
            trip_id: Trip ID
            story_date: Story date to fetch locations for

        Returns:
            List of location data dicts
        """
        # For now, return empty list as Geo service integration is optional
        # TODO: Implement when Geo service is available
        return []

    def assemble_prompt(
        self,
        trip_data: Dict[str, Any] | None,
        toy_data: Dict[str, Any] | None,
        geo_data: list[Dict[str, Any]],
        story_date: str,
    ) -> str:
        """
        Assemble prompt for Azure OpenAI from context data.

        Args:
            trip_data: Trip context
            toy_data: Toy context
            geo_data: Location data
            story_date: Date for the story

        Returns:
            Assembled prompt string
        """
        toy_name = toy_data.get("name", "the toy") if toy_data else "the toy"
        trip_location = trip_data.get("location_name", "an unknown destination") if trip_data else "an unknown destination"
        trip_title = trip_data.get("title", "a trip") if trip_data else "a trip"

        prompt = f"""Generate a whimsical and engaging daily story recap for {toy_name}'s adventure on {story_date}.

Trip: {trip_title}
Location: {trip_location}
Date: {story_date}

The story should be creative, fun, and suitable for all ages. Include:
1. A brief summary (1-2 sentences) of the day's adventure
2. 2-3 sections describing different parts of the day (Morning, Afternoon, Evening)

Each section should be 2-3 sentences long and capture the magical experience of a stuffed toy exploring the world.

Format the response as JSON with this structure:
{{
    "summary": "Brief 1-2 sentence summary",
    "sections": [
        {{"title": "Morning", "content": "Morning adventure description"}},
        {{"title": "Afternoon", "content": "Afternoon adventure description"}},
        {{"title": "Evening", "content": "Evening adventure description"}}
    ]
}}
"""

        return prompt

    async def generate_story(
        self,
        owner_id: str,
        trip_id: UUID,
        story_date: str,
        owner_token: str | None = None,
    ) -> Story:
        """
        Generate a story for a trip on a specific date.

        Args:
            owner_id: Owner ID (Entra OID)
            trip_id: Trip ID
            story_date: Date for the story (YYYY-MM-DD)
            owner_token: Optional bearer token for context fetching

        Returns:
            Generated Story model

        Raises:
            Exception: If generation fails after retries
        """
        story_id = f"story_{story_date}"

        logger.info(
            "Starting story generation",
            extra={
                "story_id": story_id,
                "owner_id": owner_id,
                "trip_id": str(trip_id),
                "story_date": story_date,
            },
        )

        # Initialize story with pending status
        story = Story(
            id=story_id,
            owner_id=owner_id,
            trip_id=trip_id,
            story_date=story_date,
            status=StoryStatus.IN_PROGRESS,
            summary="",
            sections=[],
        )

        try:
            # Fetch trip data first
            trip_data = await self.fetch_trip_context(str(trip_id), owner_token or "")
            
            # Fetch toy data if we have trip data
            toy_data = None
            if trip_data and "toy_id" in trip_data:
                toy_data = await self.fetch_toy_context(trip_data["toy_id"], owner_token or "")

            geo_data = await self.fetch_geo_context(str(trip_id), story_date)

            # Assemble prompt
            prompt = self.assemble_prompt(trip_data, toy_data, geo_data, story_date)

            # Call Azure OpenAI with retry logic
            max_retries = 3
            retry_delay = 1.0

            for attempt in range(max_retries):
                try:
                    response = await self._call_openai(prompt)
                    
                    # Parse response (expecting JSON)
                    import json
                    result = json.loads(response)
                    
                    story.summary = result.get("summary", "")
                    story.sections = [
                        StorySection(title=s["title"], content=s["content"])
                        for s in result.get("sections", [])
                    ]
                    story.status = StoryStatus.COMPLETED
                    story.updated_at = datetime.now(UTC)

                    logger.info(
                        "Story generation completed",
                        extra={
                            "story_id": story_id,
                            "attempt": attempt + 1,
                        },
                    )
                    break

                except (RateLimitError, APIError) as e:
                    if attempt < max_retries - 1:
                        logger.warning(
                            "OpenAI call failed, retrying",
                            extra={
                                "story_id": story_id,
                                "attempt": attempt + 1,
                                "error": str(e),
                            },
                        )
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                    else:
                        raise

        except Exception as e:
            logger.error(
                "Story generation failed",
                extra={
                    "story_id": story_id,
                    "error": str(e),
                },
            )
            story.status = StoryStatus.FAILED
            story.error_message = str(e)
            story.updated_at = datetime.now(UTC)

        return story

    async def _call_openai(self, prompt: str) -> str:
        """
        Call Azure OpenAI API.

        Args:
            prompt: Prompt text

        Returns:
            Generated text response
        """
        # Run synchronous OpenAI client in executor to avoid blocking
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.openai_client.chat.completions.create(
                model=self.azure_openai_deployment,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a creative storyteller generating whimsical adventure stories for stuffed toys traveling the world.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=1000,
                response_format={"type": "json_object"},
            ),
        )

        return response.choices[0].message.content
