"""Core analysis service — orchestrates platform adapters, caching, and insights."""
import uuid
from typing import Any, Optional

from app.adapters.base import PlatformAdapter
from app.adapters.youtube import youtube_adapter
from app.adapters.instagram import instagram_adapter
from app.adapters.twitter import twitter_adapter
from app.adapters.tiktok import tiktok_adapter
from app.adapters.linkedin import linkedin_adapter
from app.analytics.engine import analytics_engine
from app.analytics.insights import insights_generator
from app.services.cache_service import (
    get_cached,
    set_cached,
    set_job_status,
    make_cache_key,
)
from app.utils.url_detector import URLDetector
from app.utils.logger import logger

# Platform adapter registry
ADAPTERS: dict[str, PlatformAdapter] = {
    "youtube": youtube_adapter,
    "instagram": instagram_adapter,
    "twitter": twitter_adapter,
    "tiktok": tiktok_adapter,
    "linkedin": linkedin_adapter,
}

# URL detector
detector = URLDetector()


def create_job_id() -> str:
    """Generate a unique job identifier."""
    return str(uuid.uuid4())


async def analyze_post_async(job_id: str, url: str, timeframe: str = "30d") -> None:
    """
    Full pipeline for analyzing a single post asynchronously.

    Progress updates are written to Redis under the job_id key.

    Args:
        job_id: Unique identifier for this analysis job.
        url: Public URL of the post to analyze.
        timeframe: Analysis timeframe string (unused currently, reserved for future use).
    """
    try:
        # Step 1: Detect platform
        await set_job_status(job_id, "fetching", 10, "Detecting platform...")
        detection = detector.detect(url)
        platform = detection["platform"]
        content_type = detection["type"]
        identifier = detection["identifier"]

        logger.info(
            "Job %s: Detected %s %s (%s)", job_id, platform, content_type, identifier
        )

        # Step 2: Check Redis cache
        cache_key = make_cache_key("post", platform, identifier, timeframe)
        cached = await get_cached(cache_key)
        if cached:
            logger.info("Job %s: Cache hit for %s/%s", job_id, platform, identifier)
            await set_job_status(
                job_id, "completed", 100, "Done (cached)", result=cached
            )
            return

        # Step 3: Fetch from adapter
        await set_job_status(job_id, "fetching", 25, "Fetching data from platform...")
        adapter = ADAPTERS.get(platform)
        if not adapter:
            raise ValueError(f"No adapter for platform: {platform}")

        raw = await adapter.fetch_post(identifier, post_type=content_type)

        # Step 4: Compute insights
        await set_job_status(job_id, "computing", 80, "Computing insights...")

        # Parse published_at if available
        published_at = None
        if raw.get("published_at"):
            try:
                from datetime import datetime
                published_at = datetime.fromisoformat(raw["published_at"])
            except ValueError:
                pass

        post_insights = insights_generator.for_post(
            platform=platform,
            views=raw.get("views", 0),
            likes=raw.get("likes", 0),
            comments=raw.get("comments", 0),
            shares=raw.get("shares", 0),
            engagement_rate=raw.get("engagement_rate", 0.0),
            virality_score=raw.get("virality_score", 0.0),
            followers=raw.get("author_followers", 0),
            published_at=published_at,
        )

        # Step 5: Build result payload
        result = {
            "platform": platform,
            "type": content_type,
            "url": url,
            "metadata": {
                "title": raw.get("title"),
                "description": raw.get("description"),
                "thumbnail_url": raw.get("thumbnail_url"),
                "author": raw.get("author", "Unknown"),
                "published_at": raw.get("published_at"),
                "platform": platform,
                "post_type": content_type,
                "url": url,
                "hashtags": raw.get("hashtags", []),
            },
            "metrics": {
                "views": raw.get("views", 0),
                "likes": raw.get("likes", 0),
                "comments": raw.get("comments", 0),
                "shares": raw.get("shares", 0),
                "engagement_rate": raw.get("engagement_rate", 0.0),
                "virality_score": raw.get("virality_score", 0.0),
                "trend_score": raw.get("trend_score", 50.0),
                "author_followers": raw.get("author_followers"),
            },
            "hashtags": raw.get("hashtags", []),
            "insights": post_insights,
            "history": [],  # TODO: populate from DB snapshots
            "data_source": raw.get("data_source", "unknown"),
        }

        # Step 6: Cache result
        await set_cached(cache_key, result)

        # Step 7: Complete
        await set_job_status(job_id, "completed", 100, "Done", result=result)
        logger.info("Job %s: Post analysis completed successfully.", job_id)

    except Exception as exc:
        logger.error("Job %s: Analysis failed: %s", job_id, exc, exc_info=True)
        await set_job_status(
            job_id,
            "failed",
            0,
            "Analysis failed",
            error=str(exc),
        )


