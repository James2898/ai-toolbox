# ai-toolbox

Skills, specialist agents, rules, and hooks for software engineering workflows, packaged for **Claude Code** and **Google Antigravity** from one source.

**Interactive Catalog:** <https://james2898.github.io/ai-toolbox/>  
Browse and search all 42 skills, 13 specialist agents, multi-agent workflow diagrams, and hook specifications. Release notes are in the [Changelog](https://james2898.github.io/ai-toolbox/changelog.html).

## What is inside

- **42 Skills:** QA test planning, Playwright live DOM verification, bug reproduction loops, code health audits, PR reviews, and plain-language explanations.
- **13 Specialist Agents:** Autonomous subagents routed by `@project-manager` across Tier 0 (direct), Tier 1 (standard), and Tier 2 (complex fullstack) workflows.
- **Rules & Guardrails:** Lean change enforcement (minimal diffs, no unneeded abstractions) and strict agent role boundaries.
- **Safety Hooks:** Guardrails preventing unintended large terminal writes, staging mistakes, and uncleaned worktrees.

Full arguments, sample inputs, and usage details for every tool are documented on the [catalog site](https://james2898.github.io/ai-toolbox/).

## Installation

### Claude Code

```bash
claude plugin marketplace add James2898/ai-toolbox
claude plugin install ai-toolbox@ai-toolbox
```

Update to the latest commit anytime:

```bash
claude plugin update ai-toolbox@ai-toolbox
```

### Google Antigravity

Link the built plugin into your Antigravity plugins directory:

```bash
# Linux / macOS
python3 tools/build_antigravity.py --link

# Windows
py -3 tools/build_antigravity.py --link
```

Alternatively, copy `antigravity/ai-toolbox` into `~/.gemini/config/plugins/ai-toolbox` and restart Antigravity.

## Project profiles

Skills read repository settings (test commands, base branches, dev URLs, documentation folders) from a profile instead of hardcoding them:

1. `AI_TOOLBOX_PROFILE` environment variable path,
2. `<project root>/.ai-toolbox/profile.yml`, or
3. Interactive detection prompts when unset.

Copy [`profiles/example.yml`](profiles/example.yml) to configure your project.

## Repository layout

```
ai-toolbox/
├── .claude-plugin/marketplace.json   marketplace registration for Claude Code
├── claude/                           source of truth: edit skills, agents, rules, and hooks here
│   ├── .claude-plugin/plugin.json
│   ├── skills/<name>/SKILL.md
│   ├── agents/<name>.md
│   ├── rules/
│   └── hooks/
├── antigravity/ai-toolbox/           generated Antigravity plugin (do not edit directly)
├── docs/                             generated catalog site for GitHub Pages (do not edit directly)
├── CHANGELOG.md                      source release notes (rendered as docs/changelog.html)
├── profiles/example.yml              annotated template for project profiles
└── tools/
    ├── build_antigravity.py          compiles claude/ -> antigravity/
    ├── build_site.py                 compiles claude/ -> docs/ (index.html and changelog.html)
    ├── leak_check.py                 pre-commit scanner for private paths and secrets
    └── site_categories.yml           category mapping for catalog site navigation
```

## Contributing

1. **Edit under `claude/` only.** Never edit `antigravity/` or `docs/` directly.
2. **Rebuild targets:** run `python3 -I tools/build_antigravity.py` and `python3 -I tools/build_site.py`.
3. **Scan for leaks:** run `python3 -I tools/leak_check.py --staged` before committing.
4. **Target `develop` for pull requests:** open PRs against `develop` (`gh pr create --base develop`).
5. **Dry-run skill changes:** verify new or updated skills in a test repo before opening a PR.

## License

[MIT](LICENSE)
