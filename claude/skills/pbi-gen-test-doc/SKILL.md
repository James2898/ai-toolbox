---
name: pbi-gen-test-doc
description: Parses a PBI document (PDF or Markdown), audits the codebase against acceptance criteria, gets user approval on test scenarios, and generates a structured test plan .md file
allowed-tools:
  - Read
  - Write
  - Glob
  - Grep
  - Bash
  - Agent
  - AskUserQuestion
user-invocable: true
---

# PBI Audit & Test Plan Generator Skill

This Skill sits at the top of the QA pipeline. It accepts a PBI document (PDF or Markdown) as input and automates the following:

1. **Executive Summary** — Extracts and structures user stories and acceptance criteria from the PBI
2. **Codebase Audit** — Verifies whether each acceptance criterion is implemented in the codebase
3. **Scenario Approval Gate** — Presents a draft list of test scenarios for the user to review, edit, and approve
4. **Test Plan .md Generation** — Outputs a structured test plan in the same table format as the team's QA documents (No / Test Scenario / Test Detail / Actions / Expected / Date / Result)

## Position in the Pipeline

```
/pbi-gen-test-doc (this Skill)          ← entry point
    → {qa_out_dir}/{pbi_id}_test_plan.md

(your project's QA tooling)             ← e.g. generate an automation/execution format
(your project's QA tooling)             ← e.g. import cases into a tracker/sheet
(your project's QA tooling)             ← e.g. run the e2e suite
```

> **Output folder.** `{qa_out_dir}` is `docs.qa_out_dir` from the project profile (see the toolbox README), or `.qa/` when there is no profile. Keep it gitignored.

---

## STEP 1: Input

Accept the PBI document path from the user.

**Supported input formats**:
- PDF file path (e.g. `~/Downloads/PBI-3623.pdf`)
- PBI directory path (e.g. `docs/backlog/archives/PBI-3623-work-budget/`)
- Markdown file path (e.g. `docs/backlog/archives/PBI-3623-work-budget/requirements.md`)

If no argument is provided, use `AskUserQuestion` to ask the user for the path.

---

## STEP 2: Input Validation

**For PDF**: Read directly using the `Read` tool (Claude's native PDF reading — no Python or shell).

**For directory**: Search with `Glob`:
- `{dir}/requirements.md` (required)
- `{dir}/design.md` (optional)
- `{dir}/tasks.md` (optional)

If the required file does not exist, display an error message and stop.

---

## STEP 3: Launch pbi-test-doc-generator Agent

Launch `pbi-test-doc-generator` using the `Agent` tool:

```
Agent(
  subagent_type: "pbi-test-doc-generator",
  prompt: "
    Analyze the following PBI document:
    - Input path: {input_path}
    - Input type: {pdf|directory|markdown}
    - Codebase root: {codebase_root}  ← current working directory

    Phase 1: Parse the PBI (generate Executive Summary)
    Phase 2: Audit the codebase (classify each AC as IMPLEMENTED / MISSING / DEVIATED / EXTRA)
    Phase 3: Draft test scenarios (titles only, grouped by category)

    Return results as JSON.
  "
)
```

Note: The agent runs in an isolated context and does not pollute the main conversation.

---

## STEP 4: Display Audit Results

Format the JSON returned by the agent into three sections and display to the user:

### Section 1: Executive Summary
```
## Executive Summary

PBI: {pbi_id} — {title}
Summary: {summary}

User Stories:
  - US-001: ...
  - US-002: ...

Acceptance Criteria: {N} items
```

### Section 2: Codebase Audit
```
## Codebase Audit

| AC | Description | Status | Evidence | Notes |
|---|---|---|---|---|
| AC-001 | ... | ✅ IMPLEMENTED | path:line | |
| AC-002 | ... | ❌ MISSING | — | No code found |
| AC-003 | ... | ⚠️ DEVIATED | path:line | Expected X, code does Y |

Extra behaviors (in code but not in AC):
  - ...
```

### Section 3: Proposed Test Scenarios
```
## Proposed Test Scenarios ({N} total)

1. [Happy Path] PM task budget appears for single month
2. [Happy Path] PM task budget distributed across months
3. [Aggregation] Multiple PM tasks same employee — aggregated
4. [Data Refresh] Export reflects updated PM task dates
5. [Edge Cases] PM task with null start_date excluded
...
```

---

## STEP 5: User Approval Gate

### 5a: Display additional surfaces (if any)

If the `pbi-test-doc-generator` JSON contains a non-empty `additional_surfaces` array, display them before asking for approval:

```
## Additional Surfaces Found

The following surfaces share data or code with the primary feature.
You may include their regression scenarios in the test plan.

Surface 1: {surface_name}
  Entry point : {entry_point}
  Shared via  : {shared_term}
  Impact      : {pbl_impact}
  Scenario    : "{regression_title}"

Surface 2: ...

Type the number(s) to include (e.g. "1 2"), "none" to skip, or "all" to include all.
```

Wait for user input. For each surface the user selects, append its `regression_title` as a new scenario in the `Regression` category of the main scenario list before proceeding.

### 5b: Ask for scenario approval

```
AskUserQuestion(
  question: "Please review the test scenarios above. Type 'approve' to proceed, or describe any changes (add / remove / rename scenarios).",
  header: "TestScenarioApproval"
)
```

If the user provides changes:
- Add scenario → append to list
- Remove scenario → remove from list
- Rename scenario → update the entry
- "approve" → proceed to STEP 6

---

## STEP 6: Launch pbi-test-doc-writer Agent

Pass the approved scenario list and audit results to `pbi-test-doc-writer`:

```
Agent(
  subagent_type: "pbi-test-doc-writer",
  prompt: "
    Generate a test plan .md file from the following:
    - PBI ID: {pbi_id}
    - PBI Title: {title}
    - Approved scenarios: {approved_scenarios_json}
    - Audit results: {audit_json}
    - Output path: {qa_out_dir}/{pbi_id}_test_plan.md
  "
)
```

Before launching, run `mkdir -p {qa_out_dir}/` via `Bash` to ensure the output directory exists.

---

## STEP 7: Completion Report

```
## Test Plan Generated

- PBI: {pbi_id} — {title}
- Test scenarios: {N}
- Output: {qa_out_dir}/{pbi_id}_test_plan.md

Audit summary:
  - IMPLEMENTED: {X}
  - MISSING: {Y}
  - DEVIATED: {Z}
  - EXTRA: {W}

Next steps:
1. Review and manually edit the output file if needed
2. For automation → hand the plan to your project's test-generation tooling
```

---

## Error Handling

| Condition | Action |
|---|---|
| No file path provided | Ask via AskUserQuestion |
| PDF cannot be read | Display error and stop |
| requirements.md not found | Display error and stop |
| pbi-test-doc-generator Agent fails | Forward the error as-is |
| pbi-test-doc-writer Agent fails | Forward the error as-is |

---

## Notes

1. **Output directory**: `{qa_out_dir}/` is relative to the current working directory. Run `mkdir -p` via `Bash` before launching the writer agent.
2. **PDF reading**: Use Claude's `Read` tool directly — do not use Python or shell commands.
3. **Codebase audit**: `pbi-test-doc-generator` runs Glob/Grep relative to the current working directory.
4. **Output format**: This is a human-readable table for QA reviewers — not a machine-readable automation format; use `/scenario-test --format=importer` or your project's generator for that.
