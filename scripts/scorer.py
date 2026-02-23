"""
scorer.py - Rule-based job scoring for Phase 1
No AI/API required. Scores based on company scale, location, seniority, industry.
Skill match is skipped for Phase 1 (added in Phase 2).
"""

import re
from typing import Optional


def normalize(text: str) -> str:
    """Lowercase and strip common noise words for matching."""
    if not text:
        return ""
    text = text.lower()
    for noise in ["pvt ltd", "pvt. ltd.", "private limited", "inc.", "inc", "india", "ltd", "llp", "technologies", "technology", "solutions", "services"]:
        text = text.replace(noise, "")
    return re.sub(r"[^a-z0-9 ]", "", text).strip()


def score_company(company_name: str, description: str, config: dict) -> int:
    """Score company scale/reputation. Max 35 points."""
    if not company_name:
        return 12  # Unknown

    name_norm = normalize(company_name)
    tier1_list = [normalize(c) for c in config["company_preferences"]["tier1"]]

    # Tier 1 check
    for tier1 in tier1_list:
        if tier1 and tier1 in name_norm:
            return 35

    # Headcount signals in description
    desc_lower = (description or "").lower()

    # Large scale signals
    large_signals = [
        r"\b[1-9]\d{3,}\+?\s*employees",     # 1000+ employees
        r"\bseries [d-z]\b",                  # Series D+
        r"\bpre.?ipo\b",
        r"\bunicorn\b",
        r"\bpublicly listed\b",
        r"\bnse\b|\bbse\b|\bnasdaq\b|\bnyse\b",  # Listed companies
    ]
    for pattern in large_signals:
        if re.search(pattern, desc_lower):
            return 25

    # Mid-size signals
    mid_signals = [
        r"\b[2-9]\d{2}\+?\s*employees",       # 200-999 employees
        r"\bseries [b-c]\b",
        r"\bgrowth.?stage\b",
    ]
    for pattern in mid_signals:
        if re.search(pattern, desc_lower):
            return 15

    # Startup signals
    startup_signals = [
        r"\bseed\b", r"\bpre.?seed\b",
        r"\bseries a\b",
        r"\bearly.?stage\b",
        r"\b[1-9]\d?\+?\s*employees\b",        # < 100 employees
    ]
    for pattern in startup_signals:
        if re.search(pattern, desc_lower):
            return 8

    return 12  # Unknown


def score_location(location: str, config: dict) -> int:
    """Score location fit. Max 25 points."""
    if not location:
        return 10  # Unknown

    loc_lower = location.lower()

    if any(x in loc_lower for x in ["bengaluru", "bangalore"]):
        return 25
    if any(x in loc_lower for x in ["delhi", "ncr", "gurugram", "gurgaon", "noida", "faridabad"]):
        return 20
    if "remote" in loc_lower:
        return 18
    if "hybrid" in loc_lower:
        return 15
    if any(x in loc_lower for x in ["mumbai", "hyderabad", "pune", "chennai", "kolkata"]):
        return 12
    if "india" in loc_lower:
        return 10
    # International
    return 5


def score_seniority(title: str, config: dict) -> int:
    """Score seniority level match. Max 20 points."""
    if not title:
        return 10

    title_lower = title.lower()

    # Exclude non-PM roles early — only applies if "product manager" isn't also in the title
    non_pm_roles = [
        "delivery manager", "project manager", "program manager",
        "scrum master", "agile coach",
        "engineering manager", "technical lead", "tech lead",
        "business analyst", "product analyst",
        "product owner",
        "account manager", "operations manager", "marketing manager",
        "release manager", "portfolio manager",
        "sdet", "software development engineer",
        "it pm", "it project", "it program",
        "general manager", "country manager",
    ]
    for excluded in non_pm_roles:
        if excluded in title_lower and "product manager" not in title_lower:
            return 2

    senior_patterns = ["senior product manager", "senior pm", "pm3", "pm-3", "pm iii", "lead product manager", "lead pm", "product lead", "staff pm", "staff product manager"]
    for p in senior_patterns:
        if p in title_lower:
            return 20

    generic_patterns = ["product manager", " pm "]
    for p in generic_patterns:
        if p in title_lower:
            return 14

    # Stretch (above target)
    stretch_patterns = ["product director", "director of product", "head of product", "vp product", "group product manager", "gpm"]
    for p in stretch_patterns:
        if p in title_lower:
            return 10

    # Too junior
    junior_patterns = ["associate product manager", "apm", "junior product manager", "junior pm"]
    for p in junior_patterns:
        if p in title_lower:
            return 4

    # Way too senior
    exec_patterns = ["chief product officer", "cpo", "vp of product", "vice president"]
    for p in exec_patterns:
        if p in title_lower:
            return 6

    # If the title has no product/pm signal at all, it's probably not a PM role
    has_product_signal = "product" in title_lower or re.search(r"\bpm\b", title_lower)
    if not has_product_signal:
        return 4  # Non-PM manager (not on exclusion list but clearly not target role)

    return 8  # Unknown PM-adjacent role


def score_industry(description: str, config: dict) -> int:
    """Score industry fit. Max 20 points."""
    if not description:
        return 10

    desc_lower = description.lower()

    primary_keywords = config["domain_preferences"]["primary_keywords"]
    secondary_keywords = config["domain_preferences"]["secondary_keywords"]

    has_primary = any(kw in desc_lower for kw in primary_keywords)
    has_secondary = any(kw in desc_lower for kw in secondary_keywords)

    if has_primary:
        return 20
    if has_secondary:
        return 18

    # SaaS / B2B
    if any(x in desc_lower for x in ["saas", "b2b", "enterprise software", "platform"]):
        return 14

    # Fintech
    if any(x in desc_lower for x in ["fintech", "finance", "banking", "payments", "lending"]):
        return 12

    # Gaming / unrelated
    if any(x in desc_lower for x in ["gaming", "game", "entertainment", "media", "fashion", "e-commerce"]):
        return 6

    return 10  # Other / not determined


