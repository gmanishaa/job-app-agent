---
name: tailor-resume
description: Given a job posting (from the day's matches list or a direct link), reword and reorder the user's master resume bullets to match the job description's language, without inventing new content.
---

# tailor-resume

Run this when the user asks to tailor their resume for a specific posting
(e.g. "tailor #3", or a pasted job link).

## Steps

1. Resolve the posting: if given a number, look it up in the most recent
   `data/matches/<date>.md`. If given a link directly, use that instead.

2. WebFetch the job description. If the page isn't fully readable (login
   wall — e.g. some aggregator links require an account), tell the user
   and ask them to paste the JD text instead. Do not guess at the content.

3. Read `data/resume/master_resume.md`.

4. Reword and reorder the existing bullets to match the job description's
   language and priorities:
   - Do not invent new bullets, achievements, or skills that aren't
     already in the master resume.
   - Do not change facts, numbers, or the scope of a bullet — only
     wording and ordering.
   - Reorder bullets ONLY within a single job/project entry so the most
     relevant-to-this-JD items come first. NEVER reorder the entries
     themselves: Work Experience and Education stay in the master
     resume's reverse-chronological order regardless of relevance —
     that's the order resumes are expected to be in. (Projects may be
     reordered relative to each other; they aren't chronological.)
   - Respect the space budget declared in the master resume's note block
     (total bullet count, preferred and absolute per-bullet character
     limits). Rewording must never push a bullet past the absolute
     limit, and should land under the preferred limit when it can —
     tightening while rewording is fine.
   - Select which project(s) to include per posting: pick the project
     most relevant to this JD and drop the others — the master resume is
     a superset, not a template to copy whole. If two projects are both
     strongly relevant, include both and cut the least-relevant
     experience bullets to stay within the total budget (trim bullets
     from jobs, never a whole job). List every dropped project and cut
     bullet in the fit summary so the user can override.
   - Skills section: reorder each category so the skills this JD asks for
     come first. A skill missing from the Skills list may be ADDED only
     when both hold: (a) the JD asks for it, and (b) the master resume
     explicitly evidences it elsewhere — named in a work/project bullet
     (e.g. Docker/Kubernetes in a Varian bullet) or a strict umbrella of
     something named (JD says "SQL", resume has PostgreSQL/MySQL). Never
     add a skill that is merely adjacent (JD wants Vue, resume shows
     React — that is a gap for the fit summary, not an addition). Every
     added skill must be called out in the fit summary with the bullet
     that evidences it, so the user can veto it.

5. Write a fit summary — short, three parts, honest:
   - **Direct matches**: stack/tools/keywords the JD asks for that the
     resume explicitly has.
   - **Transferable matches**: JD requirements the resume covers without
     sharing a keyword — e.g. the JD says "event-driven architectures"
     and the resume shows Kafka pipeline work, or "mentoring" and the
     resume shows onboarding new hires. Name the JD requirement and the
     resume evidence for each.
   - **Gaps**: JD requirements (esp. hard ones) with no real resume
     evidence. State them plainly — do not paper over a gap by
     stretching a bullet's meaning; the user decides how to handle it.

6. Write the tailored bullets (grouped by resume section) plus the fit
   summary to `data/tailored/<company-slug>-<today's date>.md`, and print
   the same content in chat so the user can copy bullets directly into
   their formatted resume.

7. Update the tracker by piping the posting's JSON (company, role,
   location, link at minimum — copy them from the matches file entry, or
   from the JD itself when tailoring a direct link) into:
   `.venv/bin/python scripts/track_applications.py set-status tailored --file <path from step 6>`
   A warning that the posting wasn't tracked yet is normal when tailoring
   from a direct link; relay it and continue.
