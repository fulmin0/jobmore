"""
app.py - Jobmore web interface
Three pages: Discover, Pipeline, Scoring Insights

Run with:  streamlit run scripts/app.py
"""

import json
import re
import sys
import requests
import pandas as pd
import streamlit as st
from pathlib import Path
from datetime import date, timedelta
from bs4 import BeautifulSoup

SCRIPT_DIR = Path(__file__).parent
PROJECT_BASE = SCRIPT_DIR.parent
DATA_FILE = PROJECT_BASE / "data" / "jobs_found.json"
CONFIG_PATH = PROJECT_BASE / "config.json"
JOBS_DIR = PROJECT_BASE / "output" / "jobs"
APPLIED_DIR = JOBS_DIR / "applied"
ARCHIVE_DIR = JOBS_DIR / "archive"

sys.path.insert(0, str(SCRIPT_DIR))
from discover import normalize_company, normalize_title
from scorer import score_job

PIPELINE_STAGES = [
    "want_to_apply",
    "content_ready",
    "referral_found",
    "referral_submitted",
    "applied",
    "recruiter_screen",
    "interview",
    "offer",
    "rejected",
    "withdrawn",
]

SCORE_FLAGS = [
    "company_tier_wrong",
    "seniority_wrong",
    "industry_wrong",
    "location_wrong",
    "dealbreaker_false_positive",
    "actually_good_fit",
]

FEEDBACK_RATINGS = ["relevant", "maybe", "not_relevant"]

# Stall threshold in days per stage (stages not listed are terminal/unchecked)
STALL_THRESHOLDS = {
    "want_to_apply": 5,
    "content_ready": 7,
    "referral_found": 5,
    "referral_submitted": 7,
    "applied": 7,
    "recruiter_screen": 7,
    "interview": 7,
}

CLOSED_STAGES = {"rejected", "withdrawn"}


# ─── LinkedIn fetch ────────────────────────────────────────────────────────────

def fetch_linkedin_job(url: str) -> dict | None:
    match = re.search(r'/jobs/view/(\d+)', url)
    if not match:
        return None
    job_id = match.group(1)
    try:
        resp = requests.get(
            f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10,
        )
    except requests.RequestException:
        return None
    if resp.status_code != 200:
        return None
    soup = BeautifulSoup(resp.text, "html.parser")
    title = soup.select_one(".top-card-layout__title")
    company = soup.select_one(".topcard__org-name-link") or soup.select_one(".top-card-layout__second-line")
    location = soup.select_one(".topcard__flavor--bullet")
    description = soup.select_one(".description__text")
    return {
        "title": title.get_text(strip=True) if title else "",
        "company": company.get_text(strip=True) if company else "",
        "location": location.get_text(strip=True) if location else "",
        "description": description.get_text(strip=True) if description else "",
        "job_url": url.split("?")[0].rstrip("/"),
    }


# ─── Job directory & notes helpers ───────────────────────────────────────────

def get_job_dir(job: dict) -> Path | None:
    """Return the job's output folder by ID prefix, then fuzzy company name."""
    job_id = job.get("id")
    if job_id:
        prefix = f"{int(job_id):04d}_"
        for base in [JOBS_DIR, APPLIED_DIR, ARCHIVE_DIR]:
            if not base.exists():
                continue
            for d in base.iterdir():
                if d.is_dir() and d.name.startswith(prefix):
                    return d
    # Fuzzy fallback: first alphanum token of company name
    company = job.get("company", "")
    tokens = re.findall(r'[a-zA-Z0-9]+', company)
    if not tokens:
        return None
    fw = tokens[0].lower()
    for base in [JOBS_DIR, APPLIED_DIR, ARCHIVE_DIR]:
        if not base.exists():
            continue
        matches = [d for d in base.iterdir() if d.is_dir() and d.name.lower().startswith(fw)]
        if len(matches) == 1:
            return matches[0]
    return None


def read_notes(job: dict) -> str:
    job_dir = get_job_dir(job)
    if job_dir:
        notes_file = job_dir / "notes.md"
        if notes_file.exists():
            return notes_file.read_text(encoding="utf-8")
    return job.get("pipeline", {}).get("notes", "")


