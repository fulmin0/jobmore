"""
calibrate.py — Derive per-company scoring adjustments from accumulated feedback.

Called daily by discover.py before re-scoring. Writes data/feedback_overrides.json
which scorer.py applies as a final nudge after component scoring.

Adjustment rules (applied in priority order):
  Multi-rating (≥2 ratings for same company):
    ≥75% not_relevant          → -15
    ≥75% relevant/maybe        → +8
  Single-job flags (only when no multi-rating rule fired):
    actually_good_fit          → +10
    company_tier_wrong + not_relevant  → -10
    company_tier_wrong + relevant/maybe → +8
"""

import json
import os
from collections import defaultdict
from datetime import date

from scorer import normalize

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
OVERRIDES_PATH = os.path.join(DATA_DIR, "feedback_overrides.json")

# Minimum ratings for the multi-rating company rule to fire
_MIN_RATINGS = 2
_SUPPRESS_THRESHOLD = 0.75   # fraction not_relevant to soft-suppress
_BOOST_THRESHOLD = 0.75      # fraction relevant/maybe to soft-boost


def run_calibration(jobs_data: dict) -> dict:
    """
    Derive overrides from feedback in jobs_data.
    Writes feedback_overrides.json and returns the overrides dict.
    """
    rated_jobs = [j for j in jobs_data.get("active_jobs", []) if "feedback" in j]

    empty = {
        "last_calibrated": date.today().isoformat(),
        "rated_count": 0,
        "company_adjustments": {},
    }
    if not rated_jobs:
        _write(empty)
        return empty

    # Aggregate per company
    company_ratings: dict[str, list] = defaultdict(list)
    company_flag_jobs: dict[str, list] = defaultdict(list)

    for job in rated_jobs:
        ckey = normalize(job.get("company", ""))
        if not ckey:
            continue
        rating = job["feedback"].get("rating", "")
        flags = set(job["feedback"].get("score_flags", []))
        if rating:
            company_ratings[ckey].append(rating)
        if flags:
            company_flag_jobs[ckey].append({"rating": rating, "flags": flags})

    adjustments: dict[str, int] = {}
    sources: dict[str, str] = {}  # for the summary log

    # Rule 1: multi-rating company suppression / boost
    for ckey, ratings in company_ratings.items():
        if len(ratings) < _MIN_RATINGS:
            continue
        total = len(ratings)
        not_rel = ratings.count("not_relevant")
        positive = ratings.count("relevant") + ratings.count("maybe")

        if not_rel / total >= _SUPPRESS_THRESHOLD:
            adjustments[ckey] = -15
            sources[ckey] = f"{not_rel}/{total} not_relevant"
        elif positive / total >= _BOOST_THRESHOLD:
            adjustments[ckey] = 8
            sources[ckey] = f"{positive}/{total} relevant/maybe"

    # Rule 2: single-job flag signals (only when multi-rating rule didn't fire)
    all_companies = set(company_ratings.keys()) | set(company_flag_jobs.keys())
    for ckey in all_companies:
        if ckey in adjustments:
            continue  # multi-rating rule already applied
        for entry in company_flag_jobs.get(ckey, []):
            flags = entry["flags"]
            rating = entry["rating"]

            if "actually_good_fit" in flags:
                adj = max(adjustments.get(ckey, 0), 10)
                adjustments[ckey] = adj
                sources[ckey] = "actually_good_fit flag"

            if "company_tier_wrong" in flags:
                if rating == "not_relevant":
                    adj = min(adjustments.get(ckey, 0), -10)
                    adjustments[ckey] = adj
                    sources[ckey] = "company_tier_wrong + not_relevant"
                elif rating in ("relevant", "maybe"):
                    adj = max(adjustments.get(ckey, 0), 8)
                    adjustments[ckey] = adj
                    sources[ckey] = "company_tier_wrong + relevant"

    overrides = {
        "last_calibrated": date.today().isoformat(),
        "rated_count": len(rated_jobs),
        "company_adjustments": adjustments,
    }

    _write(overrides)
    _print_summary(adjustments, sources, len(rated_jobs))
    return overrides


def _write(overrides: dict) -> None:
    with open(OVERRIDES_PATH, "w") as f:
        json.dump(overrides, f, indent=2)


def _print_summary(adjustments: dict, sources: dict, rated_count: int) -> None:
    print(f"\n--- Feedback Calibration ---")
    print(f"Rated: {rated_count} jobs | Adjustments: {len(adjustments)} companies")
    for ckey, adj in sorted(adjustments.items(), key=lambda x: -abs(x[1])):
        sign = "+" if adj > 0 else ""
        reason = sources.get(ckey, "")
        print(f"  {sign}{adj:+d}  {ckey}  ({reason})")
    if not adjustments:
        print("  No adjustments derived yet.")
