---
name: gh-pr-merge
description: Merge a pull request on GitHub only after the project's merge gate is verified and the user explicitly confirms — the designated final reviewer's latest review is APPROVED and newer than the last base change, reviewDecision APPROVED, mergeStateStatus CLEAN, checks green, threads resolved, not a draft, base branch as expected, the user is the assignee — then merges with the configured merge method, deletes the head branch unless protected, cleans up the local branch and reminds which tracker status to set. Never enables auto-merge, never force-merges. Use whenever the user says "merge this PR", "merge PR 123", "is this ready to merge", "can I merge now", or after the final approval lands.
allowed-tools:
  - Bash
  - AskUserQuestion
user-invocable: true
disable-model-invocation: true
---

# Merge a Pull Request

Merge rule (when `{assignee_merges}` is true): **the assignee merges their own PR, and only after the final reviewer approves.** Merging is outward-facing and irreversible in practice, so this skill checks the gate, shows the evidence, asks once, and merges only on an explicit yes. Approvals can be dismissed under you (a base-branch force-push followed by a base toggle dismisses them with "The base branch was changed."), so the gate is re-read live every time, never remembered.

## Project settings

This skill reads the project profile (see the toolbox README): `AI_TOOLBOX_PROFILE`, else `<project root>/.ai-toolbox/profile.yml`. Placeholders used below:

| Placeholder | Profile key | Without a profile |
|---|---|---|
| `{final_reviewer}` | `review.final_reviewer` | ask before evaluating the gate |
| `{assignee_merges}` | `review.assignee_merges` | true |
| `{merge_method}` | `git.merge_method` | the repo's allowed method; if several are allowed, ask |
| `{protected}` | `git.protected` | `main`, `master`, `develop`, `release/*` (never deleted) |
| `{topic_bases}` | `git.topic_bases` | none |
| `{default_base}` | `git.default_base` | the remote default branch |
| `{post_merge_command}` | `git.post_merge_command` | none |
| `{status_after_merge}` | `bug_tracker.status_after_merge` | skip the reminder |
| `{deploy}` | `deploy` | skip the reminder |

If `{final_reviewer}` is empty, ask for it before evaluating the gate and suggest adding it to the profile.

When the PR's **author is** the final reviewer, that row cannot be satisfied by them; the gate is then `reviewDecision` = `APPROVED` from the other reviewers. Say so in the table instead of failing the row.

## Inputs

`$ARGUMENTS`: PR number or URL (default: the PR of the current branch). Flags: `--keep-branch`, `--squash` / `--rebase` / `--merge` (only if the user asks; the default is `{merge_method}`).

## Step 1 — Account and PR

```bash
gh auth status
gh api user -q .login
gh pr view <n> --json number,title,url,author,assignees,isDraft,baseRefName,headRefName,headRefOid,mergeable,mergeStateStatus,reviewDecision,reviews,statusCheckRollup,commits
gh pr checks <n>
gh api graphql -f query='query($o:String!,$r:String!,$n:Int!){repository(owner:$o,name:$r){pullRequest(number:$n){reviewThreads(first:100){nodes{isResolved}}}}}' -F o=<owner> -F r=<repo> -F n=<n>
```

If you keep several `gh` accounts and switch between them per repository (for example with a shell wrapper), the switch may not have run in a non-interactive shell. If the login is not the account expected for this repository, switch (`gh auth switch`) before reading anything else.

## Step 2 — Evaluate the gate (every row, live)

| Condition | Evidence | Verdict |
|---|---|---|
| Final reviewer's **latest** review is `APPROVED` | `reviews[]` filtered by `{final_reviewer}`, last by `submittedAt` | |
| That approval is newer than the last push and the last base change | compare `submittedAt` with the latest commit's `committedDate`; a dismissed review ("The base branch was changed.") fails this row | |
| `reviewDecision` = `APPROVED` | | |
| `mergeStateStatus` = `CLEAN` | `BLOCKED` / `BEHIND` / `DIRTY` / `UNSTABLE` → fail, with the status named | |
| All checks pass | `gh pr checks` | |
| All review threads resolved | GraphQL `isResolved` | |
| Not a draft | `isDraft` | |
| Base is the intended branch | work that belongs to a train in `{topic_bases}` → that train; others → `{default_base}` unless the user says otherwise | |
| The user is an assignee (or the author when unassigned) — only when `{assignee_merges}` | `assignees`, `author` | |

Any FAIL → stop, print the table, say what has to happen first. Do not offer to bypass; the gate belongs to the project, not to the user to waive from here.

## Step 3 — Confirm once

Show: number, title, `base ← head`, merge method, commit count, whether the head branch will be deleted (yes unless `--keep-branch` or it matches `{protected}`), and the gate table (all PASS). `AskUserQuestion`: merge · abort.

## Step 4 — Merge

```bash
gh pr merge <n> --<merge_method> [--delete-branch]
```

Never `--auto`, never `--admin`, never a different method than confirmed.

## Step 5 — Local cleanup (only if the head branch was checked out)

```bash
git fetch origin <base>
git switch <base> && git pull --ff-only
{post_merge_command}   # if set, e.g. a submodule sync
```

**Branch / Worktree Cleanup Prompting:**
- Never delete the local branch automatically. Prompt the user whether to delete the local branch (`git branch -d <head>`).
- If working inside a **linked git worktree**:
  - Do **not** remove the worktree automatically.
  - Prompt the user whether to remove the worktree and its branch (e.g., `git worktree remove <worktree-path> && git branch -d <head>`), and wait for confirmation.

## Step 6 — Report

Merge commit, PR URL, and the two reminders that are easy to forget:
- Tracker status → `{status_after_merge}`, if configured (usually not the closed state; QA moves it on after retesting).
- Where it deploys: look up the base branch in `{deploy}` and name the environment; if the base has no entry, say so.

## Rules

- Read-only until the confirmed `gh pr merge`; no pushes, no rebases, no branch edits.
- A dismissed approval is a failed gate, even if the same reviewer approved earlier.
- Never merge unprompted — "is it ready?" gets the gate table, not a merge.
