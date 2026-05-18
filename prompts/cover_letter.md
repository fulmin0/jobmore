# Cover Letter — Workflow


## Role

Write as a PM who has done the work to understand this company's specific challenge — not a form letter. Every paragraph should contain something that could only be written for this role, not copied to another application.

---

## Inputs

1. `output/jobs/{dir}/job_intelligence.md` — pillars, story bank, notation flag
2. `output/jobs/{dir}/notes.md` — HM signals, key stories, gaps
3. `templates/cover_letter_base.tex` — copy to job directory, fill in body

Do not create before the resume content (`resume_content.md`) is reviewed and approved by the user. PDF build can proceed in parallel — LaTeX/spacing issues do not block cover letter drafting.

---

## Pre-writing — read the Job Intelligence Package

Before writing anything, confirm `output/jobs/{dir}/job_intelligence.md` exists.
- **If it exists**: read it. Use pillars, story bank, notation directly.
- **If it doesn't exist**: run `prompts/job_intelligence.md` first, then return here.

From the intelligence file:
- **Story selection**: use ranked story bank. Score ≥ 2 stories preferred. ⚠️ domain-adjacent only as fallback — flag explicitly.
- **Paragraph ordering**: primary qualification → differentiator → table stakes → close. Never order by JD reading position.
- **Notation**: apply the Convert L/crore flag.

---

## Structure — 4 paragraphs

**Paragraph 1 — Hook (3-4 sentences)**
Why this company and this role specifically. Must contain something from the HM's post, the company's stated mission, or a specific product decision they made — not generic praise. End with one sentence establishing YOUR domain fit — what you built, not what you lack.

- Good: reference a specific company challenge, recent launch, or HM signal
- Bad: "I am excited to apply for the position of..."
- Never say: "roadmap", "managed", "passionate about", "leverage synergies"
- **Hook closing rule**: The hook's final sentence names a specific experience as your entry credential. It does NOT acknowledge a domain gap — that belongs in para 2's bridge sentence. "The Senior PM role is the work I want to own next, applied to X instead of Y" is a gap statement masquerading as a strength statement — cut it.

**Paragraph 2 — Primary credential (4-5 sentences)**
The story that directly addresses the differentiator pillar. Tell it as a problem → action → outcome narrative. Include one concrete metric. This should be the hardest-to-substitute experience — the thing that makes you the specific right person, not just a qualified PM.

- Use the top-ranked domain-correct story from the story bank
- Depth over breadth — one story told well beats three stories listed
- **Domain gap rule**: When the top-ranked story is ⚠️ domain-adjacent (not exact domain match), add one bridge sentence explicitly connecting the domains: "The vertical is different; the underlying problem — [X] — is identical." Do not present an adjacent-domain story as if it IS the target domain.
- **Bonus-explicit pillars**: If `job_intelligence.md` flags a `⭐ bonus-explicit` pillar, weave it into this paragraph or paragraph 3 — at minimum one clause. Never omit an explicitly-named JD bonus entirely.

**Paragraph 3 — Supporting credential (3-4 sentences)**
A second story addressing either another differentiator pillar or a table-stakes pillar that hasn't been covered. Can be shorter. Must have a metric or a named outcome.

- Use the second-ranked story from the story bank
- If the role has two differentiators, use both paras 2 and 3 for them; push table stakes to the opener or close
- **One story only**: paragraph 3 covers exactly one story. Never stack two stories in the same paragraph — each gets its own paragraph or is cut. This is a hard rule, not a style preference.

**Paragraph 4 — Close (2-3 sentences)**
Simple, direct. State what you'd bring specifically. No performative enthusiasm. End with the ask.

- Good: "I'd bring [specific thing] to [specific problem]. I would appreciate the opportunity to discuss."
- Bad: "I look forward to hearing from you and am excited about the possibility of joining your team."

---

## Anti-patterns

| Don't | Do instead |
|-------|-----------|
| "managed a roadmap" | "shipped", "built", "diagnosed", "unblocked" |
| Generic hook ("I am excited to apply") | Specific company signal from HM post or product |
| Three stories in one paragraph | One story per paragraph, told in full |
| Metrics without context | Metric + what it meant for the business |
| Repeating the resume | Resume lists; cover letter explains the why and the how |
| More than 4 paragraphs | 4 paragraphs max — editors cut from the bottom |
| "I would be a great fit because..." | Show, don't claim |

---

## Output

1. Copy `templates/cover_letter_base.tex` to `output/jobs/{dir}/cover_letter.tex`
2. Fill in the body paragraphs — placeholder personal info (`Your Name`, etc.) stays until the user injects personal details
3. Compile: `tectonic output/jobs/{dir}/cover_letter.tex`
4. Present to the user for review before considering done

**Close-out**: After producing the cover letter, append a version block to `output/jobs/{dir}/iterations.md` describing what changed. Remind the user: write feedback below the `---` line, then type `/revise` to proceed or `/approve` when satisfied.
