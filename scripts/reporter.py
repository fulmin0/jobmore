"""
reporter.py - Generate Slack messages, update Markdown and log files.
Files are always written first. Slack is optional (skipped if not configured).
"""

import json
import re
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime, date

SCRIPT_DIR = Path(__file__).parent
ALL_SOURCES = ["linkedin", "indeed", "naukri", "google", "glassdoor", "zip_recruiter"]


def load_source_reliability(data_dir: Path) -> dict:
    reliability_path = data_dir / "source_reliability.json"
    if reliability_path.exists():
        with open(reliability_path) as f:
            return json.load(f)
    return {s: {"last_success": None, "consecutive_failures": 0} for s in ALL_SOURCES}


def save_source_reliability(reliability: dict, data_dir: Path) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    with open(data_dir / "source_reliability.json", "w") as f:
        json.dump(reliability, f, indent=2)


def format_tracker_table(reliability: dict) -> str:
    rows = ["| Source | Last Success | Consecutive Failures | Status |",
            "|--------|-------------|---------------------|--------|"]
    for source in ALL_SOURCES:
        data = reliability.get(source, {"last_success": None, "consecutive_failures": 0})
        last = data.get("last_success") or "—"
        failures = data.get("consecutive_failures", 0)
        status = "✅ OK" if failures == 0 else ("⚠️ Unstable" if failures <= 2 else "❌ Down")
        rows.append(f"| {source.capitalize()} | {last} | {failures} | {status} |")
    return "\n".join(rows)


def format_source_links(sources: list) -> str:
    """Format source links as markdown."""
    if not sources:
        return ""
    parts = []
    for s in sources:
        platform = s.get("platform", "link").capitalize()
        url = s.get("url", "")
        if url:
            parts.append(f"[{platform}]({url})")
    return " · ".join(parts)


def format_job_row_md(job: dict, rank: int) -> str:
    """Format a job as a markdown table row."""
    title = job.get("title", "Unknown")
    company = job.get("company", "Unknown")
    score = job.get("score", 0)
    label = job.get("score_label", "")
    links = format_source_links(job.get("sources", []))
    location = job.get("location", "")

    return f"| {rank} | {company} | {title} | {score} | {label} | {location} | {links} |"


def format_job_slack(job: dict, rank: int) -> str:
    """Format a job for Slack message."""
    title = job.get("title", "Unknown")
    company = job.get("company", "Unknown")
    score = job.get("score", 0)
    label = job.get("score_label", "")
    location = job.get("location", "")

    sources = job.get("sources", [])
    url = sources[0]["url"] if sources else ""

    link_text = f"<{url}|{company}>" if url else company
    return f"*{rank}. {link_text}* — {title} | Score: {score} ({label}) | {location}"


def write_jobs_found_md(active_jobs: list, today_str: str, total_count: int, data_dir: Path) -> None:
    """
    Overwrite jobs_found.md with top 25 active jobs.
    total_count is the real number of jobs in the database (may be > 25).
    """
    data_dir.mkdir(parents=True, exist_ok=True)
    top5 = active_jobs[:5]
    rest = active_jobs[5:25]

    header = f"""# Active Jobs — Updated {today_str}

Jobs discovered in the last 7 days with no action taken.
Scores: 85-100 Strong · 70-84 Good · 50-69 Possible · <50 Poor

---

## Top 5 — Best Matches

| Rank | Company | Role | Score | Match | Location | Links |
|------|---------|------|-------|-------|----------|-------|
"""
    top5_rows = "\n".join(format_job_row_md(j, i + 1) for i, j in enumerate(top5))

    ref_header = """

---

## Reference — Ranked 6–25

| Rank | Company | Role | Score | Match | Location | Links |
|------|---------|------|-------|-------|----------|-------|
"""
    ref_rows = "\n".join(format_job_row_md(j, i + 6) for i, j in enumerate(rest))

    footer = f"""

---
*Last updated: {today_str} · Total active: {total_count} jobs (showing top 25)*
"""

    content = header + top5_rows + ref_header + ref_rows + footer

    with open(data_dir / "jobs_found.md", "w") as f:
        f.write(content)


