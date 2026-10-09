import csv
import re
from datetime import datetime

in_path = r"u:/Users/sc616138/Documents/UIUX_Siebel - J8 - Copy/UIUX_Siebel - J8 - Copy/Output/Debug_Run/generated_test_cases.76.clean.csv"
out_path = r"u:/Users/sc616138/Documents/UIUX_Siebel - J8 - Copy/UIUX_Siebel - J8 - Copy/Output/Debug_Run/generated_test_cases.76.clean - Copy.csv"

# constants
LOGIN_USER = 'CAREUSER1'
LOGIN_PWD = 'P@ssword123'
FIRST_NAME = 'lokesh'
LAST_NAME = 'kumar'
DOB = '25/06/2004'
PHONE = '61439004328'
EMAIL = 'lokesh@tcs.com'
CA_PIN = '1378'
ABN = '14745900491'
PASSPORT_NO = 'A1111111'
PASSPORT_EXP = '30/09/2037'
EMPLOYER = 'TCS'
EMPLOYER_CONTACT = '61439006789'
DURATION_YEARS = '5'
DURATION_MONTHS = '60'
PAYMENT_TYPE = 'Direct Debit'
BSB = '012605'
ACCOUNT_NO = '7654324'
ACCOUNT_NAME = 'lokesh'
ADDRESS_TEXT = '177 PACIFIC DR, PORT MACQUARIE NSW 2444'
ADDRESS_LOC = 'LOC140100000821'
PROPOSITION = 'Vodafone Postpaid Infinite MTM July 2026'
PLAN_TILE = 'Vodafone Postpaid Infinite'
DEVICE = 'iPhone 17'
STORAGE = '256GB'
PAYMENT_TERM = '36'
DEVICE_CARE = 'Vodafone Device Care'
WEARABLE = 'Apple Watch Ultra 2'
ACCESSORY = 'PlayStation 5 Disc Slim E'
SIM_ICCID = '84123456789001234567'
IMEI = '352099001761481'
MSISDN = '61439004328'


