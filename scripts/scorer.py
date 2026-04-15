"""
scorer.py - Rule-based job scoring.
5 components (title_match + role_scope + company_signal + domain_overlap + location = 100)
plus standalone adjustments: yoe_fit, salary_adjustment, age_decay.
"""

import re
from typing import Optional


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

TIER1_COMPANIES = frozenset({
    # FAANG / global tech
    "google", "amazon", "amazoncom", "microsoft", "meta", "apple", "netflix",
    # Indian unicorns / top-tier product companies
    "flipkart", "swiggy", "zomato", "razorpay", "paytm", "phonepe", "meesho",
    "freshworks", "zoho", "cred", "groww", "zerodha", "navi", "ola",
    "urban company", "blinkit", "dunzo", "moengage", "clevertap", "slice",
    # Global product companies with India PMs
    "stripe", "atlassian", "salesforce", "hubspot", "zendesk", "datadog",
    "snowflake", "figma", "notion", "linear",
    # Healthcare / AI specific (relevant to candidate)
    "practo", "healthifyme", "1mg", "curefit",
})

TIER2_COMPANIES = frozenset({
    # Large established non-tech brands with genuine digital product orgs
    "decathlon", "ikea", "zara", "uniqlo",
    "tata", "reliance retail", "nykaa", "myntra",
    "marks and spencer", "marks & spencer",
    "walmart", "carrefour",
    "nestle", "unilever", "hindustan unilever",
    "hdfc", "icici", "axis bank", "kotak",
})

STAFFING_INDICATORS = [
    "our client", "client of ours", "confidential client", "undisclosed client",
    "hiring on behalf", "we are hiring on behalf", "on behalf of our client",
    "staffing", "placement agency", "executive search", "retained search",
]

DOMAIN_KEYWORDS = {
    "ai_ml": {
        "keywords": [
            "artificial intelligence", "machine learning", "ml platform",
            "genai", "gen ai", "generative ai", "llm", "large language model",
            "nlp", "natural language processing", "computer vision",
            "ai-powered", "ai-driven", "ai features", "model training",
            "data science", "predictive", "recommendation engine",
            "intelligent automation", "ai assistant", "copilot", "ai-native",
            "ai-first", "ai-augmented", "integrate ai", "ai integration",
            "ai to improve",
        ],
        "points": 7,
    },
    "b2b_saas": {
        "keywords": [
            "b2b saas", "b2b software", "enterprise saas", "saas product",
            "software as a service", "enterprise customers", "smb customers",
            "product-led growth", "plg", "multi-tenant", "api-first",
            "developer tools", "enterprise platform", "self-serve", "freemium",
        ],
        "points": 6,
    },
    "healthcare": {
        "keywords": [
            "healthcare", "health tech", "healthtech", "clinical",
            "patient", "medical", "hospital", "ehr", "emr",
            "telehealth", "digital health", "life sciences",
            "pharma", "health data", "care management",
        ],
        "points": 5,
    },
    "ecommerce": {
        "keywords": [
            "ecommerce", "e-commerce", "d2c", "direct to consumer", "direct-to-consumer",
            "omnichannel", "omni-channel", "shopify", "retail tech",
            "digital commerce", "online retail", "marketplace platform",
        ],
        "points": 5,
    },
}

