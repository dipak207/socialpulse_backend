"""TikTok adapter — yt-dlp primary with Playwright OG fallback."""
import asyncio
from datetime import datetime, timezone
from typing import Any, Optional

from app.adapters.base import PlatformAdapter
from app.analytics.engine import analytics_engine
from app.scrapers.extraction_fallbacks import extraction_fallbacks
from app.scrapers.browser_manager import browser_manager
from app.utils.logger import logger

try:
    import yt_dlp
    _YTDLP_AVAILABLE = True
except ImportError:
    _YTDLP_AVAILABLE = False


class TikTokAdapter(PlatformAdapter):
    """
    Fetches TikTok video and profile analytics.

    Primary: yt-dlp metadata extraction
    Fallback: Playwright + OG tag extraction
    """

    async def fetch_post(self, identifier: str, post_type: str = "video") -> dict[str, Any]:
        """
        Fetch a TikTok video's analytics.

        Args:
            identifier: TikTok video ID (numeric string).
            post_type: "video".
        """
        if _YTDLP_AVAILABLE:
            try:
                return await asyncio.get_event_loop().run_in_executor(
                    None, self._fetch_video_ytdlp, identifier
                )
            except Exception as exc:
                logger.warning(
                    "yt-dlp TikTok fetch failed for %s: %s. Falling back to Playwright.",
                    identifier,
                    exc,
                )

        return await self._fetch_video_playwright(identifier)

    def _fetch_video_ytdlp(self, video_id: str) -> dict[str, Any]:
        """Synchronous yt-dlp fetch for a TikTok video."""
        # yt-dlp needs the full URL for TikTok
        url = f"https://www.tiktok.com/@user/video/{video_id}"

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        views = info.get("view_count") or 0
        likes = info.get("like_count") or 0
        comments = info.get("comment_count") or 0
        reposts = info.get("repost_count") or 0
        followers = info.get("channel_follower_count") or 0

        er = analytics_engine.engagement_rate(likes, comments, reposts, max(followers, 1))

        upload_date = info.get("upload_date")
        published_at: Optional[datetime] = None
        if upload_date:
            try:
                published_at = datetime.strptime(upload_date, "%Y%m%d").replace(
                    tzinfo=timezone.utc
                )
            except ValueError:
                pass

        virality = analytics_engine.virality_score(
            likes, comments, reposts, max(views, 1), max(followers, 1), published_at
        )

        description = info.get("description", "") or ""
        hashtags = extraction_fallbacks.extract_hashtags(description)

        return {
            "platform": "tiktok",
            "type": "video",
            "platform_post_id": video_id,
            "url": info.get("webpage_url") or url,
            "title": info.get("title", ""),
            "description": description[:500],
            "thumbnail_url": info.get("thumbnail"),
            "author": info.get("uploader") or info.get("channel", "unknown"),
            "author_id": info.get("channel_id", ""),
            "author_followers": followers,
            "published_at": published_at.isoformat() if published_at else None,
            "views": views,
            "likes": likes,
            "comments": comments,
            "shares": reposts,
            "engagement_rate": er,
            "virality_score": virality,
            "trend_score": 50.0,
            "hashtags": hashtags,
            "duration_seconds": info.get("duration") or 0,
            "data_source": "yt-dlp",
        }

    async def _fetch_video_playwright(self, video_id: str) -> dict[str, Any]:
        """Playwright OG tag fallback for a TikTok video."""
        url = f"https://www.tiktok.com/video/{video_id}"

        async with browser_manager.new_page() as page:
            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
            except Exception as exc:
                logger.warning("TikTok Playwright load failed for %s: %s", video_id, exc)
            html = await page.content()

        og = extraction_fallbacks.extract_og_tags(html)
        description = og.get("og_description", "") or ""
        hashtags = extraction_fallbacks.extract_hashtags(description)

        likes_raw = og.get("og_video_secure_url", "0")
        likes = extraction_fallbacks.extract_number(
            og.get("twitter_data1", "0")
        )

        return {
            "platform": "tiktok",
            "type": "video",
            "platform_post_id": video_id,
            "url": url,
            "title": og.get("og_title", ""),
            "description": description[:500],
            "thumbnail_url": og.get("og_image"),
            "author": og.get("og_site_name", "tiktok"),
            "author_id": "",
            "author_followers": 0,
            "published_at": None,
            "views": 0,
            "likes": likes,
            "comments": 0,
            "shares": 0,
            "engagement_rate": 0.0,
            "virality_score": 0.0,
            "trend_score": 50.0,
            "hashtags": hashtags,
            "data_source": "playwright-og",
        }

    async def fetch_profile(self, identifier: str) -> dict[str, Any]:
        """
        Fetch a TikTok profile's analytics.

        Args:
            identifier: TikTok username (without @).
        """
        if _YTDLP_AVAILABLE:
            try:
                return await asyncio.get_event_loop().run_in_executor(
                    None, self._fetch_profile_ytdlp, identifier
                )
            except Exception as exc:
                logger.warning(
                    "yt-dlp TikTok profile fetch failed for %s: %s. Falling back.",
                    identifier,
                    exc,
                )

        return await self._fetch_profile_playwright(identifier)

    def _fetch_profile_ytdlp(self, username: str) -> dict[str, Any]:
        """Synchronous yt-dlp fetch for a TikTok profile/channel."""
        url = f"https://www.tiktok.com/@{username}"

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "playlistend": 12,
            "skip_download": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        entries = info.get("entries", []) or []
        followers = info.get("channel_follower_count") or 0

        top_posts = []
        ers: list[float] = []

        for entry in entries[:12]:
            v_views = entry.get("view_count") or 0
            v_likes = entry.get("like_count") or 0
            v_comments = entry.get("comment_count") or 0
            v_reposts = entry.get("repost_count") or 0
            v_er = analytics_engine.engagement_rate(
                v_likes, v_comments, v_reposts, max(followers, 1)
            )
            v_virality = analytics_engine.virality_score(
                v_likes, v_comments, v_reposts, max(v_views, 1), max(followers, 1)
            )
            ers.append(v_er)
            top_posts.append(
                {
                    "url": entry.get("url") or f"https://www.tiktok.com/@{username}/video/{entry.get('id', '')}",
                    "title": entry.get("title", ""),
                    "thumbnail_url": entry.get("thumbnail"),
                    "views": v_views,
                    "likes": v_likes,
                    "comments": v_comments,
                    "shares": v_reposts,
                    "engagement_rate": v_er,
                    "virality_score": v_virality,
                    "published_at": None,
                }
            )

        avg_er = sum(ers) / len(ers) if ers else 0.0

        return {
            "platform": "tiktok",
            "platform_user_id": info.get("channel_id", username),
            "username": username,
            "display_name": info.get("channel") or info.get("uploader") or username,
            "avatar_url": info.get("thumbnail"),
            "bio": "",
            "verified": False,
            "followers": followers,
            "following": None,
            "posts_count": info.get("playlist_count") or len(entries),
            "avg_engagement_rate": round(avg_er, 4),
            "posting_frequency": 0.0,
            "top_posts": top_posts,
            "hashtags": [],
            "data_source": "yt-dlp",
        }

    async def _fetch_profile_playwright(self, username: str) -> dict[str, Any]:
        """Playwright OG tag fallback for a TikTok profile."""
        url = f"https://www.tiktok.com/@{username}"

        async with browser_manager.new_page() as page:
            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
            except Exception as exc:
                logger.warning("TikTok profile Playwright failed for %s: %s", username, exc)
            html = await page.content()

        og = extraction_fallbacks.extract_og_tags(html)
        description = og.get("og_description", "") or ""

        import re
        follower_match = re.search(r"([\d,.]+[KkMm]?)\s+Followers", description)
        followers = extraction_fallbacks.extract_number(follower_match.group(1)) if follower_match else 0

        return {
            "platform": "tiktok",
            "platform_user_id": username,
            "username": username,
            "display_name": og.get("og_title", username),
            "avatar_url": og.get("og_image"),
            "bio": description[:500],
            "verified": False,
            "followers": followers,
            "following": None,
            "posts_count": 0,
            "avg_engagement_rate": 0.0,
            "posting_frequency": 0.0,
            "top_posts": [],
            "hashtags": [],
            "data_source": "playwright-og",
        }


# Singleton instance
tiktok_adapter = TikTokAdapter()

__all__ = ["TikTokAdapter", "tiktok_adapter"]
