---
name: bug-triage
description: "Triage a QA bug-report sheet (the project's bug tracker) and report which bugs are actually AVAILABLE and worth taking — filtered by phase/status/assignee, then reality-checked against the codebase and open PRs so you don't take one that's already fixed, already someone else's, or blocked on a designer/backend. Reads a downloaded CSV export (the only supported source — never scrape the live sheet with a browser tool). Produces a verdict table with a recommendation and an honest groupability note (which bugs could genuinely share a PR). Use whenever the user pastes or points at a bug report sheet, asks \"which bug should I take\", \"what's open/available\", \"organize the bugs\", \"check this phase's bugs\", \"can these be done together\", or wants a bug's status verified before starting work. Reports only — it never creates branches, edits code, or writes to the sheet."
---

> **Running in Antigravity**: this skill is generated from the Claude Code source.
> - `ask_question` is Antigravity's interactive question tool (Claude Code: AskUserQuestion).

# Bug Triage

Turn a 90-row bug sheet into a short list of bugs that are **genuinely available and code-ready**, each already checked well enough to decide on.

The value isn't the filtering — you can eyeball Status/Phase/Assignee yourself. The value is the **reality check**: the sheet lies. It lists bugs as open that shipped months ago, marks bugs unassigned whose files are live under someone's open PR, and describes personas ambiguously enough to send you chasing the wrong tier. Every check below exists because it actually went wrong.

## Project settings

This skill reads the project profile (see the toolbox README): `AI_TOOLBOX_PROFILE`, else `<project root>/.ai-toolbox/profile.yml`. Placeholders used below:

| Placeholder | Profile key | Without a profile |
|---|---|---|
| `{source}` | `bug_tracker.source` | `csv` |
| `{export_glob}` | `bug_tracker.export_glob` | ask for the path |
| `{col_id}` `{col_title}` `{col_status}` `{col_phase}` `{col_assignee}` `{col_severity}` | `bug_tracker.columns.id` / `.title` / `.status` / `.phase` / `.assignee` / `.severity` | infer from the header row and state the mapping you used |
| `{col_research}` `{col_how_to_fix}` | `bug_tracker.columns.research` / `.how_to_fix` | infer from the header row; skip if absent |
| `{status_new}` | `bug_tracker.status_values.new` | infer from the values present and ask |
| `{status_in_progress}` | `bug_tracker.status_values.in_progress` | infer and ask |
| `{status_skip}` | `bug_tracker.status_values.skip` (closed, on hold, under investigation) | infer and ask |
| `{phase}` | `bug_tracker.phase_values.current` | ask |
| `{personas}` | `personas` (role names and what each can do) | none: flag ambiguous role terms and ask |
| `{repo}` | from `git remote get-url origin` | — |

Status values may come in more than one language or spelling; list every form that should match.

## Hard constraint: reading the sheet

**Some environments block shell commands that name this file type** (for example a data-protection hook that rejects `.csv` in Bash). If yours does — or you don't know yet — follow this:

- **Use the `read_file` tool** for the CSV file. Never `cat`/`head`/`grep` it in Bash — the call is denied and you'll waste a turn.
- Don't try to work around such a hook. It's protecting a sheet that contains reporter names.

## Input — the CSV export, and only the CSV export

