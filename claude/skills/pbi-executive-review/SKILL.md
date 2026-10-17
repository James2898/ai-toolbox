---
name: pbi-executive-review
description: Reads a PBI document (pasted text, Markdown, PDF, or directory) and produces a structured review with executive summary, frontend/backend development phases, and a list of blocking concerns/questions. Codebase-aware — verifies referenced files, hooks, and components actually exist before recommending reuse.
allowed-tools:
  - Read
  - Write
  - Glob
  - Grep
  - Bash
  - Agent
  - AskUserQuestion
user-invocable: true
disable-model-invocation: true
---

# PBI Executive Review Skill

This Skill reviews a PBI document against the current codebase and produces a development plan separating frontend and backend work, plus a list of blocking questions the user should resolve before implementation begins.

It answers four questions:
1. **What is this PBI actually asking for?** (executive summary in 4–6 lines)
2. **What does the frontend need to do?** (phased steps, file paths, reusable hooks/components)
3. **What does the backend need to do?** (endpoints, schemas, DDD context impact — or explicitly "out of scope")
4. **What ambiguities or missing inputs should the user resolve first?** (numbered, blocking)

## Position in the Pipeline

```
/pbi-executive-review <pbi_input>   ← this Skill (planning, no code changes)
    → prints plan to terminal
    → optionally writes to tasks/PBI-XXX_plan.md

/pbi-gen-test-doc                   ← generates test plans from acceptance criteria
/pbi-audit-test-doc                 ← cross-references PBI vs existing test cases
/project-manager                    ← actually implements (reads this plan as input)
```

This Skill is **read-only** by default. It does not edit code. It produces a planning document the user (or `/project-manager`) can act on next.

---

## STEP 1: Input

Read `$ARGUMENTS`. The PBI may arrive in any of these forms:

1. **A file path** — `.md`, `.pdf`, or a directory containing `requirements.md`
2. **A URL** — Notion / Confluence / GitLab issue link (use `WebFetch` if available, else ask the user to paste the body)
3. **Pasted text** — the PBI body in the prompt itself
4. **No argument** — ask the user to paste the PBI body or provide a path

If `$ARGUMENTS` is empty or whitespace, use `AskUserQuestion`:
> "Please provide the PBI — paste the text directly, or give a path (Markdown / PDF / directory)."

If a path is provided that does not exist, ask once whether the user meant to paste the text inline.

---

## STEP 2: Read the PBI

- **File**: use `Read` (Claude reads PDF natively; no shell required).
- **Directory**: use `Glob` for `{dir}/requirements.md` first, then fall back to `{dir}/*.md`.
- **Pasted text**: use the input as-is.

Extract these fields where present (do not invent if missing):
- PBI ID / title
- Issue / Purpose / Business Value
- Goal & Expected Outcome
- User Story
- Acceptance Criteria (number them AC-1, AC-2, …)
- Technical Notes / Implementation Detail
- Scope & Out-of-Scope lists
- Linked Figma / design references

If the PBI text is under 200 characters, treat it as insufficient and ask the user for the full body.

---

## STEP 3: Codebase Reconnaissance (codebase-aware planning)

This is what makes the output actionable rather than generic. **Skip this step only if the PBI is purely conceptual** (research / discovery PBIs with no code component).

Spawn up to **3 parallel `Explore` agents** in a single message. Use the minimum number of agents necessary:

- **1 agent** — when the PBI scope is isolated to a known view/module the user named explicitly.
- **2–3 agents** — when the PBI touches multiple layers (e.g. a frontend view + a backend endpoint + a shared hook).

