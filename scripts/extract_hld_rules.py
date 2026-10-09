#!/usr/bin/env python3
"""
Extract business and validation rules from HLD markdown or PDF.

Usage:
  python scripts/extract_hld_rules.py --input path/to/hld.md --output path/to/hld_rules.json
  python scripts/extract_hld_rules.py --input path/to/hld.pdf --output path/to/hld_rules.json
"""

from __future__ import annotations

import argparse
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

LOG = logging.getLogger("extract_hld_rules")

CATEGORY_PATTERNS: Dict[str, List[str]] = {
    "validation_scenarios": ["validation", "must", "required", "not allowed", "invalid", "please select", "values not updated"],
    "negative_scenarios": ["error", "fail", "rejected", "exception", "not allowed"],
    "boundary_scenarios": ["minimum", "maximum", "min", "max", "boundary", "limit"],
    "business_rules": ["business rule", "rule", "behavior", "shall", "should"],
    "restrictions": ["restricted", "restriction", "cannot", "must not", "disabled"],
    "limits": ["limit", "up to", "at most", "no more than", "maximum of", "more than"],
    "eligibility_rules": ["eligible", "eligibility"],
    "compatibility_rules": ["compatible", "incompatible", "compatibility"],
    "rtsa_rules": ["rtsa", "stockavailability", "estimated shipment", "esd"],
    "stock_rules": ["stock", "availability", "back order", "low stock", "out of stock", "in stock"],
    "warning_messages": ["warning", "warn"],
    "success_messages": ["success", "successfully", "completed"],
}

EXTRA_RULE_CATEGORIES = [
    "rtsa_trigger_rules",
    "rtsa_mapping_rules",
]

BASE_DOMAIN_HINTS = [
    "journey",
    "screen",
    "ui",
    "user",
    "select",
    "validation",
    "message",
    "error",
    "warning",
    "success",
    "limit",
    "restriction",
    "eligible",
    "compatible",
    "stock",
    "rtsa",
    "add to cart",
    "update cart",
    "quote",
    "order",
]

SCOPE_NOISE_TOKENS = {
    "sales",
    "calculator",
    "new",
    "customer",
    "screen",
    "journey",
    "feature",
    "scope",
}

SOFT_EXCLUDE_HINTS = [
    "apple voucher",
    "quote rejected",
    "search all quotes",
    "customer details",
    "id details",
    "credit check",
    "billing",
    "visa",
    "sample value",
    "field mapping",
    "payload mapping",
]

BEHAVIOR_HINTS = [
    "show",
    "display",
    "enabled",
    "disabled",
    "allow",
    "not allow",
    "not allowed",
    "must",
    "should",
    "cannot",
    "required",
    "select",
    "add to cart",
    "update cart",
    "calculate bundle",
    "values not updated",
]

EXCLUDE_HINTS = [
    "<?xml",
    "siebelmessage",
    "transactionname=",
    "messageid=",
    "intobjectname=",
    "bwerrcode",
    "xsd",
    "json",
    "payload",
    "request:",
    "response:",
    "s_order",
    "database",
    "table",
    "column",
    "field",
    "sample value",
    "matrix ->",
    "administration - pricing",
    "pronto",
    "workflow",
    "technical guidance",
    "tbui",
    "<stockavailability",
    "approved requirement",
    "wireframe given by",
    "sample data",
    "test data",
    "s_order",
    "xml",
]

FEATURE_EXCLUDE_HINTS = [
    "s_order",
    "payload",
    "xml",
    "json",
    "schema",
    "data model",
    "field mapping",
    "table",
    "column",
    "apple voucher",
    "quote saved",
    "resume quote",
    "email quote",
    "quote validity",
    "quotes and orders",
    "order submitted",
    "attachments",
    "approval id",
    "external reference id",
]

USER_VISIBLE_HINTS = [
    "screen",
    "page",
    "tab",
    "banner",
    "message",
    "warning",
    "validation",
    "error",
    "button",
    "select",
    "filter",
    "sort",
    "display",
    "show",
    "stock",
    "cart",
    "device",
    "plan",
    "accessories",
    "wearables",
    "add to cart",
    "check store stock",
]

REQUIREMENT_VERBS = [
    "show",
    "display",
    "select",
    "add",
    "update",
    "validate",
    "allow",
    "prevent",
    "check",
    "calculate",
    "enable",
    "disable",
    "return",
    "read only",
    "available",
    "not available",
    "required",
    "must",
    "should",
]

SCOPE_ALIASES = {
    "figma": "journey_scope_filter",
    "hld": "journey_scope_filter",
}

CATEGORY_PRIORITY = [
    "validation_scenarios",
    "negative_scenarios",
    "boundary_scenarios",
    "business_rules",
    "restrictions",
    "limits",
    "eligibility_rules",
    "compatibility_rules",
    "rtsa_rules",
    "stock_rules",
    "warning_messages",
    "success_messages",
]

RULE_TEMPLATES = {
    "if_then": re.compile(r"\bif\s+(?P<condition>.+?)\s*,\s*(?:then\s+)?(?P<outcome>.+)", re.IGNORECASE),
    "when_then": re.compile(r"\bwhen\s+(?P<trigger>.+?)\s*,\s*(?:then\s+)?(?P<outcome>.+)", re.IGNORECASE),
    "must_rule": re.compile(r"\b(?P<actor>system|agent|user|customer)?\s*(?P<action>.+?\b(?:must|should|cannot|must not)\b.+)", re.IGNORECASE),
    "value_set": re.compile(r"\bvalues?\s+of\s+(?P<object>.+?)\s+are\s+(?P<values>.+)", re.IGNORECASE),
}


