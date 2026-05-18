Read `data/current_job.txt` to get the active job directory path.

Confirm with the user: "Reading iterations.md for {job_dir} — correct?" before proceeding.

Once confirmed:
1. Read the ENTIRE `{job_dir}/iterations.md`. Do two things:
   a. **Carry-forward constraints**: Scan every user feedback block (text below each `---` separator across ALL versions — V1, V2, V3, etc.). Extract every correction, locked metric, framing fix, and "do not use" instruction. Synthesize a deduplicated list. State it in the chat in this format before writing anything:
      ```
      Carry-forward constraints:
      - [locked item: e.g. "Scale: 24k+ daily active (NOT 4.2 crore direct users)"]
      - [locked item: ...]

      Latest feedback (V{N}): [one sentence paraphrase of the user's newest feedback]

      Proceeding with revision.
      ```
   b. **Latest feedback**: identify the user's feedback written below the most recent `---` separator — this is the new feedback to action.
2. Append a row to `data/iteration_log.md` with:
   - Date: today's date (YYYY-MM-DD)
   - Job: company + title from the directory name
   - Artifact: the artifact being revised (infer from iterations.md or conversation context)
   - Version: current version number (the one the user just gave feedback on)
   - Status: revision_requested
   - What changed: one sentence summarising the feedback (written after the revision, describing what you changed)
3. Proceed with the revision based on the feedback.
4. After producing the revised artifact, append the next version block to `{job_dir}/iterations.md`:

```
## V{N}
**Created:** —
**Changed:** {artifact} — {one sentence describing what changed}
**Deleted:** —

---
```

Update `data/iteration_log.md` row's "What changed" column with the same one-sentence description.
