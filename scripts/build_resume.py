#!/usr/bin/env python3
"""
build_resume.py — Parse Resume-Ready bullets from resume_content.md,
inject into LaTeX template, compile to PDF via Tectonic.

Usage:
  python3 scripts/build_resume.py --job "Mumzworld::Senior PM - Operations"
  python3 scripts/build_resume.py --file output/jobs/Mumzworld_Senior_PM_Operations/resume_content.md
  python3 scripts/build_resume.py --list-keys --job "Mumzworld::Senior PM - Operations"

One-time setup:
  1. Copy your Overleaf .tex file to templates/resume_base.tex
  2. Add injection markers around each role's \\item lines:
       % INJECT_START: senior_pm_businessonbot
       \\item Old bullet...
       % INJECT_END: senior_pm_businessonbot
     Run --list-keys to see the keys and baseline bullet counts.
  3. brew install tectonic && pip install pypdf

Raw LaTeX passthrough:
  Bullets in resume_content.md that contain a backslash (\\) are treated as
  raw LaTeX and injected verbatim — they are NOT escaped. This lets the
  content generator decide per bullet whether to preserve \\href{...}{...}
  links, \\textbf{...} emphasis, etc. Plain-text bullets (the common case)
  still get safe escaping for &, %, _, #, etc.

Text-block keys (summary, skills, bob_subheading, apollo_subheading):
  These keys inject a single line of text rather than a bullet list.
  Plain-text values are LaTeX-escaped. Values containing a backslash are
  treated as raw LaTeX and injected verbatim (same passthrough rule).
  For subheadings, provide the full raw LaTeX line including \\textbf{},
  \\hfill{year}, and trailing \\\\ — the raw-passthrough rule handles it.

Unicode character substitution:
  Before injection, ₹ → \\rupee{}, → → $\\rightarrow$, ~N → ${\\sim}$N.
  Fontin (the resume font) lacks these glyphs — the substitutions use
  LaTeX commands that render correctly regardless of font.
"""

import argparse
import copy
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
import time
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

# ---------------------------------------------------------------------------
# Personal config — loaded once at import time from config.json
# ---------------------------------------------------------------------------

def _load_personal() -> dict:
    config_path = PROJECT_ROOT / 'config.json'
    if not config_path.exists():
        print('Error: config.json not found. Copy config.example.json → config.json and fill in your details.')
        sys.exit(1)
    cfg = json.loads(config_path.read_text(encoding='utf-8'))
    personal = cfg.get('personal')
    if not personal:
        print("Error: 'personal' section missing from config.json — see config.example.json for required fields.")
        sys.exit(1)
    required = ['full_name', 'email', 'phone', 'phone_link', 'linkedin_url', 'linkedin_display', 'pdf_name']
    missing = [k for k in required if not personal.get(k)]
    if missing:
        print(f"Error: config.json personal section is missing fields: {', '.join(missing)}")
        sys.exit(1)
    return personal

PERSONAL = _load_personal()
PDF_NAME = PERSONAL['pdf_name']


def substitute_personal(tex: str) -> str:
    """Replace %%PERSONAL_*%% placeholders in a LaTeX string."""
    replacements = {
        '%%PERSONAL_NAME%%':            PERSONAL['full_name'],
        '%%PERSONAL_EMAIL%%':           PERSONAL['email'],
        '%%PERSONAL_PHONE%%':           PERSONAL['phone'],
        '%%PERSONAL_PHONE_LINK%%':      PERSONAL['phone_link'],
        '%%PERSONAL_LINKEDIN_URL%%':    PERSONAL['linkedin_url'],
        '%%PERSONAL_LINKEDIN_DISPLAY%%': PERSONAL['linkedin_display'],
    }
    for placeholder, value in replacements.items():
        tex = tex.replace(placeholder, value)
    return tex
JOBS_DIR = PROJECT_ROOT / "output" / "jobs"
READY_DIR = PROJECT_ROOT / "output" / "ready"
TEMPLATE_PATH = PROJECT_ROOT / "templates" / "resume_base.tex"

