"""
discover.py - Daily job discovery runner using JobSpy.
Run manually or via launchd at 7:30am IST daily.

Usage:
    python discover.py              # Full run
    python discover.py --test       # Test mode (fewer results, verbose output)
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta

# Resolve paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_BASE = SCRIPT_DIR.parent                  # project root
CONFIG_PATH = PROJECT_BASE / "config.json"
DATA_DIR = PROJECT_BASE / "data"                  # jobs_found.json
ARCHIVE_DIR = PROJECT_BASE / "archive" / "expired_jobs"

sys.path.insert(0, str(SCRIPT_DIR))
from scorer import score_all
from reporter import generate_report
from calibrate import run_calibration


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return json.load(f)


def normalize_company(name: str) -> str:
    """Normalize company name for deduplication."""
    import re
    if not name:
        return ""
    name = name.lower()
    for noise in ["pvt ltd", "pvt. ltd.", "private limited", "inc.", "inc", "india", "ltd", "llp",
                  "technologies", "technology", "solutions", "services"]:
        name = name.replace(noise, "")
    return re.sub(r"[^a-z0-9 ]", "", name).strip()


def normalize_title(title: str) -> str:
    """Normalize job title for deduplication."""
    import re
    if not title:
        return ""
    title = title.lower()
    for noise in ["senior", "lead", "staff", "principal", "i", "ii", "iii", "1", "2", "3"]:
        title = re.sub(rf"\b{noise}\b", "", title)
    return re.sub(r"[^a-z0-9 ]", "", title).strip()


def deduplicate(jobs: list) -> list:
    """
    Deduplicate jobs by (normalized_company + normalized_title).
    Merge source URLs into a single entry.
    """
    seen = {}
    for job in jobs:
        key = f"{normalize_company(job.get('company', ''))}__{normalize_title(job.get('title', ''))}"
        if key not in seen:
            seen[key] = job.copy()
            seen[key]["sources"] = [{
                "platform": job.get("site", "unknown"),
                "url": job.get("job_url", job.get("url", ""))
            }]
        else:
            # Merge source URL
            existing_urls = [s["url"] for s in seen[key]["sources"]]
            new_url = job.get("job_url", job.get("url", ""))
            if new_url and new_url not in existing_urls:
                seen[key]["sources"].append({
                    "platform": job.get("site", "unknown"),
                    "url": new_url
                })
    return list(seen.values())


def run_jobspy(config: dict, test_mode: bool = False) -> tuple[list, dict]:
    """
    Run JobSpy across all configured sources.
    Returns (jobs_list, source_results) where source_results tracks per-source outcomes.
    """
    try:
        from jobspy import scrape_jobs
    except ImportError:
        print("ERROR: jobspy not installed. Run: pip install jobspy")
        sys.exit(1)

    discovery = config["discovery"]
    source_results = {}
    all_jobs = []

    search_term = " OR ".join(config.get("target_roles", ["Senior Product Manager"]))
    search_locations = config["location"].get("search_locations", config["location"].get("search_location", ["India"]))
    if isinstance(search_locations, str):
        search_locations = [search_locations]

    results_wanted = 20 if test_mode else discovery["results_wanted"]
    hours_old = discovery["hours_old"]

    print(f"Running discovery: {len(discovery['sources'])} sources x {len(search_locations)} locations, last {hours_old}h, {results_wanted} results max per source/location")

    for search_location in search_locations:
        for source in discovery["sources"]:
            label = f"{source}/{search_location}"
            print(f"  Fetching from {label}...", end=" ", flush=True)
            try:
                # country_indeed must be a real country code — use "India" as fallback for non-country strings like "Remote"
                country = search_location if search_location.lower() not in ("remote", "worldwide") else "India"
                jobs = scrape_jobs(
                    site_name=[source],
                    search_term=search_term,
                    location=search_location,
                    results_wanted=results_wanted,
                    hours_old=hours_old,
                    country_indeed=country,
                    linkedin_fetch_description=True
                )

                if jobs is None or (hasattr(jobs, '__len__') and len(jobs) == 0):
                    print(f"0 jobs")
                    source_results[label] = {"status": "empty", "count": 0}
                    continue

                # Convert DataFrame rows to dicts
                job_list = []
                for _, row in jobs.iterrows():
                    job = {
                        "title": str(row.get("title", "")),
                        "company": str(row.get("company", "")),
                        "location": str(row.get("location", "")),
                        "description": str(row.get("description", "")),
                        "job_url": str(row.get("job_url", "")),
                        "date_posted": str(row.get("date_posted", "")),
                        "site": source,
                        "salary_source": str(row.get("min_amount", "")) or str(row.get("max_amount", ""))
                    }
                    job_list.append(job)

                count = len(job_list)
                print(f"{count} jobs")
                source_results[label] = {"status": "success", "count": count}
                all_jobs.extend(job_list)

            except Exception as e:
                err = str(e)[:100]
                print(f"FAILED ({err})")
                source_results[label] = {"status": "error", "error": err, "count": 0}

    return all_jobs, source_results


def save_job_details(jobs: list, date_str: str, job_details_dir: Path) -> None:
    """Save individual job detail files."""
    job_details_dir.mkdir(parents=True, exist_ok=True)

    for job in jobs:
        company_slug = normalize_company(job.get("company", "unknown")).replace(" ", "_")[:30]
        title_slug = job.get("title", "unknown").lower().replace(" ", "_")
        title_slug = "".join(c for c in title_slug if c.isalnum() or c == "_")[:40]
        filename = f"{date_str}_{company_slug}_{title_slug}.md"

        filepath = job_details_dir / filename
        job["detail_file"] = filename

        sources_md = "\n".join([f"- [{s['platform']}]({s['url']})" for s in job.get("sources", [])])
        breakdown = job.get("score_breakdown", {})

        content = f"""# {job.get('title', 'Unknown')} — {job.get('company', 'Unknown')}

