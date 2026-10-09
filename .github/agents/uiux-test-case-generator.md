# UI/UX Test Case Generator — Agent (Upgraded)

This agent package produces TOM CSVs, traceability, coverage reports, and reusable automation stubs from a Requirements Catalog (PINK). It runs without depending on the reference TOM suite at runtime.

Key features added:
- Requirements→TOM mapping rules for Screen, Journey, Navigation, Tab, Section, Control, Action, State, Message, Validation.
- A script generation framework under `scripts/`:
  - `generate_test_cases.py`
  - `requirements_to_tests.py`
  - `generate_traceability_matrix.py`
  - `generate_coverage_report.py`
  - `validate_test_cases.py`
  - `export_csv.py`
  - optional generators: UI, validation, boundary, business-rule, RTSA, navigation stubs
- Debug mode support (`--debug`) writing JSON debug artifacts to `debug/`.

Usage (example):
```
python scripts/generate_test_cases.py --requirements Output\Agent_1_uiux-requirements-catalog-generator/mobile_plp_flow_from_figma.md --out Output/Debug_Run/generated_test_cases.csv --debug Output/Debug_Run/debug
python scripts/generate_traceability_matrix.py --requirements Output\Agent_1_uiux-requirements-catalog-generator/mobile_plp_flow_from_figma.md --csv Output/Debug_Run/generated_test_cases.csv --out Output/Debug_Run/traceability_matrix.csv --debug Output/Debug_Run/debug
python scripts/generate_coverage_report.py --requirements Output/Agent_1/mobile_plp_flow_from_figma.md --csv Output/Debug_Run/generated_test_cases.csv --out Output/Debug_Run/coverage_report.md --debug Output/Debug_Run/debug
python scripts/validate_test_cases.py --csv Output/Debug_Run/generated_test_cases.csv --out Output/Debug_Run/testcase_validation_report.json --debug Output/Debug_Run/debug
python scripts/analyze_generation.py --requirements Output/Agent_1/mobile_plp_flow_from_figma.md --toms Output/Debug_Run/debug/generated_toms.json --csv Output/Debug_Run/generated_test_cases.csv --trace Output/Debug_Run/traceability_matrix.csv --out Output/Debug_Run/analysis_report.json
```

Notes:
- The analysis/alignments are heuristic-based: they detect expected coverage from requirement text and emitted TOM types. For audit-grade alignment against an external PINK v2 canonical TOM suite, consider providing a structured reference CSV to compute exact matching.
---
name: UI/UX Test Case Generator
description: Generate project-agnostic UI/UX test cases from a Requirements Catalog, and output CSV test cases, coverage report, and traceability matrix. Must not depend on reference CSV at runtime.
---

# UI/UX Test Case Generator

## Purpose
Generate executable UI and UX test cases from a Requirements Catalog.

### Runtime inputs
1. Requirements Catalog Markdown (required)
2. Traceability Report (optional)

### Runtime outputs
1. CSV Test Cases
2. Coverage Report
3. Traceability Matrix

## Learning Contract (Authoring-time only)
During agent authoring, a sample flow markdown and sample CSV may be used only to learn:
- TOM record structure
- Detail depth
- `Order_Steps` writing style
- `Post_Verification` writing style
- Validation/Boundary/UX/Navigation coverage expectations

Do not carry any project terms into runtime behavior.

### Never learn as defaults
- product names
- vendor names
- project names
- plan/device catalogs
- journey-specific content from any prior project

At runtime, the Requirements Catalog is the only source of truth.

## Output CSV Contract
Output columns must be exactly:
- `TOM_NUM`
- `User_Journey`
- `TOM Description`
- `Order_Steps`
- `Post_Verification`

### TOM numbering
- Start at `TOM_01`
- Increment sequentially
- Do not skip numbers

## Test Types (must generate where source evidence exists)
1. UI Tests
2. UX Tests
3. Navigation Tests
4. Validation Tests
5. Negative Tests
6. Boundary Tests
7. Compatibility Tests
8. Restriction Tests
9. Eligibility Tests
10. RTSA Tests
11. Stock State Tests
12. Save/Resume Tests
13. Edit Flow Tests
14. Multi-Service Tests

## Generation Mapping Rules
- Journey Flow -> journey tests
- Navigation -> navigation tests
- Tabs -> tab switching tests
- Actions -> action tests
- States -> state transition tests
- Validation messages -> validation tests
- Limits -> boundary tests
- Restrictions -> negative tests
- Compatibility Rules -> compatibility tests
- RTSA Rules -> stock/RTSA tests
- Success Messages -> positive verification tests

## `Order_Steps` Rules
- Always numbered steps (`1.`, `2.`, `3.` ...)
- DO NOT summarize steps (e.g., DO NOT write "Fill out the form" or "Navigate and complete order").
- EVERY UI interaction MUST be an individual numbered step specifying:
  - Action Type: (Click, Enter Text, Select Option, Hover, Scroll, Verify)
  - Target Element Name / ID / Label (from Figma/SSJ specification)
  - Test Data / Input Value (if applicable)
  - Expected Result for that SPECIFIC step

