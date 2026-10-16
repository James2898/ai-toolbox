#!/usr/bin/env bash
# PostToolUse hook: detect when the project-manager skill serializes the
# Tier 1/2 parallel pair (codebase-explorer + requirements-engineer)
# instead of emitting both Agent(...) blocks in a single response.
#
# Mechanism:
#   1. Read the hook input JSON from stdin.
#   2. If the tool is `Agent` and subagent_type is one of the parallel-pair
#      members, append a timestamped record to a per-session state file.
#   3. When `requirements-engineer` fires, compare its timestamp to the
#      most recent `codebase-explorer` record:
#        - Within 2s → emitted together (parallel) → silent pass.
#        - More than 2s after explorer FINISHED → serial violation → warn.
#   4. Reset state when chain-terminating agents fire
#      (validator-agent, debug-memory) so a new task starts clean.
#
# Output: hook MUST exit 0 (never block). Warnings go to stderr and
# surface to the model as a system-reminder on the next turn.

set -uo pipefail

input=$(cat)

# Extract fields with jq if available, else fall back to grep.
if command -v jq >/dev/null 2>&1; then
  tool_name=$(echo "$input" | jq -r '.tool_name // empty')
  subagent=$(echo "$input" | jq -r '.tool_input.subagent_type // empty')
  session=$(echo "$input" | jq -r '.session_id // .sessionId // "default"')
  tool_status=$(echo "$input" | jq -r '.tool_response.status // .status // "ok"')
else
  tool_name=$(echo "$input" | grep -o '"tool_name"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*"\([^"]*\)"$/\1/')
  subagent=$(echo "$input" | grep -o '"subagent_type"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"\([^"]*\)"$/\1/')
  session=$(echo "$input" | grep -o '"session_id"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"\([^"]*\)"$/\1/')
  [ -z "$session" ] && session="default"
  tool_status="ok"
fi

# Only care about Agent calls.
[ "$tool_name" != "Agent" ] && exit 0
[ -z "$subagent" ] && exit 0

state_dir="/tmp/claude-pm-parallel"
mkdir -p "$state_dir"
state_file="$state_dir/$session.json"

now=$(date +%s)

# Initialize state file if missing.
if [ ! -f "$state_file" ]; then
  echo '{"explorer_returned_at":0,"requirements_at":0,"warned":false}' > "$state_file"
fi

read_state() {
  if command -v jq >/dev/null 2>&1; then
    jq -r ".$1 // 0" "$state_file" 2>/dev/null || echo 0
  else
    grep -o "\"$1\"[[:space:]]*:[[:space:]]*[0-9]*" "$state_file" | grep -o '[0-9]*$' || echo 0
  fi
}

write_state() {
  local key="$1" val="$2"
  if command -v jq >/dev/null 2>&1; then
    tmp=$(mktemp)
    jq ".$key = $val" "$state_file" > "$tmp" && mv "$tmp" "$state_file"
  else
    # Crude fallback: rewrite the whole file.
    explorer=$(read_state explorer_returned_at)
    requirements=$(read_state requirements_at)
    warned=$(grep -o '"warned"[[:space:]]*:[[:space:]]*\(true\|false\)' "$state_file" | grep -o 'true\|false' || echo false)
    case "$key" in
      explorer_returned_at) explorer="$val" ;;
      requirements_at) requirements="$val" ;;
      warned) warned="$val" ;;
    esac
    echo "{\"explorer_returned_at\":$explorer,\"requirements_at\":$requirements,\"warned\":$warned}" > "$state_file"
  fi
}

case "$subagent" in
  codebase-explorer)
    # PostToolUse fires AFTER the agent returns, so this timestamp is
    # explorer's completion time.
    write_state explorer_returned_at "$now"
    ;;
  requirements-engineer)
    explorer_returned=$(read_state explorer_returned_at)
    if [ "$explorer_returned" -eq 0 ]; then
      # Explorer has not returned yet — either (a) requirements-engineer
      # was invoked FIRST in the parallel pair and its PostToolUse fired
      # before explorer's, or (b) requirements-engineer is a legitimate
      # mid-chain re-route. Both are non-violations.
      :
    else
      delta=$(( now - explorer_returned ))
      # PostToolUse fires when each agent returns. In a parallel pair
      # invoked in the same response, both agents start at the same time
      # and return whenever each finishes — the gap between completions
      # can be minutes apart (e.g. explorer 2m52s vs requirements 2m14s
      # = 38s gap). What distinguishes serial from parallel is NOT the
      # post-completion delta but whether the second agent was invoked
      # before the first one returned.
      #
      # Heuristic refinement: a "serial" violation is when the gap is
      # so large it could not plausibly be parallel execution. A
      # parallel-pair completion gap rarely exceeds 5 min. We pick 60s
      # as the threshold: if requirements fires >60s AFTER explorer
      # already completed, PM almost certainly waited for the result
      # and then invoked sequentially.
      if [ "$delta" -gt 60 ]; then
        warned=$(grep -o '"warned"[[:space:]]*:[[:space:]]*\(true\|false\)' "$state_file" | grep -o 'true\|false' || echo false)
        if [ "$warned" != "true" ]; then
          cat >&2 <<EOF
⚠ PM PARALLELISM VIOLATION: \`requirements-engineer\` was invoked ${delta}s after \`codebase-explorer\` returned. Tier 1/2 §1 requires both \`Agent(...)\` tool-use blocks in the SAME response (concurrent execution). You serialized them, which roughly doubles wall-clock time for the explore+clarify phase.

Self-correct next time: emit both \`Agent(...)\` blocks in your FIRST response message for any Tier 1 or Tier 2 task. Do not wait for explorer to return before invoking requirements-engineer — they have no shared inputs.
EOF
          write_state warned true
        fi
      fi
    fi
    write_state requirements_at "$now"
    ;;
  validator-agent|debug-memory)
    # Chain is ending — reset state so the next task starts clean.
    rm -f "$state_file"
    ;;
esac

exit 0
