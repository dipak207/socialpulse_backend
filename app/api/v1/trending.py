"""API route: GET /trending — top hashtags and viral posts."""
from fastapi import APIRouter, Query, Request
from sqlalchemy import select, desc, func
from typing import Optional

from app.db.session import AsyncSessionLocal
from app.models.hashtag_trends import HashtagTrend
from app.models.analyzed_posts import AnalyzedPost
from app.utils.rate_limiter import limiter
from app.utils.logger import logger

router = APIRouter()

_VALID_PLATFORMS = {"youtube", "instagram", "twitter", "tiktok", "linkedin"}


@router.get("/trending")
@limiter.limit("60/minute")
async def get_trending(
    request: Request,
    platform: Optional[str] = Query(None, description="Filter by platform"),
    limit: int = Query(20, ge=1, le=100, description="Max number of results"),
) -> dict:
    """
    Retrieve trending hashtags and viral posts from the database.

    Args:
        platform: Optional platform filter (youtube, instagram, twitter, tiktok, linkedin).
        limit: Number of results to return (1-100).

    Returns:
        Dict with 'hashtags' and 'viral_posts' lists.
    """
    if platform and platform.lower() not in _VALID_PLATFORMS:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=422,
            detail=f"Invalid platform. Must be one of: {', '.join(_VALID_PLATFORMS)}",
        )

    platform_filter = platform.lower() if platform else None

    async with AsyncSessionLocal() as session:
        # --- Top hashtags ---
        hashtag_query = select(HashtagTrend).order_by(
            desc(HashtagTrend.occurrence_count)
        )
        if platform_filter:
            hashtag_query = hashtag_query.where(
                HashtagTrend.platform == platform_filter
            )
        hashtag_query = hashtag_query.limit(limit)

        hashtag_result = await session.execute(hashtag_query)
        hashtag_rows = hashtag_result.scalars().all()

        hashtags = [
            {
                "hashtag": row.hashtag,
                "platform": row.platform,
                "occurrence_count": row.occurrence_count,
                "avg_engagement_rate": float(row.avg_engagement_rate or 0),
                "last_seen_at": row.last_seen_at.isoformat() if row.last_seen_at else None,
            }
            for row in hashtag_rows
        ]

        # --- Viral posts (top by virality_score) ---
        post_query = select(AnalyzedPost).order_by(
            desc(AnalyzedPost.virality_score)
        )
        if platform_filter:
            post_query = post_query.where(AnalyzedPost.platform == platform_filter)
        post_query = post_query.limit(limit)

        post_result = await session.execute(post_query)
        post_rows = post_result.scalars().all()

        viral_posts = [
            {
                "platform": row.platform,
                "platform_post_id": row.platform_post_id,
                "post_type": row.post_type,
                "url": row.url,
                "title": row.title,
                "thumbnail_url": row.thumbnail_url,
                "author": row.author,
                "views": row.views,
                "likes": row.likes,
                "comments": row.comments,
                "shares": row.shares,
                "engagement_rate": float(row.engagement_rate or 0),
                "virality_score": float(row.virality_score or 0),
                "trend_score": float(row.trend_score or 0),
                "hashtags": row.hashtags or [],
                "published_at": row.published_at.isoformat() if row.published_at else None,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in post_rows
        ]

    logger.info(
        "Trending: returned %d hashtags and %d viral posts (platform=%s)",
        len(hashtags),
        len(viral_posts),
        platform_filter or "all",
    )

    return {
        "platform": platform_filter or "all",
        "hashtags": hashtags,
        "viral_posts": viral_posts,
        "total_hashtags": len(hashtags),
        "total_viral_posts": len(viral_posts),
    }