def extract_salary_lpa(description: str) -> Optional[float]:
    """
    Try to extract salary in LPA from job description.
    Returns None if not found. Handles formats like:
    - "42 LPA", "42-55 LPA", "Rs 42 lakhs", "INR 42L"
    """
    if not description:
        return None

    patterns = [
        r"(\d+(?:\.\d+)?)\s*[-–to]+\s*(\d+(?:\.\d+)?)\s*lpa",     # range: 42-55 LPA
        r"(\d+(?:\.\d+)?)\s*lpa",                                    # single: 42 LPA
        r"(\d+(?:\.\d+)?)\s*[-–to]+\s*(\d+(?:\.\d+)?)\s*lakh",     # range: 42-55 lakhs
        r"(\d+(?:\.\d+)?)\s*lakh",                                   # single: 42 lakhs
        r"inr\s*(\d+(?:\.\d+)?)\s*l",                               # INR 42L
        r"rs\.?\s*(\d+(?:\.\d+)?)\s*l",                             # Rs 42L
    ]

    desc_lower = description.lower()
    for pattern in patterns:
        match = re.search(pattern, desc_lower)
        if match:
            groups = match.groups()
            # Take average if range
            values = [float(g) for g in groups if g is not None]
            return sum(values) / len(values)

    return None


def apply_salary_adjustment(score: int, description: str, config: dict) -> int:
    """Apply salary bonus/penalty based on mentioned salary."""
    salary = extract_salary_lpa(description)
    if salary is None:
        return score  # No change if not mentioned

    min_salary = config["compensation"]["minimum_salary_lpa"]
    near_min = config["scoring"]["salary_near_min_threshold"]

    if salary >= min_salary:
        return score + config["scoring"]["salary_bonus_above_min"]
    elif salary >= near_min:
        return score + config["scoring"]["salary_penalty_near_min"]  # negative
    else:
        return score + config["scoring"]["salary_penalty_below"]  # more negative


def check_dealbreakers(title: str, description: str) -> Optional[int]:
    """
    Check for deal-breaker keywords with context awareness.
    Returns override score if deal-breaker found, else None.
    """
    desc_lower = (description or "").lower()

    # "on-call" - check it's not negated ("no on-call", "not on-call")
    oncall_matches = [m.start() for m in re.finditer(r"on.?call", desc_lower)]
    for pos in oncall_matches:
        context = desc_lower[max(0, pos - 50):pos]
        if not re.search(r"\b(no|not|without|zero)\b", context):
            return 20

    # "24/7 support" in requirements context
    if re.search(r"24/7\s+support", desc_lower):
        # Check it's in requirements, not company description
        req_section = re.search(r"(requirement|responsibilit|you will|you must).{0,500}24/7", desc_lower, re.DOTALL)
        if req_section:
            return 10

    # Startup signals → not a hard block, cap at 50
    startup_hard = [r"\bpre.?seed\b", r"\bseed stage\b", r"\bfounding team\b", r"\bfirst hire\b"]
    for pattern in startup_hard:
        if re.search(pattern, desc_lower):
            return 50

    return None


def score_job(job: dict, config: dict) -> dict:
    """
    Main scoring function. Returns job dict with score and breakdown added.

    job dict expected keys: title, company, location, description, url, source, date_posted
    """
    title = job.get("title", "")
    company = job.get("company", "")
    location = job.get("location", "")
    description = job.get("description", "")

    # Check deal-breakers first
    override = check_dealbreakers(title, description)
    if override is not None:
        job["score"] = override
        job["score_breakdown"] = {"deal_breaker_override": override}
        job["score_label"] = get_label(override)
        return job

    # Component scores
    company_score = score_company(company, description, config)
    location_score = score_location(location, config)
    seniority_score = score_seniority(title, config)
    industry_score = score_industry(description, config)

    # Hard cap: non-PM roles never appear in top 25 regardless of company/location
    if seniority_score <= 4:
        job["score"] = 40
        job["score_breakdown"] = {
            "company_scale": company_score,
            "location": location_score,
            "seniority": seniority_score,
            "industry": industry_score,
            "non_pm_role_cap": 40
        }
        job["score_label"] = get_label(40)
        return job

    raw_score = company_score + location_score + seniority_score + industry_score

    # Salary adjustment
    final_score = apply_salary_adjustment(raw_score, description, config)
    final_score = max(0, min(100, final_score))

    job["score"] = final_score
    job["score_breakdown"] = {
        "company_scale": company_score,
        "location": location_score,
        "seniority": seniority_score,
        "industry": industry_score,
        "salary_adjustment": final_score - raw_score,
        "total": final_score
    }
    job["score_label"] = get_label(final_score)
    return job


def get_label(score: int) -> str:
    if score >= 85:
        return "Strong match"
    elif score >= 70:
        return "Good match"
    elif score >= 50:
        return "Possible"
    else:
        return "Poor fit"


def score_all(jobs: list, config: dict) -> list:
    """Score a list of jobs and return sorted by score descending."""
    scored = [score_job(job, config) for job in jobs]
    return sorted(scored, key=lambda j: j.get("score", 0), reverse=True)
