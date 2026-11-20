#!/usr/bin/env python3
"""Build the catalog site (GitHub Pages) from the Claude Code source in claude/.

docs/ is generated; edit claude/, CHANGELOG.md, tools/site_categories.yml or tools/site/
(template.html, changelog.html, workflow.json) instead:

    python3 -I tools/build_site.py           # rebuild docs/index.html and docs/changelog.html
    python3 -I tools/build_site.py --check   # exit 1 if the committed docs/ is stale

The pages repeat only what the repository already publishes: skill and agent frontmatter,
hook script headers, rule summaries, the keys of profiles/example.yml and CHANGELOG.md. The output holds no
commit id or date, so rebuilding an unchanged tree gives the same bytes and --check stays stable.
"""
import html
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
CHANGELOG = ROOT / "CHANGELOG.md"
CHANGELOG_TEMPLATE = ROOT / "tools" / "site" / "changelog.html"
SKILL_TEMPLATE = ROOT / "tools" / "site" / "skill_template.html"
CHANGE_KINDS = ("Added", "Changed", "Fixed", "Removed")
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


def inline_format(text):
    code_spans = []

    def save_code(m):
        code_spans.append("<code>" + html.escape(m.group(1)) + "</code>")
        return f"\x00CODE{len(code_spans) - 1}\x00"

    text = re.sub(r"`([^`]+)`", save_code, text)
    text = html.escape(text)

    def replace_link(m):
        lt = m.group(1)
        url = m.group(2)
        return f'<a href="{url}">{lt}</a>'

    text = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", replace_link, text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*\s](?:.*?[^*\s])?)\*(?!\*)", r"<em>\1</em>", text)

    for i, cs in enumerate(code_spans):
        text = text.replace(f"\x00CODE{i}\x00", cs)

    return text


def parse_lists(lines, i, n):
    items = []
    while i < n:
        line = lines[i]
        if not line.strip():
            if i + 1 < n and (re.match(r"^\s*([-*+]|\d+\.)\s+", lines[i + 1]) or (re.match(r"^\s+", lines[i + 1]) and not re.match(r"^\s*[#|`>]", lines[i + 1]))):
                i += 1
                continue
            else:
                break
        m_item = re.match(r"^(\s*)([-*+]|\d+\.)\s+(.*)$", line)
        if m_item:
            ind = len(m_item.group(1))
            bullet = m_item.group(2)
            content = m_item.group(3)
            is_ol = bullet[0].isdigit()
            i += 1
            cont = []
            while i < n and lines[i].strip() and not re.match(r"^\s*([-*+]|\d+\.)\s+", lines[i]):
                if lines[i].startswith(" " * (ind + 1)) or not re.match(r"^[#|`>]", lines[i]):
                    cont.append(lines[i].strip())
                    i += 1
                else:
                    break
            full_text = content + (" " + " ".join(cont) if cont else "")
            items.append((ind, is_ol, full_text))
        else:
            break

    if not items:
        return "", i

    stack = []
    html_out = []

    for ind, is_ol, text in items:
        tag = "ol" if is_ol else "ul"
        if not stack:
            stack.append((ind, tag))
            html_out.append(f"<{tag}><li>{inline_format(text)}")
        elif ind > stack[-1][0]:
            stack.append((ind, tag))
            html_out.append(f"<{tag}><li>{inline_format(text)}")
        elif ind < stack[-1][0]:
            while stack and ind < stack[-1][0]:
                _, close_tag = stack.pop()
                html_out.append(f"</li></{close_tag}>")
            if stack and stack[-1][1] != tag:
                _, close_tag = stack.pop()
                html_out.append(f"</li></{close_tag}><{tag}>")
                stack.append((ind, tag))
            else:
                html_out.append("</li>")
            html_out.append(f"<li>{inline_format(text)}")
        else:
            if stack[-1][1] != tag:
                _, close_tag = stack.pop()
                html_out.append(f"</li></{close_tag}><{tag}>")
                stack.append((ind, tag))
            else:
                html_out.append("</li>")
            html_out.append(f"<li>{inline_format(text)}")

    while stack:
        _, close_tag = stack.pop()
        html_out.append(f"</li></{close_tag}>")

    return "".join(html_out), i