def write_notes(job: dict, content: str) -> None:
    job_dir = get_job_dir(job)
    if job_dir:
        (job_dir / "notes.md").write_text(content, encoding="utf-8")


def move_job_dir(job: dict, target_dir: Path) -> None:
    """Safely move the job's folder to target_dir if it exists and isn't already there."""
    job_dir = get_job_dir(job)
    if job_dir and job_dir.parent.resolve() != target_dir.resolve():
        target_dir.mkdir(exist_ok=True)
        dest = target_dir / job_dir.name
        if not dest.exists():
            job_dir.rename(dest)
        else:
            # If destination exists, we could merge or handle collision;
            # for now, just don't overwrite if it's already there (rare case).
            pass


def next_job_id(jobs_data: dict) -> int:
    nid = jobs_data.get("next_id", 1)
    jobs_data["next_id"] = nid + 1
    return nid


# ─── Data helpers ─────────────────────────────────────────────────────────────

def load_jobs() -> dict:
    if DATA_FILE.exists():
        with open(DATA_FILE) as f:
            return json.load(f)
    return {"active_jobs": []}


def save_jobs(data: dict) -> None:
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2, default=str)


def job_key(job: dict) -> str:
    return f"{job.get('company', '')}::{job.get('title', '')}"


def find_job_idx(jobs: list, key: str) -> int:
    for i, j in enumerate(jobs):
        if job_key(j) == key:
            return i
    return -1


def today_iso() -> str:
    return date.today().isoformat()


# ─── Mutation helpers ─────────────────────────────────────────────────────────

def save_to_pipeline(jobs_data: dict, jkey: str) -> None:
    idx = find_job_idx(jobs_data["active_jobs"], jkey)
    if idx < 0:
        return
    today = today_iso()
    jobs_data["active_jobs"][idx]["pipeline"] = {
        "status": "want_to_apply",
        "date_added": today,
        "date_updated": today,
        "notes": "",
        "history": [{"status": "want_to_apply", "date": today}],
    }
    save_jobs(jobs_data)


def update_pipeline_status(jobs_data: dict, jkey: str, new_status: str, notes: str = "") -> None:
    idx = find_job_idx(jobs_data["active_jobs"], jkey)
    if idx < 0:
        return
    job = jobs_data["active_jobs"][idx]
    today = today_iso()
    old_status = job.get("pipeline", {}).get("status")
    if "pipeline" not in job:
        job["pipeline"] = {
            "status": new_status,
            "date_added": today,
            "date_updated": today,
            "notes": notes,
            "history": [{"status": new_status, "date": today}],
        }
    else:
        if old_status != new_status:
            job["pipeline"]["history"].append({"status": new_status, "date": today})
        job["pipeline"]["status"] = new_status
        job["pipeline"]["date_updated"] = today
        if notes:
            job["pipeline"]["notes"] = notes
    # Auto-move folder based on status transitions
    if new_status in ["rejected", "withdrawn"]:
        move_job_dir(job, ARCHIVE_DIR)
    elif new_status in ["applied", "recruiter_screen", "interview", "offer"]:
        move_job_dir(job, APPLIED_DIR)
    elif new_status in ["want_to_apply", "content_ready", "referral_found", "referral_submitted"]:
        move_job_dir(job, JOBS_DIR)
    save_jobs(jobs_data)


def save_feedback(jobs_data: dict, jkey: str, rating: str, notes: str, flags: list) -> None:
    idx = find_job_idx(jobs_data["active_jobs"], jkey)
    if idx < 0:
        return
    jobs_data["active_jobs"][idx]["feedback"] = {
        "rating": rating,
        "notes": notes,
        "date_rated": today_iso(),
        "score_flags": flags,
    }
    save_jobs(jobs_data)


# ─── Score display ────────────────────────────────────────────────────────────

def score_metric(col, score: int) -> None:
    if score >= 85:
        col.success(f"Score: {score}")
    elif score >= 70:
        col.info(f"Score: {score}")
    elif score >= 50:
        col.warning(f"Score: {score}")
    else:
        col.error(f"Score: {score}")


