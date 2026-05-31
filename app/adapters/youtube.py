"""YouTube adapter — YouTube Data API v3 with yt-dlp fallback."""
import os
import asyncio
import isodate
from datetime import datetime, timezone
from typing import Any, Optional

from app.adapters.base import PlatformAdapter
from app.analytics.engine import analytics_engine
from app.scrapers.extraction_fallbacks import extraction_fallbacks
from app.utils.logger import logger

# Optional API dependencies — graceful fallback if not configured
try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    _GOOGLE_AVAILABLE = True
except ImportError:
    _GOOGLE_AVAILABLE = False

try:
    import yt_dlp
    _YTDLP_AVAILABLE = True
except ImportError:
    _YTDLP_AVAILABLE = False


class YouTubeAdapter(PlatformAdapter):
    """
    Fetches YouTube video and channel analytics.

    Primary: YouTube Data API v3
    Fallback: yt-dlp metadata extraction
    """

    def __init__(self) -> None:
        self._api_key: Optional[str] = os.getenv("YOUTUBE_API_KEY")
        self._youtube_client = None

    def _get_client(self):
        """Lazily build the YouTube API client."""
        if self._youtube_client is None and self._api_key and _GOOGLE_AVAILABLE:
            self._youtube_client = build(
                "youtube", "v3", developerKey=self._api_key, cache_discovery=False
            )
        return self._youtube_client

    async def fetch_post(self, identifier: str, post_type: str = "video") -> dict[str, Any]:
        """
        Fetch a YouTube video's analytics.

        Args:
            identifier: YouTube video ID (11 chars).
            post_type: "video" or "shorts".
        """
        client = self._get_client()
        if client and self._api_key:
            try:
                return await asyncio.get_event_loop().run_in_executor(
                    None, self._fetch_video_api, identifier, post_type
                )
            except Exception as exc:
                logger.warning("YouTube API failed for %s: %s. Falling back to yt-dlp.", identifier, exc)

        # Fallback to yt-dlp
        if _YTDLP_AVAILABLE:
            return await asyncio.get_event_loop().run_in_executor(
                None, self._fetch_video_ytdlp, identifier, post_type
            )

        raise RuntimeError(f"Cannot fetch YouTube video {identifier}: no API key and yt-dlp unavailable.")

    def _fetch_video_api(self, video_id: str, post_type: str) -> dict[str, Any]:
        """Synchronous YouTube Data API fetch for a video."""
        client = self._get_client()

        # Fetch video details
        video_resp = (
            client.videos()
            .list(
                part="statistics,snippet,contentDetails",
                id=video_id,
            )
            .execute()
        )

        items = video_resp.get("items", [])
        if not items:
            raise ValueError(f"YouTube video not found: {video_id}")

        item = items[0]
        snippet = item.get("snippet", {})
        stats = item.get("statistics", {})
        content_details = item.get("contentDetails", {})

        channel_id = snippet.get("channelId", "")
        channel_title = snippet.get("channelTitle", "Unknown")

        # Fetch channel subscriber count
        subscribers = 0
        if channel_id:
            ch_resp = (
                client.channels()
                .list(part="statistics", id=channel_id)
                .execute()
            )
            ch_items = ch_resp.get("items", [])
            if ch_items:
                ch_stats = ch_items[0].get("statistics", {})
                subscribers = int(ch_stats.get("subscriberCount", 0))

        views = int(stats.get("viewCount", 0))
        likes = int(stats.get("likeCount", 0))
        comments = int(stats.get("commentCount", 0))
        shares = 0  # YouTube API does not expose share count

        er = analytics_engine.engagement_rate(likes, comments, shares, max(subscribers, 1))

        published_raw = snippet.get("publishedAt", "")
        published_at: Optional[datetime] = None
        if published_raw:
            try:
                published_at = datetime.fromisoformat(
                    published_raw.replace("Z", "+00:00")
                )
            except ValueError:
                pass

        virality = analytics_engine.virality_score(
            likes, comments, shares, views, max(subscribers, 1), published_at
        )

        description = snippet.get("description", "")
        hashtags = extraction_fallbacks.extract_hashtags(description)

        # Parse duration
        duration_iso = content_details.get("duration", "PT0S")
        try:
            duration_seconds = int(isodate.parse_duration(duration_iso).total_seconds())
        except Exception:
            duration_seconds = 0

        return {
            "platform": "youtube",
            "type": post_type,
            "platform_post_id": video_id,
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "title": snippet.get("title", ""),
            "description": description[:500],
            "thumbnail_url": (
                snippet.get("thumbnails", {}).get("high", {}).get("url")
                or snippet.get("thumbnails", {}).get("default", {}).get("url")
            ),
            "author": channel_title,
            "author_id": channel_id,
            "author_followers": subscribers,
            "published_at": published_at.isoformat() if published_at else None,
            "views": views,
            "likes": likes,
            "comments": comments,
            "shares": shares,
            "duration_seconds": duration_seconds,
            "engagement_rate": er,
            "virality_score": virality,
            "trend_score": 50.0,
            "hashtags": hashtags,
            "tags": snippet.get("tags", []),
            "category_id": snippet.get("categoryId", ""),
            "data_source": "api",
        }

    def _fetch_video_ytdlp(self, video_id: str, post_type: str) -> dict[str, Any]:    
        url = f"https://www.youtube.com/watch?v={video_id}"

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "extract_flat": False,
            "noplaylist": True,
            "ignoreerrors": True,
            "socket_timeout": 20,
            "retries": 3,
            "geo_bypass": True,
            "nocheckcertificate": True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

            if not info:
                raise ValueError(f"Could not extract metadata for video {video_id}")

        except Exception as exc:
            logger.error("yt-dlp extraction failed for %s: %s", video_id, exc)
            raise RuntimeError(f"yt-dlp extraction failed: {exc}")

        views = info.get("view_count") or 0
        likes = info.get("like_count") or 0
        comments = info.get("comment_count") or 0
        subscribers = info.get("channel_follower_count") or 0

        er = analytics_engine.engagement_rate(
            likes,
            comments,
            0,
            max(subscribers, 1)
        )

        published_at: Optional[datetime] = None
        upload_date = info.get("upload_date")

        if upload_date:
            try:
                published_at = datetime.strptime(
                    upload_date,
                    "%Y%m%d"
                ).replace(tzinfo=timezone.utc)
            except ValueError:
                pass

        virality = analytics_engine.virality_score(
            likes,
            comments,
            0,
            views,
            max(subscribers, 1),
            published_at
        )

        description = info.get("description", "") or ""
        hashtags = extraction_fallbacks.extract_hashtags(description)

        return {
            "platform": "youtube",
            "type": post_type,
            "platform_post_id": video_id,
            "url": url,
            "title": info.get("title", ""),
            "description": description[:500],
            "thumbnail_url": info.get("thumbnail"),
            "author": info.get("uploader") or info.get("channel", "Unknown"),
            "author_id": info.get("channel_id", ""),
            "author_followers": subscribers,
            "published_at": (
                published_at.isoformat()
                if published_at
                else None
            ),
            "views": views,
            "likes": likes,
            "comments": comments,
            "shares": 0,
            "duration_seconds": info.get("duration") or 0,
            "engagement_rate": er,
            "virality_score": virality,
            "trend_score": 50.0,
            "hashtags": hashtags,
            "tags": info.get("tags", []),
            "data_source": "yt-dlp",
        }
    async def fetch_profile(self, identifier: str) -> dict[str, Any]:
        """
        Fetch a YouTube channel's analytics.

        Args:
            identifier: Channel handle (e.g. @MrBeast) or channel ID (UCxxxxxxxx).
        """
        client = self._get_client()
        if client and self._api_key:
            try:
                return await asyncio.get_event_loop().run_in_executor(
                    None, self._fetch_channel_api, identifier
                )
            except Exception as exc:
                logger.warning(
                    "YouTube API channel fetch failed for %s: %s. Falling back.", identifier, exc
                )

        if _YTDLP_AVAILABLE:
            return await asyncio.get_event_loop().run_in_executor(
                None, self._fetch_channel_ytdlp, identifier
            )

        raise RuntimeError(
            f"Cannot fetch YouTube channel {identifier}: no API key and yt-dlp unavailable."
        )

    def _fetch_channel_api(self, identifier: str) -> dict[str, Any]:
        """Synchronous YouTube Data API fetch for a channel."""
        client = self._get_client()

        # Determine if this is a channel ID or a handle
        if identifier.startswith("UC"):
            channel_resp = (
                client.channels()
                .list(part="statistics,snippet,brandingSettings", id=identifier)
                .execute()
            )
        else:
            handle = identifier.lstrip("@")
            channel_resp = (
                client.channels()
                .list(
                    part="statistics,snippet,brandingSettings",
                    forHandle=f"@{handle}",
                )
                .execute()
            )

        items = channel_resp.get("items", [])
        if not items:
            raise ValueError(f"YouTube channel not found: {identifier}")

        item = items[0]
        channel_id = item["id"]
        snippet = item.get("snippet", {})
        stats = item.get("statistics", {})

        subscribers = int(stats.get("subscriberCount", 0))
        total_views = int(stats.get("viewCount", 0))
        video_count = int(stats.get("videoCount", 0))

        # Fetch top 10 recent videos
        search_resp = (
            client.search()
            .list(
                part="id",
                channelId=channel_id,
                type="video",
                order="date",
                maxResults=10,
            )
            .execute()
        )

        video_ids = [
            item["id"]["videoId"]
            for item in search_resp.get("items", [])
            if item.get("id", {}).get("videoId")
        ]

        top_posts: list[dict] = []
        avg_er = 0.0

        if video_ids:
            videos_resp = (
                client.videos()
                .list(
                    part="statistics,snippet,contentDetails",
                    id=",".join(video_ids),
                )
                .execute()
            )

            ers: list[float] = []
            for v in videos_resp.get("items", []):
                v_stats = v.get("statistics", {})
                v_snippet = v.get("snippet", {})
                v_views = int(v_stats.get("viewCount", 0))
                v_likes = int(v_stats.get("likeCount", 0))
                v_comments = int(v_stats.get("commentCount", 0))
                v_er = analytics_engine.engagement_rate(
                    v_likes, v_comments, 0, max(subscribers, 1)
                )
                v_virality = analytics_engine.virality_score(
                    v_likes, v_comments, 0, v_views, max(subscribers, 1)
                )
                ers.append(v_er)

                published_raw = v_snippet.get("publishedAt", "")
                pub_at = None
                if published_raw:
                    try:
                        pub_at = datetime.fromisoformat(
                            published_raw.replace("Z", "+00:00")
                        ).isoformat()
                    except ValueError:
                        pass

                top_posts.append(
                    {
                        "url": f"https://www.youtube.com/watch?v={v['id']}",
                        "title": v_snippet.get("title", ""),
                        "thumbnail_url": v_snippet.get("thumbnails", {})
                        .get("high", {})
                        .get("url"),
                        "views": v_views,
                        "likes": v_likes,
                        "comments": v_comments,
                        "shares": 0,
                        "engagement_rate": v_er,
                        "virality_score": v_virality,
                        "published_at": pub_at,
                    }
                )

            avg_er = sum(ers) / len(ers) if ers else 0.0

        # Compute posting frequency from top posts
        post_dates = []
        for p in top_posts:
            if p.get("published_at"):
                try:
                    post_dates.append(datetime.fromisoformat(p["published_at"]))
                except ValueError:
                    pass
        freq = analytics_engine.posting_frequency(post_dates)

        created_at_raw = snippet.get("publishedAt", "")
        created_at = None
        if created_at_raw:
            try:
                created_at = datetime.fromisoformat(
                    created_at_raw.replace("Z", "+00:00")
                ).isoformat()
            except ValueError:
                pass

        return {
            "platform": "youtube",
            "platform_user_id": channel_id,
            "username": snippet.get("customUrl", identifier).lstrip("@"),
            "display_name": snippet.get("title", ""),
            "avatar_url": snippet.get("thumbnails", {})
            .get("high", {})
            .get("url"),
            "bio": snippet.get("description", "")[:500],
            "verified": False,  # YouTube API doesn't expose verification in basic tier
            "followers": subscribers,
            "following": None,
            "posts_count": video_count,
            "avg_engagement_rate": round(avg_er, 4),
            "posting_frequency": freq,
            "top_posts": top_posts,
            "total_views": total_views,
            "created_at": created_at,
            "data_source": "api",
        }

    def _fetch_channel_ytdlp(self, identifier: str) -> dict[str, Any]:
        """Synchronous yt-dlp fallback for channel data."""
        handle = identifier.lstrip("@")
        url = f"https://www.youtube.com/@{handle}"

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "playlistend": 10,
            "skip_download": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        entries = info.get("entries", []) or []
        subscribers = info.get("channel_follower_count") or 0

        top_posts = []
        for entry in entries[:10]:
            v_views = entry.get("view_count") or 0
            v_likes = entry.get("like_count") or 0
            v_comments = entry.get("comment_count") or 0
            v_er = analytics_engine.engagement_rate(
                v_likes, v_comments, 0, max(subscribers, 1)
            )
            top_posts.append(
                {
                    "url": entry.get("url") or f"https://youtu.be/{entry.get('id','')}",
                    "title": entry.get("title", ""),
                    "thumbnail_url": entry.get("thumbnail"),
                    "views": v_views,
                    "likes": v_likes,
                    "comments": v_comments,
                    "shares": 0,
                    "engagement_rate": v_er,
                    "virality_score": analytics_engine.virality_score(
                        v_likes, v_comments, 0, v_views, max(subscribers, 1)
                    ),
                    "published_at": None,
                }
            )

        avg_er = (
            sum(p["engagement_rate"] for p in top_posts) / len(top_posts)
            if top_posts
            else 0.0
        )

        return {
            "platform": "youtube",
            "platform_user_id": info.get("channel_id", handle),
            "username": handle,
            "display_name": info.get("channel") or info.get("uploader") or handle,
            "avatar_url": info.get("thumbnail"),
            "bio": info.get("description", "")[:500] if info.get("description") else "",
            "verified": False,
            "followers": subscribers,
            "following": None,
            "posts_count": info.get("playlist_count") or len(entries),
            "avg_engagement_rate": round(avg_er, 4),
            "posting_frequency": 0.0,
            "top_posts": top_posts,
            "total_views": info.get("view_count") or 0,
            "data_source": "yt-dlp",
        }


# Singleton instance
youtube_adapter = YouTubeAdapter()

__all__ = ["YouTubeAdapter", "youtube_adapter"]
