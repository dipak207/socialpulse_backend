"""APScheduler background jobs for cache cleanup and hashtag trend refresh."""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timezone

from app.utils.logger import logger

# Global scheduler instance
_scheduler = AsyncIOScheduler(timezone="UTC")


async def cleanup_expired_cache() -> None:
    """
    Delete expired CachedMetric rows from the database.

    Runs daily at 03:00 UTC.
    """
    try:
        from app.db.session import AsyncSessionLocal
        from app.models.cached_metrics import CachedMetric
        from sqlalchemy import delete

        now = datetime.now(timezone.utc)
        async with AsyncSessionLocal() as session:
            stmt = delete(CachedMetric).where(CachedMetric.expires_at < now)
            result = await session.execute(stmt)
            await session.commit()
            deleted = result.rowcount
            logger.info(
                "Cache cleanup: deleted %d expired CachedMetric rows (ran at %s).",
                deleted,
                now.isoformat(),
            )
    except Exception as exc:
        logger.error("Cache cleanup job failed: %s", exc, exc_info=True)


async def refresh_trending_hashtags() -> None:
    """
    Refresh HashtagTrend table from recent AnalyzedPost data.

    Reads hashtags from posts created in the last 7 days and upserts
    occurrence counts + average engagement rates.

    Runs every 6 hours.
    """
    try:
        from app.db.session import AsyncSessionLocal
        from app.models.analyzed_posts import AnalyzedPost
        from app.models.hashtag_trends import HashtagTrend
        from sqlalchemy import select, func
        from datetime import timedelta

        cutoff = datetime.now(timezone.utc) - timedelta(days=7)

        async with AsyncSessionLocal() as session:
            # Fetch recent posts with hashtags
            stmt = (
                select(AnalyzedPost)
                .where(AnalyzedPost.created_at >= cutoff)
                .where(AnalyzedPost.hashtags.isnot(None))
            )
            result = await session.execute(stmt)
            posts = result.scalars().all()

            if not posts:
                logger.info("Hashtag refresh: no recent posts found.")
                return

            # Aggregate hashtag occurrences and engagement rates per platform
            hashtag_data: dict[tuple[str, str], dict] = {}
            for post in posts:
                platform = post.platform
                er = float(post.engagement_rate or 0)
                for tag in (post.hashtags or []):
                    key = (tag.lower(), platform)
                    if key not in hashtag_data:
                        hashtag_data[key] = {"count": 0, "er_sum": 0.0}
                    hashtag_data[key]["count"] += 1
                    hashtag_data[key]["er_sum"] += er

            # Upsert each hashtag trend
            upserted = 0
            for (hashtag, platform), agg in hashtag_data.items():
                avg_er = agg["er_sum"] / agg["count"] if agg["count"] > 0 else 0.0

                # Check if exists
                existing_stmt = select(HashtagTrend).where(
                    HashtagTrend.hashtag == hashtag,
                    HashtagTrend.platform == platform,
                )
                existing_result = await session.execute(existing_stmt)
                trend = existing_result.scalar_one_or_none()

                now = datetime.now(timezone.utc)

                if trend:
                    trend.occurrence_count += agg["count"]
                    # Rolling average
                    total = trend.occurrence_count
                    trend.avg_engagement_rate = (
                        (float(trend.avg_engagement_rate or 0) * (total - agg["count"]) + agg["er_sum"])
                        / total
                    )
                    trend.last_seen_at = now
                else:
                    trend = HashtagTrend(
                        hashtag=hashtag,
                        platform=platform,
                        occurrence_count=agg["count"],
                        avg_engagement_rate=round(avg_er, 4),
                        last_seen_at=now,
                    )
                    session.add(trend)

                upserted += 1

            await session.commit()
            logger.info(
                "Hashtag refresh: upserted %d hashtag trends from %d posts.",
                upserted,
                len(posts),
            )

    except Exception as exc:
        logger.error("Hashtag refresh job failed: %s", exc, exc_info=True)


def start_scheduler() -> None:
    """Register and start all background jobs."""
    # Daily cache cleanup at 03:00 UTC
    _scheduler.add_job(
        cleanup_expired_cache,
        trigger=CronTrigger(hour=3, minute=0),
        id="cleanup_expired_cache",
        replace_existing=True,
        name="Daily cache cleanup",
    )

    # Hashtag trend refresh every 6 hours
    _scheduler.add_job(
        refresh_trending_hashtags,
        trigger=CronTrigger(hour="*/6"),
        id="refresh_trending_hashtags",
        replace_existing=True,
        name="Hashtag trend refresh (6h)",
    )

    _scheduler.start()
    logger.info("APScheduler started with %d jobs.", len(_scheduler.get_jobs()))


def stop_scheduler() -> None:
    """Gracefully shut down the scheduler."""
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped.")


__all__ = ["start_scheduler", "stop_scheduler"]
