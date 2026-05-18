# Job Intelligence — Shared Front-End

Run this **once per job** before generating any artifact (elevator pitch, resume, cover letter). Write the output to `output/jobs/{dir}/job_intelligence.md`. All artifact prompts read this file instead of re-deriving the analysis.

---

## Inputs

1. Full JD — read from `data/jobs_found.json` for this job
2. All experience files — read all `data/experience/*.md`
3. Job notes — read `output/jobs/{dir}/notes.md` for HM signals if they exist
4. Master story bank — read `data/story_bank.md` if it exists. Extract all `### ` headings into a dedup registry (list of story names already banked). If file does not exist, treat as empty.

---

## Step 1 — Extract JD pillars

Read the full JD. Extract the top 4 requirements across these categories:
- **Domain**: the industry or product category (e.g. healthcare SaaS, B2B fintech, PLG SaaS)
- **Experience type**: what kind of PM work (e.g. 0-to-1, platform, growth, AI/ML)
- **Platform type**: specific technology or channel (e.g. mobile, WhatsApp, marketplace)
- **Specific capability**: a named skill or methodology (e.g. risk modelling, conversational AI, RFID)

---

## Step 2 — Classify each pillar

For every pillar, label it:

**Differentiator** — what makes this role distinct from a generic senior PM role at any company. Signals: dedicated JD section, unusual requirement, non-obvious capability. This is what they can't hire a commodity PM for.

**Table stakes** — what every senior PM is expected to have: retention, data-driven decisions, stakeholder management, execution, cross-functional alignment. Present in every JD regardless of role.

**Primary qualification** — the baseline that gets you considered at all (years of experience, domain, seniority).

---

## Step 3 — Build the story bank

Read all files in `data/experience/`. For each distinct story or experience, record:

1. **Pillars covered** — which of the job's pillars does this story address?
2. **Domain match** — does this story's domain match the JD's domain-specific requirement?
   - ✅ = exact domain match (healthcare story for healthcare JD)
   - ⚠️ = adjacent domain (SaaS story for healthcare SaaS JD — covers SaaS but not healthcare)
   - ❌ = domain mismatch (D2C e-commerce for healthcare JD)
3. **Multi-pillar score** — count of domain-correct pillars covered (domain mismatches score 0 for domain-specific pillars)

**Domain correctness rule**: A domain-specific pillar (e.g. "healthcare SaaS") must be satisfied by a domain-correct story. A proxy domain (D2C SaaS for healthcare SaaS) scores ⚠️ and should only be used if no domain-correct alternative exists — flag it explicitly.

**Ranking**: Sort stories by multi-pillar score descending. Ties broken by: differentiator pillar coverage > table-stakes pillar coverage.

**Explicitly-named bonus pillars**: If the JD names a capability as "bonus" or "nice to have" but calls it out explicitly (e.g., "Bonus points for AI/ML experience"), flag it in the story bank as `⭐ bonus-explicit`. Artifact prompts must cover it with at least one story even if score = 1 — an explicitly-named bonus is a differentiator signal, not table stakes to deprioritize.

---

## Step 4 — Global notation

Is the company headquartered outside India, or does the JD signal a global audience?
- If yes: convert Indian shorthand in all artifact content. L → K (8L → 800K), crore → M (₹3.45 crore → ₹34.5M). ₹ symbol is fine.
- If no (India-based hire): Indian notation acceptable.

---

## Step 5 — Gap + Mitigation Analysis

Scan the JD Pillars table for any pillar where no story has ✅ domain match. These are gaps.

**Pillars where the best story is ⚠️ are not gaps** — note the reframe opportunity in the output but do not classify as a gap.

For each gap pillar:

**Severity**:
- Critical — pillar is Differentiator
- Moderate — pillar is Primary qualification
- Minor — pillar is Table stakes

**Adjacent availability**: Find the highest-scoring ⚠️ story for this pillar. If none exists (all ❌), note "No adjacent coverage."

**Mitigation selection**:

| Situation | Mitigation |
|-----------|-----------|
| Critical, ⚠️ available | Reframe (write exact bridging language) + Cover letter callout |
| Critical, ❌ only | Don't apply (unless HM notes.md signals flexibility) |
| Moderate, ⚠️ available | Reframe (write exact bridging language) |
| Moderate, ❌ only | Cover letter callout |
| Minor, any | Resume omit safely |

**Reframe rule**: Do not write generic advice. Write the specific sentence to use. Example: for a prescription adherence story covering a purchase completion pillar → "use 'drove purchase completion from 40% to 82% via AI-triggered follow-up' — the underlying behavior is identical, only the vocabulary shifts." Use CLAUDE.md domain translation rules (prescription adherence → purchase completion, MRR → platform GMV, etc.).

