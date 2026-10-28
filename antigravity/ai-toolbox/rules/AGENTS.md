# Agent Routing Rules

> These rules apply globally to all projects using the multi-agent workflow.
> Projects may extend these rules by adding project-specific rules in their own `.claude/rules/` directory.

These rules are auto-loaded alongside CLAUDE.md and apply to every session. They cover failure modes and process guards for the multi-agent workflow.

---

## PM Must Not Implement

The `@project-manager` is a router, not an implementer. It must never:
- Write, edit, or create any code or implementation files
- Perform the work of a specialist agent inline
- Skip using the `Agent` tool to delegate to the next agent in the chain

Every agent in the tier chain **must** be invoked via the `Agent` tool. The user invokes `@project-manager` once — the PM orchestrates the full chain automatically without requiring the user to call each agent manually.

If the PM produces anything other than the Handoff Trio and an `Agent` tool call, it has overstepped its role.

---

## Missing Agent Files

If an agent in the Agent Registry has Status = **Placeholder** (its `.md` file does not exist yet), **stop and tell the user** rather than inferring or inventing its behavior. Do not guess what the agent would do.

## Skip Logic Guard

You may only skip an agent if the user explicitly approves it in the task prompt.

- **Never skip `@task-logger`** for Tier 1 or Tier 2 tasks without explicit user approval.
- **Never skip `@integration-contract`** for Tier 2 tasks without explicit user approval.

## Token Discipline

Keep agent handoffs token-light. Pass the **Handoff Trio** only:
- Task ID (or "pending")
- Relevant file paths (specific, not vague)
- Last decision (one sentence)

Do not re-summarize the full conversation history in each handoff.

## Gap-Handling Default

When a backend endpoint is marked `MISSING`:
- Disable the relevant UI controls.
- Show an explanatory hint to the user (not a silent failure).
- Never silently mock an endpoint or fabricate a response without logging it in the integration contract doc.

**All-MISSING escalation:** If `@integration-contract` marks 50% or more of the required endpoints as `MISSING`, do not proceed to `@task-logger`. Stop and notify the user with the full list of missing endpoints and ask whether to: (a) proceed with fully disabled UI, (b) request backend work first, or (c) reduce scope.

## Post-Validation Loop (BLOCKED verdict)

When `@validator-agent` issues a **BLOCKED** verdict, the orchestration must not stop. The PM must automatically continue the chain:

1. Invoke `@fullstack-developer` with the blocker list from the validator report as the task input.
2. After `@fullstack-developer` completes, invoke `@validator-agent` again for a re-audit.
3. Repeat until `@validator-agent` issues **APPROVED** or **APPROVED WITH CONDITIONS**.
4. Only surface to the user if:
   - The same blocker reappears after 2 fix attempts (likely a design conflict — needs human decision)
   - `@fullstack-developer` cannot resolve a blocker without architectural changes outside the current task scope

Do not ask the user to trigger the fix loop manually — it runs automatically as part of the chain.

---

## Requirements Blocking Questions

When `@requirements-engineer` surfaces an Open Question it cannot resolve from context:
1. It must pause the chain and notify the user explicitly with the blocking question(s).
2. The PM resumes the chain only after the user provides answers.
3. `@requirements-engineer` re-runs with the answers and produces the Feature Specification.
4. Do not proceed to `@task-logger` until the Feature Specification has no Open Questions remaining.

---

## Release Manager Retry Limit

When `@release-manager` sends NEEDS CHANGES back to `@fullstack-developer`:
1. Track the retry count per failing criterion.
2. If the same criterion FAILs twice in a row after fixes, stop and surface to the user — do not loop again.
3. Include: the criterion text, both fix attempts, and why they are still failing.

---

## Ambiguous Requests

If a request is ambiguous, route through `@project-manager` → `@requirements-engineer`. Do not guess intent.

## Unknown Tech Stack

If the tech stack for a given layer is still TBD, do not assume a framework or library. Check `docs/tech-stack.md` first, then ask the user or route through `@requirements-engineer`.

---

## Headless Shells, Interactive Commands & Token Loop Guard

- **No Interactive Auth or Terminal Input Commands**: Never execute commands that prompt for interactive credentials (e.g., `git push`, `gh auth login`, `ssh` without key) unless credentials/tokens are pre-verified. Always prefer non-interactive flags (e.g., `CI=true`, `PIP_NO_INPUT=1`, `npm --yes`).
- **Reactive Wakeup Over Active Polling (Long-Running Tasks)**:
  - For naturally slow commands (e.g., package installation, build, test suites), use higher synchronous wait limits or let the task run in the background and rely on the platform's **reactive completion notification**. Do **not** actively poll `manage_task` or read terminal buffers in a loop.
- **Strict Stalling & Retry Cap (Max 1 Retry)**:
  - If a background command stalls waiting for interactive input, hangs unexpectedly, or fails on missing credentials:
    1. Check status / retry at most **once**.
    2. If still unresolvable or blocked on credentials/input, **immediately terminate the task**.
    3. Surface the exact command to the user to execute directly in their interactive terminal.
- **Token Loop Prevention**: In sessions with large active context windows (100k+ tokens), repetitive polling loops re-read the entire context on every turn, rapidly burning millions of tokens in minutes.
- **Windows CLI Tool Paths**: When tools like `gh` are not found on the default session `$env:PATH`, inspect standard locations (e.g., `C:\Program Files\GitHub CLI\gh.exe`) before assuming they are missing.

