"""Playwright browser manager with anti-detection and stealth capabilities."""
import asyncio
import os
from contextlib import asynccontextmanager
from typing import Optional, AsyncIterator

from playwright.async_api import (
    async_playwright,
    Browser,
    BrowserContext,
    Page,
    Playwright,
)
from app.scrapers.anti_bot import anti_bot
from app.utils.logger import logger

# Stealth script to mask automation fingerprints
STEALTH_INIT_SCRIPT = """
() => {
    // Remove webdriver flag
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined,
        configurable: true
    });

    // Add chrome runtime stub
    window.chrome = {
        runtime: {
            id: 'kmendfapggjehodndflmmgagfalggaj',
            getManifest: () => ({}),
            connect: () => {},
        }
    };

    // Override plugins to appear as real browser
    Object.defineProperty(navigator, 'plugins', {
        get: () => [1, 2, 3, 4, 5],
        configurable: true
    });

    // Override languages
    Object.defineProperty(navigator, 'languages', {
        get: () => ['en-US', 'en'],
        configurable: true
    });

    // Override permissions
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) =>
        parameters.name === 'notifications'
            ? Promise.resolve({ state: Notification.permission })
            : originalQuery(parameters);
}
"""

_CHROMIUM_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
    "--disable-accelerated-2d-canvas",
    "--disable-gpu",
    "--disable-extensions",
    "--disable-infobars",
    "--disable-notifications",
    "--disable-popup-blocking",
    "--window-size=1920,1080",
    "--lang=en-US",
]


class BrowserManager:
    """Singleton Playwright browser manager with anti-bot stealth."""

    _instance: Optional["BrowserManager"] = None
    _lock: asyncio.Lock = asyncio.Lock()

    def __init__(self) -> None:
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._headless: bool = os.getenv("PLAYWRIGHT_HEADLESS", "true").lower() == "true"

    @classmethod
    def get_instance(cls) -> "BrowserManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def start(self) -> None:
        """Launch the Playwright Chromium browser."""
        if self._browser and self._browser.is_connected():
            return
        logger.info("Starting Playwright Chromium browser (headless=%s)…", self._headless)
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self._headless,
            args=_CHROMIUM_ARGS,
        )
        logger.info("Playwright browser started.")

    async def stop(self) -> None:
        """Gracefully close the browser and Playwright instance."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        logger.info("Playwright browser stopped.")

    @asynccontextmanager
    async def new_context(self) -> AsyncIterator[BrowserContext]:
        """
        Async context manager that yields a new stealth browser context.
        Automatically closes the context on exit.
        """
        if not self._browser or not self._browser.is_connected():
            await self.start()

        ctx_args = anti_bot.get_playwright_args()
        context: BrowserContext = await self._browser.new_context(**ctx_args)

        # Inject stealth init script into every page in this context
        await context.add_init_script(STEALTH_INIT_SCRIPT)

        try:
            yield context
        finally:
            await context.close()

    @asynccontextmanager
    async def new_page(self) -> AsyncIterator[Page]:
        """
        Async context manager that yields a stealthy page.
        Automatically closes the page and context on exit.
        """
        async with self.new_context() as context:
            page: Page = await context.new_page()
            # Block unnecessary resources to speed up scraping
            await page.route(
                "**/*.{png,jpg,jpeg,gif,webp,svg,ico,woff,woff2,ttf,otf,eot}",
                lambda route: route.abort(),
            )
            try:
                yield page
            finally:
                await page.close()


# Singleton instance
browser_manager = BrowserManager.get_instance()

__all__ = ["BrowserManager", "browser_manager"]
