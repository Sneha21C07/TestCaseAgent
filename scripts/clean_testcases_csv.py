import csv
import re
from pathlib import Path

IN_PATH = Path(__file__).parents[1] / 'Output' / 'Debug_Run' / 'Testcases_updated.csv'
OUT_PATH = Path(__file__).parents[1] / 'Output' / 'Debug_Run' / 'Testcases_updated.cleaned.csv'

TRUNCATE_AFTER = 16

# heuristics for e2e preservation: if Post_Verification mentions 'order number' or 'order status' or 'quote number' keep full
E2E_PATTERNS = re.compile(r'order number|order status|quote number|order status set', re.I)

# split patterns for post_verification to introduce newlines
SPLIT_KEYWORDS = [
    ' Coverage summary', ' Controls', ' Clicking', ' Message shown', ' Selecting', ' Cart updated',
    ' Changes have been made', ' Item counter', ' Search results', ' Service-added', ' Returned stock',
    ' Warning message', ' In-stock', ' Out-of-Stock', ' Add to cart is blocked', ' Add to cart is blocked until',
    ' Populated', ' Selecting', ' Switching', ' Returning', ' Clicking next', ' Clicking previous'
]

def split_post_verification(text):
    if not text or text.strip() == '':
        return text
    t = text.strip()
    # normalize multiple spaces
    t = re.sub(r"\s{2,}", " ", t)
    # insert newline before keywords
    for kw in SPLIT_KEYWORDS:
        t = t.replace(kw, '\n' + kw.strip())
    # also split on '. ' where sentences present
    t = re.sub(r'\.\s+', '.\n', t)
    # split into lines, strip
    lines = [ln.strip() for ln in t.split('\n') if ln.strip()]
    # if lines already numbered, keep but ensure numbering sequential
    new_lines = []
    num = 1
    for ln in lines:
        # remove existing numbering like '1.' or '1. '
        ln2 = re.sub(r'^\d+\.\s*', '', ln)
        new_lines.append(f"{num}. {ln2}")
        num += 1
    return '\\n'.join(new_lines)

# truncate order steps to first N numbered lines
def truncate_order_steps(os_text, keep=TRUNCATE_AFTER, preserve_e2e=False, post_ver=None):
    if not os_text or os_text.strip() == '':
        return os_text
    lines = [ln for ln in os_text.splitlines() if ln.strip()]
    if preserve_e2e and post_ver and E2E_PATTERNS.search(post_ver):
        return os_text
    # If already short, return as-is
    if len(lines) <= keep:
        return os_text
    # otherwise keep only first 'keep' lines
    kept = lines[:keep]
    return '\n'.join(kept)


def main():
    seen_first_tom04 = False
    rows = []
    with IN_PATH.open('r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        for r in reader:
            tom = r['TOM_NUM'].strip()
            # Rule 1: delete first TOM_04 entry (row 3)
            if tom == 'TOM_04' and not seen_first_tom04:
                seen_first_tom04 = True
                # skip this first occurrence
                continue
            rows.append(r)

    cleaned = []
    for r in rows:
        post = r.get('Post_Verification','')
        order_steps = r.get('Order_Steps','')
        # Determine if this row likely E2E (based on Post_Verification content)
        preserve_e2e = bool(E2E_PATTERNS.search(post))
        truncated = truncate_order_steps(order_steps, keep=TRUNCATE_AFTER, preserve_e2e=preserve_e2e, post_ver=post)
        normalized_post = split_post_verification(post)
        # Ensure TOM_NUM uniqueness: if duplicates exist (unlikely now), append suffix
        cleaned.append({
            'TOM_NUM': r['TOM_NUM'].strip(),
            'User_Journey': r.get('User_Journey','').strip(),
            'TOM Description': r.get('TOM Description','').strip(),
            'Order_Steps': truncated,
            'Post_Verification': normalized_post,
        })

    # write out with utf-8-sig and QUOTE_ALL
    with OUT_PATH.open('w', encoding='utf-8-sig', newline='') as f:
        fieldnames = ['TOM_NUM','User_Journey','TOM Description','Order_Steps','Post_Verification']
        writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        for r in cleaned:
            writer.writerow(r)

    print(f'Wrote cleaned CSV to {OUT_PATH}')

if __name__ == '__main__':
    main()
