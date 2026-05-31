"""LinkedIn adapter — Playwright OG extraction (experimental/beta)."""
from typing import Any

from app.adapters.base import PlatformAdapter
from app.scrapers.extraction_fallbacks import extraction_fallbacks
from app.scrapers.browser_manager import browser_manager
from app.utils.logger import logger


class LinkedInAdapter(PlatformAdapter):
    """
    Fetches LinkedIn post analytics using Playwright OG tag extraction.

    ⚠️  EXPERIMENTAL — LinkedIn has strict bot-detection and requires login
    for most content. Metrics availability is limited for public content.
    Results may be incomplete or unavailable.
    """

    EXPERIMENTAL: bool = True
    BETA_NOTE: str = (
        "LinkedIn analytics are in BETA. LinkedIn aggressively blocks scraping "
        "and most content requires authentication. Only public post OG tags "
        "are extracted. Follower counts and engagement metrics may be unavailable. "
        "For production use, consider the official LinkedIn Marketing Developer Platform API."
    )

    async def fetch_post(self, identifier: str, post_type: str = "post") -> dict[str, Any]:
        """
        Fetch a LinkedIn post's publicly visible OG metadata.

        Args:
            identifier: LinkedIn post identifier (from URL slug).
            post_type: "post".

        Returns:
            Normalized dict with available fields (many may be empty due to LinkedIn restrictions).
        """
        logger.warning("⚠️  LinkedIn adapter is EXPERIMENTAL. %s", self.BETA_NOTE)

        url = f"https://www.linkedin.com/posts/{identifier}"

        og: dict = {}
        description = ""

        try:
            async with browser_manager.new_page() as page:
                await page.goto(url, wait_until="networkidle", timeout=45000)
                html = await page.content()
                og = extraction_fallbacks.extract_og_tags(html)
                description = og.get("og_description", "") or og.get(
                    "twitter_description", ""
                )
        except Exception as exc:
            logger.error("LinkedIn post fetch failed for %s: %s", identifier, exc)

        hashtags = extraction_fallbacks.extract_hashtags(description)

        return {
            "platform": "linkedin",
            "type": post_type,
            "platform_post_id": identifier,
            "url": url,
            "title": og.get("og_title"),
            "description": description[:500],
            "thumbnail_url": og.get("og_image"),
            "author": og.get("og_site_name", "linkedin"),
            "author_id": "",
            "author_followers": 0,
            "published_at": None,
            "views": 0,
            "likes": 0,
            "comments": 0,
            "shares": 0,
            "engagement_rate": 0.0,
            "virality_score": 0.0,
            "trend_score": 50.0,
            "hashtags": hashtags,
            "data_source": "playwright-og",
            "experimental": True,
            "note": self.BETA_NOTE,
        }

    async def fetch_profile(self, identifier: str) -> dict[str, Any]:
        """
        LinkedIn profile analytics are not supported in this adapter.

        Raises:
            NotImplementedError: Always, with a descriptive beta message.
        """
        raise NotImplementedError(
            f"LinkedIn profile analytics for '{identifier}' are not currently supported. "
            f"{self.BETA_NOTE} "
            "Profile data is behind LinkedIn's authentication wall and cannot be "
            "accessed without valid credentials."
        )


# Singleton instance
linkedin_adapter = LinkedInAdapter()

__all__ = ["LinkedInAdapter", "linkedin_adapter"]
