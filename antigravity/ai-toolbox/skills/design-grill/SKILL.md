---
name: design-grill
description: "Interrogate a feature request, PBI or spec adversarially and return a ranked list of clarifying questions — each with why it matters and which spec section it feeds, a category, and the assumption that will be used if nobody answers — so hidden scope, missing edge cases and unstated constraints surface while they are cheap. With --rounds it instead interviews the user round by round over a design tree, asking every question that is unblocked now with a recommended answer that \"yes\" accepts, until no decision is left open. Reads the PBI hardcopy, CLAUDE.md / AGENTS.md and project rules so it never asks what the guidelines already answer, and greps the codebase only to check whether an assumption holds. Read-only; returns the result in chat, or appends it to the PBI hardcopy on request. Use whenever the user asks \"what's unclear in this PBI\", \"grill this spec\", \"grill me on this\", \"what should I ask the PO\", \"find the gaps before we design\", \"let's settle the open decisions\", or before writing requirements or running /pbi-executive-review."
---

> **Running in Antigravity**: this skill is generated from the Claude Code source.
> - `ask_question` is Antigravity's interactive question tool (Claude Code: AskUserQuestion).
> - `ARGS` means whatever the user typed after `/<this-skill>`, or the request that triggered it.

# Design Grill

Ask the questions whose answers would change the spec, ranked by how much they would change it, each with the default you would otherwise proceed on — so the human can confirm a default with one word instead of writing prose.

## Inputs

