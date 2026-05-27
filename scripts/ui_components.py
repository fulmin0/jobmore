"""
ui_components.py — HTML card renderers for the jobmore board page.
Returns raw HTML strings; no Streamlit calls.
"""

from html import escape


def _e(s: object) -> str:
    return escape(str(s))


_GEAR_SVG = (
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
    '<circle cx="12" cy="12" r="3"/>'
    '<path d="M19.4 15a1.7 1.7 0 0 0 .34 1.87l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06'
    'a1.7 1.7 0 0 0-1.87-.34 1.7 1.7 0 0 0-1.03 1.55V21a2 2 0 1 1-4 0v-.09'
    'a1.7 1.7 0 0 0-1.11-1.55 1.7 1.7 0 0 0-1.87.34l-.06.06a2 2 0 1 1-2.83-2.83'
    'l.06-.06A1.7 1.7 0 0 0 4.6 15a1.7 1.7 0 0 0-1.55-1.03H3a2 2 0 1 1 0-4h.09'
    'A1.7 1.7 0 0 0 4.6 8.91a1.7 1.7 0 0 0-.34-1.87l-.06-.06a2 2 0 1 1 2.83-2.83'
    'l.06.06a1.7 1.7 0 0 0 1.87.34H9a1.7 1.7 0 0 0 1.03-1.55V3a2 2 0 1 1 4 0v.09'
    'c0 .68.4 1.3 1.03 1.55a1.7 1.7 0 0 0 1.87-.34l.06-.06a2 2 0 1 1 2.83 2.83'
    'l-.06.06a1.7 1.7 0 0 0-.34 1.87V9c.25.63.87 1.03 1.55 1.03H21a2 2 0 1 1 0 4'
    'h-.09a1.7 1.7 0 0 0-1.55 1.03Z"/>'
    '</svg>'
)

_COL_SUBTITLES = {
    "Discover": "new",
    "Shortlist": "prepping",
    "Referral": "jobs",
    "Applied": "in flight",
    "Interview": "active",
}

_COL_MARKS = {
    "Shortlist": "accent",
    "Referral": "accent",
    "Applied": "accent",
    "Interview": "green",
}


def render_goal(g: dict) -> str:
    tone = f" goal--{g['tone']}" if g.get("tone") else ""
    target = g["target"]
    done = g["done"]
    pct = min(100, round(done / target * 100)) if target > 0 else (100 if done > 0 else 0)
    return (
        f'<div class="goal{tone}">'
        f'<div class="goal-line">'
        f'<span class="goal-label">{_e(g["label"])}</span>'
        f'<span class="goal-num tabular">{done}<span class="of">/{target}</span></span>'
        f'</div>'
        f'<div class="goal-bar"><i style="width:{pct}%"></i></div>'
        f'</div>'
    )


def render_topbar(goals: list) -> str:
    goals_html = "".join(render_goal(g) for g in goals)
    return (
        '<div class="topbar">'
        '<span class="brand">jobmore</span>'
        f'<div class="goals">{goals_html}</div>'
        '<div class="actions">'
        '<button class="btn btn--ghost btn--small">+ Add job</button>'
        f'<button class="icon-btn" aria-label="settings">{_GEAR_SVG}</button>'
        '</div>'
        '</div>'
    )


def render_strip(strip_items: list) -> str:
    if not strip_items:
        return ""
    items_html = "".join(
        f'<span class="strip-item{"  overdue" if s.get("overdue") else ""}">{_e(s["text"])}</span>'
        for s in strip_items
    )
    return (
        '<div class="strip">'
        '<span class="strip-label">Due today</span>'
        f'<span class="strip-count tabular">{len(strip_items)}</span>'
        f'<div class="strip-items">{items_html}</div>'
        '</div>'
    )


