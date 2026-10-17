---
name: gh-pr-approve
description: Approve a pull request with the gh CLI after checking that the active GitHub account is the one expected for the repository and is not the PR author (self-approval is refused), showing existing reviews, and confirming the exact PR and optional approval comment with the user. Approve-only — never comments, requests changes, or merges. Use whenever the user says "approve this PR", "LGTM, approve PR 1090", "approve a teammate's PR", or wants to submit an approving review from the terminal.
allowed-tools:
  - Bash
  - AskUserQuestion
user-invocable: true
disable-model-invocation: true
---

# Approve a Pull Request

An approval is a public statement under your name, so the skill makes sure it is the right name (people with a work and a personal GitHub account approve from the wrong one easily), the right PR, and not your own PR.
## Inputs

`$ARGUMENTS`: PR number or URL (default: the current branch's PR). Flags: `--body="<text>"` for an approval comment.

## Step 1 — Which account is active

```bash
gh auth status
gh api user -q .login
```

If you keep more than one account in `gh`, the active one may not be the one this repository expects. If the login is not the account expected for this repository, run `gh auth switch --user <expected>` and re-check before anything else; approving from the wrong account is embarrassing and has to be redone.

## Step 2 — The PR

```bash
gh pr view <n> --json number,title,url,author,isDraft,baseRefName,headRefName,reviewDecision,reviews
```

- Author login equals the active login → **stop**: self-approval is refused, no override.
- Draft → say so; approving a draft is usually a mistake, ask before continuing.
- Show existing reviews (login, state, date) so the user knows what their approval adds. If the project profile names a `review.final_reviewer`, that approval is the merge gate; another approval is useful review signal but does not make the PR mergeable — say that when it applies.

## Step 3 — Confirm

`AskUserQuestion` showing number, title, author, `base ← head`, and the body text (or "no comment"). Options: approve · abort.

## Step 4 — Approve

```bash
gh pr review <n> --approve [--body "<text>"]
```

## Step 5 — Report

The review URL and the resulting `reviewDecision`.

## Rules

- Approve only. Comments and change requests are written by hand or by the review skills; merging is `/gh-pr-merge`.
- Never approve a PR authored by the active account.
- Read-only apart from the one confirmed `gh pr review` call.
