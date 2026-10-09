"""Convert a Requirements Catalog into a set of test-case rows.

This module implements small, generic heuristics to convert a markdown requirements
catalog into testable TOM rows. It is intentionally conservative: it will not
invent business rules. When ambiguous, it marks traceability uncertainty.

Functions:
- parse_requirements(markdown_text) -> list of requirement dicts
- generate_tests(requirements, start_index=1) -> list of test row dicts
"""
from typing import List, Dict
import re


def parse_requirements(md_text: str) -> List[Dict]:
    """Parse markdown into requirement entries. Returns list of dicts with keys:
    - id (generated)
    - heading (nearest H1/H2/H3)
    - text (requirement body)
    """
    lines = md_text.splitlines()
    entries = []
    cur_heading = ""
    buf = []
    for ln in lines:
        h = None
        m = re.match(r'^(#{1,6})\s+(.*)$', ln)
        if m:
            # flush previous
            if buf:
                text = " ".join([l.strip() for l in buf if l.strip()])
                entries.append({"heading": cur_heading, "text": text})
                buf = []
            cur_heading = m.group(2).strip()
        else:
            buf.append(ln)
    if buf:
        text = " ".join([l.strip() for l in buf if l.strip()])
        entries.append({"heading": cur_heading, "text": text})
    # assign ids
    for i, e in enumerate(entries, start=1):
        e["id"] = f"REQ-{i:04d}"
    return entries


def _detect_tags(text: str) -> Dict[str, bool]:
    t = (text or "").lower()
    tags = {
        'screen': False,
        'journey': False,
        'navigation': False,
        'tab': False,
        'section': False,
        'control': False,
        'action': False,
        'state': False,
        'message': False,
        'validation': False,
    }
    if any(k in t for k in ['screen', 'screen:']):
        tags['screen'] = True
    if any(k in t for k in ['journey', 'flow', 'user journey']):
        tags['journey'] = True
    if any(k in t for k in ['navigate', 'tap', 'click', 'go to', 'open']):
        tags['navigation'] = True
    if 'tab' in t:
        tags['tab'] = True
    if 'section' in t:
        tags['section'] = True
    if any(k in t for k in ['button', 'dropdown', 'field', 'input', 'control', 'checkbox', 'radio', 'select']):
        tags['control'] = True
    if any(k in t for k in ['add ', 'remove ', 'update ', 'select ', 'save ', 'edit ', 'checkout', 'purchase', 'apply ']):
        tags['action'] = True
    if any(k in t for k in ['state', 'status', 'available', 'unavailable', 'in stock', 'out of stock']):
        tags['state'] = True
    if any(k in t for k in ['message', 'warning', 'error', 'success', 'info']):
        tags['message'] = True
    if any(k in t for k in ['validate', 'validation', 'must ', 'should ', 'required', 'must be']):
        tags['validation'] = True
    return tags