def render_col_header(title: str, count: int) -> str:
    mark = _COL_MARKS.get(title)
    mark_html = f'<span class="col-mark col-mark--{_e(mark)}"></span>' if mark else ""
    subtitle = f"{count} {_COL_SUBTITLES.get(title, '')}"
    return (
        '<div class="col-head">'
        f'<span class="col-title">{_e(title)}</span>'
        f'<span class="col-count">{_e(subtitle)}</span>'
        f'{mark_html}'
        '</div>'
    )


def render_card(card: dict) -> str:
    kind = card["kind"]
    score = card.get("score", 0)
    hi = " score--hi" if score >= 85 else ""
    score_html = f'<span class="score{hi}">{score}</span>' if kind == "discover" else ""

    head = (
        '<div class="card-head">'
        '<div class="card-name">'
        f'<div class="card-co">{_e(card["co"])}</div>'
        f'<div class="card-title">{_e(card["title"])}</div>'
        '</div>'
        f'{score_html}'
        '</div>'
    )
    meta = f'<div class="card-meta">{_e(card["loc"])}<span class="sep">·</span>{_e(card["rem"])}</div>'

    if kind == "discover":
        body = (
            '<div class="card-quick">'
            '<span class="btn btn--ghost btn--small">skip</span>'
            '<span class="btn btn--primary btn--small">+ shortlist</span>'
            '</div>'
        )
    elif kind == "shortlist":
        materials = card.get("materials")
        mat = f"{materials}/4" if materials is not None else "—"
        stale = (
            f'<span class="dot dot--red"></span>'
            f'<span class="note">{card["days_stale"]}d no update</span>'
        ) if card.get("is_stale") else ""
        body = (
            '<div class="card-status">'
            f'<span class="materials-text"><span class="num">{_e(mat)}</span> materials ready</span>'
            f'{stale}'
            '</div>'
        )
    elif kind == "referral":
        if card.get("is_overdue"):
            tone, dot_cls = "is-overdue", "dot--red"
            inner = f'<span><span class="label">{card["days_overdue"]}d overdue</span> · remind {_e(card["contact"])}</span>'
        elif card.get("sub") == "submitted":
            tone, dot_cls = "is-due", "dot--accent"
            inner = f'<span><span class="label">submitted</span> · {_e(card["contact"])}</span>'
        else:
            tone, dot_cls = "is-due", "dot--accent"
            inner = f'<span>via {_e(card["contact"])}</span>'
        body = f'<div class="card-status {tone}"><span class="dot {dot_cls}"></span>{inner}</div>'
    elif kind == "applied":
        sub = card.get("sub", "applied")
        if sub == "screen":
            recruiter = card.get("recruiter") or "recruiter"
            status_inner = f'<span class="note">screen w/ {_e(recruiter)}</span>'
        else:
            status_inner = f'<span class="note">{_e(card["since"])}</span>'
        fo = card.get("fo_up")
        fo_html = ""
        if fo:
            t = "is-overdue" if fo["urgent"] else "is-due"
            d = "dot--red" if fo["urgent"] else "dot--accent"
            fo_html = (
                f'<div class="card-status {t}">'
                f'<span class="dot {d}"></span>'
                f'<span>{_e(fo["label"])}</span>'
                '</div>'
            )
        body = f'<div class="card-status">{status_inner}</div>{fo_html}'
    elif kind == "interview":
        rounds = card.get("rounds", ["next"])
        dots = ""
        for r in rounds:
            if r == "done":
                dots += '<span class="round-dot round-dot--done"></span>'
            elif r == "next":
                dots += '<span class="round-dot round-dot--next"></span>'
            else:
                dots += '<span class="round-dot"></span>'
        body = (
            '<div class="card-status is-prep">'
            f'<span class="rounds">{dots}</span>'
            f'<span class="label">{_e(card.get("next_label", "Interview in progress"))}</span>'
            '</div>'
        )
    else:
        body = ""

    return f'<div class="card" tabindex="0">{head}{meta}{body}</div>'