NON_PM_ROLES = [
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


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def normalize(text: str) -> str:
    """Lowercase and strip common noise words for matching."""
    if not text:
        return ""
    text = text.lower()
    for noise in ["pvt ltd", "pvt. ltd.", "private limited", "inc.", "inc", "india",
                  "ltd", "llp", "technologies", "technology", "solutions", "services"]:
        text = text.replace(noise, "")
    return re.sub(r"[^a-z0-9 ]", "", text).strip()


def extract_min_yoe(description: str) -> Optional[int]:
    """Extract minimum years of experience from a job description."""
    if not description:
        return None
    desc_lower = description.lower()
    patterns = [
        r"(\d+)\s*\+?\s*years?\s+of\s+experience",
        r"(\d+)\s*\+\s*years?",
        r"minimum\s+(\d+)\s+years?",
        r"at\s+least\s+(\d+)\s+years?",
        r"(\d+)\s*[-–to]+\s*\d+\s+years?",
    ]
    values = []
    for pattern in patterns:
        for match in re.finditer(pattern, desc_lower):
            values.append(int(match.group(1)))
    return min(values) if values else None


def extract_salary_lpa(description: str) -> Optional[float]:
    """Extract salary in LPA from job description."""
    if not description:
        return None
    patterns = [
        r"(\d+(?:\.\d+)?)\s*[-–to]+\s*(\d+(?:\.\d+)?)\s*lpa",
        r"(\d+(?:\.\d+)?)\s*lpa",
        r"(\d+(?:\.\d+)?)\s*[-–to]+\s*(\d+(?:\.\d+)?)\s*lakh",
        r"(\d+(?:\.\d+)?)\s*lakh",
        r"inr\s*(\d+(?:\.\d+)?)\s*l",
        r"rs\.?\s*(\d+(?:\.\d+)?)\s*l",
    ]
    desc_lower = description.lower()
    for pattern in patterns:
        match = re.search(pattern, desc_lower)
        if match:
            groups = match.groups()
            values = [float(g) for g in groups if g is not None]
            return sum(values) / len(values)
    return None


# ---------------------------------------------------------------------------
# Component scorers
# ---------------------------------------------------------------------------

def score_title_match(title: str, min_yoe: Optional[int] = None) -> int:
    """
    Score title tier fit. Max 30, can be negative.
    Detection order matters — more specific patterns checked first.
    """
    if not title:
        return 10

    title_lower = title.lower()

    # 1. Non-PM exclusion list (unless "product manager" also present)
    for excluded in NON_PM_ROLES:
        if excluded in title_lower and "product manager" not in title_lower:
            return -45

    # 2. Exact target tier
    senior_patterns = [
        "senior product manager", "senior pm", "pm3", "pm-3", "pm iii",
        "lead product manager", "lead pm", "product lead",
        "staff product manager", "staff pm",
        "principal product manager", "principal pm",
    ]
    for p in senior_patterns:
        if p in title_lower:
            return 30

    # 3. Too junior — check before generic so "associate pm" doesn't match "pm"
    junior_patterns = [
        "associate product manager", "junior product manager", "junior pm",
        "product manager i", "pm1", "pm-1",
    ]
    for p in junior_patterns:
        if p in title_lower:
            return -25
    # Standalone "apm" word-boundary only (avoid matching "sapm", "capm" etc.)
    if re.search(r"\bapm\b", title_lower):
        return -25

    # 4. Way too senior / exec — check before generic
    exec_patterns = ["chief product officer", "cpo", "vp of product", "vice president of product"]
    for p in exec_patterns:
        if p in title_lower:
            return 5

    # 5. Stretch (above target but not exec)
    stretch_patterns = [
        "product director", "director of product", "head of product",
        "vp product", "group product manager", "gpm",
    ]
    for p in stretch_patterns:
        if p in title_lower:
            return 12

    # 6. Generic PM — boost to 24 if YOE squarely in sweet spot (5–8 yrs)
    if "product manager" in title_lower:
        if min_yoe is not None and 5 <= min_yoe <= 8:
            return 24
        return 18
    if re.search(r"\bpm\b", title_lower):
        if min_yoe is not None and 5 <= min_yoe <= 8:
            return 24
        return 18

    # 7. Unknown PM-adjacent
    if "product" in title_lower:
        return 8

    # 8. No PM signal at all
    return -20


def score_role_scope(description: str) -> int:
    """
    Score ownership/strategy language in the JD. Max 25, floor 0.
    Three sub-dimensions: ownership language, strategic scope signals, execution penalty.
    """
    if not description:
        return 8  # neutral — no description available

    desc_lower = description.lower()

    # Sub-dimension 1: Ownership language (max 12)
    strong_ownership = [
        "define the roadmap", "own the roadmap", "product vision", "product strategy",
        "end-to-end ownership", "own the product", "full ownership",
        "shape the direction", "drive the roadmap", "set the vision",
    ]
    moderate_ownership = [
        "roadmap", "vision", "strategy", "ownership", "own", "define", "drive",
    ]
    strong_hits = sum(1 for p in strong_ownership if p in desc_lower)
    moderate_hits = sum(1 for p in moderate_ownership if p in desc_lower)
    ownership_sub = min(8, strong_hits * 2) + min(4, moderate_hits)
    ownership_sub = min(12, ownership_sub)

    # Sub-dimension 2: Strategic scope signals (max 8, 1 pt each unique hit)
    scope_signals = [
        "cross-functional", "stakeholders", "go-to-market", "north star", "okr",
        "0 to 1", "0-to-1", "greenfield", "platform strategy", "long-term",
        "business impact", "product-market fit", "launch a new", "build from scratch",
        "multi-year", "company strategy", "executive stakeholders",
    ]
    scope_sub = min(8, sum(1 for p in scope_signals if p in desc_lower))

    # Sub-dimension 3: Execution-only penalty (-5)
    execution_penalty = 0
    if ownership_sub == 0 and scope_sub <= 1:
        execution_signals = [
            "assist", "support the product team", "user stories",
            "maintain the backlog", "groom the backlog", "work under",
            "report to the product manager",
        ]
        if any(p in desc_lower for p in execution_signals):
            execution_penalty = -5

    total = ownership_sub + scope_sub + execution_penalty
    return max(0, min(25, total))


def score_company_signal(company: str, description: str) -> int:
    """
    Score company quality. Max 20.
    Priority: staffing spam → tier 1 → description signals → unknown floor.
    """
    desc_lower = (description or "").lower()

    # 1. Staffing/recruiter spam → 4
    if any(indicator in desc_lower for indicator in STAFFING_INDICATORS):
        return 4

    # 2. Tier 1 known company → 20
    company_norm = normalize(company)
    for tier1 in TIER1_COMPANIES:
        if tier1 and tier1 in company_norm:
            return 20

    # 2b. Tier 2 — large established brand with real digital ops → 12
    for tier2 in TIER2_COMPANIES:
        if tier2 and tier2 in company_norm:
            return 12

    # 3. Quality signals from description (additive, cap 14, floor 5)
    signal_score = 0
    if re.search(r"\bseries\s+[c-z]\b", desc_lower):
        signal_score += 5
    elif re.search(r"\bseries\s+b\b", desc_lower):
        signal_score += 4
    elif re.search(r"\bseries\s+a\b", desc_lower):
        signal_score += 3
    if re.search(r"\b(ipo|publicly listed|nasdaq|nyse|bse|nse)\b", desc_lower):
        signal_score += 5
    if "unicorn" in desc_lower:
        signal_score += 4
    if re.search(r"\b(backed by|funded by)\b", desc_lower):
        signal_score += 2
    if re.search(r"\b(fortune 500|5000\+\s*employees|10,?000\+\s*employees)\b", desc_lower):
        signal_score += 3
    if any(x in desc_lower for x in ["saas", "b2b software", "enterprise software"]):
        signal_score += 2
    if any(x in desc_lower for x in ["ai-native", "ai-first"]):
        signal_score += 2

    return max(5, min(14, signal_score))


def score_domain_overlap(description: str) -> int:
    """
    Score match to candidate's proven domains. Max 15.
    Domains: AI/ML (7pts), B2B SaaS (6pts), Healthcare (5pts).
    """
    if not description:
        return 0

    desc_lower = description.lower()
    total = 0
    for domain_config in DOMAIN_KEYWORDS.values():
        if any(kw in desc_lower for kw in domain_config["keywords"]):
            total += domain_config["points"]

    return min(15, total)


def score_location(location: str, config: dict) -> int:
    """Score location fit. Max 10. Location is no bar."""
    if not location:
        return 8

    loc_lower = location.lower()

    if "india" in loc_lower or any(x in loc_lower for x in [
        "bengaluru", "bangalore", "delhi", "ncr", "gurugram", "gurgaon", "noida",
        "mumbai", "hyderabad", "pune", "chennai", "kolkata", "faridabad",
    ]):
        return 10
    if "remote" in loc_lower:
        return 10
    if "hybrid" in loc_lower:
        return 9
    return 8  # International in-office / unknown


def score_yoe_fit(description: str) -> int:
    """
    YOE fit adjustment (negative or zero). Sweet spot is 5-8 years.
    """
    min_yoe = extract_min_yoe(description)
    if min_yoe is None:
        return 0
    if min_yoe <= 3:
        return -15
    if min_yoe == 4:
        return -8
    if min_yoe <= 8:
        return 0   # sweet spot: 5-8 years
    if min_yoe <= 11:
        return -5
    return -10     # 12+ years: overqualification signal


def apply_salary_adjustment(score: int, description: str, config: dict) -> int:
    """Apply salary bonus/penalty based on mentioned salary."""
    salary = extract_salary_lpa(description)
    if salary is None:
        return score
    min_salary = config["compensation"]["minimum_salary_lpa"]
    if salary >= min_salary:
        return score + config["scoring"]["salary_bonus_above_min"]
    else:
        return score + config["scoring"]["salary_penalty_below"]


# US state abbreviations (all 50 + DC)
_US_STATES_RE = re.compile(
    r",\s*(?:AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT"
    r"|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY|DC)\b"
)


def _is_us_onsite_no_visa(location: str, description: str) -> bool:
    """True if job is US-only on-site with no visa sponsorship mentioned."""
    loc_lower = (location or "").lower()
    desc_lower = (description or "").lower()

    # Must be a US location
    is_us = bool(_US_STATES_RE.search(location or "")) or "united states" in loc_lower
    if not is_us:
        return False

    # Exempt if remote or hybrid (check both location field and description)
    remote_signals = ("remote", "hybrid", "work from home", "wfh")
    if any(s in loc_lower for s in remote_signals):
        return False
    if any(s in desc_lower for s in remote_signals):
        return False

    # Exempt if visa sponsorship is explicitly offered
    visa_signals = (
        "visa sponsorship", "work authorization", "work visa",
        "h-1b", "h1b", "immigration support", "relocation assistance",
        "will sponsor", "we sponsor",
    )
    if any(s in desc_lower for s in visa_signals):
        return False

    return True


def check_dealbreakers(title: str, description: str, location: str = "") -> Optional[int]:
    """
    Check for deal-breaker keywords. Returns override score or None.
    If an override is returned, all component scoring is skipped.
    """
    desc_lower = (description or "").lower()

    # US on-site with no visa sponsorship — hard disqualify
    if _is_us_onsite_no_visa(location, description):
        return 0

    # "on-call" — context-aware, ignore if negated
    for pos in [m.start() for m in re.finditer(r"on.?call", desc_lower)]:
        context = desc_lower[max(0, pos - 50):pos]
        if not re.search(r"\b(no|not|without|zero)\b", context):
            return 20

    # "24/7 support" in requirements context
    if re.search(r"24/7\s+support", desc_lower):
        if re.search(r"(requirement|responsibilit|you will|you must).{0,500}24/7", desc_lower, re.DOTALL):
            return 10

    # Very early stage startup signals
    for pattern in [r"\bpre.?seed\b", r"\bseed stage\b", r"\bfounding team\b", r"\bfirst hire\b"]:
        if re.search(pattern, desc_lower):
            return 50

    return None


# ---------------------------------------------------------------------------
# Main scoring entry point
# ---------------------------------------------------------------------------

def score_job(job: dict, config: dict) -> dict:
    """
    Score a job. Returns job dict with score, score_breakdown, score_label added.
    """
    title = job.get("title", "")
    company = job.get("company", "")
    location = job.get("location", "")
    description = job.get("description", "")

    # Dealbreakers override all component scoring
    override = check_dealbreakers(title, description, location)
    if override is not None:
        reason = "US on-site, no visa sponsorship" if override == 0 else None
        job["score"] = override
        job["score_breakdown"] = {"deal_breaker_override": override, **({"reason": reason} if reason else {})}
        job["score_label"] = get_label(override)
        return job

    # Component scores
    min_yoe_val = extract_min_yoe(description)
    title_score = score_title_match(title, min_yoe=min_yoe_val)
    scope_score = score_role_scope(description)
    company_score = score_company_signal(company, description)
    domain_score = score_domain_overlap(description)
    location_score = score_location(location, config)

    base = title_score + scope_score + company_score + domain_score + location_score

    # Standalone adjustments
    yoe_adj = score_yoe_fit(description)
    salary_adj = apply_salary_adjustment(base + yoe_adj, description, config) - (base + yoe_adj)

    adjusted = base + yoe_adj + salary_adj

    # Age decay: -2 points/day after day 3, capped at -20
    decay = 0
    date_found = job.get("date_found", "")
    if date_found:
        from datetime import date as date_cls
        try:
            age_days = (date_cls.today() - date_cls.fromisoformat(date_found)).days
            if age_days > 3:
                decay = min((age_days - 3) * 2, 20)
        except ValueError:
            pass

    final_score = max(0, min(100, adjusted - decay))

    # Feedback-derived company adjustment (from calibrate.py overrides)
    feedback_adj = 0
    fb_overrides = config.get("feedback_overrides", {}).get("company_adjustments", {})
    if fb_overrides:
        company_norm = normalize(company)
        feedback_adj = fb_overrides.get(company_norm, 0)
        if feedback_adj:
            final_score = max(1, min(100, final_score + feedback_adj))

    job["score"] = final_score
    job["score_breakdown"] = {
        "title_match": title_score,
        "role_scope": scope_score,
        "company_signal": company_score,
        "domain_overlap": domain_score,
        "location": location_score,
        "yoe_required": min_yoe_val,
        "yoe_fit": yoe_adj,
        "salary_adjustment": salary_adj,
        "age_decay": -decay if decay else 0,
        **({"feedback_adj": feedback_adj} if feedback_adj else {}),
        "total": final_score,
    }
    job["score_label"] = get_label(final_score)
    return job


def get_label(score: int) -> str:
    if score == 0:
        return "Disqualified"
    if score >= 80:
        return "Strong match"
    elif score >= 65:
        return "Good match"
    elif score >= 45:
        return "Possible"
    else:
        return "Poor fit"


def score_all(jobs: list, config: dict) -> list:
    """Score a list of jobs and return sorted by score descending."""
    scored = [score_job(job, config) for job in jobs]
    return sorted(scored, key=lambda j: j.get("score", 0), reverse=True)
