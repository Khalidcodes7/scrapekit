"""ScrapeKit - config-driven web scraping and data extraction."""

from .exporters import export
from .fetcher import Fetcher, FetchConfig
from .parser import Field, extract_fields
from .pipeline import ScrapeConfig, Scraper

__version__ = "0.1.0"
__all__ = [
    "Fetcher",
    "FetchConfig",
    "Field",
    "ScrapeConfig",
    "Scraper",
    "export",
    "extract_fields",
    "__version__",
]