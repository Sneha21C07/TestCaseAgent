#!/usr/bin/env python3
"""
Validate Requirements Catalog structure and guardrails.

Usage:
  python scripts/validate_catalog.py --catalog path/to/requirements_catalog.md
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

REQUIRED_HEADINGS = [
    "## Overview",
    "## Journey Flow",
    "## HLD Enrichments",
    "### Validation Scenarios",
    "### Negative Scenarios",
    "### Boundary Scenarios",
    "### Business Rules",
    "### Restrictions",
    "### Limits",
    "### Eligibility Rules",
    "### Compatibility Rules",
    "### RTSA Rules",
    "### Stock Rules",
    "### Warning Messages",
    "### Success Messages",
    "## Missing Requirements",
    "## Traceability Notes",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate requirements catalog")
    parser.add_argument("--catalog", required=True)
    args = parser.parse_args()

    text = Path(args.catalog).read_text(encoding="utf-8", errors="ignore")

    missing = [h for h in REQUIRED_HEADINGS if h not in text]
    violations = []

    if re.search(r"\btest cases?\b", text, flags=re.IGNORECASE):
        violations.append("Catalog mentions test case generation directly; keep output as requirements-only.")

    if missing:
        print("Missing headings:")
        for h in missing:
            print(f"- {h}")

    if violations:
        print("Guardrail violations:")
        for v in violations:
            print(f"- {v}")

    if missing or violations:
        return 1

    print("Validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
