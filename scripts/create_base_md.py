import sys
import re
from pathlib import Path

# Add scripts to path so we can import build_resume
sys.path.append('scripts')
import build_resume

def create_base_md():
    template_path = Path('templates/resume_base.tex')
    if not template_path.exists():
        print(f"Error: {template_path} not found")
        return

    text = template_path.read_text(encoding='utf-8')
    baseline = build_resume.parse_template_baseline(template_path)
    
    content = ['## Resume-Ready Bullets\n']
    
    # Keys in order as they appear in the template
    keys = ['summary', 'r1_header', 'r1_subheading', 'r1_bullets', 'r2_header', 'r2_subheading', 'r2_bullets', 'r2b_subheading', 'r2b_bullets', 'r2c_header', 'r2c_bullets', 'r3_title', 'earlier_experience', 'education', 'skills']
    
    for key in keys:
        content.append(f'### {key}')
        
        if key in build_resume.TEXT_BLOCK_KEYS:
            # Extract raw text block directly from template for these keys
            pattern = r'% INJECT_START: ' + key + r'\n(.*?)\n% INJECT_END: ' + key
            match = re.search(pattern, text, re.DOTALL)
            if match:
                block = match.group(1).strip()
                # Clean up comments
                lines = []
                for l in block.split('\n'):
                    # Strip LaTeX comments
                    l = re.sub(r'(?<!\\)%.*$', '', l).strip()
                    if l:
                        lines.append(l)
                content.append(' '.join(lines))
        elif key in baseline:
            # It is a role
            for bullet in baseline[key]['bullets']:
                content.append(f'- {bullet}')
        
        content.append('')

    Path('data/base_resume.md').write_text('\n'.join(content), encoding='utf-8')
    print('Created data/base_resume.md')

if __name__ == '__main__':
    create_base_md()