def read_hld_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".md":
        return path.read_text(encoding="utf-8", errors="ignore")

    if suffix == ".pdf":
        try:
            from pypdf import PdfReader  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                "PDF parsing requires 'pypdf'. Install with: pip install pypdf"
            ) from exc

        reader = PdfReader(str(path))
        pages = [page.extract_text() or "" for page in reader.pages]
        text = "\n".join(pages)

        sidecar = path.parent.parent.parent / "tmp_hld_extracted.json"
        if sidecar.exists():
            try:
                payload = json.loads(sidecar.read_text(encoding="utf-8"))
                extra = "\n".join(normalize_line(str(row.get("text", ""))) for row in payload if row.get("text"))
                if extra:
                    text = f"{text}\n{extra}"
            except Exception:
                pass
        return text

    raise ValueError(f"Unsupported HLD format: {path.suffix}")


def normalize_line(line: str) -> str:
    return re.sub(r"\s+", " ", line.strip())


def parse_scope_terms(scope_text: str | None) -> list[str]:
    if not scope_text:
        return []
    parts = re.split(r"[|,;\n]+", scope_text)
    return [normalize_line(part).lower() for part in parts if normalize_line(part)]


def load_ui_scope_terms(ui_catalog_path: str | None, limit: int = 60) -> List[str]:
    if not ui_catalog_path:
        return []
    path = Path(ui_catalog_path)
    if not path.exists():
        return []

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []

    terms: List[str] = []
    terms.extend(payload.get("tabs", []))
    for screen in payload.get("screens", []):
        terms.append(screen.get("name", ""))
        sections = screen.get("sections", {})
        terms.extend(sections.get("tabs", [])[:8])
        # include only high-signal behavioral anchors
        for token in ["add to cart", "check store stock", "calculate bundle & save", "values not updated", "rtsa"]:
            if any(token in str(v).lower() for v in sections.get("messages", []) + sections.get("sections", [])):
                terms.append(token)

    clean: List[str] = []
    for term in terms:
        t = normalize_line(str(term)).lower()
        if len(t) < 3:
            continue
        if t in SCOPE_NOISE_TOKENS:
            continue
        if t in {"search", "select", "edit", "remove", "mobile", "plp", "stock"}:
            continue
        # Remove noisy long lines and numeric-heavy fragments.
        if len(t) > 80:
            continue
        if re.search(r"\d{4,}", t):
            continue
        if t not in clean:
            clean.append(t)
        if len(clean) >= limit:
            break
    return clean


def load_ui_journey_context(ui_catalog_path: str | None) -> dict:
    if not ui_catalog_path:
        return {"anchors": [], "screen_names": [], "tabs": [], "actions": []}
    path = Path(ui_catalog_path)
    if not path.exists():
        return {"anchors": [], "screen_names": [], "tabs": [], "actions": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"anchors": [], "screen_names": [], "tabs": [], "actions": []}

    screen_names = [normalize_line(str(x.get("name", ""))).lower() for x in payload.get("screens", []) if x.get("name")]
    tabs = [normalize_line(str(x)).lower() for x in payload.get("tabs", []) if str(x).strip()]
    actions = [normalize_line(str(x)).lower() for x in payload.get("aggregate", {}).get("actions", []) if str(x).strip()]
    messages = [normalize_line(str(x)).lower() for x in payload.get("aggregate", {}).get("messages", []) if str(x).strip()]

    anchors: List[str] = []
    anchors.extend(screen_names[:12])
    anchors.extend(tabs[:10])
    anchors.extend(actions[:12])
    anchors.extend(messages[:10])
    anchors = sorted(set([a for a in anchors if len(a) >= 3]))
    return {
        "anchors": anchors,
        "screen_names": screen_names,
        "tabs": tabs,
        "actions": actions,
    }


def tokenize_scope(text: str) -> List[str]:
    parts = re.split(r"[^a-z0-9]+", text.lower())
    stop = {"the", "and", "for", "with", "from", "to", "of", "a", "an"}
    return [p for p in parts if p and p not in stop and len(p) > 2]


def term_matches_line(line_lower: str, term: str) -> bool:
    if term in line_lower:
        return True
    words = tokenize_scope(term)
    if len(words) >= 2:
        return all(word in line_lower for word in words)
    return False


def split_to_statements(text: str) -> List[str]:
    raw = [normalize_line(x) for x in text.splitlines() if normalize_line(x)]
    statements: List[str] = []
    for line in raw:
        chunks = re.split(r"(?<=[\.;:])\s+", line)
        for chunk in chunks:
            chunk = normalize_line(chunk)
            if chunk:
                statements.append(chunk)
    return statements


def is_heading_like(line: str) -> bool:
    normalized = normalize_line(line)
    if not normalized or len(normalized) > 90:
        return False
    if re.search(r"[\.!?]$", normalized) and not normalized.endswith(":"):
        return False
    word_count = len(normalized.split())
    if word_count > 12:
        return False
    return bool(re.match(r"^[A-Z0-9][A-Za-z0-9 /&()#:+\-]+:?$", normalized))


