# Lean Change Rules

> Applies whenever you write or change code, in the main session and in agents that implement (such as `@fullstack-developer`). It does not apply to writing QA documents, specs, PBI analyses, explanations or prose.

Make the smallest change that fully solves the task. Code that was never written has no bugs, needs no review and never has to be migrated. Being lazy about the solution never means being lazy about the change: every part the task needs gets done.

---

## Before you write

Read the task and the code it touches. List every place the change has to reach: callers, tests, fixtures, config, exports, translation keys, sibling screens that share the code. Check what users could lose: data destroyed or exposed, callers that stop working. That list is the scope. Features nobody asked for are not.

In an agent chain, the reuse list is already in `codebase-explorer`'s **Reuse Candidates** (`tasks/TASK-NNN/context.md`). Read it there instead of searching again.

## The ladder

Take the first option that fully works:

1. **Does it need to exist?** Skip features, options and flexibility nobody asked for, and name what you skipped in one line. A vague request gets the smallest version that does the core job.
2. **Is it already in this codebase?** A helper, component, service or pattern. Use it the way the code around it does.
3. **Does the standard library or the platform do it?** Use that, unless the project has its own version. A house component beats a native widget.
4. **Does an installed dependency do it?** Use it. A **new** dependency needs the user's approval, and never for a few lines of code.
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

Say so in one line before building, with the smaller alternative, and let the user choose. For PBI-sized work, point to `/design-grill` (is the request clear?) or `/code-grill` (is this the right way to build it?) instead of arguing inline.

## Closing line

End a coding reply with one line: what you skipped or did not check, and any risk the user must know. When `action-first` is on, put that line in its state restatement instead of adding a closer.

## Precedence

CLAUDE.md, the task file's acceptance criteria and Out of Scope, project rules, and an invoked skill's own output format all outrank this file. Where they say more, do more.

---

Adapted from [ponytail](https://github.com/DietrichGebert/ponytail) v5.3.2 by Dietrich Gebert (MIT License). The wording, the scope line, the agent-chain hooks and the precedence rules are this toolbox's own.
