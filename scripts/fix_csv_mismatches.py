import csv
import re
import sys

in_path = sys.argv[1]
out_path = sys.argv[2]

with open(in_path, newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    rows = list(reader)
    fieldnames = reader.fieldnames

quote_re = re.compile(r"Quote header shows customer ([^,\n]+)", flags=re.IGNORECASE)
first_re = re.compile(r"Customer First Name \| Input: (.*?) \|", flags=re.IGNORECASE)
last_re = re.compile(r"Customer Last Name \| Input: (.*?) \|", flags=re.IGNORECASE)
addr_re = re.compile(r"Address Lookup field \| Input: (.*?) \|", flags=re.IGNORECASE)
phone_re = re.compile(r"Contact Phone field \| Input: (.*?) \|", flags=re.IGNORECASE)
email_re = re.compile(r"Contact Email field \| Input: (.*?) \|", flags=re.IGNORECASE)

# generic address-like pattern to spot addresses in Post_Verification
post_addr_re = re.compile(r"\d{1,4}\s+[A-Za-z0-9\s\.\-]+?,\s*[A-Za-z\s]+,\s*\d{3,4}")

changed = 0
changes_detail = []
for idx, row in enumerate(rows, start=1):
    order = row.get('Order_Steps') or ''
    post = row.get('Post_Verification') or ''

    # 1) Fix customer name in Quote header
    m1 = first_re.search(order)
    m2 = last_re.search(order)
    if m1 and m2 and post:
        first = m1.group(1).strip()
        last = m2.group(1).strip()
        desired_name = f"{first} {last}"
        qm = quote_re.search(post)
        if qm:
            existing = qm.group(1).strip()
            if existing.lower() != desired_name.lower():
                post = quote_re.sub(f"Quote header shows customer {desired_name}", post)
                row['Post_Verification'] = post
                changed += 1
                changes_detail.append((row.get('TOM_NUM','?'), 'customer', existing, desired_name))

    # 2) Fix address mentions in Post_Verification to match Order_Steps
    ma = addr_re.search(order)
    if ma and post:
        desired_addr = ma.group(1).strip()
        pam = post_addr_re.search(post)
        if pam:
            existing_addr = pam.group(0).strip()
            if existing_addr.lower() != desired_addr.lower():
                post = post_addr_re.sub(desired_addr, post)
                row['Post_Verification'] = post
                changed += 1
                changes_detail.append((row.get('TOM_NUM','?'), 'address', existing_addr, desired_addr))

    # 3) Fix phone/email if mentioned in Post_Verification
    mp = phone_re.search(order)
    me = email_re.search(order)
    if mp and post:
        desired_phone = mp.group(1).strip()
        if desired_phone and desired_phone not in post:
            # replace any phone-like sequence in post if present
            post_phone_re = re.compile(r"\b\d{9,15}\b")
            pph = post_phone_re.search(post)
            if pph:
                existing_phone = pph.group(0)
                if existing_phone != desired_phone:
                    post = post_phone_re.sub(desired_phone, post, count=1)
                    row['Post_Verification'] = post
                    changed += 1
                    changes_detail.append((row.get('TOM_NUM','?'), 'phone', existing_phone, desired_phone))
    if me and post:
        desired_email = me.group(1).strip()
        if desired_email and desired_email.lower() not in post.lower():
            # replace any email-like sequence in post if present
            post_email_re = re.compile(r"[\w\.-]+@[\w\.-]+")
            peh = post_email_re.search(post)
            if peh:
                existing_email = peh.group(0)
                if existing_email.lower() != desired_email.lower():
                    post = post_email_re.sub(desired_email, post, count=1)
                    row['Post_Verification'] = post
                    changed += 1
                    changes_detail.append((row.get('TOM_NUM','?'), 'email', existing_email, desired_email))

# write out
with open(out_path, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
    writer.writeheader()
    for r in rows:
        writer.writerow(r)

print(f"Processed {len(rows)} rows, updated {changed} Post_Verification entries.")