**Score:** {job.get('score', 0)} / 100 ({job.get('score_label', '')})
**Location:** {job.get('location', 'Unknown')}
**Date Found:** {date_str.replace('_', '-')}

## Score Breakdown
| Factor | Score |
|--------|-------|
| Title Match | {breakdown.get('title_match', '—')} / 30 |
| Role Scope | {breakdown.get('role_scope', '—')} / 25 |
| Company Signal | {breakdown.get('company_signal', '—')} / 20 |
| Domain Overlap | {breakdown.get('domain_overlap', '—')} / 15 |
| Location | {breakdown.get('location', '—')} / 10 |
| YOE Fit | {breakdown.get('yoe_fit', 0):+d} (req: {breakdown.get('yoe_required', '?')} yrs) |
| Salary Adjustment | {breakdown.get('salary_adjustment', 0):+d} |
| **Total** | **{breakdown.get('total', job.get('score', 0))} / 100** |

## Links
{sources_md or '- No links available'}

## Job Description
{job.get('description', 'No description available')[:3000]}
{'...(truncated)' if len(job.get('description', '')) > 3000 else ''}

---
*Status: discovered*
*Action: —*
*Notes: —*
"""
        with open(filepath, "w") as f:
            f.write(content)


def archive_expired(config: dict, jobs_data: dict) -> int:
    """Move jobs older than retention_days with no action to archive."""
    retention_days = config["discovery"]["retention_days"]
    today = datetime.now().date()
    archived = 0

    active_jobs = jobs_data.get("active_jobs", [])
    expired = []
    still_active = []

    for job in active_jobs:
        found_date_str = job.get("date_found", "")
        if not found_date_str:
            still_active.append(job)
            continue

        try:
            found_date = datetime.strptime(found_date_str, "%Y-%m-%d").date()
        except ValueError:
            still_active.append(job)
            continue

        days_old = (today - found_date).days
        action = job.get("action", "none")

        # Never archive jobs that have been saved to the pipeline or rated
        if job.get("pipeline") or job.get("feedback"):
            still_active.append(job)
            continue

        if days_old >= retention_days and action == "none":
            expired.append(job)
            archived += 1
        else:
            still_active.append(job)

    if expired:
        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        archive_file = ARCHIVE_DIR / f"{today.strftime('%Y_%m_%d')}_expired.json"
        with open(archive_file, "a") as f:
            for job in expired:
                f.write(json.dumps(job) + "\n")

    jobs_data["active_jobs"] = still_active
    return archived


def load_existing_jobs() -> dict:
    """Load existing jobs_found.json if it exists."""
    jobs_path = DATA_DIR / "jobs_found.json"
    if jobs_path.exists():
        with open(jobs_path) as f:
            return json.load(f)
    return {"active_jobs": [], "last_updated": ""}


def save_jobs(jobs_data: dict) -> None:
    """Save jobs_found.json."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(DATA_DIR / "jobs_found.json", "w") as f:
        json.dump(jobs_data, f, indent=2, default=str)


