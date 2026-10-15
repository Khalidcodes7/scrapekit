"""Selector-based field extraction."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional
from urllib.parse import urljoin


@dataclass
class Field:
    """One output column and the rule that produces it."""

    name: str
    selector: str
    attr: Optional[str] = None      # None/"text" -> text, "html" -> inner HTML, else attribute
    all: bool = False               # collect every match into a list
    regex: Optional[str] = None     # extract group 1 (or whole match)
    transform: Optional[str] = None  # strip | int | float | lower | upper
    default: Any = None


_URL_ATTRS = ("href", "src", "data-src", "action")


def _select(scope, expression: str):
    """Run a CSS (default) or XPath selector. Supports `css:` / `xpath:` prefixes."""
    expr = expression.strip()
    if expr.startswith("xpath:"):
        return scope.xpath(expr[6:].strip())
    if expr.startswith("css:"):
        return scope.css(expr[4:].strip())
    if expr.startswith(("/", "(")):
        return scope.xpath(expr)
    return scope.css(expr)


def _node_value(node, attr: Optional[str]) -> Optional[str]:
    if attr in (None, "", "text"):
        return node.xpath("string(.)").get()
    if attr in ("html", "inner_html", "outer_html"):
        return node.get()
    return node.attrib.get(attr)


def _apply_transform(value: Any, transform: Optional[str]) -> Any:
    if value is None or not transform:
        return value
    key = transform.lower()
    if key == "strip":
        return value.strip()
    if key == "lower":
        return value.lower()
    if key == "upper":
        return value.upper()
    if key == "int":
        digits = re.sub(r"[^\d\-]", "", value)
        return int(digits) if digits not in ("", "-") else 0
    if key == "float":
        digits = re.sub(r"[^\d.\-]", "", value)
        try:
            return float(digits)
        except ValueError:
            return 0.0
    raise ValueError(f"Unknown transform: {transform!r}")


def _postprocess(value: Optional[str], field: Field) -> Optional[str]:
    if value is None:
        return None
    if field.regex:
        match = re.search(field.regex, value)
        if not match:
            return None
        value = match.group(1) if match.groups() else match.group(0)
    value = _apply_transform(value, field.transform)
    if isinstance(value, str):
        value = value.strip()
    return value


def _absolutize(value: Any, field: Field, base_url: str) -> Any:
    if base_url and field.attr in _URL_ATTRS and isinstance(value, str) and value:
        return urljoin(base_url, value)
    return value


def extract_fields(scope, fields: list[Field], base_url: str = "") -> dict:
    """Extract one record from `scope` (a Selector or SelectorList) using `fields`."""
    row: dict[str, Any] = {}

    for field in fields:
        nodes = _select(scope, field.selector)

        if field.all:
            values = []
            for node in nodes:
                value = _postprocess(_node_value(node, field.attr), field)
                if value not in (None, ""):
                    values.append(_absolutize(value, field, base_url))
            row[field.name] = values if values else (field.default if field.default is not None else [])
            continue

        value = _postprocess(_node_value(nodes[0], field.attr), field) if nodes else None
        if value in (None, ""):
            row[field.name] = field.default
        else:
            row[field.name] = _absolutize(value, field, base_url)

    return row