# ─── Page 1: Discover ─────────────────────────────────────────────────────────

def discover_page():
    st.header("Discover")

    jobs_data = load_jobs()
    jobs = jobs_data.get("active_jobs", [])

    if not jobs:
        st.info("No jobs found. Run `python scripts/discover.py` to fetch jobs.")
        return

    today = date.today()

    # Sidebar filters (appended below navigation)
    with st.sidebar:
        st.divider()
        st.subheader("Filters")
        show_today_only = st.checkbox("Today's jobs only", value=False)
        show_low_score = st.checkbox("Show low-score & disqualified jobs (< 50)", value=False)
        score_min, score_max = st.slider("Score range", 0, 100, (0, 100))

        all_sources = sorted({
            s.get("platform", "unknown")
            for j in jobs
            for s in j.get("sources", [])
        })
        selected_sources = st.multiselect("Sources", all_sources, default=all_sources)

        date_range = st.date_input(
            "Date range",
            value=(today - timedelta(days=30), today),
            max_value=today,
        )

    # Apply filters
    filtered = []
    for j in jobs:
        score = j.get("score", 0)

        if not show_low_score and score < 50:
            continue
        if score < score_min or score > score_max:
            continue
        if show_today_only and j.get("date_found") != today.isoformat():
            continue

        if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
            found_str = j.get("date_found", "")
            if found_str:
                try:
                    found_date = date.fromisoformat(found_str)
                    if not (date_range[0] <= found_date <= date_range[1]):
                        continue
                except ValueError:
                    pass

        job_sources = [s.get("platform", "unknown") for s in j.get("sources", [])]
        if selected_sources and not any(s in selected_sources for s in job_sources):
            continue

        filtered.append(j)

    # Sort: today's jobs first, then by score descending
    today_iso_val = today.isoformat()
    filtered.sort(key=lambda j: (0 if j.get("date_found") == today_iso_val else 1, -j.get("score", 0)))

    st.write(f"Showing **{len(filtered)}** of {len(jobs)} jobs")

    for i, job in enumerate(filtered):
        jk = job_key(job)
        score = job.get("score", 0)
        in_pipeline = "pipeline" in job
        has_feedback = "feedback" in job

        # Card header
        col1, col2, col3 = st.columns([4, 1, 1])
        with col1:
            st.markdown(f"**{job.get('company', '—')}** — {job.get('title', '—')}")
            st.caption(f"📍 {job.get('location', '—')}  ·  Found: {job.get('date_found', '—')}")
        score_metric(col2, score)
        with col3:
            if in_pipeline:
                st.caption(f"📋 {job['pipeline'].get('status', '').replace('_', ' ')}")
            elif has_feedback:
                st.caption(f"⭐ {job['feedback'].get('rating', '').replace('_', ' ')}")

        # Source links
        sources = job.get("sources", [])
        if sources:
            links = "  ·  ".join(
                f"[{s.get('platform', 'link').capitalize()}]({s.get('url', '')})"
                for s in sources
                if s.get("url")
            )
            st.markdown(links)

        # Expandable details + actions
        with st.expander(f"Details & Actions — {job.get('company', '—')} · {job.get('title', '—')}"):
            # Score breakdown
            breakdown = job.get("score_breakdown", {})
            if breakdown and "deal_breaker_override" not in breakdown:
                st.markdown("**Score Breakdown**")
                bc = st.columns(5)
                bd_fields = [
                    ("company_scale", "Company /35"),
                    ("location", "Location /25"),
                    ("seniority", "Seniority /20"),
                    ("industry", "Industry /20"),
                    ("salary_adjustment", "Salary adj."),
                ]
                for col_idx, (k, label) in enumerate(bd_fields):
                    if k in breakdown:
                        bc[col_idx].metric(label, breakdown[k])
            elif "deal_breaker_override" in breakdown:
                st.warning(f"Deal-breaker override: score capped at {breakdown['deal_breaker_override']}")

            st.divider()

            # Save to pipeline
            if not in_pipeline:
                if st.button("📋 Save to Pipeline", key=f"save_{i}"):
                    data = load_jobs()
                    save_to_pipeline(data, jk)
                    st.success("Saved to pipeline!")
                    st.rerun()
            else:
                st.success(f"In pipeline: **{job['pipeline'].get('status', '').replace('_', ' ')}**")

            st.markdown("**Rate this job**")
            with st.form(key=f"rate_form_{i}"):
                existing_feedback = job.get("feedback", {})
                current_rating = existing_feedback.get("rating", FEEDBACK_RATINGS[0])
                rating_idx = FEEDBACK_RATINGS.index(current_rating) if current_rating in FEEDBACK_RATINGS else 0

                rating = st.selectbox(
                    "Rating",
                    FEEDBACK_RATINGS,
                    index=rating_idx,
                    format_func=lambda x: x.replace("_", " ").title(),
                )
                rating_note = st.text_input(
                    "Note (optional)",
                    value=existing_feedback.get("notes", ""),
                )
                current_flags = existing_feedback.get("score_flags", [])
                flags = st.multiselect(
                    "Flag score issues",
                    SCORE_FLAGS,
                    default=current_flags,
                    format_func=lambda x: x.replace("_", " ").title(),
                )
                if st.form_submit_button("Save Feedback"):
                    data = load_jobs()
                    save_feedback(data, jk, rating, rating_note, flags)
                    st.success("Feedback saved!")
                    st.rerun()

        st.divider()


