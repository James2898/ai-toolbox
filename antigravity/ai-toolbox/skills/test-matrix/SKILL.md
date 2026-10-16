---
name: test-matrix
description: "Build a condition-matrix of test cases plus an impact analysis for a feature change. Identifies the factors that change behaviour (role, state, input class, flag, boundary), gets the factor set approved, expands it into numbered cases (full combination when small, pairwise + boundaries + every AC's happy path when large), derives expected results from acceptance criteria and code, and maps which modules, endpoints, screens and sibling surfaces the factors touch. Writes {qa_out_dir}/<slug>/test-matrix.md; feeds /test-data and /export-csv. Use whenever the user asks for a test matrix, condition table, combinations, \"what cases do we need\", decision table, boundary cases, or impact analysis of a feature."
---

> **Running in Antigravity**: this skill is generated from the Claude Code source.
> - `ask_question` is Antigravity's interactive question tool (Claude Code: AskUserQuestion).
> - `ARGS` means whatever the user typed after `/<this-skill>`, or the request that triggered it.

# Test Matrix

Turn a feature into a **condition matrix**: the factors that change behaviour, their value classes, and the cases that cover their combinations — plus an **impact analysis** of where those factors live in the code.

Second step of the QA chain: `/test-plan → /test-matrix (this) → /test-data → /export-csv`. Reads `{qa_out_dir}/<slug>/test-plan.md` when it exists; works standalone otherwise. Output: `{qa_out_dir}/<slug>/test-matrix.md`.

## Project settings

This skill reads the project profile (see the toolbox README): `AI_TOOLBOX_PROFILE`, else `<project root>/.ai-toolbox/profile.yml`. Placeholders used below:

| Placeholder | Profile key | Without a profile |
|---|---|---|
| `{qa_out_dir}` | `docs.qa_out_dir` | `.qa/` (keep it gitignored) |
| `{pbi_dir}` | `docs.pbi_dir` | `pbi-docs/` |
| `{handler_layer}` | `api.handler_layer` | find the backend route handlers |
| `{ddl_paths}` | `database.ddl_paths` | search for migrations or `schema.sql` |

## Inputs

`ARGS`: a feature description, PBI id (`{pbi_dir}/<id>*.md`), PR number/URL, a path to a spec or an existing `test-plan.md`, or a slug (`{qa_out_dir}/<slug>/`). Flags: `--out=<dir>`, `--max-cases=<n>` (default 60). Nothing provided → ask.

## Step 0 — Check for decisions newer than the source

A PBI hardcopy or spec is a snapshot. Designs move after it is saved, and a matrix built on the snapshot tests the wrong product. A typical case: the hardcopy says a checkbox is ticked by default, while an open PR has already reversed it.

Before choosing factors:
1. Note the source's date (the hardcopy's **Saved** line, or the spec's last commit: `git --no-pager log -1 --format=%cs -- <path>`).
2. Find work that may have overruled it: `GH_PAGER=cat gh pr list --state all --search "<PBI id or feature keyword>" --json number,title,state,headRefName,updatedAt`, plus any PR the source itself links to.
3. For each PR newer than the source, read its body and any `requirements.md` / `design.md` it adds (`gh api repos/<owner>/<repo>/contents/<path>?ref=<head>`), looking for changed defaults, renamed labels, settled open items and dropped scope.
4. Record the result at the top of the matrix under **Decision sources**, one row per source with its date and what it changed. Expectations that come from a later decision get `(PR <n>)` in their Source cell; the rest keep their AC or scenario id.
5. When wording is in flux (labels, checkbox polarity), phrase factors by **behaviour or API parameter** (e.g. `include_overridden=false/true`) and map the UI wording in a note, so the cases survive the next rename.

If nothing newer exists, write "Decision sources: <source> only (checked <date>)". The check is part of the deliverable, not an extra.

## Step 1 — Identify factors (then get them approved)

