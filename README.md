# ScrapeKit

> Config-driven web scraping and data extraction toolkit — extract structured data from any website with CSS or XPath selectors, in minutes.

[![CI](https://github.com/Khalidcodes7/scrapekit/actions/workflows/ci.yml/badge.svg)](https://github.com/Khalidcodes7/scrapekit/actions)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PyPI-style](https://img.shields.io/badge/install-pip%20install%20--e%20.-blueviolet.svg)](#installation)

ScrapeKit is a lightweight, production-ready toolkit for extracting structured data from websites. Define **what** you want in a simple YAML file — ScrapeKit handles the rest: retries, throttling, robots.txt compliance, pagination, and export to CSV / JSON / JSONL / Excel.

Built for developers, data analysts, and businesses that need reliable data extraction **without** the complexity of heavy frameworks.

---

## ✨ Features

- 🎯 **Config-driven** — describe your target in YAML, no code required
- 🔁 **Automatic pagination** — follow "next page" links until done
- 🧠 **CSS & XPath selectors** — `css:h3 a` or `xpath://div[@class="x"]`
- 🧹 **Field transforms** — `strip`, `int`, `float`, `lower`, `upper`
- 🔍 **Regex extraction** — pull out just the part you need
- 🔗 **URL absolutization** — relative links automatically become full URLs
- 🛡️ **robots.txt aware** — respects site rules by default
- ⏱️ **Polite throttling** — configurable delay + jitter between requests
- 🔄 **Automatic retries** — handles 429 / 5xx with exponential backoff
- 📤 **Multiple exports** — CSV, JSON, JSONL, Excel
- 🖥️ **CLI + Python API** — use it as a tool or a library
- 🧪 **Tested** — pytest suite with CI on every push

---

## 📦 Installation

### From source (recommended)

```bash
git clone https://github.com/Khalidcodes7/scrapekit.git
cd scrapekit
pip install -e .
```

### Optional extras

```bash
# Render JavaScript-heavy pages with Playwright
pip install -e ".[render]"
playwright install chromium

# Excel export support
pip install -e ".[excel]"
```

---

## 🚀 Quick Start

### 1. Write a config file — `my_scrape.yaml`

```yaml
name: books
start_urls:
  - https://books.toscrape.com/catalogue/page-1.html

item_selector: "css:article.product_pod"
next_page: "css:li.next a"
max_pages: 5

fetch:
  delay: 1.0
  respect_robots: true

fields:
  - name: title
    selector: "css:h3 a"
    attr: title

  - name: price
    selector: "css:p.price_color"
    transform: float

  - name: product_url
    selector: "css:h3 a"
    attr: href
```

### 2. Run it

```bash
scrapekit run my_scrape.yaml -o books.csv
```

Or via Python module:

```bash
python -m scrapekit.cli run my_scrape.yaml -o books.csv
```

### 3. Get your data

```csv
title,price,product_url,_source_url
A Light in the Attic,51.77,https://books.toscrape.com/...,https://books.toscrape.com/...
Tipping the Velvet,53.74,https://books.toscrape.com/...,https://books.toscrape.com/...
```

---

## 🐍 Python API

Use ScrapeKit directly from your code:

```python
from scrapekit import Field, ScrapeConfig, Scraper, export

config = ScrapeConfig(
    start_urls=["https://books.toscrape.com/catalogue/page-1.html"],
    item_selector="css:article.product_pod",
    next_page="css:li.next a",
    max_pages=3,
    fields=[
        Field(name="title", selector="css:h3 a", attr="title"),
        Field(name="price", selector="css:p.price_color", transform="float"),
        Field(name="url", selector="css:h3 a", attr="href"),
    ],
)

with Scraper(config) as scraper:
    rows = list(scraper.run())

export(rows, "books.csv")
export(rows, "books.jsonl")
```

---

## 🖥️ CLI Reference

### `scrapekit run <config> -o <output>`

Run a scrape job from a YAML or JSON config.

| Flag | Description |
|------|-------------|
| `-o, --output` | Output file — `.csv`, `.json`, `.jsonl`, or `.xlsx` |
| `--format` | Force a specific format |
| `--max-pages N` | Override config's `max_pages` |
| `--max-items N` | Stop after N records |
| `--delay S` | Override delay between requests (seconds) |
| `--render` | Use Playwright for JS-rendered pages |
| `--no-robots` | Ignore robots.txt (use responsibly) |
| `--columns col1 col2` | Subset / reorder output columns |
| `-v, --verbose` | Debug logging |

### `scrapekit fetch <url>`

Fetch a single URL and print (or save) the HTML. Useful for debugging selectors.

```bash
scrapekit fetch https://example.com -o page.html
```

---

## 📚 Config Reference

### Top-level keys

| Key | Type | Description |
|-----|------|-------------|
| `name` | string | Job label (used in logs) |
| `start_urls` | list / string | One or more URLs to begin from |
| `item_selector` | selector | Repeating item container (omit for single-record pages) |
| `next_page` | selector | "Next page" link selector for pagination |
| `max_pages` | int | Stop after N pages |
| `max_items` | int | Stop after N records |
| `fetch` | object | Networking options (see below) |
| `fields` | list | Field definitions (see below) |

### `fetch` options

| Key | Default | Description |
|-----|---------|-------------|
| `delay` | `1.0` | Seconds between requests |
| `jitter` | `0.3` | Random extra delay to avoid patterns |
| `timeout` | `20.0` | Request timeout in seconds |
| `retries` | `3` | Number of retries on failure |
| `respect_robots` | `true` | Honor robots.txt |
| `user_agent` | custom | Override the default user agent |
| `headers` | `{}` | Extra HTTP headers |
| `proxies` | `null` | Proxy config dict |
| `render` | `false` | Use Playwright for JS pages |

### Field options

| Key | Default | Description |
|-----|---------|-------------|
| `name` | required | Output column name |
| `selector` | required | CSS (`css:`) or XPath (`xpath:`) selector |
| `attr` | `text` | `text`, `html`, or any HTML attribute (`href`, `src`, `title`, ...) |
| `all` | `false` | Collect all matches into a list |
| `regex` | `null` | Extract group 1 (or whole match) from the value |
| `transform` | `null` | `strip`, `int`, `float`, `lower`, `upper` |
| `default` | `null` | Value used when the selector matches nothing |

---

## 🗂️ Project Structure

```
scrapekit/
├── scrapekit/              # Main package
│   ├── __init__.py        # Public API
│   ├── cli.py             # Command-line interface
│   ├── exporters.py       # CSV / JSON / JSONL / Excel writers
│   ├── fetcher.py         # HTTP layer (retries, throttling, robots.txt)
│   ├── parser.py          # Selector-based field extraction
│   └── pipeline.py        # Job orchestration + pagination
├── examples/
│   ├── books.yaml         # Demo config
│   └── quickstart.py      # Programmatic usage example
├── tests/
│   └── test_parser.py     # Pytest suite
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## ⚖️ Legal & Ethical Use

ScrapeKit is built to be **respectful**:

- Respects `robots.txt` by default (disable with `--no-robots` at your own risk)
- Default delay prevents overloading target servers
- Custom User-Agent identifies the tool

**You are responsible** for complying with the target website's Terms of Service and applicable laws (GDPR, CFAA, etc.). Only scrape data you have the right to access.

---

## 🧪 Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest -v

# Run the demo
python -m scrapekit.cli run examples/books.yaml -o books.csv
```

---

## 📄 License

MIT — see [LICENSE](LICENSE).

---

## 💼 Hire Me

Need a **custom scraper** for a specific website, dataset, or API? I build production-grade data extraction pipelines — from simple product listings to complex multi-page e-commerce and marketplace scrapes.

📧 **Contact:** k.naveedfsd1968@gmail.com
🔗 **GitHub:** [@Khalidcodes7](https://github.com/Khalidcodes7)