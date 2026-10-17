---
name: diagnose
description: "Find the root cause of a bug, failing or flaky test, or wrong output by first building a command that reproduces the failure (a red loop), then shrinking the case, ranking hypotheses that a single probe can rule out, and proving the cause at file:line by flipping the loop from red to green. Ends with a regression test at a real seam and a saved loop file that pr-details uses as evidence. Use when the user asks why something fails, to debug or root-cause an issue, says a test is flaky or passes locally but fails in CI, or hands over a bug to investigate. With --cause-only it stops at the proven cause and the fix options; bugfix and project-manager call it that way."
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
  - Edit
  - Write
  - Agent
  - AskUserQuestion
user-invocable: true
---

# diagnose — red loop first, then the cause

The rule this skill exists for: **no hypothesis until a command shows the failure.** A theory checked against a red loop is evidence; a theory checked against reading code is a guess. The loop is also what proves the fix and what the reviewer re-runs.

## Arguments

| Argument | Meaning |
|---|---|
| free text | the symptom, a bug id, a failing test name, or an error message |
| `--cause-only` | stop after step 5 with the proven cause and fix options; change no code permanently |
| `--loop="<cmd>"` | a reproduction command the user already has; start at step 2's verification |

## Project settings

This skill reads the project profile (see the toolbox README): `AI_TOOLBOX_PROFILE`, else `<project root>/.ai-toolbox/profile.yml`.

| Placeholder | Profile key | Without a profile |
|---|---|---|
| `{frontend_check}` | `commands.frontend_check` | from `package.json` scripts |
| `{backend_test}` | `commands.backend_test` | from the build files (`go.mod`, `pyproject.toml`, …) |
| `{dependent_suites}` | `commands.dependent_suites` | grep for tests that assert on what you changed |
| `{local_url}` | `environments.local_url` | ask |
| `{forbidden_hosts}` | `environments.forbidden_hosts` | treat anything that is not localhost as forbidden |
| `{loop_dir}` | `docs.loop_dir` | `.ai-toolbox/loops` |

Project test rules (`CLAUDE.md`, `AGENTS.md`, `.claude/rules/`, contributing docs) decide where tests live and what may be mocked. Read them before step 6.

## Steps

### 1. State the symptom

Write one line each: **expected**, **actual**, **where seen** (screen, endpoint, test, environment, data). If the report is ambiguous on any of the three, ask one question before going further.

Done when: the three lines are written.

### 2. Build the red loop

Pick the cheapest loop that shows the failure, trying in this order:

1. an existing test that already fails;
2. a new focused test at the nearest seam the project already tests (a hook, service, use case or handler);
3. a script or `curl` against `{local_url}` that returns the wrong status or body;
4. a browser step through `live-verify` for behaviour that only shows in the UI;
5. a temporary log or probe in the code path, read back from the output.

Run it and paste the red output. Then check two things:

- **Red for the right reason.** The failure message matches the symptom from step 1. A test that fails on a missing fixture or an environment default proves nothing about the bug.
- **Deterministic.** Run it twice. If results differ, run it N times (10 is a good start) and record the failure rate; the loop for a flaky bug is "fails k of N".

If three honest attempts do not produce red, stop. Report what you tried and what each attempt showed, and ask the user: not reproducible here, needs data or an environment you lack, or already fixed. Do not move to hypotheses without red.

Done when: a command and its red output, matching the symptom, are on screen.

### 3. Shrink the case

Remove inputs, rows, steps and options one at a time while the loop stays red. Keep what makes it go green when removed.

Done when: every remaining piece of the case is needed for red.

### 4. Rank hypotheses and probe

List two to four hypotheses. For each, name **the one probe that would rule it out** and what that probe would show if the hypothesis were true. Rank by likelihood times cheapness of the probe, then run the probes in that order and record each result.

Where to look for hypotheses:

- **The whole path**, not just the layer that shows the symptom: UI handler → request layer → endpoint → use case → query. The cause often sits a layer away (a spinner that never stops can be a request the backend rejects).
- **The sibling.** A mirrored feature that works (create versus edit, list versus detail) is both a diagnosis and a fix template. Diff the two paths.
- **Recent changes.** `git log -p --since=<when it last worked> -- <paths>`; use `git bisect run <loop>` when there is a known good commit.

Done when: one hypothesis survives and every other one was ruled out by probe output, not by argument.

### 5. Prove the cause

Point at `file:line`. Make the smallest change there that should fix it (or revert the suspect commit) and run the loop: it must flip from red to green, and back to red when you undo the change. That flip is the proof.

With `--cause-only`, undo the change and stop. Report the cause, the flip output, and each fix shape with its consequence and a recommendation.

Done when: the red → green → red flip is shown for that line.

### 6. Fix and pin it with a regression test

- Apply the fix the user chose (or the proven change, if there was only one shape).
- Turn the loop into a test at a real seam: the public function, hook or handler the project already tests at, following the project's mocking rules. The test asserts behaviour the user would notice, never the fixture you built for it.
- Show the test fails without the fix (stash or revert the fix, run, re-apply) and passes with it.
- Run the dependent suites (`{dependent_suites}`, or grep for tests that assert on the changed field or shape) as well as the package you edited, with `{frontend_check}` and `{backend_test}`.

Done when: the new test's red-without / green-with output and the dependent suites' results are on screen.

### 7. Save the loop file

Write `{loop_dir}/<slug>.md`:

```markdown
# <symptom in one line>
- Expected / actual / where:
- Loop: `<command>`   (flaky: k of N)
- Red output: <short excerpt>
- Shrunk case:
- Hypotheses: | hypothesis | probe | result | ruled out? |
- Cause: `file:line` — <one sentence>
- Flip: <red → green → red excerpts>
- Regression test: `<path>::<name>` — red without fix, green with
```

Use ids and statuses only; never names, emails or other personal data from the app or database. `pr-details` reads this file for its Evidence section, and a reviewer can re-run the loop command.

Done when: the file exists and its loop command still runs.

## Report

Close with a short table: symptom, loop command, cause `file:line`, proof (flip), fix, regression test, dependent suites run, loop file path. Name any step you skipped and why.

## Boundaries

- Requests go only to `{local_url}` or a host the user names; never to `{forbidden_hosts}` or production.
- Temporary probes and log lines are removed before the report; say that you removed them.
- No commits or pushes unless the user asks.