def markdown_to_html(md):
    lines = md.replace("\r\n", "\n").split("\n")
    html_out = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]

        if not line.strip():
            i += 1
            continue

        m_fence = re.match(r"^(\s*)(`{3,}|~{3,})(.*)$", line)
        if m_fence:
            fence_indent = len(m_fence.group(1))
            fence_chars = m_fence.group(2)
            lang = m_fence.group(3).strip()
            code_lines = []
            i += 1
            while i < n:
                m_close = re.match(r"^(\s*)(`{3,}|~{3,})\s*$", lines[i])
                if m_close and len(m_close.group(1)) <= fence_indent and m_close.group(2)[0] == fence_chars[0] and len(m_close.group(2)) >= len(fence_chars):
                    i += 1
                    break
                code_lines.append(lines[i])
                i += 1
            code_str = html.escape("\n".join(code_lines))
            cls_attr = f' class="language-{html.escape(lang)}"' if lang else ""
            html_out.append(f"<pre><code{cls_attr}>{code_str}</code></pre>")
            continue

        m_head = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m_head:
            level = len(m_head.group(1))
            tag = f"h{min(level, 6)}"
            heading_content = inline_format(m_head.group(2).strip())
            html_out.append(f"<{tag}>{heading_content}</{tag}>")
            i += 1
            continue

        if re.match(r"^(\*{3,}|-{3,}|_{3,})$", line.strip()):
            html_out.append("<hr>")
            i += 1
            continue

        if line.startswith(">"):
            bq_lines = []
            while i < n and lines[i].startswith(">"):
                bq_lines.append(re.sub(r"^>\s?", "", lines[i]))
                i += 1
            bq_content = markdown_to_html("\n".join(bq_lines))
            html_out.append(f"<blockquote>{bq_content}</blockquote>")
            continue

        if line.strip().startswith("|") and i + 1 < n and re.match(r"^\s*\|?\s*[-:]+[-| :]*\|?\s*$", lines[i + 1]):
            header_raw = [c.strip() for c in line.strip().strip("|").split("|")]
            alignments = []
            sep_cells = [c.strip() for c in lines[i + 1].strip().strip("|").split("|")]
            for sc in sep_cells:
                if sc.startswith(":") and sc.endswith(":"):
                    alignments.append(' style="text-align:center"')
                elif sc.endswith(":"):
                    alignments.append(' style="text-align:right"')
                else:
                    alignments.append("")
            i += 2
            body_rows = []
            while i < n and lines[i].strip().startswith("|"):
                row_cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                body_rows.append(row_cells)
                i += 1

            th_cells = []
            for idx, c in enumerate(header_raw):
                align = alignments[idx] if idx < len(alignments) else ""
                th_cells.append(f"<th{align}>{inline_format(c)}</th>")
            tr_head = f"<tr>{''.join(th_cells)}</tr>"
            tr_body_list = []
            for row in body_rows:
                td_cells = []
                for idx, c in enumerate(row):
                    align = alignments[idx] if idx < len(alignments) else ""
                    td_cells.append(f"<td{align}>{inline_format(c)}</td>")
                tr_body_list.append(f"<tr>{''.join(td_cells)}</tr>")
            tbody_html = "".join(tr_body_list)
            html_out.append(f'<div class="table-scroll"><table><thead>{tr_head}</thead><tbody>{tbody_html}</tbody></table></div>')
            continue

        if re.match(r"^\s*([-*+]|\d+\.)\s+", line):
            list_html, i = parse_lists(lines, i, n)
            html_out.append(list_html)
            continue

        para_lines = []
        while i < n and lines[i].strip():
            if (lines[i].strip().startswith("```") or
                re.match(r"^#{1,6}\s+", lines[i]) or
                re.match(r"^(\*{3,}|-{3,}|_{3,})$", lines[i].strip()) or
                lines[i].startswith(">") or
                lines[i].strip().startswith("|") or
                re.match(r"^\s*([-*+]|\d+\.)\s+", lines[i])):
                break
            para_lines.append(lines[i].strip())
            i += 1
        if para_lines:
            para_content = inline_format(" ".join(para_lines))
            html_out.append(f"<p>{para_content}</p>")

    return "\n".join(html_out)


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
            elif line.strip().startswith("<!--") or line.strip().endswith("-->"):
                continue
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


def inline(text):
    # Split Markdown into text, `code` and [text](url) runs, so the page builds DOM nodes instead of parsing HTML.
    out, pos = [], 0
    for m in re.finditer(r"`([^`]+)`|\[([^\]]+)\]\(([^)\s]+)\)", text):
        if m.start() > pos:
            out.append({"t": text[pos:m.start()]})
        out.append({"code": m.group(1)} if m.group(1) is not None else {"t": m.group(2), "href": m.group(3)})
        pos = m.end()
    if pos < len(text):
        out.append({"t": text[pos:]})
    return out


