from parsel import Selector

from scrapekit.parser import Field, extract_fields
from scrapekit.pipeline import ScrapeConfig

HTML = """
<html><body>
  <article class="product">
    <h3><a href="/item/1" title="Widget">Widget</a></h3>
    <p class="price">£12.50</p>
    <span class="tag">new</span>
    <span class="tag">sale</span>
  </article>
  <article class="product">
    <h3><a href="/item/2" title="Gadget">Gadget</a></h3>
    <p class="price">£7.00</p>
  </article>
</body></html>
"""


def _scope():
    return Selector(HTML).css("article.product")


def test_extracts_text_and_attribute():
    row = extract_fields(_scope(), [
        Field(name="title", selector="css:h3 a", attr="title"),
        Field(name="href", selector="css:h3 a", attr="href"),
        Field(name="price", selector="p.price", transform="float"),
    ], base_url="https://example.com/list")
    assert row["title"] == "Widget"
    assert row["href"] == "https://example.com/item/1"
    assert row["price"] == 12.5


def test_all_returns_list():
    row = extract_fields(_scope(), [
        Field(name="tags", selector="css:span.tag", all=True),
    ])
    assert row["tags"] == ["new", "sale"]


def test_regex_and_default():
    row = extract_fields(_scope(), [
        Field(name="currency", selector="p.price", regex=r"([^\d\s]+)"),
        Field(name="missing", selector="css:.nope", default="n/a"),
    ])
    assert row["currency"] == "£"
    assert row["missing"] == "n/a"


def test_config_from_dict_builds_fields():
    config = ScrapeConfig.from_dict({
        "start_urls": "https://example.com",
        "fields": [{"name": "t", "selector": "css:h1"}],
    })
    assert config.start_urls == ["https://example.com"]
    assert isinstance(config.fields[0], Field)