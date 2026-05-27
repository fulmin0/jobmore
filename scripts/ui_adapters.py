"""
ui_adapters.py — maps real active_jobs dicts → typed card dicts for the board UI.
Pure data module: no Streamlit imports, no filesystem access.
"""

from datetime import date


STALL_DAYS = {
    "want_to_apply": 7,
    "content_ready": 5,
    "referral_found": 5,
    "referral_submitted": 7,
    "applied": 10,
    "recruiter_screen": 7,
    "interview": 5,
}


def days_since(date_str: str) -> int:
    try:
        return (date.today() - date.fromisoformat(date_str)).days
    except Exception:
        return 0


def infer_remote(location: str) -> str:
    loc = (location or "").lower()
    if "remote" in loc:
        return "remote"
    if "hybrid" in loc:
        return "hybrid"
    return "onsite"


def _base(job: dict, kind: str) -> dict:
    return {
        "kind": kind,
        "id": job.get("id", 0),
        "co": job.get("company", ""),
        "title": job.get("title", ""),
        "loc": job.get("location", ""),
        "rem": infer_remote(job.get("location", "")),
        "score": job.get("score", 0),
        "job_key": f"{job.get('company', '')}::{job.get('title', '')}",
    }


def _is_stale(job: dict) -> bool:
    pipeline = job.get("pipeline", {})
    status = pipeline.get("status", "")
    date_updated = pipeline.get("date_updated", "")
    if status not in STALL_DAYS or not date_updated:
        return False
    return days_since(date_updated) >= STALL_DAYS[status]


def build_discover_cards(jobs: list, limit: int = 50) -> list:
    result = []
    for job in jobs:
        if "pipeline" in job:
            continue
        if job.get("score", 0) < 50:
            continue
        if job.get("feedback", {}).get("rating") == "not_relevant":
            continue
        result.append(_base(job, "discover"))
    result.sort(key=lambda c: -c["score"])
    return result[:limit]


def build_shortlist_cards(jobs: list) -> list:
    result = []
    for job in jobs:
        status = job.get("pipeline", {}).get("status")
        if status not in ("want_to_apply", "content_ready"):
            continue
        card = _base(job, "shortlist")
        pipeline = job.get("pipeline", {})
        date_updated = pipeline.get("date_updated", "")
        d = days_since(date_updated) if date_updated else 0
        threshold = STALL_DAYS.get(status, 999)
        card["materials"] = None  # filled by board_page via get_content_status
        card["is_stale"] = d >= threshold
        card["days_stale"] = d
        result.append(card)
    return result


def build_referral_cards(jobs: list) -> list:
    result = []
    for job in jobs:
        status = job.get("pipeline", {}).get("status")
        if status not in ("referral_found", "referral_submitted"):
            continue
        card = _base(job, "referral")
        pipeline = job.get("pipeline", {})
        notes = (pipeline.get("notes") or "").strip()
        contact = notes.split("\n")[0][:40].strip() if notes else "Follow up required"
        date_updated = pipeline.get("date_updated", "")
        d = days_since(date_updated) if date_updated else 0
        threshold = STALL_DAYS.get(status, 5)
        card["contact"] = contact
        card["sub"] = "submitted" if status == "referral_submitted" else None
        card["is_overdue"] = d >= threshold
        card["days_overdue"] = d
        result.append(card)
    return result


def build_applied_cards(jobs: list) -> list:
    result = []
    for job in jobs:
        status = job.get("pipeline", {}).get("status")
        if status not in ("applied", "recruiter_screen"):
            continue
        card = _base(job, "applied")
        pipeline = job.get("pipeline", {})
        date_updated = pipeline.get("date_updated", pipeline.get("date_added", ""))
        d = days_since(date_updated) if date_updated else 0
        threshold = STALL_DAYS.get(status, 7)
        card["sub"] = "screen" if status == "recruiter_screen" else "applied"
        card["since"] = f"applied {pipeline.get('date_updated', '')}"
        card["recruiter"] = None
        fo_urgent = d >= threshold and status == "applied"
        card["fo_up"] = {
            "urgent": fo_urgent,
            "label": f"follow up · {d}d no response" if fo_urgent else "HM round pending",
        }
        result.append(card)
    return result


def build_interview_cards(jobs: list) -> list:
    result = []
    for job in jobs:
        status = job.get("pipeline", {}).get("status")
        if status not in ("interview", "offer"):
            continue
        card = _base(job, "interview")
        pipeline = job.get("pipeline", {})
        history = pipeline.get("history", [])
        interview_count = sum(1 for h in history if h.get("status") == "interview")
        done_count = max(0, interview_count - 1)
        card["rounds"] = ["done"] * done_count + ["next", "pending"]
        notes = (pipeline.get("notes") or "").strip()
        card["next_label"] = notes.split("\n")[0][:60].strip() if notes else "Interview in progress"
        result.append(card)
    return result


def build_goals(pipeline_jobs: list, config: dict) -> list:
    goals_cfg = config.get("goals", {})
    shortlist_target = goals_cfg.get("shortlist_target", 5)
    mock_done = goals_cfg.get("mock_done", 0)
    shortlist_count = sum(
        1 for j in pipeline_jobs
        if j.get("pipeline", {}).get("status") in ("want_to_apply", "content_ready")
    )
    stalled_count = sum(1 for j in pipeline_jobs if _is_stale(j))
    return [
        {"label": "shortlist", "done": shortlist_count, "target": shortlist_target, "tone": None},
        {
            "label": "stalled",
            "done": stalled_count,
            "target": max(1, stalled_count),
            "tone": "red" if stalled_count > 0 else None,
        },
        {"label": "mock", "done": mock_done, "target": 1, "tone": "green"},
    ]


def build_strip_items(pipeline_jobs: list, limit: int = 6) -> list:
    items = []
    for job in pipeline_jobs:
        if not _is_stale(job):
            continue
        pipeline = job.get("pipeline", {})
        status = pipeline.get("status", "")
        date_updated = pipeline.get("date_updated", "")
        d = days_since(date_updated) if date_updated else 0
        threshold = STALL_DAYS.get(status, 7)
        text = f"{job.get('company', '')} · {status.replace('_', ' ')} · {d}d"
        items.append({"text": text, "overdue": d >= int(threshold * 1.5)})
    items.sort(key=lambda x: (0 if x["overdue"] else 1))
    return items[:limit]
