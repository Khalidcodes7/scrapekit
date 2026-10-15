"""HTTP fetching layer: retries, throttling, robots.txt, optional JS rendering."""
from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0 Safari/537.36 ScrapeKit/0.1"
)


@dataclass
class FetchConfig:
    """Networking behaviour for a scrape job."""

    delay: float = 1.0
    jitter: float = 0.3
    timeout: float = 20.0
    retries: int = 3
    respect_robots: bool = True
    user_agent: str = DEFAULT_UA
    headers: dict = field(default_factory=dict)
    proxies: Optional[dict] = None
    render: bool = False


class RobotsCache:
    """Fetches and caches robots.txt per host."""

    def __init__(self, user_agent: str) -> None:
        self.user_agent = user_agent
        self._cache: dict[str, Optional[RobotFileParser]] = {}

    def allowed(self, url: str) -> bool:
        parts = urlparse(url)
        root = f"{parts.scheme}://{parts.netloc}"
        if root not in self._cache:
            parser = RobotFileParser()
            parser.set_url(urljoin(root, "/robots.txt"))
            try:
                parser.read()
            except Exception as exc:
                logger.warning("robots.txt unreadable for %s (%s) - allowing", root, exc)
                parser = None
            self._cache[root] = parser
        parser = self._cache[root]
        return True if parser is None else parser.can_fetch(self.user_agent, url)


class Fetcher:
    """Session-based fetcher with retries, throttling and robots.txt support."""

    def __init__(self, config: Optional[FetchConfig] = None) -> None:
        self.config = config or FetchConfig()

        self.session = requests.Session()
        retry = Retry(
            total=self.config.retries,
            backoff_factor=0.6,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset(["GET", "HEAD"]),
            respect_retry_after_header=True,
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=20, pool_maxsize=20)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self.session.headers.update(
            {"User-Agent": self.config.user_agent, "Accept-Language": "en-US,en;q=0.9"}
        )
        if self.config.headers:
            self.session.headers.update(self.config.headers)
        if self.config.proxies:
            self.session.proxies.update(self.config.proxies)

        self._robots = RobotsCache(self.config.user_agent)
        self._last_request = 0.0
        self._playwright = None
        self._browser = None

    def get(self, url: str, **kwargs) -> str:
        """Fetch a URL and return decoded HTML."""
        if self.config.respect_robots and not self._robots.allowed(url):
            raise PermissionError(f"Blocked by robots.txt: {url}")

        self._throttle()
        logger.debug("GET %s", url)

        if self.config.render:
            return self._render(url)

        response = self.session.get(url, timeout=self.config.timeout, **kwargs)
        response.raise_for_status()
        if not response.encoding or response.encoding.lower() == "iso-8859-1":
            response.encoding = response.apparent_encoding
        return response.text

    def close(self) -> None:
        self.session.close()
        if self._browser is not None:
            self._browser.close()
            self._browser = None
        if self._playwright is not None:
            self._playwright.stop()
            self._playwright = None

    def __enter__(self) -> "Fetcher":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def _throttle(self) -> None:
        if self.config.delay <= 0:
            return
        elapsed = time.monotonic() - self._last_request
        wait = self.config.delay - elapsed
        if wait > 0:
            time.sleep(wait + random.uniform(0, self.config.jitter))
        self._last_request = time.monotonic()

    def _render(self, url: str) -> str:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError(
                "render=True requires Playwright: pip install 'scrapekit[render]' "
                "&& playwright install chromium"
            ) from exc

        if self._playwright is None:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=True)

        page = self._browser.new_page(user_agent=self.config.user_agent)
        try:
            page.goto(url, timeout=self.config.timeout * 1000, wait_until="networkidle")
            return page.content()
        finally:
            page.close()