async def analyze_profile_async(job_id: str, url: str) -> None:
    """
    Full pipeline for analyzing a social media profile asynchronously.

    Args:
        job_id: Unique identifier for this analysis job.
        url: Public URL of the profile to analyze.
    """
    try:
        # Step 1: Detect platform
        await set_job_status(job_id, "fetching", 10, "Detecting platform...")
        detection = detector.detect(url)
        platform = detection["platform"]
        content_type = detection["type"]
        identifier = detection["identifier"]

        logger.info(
            "Job %s: Detected %s profile (%s)", job_id, platform, identifier
        )

        # Step 2: Cache check
        cache_key = make_cache_key("profile", platform, identifier)
        cached = await get_cached(cache_key)
        if cached:
            logger.info("Job %s: Cache hit for profile %s/%s", job_id, platform, identifier)
            await set_job_status(
                job_id, "completed", 100, "Done (cached)", result=cached
            )
            return

        # Step 3: Fetch
        await set_job_status(job_id, "fetching", 25, "Fetching profile data...")
        adapter = ADAPTERS.get(platform)
        if not adapter:
            raise ValueError(f"No adapter for platform: {platform}")

        raw = await adapter.fetch_profile(identifier)

        # Step 4: Insights
        await set_job_status(job_id, "computing", 80, "Generating insights...")
        profile_insights = insights_generator.for_profile(
            platform=platform,
            followers=raw.get("followers", 0),
            avg_engagement_rate=raw.get("avg_engagement_rate", 0.0),
            posting_frequency=raw.get("posting_frequency", 0.0),
            posts_count=raw.get("posts_count", 0),
        )

        # Step 5: Build result
        result = {
            "platform": platform,
            "username": raw.get("username", identifier),
            "display_name": raw.get("display_name"),
            "avatar_url": raw.get("avatar_url"),
            "bio": raw.get("bio"),
            "url": url,
            "metrics": {
                "followers": raw.get("followers", 0),
                "following": raw.get("following"),
                "posts_count": raw.get("posts_count", 0),
                "avg_engagement_rate": raw.get("avg_engagement_rate", 0.0),
                "posting_frequency": raw.get("posting_frequency", 0.0),
                "verified": raw.get("verified", False),
                "avg_views": _avg(raw.get("top_posts", []), "views"),
                "avg_likes": _avg(raw.get("top_posts", []), "likes"),
                "avg_comments": _avg(raw.get("top_posts", []), "comments"),
                "avg_shares": _avg(raw.get("top_posts", []), "shares"),
            },
            "top_posts": raw.get("top_posts", []),
            "hashtags": raw.get("hashtags", []),
            "insights": profile_insights,
            "data_source": raw.get("data_source", "unknown"),
        }

        # Step 6: Cache
        await set_cached(cache_key, result, ttl_seconds=1800)

        # Step 7: Complete
        await set_job_status(job_id, "completed", 100, "Done", result=result)
        logger.info("Job %s: Profile analysis completed.", job_id)

    except Exception as exc:
        logger.error("Job %s: Profile analysis failed: %s", job_id, exc, exc_info=True)
        await set_job_status(
            job_id,
            "failed",
            0,
            "Profile analysis failed",
            error=str(exc),
        )


def _avg(items: list[dict], key: str) -> int:
    """Compute integer average of a field across a list of dicts."""
    values = [item.get(key, 0) for item in items if item.get(key) is not None]
    if not values:
        return 0
    return int(sum(values) / len(values))


__all__ = [
    "ADAPTERS",
    "detector",
    "create_job_id",
    "analyze_post_async",
    "analyze_profile_async",
]
