#!/usr/bin/env python3
"""Apply hard-exclude rules and split remaining postings into keyword_match vs review.

Reads a JSON list of postings from stdin (e.g. the combined output of
diff_snapshot.py across sources). Writes to stdout:

    {"keyword_match": [...], "review": [...]}

keyword_match postings hit an include-keyword and need no further processing.
review postings survived the hard excludes but didn't hit a keyword -- the
find-jobs skill runs an LLM judgment pass over these against the user's
profile before deciding whether to include them.
"""
from __future__ import annotations

import json
import re
import sys

from common import get_max_age_days, load_sources_config


def matches_any(text: str, terms: list[str]) -> bool:
    text_lower = text.lower()
    return any(term.lower() in text_lower for term in terms)


def matches_any_word(text: str, terms: list[str]) -> bool:
    """Word-boundary match, for location terms.

    Substring matching would be wrong here: two-letter state/province codes
    like 'CA' or 'ON' appear inside ordinary words ('Africa', 'London').
    """
    return any(
        re.search(rf"\b{re.escape(term)}\b", text, re.IGNORECASE) for term in terms
    )


def main():
    config = load_sources_config()
    filters = config.get("filters", {})

    postings = json.load(sys.stdin)

    locations_exclude = filters.get("locations_exclude", [])
    locations_include = filters.get("locations_include", [])
    seniority_exclude = filters.get("seniority_exclude", [])
    keywords_exclude = filters.get("keywords_exclude", [])
    keywords_include = filters.get("keywords_include", [])
    max_age_days = get_max_age_days(config)

    keyword_match = []
    review = []
    too_old = 0
    dupes = 0
    loc_unverified = 0
    seen = set()

    for p in postings:
        haystack = (f"{p['role']} {p['location']} {p['company']} "
                    f"{p.get('category', '')} {p.get('sponsorship', '')}")

        # Unknown age (None) is kept — only drop postings known to be stale.
        age = p.get("age_days")
        if age is not None and age > max_age_days:
            too_old += 1
            continue
        # Exact dupes: repeated rows within a source and the same posting
        # tracked by multiple sources.
        key = f"{p['company']}|{p['role']}|{p['location']}".lower()
        if key in seen:
            dupes += 1
            continue
        seen.add(key)
        if matches_any(p["location"], locations_exclude):
            continue
        if matches_any(p["role"], seniority_exclude):
            continue
        if matches_any(haystack, keywords_exclude):
            continue

        # Location allowlist: a posting whose location matches no include
        # term is NOT dropped — location strings are too messy for that
        # ("NYC", "Amsterdam", "Ottawa, CA"). It goes to review, flagged, so
        # the LLM pass decides from the actual string.
        if locations_include and not matches_any_word(p["location"], locations_include):
            loc_unverified += 1
            review.append({**p, "location_unverified": True})
            continue

        if matches_any(p["role"], keywords_include):
            keyword_match.append(p)
        else:
            review.append(p)

    if too_old:
        print(f"Dropped {too_old} postings older than {max_age_days} day(s)", file=sys.stderr)
    if dupes:
        print(f"Dropped {dupes} duplicate postings", file=sys.stderr)
    if loc_unverified:
        print(f"{loc_unverified} postings sent to review with unverified locations",
              file=sys.stderr)
    json.dump({"keyword_match": keyword_match, "review": review}, sys.stdout, indent=2)


if __name__ == "__main__":
    main()