def extract_contextual_statements(text: str) -> List[dict]:
    raw_lines = [normalize_line(x) for x in text.splitlines() if normalize_line(x)]
    rows: List[dict] = []
    current_heading = ""
    last_content = ""

    for idx, line in enumerate(raw_lines):
        if is_heading_like(line):
            current_heading = line.rstrip(":")
            continue

        next_content = ""
        for future in raw_lines[idx + 1:]:
            if is_heading_like(future):
                continue
            next_content = future
            break

        chunks = re.split(r"(?<=[\.;:])\s+", line)
        for chunk in chunks:
            statement = normalize_line(chunk)
            if not statement:
                continue
            rows.append(
                {
                    "text": statement,
                    "heading": current_heading,
                    "previous_line": last_content,
                    "next_line": next_content,
                }
            )
        last_content = line

    return rows


def normalize_statement_with_context(statement_info: dict) -> str:
    text = normalize_rule_text(statement_info.get("text", ""))
    previous_line = normalize_rule_text(statement_info.get("previous_line", ""))
    next_line = normalize_rule_text(statement_info.get("next_line", ""))
    heading = normalize_rule_text(statement_info.get("heading", ""))

    if not text:
        return ""

    if previous_line.endswith("Please") and text[:1].islower():
        text = f"{previous_line} {text}"
    elif heading and heading.lower().startswith("please select less") and text[:1].islower():
        text = f"{heading} {text}"

    if re.search(r"\b(and|or|to|for|with|the|of|based on|in|are|will be|when)$", text.lower()) and next_line:
        text = f"{text} {next_line}"
    elif len(text.split()) <= 4 and next_line:
        text = f"{text} {next_line}"

    if previous_line and text[:1].islower() and len(previous_line.split()) <= 14:
        text = f"{previous_line} {text}"

    text = normalize_rule_text(text)
    text = re.sub(r"\s+([\.,])", r"\1", text)
    return text


def build_secondary_categories(requirement: dict) -> Dict[str, List[str]]:
    text = requirement.get("normalized_text", "")
    heading = str(requirement.get("source", {}).get("heading", ""))
    corpus = f"{heading} {text}".lower()
    derived: Dict[str, List[str]] = {k: [] for k in list(CATEGORY_PATTERNS) + EXTRA_RULE_CATEGORIES}

    if any(token in corpus for token in ["maximum", "minimum", "up to", "at most", "one or more", "quantity", "more than"]):
        derived["limits"].append(text)
    if any(token in corpus for token in ["eligible", "eligibility", "not eligible", "can be purchased", "available for"]):
        derived["eligibility_rules"].append(text)
    if any(token in corpus for token in ["sim-only orders", "sim accessories", "non-sim accessories", "device orders", "valid service line"]):
        derived["eligibility_rules"].append(text)
    if any(token in corpus for token in ["please", "warning", "show banner", "popup", "select less", "values not updated"]):
        derived["warning_messages"].append(text)
    if any(token in corpus for token in ["successfully", "completed", "added to the cart", "shown instantly"]):
        derived["success_messages"].append(text)
    if any(token in corpus for token in ["not added to the cart", "blocks", "block", "fails", "unable", "not valid", "not available"]):
        derived["negative_scenarios"].append(text)
    if any(token in corpus for token in ["disabled", "read only", "hidden/shown", "must not", "cannot"]):
        derived["restrictions"].append(text)
    if "rtsa" in corpus or "stockavailability" in corpus or "estimated shipment" in corpus or "esd" in corpus or "stock indicator consistency" in corpus:
        if any(token in corpus for token in ["when", "trigger", "on load", "search", "carousel", "postcode", "capacity", "colour", "once for each order", "stock indicator consistency", "invokepostconfiguration", "mpropositionnext"]):
            derived["rtsa_trigger_rules"].append(text)
        if any(token in corpus for token in ["show following products", "display in quote summary", "stockavailability", "estshipment", "errorcode", "errormsg", "sku"]):
            derived["rtsa_mapping_rules"].append(text)
        derived["rtsa_rules"].append(text)

    return derived


def extract_supplemental_rule_catalog(text: str, ui_journey_context: dict | None = None) -> Dict[str, List[str]]:
    catalog: Dict[str, List[str]] = {k: [] for k in list(CATEGORY_PATTERNS) + EXTRA_RULE_CATEGORIES}
    normalized = normalize_rule_text(text)
    lower = normalized.lower()

    if all(token in lower for token in ["invokepostconfiguration", "mpropositionnext", "stock indicator consistency"]):
        rule = (
            "The BS: VF TBUI MSO Utilities Method:mInvokePostConfiguration() invokes "
            "BS: VF TBUI MSO Utilities Method:mPropositionNext() once for each order to maintain and check stock indicator consistency."
        )
        catalog["rtsa_trigger_rules"].append(rule)
        catalog["rtsa_rules"].append(rule)
        catalog["business_rules"].append(rule)

    for rule in [
        "System allows SIM accessories for physical SIM orders.",
        "System allows non-SIM accessories when SIM type is eSIM.",
        "System allows progression when at least one valid service line exists.",
        "The items in your cart are not eligible for bundle and save.",
    ]:
        if normalize_rule_text(rule).lower() in normalized.lower() or any(rule.lower() in anchor for anchor in (ui_journey_context or {}).get("anchors", [])):
            catalog["eligibility_rules"].append(rule)

    return catalog


