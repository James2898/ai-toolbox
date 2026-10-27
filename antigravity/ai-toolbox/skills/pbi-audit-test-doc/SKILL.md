---
name: pbi-audit-test-doc
description: "Compares a PBI document against an existing test case document and produces a gap analysis report — missing coverage, weak assertions, and redundant cases. Accepts PDF, Markdown, or directory for either input; automatically detects which file is the PBI and which is the test document."
---

> **Running in Antigravity**: this skill is generated from the Claude Code source.
> - `ask_question` is Antigravity's interactive question tool (Claude Code: AskUserQuestion).
> - `ARGS` means whatever the user typed after `/<this-skill>`, or the request that triggered it.
> - Where this says `Agent(subagent_type: "x")`, delegate via `invoke_subagent` to the subagent `x` with the same prompt.

# PBI Test Review Skill

This Skill cross-references a PBI document (acceptance criteria source) against an existing test case document, then produces a structured gap analysis report.

It answers three questions:
1. Which acceptance criteria have **no** test coverage?
2. Which test cases have **weak assertions** (vague expected values, no concrete numbers)?
3. Which test cases are **redundant** (duplicate conditions already covered by another case)?

## Position in the Pipeline

```
/pbi-audit-test-doc <path_a> <path_b>     ← this Skill (order does not matter)
    → {qa_out_dir}/{pbi_id}_review.md

/pbi-gen-test-doc                         ← generates test plans from scratch
(your project's QA tooling)               ← e.g. converts cases into an automation format

> **Output folder.** `{qa_out_dir}` is `docs.qa_out_dir` from the project profile (see the toolbox README), or `.qa/` when there is no profile. Keep it gitignored.
```

---

## STEP 1: Input

Read paths from `ARGS`. The user may pass one or two paths in any order.

**Supported formats for each path**:
- PDF file (e.g. `~/Downloads/PBI-3623.pdf`)
- Markdown file (e.g. `{qa_out_dir}/PBI-042_test_plan.md`)
- Directory (e.g. `docs/backlog/archives/PBI-3623-work-budget/`) — read `requirements.md` inside it

If no paths are provided, use `ask_question`:
> "Please provide the PBI document path and the test case document path (PDF, Markdown, or directory — order does not matter)."

If only one path is provided, use `ask_question` to ask for the second:
> "Got one document. Please provide the second document path."

---

## STEP 2: Read Both Documents

Read each file using the `read_file` tool (Claude's native PDF reading — no Python or shell).

**For directories**: use `Glob` to find `{dir}/requirements.md` (required). Also read `{dir}/design.md` if present.

If either file cannot be read, display an error message and stop.

---

## STEP 3: Identify Which Document Is Which

Do NOT rely on argument order or filename. After reading both documents, examine their content:

**PBI document signals** (any one is sufficient):
- Contains acceptance criteria sections (`AC-XXX`, "Acceptance Criteria", "受け入れ条件", or numbered requirement bullets)
- Contains user story sections (`US-XXX`, "User Stories", "ユーザーストーリー")
- Contains scope / out-of-scope sections
- Describes *what* should be built (requirements language)

**Test case document signals** (any one is sufficient):
- Contains a table with columns resembling: No / Test Scenario / Test Detail / Actions / Expected / Date / Result
- Contains numbered test scenarios grouped by category (Happy Path, Edge Cases, Regression, etc.)
- Describes *how* to verify behavior (test steps and expected results)

If both documents match PBI signals or both match test case signals, use `ask_question`:
> "I could not automatically determine which document is the PBI and which is the test case. Please clarify: which file is the PBI? [list both filenames]"

Otherwise proceed with the detected roles.

---

## STEP 4: Launch pbi-test-doc-auditor

Pass both document paths and their detected roles to the `pbi-test-doc-auditor`:

```
Agent(
  subagent_type: "pbi-test-doc-auditor",
  prompt: "
    Review the following documents:
    - PBI path: {pbi_path}  (role: PBI / acceptance criteria source)
    - Test case path: {testcase_path}  (role: test case document)

    Phase 1: Extract acceptance criteria from the PBI
    Phase 2: Extract test cases from the test document
    Phase 3: Cross-reference — identify gaps, weak assertions, and redundancies

    Return results as JSON.
  "
)
```

---

## STEP 5: Display Review Results

Format the JSON returned by the agent into four sections:

### Section 1: Coverage Summary
```
## Coverage Summary

PBI: {pbi_id} — {title}
Acceptance Criteria: {total_ac}
Test Cases reviewed: {total_tc}

Coverage:
  ✅ Fully covered ACs : {n}
  ⚠️  Partially covered : {n}
  ❌ Not covered       : {n}

Issues found:
  🔴 Missing coverage  : {n}
  🟡 Weak assertions   : {n}
  🔵 Redundant cases   : {n}
```

### Section 2: Missing Coverage
```
## Missing Coverage

| AC | Description | Gap |
|---|---|---|
| AC-002 | ... | No test case targets this criterion |
| AC-004 | ... | Only happy path covered; edge case missing |
```

### Section 3: Weak Assertions
```
## Weak Assertions

| TC | Scenario | Issue | Suggestion |
|---|---|---|---|
| 1-3 | ... | Expected says "value is correct" — no concrete number | Specify: task_work_budget_min=4800 |
```

### Section 4: Redundant Cases
```
## Redundant Cases

| TC | Scenario | Duplicates | Recommendation |
|---|---|---|---|
| 2-1 | ... | Same condition as 1-2 | Merge or differentiate by adding a second assignee |
```

---

## STEP 6: Ask for Report Output

```
ask_question(
  question: "Review complete. Type 'save' to write the report to {qa_out_dir}/{pbi_id}_review.md, or 'skip' to discard.",
  header: "ReviewOutput"
)
```

If "save" → proceed to STEP 7.
If "skip" → display "Report discarded." and stop.

---

## STEP 7: Write Report

Run `mkdir -p {qa_out_dir}/` via `Bash`, then write the report to `{qa_out_dir}/{pbi_id}_review.md`.

Report format:

```markdown
# {PBI Title} — Test Review

## Coverage Summary

| Item | Value |
|---|---|
| PBI | {pbi_id} |
| Reviewed | {YYYY-MM-DD} |
| Acceptance Criteria | {N} |
| Test Cases | {N} |
| Fully Covered ACs | {N} |
| Partially Covered ACs | {N} |
| Uncovered ACs | {N} |

---

## Missing Coverage

| AC | Description | Gap |
|---|---|---|
...

---

## Weak Assertions

| TC | Scenario | Issue | Suggestion |
|---|---|---|---|
...

---

## Redundant Cases

| TC | Scenario | Duplicates | Recommendation |
|---|---|---|---|
...

---

## Recommended Actions

1. {highest-priority gap}
2. {weak assertion fix}
3. ...
```

---

## STEP 8: Completion Report

```
## Review Report Written

- PBI: {pbi_id} — {title}
- Output: {qa_out_dir}/{pbi_id}_review.md

Summary:
  - Missing coverage : {n} ACs
  - Weak assertions  : {n} test cases
  - Redundant cases  : {n} test cases
```

---

## Error Handling

| Condition | Action |
|---|---|
| No paths provided | Ask via ask_question |
| Only one path provided | Ask for the second via ask_question |
| Cannot determine which is PBI vs test | Ask via ask_question |
| File cannot be read | Display error and stop |
| pbi-test-doc-auditor fails | Forward the error as-is |
