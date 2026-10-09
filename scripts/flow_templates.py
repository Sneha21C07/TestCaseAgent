"""Reusable flow templates that produce step lists for common UI/UX patterns.

Templates are intentionally high-level and must be combined with real requirement
titles and actions by the flow builder.
"""
from typing import List, Dict


def template_device_first(req: Dict, related: List[Dict]) -> List[Dict]:
    steps = [
        {'action': 'open_page', 'target': 'Product Listing Page', 'desc': 'Open PLP'},
        {'action': 'select_device', 'target': req.get('title'), 'desc': f"Select device: {req.get('title')}"},
        {'action': 'add_to_cart', 'target': 'device', 'desc': 'Add device to cart'},
        {'action': 'select_plan', 'target': 'compatible plan', 'desc': 'Select compatible plan'},
        {'action': 'verify_cart', 'target': 'cart', 'desc': 'Verify cart updated with device+plan'}
    ]
    return steps


def template_plan_first(req: Dict, related: List[Dict]) -> List[Dict]:
    steps = [
        {'action': 'open_page', 'target': 'Product Listing Page', 'desc': 'Open PLP'},
        {'action': 'select_plan', 'target': req.get('title'), 'desc': f"Select plan: {req.get('title')}"},
        {'action': 'choose_device', 'target': 'device', 'desc': 'Choose compatible device (if required)'},
        {'action': 'add_to_cart', 'target': 'plan+device', 'desc': 'Add selected configuration to cart'}
    ]
    return steps


def template_rtsa(req: Dict, related: List[Dict]) -> List[Dict]:
    steps = [
        {'action': 'check_stock', 'target': 'RTSA/stock', 'desc': 'Check stock for selected variant'},
        {'action': 'choose_variant', 'target': 'color/storage', 'desc': 'Select colour/storage variant'},
        {'action': 'verify_variant_update', 'target': 'UI', 'desc': 'Verify UI updates for variant'}
    ]
    return steps


def template_save_resume(req: Dict, related: List[Dict]) -> List[Dict]:
    steps = [
        {'action': 'configure_offer', 'target': 'quote', 'desc': 'Configure quote (device+plan)'},
        {'action': 'save_quote', 'target': 'quote', 'desc': 'Save current quote'},
        {'action': 'resume_quote', 'target': 'quote', 'desc': 'Resume saved quote and verify state'}
    ]
    return steps


def template_store_stock(req: Dict, related: List[Dict]) -> List[Dict]:
    steps = [
        {'action': 'search_store', 'target': 'store availability', 'desc': 'Search store stock'},
        {'action': 'reserve_in_store', 'target': 'reservation', 'desc': 'Reserve device in selected store'},
        {'action': 'verify_reservation', 'target': 'UI', 'desc': 'Verify reservation confirmation'}
    ]
    return steps


def template_validation(req: Dict, related: List[Dict]) -> List[Dict]:
    steps = [
        {'action': 'input_invalid', 'target': 'field', 'desc': 'Enter invalid values to trigger validation'},
        {'action': 'verify_message', 'target': 'validation message', 'desc': 'Verify validation message shown'}
    ]
    return steps
