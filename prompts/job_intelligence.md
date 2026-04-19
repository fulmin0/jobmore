# Job Intelligence — Shared Front-End

Run this **once per job** before generating any artifact (elevator pitch, resume, cover letter). Write the output to `output/jobs/{dir}/job_intelligence.md`. All artifact prompts read this file instead of re-deriving the analysis.

---

## Inputs

1. Full JD — read from `data/jobs_found.json` for this job
2. All experience files — read all `data/experience/*.md`
3. Job notes — read `output/jobs/{dir}/notes.md` for HM signals if they exist

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

---

## Step 4 — Global notation

Is the company headquartered outside India, or does the JD signal a global audience?
- If yes: convert Indian shorthand in all artifact content. L → K (8L → 800K), crore → M (₹3.45 crore → ₹34.5M). ₹ symbol is fine.
- If no (India-based hire): Indian notation acceptable.

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
