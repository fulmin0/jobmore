import re
from pathlib import Path

def extract_baseline():
    template_path = Path('templates/resume_base.tex')
    text = template_path.read_text(encoding='utf-8')
    pattern = r'% INJECT_START: ([^\n]+)\n(.*?)\n% INJECT_END: \1'
    
    content = ["## Resume-Ready Bullets\n"]
    
    for m in re.finditer(pattern, text, flags=re.DOTALL):
        key = m.group(1).strip()
        block = m.group(2)
        
        # Heading for the key
        content.append(f"### {key}")
        
        if key in ['summary', 'skills', 'r1_subheading', 'r2_subheading', 'r2b_subheading', 'r2c_header', 'r3_title']:
            # Text block keys
            # Strip comments and join lines
            lines = []
            for line in block.split('\n'):
                stripped = re.sub(r'(?<!\\)%.*$', '', line).strip()
                if stripped:
                    lines.append(stripped)
            content.append(' '.join(lines))
        else:
            # Role keys
            # Strip comments
            lines = []
            for line in block.split('\n'):
                stripped = re.sub(r'(?<!\\)%.*$', '', line).strip()
                if stripped:
                    lines.append(stripped)
            clean_block = ' '.join(lines)
            
            # Split on \item
            parts = re.split(r'\\item\b', clean_block)
            bullets = [p.strip().strip('{}').strip() for p in parts[1:]]
            for b in bullets:
                if b:
                    content.append(f"- {b}")
        
        content.append("")
    
    output_dir = Path('output/jobs/base')
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / 'resume_content.md').write_text('\n'.join(content), encoding='utf-8')
    print(f"Generated output/jobs/base/resume_content.md")

if __name__ == '__main__':
    extract_baseline()
