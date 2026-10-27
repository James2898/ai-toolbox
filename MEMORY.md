# MEMORY.md — ai-toolbox Architecture & Resolutions

## Agent Architecture & Model Specialization

- **RULE-001** | 2026-10-28 | Feature: `Antigravity Multi-Agent Compatibility`
  - **Context:** `ai-toolbox` agents have intentional, per-agent model specializations (`sonnet` / `pro` for high-reasoning architecture/validation; `haiku` / `flash` for lightweight logging/scans).
  - **Issue:** When Antigravity discovers subagents from plugins, unknown models (such as `sonnet`/`haiku`) or Claude-specific tool lists (`Read`, `Write`) cause Antigravity's subagent loader to fail validation and drop the subagents, leaving only agents with empty or default frontmatter visible (e.g. `fullstack-developer`).
  - **Resolution:** `tools/build_antigravity.py` explicitly translates Claude models to Antigravity model identifiers (`sonnet` -> `pro`, `haiku` -> `flash`, default -> `inherit`) and maps tool sets to Antigravity native tools (`read_file`, `write_file`, `edit_file`, `run_command`, `send_message`, `schedule`, `ask_question`).
  - **Rule:** Never strip model specializations when compiling agents for Antigravity; always map them to Antigravity's model tiers (`pro`, `flash`, `inherit`). Preserve guardrails via native tool lists (search-only vs write-enabled vs conversational).

## Operational Guardrails & Token Discipline

- **RULE-002** | 2026-10-28 | Failure Mode: `Headless Shells, Interactive Blocking & Token Bloat`
  - **Context:** Automated agent subshells run non-interactively without access to OS-level credential dialogs (e.g. Windows Git Credential Manager OAuth or SSH passphrase popups).
  - **Failure Mode:** Stalled commands (e.g. `git push`) cause agents to enter repetitive polling loops (`manage_task status`). In large sessions (100k+ tokens), each polling step re-reads the full context window from the prompt cache, multiplying token consumption by millions in minutes (e.g. ~8.29M cumulative tokens across 105 polling steps).
  - **Resolution:** Never execute commands that may trigger interactive credential prompts in background tasks unless credentials/tokens are verified beforehand. If a background process waits on credentials or user input, cancel the task immediately; do not loop or poll. Hand the exact command and PR link to the user to run in their local interactive terminal.

- **RULE-003** | 2026-10-28 | User Preference: `Explicit Approval for Git Branching & Commits`
  - **Context:** Git branch creation and commit operations must always be human-approved.
  - **Rule:** Never create a new git branch or commit changes without explicit user approval. Always propose the branch name, summary of changes, and commit message, and wait for confirmation before executing `git checkout -b`, `git branch`, or `git commit`.
