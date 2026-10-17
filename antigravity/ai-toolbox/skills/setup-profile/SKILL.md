---
name: setup-profile
description: "User-only: run only when the user types /setup-profile. Create or update the ai-toolbox project profile for the current repo: detect every key in profiles/example.yml from the repo itself (git remote and branches, PR template, package and build files, test commands, docs and migration folders), mark each value as detected or guessed, ask the unknowns in one round, then write the profile where it stays private."
---

> **Running in Antigravity**: this skill is generated from the Claude Code source.
> - User-only skill (Claude Code: disable-model-invocation). Start it only when the user typed its slash command; never on your own initiative.
> - `ask_question` is Antigravity's interactive question tool (Claude Code: AskUserQuestion).

# setup-profile — write the project profile once, from the repo

Every ai-toolbox skill reads `AI_TOOLBOX_PROFILE`, else `<project root>/.ai-toolbox/profile.yml`, and asks for whatever is missing. This skill fills the profile up front so later skills stop asking.

## Arguments

| Argument | Meaning |
|---|---|
| (none) | write `<project root>/.ai-toolbox/profile.yml` |
| `--private=<path>` | write to that path instead (for example `~/.config/ai-toolbox/profiles/<repo>.yml`) and print the `export AI_TOOLBOX_PROFILE=…` line |
| `--update` | read the existing profile, fill only empty or stale keys, and show a diff |

## Steps

### 1. Find the template and any existing profile

- The key list comes from `profiles/example.yml` in the ai-toolbox plugin (`~/.gemini/config/plugins/ai-toolbox/../profiles/example.yml` when installed as a plugin, or the toolbox checkout). If neither is reachable, use the key list in the table in step 2.
- If a profile already exists (env var or `.ai-toolbox/profile.yml`), read it. Without `--update`, ask whether to update it or stop; never overwrite it silently.

Done when: you know the target path and which keys already have values.

### 2. Detect each key from the repo

Read the evidence, not memory. Record for every key: value, source (`file:line` or command), and confidence: **detected** (read directly), **guessed** (inferred from a pattern), or **unknown**.

| Section | Where to look |
|---|---|
| `git.default_base` | `git symbolic-ref refs/remotes/origin/HEAD` |
| `git.topic_bases`, `git.branch_format` | `git branch -r` names: recurring long-lived branches and the `<type>/<topic>/<slug>` shape of recent ones |
| `git.protected` | `gh api repos/{owner}/{repo}/branches --jq '.[] \| select(.protected) \| .name'` when `gh` works; else the default branch plus `release/*` (guessed) |
| `git.merge_method` | `gh api repos/{owner}/{repo}` (`allow_merge_commit`, `allow_squash_merge`, `allow_rebase_merge`); else the shape of recent merge commits |
| `review.*` | `.github/CODEOWNERS`, `.github/pull_request_template.md`, review guideline files; recent PR titles via `gh pr list --state merged --limit 20 --json title` for `pr_title_format` |
| `commands.*` | `package.json` scripts, `Makefile`, `go.mod`, `pyproject.toml`, `docker-compose*.yml`, CI workflow files (`.github/workflows/*.yml`): the commands CI actually runs are the best source |
| `environments.local_url` | dev server config, `docker-compose` ports, `.env.example` (read only the example file, never `.env`) |
| `environments.forbidden_hosts` | production hosts named in deploy docs or CI; when unsure, leave empty and ask |
| `docs.*` | existing folders: `docs/`, `pbi-docs/`, `specs/`, an OpenAPI file, a `.qa` or `qa/` folder |
| `api.*` | where the frontend calls the API, where backend request/response structs live |
| `database.*` | migration and DDL folders, seed files, a database container in `docker-compose` |
| `bug_tracker`, `personas`, `qa_import` | rarely in the repo: mark unknown unless a doc names them |
| `deploy` | CI deploy jobs and their branch or tag triggers; deployment notes in `CLAUDE.md` or `README` |

Never read secret files (`.env`, credentials, key files) and never copy a token, password or personal data into the profile.

Done when: every key has a value, a source and a confidence, or is marked unknown.

### 3. Ask the unknowns in one round

Show a table of **guessed** and **unknown** keys only, each with your recommended value (or "leave empty, the skill will ask"). Ask with one `ask_question` round of up to four questions, highest impact first (merge gate, protected branches, forbidden hosts, test commands); a "yes" accepts every recommendation. Keys still unanswered stay empty.

Done when: each guessed key is confirmed, changed or left empty.

### 4. Write it where it stays private

- Default: `<project root>/.ai-toolbox/profile.yml`. Then make sure git ignores it without changing shared files: if `git check-ignore -q .ai-toolbox/profile.yml` fails, append `.ai-toolbox/` to `$(git rev-parse --git-common-dir)/info/exclude`, and say so. Edit `.gitignore` only if the user asks.
- `--private=<path>`: write there and print the `export AI_TOOLBOX_PROFILE=<path>` line for their shell profile.
- Keep the template's comments and key order. Put `# guessed` after any value the user did not confirm.
- With `--update`, show the diff and write only after the user agrees.

Done when: the file exists and `git status --short` does not list it.

## Report

A short table: key, value, source, confidence; then the path written and how it is kept out of git. Name the keys still empty and which skills will ask for them.
