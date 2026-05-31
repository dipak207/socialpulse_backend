"""Instagram adapter — instaloader primary with Playwright OG fallback."""
import asyncio
import re
from datetime import datetime, timezone
from typing import Any, Optional

from app.adapters.base import PlatformAdapter
from app.analytics.engine import analytics_engine
from app.scrapers.extraction_fallbacks import extraction_fallbacks
from app.scrapers.browser_manager import browser_manager
from app.utils.logger import logger

try:
    import instaloader
    _INSTALOADER_AVAILABLE = True
except ImportError:
    _INSTALOADER_AVAILABLE = False


class InstagramAdapter(PlatformAdapter):
    """
    Fetches Instagram post and profile analytics.

    Primary: instaloader (no auth required for public content)
    Fallback: Playwright + OG tag extraction
    """

    def __init__(self) -> None:
        self._loader: Optional[Any] = None

    def _get_loader(self):
        """Lazily create an instaloader instance."""
        if self._loader is None and _INSTALOADER_AVAILABLE:
            self._loader = instaloader.Instaloader(
                quiet=True,
                download_pictures=False,
                download_videos=False,
                download_video_thumbnails=False,
                compress_json=False,
                save_metadata=False,
            )
        return self._loader

    async def fetch_post(self, identifier: str, post_type: str = "post") -> dict[str, Any]:
        """
        Fetch an Instagram post or reel by shortcode.

        Args:
            identifier: Instagram shortcode (e.g. "CxD3bKWMUXQ").
            post_type: "post" or "reel".
        """
        loader = self._get_loader()
        if loader and _INSTALOADER_AVAILABLE:
            try:
                return await asyncio.get_event_loop().run_in_executor(
                    None, self._fetch_post_instaloader, identifier, post_type, loader
                )
            except Exception as exc:
                logger.warning(
                    "Instaloader post fetch failed for %s: %s. Falling back to Playwright.",
                    identifier,
                    exc,
                )

        # Playwright fallback
        return await self._fetch_post_playwright(identifier, post_type)

    def _fetch_post_instaloader(
        self, shortcode: str, post_type: str, loader
    ) -> dict[str, Any]:
        """Synchronous instaloader post fetch."""
        post = instaloader.Post.from_shortcode(loader.context, shortcode)

        likes = post.likes or 0
        comments = post.comments or 0
        followers = post.owner_profile.followers if post.owner_profile else 1
        er = analytics_engine.engagement_rate(likes, comments, 0, max(followers, 1))
        virality = analytics_engine.virality_score(
            likes, comments, 0, max(likes + comments, 1), max(followers, 1),
            post.date_utc
        )

        caption = post.caption or ""
        hashtags = extraction_fallbacks.extract_hashtags(caption)

        thumbnail_url = post.url if hasattr(post, "url") else None

        return {
            "platform": "instagram",
            "type": post_type,
            "platform_post_id": shortcode,
            "url": f"https://www.instagram.com/p/{shortcode}/",
            "title": None,
            "description": caption[:500],
            "thumbnail_url": thumbnail_url,
            "author": post.owner_username,
            "author_id": str(post.owner_id),
            "author_followers": followers,
            "published_at": post.date_utc.isoformat() if post.date_utc else None,
            "views": post.video_view_count if post.is_video else (likes * 10),
            "likes": likes,
            "comments": comments,
            "shares": 0,
            "engagement_rate": er,
            "virality_score": virality,
            "trend_score": 50.0,
            "hashtags": hashtags,
            "is_video": post.is_video,
            "data_source": "instaloader",
        }

    async def _fetch_post_playwright(
        self, shortcode: str, post_type: str
    ) -> dict[str, Any]:
        """Playwright fallback for Instagram post with JSON data extraction."""
        url = f"https://www.instagram.com/p/{shortcode}/"
        async with browser_manager.new_page() as page:
            await page.goto(url, wait_until="networkidle", timeout=30000)
            html = await page.content()

        # Try to extract metrics from window._sharedData first (most reliable)
        post_metrics = extraction_fallbacks.extract_instagram_post_metrics(html)
        
        if post_metrics:
            # Successfully extracted from JSON data
            likes = post_metrics.get("likes", 0)
            comments = post_metrics.get("comments", 0)
            views = post_metrics.get("views", 0)
            caption = post_metrics.get("caption", "")
            author = post_metrics.get("author_username", "")
            author_id = post_metrics.get("author_id", "")
            thumbnail_url = post_metrics.get("thumbnail_url", "")
            timestamp = post_metrics.get("timestamp", 0)
            is_video = post_metrics.get("is_video", False)
            
            logger.info(
                "Instagram post %s extracted: likes=%d, comments=%d, views=%d, author=%s",
                shortcode, likes, comments, views, author
            )
            
            # Estimate views for non-video posts if not available
            if not views and not is_video:
                views = max(likes * 10, 0)
            
            hashtags = extraction_fallbacks.extract_hashtags(caption)
            
            # Calculate engagement metrics
            # Use a fallback of 1000 followers if we can't get the actual value
            followers = max(post_metrics.get("author_followers", 1000), 1)
            er = analytics_engine.engagement_rate(likes, comments, 0, followers)
            virality = analytics_engine.virality_score(
                likes, comments, 0, max(likes + comments, 1), followers,
                datetime.fromtimestamp(timestamp, tz=timezone.utc) if timestamp else datetime.now(timezone.utc)
            )
            
            return {
                "platform": "instagram",
                "type": post_type,
                "platform_post_id": shortcode,
                "url": url,
                "title": None,
                "description": caption[:500],
                "thumbnail_url": thumbnail_url,
                "author": author or "instagram",
                "author_id": author_id,
                "author_followers": followers,
                "published_at": datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat() if timestamp else None,
                "views": views,
                "likes": likes,
                "comments": comments,
                "shares": 0,
                "engagement_rate": er,
                "virality_score": virality,
                "trend_score": 50.0,
                "hashtags": hashtags,
                "is_video": is_video,
                "data_source": "playwright-json",
            }
        
        # Fallback to OG tags if JSON extraction failed
        logger.warning(
            "Failed to extract Instagram post %s from JSON, falling back to OG tags",
            shortcode
        )
        og = extraction_fallbacks.extract_og_tags(html)
        description = og.get("og_description", "") or og.get("twitter_description", "")
        hashtags = extraction_fallbacks.extract_hashtags(description)

        # Try to parse metrics from OG title (legacy fallback)
        title = og.get("og_title", "") or ""
        likes = 0
        if "like" in title.lower():
            parts = title.split()
            for part in parts:
                candidate = extraction_fallbacks.extract_number(part)
                if candidate > 0:
                    likes = candidate
                    break

        logger.info("Instagram post %s extracted from OG tags: likes=%d", shortcode, likes)

        return {
            "platform": "instagram",
            "type": post_type,
            "platform_post_id": shortcode,
            "url": url,
            "title": None,
            "description": description[:500],
            "thumbnail_url": og.get("og_image"),
            "author": og.get("og_site_name", "instagram"),
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
            "is_video": False,
            "data_source": "playwright-og",
        }

    async def fetch_profile(self, identifier: str) -> dict[str, Any]:
        """
        Fetch an Instagram profile's analytics.

        Args:
            identifier: Instagram username (without @).
        """
        loader = self._get_loader()
        if loader and _INSTALOADER_AVAILABLE:
            try:
                return await asyncio.get_event_loop().run_in_executor(
                    None, self._fetch_profile_instaloader, identifier, loader
                )
            except Exception as exc:
                logger.warning(
                    "Instaloader profile fetch failed for %s: %s. Falling back.",
                    identifier,
                    exc,
                )

        return await self._fetch_profile_playwright(identifier)

    def _fetch_profile_instaloader(self, username: str, loader) -> dict[str, Any]:
        """Synchronous instaloader profile fetch."""
        profile = instaloader.Profile.from_username(loader.context, username)

        followers = profile.followers or 0
        following = profile.followees or 0
        posts_count = profile.mediacount or 0

        # Fetch up to 12 recent posts for analytics
        top_posts: list[dict] = []
        ers: list[float] = []
        post_dates: list[datetime] = []
        all_hashtags: list[str] = []

        try:
            post_iter = profile.get_posts()
            for i, post in enumerate(post_iter):
                if i >= 12:
                    break
                p_likes = post.likes or 0
                p_comments = post.comments or 0
                p_er = analytics_engine.engagement_rate(
                    p_likes, p_comments, 0, max(followers, 1)
                )
                p_virality = analytics_engine.virality_score(
                    p_likes, p_comments, 0, p_likes * 10, max(followers, 1), post.date_utc
                )
                ers.append(p_er)
                if post.date_utc:
                    post_dates.append(post.date_utc)

                caption = post.caption or ""
                hashtags = extraction_fallbacks.extract_hashtags(caption)
                all_hashtags.extend(hashtags)

                top_posts.append(
                    {
                        "url": f"https://www.instagram.com/p/{post.shortcode}/",
                        "title": None,
                        "thumbnail_url": post.url if hasattr(post, "url") else None,
                        "views": post.video_view_count if post.is_video else (p_likes * 10),
                        "likes": p_likes,
                        "comments": p_comments,
                        "shares": 0,
                        "engagement_rate": p_er,
                        "virality_score": p_virality,
                        "published_at": post.date_utc.isoformat() if post.date_utc else None,
                    }
                )
        except Exception as exc:
            logger.warning("Error iterating Instagram posts for %s: %s", username, exc)

        avg_er = sum(ers) / len(ers) if ers else 0.0
        freq = analytics_engine.posting_frequency(post_dates)

        # Deduplicate hashtags
        seen: set[str] = set()
        unique_hashtags = [h for h in all_hashtags if not (h in seen or seen.add(h))]

        return {
            "platform": "instagram",
            "platform_user_id": str(profile.userid),
            "username": username,
            "display_name": profile.full_name or username,
            "avatar_url": profile.profile_pic_url,
            "bio": profile.biography[:500] if profile.biography else "",
            "verified": profile.is_verified,
            "followers": followers,
            "following": following,
            "posts_count": posts_count,
            "avg_engagement_rate": round(avg_er, 4),
            "posting_frequency": freq,
            "top_posts": top_posts,
            "hashtags": unique_hashtags[:20],
            "data_source": "instaloader",
        }

    async def _fetch_profile_playwright(self, username: str) -> dict[str, Any]:
        """Playwright fallback for Instagram profile with JSON data extraction."""
        url = f"https://www.instagram.com/{username}/"
        async with browser_manager.new_page() as page:
            await page.goto(url, wait_until="networkidle", timeout=30000)
            html = await page.content()

        # Try to extract metrics from window._sharedData first
        profile_metrics = extraction_fallbacks.extract_instagram_profile_metrics(html)
        
        if profile_metrics:
            # Successfully extracted from JSON data
            followers = profile_metrics.get("followers", 0)
            following = profile_metrics.get("following", 0)
            posts_count = profile_metrics.get("posts_count", 0)
            display_name = profile_metrics.get("display_name", username)
            bio = profile_metrics.get("bio", "")
            verified = profile_metrics.get("verified", False)
            avatar_url = profile_metrics.get("profile_pic_url", "")
            
            logger.info(
                "Instagram profile %s extracted: followers=%d, posts=%d, verified=%s",
                username, followers, posts_count, verified
            )
            
            return {
                "platform": "instagram",
                "platform_user_id": username,
                "username": username,
                "display_name": display_name,
                "avatar_url": avatar_url,
                "bio": bio[:500] if bio else "",
                "verified": verified,
                "followers": followers,
                "following": following,
                "posts_count": posts_count,
                "avg_engagement_rate": 0.0,  # Cannot calculate without posts data
                "posting_frequency": 0.0,
                "top_posts": [],
                "hashtags": [],
                "data_source": "playwright-json",
            }
        
        # Fallback to OG tags if JSON extraction failed
        logger.warning(
            "Failed to extract Instagram profile %s from JSON, falling back to OG tags",
            username
        )
        og = extraction_fallbacks.extract_og_tags(html)
        description = og.get("og_description", "") or ""

        # Try to extract follower count from description regex
        followers = 0
        follower_match = re.search(r"([\d,.]+[KkMm]?)\s+Followers", description)
        if follower_match:
            followers = extraction_fallbacks.extract_number(follower_match.group(1))
            logger.info("Instagram profile %s extracted from OG: followers=%d", username, followers)

        return {
            "platform": "instagram",
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
instagram_adapter = InstagramAdapter()

__all__ = ["InstagramAdapter", "instagram_adapter"]
