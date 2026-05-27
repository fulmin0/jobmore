"""
app.py - Jobmore web interface
Three pages: Discover, Pipeline, Scoring Insights

Run with:  streamlit run scripts/app.py
"""

import json
import re
import sys
import shutil
import subprocess
import time
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
REFERRAL_DIR = JOBS_DIR / "referral"
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
        for base in [JOBS_DIR, APPLIED_DIR, REFERRAL_DIR, ARCHIVE_DIR]:
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
    for base in [JOBS_DIR, APPLIED_DIR, REFERRAL_DIR, ARCHIVE_DIR]:
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
    existing = {j.get("id") for j in jobs_data.get("active_jobs", [])}
    nid = jobs_data.get("next_id", 1)
    while nid in existing:
        nid += 1
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
    elif new_status in ["referral_found", "referral_submitted"]:
        move_job_dir(job, REFERRAL_DIR)
    elif new_status in ["want_to_apply", "content_ready"]:
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


# ─── Content generation ──────────────────────────────────────────────────────

CONTENT_POLL_INTERVAL = 30  # seconds between file/subprocess checks

CLI_BACKENDS = {
    "claude": ["--print", "--permission-mode", "bypassPermissions"],
    "codex":  ["--approval-mode", "full-auto"],
}

CONTENT_ISSUE_TAGS = [
    "Too formal",
    "Missing key story",
    "Wrong domain framing",
    "Doesn't match JD pillar",
    "Off-brand tone",
    "Wrong length",
]


def make_job_dir_name(job: dict) -> str:
    job_id = int(job.get("id", 0))
    company = re.sub(r'[^\w\s]', '', job.get("company", "")).strip()
    title = re.sub(r'[^\w\s]', '', job.get("title", "")).strip()
    slug = f"{company}_{title}".replace(" ", "_")
    slug = re.sub(r'_+', '_', slug)
    return f"{job_id:04d}_{slug}"


def _get_resume_pdf_path(job_dir: Path) -> Path | None:
    try:
        with open(CONFIG_PATH) as f:
            config = json.load(f)
        pdf_name = config.get("personal", {}).get("pdf_name", "")
        if pdf_name:
            p = job_dir / f"{pdf_name}.pdf"
            return p if p.exists() else None
    except Exception:
        pass
    pdfs = [p for p in job_dir.glob("*.pdf") if "cover" not in p.name.lower()]
    return pdfs[0] if pdfs else None


def get_content_status(job: dict) -> dict:
    job_dir = get_job_dir(job)
    if not job_dir:
        return {"job_intelligence": False, "elevator_pitch": False, "cover_letter": False, "resume": False}
    return {
        "job_intelligence": (job_dir / "job_intelligence.md").exists(),
        "elevator_pitch": (job_dir / "elevator_pitch.md").exists(),
        "cover_letter": (job_dir / "cover_letter.pdf").exists(),
        "resume": _get_resume_pdf_path(job_dir) is not None,
    }


def _build_generation_prompt(job: dict, job_dir: Path) -> str:
    company = job.get("company", "")
    title = job.get("title", "")
    jd = (job.get("description", "") or "")[:4000]
    rel = job_dir.relative_to(PROJECT_BASE)
    return (
        f"Generate all job application content for {company} — {title}.\n\n"
        f"Output directory: {rel}\n"
        f"Job description:\n{jd}\n\n"
        "Run in order:\n"
        f"1. Read prompts/job_intelligence.md and follow the workflow → write {rel}/job_intelligence.md\n"
        f"2. Read prompts/elevator_pitch.md and follow the workflow → write {rel}/elevator_pitch.md\n"
        f"3. Read prompts/cover_letter.md and follow the workflow → write artifacts to {rel}/\n"
        f"4. Read prompts/resume_content.md and follow the workflow → write {rel}/resume_content.md and build resume PDF\n\n"
        "Read data/experience/*.md before generating any content."
    )


def available_backends() -> list[str]:
    return [name for name in CLI_BACKENDS if shutil.which(name)]


