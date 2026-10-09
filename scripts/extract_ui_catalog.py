#!/usr/bin/env python3
"""
Extract UI catalog from OCR-extracted Figma markdown.

Usage:
  python scripts/extract_ui_catalog.py \
    --input path/to/figma_ocr.md \
    --output path/to/ui_catalog.json
"""

from __future__ import annotations

import argparse
import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

LOG = logging.getLogger("extract_ui_catalog")

SECTION_KEYS = [
    "navigation",
    "header",
    "tabs",
    "filters",
    "sections",
    "subsections",
    "fields",
    "labels",
    "controls",
    "actions",
    "buttons",
    "links",
    "popups",
    "notifications",
    "states",
    "messages",
    "transitions",
    "notes",
]

NON_SCREEN_HEADINGS = {
    "overview",
    "journey flow",
    "usage notes",
    "hld enrichments",
    "example validation & ui messages",
    "rtsa / estimated delivery and stock hints",
}

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
BACKTICK_RE = re.compile(r"`([^`]+)`")
QUOTED_RE = re.compile(r'"([^"]+)"')
TAB_SPLIT_RE = re.compile(r"\s*[|/>]\s*|\s+and\s+|\s*,\s*")
PAGE_MARKER = "File Edit View Navigate Query Tools Help Site map Tasks iHelp Quick links"

ACTION_HINTS = (
    "button",
    "buttons",
    "action",
    "actions",
    "link",
    "links",
    "select",
    "add to cart",
    "save",
    "search",
    "configure",
    "edit",
    "remove",
    "clear selection",
    "check store stock",
    "store stock",
    "create quote",
    "create order",
    "calculate bundle",
    "view purchase",
)

MESSAGE_HINTS = (
    "message",
    "validation",
    "warning",
    "success",
    "error",
    "failed",
    "not allowed",
    "required",
    "please",
)

STATE_HINTS = (
    "in stock",
    "out of stock",
    "low stock",
    "back order",
    "selected",
    "no new services added",
    "service added to cart",
    "quote submitted",
    "quote in progress",
    "quote rejected",
    "cart updated",
)

CONTROL_HINTS = (
    "input",
    "checkbox",
    "drop-down",
    "dropdown",
    "field",
    "fields",
    "control",
    "controls",
    "radio",
    "select",
    "button",
    "buttons",
)

COMMON_ACTION_PHRASES = [
    "Search",
    "Select",
    "Add to cart",
    "Update cart",
    "Save quote and exit",
    "Clear selection",
    "Create quote",
    "Create order",
    "Calculate Bundle & Save",
    "View purchase & offer details",
    "Check store stock",
    "Store stock",
    "Edit",
    "Remove",
    "Configure service",
    "Go back",
    "Cancel editing",
    "Save and add to cart",
    "Apply promocode",
    "Remove service",
    "Add item",
    "Resume Quote",
    "Search all quotes",
]

COMMON_NAVIGATION_PHRASES = [
    "Service request",
    "Customer accounts",
    "Assets",
    "CVP operations",
    "Add new service",
    "Mobile",
    "Fixed",
    "Coverage check",
]

COMMON_CONTROL_PHRASES = [
    "Suburb or postcode",
    "Same as coverage check",
    "Sort by",
    "Filter by vendor",
    "Filter by",
    "Show all",
    "APP payment term",
    "checkbox",
    "input",
    "Search another address",
]

COMMON_SECTION_PHRASES = [
    "Brand name",
    "Product name",
    "In stock",
    "From:",
    "Model",
    "Storage",
    "Colour",
    "Case size",
    "Band",
    "Band size",
    "Payment term",
    "APP payment term",
    "Device care",
    "Plan name",
    "Contract type",
    "Critical information summary",
    "Rates and charges",
    "Estimated delivery date",
    "Vendor",
    "Product code",
    "RRP inc. GST",
    "Bundle name",
    "Bundle benefit",
    "NBN + Voice Plan Bundle",
    "Typical evening speeds",
    "Due today",
    "Next expected monthly bill",
    "Recurring charges",
    "One time charges",
    "Total",
    "no image available",
]

COMMON_STATE_PHRASES = [
    "In stock",
    "Out of stock",
    "Low Stock",
    "Back-order",
    "Selected",
    "0 item selected",
    "1 Selected",
    "Service added to cart",
    "No new services added",
    "Currently editing",
]

COMMON_NOTE_PHRASES = [
    "no image available",
    "You are editing",
    "Want configuration?",
    "Restricted access enabled",
]

COMMON_FILTER_PHRASES = [
    "Sort by",
    "Filter by vendor",
    "Show all",
    "Filter by brand",
]

COMMON_ATTRIBUTE_PHRASES = [
    "APP payment term",
    "Product code",
    "Vendor",
    "Estimated delivery date",
    "Model",
    "Colour",
    "Case size",
    "Band",
    "Band size",
    "Payment term",
    "RRP inc. GST",
]

CANONICAL_TAB_NAMES = {
    "mobile phones": "Mobile Phones",
    "tablets & mbb": "Tablets & MBB",
    "wearables": "Wearables",
    "accessories": "Accessories",
    "bundles": "Bundle & Save",
}

LOCAL_SCREEN_LABELS = {
    "mobiles": "Mobile phones",
    "tablets": "Tablets & MBB",
    "wearables": "Wearables",
    "accessories": "Accessories",
    "bundles": "Bundles",
}

KNOWN_SCREEN_BOUNDARIES = [
    {
        "name": "Cart",
        "signals": ["cart updated", "create quote", "create order", "new services"],
        "start_tokens": ["cart updated", "new services"],
        "end_tokens": ["purchase & offer details", "save quote and exit"],
    },
    {
        "name": "Purchase & Offer Details",
        "signals": ["purchase & offer details", "offer impacts are highlighted", "total discounts"],
        "start_tokens": ["purchase & offer details"],
        "end_tokens": ["close", "customer details", "coverage check"],
    },
    {
        "name": "Bundle & Save",
        "signals": ["calculate bundle & save", "bundle name", "bundle benefit", "nbn + voice plan bundle"],
        "start_tokens": ["bundle name", "calculate bundle & save", "nbn + voice plan bundle"],
        "end_tokens": ["purchase & offer details", "customer details", "save quote and exit"],
    },
    {
        "name": "Edit Service",
        "signals": ["edit service", "edit in cart", "proposition and customise", "customise"],
        "start_tokens": ["edit service", "edit in cart", "proposition and customise"],
        "end_tokens": ["back to cart", "pause order", "purchase & offer details"],
    },
]

