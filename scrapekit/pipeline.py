"""Job orchestration: pagination, iteration, record production."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Iterator, Optional
from urllib.parse import urljoin

import yaml
from parsel import Selector

from .fetcher import Fetcher, FetchConfig
from .parser import Field, _select, extract_fields

logger = logging.getLogger(__name__)


@dataclass
class ScrapeConfig:
    """Declarative description of a scrape job."""

    start_urls: list
    fields: list
    name: str = "scrape"
    item_selector: Optional[str] = None   # selector for repeating item container
    next_page: Optional[str] = None       # selector for the "next page" link
    max_pages: int = 1
    max_items: Optional[int] = None
    fetch: FetchConfig = field(default_factory=FetchConfig)

    @classmethod
    def from_dict(cls, data: dict) -> "ScrapeConfig":
        data = dict(data)
        fetch = FetchConfig(**(data.pop("fetch", None) or {}))
        raw_fields = data.pop("fields", [])
        fields = [f if isinstance(f, Field) else Field(**f) for f in raw_fields]

        urls = data.pop("start_urls", [])
        if isinstance(urls, str):
            urls = [urls]
        if not urls:
            raise ValueError("Config requires 'start_urls'")
        if not fields:
            raise ValueError("Config requires at least one field")

        return cls(start_urls=urls, fields=fields, fetch=fetch, **data)

    @classmethod
    def from_file(cls, path: str) -> "ScrapeConfig":
        with open(path, "r", encoding="utf-8") as handle:
            text = handle.read()
        if path.endswith((".yaml", ".yml")):
            data = yaml.safe_load(text)
        else:
            data = json.loads(text)
        return cls.from_dict(data)


class Scraper:
    """Runs a ScrapeConfig and yields records as dictionaries."""

    def __init__(self, config: ScrapeConfig) -> None:
        self.config = config
        self.fetcher = Fetcher(config.fetch)

    def run(self) -> Iterator[dict]:
        seen: set[str] = set()
        queue = list(self.config.start_urls)
        pages = 0
        count = 0

        while queue:
            url = queue.pop(0)
            if url in seen:
                continue
            seen.add(url)

            pages += 1
            logger.info("Page %d/%d -> %s", pages, self.config.max_pages, url)
            html = self.fetcher.get(url)
            selector = Selector(html, base_url=url)

            if self.config.item_selector:
                items = _select(selector, self.config.item_selector)
            else:
                items = [selector]

            logger.debug("%d item node(s) matched", len(items))

            for item in items:
                record = extract_fields(item, self.config.fields, base_url=url)
                record.setdefault("_source_url", url)
                count += 1
                yield record
                if self.config.max_items and count >= self.config.max_items:
                    logger.info("Reached max_items=%d", self.config.max_items)
                    return

            if pages >= self.config.max_pages:
                break

            if self.config.next_page:
                link = _select(selector, self.config.next_page)
                if link:
                    node = link[0]
                    href = node.attrib.get("href") if node.attrib else node.get()
                    if href:
                        queue.append(urljoin(url, href))
                    else:
                        logger.debug("next_page selector matched but no href found")
                else:
                    logger.info("No next page found - stopping")

        logger.info("Finished: %d records from %d page(s)", count, pages)

    def close(self) -> None:
        self.fetcher.close()

    def __enter__(self) -> "Scraper":
        return self

    def __exit__(self, *exc) -> None:
        self.close()