The user exports the sheet to CSV (usually lands in `~/Downloads/`; `{export_glob}` names the pattern if configured). Ask for the path, or find the newest match with `Glob` (a glob is not a Bash command, so it isn't blocked). Then `Read` it.

**Never scrape the live sheet with a browser tool.** No browser extension, no Playwright MCP, no other browser automation. Two independent reasons, either one sufficient:

- **Policy.** Many organizations allow browser automation only for debugging, investigation, performance measurement and e2e test authoring, not for automating internal business processes such as pulling a tracker — and this sheet carries reporter names. Scraping it through a browser would be walking around a data-protection guard by another door.
- **It often cannot reach it anyway.** Browser MCPs are commonly restricted to the app's own origins; a spreadsheet host is usually not on that list, so the navigation is refused.

**If the export is stale, ask the user to re-export** — a fresh export is the only source. Do not offer a browser route as the alternative.

Say **how current the export is** in the report (its file mtime). A verdict from a two-day-old export deserves that caveat.

**Always establish how stale the sheet is — this is not optional.** An export is a snapshot; PRs opened since then are invisible to it, and they're exactly what flips a verdict from "available" to "taken". So list the open PRs (Step 2) and compare their creation dates against the export's mtime: any PR newer than the sheet is information the sheet cannot contain. Say so explicitly — "this export predates PRs #X and #Y, which is why rows A and B read differently than the sheet suggests." A real run produced two wrong-looking verdicts precisely because two teammate PRs postdated the download.

## Sheet shape

Read the header row and map it to the fields above (`{col_id}`, `{col_status}`, `{col_phase}`, `{col_assignee}`, `{col_title}` or the description column, `{col_research}`, `{col_how_to_fix}`). State the mapping in the report when it was inferred rather than configured.

Messy realities to expect, because they're all present in real exports:
- **Multi-line cells** — descriptions run many lines with embedded newlines and URLs. Parse by quoted-field, not by line.
- **Duplicate IDs** — two different bugs can share the same number. Disambiguate by date + description; never merge them.
- **Trailing empty rows** — numbered but blank, dozens of them. Ignore.
- **Mixed languages** — status values, descriptions, and research notes may be in more than one language. Match every form (see below).
- **Assignee free-text** — values like `<name>(#<PR>)`, `<name> / <name>`, or the same name lowercased, or blank. A parenthesised PR number is a *hint about a past fix*, not proof of current ownership (see the stale-tag trap).

## Step 1 — Filter to candidates

Default filter (what the user usually means by "what's available"):
- **Phase** matches the target (`{phase}`) — ask if unspecified rather than assuming.
- **Status is open**: `{status_new}` and `{status_in_progress}` count as live work; the former is unclaimed.
- **Assignee empty** → candidate. Assignee present → normally excluded, but see the stale-tag trap: an old tag can hide an unclaimed reopening.
- **Skip**: `{status_skip}` — including any "under investigation" status, which is investigation-parked, not actionable even though it looks open.

State the filter you applied, so the user can correct it.

**Don't let the Phase column alone decide.** Rows are frequently untagged — a bug can be squarely in the current workstream and still have an empty Phase cell. After the strict filter, do a second pass for **near-misses**: untagged or differently-tagged rows whose subject matches the same feature area or the same class of problem as the target phase (and especially as the user's own recent work). Surface those separately as "untagged, but same family — worth a look" rather than dropping them. A real run found the single best candidate this way: an untagged row asking for bulk-response toasts, two thirds of which the user had already built in a recent PR without closing the row.

## Step 2 — Reality-check each candidate

This is the part worth having. For each candidate, run these checks and cite what you found. Most can go in parallel.

**Is it already taken?** The Assignee column is not sufficient.
```bash
gh pr list --repo <owner>/<repo> --state open --limit 100 --json number,title,headRefName,author,files
git branch -r | grep -iE "<topic keywords>"
```
Look for a branch or PR whose title/branch name references the bug number or its topic. **The stale-tag trap:** a bug tagged with an old PR number may refer to a *different, already-merged* fix, while the currently-described scope is untaken. Read what that PR actually changed before concluding.