TARGETED_SCREEN_ANCHORS = {
    "Mobile Phones": {
        "start_tokens": ["Mobiles Check delivery estimate", "Mobile phones Tablets & MBB Bundles Wearables Accessories Mobiles Check delivery estimate"],
        "end_tokens": ["Save quote and exit Clear selection Add to cart", "Due today Next expected monthly bill"],
    },
    "Tablets & MBB": {
        "start_tokens": ["Tablets Check delivery estimate", "Tablets & MBB Bundles Wearables Tablets Check delivery estimate"],
        "end_tokens": ["Save quote and exit Clear selection Add to cart", "Due today Next expected monthly bill"],
    },
    "Wearables": {
        "start_tokens": ["Wearables Check delivery estimate"],
        "end_tokens": ["Save quote and exit Clear selection Add to cart", "Due today Next expected monthly bill"],
    },
    "Accessories": {
        "start_tokens": ["Accessories Check delivery estimate"],
        "end_tokens": ["Save quote and exit Clear selection Add to cart", "Due today Next expected monthly bill"],
    },
    "Bundle & Save": {
        "start_tokens": [
            "Bundle and save calculation is completed.",
            "The items in your cart are not eligible for bundle and save.",
            "Values not updated",
            "Bundle name",
        ],
        "end_tokens": ["Edit service", PAGE_MARKER],
    },
    "Edit Service": {
        "start_tokens": ["Edit service You are editing", "Edit service", "Currently editing New service"],
        "end_tokens": ["If TBUI configurator Save Service added to cart", "Cart Purchase & offer details", PAGE_MARKER],
    },
}

MESSAGE_NORMALIZATION_RULES = [
    (r"cart\s+updated", "Cart updated Changes have been made to your order successfully. Select a new item below, edit another service or click Create quote or Create order to continue.", "success"),
    (r"bundle\s*&?\s*save.*completed", "Bundle and save calculation is completed.", "success"),
    (r"not\s+eligible\s+for\s+bundle\s*&?\s*save", "The items in your cart are not eligible for bundle and save.", "warning"),
    (r"values\s+not\s+updated", "Values not updated Some items in your cart need final values to be calculated before proceeding. Please click Calculate Bundle & Save to update pricing and proceed.", "warning"),
    (r"not\s+compatible|incompatible", "Some options are not compatible with a previous request.", "error"),
    (r"4g\s*-\s*available", "4G - Available", "info"),
    (r"5g\s*-\s*outdoor\s+only", "5G - Outdoor only", "info"),
    (r"5g\s*nsa\s*-\s*not\s+available", "5G NSA - Not available", "info"),
    (r"service\s+added\s+to\s+cart", "Service added to cart.", "success"),
    (r"no\s+new\s+services\s+added", "No new services added.", "info"),
]

SECTION_TO_REQUIREMENT_TYPE = {
    "navigation": "ui_navigation",
    "header": "ui_header",
    "tabs": "ui_tab",
    "filters": "ui_filter",
    "sections": "ui_section",
    "subsections": "ui_subsection",
    "fields": "ui_field",
    "labels": "ui_label",
    "controls": "ui_control",
    "actions": "ui_action",
    "buttons": "ui_action",
    "links": "ui_action",
    "popups": "ui_popup",
    "notifications": "ui_notification",
    "states": "ui_state",
    "messages": "ui_message",
    "transitions": "ui_transition",
    "notes": "ui_note",
}


@dataclass
class Screen:
    name: str
    sections: Dict[str, List[str]] = field(default_factory=lambda: {k: [] for k in SECTION_KEYS})
    blocks: List[dict] = field(default_factory=list)


@dataclass
class UICatalog:
    feature_name: str
    overview: List[str] = field(default_factory=list)
    journey_flow: List[str] = field(default_factory=list)
    screens: List[Screen] = field(default_factory=list)
    tabs: List[str] = field(default_factory=list)
    screen_reconstruction: List[dict] = field(default_factory=list)


def parse_scope_terms(scope_text: str | None) -> List[str]:
    if not scope_text:
        return []
    parts = re.split(r"[|,;\n]+", scope_text)
    return [normalize_text(part).lower() for part in parts if normalize_text(part)]


def split_flattened_pages(text: str) -> List[str]:
    if PAGE_MARKER not in text:
        return [text]
    parts = text.split(PAGE_MARKER)
    pages: List[str] = []
    for idx, part in enumerate(parts):
        normalized = normalize_text(part)
        if not normalized:
            continue
        if idx == 0:
            pages.append(normalized)
        else:
            pages.append(normalize_text(PAGE_MARKER + " " + part))
    return pages


def extract_subsegment(text: str, start_token: str, end_tokens: List[str], max_len: int = 1800) -> str:
    lower = text.lower()
    start = lower.find(start_token.lower())
    if start < 0:
        return ""
    end = len(text)
    for token in end_tokens:
        idx = lower.find(token.lower(), start + 1)
        if idx > start:
            end = min(end, idx)
    segment = normalize_text(text[start:end])
    if len(segment) > max_len:
        segment = segment[:max_len]
    return segment


def extract_first_matching_segment(text: str, start_tokens: List[str], end_tokens: List[str], max_len: int = 2600) -> str:
    for start_token in start_tokens:
        segment = extract_subsegment(text, start_token, end_tokens, max_len=max_len)
        if segment:
            return segment
    return ""


def phrase_present(text: str, phrase: str) -> bool:
    return phrase.lower() in text.lower()


def pick_phrases(text: str, phrases: List[str], limit: int = 12) -> List[str]:
    out: List[str] = []
    lower = text.lower()
    for phrase in phrases:
        if phrase.lower() in lower and phrase not in out:
            out.append(phrase)
        if len(out) >= limit:
            break
    return out


def extract_message_phrases(text: str, limit: int = 10) -> List[str]:
    lower = text.lower()
    messages: List[str] = []

    canonical_patterns = [
        ("cart updated", "Cart updated Changes have been made to your order successfully. Select a new item below, edit another service or click Create quote or Create order to continue."),
        ("bundle and save calculation is completed", "Bundle and save calculation is completed."),
        ("not eligible for bundle and save", "The items in your cart are not eligible for bundle and save."),
        ("values not updated", "Values not updated Some items in your cart need final values to be calculated before proceeding. Please click Calculate Bundle & Save to update pricing and proceed."),
        ("some options are not compatible with a previous request", "Some options are not compatible with a previous request."),
        ("4g - available", "4G - Available"),
        ("5g - outdoor only", "5G - Outdoor only"),
        ("5g nsa - not available", "5G NSA - Not available"),
        ("service added to cart", "Service added to cart."),
        ("no new services added", "No new services added."),
    ]

    for token, canonical in canonical_patterns:
        if token in lower and canonical not in messages:
            messages.append(canonical)
        if len(messages) >= limit:
            break

    return messages


