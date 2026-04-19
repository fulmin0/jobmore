# Jobmore — Project Instructions

## What this is
Job search pipeline: discovery (scraping + scoring), pipeline tracking (Streamlit), and resume content generation (conversational).

## File conventions

| Path | Purpose |
|------|---------|
| `data/jobs_found.json` | Single source of truth for all jobs (schema in MEMORY.md) |
| `data/experience/{company}_{role}.md` | One file per role — lines 1-4: company/role/start/end, line 5+: detailed bullets. Enrichment appended under `## Additional Context` |
| `data/resumes/{date}.pdf` | Resume snapshots (e.g. `20260409.pdf`) |
| `output/jobs/{id:04d}_{Company}_{Title}/resume_content.md` | Generated resume content per target job |
| `output/jobs/{id:04d}_{Company}_{Title}/resume.tex` | Injected LaTeX file for this job |
| `output/jobs/{id:04d}_{Company}_{Title}/{pdf_name}.pdf` | Compiled PDF for this job (`pdf_name` from config.json `personal.pdf_name`) |
| `output/jobs/{id:04d}_{Company}_{Title}/notes.md` | HM signals, key stories, gaps, interview prep — source of truth; `pipeline.notes` in JSON is a 120-char truncated summary |
| `output/jobs/{id:04d}_{Company}_{Title}/cover_letter.tex` | LaTeX cover letter; compiled to `cover_letter.pdf` via Tectonic using `templates/cover_letter_base.tex` |
| `output/jobs/{id:04d}_{Company}_{Title}/elevator_pitch.md` | LinkedIn DM / InMail pitch to HM — ~4 short paragraphs, plain prose |
| `output/jobs/applied/{id:04d}_{Company}_{Title}/` | Same structure; folder auto-moved here when status transitions to `applied` |
| `output/ready/{pdf_name}.pdf` | Latest built resume — always the "send this" copy |
| `templates/resume_base.tex` | Master LaTeX template (copy from Overleaf, add INJECT markers) |
| `templates/cover_letter_base.tex` | Master LaTeX cover letter template — copy to job directory, fill in body |
| `config.json` | Local config — **not committed**. Contains a `personal` section with name/email/phone/LinkedIn/pdf_name. **Do not read or log the `personal` fields** — they are injected automatically by `build_resume.py` at compile time. |
| `prompts/` | Workflow templates loaded on demand |

## Trigger rules