def start_content_generation(job: dict, backend: str = "claude") -> None:
    jk = job_key(job)
    cli_bin = shutil.which(backend)
    if not cli_bin:
        st.error(f"`{backend}` CLI not found in PATH.")
        return
    job_dir = get_job_dir(job)
    if not job_dir:
        dir_name = make_job_dir_name(job)
        job_dir = JOBS_DIR / dir_name
        job_dir.mkdir(parents=True, exist_ok=True)
    prompt = _build_generation_prompt(job, job_dir)
    proc = subprocess.Popen(
        [cli_bin, *CLI_BACKENDS[backend], prompt],
        cwd=str(PROJECT_BASE),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    now = time.time()
    st.session_state[f"gen_proc_{jk}"] = proc
    st.session_state[f"gen_start_{jk}"] = now
    st.session_state[f"last_poll_{jk}"] = now


def save_artifact_feedback(job_dir: Path, artifact: str, tags: list, notes: str, approved: bool) -> None:
    intel_file = job_dir / "job_intelligence.md"
    if not intel_file.exists():
        return
    content = intel_file.read_text(encoding="utf-8")
    existing = re.findall(rf"### {re.escape(artifact)} — v(\d+)", content)
    version = len(existing) + 1
    today = today_iso()
    if approved:
        entry = f"\n### {artifact} — v{version} → approved {today}\n"
    else:
        tag_str = ", ".join(tags) if tags else "none"
        entry = (
            f"\n### {artifact} — v{version} → revision requested {today}\n"
            f"Issues: {tag_str}\n"
            f"Notes: {notes}\n"
        )
    if "## Content iterations" in content:
        content += entry
    else:
        content += f"\n\n## Content iterations\n{entry}"
    intel_file.write_text(content, encoding="utf-8")


def build_revision_prompt(job: dict, artifact: str, tags: list, notes: str, job_dir: Path) -> str:
    rel = job_dir.relative_to(PROJECT_BASE)
    file_map = {
        "elevator_pitch": "elevator_pitch.md",
        "cover_letter": "cover_letter.tex",
        "resume": "resume_content.md",
    }
    artifact_file = file_map.get(artifact, f"{artifact}.md")
    tag_str = ", ".join(tags) if tags else "none"
    return (
        f"Revise the {artifact.replace('_', ' ')} for {job.get('company')} — {job.get('title')}.\n\n"
        f"Issues flagged: {tag_str}\n"
        f"Specific notes: {notes}\n\n"
        f"Current version: {rel}/{artifact_file}\n"
        f"Reference: {rel}/job_intelligence.md\n"
        f"Prompts: prompts/{artifact}.md"
    )


def _render_artifact_feedback(artifact: str, job: dict, job_dir: Path, jk: str) -> None:
    revise_key = f"revising_{jk}_{artifact}"
    prompt_key = f"revision_prompt_{jk}_{artifact}"
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("👍 Approved", key=f"approve_{jk}_{artifact}"):
            save_artifact_feedback(job_dir, artifact, [], "", approved=True)
            st.success("Logged as approved.")
    with col_b:
        if st.button("✏️ Request revision", key=f"revise_btn_{jk}_{artifact}"):
            st.session_state[revise_key] = True
    if st.session_state.get(revise_key):
        with st.form(key=f"revision_form_{jk}_{artifact}"):
            tags = st.multiselect("Issue tags", CONTENT_ISSUE_TAGS)
            notes = st.text_area("What specifically needs to change?")
            if st.form_submit_button("Save feedback + copy revision prompt"):
                save_artifact_feedback(job_dir, artifact, tags, notes, approved=False)
                prompt = build_revision_prompt(job, artifact, tags, notes, job_dir)
                st.session_state[prompt_key] = prompt
                st.session_state[revise_key] = False
                st.success("Feedback saved.")
    if prompt_key in st.session_state:
        st.code(st.session_state[prompt_key], language=None)


def _render_generation_status(jk: str, job: dict) -> None:
    proc = st.session_state.get(f"gen_proc_{jk}")
    start = st.session_state.get(f"gen_start_{jk}", time.time())
    last_poll = st.session_state.get(f"last_poll_{jk}", start)
    now = time.time()
    elapsed_s = int(now - start)
    elapsed_str = f"{elapsed_s // 60}m {elapsed_s % 60}s" if elapsed_s >= 60 else f"{elapsed_s}s"
    next_poll_s = max(0, CONTENT_POLL_INTERVAL - int(now - last_poll))
    st.info(f"⏱ {elapsed_str} elapsed  |  Next check in {next_poll_s}s")
    if now - last_poll >= CONTENT_POLL_INTERVAL:
        if proc is not None and proc.poll() is not None:
            del st.session_state[f"gen_proc_{jk}"]
            del st.session_state[f"gen_start_{jk}"]
            del st.session_state[f"last_poll_{jk}"]
            st.rerun()
            return
        st.session_state[f"last_poll_{jk}"] = now
    status = get_content_status(job)
    step_cols = st.columns(4)
    for col, name, label in zip(
        step_cols,
        ["job_intelligence", "elevator_pitch", "cover_letter", "resume"],
        ["Intelligence", "Pitch", "Cover Letter", "Resume"],
    ):
        col.metric(label, "✅" if status[name] else "⏳")


def render_content_panel(job: dict) -> None:
    jk = job_key(job)
    job_dir = get_job_dir(job)
    is_generating = f"gen_proc_{jk}" in st.session_state
    with st.expander("📄 Content"):
        if is_generating:
            _render_generation_status(jk, job)
            return
        status = get_content_status(job)
        has_any = any(status.values())
        backend = st.session_state.get("ai_backend", "claude")
        cli_available = bool(shutil.which(backend))
        if not has_any:
            if not cli_available:
                st.warning(f"`{backend}` CLI not found in PATH — cannot auto-generate.")
            else:
                if st.button("⚡ Generate content", key=f"gen_{jk}"):
                    start_content_generation(job, backend)
                    st.rerun()
            return
        if not all(status.values()) and cli_available:
            if st.button("🔄 Regenerate missing", key=f"regen_{jk}"):
                start_content_generation(job, st.session_state.get("ai_backend", "claude"))
                st.rerun()
        if status["elevator_pitch"] and job_dir:
            st.markdown("**📝 Elevator Pitch**")
            text = (job_dir / "elevator_pitch.md").read_text(encoding="utf-8")
            st.code(text, language=None)
            _render_artifact_feedback("elevator_pitch", job, job_dir, jk)
            st.divider()
        if status["cover_letter"] and job_dir:
            st.markdown("**📎 Cover Letter**")
            pdf_bytes = (job_dir / "cover_letter.pdf").read_bytes()
            st.download_button(
                "⬇ Download Cover Letter PDF",
                pdf_bytes,
                file_name="cover_letter.pdf",
                mime="application/pdf",
                key=f"dl_cl_{jk}",
            )
            _render_artifact_feedback("cover_letter", job, job_dir, jk)
            st.divider()
        if status["resume"] and job_dir:
            pdf_path = _get_resume_pdf_path(job_dir)
            if pdf_path:
                st.markdown("**📎 Resume**")
                pdf_bytes = pdf_path.read_bytes()
                st.download_button(
                    "⬇ Download Resume PDF",
                    pdf_bytes,
                    file_name=pdf_path.name,
                    mime="application/pdf",
                    key=f"dl_res_{jk}",
                )
                _render_artifact_feedback("resume", job, job_dir, jk)


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


# ─── Job card renderer ────────────────────────────────────────────────────────

def render_job_card(job: dict, card_idx: int, tab_prefix: str = "") -> None:
    jk = job_key(job)
    score = job.get("score", 0)
    in_pipeline = "pipeline" in job
    has_feedback = "feedback" in job

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

    sources = job.get("sources", [])
    link_col, btn_col = st.columns([4, 1])
    with link_col:
        if sources:
            links = "  ·  ".join(
                f"[{s.get('platform', 'link').capitalize()}]({s.get('url', '')})"
                for s in sources
                if s.get("url")
            )
            st.markdown(links)
    with btn_col:
        if not in_pipeline:
            if st.button("📋 Save to Pipeline", key=f"{tab_prefix}save_{card_idx}"):
                data = load_jobs()
                save_to_pipeline(data, jk)
                start_content_generation(job, st.session_state.get("ai_backend", "claude"))
                st.success("Saved! Generating content...")
                st.rerun()

    with st.expander(f"Details & Actions — {job.get('company', '—')} · {job.get('title', '—')}"):
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

        st.markdown("**Rate this job**")
        with st.form(key=f"{tab_prefix}rate_form_{card_idx}"):
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
            value=(today - timedelta(days=1), today),
            max_value=today,
        )

    # Apply filters (used by All Jobs tab)
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

    # Sort All Jobs: today's jobs first, then by score descending
    today_iso_val = today.isoformat()
    filtered.sort(key=lambda j: (0 if j.get("date_found") == today_iso_val else 1, -j.get("score", 0)))

    # Target Jobs: is_target_company == True, sorted by score descending (no sidebar filters)
    target_jobs = sorted(
        [j for j in jobs if j.get("is_target_company")],
        key=lambda j: j.get("score", 0),
        reverse=True,
    )

    tab_target, tab_all = st.tabs(["🎯 Target Jobs", "All Jobs"])

    with tab_target:
        if not target_jobs:
            st.info("No target company jobs found. Add companies to `data/target_companies.json` and run discovery.")
        else:
            st.write(f"**{len(target_jobs)}** jobs from target companies")
            for i, job in enumerate(target_jobs):
                render_job_card(job, i, tab_prefix="target_")

    with tab_all:
        st.write(f"Showing **{len(filtered)}** of {len(jobs)} jobs")
        for i, job in enumerate(filtered):
            render_job_card(job, i, tab_prefix="all_")


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
                    existing_job = next(
                        (j for j in jobs_data["active_jobs"]
                         if normalize_company(j["company"]) + "__" + normalize_title(j["title"])
                         == normalize_company(fetched["company"]) + "__" + normalize_title(fetched["title"])),
                        None,
                    )
                    if existing_job is not None:
                        if "pipeline" in existing_job:
                            status = existing_job["pipeline"].get("status", "unknown").replace("_", " ").title()
                            st.info(f"**{existing_job['company']} — {existing_job['title']}** is already in the pipeline ({status}).")
                        else:
                            today = today_iso()
                            existing_job["pipeline"] = {
                                "status": "want_to_apply",
                                "date_added": today,
                                "date_updated": today,
                                "notes": "",
                                "history": [{"status": "want_to_apply", "date": today}],
                            }
                            save_jobs(jobs_data)
                            start_content_generation(existing_job, st.session_state.get("ai_backend", "claude"))
                            st.success(f"Added **{existing_job['company']} — {existing_job['title']}** to pipeline. Generating content...")
                            st.rerun()
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
                        start_content_generation(new_job, st.session_state.get("ai_backend", "claude"))
                        st.success(f"Added **{fetched['company']} — {fetched['title']}** to pipeline (score: {fetched.get('score', 0)}). Generating content...")
                        st.rerun()

    # ── Add manually (no URL) ──
    # Show success/info banner outside expander so it survives the rerun
    if "manual_add_banner" in st.session_state:
        level, msg = st.session_state.pop("manual_add_banner")
        getattr(st, level)(msg)

    _form_v = st.session_state.get("manual_form_v", 0)
    _expander_open = st.session_state.pop("manual_expander_open", False)
    with st.expander("✏️ Add job manually (no URL)", expanded=_expander_open):
        with st.form(f"manual_add_form_{_form_v}"):
            man_company = st.text_input("Company *")
            man_title = st.text_input("Title *")
            man_location = st.text_input("Location")
            man_url = st.text_input("Job URL (optional)")
            man_desc = st.text_area("Job description / paste text (optional)", height=200)
            submitted = st.form_submit_button("Add to Pipeline")

        if submitted:
            if not man_company.strip() or not man_title.strip():
                st.warning("Company and Title are required.")
            else:
                existing_job = next(
                    (j for j in jobs_data["active_jobs"]
                     if normalize_company(j["company"]) + "__" + normalize_title(j["title"])
                     == normalize_company(man_company.strip()) + "__" + normalize_title(man_title.strip())),
                    None,
                )
                if existing_job is not None:
                    if "pipeline" in existing_job:
                        status = existing_job["pipeline"].get("status", "unknown").replace("_", " ").title()
                        st.session_state["manual_add_banner"] = ("info", f"**{existing_job['company']} — {existing_job['title']}** is already in the pipeline ({status}).")
                        st.session_state["manual_form_v"] = _form_v + 1
                        st.rerun()
                    else:
                        today = today_iso()
                        existing_job["pipeline"] = {
                            "status": "want_to_apply",
                            "date_added": today,
                            "date_updated": today,
                            "notes": "",
                            "history": [{"status": "want_to_apply", "date": today}],
                        }
                        save_jobs(jobs_data)
                        start_content_generation(existing_job, st.session_state.get("ai_backend", "claude"))
                        st.session_state["manual_add_banner"] = ("success", f"Added **{existing_job['company']} — {existing_job['title']}** to pipeline. Generating content...")
                        st.session_state["manual_form_v"] = _form_v + 1
                        st.rerun()
                else:
                    job_obj = {
                        "title": man_title.strip(),
                        "company": man_company.strip(),
                        "location": man_location.strip(),
                        "description": man_desc.strip(),
                        "job_url": man_url.strip(),
                    }
                    try:
                        with open(CONFIG_PATH) as f:
                            config = json.load(f)
                        score_job(job_obj, config)
                    except Exception:
                        job_obj.setdefault("score", 0)
                        job_obj.setdefault("score_breakdown", {})
                        job_obj.setdefault("score_label", "Unknown")
                    today = today_iso()
                    new_job = {
                        "id": next_job_id(jobs_data),
                        "title": job_obj["title"],
                        "company": job_obj["company"],
                        "location": job_obj["location"],
                        "description": job_obj["description"],
                        "job_url": job_obj["job_url"],
                        "date_posted": "None",
                        "site": "manual",
                        "salary_source": "None",
                        "sources": [{"platform": "manual", "url": job_obj["job_url"]}],
                        "score": job_obj.get("score", 0),
                        "score_breakdown": job_obj.get("score_breakdown", {}),
                        "score_label": job_obj.get("score_label", "Unknown"),
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
                    start_content_generation(new_job, st.session_state.get("ai_backend", "claude"))
                    st.session_state["manual_add_banner"] = ("success", f"Added **{job_obj['company']} — {job_obj['title']}** to pipeline (score: {job_obj.get('score', 0)}). Generating content...")
                    st.session_state["manual_form_v"] = _form_v + 1
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

            render_content_panel(job)

            st.divider()

    # Auto-rerun every second while any job is generating (keeps countdown timer live)
    if any(f"gen_proc_{job_key(j)}" in st.session_state for j in pipeline_jobs):
        time.sleep(1)
        st.rerun()


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
        st.divider()
        backends = available_backends()
        if backends:
            selected_backend = st.selectbox(
                "AI backend",
                backends,
                index=0,
                help="CLI used for content generation",
            )
        else:
            selected_backend = "claude"
            st.warning("No AI CLI found in PATH (`claude` or `codex`).")
        st.session_state["ai_backend"] = selected_backend

    if page == "Discover":
        discover_page()
    elif page == "Pipeline":
        pipeline_page()
    else:
        insights_page()


if __name__ == "__main__":
    main()