Each agent's prompt must:
- Name the specific files/directories or symbols to look for
- Ask the agent to **report file paths and confirm existence** (so the plan does not recommend reusing things that don't exist)
- Ask the agent to flag related sibling branches if the PBI references work-in-progress on another branch (run `git branch -a | grep <keyword>` and `git log --all --oneline | grep <keyword>`)
- Cap the response (e.g. "report under 400 words")

Verify before recommending reuse:
- If the plan will say "reuse hook X" — confirm `X` exists with `Grep` or by file read.
- If the plan will say "follow the pattern in component Y" — confirm `Y` exists.
- If a reference component is on a sibling branch only, **call this out explicitly in the Concerns section** — do not pretend it's already mergeable.

---

## STEP 4: Identify FE / BE / Shared scope

Classify each acceptance criterion into:
- **FE** — UI, state, locale, routing, client-side logic
- **BE** — endpoints, DB schema, DDD usecase/handler/repo, batch jobs
- **Shared** — contracts (request/response shapes), feature flags, integration tests
- **Out of scope (per PBI)** — items the PBI explicitly defers; list separately so they don't leak into phases

If the PBI says "frontend only on mock data" or similar, the BE phase becomes a short "out of scope, future coordination notes" section (do not pad it).

---

## STEP 5: Identify Blocking Concerns

A concern is **BLOCKING** if any of these hold:
1. An acceptance criterion references a file/component/page that does not exist in the codebase (and is not promised by another known branch)
2. A data field needed by the UI is absent from the mock or backend schema
3. Two ACs imply contradictory behavior
4. The "consistency with X" instruction has no concrete X to copy from
5. A sibling PBI/branch is named but its merge order is unclear
6. UI copy / format / sort key naming has multiple defensible answers and no design decision

Concerns that are *non-blocking* (style nits, low-priority polish, future-PBI hooks) go in a separate "Non-blocking flags" subsection.

Each blocking concern gets:
- A short title
- The evidence (file path + line, or screenshot/Figma reference, or the AC number)
- A specific question the user can answer in one sentence

Aim for **3–8 blocking concerns** for a typical PBI. If there are zero, the PBI is unusually well-specified — say so explicitly.

---

## STEP 6: Compose the Plan

Output to the terminal in this exact structure. Use the same Markdown headings every time so users can scan multiple plans uniformly.

```markdown
# PBI Plan: {PBI ID} — {Title}

## Executive Summary

{4–6 line summary: what's being built, on top of what foundation, with which constraints, for which user. No bullet list — prose.}

---

## Concerns / Questions for the User (BLOCKING)

These should be answered before development starts — they materially change scope.

1. **{Title}.** {Evidence with file:line}. **Question:** {one specific sentence}.
2. ...

### Non-blocking flags

- **{Title}.** {One-line note}.
- ...

---

## Phase 1 — Frontend

{If frontend has no scope: a single sentence saying so, then skip the steps.}

### F1. {Step title}
**Files:** `{path1}`, `{path2}`
{1–3 sentence description of the change. Reference reusable hooks/components by file path.}
{Which AC(s) this covers.}

### F2. ...

### Tests
{Unit-test targets in the project's test framework. Mention end-to-end tests only if the PBI calls for them or a happy path is genuinely useful. Follow the project's own rules on which layers get unit tests.}

---

## Phase 2 — Backend

{If backend has no scope: a single sentence saying so + bullet list of "future coordination points" (informational only).}

### B1. {Step title}
**Files:** `{path1}`, `{path2}`
{Layer: handler / usecase / domain / infra / dao. Reference existing patterns.}
{Which AC(s) this covers.}

### B2. ...

### Tests
{Go unit-test targets. Mention sqlmock / integration as appropriate.}

---

## Critical Files Reference

| Concern | File |
|---|---|
| {…} | `{path}` |

---

## Verification Plan

Use the project's own verify commands — read them from `package.json` scripts, a Makefile, or CONTRIBUTING before assuming. Typical shape:

1. **Type & lint** (frontend): the project's type-check + lint scripts (e.g. `npm run type-check && npm run lint`)
2. **Tests**: the project's test script (e.g. `npm test`, `go test ./...`, `pytest`)
3. **Build**: the project's build or container-log check shows no errors
4. **Manual**: {numbered scenarios that exercise each AC}
5. **i18n**: switch language to ja / zh, confirm new strings localize.

---

## Recommendation Summary

{1–3 sentences: complexity verdict, blocking-question count, rough effort estimate (frontend-days + backend-days).}
```

**Stylistic rules for the plan body**:
- Use `file_path:line` references where helpful.
- Reference existing hooks/components by full `@/` import path so the developer can paste-search.
- Do **not** invent locale keys, DB columns, or struct fields — if a name has to be chosen, list it as a non-blocking flag for the developer.
- Quote acceptance-criterion numbers (AC-1, AC-2) when assigning them to phases.

---

## STEP 7: Ask Whether to Save the Plan

```
AskUserQuestion(
  question: "Plan complete. Type 'save' to write to tasks/{pbi_id}_plan.md, 'save:<path>' to choose a different path, or 'skip' to keep it terminal-only.",
  header: "PlanOutput"
)
```

- `save` → proceed to STEP 8.
- `save:<path>` → write to the user-supplied path.
- `skip` → display "Plan kept in terminal only." and stop.

If the PBI ID could not be extracted, default the filename to `tasks/pbi-executive-review-{YYYY-MM-DD-HHmm}.md`.

---

## STEP 8: Write Plan File

Run `mkdir -p $(dirname {target_path})` via `Bash`, then `Write` the plan to the target path.

Display:
```
## Plan Written

- PBI: {pbi_id} — {title}
- Path: {target_path}
- Blocking questions: {n}
- Frontend steps: {n}
- Backend steps: {n}
```

---

## STEP 9: Optional Handoff

After writing, offer (one line, no `AskUserQuestion`):

> "Want me to feed this into `/project-manager` once you've answered the blocking questions? Just say so."

Do not auto-route. The user must explicitly approve.

---

## Error Handling

| Condition | Action |
|---|---|
| No PBI input provided | Ask via `AskUserQuestion` |
| Path does not exist | Ask once if user meant to paste inline |
| PBI body under 200 chars | Treat as insufficient; ask for full text |
| `Explore` agent times out / fails | Continue without codebase verification, but mark the affected concerns as "unverified — codebase scan failed" so the user knows |
| Plan would have zero blocking questions and zero phases | Stop and tell the user the input does not look like a buildable PBI |

---

## Anti-patterns (do not do these)

- **Do not edit code.** This Skill is read-only. The only writes are the optional plan file at STEP 8.
- **Do not assume reuse without verification.** If the plan says "reuse `useFoo`", `useFoo` must have been confirmed to exist in STEP 3.
- **Do not pad the backend phase** when the PBI is FE-only. A short "out of scope" note + future coordination bullets is better than fabricated tasks.
- **Do not merge blocking and non-blocking concerns.** Users skim the blocking list to unblock the PM; mixing in style nits dilutes that signal.
- **Do not invent acceptance-criterion numbers** if the PBI used a different scheme (e.g. "Scenario 3"). Mirror the PBI's own numbering.
- **Do not default to "looks good, proceed"** when there are real ambiguities. The skill's value is surfacing them.