def filter_text_by_scope(text: str, scope_terms: list[str], scope_window: int = 4) -> tuple[str, dict]:
    if not scope_terms:
        return text, {"enabled": False, "scope_terms": [], "matched_blocks": 0, "total_blocks": 0}

    lines = text.splitlines()
    matches: list[int] = []
    for idx, raw in enumerate(lines):
        lowered = raw.lower()
        if any(term_matches_line(lowered, term) for term in scope_terms):
            matches.append(idx)

    keep: set[int] = set()
    for idx in matches:
        for offset in range(-scope_window, scope_window + 1):
            neighbor = idx + offset
            if 0 <= neighbor < len(lines):
                keep.add(neighbor)

    filtered_lines = [line for idx, line in enumerate(lines) if idx in keep]

    return "\n".join(filtered_lines), {
        "enabled": True,
        "scope_terms": scope_terms,
        "matched_lines": len(matches),
        "total_lines": len(lines),
        "kept_lines": len(keep),
        "window": scope_window,
    }


def build_scope_terms(figma_scope: str | None, hld_scope: str | None, fallback: list[str]) -> list[str]:
    terms: list[str] = []
    for candidate in [figma_scope or "", hld_scope or ""]:
        norm = normalize_line(candidate).lower()
        if norm:
            terms.append(norm)
            tokens = tokenize_scope(norm)
            for token in tokens:
                if token not in SCOPE_NOISE_TOKENS:
                    terms.append(token)
            if len(tokens) >= 2:
                terms.append(" ".join(tokens[:2]))
            if len(tokens) >= 3:
                terms.append(" ".join(tokens[:3]))

    if not terms:
        terms.extend(fallback)

    # Keep unique and meaningful terms only.
    deduped: list[str] = []
    for term in terms:
        if len(term) < 3:
            continue
        if term not in deduped:
            deduped.append(term)
    return deduped


def build_scope_tokens(scope_terms: List[str]) -> List[str]:
    tokens: List[str] = []
    for term in scope_terms:
        tokens.extend(tokenize_scope(term))
    return sorted(set(tokens))


def looks_like_message(text: str) -> bool:
    if '"' in text:
        return True
    return any(token in text.lower() for token in ["please", "must", "not allowed", "cannot"])


def is_noise(text: str) -> bool:
    lower = text.lower()
    if any(hint in lower for hint in EXCLUDE_HINTS):
        return True
    if re.search(r"\b[a-z0-9_]+\.[a-z0-9_]+\b", lower):
        return True
    if "matrix" in lower and "compatib" not in lower and "select" not in lower:
        return True
    if text.strip().endswith("?") and not looks_like_message(text):
        return True
    if len(text) > 260:
        return True
    return False


def has_behavior_signal(lower: str) -> bool:
    if any(hint in lower for hint in BEHAVIOR_HINTS):
        return True
    # Any category keyword also counts as behavioral signal.
    for hints in CATEGORY_PATTERNS.values():
        if any(hint in lower for hint in hints):
            return True
    return False


def has_scope_anchor(lower: str, scope_tokens: List[str]) -> bool:
    if not scope_tokens:
        return True
    return any(token in lower for token in scope_tokens)


def journey_relevance_score(text: str, scope_tokens: List[str], journey_context: dict | None = None) -> int:
    lower = text.lower()
    score = 0
    if has_scope_anchor(lower, scope_tokens):
        score += 2
    if has_behavior_signal(lower):
        score += 2
    if any(hint in lower for hint in BASE_DOMAIN_HINTS):
        score += 1
    anchors = (journey_context or {}).get("anchors", [])
    if anchors and any(anchor in lower for anchor in anchors):
        score += 2
    return score


def has_user_visible_signal(statement_info: dict) -> bool:
    corpus = " ".join(
        [
            statement_info.get("heading", ""),
            statement_info.get("text", ""),
            statement_info.get("previous_line", ""),
            statement_info.get("next_line", ""),
        ]
    ).lower()
    return any(hint in corpus for hint in USER_VISIBLE_HINTS)


def looks_like_requirement_statement(statement_info: dict) -> bool:
    text = normalize_rule_text(statement_info.get("text", ""))
    lower = text.lower()
    if len(text) < 12:
        return False
    if text.endswith(":") and len(text.split()) <= 6:
        return False
    if is_heading_like(text):
        return False
    if is_truncated_requirement(text):
        return False
    if not any(verb in lower for verb in REQUIREMENT_VERBS) and not looks_like_message(text):
        return False
    return True


def is_truncated_requirement(text: str) -> bool:
    return bool(re.search(r"\b(and|or|to|for|with|the|of|isn.?t|will be|when)\s*$", text.lower()))


def is_journey_relevant(statement_info: dict, scope_tokens: List[str], journey_context: dict | None = None) -> bool:
    text = statement_info.get("text", "")
    heading = statement_info.get("heading", "")
    normalized_text = normalize_rule_text(statement_info.get("normalized_text", "") or text)
    lower = text.lower()
    full_lower = " ".join([heading, statement_info.get("previous_line", ""), text, statement_info.get("next_line", "")]).lower()
    if is_noise(text):
        return False

    if len(normalized_text) > 320:
        return False

    if any(hint in full_lower for hint in SOFT_EXCLUDE_HINTS):
        return False

    if any(hint in full_lower for hint in FEATURE_EXCLUDE_HINTS):
        return False

    if not looks_like_requirement_statement(statement_info):
        return False

    score = journey_relevance_score(full_lower, scope_tokens, journey_context=journey_context)
    if score < 3:
        return False

    if not has_user_visible_signal(statement_info):
        return False

    has_domain = any(hint in full_lower for hint in BASE_DOMAIN_HINTS)
    if looks_like_message(text):
        return has_domain or score >= 3

    return has_domain


