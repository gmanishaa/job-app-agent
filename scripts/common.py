"""Shared helpers for the job-app-agent scripts."""
from __future__ import annotations

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


def _parse_table_block(block: list[str]) -> list[dict]:
    """Parse one contiguous block of |-lines: first line is the header."""
    header = _split_row(block[0])
    rows = []
    for line in block[1:]:
        cells = _split_row(line)
        if _is_separator_row(cells) or len(cells) != len(header):
            continue
        rows.append(dict(zip(header, cells)))
    return rows


def parse_markdown_table(markdown_text: str) -> list[dict]:
    """Parse every markdown table in the text into a list of row dicts keyed by header.

    The job-list READMEs often contain several tables (split by category or
    month), each with its own header, so tables are parsed independently and
    the rows concatenated. normalize_rows() reconciles the varying headers.
    """
    rows: list[dict] = []
    block: list[str] = []
    for line in markdown_text.splitlines() + [""]:  # sentinel flushes last block
        if line.strip().startswith("|"):
            block.append(line)
        elif block:
            rows.extend(_parse_table_block(block))
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
    """Parse an age cell like '0d', '12h', '2w', '1mo' into whole days.

    Returns None when the cell doesn't match that pattern (e.g. a literal
    date, or an empty cell) — unknown ages are kept, not dropped.
    """
    m = re.match(r"(\d+)\s*(h|d|w|mo)$", cell.strip().lower())
    if not m:
        return None
    n, unit = int(m.group(1)), m.group(2)
    return {"h": 0, "d": n, "w": n * 7, "mo": n * 30}[unit]


def strip_markdown_link(cell: str) -> tuple[str, str | None]:
    """Given a cell that may be a [text](url) link, return (text, url)."""
    m = re.match(r"\[([^\]]+)\]\(([^)]+)\)", cell.strip())
    if m:
        return m.group(1), m.group(2)
    return cell, None
