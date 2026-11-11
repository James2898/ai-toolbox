#!/usr/bin/env bash
# PreToolUse hook on Bash: deny very large commands that write a file through
# a heredoc, output redirection or tee, and tell the caller to use the Write
# tool instead.
#
# Why this exists:
#   In auto mode Claude Code adds a reminder to the main session and to every
#   subagent to do file work through Bash ("make file changes with sed,
#   heredocs ..."). A subagent that has to produce a long document then writes
#   it as one `cat > file <<'EOF'` call tens of KB long. Such calls were seen
#   to stall before running: no tool result, no file on disk, and the agent
#   showing as running for hours until stopped by hand (twice in one SDD
#   design phase). A prompt line ("use the Write tool") helps but is easy to
#   forget in a dispatch; this hook turns the stall into an immediate denial
#   the agent can recover from by retrying with Write.
#
# Detection: the Bash command is longer than MAX_CHARS and contains `<<`,
# `>` or a `tee` word. Shorter commands and long commands without a write
# shape (a long grep, a long echo to stdout without redirection) pass.
#
# Output:
#   - allow: no output, exit 0.
#   - deny: JSON with hookSpecificOutput.permissionDecision "deny" and a
#     reason naming the Write tool, exit 0. The agent sees the reason as the
#     tool result and can retry.
#
# Configuration: raise MAX_CHARS if legitimate large scripts get blocked.
# A long `python3 - <<'PY'` edit script counts as a write shape too; the
# intended alternative for those is the Edit tool.

set -uo pipefail

MAX_CHARS=8000

input=$(cat)

# Without jq the command cannot be read safely; allow rather than guess.
command -v jq >/dev/null 2>&1 || exit 0

cmd=$(printf '%s' "$input" | jq -r '.tool_input.command // empty')
[ -z "$cmd" ] && exit 0

len=${#cmd}
[ "$len" -le "$MAX_CHARS" ] && exit 0

if printf '%s' "$cmd" | grep -Eq '<<|>|(^|[^[:alnum:]_])tee([^[:alnum:]_]|$)'; then
  jq -n --arg len "$len" --arg max "$MAX_CHARS" '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason: ("Blocked: this Bash command is " + $len + " characters (limit " + $max + ") and writes through a heredoc, redirection or tee. Commands this large can stall the permission check. Create the file with the Write tool (use Edit for changes), one file per call.")
    }
  }'
fi

exit 0