# Keys that inject a single line of text rather than a bullet list.
# Extend this set when new text-block inject regions are added to the template.
TEXT_BLOCK_KEYS = {'summary', 'skills', 'bob_subheading', 'apollo_subheading', 'mouve_title'}

# ---------------------------------------------------------------------------
# Line budget constants
# Calibrated empirically via --calibrate. Update after running:
#   python3 scripts/build_resume.py --calibrate --job "Company::Title"
# Working limits are 90% of the empirical maximums.
# ---------------------------------------------------------------------------
CALIBRATED_CHARS_PER_LINE: int = 82   # 90% of empirical max (92); calibrated 2026-04-14
CALIBRATED_MAX_LINES: int = 17        # 90% of empirical max (19); calibrated 2026-04-14


# ---------------------------------------------------------------------------
# Normalisation helpers
# ---------------------------------------------------------------------------

def normalize_key(text: str) -> str:
    """
    Turn a role header into a marker key.
    "Senior PM, BusinessOnBot (2024-25)" → "senior_pm_businessonbot"
    """
    text = re.sub(r'\(\d{4}[-–]\d{2,4}\)', '', text)   # strip year ranges
    text = re.sub(r'\(\d{4}\)', '', text)                # strip single years
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '_', text)
    return text.strip('_')


def normalize_job_folder(job_key: str) -> str:
    """
    Turn "Mumzworld::Senior PM - Operations" → "Mumzworld_Senior_PM_Operations"
    """
    name = re.sub(r'::', '_', job_key)
    name = re.sub(r'[^a-zA-Z0-9]+', '_', name)
    return name.strip('_')


# ---------------------------------------------------------------------------
# Resume-Ready parser
# ---------------------------------------------------------------------------

def parse_resume_ready(md_path: Path) -> dict:
    """
    Parse the Resume-Ready section from a resume_content.md file.

    Returns:
      {
        'summary': str,
        'skills':  str,
        'roles':   { key: {'header': str, 'bullets': [str, ...]} },
        'role_order': [key, ...]   # insertion order
      }
    """
    content = md_path.read_text(encoding='utf-8')

    if '## Resume-Ready Bullets' not in content:
        raise ValueError(f"No '## Resume-Ready Bullets' section found in {md_path}")

    section_text = content.split('## Resume-Ready Bullets', 1)[1]
    # Stop at the separator line that follows the section
    end = re.search(r'\n---', section_text)
    if end:
        section_text = section_text[:end.start()]

    result = {'summary': '', 'skills': '', 'roles': {}, 'role_order': [], 'text_blocks': {}}
    current_key = None

    for line in section_text.split('\n'):
        stripped = line.strip()

        # Skip blank lines and italic hints (*text*) — but not **bold** headers
        if not stripped or (stripped.startswith('*') and not stripped.startswith('**') and stripped.endswith('*')):
            continue

        # Summary header
        if stripped == '**Summary**':
            current_key = 'summary'
            continue

        # Skills header
        if stripped == '**Skills**':
            current_key = 'skills'
            continue

        # Role header: **Role, Company (Years)**  <!-- optional HTML comment ignored -->
        stripped_no_comment = re.sub(r'\s*<!--.*?-->', '', stripped).strip()
        role_m = re.match(r'^\*\*(.+?)\*\*$', stripped_no_comment)
        if role_m:
            header = role_m.group(1)
            if header not in ('Summary', 'Skills'):
                key = normalize_key(header)
                result['roles'][key] = {'header': header, 'bullets': []}
                result['role_order'].append(key)
                current_key = key
                continue

        # Bullet line
        if stripped.startswith('- ') and current_key and current_key not in ('summary', 'skills'):
            bullet = stripped[2:].strip()
            # Strip backtick-wrapped tags: `[REAL]`, `[MIXED: ...]`, `[EXTRAPOLATED]`
            bullet = re.sub(r'\s*`\[(?:REAL|MIXED|EXTRAPOLATED)[^\]]*\]`', '', bullet)
            bullet = re.sub(r'\s*\[(?:REAL|MIXED|EXTRAPOLATED)[^\]]*\]', '', bullet)
            bullet = bullet.strip()
            if bullet:
                result['roles'][current_key]['bullets'].append(bullet)
            continue

        # Single-line content for text-block keys
        if current_key == 'summary' and stripped and not stripped.startswith('**'):
            result['summary'] = stripped
        elif current_key == 'skills' and stripped and not stripped.startswith('**'):
            result['skills'] = stripped
        elif (current_key in TEXT_BLOCK_KEYS and current_key not in ('summary', 'skills')
              and stripped and not stripped.startswith('**') and not stripped.startswith('-')):
            result['text_blocks'][current_key] = stripped

    return result


