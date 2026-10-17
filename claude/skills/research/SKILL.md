---
name: research
description: "Answer a technical question from primary sources and save a cited note: the project's own code and docs at file:line, official docs, specs and changelogs for the exact version the project pins, and the library's source; blogs and forum answers only as leads. Every claim carries its source and version, conflicts are shown, and anything unchecked is marked unverified. Use when the user asks to research, look up or confirm how a library, API, tool or standard behaves, compare options with evidence, or check whether something is still true for their version."
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
  - Write
  - WebSearch
  - WebFetch
  - Agent
user-invocable: true
---

# research — primary sources, cited, for your version

A research note is only as good as its weakest citation. The common failure is a confident answer built from a blog post about a different major version. This skill pins the version first, then reads the source that actually decides the behaviour.

## Arguments

| Argument | Meaning |
|---|---|
| question | what to find out, in one or two sentences |
| `--save` / `--no-save` | write the note (default: save when the answer has three or more findings) |
| `--depth=quick\|full` | `quick` stops at the first primary source that settles it; `full` (default) checks every source rung |

## Project settings

Reads the project profile (`AI_TOOLBOX_PROFILE`, else `<project root>/.ai-toolbox/profile.yml`): `docs.research_dir`, default `.ai-toolbox/research`.

## Steps

### 1. Frame the question

Write: the question, **what answer would settle it** (a behaviour, a yes/no, a number, a recommendation), and the versions in play. Read the pinned versions from the lock files and build files (`package-lock.json`, `go.mod`/`go.sum`, `pyproject.toml`, `Gemfile.lock`, Docker images). Split a broad question into two to four sub-questions that can be answered separately.

Done when: the question, the settling criterion and the pinned versions are written.

### 2. Read sources in this order

1. **The project itself**: how the code uses the thing today (`grep`), its docs, ADRs and rules. Cite `file:line`.
2. **Official, version-matched**: the reference docs, spec or RFC, release notes and changelog entries between the pinned version and the latest.
3. **The library's source at the pinned version**: `node_modules/<pkg>`, the Go module cache, site-packages, or the tagged source on the repository host. Source beats docs when they disagree; say so.
4. **Issue trackers and PRs** of the project that owns it: known bugs, behaviour changes, maintainers' statements.
5. **Secondary** (blogs, Q&A sites, videos): leads only. A claim that rests on them alone is marked unverified.

For independent sub-questions, run them in parallel with sub-agents and give each the version list. Never put internal code, hostnames, customer data or credentials into a web search or fetch; describe the behaviour generically instead.

Done when: every sub-question has at least one primary source, or is marked unanswered with what was tried.

### 3. Check the findings against each other

- Version: does each source apply to the pinned version? A source for another major version is a lead, not evidence.
- Conflicts: when sources disagree, show both, say which wins and why (source code over docs, newer changelog over older docs).
- Run it, when cheap: a short script or test at the pinned version settles behaviour better than any page. Paste the command and output.

Done when: each claim is labelled verified (primary source or run), inferred, or unverified.

### 4. Answer, then save

Lead with the answer in two to four sentences, then the findings table. Save to `{research_dir}/<YYYY-MM-DD>-<slug>.md` when `--save`, or by default when there are three or more findings:

```markdown
# <question>   (<YYYY-MM-DD>, versions: <pkg@x.y>, …)

## Answer
<two to four sentences; recommendation if one was asked for>

## Findings
| # | Claim | Source | Applies to version | Status |
|---|---|---|---|---|
| 1 | … | <URL or file:line> | x.y | verified / inferred / unverified |

## Conflicts
- <source A says … ; source B says … ; B wins because …>

## Open
- <what is still unknown and the one check that would settle it>

## Re-check
- <command, link or file to look at when the version changes>
```

Make sure git ignores the folder: if `git check-ignore -q {research_dir}/x` fails, add it to `$(git rev-parse --git-common-dir)/info/exclude` and say so.

## Boundaries

Quote at most a short phrase from any page; summarise in your own words and link. Never present an unverified claim without its label.