A factor is anything that changes the outcome: persona/permission, entity state, input class, flag/setting, time window, data volume, platform mode. For each factor list its **value classes** — equivalence classes plus the boundaries between them (empty / one / many; min / max / max+1; past / today / future; null / set).

Find them in three places and cite each source:
1. Acceptance criteria and spec text ("if the rule is deleted, skip it" → factor *rule state*: active / deleted).
2. Code: frontend validation and enums (type definitions, constant lists, form validation rules), backend request validation and error codes (`{handler_layer}`), permission gates (role checks, feature flags, navigation guards).
3. Data: nullable columns and enums in the schema (`{ddl_paths}`) — but a nullable column is not a reachable state; include a null value only when code can produce it.

Show the factor table and ask with `ask_question` before expanding: the factor set determines the whole matrix, and one wrong factor multiplies into dozens of wrong cases. Options: approve / edit (user lists changes) / abort.

## Step 2 — Expand into cases

- **Full combination** when factors × values ≤ `--max-cases`.
- Otherwise **pairwise** over all factors, then add: every boundary value at least once, one happy-path case per acceptance criterion, and every explicitly risky pair the plan or the user named.
- List **impossible combinations** separately with the reason (e.g. "deleted rule cannot be *selected*: the picker filters deleted rows at `useRuleOptions.ts:42`").
- IDs are `TM-001…` and never renumbered once the file exists; new cases append.
- Priority: P1 = AC happy path or data-loss/permission risk; P2 = boundary and error paths; P3 = cosmetic or redundant pair.

## Step 3 — Expected result per case

Write the observable outcome (what the screen shows, what the API returns, which rows exist). Derive from the AC first; when it comes only from reading code, append `(code-derived)`; when neither settles it, write `?` and add it to Open questions rather than inventing a result.

## Step 4 — Impact analysis

For every factor, grep where it is read or written and list:
- FE: screens, hooks and components that branch on it; shared modules and design-system components (every consumer is a sibling surface).
- BE: handlers → business logic → data access that filter or validate on it; endpoints affected.
- Data: tables/columns, migrations, seed data needed (hand to `/test-data`).
- Sibling surfaces: screens that share a hook/component/usecase with the feature — these go to `/regression-test`.

## Step 5 — Write the file

Create `{qa_out_dir}/<slug>/` if needed. Use exactly this template (column headers matter: `/test-data` and `/export-csv` parse them):

```markdown
# Test Matrix — <title>

- **Source:** <PBI / PR / description>   **Date:** <YYYY-MM-DD>   **Plan:** `test-plan.md` | none
- **Coverage:** full combination | pairwise + boundaries   **Cases:** <n>

## Decision sources
| Source | Date | What it decides or changes |
|---|---|---|

## Factors
| Factor | Values (equivalence classes + boundaries) | Source |
|---|---|---|

## Cases
| ID | <Factor 1> | <Factor 2> | … | Expected | Priority | Source |
|---|---|---|---|---|---|---|
| TM-001 | … | … | … | … | P1 | AC-1 |

## Impossible combinations
| Factors | Why impossible (evidence) |
|---|---|

## Impact analysis
| Factor | FE | BE | Data | Sibling surfaces |
|---|---|---|---|---|

## Open questions
- …
```

## Step 6 — Report

Print: path, the decision sources (and anything later that overruled the original), factor count, case count by priority, impossible combinations, and the next commands:

```
/test-data {qa_out_dir}/<slug>/test-matrix.md
/export-csv {qa_out_dir}/<slug>/test-matrix.md
```

## Notes

- Personas are roles plus permission flags (e.g. "global admin with `canManageApplications`"), never real people.
- More than ~60 cases means the feature should be split into sub-matrices (one file per sub-feature, suffix the slug), not that the table should be trimmed.
- Keep "Expected" factual and short; steps to reach the state belong in `/scenario-test`.