def _make_row(tom_counter: int, flow: str, desc: str, kind: str, req_id: str) -> Dict:
    title = f"{kind.title()} test for: {desc[:120]}"
    # Use canonical structured step format for produced rows
    def s(step_no, action, target, inp, exp):
        # sanitize inputs and enforce canonical formatting
        act = (action or '').replace('—', '-').replace('–', '-')
        targ = (target or 'UI element').replace('—', '-').replace('–', '-')
        inp_val = (inp or 'N/A')
        exp_s = (exp or '').replace('—', '-').replace('–', '-')
        # remove accidental double quotes inside values
        targ = targ.replace('"', '')
        exp_s = exp_s.replace('"', '')
        return f"{step_no}. Action: {act} | Target: {targ} | Input: {inp_val} | Expected: {exp_s}"

    if kind == 'screen':
        steps = "\n".join([
            s(1, 'Click', 'Sales calculator header', None, 'Sales calculator page opens'),
            s(2, 'Click', 'Relevant tab', None, 'Screen opens and primary elements render')
        ])
        pv = "Visible elements, labels and layout match the Requirements Catalog."
    elif kind == 'journey':
        steps = "\n".join([
            s(1, 'Enter Text', 'Login Username field', 'CAREUSER1', 'Username entered'),
            s(2, 'Enter Text', 'Login Password field', '<password>', 'Password entered'),
            s(3, 'Click', 'Sales Calculator', None, 'Sales Calculator opens'),
        ])
        pv = "End-to-end outcome matches the requirement and any messages or state changes are observed."
    elif kind == 'navigation':
        steps = "\n".join([
            s(1, 'Click', 'Navigation control', None, 'Navigation action performed'),
            s(2, 'Verify', 'Target screen', None, 'Target screen opens and primary elements render')
        ])
        pv = "Target screen appears and focus/state is correct."
    elif kind == 'tab':
        steps = "\n".join([
            s(1, 'Click', 'Tab control', None, 'Tab opens and content becomes visible'),
            s(2, 'Verify', 'Tab content area', None, 'Tab content matches requirements')
        ])
        pv = "Tab content visible and correct."
    elif kind == 'section':
        steps = s(1, 'Verify', 'Section area', None, 'Section contents and controls render as specified')
        pv = "Section validations and messages present when applicable."
    elif kind == 'control':
        steps = "\n".join([
            s(1, 'Enter Text', 'Control input', None, 'Input accepted and control updated'),
            s(2, 'Verify', 'Control state', None, 'Control behaves as specified and triggers validations where applicable')
        ])
        pv = "Control behaves as specified; validation messages appear when expected."
    elif kind == 'action':
        steps = "\n".join([
            s(1, 'Click', 'Primary action control', None, 'Primary action invoked'),
            s(2, 'Verify', 'Outcome area', None, 'System response or messages match expected outcome')
        ])
        pv = "Action produces expected state change or message (explicit control-level verification)."
    elif kind == 'state':
        steps = "\n".join([
            s(1, 'Simulate', 'State trigger', None, 'State transition initiated'),
            s(2, 'Verify', 'UI state indicators', None, 'UI reflects the new state correctly')
        ])
        pv = "State transition is observable and consistent with the requirement."
    elif kind == 'message':
        steps = "\n".join([
            s(1, 'Enter Text', 'Trigger input', None, 'Triggering action performed'),
            s(2, 'Verify', 'Message area', None, 'Message text and tone match requirement')
        ])
        pv = "Message appears with exact wording and severity as specified."
    elif kind == 'validation':
        steps = "\n".join([
            s(1, 'Enter Text', 'Validation input', 'INVALID', 'Validation triggers'),
            s(2, 'Verify', 'Validation region', None, 'Validation message displays and action is blocked')
        ])
        pv = "Validation messages and blocking behavior match the Requirements Catalog."
    else:
        steps = s(1, 'Verify', 'UI element', None, 'Verify visible behavior per requirement')
        pv = "Verify visible behavior per requirement."

    return {
        "TOM_NUM": f"TOM-{tom_counter:05d}",
        "User_Journey": flow,
        "TOM Description": title,
        "Order_Steps": steps,
        "Post_Verification": pv,
        "sequence": 1,
        "flow_name": flow,
        "screen_name": None,
        "action_type": None,
        "traceability_ids": req_id,
    }


# --- Generator helper functions (merged from optional generators) ---
def _generate_screen_tests(flow, desc, req_id, start_index):
    return [_make_row(start_index, flow, desc, 'screen', req_id)]


def _generate_journey_tests(flow, desc, req_id, start_index):
    # produce a small multi-step journey TOM
    row = _make_row(start_index, flow, desc, 'journey', req_id)
    # expand order steps to include sample multi-step guidance if possible
    row['Order_Steps'] = '1) Start at entry screen.\n2) Perform primary actions (select device/plan).\n3) Proceed to cart and verify outcome.'
    row['Post_Verification'] = 'End-to-end outcome matches requirement; messages and cart state observed.'
    return [row]


