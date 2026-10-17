---
name: demo-guide
description: "User-only: run only when the user types /demo-guide. Write a demo guide for presenting a change — audience and goal, environment choice (local branch vs a deployed environment, with the reason), personas by role, setup steps and data (via /test-data or the UI), a timed script table (say / do / show / if it fails), wow moments, known gaps said before someone asks, cleanup, and likely questions with prepared answers drawn from the PBI's open questions and review threads. Writes {qa_out_dir}/<slug>/demo-guide.md. Use whenever the user has to demo, present or walk stakeholders through a feature, prepare for sprint review, \"show this to the PO\", or wants a script and Q&A for a feature presentation."
---

> **Running in Antigravity**: this skill is generated from the Claude Code source.
> - User-only skill (Claude Code: disable-model-invocation). Start it only when the user typed its slash command; never on your own initiative.
> - `ask_question` is Antigravity's interactive question tool (Claude Code: AskUserQuestion).
> - `ARGS` means whatever the user typed after `/<this-skill>`, or the request that triggered it.

# Demo Guide

A demo fails for boring reasons: the wrong environment, missing data, a stale bundle, a question nobody prepared for. The guide removes those. Output: `{qa_out_dir}/<slug>/demo-guide.md`.

## Project settings

This skill reads the project profile (see the toolbox README): `AI_TOOLBOX_PROFILE`, else `<project root>/.ai-toolbox/profile.yml`. Placeholders used below:

| Placeholder | Profile key | Without a profile |
|---|---|---|
| `{qa_out_dir}` | `docs.qa_out_dir` | `.qa/` (keep it gitignored) |
| `{pbi_dir}` | `docs.pbi_dir` | `pbi-docs/` |
| `{deploy}` | `deploy` | ask where each branch deploys |
| `{local_url}` | `environments.local_url` | ask |

## Inputs

`ARGS`: a feature description, PBI id (`{pbi_dir}/<id>*.md`), PR number, or a slug. Flags: `--audience=po|team|customer` (default `po`), `--minutes=<n>` (default 10), `--env=local|<environment name>`, `--out=<dir>`.

## Step 1 — Establish the facts

- **What exists where.** Is the change merged? Deployed? (`gh pr view <n> --json state,mergedAt,baseRefName`; `git branch -r --contains <sha>`.) Where each branch or tag deploys comes from `{deploy}`. A deployed environment never shows unpushed local work — if the demo needs unmerged changes, the environment is local (`{local_url}`) and the guide says so.
- **Acceptance criteria and open questions** from the PBI hardcopy or PR body — the Q&A section is built from these.
- **Review threads** (`gh pr view <n> --comments`, `gh api repos/<owner>/<repo>/pulls/<n>/comments`) — reviewers' questions are the audience's questions.

## Step 2 — Narrative in three beats

One line each: the **problem** the audience recognises, the **change**, the **proof** they will see on screen. Everything in the script serves one of the three; cut steps that do not.

## Step 3 — Personas and accounts

Roles plus permission flags, placeholders for logins. When permissions are part of the story, plan two personas (one who can, one who cannot) and two browser profiles or an incognito window so switching takes seconds.

## Step 4 — Setup

- Data: reference `/test-data` blocks (`TM-xxx`) or list UI steps to create it; prefer data that makes the "after" visibly different from the "before".
- Environment: dev server restarted and page hard-reloaded (a stale HMR bundle has faked both bugs and fixes before); feature flags; the exact URLs to pre-open in tabs, in order.
- Reset: how to return the data to the starting state between rehearsals.

## Step 5 — Script

| # | Time | Say | Do (where → action) | Show / expected | If it fails |
|---|---|---|---|---|---|

Rules: ≤ 12 steps for a 10-minute slot; one action per row; "Show" names what the audience should look at; every step with a dependency (network, sync job, external service) has a fallback (screenshot, pre-recorded state, skip line). Mark one or two **wow moments** — the rows where the problem visibly disappears — and put them before the half-way mark.

## Step 6 — Known gaps, before someone asks

From the PBI's open questions, the bug sheet, deferred items in PR threads and the plan's "Not covered": one line each, with the planned follow-up. Saying them first keeps the Q&A on the feature instead of on surprises.

## Step 7 — Likely questions

| Question | Answer | Source |
|---|---|---|

Derive from: ambiguities in the PBI, trade-offs the implementation made, "what about <other role>", performance at scale, how it reaches production (deployment path and timing), data migration for existing records, i18n (every supported language), what QA covered.

## Step 8 — Cleanup and checklist

- Cleanup: test-data cleanup blocks or UI deletions; state to restore.
- Pre-demo checklist: environment up · data present · logged in as persona A (and B) · bundle fresh · tabs open · fallback screenshots saved · timer.

## Template

```markdown
# Demo Guide — <feature>
- **Audience:** <po/team/customer>   **Duration:** <n> min   **Date:** <YYYY-MM-DD>
- **Environment:** <local | environment name> — <why>   **URLs:** …
- **State of the change:** PR #<n> <merged/open>, deployed to <env or nowhere>

## Story
1. Problem — …   2. Change — …   3. Proof — …

## Personas
| Persona | Role / flags | Used in steps |

## Setup
…

## Script
| # | Time | Say | Do | Show / expected | If it fails |

## Known gaps
- …

## Likely questions
| Question | Answer | Source |

## Cleanup
…

## Pre-demo checklist
- [ ] …
```

## Done when

- The environment choice is justified by where the change actually is.
- Every script step has an observable "Show" and a fallback where it can fail.
- The Q&A covers the PBI's open questions and the reviewers' questions.