def normalize_rule_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\u201c", '"').replace("\u201d", '"').strip())


def normalize_hld_cleanup_text(text: str) -> str:
    cleaned = normalize_rule_text(text)
    replacements = {
        "forphysical": "for physical",
        "rata plan": "rate plan",
        "SIM‑Only": "SIM-Only",
        "non‑SIM": "non-SIM",
        "in‑stock": "in-stock",
        "out‑of‑stock": "out-of-stock",
    }
    for old, new in replacements.items():
        cleaned = cleaned.replace(old, new)
    return cleaned


def is_case_table_fragment(text: str) -> bool:
    lower = text.lower()
    if lower.startswith("case "):
        return True
    if lower.startswith("col ") and " case " in lower:
        return True
    if sum(lower.count(token) for token in [" case ", "col ", "nwtotargetnw", "changelocation", "additionalconnect"]) >= 3:
        return True
    return False


def is_truncated_hld_statement(text: str) -> bool:
    lower = text.lower().strip()
    if not lower:
        return True
    if lower.endswith(":") or lower.endswith("+") or lower.endswith("/"):
        return True
    if lower.endswith("ex.") or lower.endswith("based on") or lower.endswith("shown to") or lower.endswith("will not be"):
        return True
    if re.search(r"\b(pr|incluorder|proimplemente|nwtotargetnw|changelocation)\b", lower):
        return True
    return False


def is_misclassified_rtsa_text(text: str) -> bool:
    lower = text.lower()
    rtsa_markers = ["rtsa", "stockavailability", "estimated shipment", "esd", "errorcode", "errormsg", "invokepostconfiguration", "mpropositionnext"]
    if any(marker in lower for marker in rtsa_markers):
        return False
    if "stock" in lower and "availability" in lower:
        return False
    return True


def should_drop_rule_entry(category: str, text: str) -> bool:
    lower = text.lower().strip()
    if not lower:
        return True
    if is_case_table_fragment(text):
        return True
    if is_truncated_hld_statement(text):
        return True
    if "templates name = vha nsa sales calculator" in lower:
        return True
    if lower in {'"vf au simo csr" + product line:', '"vf au simo csr" / product line:'}:
        return True
    if "single buttons should coexist" in lower:
        return True
    if category in {"rtsa_rules", "rtsa_trigger_rules", "rtsa_mapping_rules"} and is_misclassified_rtsa_text(text):
        return True
    return False


def dedupe_prefer_longer(values: List[str]) -> List[str]:
    ordered: List[str] = []
    for value in sorted(set(values), key=lambda x: (-len(x), x.lower())):
        if any(value.lower() in existing.lower() for existing in ordered):
            continue
        ordered.append(value)
    return sorted(ordered)


def cleanup_rule_catalog(out: Dict[str, List[str]], requirements: List[dict[str, Any]], classification_log: List[dict]) -> tuple[Dict[str, List[str]], List[dict[str, Any]], List[dict]]:
    cleaned_catalog: Dict[str, List[str]] = {}
    allowed_by_category: Dict[str, set[str]] = {}

    for category, values in out.items():
        cleaned_values: List[str] = []
        for value in values:
            normalized = normalize_hld_cleanup_text(value)
            if normalized == "Please select less Accessories and refer the customer to a store to purchase any additional":
                normalized = "Please select less Accessories and refer the customer to a store to purchase any additional accessories."
            if normalized == "Please select plan. phones,":
                normalized = "Please select plan."
            if should_drop_rule_entry(category, normalized):
                continue
            if category == "validation_scenarios" and "technology type technology description" in normalized.lower():
                continue
            if category == "success_messages" and not any(token in normalized.lower() for token in ["success", "completed", "shown instantly", "added to the cart"]):
                continue
            if category == "success_messages" and "not added to the cart" in normalized.lower():
                continue
            if category == "warning_messages" and not any(token in normalized.lower() for token in ["please", "warning", "popup", "values not updated", "maximum"]):
                continue
            if category == "warning_messages" and "compatibility check will happen" in normalized.lower():
                normalized = "Compatibility issues are shown in a popup on Update cart."
            if category == "compatibility_rules":
                if "compatibility check will happen" in normalized.lower():
                    normalized = "Compatibility check will happen on Update cart button click."
                elif normalized.lower().startswith("small simo"):
                    normalized = "Compatibility check will happen on Update cart button click."
                elif normalized.lower().startswith("update cart button click based on"):
                    normalized = "Compatibility check will happen on Update cart button click."
            cleaned_values.append(normalized)

        cleaned_values = dedupe_prefer_longer(cleaned_values)
        cleaned_catalog[category] = cleaned_values
        allowed_by_category[category] = {v.lower() for v in cleaned_values}

    if not cleaned_catalog.get("compatibility_rules"):
        fallback = [
            normalize_hld_cleanup_text(x)
            for x in cleaned_catalog.get("business_rules", [])
            if "compatible" in x.lower() or "compatibility" in x.lower()
        ]
        cleaned_catalog["compatibility_rules"] = dedupe_prefer_longer(fallback)
        allowed_by_category["compatibility_rules"] = {v.lower() for v in cleaned_catalog["compatibility_rules"]}
    else:
        cleaned_catalog["compatibility_rules"] = dedupe_prefer_longer(cleaned_catalog["compatibility_rules"])
        allowed_by_category["compatibility_rules"] = {v.lower() for v in cleaned_catalog["compatibility_rules"]}

    if not cleaned_catalog.get("rtsa_mapping_rules"):
        fallback = [x for x in cleaned_catalog.get("rtsa_rules", []) if "stockavailability" in x.lower() or "errorcode" in x.lower()]
        cleaned_catalog["rtsa_mapping_rules"] = dedupe_prefer_longer(fallback)
        allowed_by_category["rtsa_mapping_rules"] = {v.lower() for v in cleaned_catalog["rtsa_mapping_rules"]}

    cleaned_requirements: List[dict[str, Any]] = []
    for req in requirements:
        category = str(req.get("category", ""))
        normalized = normalize_hld_cleanup_text(str(req.get("normalized_text", req.get("text", ""))))
        if should_drop_rule_entry(category, normalized):
            continue
        if normalized.lower() not in allowed_by_category.get(category, set()):
            continue
        req["text"] = normalized
        req["normalized_text"] = normalized
        cleaned_requirements.append(req)

    cleaned_log: List[dict] = []
    for row in classification_log:
        category = row.get("category")
        normalized = normalize_hld_cleanup_text(str(row.get("normalized_text") or row.get("statement", "")))
        if category and should_drop_rule_entry(str(category), normalized):
            continue
        if category and normalized.lower() not in allowed_by_category.get(str(category), set()):
            continue
        row["statement"] = normalize_hld_cleanup_text(str(row.get("statement", normalized)))
        row["normalized_text"] = normalized
        cleaned_log.append(row)

    return cleaned_catalog, cleaned_requirements, cleaned_log