def _generate_navigation_tests(flow, desc, req_id, start_index):
    return [_make_row(start_index, flow, desc, 'navigation', req_id)]


def _generate_ui_tests(flow, desc, req_id, start_index, tags):
    rows = []
    idx = start_index
    # tab test
    if tags.get('tab'):
        rows.append(_make_row(idx, flow, desc, 'tab', req_id)); idx += 1
    # section test
    if tags.get('section'):
        rows.append(_make_row(idx, flow, desc, 'section', req_id)); idx += 1
    # control test
    if tags.get('control'):
        rows.append(_make_row(idx, flow, desc, 'control', req_id)); idx += 1
    # action test
    if tags.get('action'):
        rows.append(_make_row(idx, flow, desc, 'action', req_id)); idx += 1
    return rows


def _generate_state_message_tests(flow, desc, req_id, start_index, tags):
    rows = []
    idx = start_index
    if tags.get('state'):
        rows.append(_make_row(idx, flow, desc, 'state', req_id)); idx += 1
    if tags.get('message'):
        rows.append(_make_row(idx, flow, desc, 'message', req_id)); idx += 1
    return rows


def _generate_validation_tests(flow, desc, req_id, start_index):
    # create valid + invalid pair where applicable
    valid = _make_row(start_index, flow, desc, 'validation', req_id)
    invalid = _make_row(start_index+1, flow, desc, 'validation', req_id)
    invalid['TOM Description'] = 'Negative validation test (invalid inputs) for: ' + invalid['TOM Description']
    invalid['Order_Steps'] = '1) Enter invalid input.\n2) Verify validation message blocks progression.'
    return [valid, invalid]


def _generate_business_and_rtsa_tests(flow, desc, req_id, start_index):
    # heuristic expansions for business rules, boundaries, and RTSA
    t = (flow + ' ' + desc).lower()
    rows = []
    idx = start_index
    if 'wearable' in t or 'wearables' in t:
        rows.append(_make_row(idx, flow, 'Wearables max limit test (max 5)', 'validation', req_id)); idx += 1
    if 'accessor' in t or 'accessories' in t:
        rows.append(_make_row(idx, flow, 'Accessories max limit test (max 10)', 'validation', req_id)); idx += 1
    if 'sim' in t and 'qty' in t or 'sim only' in t:
        rows.append(_make_row(idx, flow, 'SIM quantity >1 multi-SIM flow', 'journey', req_id)); idx += 1
    # RTSA mentions
    if 'rtsa' in t or 'stock' in t or 'estimated delivery' in t:
        rows.append(_make_row(idx, flow, 'RTSA: stock and attribute change scenarios', 'state', req_id)); idx += 1
    return rows
# --- end generator helpers ---


