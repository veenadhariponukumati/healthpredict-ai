"""Object Storage Protocol interface.

Abstraction over blob/object storage for ML artifacts, model files, and backups.
Implementations: AzureBlobStorage, S3Storage, GCSStorage, LocalFileStorage.
"""

from __future__ import annotations

from typing import Protocol


class ObjectStorageProtocol(Protocol):
    """Blob/object storage for ML artifacts, model files, and backups."""

    async def upload(self, local_path: str, remote_key: str) -> str:
        """Upload a file. Returns the remote URI."""
        ...

    async def download(self, remote_key: str, local_path: str) -> str:
        """Download a file. Returns the local path."""
        ...

    async def delete(self, remote_key: str) -> None:
        """Delete a stored object."""
        ...

    async def list(self, prefix: str) -> list[str]:
        """List objects under a prefix."""
        ...

    async def generate_signed_url(
        self, remote_key: str, expiry_seconds: int
    ) -> str:
        """Generate a time-limited access URL."""
        ...

    async def health(self) -> bool:
        """Check storage backend availability."""
        ...