"""Row exporters: CSV, JSON, JSONL, Excel."""
from __future__ import annotations

import csv
import json
import os
from typing import Optional, Sequence


def _flat(value):
    """Flatten lists/dicts so they fit in a spreadsheet cell."""
    if isinstance(value, list):
        return " | ".join(_flat(v) for v in value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    return value


def _columns(rows: list[dict], columns: Optional[Sequence[str]]) -> list[str]:
    if columns:
        return list(columns)
    ordered: list[str] = []
    for row in rows:
        for key in row:
            if key not in ordered:
                ordered.append(key)
    return ordered


def to_csv(rows, path, columns=None, **_) -> int:
    rows = list(rows)
    cols = _columns(rows, columns)
    with open(path, "w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=cols, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _flat(row.get(key)) for key in cols})
    return len(rows)


def to_json(rows, path, columns=None, indent: int = 2, **_) -> int:
    rows = list(rows)
    if columns:
        rows = [{key: row.get(key) for key in columns} for row in rows]
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(rows, handle, ensure_ascii=False, indent=indent)
    return len(rows)


def to_jsonl(rows, path, columns=None, **_) -> int:
    count = 0
    with open(path, "w", encoding="utf-8") as handle:
        for row in rows:
            if columns:
                row = {key: row.get(key) for key in columns}
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
    return count


def to_excel(rows, path, columns=None, **_) -> int:
    try:
        from openpyxl import Workbook
    except ImportError as exc:
        raise RuntimeError("Excel export requires openpyxl: pip install openpyxl") from exc

    rows = list(rows)
    cols = _columns(rows, columns)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "data"
    sheet.append(cols)
    for row in rows:
        sheet.append([_flat(row.get(key)) for key in cols])
    workbook.save(path)
    return len(rows)


EXPORTERS = {
    ".csv": to_csv,
    ".json": to_json,
    ".jsonl": to_jsonl,
    ".xlsx": to_excel,
}


def export(rows, path: str, columns: Optional[Sequence[str]] = None) -> int:
    """Write rows to `path`, choosing the format from the file extension."""
    ext = os.path.splitext(path)[1].lower()
    exporter = EXPORTERS.get(ext)
    if exporter is None:
        raise ValueError(f"Unsupported format {ext!r}. Choose from {sorted(EXPORTERS)}")
    return exporter(rows, path, columns=columns)