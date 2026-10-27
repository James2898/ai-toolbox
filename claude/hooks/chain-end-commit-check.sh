#!/usr/bin/env bash
# PostToolUse hook on Agent: when @debug-memory finishes (the canonical
# chain terminator), check the working tree for uncommitted edits to
# files that should have been part of the task's commit set.
#
# Why this exists:
#   The dev-side pre-commit-staging-check.sh hook only fires when the
#   dev runs `git commit`. Edits made AFTER the dev's commit by:
#     - @release-manager (CHANGELOG.md, sometimes tasks/TASK-NNN.md status)
#     - @project-manager (tasks/TASK-NNN.md PASS WITH AMENDMENT edits)
#     - @validator-agent (PR title/body draft — usually not file edits)
#     - @debug-memory (MEMORY.md BUG-NNN additions)
#   ...were left modified-but-unstaged across TASK-016, TASK-017, TASK-018,
#   and TASK-019. Each agent's "step 8/etc. — MUST commit" prompt rule
#   batted 0-for-4. Time for hook enforcement.
#
#   This hook fires once at chain end (when debug-memory returns) and
#   surveys what's still uncommitted across the trailing-edit files.
#   Soft warning for now (exit 0). Surfaces as a system-reminder on the
#   next turn, giving the orchestrator a clear last-mile prompt to
#   commit the cleanup.
#
# Targets:
#   - tasks/TASK-*.md (any tracked or untracked task file)
#   - tasks/TASK-*/ (artifact directories)
#   - CHANGELOG.md
#   - MEMORY.md
#
# Explicitly ignored (noise / user-local):
#   - .claude/settings.local.json
#   - .claude/worktrees/
#   - development phases/*.md (unless the task explicitly touched them)

set -uo pipefail

input=$(cat)

if ! command -v jq >/dev/null 2>&1; then
  exit 0
fi

tool_name=$(echo "$input" | jq -r '.tool_name // empty')
subagent=$(echo "$input" | jq -r '.tool_input.subagent_type // empty')
cwd=$(echo "$input" | jq -r '.cwd // empty')

[ "$tool_name" != "Agent" ] && exit 0
[ "$subagent" != "debug-memory" ] && exit 0
[ -z "$cwd" ] && exit 0

repo=$(git -C "$cwd" rev-parse --show-toplevel 2>/dev/null) || exit 0

# Pull short porcelain status. Format: XY<space><path>.
status=$(git -C "$repo" status --porcelain 2>/dev/null) || exit 0
[ -z "$status" ] && exit 0

# Same parsing approach as pre-commit-staging-check.sh.
# We want lines where the file is modified-or-new and NOT staged for commit:
#   X (index)        = space or ?
#   Y (working tree) = M, D, A, or ?
unstaged_paths=$(
  printf '%s\n' "$status" \
    | awk '
        {
          x = substr($0, 1, 1);
          y = substr($0, 2, 1);
          path = substr($0, 4);
          if ((x == " " || x == "?") && (y == "M" || y == "D" || y == "A" || y == "?")) {
            print path;
          }
        }
      '
)

[ -z "$unstaged_paths" ] && exit 0

# Check repository visibility
is_public=false
if command -v gh >/dev/null 2>&1; then
  gh_out=$(gh repo view --json isPrivate 2>/dev/null || true)
  if echo "$gh_out" | grep -q '"isPrivate":false'; then
    is_public=true
  fi
fi

# Match against our list of "should-have-been-committed" patterns.
matched=()

while IFS= read -r path; do
  [ -z "$path" ] && continue

  # Strip surrounding quotes (git status quotes paths with spaces).
  clean="${path%\"}"
  clean="${clean#\"}"

  # Skip well-known noise files.
  case "$clean" in
    .claude/settings.local.json) continue ;;
    .claude/worktrees/*) continue ;;
  esac

  case "$clean" in
    CHANGELOG.md)
      matched+=("CHANGELOG.md")
      ;;
    MEMORY.md)
      if [ "$is_public" = "true" ]; then
        echo "⚠ PUBLIC REPO HYGIENE ALERT: Repository is public. Do NOT commit MEMORY.md! Ensure MEMORY.md is in .gitignore." >&2
      else
        matched+=("MEMORY.md")
      fi
      ;;
    tasks/TASK-*.md)
      matched+=("$clean")
      ;;
    tasks/TASK-*/*)
      matched+=("$clean")
      ;;
  esac
done <<< "$unstaged_paths"

# Check staged leaks if tools/leak_check.py exists
leak_script="$repo/tools/leak_check.py"
if [ -f "$leak_script" ]; then
  py_cmd=""
  if command -v python3 >/dev/null 2>&1; then
    py_cmd="python3"
  elif command -v py >/dev/null 2>&1; then
    py_cmd="py -3"
  fi
  if [ -n "$py_cmd" ]; then
    leak_out=$($py_cmd "$leak_script" --staged 2>&1 || true)
    if echo "$leak_out" | grep -q "finding(s)"; then
      echo "⚠ LEAK CHECK WARNING: Staged files contain potential credentials/leaks:" >&2
      echo "$leak_out" | grep -E "finding:|findings" >&2
    fi
  fi
fi

[ "${#matched[@]}" -eq 0 ] && exit 0

# Try to infer the active TASK-NNN from the most recent commit's
# message or files. Useful for the warning copy.
recent_task=$(
  git -C "$repo" log -1 --pretty=%s 2>/dev/null \
    | grep -oE 'TASK-[0-9]{8}-[a-z0-9]{3}|TASK-[0-9]+' \
    | head -1
)
[ -z "$recent_task" ] && recent_task="TASK-NNN"

{
  echo "⚠ CHAIN-END COMMIT WARNING"
  echo ""
  echo "@debug-memory has returned — the chain is done. But the following"
  echo "project artifacts are still modified-but-unstaged in the working"
  echo "tree from agents that ran AFTER the dev's commit:"
  echo ""
  for m in "${matched[@]}"; do
    echo "  - $m"
  done
  echo ""
  echo "Typical sources of these trailing edits:"
  echo "  - CHANGELOG.md       ← @release-manager added the task entry"
  echo "  - MEMORY.md          ← @debug-memory added BUG-NNN entries"
  echo "  - tasks/$recent_task.md ← @project-manager amended ACs after PASS WITH AMENDMENT"
  echo ""
  echo "If the task is shipping now, fold these into a follow-up commit"
  echo "on the same feature branch BEFORE pushing/opening the PR:"
  echo ""
  echo "  git add$(for m in "${matched[@]}"; do printf ' %q' "$m"; done)"
  mem_note=""
  [ "$is_public" != "true" ] && mem_note=", MEMORY"
  echo "  git commit -m \"docs($recent_task): trailing chain edits — CHANGELOG${mem_note}, AC amendments\""
  echo ""
  echo "Observed failures: TASK-016, TASK-017, TASK-018, TASK-019 — four"
  echo "consecutive tasks where trailing-agent edits were left uncommitted."
  echo "Prompt-level rules on each agent have not held."
} >&2

exit 0