def main():
    parser = argparse.ArgumentParser(description="Jobmore daily job discovery")
    parser.add_argument("--test", action="store_true", help="Test mode: fewer results, verbose")
    args = parser.parse_args()

    config = load_config()
    md_path = config.get("output", {}).get("md_path", "").strip()
    OUTPUT_BASE = PROJECT_BASE / "output"
    job_details_dir = OUTPUT_BASE / "job_details"

    today = datetime.now()
    date_str = today.strftime("%Y_%m_%d")

    print(f"\n{'='*50}")
    print(f"Jobmore Discovery Run — {today.strftime('%Y-%m-%d %H:%M IST')}")
    print(f"{'='*50}\n")

    # Load existing jobs and archive expired
    jobs_data = load_existing_jobs()
    archived_count = archive_expired(config, jobs_data)
    if archived_count:
        print(f"Archived {archived_count} expired jobs (no action in {config['discovery']['retention_days']} days)\n")

    # Run discovery
    raw_jobs, source_results = run_jobspy(config, test_mode=args.test)
    print(f"\nTotal raw jobs fetched: {len(raw_jobs)}")

    # Deduplicate
    unique_jobs = deduplicate(raw_jobs)
    print(f"After deduplication: {len(unique_jobs)}")

    # Score all jobs
    scored_jobs = score_all(unique_jobs, config)
    print(f"Scored {len(scored_jobs)} jobs\n")

    # Add metadata
    today_str = today.strftime("%Y-%m-%d")
    for job in scored_jobs:
        job["date_found"] = today_str
        job["action"] = "none"

    # Derive per-company scoring adjustments from accumulated feedback,
    # then re-score all existing jobs so the overrides take effect today.
    overrides = run_calibration(jobs_data)
    config["feedback_overrides"] = overrides

    # Re-score existing active jobs with latest scoring logic.
    # score_job() only writes score/score_breakdown/score_label, so pipeline
    # and feedback fields survive the re-score unchanged.
    jobs_data["active_jobs"] = score_all(jobs_data["active_jobs"], config)

    # Merge with new jobs (avoid re-adding already-seen jobs)
    existing_keys = set()
    for j in jobs_data["active_jobs"]:
        key = f"{normalize_company(j.get('company',''))}__{normalize_title(j.get('title',''))}"
        existing_keys.add(key)

    existing_ids = {j.get("id") for j in jobs_data.get("active_jobs", [])}
    new_jobs = []
    for j in scored_jobs:
        key = f"{normalize_company(j.get('company',''))}__{normalize_title(j.get('title',''))}"
        if key not in existing_keys:
            nid = jobs_data.get("next_id", 1)
            while nid in existing_ids:
                nid += 1
            jobs_data["next_id"] = nid + 1
            existing_ids.add(nid)
            j["id"] = nid
            new_jobs.append(j)
            existing_keys.add(key)

    jobs_data["active_jobs"].extend(new_jobs)
    jobs_data["active_jobs"] = sorted(jobs_data["active_jobs"], key=lambda j: j.get("score", 0), reverse=True)
    jobs_data["last_updated"] = today_str

    print(f"New jobs added: {len(new_jobs)}")

    # Save details for top 25
    save_job_details(scored_jobs[:25], date_str, job_details_dir)

    # Save jobs_found.json
    save_jobs(jobs_data)

    # Generate report (Slack + markdown + log)
    # Filter top matches: last 3 days + score >= 80
    cutoff_date = (today - timedelta(days=3)).strftime("%Y-%m-%d")
    recent_strong = [
        j for j in jobs_data["active_jobs"]
        if j.get("date_found", "") >= cutoff_date and j.get("score", 0) >= 80
    ]
    others = [j for j in jobs_data["active_jobs"] if j not in recent_strong]
    report_jobs = recent_strong + others
    top5 = report_jobs[:5]
    next20 = report_jobs[5:25]
    generate_report(top5, next20, source_results, config, archived_count, len(new_jobs), today, len(jobs_data["active_jobs"]), active_jobs=jobs_data["active_jobs"], output_base=OUTPUT_BASE)

    print("\nDone.")


if __name__ == "__main__":
    main()