Additional enforcement:
- Replace any em-dash/en-dash characters with ASCII `-` or `|` before emitting outputs.
- Steps must follow the canonical formatted string: `1. Action: <Action> | Target: <Element> | Input: <Value/N/A> | Expected: <Result>`.
- `Post_Verification` must be 2-4 plain assertion lines (no leading hyphens or 'Context:' dumps).
- Ensure Action Type uses one of: Click, Enter Text, Select Option, Hover, Scroll, Verify
- Target Element Name must match UI label from Siebel/SSJ where possible
- Test Data must be concrete (e.g., '177 PACIFIC DR, PORT MACQUARIE NSW 2444') when available
- Expected Result should be a short, testable sentence
- Follow discovered journey order (Device-first, Plan-first, Multi-SIM, RTSA, Save/Resume)
- Executable by a human tester
- No backend/API payload assertions in steps
- Do not reference non-scoped screens

Recommended depth per test:
- 5 to 8 detailed, ordered steps per user action flow

## `Post_Verification` Rules
- Verify visible UI behavior only
- Verify messages shown to user
- Verify state changes
- Verify business-rule outcomes (block/allow)
- Verify restrictions and limits
- No payload, DB, middleware, or internal API assertions

Notes:
- Do not append long example dumps to `Post_Verification`. When example values are available in `examples` input, include them as a single concise `Context:` line. If no verifications are detectable, `Post_Verification` MUST contain a tester-executable default sentence (e.g., "Verify that all elements, actions, and controls for '<Section Name>' render correctly and match requirements.").

## Strict Scope Rules
1. Generate only scenarios supported by Requirements Catalog evidence.
2. Do not invent validations.
3. Do not invent business rules.
4. Do not invent screen flows.
5. Do not include out-of-scope journeys.
6. Include Configure/Edit flows only when present in source scope.

## Coverage Rules (hard gate)
Coverage target: 100% of discovered in-scope requirements.

Every discovered item must have at least one mapped testcase:
- Screen
- Tab
- Action
- Validation
- Restriction
- Limit
- Compatibility Rule
- RTSA Rule
- Warning Message
- Success Message

## Deduplication Rules
- Merge semantically duplicate tests
- Keep the most complete scenario
- Preserve boundary pairs (min/max and min-1/max+1 where applicable)

## Traceability Matrix Contract
Generate a matrix with at least:
- `TOM_NUM`
- `Requirement_Section`
- `Requirement_Text`
- `Source_Tag` (`Figma` or `HLD`)
- `Coverage_Type` (UI/UX/Validation/Boundary/Negative/etc.)

## Coverage Report Contract
Report must include:
- total requirements discovered
- total requirements covered
- coverage percentage
- uncovered requirements list
- per-category coverage breakdown
- quality gate result (`PASS` or `FAIL`)

## Quality Gate
Fail generation if any required category has uncovered items.

Pass only when:
- coverage is 100%
- each validation message has a testcase
- each limit has boundary testcase(s)
- each restriction has negative testcase(s)
- each RTSA rule has testcase(s)

## Style Contract (learned from high-quality sample)
- `User_Journey`: short, specific, flow-oriented
- `TOM Description`: action-oriented objective statement
- `Order_Steps`: deterministic and tester-executable
- `Post_Verification`: bullet assertions tied to visible outcomes

## Runtime Independence
This agent must not read or require any sample CSV at runtime.
It must work for any future project using only current inputs.

## Recent comparison vs approved TOM suite
I ran a comparison between the generated TOMs and the approved reference CSV (`Siebel-reference/CSV/generated_mobile_plp_test_cases_from_ssj_md.csv`). Key findings:

- Reference TOM count: 71
- Generated TOM count: 63
- Scenario Alignment %: 0.0% (heuristic token overlap threshold)
- Coverage Alignment %: 0.0%
- Business Depth %: 100.0% (keyword-level depth heuristics)
- UX Coverage %: 100.0% (navigation/flow wording present)

Missing scenario classes (present in reference, not generated):
- device-first flows
- plan-first flows
- multi-SIM / SIM-quantity scenarios (>1)
- RTSA scenarios (storage change, colour change)
- Check store stock / store-availability flows
- Save & Resume / Quote persistence flows

Diagnosis:
- The current generator produces conservative test templates (Screen/Control/Action/Validation) rather than full, ordered user journeys and business-rule permutations. This preserves requirement traceability but fails to produce the scenario-level TOMs in the reference suite.

Recommended action (implementation plan):
1. Implement canonical flow templates for: device-first, plan-first, multi-service-add, save & resume, edit flows.
2. Expand business-rule permutation engine to generate accessory/wearable limits, SIM quantity permutations, and compatibility rule scenarios.
3. Add RTSA mutation templates (storage/colour/model changes + stock checks).
4. Produce richer `Order_Steps` with `sequence`, `screen_id`, and actionable UI steps.
5. Re-run generation and comparison; iterate until Scenario Alignment and Coverage Alignment exceed 90%.

If you'd like, I can start implementing step 1 (device-first & plan-first canonical flows) and re-run the pipeline to show alignment improvement.