def extract_rule_template(line: str) -> dict | None:
    normalized = normalize_rule_text(line)

    m_if = RULE_TEMPLATES["if_then"].search(normalized)
    if m_if:
        return {
            "template_type": "if_then",
            "condition": normalize_rule_text(m_if.group("condition")),
            "outcome": normalize_rule_text(m_if.group("outcome")),
        }

    m_when = RULE_TEMPLATES["when_then"].search(normalized)
    if m_when:
        return {
            "template_type": "when_then",
            "trigger": normalize_rule_text(m_when.group("trigger")),
            "outcome": normalize_rule_text(m_when.group("outcome")),
        }

    m_value = RULE_TEMPLATES["value_set"].search(normalized)
    if m_value:
        values = [normalize_rule_text(v) for v in re.split(r",|/| and ", m_value.group("values")) if normalize_rule_text(v)]
        return {
            "template_type": "value_set",
            "object": normalize_rule_text(m_value.group("object")),
            "values": values,
        }

    m_must = RULE_TEMPLATES["must_rule"].search(normalized)
    if m_must and m_must.group("action"):
        actor = normalize_rule_text(m_must.group("actor") or "system")
        return {
            "template_type": "obligation",
            "actor": actor,
            "action": normalize_rule_text(m_must.group("action")),
        }

    return None


def classify_statement(statement_info: dict) -> Tuple[str | None, Dict[str, int], dict | None]:
    line = statement_info.get("normalized_text") or statement_info.get("text", "")
    heading = statement_info.get("heading", "")
    previous_line = statement_info.get("previous_line", "")
    next_line = statement_info.get("next_line", "")
    lower = line.lower()
    context_lower = " ".join([heading, previous_line, line, next_line]).lower()
    template = extract_rule_template(line)
    scores: Dict[str, int] = {}
    for category, patterns in CATEGORY_PATTERNS.items():
        hit_count = sum(1 for p in patterns if p in lower)
        hit_count += sum(1 for p in patterns if p in heading.lower())
        hit_count += sum(1 for p in patterns if p in previous_line.lower() or p in next_line.lower())
        if hit_count > 0:
            scores[category] = hit_count

    if "compatible" in context_lower:
        scores["compatibility_rules"] = scores.get("compatibility_rules", 0) + 1
    if "check store stock" in context_lower:
        scores["stock_rules"] = scores.get("stock_rules", 0) + 1
    if "rtsa" in context_lower or "stockavailability" in context_lower or "vhagetstockavailability" in context_lower:
        scores["rtsa_rules"] = scores.get("rtsa_rules", 0) + 2

    if template:
        template_type = template.get("template_type")
        if template_type in {"if_then", "when_then", "obligation"}:
            scores["business_rules"] = scores.get("business_rules", 0) + 2
        if template_type == "value_set":
            scores["boundary_scenarios"] = scores.get("boundary_scenarios", 0) + 2
        if any(x in context_lower for x in ["not allowed", "cannot", "unable", "invalid"]):
            scores["negative_scenarios"] = scores.get("negative_scenarios", 0) + 2
        if any(x in context_lower for x in ["must", "required", "please select"]):
            scores["validation_scenarios"] = scores.get("validation_scenarios", 0) + 1

    if any(x in heading.lower() for x in ["validation", "warning", "message", "stock", "eligibility", "compatibility"]):
        for category, patterns in CATEGORY_PATTERNS.items():
            if any(x in heading.lower() for x in patterns):
                scores[category] = scores.get(category, 0) + 2

    if any(x in context_lower for x in ["show the list", "will be shown", "shown instantly", "added to the cart"]):
        scores["business_rules"] = scores.get("business_rules", 0) + 2
    if any(x in context_lower for x in ["select less", "show banner", "popup", "warning"]):
        scores["warning_messages"] = scores.get("warning_messages", 0) + 2
    if any(x in context_lower for x in ["not eligible", "eligible", "eligibility"]):
        scores["eligibility_rules"] = scores.get("eligibility_rules", 0) + 2
    if any(x in context_lower for x in ["maximum", "minimum", "one or more", "more than"]):
        scores["limits"] = scores.get("limits", 0) + 2
    if any(x in context_lower for x in ["completed", "successfully"]):
        scores["success_messages"] = scores.get("success_messages", 0) + 2

    if not scores:
        return None, {}, template

    best_score = max(scores.values())
    candidates = [c for c, s in scores.items() if s == best_score]
    for preferred in CATEGORY_PRIORITY:
        if preferred in candidates:
            return preferred, scores, template
    return candidates[0], scores, template