**Cover letter callout rule**: Write a 1-2 sentence template. Example: "I haven't worked directly in background verification, but the risk scoring framework I built for Apollo Health Insurance — inferring clinical risk from 15 years of longitudinal data — uses the same underwriting logic."

**Don't apply rule**: Only trigger when Critical pillar has ❌ only AND notes.md has no HM signals overriding. State: "Pillar '{X}' is a Differentiator with no ✅ or ⚠️ coverage. Recommend not applying unless HM signals flexibility."

If all pillars have ✅ coverage, write: "No gaps — all pillars have domain-correct coverage."

---

## Step 6 — Story Bank Update

For each story in the ranked story bank table where Score ≥ 2:

1. Check the dedup registry from Input 4.
   - **Name found** → update `**Last used**` to today. Also check if new pillar tags from this job should be unioned into the existing `**Pillars**` field — append any new ones, never overwrite.
   - **Name not found** → draft a new STAR+R entry and append to `data/story_bank.md`.

**STAR+R drafting rules**:
- **S**: 1-2 sentences. Name the company, product, user problem. No jargon.
- **T**: What you personally owned. Start with "I owned…" or "I was responsible for…"
- **A**: 2-3 bullets. Concrete decisions made. Include one non-obvious action (the insight that drove the result).
- **R**: Lead with the metric. Source from `## Additional Context` in the experience file where a verified figure exists. Apply notation rule from Step 4.
- **Reflection**: One specific sentence — what you'd do differently OR what this taught you. Not "I learned the importance of X" — name the specific thing.
- **Pillars**: All pillar tags this story has ever covered across jobs (union, additive).
- **Source**: The `data/experience/` filename (e.g., `pm_apollo247.md`).
- **Last used**: Today's date, YYYY-MM-DD.

**Story name normalization**: Use the initiative label from the experience file (e.g., "GenAI PoS recommendation engine"), not JD-specific rewording. Consistent naming is how dedup works across jobs.

**If `data/story_bank.md` does not exist**: create it with this header before the first entry:
```
# Story Bank

Stories scoring ≥ 2 on at least one job. Dedup key = story name. Use **Last used** for manual pruning.

---
```

Stories scoring < 2 are never added to the master bank.

---

## Output format

Write to `output/jobs/{dir}/job_intelligence.md`:

```markdown
# Job Intelligence — {Company}, {Title}

Generated: {date}

---

## JD Pillars

| Pillar | Type | Domain requirement |
|--------|------|--------------------|
| {e.g. Healthcare SaaS} | Primary qualification | Healthcare domain |
| {e.g. AI/GenAI} | Differentiator | Any |
| {e.g. PLG / growth loops} | Differentiator | Any |
| {e.g. Engagement & retention} | Table stakes | Any |

---

## Story bank

| Story | Role | Pillars covered | Domain | Score |
|-------|------|----------------|--------|-------|
| {e.g. WhatsApp AI chatbot} | Apollo 247 | AI + retention | ✅ healthcare | 2 |
| {e.g. GenAI PoS engine} | Apollo 247 | AI + GMV | ✅ healthcare | 2 |
| {e.g. Doctor App NPS} | Apollo 247 | Healthcare SaaS | ✅ healthcare | 1 |
| {e.g. BoB platform} | BoB | SaaS + enterprise | ⚠️ D2C not healthcare | 0* |

*⚠️ = domain mismatch for a domain-specific pillar. Use only if no domain-correct alternative exists.

---

## Notation

- Company locale: {e.g. Global HQ / India hire}
- Convert L/crore: {Yes / No}
- Notes: {any specific conversion flags}

---

## Gap Analysis

*(No gaps — all pillars have domain-correct coverage.)*

*(Replace the line above with the table below when gaps exist:)*

| Pillar | Severity | Best adjacent | Mitigation |
|--------|----------|---------------|------------|
| {pillar} | Critical / Moderate / Minor | {story name or "None"} | Reframe / Callout / Don't apply / Omit safely |

### Gap details
**{Pillar name}** (Severity: Critical)
- Adjacent: {story name} — reframe as: "{exact sentence}"
- Cover letter callout: "{1-2 sentence template}"

---

## Story bank updates

- Added: {Story Name}, {Story Name}
- Updated Last used: {Story Name} → {date}
- Skipped (score < 2): {Story Name}

---

## Content iterations

### Elevator pitch
*(log versions here as they happen)*

### Resume
*(log versions here as they happen)*

### Cover letter
*(log versions here as they happen)*
```

---

## When to re-run

Re-run (overwrite the output file) if:
- The JD changes
- New experience files are added to `data/experience/`
- HM signals are added to notes.md that change the pillar priority

Do NOT re-run just because an artifact was rejected — log the correction to `## Content iterations` instead and update the relevant prompts file.

Re-running is safe: Step 6 checks `data/story_bank.md` by heading name before appending. Existing entries are never re-drafted; only `**Last used**` and `**Pillars**` are updated.