def update_discovery_log(source_results: dict, new_count: int, archived_count: int, today_str: str, data_dir: Path) -> None:
    """Append today's run to discovery_log.md and update source reliability tracker."""
    log_path = data_dir / "discovery_log.md"

    # Update + save reliability state
    reliability = load_source_reliability(data_dir)
    for source, result in source_results.items():
        if source not in reliability:
            reliability[source] = {"last_success": None, "consecutive_failures": 0}
        if result.get("status") == "success":
            reliability[source]["last_success"] = today_str
            reliability[source]["consecutive_failures"] = 0
        else:
            reliability[source]["consecutive_failures"] = reliability[source].get("consecutive_failures", 0) + 1
    save_source_reliability(reliability, data_dir)

    # Build run entry
    run_lines = [f"\n### Run — {today_str}\n",
                 f"- New jobs added: {new_count}",
                 f"- Jobs archived (7-day expired): {archived_count}",
                 "- Per-source results:"]
    failed_sources = []
    for source, result in source_results.items():
        status = result.get("status")
        count = result.get("count", 0)
        if status == "success":
            run_lines.append(f"  - {source}: ✅ {count} jobs")
        elif status == "empty":
            run_lines.append(f"  - {source}: ⚠️ 0 jobs (blocked or no results)")
            failed_sources.append(source)
        else:
            run_lines.append(f"  - {source}: ❌ Failed — {result.get('error', 'unknown error')}")
            failed_sources.append(source)
    if failed_sources:
        run_lines.append(f"- Failed sources: {', '.join(failed_sources)}")
    new_entry = "\n".join(run_lines) + "\n"

    # Build tracker section
    tracker_section = f"## Source Reliability Tracker\n\n{format_tracker_table(reliability)}\n\n---"

    existing = log_path.read_text() if log_path.exists() else ""

    if "## Source Reliability Tracker" in existing:
        # Replace the tracker block (up to and including the standalone --- divider line)
        # Use \n---\n to avoid matching --- inside table separator rows like |--------|
        existing = re.sub(
            r"## Source Reliability Tracker.*?\n---\n",
            tracker_section + "\n",
            existing, count=1, flags=re.DOTALL
        )
    else:
        # Build fresh log file
        existing = (
            "# Job Discovery Log\n\nTrack daily discovery runs, source reliability, and experiments.\n\n---\n\n"
            f"{tracker_section}\n\n## Daily Run Log\n\n<!-- New entries added below by reporter.py -->"
        )

    # Append run entry after marker
    if "<!-- New entries added below by reporter.py -->" in existing:
        existing = existing.replace(
            "<!-- New entries added below by reporter.py -->",
            f"<!-- New entries added below by reporter.py -->{new_entry}"
        )
    else:
        existing += new_entry

    with open(log_path, "w") as f:
        f.write(existing)


def send_slack(message: str, config: dict) -> bool:
    """Send Slack message via webhook. Returns True if successful."""
    slack_config = config.get("slack", {})

    if not slack_config.get("enabled", False):
        print("Slack: disabled (set enabled=true in config.json to activate)")
        return False

    webhook_url = slack_config.get("webhook_url", "")
    if not webhook_url:
        print("Slack: no webhook_url configured")
        return False

    payload = json.dumps({"text": message}).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                print("Slack: message sent ✅")
                return True
            else:
                print(f"Slack: unexpected status {response.status}")
                return False
    except urllib.error.URLError as e:
        print(f"Slack: failed to send ({e})")
        return False


_STALL_THRESHOLDS = {
    "want_to_apply": 5,
    "content_ready": 7,
    "referral_found": 5,
    "referral_submitted": 7,
    "applied": 7,
    "recruiter_screen": 7,
    "interview": 7,
}

_STALL_LABELS = {
    "want_to_apply": "want to apply — content not started",
    "content_ready": "content ready — not applied yet",
    "referral_found": "referral found — submit it",
    "referral_submitted": "referral submitted — follow up?",
    "applied": "applied — no update in 7 days (follow up?)",
    "recruiter_screen": "recruiter screen — no update",
    "interview": "interview — no update",
}

