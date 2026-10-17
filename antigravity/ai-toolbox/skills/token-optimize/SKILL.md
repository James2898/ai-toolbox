---
name: token-optimize
description: "User-only: run only when the user types /token-optimize. Audit and compress prompt-like files — SKILL.md skills, agent definitions, CLAUDE.md and rules files, slash commands, system prompts — to cut tokens without changing behavior. Measures each file (chars, lines, estimated tokens, how much of it is always-loaded description), names the padding it found (filler, repeated rules, prose that should be a table, shouting caps), proposes a compressed rewrite as a diff, and proves every flag, path, command, gate and output contract survived. Dry-run by default; writes only after the user approves the diff. Use whenever the user wants a skill, prompt or agent \"shorter\", \"leaner\", \"cheaper\", asks how many tokens a skill costs, says context is getting bloated, or wants to review the size of a skills folder or .claude/."
---

> **Running in Antigravity**: this skill is generated from the Claude Code source.
> - User-only skill (Claude Code: disable-model-invocation). Start it only when the user typed its slash command; never on your own initiative.
> - `ask_question` is Antigravity's interactive question tool (Claude Code: AskUserQuestion).
> - `ARGS` means whatever the user typed after `/<this-skill>`, or the request that triggered it.

# Token Optimize

Compress instruction files without changing what they make the model do.

Why this matters: a skill's `description` is loaded into **every** session, and its body is loaded every time it triggers. Each wasted token is paid hundreds of times. But a compression that silently drops a flag, a path or a confirmation gate breaks the skill in a way nobody notices until it misfires. So the job is two-sided: cut hard, and prove nothing load-bearing was cut.
## Inputs

Parse `ARGS`:

| Argument | Meaning | Default |
|---|---|---|
| `<target>` | File or directory to audit (a skills folder, an agents folder, `.claude/`, a single `SKILL.md`) | ask with `ask_question` |
| `--only=<glob>` | Restrict a directory audit (e.g. `--only='pr-*'`) | all `*.md` |
| `--budget=<n>` | Target max estimated tokens per file; files over it are ranked first | none |
| `--apply` | Allow writing the compressed files — still only after the user approves each diff | off (dry run) |
| `--format=text\|json` | Report format | `text` |

Never write anything without `--apply` **and** an explicit yes on the shown diff. Skill and agent files shape every future session; never edit them without the user's approval.

## Step 1 — Measure

Run the bundled script (read-only). It prints one row per file: chars, lines, estimated tokens (chars ÷ 4, a ±20 % heuristic), the description's own token share, and heuristic flags.

```bash
python3 -I <this skill's folder>/scripts/token_report.py <target> [--only '<glob>'] [--json]
```

Rank by estimated tokens (or by overshoot when `--budget` is set). Say which files are worth touching and which are already lean; do not "optimize" a 40-line file for a 5 % gain.

## Step 2 — Find what is padding and what is load-bearing

Read each candidate file in full. Classify every passage.

**Padding (safe to cut or compress)**

- Throat-clearing and narration: "This skill will help you…", "Let's begin by…", restating the title.
- A rule stated twice in different words. Keep the clearest statement once; delete the echo.
- Prose that enumerates options, columns or steps. Turn it into a table or a numbered list.
- Illustrative examples beyond the first one that teaches something new.
- Headings that only announce the next heading.
- Justifications longer than the rule they justify, **unless** the why is what makes the model apply the rule sensibly in unseen cases. Keep short whys; cut essays.
- `MUST` / `NEVER` / `ALWAYS` in caps. Write the rule plainly and say why; caps add tokens, not compliance.

**Load-bearing (keep verbatim)**

- Frontmatter `name`; the `description` is the trigger surface — do not shorten it unless the user asked for description work specifically. Flag it; do not touch it.
- Every CLI argument, flag and default value; every file path, directory, URL, command line and tool name.
- Every confirmation gate, stop condition, "never do X" safety line, and every numeric limit.
- Every output template, table header, ID scheme and fenced format block — downstream skills parse these.
- Deference lines ("format X wins", "defer to skill Y") and references to other skills, memories or docs.
- Labels like unverified / (inferred) or a project's own uncertainty markers — they are contract, not filler.

## Step 3 — Rewrite

Produce the compressed version in a scratch location (for example the user's scratchpad or `/tmp/token-optimize/<name>.md`), not in place.

Style rules for the rewrite:
- Imperative, telegraphic sentences. One idea per line.
- Static, invariant sections first; dynamic or example material last (this also helps prompt caching).
- Replace duplicated universal rules with one reference to where the rule lives (CLAUDE.md, a rules file, a sibling skill).
- Keep identical wording for anything that appears in several skills on purpose (shared headers, shared format blocks) so they stay in sync.

## Step 4 — Prove nothing broke

Run the invariant check. It extracts backtick spans, `--flags`, paths, commands and gate/safety lines from the original and reports any that are missing from the rewrite.

```bash
python3 -I <this skill's folder>/scripts/token_report.py --check <original> <rewrite>
```

A non-empty "missing" list is a stop: either restore the item or state in the report why dropping it is intended (for example, a duplicate of a line that is still present). Also re-check by eye:
- frontmatter still parses (`---` fences, same keys);
- every numbered step still exists in the same order;
- the output template is byte-identical unless the user asked to change it.

## Step 5 — Report, then ask

Print the report (schema below) and the unified diff for each file. If `--apply` was given, ask once per file with `ask_question`: apply / skip / edit further. Apply only on yes, and only to that file. Without `--apply`, end at the report and say how to apply.

## Report schema

Text:

```
=== Token Optimization Report ===
Target: <path>
Files audited: <n>   Files proposed: <m>

<file>
  Before: <chars> chars / <lines> lines / ~<tokens> tokens (description ~<d> tokens, always loaded)
  After:  <chars> chars / <lines> lines / ~<tokens> tokens   Saved: <n> tokens (<pct>%)
  Cuts:   <one line per category, e.g. "filler x4, duplicated rule x2, prose→table x1">
  Kept:   description untouched; <k> flags, <p> paths, <g> gates verified present
  Invariants: PASS | FAIL (<what is missing>)
  Status: dry-run | applied | skipped
```

JSON (`--format=json`): one object per file with the same fields in snake_case plus `diff_path`.

## Done when

- Every candidate file has a measured before/after and an invariant verdict.
- No `description` was changed unless the user asked for that.
- Nothing was written to the original paths without `--apply` and a yes.
- Savings under ~15 % are reported as "already lean" rather than applied — churn in a durable file is a cost too.
