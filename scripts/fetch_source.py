#!/usr/bin/env python3
"""Fetch a source's job listing page and save a dated snapshot.

Usage: python fetch_source.py <source_name>
"""
from __future__ import annotations

import datetime
import json
import sys
import time

import requests

from common import (
    get_data_dir,
    load_sources_config,
    parse_age_days,
    parse_markdown_table,
    strip_markdown_link,
)


def normalize_rows(raw_rows: list[dict]) -> list[dict]:
    """Best-effort mapping from a repo's table headers to a common schema.

    Column names vary between repos, so this checks a few common header
    spellings. If a source uses something different, add its header name
    to the lists below rather than writing a one-off parser.
    """
    records = []
    last_company = ""
    for row in raw_rows:
        company_cell = row.get("Company") or row.get("Company Name") or ""
        role_cell = row.get("Role") or row.get("Position") or row.get("Title") or ""
        location_cell = row.get("Location") or ""
        link_cell = row.get("Application/Link") or row.get("Link") or row.get("Apply") or ""
        age_cell = row.get("Age") or row.get("Date Posted") or row.get("Date") or ""

        company, _ = strip_markdown_link(company_cell)
        role, role_link = strip_markdown_link(role_cell)
        _, link = strip_markdown_link(link_cell)

        # Repos mark "same company as the row above" with an arrow.
        company = company.strip()
        if company in ("↳", "→"):
            company = last_company
        elif company:
            last_company = company

        records.append({
            "company": company,
            "role": role.strip(),
            "location": location_cell.strip(),
            "link": (link or role_link or "").strip(),
            "age_days": parse_age_days(age_cell),
        })
    return records


def normalize_json_listings(listings: list[dict]) -> list[dict]:
    """Map a Simplify-style listings.json to the common schema.

    Skips inactive listings. age_days comes from the unix `date_posted`.
    """
    records = []
    now = time.time()
    for item in listings:
        if not item.get("active", True):
            continue
        locations = item.get("locations") or []
        if not isinstance(locations, list):
            locations = [str(locations)]
        date_posted = item.get("date_posted")
        records.append({
            "company": (item.get("company_name") or "").strip(),
            "role": (item.get("title") or "").strip(),
            "location": "; ".join(l.strip() for l in locations),
            "link": (item.get("url") or "").strip(),
            "age_days": int((now - date_posted) // 86400) if date_posted else None,
            "category": (item.get("category") or "").strip(),
        })
    return records


def main():
    if len(sys.argv) != 2:
        print("Usage: fetch_source.py <source_name>", file=sys.stderr)
        sys.exit(1)

    source_name = sys.argv[1]
    config = load_sources_config()
    source = next((s for s in config["repos"] if s["name"] == source_name), None)
    if source is None:
        print(f"No source named '{source_name}' in sources.yaml", file=sys.stderr)
        sys.exit(1)

    resp = requests.get(source["url"], timeout=30)
    resp.raise_for_status()

    source_type = source.get("type", "markdown")
    if source_type == "json":
        records = normalize_json_listings(resp.json())
    elif source_type == "markdown":
        records = normalize_rows(parse_markdown_table(resp.text))
    else:
        print(f"Unknown source type '{source_type}' for {source_name}", file=sys.stderr)
        sys.exit(1)

    for r in records:
        r["source"] = source_name

    today = datetime.date.today().isoformat()
    snapshot_dir = get_data_dir() / "snapshots" / source_name
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    # Raw snapshot keeps the fetched page for later inspection (e.g. when a
    # parse anomaly needs a human/LLM look). The `raw.` prefix keeps it out
    # of diff_snapshot's `????-??-??.json` glob.
    raw_ext = "json" if source_type == "json" else "md"
    (snapshot_dir / f"raw.{today}.{raw_ext}").write_text(resp.text)
    (snapshot_dir / f"{today}.json").write_text(json.dumps(records, indent=2))

    print(f"Fetched {len(records)} postings from {source_name} -> {snapshot_dir / f'{today}.json'}")


if __name__ == "__main__":
    main()
