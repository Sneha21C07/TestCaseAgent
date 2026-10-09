import csv
import re
from pathlib import Path


def normalize(input_path, output_path):
    changes = []
    with open(input_path, 'r', encoding='utf-8-sig', newline='') as rf:
        reader = csv.DictReader(rf)
        fieldnames = reader.fieldnames
        rows = list(reader)

    if not fieldnames:
        print('No columns found in input CSV')
        return

    for row in rows:
        tom = row.get('TOM_NUM') or row.get('"TOM_NUM"') or ''
        order = (row.get('Order_Steps') or '')
        post = (row.get('Post_Verification') or '')

        if 'Quote header shows customer' not in post:
            continue

        # extract first/last from Order_Steps
        first = re.search(r'Customer First Name\s*\|\s*Input:\s*([^\|\n]+)', order, re.I)
        last = re.search(r'Customer Last Name\s*\|\s*Input:\s*([^\|\n]+)', order, re.I)
        full_name = ''
        if first:
            full_name = first.group(1).strip()
        if last:
            if full_name:
                full_name = full_name + ' ' + last.group(1).strip()
            else:
                full_name = last.group(1).strip()

        if not full_name:
            # nothing to normalize to
            continue

        # preserve quote number if present
        qnum_m = re.search(r'quote number\s*[:]?\s*(\d+)', post, re.I)
        qnum = qnum_m.group(1) if qnum_m else None

        # remove existing quote number fragments to avoid duplication
        post_no_q = re.sub(r'[,;]?\s*quote number\s*[:]?\s*\d+', '', post, flags=re.I)

        # replace the customer part
        post_replaced = re.sub(r'(Quote header shows customer)\s*[^,\n]*', r"\1 " + full_name, post_no_q, flags=re.I)

        # append quote number if it existed originally
        if qnum:
            # ensure separator
            if not re.search(r'quote number', post_replaced, re.I):
                post_replaced = post_replaced.strip()
                if not post_replaced.endswith(',') and not post_replaced.endswith('.'):
                    post_replaced = post_replaced + ', '
                post_replaced = post_replaced + f'quote number {qnum}'

        # cleanup extra whitespace and commas
        post_replaced = re.sub(r'\s+,', ',', post_replaced)
        post_replaced = re.sub(r'\s{2,}', ' ', post_replaced).strip()

        if post_replaced != post:
            changes.append((tom, post, post_replaced))
            row['Post_Verification'] = post_replaced

    outp = Path(output_path)
    with open(outp, 'w', encoding='utf-8', newline='') as wf:
        writer = csv.DictWriter(wf, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    # print summary
    print(f'Processed {len(rows)} rows, updated {len(changes)} Post_Verification entries')
    for tom, before, after in changes:
        print(f'- {tom}:')
        print(f'  BEFORE: {before[:200]}')
        print(f'  AFTER : {after[:200]}')


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 3:
        print('Usage: normalize_quote_header.py <input.csv> <output.csv>')
        sys.exit(2)
    normalize(sys.argv[1], sys.argv[2])
