# Elevator Pitch — Workflow


## Role

Write as a PM who is genuinely interested in this specific company. Not a form message. Not a pitch deck. A person who read the HM's post and has a real point of view.

---

## Inputs

Read `output/jobs/{dir}/notes.md`. Use **only**:
- **HM signals** — what the HM said they're looking for, phrases they used, things they care about
- **Key stories** — the specific experiences that map to their stated problem
- **Gaps** — honest framing of what's missing, if relevant to the opener

If no direct message from HM exists in notes.md, use the Job Description as the signal source.

Do **not** use:
- The "Message to HM" section — that's a raw user draft, not the source of truth
- Generic claims not tied to a specific HM signal or story

---

## Pre-writing — read the Job Intelligence Package

Before writing anything, check if `output/jobs/{dir}/job_intelligence.md` exists.
- **If it exists**: read it. Use the pillars table, story bank rankings, and notation flag directly. Do not re-derive.
- **If it doesn't exist**: run `prompts/job_intelligence.md` first to generate it, then return here.

From the intelligence file, apply:
- **Story selection**: pick from the ranked story bank. Prefer score ≥ 2 (multi-pillar). Use ⚠️ domain-adjacent stories only when no domain-correct alternative covers the pillar — flag it explicitly.
- **Bullet ordering**: Bullet 1 = primary qualification → Bullet 2 = differentiator → Bullet 3 = table stakes. Never order by JD reading position.
- **Notation**: apply the Convert L/crore flag.

**After approval — log to `## Content iterations` in `job_intelligence.md`**: record each version and the rejection reason. If corrections were needed, identify the rule gap and update this prompts file before closing.

---

## Format

**File header** (always):
```
**Channel:** LinkedIn InMail / DM
**Role:** {exact role title from notes.md}
```

The message has 3 parts:

**1. Opener** — 2 sentences:

   a) Address by first name, state the role. No preamble.
   - Good: `Hi Ganesh, I'm reaching out for the Omni Commerce PM role.`
   - Bad: `Hi, I hope this message finds you well. I came across your post about...`

   b) One sentence naming the exact experience that maps to their problem. Use scale and specificity wherever possible.
   - Good: `I have built phygital products used by over 4.2 crore users over the last 7 years of my product journey.`
   - Bad: `I have extensive experience in phygital and omnichannel product management across multiple domains.`

**2. Main Content** — 3 bullets, ordered per Step 5 above. Each ties a specific experience to a JD signal. Include impact metrics where real.

**3. Closing** — Simple, direct. No performative enthusiasm.
   - Good: `I would appreciate to be considered for the role.`
   - Sign off: `Best, {name}`

---

## Anti-patterns

| Don't | Do instead |
|-------|-----------|
| "managed a roadmap" | "shipped", "built", "diagnosed", "unblocked" |
| Generic opening | First name + role, direct |
| 4+ paragraphs | 2-sentence opener + 3 bullets + 1-line close |
| "I have X years of experience in Y" | Name the specific thing you shipped and its impact |
| Vague ask ("happy to connect") | "I would appreciate to be considered for the role." |
| Opener that reads like a resume summary (3 nouns listed) | One concrete sentence with a single strong claim |
| Single-pillar bullet when a multi-pillar alternative exists | Pick the story that covers 2+ JD requirements at once |
| Proxy domain satisfying a domain-specific requirement | Match domain precisely; flag if no match exists |
| Ordering bullets by JD reading order | Order by: primary qual → differentiator → table stakes |

---

## Canonical example — 0032 Decathlon

**Pre-writing checklist applied:**
- Pillars: phygital/omnichannel (domain), No-Bug culture (differentiator — named explicitly in post), store ops credibility (differentiator — HM explicitly wants active sportsperson with store DNA), Circular Commerce (table stakes for this role)
- Differentiators: No-Bug culture + store ops (both named explicitly by HM)
- Multi-pillar check: WhatsApp bot covers phygital + retention (2 pillars); Doctor App covers No-Bug culture + NPS discipline (2 pillars); father's supermarket covers store ops credibility (unique, irreplaceable)
- Order: pharma pipeline (primary phygital qual) → Doctor App (No-Bug differentiator) → store ops (culture differentiator)

**Output:**
```
Hi Ganesh, I'm reaching out for the Omni Commerce PM role. I have built phygital products used by over 4.2 crore users over the last 7 years of my product journey.

• Built the growth pipeline from 3k+ Apollo Pharmacies to digital, increasing retention by ₹8M MoM
• Owned Doctor platform, 5k+ doctors across 55+ Apollo hospitals. Increased NPS from <10 to 74 in 4 months — zero tolerance for bugs in patient journey from appointment to getting prescription.
• Store ops in my DNA — set up my father's supermarket from scratch: POS setup, taking inventory, doing sales, accounting.

I would appreciate to be considered for the role.

Best,
Archit
```

---

## Output

Write to `output/jobs/{dir}/elevator_pitch.md`. Use the file header format above. Present to the user for review before considering it done.
