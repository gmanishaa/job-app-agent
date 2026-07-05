# job-app-agent

A personal job-search agent built as Claude Code skills, running on a Claude
Pro subscription (no separate API billing).

## What it does

1. **`/find-jobs`** — pulls new postings from GitHub repos that track job
   listings daily, applies hard-exclude rules, a recency cutoff
   (`max_age_days`, default 1), and a keyword match, then runs an LLM
   review pass on borderline postings before listing everything.
   Sources can be `type: json` (structured listings.json, preferred —
   the SimplifyJobs-family repos publish one) or `type: markdown`
   (README table parsing, fallback). Deterministic work happens in plain
   Python scripts; the LLM only handles judgment calls and flagged
   anomalies, keeping subscription usage for actual reasoning.
2. **`/tailor-resume`** — given a posting you pick from that list, rewords
   and reorders your existing resume bullets to match the job description's
   language. It does not invent new bullets or change facts/scope. Output
   (bullets plus a fit summary of direct matches, transferable matches,
   and honest gaps) is written to `data/tailored/` and printed in chat.

Every posting shown is recorded in `data/applications.yaml` with a status
(`seen` → `tailored` → `applied`). find-jobs marks postings you've already
seen instead of re-listing them as new; tailoring sets `tailored`; set
`applied` by hand (the file is plain YAML) until the apply step exists.

Resume-document automation and applying are future steps.

## Setup

1. `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`
   (the skills and test commands use `.venv/bin/python` so nothing is
   installed into your system Python)
2. Create a `data/` directory as a **sibling** of this repo, i.e. `../data`
   relative to here. This holds your resume and personal criteria and is
   never committed to this repo.
3. Copy `config/sources.example.yaml` to `../data/sources.yaml` and fill in
   real repos, filter rules, and your profile blurb.
4. Add your resume content to `../data/resume/master_resume.md`.
5. Optionally set `JOB_AGENT_DATA_DIR` if you want the data directory
   somewhere other than `../data`.

## Tests

`.venv/bin/python -m pytest tests/` covers the parsing, age/recency,
dedup, and filter logic. Run it after touching anything in `scripts/`, and when a
tracked source changes format.

## Usage

Run `/find-jobs` in Claude Code to check for new postings, then
`/tailor-resume` (referencing a number from the list, e.g. "tailor #3") once
you've picked one.

## Roadmap

- Docker-containerized manual runs, then a scheduled trigger, once the
  pipeline is stable.
- Resume-doc automation (Google Docs API, duplicate-then-edit) for bullets
  without inline formatting.
- Guided/semi-autonomous apply step with human confirmation before submit.
