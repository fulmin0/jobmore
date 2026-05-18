# /resume-content

## Purpose
Run the full resume content workflow for the active job. Enforces: job_intelligence exists and role-type is confirmed, rewrite gate runs on every bullet, summary is written last, V1 is not called complete until user has reviewed.

## Step 1 — Identify active job
Ask the user: "Which job are we working on? (Company::Title or directory name)"
Confirm the output directory exists at `output/jobs/{dir}/` before proceeding.

## Step 2 — Role-type confirmation gate
Read `output/jobs/{dir}/job_intelligence.md`.
- If it does not exist: stop. Tell the user: "job_intelligence.md not found for this job. Run job intelligence first, then return here."
- If it exists: find or infer the role type from the file. State in one line: "This is a [product / program / engineering / growth / other] role. I'm reading it as [X] because [one sentence of reasoning]. Confirm before I proceed."
- Wait for explicit user confirmation or correction before generating any content.
- If the user corrects the role type: note the correction, update your understanding, proceed with corrected framing.

## Step 3 — Run resume content workflow
Read `prompts/resume_content.md` and execute the full workflow.
The rewrite gate (Step 4d in the prompt) and summary-last rule (Step 4c) are non-negotiable — do not skip them even if the session is long.

## Step 4 — V1 completeness check
Before calling this session done, confirm:
- [ ] `resume_content.md` written to job directory
- [ ] Every bullet has passed the rewrite gate (action + outcome present)
- [ ] Summary was written after bullets, derived from final set
- [ ] Talking points written in working doc for every bullet
- [ ] Dimension coverage check run (5 dimensions across full resume)
- [ ] JD pillar coverage check run (every major pillar addressed)

If any item is unchecked, complete it before ending the session.

## Step 5 — Close-out
Append a V1 version block to `output/jobs/{dir}/iterations.md`:

```
## V1
**Created:** resume_content.md
**Changed:** —
**Deleted:** —

---
[user writes feedback here]

<!-- APPEND_NEXT_VERSION_HERE -->
```

Remind the user: "Write feedback below the `---` line, then type `/revise` to proceed or `/approve` when satisfied."
