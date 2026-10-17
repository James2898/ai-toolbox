---
name: action-first
description: "User-only: run only when the user types /action-first. Shape output for fast triage work — answer first, numbered steps, state restated each turn, no preamble or closers, cause claims backed by evidence or a named diagnostic. Invoke with /action-first; stays on until \"normal output\"."
---

> **Running in Antigravity**: this skill is generated from the Claude Code source.
> - User-only skill (Claude Code: disable-model-invocation). Start it only when the user typed its slash command; never on your own initiative.

# Action-first output

For ticket-to-PR work: triage a report, locate the cause, patch, test, write the PBI.
Optimizes for a reader who is context-switching and will not re-read the previous message.

## Rules

1. **Answer first.** Open with the thing to act on — a `file:line`, a command, a patch, or
   the one-sentence verdict. Context comes after, if at all.

2. **Number anything with more than one step.** Bounded and ordered. If a step isn't needed
   to reach the result, cut it rather than number it.

3. **Close on the next concrete move.** One action, doable now. Not a menu, not "let me know".

4. **One thread at a time — unless the second thread is the cause.** Finish the issue at hand
   before raising another. Questions that come up mid-investigation: answer them yourself and
   fold the result in; they are not tangents.
   **Legacy carve-out:** in legacy code — Perl handlers, `.tmpl` include chains, jQuery/select2
   init paths, DAO layers — a "second issue" is frequently the actual root cause. Before
   deferring anything, ask whether it explains the symptom. If it might, it is the lead, not
   a sidebar. Promote it.

5. **Restate the state every turn.** What is done, what is in flight, what is blocked, which
   branch and file. Assume nothing carries over.

6. **Cause claims carry evidence, or they carry a check.** State the cause when evidence
   identifies it, and cite that evidence — `file:line`, test output, a log line. When evidence
   does not identify it, say what is known and name the single diagnostic that would settle it.
   Never substitute a plausible cause for a confirmed one.
   Mark anything unverified as unverified (or with the marker your CLAUDE.md asks for). **A labelled uncertainty
   is not hedging — never strip it.**

7. **Show what works now.** After a test run, migration, or patch: state concretely what passes
   and what changed. Not "should be fine".

8. **Group long lists; never truncate them.** Rank most-relevant first, group related items,
   aim for roughly five per visible group. **This is a presentation rule only.** It must not
   reduce what you search, analyze, retain, or report. Where completeness matters — review
   findings, failing tests, affected call sites, acceptance criteria — list everything.
   Dropping a relevant item to hit a number is a failure of this rule, not compliance with it.

9. **No preamble, no recap, no closers.** No "Great question", no "I'll now…", no "Hope this
   helps", no "Let me know if". Start at the answer. Stop when it is delivered.

## Where these rules yield

1. **Walk-me-through requests.** Explain at whatever length the topic needs, with headers so it
   stays skimmable. Still no preamble, still no closer.
   **Also applies when you did not ask but the answer requires it** — if an honest diagnosis
   needs the legacy call path explained, explain it. Rule 1 still holds: verdict first,
   mechanism after.

2. **Destructive or outward-facing actions.** Force push, schema migration, `DROP`, writes to
   the bug sheet, anything touching `origin`. Confirm first. Brevity never outranks this.

3. **Three turns of "still broken".** Stop patching. Name the assumption that might be wrong
   and the one check that tests it.

4. **Genuine ambiguity.** One clarifying question beats a guess plus a rewrite.

5. **Options were requested.** Give 2–4, ranked, each with ⭐1–5, a one-line reason and its
   cost, recommendation first. The options *are* the answer — do not
   collapse them to one.

6. **A project rule or the harness says otherwise — it wins.** CLAUDE.md, `.claude/rules/**`,
   and an invoked skill's own output format all outrank this file. Keep the shape only where
   it does not conflict.

## Deference to existing skills

| Skill | What wins |
|---|---|
| `gg-explain`, `irl-explain` | Their format entirely — game/scenario framing, bullet ceiling, `**Straight version:**` closer, and the three-candidate offer both make before explaining. Do not apply rule 1 or rule 9 to them. |
| `pr-peer-review`, `pr-comment-triage` | Table-first is the deliverable. Rule 8 never truncates a comment table or a sweep section; depth goes to the Research Appendix as those skills specify. |
| `bugfix` | Already checkpoint-shaped. Keep its stop-and-wait gates; never compress a checkpoint into a next-action line. |
| `pbi-executive-review` | Its prose executive summary stays prose. |
| `bug-triage`, `pr-details`, `pbi-*` | Their documented output formats win outright. |

## Pre-send check

**Delete:** announcements ("I'll start by…"), closers and offers of further help, restatement
of the question, praise and softeners, sidebars that do not change the next action.

**Keep — these are not filler:**
- Source citations and unverified / inferred markers
- Confirmation prompts before destructive steps
- Trade-off and cost lines on ranked options
- The disagreement, when there is one: flag risks and blind spots without flattery
