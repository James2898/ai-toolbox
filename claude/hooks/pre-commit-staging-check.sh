#!/usr/bin/env bash
# PreToolUse hook on Bash: warn when `git commit` is about to run with
# important project artifacts modified-but-unstaged.
#
# Why this exists:
#   Across TASK-016, TASK-017, and TASK-018 the @fullstack-developer agent
#   committed only the code change, leaving `tasks/TASK-NNN.md`,
#   `tasks/TASK-NNN/` artifacts, and CHANGELOG.md modified-but-unstaged
#   in the working tree. @release-manager edited CHANGELOG.md but never
#   ran `git commit` after. Prompt-level rules added to agent definitions
#   failed three tasks in a row (0-for-3).
#
#   This hook intercepts `git commit` BEFORE it executes and inspects the
#   index/working-tree. If important files are modified but not staged
#   it emits a warning to stderr. Soft warning for now (exit 0) — Claude
#   sees the warning as a system-reminder and should self-correct. If
#   that still fails after another task or two, escalate to exit 2.
#
# Detection: matches Bash commands that contain `git commit` (and not
# `--amend`, since amends are an explicit user override).
#
# Targets:
#   CHANGELOG.md — modified but not staged
#   tasks/TASK-*.md — modified or new but not staged
#   tasks/TASK-*/ — new artifacts directory but not staged
#
# Output:
#   exit 0 always (soft warning only). Stderr warning surfaces to the
#   agent as a system-reminder on the next turn.

set -uo pipefail

input=$(cat)

if ! command -v jq >/dev/null 2>&1; then
  exit 0
fi

tool_name=$(echo "$input" | jq -r '.tool_name // empty')
command=$(echo "$input" | jq -r '.tool_input.command // empty')
cwd=$(echo "$input" | jq -r '.cwd // empty')

[ "$tool_name" != "Bash" ] && exit 0
[ -z "$command" ] && exit 0
[ -z "$cwd" ] && exit 0

# Match `git commit` but skip --amend (those are explicit overrides).
echo "$command" | grep -qE '(^|[[:space:]&;|])git[[:space:]]+commit([[:space:]]|$)' || exit 0
echo "$command" | grep -qE '(\-\-amend|\-c[[:space:]]|\-C[[:space:]])' && exit 0

# Find the repo root for this cwd. If not in a repo, skip.
repo=$(git -C "$cwd" rev-parse --show-toplevel 2>/dev/null) || exit 0

# Read staged + unstaged status. Format: XY <path>
# X = index status, Y = working-tree status.
# We care about files where Y is non-space (working-tree modified) AND
# X is space-or-? (index clean for that file).
status=$(git -C "$repo" status --porcelain 2>/dev/null) || exit 0

warnings=()

# Helper: check if a path appears in status with working-tree-only changes
# (i.e., not currently staged for the upcoming commit).
unstaged_paths=$(
  printf '%s\n' "$status" \
    | awk '
        # Columns are: positions 1-2 status, position 3 space, then path.
        # We want lines where position 1 is space or ? (index clean) AND
        # position 2 is M/D/A/? (working tree dirty).
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

if [ -z "$unstaged_paths" ]; then
  exit 0
fi

# Check each target pattern.
while IFS= read -r path; do
  [ -z "$path" ] && continue

  # Strip surrounding quotes if present (git status quotes paths with spaces).
  clean_path="${path%\"}"
  clean_path="${clean_path#\"}"

  case "$clean_path" in
    CHANGELOG.md)
      warnings+=("CHANGELOG.md")
      ;;
    tasks/TASK-*.md)
      warnings+=("$clean_path")
      ;;
    tasks/TASK-*/)
      warnings+=("$clean_path (directory)")
      ;;
    tasks/TASK-*/*)
      # File inside a TASK-NNN/ directory.
      warnings+=("$clean_path")
      ;;
  esac
done <<< "$unstaged_paths"

[ "${#warnings[@]}" -eq 0 ] && exit 0

# Emit warning. Soft (exit 0) so the commit still proceeds — Claude sees
# this as system-reminder text on the next turn.
{
  echo "⚠ PRE-COMMIT STAGING WARNING"
  echo ""
  echo "You're about to run \`git commit\` but the following project artifacts"
  echo "are modified-but-unstaged in the working tree:"
  echo ""
  for w in "${warnings[@]}"; do
    echo "  - $w"
  done
  echo ""
  echo "These should almost always be part of the same commit as the code"
  echo "change:"
  echo "  - CHANGELOG.md      → release-manager edits but must commit"
  echo "  - tasks/TASK-NNN.md → dev fills Resolution before committing"
  echo "  - tasks/TASK-NNN/   → task-logger artifacts (spec, context, etc)"
  echo ""
  echo "If your commit intentionally excludes them, ignore this warning."
  echo "Otherwise, abort the commit, stage them, and re-run."
  echo ""
  echo "Observed failures: TASK-016, TASK-017, TASK-018 each shipped commits"
  echo "missing the task file and/or CHANGELOG. The cleanup had to be done"
  echo "manually after the fact."
} >&2

exit 0