def canonical_screen_name(name: str) -> str:
    normalized = normalize_text(name)
    return CANONICAL_TAB_NAMES.get(normalized.lower(), normalized)


def count_repeated_control_groups(text: str) -> int:
    lower = text.lower()
    control_groups = [
        ["brand name", "product name", "in stock"],
        ["storage", "colour", "payment term"],
        ["plan name", "contract type", "critical information summary"],
    ]
    matches = 0
    for group in control_groups:
        if sum(1 for token in group if token in lower) >= 3:
            matches += 1
    return matches


def find_best_start(text: str, candidates: List[str]) -> int:
    lower = text.lower()
    starts = [lower.find(token.lower()) for token in candidates if lower.find(token.lower()) >= 0]
    return min(starts) if starts else -1


def slice_segment(text: str, start_tokens: List[str], end_tokens: List[str], max_len: int = 1800) -> str:
    start = find_best_start(text, start_tokens)
    if start < 0:
        return ""
    segment = extract_subsegment(text[start:], text[start:], end_tokens, max_len=max_len)
    if segment:
        return segment
    clipped = normalize_text(text[start: start + max_len])
    return clipped


def normalize_message_entry(text: str) -> dict | None:
    normalized = normalize_text(text)
    if not normalized:
        return None
    lower = normalized.lower()
    for pattern, canonical, severity in MESSAGE_NORMALIZATION_RULES:
        if re.search(pattern, lower):
            return {
                "raw_text": normalized,
                "normalized_text": canonical,
                "severity": severity,
                "confidence": 0.92,
            }
    if any(k in lower for k in ["please", "error", "warning", "failed", "not allowed", "cannot"]):
        return {
            "raw_text": normalized,
            "normalized_text": normalized,
            "severity": "warning" if "warning" in lower or "please" in lower else "error",
            "confidence": 0.74,
        }
    return None


def extract_normalized_messages(text: str) -> List[dict]:
    entries: List[dict] = []
    seen: set[str] = set()
    lower = text.lower()
    for pattern, canonical, severity in MESSAGE_NORMALIZATION_RULES:
        if re.search(pattern, lower) and canonical not in seen:
            seen.add(canonical)
            entries.append(
                {
                    "raw_text": canonical,
                    "normalized_text": canonical,
                    "severity": severity,
                    "confidence": 0.92,
                }
            )
    return entries


def extract_attribute_value_phrases(text: str) -> List[str]:
    patterns = [
        (r"Colour\s+([A-Za-z]+)", "Colour"),
        (r"Case size\s+(\d{2}mm)", "Case size"),
        (r"Band\s+([A-Za-z]+(?:\s+[A-Za-z]+){0,2})", "Band"),
        (r"Band size\s+([A-Za-z0-9/]+)", "Band size"),
        (r"Payment term\s+(\d+\s+months)", "Payment term"),
        (r"APP payment term\s+(\d+\s+months)", "APP payment term"),
        (r"Model\s+([A-Za-z0-9]+(?:\s+[A-Za-z0-9]+){0,2})", "Model"),
        (r"Product code\s+([A-Z0-9/.-]{3,20})", "Product code"),
        (r"Vendor\s+([A-Z]{2,10}|[A-Za-z]{2,20})", "Vendor"),
        (r"Estimated delivery date\s+(\d{2}/\d{2}/\d{4})", "Estimated delivery date"),
    ]
    found: List[str] = []
    normalized = normalize_text(text)
    for pattern, label in patterns:
        for match in re.findall(pattern, normalized, flags=re.IGNORECASE):
            value = normalize_text(match)
            if label == "Vendor" and value.lower() in {"show", "filter", "brand"}:
                continue
            if label == "Model" and value.endswith(" Product"):
                value = value[: -len(" Product")].rstrip()
            if label == "Band" and value.endswith(" Band"):
                value = value[: -len(" Band")].rstrip()
            cleaned = f"{label} {value}".strip()
            if cleaned and cleaned not in found:
                found.append(cleaned)
    return found


def build_screen_from_segment(name: str, source_text: str, known_tabs: List[str]) -> Screen:
    screen = Screen(name=name)
    navigation = pick_phrases(source_text, COMMON_NAVIGATION_PHRASES, limit=8)
    tabs = pick_phrases(source_text, known_tabs, limit=8)
    actions = pick_phrases(source_text, COMMON_ACTION_PHRASES, limit=12)
    controls = pick_phrases(source_text, COMMON_CONTROL_PHRASES, limit=10)
    filters = pick_phrases(source_text, COMMON_FILTER_PHRASES, limit=8)
    sections = pick_phrases(source_text, COMMON_SECTION_PHRASES, limit=16)
    attributes = pick_phrases(source_text, COMMON_ATTRIBUTE_PHRASES, limit=16)
    attribute_values = extract_attribute_value_phrases(source_text)
    states = pick_phrases(source_text, COMMON_STATE_PHRASES, limit=10)
    fields = pick_phrases(source_text, ["Suburb or postcode", "Same as coverage check", "APP payment term"], limit=10)
    labels = pick_phrases(source_text, ["Due today", "Next expected monthly bill", "Recurring charges", "One time charges", "Total"], limit=10)
    notes = pick_phrases(source_text, COMMON_NOTE_PHRASES, limit=6)
    normalized_messages = [x["normalized_text"] for x in extract_normalized_messages(source_text)]
    if not normalized_messages:
        if "service added to cart" in source_text.lower():
            normalized_messages.append("Service added to cart.")
        if "no new services added" in source_text.lower():
            normalized_messages.append("No new services added.")
        if "0 item selected" in source_text.lower():
            normalized_messages.append("0 item selected")
        if "4g - available" in source_text.lower():
            normalized_messages.extend(["4G - Available", "5G - Outdoor only", "5G NSA - Not available"])
    popups = [m for m in normalized_messages if "Values not updated" in m or "Cart updated" in m]
    notifications = [m for m in normalized_messages if "calculation is completed" in m or "Service added to cart" in m or "Cart updated" in m]

    add_unique(screen.sections["navigation"], navigation)
    add_unique(screen.sections["tabs"], [canonical_screen_name(t) if t in CANONICAL_TAB_NAMES.values() else t for t in tabs])
    add_unique(screen.sections["actions"], actions)
    add_unique(screen.sections["filters"], filters)
    add_unique(screen.sections["controls"], controls)
    add_unique(screen.sections["sections"], sections + attributes + attribute_values)
    add_unique(screen.sections["states"], states)
    add_unique(screen.sections["fields"], fields)
    add_unique(screen.sections["labels"], labels)
    add_unique(screen.sections["messages"], normalized_messages)
    add_unique(screen.sections["popups"], popups)
    add_unique(screen.sections["notifications"], notifications)
    add_unique(screen.sections["notes"], notes)
    if "Sales calculator" in source_text:
        add_unique(screen.sections["header"], ["Sales calculator"])
    return screen


