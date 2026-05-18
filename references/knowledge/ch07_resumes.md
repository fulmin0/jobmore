# Ch7: Resumes

## Summary
The most practically applicable chapter for job searching. Covers exactly what makes a PM resume effective — structure, content rules, what to include/exclude, and how to pass the 15-second skim. Includes a named "5 rules" framework and detailed guidance on bullet writing. High-signal chapter; apply directly to resume content workflow.

## Key Concepts
- **The 15-second rule**: Recruiters skim, not read. Resume must communicate value within the first glance — headline, company names, and top bullet per role must all carry weight
- **5 Resume Rules**:
  1. **Shorter is better**: One page for under 10 years of experience. Two pages only if you have extensive, all-relevant experience
  2. **Bullets, not blobs**: No paragraph-style descriptions. Every line is a bullet
  3. **Accomplishments, not responsibilities**: "Led X to achieve Y" beats "Responsible for Z". The question is: what changed because of you?
  4. **Good template**: Clean, scannable, ATS-friendly. No tables, no columns, no graphics. Standard section headers (Experience, Education, Skills)
  5. **Don't skip your best stuff**: If the most impressive thing you've done is buried at the bottom, restructure — lead with impact
- **Bullet writing formula**: `[Action verb] + [what you did] + [measurable outcome]` — every bullet should answer "so what?"
- **Action verbs that signal PM thinking**: Led, Shipped, Defined, Prioritized, Drove, Launched, Analyzed, Reduced, Grew, Designed, Owned, Partnered
- **Metrics rule**: Quantify when you can. "Reduced churn by 18%" beats "Improved retention". If you can't quantify, qualify with scale ("for 2M+ users", "across 14 markets")
- **What to include**:
  - Every relevant role (no gaps without explanation)
  - Education (briefly — school, degree, year; honors only if top-tier)
  - Skills section: tools (SQL, Figma, JIRA), methodologies (Agile, A/B testing), languages if relevant
  - Side projects only if shipped and demonstrably impactful
- **What to exclude**:
  - "References available upon request" — waste of space
  - Objective statement — outdated; replace with a 2-line summary if anything
  - GPA unless >3.5 and recent grad
  - Unrelated work history beyond 1 line
- **Summary line (optional but useful for senior PMs)**: 1–2 sentences of positioning — what you do, for whom, at what scale. Functions as the skim-layer hook above the work history

## Direct Quotes / Signals Worth Preserving
- "A resume isn't read; it's skimmed. A resume screener will glance at your resume for about 15 seconds before deciding to keep reading or move on."
- "Don't list your responsibilities. List your accomplishments. Nobody cares what you were supposed to do. They care what you actually did."
- Rule #5 framing: "If the most impressive thing you've done is buried on page 2 because you're following reverse-chronological order, you're doing it wrong."

## Relevance to Job Search Pipeline
- **Direct application to resume content workflow**: The 5 rules are the editorial framework for every bullet rewrite. When evaluating a bullet, ask: Is this an accomplishment or a responsibility? Is it quantified? Is it the most impactful version?
- **Bullet count constraint rationale**: The "shorter is better" rule is why the baseline bullet count from `build_resume.py --list-keys` is a hard cap — not a guideline
- **Summary line**: Use the summary framing (capabilities + scale) for the `summary` inject key in `resume_base.tex`
- **Skills section**: The skills inject key should follow "tools, methodologies, domain knowledge" structure from this chapter
- **ATS compliance**: The "good template" rule explains why `resume_base.tex` uses standard LaTeX structure without tables or custom section names
