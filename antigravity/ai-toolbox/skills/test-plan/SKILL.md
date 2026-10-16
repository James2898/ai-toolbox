---
name: test-plan
description: "Build a test plan for a change and decide which test types it needs — unit, API contract, condition matrix, end-to-end scenario, regression, data/migration, manual visual, permission/persona — each with the reason the change triggers it. Takes a PBI id (reads the PBI folder), a spec file, a PR number/URL, or a plain feature description, and writes {qa_out_dir}/<slug>/test-plan.md plus the exact follow-up commands (/test-matrix, /test-data, /export-csv, /api-test, /scenario-test, /regression-test). Head of the QA document chain. Use whenever the user asks \"how should we test this\", \"what tests does this PR need\", \"make a test plan\", \"QA plan for PBI-…\", or wants to decide test scope before writing cases."
---

> **Running in Antigravity**: this skill is generated from the Claude Code source.
> - `ask_question` is Antigravity's interactive question tool (Claude Code: AskUserQuestion).
> - `ARGS` means whatever the user typed after `/<this-skill>`, or the request that triggered it.

# Test Plan

Decide **what kinds of testing a change needs and why**, before anyone writes cases. The plan is short; the cases live in the sibling documents it points to.

## Position in the QA document chain

```
/test-plan (this)  →  /test-matrix  →  /test-data  →  /export-csv
        └→ /api-test · /scenario-test · /regression-test · /demo-guide   (as the plan selects)
/pbi-gen-test-doc  = the fuller PBI-driven test document (scenario approval gate + QA table); use it when a PBI needs the full document rather than a plan
```

All documents of one change share one folder: `{qa_out_dir}/<slug>/` (`--out=<dir>` overrides).

## Project settings

This skill reads the project profile (see the toolbox README): `AI_TOOLBOX_PROFILE`, else `<project root>/.ai-toolbox/profile.yml`. Placeholders used below:

| Placeholder | Profile key | Without a profile |
|---|---|---|
| `{qa_out_dir}` | `docs.qa_out_dir` | `.qa/` (keep it gitignored) |
| `{pbi_dir}` | `docs.pbi_dir` | `pbi-docs/` |
| `{topic_bases}` | `git.topic_bases` | none: use the PR's own base |
| `{ddl_paths}` | `database.ddl_paths` | search for migrations or `schema.sql` |
| `{client_layer}` | `api.client_layer` | find where the frontend calls the API |
| `{handler_layer}` | `api.handler_layer` | find the backend route handlers |
| `{backend_test}` | `commands.backend_test` | from the build files (`go.mod`, `pom.xml`, `pyproject.toml`, …) |
| `{frontend_check}` | `commands.frontend_check` | from `package.json` scripts |
| `{build_logs}` | `commands.build_logs` | skip |
| `{local_url}` | `environments.local_url` | ask |
| `{baseline_url}` | `environments.baseline_url` | skip baseline evidence |
| `{qa_import}` | `qa_import.importer` | none |

## Inputs

`ARGS` is one of:

| Form | How it is read |
|---|---|
| PBI or ticket id (`PBI-042`, `JIRA-123`) | `Glob {pbi_dir}/<id>*.md`; if absent, ask for the PBI text or path |
| File or directory path | `requirements.md` / `design.md` / `tasks.md` when it is a spec folder; otherwise the file itself |
| PR number or URL | `gh pr view <n> --json title,body,baseRefName,headRefName,files` — derive the base from the PR, never assume the default branch: work on a long-lived train (`{topic_bases}`) targets that train, and diffing against the default would sweep in other people's commits |
| Free text | Treat as the feature description; ask one clarifying question only if the scope is unreadable |

Nothing provided → ask with `ask_question`.

**Slug:** PBI id lower-cased (`pbi-042`), else the PR head branch's last segment, else kebab-case of the title (≤ 6 words). If `{qa_out_dir}/<slug>/test-plan.md` exists, ask: overwrite, version (`test-plan-v2.md`), or abort.

## Step 1 — Understand the change

Build a one-screen picture before choosing test types:

- **Acceptance criteria / expected behaviours** — from the PBI, spec, or PR body. Number them `AC-1…` if the source doesn't.
- **Layers touched** — for a PR: `git fetch origin <base>` then `git diff --name-status origin/<base>...origin/<head>` (or the local branch). Bucket files: FE view / FE shared module / FE translations / BE handler / BE business logic / BE data access / schema (`{ddl_paths}`) / config / tests. For a PBI without code yet, infer the layers from the design or from where similar features live.
- **Interfaces crossed** — new or changed endpoints (`{client_layer}` on the frontend, `{handler_layer}` on the backend), new query params, new DB columns, new permissions or persona gates, new translation keys.
- **What must not change** — sibling screens and shared hooks/components the change touches (grep the imports of changed files). This feeds the regression decision.

