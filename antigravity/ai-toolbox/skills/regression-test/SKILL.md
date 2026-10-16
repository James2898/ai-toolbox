---
name: regression-test
description: "Produce a regression plan that proves existing behaviour is unchanged after a change. Derives the blast radius from the real diff (base taken from the PR, never assumed): importers of changed hooks, components and services, sibling screens sharing them, renamed translation keys, changed schema readers, endpoint consumers, newly reachable branches behind changed guards — then separates \"changed on purpose\" from \"must stay the same\", lists the automated suites to run including dependent packages, and writes manual checks with baseline-vs-after evidence columns. Writes {qa_out_dir}/<slug>/regression-test.md. Use whenever the user asks \"what could this break\", \"regression checks for this PR\", \"which other screens are affected\", \"did we touch anything shared\", or needs a regression plan before merge or release."
---

> **Running in Antigravity**: this skill is generated from the Claude Code source.
> - `ask_question` is Antigravity's interactive question tool (Claude Code: AskUserQuestion).
> - `ARGS` means whatever the user typed after `/<this-skill>`, or the request that triggered it.

# Regression Plan

A regression plan answers one question: **what else uses what this change touched, and how do we show it still behaves the same?** Output: `{qa_out_dir}/<slug>/regression-test.md`.

## Project settings

This skill reads the project profile (see the toolbox README): `AI_TOOLBOX_PROFILE`, else `<project root>/.ai-toolbox/profile.yml`. Placeholders used below:

| Placeholder | Profile key | Without a profile |
|---|---|---|
| `{qa_out_dir}` | `docs.qa_out_dir` | `.qa/` (keep it gitignored) |
| `{topic_bases}` | `git.topic_bases` | none: use the PR's own base |
| `{client_layer}` | `api.client_layer` | find where the frontend calls the API |
| `{handler_layer}` | `api.handler_layer` | find the backend route handlers |
| `{ddl_paths}` | `database.ddl_paths` | search for migrations or `schema.sql` |
| `{frontend_check}` | `commands.frontend_check` | from `package.json` scripts |
| `{backend_test}` | `commands.backend_test` | from the build files (`go.mod`, `pom.xml`, `pyproject.toml`, …) |
| `{build_logs}` | `commands.build_logs` | skip |
| `{baseline_url}` | `environments.baseline_url` | skip baseline evidence |
| `{local_url}` | `environments.local_url` | ask |

## Inputs

`ARGS`: a PR number/URL, a branch name, `--base=<branch>` with a head, a diff file, or a description plus a slug. Flags: `--out=<dir>`, `--run` (execute the automated suites and fill results). Nothing provided → ask.

## Step 1 — Get the diff against the right base

```bash
gh pr view <n> --json baseRefName,headRefName,files,title,url
git fetch origin <base> <head>
git diff --name-status origin/<base>...origin/<head>
```

Derive the base from the PR. Work on a long-lived train (`{topic_bases}`) targets that train; diffing it against the default branch sweeps in other people's commits and produces a plan full of surfaces this PR never touched. For a local branch without a PR, ask which base it stacks on. When attribution of a file is in doubt, compare blob ids: `git rev-parse origin/<base>:<path>` vs `origin/<head>:<path>` — identical means not changed here.

## Step 2 — Blast radius per changed file

| Changed thing | Find its dependants | Surface at risk |
|---|---|---|
| FE shared hook or utility | `grep -rn "<import path of the file>"` across the frontend source | every importer's screen |
| FE shared or design-system component | same grep | every consumer; style changes propagate silently |
| FE view-local file (`views/<View>/…`) | importers inside that view | that view only (still list its tabs/drawers) |
| Translation files | grep each changed or renamed key where translations are looked up | every screen rendering the key; keys missing in one language |
| BE business logic | the handlers that call it | each endpoint → its frontend request consumers (`{client_layer}`) |
| BE data access / converter | every service using it | all of those endpoints |
| BE handler / route / request validation (`{handler_layer}`) | the frontend request that calls it | screens using that request |
| Error code or message | frontend error mapping, toasts | error display paths |
| Schema (`{ddl_paths}`) | grep the table name in data-access code, SQL files, seed scripts | every reader and writer; local seed data |
| Guard / gate / default value | the branch that was previously unreachable | **newly reachable code** counts as changed behaviour even if its lines are untouched |
| Config / env / build | everything | smoke test |

Record the grep you ran next to each surface, so the next reviewer can rerun it.

## Step 3 — Split "changed on purpose" from "must stay the same"

- **Changed on purpose**: surfaces whose new behaviour is the feature. List them once with the AC they implement; they are covered by `/test-matrix` and `/scenario-test`, not here.
- **Must stay the same**: every other surface from Step 2. Each gets a row in the plan with the shared artefact that puts it at risk (`file:line`).

## Step 4 — Decide the checks

**Automated** — run the suites of the changed packages **and of every dependant found in Step 2**; a passing suite in the changed package says nothing about its callers.

| Layer | Command |
|---|---|
| FE targeted | the frontend test runner on the spec files of the changed files and their importers |
| FE full | `{frontend_check}` |
| BE changed + dependants | `{backend_test}`, scoped to each changed and dependent package |
| Build | `{build_logs}` for compile errors |

**Manual** — per must-stay-the-same surface: the steps to exercise it, the **baseline** (`{baseline_url}`, or the base branch run locally — a deployed environment never contains unpushed work), the **after** (`{local_url}` on the head branch, dev server restarted so the bundle is fresh), the evidence to capture (screenshot, DOM text, network status), and the expected verdict "identical".

## Step 5 — Write the plan

```markdown
# Regression Plan — <PR title>
- **PR:** #<n> <url>   **Base:** `<base>`   **Head:** `<head>`   **Date:** <YYYY-MM-DD>
- **Changed files:** <n> (FE <a> / BE <b> / translations <c> / schema <d> / other <e>)

## Changed on purpose (not regression scope)
| Surface | AC | Covered by |
|---|---|---|

## Must stay the same
| ID | Surface | At risk because (file:line / grep) | Check | Baseline | After | Result |
|---|---|---|---|---|---|---|
| RT-001 | <screen / endpoint> | shares `useX` (`domain/…/useX.ts:12`) | manual: <steps> | | | |
| RT-002 | <package> | calls changed business logic | auto: `{backend_test}` (that package) | | | |

## Automated suites to run
| Suite | Command | Why (dependant of) | Result |
|---|---|---|---|

## Not covered
- <surfaces you could not reach, with why>
```

## Step 6 — Report (and `--run`)

Print the path, counts (surfaces at risk, automated suites, manual checks), and the top three risks. With `--run`, execute the automated suites, paste pass/fail into the Result column, and never mark anything PASS that did not actually run and pass here.

## Notes

- Translation keys: a renamed key is a regression in every language nobody checked.
- A clean rebase can still hide a semantic break — re-run the dependants after any base change.
- Keep the plan honest about what was not checked; an empty "Not covered" section is a smell.
