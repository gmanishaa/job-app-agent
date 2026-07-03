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
   - Reorder bullets within each section so the most relevant-to-this-JD
     items come first.

5. Output the tailored bullets as plain text/markdown in chat, grouped by
   resume section, so the user can copy them into their formatted resume.
   Do not write to any file — this step is output-only for now.