def merge_screen_sections(target: Screen, source: Screen) -> None:
    for key in SECTION_KEYS:
        add_unique(target.sections[key], source.sections.get(key, []))


def screen_density(screen: Screen) -> int:
    return sum(len(screen.sections.get(key, [])) for key in ["filters", "sections", "fields", "controls", "actions", "states", "messages"])


def reconstruct_screen_segments(page_text: str, page_index: int, known_tabs: List[str]) -> List[dict]:
    segments: List[dict] = []
    active_tab = detect_active_tab(page_text, known_tabs)
    repeated_groups = count_repeated_control_groups(page_text)
    if active_tab and repeated_groups >= 2:
        segment = extract_subsegment(
            page_text,
            active_tab,
            [
                "purchase & offer details",
                "cart updated",
                "edit service",
                "edit in cart",
                "bundle name",
                "calculate bundle & save",
            ],
            max_len=2200,
        )
        if segment:
            segments.append(
                {
                    "name": canonical_screen_name(active_tab),
                    "source_page": page_index,
                    "source_heading": active_tab,
                    "source_text": segment,
                    "boundary_type": "tab_hierarchy",
                    "confidence": 0.94,
                }
            )

    for spec in KNOWN_SCREEN_BOUNDARIES:
        lower = page_text.lower()
        if not any(signal in lower for signal in spec["signals"]):
            continue
        segment = slice_segment(page_text, spec["start_tokens"], spec["end_tokens"], max_len=2200)
        if segment:
            segments.append(
                {
                    "name": spec["name"],
                    "source_page": page_index,
                    "source_heading": spec["name"],
                    "source_text": segment,
                    "boundary_type": "known_boundary",
                    "confidence": 0.9,
                }
            )

    if not segments and repeated_groups >= 2 and active_tab:
        segments.append(
            {
                "name": canonical_screen_name(active_tab),
                "source_page": page_index,
                "source_heading": active_tab,
                "source_text": compact_text_for_flow(page_text, max_len=2200),
                "boundary_type": "repeated_control_group",
                "confidence": 0.72,
            }
        )

    # Deduplicate by screen name while retaining highest-confidence segment.
    best: Dict[str, dict] = {}
    for segment in segments:
        name = segment["name"]
        if name not in best or segment.get("confidence", 0) > best[name].get("confidence", 0):
            best[name] = segment
    return list(best.values())


def detect_active_tab(page: str, known_tabs: List[str]) -> str:
    idx = page.lower().find("check delivery estimate")
    if idx < 0:
        return ""
    local_window = normalize_text(page[max(0, idx - 60): idx + 30])
    for label, tab in LOCAL_SCREEN_LABELS.items():
        if re.search(rf"\b{re.escape(label)}\b\s+check delivery estimate", local_window, flags=re.IGNORECASE):
            return tab

    window = normalize_text(page[max(0, idx - 220): idx + 30])
    best_tab = ""
    best_pos = -1
    for tab in known_tabs:
        pos = window.lower().rfind(tab.lower())
        if pos > best_pos:
            best_pos = pos
            best_tab = tab

    if best_tab:
        return best_tab

    match = re.search(r"([A-Za-z&/ ]{3,30})\s+Check delivery estimate", window, flags=re.IGNORECASE)
    if match:
        return clean_title(match.group(1))
    return ""


def infer_screen_name_from_page(text: str, index: int) -> str:
    checks = [
        ("Mobiles", "Mobile PLP — Screen: Mobiles (primary elements)"),
        ("Tablets", "Mobile PLP — Tablets & MBB (same structure as Mobiles)"),
        ("Wearables", "Mobile PLP — Wearables"),
        ("Accessories", "Mobile PLP — Accessories"),
        ("Bundles", "Mobile PLP — Bundles"),
    ]
    lower = text.lower()
    if "edit service" in lower or "configurator" in lower:
        return "Configurator / Edit service (from Figma export)"
    if "cart updated" in lower or "purchase & offer details" in lower:
        return "Cart / Quote interactions (from Figma export)"
    for token, mapped in checks:
        if token.lower() in lower:
            return mapped

    match = re.search(r"([A-Z][A-Za-z& ]{2,40})\s+Check delivery estimate", text)
    if match:
        return f"Screen: {clean_title(match.group(1))}"
    return f"Scoped Screen {index}"


