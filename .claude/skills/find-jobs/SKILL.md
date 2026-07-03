---
name: find-jobs
description: Fetch today's postings from tracked GitHub job-list repos, filter them, run an LLM review pass on borderline postings, and present a numbered list to the user.
---

# find-jobs

Run this when the user asks to check for new job postings.

## Setup check

Confirm `data/sources.yaml` exists (the sibling `data/` directory next to
this repo, or `$JOB_AGENT_DATA_DIR` if set). If it doesn't exist, tell the
user to copy `agent/config/sources.example.yaml` there and fill it in, then
stop.

## Steps

In all commands below, use `.venv/bin/python` (the venv created during
README setup) — the system Python does not have the dependencies.

1. For each entry in `repos` in `data/sources.yaml`, run:
   `.venv/bin/python scripts/fetch_source.py <name>`
   If one source fails (network error, or parses to 0 rows), report which
   source failed and why, and continue with the rest — don't abort the
   whole run over one bad source.

2. For each source, run:
   `.venv/bin/python scripts/diff_snapshot.py <name>`
   and combine the JSON lists of new postings across all sources into one
   list. (Exact duplicates are dropped by filter_jobs.py in the next step;
   only flag near-duplicates you notice in the final list, e.g. the same
   role with slightly different titles across sources.)

3. Pipe the combined new-postings JSON into:
   `.venv/bin/python scripts/filter_jobs.py`
   This returns `{"keyword_match": [...], "review": [...]}`.

   Any script in steps 1-3 may print WARNING lines to stderr (row-count
   drop suggesting a source format change, clamped max_age_days, dropped
   stale postings). Relay these to the user verbatim — never swallow them.
   If a row-count warning fires, offer to inspect that source's
   `raw.<date>.*` snapshot to diagnose what changed.

4. `keyword_match` postings are auto-included in the final list, no further
   processing needed.

5. Review-bucket triage — two passes, cheapest first:
   - **Pass 1 (no fetching):** judge every `review` posting on its
     title, category, company, and location alone against the free-text
     `profile` field in `sources.yaml`. Discard clear non-fits (wrong
     discipline, wrong direction entirely). Only postings where the fit
     is genuinely uncertain from the title move to pass 2 — this bucket
     can run to hundreds of postings, so pass 1 must do most of the
     cutting.
   - **Pass 2 (WebFetch, plausible ones only):** fetch the posting's
     `link` and judge the actual job description against the profile. Be
     conservative — this bucket already skipped the cheap keyword match
     for a reason. If the page isn't fetchable (login wall — e.g. some
     aggregator links like Jobright require an account), mark it
     `needs_manual_check` instead of silently dropping it.

6. Combine `keyword_match` + LLM-approved `review` items + any
   `needs_manual_check` items into the final list. Write it to
   `data/matches/<today's date>.md` as a numbered markdown table with
   columns: `#`, Company, Role, Location, Matched via (keyword /
   llm-review / manual-check-needed), Link.

7. Print the same list in chat. Tell the user they can say something like
   "tailor #3" (or a list of numbers) to generate resume bullets for a
   specific posting, which hands off to the `tailor-resume` skill.
