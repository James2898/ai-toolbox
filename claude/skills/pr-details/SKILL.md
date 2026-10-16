---
name: pr-details
description: Generates a PR title and body with a reviewer test checklist from git diff, task file, and commit history
allowed-tools:
  - Bash
  - Read
  - Glob
  - AskUserQuestion
user-invocable: true
---

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

Read `$ARGUMENTS`. If a base branch was supplied (e.g. `/pr-details develop`), use it. Otherwise default to `main`. Store as `{base}`.

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

If `{task_id}` is not null, attempt to read `tasks/{task_id}.md` using the `Read` tool.

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

### 4f. Screenshots

Static placeholder section — always include:

```
## Screenshots

_Attach screenshots or Vercel preview link here._
```

---

## STEP 5: Output to terminal

Print the complete PR title and body using this exact wrapper format so the user can copy it cleanly:

```
=== PR TITLE ===
<title here>

=== PR BODY (copy below) ===
<full markdown body here>
```

---

## STEP 6: Offer to create the PR via gh

Use `AskUserQuestion`:

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
