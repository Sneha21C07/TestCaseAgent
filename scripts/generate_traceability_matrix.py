"""Generate a traceability matrix CSV linking TOMs to requirements."""
import argparse
import csv
import json
import os
from typing import List, Dict


def load_requirements(md_path: str) -> List[Dict]:
    with open(md_path, 'r', encoding='utf-8') as fh:
        return fh.read().splitlines()


def load_tests(csv_path: str) -> List[Dict]:
    rows = []
    with open(csv_path, 'r', encoding='utf-8') as fh:
        reader = csv.DictReader(fh)
        for r in reader:
            rows.append(r)
    return rows


def simple_trace_map(requirements_lines: List[str], tests: List[Dict]) -> List[Dict]:
    # naive: map by substring match of test description in requirements text
    req_text = "\n".join(requirements_lines)
    out = []
    for t in tests:
        req_matches = []
        # check for traceability_ids first
        if t.get('traceability_ids'):
            req_matches = [t['traceability_ids']]
        else:
            desc = t.get('TOM Description', '')
            if desc and desc in req_text:
                # not exact mapping but capture as found
                req_matches.append('FOUND_IN_REQS')
        # use test description as fallback requirement text
        desc = t.get('TOM Description', '')
        out.append({
            'TOM_NUM': t.get('TOM_NUM'),
            'Requirement_ID': ','.join(req_matches) if req_matches else '',
            'Requirement_Text': desc[:200],
            'Requirement_Source': 'Requirements Catalog',
            'Coverage_Type': 'AutoMapped',
        })
    return out


def write_csv(path: str, rows: List[Dict], headers: List[str]):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', newline='', encoding='utf-8') as fh:
        writer = csv.DictWriter(fh, fieldnames=headers, extrasaction='ignore')
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument('--requirements', required=True)
    p.add_argument('--csv', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--debug')
    args = p.parse_args(argv)

    req_lines = load_requirements(args.requirements)
    tests = load_tests(args.csv)
    matrix = simple_trace_map(req_lines, tests)

    headers = ['TOM_NUM', 'Requirement_ID', 'Requirement_Text', 'Requirement_Source', 'Coverage_Type']
    write_csv(args.out, matrix, headers)

    if args.debug:
        os.makedirs(args.debug, exist_ok=True)
        with open(os.path.join(args.debug, 'traceability_debug.json'), 'w', encoding='utf-8') as fh:
            json.dump(matrix, fh, indent=2, ensure_ascii=False)
    print(f"Wrote traceability matrix to {args.out}")


if __name__ == '__main__':
    main()
