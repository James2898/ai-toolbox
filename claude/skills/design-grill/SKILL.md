---
name: design-grill
description: Interrogate a feature request, PBI or spec adversarially and return a ranked list of clarifying questions — each with why it matters and which spec section it feeds, a category, and the assumption that will be used if nobody answers — so hidden scope, missing edge cases and unstated constraints surface while they are cheap. Reads the PBI hardcopy, CLAUDE.md / AGENTS.md and project rules so it never asks what the guidelines already answer, and greps the codebase only to check whether an assumption holds. Read-only; returns the list in chat, or appends it to the PBI hardcopy on request. Use whenever the user asks "what's unclear in this PBI", "grill this spec", "what should I ask the PO", "find the gaps before we design", or before writing requirements or running /pbi-executive-review.
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash
  - Edit
  - AskUserQuestion
user-invocable: true
---

# Design Grill

Ask the questions whose answers would change the spec, ranked by how much they would change it, each with the default you would otherwise proceed on — so the human can confirm a default with one word instead of writing prose.
## Inputs

`$ARGUMENTS`: a PBI id (looked up in the profile's `docs.pbi_dir`, default `pbi-docs/`), a file path, a PR number (its body), or pasted request text. Flags: `--max=<n>` questions (default 12), `--append` (append the result to the PBI hardcopy, after confirmation). Nothing provided → ask for the request text.

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

## Produce

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

## Append (`--append`)

With `AskUserQuestion` confirmation, append the block above to the PBI hardcopy under `## Open questions (grill)`; never rewrite existing sections. Without `--append`, the result stays in chat.

## Rules

- Ask; do not answer for the human. Label every default as an assumption, never as a fact.
- Read-only apart from the confirmed append.
- Mark anything inferred as (inferred), or with the marker your project rules ask for; cite the file for anything verified.
- Hand the answered questions to `/pbi-analyze`, `/pbi-executive-review` or your requirements workflow; this skill does not write specs.
