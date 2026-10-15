"""Programmatic usage of ScrapeKit.

Run from the project root:
    python examples/quickstart.py
"""
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
        Field(name="tags", selector="css:p.star-rating", attr="class", all=True),
    ],
)

with Scraper(config) as scraper:
    rows = list(scraper.run())

print(f"Scraped {len(rows)} records")
for row in rows[:3]:
    print(row)

export(rows, "books.csv")
export(rows, "books.jsonl")
print("Wrote books.csv and books.jsonl")