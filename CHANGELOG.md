# Changelog

Changes to the ai-toolbox skills, agents, rules, hooks and build tools, newest first. Only merged work is listed, dated by the day its pull request merged.

## 2026-10-28

### Added
- `leak-check` skill: audits repository visibility (public vs private), confirms `MEMORY.md` and session notes are untracked and gitignored in public repos, and scans for platform tokens (Claude `sk-ant-`, Gemini `AIza`, GitHub PATs), private keys, emails, and local user paths. ([#11](https://github.com/James2898/ai-toolbox/pull/11))
- Hooks: `chain-end-commit-check.sh` and `pre-commit-staging-check.sh` enforce public repository memory hygiene and scan staged files for leaks before commits. ([#11](https://github.com/James2898/ai-toolbox/pull/11))
- Antigravity: model mapping (`sonnet` → `pro`, `haiku` → `flash`, default → `inherit`) and tool guardrail preservation for all 12 subagents. ([#11](https://github.com/James2898/ai-toolbox/pull/11))
- Rules: operational guardrails against headless interactive commands, token multiplication loops, and autonomous git operations. ([#11](https://github.com/James2898/ai-toolbox/pull/11))

### Changed
- `self-review`: added privacy and leak hygiene check to Standards axis before opening PRs. ([#11](https://github.com/James2898/ai-toolbox/pull/11))
- `tools/leak_check.py`: added Claude API key, Gemini API key, and Windows user path patterns, with auto-initialization for private pattern templates. ([#11](https://github.com/James2898/ai-toolbox/pull/11))
- `tools/build_antigravity.py`: direct directory copy on Windows to ensure Go Language Server plugin scanner discovers all subagents and skills. ([#11](https://github.com/James2898/ai-toolbox/pull/11))

### Removed
- `MEMORY.md`: untracked from Git and added to `.gitignore` to keep public open-source repository clean. ([#11](https://github.com/James2898/ai-toolbox/pull/11))

## 2026-10-27

### Added
- `lean-change` rule: an always-on ladder for code changes (does it need to exist → already in the codebase → standard library → installed dependency → one line → minimum code), a never-cut list (validation, data-loss handling, security, accessibility, anything asked for) and the `shortcut: <limit>, <when to upgrade>` comment. Adapted from [ponytail](https://github.com/DietrichGebert/ponytail) v5.3.2 (MIT). ([#9](https://github.com/James2898/ai-toolbox/pull/9))
- `code-grill` skill: grills an implementation approach round by round before coding, in ladder order, and closes with a decision record and the smallest plan. `--diff` grills the branch afterwards for plan drift and new debt markers. ([#9](https://github.com/James2898/ai-toolbox/pull/9))
- `repo-audit` skill: read-only audit of a whole repository or package, ranked as Must fix / Should fix / Nice to have, each finding with a triggering case and a re-read `file:line`. Secrets are reported by location and type, never by value. ([#9](https://github.com/James2898/ai-toolbox/pull/9))
- `code-debt` skill: ranked ledger of FIXME, HACK, TODO, `shortcut:` and other markers in code comments, bumped for risk paths and untracked work. `--diff` lists only what a branch adds; `--ref` scans a branch without checking it out. ([#9](https://github.com/James2898/ai-toolbox/pull/9))
- Catalog: a **Code health** category, and this changelog page, generated from `CHANGELOG.md` and linked from the catalog header. ([#9](https://github.com/James2898/ai-toolbox/pull/9))
- Profile keys: `docs.audit_dir`, `docs.debt_file`, `code_debt.risk_paths`, `code_debt.markers`, `bug_tracker.ticket_pattern`. ([#9](https://github.com/James2898/ai-toolbox/pull/9))

### Changed
- `fullstack-developer` applies the lean-change ladder as its own rule and lists shortcuts and skipped extras in the task Resolution. ([#9](https://github.com/James2898/ai-toolbox/pull/9))
- `validator-agent` audits a fourth dimension, Lean. Lean findings are Warning or Suggestion only, so they never start the fix loop. ([#9](https://github.com/James2898/ai-toolbox/pull/9))
- `codebase-explorer` notes when the standard library, the platform or an installed dependency already covers part of a task. ([#9](https://github.com/James2898/ai-toolbox/pull/9))
- README: changelog entries are added after a PR merges, and the dry-run step describes a shared fixture repo and ref-based branch handling. ([#9](https://github.com/James2898/ai-toolbox/pull/9))

## 2026-10-26

### Added
- `humanizer` skill: rewrites machine-sounding prose without changing its facts, in chat, file or embedded mode. Pattern families adapted from blader/humanizer (MIT). ([#7](https://github.com/James2898/ai-toolbox/pull/7))
- `design-grill --rounds`: interviews the user round by round over a design tree, with a recommended answer that "yes" accepts, until no decision is left open. ([#6](https://github.com/James2898/ai-toolbox/pull/6))

### Fixed
- `pr-details` derives its pre-merge checks from the repository instead of a fixed list. ([#8](https://github.com/James2898/ai-toolbox/pull/8))
- `retro` no longer lets the question prompt cover the findings it is asking about. ([#6](https://github.com/James2898/ai-toolbox/pull/6))

## 2026-10-18

### Added
- Catalog site: `docs/index.html`, generated by `tools/build_site.py` from `claude/`, lists every skill, agent, hook, rule and profile key plus the orchestration flow per tier. `--check` fails when `docs/` is stale. ([#4](https://github.com/James2898/ai-toolbox/pull/4))
- `diagnose` skill: builds a failing reproduction loop before any hypothesis, proves the cause by flipping it red to green, and saves the loop as PR evidence. ([#3](https://github.com/James2898/ai-toolbox/pull/3))
- `setup-profile`, `self-review`, `to-questionnaire` and `handoff` skills. ([#3](https://github.com/James2898/ai-toolbox/pull/3))
- `research` and `retro` skills. ([#3](https://github.com/James2898/ai-toolbox/pull/3))
- `pr-details`: a summary visual, an Evidence table and a Merge danger block. ([#3](https://github.com/James2898/ai-toolbox/pull/3))

### Changed
- Eight skills are user-only (`disable-model-invocation`), which cuts the always-loaded skill descriptions by about 27%. Antigravity, which has no such flag, gets a description prefix instead. ([#3](https://github.com/James2898/ai-toolbox/pull/3))
- `bugfix` hands root-cause work to `diagnose --cause-only`. ([#3](https://github.com/James2898/ai-toolbox/pull/3))
- Antigravity agents get the tools their role needs (write agents can edit, search agents can read and search), and Tier 0 tasks always get their own branch. ([#5](https://github.com/James2898/ai-toolbox/pull/5))

### Fixed
- `bugfix` and `git-branch-create` create branches with `--no-track`, so a bare `git push` cannot land on the base branch. ([#3](https://github.com/James2898/ai-toolbox/pull/3))
- `token-optimize` counts user-only skill descriptions separately, since they are not always loaded. ([#3](https://github.com/James2898/ai-toolbox/pull/3))
- `retro` re-checks each finding's evidence before presenting it. ([#3](https://github.com/James2898/ai-toolbox/pull/3))

## 2026-10-17

### Added
- First release: 26 skills, 12 agents, the `agent-routing` rule and 6 hooks, installable as a Claude Code plugin, with the Antigravity plugin generated by `tools/build_antigravity.py`. Project details come from `profiles/example.yml`; `tools/leak_check.py` blocks private names and secrets before a commit; `tools/link_claude.sh` links the source into `~/.claude`. ([#1](https://github.com/James2898/ai-toolbox/pull/1))
- `project-manager` skill: routes development tasks to the specialist agents by tier. ([#2](https://github.com/James2898/ai-toolbox/pull/2))
