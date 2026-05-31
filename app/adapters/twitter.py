"""Twitter/X adapter — Playwright-based scraping (no official API required)."""
import re
from datetime import datetime, timezone
from typing import Any, Optional

from app.adapters.base import PlatformAdapter
from app.analytics.engine import analytics_engine
from app.scrapers.browser_manager import browser_manager
from app.scrapers.extraction_fallbacks import extraction_fallbacks
from app.utils.logger import logger

# Regex patterns to extract metrics from Twitter page text
_VIEWS_RE = re.compile(r"([\d,]+(?:\.\d+)?[KkMmBb]?)\s+[Vv]iews?")
_LIKES_RE = re.compile(r"([\d,]+(?:\.\d+)?[KkMmBb]?)\s+[Ll]ike")
_REPLIES_RE = re.compile(r"([\d,]+(?:\.\d+)?[KkMmBb]?)\s+[Rr]epl(?:y|ies)")
_REPOSTS_RE = re.compile(r"([\d,]+(?:\.\d+)?[KkMmBb]?)\s+[Rr]epost")
_FOLLOWERS_RE = re.compile(r"([\d,]+(?:\.\d+)?[KkMmBb]?)\s+[Ff]ollower")
_FOLLOWING_RE = re.compile(r"([\d,]+(?:\.\d+)?[KkMmBb]?)\s+[Ff]ollowing")


class TwitterAdapter(PlatformAdapter):
    """
    Fetches Twitter/X post and profile analytics using Playwright.
    
    NOTE: Twitter/X does not have a free public API. 
    This adapter uses browser automation to extract publicly visible metrics.
    """

    async def fetch_post(self, identifier: str, post_type: str = "post") -> dict[str, Any]:
        """
        Fetch a Twitter/X post's publicly visible metrics.

        Args:
            identifier: Tweet ID (numeric string).
            post_type: "post".
        """
        url = f"https://x.com/i/web/status/{identifier}"

        async with browser_manager.new_page() as page:
            try:
                await page.goto(url, wait_until="networkidle", timeout=45000)
                # Wait for tweet article to appear
                await page.wait_for_selector("article", timeout=15000)
            except Exception as exc:
                logger.warning("Twitter page load issue for %s: %s", identifier, exc)

            html = await page.content()
            text = await page.inner_text("body")

        og = extraction_fallbacks.extract_og_tags(html)

        # Extract metrics from page text using regex
        views = self._extract_metric(_VIEWS_RE, text)
        likes = self._extract_metric(_LIKES_RE, text)
        replies = self._extract_metric(_REPLIES_RE, text)
        reposts = self._extract_metric(_REPOSTS_RE, text)

        description = og.get("og_description", "") or og.get("twitter_description", "")
        hashtags = extraction_fallbacks.extract_hashtags(description)

        # Attempt to get author followers from profile (not always on post page)
        author_followers = 0
        author_match = re.search(r'@([\w]+)', description)
        username = author_match.group(1) if author_match else "unknown"

        er = analytics_engine.engagement_rate(
            likes, replies, reposts, max(author_followers, 1)
        )
        virality = analytics_engine.virality_score(
            likes, replies, reposts, max(views, 1), max(author_followers, 1)
        )

        return {
            "platform": "twitter",
            "type": post_type,
            "platform_post_id": identifier,
            "url": f"https://x.com/i/web/status/{identifier}",
            "title": og.get("og_title"),
            "description": description[:500],
            "thumbnail_url": og.get("og_image") or og.get("twitter_image"),
            "author": username,
            "author_id": username,
            "author_followers": author_followers,
            "published_at": None,
            "views": views,
            "likes": likes,
            "comments": replies,
            "shares": reposts,
            "engagement_rate": er,
            "virality_score": virality,
            "trend_score": 50.0,
            "hashtags": hashtags,
            "data_source": "playwright",
        }

    async def fetch_profile(self, identifier: str) -> dict[str, Any]:
        """
        Fetch a Twitter/X profile's publicly visible metrics.

        Args:
            identifier: Twitter/X username (without @).
        """
        url = f"https://x.com/{identifier}"

        async with browser_manager.new_page() as page:
            try:
                await page.goto(url, wait_until="networkidle", timeout=45000)
                await page.wait_for_selector('[data-testid="UserName"]', timeout=15000)
            except Exception as exc:
                logger.warning("Twitter profile page load issue for %s: %s", identifier, exc)

            html = await page.content()
            text = await page.inner_text("body")

        og = extraction_fallbacks.extract_og_tags(html)

        followers = self._extract_metric(_FOLLOWERS_RE, text)
        following = self._extract_metric(_FOLLOWING_RE, text)

        description = og.get("og_description", "") or og.get("twitter_description", "")

        return {
            "platform": "twitter",
            "platform_user_id": identifier,
            "username": identifier,
            "display_name": og.get("og_title", identifier),
            "avatar_url": og.get("og_image") or og.get("twitter_image"),
            "bio": description[:500],
            "verified": False,
            "followers": followers,
            "following": following,
            "posts_count": 0,
            "avg_engagement_rate": 0.0,
            "posting_frequency": 0.0,
            "top_posts": [],
            "hashtags": [],
            "data_source": "playwright",
        }

    @staticmethod
    def _extract_metric(pattern: re.Pattern, text: str) -> int:
        """Extract a metric value using a compiled regex pattern."""
        m = pattern.search(text)
        if m:
            return extraction_fallbacks.extract_number(m.group(1))
        return 0


# Singleton instance
twitter_adapter = TwitterAdapter()

__all__ = ["TwitterAdapter", "twitter_adapter"]
