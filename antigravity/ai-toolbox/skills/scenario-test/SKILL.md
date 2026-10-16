---
name: scenario-test
description: "Write end-to-end user-journey test scenarios for a user story or feature — persona, preconditions and data, numbered steps (where / action / expected), alternate entry points, error recovery, interruption (close a drawer mid-edit, reopen, refresh), concurrency, and cleanup — each linked to the matrix case ids it covers. Writes {qa_out_dir}/<slug>/scenario-test.md; with --format=importer also emits importer-ready JSON blocks (title, page_path, login_info, preconditions, expected, cleanup) so scenarios go straight to the team sheet and the Playwright runner. Use whenever the user asks for E2E scenarios, user journeys, \"walk through this as a user\", acceptance test scripts, manual test steps, or Playwright-ready test cases from a story."
---

> **Running in Antigravity**: this skill is generated from the Claude Code source.
> - `ask_question` is Antigravity's interactive question tool (Claude Code: AskUserQuestion).
> - `ARGS` means whatever the user typed after `/<this-skill>`, or the request that triggered it.

# Scenario Tests

Journeys, not conditions. The matrix says *which* combinations matter; a scenario says *how a person reaches and observes* them, screen by screen. Output: `{qa_out_dir}/<slug>/scenario-test.md`.

## Project settings

This skill reads the project profile (see the toolbox README): `AI_TOOLBOX_PROFILE`, else `<project root>/.ai-toolbox/profile.yml`. Placeholders used below:

| Placeholder | Profile key | Without a profile |
|---|---|---|
| `{qa_out_dir}` | `docs.qa_out_dir` | `.qa/` (keep it gitignored) |
| `{pbi_dir}` | `docs.pbi_dir` | `pbi-docs/` |
| `{qa_import}` | `qa_import.importer` | none |

## Inputs

`ARGS`: a user story ("As a global admin I want…"), a feature description, a PBI id (`{pbi_dir}/<id>*.md`), a PR number, or a slug whose folder already has a plan/matrix. Flags: `--format=md|importer` (default `md`; `importer` adds the JSON blocks), `--personas=<a,b>`, `--out=<dir>`, `--max=<n>` scenarios (default 12).

## Step 1 — Personas and entry points

- Personas are **roles plus permission flags** ("global admin with `canManageApplications`", "member without the mapping menu"), never named people. Logins are placeholders.
- Entry points: the nav item, a deep link/URL, a cross-link from another screen (help text, breadcrumb, related list), a redirect after an action. Each distinct entry point that changes what the user sees is its own scenario or variant.

## Step 2 — Choose the journeys

Cover, in this order, until `--max`:
1. **Main path per acceptance criterion** — the shortest route to observing the AC.
2. **Alternate entry points** for the same outcome (nav vs deep link vs cross-link).
3. **Error recovery** — a validation error, the fix, the successful retry; a server error and what the user sees.
4. **Interruption** — close a drawer/modal mid-edit and reopen (stale data has leaked this way before), navigate away and back, browser refresh: what persists, what resets.
5. **Concurrency** — a second tab or a second user changes the same record; what the first one sees after the next action (only when the data is shared).
6. **Responsive / mode switches** — when the view has media queries or a platform mode (mobile vs desktop).

## Step 3 — Write each scenario

```markdown
### SC-001 — <journey title>
- **Persona:** <role + flags>   **Entry:** <nav / URL / cross-link>
- **Preconditions:** <state in words>; data: <TM-xxx blocks from test-data.sql, or UI setup steps>
- **Covers:** TM-001, TM-004 · AC-2

| Step | Where | Action | Expected |
|---|---|---|---|
| 1 | `/<route>` | click "<label>" | drawer "<title>" opens, fields empty |
| 2 | drawer | type "<value>" in <field>, submit | toast "<message key or text>", row appears at top |
| … | | | |

- **Post-condition check:** <API/DB observation — SELECT or endpoint, or "visual only">
- **Cleanup:** <delete the created row via UI / test-data cleanup block>
```

Rules for steps: one action per row; "Expected" is observable (text, element state, URL, toast, network status) and names the thing to look at; keep a scenario to ≤ 12 steps — split longer journeys at the natural checkpoint. Use the real route paths and labels from the code (route definitions, translation yml) so the steps are executable, and mark anything you could not confirm `(unverified)`.

## Step 4 — Importer format (`--format=importer`)

After each scenario, add a Markdown-with-JSON block, a common import format for test-case tools (your team's importer, if any: `{qa_import}`):

```json
{
  "title": "TC-001: <journey title>",
  "page_path": "/<route>",
  "login_info": { "email": "<persona-email>", "password": "<from secret store>" },
  "preconditions": ["<precondition 1>", "data: TM-001 block"],
  "expected": ["step 1: <expected>", "step 2: <expected>"],
  "cleanup": "<cleanup text>"
}
```

`login_info` stays a placeholder in the document; the importer's sheet is where real test accounts are entered. The E2E path (`{module}/{feature}/{yyyymmdd_name}`) is chosen at import time, not here.

## Step 5 — Write and report

File header:

```markdown
# Scenario Tests — <feature>
- **Source:** <story / PBI / PR>   **Date:** <YYYY-MM-DD>   **Scenarios:** <n>
- **Personas:** <list>   **Data:** `test-data.sql` blocks referenced per scenario

## Coverage
| Scenario | Covers (TM / AC) | Persona | Steps |
|---|---|---|---|
```

Report: path, scenario count by kind (main / alternate / error / interruption / concurrency), matrix cases not covered by any scenario, and the next step (your team's importer, `{qa_import}`, when the importer format was produced).

## Notes

- A scenario that cannot name its route or label is not executable yet — grep for them before writing.
- Toast messages and labels: cite the translation key when the text is translated, so the scenario survives copy changes.
- Pair with `/regression-test` for sibling screens; scenarios here are for the feature itself.
