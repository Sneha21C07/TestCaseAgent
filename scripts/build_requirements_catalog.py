#!/usr/bin/env python3
"""
Build requirements catalog markdown by merging UI catalog and HLD rule catalog.

Usage:
  python scripts/build_requirements_catalog.py \
    --ui-catalog path/to/ui_catalog.json \
    --hld-rules path/to/hld_rules.json \
    --feature-name "My Feature" \
    --output path/to/requirements_catalog.md
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, List

SECTION_ORDER = [
    "Navigation",
    "Header",
    "Tabs",
    "Filters",
    "Sections",
    "Controls",
    "Actions",
    "States",
    "Messages",
    "Notes",
]

RULE_MAP = {
    "Validation Scenarios": "validation_scenarios",
    "Negative Scenarios": "negative_scenarios",
    "Boundary Scenarios": "boundary_scenarios",
    "Business Rules": "business_rules",
    "Restrictions": "restrictions",
    "Limits": "limits",
    "Eligibility Rules": "eligibility_rules",
    "Compatibility Rules": "compatibility_rules",
    "RTSA Rules": "rtsa_rules",
    "Stock Rules": "stock_rules",
    "Warning Messages": "warning_messages",
    "Success Messages": "success_messages",
}

RULE_LIMITS = {
    "validation_scenarios": 2,
    "negative_scenarios": 2,
    "boundary_scenarios": 3,
    "business_rules": 2,
    "restrictions": 1,
    "limits": 2,
    "eligibility_rules": 1,
    "compatibility_rules": 2,
    "rtsa_rules": 3,
    "stock_rules": 3,
    "warning_messages": 1,
    "success_messages": 1,
}


def bullets(rows: List[str], source: str | None = None) -> List[str]:
    if source:
        return [f"- [{source}] {x}" for x in rows]
    return [f"- {x}" for x in rows]


def compact_text(text: str) -> str:
    cleaned = " ".join(text.replace("\u2018", "'").replace("\u2019", "'").split())
    lowered = cleaned.lower()
    if (
        cleaned.startswith("<?xml")
        or cleaned.startswith("<")
        or "<" in cleaned
        or ">" in cleaned
        or "messageid=" in lowered
        or "transactionname=" in lowered
        or "intobjectname=" in lowered
        or "bwe rrcode=" in lowered
        or "bwerrcode=" in lowered
    ):
        return ""
    if len(cleaned) > 180:
        cleaned = cleaned[:177].rstrip() + "..."
    return cleaned


def compact_entries(entries: List[str], limit: int = 4) -> List[str]:
    compacted: List[str] = []
    seen: set[str] = set()
    for entry in entries:
        text = compact_text(entry)
        if not text:
            continue
        if text in seen:
            continue
        seen.add(text)
        compacted.append(text)
        if len(compacted) >= limit:
            break
    return compacted


def derive_overview_rows(ui: dict, feature_name: str) -> List[str]:
    rows = [compact_text(x) for x in ui.get("overview", []) if compact_text(x) and x != "---"]
    if rows:
        return rows

    inferred: List[str] = [f"Feature scope: {feature_name}"]
    tabs = ui.get("tabs", [])
    if tabs:
        inferred.append("Top tabs: " + " | ".join(tabs[:8]))

    counts = ui.get("counts", {})
    inferred.append(
        "Discovered from Figma OCR: "
        f"screens={counts.get('screens', 0)}, tabs={counts.get('tabs', 0)}, "
        f"actions={counts.get('actions', 0)}, messages={counts.get('messages', 0)}, states={counts.get('states', 0)}"
    )
    return inferred


def derive_journey_flow_rows(ui: dict) -> List[str]:
    rows = [compact_text(x) for x in ui.get("journey_flow", []) if compact_text(x)]
    return compact_entries(rows, limit=12)


def detect_phrases(text: str, candidates: List[str]) -> List[str]:
    lower = text.lower()
    found: List[str] = []
    for candidate in candidates:
        if candidate.lower() in lower and candidate not in found:
            found.append(candidate)
    return found


def detect_title_phrases(text: str, max_items: int = 8) -> List[str]:
    pattern = re.compile(r"(?:[A-Z][A-Za-z0-9&/-]*)(?:\s+(?:[A-Z][A-Za-z0-9&/-]*|&)){0,2}")
    blacklist = {
        "File",
        "Edit",
        "View",
        "Navigate",
        "Query",
        "Tools",
        "Help",
        "Tasks",
        "Quick",
        "Links",
    }
    phrases: List[str] = []
    for match in pattern.findall(text):
        phrase = compact_text(match)
        if not phrase or phrase in blacklist or len(phrase) < 4:
            continue
        if phrase not in phrases:
            phrases.append(phrase)
        if len(phrases) >= max_items:
            break
    return phrases


def synthesize_generic_screen(ui: dict, feature_name: str) -> List[dict]:
    aggregate = ui.get("aggregate", {})
    raw_text = " ".join(ui.get("journey_flow", []))

    action_candidates = [
        "Search",
        "Select",
        "Add to cart",
        "Update cart",
        "Save",
        "Create quote",
        "Create order",
        "Edit",
        "Remove",
        "Calculate",
        "View",
        "Configure",
        "Resume",
    ]
    state_candidates = [
        "In stock",
        "Out of stock",
        "Low Stock",
        "Back Order",
        "Selected",
        "Completed",
        "Failed",
    ]
    control_candidates = [
        "input",
        "checkbox",
        "dropdown",
        "Sort by",
        "Filter by",
        "Suburb or postcode",
    ]
    message_fragments = re.findall(r"[^.]*?(?:Please|not allowed|failed|completed|updated)[^.]*\.?", raw_text, flags=re.IGNORECASE)
    message_rows = compact_entries([compact_text(x) for x in message_fragments if compact_text(x)], limit=8)

    inferred_tabs = compact_entries(aggregate.get("tabs", []), limit=8)
    if not inferred_tabs:
        inferred_tabs = detect_title_phrases(raw_text, max_items=8)

    sections: Dict[str, List[str]] = {
        "navigation": compact_entries(aggregate.get("sections", []) or detect_title_phrases(raw_text, max_items=6), limit=8),
        "header": compact_entries(detect_phrases(raw_text, ["Home", "Sales calculator", "Quote details"]), limit=6),
        "tabs": compact_entries(ui.get("tabs", []) + inferred_tabs, limit=8),
        "filters": compact_entries(detect_phrases(raw_text, ["Filter by", "Sort by", "Show all"]), limit=6),
        "sections": compact_entries(aggregate.get("sections", []) or detect_title_phrases(raw_text, max_items=10), limit=12),
        "controls": compact_entries(aggregate.get("controls", []) + detect_phrases(raw_text, control_candidates), limit=10),
        "actions": compact_entries(aggregate.get("actions", []) + detect_phrases(raw_text, action_candidates), limit=10),
        "states": compact_entries(aggregate.get("states", []) + detect_phrases(raw_text, state_candidates), limit=8),
        "messages": compact_entries(aggregate.get("messages", []) + message_rows, limit=10),
        "notes": ["Screen structure inferred from aggregate OCR extraction."],
    }
    return [{"name": f"{feature_name} — Scoped Journey Screen", "sections": sections, "blocks": []}]


def build_figma_trace(ui: dict, fallback_rows: List[str], limit: int = 10) -> List[str]:
    rows: List[str] = []
    rows.extend(compact_entries(ui.get("tabs", []), limit=3))

    for screen in ui.get("screens", [])[:4]:
        name = compact_text(screen.get("name", ""))
        if name:
            rows.append(name)
        sections = screen.get("sections", {})
        rows.extend(compact_entries(sections.get("actions", []), limit=2))
        rows.extend(compact_entries(sections.get("messages", []), limit=1))

    rows.extend(compact_entries(fallback_rows, limit=4))
    return compact_entries(rows, limit=limit)


def build_hld_trace(rule_catalog: Dict[str, List[str]], limit: int = 10) -> List[str]:
    rows: List[str] = []
    for key in [
        "validation_scenarios",
        "business_rules",
        "limits",
        "compatibility_rules",
        "rtsa_rules",
        "stock_rules",
    ]:
        rows.extend(compact_entries(rule_catalog.get(key, []), limit=2))
    return compact_entries(rows, limit=limit)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_markdown(ui: dict, rules: dict, feature_name: str) -> tuple[str, dict]:
    missing: List[str] = []
    lines: List[str] = []
    figma_trace: List[str] = []
    hld_trace: List[str] = []

    lines.append(f"# {feature_name}")
    lines.append("")
    lines.append("## Overview")
    overview_rows = derive_overview_rows(ui, feature_name)
    lines.extend(bullets(overview_rows, source="Figma"))
    figma_trace.extend(overview_rows)
    lines.append("")

    lines.append("## Journey Flow")
    flow_rows = derive_journey_flow_rows(ui)
    if flow_rows:
        lines.extend(bullets(flow_rows, source="Figma"))
        figma_trace.extend(flow_rows)
    else:
        lines.append("- [Figma] Journey flow was not explicitly extracted.")
    lines.append("")

    screens = ui.get("screens", []) or synthesize_generic_screen(ui, feature_name)
    if not screens:
        missing.append("No screens discovered from Figma OCR markdown")

    for idx, screen in enumerate(screens, start=1):
        name = screen.get("name", f"Screen {idx}")
        lines.append(f"## {name}")
        sections: Dict[str, List[str]] = screen.get("sections", {})
        blocks: List[dict] = screen.get("blocks", [])

        if blocks:
            for block in blocks:
                block_title = block.get("title", "")
                block_lines = [x for x in block.get("lines", []) if x != "---"]
                if block_title:
                    lines.append(f"### {block_title}")
                    lines.extend(bullets(block_lines, source="Figma"))
                    figma_trace.extend(block_lines)
                    lines.append("")
        else:
            for sec in SECTION_ORDER:
                key = sec.lower()
                entries = sections.get(key, [])
                if entries:
                    lines.append(f"### {sec}")
                    lines.extend(bullets(entries, source="Figma"))
                    figma_trace.extend(entries)
                    lines.append("")
                else:
                    missing.append(f"{name} -> {sec} missing")

        lines.append("--------------------------------------------------")
        lines.append("")

    lines.append("## HLD Enrichments")
    rule_catalog: Dict[str, List[str]] = rules.get("rule_catalog", {})

    for section_title, key in RULE_MAP.items():
        entries = compact_entries(rule_catalog.get(key, []), limit=RULE_LIMITS.get(key, 3))
        if entries:
            lines.append(f"- {section_title}:")
            lines.extend([f"  - [HLD] {entry}" for entry in entries])
            hld_trace.extend(entries)
        else:
            missing.append(f"HLD -> {section_title} missing")

    lines.append("")
    lines.append("## Missing Requirements")
    if missing:
        for m in sorted(set(missing)):
            lines.append(f"- {m}")
    else:
        lines.append("- None identified in current scoped sources.")

    lines.append("")
    lines.append("## Traceability Notes")
    lines.append("- Figma-derived requirements:")
    trace_figma_rows = build_figma_trace(ui, figma_trace, limit=8)
    for row in trace_figma_rows:
        lines.append(f"  - [Figma] {row}")
    lines.append("- HLD-derived requirements:")
    trace_hld_rows = build_hld_trace(rule_catalog, limit=8)
    for row in trace_hld_rows:
        lines.append(f"  - [HLD] {row}")
    lines.append("- Missing requirements:")
    if missing:
        for row in sorted(set(missing))[:8]:
            lines.append(f"  - {row}")
    else:
        lines.append("  - None")

    markdown = "\n".join(lines) + "\n"
    traceability_report = {
        "feature_name": feature_name,
        "ui_screens": len(ui.get("screens", [])),
        "ui_tabs": len(ui.get("tabs", [])),
        "ui_trace_rows": len(trace_figma_rows),
        "hld_trace_rows": len(trace_hld_rows),
        "missing_count": len(sorted(set(missing))),
        "hld_rule_counts": rules.get("counts", {}),
    }
    return markdown, traceability_report


def build_coverage_report(traceability_report: dict, missing_items: List[str]) -> str:
    lines: List[str] = []
    lines.append("# Coverage Report")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- Feature: {traceability_report.get('feature_name', 'Unknown')}")
    lines.append(f"- UI screens discovered: {traceability_report.get('ui_screens', 0)}")
    lines.append(f"- UI tabs discovered: {traceability_report.get('ui_tabs', 0)}")
    lines.append(f"- Figma trace rows: {traceability_report.get('ui_trace_rows', 0)}")
    lines.append(f"- HLD trace rows: {traceability_report.get('hld_trace_rows', 0)}")
    lines.append(f"- Missing requirement items: {traceability_report.get('missing_count', 0)}")
    lines.append("")
    lines.append("## HLD Category Coverage")
    for category, count in sorted((traceability_report.get("hld_rule_counts") or {}).items()):
        lines.append(f"- {category}: {count}")
    lines.append("")
    lines.append("## Missing Requirements")
    if missing_items:
        for item in missing_items:
            lines.append(f"- {item}")
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def extract_missing_items(markdown: str) -> List[str]:
    missing_items: List[str] = []
    in_missing_section = False
    for line in markdown.splitlines():
        if line.strip() == "## Missing Requirements":
            in_missing_section = True
            continue
        if in_missing_section and line.startswith("## "):
            in_missing_section = False
        if in_missing_section and line.startswith("- "):
            item = line[2:].strip()
            if item and item.lower() != "none identified in current scoped sources.":
                missing_items.append(item)
    return sorted(set(missing_items))


def main() -> int:
    parser = argparse.ArgumentParser(description="Build merged Requirements Catalog markdown")
    parser.add_argument("--ui-catalog", required=True, help="Path to UI catalog JSON")
    parser.add_argument("--hld-rules", required=True, help="Path to HLD rules JSON")
    parser.add_argument("--feature-name", required=True, help="Feature name for title")
    parser.add_argument("--output", required=True, help="Output markdown path")
    parser.add_argument("--debug", action="store_true", help="Enable debug artifact generation")
    parser.add_argument("--debug-dir", default="", help="Optional directory for debug artifacts")
    parser.add_argument("--enforce-quality-gates", action="store_true", help="Fail when required minimum quality thresholds are not met")
    parser.add_argument("--max-missing", type=int, default=25, help="Maximum allowed number of missing requirement items")
    args = parser.parse_args()

    ui = load_json(Path(args.ui_catalog))
    rules = load_json(Path(args.hld_rules))

    out, traceability_report = build_markdown(ui, rules, args.feature_name)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(out, encoding="utf-8")

    missing_items = extract_missing_items(out)
    quality_gates = {
        "max_missing": args.max_missing,
        "missing_count": len(missing_items),
        "passed": len(missing_items) <= args.max_missing,
    }
    traceability_report["quality_gates"] = quality_gates

    if args.enforce_quality_gates and not quality_gates["passed"]:
        raise ValueError(
            f"Quality gate failed: missing requirements={quality_gates['missing_count']} > max_missing={quality_gates['max_missing']}"
        )

    if args.debug:
        debug_dir = Path(args.debug_dir) if args.debug_dir else out_path.parent
        debug_dir.mkdir(parents=True, exist_ok=True)

        (debug_dir / "catalog_debug.md").write_text(out, encoding="utf-8")
        (debug_dir / "traceability_report.json").write_text(
            json.dumps(traceability_report, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        coverage_md = build_coverage_report(traceability_report, missing_items)
        (debug_dir / "coverage_report.md").write_text(coverage_md, encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
