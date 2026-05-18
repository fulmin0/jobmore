#!/usr/bin/env python3
"""One-time migration: move existing job folders to the correct directory
based on current pipeline status in jobs_found.json.

Status → folder mapping:
  want_to_apply, content_ready          → output/jobs/         (root)
  referral_found, referral_submitted    → output/jobs/referral/
  applied, recruiter_screen,
    interview, offer                    → output/jobs/applied/
  rejected, withdrawn                   → output/jobs/archive/
  no_pipeline / orphan (no JSON entry)  → output/jobs/archive/
"""

import json
import re
import sys
from pathlib import Path

PROJECT_BASE = Path(__file__).parent.parent
DATA_FILE = PROJECT_BASE / "data" / "jobs_found.json"

JOBS_DIR    = PROJECT_BASE / "output" / "jobs"
APPLIED_DIR = JOBS_DIR / "applied"
REFERRAL_DIR = JOBS_DIR / "referral"
ARCHIVE_DIR = JOBS_DIR / "archive"

NON_JOB_DIRS = {"applied", "referral", "archive", "base", "base_resume"}

STATUS_TO_DIR = {
    "want_to_apply":      JOBS_DIR,
    "content_ready":      JOBS_DIR,
    "referral_found":     REFERRAL_DIR,
    "referral_submitted": REFERRAL_DIR,
    "applied":            APPLIED_DIR,
    "recruiter_screen":   APPLIED_DIR,
    "interview":          APPLIED_DIR,
    "offer":              APPLIED_DIR,
    "rejected":           ARCHIVE_DIR,
    "withdrawn":          ARCHIVE_DIR,
}


def id_from_folder(name: str) -> str | None:
    m = re.match(r'^(\d+)_', name)
    return m.group(1) if m else None


def move(src: Path, target_dir: Path, dry_run: bool) -> None:
    dest = target_dir / src.name
    if dest.resolve() == src.resolve():
        print(f"  [ok]    {src.name}  (already in {target_dir.name}/)")
        return
    if dest.exists():
        print(f"  [SKIP]  {src.name}  → {target_dir.name}/ (destination already exists)")
        return
    print(f"  [move]  {src.name}  →  {target_dir.name}/")
    if not dry_run:
        target_dir.mkdir(exist_ok=True)
        src.rename(dest)


def main(dry_run: bool = False) -> None:
    with open(DATA_FILE) as f:
        data = json.load(f)

    jobs = data.get("active_jobs", [])
    id_to_status: dict[str, str] = {}
    for j in jobs:
        jid = str(j.get("id", ""))
        pipeline = j.get("pipeline") or {}
        id_to_status[jid] = pipeline.get("status", "no_pipeline")

    search_bases = [JOBS_DIR, APPLIED_DIR, REFERRAL_DIR, ARCHIVE_DIR]

    # Collect all job folders across all bases
    all_folders: list[Path] = []
    for base in search_bases:
        if not base.exists():
            continue
        for d in base.iterdir():
            if d.is_dir() and d.name not in NON_JOB_DIRS and not d.name.startswith("."):
                all_folders.append(d)

    print(f"{'DRY RUN — ' if dry_run else ''}Scanning {len(all_folders)} job folders...\n")

    for folder in sorted(all_folders, key=lambda p: p.name):
        jid = id_from_folder(folder.name)
        status = id_to_status.get(jid, "orphan") if jid else "orphan"
        target = STATUS_TO_DIR.get(status, ARCHIVE_DIR)
        move(folder, target, dry_run)

    print("\nDone." + (" (dry run — nothing moved)" if dry_run else ""))


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    if not dry_run:
        print("WARNING: This will move folders. Pass --dry-run to preview first.\n")
    main(dry_run)