`ARGS`: a PBI id (looked up in the profile's `docs.pbi_dir`, default `pbi-docs/`), a file path, a PR number (its body), or pasted request text. Nothing provided → ask for the request text.

| Flag | Meaning |
|---|---|
| (none) | **List mode**: one ranked table in chat, for questions someone else (PO, lead, designer) will answer |
| `--rounds` | **Rounds mode**: the user is the one deciding; interview them round by round until every decision is settled or parked |
| `--max=<n>` | list mode: at most n questions (default 12) |
| `--per-round=<n>` | rounds mode: at most n questions per round (default 6) |
| `--append` | append the result to the PBI hardcopy, after confirmation |

Pick the mode from the request when no flag is given: "grill me", "let's settle this", "walk me through the decisions" → rounds; "what should I ask the PO", "list the gaps" → list.

## Read first, so you do not ask what is already answered

- The request itself, in full.
- The PBI hardcopy in `docs.pbi_dir` (default `pbi-docs/<id>*.md`) — the Analysis section already lists ambiguities and risks; deepen those, do not repeat them.
- `CLAUDE.md`, `AGENTS.md`, `.claude/rules/*.md` and other project rule files — conventions (layers, i18n, error handling, testing) are settled; a question about them is noise.
- Existing specs for the same area (`docs/specs/`, `docs/backlog/**/requirements.md`) and the live screens/endpoints the request touches.
- The codebase, **only to test an assumption**: does this endpoint exist, is this column nullable, which screens share this hook, is this value an enum. Cite `file:line` for what you checked.

## Angles to cover before finalising

- Happy path vs failure modes; what the user sees on each error.
- Empty, boundary and at-scale inputs (zero rows, one, thousands; longest allowed text).
- Permissions and personas (by role and flag), company/tenant isolation, admin tiers.
- Backward compatibility: existing records, in-flight data, old clients, feature flags, rollout order.
- Data and state: new vs changed entities, nullable means reachable?, transitions, deletes (soft/hard).
- Non-functional: performance (query count, pagination), security, PII, i18n (the three locales), accessibility, mobile/responsive.
- Integration: sync jobs, external services, batch timing, time zones.
- Observability: logging needs — new log codes need an operations agreement, so ask whether one exists.
- Acceptance: is every AC testable? Does product intent contradict an AC (which wins)? Explicit non-goals.

## List mode (default)

A ranked table, blockers first (a blocker changes scope or data model; a major changes behaviour or AC; a minor refines wording):

```markdown
## Grill — <request title> (<YYYY-MM-DD>)

| # | Rank | Question | Why it matters → spec section | Category | Assumption if unanswered |
|---|---|---|---|---|---|
| 1 | blocker | <one specific, answerable question> | <concrete risk> → Scope / AC / Data model / NFR / Integration | scope boundary · user/behaviour · data & state · edge/error · non-functional · integration · acceptance/DoD | <the default you would proceed on> |

**Checked in code:** <assumption> — `<file:line>` (holds / does not hold)
**Readiness:** specs-ready once #1–#<k> are answered | still fundamentally underspecified because <…>
```

Aim for the smallest set that removes real ambiguity — typically 5–12. No compound questions; no questions the guidelines or the PBI already answer; no padding to reach a count.

## Rounds mode (`--rounds`)

The user makes the decisions; you find the facts. Work the request as a **design tree**: each decision has the decisions that only make sense once it is settled (whether to soft-delete decides whether restore needs a question at all).

### 1. Build the tree

From the reading and the angles above, list the open decisions and, for each, which other decisions it depends on. Drop anything the guidelines, the PBI or the code already settle; note those under **Already settled** with their source.

Done when: every open decision has its prerequisites named (or none).

### 2. Ask the frontier

The **frontier** is every open decision whose prerequisites are all settled. Ask it as one round: the highest-ranked `--per-round` questions (blockers first), the rest waiting for the next round. A question whose answer depends on another question in the same round belongs to a later round.

Before asking, settle facts yourself: a question that needs a fact from the code or docs is not a question for the user. Check it with `Grep`/`Read`, or for a wide search spawn a read-only search subagent in the background (Claude Code: the built-in `Explore` agent); only the questions downstream of that fact wait for it, so ask the rest now.

Post the round as a chat message, not `ask_question` (answers are free text and a round can hold more than four questions). Format the questions as a table for readability:

```markdown
### Round <n> — <k> open, <m> settled

| # | Rank | Question | Options & Context | ➡️ Recommendation & Reason |
|---|---|---|---|---|
| **Q<n>.1** | blocker | <the question> | <concrete options or relevant context> | <your answer, and the one-line reason or the `file:line` behind it> |
| **Q<n>.2** | major | … | … | … |

Reply "yes" to accept every recommendation, or answer by number (`1: separate duplicates, 2: strip models`). "ask PO" or "skip" parks a question.
```

Word each question so that "yes" accepts the recommendation. Number questions by round (`Q2.3`) so later rounds can refer back.

Done when: the round is posted. Then wait for the user's reply; do not continue on your own.

### 3. Fold the answers in

- "yes" accepts every recommendation in the round; a numbered answer overrides only that question.
- An answer that contradicts the PBI, an AC or a project rule: say which and ask which wins, in the next round.
- **Parked** ("ask PO", "skip", "don't know"): keep your recommendation as a labelled assumption and carry the question to the final record. Questions downstream of it are still asked, framed on that assumption, so the tree keeps moving.
- Recompute the frontier: settled answers unblock the decisions that hung off them, and an answer can open a branch you had not listed.

Show a one-line ledger at the top of the next round: `Settled: Q1.1 soft delete · Q1.2 admins only (assumed, parked)`.

After the fifth round with the frontier still open, ask whether to keep going or park the rest.

### 4. Close when the frontier is empty

Every branch visited, nothing silently assumed. Produce the record and ask the user to confirm it is a shared understanding before anything acts on it:

```markdown
## Grill decisions — <request title> (<YYYY-MM-DD>)

| # | Decision | Answer | Source | Spec section |
|---|---|---|---|---|
| Q1.1 | <decision> | <answer> | user · recommendation accepted · code `<file:line>` · rule `<file>` | Scope / AC / Data model / NFR / Integration |

### Parked — needs someone else
| # | Question | Assumption in force | Who can answer |
|---|---|---|---|

**Readiness:** specs-ready | specs-ready on the parked assumptions | still underspecified because <…>
```

When questions are parked, offer the `to-questionnaire` skill to turn them into a sheet for the PO; call the Skill tool with "to-questionnaire" only if the user agrees.

## Append (`--append`)

With `ask_question` confirmation, append the result to the PBI hardcopy: list mode under `## Open questions (grill)`; rounds mode under `## Design decisions (grill)`, with any parked table under `## Open questions (grill)`. Never rewrite existing sections. Without `--append`, the result stays in chat.

## Rules

- Ask; do not answer for the human. Label every default and every parked answer as an assumption, never as a fact.
- Facts are yours to find, decisions are the user's: never ask the user something the code, the docs or the rules can answer.
- Read-only apart from the confirmed append.
- Mark anything inferred as (inferred), or with the marker your project rules ask for; cite the file for anything verified.
- This skill does not write specs. Tell the user they can take the result to `/pbi-analyze`, `/pbi-executive-review` or their requirements workflow.

Rounds mode adapts the `grilling` skill from [mattpocock/skills](https://github.com/mattpocock/skills) (MIT).
