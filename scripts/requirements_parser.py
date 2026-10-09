"""Parse a requirements catalog markdown into structured requirement objects.

The parser is intentionally tolerant: it looks for explicit IDs like REQ-### and
falls back to heading-based extraction when IDs aren't present.

Returned object example:
{
  'id': 'REQ-001',
  'type': 'BusinessRule',
  'title': 'Device-first flow',
  'condition': 'Device selected',
  'outcome': 'Compatible plans displayed',
  'raw': 'full text block'
}
"""
from typing import List, Dict
import re


def parse_markdown_requirements(md_path: str) -> List[Dict]:
    with open(md_path, 'r', encoding='utf-8') as fh:
        text = fh.read()

    # Try to extract explicit REQ-IDs
    reqs = []
    pattern = re.compile(r'(REQ-\d{1,4})', re.IGNORECASE)
    matches = list(pattern.finditer(text))
    if matches:
        # For each match, take the block until the next REQ-
        for i, m in enumerate(matches):
            start = m.start()
            end = matches[i+1].start() if i+1 < len(matches) else len(text)
            block = text[start:end].strip()
            lines = [l.strip() for l in block.splitlines() if l.strip()]
            rid = m.group(1).upper()
            title = lines[0] if lines else rid
            # Try to parse Condition: and Outcome:
            cond = None
            outcome = None
            for ln in lines:
                if ln.lower().startswith('condition:'):
                    cond = ln.split(':',1)[1].strip()
                if ln.lower().startswith('outcome:') or ln.lower().startswith('result:'):
                    outcome = ln.split(':',1)[1].strip()
            rtype = 'Requirement'
            if 'rule' in block.lower() or 'validation' in block.lower():
                rtype = 'BusinessRule'
            elif 'ui' in block.lower() or 'screen' in block.lower() or 'control' in block.lower():
                rtype = 'UI'
            reqs.append({'id': rid, 'type': rtype, 'title': title, 'condition': cond, 'outcome': outcome, 'raw': block})
        return reqs

    # Fallback: split by headings (## or ###)
    sections = re.split(r'(^#{2,3}\s+)', text, flags=re.MULTILINE)
    cur_id = 1
    buf = []
    for part in sections:
        if part.strip().startswith('##') or part.strip().startswith('###'):
            # heading marker; skip
            continue
        if not part.strip():
            continue
        # assign an ID
        rid = f"REQ-{cur_id:03d}"
        title = part.splitlines()[0].strip()
        block = '\n'.join(part.splitlines()[1:]).strip()
        rtype = 'Requirement'
        if 'rule' in block.lower() or 'validation' in block.lower():
            rtype = 'BusinessRule'
        elif 'ui' in block.lower() or 'screen' in block.lower():
            rtype = 'UI'
        reqs.append({'id': rid, 'type': rtype, 'title': title, 'condition': None, 'outcome': None, 'raw': block})
        cur_id += 1

    return reqs


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print('Usage: requirements_parser.py <requirements.md>')
        sys.exit(2)
    out = parse_markdown_requirements(sys.argv[1])
    import json
    print(json.dumps(out, indent=2, ensure_ascii=False))
