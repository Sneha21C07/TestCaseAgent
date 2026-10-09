"""Build end-to-end flows by matching requirements to templates using the index."""
from typing import List, Dict
from .flow_templates import (
    template_device_first,
    template_plan_first,
    template_rtsa,
    template_save_resume,
    template_store_stock,
    template_validation,
)


def choose_template_for_requirement(req: Dict) -> str:
    title = (req.get('title') or '').lower()
    raw = (req.get('raw') or '').lower()
    if 'device' in title or 'device' in raw:
        return 'device_first'
    if 'plan' in title or 'plan' in raw:
        return 'plan_first'
    if 'rtsa' in title or 'stock' in raw or 'variant' in raw:
        return 'rtsa'
    if 'save' in raw or 'resume' in raw or 'quote' in raw:
        return 'save_resume'
    if 'store' in raw or 'in store' in raw:
        return 'store_stock'
    if 'validation' in raw or 'validate' in raw or 'error' in raw:
        return 'validation'
    return 'device_first'


def build_flows(reqs: List[Dict], index) -> List[Dict]:
    flows = []
    for r in reqs:
        template_name = choose_template_for_requirement(r)
        related = index.related_requirements(r['id'], top_n=5)
        if template_name == 'device_first':
            steps = template_device_first(r, related)
        elif template_name == 'plan_first':
            steps = template_plan_first(r, related)
        elif template_name == 'rtsa':
            steps = template_rtsa(r, related)
        elif template_name == 'save_resume':
            steps = template_save_resume(r, related)
        elif template_name == 'store_stock':
            steps = template_store_stock(r, related)
        elif template_name == 'validation':
            steps = template_validation(r, related)
        else:
            steps = template_device_first(r, related)

        flow = {'flow_id': f"FLOW-{r['id']}", 'name': f"{template_name}:{r['id']}", 'source_req': r['id'], 'steps': steps, 'related_requirements': [x['id'] for x in related]}
        flows.append(flow)
    return flows


if __name__ == '__main__':
    import sys, json
    print('flow_builder ready')