---

## Git Operations Approval

Never create a new git branch (`git checkout -b`, `git branch`) or commit changes (`git commit`) autonomously without explicit user approval. Always present the proposed branch name, staged diff/changes, and commit message to the user, and wait for confirmation before executing.

---

## Subagent Model Tiers & Tool Guardrail Preservation

When configuring, modifying, or compiling subagents across platforms:
1. **Never Strip Model Tiers**: Per-agent model specializations (`sonnet`/`pro` for architecture and validation; `haiku`/`flash` for scripters and loggers) are deliberate architectural choices for performance and cost. Map models across platforms instead of removing them.
2. **Never Strip Tool Guardrails**: Tool restrictions (`read_file` only vs write-enabled vs prompt-only) enforce least-privilege security boundaries. Map Claude tools to platform-native tools rather than giving all agents full system access.

---

## Antigravity Local Plugin Discovery (Windows)

When deploying or linking local plugins on Windows (`~/.gemini/config/plugins/<name>`):
- **Never Use Directory Junctions (`mklink /J`)**: Antigravity's Go Language Server discovers plugins via `filepath.Walk`, which treats Windows directory junctions as reparse points and skips them without following, causing plugins to disappear from discovery.
- **Direct Copy Required**: On Windows, always copy the directory contents directly (`shutil.copytree`) instead of creating an NTFS junction.

---

# Lean Change Rules

> Applies whenever you write or change code, in the main session and in agents that implement (such as `@fullstack-developer`). It does not apply to writing QA documents, specs, PBI analyses, explanations or prose.

Make the smallest change that fully solves the task. Code that was never written has no bugs, needs no review and never has to be migrated. Being lazy about the solution never means being lazy about the change: every part the task needs gets done.

---

## Before you write

Read the task and the code it touches. List every place the change has to reach: callers, tests, fixtures, config, exports, translation keys, sibling screens that share the code. Check what users could lose: data destroyed or exposed, callers that stop working. That list is the scope. Features nobody asked for are not. When the code cannot show something the change depends on (an untyped response, a value from outside the repo), write down the assumption and name it in the closing line.

In an agent chain, the reuse list is already in `codebase-explorer`'s **Reuse Candidates** (`tasks/TASK-NNN/context.md`). Read it there instead of searching again.

## The ladder

Take the first option that fully works:

1. **Does it need to exist?** Skip features, options and flexibility nobody asked for, and name what you skipped in one line. A vague request gets the smallest version that does the core job.
2. **Is it already in this codebase?** A helper, component, service or pattern. Use it the way the code around it does. When two copies exist, use the one the surrounding code already imports, else the one in the shared layer (`lib`, `utils`, `common`), and name the other copy in one line instead of merging it unasked.
3. **Does the standard library or the platform do it?** Use that, unless the project has its own version. A house component beats a native widget.
4. **Does an installed dependency do it?** Use it. A **new** dependency needs the user's approval. Even when the user offers one ("feel free to add X"), say first when a few lines or something already installed does the job, and add it only if they still want it.
5. **Can it be one line a reader understands at a glance?** Write one line.
6. **Otherwise,** write the minimum code that works.

## While you write

- No abstraction, wrapper, option, config, type conversion or "for later" code that nothing needs today. A new layer needs two real callers now, not one caller and a guess.
- Keep the structure the codebase already has: its layers, interfaces and naming.
- Deleting beats adding. The shortest working diff wins, once you know everything it must touch. A one-liner that needs decoding is not short.
- Comment only the why the code cannot show, in one line.
- Bug fix: grep every caller of the function before editing it, then fix the root cause once, in the shared code.
- Code you move or merge keeps its validation and error handling.
- Between options of the same size, take the one that is correct on edge cases.
- New logic with a branch, a loop, a parser, money or auth gets one small test, run with the project's test command. A trivial change needs none.
- A shortcut with a known limit gets a comment in this exact form, so `/code-debt` can list it later:
  `shortcut: <the limit>, <when to upgrade>`

## Never cut

- Validation at trust boundaries
- Error handling that prevents data loss
- Security and permission checks
- Accessibility
- Anything an acceptance criterion or the user asked for

## When part of the request looks unjustified

Say so in one line, with the smaller alternative. When the smaller option still gives the user everything they asked for, build it and name the bigger one; when it would leave out something they asked for, ask before building. For PBI-sized work, point to `/design-grill` (is the request clear?) or `/code-grill` (is this the right way to build it?) instead of arguing inline.

## Closing line

End a coding reply with one line: what you skipped or did not check, and any risk the user must know. When `action-first` is on, put that line in its state restatement instead of adding a closer.

## Precedence

CLAUDE.md, the task file's acceptance criteria and Out of Scope, project rules, and an invoked skill's own output format all outrank this file. Where they say more, do more. A plan written in a task file is input to this ladder, not a rule above it. When the user's request in chat and an acceptance criterion disagree, ask which wins instead of picking one.

---

Adapted from [ponytail](https://github.com/DietrichGebert/ponytail) v5.3.2 by Dietrich Gebert (MIT License). The wording, the scope line, the agent-chain hooks and the precedence rules are this toolbox's own.