_CLOSED_STAGES = {"rejected", "withdrawn"}


def get_pipeline_nudge(active_jobs: list) -> str:
    """
    Build a pipeline pending-actions string for the Slack digest.
    Returns empty string if there are no pipeline jobs.
    """
    if not active_jobs:
        return ""

    today = date.today()
    closed = _CLOSED_STAGES

    active_pipeline_count = sum(
        1 for j in active_jobs
        if j.get("pipeline") and j["pipeline"].get("status") not in closed
    )
    if not active_pipeline_count:
        return ""

    # Count stalled jobs per stage
    stalled: dict[str, int] = {}
    for job in active_jobs:
        pipeline = job.get("pipeline")
        if not pipeline:
            continue
        status = pipeline.get("status", "")
        threshold = _STALL_THRESHOLDS.get(status)
        if threshold is None:
            continue
        date_updated_str = pipeline.get("date_updated", "")
        if not date_updated_str:
            continue
        try:
            days_stale = (today - date.fromisoformat(date_updated_str)).days
        except ValueError:
            continue
        if days_stale >= threshold:
            stalled[status] = stalled.get(status, 0) + 1

    lines = [f"*📋 Pipeline: {active_pipeline_count} active job(s)*"]
    if stalled:
        for stage in _STALL_THRESHOLDS:  # preserve logical order
            if stage in stalled:
                label = _STALL_LABELS.get(stage, stage.replace("_", " "))
                lines.append(f"• {stalled[stage]} job(s): {label}")
    else:
        lines.append("No stalled jobs — keep going!")

    return "\n".join(lines)


def generate_slack_message(top5: list, next20: list, source_results: dict, new_count: int, today_str: str, active_jobs: list = None) -> str:
    """Build the daily Slack message."""
    sources_ok = sum(1 for r in source_results.values() if r.get("status") == "success")
    sources_total = len(source_results)

    top5_text = "\n".join(format_job_slack(j, i + 1) for i, j in enumerate(top5)) or "_No strong matches today_"
    next20_text = "\n".join(format_job_slack(j, i + 6) for i, j in enumerate(next20[:5])) or "_None_"

    failed = [s for s, r in source_results.items() if r.get("status") != "success"]
    source_note = f"⚠️ Failed sources: {', '.join(failed)}" if failed else f"✅ All {sources_total} sources OK"

    pipeline_section = get_pipeline_nudge(active_jobs or [])
    pipeline_block = f"\n\n{pipeline_section}" if pipeline_section else ""

    message = f"""*🔍 Jobmore Daily — {today_str}*
{source_note} · {new_count} new jobs found

*Top Matches (last 3 days, 80+):*
{top5_text}

*Also check (6-10):*
{next20_text}{pipeline_block}

_Full list → output/data/jobs_found.md_"""

    return message


def generate_report(
    top5: list,
    next20: list,
    source_results: dict,
    config: dict,
    archived_count: int,
    new_count: int,
    run_time: datetime,
    total_count: int = 0,
    active_jobs: list = None,
    output_base: Path = None,
) -> None:
    """
    Main reporter entry point.
    1. Always write files first (jobs_found.md, discovery_log.md)
    2. Then try Slack (optional, fails gracefully)
    """
    if output_base is None:
        output_base = Path("output")
    data_dir = output_base / "data"

    today_str = run_time.strftime("%Y-%m-%d")

    print("\n--- Writing files ---")

    # 1. Write jobs_found.md (active jobs only)
    write_jobs_found_md(top5 + next20, today_str, total_count, data_dir)
    print("jobs_found.md ✅")

    # 2. Update discovery_log.md
    update_discovery_log(source_results, new_count, archived_count, today_str, data_dir)
    print("discovery_log.md ✅")

    # 3. Slack (optional)
    print("\n--- Sending Slack report ---")
    slack_msg = generate_slack_message(top5, next20, source_results, new_count, today_str, active_jobs)
    send_slack(slack_msg, config)

    # Print to terminal always (useful for manual runs)
    print("\n--- Daily Summary ---")
    print(slack_msg)
