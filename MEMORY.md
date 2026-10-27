# MEMORY.md — ai-toolbox Architecture & Resolutions

## Agent Architecture & Model Specialization

- **RULE-001** | 2026-10-28 | Feature: `Antigravity Multi-Agent Compatibility`
  - **Context:** `ai-toolbox` agents have intentional, per-agent model specializations (`sonnet` / `pro` for high-reasoning architecture/validation; `haiku` / `flash` for lightweight logging/scans).
  - **Issue:** When Antigravity discovers subagents from plugins, unknown models (such as `sonnet`/`haiku`) or Claude-specific tool lists (`Read`, `Write`) cause Antigravity's subagent loader to fail validation and drop the subagents, leaving only agents with empty or default frontmatter visible (e.g. `fullstack-developer`).
  - **Resolution:** `tools/build_antigravity.py` explicitly translates Claude models to Antigravity model identifiers (`sonnet` -> `pro`, `haiku` -> `flash`, default -> `inherit`) and maps tool sets to Antigravity native tools (`read_file`, `write_file`, `edit_file`, `run_command`, `send_message`, `schedule`, `ask_question`).
  - **Rule:** Never strip model specializations when compiling agents for Antigravity; always map them to Antigravity's model tiers (`pro`, `flash`, `inherit`). Preserve guardrails via native tool lists (search-only vs write-enabled vs conversational).