# ─── Page 2: Pipeline ─────────────────────────────────────────────────────────

def pipeline_page():
    st.header("Pipeline")

    jobs_data = load_jobs()
    jobs = jobs_data.get("active_jobs", [])

    # ── Add by LinkedIn URL ──
    with st.expander("➕ Add job by LinkedIn URL"):
        url_input = st.text_input("LinkedIn job URL", placeholder="https://www.linkedin.com/jobs/view/...")
        if st.button("Fetch & Add to Pipeline"):
            if not url_input.strip():
                st.warning("Please enter a URL.")
            else:
                with st.spinner("Fetching job details..."):
                    fetched = fetch_linkedin_job(url_input.strip())
                if not fetched:
                    st.error("Could not fetch job. Check the URL or try again.")
                elif not fetched["title"] or not fetched["company"]:
                    st.error(f"Fetched job is missing title or company. Got: {fetched}")
                else:
                    # Dedup check
                    existing_keys = {
                        normalize_company(j["company"]) + "__" + normalize_title(j["title"])
                        for j in jobs_data["active_jobs"]
                    }
                    dedup_key = normalize_company(fetched["company"]) + "__" + normalize_title(fetched["title"])
                    if dedup_key in existing_keys:
                        st.warning(f"**{fetched['company']} — {fetched['title']}** is already in your job list.")
                    else:
                        # Score
                        try:
                            with open(CONFIG_PATH) as f:
                                config = json.load(f)
                            score_job(fetched, config)
                        except Exception:
                            fetched.setdefault("score", 0)
                            fetched.setdefault("score_breakdown", {})
                            fetched.setdefault("score_label", "Unknown")
                        # Build full job object
                        today = today_iso()
                        new_job = {
                            "id": next_job_id(jobs_data),
                            "title": fetched["title"],
                            "company": fetched["company"],
                            "location": fetched["location"],
                            "description": fetched["description"],
                            "job_url": fetched["job_url"],
                            "date_posted": "None",
                            "site": "manual",
                            "salary_source": "None",
                            "sources": [{"platform": "manual", "url": fetched["job_url"]}],
                            "score": fetched.get("score", 0),
                            "score_breakdown": fetched.get("score_breakdown", {}),
                            "score_label": fetched.get("score_label", "Unknown"),
                            "date_found": today,
                            "action": "none",
                            "detail_file": "",
                            "pipeline": {
                                "status": "want_to_apply",
                                "date_added": today,
                                "date_updated": today,
                                "notes": "",
                                "history": [{"status": "want_to_apply", "date": today}],
                            },
                        }
                        jobs_data["active_jobs"].append(new_job)
                        save_jobs(jobs_data)
                        st.success(f"Added **{fetched['company']} — {fetched['title']}** to pipeline (score: {fetched.get('score', 0)})")
                        st.rerun()

    pipeline_jobs = [j for j in jobs if "pipeline" in j]

    if not pipeline_jobs:
        st.info("No jobs in pipeline yet. Go to Discover to save jobs.")
        return

    show_closed = st.checkbox("Show rejected / withdrawn", value=False)

    today = date.today()

    # Build groups in stage order
    for stage in PIPELINE_STAGES:
        if stage in CLOSED_STAGES and not show_closed:
            continue

        group = [j for j in pipeline_jobs if j["pipeline"].get("status") == stage]
        if not group:
            continue

        stall_days = STALL_THRESHOLDS.get(stage)  # None for terminal stages

        st.subheader(f"{stage.replace('_', ' ').title()}  ({len(group)})")

        for i, job in enumerate(group):
            jk = job_key(job)
            pipeline = job["pipeline"]
            date_updated_str = pipeline.get("date_updated", "")
            date_added_str = pipeline.get("date_added", "")
            notes = pipeline.get("notes", "")

            # Stale detection
            days_stale = 0
            is_stale = False
            if date_updated_str and stall_days is not None:
                try:
                    days_stale = (today - date.fromisoformat(date_updated_str)).days
                    is_stale = days_stale >= stall_days
                except ValueError:
                    pass

            # Days in pipeline
            days_in_pipeline = 0
            if date_added_str:
                try:
                    days_in_pipeline = (today - date.fromisoformat(date_added_str)).days
                except ValueError:
                    pass

            stale_tag = "  ⚠️ Stale" if is_stale else ""
            job_id = job.get("id", "")
            id_tag = f"#{job_id} · " if job_id else ""

            with st.container():
                col1, col2, col3 = st.columns([3, 1, 2])

                with col1:
                    st.markdown(f"**{job.get('company', '—')}** — {job.get('title', '—')}{stale_tag}")
                    st.caption(
                        f"{id_tag}Score: {job.get('score', 0)}  ·  "
                        f"Added: {date_added_str}  ·  "
                        f"Updated: {days_stale}d ago  ·  "
                        f"{days_in_pipeline}d in pipeline"
                    )

                with col2:
                    sources = job.get("sources", [])
                    if sources and sources[0].get("url"):
                        st.markdown(f"[Open job]({sources[0]['url']})")

                with col3:
                    current_stage = pipeline.get("status", "want_to_apply")
                    stage_idx = PIPELINE_STAGES.index(current_stage) if current_stage in PIPELINE_STAGES else 0
                    with st.form(key=f"pipeline_form_{stage}_{i}"):
                        new_status = st.selectbox(
                            "Stage",
                            PIPELINE_STAGES,
                            index=stage_idx,
                            format_func=lambda x: x.replace("_", " ").title(),
                            label_visibility="collapsed",
                        )
                        if st.form_submit_button("Update"):
                            data = load_jobs()
                            update_pipeline_status(data, jk, new_status)
                            st.success("Updated!")
                            st.rerun()

            # Notes — read from notes.md, write back on save
            current_notes = read_notes(job)
            with st.expander("📝 Notes", expanded=bool(current_notes)):
                with st.form(key=f"notes_form_{stage}_{i}"):
                    new_notes = st.text_area(
                        "notes",
                        value=current_notes,
                        height=200,
                        label_visibility="collapsed",
                    )
                    if st.form_submit_button("Save notes"):
                        write_notes(job, new_notes)
                        # Keep a short summary in JSON for quick reference
                        data = load_jobs()
                        idx2 = find_job_idx(data["active_jobs"], jk)
                        if idx2 >= 0 and "pipeline" in data["active_jobs"][idx2]:
                            data["active_jobs"][idx2]["pipeline"]["notes"] = new_notes[:120]
                            save_jobs(data)
                        st.success("Notes saved!")

            st.divider()


