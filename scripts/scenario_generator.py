"""Generate TOMs (Test Objective Matrices) from flows and requirements.

Produces dictionaries suitable for CSV export and traceability mapping.
"""
from typing import List, Dict


def generate_toms_from_flows(flows: List[Dict], reqs: List[Dict]) -> List[Dict]:
    req_map = {r['id']: r for r in reqs}
    toms = []
    counter = 1
    for f in flows:
        tom_num = f"TOM-{counter:05d}"
        title = f"{f['name']}"
        desc = f"Auto-generated flow from {f['source_req']} using template"
        steps_text = ' | '.join([s.get('desc') for s in f.get('steps', [])])
        trace_ids = [f['source_req']] + f.get('related_requirements', [])
        tom = {
            'TOM_NUM': tom_num,
            'TOM Title': title,
            'TOM Description': desc,
            'Order_Steps': steps_text,
            'Traceability_IDs': ';'.join(trace_ids),
        }
        toms.append(tom)
        counter += 1
    return toms


if __name__ == '__main__':
    print('scenario_generator ready')
