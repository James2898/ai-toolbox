---
name: self-review
description: "Review your own branch before opening or updating a PR, on two separate axes: Standards (does the diff follow the project's rules, conventions and sibling code) and Spec (does it do what the PBI, task or bug asked, no more and no less). Every finding cites file:line plus the rule or acceptance criterion it breaks, and is verified by reading the code or running a command. Read-only. Use when the user asks to self-review, check their branch or diff before a PR, or asks whether their change is ready for review."
---

> **Running in Antigravity**: this skill is generated from the Claude Code source.
> - `ask_question` is Antigravity's interactive question tool (Claude Code: AskUserQuestion).

# self-review — Standards and Spec, kept apart

A reviewer asks two different questions: *is this written the way we write things here* and *is this the thing we asked for*. Mixing them hides the second one behind style comments. This skill answers each on its own, before a reviewer has to.

## Arguments

| Argument | Meaning |
|---|---|
| (none) | the current branch against its base |
| `--base=<branch>` | the base to diff against |
| `--spec=<PBI id, path or PR>` | the requirement to check against |
| `--axis=standards\|spec` | run one axis only |

## Project settings

Reads the project profile (`AI_TOOLBOX_PROFILE`, else `<project root>/.ai-toolbox/profile.yml`).

| Placeholder | Profile key | Without a profile |
|---|---|---|
| `{default_base}`, `{topic_bases}` | `git.default_base`, `git.topic_bases` | `git symbolic-ref refs/remotes/origin/HEAD` |
| `{pbi_dir}` | `docs.pbi_dir` | `pbi-docs/` |
| `{frontend_check}`, `{backend_test}`, `{format_check}` | `commands.*` | from `package.json` and the build files |
| `{memory_dir}` | `docs.memory_dir` | skip, and say so |

## Steps

### 1. Pin the diff

Base: `--base`, else the base of the branch's open PR (`gh pr view --json baseRefName`), else the topic base the branch was cut from, else `{default_base}`. Never assume `main` or `develop`. `git fetch origin <base>`, then read `git diff origin/<base>...HEAD` in full, plus uncommitted changes (`git status --short`) as a separate list.

Done when: the base, the commit list and the changed files are stated.

### 2. Pin the spec

From `--spec`, the PBI hardcopy in `{pbi_dir}` matching the branch name, the PR body, a task file, or the bug report. List its acceptance criteria as AC-1…AC-n. If none is found, ask once; without one, the Spec axis reports "no spec — not checked" instead of guessing intent.

Done when: the AC list is written, or the Spec axis is marked unchecked.

### 3. Standards axis

The rules are what the project wrote down, plus what its sibling code does:

- Rule files: `CLAUDE.md`, `AGENTS.md`, `.claude/rules/**`, contributing and review guideline files. Check each changed file against the rules whose scope covers it.
- Sibling code: for each new or changed function, component, hook or handler, find the closest existing one doing the same job and compare naming, layering, error handling, test style.
- Lessons: grep `{memory_dir}` for the files, symbols and feature area the diff touches; check the diff against the hits.
- Smell baseline: dead or unreachable code, duplicated types or helpers that already exist, names that leak the caller's state (`isDrawerOpen` where `showX` is meant), comments that narrate the diff instead of the code, tests that assert their own fixture, scope that drifted beyond the spec.
- Mechanical checks: run `{frontend_check}`, `{backend_test}` and `{format_check}` for the touched areas, plus the suites that depend on changed shapes. Classify any failure against the base (`git stash; run; git stash pop` or a base worktree) before blaming the diff.

### 4. Spec axis

For each AC: **met** (cite the `file:line` that does it and the test or command that proves it), **partly met**, **not met**, or **contradicted**. Then list what the diff does that no AC asks for (scope creep) and ACs that are untestable as written.

### 5. Verify before reporting

Re-open every finding's `file:line` and confirm the claim against the code as it is, the rule text as written, and the sibling. Drop findings you cannot confirm. Do not rank a style point as blocking unless a written rule makes it so.

Optionally, for risky diffs (auth, data writes, concurrency, shared components), spawn `validator-agent` in the background and fold in only the findings you could verify.

Done when: every remaining finding has a citation you re-read.

## Report

```markdown
## Self-review — <branch> vs <base>

**Verdict:** ready | ready after fixes | not ready — <one line why>

### Spec
| AC | Status | Where | Proof |
|---|---|---|---|

Unasked-for changes: …

### Standards
| # | Severity | file:line | Finding | Rule or sibling it breaks |
|---|---|---|---|---|

### Checks run
| Command | Result | Same on base? |
```

Severity: **blocking** (breaks a written rule, an AC or a test), **should** (diverges from sibling code a reviewer will flag), **nit**. Stop at the report: no edits, commits or comments unless the user asks.