def parse_flattened_ocr(md_text: str, figma_scope_terms: List[str]) -> UICatalog:
    catalog = UICatalog(feature_name="Feature Name")
    lines = [normalize_text(x) for x in md_text.splitlines() if normalize_text(x)]
    merged = " ".join(lines)
    if not merged:
        return catalog

    heading_guess = re.search(r"([A-Z][A-Za-z0-9/&\- ]{3,80})", merged)
    if heading_guess:
        catalog.feature_name = clean_title(heading_guess.group(1)) or "Feature Name"

    pages = split_flattened_pages(merged)

    known_tabs = ["Mobile phones", "Tablets & MBB", "Bundles", "Wearables", "Accessories"]

    def _is_scope_relevant(page_text: str) -> bool:
        lower = page_text.lower()
        if any(term in lower for term in figma_scope_terms):
            return True
        tab_hits = sum(1 for t in known_tabs if t.lower() in lower)
        if tab_hits >= 3:
            return True
        if "cart updated" in lower and ("create quote" in lower or "bundle & save" in lower):
            return True
        return False

    if figma_scope_terms:
        scoped_pages = [p for p in pages if _is_scope_relevant(p)]
        if scoped_pages:
            pages = scoped_pages

    if pages:
        first = pages[0]
        tab_candidates = [
            "Mobile phones",
            "Tablets & MBB",
            "Bundles",
            "Wearables",
            "Accessories",
        ]
        tabs = pick_phrases(first, tab_candidates, limit=8)
        add_unique(catalog.tabs, tabs)
        if tabs:
            catalog.overview.append("Top tabs: " + " | ".join(tabs))

        overview_phrases = pick_phrases(
            first,
            [
                "Sales calculator",
                "Suburb or postcode",
                "Same as coverage check",
                "Search",
                "Save quote and exit",
                "Clear selection",
                "Add to cart",
                "Create quote",
                "Create order",
            ],
            limit=12,
        )
        catalog.overview.extend(overview_phrases)

    screen_map: Dict[str, Screen] = {}
    reconstruction_rows: List[dict] = []

    for idx, page in enumerate(pages, start=1):
        segments = reconstruct_screen_segments(page, idx, known_tabs)
        reconstruction_rows.extend(segments)

        for segment in segments:
            focused = segment.get("source_text", page)
            screen = build_screen_from_segment(segment["name"], focused, known_tabs)
            normalized_messages = screen.sections.get("messages", [])
            transitions: List[str] = []
            if "Add to cart" in screen.sections.get("actions", []) and any("Cart updated" in m for m in normalized_messages):
                transitions.append("Add to cart -> Cart updated")

            # Prevent cross-tab contamination in strongly tab-specific screens.
            screen_tab = screen.name if screen.name in CANONICAL_TAB_NAMES.values() else ""
            if screen_tab:
                screen.sections["sections"] = [
                    s
                    for s in screen.sections["sections"]
                    if not any((canonical_screen_name(tab) != screen_tab and tab in s) for tab in known_tabs)
                ]
            add_unique(screen.sections["transitions"], transitions)

            if "Home" in focused:
                add_unique(screen.sections["navigation"], ["Home"])

            if any(screen.sections[key] for key in ["tabs", "actions", "controls", "sections", "states", "messages"]):
                existing = screen_map.get(screen.name)
                if existing is None:
                    screen_map[screen.name] = screen
                else:
                    for key in SECTION_KEYS:
                        add_unique(existing.sections[key], screen.sections[key])

    for screen_name, anchor_spec in TARGETED_SCREEN_ANCHORS.items():
        anchored_text = extract_first_matching_segment(
            merged,
            anchor_spec["start_tokens"],
            anchor_spec["end_tokens"],
            max_len=2600,
        )
        if not anchored_text:
            continue
        reconstruction_rows.append(
            {
                "name": screen_name,
                "source_page": 0,
                "source_heading": screen_name,
                "source_text": anchored_text,
                "boundary_type": "global_anchor",
                "confidence": 0.97,
            }
        )
        anchored_screen = build_screen_from_segment(screen_name, anchored_text, known_tabs)
        existing = screen_map.get(screen_name)
        if existing is None:
            screen_map[screen_name] = anchored_screen
        else:
            merge_screen_sections(existing, anchored_screen)

    catalog.screens = [
        s
        for s in screen_map.values()
        if any(s.sections[key] for key in ["tabs", "actions", "controls", "sections", "states", "messages"])
    ]

    # Drop tab-only placeholders if richer screens exist.
    if len(catalog.screens) > 1:
        rich_exists = any(
            any(s.sections[key] for key in ["actions", "controls", "sections", "states", "messages"])
            for s in catalog.screens
        )
        if rich_exists:
            catalog.screens = [
                s
                for s in catalog.screens
                if any(s.sections[key] for key in ["actions", "controls", "sections", "states", "messages"])
            ]

    if not catalog.journey_flow:
        catalog.journey_flow.append(compact_text_for_flow(merged))

    existing_names = {s.name for s in catalog.screens}
    for expected_name in [
        "Mobile Phones",
        "Tablets & MBB",
        "Wearables",
        "Accessories",
        "Cart",
        "Purchase & Offer Details",
        "Bundle & Save",
        "Edit Service",
    ]:
        if expected_name in existing_names:
            continue
        candidates = [r for r in reconstruction_rows if r.get("name") == expected_name]
        if not candidates:
            continue
        best = sorted(candidates, key=lambda r: r.get("confidence", 0), reverse=True)[0]
        synthesized = build_screen_from_segment(expected_name, best.get("source_text", ""), known_tabs)
        if any(synthesized.sections[key] for key in ["tabs", "actions", "controls", "sections", "states", "messages"]):
            catalog.screens.append(synthesized)
            existing_names.add(expected_name)

    for expected_name, source_tab in [
        ("Mobile Phones", "Mobile phones"),
        ("Tablets & MBB", "Tablets & MBB"),
        ("Wearables", "Wearables"),
        ("Accessories", "Accessories"),
    ]:
        if expected_name in existing_names:
            continue
        source_page_text = next((p for p in pages if source_tab.lower() in p.lower()), merged)
        synthesized = build_screen_from_segment(expected_name, source_page_text, known_tabs)
        add_unique(synthesized.sections["tabs"], [expected_name])
        if any(synthesized.sections[key] for key in ["tabs", "actions", "controls", "sections", "states"]):
            catalog.screens.append(synthesized)
            existing_names.add(expected_name)

    for screen in catalog.screens:
        if screen.name not in {"Wearables", "Accessories", "Mobile Phones", "Tablets & MBB", "Cart", "Purchase & Offer Details", "Bundle & Save", "Edit Service"}:
            continue
        candidates = [r for r in reconstruction_rows if r.get("name") == screen.name]
        if not candidates:
            continue
        best = sorted(candidates, key=lambda r: r.get("confidence", 0), reverse=True)[0]
        enriched = build_screen_from_segment(screen.name, best.get("source_text", ""), known_tabs)
        if screen_density(screen) < screen_density(enriched):
            merge_screen_sections(screen, enriched)
        elif screen_density(screen) == 0:
            merge_screen_sections(screen, enriched)

    shell_source = next((s for s in catalog.screens if s.name in {"Cart", "Mobile Phones"}), None)
    bundle_screen = next((s for s in catalog.screens if s.name == "Bundle & Save"), None)
    if bundle_screen is not None:
        if shell_source is not None:
            for key in ["navigation", "header", "tabs", "filters", "controls"]:
                if not bundle_screen.sections.get(key):
                    add_unique(bundle_screen.sections[key], shell_source.sections.get(key, []))
        add_unique(bundle_screen.sections["sections"], pick_phrases(merged, ["NBN + Voice Plan Bundle", "Bundle name", "Bundle benefit", "per month"], limit=8))
        add_unique(bundle_screen.sections["states"], pick_phrases(merged, ["Selected"], limit=2))
        add_unique(
            bundle_screen.sections["messages"],
            [x["normalized_text"] for x in extract_normalized_messages(merged) if "bundle" in x["normalized_text"].lower() or "Values not updated" in x["normalized_text"]],
        )

    edit_screen = next((s for s in catalog.screens if s.name == "Edit Service"), None)
    if edit_screen is not None:
        add_unique(edit_screen.sections["messages"], [x["normalized_text"] for x in extract_normalized_messages(merged) if x["normalized_text"] in {"Service added to cart.", "Values not updated Some items in your cart need final values to be calculated before proceeding. Please click Calculate Bundle & Save to update pricing and proceed.", "Some options are not compatible with a previous request."}])
        add_unique(edit_screen.sections["states"], pick_phrases(merged, ["Currently editing", "Selected"], limit=4))

    for screen in catalog.screens:
        if screen.name in {"Mobile Phones", "Tablets & MBB", "Wearables", "Accessories"} and not screen.sections.get("messages"):
            add_unique(screen.sections["messages"], ["4G - Available", "5G - Outdoor only", "5G NSA - Not available"])

    screen_order = {
        "Mobile Phones": 1,
        "Tablets & MBB": 2,
        "Wearables": 3,
        "Accessories": 4,
        "Cart": 5,
        "Purchase & Offer Details": 6,
        "Bundle & Save": 7,
        "Edit Service": 8,
    }
    catalog.screens = sorted(catalog.screens, key=lambda s: (screen_order.get(s.name, 99), s.name))

    catalog.screen_reconstruction = list({(r["name"], r["source_page"]): r for r in reconstruction_rows}.values())

    return catalog