def build_e2e_steps(is_business=False, tom_desc=''):
    steps = []
    # 1 Login
    steps.append(f"Action: Enter Text | Target: Login Username field | Input: {LOGIN_USER} | Expected: Username entered")
    steps.append(f"Action: Enter Text | Target: Login Password field | Input: {LOGIN_PWD} | Expected: Password entered")
    steps.append(f"Action: Click | Target: Login Submit button | Input: N/A | Expected: User authenticated and home accessible")
    # 2 Sales Calculator & customer details
    steps.append("Action: Click | Target: Sales Calculator | Input: N/A | Expected: Sales Calculator opened")
    steps.append(f"Action: Enter Text | Target: Customer First Name | Input: {FIRST_NAME} | Expected: First Name entered")
    steps.append(f"Action: Enter Text | Target: Customer Last Name | Input: {LAST_NAME} | Expected: Last Name entered")
    # 3 Address / Coverage check
    steps.append(f"Action: Enter Text | Target: Address Lookup field | Input: {ADDRESS_TEXT} | Expected: Address suggestions displayed")
    steps.append(f"Action: Select | Target: Address suggestion | Input: {ADDRESS_LOC} | Expected: Address selected and coverage context set")
    # 4 Navigate to Mobile PLP and perform search/filter/sort per TOM
    steps.append("Action: Click | Target: Mobile PLP tab | Input: N/A | Expected: Mobile PLP opened")

    # generic search/filter/sort steps will be appended by caller if needed
    # 5 Select plan and device
    steps.append(f"Action: Select | Target: Plan tile | Input: {PLAN_TILE} | Expected: Plan selected")
    steps.append(f"Action: Click | Target: Device Card '{DEVICE}' | Input: N/A | Expected: Device card opened")
    steps.append(f"Action: Select | Target: Storage option | Input: {STORAGE} | Expected: Storage selected")
    steps.append(f"Action: Select | Target: Payment term | Input: {PAYMENT_TERM} months | Expected: Payment term set")
    steps.append(f"Action: Click | Target: Add-on '{DEVICE_CARE}' | Input: N/A | Expected: Device care added")
    # 6 Add to cart, calculate, create quote
    steps.append("Action: Click | Target: Add to Cart button | Input: N/A | Expected: Item added to cart")
    steps.append("Action: Click | Target: Calculate Bundle & Save button | Input: N/A | Expected: Bundle calculated and saved")
    steps.append("Action: Click | Target: Create Quote button | Input: N/A | Expected: Quote created with quote number")
    # 7 Create Order and enter contact
    steps.append("Action: Click | Target: Create Order button | Input: N/A | Expected: Order screen opened")
    steps.append(f"Action: Enter Text | Target: DOB field | Input: {DOB} | Expected: DOB entered")
    steps.append(f"Action: Enter Text | Target: Contact Phone field | Input: {PHONE} | Expected: Phone entered")
    steps.append(f"Action: Enter Text | Target: Contact Email field | Input: {EMAIL} | Expected: Email entered")
    if is_business:
        steps.append(f"Action: Enter Text | Target: ABN/ACN field | Input: {ABN} | Expected: ABN/ACN entered")
        steps.append("Action: Click | Target: Validate ABN button | Input: N/A | Expected: ABR Enquiry popup shown")
        steps.append("Action: Click | Target: ABR Enquiry popup result | Input: Select first entity | Expected: Entity selected")
        steps.append("Action: Select | Target: Customer Type | Input: Sole Trader | Expected: Customer Type set")
        steps.append("Action: Select | Target: Employee Range | Input: 10-49 | Expected: Employee Range set")
        steps.append("Action: Select | Target: Industry Type | Input: Business Services - Other | Expected: Industry set")
    else:
        steps.append(f"Action: Enter Text | Target: CA PIN field | Input: {CA_PIN} | Expected: 4-digit CA PIN accepted")
    # 8 ID Validation
    steps.append(f"Action: Select | Target: Primary ID Type | Input: Passport | Expected: Passport selected")
    steps.append(f"Action: Enter Text | Target: Primary ID Number | Input: {PASSPORT_NO} | Expected: Passport number accepted")
    steps.append(f"Action: Enter Text | Target: Primary ID Expiry Date | Input: {PASSPORT_EXP} | Expected: Expiry date accepted")
    # 9 Credit Check
    steps.append(f"Action: Enter Text | Target: Employer field | Input: {EMPLOYER} | Expected: Employer entered")
    steps.append(f"Action: Enter Text | Target: Employer Contact field | Input: {EMPLOYER_CONTACT} | Expected: Employer contact entered")
    steps.append(f"Action: Enter Text | Target: Duration with employer (years) | Input: {DURATION_YEARS} | Expected: Years entered")
    steps.append(f"Action: Verify | Target: Total employment in months | Input: N/A | Expected: {DURATION_MONTHS}")
    steps.append("Action: Click | Target: Authorisation checkbox | Input: Checked | Expected: Authorisation recorded")
    steps.append("Action: Click | Target: Submit Credit Check button | Input: N/A | Expected: Credit check submitted")
    # 10 Billing
    steps.append(f"Action: Select | Target: Payment Type | Input: {PAYMENT_TYPE} | Expected: Payment type selected")
    steps.append(f"Action: Enter Text | Target: BSB | Input: {BSB} | Expected: BSB entered")
    steps.append(f"Action: Enter Text | Target: Account Number | Input: {ACCOUNT_NO} | Expected: Account number entered")
    steps.append(f"Action: Enter Text | Target: Account Name | Input: {ACCOUNT_NAME} | Expected: Account name entered")
    # 11 Customize & Proposition - MSISDN/IMSI/IMEI
    steps.append(f"Action: Click | Target: Allocate MSISDN | Input: N/A | Expected: MSISDN allocation requested")
    steps.append(f"Action: Enter Text | Target: SIM ICCID | Input: {SIM_ICCID} | Expected: SIM ICCID accepted")
    steps.append(f"Action: Enter Text | Target: IMEI | Input: {IMEI} | Expected: IMEI accepted")
    steps.append("Action: Click | Target: Mark as Ready button | Input: N/A | Expected: Line marked as Ready for provisioning")
    # 12 Review & Submit
    steps.append("Action: Click | Target: Submit Order button | Input: N/A | Expected: Order status set to Submitted and order number generated")

    # Add wearable or accessory if indicated by tom_desc
    lower = tom_desc.lower()
    if 'wearable' in lower or 'watch' in lower or 'apple watch' in lower:
        steps.insert(11, f"Action: Click | Target: Wearable '{WEARABLE}' | Input: N/A | Expected: Wearable added")
    if 'accessory' in lower or 'playstation' in lower or 'ps5' in lower:
        steps.insert(11, f"Action: Click | Target: Accessory '{ACCESSORY}' | Input: N/A | Expected: Accessory added")

    return steps


