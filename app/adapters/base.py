"""Abstract base class for all platform adapters."""
from abc import ABC, abstractmethod
from typing import Any


class PlatformAdapter(ABC):
    """
    Abstract base class that all platform-specific adapters must implement.

    Each adapter is responsible for fetching raw data from its respective
    platform and normalizing it into the common SocialPulse schema.
    """

    @abstractmethod
    async def fetch_post(self, identifier: str, post_type: str = "post") -> dict[str, Any]:
        """
        Fetch and normalize data for a single post / video / reel.

        Args:
            identifier: Platform-specific post/video ID or shortcode.
            post_type: Content type (e.g. "video", "post", "reel", "shorts").

        Returns:
            Normalized dict with keys matching PostAnalysisResponse fields.

        Raises:
            ValueError: If the identifier is invalid.
            RuntimeError: If fetching fails after all retries.
        """
        ...

    @abstractmethod
    async def fetch_profile(self, identifier: str) -> dict[str, Any]:
        """
        Fetch and normalize data for a user profile / channel.

        Args:
            identifier: Platform-specific username, handle, or channel ID.

        Returns:
            Normalized dict with keys matching ProfileAnalysisResponse fields.

        Raises:
            ValueError: If the identifier is invalid.
            RuntimeError: If fetching fails after all retries.
        """
        ...


__all__ = ["PlatformAdapter"]
