#!/usr/bin/env python3
"""Build the catalog site (GitHub Pages) from the Claude Code source in claude/.

docs/ is generated; edit claude/, tools/site_categories.yml or tools/site/ (template.html,
workflow.json) instead:

    python3 -I tools/build_site.py           # rebuild docs/index.html
    python3 -I tools/build_site.py --check   # exit 1 if the committed docs/ is stale

The page repeats only what the repository already publishes: skill and agent frontmatter,
hook script headers, rule summaries and the keys of profiles/example.yml. The output holds no
commit id or date, so rebuilding an unchanged tree gives the same bytes and --check stays stable.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "claude"
OUT = ROOT / "docs"
TEMPLATE = ROOT / "tools" / "site" / "template.html"
CATEGORIES = ROOT / "tools" / "site_categories.yml"
PROFILE = ROOT / "profiles" / "example.yml"
WORKFLOW = ROOT / "tools" / "site" / "workflow.json"
AGY_DIR = "antigravity/ai-toolbox"
WRITE_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
SKIP_PARTS = {"evals", "__pycache__"}


class BuildError(Exception):
    pass


def unquote(v):
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        v = v[1:-1].replace('\\"', '"')
    return v


def frontmatter(path):
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n?", text, re.S)
    if not m:
        raise BuildError(f"{path.relative_to(ROOT)}: no frontmatter")
    fields, current = {}, None
    for line in m.group(1).splitlines():
        item = re.match(r"^\s+-\s*(.+)$", line)
        if item and current:
            fields[current].append(unquote(item.group(1)))
            continue
        kv = re.match(r"^([A-Za-z][\w-]*):\s*(.*)$", line)
        if not kv:
            continue
        key, value = kv.groups()
        if value == "":
            fields[key], current = [], key
        else:
            fields[key], current = unquote(value), None
    for key in ("name", "description"):
        if not fields.get(key):
            raise BuildError(f"{path.relative_to(ROOT)}: missing {key}")
    return fields, text[m.end():]


def first_sentence(text):
    # Stop at the first sentence end that is followed by a capital letter, skipping "e.g." style abbreviations.
    for m in re.finditer(r"[.!?](?=\s+[A-Z(\"'`])", text):
        if not re.search(r"\b(?:e\.g|i\.e|etc|vs)\.$", text[: m.end()]):
            return text[: m.end()]
    return text


def tool_list(value):
    if value is None:
        return None
    if isinstance(value, str):
        return [t.strip() for t in value.split(",") if t.strip()]
    return value


def read_categories():
    cats, current = [], None
    for raw in CATEGORIES.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line:
            continue
        head = re.match(r"^(\S.*):$", line)
        item = re.match(r"^\s+-\s*(\S+)$", line)
        if head:
            current = {"name": head.group(1), "skills": []}
            cats.append(current)
        elif item and current:
            current["skills"].append(item.group(1))
        else:
            raise BuildError(f"site_categories.yml: cannot read line {raw!r}")
    return cats


def read_skills():
    skills = []
    for path in sorted(SRC.glob("skills/*/SKILL.md")):
        fm, body = frontmatter(path)
        folder = path.parent
        tools = tool_list(fm.get("allowed-tools"))
        extras = sorted(p.name for p in folder.iterdir() if p.is_dir() and p.name not in SKIP_PARTS)
        rel = path.relative_to(ROOT).as_posix()
        skills.append({
            "name": fm["name"],
            "description": fm["description"],
            "summary": first_sentence(fm["description"]),
            "user_only": str(fm.get("disable-model-invocation", "")).lower() == "true",
            "tools": tools,
            "writes": tools is None or bool(WRITE_TOOLS & set(tools)),
            "uses_agents": (tools is not None and "Agent" in tools) or "subagent_type" in body,
            "extras": extras,
            "path": rel,
            "agy_path": f"{AGY_DIR}/skills/{folder.name}/SKILL.md",
            "_body": body,
        })
    return skills


def read_agents(skills):
    agents = []
    for path in sorted(SRC.glob("agents/*.md")):
        fm, _ = frontmatter(path)
        name = fm["name"]
        pattern = re.compile(rf"(?<![\w-]){re.escape(name)}(?![\w-])")
        agents.append({
            "name": name,
            "description": fm["description"],
            "model": fm.get("model") if isinstance(fm.get("model"), str) else None,
            "used_by": [s["name"] for s in skills if pattern.search(s["_body"])],
            "path": path.relative_to(ROOT).as_posix(),
        })
    return agents


def script_summary(path):
    lines = path.read_text(encoding="utf-8").splitlines()[1:]
    out = []
    for line in lines:
        if not line.startswith("#"):
            break
        text = line[1:].strip()
        if not text:
            if out:
                break
            continue
        out.append(text)
    return " ".join(out)


def read_hooks():
    config = json.loads((SRC / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    hooks = []
    for event, entries in config.get("hooks", {}).items():
        for entry in entries:
            for hook in entry.get("hooks", []):
                name = hook["command"].rsplit("/", 1)[-1]
                script = SRC / "hooks" / name
                if not script.is_file():
                    raise BuildError(f"hooks.json names {name}, which is not in claude/hooks/")
                hooks.append({
                    "name": name,
                    "event": event,
                    "matcher": entry.get("matcher", "*"),
                    "summary": script_summary(script),
                    "path": script.relative_to(ROOT).as_posix(),
                })
    return config.get("description", ""), hooks


def read_rules():
    rules = []
    for path in sorted(SRC.glob("rules/*.md")):
        title, para = path.stem, []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("# ") and title == path.stem:
                title = line[2:].strip()
            elif line.strip() and not line.startswith("#"):
                para.append(re.sub(r"^>\s?", "", line).strip())
            elif para:
                break
        rules.append({"title": title, "summary": " ".join(para), "path": path.relative_to(ROOT).as_posix()})
    return rules


def read_profile():
    groups, group = [], None
    for raw in PROFILE.read_text(encoding="utf-8").splitlines():
        section = re.match(r"^([a-z_]+):\s*(?:#\s?(.*))?$", raw)
        key = re.match(r"^  ([a-z_\"][^:]*):\s*(.*)$", raw)
        if section:
            group = {"section": section.group(1), "comment": section.group(2) or "", "keys": []}
            groups.append(group)
        elif key and group:
            value, comment = key.group(2), ""
            split = re.match(r"^(.*?)\s{2,}#\s?(.*)$", value) or re.match(r"^#\s?(.*)$", value)
            if split and split.lastindex == 2:
                value, comment = split.group(1), split.group(2)
            elif split:
                value, comment = "", split.group(1)
            value = value.strip()
            group["keys"].append({"key": key.group(1).strip('"'), "example": "" if value in ('""', "[]") else value,
                                  "comment": comment.strip()})
        elif re.match(r"^  - ", raw) and group and not group["keys"]:
            group.setdefault("items", []).append(raw.strip()[2:])
    for g in groups:
        if not g["keys"]:
            g["keys"] = [{"key": "(list)", "example": "; ".join(g.pop("items", [])), "comment": g["comment"]}]
        g.pop("items", None)
    return groups


def read_workflow(agent_names):
    wf = json.loads(WORKFLOW.read_text(encoding="utf-8"))
    wf.pop("_comment", None)
    named = [n["agent"] for t in wf["tiers"] for stage in t["stages"] for n in stage if "agent" in n]
    named += [a for t in wf["tiers"] for a in t["skipped"]] + [wf["fix_loop"]["after_agent"]]
    unknown = sorted(set(named) - set(agent_names))
    if unknown:
        raise BuildError("workflow.json names agents not in claude/agents/: " + ", ".join(unknown))
    for key in ("source", "rules"):
        if not (ROOT / wf[key]).is_file():
            raise BuildError(f"workflow.json {key} path does not exist: {wf[key]}")
    return wf


def build_data():
    plugin = json.loads((SRC / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    repo = plugin["repository"].rstrip("/")
    slug = re.sub(r"^https://github\.com/", "", repo)
    skills = read_skills()
    names = [s["name"] for s in skills]
    cats = read_categories()
    mapped = [n for c in cats for n in c["skills"]]
    problems = []
    if sorted(set(names) - set(mapped)):
        problems.append("not in site_categories.yml: " + ", ".join(sorted(set(names) - set(mapped))))
    if sorted(set(mapped) - set(names)):
        problems.append("in site_categories.yml but not in claude/skills/: " + ", ".join(sorted(set(mapped) - set(names))))
    dupes = sorted({n for n in mapped if mapped.count(n) > 1})
    if dupes:
        problems.append("listed more than once in site_categories.yml: " + ", ".join(dupes))
    if problems:
        raise BuildError("; ".join(problems))

    agents = read_agents(skills)
    hooks_description, hooks = read_hooks()
    for s in skills:
        del s["_body"]
    return {
        "name": plugin["name"],
        "version": plugin["version"],
        "description": plugin["description"],
        "license": plugin.get("license", ""),
        "repo": repo,
        "install": [
            {"id": "tab-claude", "steps": [
                {"note": "Add this repository as a plugin marketplace, then install the plugin:",
                 "commands": [f"claude plugin marketplace add {slug}", f"claude plugin install {plugin['name']}@{plugin['name']}"]},
                {"note": "Then point the skills at your project with a profile (see Project profile below)."},
            ]},
            {"id": "tab-agy", "steps": [
                {"note": "Install from the repository:",
                 "commands": [f"agy plugin install {repo}"]},
                {"note": f"Or copy (or symlink) {AGY_DIR} into ~/.gemini/config/plugins/{plugin['name']}, then restart Antigravity."},
            ]},
        ],
        "categories": cats,
        "skills": skills,
        "agents": agents,
        "workflow": read_workflow([a["name"] for a in agents]),
        "hooks_description": hooks_description,
        "hooks": hooks,
        "rules": read_rules(),
        "profile": read_profile(),
    }


def render():
    data = json.dumps(build_data(), ensure_ascii=False, indent=1).replace("</", "<\\/")
    template = TEMPLATE.read_text(encoding="utf-8")
    if template.count("/*DATA*/") != 1:
        raise BuildError("template.html must contain /*DATA*/ exactly once")
    return {"index.html": template.replace("/*DATA*/", data), ".nojekyll": ""}


def main(argv):
    try:
        files = render()
    except BuildError as e:
        print(f"build_site: {e}", file=sys.stderr)
        return 1
    if "--check" in argv:
        stale = [n for n, c in files.items()
                 if not (OUT / n).is_file() or (OUT / n).read_text(encoding="utf-8") != c]
        if stale:
            print("docs/ is stale: " + ", ".join(stale) + ". Run: python3 -I tools/build_site.py", file=sys.stderr)
            return 1
        print("docs/ is up to date")
        return 0
    OUT.mkdir(exist_ok=True)
    for name, content in files.items():
        (OUT / name).write_text(content, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}/index.html")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