# ---------------------------------------------------------------------------
# LaTeX escaping
# ---------------------------------------------------------------------------

# Order matters: backslash must be processed before other replacements.
_LATEX_REPLACEMENTS = [
    ('\\', r'\textbackslash{}'),
    ('{',  r'\{'),
    ('}',  r'\}'),
    ('&',  r'\&'),
    ('%',  r'\%'),
    ('$',  r'\$'),
    ('#',  r'\#'),
    ('_',  r'\_'),
    ('~',  r'\textasciitilde{}'),
    ('^',  r'\textasciicircum{}'),
]


def latex_escape(text: str) -> str:
    """Escape LaTeX special characters. Unicode (₹, →, …) left as-is for XeLaTeX."""
    for char, repl in _LATEX_REPLACEMENTS:
        text = text.replace(char, repl)
    return text


def _fix_unicode_chars(text: str) -> str:
    """
    Replace Unicode glyphs that Fontin cannot render with LaTeX command equivalents.

    - ₹  →  \\rupee{}          (tfrupee package, already loaded in template)
    - →  →  $\\rightarrow$     (math-mode arrow, font-independent)
    - ~N →  ${\\sim}$N         (tilde-as-approximation before a digit only)
    """
    text = text.replace('₹', r'\rupee{}')
    text = text.replace('→', r'$\rightarrow$')
    text = re.sub(r'~(\d)', lambda m: r'${\sim}$' + m.group(1), text)
    return text


def format_bullet(text: str) -> str:
    """
    Format a bullet for LaTeX injection.

    Raw-passthrough rule: if the bullet *originally* contains any backslash,
    treat it as raw LaTeX (generator kept \\href{...} etc.) — apply only
    unicode substitution, then inject verbatim.

    Plain-text path: escape LaTeX special chars first (% → \\%, & → \\& etc.),
    skipping ~ (handled by _fix_unicode_chars), then apply unicode substitution.
    This order ensures % in "~25%" gets escaped as \\% before _fix_unicode_chars
    converts ~25 into a $...$ math expression that triggers raw injection.
    """
    is_raw = '\\' in text  # check for pre-existing raw LaTeX before substitutions

    if is_raw:
        text = _fix_unicode_chars(text)
    else:
        # Escape all special chars except ~ (handled by _fix_unicode_chars below)
        for char, repl in _LATEX_REPLACEMENTS:
            if char != '~':
                text = text.replace(char, repl)
        text = _fix_unicode_chars(text)

    return f'  \\item {text}'


# ---------------------------------------------------------------------------
# Template baseline parser (for --list-keys and score-then-merge workflow)
# ---------------------------------------------------------------------------

