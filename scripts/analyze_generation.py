"""Analyze generated TOMs against the Requirements Catalog (PINK v2) and produce metrics.

Usage:
  python analyze_generation.py --requirements <req_md> --toms debug/generated_toms.json --csv Output/Debug_Run/generated_test_cases.csv --trace Output/Debug_Run/traceability_matrix.csv --out Output/Debug_Run/analysis_report.json
"""
import argparse
import json
import csv
import os
from collections import defaultdict, Counter


def load_requirements(md_path):
    with open(md_path, 'r', encoding='utf-8') as fh:
        text = fh.read()
    # split into simple requirement blocks: headings + paragraph
    reqs = []
    cur_heading = None
    buf = []
    for ln in text.splitlines():
        if ln.strip().startswith('#'):
            if buf:
                reqs.append({'heading': cur_heading or '', 'text': ' '.join([l.strip() for l in buf if l.strip()])})
                buf = []
            cur_heading = ln.strip().lstrip('#').strip()
        else:
            buf.append(ln)
    if buf:
        reqs.append({'heading': cur_heading or '', 'text': ' '.join([l.strip() for l in buf if l.strip()])})
    # assign ids
    for i, r in enumerate(reqs, start=1):
        r['id'] = f'REQ-{i:04d}'
    return reqs


def load_toms(json_path):
    with open(json_path, 'r', encoding='utf-8') as fh:
        return json.load(fh)


def load_csv_rows(p):
    rows = []
    with open(p, 'r', encoding='utf-8') as fh:
        reader = csv.DictReader(fh)
        for r in reader:
            rows.append(r)
    return rows


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument('--requirements', required=True)
    p.add_argument('--toms', required=True)
    p.add_argument('--csv', required=True)
    p.add_argument('--trace', required=True)
    p.add_argument('--out', required=True)
    args = p.parse_args(argv)

    reqs = load_requirements(args.requirements)
    toms = load_toms(args.toms)
    csv_rows = load_csv_rows(args.csv)
    trace_rows = load_csv_rows(args.trace)

    total_toms = len(toms)
    # map req id -> tom kinds present
    req_map = {r['id']: r for r in reqs}
    req_coverage = defaultdict(list)
    for t in toms:
        rid = t.get('traceability_ids')
        kind = None
        desc = (t.get('TOM Description') or '').lower()
        for k in ['screen', 'journey', 'navigation', 'tab', 'section', 'control', 'action', 'state', 'message', 'validation']:
            if f'{k} test' in desc:
                kind = k
                break
        if not kind:
            kind = 'generic'
        if rid:
            # traceability_ids may be comma-separated
            for r in str(rid).split(','):
                req_coverage[r.strip()].append(kind)

    covered_reqs = [r for r in reqs if r['id'] in req_coverage]
    uncovered_reqs = [r for r in reqs if r['id'] not in req_coverage]

    requirements_coverage_pct = round(100.0 * len(covered_reqs) / max(1, len(reqs)), 2)

    # traceability coverage: TOMs that have traceability_ids
    toms_with_trace = [t for t in toms if t.get('traceability_ids')]
    traceability_coverage_pct = round(100.0 * len(toms_with_trace) / max(1, total_toms), 2)

    # duplicate TOMs
    tom_nums = [t.get('TOM_NUM') for t in toms]
    dup_counts = {k: v for k, v in Counter(tom_nums).items() if v > 1}

    # validation errors via validate_test_cases.py expectations: missing fields etc
    # quick checks
    missing_order = [t['TOM_NUM'] for t in toms if not t.get('Order_Steps')]
    missing_post = [t['TOM_NUM'] for t in toms if not t.get('Post_Verification')]

    # For PINK alignment: use the requirements file itself as reference (PINK v2)
    # Determine for each req which kinds were expected by scanning text
    def detect_expected_kinds(text):
        t = (text or '').lower()
        ex = set()
        if any(k in t for k in ['journey', 'flow']):
            ex.add('journey')
        if any(k in t for k in ['validate', 'validation', 'required', 'must']):
            ex.add('validation')
        if any(k in t for k in ['rule', 'business rule']):
            ex.add('business_rule')
        if any(k in t for k in ['rtsa', 'stock', 'inventory', 'in stock', 'out of stock']):
            ex.add('rtsa')
        if any(k in t for k in ['limit', 'max', 'minimum', 'maximum']):
            ex.add('boundary')
        return ex

    pink_expectations = {r['id']: detect_expected_kinds(r['heading'] + ' ' + r['text']) for r in reqs}

    # For each expectation, check presence in req_coverage kinds
    missing_scenarios = []
    missing_validations = []
    missing_business = []
    missing_rtsa = []
    missing_boundary = []
    for rid, expects in pink_expectations.items():
        kinds_present = set(req_coverage.get(rid, []))
        if 'journey' in expects and 'journey' not in kinds_present:
            missing_scenarios.append(rid)
        if 'validation' in expects and 'validation' not in kinds_present:
            missing_validations.append(rid)
        if 'business_rule' in expects and not any(k in kinds_present for k in ['action','control','validation']):
            missing_business.append(rid)
        if 'rtsa' in expects and not any(k in kinds_present for k in ['state','message']):
            missing_rtsa.append(rid)
        if 'boundary' in expects and not any(k in kinds_present for k in ['validation','state','action']):
            missing_boundary.append(rid)

    analysis = {
        'total_toms': total_toms,
        'total_requirements': len(reqs),
        'requirements_covered_count': len(covered_reqs),
        'requirements_coverage_pct': requirements_coverage_pct,
        'traceability_coverage_pct': traceability_coverage_pct,
        'uncovered_requirements': [r['id'] for r in uncovered_reqs],
        'duplicate_toms': dup_counts,
        'missing_order_steps': missing_order,
        'missing_post_verification': missing_post,
        'missing_scenarios': missing_scenarios,
        'missing_validations': missing_validations,
        'missing_business_rules': missing_business,
        'missing_rtsa_coverage': missing_rtsa,
        'missing_boundary_coverage': missing_boundary,
    }

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, 'w', encoding='utf-8') as fh:
        json.dump(analysis, fh, indent=2)

    print('Analysis written to', args.out)


if __name__ == '__main__':
    main()
