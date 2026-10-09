"""Generate a coverage report markdown summarising coverage metrics."""
import argparse
import csv
import json
import os
from collections import Counter


def load_requirements(md_path: str) -> str:
    with open(md_path, 'r', encoding='utf-8') as fh:
        return fh.read()


def load_tests(csv_path: str):
    rows = []
    with open(csv_path, 'r', encoding='utf-8') as fh:
        reader = csv.DictReader(fh)
        for r in reader:
            rows.append(r)
    return rows


def compute_coverage(requirements_text: str, tests: list) -> dict:
    # naive metrics by scanning available fields
    screens = set([t.get('screen_name') for t in tests if t.get('screen_name')])
    actions = set([t.get('action_type') for t in tests if t.get('action_type')])
    validations = [t for t in tests if t.get('Post_Verification')]
    traces = [t for t in tests if t.get('traceability_ids')]
    metrics = {
        'screens_covered': len(screens),
        'actions_covered': len([a for a in actions if a]),
        'validations_covered': len(validations),
        'toms_total': len(tests),
        'traceable_toms': len(traces),
    }
    # Coverage % approximations
    metrics['traceability_coverage_pct'] = round(100.0 * metrics['traceable_toms'] / max(1, metrics['toms_total']), 2)
    return metrics


def write_md(path: str, metrics: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write('# Coverage Report\n\n')
        for k, v in metrics.items():
            fh.write(f'- {k.replace("_", " ").title()}: {v}\n')


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument('--requirements', required=True)
    p.add_argument('--csv', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--debug')
    args = p.parse_args(argv)

    req_text = load_requirements(args.requirements)
    tests = load_tests(args.csv)
    metrics = compute_coverage(req_text, tests)
    write_md(args.out, metrics)

    if args.debug:
        os.makedirs(args.debug, exist_ok=True)
        with open(os.path.join(args.debug, 'coverage_debug.json'), 'w', encoding='utf-8') as fh:
            json.dump(metrics, fh, indent=2)
    print(f"Wrote coverage report to {args.out}")


if __name__ == '__main__':
    main()
