"""Shared helpers for the job-app-agent scripts."""
from __future__ import annotations

import datetime
import os
import re
import sys
from pathlib import Path

import yaml

MAX_AGE_DAYS_CAP = 3


def get_data_dir() -> Path:
    env = os.environ.get("JOB_AGENT_DATA_DIR")
    if env:
        return Path(env).expanduser().resolve()
    return (Path(__file__).resolve().parent.parent.parent / "data").resolve()


def load_sources_config() -> dict:
    path = get_data_dir() / "sources.yaml"
    if not path.exists():
        raise FileNotFoundError(
            f"No config at {path}. Copy config/sources.example.yaml there and fill it in."
        )
    with open(path) as f:
        return yaml.safe_load(f)


def _split_row(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _is_separator_row(cells: list[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-+:?", c) for c in cells)


def parse_markdown_table(markdown_text: str) -> list[dict]:
    """Parse every markdown table in the text into a list of row dicts keyed by header.

    The job-list READMEs often contain several tables (split by category or
    month), each with its own header, so tables are parsed independently and
    the rows concatenated. normalize_rows() reconciles the varying headers.

    A block of |-lines only starts a *new* table when its second line is a
    separator row (header | --- | ...). Otherwise it's treated as a
    continuation of the current table — this happens when a stray newline
    inside a cell splits a table in two, and would otherwise misread a data
    row as the header, junking every row after it.
    """
    rows: list[dict] = []
    header: list[str] | None = None
    block: list[str] = []

    def flush() -> None:
        nonlocal header
        if len(block) >= 2 and _is_separator_row(_split_row(block[1])):
            header = _split_row(block[0])
            data_lines = block[2:]
        elif header is not None:
            data_lines = block
        else:
            return  # pipe-lines before any table header: not a table
        for line in data_lines:
            cells = _split_row(line)
            if _is_separator_row(cells) or len(cells) != len(header):
                continue
            rows.append(dict(zip(header, cells)))

    for line in markdown_text.splitlines() + [""]:  # sentinel flushes last block
        if line.strip().startswith("|"):
            block.append(line)
        elif block:
            flush()
            block = []
    return rows


def get_max_age_days(config: dict) -> int:
    """Read max_age_days from config, defaulting to 1 and clamping to 1..3."""
    raw = config.get("max_age_days", 1)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        print(f"WARNING: max_age_days={raw!r} is not a number; using 1", file=sys.stderr)
        return 1
    if value > MAX_AGE_DAYS_CAP:
        print(f"WARNING: max_age_days={value} capped at {MAX_AGE_DAYS_CAP}", file=sys.stderr)
        return MAX_AGE_DAYS_CAP
    if value < 1:
        print(f"WARNING: max_age_days={value} raised to 1", file=sys.stderr)
        return 1
    return value


def parse_age_days(cell: str) -> int | None:
    """Parse an age cell into whole days.

    Handles '0d'/'12h'/'2w'/'1mo' relative ages and 'Jul 05'-style dates
    (assumed to be the most recent past occurrence of that month/day).
    Returns None when the cell matches neither — unknown ages are kept,
    not dropped.
    """
    text = cell.strip()
    m = re.match(r"(\d+)\s*(h|d|w|mo)$", text.lower())
    if m:
        n, unit = int(m.group(1)), m.group(2)
        return {"h": 0, "d": n, "w": n * 7, "mo": n * 30}[unit]

    try:
        parsed = datetime.datetime.strptime(text.title(), "%b %d")
    except ValueError:
        return None
    today = datetime.date.today()
    posted = parsed.date().replace(year=today.year)
    if posted > today:
        posted = posted.replace(year=today.year - 1)
    return (today - posted).days


def strip_markdown_link(cell: str) -> tuple[str, str | None]:
    """Extract (text, url) from a table cell.

    Handles [text](url) markdown links (including bold/italic-wrapped, e.g.
    **[SAP](url)**) and HTML anchors (e.g. <a href="url"><strong>NVIDIA</strong></a>,
    where the anchor body may be an <img> — then text comes back empty).
    Plain cells return (cell text, None) with any stray HTML tags removed.
    """
    cell = cell.strip()

    m = re.search(r'<a\s[^>]*href="([^"]+)"[^>]*>(.*?)</a>', cell, re.S)
    if m:
        text = re.sub(r"<[^>]+>", "", m.group(2)).strip()
        return text, m.group(1)

    m = re.match(r"\[([^\]]+)\]\(([^)]+)\)", cell.strip("*_ "))
    if m:
        return m.group(1).strip("*_ "), m.group(2)

    return re.sub(r"<[^>]+>", "", cell).strip("*_ ").strip(), None
