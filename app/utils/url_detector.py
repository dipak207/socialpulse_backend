"""URL detection utility for identifying social media platforms and content types."""
import re
from typing import Optional
from urllib.parse import urlparse, parse_qs


class URLDetector:
    """Detects social media platform, content type, and identifier from a URL."""

    # ----- YouTube patterns -----
    # ----- YouTube patterns -----

# Standard videos
    _YT_VIDEO = re.compile(
        r"(?:youtube\.com/watch\?.*v=|youtu\.be/)([A-Za-z0-9_-]{11})"
    )

    # Shorts
    _YT_SHORTS = re.compile(
        r"youtube\.com/shorts/([A-Za-z0-9_-]{11})"
    )

    # Live streams
    _YT_LIVE = re.compile(
        r"youtube\.com/live/([A-Za-z0-9_-]{11})"
    )
    _YT_CHANNEL_HANDLE = re.compile(
        r"youtube\.com/@([\w.-]+)"
    )
    _YT_CHANNEL_ID = re.compile(
        r"youtube\.com/channel/(UC[\w-]{22})"
    )

    # ----- Instagram patterns -----
    _IG_POST = re.compile(
        r"instagram\.com/p/([A-Za-z0-9_-]+)"
    )
    _IG_REEL = re.compile(
        r"instagram\.com/reel/([A-Za-z0-9_-]+)"
    )
    _IG_PROFILE = re.compile(
        r"instagram\.com/([\w.]+)/?$"
    )

    # ----- Twitter / X patterns -----
    _TW_POST = re.compile(
        r"(?:twitter\.com|x\.com)/([\w]+)/status/(\d+)"
    )
    _TW_PROFILE = re.compile(
        r"(?:twitter\.com|x\.com)/([\w]+)/?$"
    )

    # ----- TikTok patterns -----
    _TK_VIDEO = re.compile(
        r"tiktok\.com/@([\w.]+)/video/(\d+)"
    )
    _TK_PROFILE = re.compile(
        r"tiktok\.com/@([\w.]+)/?$"
    )

    # ----- LinkedIn patterns -----
    _LI_POST = re.compile(
        r"linkedin\.com/posts/([\w%-]+)"
    )
    _LI_PROFILE = re.compile(
        r"linkedin\.com/in/([\w%-]+)"
    )

    def detect(self, url: str) -> dict:
        """
        Detect the social media platform, content type, and identifier from a URL.

        Args:
            url: The URL to analyze.

        Returns:
            A dict with keys: platform, type, identifier, display_url.

        Raises:
            ValueError: If the URL does not match any supported platform.
        """
        # Normalize URL
        url = url.strip()
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        # --- YouTube ---
        m = self._YT_SHORTS.search(url)
        if m:
            return self._result("youtube", "shorts", m.group(1), url)
        m = self._YT_LIVE.search(url)
        if m:
            return self._result("youtube", "live", m.group(1), url)
        m = self._YT_VIDEO.search(url)
        if m:
            return self._result("youtube", "video", m.group(1), url)

        m = self._YT_CHANNEL_HANDLE.search(url)
        if m:
            return self._result("youtube", "channel", m.group(1), url)

        m = self._YT_CHANNEL_ID.search(url)
        if m:
            return self._result("youtube", "channel", m.group(1), url)

        # --- Instagram ---
        m = self._IG_POST.search(url)
        if m:
            return self._result("instagram", "post", m.group(1), url)

        m = self._IG_REEL.search(url)
        if m:
            return self._result("instagram", "reel", m.group(1), url)

        m = self._IG_PROFILE.search(url)
        if m:
            # Exclude reserved IG paths
            username = m.group(1)
            if username not in ("p", "reel", "explore", "stories", "tv", "accounts"):
                return self._result("instagram", "profile", username, url)

        # --- Twitter / X ---
        m = self._TW_POST.search(url)
        if m:
            return self._result("twitter", "post", m.group(2), url)

        m = self._TW_PROFILE.search(url)
        if m:
            username = m.group(1)
            if username not in ("i", "home", "explore", "notifications", "messages", "search"):
                return self._result("twitter", "profile", username, url)

        # --- TikTok ---
        m = self._TK_VIDEO.search(url)
        if m:
            return self._result("tiktok", "video", m.group(2), url)

        m = self._TK_PROFILE.search(url)
        if m:
            return self._result("tiktok", "profile", m.group(1), url)

        # --- LinkedIn ---
        m = self._LI_POST.search(url)
        if m:
            return self._result("linkedin", "post", m.group(1), url)

        m = self._LI_PROFILE.search(url)
        if m:
            return self._result("linkedin", "profile", m.group(1), url)

        raise ValueError(
            f"Unsupported URL: '{url}'. "
            "Supported platforms: YouTube, Instagram, Twitter/X, TikTok, LinkedIn."
        )

    @staticmethod
    def _result(platform: str, content_type: str, identifier: str, url: str) -> dict:
        return {
            "platform": platform,
            "type": content_type,
            "identifier": identifier,
            "display_url": url,
        }


# Singleton
url_detector = URLDetector()

__all__ = ["URLDetector", "url_detector"]
