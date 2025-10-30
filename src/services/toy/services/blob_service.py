"""Blob storage service for avatar images."""
import logging
import mimetypes
from io import BytesIO
from uuid import uuid4

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, ContentSettings
from fastapi import UploadFile

logger = logging.getLogger(__name__)


class BlobService:
    """Service for managing blob storage operations."""

    # Supported image formats
    ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
    MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5MB

    def __init__(self, storage_account_url: str, container_name: str):
        """
        Initialize blob service.

        Args:
            storage_account_url: Storage account URL
            container_name: Container name for avatars
        """
        self.storage_account_url = storage_account_url
        self.container_name = container_name
        self._client: BlobServiceClient | None = None
        self._container_client = None

    def _ensure_initialized(self):
        """Ensure blob service client and container are initialized."""
        if self._container_client is not None:
            return

        # Initialize client with managed identity
        credential = DefaultAzureCredential()
        self._client = BlobServiceClient(account_url=self.storage_account_url, credential=credential)

        # Get container (must be pre-created via infrastructure)
        self._container_client = self._client.get_container_client(self.container_name)
        logger.info(f"Connected to container '{self.container_name}'")

    async def upload_avatar(self, file: UploadFile, toy_id: str) -> str:
        """
        Upload avatar image to blob storage.

        Args:
            file: Uploaded file from FastAPI
            toy_id: Toy ID for naming the blob

        Returns:
            Blob name (reference for database)

        Raises:
            ValueError: If file type or size is invalid
        """
        self._ensure_initialized()

        # Validate content type
        content_type = file.content_type
        if content_type not in self.ALLOWED_CONTENT_TYPES:
            raise ValueError(
                f"Unsupported file type: {content_type}. Allowed: {', '.join(self.ALLOWED_CONTENT_TYPES)}"
            )

        # Read file content and validate size
        content = await file.read()
        if len(content) > self.MAX_FILE_SIZE_BYTES:
            raise ValueError(f"File size exceeds maximum of {self.MAX_FILE_SIZE_BYTES / 1024 / 1024}MB")

        # Generate blob name: {toy_id}/{uuid}.{extension}
        extension = mimetypes.guess_extension(content_type) or ".jpg"
        blob_name = f"{toy_id}/{uuid4()}{extension}"

        # Upload to blob storage
        blob_client = self._container_client.get_blob_client(blob_name)
        content_settings = ContentSettings(content_type=content_type)

        blob_client.upload_blob(
            data=content,
            content_settings=content_settings,
            overwrite=True,
        )

        logger.info(f"Uploaded avatar: {blob_name} ({len(content)} bytes)")
        return blob_name

    async def download_avatar(self, blob_name: str) -> tuple[bytes, str]:
        """
        Download avatar image from blob storage.

        Args:
            blob_name: Blob reference from database

        Returns:
            Tuple of (image bytes, content type)

        Raises:
            FileNotFoundError: If blob doesn't exist
        """
        self._ensure_initialized()

        blob_client = self._container_client.get_blob_client(blob_name)

        try:
            # Download blob
            download_stream = blob_client.download_blob()
            content = download_stream.readall()
            properties = blob_client.get_blob_properties()
            content_type = properties.content_settings.content_type or "application/octet-stream"

            logger.debug(f"Downloaded avatar: {blob_name} ({len(content)} bytes)")
            return content, content_type

        except Exception as e:
            logger.error(f"Failed to download blob {blob_name}: {e}")
            raise FileNotFoundError(f"Avatar not found: {blob_name}") from e

    async def delete_avatar(self, blob_name: str) -> bool:
        """
        Delete avatar image from blob storage.

        Args:
            blob_name: Blob reference from database

        Returns:
            True if deleted, False if not found
        """
        self._ensure_initialized()

        blob_client = self._container_client.get_blob_client(blob_name)

        try:
            blob_client.delete_blob()
            logger.info(f"Deleted avatar: {blob_name}")
            return True
        except Exception as e:
            logger.warning(f"Failed to delete blob {blob_name}: {e}")
            return False

    async def stream_avatar(self, blob_name: str) -> tuple[BytesIO, str]:
        """
        Stream avatar image from blob storage (memory efficient).

        Args:
            blob_name: Blob reference from database

        Returns:
            Tuple of (BytesIO stream, content type)

        Raises:
            FileNotFoundError: If blob doesn't exist
        """
        content, content_type = await self.download_avatar(blob_name)
        return BytesIO(content), content_type

    def close(self):
        """Close blob service client connection."""
        if self._client:
            self._client.close()
            logger.info("Blob service client closed")
