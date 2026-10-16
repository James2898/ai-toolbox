#!/usr/bin/env bash
# PostToolUse hook: prune stale Claude worktrees after chain-ending agents
# (validator-agent or debug-memory) return.
#
# Why this exists:
#   Agents spawned with `isolation: "worktree"` create git worktrees at
#   .claude/worktrees/agent-*/. The harness locks them during the agent's
#   run but does not always unlock and prune them when the chain ends.
#   Across multiple tasks, this accumulated 12 stale worktrees (~0.5–1.2 GB
#   disk waste, plus stale branch refs that broke TASK-017's dev session).
#
#   This hook detects when a chain-ending agent returns and force-removes
#   any worktrees under .claude/worktrees/ that exist in the current repo.
#
# Trigger:
#   PostToolUse on Agent with subagent_type ∈ {validator-agent, debug-memory}
#   (chain-ending agents per the workflow conventions).
#
# Safety:
#   - Only operates on paths matching `.claude/worktrees/agent-*` under the
#     current repo's worktree list. Will not touch other worktrees.
#   - Force-removes after unlock — any uncommitted work in a stale worktree
#     is lost. This is the design: chain-ending agents mean the task is done,
#     so the worktree's contents have already been merged or rejected.
#   - Silent on success; logs to stderr only if removal fails.

set -uo pipefail

input=$(cat)

if ! command -v jq >/dev/null 2>&1; then
  exit 0
fi

tool_name=$(echo "$input" | jq -r '.tool_name // empty')
subagent=$(echo "$input" | jq -r '.tool_input.subagent_type // empty')
cwd=$(echo "$input" | jq -r '.cwd // empty')

[ "$tool_name" != "Agent" ] && exit 0
[ -z "$subagent" ] && exit 0
[ -z "$cwd" ] && exit 0

case "$subagent" in
  validator-agent|debug-memory)
    ;;
  *)
    exit 0
    ;;
esac

# Find the git toplevel from cwd. If not a git repo, bail.
git_root=$(git -C "$cwd" rev-parse --show-toplevel 2>/dev/null) || exit 0
[ -z "$git_root" ] && exit 0

# Iterate over worktrees that match .claude/worktrees/agent-* and remove.
removed=0
while IFS= read -r wt; do
  case "$wt" in
    "$git_root"/.claude/worktrees/agent-*)
      git -C "$git_root" worktree unlock "$wt" 2>/dev/null
      if git -C "$git_root" worktree remove --force "$wt" 2>/dev/null; then
        removed=$((removed + 1))
      else
        echo "worktree-cleanup: failed to remove $wt" >&2
      fi
      ;;
  esac
done < <(git -C "$git_root" worktree list --porcelain 2>/dev/null | grep '^worktree' | awk '{print $2}')

if [ "$removed" -gt 0 ]; then
  git -C "$git_root" worktree prune 2>/dev/null
fi

exit 0
