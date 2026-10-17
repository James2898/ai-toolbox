---
name: retro
description: "Look back at a working session and turn its friction into ranked, concrete improvements to your setup: a memory entry, a skill or agent edit, a project rule, a hook, a permission, or a profile key. Each item cites what happened in the session, says where the change goes and shows the exact text, with a rating and effort. Proposes only; applies nothing until you pick."
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - AskUserQuestion
user-invocable: true
disable-model-invocation: true
---

# retro — fix the setup, not just the session

A session's mistakes repeat until something in the setup changes: a memory the next session reads, a skill step, a rule, a hook. This skill finds the moments that cost time and proposes the smallest durable change for each.

## Arguments

| Argument | Meaning |
|---|---|
| (none) | review the current conversation |
| `<transcript path>` | review a saved session transcript instead (for Claude Code, a `.jsonl` file under `~/.claude/projects/<project>/`) |
| `--focus=<topic>` | look only at one area, such as git, tests or a named skill |

## Project settings

Reads the project profile (`AI_TOOLBOX_PROFILE`, else `<project root>/.ai-toolbox/profile.yml`): `docs.memory_dir` is where lessons live. Without it, use the tool's own memory folder if one exists, or say there is none.

## Steps

### 1. Find the friction

Go through the session in order and list each moment that cost a turn or more. For a transcript file, `grep` for the signals instead of reading it whole.

| Signal | Example |
|---|---|
| User correction | "no, that's not what I meant", a rejected tool call, a re-asked question |
| Blocked action | permission denied, a hook blocked a command, a sandbox refusal |
| Retry | the same command or edit tried more than once |
| Wrong claim | something stated as fact, then shown wrong |
| Missing context | a fact the session had to rediscover that an earlier session already knew |
| Skill mismatch | a skill that didn't trigger, triggered wrongly, or whose step didn't fit |

For each: what happened (a short quote or the command), turns lost, and the root cause in one line.

Done when: each friction moment has a cause, or the session had none worth fixing (say so and stop).

### 2. Pick the smallest durable fix

Match each cause to where a fix would have prevented it:

| Cause | Fix lives in |
|---|---|
| A fact about the user, project or team the session lacked | memory entry |
| A skill step that was missing, wrong or ambiguous | that skill's `SKILL.md` |
| A convention the code follows but nothing states | project rule file (`CLAUDE.md`, `AGENTS.md`, `.claude/rules/`) |
| A check that prose kept failing to enforce | hook |
| A safe command that kept asking for permission | permission allow-list |
| A project value a skill had to ask for | profile key |

Before proposing a memory entry, grep `{memory_dir}` for an existing one: update it rather than adding a duplicate. Before proposing a skill edit, read the current step; the fix may belong one step earlier.

Done when: each cause has one proposed fix with its target file.

### 3. Rank and present

Before the table, re-check each finding's evidence with a command: a claim that something is missing needs a search of the whole repo or plugin, not one folder. Correct or drop any finding that fails the check.

```markdown
## Retro — <session topic> (<YYYY-MM-DD>)

| # | ⭐ | Effort | Friction (evidence) | Fix | Where |
|---|---|---|---|---|---|
| 1 | ⭐⭐⭐⭐⭐ | S | <quote or command; turns lost> | <one line> | <file> |

### 1. <fix title>
<the exact text, diff or setting to add>
```

Rank by turns it would save across future sessions times how often the cause recurs. Rate each ⭐1–5 with a one-line reason. Leave out fixes for one-off accidents.

Then ask which to apply, with one multi-select question.

### 4. Apply only what was picked

- Memory: write or update the entry and its index line.
- Skills, agents, rules, hooks, permissions: show the diff first and apply after the user confirms that diff; these change how every future session behaves.
- Report what was applied, and which items were left for later.

## Boundaries

Quote only what is needed to show the friction. Leave out secrets, tokens and personal data from the session, and colleagues' names from anything written to a shared file.
