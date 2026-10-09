#!/usr/bin/env python3
"""
Generate source-to-catalog traceability report.

Usage:
  python scripts/generate_traceability.py \
    --ui-catalog path/to/ui_catalog.json \
    --hld-rules path/to/hld_rules.json \
    --catalog-md path/to/requirements_catalog.md \
    --output path/to/traceability.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Iterable, List


def contains(haystack: str, needle: str) -> bool:
    return needle.lower() in haystack.lower()


def flatten_ui(ui: dict) -> Dict[str, List[str]]:
    out: Dict[str, List[str]] = {
        "screens": [],
        "tabs": [],
        "sections": [],
        "actions": [],
        "states": [],
        "messages": [],
        "controls": [],
    }

    for s in ui.get("screens", []):
        out["screens"].append(s.get("name", ""))
        sections = s.get("sections", {})
        out["tabs"].extend(sections.get("tabs", []))
        out["sections"].extend(sections.get("sections", []))
        out["actions"].extend(sections.get("actions", []))
        out["states"].extend(sections.get("states", []))
        out["messages"].extend(sections.get("messages", []))
        out["controls"].extend(sections.get("controls", []))

    for k in out:
        out[k] = sorted(set([x for x in out[k] if x]))
    return out


def evaluate_items(items: Iterable[str], catalog_text: str) -> dict:
    present = []
    missing = []
    for item in items:
        (present if contains(catalog_text, item) else missing).append(item)

    total = len(present) + len(missing)
    coverage = (len(present) / total * 100.0) if total else 100.0
    return {
        "total": total,
        "present": len(present),
        "missing": len(missing),
        "coverage_pct": round(coverage, 2),
        "missing_items": missing,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate traceability report")
    parser.add_argument("--ui-catalog", required=True)
    parser.add_argument("--hld-rules", required=True)
    parser.add_argument("--catalog-md", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    ui = json.loads(Path(args.ui_catalog).read_text(encoding="utf-8"))
    hld = json.loads(Path(args.hld_rules).read_text(encoding="utf-8"))
    catalog_text = Path(args.catalog_md).read_text(encoding="utf-8", errors="ignore")

    ui_flat = flatten_ui(ui)
    hld_rules: Dict[str, List[str]] = hld.get("rule_catalog", {})

    result = {
        "ui_traceability": {k: evaluate_items(v, catalog_text) for k, v in ui_flat.items()},
        "hld_traceability": {k: evaluate_items(v, catalog_text) for k, v in hld_rules.items()},
    }

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