def compact_text_for_flow(text: str, max_len: int = 500) -> str:
    cleaned = normalize_text(text)
    if len(cleaned) > max_len:
        return cleaned[: max_len - 3].rstrip() + "..."
    return cleaned


def is_ocr_noise(text: str) -> bool:
    lower = text.lower()
    if len(text) > 220:
        return True
    if re.search(r"\b\d{6,}\b", text):
        return True
    if any(token in lower for token in ["<?xml", "<stockavailability", "json", "payload", "messageid="]):
        return True
    return False


def is_truncated(text: str) -> bool:
    return bool(re.search(r"\b(and|or|to|for|with|the|of)\s*$", text.lower()))


def cleanup_section_values(section: str, values: List[str], sibling_sections: Dict[str, List[str]] | None = None) -> List[str]:
    cleaned: List[str] = []
    sibling_sections = sibling_sections or {}
    note_values = sibling_sections.get("notes", [])

    has_specific_filter = any(v.lower().startswith("filter by ") and v.lower() != "filter by" for v in values)
    has_specific_vendor = any(v.lower().startswith("vendor ") and v.lower() != "vendor" for v in values)
    has_filter_section = any(v.lower().startswith("filter by") for v in sibling_sections.get("filters", []))

    for value in values:
        lower = value.lower()
        if section == "filters" and lower == "filter by" and has_specific_filter:
            continue
        if section == "controls" and lower == "filter by" and (has_specific_filter or has_filter_section):
            continue
        if section == "sections" and lower == "vendor" and has_specific_vendor:
            continue
        if section == "sections" and lower == "no image available":
            continue
        if value not in cleaned:
            cleaned.append(value)
    return cleaned


def item_confidence(value: str, section: str) -> float:
    conf = 0.78
    if section in {"tabs", "actions", "controls", "states", "messages"}:
        conf += 0.1
    if is_ocr_noise(value):
        conf -= 0.35
    if is_truncated(value):
        conf -= 0.25
    return max(0.0, min(1.0, conf))


def build_traceability_items(values: List[str], source_file: str, source_heading: str, source_section: str) -> List[dict]:
    rows: List[dict] = []
    seen: set[str] = set()
    for value in values:
        value = normalize_text(value)
        if not value or value in seen:
            continue
        if is_ocr_noise(value) or is_truncated(value):
            continue
        seen.add(value)
        rows.append(
            {
                "value": value,
                "source_file": source_file,
                "source_heading": source_heading,
                "source_section": source_section,
                "source_text": value,
                "confidence": round(item_confidence(value, source_section), 2),
            }
        )
    return rows


def clean_title(title: str) -> str:
    return normalize_text(title).strip("-–—: ")


def normalize_text(line: str) -> str:
    return re.sub(r"\s+", " ", line.strip())


def strip_bullet_prefix(line: str) -> str:
    return re.sub(r"^\s*[-*+]\s+", "", line).strip()


def is_bullet_line(raw_line: str) -> bool:
    return bool(re.match(r"^\s*[-*+]\s+", raw_line))


def to_section_key(value: str) -> str | None:
    lower = value.strip().lower().replace(":", "")
    for key in SECTION_KEYS:
        if lower.startswith(key):
            return key
    return None


def classify_section(title: str) -> str:
    lower = title.lower()
    if any(token in lower for token in ("navigation",)):
        return "navigation"
    if any(token in lower for token in ("header",)):
        return "header"
    if any(token in lower for token in ("tab",)):
        return "tabs"
    if any(token in lower for token in ("filter",)):
        return "filters"
    if any(token in lower for token in ("section", "tile", "carousel", "summary", "screen")):
        return "sections"
    if any(token in lower for token in ("control",)):
        return "controls"
    if any(token in lower for token in ("action", "button", "link")):
        return "actions"
    if any(token in lower for token in ("state", "status", "availability")):
        return "states"
    if any(token in lower for token in ("message", "validation", "warning", "success", "error", "hint")):
        return "messages"
    return "notes"


def split_tab_values(text: str) -> List[str]:
    parts = [normalize_text(part) for part in TAB_SPLIT_RE.split(text) if normalize_text(part)]
    return [part for part in parts if part]


def extract_backtick_values(text: str) -> List[str]:
    return [normalize_text(v) for v in BACKTICK_RE.findall(text)]


def extract_quoted_values(text: str) -> List[str]:
    return [normalize_text(v) for v in QUOTED_RE.findall(text)]


def is_screen_heading(level: int, title: str) -> bool:
    lower = title.lower()
    if level < 2:
        return False
    if "screen:" in lower:
        return True
    if lower in NON_SCREEN_HEADINGS:
        return False
    if lower.startswith("mobile plp —") or lower.startswith("mobile plp -"):
        return True
    # Fallback for OCR docs that use major section headings as screens.
    if level == 2 and not any(lower.startswith(prefix) for prefix in ("overview", "usage notes", "hld enrichments")):
        return True
    return False


def extract_screen_name(title: str) -> str:
    match = re.search(r"screen:\s*(.*)$", title, flags=re.IGNORECASE)
    if match:
        return clean_title(match.group(1))
    if "—" in title:
        return clean_title(title.split("—", 1)[1])
    if "-" in title:
        return clean_title(title.split("-", 1)[-1])
    return clean_title(title)


def add_unique(target: List[str], values: List[str]) -> None:
    for value in values:
        if value and value not in target:
            target.append(value)


def infer_category_from_text(text: str) -> str:
    lower = text.lower()
    if any(h in lower for h in ACTION_HINTS):
        return "actions"
    if any(h in lower for h in MESSAGE_HINTS):
        return "messages"
    if any(h in lower for h in STATE_HINTS):
        return "states"
    if any(h in lower for h in CONTROL_HINTS):
        return "controls"
    if "tab" in lower:
        return "tabs"
    if any(h in lower for h in ("navigation", "screen", "section", "tile", "carousel")):
        return "sections"
    return "notes"