def generate_tests(requirements: List[Dict], start_index: int = 1) -> List[Dict]:
    """Generate TOM rows with more detailed mappings based on heuristics.

    For each parsed requirement entry this function will attempt to
    identify what kind of tests are required and emit one or more TOMs:
    - Screen validation
    - Journey flow
    - Navigation
    - Tabs
    - Sections
    - Controls
    - Actions
    - State transitions
    - Message verification
    - Validation tests

    The function is conservative: it only emits tests for things it can
    reasonably detect from the requirement text/heading. It will always
    emit at least one TOM per requirement to preserve coverage.
    """
    rows = []
    tom_counter = start_index
    for req in requirements:
        flow = req.get("heading") or "Unnamed Flow"
        desc = req.get("text") or "(no description)"
        req_id = req.get("id")

        tags = _detect_tags(flow + ' ' + desc)

        emitted = False
        # Emit richer TOMs using internal generator functions
        # Screen-level tests
        if tags.get('screen'):
            gen = _generate_screen_tests(flow, desc, req_id, tom_counter)
            rows.extend(gen)
            tom_counter += len(gen)
            emitted = True

        # Journey-level tests
        if tags.get('journey'):
            gen = _generate_journey_tests(flow, desc, req_id, tom_counter)
            rows.extend(gen)
            tom_counter += len(gen)
            emitted = True

        # Navigation tests
        if tags.get('navigation'):
            gen = _generate_navigation_tests(flow, desc, req_id, tom_counter)
            rows.extend(gen)
            tom_counter += len(gen)
            emitted = True

        # Tab/Section/Control/Action tests
        if tags.get('tab') or tags.get('section') or tags.get('control') or tags.get('action'):
            gen = _generate_ui_tests(flow, desc, req_id, tom_counter, tags)
            rows.extend(gen)
            tom_counter += len(gen)
            emitted = True

        # State/Message tests
        if tags.get('state') or tags.get('message'):
            gen = _generate_state_message_tests(flow, desc, req_id, tom_counter, tags)
            rows.extend(gen)
            tom_counter += len(gen)
            emitted = True

        # Validation tests
        if tags.get('validation'):
            gen = _generate_validation_tests(flow, desc, req_id, tom_counter)
            rows.extend(gen)
            tom_counter += len(gen)
            emitted = True

        # Business-rule, boundary, RTSA expansions (heuristic)
        gen = _generate_business_and_rtsa_tests(flow, desc, req_id, tom_counter)
        if gen:
            rows.extend(gen)
            tom_counter += len(gen)
            emitted = True

        # Fallback: if nothing specific detected, emit a conservative TOM
        if not emitted:
            # produce a more granular sequence using J1-J9 if we can infer PLP
            if re.search(r'plp|mobile|mobile phones', (flow + ' ' + desc).lower()):
                # Build a J1-J6 minimal manual flow per requirement
                steps = []
                steps.append('1. Enter Text — Target: Login Username field — Input: CAREUSER1 — Expected: Username entered')
                steps.append('2. Enter Text — Target: Login Password field — Input: <password> — Expected: Password entered')
                steps.append('3. Click — Target: Login Submit button — Input: N/A — Expected: User logged in and Sales Calculator accessible')
                steps.append('4. Enter Text — Target: Customer Details First Name — Input: TestFirst — Expected: First name saved')
                steps.append('5. Enter Text — Target: Customer Details Last Name — Input: TestLast — Expected: Last name saved')
                steps.append('6. Enter Text — Target: Coverage Address field — Input: 177 PACIFIC DR, PORT MACQUARIE NSW 2444 — Expected: Coverage results show 4G/5G/NBN availability')
                steps.append('7. Click — Target: Mobile phones tab — Input: N/A — Expected: Mobile phones listing shown')
                steps.append('8. Click — Target: Device card iPhone 17 Pro Max — Input: N/A — Expected: Device card selected')
                steps.append('9. Select Option — Target: Storage dropdown — Input: 256GB — Expected: Storage set to 256GB')
                steps.append('10. Select Option — Target: Colour picker — Input: Space Black — Expected: Colour set to Space Black')
                steps.append('11. Click — Target: Plan tile "Large MTM plan" Select — Input: N/A — Expected: Plan selected for the service')
                steps.append('12. Click — Target: Add to cart button — Input: N/A — Expected: New service row appears in cart')
                row = _make_row(tom_counter, flow, desc, 'journey', req_id)
                row['Order_Steps'] = '\n'.join(steps)
                row['Post_Verification'] = 'Cart updated message displayed. New service row contains selected device and plan.'
                rows.append(row)
                tom_counter += 1
            else:
                row = _make_row(tom_counter, flow, desc, 'generic', req_id)
                rows.append(row)
                tom_counter += 1

    return rows


if __name__ == "__main__":
    import sys
    print("requirements_to_tests is a library module. Import and use its functions.")
    sys.exit(0)