def parse_template_baseline(template_path: Path) -> dict:
    """
    Parse templates/resume_base.tex and return:
      { key: {'bullet_count': int, 'bullets': [str, ...]} }

    Rough extraction: grabs every % INJECT_START/END block, strips comments,
    and counts \\item occurrences. The bullet text is a best-effort read for
    the content generator to score against; it is NOT byte-perfect LaTeX.
    """
    if not template_path.exists():
        return {}

    text = template_path.read_text(encoding='utf-8')
    pattern = r'% INJECT_START: ([^\n]+)\n(.*?)\n% INJECT_END: \1'
    result = {}

    for m in re.finditer(pattern, text, flags=re.DOTALL):
        key = m.group(1).strip()
        block = m.group(2)

        # Strip LaTeX comments (% to end of line), but not escaped \%
        lines = []
        for line in block.split('\n'):
            stripped = re.sub(r'(?<!\\)%.*$', '', line).strip()
            if stripped:
                lines.append(stripped)
        clean_block = ' '.join(lines)

        # Split on \item and take everything after the first one
        parts = re.split(r'\\item\b', clean_block)
        bullets = [p.strip().strip('{}').strip() for p in parts[1:]]
        bullets = [b for b in bullets if b]

        result[key] = {
            'bullet_count': len(bullets),
            'bullets': bullets,
        }

    return result


# ---------------------------------------------------------------------------
# Template injection
# ---------------------------------------------------------------------------

def inject_into_template(template_text: str, parsed: dict) -> str:
    """
    Replace content between % INJECT_START: key / % INJECT_END: key markers.
    Unmatched markers are left unchanged.
    """
    pattern = r'(% INJECT_START: ([^\n]+))\n(.*?)\n(% INJECT_END: \2)'

    def _passthrough_or_escape(text: str) -> str:
        """Unicode substitution, then raw LaTeX if backslash present, else escaped plain text."""
        text = _fix_unicode_chars(text)
        return text if '\\' in text else latex_escape(text)

    def replace_block(m):
        start_comment = m.group(1)
        key = m.group(2).strip()
        end_comment = m.group(4)

        if key == 'summary' and parsed['summary']:
            body = _passthrough_or_escape(parsed['summary'])
        elif key == 'skills' and parsed['skills']:
            body = _passthrough_or_escape(parsed['skills'])
        elif key in parsed.get('text_blocks', {}) and parsed['text_blocks'][key]:
            body = _passthrough_or_escape(parsed['text_blocks'][key])
        elif key in parsed['roles'] and parsed['roles'][key]['bullets']:
            items = [format_bullet(b) for b in parsed['roles'][key]['bullets']]
            body = '\n  \\vspace{-4pt}\n'.join(items)
        else:
            return m.group(0)  # no match — leave intact

        return f'{start_comment}\n{body}\n{end_comment}'

    return re.sub(pattern, replace_block, template_text, flags=re.DOTALL)


# ---------------------------------------------------------------------------
# Compilation
# ---------------------------------------------------------------------------