**Is it already fixed?** The sheet is often behind the code. Grep for the behavior the bug says is missing. If the code already does it, say so with the `file:line` — that bug is a **close-it**, not a take-it. (One bug's "missing error toast" had shipped in an unrelated cutover PR months earlier.)

**Watch for partial satisfaction — it's the common case, not the edge case.** Often the bug's *literal wording* is already met while its evident *intent* isn't. A report saying "make sure the toast is shown" was satisfied by a generic error toast — but the backend was returning a specific, distinguishable reason that the frontend threw away, so the user still couldn't tell what went wrong. Both readings are defensible, and they lead to different work (close it vs. a small mapping job).

When you hit this, don't force it into fixed-or-not. Report it as **🟡 partially satisfied**, and make the fork explicit: what the literal ask is and whether it's met, what the fuller reading would require, and roughly what that costs. Then say the branch shouldn't start until the reporter picks — because starting blind means building the wrong half. Resolving the ambiguity is the deliverable here, not a fix.

**Would it collide with an open PR?** Even when unassigned, check whether the files it would touch appear in someone's open PR's file list. If yes, it's *effectively blocked* — flag the conflict rather than calling it available.

**Is it actually code-ready?** Read the description and research notes for blockers the sheet states plainly: "confirm with designer first", "should be a problem on backend", "to be handled in following phase", "needs a dedicated API". Those are **not** available regardless of status.

**Is anything ambiguous?** Flag rather than guess:
- **Persona/permission terms** — products often have several admin tiers whose names overlap (an "overall admin" can mean a feature-scoped admin *or* the organization-wide admin role). Check the term against `{personas}`. Picking a reading silently once led to "this bug doesn't exist" — wrongly. If the term is ambiguous, say which readings exist and ask.
- Vague acceptance ("should be improved", "let us check this") — note that scope needs pinning before it can be estimated.

**Could it ride an existing PR?** If an open PR of the user's already touches the same file or subsystem, folding the fix in is usually cheaper for reviewers than a new stacked PR. Suggest it.

## Step 3 — Report

Open with 2–3 sentences: how many rows, how many survived the filter, and the headline (e.g. "6 in-phase/unassigned; only 2 are genuinely code-ready — one is already fixed and two are design-blocked").

Then the table (illustrative rows):

```markdown
| ID | Description (1 line) | Verdict | Why (with citation) | Rec |
|----|----------------------|---------|---------------------|-----|
| 12 | Concurrent delete shows no error toast | ✅ available | No PR/branch; behavior absent at `useDeleteItem.ts:22` | ⭐⭐⭐⭐⭐ |
| 15 | Edit-save on a deleted record | 🔍 already fixed | Shipped in PR #101; `useSaveRecord.ts:61` handles it | close it |
| 17 | Checkbox 2px misalignment | ❌ conflict | Unassigned, but its 3 files are live in open PR #102 | wait |
| 19 | Long names don't wrap | ⚠️ blocked | Sheet: "confirm with designer first" | not ready |
| 21 | Toast when member already in another group | 🟡 partial | A danger toast fires (`…CreateModal.ts:61`), but it's generic — backend returns a specific `AlreadyExists` the FE drops | ask reporter |
```

Verdicts: **✅ available** · **⚠️ blocked** (design/backend/next-phase) · **❌ taken or conflicting** · **🔍 already fixed** · **🟡 partially satisfied** (literal ask met, intent isn't — name both readings and their cost) · **❓ ambiguous** (needs a decision before it can be scoped).

Then a **groupability** note — and be honest about it. Two bugs are only a real pair if they share files or one shared fix. Bugs that merely *sound* related (both "concurrency toast") can turn out structurally unrelated: one endpoint returning 200-always-with-per-item-statuses needs entirely different handling from one returning a real 404. Say when a "pair" isn't one, and why.

Close with what you did NOT check and why, if anything (e.g. couldn't verify a bug without running the app).

## Step 4 — Stop

Report only. Don't create branches, don't start fixing, don't edit the sheet. The user picks, then hands off to their normal flow (a branch-creation skill to start the work, a live-verification skill to verify it, a PR-description skill for the PR).

**Follow-up mode (on explicit request only):** the user often wants sheet field text afterwards — "draft the research / how-to-fix for bug 12". That's a separate ask. When they make it: `{col_research}` = **what the issue is**, `{col_how_to_fix}` = **the fix + where it happened** (name the PR, not just a commit). Keep both to a few lines; they're read in a spreadsheet cell.

## People's names

The sheet has reporter and assignee names. Use them **internally** for filtering, but keep them out of the report: write "assigned" / "unassigned" rather than naming who. The exception is the user themselves — "this one's already yours" is the whole point of the check. Reporter and assignee names are personal information; keep them out of outputs.
