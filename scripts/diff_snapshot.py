#!/usr/bin/env python3
"""Compare today's snapshot against the most recent prior one and print new postings.

Diffs against the most recent prior snapshot (not strictly "yesterday"), so
gaps between manual runs never cause postings to be silently missed.

Usage: python diff_snapshot.py <source_name>
"""
from __future__ import annotations

import datetime
import json
import sys

from common import get_data_dir


def record_key(r: dict) -> str:
    # Deliberately excludes the link: sources rewrite URLs (tracking params,
    # aggregator swaps), which would resurface old postings as "new". Matches
    # the dedup key in filter_jobs.py.
    return f"{r['company']}|{r['role']}|{r['location']}".lower()


def main():
    if len(sys.argv) != 2:
        print("Usage: diff_snapshot.py <source_name>", file=sys.stderr)
        sys.exit(1)

    source_name = sys.argv[1]
    snapshot_dir = get_data_dir() / "snapshots" / source_name
    snapshots = sorted(snapshot_dir.glob("????-??-??.json"))

    if not snapshots:
        print("[]")
        return

    today = datetime.date.today().isoformat()
    today_path = snapshot_dir / f"{today}.json"
    if today_path not in snapshots:
        print(f"No snapshot for today ({today}). Run fetch_source.py first.", file=sys.stderr)
        sys.exit(1)

    prior_snapshots = [p for p in snapshots if p != today_path]
    today_records = json.loads(today_path.read_text())

    if not prior_snapshots:
        # First run ever for this source: everything counts as new.
        print(json.dumps(today_records, indent=2))
        return

    prior_records = json.loads(prior_snapshots[-1].read_text())
    prior_keys = {record_key(r) for r in prior_records}

    # A big drop in total rows usually means the source changed format and
    # parsing broke, not that jobs vanished. Warn instead of failing silently.
    if len(today_records) < len(prior_records) / 2:
        print(
            f"WARNING: today's snapshot has {len(today_records)} rows vs "
            f"{len(prior_records)} in the prior one ({prior_snapshots[-1].name}) — "
            f"the source may have changed format. Check raw.{today}.* in {snapshot_dir}.",
            file=sys.stderr,
        )

    new_records = [r for r in today_records if record_key(r) not in prior_keys]
    print(json.dumps(new_records, indent=2))


if __name__ == "__main__":
    main()