def extract_rules(
    text: str,
    scope_terms: list[str] | None = None,
    figma_scope: str | None = None,
    hld_scope: str | None = None,
    ui_scope_terms: list[str] | None = None,
    ui_journey_context: dict | None = None,
    scope_window: int = 2,
) -> dict:
    effective_scope_terms = build_scope_terms(figma_scope, hld_scope, scope_terms or [])
    if ui_scope_terms:
        for term in ui_scope_terms:
            if term not in effective_scope_terms:
                effective_scope_terms.append(term)
    scope_tokens = build_scope_tokens(effective_scope_terms)
    filtered_text, scope_meta = filter_text_by_scope(text, effective_scope_terms, scope_window=scope_window)
    statements = extract_contextual_statements(filtered_text)
    for row in statements:
        row["normalized_text"] = normalize_statement_with_context(row)
    statements = [row for row in statements if is_journey_relevant(row, scope_tokens, journey_context=ui_journey_context)]
    out: Dict[str, List[str]] = {k: [] for k in list(CATEGORY_PATTERNS) + EXTRA_RULE_CATEGORIES}
    classification_log: List[dict] = []
    unclassified: List[str] = []
    requirements: List[dict[str, Any]] = []
    req_id = 1

    for statement_info in statements:
        line = statement_info.get("text", "")
        category, score_map, template = classify_statement(statement_info)
        normalized_line = normalize_rule_text(statement_info.get("normalized_text") or line)
        relevance = journey_relevance_score(
            " ".join(
                [
                    statement_info.get("heading", ""),
                    statement_info.get("previous_line", ""),
                    normalized_line,
                    statement_info.get("next_line", ""),
                ]
            ),
            scope_tokens,
            ui_journey_context,
        )
        if not category:
            unclassified.append(line)
            classification_log.append(
                {
                    "statement": line,
                    "heading": statement_info.get("heading", ""),
                    "previous_line": statement_info.get("previous_line", ""),
                    "next_line": statement_info.get("next_line", ""),
                    "category": None,
                    "scores": score_map,
                    "rule_template": template,
                    "journey_relevance_score": relevance,
                    "status": "unclassified",
                }
            )
            continue

        out[category].append(normalized_line)
        classification_log.append(
            {
            "statement": line,
            "normalized_text": normalized_line,
                "heading": statement_info.get("heading", ""),
                "previous_line": statement_info.get("previous_line", ""),
                "next_line": statement_info.get("next_line", ""),
                "category": category,
                "scores": score_map,
                "rule_template": template,
                "journey_relevance_score": relevance,
                "status": "classified",
            }
        )

        requirements.append(
            {
                "id": f"HLD-REQ-{req_id:04d}",
                "category": category,
                "text": normalized_line,
                "normalized_text": normalized_line,
                "source": {
                    "file": "hld_document",
                    "heading": statement_info.get("heading", "HLD extracted statements"),
                    "neighbor_lines": [statement_info.get("previous_line", ""), statement_info.get("next_line", "")],
                    "section": category,
                    "text": line,
                },
                "confidence": round(min(0.98, 0.55 + (0.08 * min(4, len(score_map))) + (0.04 * min(5, relevance))), 2),
                "rule_template": template,
            }
        )
        req_id += 1

    for requirement in requirements:
        secondary = build_secondary_categories(requirement)
        for key, values in secondary.items():
            out[key].extend(values)

    supplemental = extract_supplemental_rule_catalog(text, ui_journey_context=ui_journey_context)
    for key, values in supplemental.items():
        out[key].extend(values)

    if not out["warning_messages"]:
        out["warning_messages"].extend([x for x in out["validation_scenarios"] if looks_like_message(x) or "select less" in x.lower()])
    if not out["limits"]:
        out["limits"].extend([x for x in out["validation_scenarios"] if any(t in x.lower() for t in ["maximum", "more than", "one or more"])])
    if not out["negative_scenarios"]:
        out["negative_scenarios"].extend([x for x in out["business_rules"] if "not added to the cart" in x.lower() or "block" in x.lower()])
    if not out["eligibility_rules"] and ui_journey_context:
        if any("not eligible" in x for x in ui_journey_context.get("anchors", [])):
            out["eligibility_rules"].append("The items in your cart are not eligible for bundle and save.")
    if not out["rtsa_trigger_rules"]:
        derived_triggers = [
            x
            for x in out["business_rules"] + out["rtsa_rules"]
            if any(token in x.lower() for token in ["once for each order", "stock indicator consistency", "invokepostconfiguration", "mpropositionnext"])
        ]
        out["rtsa_trigger_rules"].extend(derived_triggers)
    if not out["success_messages"] and ui_journey_context:
        if any("completed" in x for x in ui_journey_context.get("anchors", [])):
            out["success_messages"].append("Bundle and save calculation is completed.")
    if not out["warning_messages"] and ui_journey_context:
        if any("values not updated" in x for x in ui_journey_context.get("anchors", [])):
            out["warning_messages"].append("Values not updated Some items in your cart need final values to be calculated before proceeding. Please click Calculate Bundle & Save to update pricing and proceed.")

    for key in out:
        out[key] = sorted(set(out[key]))

    out, requirements, classification_log = cleanup_rule_catalog(out, requirements, classification_log)

    messages = [x.get("text", "") for x in statements if looks_like_message(x.get("text", ""))]

    return {
        "rule_catalog": out,
        "candidate_messages": sorted(set(messages)),
        "counts": {k: len(v) for k, v in out.items()},
        "journey_scope_filter": scope_meta,
        "classification_log": classification_log,
        "unclassified_statements": sorted(set(unclassified)),
        "requirements": requirements,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract HLD rule catalog from markdown or PDF")
    parser.add_argument("--input", required=True, help="HLD path (.md or .pdf)")
    parser.add_argument("--output", required=True, help="Output rule catalog JSON path")
    parser.add_argument("--figma-scope", default="", help="Requested Figma journey scope (e.g., Mobile PLP)")
    parser.add_argument("--hld-scope", default="", help="Requested HLD feature/module scope (e.g., Sales Calculator - New Customer)")
    parser.add_argument("--ui-catalog", default="", help="Optional UI catalog JSON to derive additional journey vocabulary for HLD filtering")
    parser.add_argument("--debug", action="store_true", help="Enable debug artifact generation")
    parser.add_argument("--debug-dir", default="", help="Optional directory for debug artifacts")
    parser.add_argument("--enforce-quality-gates", action="store_true", help="Fail execution when quality gates are violated")
    parser.add_argument("--max-unclassified", type=int, default=0, help="Maximum allowed unclassified statements when quality gates are enforced")
    parser.add_argument(
        "--journey-scope-filter",
        default="",
        help="Optional scope keywords/patterns (pipe/comma/semicolon separated) used to keep only journey-relevant sections",
    )
    parser.add_argument(
        "--scope-window",
        type=int,
        default=1,
        help="Number of neighboring text blocks to keep around a scope match",
    )
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    args = parser.parse_args()

    logging.basicConfig(level=getattr(logging, args.log_level), format="%(levelname)s: %(message)s")

    in_path = Path(args.input)
    out_path = Path(args.output)

    if not in_path.exists():
        raise FileNotFoundError(f"Input HLD not found: {in_path}")

    text = read_hld_text(in_path)
    scope_terms = parse_scope_terms(args.journey_scope_filter)
    ui_scope_terms = load_ui_scope_terms(args.ui_catalog)
    ui_journey_context = load_ui_journey_context(args.ui_catalog)
    payload = extract_rules(
        text,
        scope_terms=scope_terms,
        figma_scope=args.figma_scope,
        hld_scope=args.hld_scope,
        ui_scope_terms=ui_scope_terms,
        ui_journey_context=ui_journey_context,
        scope_window=args.scope_window,
    )
    effective_scope_terms = build_scope_terms(args.figma_scope, args.hld_scope, scope_terms)
    if ui_scope_terms:
        for term in ui_scope_terms:
            if term not in effective_scope_terms:
                effective_scope_terms.append(term)
    if effective_scope_terms:
        _, scope_meta = filter_text_by_scope(text, effective_scope_terms, scope_window=args.scope_window)
        payload["journey_scope_filter"] = scope_meta
        payload["journey_scope_filter"]["scope_window"] = args.scope_window
        payload["journey_scope_filter"]["applied_to"] = str(in_path)
        payload["journey_scope_filter"]["figma_scope"] = args.figma_scope
        payload["journey_scope_filter"]["hld_scope"] = args.hld_scope

    classification_entries = payload.get("classification_log", [])
    statements = [x.get("statement", "") for x in classification_entries if x.get("statement")]
    duplicate_count = max(0, len(statements) - len(set(statements)))
    unclassified_count = len(payload.get("unclassified_statements", []))
    payload["quality_gates"] = {
        "max_unclassified": args.max_unclassified,
        "unclassified_count": unclassified_count,
        "duplicate_statement_count": duplicate_count,
        "requirements_count": len(payload.get("requirements", [])),
        "passed": unclassified_count <= args.max_unclassified,
    }

    payload["journey_context"] = ui_journey_context

    if args.enforce_quality_gates and unclassified_count > args.max_unclassified:
        raise ValueError(
            f"Quality gate failed: unclassified statements={unclassified_count} > max_unclassified={args.max_unclassified}"
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    LOG.info("HLD rules written: %s", out_path)

    if args.debug:
        debug_dir = Path(args.debug_dir) if args.debug_dir else out_path.parent
        debug_dir.mkdir(parents=True, exist_ok=True)
        (debug_dir / "hld_rules.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        (debug_dir / "classification_log.json").write_text(
            json.dumps(
                {
                    "applied_to": str(in_path),
                    "figma_scope": args.figma_scope,
                    "hld_scope": args.hld_scope,
                    "scope_window": args.scope_window,
                    "total_statements": len(payload.get("classification_log", [])),
                    "classified": sum(1 for x in payload.get("classification_log", []) if x.get("status") == "classified"),
                    "unclassified": sum(1 for x in payload.get("classification_log", []) if x.get("status") == "unclassified"),
                    "quality_gates": payload.get("quality_gates", {}),
                    "entries": payload.get("classification_log", []),
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
