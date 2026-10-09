#!/usr/bin/env python3
"""
Generate human-readable coverage report from traceability JSON.

Usage:
  python scripts/coverage_report.py \
    --traceability path/to/traceability.json \
    --output path/to/coverage_report.md
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict


def section_rows(section: Dict[str, dict]) -> list[str]:
    rows = []
    for key, data in section.items():
        rows.append(
            f"| {key} | {data.get('total', 0)} | {data.get('present', 0)} | {data.get('missing', 0)} | {data.get('coverage_pct', 0)}% |"
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate markdown coverage report")
    parser.add_argument("--traceability", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    data = json.loads(Path(args.traceability).read_text(encoding="utf-8"))
    ui = data.get("ui_traceability", {})
    hld = data.get("hld_traceability", {})

    lines = [
        "# Coverage Report",
        "",
        "## UI Coverage",
        "| Category | Total | Present | Missing | Coverage |",
        "|---|---:|---:|---:|---:|",
    ]
    lines.extend(section_rows(ui))

    lines.extend([
        "",
        "## HLD Coverage",
        "| Category | Total | Present | Missing | Coverage |",
        "|---|---:|---:|---:|---:|",
    ])
    lines.extend(section_rows(hld))

    lines.append("")
    lines.append("## Missing Items")

    for section_name, section in [("UI", ui), ("HLD", hld)]:
        for category, info in section.items():
            missing_items = info.get("missing_items", [])
            if missing_items:
                lines.append(f"- {section_name}/{category}:")
                for item in missing_items:
                    lines.append(f"  - {item}")

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
