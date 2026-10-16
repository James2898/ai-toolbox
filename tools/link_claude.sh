#!/usr/bin/env bash
# Link this repo's Claude Code skills and agents into your personal Claude folders,
# so they run with short names (/test-plan) and edits here apply immediately.
# This is the alternative to installing the plugin (which prefixes every skill: /ai-toolbox:test-plan).
#
#   tools/link_claude.sh            # dry run: show what would be linked
#   tools/link_claude.sh --apply    # create the links
#
# Safety: never deletes or overwrites. An existing real folder or file with the same name is
# reported and skipped; move it away yourself first if you want the repo version linked.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
CLAUDE_HOME="${CLAUDE_HOME:-$HOME/.claude}"
APPLY=0
[[ "${1:-}" == "--apply" ]] && APPLY=1

link_one() {
  local src="$1" dest="$2"
  if [[ -L "$dest" ]]; then
    if [[ "$(readlink "$dest")" == "$src" ]]; then
      echo "ok       $dest"
    else
      echo "SKIP     $dest (a link to somewhere else: $(readlink "$dest"))"
    fi
  elif [[ -e "$dest" ]]; then
    echo "SKIP     $dest (a real file or folder exists; move it away to use the repo version)"
  elif (( APPLY )); then
    ln -s "$src" "$dest"
    echo "linked   $dest -> $src"
  else
    echo "would    $dest -> $src"
  fi
}

mkdir -p "$CLAUDE_HOME/skills" "$CLAUDE_HOME/agents"
for d in "$REPO"/claude/skills/*/; do
  [[ -f "$d/SKILL.md" ]] || continue
  name="$(basename "$d")"
  link_one "${d%/}" "$CLAUDE_HOME/skills/$name"
done
for f in "$REPO"/claude/agents/*.md; do
  [[ -f "$f" ]] || continue
  link_one "$f" "$CLAUDE_HOME/agents/$(basename "$f")"
done
mkdir -p "$CLAUDE_HOME/hooks" "$CLAUDE_HOME/rules"
for f in "$REPO"/claude/hooks/*.sh; do
  [[ -f "$f" ]] || continue
  link_one "$f" "$CLAUDE_HOME/hooks/$(basename "$f")"
done
for f in "$REPO"/claude/rules/*.md; do
  [[ -f "$f" ]] || continue
  link_one "$f" "$CLAUDE_HOME/rules/$(basename "$f")"
done
echo "Hooks are linked but not switched on: wire them in your Claude settings file (claude/hooks/hooks.json lists the events and matchers)."
(( APPLY )) || echo -e "\nDry run. Re-run with --apply to create the links."
