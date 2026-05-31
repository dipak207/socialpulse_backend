"""Anti-bot evasion utilities: realistic user agents, headers, and human-like delays."""
import asyncio
import random
from typing import Optional


class AntiBotManager:
    """Provides anti-detection strategies for web scraping."""

    USER_AGENTS: list[str] = [
        # Chrome on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        # Chrome on macOS
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        # Firefox on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) "
        "Gecko/20100101 Firefox/125.0",
        # Firefox on Linux
        "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
        # Safari on macOS
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
        # Edge on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
        # Chrome on Android
        "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.6367.82 Mobile Safari/537.36",
    ]

    ACCEPT_LANGUAGES = [
        "en-US,en;q=0.9",
        "en-GB,en;q=0.9",
        "en-US,en;q=0.9,es;q=0.8",
        "en-US,en;q=0.8,fr;q=0.6",
    ]

    def get_random_ua(self) -> str:
        """Return a random user agent string."""
        return random.choice(self.USER_AGENTS)

    def get_browser_headers(self, ua: Optional[str] = None) -> dict:
        """
        Generate realistic browser-like HTTP headers.

        Args:
            ua: Optional user agent override; uses a random one if omitted.

        Returns:
            Dict of HTTP headers.
        """
        user_agent = ua or self.get_random_ua()
        return {
            "User-Agent": user_agent,
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "image/avif,image/webp,*/*;q=0.8"
            ),
            "Accept-Language": random.choice(self.ACCEPT_LANGUAGES),
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }

    async def human_delay(self, min_ms: int = 500, max_ms: int = 2000) -> None:
        """
        Simulate human reaction time by sleeping a random amount.

        Args:
            min_ms: Minimum delay in milliseconds.
            max_ms: Maximum delay in milliseconds.
        """
        delay_seconds = random.randint(min_ms, max_ms) / 1000.0
        await asyncio.sleep(delay_seconds)

    def get_playwright_args(self, ua: Optional[str] = None) -> dict:
        """
        Return Playwright browser context arguments for anti-bot evasion.

        Returns:
            Dict suitable for playwright.new_context(**args).
        """
        user_agent = ua or self.get_random_ua()
        return {
            "user_agent": user_agent,
            "viewport": random.choice(
                [
                    {"width": 1920, "height": 1080},
                    {"width": 1440, "height": 900},
                    {"width": 1366, "height": 768},
                    {"width": 1280, "height": 800},
                ]
            ),
            "locale": random.choice(["en-US", "en-GB"]),
            "timezone_id": random.choice(
                ["America/New_York", "America/Los_Angeles", "Europe/London"]
            ),
            "extra_http_headers": {
                "Accept-Language": random.choice(self.ACCEPT_LANGUAGES),
                "DNT": "1",
            },
        }


# Singleton instance
anti_bot = AntiBotManager()

__all__ = ["AntiBotManager", "anti_bot"]
