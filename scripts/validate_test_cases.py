"""Validate generated test-cases CSV against required rules."""
import argparse
import csv
import json
import os
from collections import Counter


REQUIRED_COLUMNS = ['TOM_NUM', 'User_Journey', 'TOM Description', 'Order_Steps', 'Post_Verification']


def load_tests(csv_path: str):
    with open(csv_path, 'r', encoding='utf-8') as fh:
        reader = csv.DictReader(fh)
        rows = [r for r in reader]
    return rows


def validate(rows):
    report = {
        'total_toms': len(rows),
        'missing_columns': [],
        'missing_order_steps': [],
        'missing_post_verification': [],
        'duplicate_toms': [],
        'hallucinated': [],
    }
    # column check
    if rows:
        cols = rows[0].keys()
        for c in REQUIRED_COLUMNS:
            if c not in cols:
                report['missing_columns'].append(c)

    # content checks
    toms = [r.get('TOM_NUM') for r in rows]
    dups = [k for k, v in Counter(toms).items() if v > 1]
    report['duplicate_toms'] = dups

    for r in rows:
        if not r.get('Order_Steps'):
            report['missing_order_steps'].append(r.get('TOM_NUM'))
        if not r.get('Post_Verification'):
            report['missing_post_verification'].append(r.get('TOM_NUM'))
        # Hallucination detection is heuristic: no traceability and very short description
        if not r.get('traceability_ids') and len((r.get('TOM Description') or '').strip()) < 10:
            report['hallucinated'].append(r.get('TOM_NUM'))
    return report


def write_report(path: str, report: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(report, fh, indent=2)


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument('--csv', required=True)
    p.add_argument('--requirements')
    p.add_argument('--out', required=True)
    p.add_argument('--debug')
    args = p.parse_args(argv)

    rows = load_tests(args.csv)
    report = validate(rows)
    write_report(args.out, report)
    if args.debug:
        os.makedirs(args.debug, exist_ok=True)
        with open(os.path.join(args.debug, 'testcase_validation_report.json'), 'w', encoding='utf-8') as fh:
            json.dump(report, fh, indent=2)
    print(f"Wrote validation report to {args.out}")


if __name__ == '__main__':
    main()