# ─── Page 3: Scoring Insights ─────────────────────────────────────────────────

def insights_page():
    st.header("Scoring Insights")
    st.caption("Read-only — use this to inform manual config.json updates")

    jobs_data = load_jobs()
    jobs = jobs_data.get("active_jobs", [])

    rated_jobs = [j for j in jobs if "feedback" in j]
    flagged_jobs = [j for j in rated_jobs if j["feedback"].get("score_flags")]
    relevant_count = sum(1 for j in rated_jobs if j["feedback"].get("rating") == "relevant")
    relevance_rate = round(relevant_count / len(rated_jobs) * 100) if rated_jobs else 0

    # Summary metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total jobs", len(jobs))
    c2.metric("Rated jobs", len(rated_jobs))
    c3.metric("Flagged issues", len(flagged_jobs))
    c4.metric("Relevance rate", f"{relevance_rate}%")

    if not rated_jobs:
        st.info("No feedback collected yet. Rate jobs on the Discover page.")
        return

    st.divider()

    # Rating distribution by score bucket
    st.subheader("Rating Distribution by Score Bucket")
    buckets = [
        ("85-100 Strong", 85, 100),
        ("70-84 Good", 70, 84),
        ("50-69 Possible", 50, 69),
        ("0-49 Poor", 0, 49),
    ]
    bucket_rows = []
    for label, low, high in buckets:
        bucket_jobs = [j for j in rated_jobs if low <= j.get("score", 0) <= high]
        if bucket_jobs:
            bucket_rows.append({
                "Bucket": label,
                "Total": len(bucket_jobs),
                "Relevant": sum(1 for j in bucket_jobs if j["feedback"].get("rating") == "relevant"),
                "Maybe": sum(1 for j in bucket_jobs if j["feedback"].get("rating") == "maybe"),
                "Not Relevant": sum(1 for j in bucket_jobs if j["feedback"].get("rating") == "not_relevant"),
            })
    if bucket_rows:
        st.dataframe(pd.DataFrame(bucket_rows), use_container_width=True, hide_index=True)

    st.divider()

    # Flagged score issues
    if flagged_jobs:
        st.subheader("Flagged Score Issues")
        flag_counts: dict[str, list] = {}
        for j in flagged_jobs:
            for flag in j["feedback"].get("score_flags", []):
                flag_counts.setdefault(flag, []).append(f"{j.get('company')} — {j.get('title')}")

        flag_rows = [
            {
                "Flag": flag.replace("_", " ").title(),
                "Count": len(examples),
                "Example": examples[0],
            }
            for flag, examples in sorted(flag_counts.items(), key=lambda x: -len(x[1]))
        ]
        st.dataframe(pd.DataFrame(flag_rows), use_container_width=True, hide_index=True)
    else:
        st.info("No score flags collected yet.")

    st.divider()

    # Scoring gaps: rated relevant but scored < 70
    st.subheader("Scoring Gaps  (rated Relevant, Score < 70)")
    gap_jobs = [
        j for j in rated_jobs
        if j["feedback"].get("rating") == "relevant" and j.get("score", 0) < 70
    ]
    if gap_jobs:
        gap_rows = []
        for j in sorted(gap_jobs, key=lambda x: x.get("score", 0)):
            bd = j.get("score_breakdown", {})
            gap_rows.append({
                "Company": j.get("company", ""),
                "Title": j.get("title", ""),
                "Score": j.get("score", 0),
                "Company /35": bd.get("company_scale", ""),
                "Location /25": bd.get("location", ""),
                "Seniority /20": bd.get("seniority", ""),
                "Industry /20": bd.get("industry", ""),
            })
        st.dataframe(pd.DataFrame(gap_rows), use_container_width=True, hide_index=True)
    else:
        st.info("No scoring gaps found — all relevant jobs scored ≥ 70.")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    st.set_page_config(
        page_title="Jobmore",
        page_icon="💼",
        layout="wide",
    )

    with st.sidebar:
        st.title("💼 Jobmore")
        page = st.radio(
            "Navigate",
            ["Discover", "Pipeline", "Scoring Insights"],
            label_visibility="collapsed",
        )

    if page == "Discover":
        discover_page()
    elif page == "Pipeline":
        pipeline_page()
    else:
        insights_page()


if __name__ == "__main__":
    main()
