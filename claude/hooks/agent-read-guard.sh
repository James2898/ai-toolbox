#!/usr/bin/env bash
# PreToolUse hook: block specific agents from reading specific forbidden
# files, regardless of what their instruction file says.
#
# Why this exists:
#   Prompt-level restrictions in agent instruction files are advisory.
#   task-logger has been observed reading MEMORY.md, docs/coding-guidelines.md,
#   docs/tech-stack.md, and docs/structure.md across multiple tasks despite
#   the restrictions in its instruction file — costing ~20k tokens per task
#   and producing no improvement over the baseline.
#
#   This hook intercepts the Read tool call BEFORE it executes and exits with
#   a non-zero code (with a denial message on stderr) when the active agent
#   matches a deny entry. The agent sees the denial as a tool error and must
#   continue without that file.
#
# Detection:
#   Hook input JSON includes `session_id` and `transcript_path`. We tail the
#   transcript and grep backward for the most recent `subagent_type` value;
#   that identifies the currently active spawned agent. (If none found, the
#   call is from the main conversation, not a sub-agent — allow.)
#
#   Sub-agents that spawn further sub-agents would break this single-level
#   detection, but our agents do not — they're leaf agents called by either
#   the PM Skill or the user directly.
#
# Configuration:
#   Edit AGENT_DENY_MAP below to add/remove agent-file pairs.
#
# Output:
#   - exit 0 (allow): permit the Read call. No output.
#   - exit 2 (block): print a one-line denial to stderr; Claude Code surfaces
#     it as a tool error visible to the agent. The agent must adapt.

set -uo pipefail

input=$(cat)

# Parse hook input. Bail early if jq is missing — we need structured parsing.
if ! command -v jq >/dev/null 2>&1; then
  exit 0
fi

tool_name=$(echo "$input" | jq -r '.tool_name // empty')
transcript_path=$(echo "$input" | jq -r '.transcript_path // empty')

[ -z "$transcript_path" ] && exit 0
[ ! -f "$transcript_path" ] && exit 0

# Resolve `file_path` from the tool input. Direct from Read; inferred for Bash
# by pattern-matching cat/head/tail/sed/awk on the command string. This closes
# the obvious bypass (cat-ing a forbidden file).
file_path=""
case "$tool_name" in
  Read)
    file_path=$(echo "$input" | jq -r '.tool_input.file_path // empty')
    ;;
  Bash)
    command=$(echo "$input" | jq -r '.tool_input.command // empty')
    [ -z "$command" ] && exit 0
    # Extract first path-like argument after cat/head/tail/sed/awk/less/more.
    # Greedy match for absolute paths or relative paths with a dot, ending at
    # whitespace, pipe, redirect, or semicolon.
    file_path=$(echo "$command" \
      | grep -oE '(^|[[:space:]|;])(cat|head|tail|sed|awk|less|more)([[:space:]]+-[A-Za-z0-9]+)*[[:space:]]+[^[:space:]|;<>&]+' \
      | head -1 \
      | sed -E 's/.*(cat|head|tail|sed|awk|less|more)([[:space:]]+-[A-Za-z0-9]+)*[[:space:]]+//' \
      | tr -d '"' | tr -d "'")
    [ -z "$file_path" ] && exit 0
    ;;
  *)
    exit 0
    ;;
esac

[ -z "$file_path" ] && exit 0

# Main-session guard: a spawned sub-agent runs against its OWN transcript whose
# entries are marked `isSidechain:true`. The MAIN conversation's transcript
# contains zero sidechain entries — and the only `subagent_type` strings in it
# are the main session's own `Agent(...)` tool_use calls (the act of SPAWNING an
# agent), NOT the agent executing. Without this gate, the scan below would find
# a past `Agent(...)` call and falsely conclude that agent is "still active" for
# every subsequent main-session Read — blocking legitimate main-session memory
# upkeep after any sub-agent has run. If the transcript has no sidechain entries,
# we are in the main conversation: allow.
if ! grep -q '"isSidechain":[[:space:]]*true' "$transcript_path" 2>/dev/null; then
  exit 0
fi

# Find the most recent subagent_type in the transcript. We scan from the end
# backward so the active agent is the first match.
#
# Each Agent tool_use line in the JSONL contains: ..."subagent_type":"<name>"...
# We extract just the most recent one. tac is GNU-only on macOS, so use
# `tail -r` if available, else awk.
if command -v tac >/dev/null 2>&1; then
  reverse="tac"
elif tail -r </dev/null >/dev/null 2>&1; then
  reverse="tail -r"
else
  reverse="cat"  # fallback: scan forward and keep last match
fi

active_agent=$(
  $reverse "$transcript_path" 2>/dev/null \
    | grep -m 1 -o '"subagent_type":"[^"]*"' \
    | head -1 \
    | sed 's/.*"\([^"]*\)"$/\1/'
)

# If no agent context found, this is the main conversation — allow.
[ -z "$active_agent" ] && exit 0

# Resolve file_path to its basename + last directory segment for matching.
# We match on either basename ("MEMORY.md") or a relative suffix
# ("docs/coding-guidelines.md") so both absolute and relative forms work.
basename=$(basename "$file_path")
parent_dir=$(basename "$(dirname "$file_path")")
relative_suffix="$parent_dir/$basename"

# AGENT_DENY_MAP entries:
#   <agent-name>:<file-pattern>
#
# <file-pattern> matches either the basename or the parent-dir/basename
# suffix. Add/remove entries here.
deny_map=(
  # task-logger reads should come from tasks/pending/* artifacts only.
  # Forbid reading docs/ and MEMORY.md — those are the explorer's job.
  "task-logger:MEMORY.md"
  "task-logger:docs/coding-guidelines.md"
  "task-logger:docs/tech-stack.md"
  "task-logger:docs/structure.md"
  "task-logger:docs/api-discovery.md"

  # requirements-engineer may read MEMORY.md (the recent partial revert
  # permits it) but must NOT read source files. Source file paths are
  # too varied to enumerate here — leave to prompt enforcement for now.

  # integration-contract should not re-read coding standards / MEMORY.
  "integration-contract:MEMORY.md"
  "integration-contract:docs/coding-guidelines.md"
  "integration-contract:docs/tech-stack.md"
  "integration-contract:docs/structure.md"

  # validator-agent should read the task file's inlined MEMORY notes,
  # not MEMORY.md directly.
  "validator-agent:MEMORY.md"

  # release-manager: same as validator. Reads the task file, not MEMORY.
  "release-manager:MEMORY.md"
)

for entry in "${deny_map[@]}"; do
  agent="${entry%%:*}"
  pattern="${entry#*:}"

  [ "$agent" != "$active_agent" ] && continue

  if [ "$basename" = "$pattern" ] || [ "$relative_suffix" = "$pattern" ]; then
    cat >&2 <<EOF
🚫 BLOCKED by agent-read-guard hook

Agent: $active_agent
File:  $file_path

This agent's instruction file forbids reading this file. The information
you need is either:
  (a) inlined into the Handoff Trio / task file by an upstream agent
      (codebase-explorer or task-logger), or
  (b) outside your scope — do not work around this block.

If you genuinely need this file, return to your caller and request that
they inline the relevant content rather than re-reading. Do NOT retry,
do NOT use Bash to cat the file, do NOT use any other tool to bypass.

To change the policy, edit agent-read-guard.sh in your hooks folder (or the ai-toolbox plugin's hooks/).
EOF
    exit 2
  fi
done

exit 0
