#!/usr/bin/env python3
"""Build the Antigravity plugin from the Claude Code source in claude/.

claude/ is the only folder you edit. This script regenerates antigravity/ai-toolbox/:

    python3 -I tools/build_antigravity.py           # rebuild antigravity/ai-toolbox
    python3 -I tools/build_antigravity.py --check   # exit 1 if the committed output is stale

Format follows Antigravity's bundled docs (plugin and agy-customizations skills):
plugin.json keys, skills/<name>/SKILL.md with name + description, agents/<name>.md,
rules/AGENTS.md (plain markdown, no frontmatter). Hooks are not converted: Antigravity's
hooks.json uses a different event model, so the Claude hooks stay Claude-only.
"""
import filecmp
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "claude"
OUT = ROOT / "antigravity" / "ai-toolbox"
PLUGIN = "ai-toolbox"
AGY_PATH = f"~/.gemini/config/plugins/{PLUGIN}"

SKIP_PARTS = {"evals", "__pycache__"}
MANIFEST_KEYS = {"name", "displayName", "description", "version", "suggestedPrompts", "logo", "disabled"}

TOOL_MAP = {"Read": "view_file", "Write": "write_to_file", "Edit": "replace_file_content",
            "MultiEdit": "replace_file_content", "Bash": "run_command", "Grep": "grep_search",
            "Glob": "list_dir"}
TOOLS = "|".join(TOOL_MAP)
SUBS = [
    (re.compile(r"AskUserQuestion"), "ask_question"),
    (re.compile(r"\$ARGUMENTS"), "ARGS"),
    (re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}"), AGY_PATH),
    (re.compile(rf"`({TOOLS})`(?= tool| calls?|\b)"), lambda m: f"`{TOOL_MAP[m.group(1)]}`"),
    (re.compile(rf"\b(?:the )?({TOOLS}) tool\b"), lambda m: f"the `{TOOL_MAP[m.group(1)]}` tool"),
]
NOTES = [
    (r"AskUserQuestion", "`ask_question` is Antigravity's interactive question tool (Claude Code: AskUserQuestion)."),
    (r"\$ARGUMENTS", "`ARGS` means whatever the user typed after `/<this-skill>`, or the request that triggered it."),
    (r"Agent\(|subagent_type|`Agent` tool|Agent tool",
     "Where this says `Agent(subagent_type: \"x\")`, delegate to the subagent `x` in this plugin's `agents/` folder with the same prompt."),
    (r"mcp__", "Names starting with `mcp__` are Claude Code MCP tool names; use the same server's tool as configured in Antigravity's mcp_config.json."),
    (r"~/\.claude/", "Paths under `~/.claude/` belong to Claude Code and may not exist here; skip steps that only use them and say so."),
]


def split_frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n?", text, re.S)
    if not m:
        return {}, text
    fields = {}
    for key in ("name", "description"):
        mm = re.search(rf"^{key}:\s*(.*)$", m.group(1), re.M)
        if mm:
            v = mm.group(1).strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                v = v[1:-1].replace('\\"', '"')
            fields[key] = v
    return fields, text[m.end():]


def convert(body):
    for rx, rep in SUBS:
        body = rx.sub(rep, body)
    return body


def user_only(original):
    m = re.match(r"^---\n(.*?)\n---", original, re.S)
    return bool(m and re.search(r"^disable-model-invocation:\s*true\s*$", m.group(1), re.M))


def render(fields, body, original, kind):
    desc = fields["description"]
    notes = [n for pat, n in NOTES if re.search(pat, original)]
    if user_only(original):
        # Antigravity has no disable-model-invocation; keep the intent in the text it reads.
        desc = f"User-only: run only when the user types /{fields['name']}. {desc}"
        notes.insert(0, "User-only skill (Claude Code: disable-model-invocation). Start it only when the user typed its slash command; never on your own initiative.")
    desc = desc.replace("\\", "\\\\").replace('"', '\\"')
    out = f"---\nname: {fields['name']}\ndescription: \"{desc}\"\n---\n"
    if notes:
        out += (f"\n> **Running in Antigravity**: this {kind} is generated from the Claude Code source.\n"
                + "".join(f"> - {n}\n" for n in notes) + "\n")
    return out + convert(body).lstrip("\n")


def build(out):
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    claude_manifest = json.loads((SRC / ".claude-plugin" / "plugin.json").read_text())
    manifest = {k: v for k, v in {
        "name": PLUGIN,
        "displayName": "AI Toolbox",
        "description": claude_manifest.get("description", ""),
        "version": claude_manifest.get("version", "0.1.0"),
    }.items() if k in MANIFEST_KEYS}
    (out / "plugin.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    counts = {"skills": 0, "agents": 0, "rules": 0}

    for sdir in sorted(p for p in (SRC / "skills").glob("*") if (p / "SKILL.md").exists()):
        original = (sdir / "SKILL.md").read_text(encoding="utf-8")
        fields, body = split_frontmatter(original)
        if not fields.get("description"):
            raise SystemExit(f"{sdir.name}: SKILL.md has no description")
        fields.setdefault("name", sdir.name)
        dest = out / "skills" / sdir.name
        dest.mkdir(parents=True)
        (dest / "SKILL.md").write_text(render(fields, body, original, "skill"), encoding="utf-8")
        for f in sdir.rglob("*"):
            rel = f.relative_to(sdir)
            if f.is_dir() or f.name == "SKILL.md" or SKIP_PARTS & set(rel.parts):
                continue
            target = dest / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            if f.suffix == ".md":
                target.write_text(convert(f.read_text(encoding="utf-8")), encoding="utf-8")
            else:
                shutil.copy2(f, target)
        counts["skills"] += 1

    for af in sorted((SRC / "agents").glob("*.md")):
        original = af.read_text(encoding="utf-8")
        fields, body = split_frontmatter(original)
        if not fields.get("description"):
            raise SystemExit(f"agent {af.name}: no description")
        fields.setdefault("name", af.stem)
        (out / "agents").mkdir(exist_ok=True)
        (out / "agents" / f"{fields['name']}.md").write_text(render(fields, body, original, "subagent"), encoding="utf-8")
        counts["agents"] += 1

    rules = sorted((SRC / "rules").glob("*.md"))
    if rules:
        (out / "rules").mkdir()
        parts = [convert(split_frontmatter(r.read_text(encoding="utf-8"))[1]).strip() for r in rules]
        (out / "rules" / "AGENTS.md").write_text("\n\n---\n\n".join(parts) + "\n", encoding="utf-8")
        counts["rules"] = len(rules)

    (out / "README.md").write_text(
        "# AI Toolbox for Antigravity\n\nGenerated by `tools/build_antigravity.py` from `claude/`. "
        "Do not edit these files; edit the source and rebuild.\n", encoding="utf-8")
    return counts


def same_tree(a, b):
    cmp = filecmp.dircmp(a, b)
    if cmp.left_only or cmp.right_only or cmp.diff_files or cmp.funny_files:
        return False
    return all(same_tree(a / d, b / d) for d in cmp.common_dirs)


def main(argv):
    if "--check" in argv:
        with tempfile.TemporaryDirectory() as tmp:
            fresh = Path(tmp) / PLUGIN
            build(fresh)
            if not OUT.exists() or not same_tree(fresh, OUT):
                print("antigravity/ is stale: run python3 -I tools/build_antigravity.py")
                return 1
        print("antigravity/ is up to date")
        return 0
    counts = build(OUT)
    print(f"built {OUT.relative_to(ROOT)}: {counts['skills']} skills, {counts['agents']} agents, {counts['rules']} rule files")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
