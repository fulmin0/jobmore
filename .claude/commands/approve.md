Read `data/current_job.txt` to get the active job directory path.

Confirm with the user: "Logging approved for {job_dir} — correct?" before writing anything.

Once confirmed:
1. Append a row to `data/iteration_log.md` with:
   - Date: today's date (YYYY-MM-DD)
   - Job: company + title from the directory name
   - Artifact: the artifact just approved (resume | elevator_pitch | cover_letter | job_intelligence — infer from conversation context)
   - Version: next version number for this job+artifact (check existing rows in iteration_log.md)
   - Status: approved
   - What changed: —

2. Respond normally to continue the conversation.
