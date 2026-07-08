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
   - **Pass 1 (no fetching, cheap model):** delegate this to a single
     subagent pinned to the cheapest model (Haiku) — this step is
     high-volume title triage, not deep reasoning, and delegating keeps
     the full postings list out of the main conversation's context. Give
     the subagent the `profile` text and the numbered `review` list.
     The exact JSON field names on each posting are: `role` (the job
     title — the field is NOT named "title"), `company`, `category`,
     `location`, `sponsorship`, and optionally `location_unverified`
     (boolean). Have it return a
     verdict per posting: `fit` (clearly matches the profile from the
     title alone), `no-fit` (clearly wrong discipline or region), or
     `uncertain` — each with a one-line reason. Instruct it to be
     conservative: `no-fit` only when clear; anything doubtful comes
     back `uncertain`, never silently discarded.
     For postings flagged `location_unverified` (matched no
     `locations_include` term): `no-fit` if the location string is
     clearly outside the profile's target regions, judge normally if
     clearly inside, `uncertain` if too vague to tell.
     Back in the main conversation: sanity-check the verdicts briefly
     (reasons that don't make sense mean re-judging that posting
     yourself), add `fit` postings to the final list as llm-review
     matches, drop `no-fit`, and send `uncertain` to pass 2.
     This bucket can run to hundreds of postings, so pass 1 must do
     most of the cutting.
   - **Pass 2 (WebFetch, plausible ones only):** delegate this to a
     single subagent pinned to the second-lowest-cost model (Sonnet 5) —
     this pass does real reasoning over full job descriptions, so it
     warrants a stronger model than pass 1's Haiku, but delegating still
     keeps the fetched pages out of the main conversation's context. Give
     the subagent the `profile` text and the `uncertain` postings with
     their `link`s. Have it fetch each posting's `link` and judge the
     actual job description against the profile. Be conservative — this
     bucket already skipped the cheap keyword match for a reason. If the
     page isn't fetchable (login wall — e.g. some aggregator links like
     Jobright require an account), have it mark the posting
     `needs_manual_check` instead of silently dropping it. Back in the
     main conversation, sanity-check the verdicts, add the `fit` ones as
     llm-review matches, and carry any `needs_manual_check` items
     forward.

6. Combine `keyword_match` + LLM-approved `review` items + any
   `needs_manual_check` items into one list, then pipe it as JSON into:
   `.venv/bin/python scripts/track_applications.py upsert`
   This records new postings in `data/applications.yaml` with status
   `seen`, and echoes the list back with `status` and `already_seen`
   fields for postings that were shown in a previous run.

7. Write the final list to `data/matches/<today's date>.md` as a numbered
   markdown table with columns: `#`, Company, Role, Location, Matched via
   (keyword / llm-review / manual-check-needed), Status, Link.
   - Status is `new` for first-time postings; for `already_seen` ones show
     their tracker status (`seen` / `tailored` / `applied`) so the user
     doesn't re-apply — keep them in the list, visibly marked, rather than
     hiding them.

8. Print the same list in chat. Tell the user they can say something like
   "tailor #3" (or a list of numbers) to generate resume bullets for a
   specific posting, which hands off to the `tailor-resume` skill.