def compile_pdf(tex_path: Path, out_dir: Path) -> Path:
    """Compile .tex → PDF using Tectonic. Returns path to {PDF_NAME}.pdf."""
    result = subprocess.run(
        ['tectonic', str(tex_path), '--outdir', str(out_dir)],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print('Tectonic compilation failed:')
        print(result.stderr or result.stdout)
        sys.exit(1)

    # Tectonic names output {stem}.pdf
    compiled = out_dir / (tex_path.stem + '.pdf')
    final = out_dir / f'{PDF_NAME}.pdf'
    if compiled.exists() and compiled != final:
        compiled.rename(final)
    return final


def get_page_count(pdf_path: Path):
    """Return page count of a PDF, or None if pypdf is not installed."""
    try:
        import pypdf
        return len(pypdf.PdfReader(str(pdf_path)).pages)
    except ImportError:
        print('Warning: pypdf not installed — skipping page count check. Run: pip install pypdf')
        return None


# ---------------------------------------------------------------------------
# Interactive pruning loop
# ---------------------------------------------------------------------------

def pruning_loop(parsed: dict, job_dir: Path) -> Path:
    """Interactively remove bullets until the PDF fits one page."""
    pdf_path = job_dir / f'{PDF_NAME}.pdf'

    while True:
        # Display current bullets with numbers
        print('\nCurrent bullets:')
        index = 1
        bullet_map = {}  # display_index → (role_key, position_in_role)
        for key in parsed['role_order']:
            role = parsed['roles'][key]
            if not role['bullets']:
                continue
            print(f"\n  [{role['header']}]")
            for i, b in enumerate(role['bullets']):
                preview = b if len(b) <= 100 else b[:97] + '...'
                print(f'    {index}. {preview}')
                bullet_map[index] = (key, i)
                index += 1

        resp = input(
            '\nResume > 1 page. Remove bullet(s) by number (e.g. 3,7), '
            "'auto' to drop last bullet per role, or 'done' to keep as-is: "
        ).strip().lower()

        if resp == 'done':
            break

        if resp == 'auto':
            for key in parsed['role_order']:
                if len(parsed['roles'][key]['bullets']) > 1:
                    parsed['roles'][key]['bullets'].pop()
        else:
            # Parse comma-separated numbers, group by role, remove in reverse order
            to_remove = set()
            for part in resp.split(','):
                try:
                    n = int(part.strip())
                    if n in bullet_map:
                        to_remove.add(n)
                except ValueError:
                    pass

            by_role = defaultdict(list)
            for n in to_remove:
                rkey, bi = bullet_map[n]
                by_role[rkey].append(bi)
            for rkey, positions in by_role.items():
                for bi in sorted(positions, reverse=True):
                    parsed['roles'][rkey]['bullets'].pop(bi)

        # Re-inject and recompile
        tex_path = job_dir / 'resume.tex'
        injected = inject_into_template(TEMPLATE_PATH.read_text(encoding='utf-8'), parsed)
        tex_path.write_text(injected, encoding='utf-8')

        print('Recompiling...')
        pdf_path = compile_pdf(tex_path, job_dir)
        pages = get_page_count(pdf_path)
        if pages is None or pages <= 1:
            print(f'  {pages or "?"} page(s) — good.')
            break
        print(f'  Still {pages} pages.')

    return pdf_path


# ---------------------------------------------------------------------------
# Line budget pre-flight check
# ---------------------------------------------------------------------------

def check_line_budget(parsed: dict) -> tuple[int, list[str]]:
    """
    Estimate total bullet content lines and return (total_lines, warnings).

    Uses CALIBRATED_CHARS_PER_LINE as the working line width (already 90% of
    empirical max). Only bullet content is counted — structural elements
    (role headers, section headers, name block) are fixed overhead already
    accounted for in CALIBRATED_MAX_LINES.

    Returns (total_lines, warnings) where warnings is empty if within budget.
    """
    warnings: list[str] = []
    total_lines = 0

    for key in parsed.get('role_order', []):
        bullets = parsed['roles'][key]['bullets']
        for bullet in bullets:
            # Strip LaTeX commands for length estimation:
            #   \cmd{text} → text,  \cmd → ''
            clean = re.sub(r'\\[a-zA-Z]+\{([^}]*)\}', r'\1', bullet)
            clean = re.sub(r'\\[a-zA-Z]+\b', '', clean)
            clean = re.sub(r'\s+', ' ', clean).strip()
            lines = max(1, len(textwrap.wrap(clean, width=CALIBRATED_CHARS_PER_LINE)))
            total_lines += lines
            if lines > 2:
                preview = bullet[:60] + ('…' if len(bullet) > 60 else '')
                warnings.append(
                    f'  [{key}] {lines}-line bullet — consider trimming: {preview}'
                )

    if total_lines > CALIBRATED_MAX_LINES:
        warnings.insert(
            0,
            f'Total estimated content lines: {total_lines} (budget: {CALIBRATED_MAX_LINES}) — likely 2+ pages',
        )

    return total_lines, warnings


# ---------------------------------------------------------------------------
# Job directory resolution
# ---------------------------------------------------------------------------

def find_job_dir(job_key=None, file_path=None):
    """Return (job_dir: Path, md_path: Path)."""
    if file_path:
        p = Path(file_path).resolve()
        if not p.exists():
            print(f'Error: file not found: {file_path}')
            sys.exit(1)
        # If already inside output/jobs/{dir}/, use that dir
        if p.parent.parent == JOBS_DIR.resolve():
            return p.parent, p
        # Legacy path (output/resume_content/) — derive folder from stem
        stem = p.stem
        job_dir = JOBS_DIR / stem
        job_dir.mkdir(parents=True, exist_ok=True)
        dest = job_dir / 'resume_content.md'
        if not dest.exists():
            shutil.copy(p, dest)
        return job_dir, dest

    if job_key:
        folder_name = normalize_job_folder(job_key)
        exact = JOBS_DIR / folder_name
        if exact.exists():
            return exact, exact / 'resume_content.md'
        # Case-insensitive fallback
        for d in JOBS_DIR.iterdir():
            if d.is_dir() and d.name.lower() == folder_name.lower():
                return d, d / 'resume_content.md'
        print(f"Error: no job folder found for '{job_key}' (tried '{folder_name}')")
        print('Available jobs:')
        for d in sorted(JOBS_DIR.iterdir()):
            if d.is_dir():
                print(f'  {d.name}')
        sys.exit(1)

    print('Error: provide --job or --file')
    sys.exit(1)


# ---------------------------------------------------------------------------
# Calibration
# ---------------------------------------------------------------------------

_SAMPLE_TEXT = (
    'Built integrated shipped designed managed drove launched scaled delivered '
    'product feature workflow channel integration platform analytics pipeline '
)


def _build_calibration_pdf(parsed: dict, cal_dir: Path) -> Path:
    """Compile a PDF from a modified parsed dict into cal_dir. Returns PDF path."""
    template_text = TEMPLATE_PATH.read_text(encoding='utf-8')
    template_text = substitute_personal(template_text)
    injected = inject_into_template(template_text, parsed)
    fonts_abs = str(TEMPLATE_PATH.parent / 'fonts') + '/'
    injected = injected.replace('Path = fonts/', f'Path = {fonts_abs}')
    tex_path = cal_dir / 'resume.tex'
    tex_path.write_text(injected, encoding='utf-8')
    result = subprocess.run(
        ['tectonic', str(tex_path), '--outdir', str(cal_dir)],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print('Tectonic failed during calibration:')
        print(result.stderr or result.stdout)
        sys.exit(1)
    compiled = cal_dir / (tex_path.stem + '.pdf')
    final = cal_dir / f'{PDF_NAME}.pdf'
    if compiled.exists() and compiled != final:
        compiled.rename(final)
    return final


def _make_text(n: int) -> str:
    """Generate representative placeholder text of approximately n chars."""
    full = (_SAMPLE_TEXT * ((n // len(_SAMPLE_TEXT)) + 2))[:n]
    return full.rstrip()


def calibrate_resume(job_dir: Path, md_path: Path) -> None:
    """
    Empirically calibrate CALIBRATED_CHARS_PER_LINE and CALIBRATED_MAX_LINES
    by running binary-search compilations through Tectonic.

    Phase 1: Add 1-line bullets until page count hits 2 → finds max content lines.
    Phase 2: Binary search char length of one bullet until it wraps → finds chars per line.

    Prints the constants to paste into this file.
    """
    SHORT = _make_text(20)   # Definitely fits 1 line at any reasonable font size

    cal_dir = job_dir / '_calibration'
    cal_dir.mkdir(exist_ok=True)

    # Minimal baseline: 1 short bullet per role.
    # Exclude text-block keys (bob_subheading, apollo_subheading) — they appear in
    # role_order because they match the **...** header pattern, but their content is
    # handled by the text_blocks injection path, not the bullet injection path.
    parsed = copy.deepcopy(parse_resume_ready(md_path))
    role_keys = [k for k in parsed['role_order'] if k not in TEXT_BLOCK_KEYS]
    for key in role_keys:
        parsed['roles'][key]['bullets'] = [SHORT]
    first_role = role_keys[0]

    # --- Phase 1: max content lines ---
    print('\nStep 1/2 — Calibrating max content lines per page:')
    for iteration in range(80):
        pdf = _build_calibration_pdf(parsed, cal_dir)
        pages = get_page_count(pdf)
        if pages is None:
            print('Error: pypdf required for calibration. Run: pip install pypdf')
            shutil.rmtree(cal_dir, ignore_errors=True)
            sys.exit(1)
        total = sum(len(parsed['roles'][k]['bullets']) for k in role_keys)
        print(f'  {total:3d} lines → {pages} page(s)')
        if pages > 1:
            max_lines = total - 1
            parsed['roles'][first_role]['bullets'].pop()   # restore 1-page state
            print(f'  → Max content lines: {max_lines}')
            break
        parsed['roles'][first_role]['bullets'].append(SHORT)
    else:
        print('Error: calibration did not converge — check template.')
        shutil.rmtree(cal_dir, ignore_errors=True)
        sys.exit(1)

    # --- Phase 2: chars per line ---
    # Need room for exactly 1 more line:
    #   baseline = max_lines-1 bullets (1 page with room for 1 more line)
    #   + 1-line test bullet  → max_lines total   → 1 page  (fits)
    #   + 2-line test bullet  → max_lines+1 total → 2 pages (wraps)
    # Remove 1 more bullet to create the (max_lines-1) baseline.
    parsed['roles'][first_role]['bullets'].pop()
    print('\nStep 2/2 — Calibrating chars per line:')
    lo, hi = 10, 200
    while lo < hi:
        mid = (lo + hi + 1) // 2
        test_parsed = copy.deepcopy(parsed)
        test_parsed['roles'][first_role]['bullets'].append(_make_text(mid))
        pdf = _build_calibration_pdf(test_parsed, cal_dir)
        pages = get_page_count(pdf)
        fits = pages is not None and pages <= 1
        print(f'  {mid:3d} chars → {pages} page(s) → {"fits  " if fits else "wraps"}')
        if fits:
            lo = mid
        else:
            hi = mid - 1

    chars_per_line = lo
    print(f'  → Max chars per line: {chars_per_line}')

    shutil.rmtree(cal_dir, ignore_errors=True)

    working_chars = int(chars_per_line * 0.9)
    working_lines = int(max_lines * 0.9)

    print(f'\n{"=" * 60}')
    print('Calibration results:')
    print(f'  Max chars per line:  {chars_per_line}  →  working limit: {working_chars}  (× 0.9)')
    print(f'  Max content lines:   {max_lines}  →  working limit: {working_lines}  (× 0.9)')
    print(f'\nUpdate constants in scripts/build_resume.py:')
    print(f'  CALIBRATED_CHARS_PER_LINE = {working_chars}')
    print(f'  CALIBRATED_MAX_LINES      = {working_lines}')
    print('=' * 60)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Build tailored resume PDF from resume_content.md.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('--job', metavar='COMPANY::TITLE',
                        help='Job key matching the output/jobs/ folder name')
    parser.add_argument('--file', metavar='PATH',
                        help='Direct path to resume_content.md')
    parser.add_argument('--list-keys', action='store_true',
                        help='Print marker keys for this file and exit (no build)')
    parser.add_argument('--calibrate', action='store_true',
                        help='Empirically calibrate line-budget constants and print them (no resume built)')
    args = parser.parse_args()

    if not args.job and not args.file:
        parser.print_help()
        sys.exit(1)

    job_dir, md_path = find_job_dir(job_key=args.job, file_path=args.file)

    if not md_path.exists():
        print(f'Error: resume_content.md not found at {md_path}')
        sys.exit(1)

    parsed = parse_resume_ready(md_path)

    # --calibrate: measure line-budget constants and exit
    if args.calibrate:
        if not TEMPLATE_PATH.exists():
            print(f'Error: template not found at {TEMPLATE_PATH}')
            sys.exit(1)
        if shutil.which('tectonic') is None:
            print("Error: 'tectonic' not found. Install with: brew install tectonic")
            sys.exit(1)
        calibrate_resume(job_dir, md_path)
        return

    # --list-keys: print keys from content file + baseline counts from template
    if args.list_keys:
        print(f'Marker keys parsed from: {md_path.relative_to(PROJECT_ROOT)}')
        print('  summary')
        for key in parsed['role_order']:
            print(f"  {key}  ←  {parsed['roles'][key]['header']}")
        print('  skills')

        baseline = parse_template_baseline(TEMPLATE_PATH)
        if baseline:
            print(f'\nTemplate baseline ({TEMPLATE_PATH.relative_to(PROJECT_ROOT)}):')
            for key, info in baseline.items():
                print(f"  {key}: {info['bullet_count']} bullet(s)")
        else:
            print(f'\n(No baseline found — {TEMPLATE_PATH.relative_to(PROJECT_ROOT)} missing or has no INJECT markers)')
        return

    # Verify template exists
    if not TEMPLATE_PATH.exists():
        print(f'Error: template not found at {TEMPLATE_PATH}')
        print('Copy your Overleaf .tex file to templates/resume_base.tex')
        print('Then add % INJECT_START / % INJECT_END markers around each role\'s \\item lines.')
        sys.exit(1)

    # Warn if template is stale (> 30 days)
    age_days = (time.time() - os.path.getmtime(str(TEMPLATE_PATH))) / 86400
    if age_days > 30:
        print(f'Warning: templates/resume_base.tex last updated {int(age_days)} days ago.')
        print("If you've revised your resume layout on Overleaf, re-copy the .tex file.\n")

    # Inject into template
    template_text = TEMPLATE_PATH.read_text(encoding='utf-8')
    template_text = substitute_personal(template_text)
    injected = inject_into_template(template_text, parsed)
    # Resolve relative font path to absolute so tectonic can find fonts
    # regardless of where the injected .tex is compiled from
    fonts_abs = str(TEMPLATE_PATH.parent / 'fonts') + '/'
    injected = injected.replace('Path = fonts/', f'Path = {fonts_abs}')

    job_dir.mkdir(parents=True, exist_ok=True)
    tex_path = job_dir / 'resume.tex'
    tex_path.write_text(injected, encoding='utf-8')
    print(f'Wrote: {tex_path.relative_to(PROJECT_ROOT)}')

    # Pre-flight line budget check
    total_lines, budget_warnings = check_line_budget(parsed)
    if budget_warnings:
        print(f'\n⚠  Line budget ({total_lines}/{CALIBRATED_MAX_LINES} lines):')
        for w in budget_warnings:
            print(w)
        print()
    else:
        print(f'Line budget: {total_lines}/{CALIBRATED_MAX_LINES} lines — OK')

    # Compile
    if shutil.which('tectonic') is None:
        print("Error: 'tectonic' not found. Install with: brew install tectonic")
        print(f'LaTeX file saved at: {tex_path}')
        sys.exit(1)

    print('Compiling with Tectonic (first run auto-downloads packages)...')
    pdf_path = compile_pdf(tex_path, job_dir)
    print(f'Compiled: {pdf_path.relative_to(PROJECT_ROOT)}')

    # Page count check
    pages = get_page_count(pdf_path)
    if pages is not None and pages > 1:
        print(f'  Resume is {pages} page(s) — needs pruning.')
        pruning_loop(parsed, job_dir)
        # Write final injected .tex to reflect any pruning
        injected = inject_into_template(TEMPLATE_PATH.read_text(encoding='utf-8'), parsed)
        tex_path.write_text(injected, encoding='utf-8')
        pdf_path = job_dir / f'{PDF_NAME}.pdf'
    else:
        print(f'  {pages or "?"} page(s) — good.')

    # Copy to output/ready/
    READY_DIR.mkdir(exist_ok=True)
    ready_pdf = READY_DIR / f'{PDF_NAME}.pdf'
    shutil.copy(str(pdf_path), str(ready_pdf))
    print(f'\nResume ready: {ready_pdf.relative_to(PROJECT_ROOT)}')


if __name__ == '__main__':
    main()
