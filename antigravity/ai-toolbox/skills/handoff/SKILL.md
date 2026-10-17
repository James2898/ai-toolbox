---
name: handoff
description: "Write a handoff file so a fresh session, another agent, or another tool (Claude Code or Antigravity) can continue the current work without the conversation: goal, verified state (branch, HEAD, uncommitted files), what is done and how it was verified, decisions with reasons, open questions, and the exact next steps. With --resume, read the latest handoff and check the repo still matches it before continuing. Use when the user says hand off, write a handoff, save progress, pick this up later or in another session, or when context is running long."
---
# handoff — leave work so someone cold can pick it up

The next reader has none of this conversation. A handoff gives them the facts they can't rediscover cheaply: why things were decided, what was verified and how, and where to start. Anything they could read from the code or git log is a pointer, not a copy.

## Arguments

| Argument | Meaning |
|---|---|
| (none) | write a handoff for the current work |
| `--resume[=<file>]` | read the latest (or named) handoff, verify it, and continue |
| `--to=<who>` | a note on who picks it up (a session, a teammate, Antigravity), which shapes how much tool-specific detail to spell out |

## Project settings

Reads the project profile (`AI_TOOLBOX_PROFILE`, else `<project root>/.ai-toolbox/profile.yml`): `docs.handoff_dir`, default `.ai-toolbox/handoffs`.

## Write

### 1. Capture the state from commands, not memory

Run and record: `git branch --show-current`, `git rev-parse --short HEAD`, `git status --short`, `git log --oneline <base>..HEAD`, and the open PR if any (`gh pr view --json number,url,state`). Note running servers or containers the work depends on.

### 2. Write the file

`{handoff_dir}/<YYYY-MM-DD>-<slug>.md`:

```markdown
# Handoff — <task in one line>   (<YYYY-MM-DD HH:MM>)

## Goal
<What the user asked for, in their words where possible, and what "done" means.>

## State
- Repo / branch / HEAD: <repo> / <branch> / <sha>
- Uncommitted: <files, or none>
- PR: <link or none>   · Pushed: yes/no

## Done (and how it was verified)
- <item> — verified by `<command>` → <result>
- <item> — NOT verified: <why>

## Decisions
- <decision> — because <reason>; rejected <alternative> because <reason>

## Open questions
- <question> — waiting on <who>

## Next steps
1. <step> — `<command or file>`
2. …

## Watch out for
- <trap, rule or permission limit that bit this session>

## Pointers
- <files, docs, loop files, reports worth reading first>
```

Rules for the content:

- Every "done" line says how it was verified, or says it was not.
- Next steps are concrete enough to run without asking: a command, a file, a skill name.
- No secrets, tokens, personal data or private hostnames; the file may be read by another tool.
- Under about 80 lines; link to longer reports instead of pasting them.

Make sure git ignores the folder: if `git check-ignore -q {handoff_dir}/x` fails, add the folder to `$(git rev-parse --git-common-dir)/info/exclude` and say so.

Done when: the file exists, is ignored by git, and its State section matches the commands' output.

## Resume (`--resume`)

1. Read the newest file in `{handoff_dir}` (or the named one).
2. Compare its State with the repo now: branch, HEAD, uncommitted files, PR state. Report each difference; if HEAD moved, list the new commits.
3. Re-run one "verified by" command from the Done list that is cheap, to confirm the state still holds.
4. Restate the goal and the first next step, then continue with it unless a difference from step 2 changes the plan; in that case ask first.