## Step 2 — Pick the test types

Evaluate every row. **Start each row at skip** and move it to include only when the change contains its trigger. Record the trigger in the plan — a reviewer should be able to disagree with a specific line, not with a feeling.

Three decisions exist, and each needs its line:
- **include** — the trigger is present, and no other included type would catch the same failure.
- **skip** — no trigger, or another included type already catches the failure (name it: "covered by the API contract rows").
- **note only** — worth one sentence of risk (e.g. performance at an unmeasured scale) but no cases now; say what would turn it into include.

A plan where every row reads "include" usually means the triggers were not tested. Before writing, re-read each included row and ask: if this type were dropped, which concrete failure would go unnoticed? If you cannot name one, it is a skip or a note. Typical honest skips: E2E when no journey spans more than one screen or the area has no scenario harness; API contract when no endpoint, field or error key changes; manual visual when no FE file changes; performance when the change adds no query and no loop over unbounded data.

| Type | Include when the change has… | Produces / runs |
|---|---|---|
| Unit | new or changed logic in hooks, services, usecases, converters | frontend unit tests beside the logic they cover; backend tests via `{backend_test}` |
| API contract | new/changed endpoint, request field, response field, status/error key | `/api-test <endpoint>` |
| Condition matrix | ≥ 3 interacting conditions (role × state × input), boundaries, enums | `/test-matrix <feature>` |
| Data / migration | new table/column, backfill, data that must pre-exist for cases | `/test-data <matrix>` |
| Scenario (E2E) | a user journey spanning > 1 screen, redirects, drawers/modals, persistence | `/scenario-test <story>` (`--format=importer` when the team imports cases: `{qa_import}`) |
| Regression | shared hook/component/usecase touched, schema changed, translation keys renamed | `/regression-test <PR>` |
| Permission / persona | a gate, nav item, admin-only control, company-scoped data | matrix or scenario rows per persona (name personas by role and permission flag, never by a real person) |
| Manual visual / a11y | layout, responsive, styling, tooltips, empty states | checklist rows in the plan; live check on `{local_url}` |
| Performance | lists without pagination, N+1 risk in DAO, big exports | note the query count at the DAO and the dataset size to try |

Excluded types get one line each saying why ("no endpoint change → no API contract").

## Step 3 — Rank the risk areas

List 3–7 areas most likely to break, each with the evidence (`file:line`, AC number, or past bug) and the test type that covers it. Mark evidence-free entries as 推測.

## Step 4 — Write the plan

Write `{qa_out_dir}/<slug>/test-plan.md` (create the folder with `mkdir -p`) using exactly this template:

```markdown
# Test Plan — <title>

- **Source:** <PBI id / PR #n (base: <base>) / description>
- **Date:** <YYYY-MM-DD>
- **Slug / folder:** `{qa_out_dir}/<slug>/`
- **Environments:** local `{local_url}` (the branch under test) · baseline `{baseline_url}` ("before" evidence only — a deployed environment never contains unpushed work)

## Change summary
<3–6 lines: what changes, for whom, which layers>

## Acceptance criteria
| AC | Statement | Source |
|---|---|---|

## Test types
| Type | Decision | Trigger in this change (or why skipped / note only) | Document / command |
|---|---|---|---|
| Unit | include / skip / note only | … | … |
| API contract | … | … | `/api-test …` |
| Condition matrix | … | … | `/test-matrix …` |
| Data / migration | … | … | `/test-data …` |
| Scenario | … | … | `/scenario-test …` |
| Regression | … | … | `/regression-test …` |
| Permission / persona | … | … | … |
| Manual visual / a11y | … | … | … |
| Performance | … | … | … |

## Risk areas (ranked)
| # | Area | Why (evidence) | Covered by |
|---|---|---|---|

## Personas
| Persona | Role / permission flags | Used for |
|---|---|---|

## Entry / exit criteria
- Entry: <branch pushed, local env up, seed data present, …>
- Exit: <all P1 cases pass, no open blocker, regression surfaces unchanged, …>

## Next commands
```
/test-matrix <slug>
/test-data {qa_out_dir}/<slug>/test-matrix.md
…
```
```

## Step 5 — Report

Print the path, the included types (one line each with trigger), the skipped and note-only types (one line each with reason), and the next commands. Do not generate the cases here; the chain does that.

## Notes

- Verification commands come from the profile: `{frontend_check}`, `{backend_test}`, and `{build_logs}` for build errors.
- The plan is a decision record. Keep it under ~120 lines; depth belongs in the sibling documents.
