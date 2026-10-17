---
name: git-branch-create
description: "User-only: run only when the user types /git-branch-create. Create and switch to a new work branch the safe way — from a freshly fetched remote base, never from a stale local default, following the repo's naming convention (<type>/<topic>/<slug>, e.g. bugfix/billing/fix-invoice-rounding) and choosing the base deliberately (the default branch, or a long-lived train branch when the work belongs to it). Refuses protected names as the new branch, requires a clean tree, confirms base and name once, never pushes. Use whenever the user says \"create a branch\", \"new branch for…\", \"start work on bug 48\", \"branch off beta\", or is about to edit code while sitting on develop or master."
---

> **Running in Antigravity**: this skill is generated from the Claude Code source.
> - User-only skill (Claude Code: disable-model-invocation). Start it only when the user typed its slash command; never on your own initiative.
> - `ask_question` is Antigravity's interactive question tool (Claude Code: AskUserQuestion).
> - `ARGS` means whatever the user typed after `/<this-skill>`, or the request that triggered it.

# Create a Work Branch

Two rules live here: **never implement on the default branch**, and **always branch from the latest base**. A third is easy to miss: choose the base on purpose. When a project keeps long-lived trains (`{topic_bases}`) that sit far ahead of the default branch, branching feature work from the default builds on code that no longer matches the train.
## Inputs

`ARGS`: a full branch name, or a slug plus flags.

| Flag | Meaning |
|---|---|
| `--type=feature\|bugfix\|fix\|hotfix\|refactor\|test\|docs\|chore` | Branch type; inferred from intent when omitted (bug → `bugfix`) |
| `--topic=<topic>` | The train/topic segment (e.g. `billing`) |
| `--base=<branch>` | Base branch; overrides inference |

Nothing provided → ask for what the work is and derive the rest.

## Project settings

This skill reads the project profile (see the toolbox README): `AI_TOOLBOX_PROFILE`, else `<project root>/.ai-toolbox/profile.yml`. Placeholders used below:

| Placeholder | Profile key | Without a profile |
|---|---|---|
| `{default_base}` | `git.default_base` | the remote default branch |
| `{topic_bases}` | `git.topic_bases` | none: use the PR's own base |
| `{branch_format}` | `git.branch_format` | the dominant pattern in `git branch -r` |
| `{protected}` | `git.protected` | `main`, `master`, `develop`, `release/*` |

## Step 1 — Preconditions

```bash
git rev-parse --is-inside-work-tree
git status --porcelain
```

Not a repo → stop. Dirty tree → stop and say what is modified; suggest commit or stash, but do not stash on the user's behalf (a stash they did not ask for is where work gets lost).

## Step 2 — Resolve the base, deliberately

Priority:
1. `--base` if given.
2. If `--topic` is given, or the current branch matches `<type>/<topic>/…`, and a train matching `{topic_bases}` exists for that topic → propose the train.
3. Otherwise the remote default:
   ```bash
   DEFAULT=$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null | sed 's@^origin/@@')
   DEFAULT=${DEFAULT:-$(git remote show origin 2>/dev/null | sed -n 's/.*HEAD branch: //p')}
   ```

Say which rule picked the base. When the current branch is on a train but the user asked for something unrelated to it, ask rather than guess.

## Step 3 — Compose the name

Use `{branch_format}`: typically `<type>/<topic>/<slug>` when the work belongs to a train, `<type>/<slug>` otherwise. Slug: kebab-case, ≤ 6 words, descriptive (`skip-archived-rules-on-sync`, `fix-empty-state-copy`). Without a profile, use the dominant pattern from `git branch -r`.

## Step 4 — Refuse what must not be created

- Protected names as the **new** branch: `{protected}`, and any train matching `{topic_bases}`.
- A name that already exists:
  ```bash
  git rev-parse --verify --quiet "refs/heads/$NAME"
  git ls-remote --heads origin "$NAME"
  ```
  Exists → stop and report (switch to it instead, if that is what the user meant).

## Step 5 — One confirmation

```bash
git fetch origin "$BASE"
git log -1 --oneline "origin/$BASE"
```

Ask once with `ask_question`, showing the name, the base, the base's latest commit and the rule that picked the base. Options: create · change name · change base · abort.

## Step 6 — Create

```bash
git switch -c "$NAME" --no-track "origin/$BASE"   # without --no-track, a bare push goes to the base
git branch -vv
```

If the repository uses submodules and the switch moved a submodule pointer, run `git submodule update --init --recursive`; an empty submodule can break builds and tests.

## Step 7 — Report

Branch, base and base commit. **No push** — pushing is the user's call, in their own turn.

## Rules

- Never `reset --hard`, never stash unasked, never push, never create from a stale local base.
- Protected names are fine as a base and never as a new branch.
