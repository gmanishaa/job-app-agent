#!/usr/bin/env python3
"""Track application status across pipeline runs.

data/applications.yaml holds one entry per posting ever shown to the user,
keyed by (company, role, location) — the same key the diff and dedup use.
Statuses: seen -> tailored -> applied ("applied" is set manually until the
apply step exists). The file is plain YAML so it can be hand-edited.

Usage:
  track_applications.py upsert
      stdin: JSON list of postings (the find-jobs final list). Adds unseen
      postings with status "seen"; echoes the list back with "status" and
      "already_seen" fields so the skill can mark repeats in its table.

  track_applications.py set-status <status> [--file <tailored_file>]
      stdin: JSON posting or list of postings. Sets their status. If a
      posting wasn't tracked yet (e.g. tailoring from a direct link), it is
      added with a warning rather than rejected.
"""
from __future__ import annotations

import argparse
import datetime
import json
import sys

import yaml

from common import get_data_dir

STATUSES = ("seen", "tailored", "applied")


def entry_key(e: dict) -> str:
    return f"{e['company']}|{e['role']}|{e['location']}".lower()


def tracker_path():
    return get_data_dir() / "applications.yaml"


def load_entries() -> list[dict]:
    path = tracker_path()
    if not path.exists():
        return []
    return yaml.safe_load(path.read_text()) or []


def save_entries(entries: list[dict]) -> None:
    tracker_path().write_text(
        yaml.safe_dump(entries, sort_keys=False, allow_unicode=True)
    )


def new_entry(p: dict, status: str, today: str) -> dict:
    return {
        "company": p["company"],
        "role": p["role"],
        "location": p["location"],
        "link": p.get("link", ""),
        "source": p.get("source", ""),
        "status": status,
        "first_seen": today,
        "last_updated": today,
    }


def cmd_upsert() -> None:
    postings = json.load(sys.stdin)
    entries = load_entries()
    by_key = {entry_key(e): e for e in entries}
    today = datetime.date.today().isoformat()

    out = []
    added = 0
    for p in postings:
        existing = by_key.get(entry_key(p))
        if existing:
            out.append({**p, "status": existing["status"], "already_seen": True})
        else:
            entry = new_entry(p, "seen", today)
            entries.append(entry)
            by_key[entry_key(p)] = entry
            added += 1
            out.append({**p, "status": "seen", "already_seen": False})

    save_entries(entries)
    print(f"Tracked {added} new posting(s), {len(postings) - added} already seen",
          file=sys.stderr)
    json.dump(out, sys.stdout, indent=2)


def cmd_set_status(status: str, tailored_file: str | None) -> None:
    postings = json.load(sys.stdin)
    if isinstance(postings, dict):
        postings = [postings]

    entries = load_entries()
    by_key = {entry_key(e): e for e in entries}
    today = datetime.date.today().isoformat()

    for p in postings:
        entry = by_key.get(entry_key(p))
        if entry is None:
            print(
                f"WARNING: '{p['company']} — {p['role']}' was not in the tracker; "
                f"adding it with status '{status}'",
                file=sys.stderr,
            )
            entry = new_entry(p, status, today)
            entries.append(entry)
            by_key[entry_key(p)] = entry
        entry["status"] = status
        entry["last_updated"] = today
        if tailored_file:
            entry["tailored_file"] = tailored_file

    save_entries(entries)
    print(f"Set {len(postings)} posting(s) to '{status}'", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("upsert")
    p_set = sub.add_parser("set-status")
    p_set.add_argument("status", choices=STATUSES)
    p_set.add_argument("--file", default=None,
                       help="path of the tailored output file, recorded on the entry")
    args = parser.parse_args()

    if args.command == "upsert":
        cmd_upsert()
    else:
        cmd_set_status(args.status, args.file)


if __name__ == "__main__":
    main()
