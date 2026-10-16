#!/usr/bin/env bash
# PostToolUse hook on Agent: warn when @task-logger leaves
# `tasks/pending/` populated after its run.
#
# Why this exists:
#   Task-logger's instructions (step 3) mandate moving `tasks/pending/*`
#   to `tasks/TASK-NNN/` after assigning the task ID. Observed across
#   TASK-016, TASK-017, TASK-018: task-logger uses `Write` to recreate
#   files in `tasks/TASK-NNN/` rather than `Bash mv`, leaving the
#   original `tasks/pending/` populated with stale duplicates. Future
#   tasks then see two sets of artifacts and get confused.
#
#   This hook fires AFTER any Agent call. When the agent was task-logger,
#   it inspects whether `tasks/pending/` survived the run. If yes, it
#   emits a warning to stderr.
#
# Output: exit 0 always (soft warning).

set -uo pipefail

input=$(cat)

if ! command -v jq >/dev/null 2>&1; then
  exit 0
fi

tool_name=$(echo "$input" | jq -r '.tool_name // empty')
subagent=$(echo "$input" | jq -r '.tool_input.subagent_type // empty')
cwd=$(echo "$input" | jq -r '.cwd // empty')

[ "$tool_name" != "Agent" ] && exit 0
[ "$subagent" != "task-logger" ] && exit 0
[ -z "$cwd" ] && exit 0

repo=$(git -C "$cwd" rev-parse --show-toplevel 2>/dev/null) || exit 0
pending_dir="$repo/tasks/pending"

[ ! -d "$pending_dir" ] && exit 0

# Count files (any depth).
file_count=$(find "$pending_dir" -type f 2>/dev/null | wc -l | tr -d ' ')
[ "$file_count" -eq 0 ] && exit 0

# List files for the warning.
file_list=$(find "$pending_dir" -type f 2>/dev/null | head -10 | sed "s|$repo/||")

{
  echo "⚠ TASK-LOGGER ARTIFACT-MOVE VIOLATION"
  echo ""
  echo "@task-logger finished but \`tasks/pending/\` still contains $file_count file(s):"
  echo ""
  echo "$file_list" | sed 's/^/  - /'
  echo ""
  echo "Per task-logger's step 3, these should have been MOVED (not copied)"
  echo "to \`tasks/TASK-NNN/\` so downstream agents read from a single canonical"
  echo "location. Instead they remain as stale duplicates."
  echo ""
  echo "Fix manually before the next agent runs:"
  echo "  mv tasks/pending/* tasks/TASK-NNN/  # or remove if duplicates"
  echo "  rmdir tasks/pending"
  echo ""
  echo "Observed: TASK-016, TASK-017, TASK-018 — three consecutive tasks where"
  echo "task-logger used Write instead of mv. Prompt-level rule has not stuck."
} >&2

exit 0
