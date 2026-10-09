"""Compare generated TOMs against a reference CSV and compute alignment metrics.

Outputs a JSON report with Scenario Alignment, Coverage Alignment, Business Depth,
UX Coverage, and lists of missing scenarios/logic gaps.
"""
import argparse
import csv
import json
import os
import re
from collections import Counter


def normalize(s: str) -> str:
    if not s:
        return ''
    s = s.lower()
    s = re.sub(r'[^a-z0-9\s]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    inter = a & b
    uni = a | b
    return len(inter) / len(uni)


def load_csv(path):
    rows = []
    with open(path, 'r', encoding='utf-8') as fh:
        reader = csv.DictReader(fh)
        for r in reader:
            rows.append(r)
    return rows


BUSINESS_KEYWORDS = ['plan', 'device', 'sim', 'wearable', 'accessory', 'discount', 'bundle', 'stock', 'rtsa', 'eligibility', 'save', 'resume', 'quota', 'limit']
UX_KEYWORDS = ['navigate', 'tap', 'click', 'open', 'back', 'resume', 'save', 'flow', 'journey']
SCENARIO_CHECKS = [
    ('device-first', ['device-first', 'device first', 'device-first flow']),
    ('plan-first', ['plan-first', 'plan first']),
    ('sim-only-qty>1', ['sim only', 'sim-only', 'sim only quantity', 'sim quantity']),
    ('wearables-max-5', ['wearable', 'wearables', 'max 5', 'maximum 5']),
    ('accessories-max-10', ['accessory', 'accessories', 'max 10', 'maximum 10']),
    ('rtsa-storage-change', ['storage change', 'rtsa storage', 'change storage']),
    ('rtsa-colour-change', ['colour change', 'color change', 'rtsa colour', 'rtsa color']),
    ('check-store-stock', ['store stock', 'check store', 'check stock']),
    ('save-resume-quote', ['save & resume', 'save resume', 'save quote', 'resume quote']),
]


def detect_keywords(text, keywords):
    t = normalize(text)
    words = set(t.split())
    found = [k for k in keywords if any(w in t for w in ([k] if isinstance(k,str) else k))]
    return found


def detect_scenario_flags(text):
    t = normalize(text)
    flags = set()
    for name, variants in SCENARIO_CHECKS:
        for v in variants:
            if v in t:
                flags.add(name)
                break
    return flags


def analyze(ref_csv, gen_csv, out_json):
    refs = load_csv(ref_csv)
    gens = load_csv(gen_csv)

    total_ref = len(refs)
    total_gen = len(gens)

    matched_refs = 0
    matched_gen_ids = set()
    business_depth_scores = []
    ux_scores = []
    missing_scenarios = []

    # precompute gen normalized sets for performance
    gen_norm = []
    for g in gens:
        txt = normalize(' '.join([g.get('User_Journey',''), g.get('TOM Description',''), g.get('Order_Steps','')]))
        gen_norm.append((g, set(txt.split())))

    for r in refs:
        best = None
        best_score = 0.0
        rtxt = normalize(' '.join([r.get('User_Journey',''), r.get('TOM Description',''), r.get('Order_Steps','')]))
        rset = set(rtxt.split())
        for g, gset in gen_norm:
            score = jaccard(rset, gset)
            if score > best_score:
                best_score = score
                best = g
        # consider matched if similarity >= 0.35
        if best_score >= 0.35:
            matched_refs += 1
            matched_gen_ids.add(best.get('TOM_NUM'))
            # business depth: count business keywords in both
            ref_bus = sum(1 for k in BUSINESS_KEYWORDS if k in rtxt)
            gen_bus = sum(1 for k in BUSINESS_KEYWORDS if k in normalize(best.get('TOM Description','') + ' ' + best.get('Order_Steps','')))
            if ref_bus>0:
                business_depth_scores.append(min(gen_bus / ref_bus, 1.0))
            # ux score: navigation/order presence
            ref_ux = any(k in rtxt for k in UX_KEYWORDS)
            gen_ux = any(k in normalize(best.get('Order_Steps','')) for k in UX_KEYWORDS)
            ux_scores.append(1.0 if (ref_ux and gen_ux) or (not ref_ux) else 0.0)
        else:
            missing_scenarios.append(r)

    scenario_alignment_pct = round(100.0 * matched_refs / max(1, total_ref),2)
    coverage_alignment_pct = round(100.0 * len(matched_gen_ids) / max(1, total_gen),2)
    business_depth_pct = round(100.0 * (sum(business_depth_scores)/len(business_depth_scores) if business_depth_scores else 1.0),2)
    ux_coverage_pct = round(100.0 * (sum(ux_scores)/len(ux_scores) if ux_scores else 1.0),2)

    # specific scenario presence checks
    scenario_presence = {}
    for name, variants in SCENARIO_CHECKS:
        found_in_ref = any(any(v in normalize((r.get('User_Journey','') + ' ' + r.get('TOM Description','') + ' ' + r.get('Order_Steps',''))) for v in variants) for r in refs)
        found_in_gen = any(any(v in normalize((g.get('User_Journey','') + ' ' + g.get('TOM Description','') + ' ' + g.get('Order_Steps',''))) for v in variants) for g in gens)
        scenario_presence[name] = {'in_reference': found_in_ref, 'in_generated': found_in_gen}

    report = {
        'total_reference_toms': total_ref,
        'total_generated_toms': total_gen,
        'scenario_alignment_pct': scenario_alignment_pct,
        'coverage_alignment_pct': coverage_alignment_pct,
        'business_depth_pct': business_depth_pct,
        'ux_coverage_pct': ux_coverage_pct,
        'missing_reference_matches_count': len(missing_scenarios),
        'missing_reference_examples': [ {'TOM_NUM': r.get('TOM_NUM'), 'TOM Description': r.get('TOM Description')} for r in missing_scenarios[:20] ],
        'scenario_presence_checks': scenario_presence,
    }

    os.makedirs(os.path.dirname(out_json), exist_ok=True)
    with open(out_json, 'w', encoding='utf-8') as fh:
        json.dump(report, fh, indent=2)

    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--reference', required=True)
    p.add_argument('--generated', required=True)
    p.add_argument('--out', required=True)
    args = p.parse_args()
    r = analyze(args.reference, args.generated, args.out)
    print(json.dumps(r, indent=2))


if __name__ == '__main__':
    main()
