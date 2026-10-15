"""Command line interface: `scrapekit run config.yaml -o out.csv`."""
from __future__ import annotations

import argparse
import logging
import sys
import time

from .exporters import export
from .fetcher import Fetcher, FetchConfig
from .pipeline import ScrapeConfig, Scraper

logger = logging.getLogger("scrapekit")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scrapekit",
        description="Config-driven web scraping and data extraction.",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="run a scrape job from a YAML/JSON config")
    run.add_argument("config", help="path to config file")
    run.add_argument("-o", "--output", required=True, help="output file (.csv/.json/.jsonl/.xlsx)")
    run.add_argument("--format", choices=["csv", "json", "jsonl", "xlsx"], help="override format")
    run.add_argument("--max-pages", type=int, help="override max_pages")
    run.add_argument("--max-items", type=int, help="stop after N records")
    run.add_argument("--delay", type=float, help="seconds between requests")
    run.add_argument("--render", action="store_true", help="render JS with Playwright")
    run.add_argument("--no-robots", action="store_true", help="ignore robots.txt (use responsibly)")
    run.add_argument("--columns", nargs="*", help="subset/order of output columns")

    fetch = sub.add_parser("fetch", help="fetch one URL (debugging)")
    fetch.add_argument("url")
    fetch.add_argument("-o", "--output", help="write HTML here instead of stdout")
    fetch.add_argument("--render", action="store_true")
    fetch.add_argument("--no-robots", action="store_true")

    return parser


def cmd_fetch(args) -> int:
    config = FetchConfig(render=args.render, respect_robots=not args.no_robots)
    with Fetcher(config) as fetcher:
        html = fetcher.get(args.url)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(html)
        logger.info("Wrote %d bytes to %s", len(html), args.output)
    else:
        print(html)
    return 0


def cmd_run(args) -> int:
    config = ScrapeConfig.from_file(args.config)
    if args.max_pages is not None:
        config.max_pages = args.max_pages
    if args.max_items is not None:
        config.max_items = args.max_items
    if args.delay is not None:
        config.fetch.delay = args.delay
    if args.render:
        config.fetch.render = True
    if args.no_robots:
        config.fetch.respect_robots = False

    output = args.output
    if args.format and not output.lower().endswith(f".{args.format}"):
        output = f"{output}.{args.format}"

    started = time.time()
    rows = []
    with Scraper(config) as scraper:
        for record in scraper.run():
            rows.append(record)
            if len(rows) % 25 == 0:
                logger.info("Scraped %d records", len(rows))

    written = export(rows, output, columns=args.columns)
    logger.info("Done: %d records -> %s (%.1fs)", written, output, time.time() - started)
    return 0


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s",
        datefmt="%H:%M:%S",
    )
    try:
        if args.command == "fetch":
            return cmd_fetch(args)
        return cmd_run(args)
    except KeyboardInterrupt:
        logger.warning("Interrupted")
        return 130
    except Exception as exc:  # noqa: BLE001 - top-level CLI handler
        logger.error("%s: %s", type(exc).__name__, exc)
        if args.verbose:
            raise
        return 1


if __name__ == "__main__":
    sys.exit(main())