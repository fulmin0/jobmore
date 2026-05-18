"""
generate_content.py — Queue drainer for job content generation.

Called by app.py whenever a job enters want_to_apply. Reads
data/generation_queue.txt, processes one job at a time, writes
generation status to output/jobs/{dir}/generation_status.txt.

Enforces single-instance via data/generation.lock (flock).
Safe to call redundantly — exits immediately if already running.
"""

import fcntl
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_BASE = SCRIPT_DIR.parent
DATA_DIR = PROJECT_BASE / "data"
JOBS_DIR = PROJECT_BASE / "output" / "jobs"
QUEUE_FILE = DATA_DIR / "generation_queue.txt"
LOCK_FILE = DATA_DIR / "generation.lock"
DATA_FILE = DATA_DIR / "jobs_found.json"

STATUS_RUNNING = "running"
STATUS_DONE = "done"
STATUS_FAILED = "failed"

REQUIRED_ARTIFACTS = ["job_intelligence.md", "elevator_pitch.md", "resume_content.md"]
# Timeout: if a job takes longer than this, mark failed
GENERATION_TIMEOUT_S = 20 * 60  # 20 minutes


def _find_job_dir(job_dir_name: str) -> Path | None:
    for base in [JOBS_DIR, JOBS_DIR / "applied", JOBS_DIR / "referral", JOBS_DIR / "archive"]:
        candidate = base / job_dir_name
        if candidate.exists():
            return candidate
    return None


def _write_status(job_dir: Path, status: str, message: str = "") -> None:
    content = status if not message else f"{status}\n{message}"
    (job_dir / "generation_status.txt").write_text(content, encoding="utf-8")


def _build_prompt(job_dir_name: str) -> str:
    rel = Path("output") / "jobs" / job_dir_name
    # Load company/title from jobs_found.json for a cleaner prompt header
    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        prefix = int(job_dir_name.split("_")[0])
        job = next((j for j in data.get("active_jobs", []) if j.get("id") == prefix), None)
        if job:
            company = job.get("company", "")
            title = job.get("title", "")
            jd = (job.get("description", "") or "")[:4000]
        else:
            company, title, jd = "", "", ""
    except Exception:
        company, title, jd = "", "", ""

    header = f"Generate all job application content for {company} — {title}." if company else f"Generate all job application content for the job in {rel}."
    return (
        f"{header}\n\n"
        f"Output directory: {rel}\n"
        + (f"Job description:\n{jd}\n\n" if jd else "")
        + "Run in order:\n"
        f"1. Read prompts/job_intelligence.md and follow the workflow → write {rel}/job_intelligence.md\n"
        f"2. Read prompts/elevator_pitch.md and follow the workflow → write {rel}/elevator_pitch.md\n"
        f"3. Read prompts/cover_letter.md and follow the workflow → write artifacts to {rel}/\n"
        f"4. Read prompts/resume_content.md and follow the workflow → write {rel}/resume_content.md and build resume PDF\n\n"
        "Read data/experience/*.md before generating any content."
    )


def _run_job(job_dir_name: str) -> None:
    job_dir = _find_job_dir(job_dir_name)
    if not job_dir:
        job_dir = JOBS_DIR / job_dir_name
        job_dir.mkdir(parents=True, exist_ok=True)

    claude_bin = shutil.which("claude")
    if not claude_bin:
        _write_status(job_dir, STATUS_FAILED, "claude CLI not found in PATH")
        return

    _write_status(job_dir, STATUS_RUNNING)
    log_path = job_dir / "generation.log"
    prompt = _build_prompt(job_dir_name)

    try:
        with open(log_path, "w", encoding="utf-8") as log_f:
            proc = subprocess.Popen(
                [claude_bin, "--print", "--permission-mode", "acceptEdits", prompt],
                cwd=str(PROJECT_BASE),
                stdout=log_f,
                stderr=log_f,
            )
            start = time.time()
            while proc.poll() is None:
                if time.time() - start > GENERATION_TIMEOUT_S:
                    proc.kill()
                    _write_status(job_dir, STATUS_FAILED, f"timed out after {GENERATION_TIMEOUT_S // 60} minutes")
                    return
                time.sleep(10)

        exit_code = proc.returncode
    except Exception as e:
        _write_status(job_dir, STATUS_FAILED, str(e))
        return

    if exit_code != 0:
        _write_status(job_dir, STATUS_FAILED, f"claude exited with code {exit_code} — see generation.log")
        return

    missing = [a for a in REQUIRED_ARTIFACTS if not (job_dir / a).exists()]
    if missing:
        _write_status(job_dir, STATUS_FAILED, f"missing artifacts: {', '.join(missing)} — see generation.log")
        return

    _write_status(job_dir, STATUS_DONE)


def main() -> None:
    if not QUEUE_FILE.exists() or not QUEUE_FILE.read_text().strip():
        return

    lock_f = open(LOCK_FILE, "w")
    try:
        fcntl.flock(lock_f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        # Another instance is already running — exit cleanly
        lock_f.close()
        return

    try:
        while True:
            lines = QUEUE_FILE.read_text(encoding="utf-8").splitlines()
            pending = [l.strip() for l in lines if l.strip()]
            if not pending:
                break
            job_dir_name = pending[0]
            # Pop from queue before running so a crash doesn't re-queue infinitely
            QUEUE_FILE.write_text("\n".join(pending[1:]) + ("\n" if pending[1:] else ""), encoding="utf-8")
            _run_job(job_dir_name)
    finally:
        fcntl.flock(lock_f, fcntl.LOCK_UN)
        lock_f.close()


if __name__ == "__main__":
    main()
