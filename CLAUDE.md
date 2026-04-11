# Jobmore — Project Instructions

## What this is
Job search pipeline: discovery (scraping + scoring), pipeline tracking (Streamlit), and resume content generation (conversational).

## File conventions

| Path | Purpose |
|------|---------|
| `data/jobs_found.json` | Single source of truth for all jobs (schema in MEMORY.md) |
| `data/experience/{company}_{role}.md` | One file per role — lines 1-4: company/role/start/end, line 5+: detailed bullets. Enrichment appended under `## Additional Context` |
| `data/resumes/{date}.pdf` | Resume snapshots (e.g. `20260409.pdf`) |
| `output/jobs/{Company}_{Title}/resume_content.md` | Generated resume content per target job |
| `output/jobs/{Company}_{Title}/resume.tex` | Injected LaTeX file for this job |
| `output/jobs/{Company}_{Title}/Resume_Archit.pdf` | Compiled PDF for this job |
| `output/ready/Resume_Archit.pdf` | Latest built resume — always the "send this" copy |
| `templates/resume_base.tex` | Master LaTeX template (copy from Overleaf, add INJECT markers) |
| `config.json` | Local config — **not committed** |
| `prompts/` | Workflow templates loaded on demand |

## Trigger rules

- **Resume content (tailoring)**: When the user asks to create resume content, tailor a resume, or target a pipeline job — read `prompts/resume_content.md` for the full workflow before proceeding. Core flow:
  1. Run `python3 scripts/build_resume.py --list-keys --job "Company::Title"` to see marker keys and baseline bullet counts per role
  2. Read `templates/resume_base.tex` — this is the baseline (not the PDF)
  3. Score every baseline bullet against the JD → tag each `KEEP` / `REFRAME` / `REPLACE`
  4. Produce merged final set per role: **same bullet count as baseline, every role present**
  5. Write `output/jobs/{Company}_{Title}/resume_content.md` with a `## Resume-Ready Bullets` section
  6. Talking points go in the working doc below (not in Resume-Ready)
  - **Raw LaTeX passthrough**: bullets containing `\` are injected verbatim by the build script. Use this to preserve `\href{...}{...}` on KEEP bullets when the link strengthens the candidate. Strip to plain text when the link is noise.
  - **Hard rules**: never skip a role, never exceed the baseline bullet count per role, always use ≤150 chars per bullet
- **Resume build**: When the user asks to build the PDF, compile the resume, or run build_resume — run `source venv/bin/activate && python3 scripts/build_resume.py --job "Company::Title"`. Requires `templates/resume_base.tex` with INJECT markers. First-time setup: `brew install tectonic && pip install pypdf`. The script parses the content file, injects into the template, compiles via Tectonic, and runs an interactive pruning loop if the PDF exceeds one page.
  - **Text-block inject keys**: `summary`, `skills`, `bob_subheading`, `apollo_subheading` inject a single line of text rather than a bullet list. Subheading values in the content file must be raw LaTeX (include `\textbf{}`, `\hfill{year}`, trailing `\\`) — the raw-passthrough rule handles them verbatim.
  - **Unicode substitution**: the build script auto-replaces `₹` → `\rupee{}`, `→` → `$\rightarrow$`, `~N` → `${\sim}$N` before injection. Write these characters naturally in the content file; do not pre-escape them.
  - **Before marking PDF complete — run these checks**:
    1. Open the compiled `.tex` and confirm no literal Unicode `₹`, `→`, `←` remain (script handles them, but verify if you added raw LaTeX bullets manually).
    2. Check every metric mid-sentence reads correctly in the PDF — no blank gaps (invisible glyph = missing character substitution).
    3. `~` as approximation renders as a tilde, not a minus/dash.
    4. Each role's first bullet has visible separation from the role header line (not cramped).
    5. Summary line and role subheadings match the bullet framing — if bullets say "post-purchase ops", summary and subheadings cannot say "AI products".
    6. Confirm 1 page (build script page-count check handles this, but verify visually).
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
