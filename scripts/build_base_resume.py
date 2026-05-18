import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path('.').absolute()
TEMPLATE_PATH = PROJECT_ROOT / "templates" / "resume_base.tex"

def _load_personal() -> dict:
    config_path = PROJECT_ROOT / 'config.json'
    if not config_path.exists():
        print('Error: config.json not found.')
        sys.exit(1)
    cfg = json.loads(config_path.read_text(encoding='utf-8'))
    return cfg.get('personal', {})

PERSONAL = _load_personal()
PDF_NAME = PERSONAL.get('pdf_name', 'Resume_Base')

def substitute_personal(tex: str) -> str:
    replacements = {
        '%%PERSONAL_NAME%%':            PERSONAL.get('full_name', 'YOUR NAME'),
        '%%PERSONAL_EMAIL%%':           PERSONAL.get('email', 'YOUR EMAIL'),
        '%%PERSONAL_PHONE%%':           PERSONAL.get('phone', 'YOUR PHONE'),
        '%%PERSONAL_PHONE_LINK%%':      PERSONAL.get('phone_link', 'tel:000'),
        '%%PERSONAL_LINKEDIN_URL%%':    PERSONAL.get('linkedin_url', ''),
        '%%PERSONAL_LINKEDIN_DISPLAY%%': PERSONAL.get('linkedin_display', ''),
    }
    for placeholder, value in replacements.items():
        tex = tex.replace(placeholder, value)
    return tex

def compile_base():
    if not TEMPLATE_PATH.exists():
        print(f"Error: {TEMPLATE_PATH} not found")
        return

    tex_content = TEMPLATE_PATH.read_text(encoding='utf-8')
    tex_content = substitute_personal(tex_content)
    
    # Fix fonts
    fonts_abs = str(TEMPLATE_PATH.parent / 'fonts') + '/'
    tex_content = tex_content.replace('Path = fonts/', f'Path = {fonts_abs}')
    
    base_dir = PROJECT_ROOT / "output" / "base"
    base_dir.mkdir(parents=True, exist_ok=True)
    
    tex_out = base_dir / "resume_base.tex"
    tex_out.write_text(tex_content, encoding='utf-8')
    
    print(f"Compiling {tex_out}...")
    try:
        subprocess.run(['tectonic', str(tex_out)], check=True, capture_output=True)
        pdf_out = base_dir / "resume_base.pdf"
        print(f"Created {pdf_out}")
        
        # Copy to output/ready/Resume_Base.pdf
        ready_dir = PROJECT_ROOT / "output" / "ready"
        ready_dir.mkdir(exist_ok=True)
        shutil.copy(str(pdf_out), str(ready_dir / f"{PDF_NAME}_Base.pdf"))
        print(f"Copied to output/ready/{PDF_NAME}_Base.pdf")
        
    except subprocess.CalledProcessError as e:
        print(f"Error compiling: {e.stderr.decode()}")

if __name__ == '__main__':
    compile_base()
