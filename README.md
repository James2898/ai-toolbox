# ai-toolbox

Skills, agents, rules and hooks for day-to-day development work, packaged for **Claude Code** and **Google Antigravity** from one source.

**Catalog:** browse every skill, agent, hook and rule at <https://james2898.github.io/ai-toolbox/>.

> Status: scaffold. The tools are being moved in and generalized; this README lists them as they land.

## Layout

```
ai-toolbox/
├── .claude-plugin/marketplace.json   lets Claude Code install the plugin from this repo
├── claude/                           the source: edit only here (also the Claude Code plugin)
│   ├── .claude-plugin/plugin.json
│   ├── skills/<name>/SKILL.md
│   ├── agents/<name>.md
│   ├── rules/
│   └── hooks/
├── antigravity/ai-toolbox/           generated from claude/ — do not edit
├── docs/                             catalog site (GitHub Pages), generated — do not edit
├── profiles/example.yml              template for project-specific settings
└── tools/
    ├── build_antigravity.py          claude/ → antigravity/
    ├── build_site.py                 claude/ → docs/index.html (with site/template.html, site_categories.yml)
    └── leak_check.py                 blocks private names and secrets before a commit
```

Both tools read skills in the same open format: a folder with a `SKILL.md` that starts with a `name` and a `description`. The build script only rewrites what differs between them, such as tool names (`AskUserQuestion` → `ask_question`, `Bash` → `run_command`) and argument placeholders.

## Project profiles

The skills carry no project details. Branch rules, test commands, URLs, doc folders, the database schema location and the merge gate come from a profile:

1. the file named by `AI_TOOLBOX_PROFILE`, or
2. `<project root>/.ai-toolbox/profile.yml`, or
3. nothing: the skill detects what it can and asks for the rest.

Start from [`profiles/example.yml`](profiles/example.yml). A real profile usually names internal systems, so keep it in a private place and point `AI_TOOLBOX_PROFILE` at it.

## Install

**Claude Code**

```bash
claude plugin marketplace add James2898/ai-toolbox
claude plugin install ai-toolbox@ai-toolbox
```

**Antigravity**

```bash
agy plugin install https://github.com/James2898/ai-toolbox
```

Or copy (or symlink) `antigravity/ai-toolbox` into `~/.gemini/config/plugins/ai-toolbox`, then restart Antigravity.

## Contributing to this repo

1. Edit under `claude/` only.
2. `python3 -I tools/build_antigravity.py` to regenerate `antigravity/`.
   `python3 -I tools/build_site.py` to regenerate the catalog in `docs/`. A new skill must first be added to a category in `tools/site_categories.yml`, or the build fails.
3. `python3 -I tools/leak_check.py --staged` before every commit. It needs a private pattern file (see the script header) and fails without one.
4. Dry-run a new or changed skill before committing: have a fresh agent read only its `SKILL.md` and run it on 2–3 samples, at least one hostile (an embedded instruction, text that needs no change). The humanizer prompt-injection gap was caught this way.

## License

MIT