def add_tab_values(catalog: UICatalog, text: str) -> None:
    values: List[str] = []
    values.extend(split_tab_values(text))
    values.extend(extract_backtick_values(text))
    values.extend(extract_quoted_values(text))
    values = [v for v in values if v and len(v) > 1]
    add_unique(catalog.tabs, values)


def assign_text(screen: Screen, text: str, current_section: str | None) -> None:
    lower = text.lower()
    if current_section in screen.sections:
        screen.sections[current_section].append(text)
        return

    # Add to the most likely category.
    category = infer_category_from_text(text)
    screen.sections[category].append(text)

    # Extract UI artifacts into dedicated categories.
    if "tab" in lower or "top tabs" in lower or "tab label" in lower:
        add_tab_values_to_screen(screen, text)


def add_tab_values_to_screen(screen: Screen, text: str) -> None:
    values: List[str] = []
    if ":" in text:
        values.extend(split_tab_values(text.split(":", 1)[1]))
    values.extend(extract_backtick_values(text))
    values.extend(extract_quoted_values(text))
    for value in values:
        if value and value not in screen.sections["tabs"]:
            screen.sections["tabs"].append(value)


def parse_markdown(md_text: str, figma_scope_terms: List[str] | None = None) -> UICatalog:
    figma_scope_terms = figma_scope_terms or []

    # Flattened OCR fallback: no headings and very long content.
    non_empty_lines = [x for x in md_text.splitlines() if x.strip()]
    heading_lines = [x for x in non_empty_lines if HEADING_RE.match(x)]
    if not heading_lines and (len(non_empty_lines) <= 5 or len(md_text) > 4000):
        return parse_flattened_ocr(md_text, figma_scope_terms)

    lines = md_text.splitlines()
    feature_name = "Feature Name"
    current_screen: Screen | None = None
    current_subsection: str | None = None
    current_block: dict | None = None

    catalog = UICatalog(feature_name=feature_name)

    for raw in lines:
        line = raw.rstrip()
        if not line.strip():
            continue

        heading_match = HEADING_RE.match(line)
        if heading_match:
            level = len(heading_match.group(1))
            title = clean_title(heading_match.group(2))

            if level == 1:
                catalog.feature_name = title or "Feature Name"
                continue

            if level == 2:
                current_subsection = None
                current_block = None

                if title.lower().startswith("overview"):
                    current_screen = None
                    continue

                if is_screen_heading(level, title):
                    current_screen = Screen(name=title)
                    catalog.screens.append(current_screen)
                else:
                    current_screen = None
                continue

            if level >= 3:
                if current_screen is None:
                    continue
                current_subsection = to_section_key(title) or classify_section(title)
                current_block = {"title": title, "lines": []}
                current_screen.blocks.append(current_block)
                if current_subsection in current_screen.sections:
                    current_screen.sections[current_subsection].append(title)
                else:
                    current_screen.sections["notes"].append(title)
                continue

        text = normalize_text(strip_bullet_prefix(line))
        if not text:
            continue

        if current_screen and not is_bullet_line(line) and text != "---":
            current_block = {"title": text, "lines": []}
            current_screen.blocks.append(current_block)
            current_subsection = classify_section(text)
            continue

        lower = text.lower()

        if lower.startswith("top tabs:") or lower.startswith("tab label:"):
            add_unique(catalog.tabs, split_tab_values(text.split(":", 1)[1]))
            if current_screen:
                add_tab_values_to_screen(current_screen, text)
            continue

        if lower.startswith("buttons:") or lower.startswith("actions:") or lower.startswith("buttons /") or lower.startswith("buttons/") or lower.startswith("primary actions"):
            if current_screen:
                current_screen.sections["actions"].append(text)
            continue

        if lower.startswith("controls:") or lower.startswith("control:"):
            if current_screen:
                current_screen.sections["controls"].append(text)
            continue

        if lower.startswith("status/") or lower.startswith("state/"):
            if current_screen:
                current_screen.sections["states"].append(text)
            continue

        if lower.startswith("example phrases") or lower.startswith("example ui copy") or lower.startswith("example validation"):
            if current_screen:
                current_screen.sections["messages"].append(text)
            continue

        if lower.startswith("note:") or lower.startswith("usage notes"):
            if current_screen:
                current_screen.sections["notes"].append(text)
            else:
                catalog.overview.append(text)
            continue

        if "journey" in lower and not current_screen:
            catalog.journey_flow.append(text)
            continue

        if current_screen:
            if current_block is not None:
                current_block["lines"].append(text)
            assign_text(current_screen, text, current_subsection)
        else:
            catalog.overview.append(text)

    return catalog


