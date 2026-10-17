---
name: pr-details
description: "Generates a PR title and body from the git diff, task file and commit history: summary (with a before/after diagram when a flow changes), reviewer test checklist, before/after Evidence pulled from diagnose loop files, live-verify reports and test runs, and a Merge danger block (one-way or two-way door, blast radius, rollback)."
---

> **Running in Antigravity**: this skill is generated from the Claude Code source.
> - `ask_question` is Antigravity's interactive question tool (Claude Code: AskUserQuestion).
> - `ARGS` means whatever the user typed after `/<this-skill>`, or the request that triggered it.

# PR Details Generator Skill

This skill reads the current branch's git diff, commits, and task file, then outputs a ready-to-use PR title and body including a structured reviewer test checklist. It optionally creates the PR via `gh pr create`.

## Position in the Workflow

```
/pr-details (this Skill)
    ← runs on current branch
    → outputs PR title + body to terminal
    → optionally: gh pr create --base {base} --title ... --body ...
```

---

## STEP 1: Determine base branch

Read `ARGS`. If a base branch was supplied (e.g. `/pr-details develop`), use it. Otherwise default to `main`. Store as `{base}`.

---

## STEP 2: Collect raw inputs

Run all of the following **in parallel** via Bash:

- `git log {base}..HEAD --oneline` — commit list on this branch
- `git diff {base}...HEAD --stat` — file-level change summary
- `git diff {base}...HEAD | head -400` — truncated full diff (cap at 400 lines)
- `git branch --show-current` — current branch name

From the branch name, extract `TASK-NNN` using the regex `TASK-\d+`. Store as `{task_id}` (or null if not found).

If there are **no commits** on the branch (`git log` returns empty), print an error and stop:
> "No commits found on this branch relative to `{base}`. Nothing to generate."

---

## STEP 3: Load task file

If `{task_id}` is not null, attempt to read `tasks/{task_id}.md` using the `view_file` tool.

Extract from the task file (if found):
- **Feature Summary** — first descriptive paragraph or `## Summary` / `## Overview` section
- **Acceptance Criteria** — all bullet points under `## Acceptance Criteria` or `## AC`
- **Out of Scope** — contents of `## Out of Scope` section (if present)

If the file does not exist or `{task_id}` is null, set `{task_context}` = null and fall back to commits + diff for all content derivation.

---

## STEP 4: Synthesize PR content

Generate each section below in order. All synthesis is done inline — no sub-agent.

### 4a. PR Title

Format: `feat(TASK-NNN): <verb> <object>` — ≤70 characters, imperative mood.

- Derive the verb + object from the highest-impact change in the diff (the feature or fix that best summarises the branch purpose).
- If no `{task_id}`: omit the scope token → `feat: <verb> <object>`.
- Use `fix` instead of `feat` if all commits on the branch are `fix:` commits.

### 4b. Summary

3–5 bullet points of **what** changed.

- Source: `git diff --stat` grouped by directory + commit messages.
- Do not restate the title. Focus on components and behaviors changed.
- **Summary visual** (only when the change alters a flow, a state machine or which layer calls which): add a small before → after diagram under the bullets, as a Mermaid `flowchart` or a two-line ASCII sketch. Skip it for one-file fixes and copy changes; a diagram that restates the bullets is noise.

### 4c. Motivation

1–2 sentences of **why** this change was made.

- Priority order: task file Feature Summary → first commit message body → inferred from diff.
- If sourced from the task file, quote one sentence and attribute it with "Per {task_id}:".

### 4d. Changes (grouped by area)

Scan the changed files from `--stat` and bucket them into:

| Area | Path patterns |
|---|---|
| **Frontend** | components, pages/views, styles |
| **Backend / API** | route handlers, server actions, services, business logic |
| **Data** | migrations, schema, models/ORM, database client and types |
| **Config** | `*.config.*`, `.env*`, `package.json` |

- Map the buckets onto whatever layout this repo actually uses — the categories matter, the exact paths vary by stack.
- Omit empty buckets entirely.
- List each changed file with a one-line note describing what changed.

### 4e. Test Plan

Single unified section covering functional verification **and** pre-merge checks. Use four sub-groups:

