import csv
import re
from pathlib import Path

IN = Path('Output/Debug_Run/Testcases_updated.csv')
OUT = IN.with_name('Testcases_updated.final.csv')

# Truncation specs: keep first N lines, then append final line (1-based step numbers)
TRUNCATIONS = {
    'TOM_04': (11, "12. Action: Click | Target: Add to Cart button | Input: N/A | Expected: Validation banner 'Please select plan or device' is displayed above listing tabs and Add to Cart is blocked"),
    'TOM_05': (11, "12. Action: Click | Target: Add to Cart button | Input: N/A | Expected: Validation banner 'Please select plan' is displayed and Add to Cart is blocked until a plan is selected"),
    'TOM_68': (10, "11. Action: Click | Target: Wearable 'Apple Watch Ultra 2' Select button | Input: N/A | Expected: Validation message 'Please select plan or device' is displayed and Wearables selection is blocked"),
    'TOM_69': (10, "11. Action: Click | Target: Accessory 'PlayStation 5' Select button | Input: N/A | Expected: Validation message 'Please select plan or device' is displayed and Accessories selection is blocked"),
    'TOM_70': (10, "11. Action: Click | Target: Device Care dropdown | Input: Vodafone Device Care | Expected: Device Care selection is disabled/blocked while no device is selected"),
    'TOM_73': (10, "11. Action: Verify | Target: Item Tile Warning Area | Input: N/A | Expected: Warning message 'Stock availability and/or Estimated Shipment Date (ESD) check failed...' is displayed and remains visible under impacted item tile"),
}


def normalize_post_verification(pv_text: str) -> str:
    if pv_text is None:
        return ''
    text = pv_text.strip()
    if text == '':
        return ''
    # Split into non-empty lines, strip leading hyphens and whitespace
    lines = [re.sub(r'^[-\s]+', '', l).strip() for l in text.splitlines() if l.strip()]
    # If already looks numbered, re-number sequentially
    if lines and re.match(r'^\d+\.', lines[0]):
        cleaned = [re.sub(r'^\d+\.\s*', '', l).strip() for l in lines]
        return '\n'.join(f"{i+1}. {cleaned[i]}" for i in range(len(cleaned)))
    # Otherwise join into a single string then split into sentences heuristically
    single = ' '.join(lines)
    # Split on sentence boundaries where next sentence likely starts with uppercase/number/quote/(
    parts = re.split(r"(?<=[.?!])\s+(?=[A-Z0-9\"(\')])", single)
    parts = [p.strip() for p in parts if p.strip()]
    if len(parts) == 0:
        return single
    return '\n'.join(f"{i+1}. {parts[i]}" for i in range(len(parts)))


# Read CSV with utf-8-sig to handle possible BOM
with IN.open('r', encoding='utf-8-sig', newline='') as fh:
    reader = csv.DictReader(fh)
    rows = list(reader)
    fieldnames = reader.fieldnames

# Remove duplicate TOMs, keep LAST occurrence for each TOM_NUM
last_index = {}
for idx, r in enumerate(rows):
    tom = r.get('TOM_NUM')
    last_index[tom] = idx

new_rows = []
for idx, r in enumerate(rows):
    tom = r.get('TOM_NUM')
    if last_index.get(tom) != idx:
        # skip earlier duplicate
        continue
    new_rows.append(r)

# Apply truncations
for r in new_rows:
    tom = r.get('TOM_NUM')
    if tom in TRUNCATIONS:
        keep, final_line = TRUNCATIONS[tom]
        steps = r.get('Order_Steps', '')
        lines = [ln for ln in steps.splitlines() if ln.strip()]
        # Take first `keep` lines (if available), then append final_line
        if len(lines) >= keep:
            new_lines = lines[:keep]
        else:
            new_lines = lines[:]
        # Ensure final_line is present as last step
        new_lines = new_lines[:keep] + [final_line]
        r['Order_Steps'] = '\n'.join(new_lines)

# Normalize Post_Verification for all rows (remove leading hyphens etc.)
for r in new_rows:
    pv = r.get('Post_Verification', '')
    r['Post_Verification'] = normalize_post_verification(pv)

# Verify TOM numbering continuity: ensure TOM_01..TOM_76 present exactly once
present_toms = [r.get('TOM_NUM') for r in new_rows]
missing_toms = [f'TOM_{i:02d}' for i in range(1, 77) if f'TOM_{i:02d}' not in present_toms]

# Write back with UTF-8 BOM and QUOTE_ALL
with OUT.open('w', encoding='utf-8-sig', newline='') as fh:
    writer = csv.DictWriter(fh, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
    writer.writeheader()
    for r in new_rows:
        writer.writerow(r)

# Print a brief summary to stdout for verification when the script runs
print(f"Wrote {OUT} ({len(new_rows)} rows). Missing TOMs: {missing_toms}")