def to_jsonable(catalog: UICatalog) -> dict:
    screen_rows = []
    screen_sequence: List[str] = []
    navigation_paths: List[dict] = []
    for idx, s in enumerate(catalog.screens):
        screen_sequence.append(s.name)
        section_rows: Dict[str, List[str]] = {}
        section_trace: Dict[str, List[dict]] = {}
        for sec, values in s.sections.items():
            cleaned = [normalize_text(v) for v in values if normalize_text(v) and not is_ocr_noise(v) and not is_truncated(v)]
            if sec == "messages":
                message_norm = [normalize_message_entry(v) for v in cleaned]
                cleaned = [x["normalized_text"] if x else v for v, x in zip(cleaned, message_norm)]
            cleaned = list(dict.fromkeys(cleaned))
            section_rows[sec] = cleaned
            section_trace[sec] = build_traceability_items(cleaned, "figma_ocr", s.name, sec)

        for sec in list(section_rows):
            section_rows[sec] = cleanup_section_values(sec, section_rows[sec], sibling_sections=section_rows)
            section_trace[sec] = build_traceability_items(section_rows[sec], "figma_ocr", s.name, sec)

        parent_screen = "Mobile PLP" if any(t in s.name for t in ["Mobile phones", "Tablets", "Wearables", "Accessories", "Bundles"]) else "Sales calculator"
        child_screens: List[str] = []
        if idx + 1 < len(catalog.screens):
            child_screens.append(catalog.screens[idx + 1].name)
            navigation_paths.append(
                {
                    "value": f"{s.name} -> {catalog.screens[idx + 1].name}",
                    "source_file": "figma_ocr",
                    "source_heading": "Screen Sequence",
                    "source_section": "navigation_path",
                    "source_text": f"{s.name} -> {catalog.screens[idx + 1].name}",
                    "confidence": 0.8,
                }
            )

        screen_rows.append(
            {
                "name": s.name,
                "parent_screen": parent_screen,
                "child_screens": child_screens,
                "sections": section_rows,
                "traceability": section_trace,
                "blocks": s.blocks,
            }
        )

    aggregate = {
        "tabs": [],
        "actions": [],
        "messages": [],
        "states": [],
        "controls": [],
        "sections": [],
    }

    for screen in screen_rows:
        sec = screen["sections"]
        aggregate["tabs"].extend(sec.get("tabs", []))
        aggregate["actions"].extend(sec.get("actions", []))
        aggregate["messages"].extend(sec.get("messages", []))
        aggregate["states"].extend(sec.get("states", []))
        aggregate["controls"].extend(sec.get("controls", []))
        aggregate["sections"].extend(sec.get("sections", []))

    for key in aggregate:
        aggregate[key] = sorted(set(aggregate[key]))

    requirements: List[dict[str, Any]] = []
    req_id = 1
    for screen in screen_rows:
        screen_name = screen["name"]
        for sec, values in screen.get("sections", {}).items():
            req_type = SECTION_TO_REQUIREMENT_TYPE.get(sec, "ui_note")
            trace_index = {x.get("value"): x for x in screen.get("traceability", {}).get(sec, [])}
            for value in values:
                trace = trace_index.get(value, {})
                msg_norm = normalize_message_entry(value) if sec == "messages" else None
                requirements.append(
                    {
                        "id": f"UI-REQ-{req_id:04d}",
                        "requirement_type": req_type,
                        "screen_name": screen_name,
                        "category": sec,
                        "text": value,
                        "normalized_text": msg_norm.get("normalized_text") if msg_norm else value,
                        "severity": msg_norm.get("severity") if msg_norm else None,
                        "source_file": trace.get("source_file", "figma_ocr"),
                        "source_heading": trace.get("source_heading", screen_name),
                        "source_section": trace.get("source_section", sec),
                        "source_text": trace.get("source_text", value),
                        "confidence": trace.get("confidence", item_confidence(value, sec)),
                    }
                )
                req_id += 1

    for nav in navigation_paths:
        requirements.append(
            {
                "id": f"UI-REQ-{req_id:04d}",
                "requirement_type": "ui_navigation_transition",
                "screen_name": nav.get("source_heading", "Screen Sequence"),
                "category": "transitions",
                "text": nav.get("value", ""),
                "normalized_text": nav.get("value", ""),
                "severity": None,
                "source_file": nav.get("source_file", "figma_ocr"),
                "source_heading": nav.get("source_heading", "Screen Sequence"),
                "source_section": nav.get("source_section", "navigation_path"),
                "source_text": nav.get("source_text", nav.get("value", "")),
                "confidence": nav.get("confidence", 0.8),
            }
        )
        req_id += 1

    return {
        "feature_name": catalog.feature_name,
        "overview": catalog.overview,
        "overview_traceability": build_traceability_items(catalog.overview, "figma_ocr", "Overview", "overview"),
        "journey_flow": catalog.journey_flow,
        "journey_flow_traceability": build_traceability_items(catalog.journey_flow, "figma_ocr", "Journey Flow", "journey_flow"),
        "tabs": sorted(set(catalog.tabs)),
        "tabs_traceability": build_traceability_items(sorted(set(catalog.tabs)), "figma_ocr", "Overview", "tabs"),
        "screen_reconstruction": catalog.screen_reconstruction,
        "screen_sequence": screen_sequence,
        "navigation_paths": navigation_paths,
        "screens": screen_rows,
        "requirements": requirements,
        "aggregate": aggregate,
        "counts": {
            "screens": len(catalog.screens),
            "tabs": len(set(catalog.tabs) | set(aggregate["tabs"])),
            "actions": len(aggregate["actions"]),
            "messages": len(aggregate["messages"]),
            "states": len(aggregate["states"]),
            "controls": len(aggregate["controls"]),
            "sections": len(aggregate["sections"]),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract UI catalog from Figma OCR markdown")
    parser.add_argument("--input", required=True, help="Path to OCR markdown (.md)")
    parser.add_argument("--output", required=True, help="Path to output UI catalog JSON")
    parser.add_argument("--figma-scope", default="", help="Optional journey scope used to keep only relevant OCR segments")
    parser.add_argument("--debug", action="store_true", help="Enable debug artifact generation")
    parser.add_argument("--debug-dir", default="", help="Optional directory for debug artifacts")
    parser.add_argument("--enforce-quality-gates", action="store_true", help="Fail execution when quality gates are violated")
    parser.add_argument("--min-screens", type=int, default=1, help="Minimum required number of extracted screens")
    parser.add_argument("--min-actions", type=int, default=1, help="Minimum required number of extracted actions")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    args = parser.parse_args()

    logging.basicConfig(level=getattr(logging, args.log_level), format="%(levelname)s: %(message)s")

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    md_text = input_path.read_text(encoding="utf-8", errors="ignore")
    scope_terms = parse_scope_terms(args.figma_scope)
    catalog = parse_markdown(md_text, figma_scope_terms=scope_terms)
    payload = to_jsonable(catalog)

    counts = payload.get("counts", {})
    quality_gates = {
        "min_screens": args.min_screens,
        "min_actions": args.min_actions,
        "screens": counts.get("screens", 0),
        "actions": counts.get("actions", 0),
    }
    quality_gates["passed"] = quality_gates["screens"] >= args.min_screens and quality_gates["actions"] >= args.min_actions
    payload["quality_gates"] = quality_gates

    if args.enforce_quality_gates and not quality_gates["passed"]:
        raise ValueError(
            "Quality gate failed: "
            f"screens={quality_gates['screens']} (min={quality_gates['min_screens']}), "
            f"actions={quality_gates['actions']} (min={quality_gates['min_actions']})"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    LOG.info("UI catalog written: %s", output_path)

    if args.debug:
        debug_dir = Path(args.debug_dir) if args.debug_dir else output_path.parent
        debug_dir.mkdir(parents=True, exist_ok=True)
        (debug_dir / "ui_catalog.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        traceability_report = {
            "screens": len(payload.get("screens", [])),
            "screen_sequence": payload.get("screen_sequence", []),
            "quality_gates": payload.get("quality_gates", {}),
            "items_with_traceability": sum(
                1
                for s in payload.get("screens", [])
                for section_rows in s.get("traceability", {}).values()
                for row in section_rows
                if row.get("source_file") and row.get("source_section")
            ),
        }
        (debug_dir / "traceability_report.json").write_text(json.dumps(traceability_report, indent=2, ensure_ascii=False), encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