- **Resume content (tailoring)**: When the user asks to create resume content, tailor a resume, or target a pipeline job — read `prompts/resume_content.md` for the full workflow before proceeding. Core flow:
  1. Run `python3 scripts/build_resume.py --list-keys --job "Company::Title"` to see marker keys and baseline bullet counts per role
  2. Read `templates/resume_base.tex` — this is the baseline (not the PDF). The `%%PERSONAL_*%%` placeholders in the header are substituted at build time from config.json — treat them as opaque tokens, do not try to fill them in.
  3. Score every baseline bullet against the JD → tag each `KEEP` / `REFRAME` / `REPLACE`
  4. Produce merged final set per role: **same bullet count as baseline, every role present**
  5. Write `output/jobs/{Company}_{Title}/resume_content.md` with a `## Resume-Ready Bullets` section
  6. Talking points go in the working doc below (not in Resume-Ready)
  - **Raw LaTeX passthrough**: bullets containing `\` are injected verbatim by the build script. Use this to preserve `\href{...}{...}` on KEEP bullets when the link strengthens the candidate. Strip to plain text when the link is noise.
  - **Hard rules**: never skip a role, never exceed the baseline bullet count per role, always use ≤150 chars per bullet
  - **JD alignment audit**: When scoring bullets, map each to specific JD pillars or HM signals — not just a generic /5 score. Every major JD pillar should be addressable from at least one bullet. If a pillar has zero coverage, flag it.
  - **Unique signal check**: Before dropping a bullet, verify it's not the only source of a JD signal. Example: if only one bullet covers "No-Bug culture" and the JD explicitly requires it, dropping that bullet creates a gap that no other bullet fills — even if other bullets score higher individually.
  - **Dropped bullets → talking points**: When a bullet is replaced, move the original story to the talking points section with context on when to use it in interviews. These are still valuable — just not the best fit for the resume line budget.
  - **Summary style**: Lead with capabilities (what was built: "AI-powered ordering, retail PoS recommendations"), not company names ("Apollo Pharmacy Retail, Apollo 247") — unless the target HM would immediately recognize the companies. The summary is the HM's first scan; JD keywords matter more than employer brands.
  - **Domain translation for cross-industry targeting**: When the user's experience is in one domain (healthcare, SaaS) but the target JD is another (retail, e-commerce), translate metrics to the target domain's vocabulary while keeping the underlying truth intact. Examples: "prescription adherence" → "purchase completion" or "subscriber retention"; "risk exposure" → "portfolio value"; "MRR" → "platform GMV" (only when the metric genuinely maps). SaaS metrics (MRR, churn) are fine when the role IS SaaS — only translate when the target domain uses different terms for the same behavior.
  - **Conversion metric framing**: When absolute percentage changes look small (e.g., 2.5%→3%), consider relative framing ("20% conversion uplift") or lead with the GMV impact and put conversion as supporting detail. Let the user choose — present both options.
  - **Phygital/omnichannel prefix tags**: For JDs emphasizing phygital or omnichannel, add bold directional prefixes to bullets that show the physical↔digital bridge (e.g., `\textbf{Store→Digital:}`, `\textbf{In-store AI:}`, `\textbf{Digital→Store:}`). Makes the story scannable for an HM. Use `\textbf{}` for these — markdown `**` doesn't work in LaTeX injection.
  - **System design prep**: For jobs requiring system design skills, create `output/jobs/{Company}_{Title}/system_design_prep.md` with 2 paragraphs per relevant experience point — the design challenge, patterns to know, and how it maps to the target company's problems. This is interview prep, not resume content.
  - **User phrasing**: Present multiple options for bullet wording — never unilaterally rewrite the user's text. The user decides exact wording. When proposing changes, describe the direction and why, then draft options.
- **Resume build**: When the user asks to build the PDF, compile the resume, or run build_resume — run `source venv/bin/activate && python3 scripts/build_resume.py --job "Company::Title"`. Requires `templates/resume_base.tex` with INJECT markers. First-time setup: `brew install tectonic && pip install pypdf`. The script parses the content file, injects into the template, compiles via Tectonic, and runs an interactive pruning loop if the PDF exceeds one page.
  - **Text-block inject keys**: `summary`, `skills`, `bob_subheading`, `apollo_subheading`, `mouve_title` inject a single line of text rather than a bullet list. Subheading values in the content file must be raw LaTeX (include `\textbf{}`, `\hfill{year}`, trailing `\\`) — the raw-passthrough rule handles them verbatim.
  - **Unicode substitution**: the build script auto-replaces `₹` → `\rupee{}`, `→` → `$\rightarrow$`, `~N` → `${\sim}$N` before injection. Write these characters naturally in the content file; do not pre-escape them. **Only these 3 are handled** — other Unicode like `↔` (U+2194), `←`, emoji will fail silently or cause compilation errors. Use plain text alternatives (e.g., `store-to-digital` not `store↔digital`).
  - **Bold inline labels**: Use `\textbf{Label:}` at the start of a bullet to create bold prefix tags (e.g., `\textbf{Store→Digital:}`). The `\` triggers raw LaTeX mode; unicode substitution still applies inside. Useful for making phygital direction or category scannable.
  - **Empty itemize environments**: If a role's INJECT block has no bullets (all commented out), the wrapping `\begin{itemize}...\end{itemize}` must be commented out in the template — an empty itemize causes `Missing \item` LaTeX errors. Currently applies to Mouve (itemize wrapper commented out, `mouve_title` INJECT marker available for per-job title customization).
  - **Line budget heuristic vs reality**: The pre-flight check (CALIBRATED_CHARS_PER_LINE=82, CALIBRATED_MAX_LINES=17) is a guide, not a hard gate. The actual PDF may fit on 1 page even when the heuristic flags overrun — especially when sections with overhead (vspace, itemize wrappers) are removed. Always build and check the PDF rather than pre-trimming to hit the heuristic exactly.
  - **Before marking PDF complete — run these checks**:
    1. Open the compiled `.tex` and confirm no literal Unicode `₹`, `→`, `←` remain (script handles them, but verify if you added raw LaTeX bullets manually).
    2. Check every metric mid-sentence reads correctly in the PDF — no blank gaps (invisible glyph = missing character substitution).
    3. `~` as approximation renders as a tilde, not a minus/dash.
    4. Each role's first bullet has visible separation from the role header line (not cramped).
    5. Summary line and role subheadings match the bullet framing — if bullets say "post-purchase ops", summary and subheadings cannot say "AI products".
    6. Confirm 1 page (build script page-count check handles this, but verify visually).
- **Job Intelligence Package**: Before creating any application content for a job (resume, elevator pitch, cover letter) — check if `output/jobs/{dir}/job_intelligence.md` exists. If not, run `prompts/job_intelligence.md` to generate it **in the current Sonnet session** (judgment-intensive — do not delegate to Haiku). This file contains JD pillars, story bank rankings, domain correctness flags, and notation rules. Re-run only when the JD changes or new experience files are added.
- **Two-tier model routing**: Intelligence generation = Sonnet (main session). Artifact generation = Haiku subagent (Agent tool, model: haiku). After confirming `job_intelligence.md` is complete and correct, spawn a Haiku subagent for each artifact passing the job directory path and the relevant prompts file. The Sonnet session reviews the output — if wrong, correct in Sonnet and log the failure to `## Content iterations`.
- **Application collateral** (cover letter + elevator pitch): Generate intelligence package in Sonnet, then delegate artifact writing to a Haiku subagent using `prompts/cover_letter.md` or `prompts/elevator_pitch.md`.
- **Resume content**: Same routing — Sonnet for intelligence + scoring review, Haiku subagent for producing the merged bullet set using `prompts/resume_content.md`.
- **Correction logging**: When any artifact is approved after corrections — before closing: (a) log each version + rejection reason to `## Content iterations` in `job_intelligence.md`, (b) identify the root-cause rule gap, (c) update the corresponding prompts file. Approval after zero corrections = log "v1 → approved". This is not optional.
- **Cross-job learning**: After every 3 jobs reach `applied` status, scan `## Content iterations` across all intelligence files. Any correction reason appearing 2+ times is a systemic gap — update the prompts file.
- **Pipeline jobs**: When working with pipeline stages or job schema, refer to MEMORY.md for the schema definition.

## Running things
- Always activate venv first: `source venv/bin/activate && python3 ...`
- Discovery: `python scripts/discover.py` (or `--test`)
- Web app: `streamlit run scripts/app.py`
- Resume build: `python scripts/build_resume.py --job "Company::Title"` (or `--list-keys` to see injection marker keys)

## Conventions
- No database — everything in `data/jobs_found.json`
- Job dedup key: `normalize_company(company) + "__" + normalize_title(title)`
- App job key: `"company::title"` (for UI lookups)
