import csv
import re
from datetime import datetime

in_path = r"u:/Users/sc616138/Documents/UIUX_Siebel - J8 - Copy/UIUX_Siebel - J8 - Copy/Output/Debug_Run/generated_test_cases.76.clean.csv"
out_path = in_path  # overwrite

def normalize_steps(text):
    # split into lines
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    # remove leading numeric prefixes
    cleaned = [re.sub(r'^\s*\d+\.\s*', '', ln) for ln in lines]
    # replace Driver's License -> Passport
    cleaned = [ln.replace("Driver's License", "Passport") for ln in cleaned]
    # replace occurrences of common ID number patterns with A1111111
    cleaned = [re.sub(r"\b[A-Z]\d{6,}\b", "A1111111", ln) for ln in cleaned]
    # ensure expiry date exists; replace any Expiry patterns
    cleaned = [re.sub(r'(Expiry Date[:\s]*).+', r"\1 30/09/2037", ln) for ln in cleaned]
    return cleaned


def build_appendix(is_business=False):
    appendix = []
    if is_business:
        appendix += [
            "Action: Enter Text | Target: ABN/ACN field | Input: 14745900491 | Expected: ABN/ACN entered",
            "Action: Click | Target: Validate ABN button | Input: N/A | Expected: ABR Enquiry popup shown",
            "Action: Click | Target: ABR Enquiry popup result | Input: Select first entity | Expected: Entity selected",
            "Action: Select | Target: Customer Type | Input: Sole Trader | Expected: Customer Type set",
            "Action: Select | Target: Employee Range | Input: 10-49 | Expected: Employee Range set",
            "Action: Select | Target: Industry Type | Input: Business Services - Other | Expected: Industry set",
        ]
    else:
        appendix.append("Action: Enter Text | Target: CA PIN field | Input: 1378 | Expected: 4-digit CA PIN accepted")
    appendix += [
        "Action: Enter Text | Target: Address lookup | Input: 468 FRIEND Boulevard, BURWOOD NSW 3125 | Expected: Address suggestions displayed",
        "Action: Select | Target: Address suggestion | Input: LOC140100000821 | Expected: Address selected",
        "Action: Select | Target: Proposition | Input: Vodafone Postpaid Infinite MTM July 2026 | Expected: Proposition selected",
        "Action: Select | Target: Payment term | Input: 24 | Expected: Payment term applied",
        "Action: Click | Target: Add-on Vodafone Device Care | Input: N/A | Expected: Device Care added",
        "Action: Click | Target: Add-on Apple Watch Ultra 2 | Input: N/A | Expected: Wearable added",
        "Action: Click | Target: Add-on PlayStation 5 Disc Slim E | Input: N/A | Expected: Accessory added",
        "Action: Select | Target: Employment status | Input: Full Time | Expected: Employment status recorded",
        "Action: Enter Text | Target: Duration with employer (years) | Input: 5 | Expected: Years entered",
        "Action: Verify | Target: Total employment in months | Input: N/A | Expected: 60",
        "Action: Verify | Target: SIM allocation number | Input: 84000000000000000000 | Expected: 20-digit SIM allocation starting with 84",
        "Action: Enter Text | Target: IMEI field | Input: 352099001761481 | Expected: IMEI accepted",
        "Action: Verify | Target: MSISDN reservation | Input: N/A | Expected: MSISDN reserved",
        "Action: Verify | Target: Stock status - In Stock | Input: In Stock | Expected: Fulfillment order created immediately",
        "Action: Verify | Target: Stock status - Out of Stock | Input: Out of Stock - Connect Later | Expected: Connect Later fulfillment created",
    ]
    return appendix

rows = []
with open(in_path, newline='', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for r in reader:
        steps = normalize_steps(r['Order_Steps'])
        # detect business vs consumer
        desc = r.get('TOM Description', '') + r.get('User_Journey', '')
        is_business = bool(re.search(r'\bBusiness\b|ABN|ACN|Company|Business Services', desc, re.IGNORECASE))
        appendix = build_appendix(is_business)
        # avoid duplicating appendix if already present
        for a in appendix:
            if any(a.split('|')[0].strip() in s for s in steps):
                continue
            steps.append(a)
        # replace any occurrence of "Driver's License" previously done; ensure passport number presence
        # ensure there's an explicit Primary ID block; if not, add it
        if not any(re.search(r'Primary ID|Passport|ID Type', s, re.IGNORECASE) for s in steps):
            pid = [
                "Action: Select | Target: Primary ID Type | Input: Passport | Expected: Passport selected",
                "Action: Enter Text | Target: Primary ID Number | Input: A1111111 | Expected: Passport number accepted",
                "Action: Enter Text | Target: Primary ID Expiry Date | Input: 30/09/2037 | Expected: Expiry accepted",
            ]
            # insert after login steps if present (detect 'Login Submit' or similar)
            insert_at = 0
            for i,s in enumerate(steps[:5]):
                if 'Login Submit' in s or 'User authenticated' in s or 'Login' in s:
                    insert_at = i+1
            for idx, it in enumerate(pid):
                steps.insert(insert_at+idx, it)
        # renumber steps
        numbered = [f"{i+1}. {s}" for i,s in enumerate(steps)]
        r['Order_Steps'] = '\n'.join(numbered)
        # sanitize Post_Verification: ensure 1-3 plain assertions, no leading hyphens
        pv = r.get('Post_Verification','').strip()
        if pv:
            # split sentences and pick up to 3
            parts = re.split(r'[\n\.]\s*', pv)
            parts = [p.strip() for p in parts if p.strip()]
            parts = parts[:3]
            r['Post_Verification'] = ' '.join(parts)
        rows.append(r)

# write back
with open(out_path, 'w', newline='', encoding='utf-8-sig') as f:
    fieldnames = ['TOM_NUM','User_Journey','TOM Description','Order_Steps','Post_Verification']
    writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
    writer.writeheader()
    for r in rows:
        writer.writerow({k: r.get(k,'') for k in fieldnames})

print(f"Updated CSV written to {out_path}")