def read_changelog():
    intro, releases, release, group = [], [], None, None
    for raw in CHANGELOG.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        head = re.match(r"^## (.+)$", line)
        kind = re.match(r"^### (.+)$", line)
        item = re.match(r"^- (.+)$", line)
        if not line or line.startswith("# "):
            continue
        if head:
            title = head.group(1).strip()
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", title):
                raise BuildError(f"CHANGELOG.md: a release heading is the merge date (YYYY-MM-DD), not {title!r}")
            release, group = {"title": title, "groups": []}, None
            releases.append(release)
        elif kind:
            if release is None or kind.group(1) not in CHANGE_KINDS:
                raise BuildError(f"CHANGELOG.md: '### {kind.group(1)}' must sit under a release and be one of {', '.join(CHANGE_KINDS)}")
            group = {"kind": kind.group(1), "items": []}
            release["groups"].append(group)
        elif item and group:
            group["items"].append(item.group(1))
        elif line.startswith("  ") and group and group["items"]:
            group["items"][-1] += " " + line.strip()
        elif release is None:
            intro.append(line)
        else:
            raise BuildError(f"CHANGELOG.md: cannot read line {raw!r}")
    for r in releases:
        for g in r["groups"]:
            g["items"] = [inline(i) for i in g["items"]]
    return {"intro": inline(" ".join(intro)), "releases": releases}


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
    skill_bodies = {s["name"]: s["_body"] for s in skills}
    for s in skills:
        del s["_body"]
    return {
        "name": plugin["name"],
        "version": plugin.get("version", ""),
        "description": plugin["description"],
        "license": plugin.get("license", ""),
        "repo": repo,
        "install": [
            {"id": "tab-claude", "steps": [
                {"note": "Add this repository as a plugin marketplace, then install the plugin:",
                 "commands": [f"claude plugin marketplace add {slug}", f"claude plugin install {plugin['name']}@{plugin['name']}"]},
                {"note": "Configure repository settings in a profile (see Project profile below)."},
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
    }, skill_bodies


def as_json(data):
    return json.dumps(data, ensure_ascii=False, indent=1).replace("</", "<\\/")


def render():
    data, skill_bodies = build_data()
    template = TEMPLATE.read_text(encoding="utf-8")
    if template.count("/*DATA*/") != 1:
        raise BuildError("template.html must contain /*DATA*/ exactly once")
    # The changelog page and skill pages reuse the catalog's stylesheet, so pages cannot drift apart.
    style = re.search(r"<style>\n(.*?)</style>", template, re.S)
    if not style:
        raise BuildError("template.html must contain one <style> block")
    style_css = style.group(1).rstrip()

    changelog_page = CHANGELOG_TEMPLATE.read_text(encoding="utf-8")
    if changelog_page.count("/*STYLE*/") != 1 or changelog_page.count("/*DATA*/") != 1:
        raise BuildError("changelog.html must contain /*STYLE*/ and /*DATA*/ once")
    log = {k: data[k] for k in ("version", "repo", "license")}
    log["changelog"] = read_changelog()

    skill_template = SKILL_TEMPLATE.read_text(encoding="utf-8")
    if skill_template.count("/*STYLE*/") != 1:
        raise BuildError("skill_template.html must contain /*STYLE*/ exactly once")
    skill_base = skill_template.replace("/*STYLE*/", style_css)

    blob = data["repo"] + "/blob/main/"
    cat_by_skill = {name: c["name"] for c in data["categories"] for name in c["skills"]}

    files = {
        "index.html": template.replace("/*DATA*/", as_json(data)),
        "changelog.html": changelog_page.replace("/*STYLE*/", style_css).replace("/*DATA*/", as_json(log)),
        ".nojekyll": "",
    }

    for s in data["skills"]:
        name = s["name"]
        cat_name = cat_by_skill.get(name, "")
        badges = [f'<span class="badge gold">{html.escape(cat_name)}</span>']
        if s["user_only"]:
            badges.append('<span class="badge user">User-only</span>')
        if s["tools"] is None:
            badges.append('<span class="badge">All tools</span>')
        elif s["writes"]:
            badges.append('<span class="badge">Edits files</span>')
        else:
            badges.append('<span class="badge ro">Read-only tools</span>')
        if s["uses_agents"]:
            badges.append('<span class="badge gold">Uses subagents</span>')
        for x in s["extras"]:
            badges.append(f'<span class="badge gold">+ {html.escape(x)}/</span>')

        tools_html = ""
        if s["tools"]:
            tools_tags = " ".join(f"<code>{html.escape(t)}</code>" for t in s["tools"])
            tools_html = f'<div class="meta-tools"><span class="meta-label">Allowed tools</span> {tools_tags}</div>'

        meta_card = (
            '<article class="meta-card">\n'
            '  <div class="meta-head">\n'
            f'    <h1 class="meta-title">/ai-toolbox:{html.escape(name)}</h1>\n'
            f'    <div class="badges">{"".join(badges)}</div>\n'
            '  </div>\n'
            f'  <p class="meta-desc">{html.escape(s["description"])}</p>\n'
            + (f'  {tools_html}\n' if tools_html else '') +
            '  <div class="meta-foot">\n'
            f'    <a href="{blob + s["path"]}">Claude source</a>\n'
            f'    <a href="{blob + s["agy_path"]}">Antigravity copy</a>\n'
            '  </div>\n'
            '</article>'
        )

        body_html = markdown_to_html(skill_bodies.get(name, ""))

        page = skill_base
        page = page.replace("/*NAME*/", html.escape(name))
        page = page.replace("/*DESCRIPTION_ATTR*/", html.escape(s["summary"]))
        page = page.replace("/*CATEGORY*/", html.escape(cat_name))
        page = page.replace("/*METADATA_CARD*/", meta_card)
        page = page.replace("/*BODY*/", body_html)
        page = page.replace("/*REL_PATH*/", html.escape(s["path"]))
        page = page.replace("/*LICENSE*/", html.escape(data.get("license", "")))

        files[f"skills/{name}.html"] = page

    return files


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
        dest = OUT / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
    skill_count = len([k for k in files if k.startswith("skills/")])
    print(f"wrote {OUT.relative_to(ROOT)}/index.html, changelog.html, and {skill_count} skill pages")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