**Golden Path** (always present)
- One `[ ]` checkbox per acceptance criterion (if task file exists) or per commit feat (if no task file).
- Phrase each as: user action → expected result.

**Edge Cases & Error States** (always present)
- Derive from: ACs that mention invalid input, redirects, loading states, empty states.
- Also add a case for each `try/catch` block, error display, or guard clause visible in the diff.
- If no edge cases are derivable, add at least one: the behaviour when required data is missing or the network fails.

**Role-Based Access** (omit this sub-group entirely if no role-gating is present in the diff or task file)
- Include if the diff touches: `isMusicDirector`, `music_director` role checks, RLS policies, auth guards.
- One `[ ]` per role mentioned (e.g. `music_director`, viewer/non-director, unauthenticated user).

**Pre-merge** (always present, fixed items)
- [ ] TypeScript passes (`npx tsc --noEmit`)
- [ ] No console errors in browser
- [ ] RLS policies verified (include only if DB / RLS area is non-empty)
- [ ] Mobile viewport tested
- [ ] Dark mode tested
- [ ] Vercel preview link attached

### 4f. Evidence

Show that the change does what the PR says, as before → after pairs a reviewer can re-run. Collect from, in this order:

1. **diagnose loop files** in `{loop_dir}` (profile `docs.loop_dir`, default `.ai-toolbox/loops`) whose cause `file:line` is in this diff: the loop command, its red output before, green after, and the regression test name.
2. **live-verify reports** from this session or named by the user: per case, the toast text, status codes and UI state.
3. **Test runs**: the new or changed tests, and the commands run with their pass counts.

```
## Evidence

| What | Before | After | Re-run with |
|---|---|---|---|
| <behaviour> | <red output / status / screenshot> | <green output / status / screenshot> | `<command>` |
```

When nothing was collected, write `_No evidence collected yet — attach screenshots or test output._` rather than inventing rows. Use ids and statuses only; never personal data from the app or database.

### 4g. Merge danger

One short block so the reviewer knows how careful to be:

```
## Merge danger

- Door: one-way | two-way — <why: a migration, a data rewrite, a public API or event contract, a deleted endpoint = one-way; UI and internal code behind no contract = two-way>
- Blast radius: <screens, endpoints, jobs or other teams that read what changed — from importers of changed files and consumers of changed API shapes>
- Rollback: <revert the PR | revert plus a data fix | needs a forward fix>
```

Derive it from the diff: migrations and schema files, changed request/response shapes, deleted or renamed exports, and shared components or hooks with many importers (`grep -rl` the changed export).

---

## STEP 5: Output to terminal

If the repo has a PR template (`.github/pull_request_template.md` or `.github/PULL_REQUEST_TEMPLATE/`), keep its headings and put these sections inside it; Evidence and Merge danger go under the template's closest heading, or after its last one.

Print the complete PR title and body using this exact wrapper format so the user can copy it cleanly:

```
=== PR TITLE ===
<title here>

=== PR BODY (copy below) ===
<full markdown body here>
```

---

## STEP 6: Offer to create the PR via gh

Use `ask_question`:

> "Create the PR now via `gh pr create`? Target branch: `{base}`. (yes / no)"

- If **yes**: run `gh pr create --base {base} --title "<title>" --body "<body>" --assignee @me` via Bash. Print the returned PR URL.
- If **no**: print "Done — body is ready to copy above."
- If `gh` is not installed (command not found): skip this step and instead print the manual command:
  ```
  gh pr create --base {base} --title "<title>" --body "$(cat <<'EOF'
  <body>
  EOF
  )" --assignee @me
  ```

---

## Fallback Table

| Condition | Fallback |
|---|---|
| No TASK-NNN in branch name | Skip task file; derive all content from commits + diff |
| Task file not found | Skip AC-based test plan; derive from diff and commits |
| No commits on branch | Warn user and stop |
| `gh` not installed | Skip STEP 6; print manual `gh pr create` command |
| Diff > 400 lines | Use `--stat` only for Changes section; note truncation in output |
| No role-gating found | Omit Role-Based Access sub-group from Test Plan |
| No loop file, live-verify report or test run | Evidence section states that none was collected |