def transform_post_verification(pv):
    pv = (pv or '').strip()
    if not pv:
        return ''
    # split by sentences and newlines
    parts = re.split(r'[\n\.]+\s*', pv)
    parts = [p.strip() for p in parts if p.strip()]
    # keep up to 5 assertions to be safe, but number them
    parts = parts[:5]
    numbered = [f"{i+1}. {parts[i]}" for i in range(len(parts))]
    return '\n'.join(numbered)

rows = []
with open(in_path, newline='', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for r in reader:
        tom_desc = r.get('TOM Description','')
        user_journey = r.get('User_Journey','')
        is_business = bool(re.search(r'\bBusiness\b|ABN|ACN|Company|Business Services', tom_desc + ' ' + user_journey, re.IGNORECASE))
        # build canonical e2e steps
        steps = build_e2e_steps(is_business=is_business, tom_desc=tom_desc)

        # Insert search/sort/filter steps based on description
        desc_lower = (tom_desc + ' ' + user_journey).lower()
        extra = []
        if 'search' in desc_lower or 'search device' in desc_lower or 'search' in tom_desc.lower():
            extra.append(f"Action: Enter Text | Target: Search input field | Input: {DEVICE} | Expected: Search results filtered to {DEVICE}")
        if 'sort' in desc_lower or 'most popular' in desc_lower:
            extra.append("Action: Select Option | Target: Sort By dropdown | Input: Price (Low to High) | Expected: Listing sorted by price ascending")
        if 'filter' in desc_lower or 'filter by' in desc_lower:
            extra.append(f"Action: Click | Target: Filter by Brand checkbox | Input: Apple | Expected: Listing filtered to Apple devices")
        # wearables and accessories handled in build_e2e_steps

        # inject extras after opening Mobile PLP (after the Mobile PLP opened step)
        for i,s in enumerate(steps):
            if 'Mobile PLP opened' in s:
                insert_at = i+1
                for ex in reversed(extra):
                    steps.insert(insert_at, ex)
                break

        # Replace any occurrence of '<password>' in steps with real
        steps = [s.replace('<password>', LOGIN_PWD) for s in steps]

        # Number steps
        numbered = [f"{i+1}. {steps[i]}" for i in range(len(steps))]
        r['Order_Steps'] = '\n'.join(numbered)

        # Transform Post_Verification
        r['Post_Verification'] = transform_post_verification(r.get('Post_Verification',''))

        rows.append({
            'TOM_NUM': r.get('TOM_NUM',''),
            'User_Journey': r.get('User_Journey',''),
            'TOM Description': r.get('TOM Description',''),
            'Order_Steps': r['Order_Steps'],
            'Post_Verification': r['Post_Verification']
        })

# write out
with open(out_path, 'w', newline='', encoding='utf-8-sig') as f:
    fieldnames = ['TOM_NUM','User_Journey','TOM Description','Order_Steps','Post_Verification']
    writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
    writer.writeheader()
    for r in rows:
        writer.writerow(r)

print(f"Wrote updated file to: {out_path}")
