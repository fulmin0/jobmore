# /elevator-pitch

## Purpose
Run the elevator pitch workflow for the active job. Enforces: job_intelligence exists, fact sheet confirmed before writing, V1 not complete until user has reviewed.

## Step 1 — Identify active job
Ask: "Which job? (Company::Title or directory name)"
Confirm the output directory exists at `output/jobs/{dir}/` before proceeding.
Write `data/current_job.txt` with the active job directory path.

## Step 2 — Read job intelligence
Check `output/jobs/{dir}/job_intelligence.md`.
- **Not found**: stop. Tell the user: "job_intelligence.md not found for this job. Run job intelligence first, then return here."
- **Found**: read it. Do not re-derive pillars, story rankings, or domain flags — use what's in the file.

## Step 3 — Fact verification gate
Run the fact verification gate from `prompts/elevator_pitch.md` (the section titled "Fact verification gate").
State the proposed fact sheet in the chat. Wait for explicit user confirmation before writing anything.
If the user corrects an item, update the fact sheet, restate it, and wait for confirmation again.

## Step 4 — Write the pitch
Execute the full elevator pitch workflow from `prompts/elevator_pitch.md`.
The fact sheet from Step 3 is binding — do not introduce metrics or framing not in the confirmed fact sheet.

## Step 5 — Close-out
Append a V1 version block to `output/jobs/{dir}/iterations.md`:

```
## V1
**Created:** elevator_pitch.md
**Changed:** —
**Deleted:** —

---
[user writes feedback here]

<!-- APPEND_NEXT_VERSION_HERE -->
```

Remind the user: "Write feedback below the `---` line, then type `/revise` to proceed or `/approve` when satisfied."
