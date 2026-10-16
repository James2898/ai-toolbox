---
name: bugfix
description: "Orchestrate a bug fix end-to-end — triage, branch, root-cause, fix, validate, live-verify, record the lesson, PR, and the bug-tracker writeback. GUIDED, not autonomous — it runs each phase but stops at the genuine decision points (which fix approach, a design tradeoff, whether to push) so you stay in control; its job is to make sure no step gets skipped, not to decide for you. Composes the existing skills (bug-triage, live-verify, pr-details, pr-comment-triage) rather than reimplementing them, and owns the git/branch discipline, the investigation, and the tracker fields. Branch, base, test commands and tracker fields come from the project profile. Use when the user says \"take bug NN\", \"fix this bug\", \"start on this bug\", \"work the bug sheet\", or is beginning any bug fix and wants the full chain rather than ad-hoc steps. For spec-driven feature work use the project's feature workflow instead — this is the bug-work counterpart."
---

> **Running in Antigravity**: this skill is generated from the Claude Code source.
> - `ask_question` is Antigravity's interactive question tool (Claude Code: AskUserQuestion).

# bugfix — guided bug-fix orchestration

Run a bug from "I'll take this one" to a reviewed PR without dropping a step. The failure this prevents isn't bad code — it's the **skipped step**: shipping without live-verifying, missing that a sibling has the same defect, writing a commit that leaks a bug number, or discovering at PR time that someone already fixed it.

**You are guided, not autonomous.** Run each phase, report what you found, and **stop at the decision points**. The user makes the calls that have real tradeoffs — which fix shape, how much scope, whether to push. Your value is coverage and rigor, not deciding for them.

## Stop-and-ask checkpoints (non-negotiable)

Pause and surface options **with a recommendation and a reason** at each of these. Don't proceed on assumption:

1. **After triage** — is this bug actually available and worth taking? (already fixed / someone's PR / blocked on design or backend)
2. **After root-cause** — when more than one fix shape exists. Present each with its consequence; recommend one; let the user pick. (A typical trap: the simpler of two shapes silently breaks a mixed/partial case the other handles.)
3. **Before anything destructive or outward-facing** — pushing, force-pushing, PR creation, posting replies, writing to the tracker.
4. **When scope grows** — if the fix starts pulling in files beyond the bug, stop and confirm rather than quietly widening.

If a phase turns up something that contradicts the bug report (it's not reproducible, it's already fixed, the reported tier is wrong), say so immediately rather than fixing something that isn't broken.

## Project settings

This skill reads the project profile (see the toolbox README): `AI_TOOLBOX_PROFILE`, else `<project root>/.ai-toolbox/profile.yml`. Placeholders used below:

| Placeholder | Profile key | Without a profile |
|---|---|---|
| `{default_base}` | `git.default_base` | the repo's default branch (`git symbolic-ref refs/remotes/origin/HEAD`) |
| `{topic_bases}` | `git.topic_bases` | none: branch from `{default_base}` unless the user names a train |
| `{branch_format}` | `git.branch_format` | `bugfix/<slug>` |
| `{protected}` | `git.protected` | the default branch and `release/*` |
| `{pr_title_format}` | `review.pr_title_format` | `fix: <concise description>`, with the bug id in the body |
| `{frontend_check}` | `commands.frontend_check` | from `package.json` scripts |
| `{backend_test}` | `commands.backend_test` | from the build files (`go.mod`, `pom.xml`, `pyproject.toml`, …) |
| `{format_check}` | `commands.format_check` | the formatter config in the repo (`.prettierrc`, `gofmt`, …), if any |
| `{client_layer}` | `api.client_layer` | find where the frontend calls the API |
| `{tracker_columns}` | `bug_tracker.columns` | ask which columns hold cause, fix, remark, dates, status |
| `{status_while_open}` | `bug_tracker.status_while_open` | ask |
| `{status_after_merge}` | `bug_tracker.status_after_merge` | ask |
| `{memory_dir}` | `docs.memory_dir` | Claude Code's auto-memory directory for this project, if one exists; otherwise skip the memory pass and say so |

## The chain

Phases 1–4 and 9 you own. Phases 5–8 lean on existing skills and agents — call them, don't reimplement them.

### 1. Triage — is this bug real, available, and mine?

**If `bug-triage` already ran in this session, don't redo it.** Its verdict table IS phase 1 — treat the user's pick as checkpoint-1 confirmation and go straight to branching, unless the triage is stale (older than today, or open PRs may have changed). If triage ran in a *different* session, its context isn't here: ask the user to paste the verdict, or re-run the checks.

Otherwise, invoke the **`bug-triage`** skill if the user points at a sheet or asks what to take. If they simply named a bug with no triage behind it, verify before writing code:

- **Already fixed?** Grep the current base for the fix. Bugs sit in trackers for weeks and are often resolved by unrelated PRs.
- **Someone else's?** `gh pr list --state open` and `git branch -r` for a branch covering it. Check *file overlap* too — an open PR touching the same files blocks you even if it's titled differently.
- **Blocked?** Design-dependent ("confirm with designer") or backend/next-phase bugs aren't code-ready.

**"Already fixed" is an outcome, not just a rejection.** When the behavior turns out to already exist (shipped quietly in another PR, never logged against this bug), the run doesn't end — it usually narrows to: add the missing regression test that pins the behavior, then write the tracker fields citing the PR that actually shipped it. Offer that path explicitly; it is a common way for a bug to close.

**Pairing bugs.** Bugs are frequently taken in pairs sharing one branch/PR — legitimate when the fixes touch disjoint files, share a root cause, or one collapses into "just a regression test." Signals *against* pairing: overlapping files with an open PR, different bases, or one bug ballooning. When pairing: one branch named for the primary bug, separate commits per bug, PR title lists both ids (per `{pr_title_format}`), and the tracker writeback stays per-bug (each bug's remark notes `(with bug NN)` + the shared PR link).

**→ Checkpoint 1.** Report availability + a recommendation (including pair-vs-solo if relevant). Don't branch until the user confirms.

### 2. Branch — from the *correct latest* base

Get this right up front; rebasing later is where dead code and phantom conflicts come from.

```bash
git fetch origin <base> --quiet
git switch -c <branch per {branch_format}, e.g. bugfix/<topic>/bug<NN>-<short-slug>> origin/<base>
```

- **Base** is one of `{topic_bases}` when the bug belongs to that train, `{default_base}` otherwise — confirm which, don't assume. Never create or commit to a `{protected}` branch.
- Always branch from the **freshly fetched** remote base, never from whatever is checked out.
- If the fix depends on another in-flight PR, say so and ask whether to base on it or wait — don't silently stack.
- Uncommitted work in the tree carries over on `switch -c`; check `git status` first and confirm that's intended.

### 3. Investigate — root cause, not symptom

This is the phase worth spending time on. Trace the actual failure to a specific line, and **prove it** rather than asserting it:

- **Reproduce the condition** — via the API, a unit test, or a live probe. A bug you can't reproduce is a bug you can't verify fixed.
- **Follow the whole path** — FE handler → API wrapper → endpoint → backend usecase. The cause is often a layer away from the symptom (a "stuck loader" was really a request the backend 400s; a "success toast lying" was a 200-always endpoint with per-item statuses).
- **Read the sibling.** If a mirrored feature does the same thing correctly, that sibling is both the diagnosis and the fix template. Look for `// mirrors X` comments and create↔edit twins.
- **Check the report is right.** Reported tier/scope is sometimes wrong. Verify against the code and say so if it differs.

Cite `file:line` for the cause. If several fix shapes exist, enumerate them with consequences.

**→ Checkpoint 2.** Present the root cause and the fix options. Recommend one. Wait.

### 4. Fix — minimal, convention-matching

- **Match the sibling.** If an equivalent feature already solves this, mirror it — including the bits that look incidental (a toast's `autoHide` params, a shared classifier). Divergence is what reviewers flag.
- **Minimal diff.** No drive-by refactors, no reformatting other authors' lines. If pre-existing problems sit next to your change, note them; don't fix them here.
- **Tests alongside.** Follow the project's own test rules (`CLAUDE.md`, `.claude/rules/`, contributing docs) — typically: mock only at the HTTP boundary (`{client_layer}`), run the real wrappers, read toasts back from the real provider.
- Keep comments short and about *why*. **Never write a bug number into code or code comments** — the codebase outlives the tracker and its numbers mean nothing to other readers; bug numbers belong in the PR body and the tracker only.

**MANDATORY — run the dependent test suites, not just the package you edited.** The package you changed being green proves nothing about the suites that assert on its output. Before any push:

1. Grep for other tests that assert on the field/shape you changed — e.g. `grep -rn "<FieldName>" --include="*_test.go"` (Go) or the equivalent for a changed response type in TS.
2. Run every package that hit turns up. **Layered backends need both layers run:** when an outer layer's tests (e.g. HTTP handler tests) build whole expected responses from fixtures, a behavior change in an inner layer (use case / service) silently invalidates an outer-layer expectation without touching an outer-layer file. The inner package stays green while CI goes red.
3. **The validator does not cover this.** Its audit is git-diff-scoped and executes no test suites, so an APPROVED verdict is not evidence that dependent suites pass. Never treat it as such.

Then run the project's verification (`{frontend_check}`, `{backend_test}`): type-check, lint, the affected specs — **plus `{format_check}` on your new/edited files** if the formatter is not part of that chain. A formatter that the check command doesn't run (or that the linter config only *disables* conflicts with) lets an unformatted file sail through and get flagged in review. If the formatter warns on lines you didn't touch (other authors' pre-existing drift), leave those alone — minimal diff — and remember the commit will need `--no-verify`.

> **Run 5 and 6 in parallel.** They both consume the finished fix and have no dependency on each other — launch the validator in the background and start the live-verification (or at least draft its test steps) in the same turn, rather than waiting serially. This is how the real sessions ran ("invoke the validator and in parallel draft the live test") and it halves the wall-clock of the slowest stretch of the chain. **Do the memory grep (phase 5) before you spawn**, though — it feeds the agent's prompt, and once the agent is running you cannot add to its brief.

### 5. Validate — the local auditor, briefed with memory

Spawn **`validator-agent`** on the diff. It catches regressions that unit tests pass (e.g. a dedup option that was silently never wired). If no validator agent exists in this setup, say so and do a careful self-review instead — don't claim an audit that didn't run. Treat a BLOCKED verdict as work to do, then **re-run it** after fixing — don't self-certify.

Cross-check its findings yourself; it is occasionally wrong, and a finding you can't verify at `file:line` shouldn't drive a change.

**Brief it with the relevant memory — it cannot read memory itself.** The validator reads guideline files from the repo (`review_guideline*.md`, `.claude/rules/**`), but it has **no access to `{memory_dir}`**. Nothing else in this chain reads memory back either — `debug-memory` only writes to it — so past lessons silently fail to reach review unless you carry them across. That gap is real: a fix to a shared primitive once went to audit without the memory saying that primitive had been deliberately forked to avoid touching its consumers.

Before spawning, grep memory for lessons that bear on this diff, and **paste the relevant ones into the agent's prompt** as a "known prior lessons — check the diff against these" section:

```bash
# match on the files/symbols the diff touches, plus the feature area
grep -rilE "<component>|<hook>|<feature>" {memory_dir}
```

Prioritize memories about: the **shared primitive** being modified (fork-vs-modify decisions, blast radius), the **sibling** the fix mirrors, past **bugs in the same file or mechanism**, and reviewer conventions for this feature area. Skip ones that merely share a keyword — an irrelevant memory in the prompt costs attention and invites false findings.

Then, in your own cross-check, reconcile any memory that seems to *contradict* the fix rather than ignoring it. A memory saying "don't modify X in place" isn't automatically a veto — it may have been written about an API/behavioral change while yours is a contained bug fix — but the reconciliation belongs in the PR body, because a reviewer who remembers that lesson will raise it.

**Report which memories you fed it, and which (if any) you judged non-applicable and why.** "Validator APPROVED" without that line means the memory pass didn't happen — say so explicitly rather than letting the verdict imply coverage it doesn't have.

### 6. Live-verify — prove it in the running app

Invoke **`live-verify`**. Unit tests pass on broken screens. This is the step most often skipped and most often decisive.

If the change has branches (success / partial / error), verify **each** — not just the happy path. Include a regression pass on the sibling flow the fix mirrors.

### 7. Record the lesson — while it's fresh

Before opening the PR, decide whether this bug taught something reusable, and route it to **`debug-memory`** if so. Do it here rather than after the PR because the root cause is still in working memory — post-PR you've moved on and the detail that made it worth recording is the first thing lost.

Worth recording: a root cause that would recur in a sibling or a future feature, a false assumption the codebase invites (an endpoint that returns 200-always, a hook whose param is load-bearing), a tooling/harness trap, or a review lesson that generalizes.

Not worth recording: this bug's specific line numbers, anything the code or git history already says, or a one-off with no pattern behind it.

If nothing qualifies, say so explicitly in the final report ("no durable lesson — one-off") rather than skipping silently. That way a skipped record is a decision, not an oversight.

### 8. PR — title, body, and the review loop

**→ Checkpoint 3** before anything outward-facing.

- Commit with a `type(scope): summary` message describing the *behavior* change. **Never put the bug number in a commit message** — bug numbers live in the PR body only (the history outlives the tracker; its numbers mean nothing to other readers).
- If the touched file carries pre-existing formatting drift from other authors, commit with `--no-verify` so the hook doesn't pull their lines into your diff — and say that you did.
- **Draft by default.** Use **`pr-details`** to produce the title and body, hand them over in fenced code blocks for copy-paste, and stop. Run `gh pr create` only if the user explicitly asks; if they create it by hand, don't append the repo's PR template — their manual flow supplies it. Title format: `{pr_title_format}` (list both ids when bugs are paired). In the body, write tracker bug numbers **without `#`** — on GitHub `#48` auto-links to an unrelated issue/PR; a real PR reference (e.g. the PR that already shipped a fix) keeps its `#` on purpose.
- **Never push without explicit approval.** Pushing is a checkpoint-3 action every time, not once per run.
- **Post-push etiquette.** Before the branch is pushed: fold review/validator fixes into the right commit with `--fixup` + autosquash. **After the PR is live: new commits on top, never amend/force-push** — reviewers and bots need to see explicit fix commits, and a force-push invalidates their read.
- When review comments arrive, invoke **`pr-comment-triage`**. Fix what's valid, decline what isn't *with evidence*, and re-run the validator if the fixes were substantive.

### 9. Bug-tracker writeback

Draft the tracker fields (`{tracker_columns}`) — short, direct, and each in its own lane:

- **Cause / result of research** — *the issue only*, traced from the code with `file:line`. Not the fix.
- **Fix** — the fix, and **where it shipped** (PR link). If it turns out it was already fixed elsewhere, say so and cite the PR that did it.
- **Remark** — live-verification evidence, anything QA needs to re-record, and the PR link — with `(with bug NN)` when bugs shared one PR.
- **Dates** — any expected/actual push date columns = the actual push date (today unless told otherwise).
- **Status** — suggest `{status_while_open}` while the PR is open, `{status_after_merge}` once merged; the user flips it.

Never put customer or employee personal data in tracker text.

## Tiering — how much of this to run

Not every bug earns the whole chain. Judge by risk, and say which tier you're running:

- **Trivial** (wording, a locale key, a one-line guard): investigate → fix → tests → PR. Validator optional, live-verify if it's user-visible.
- **Standard** (most bugs): the full chain.
- **Risky** (concurrency, permissions, data-loss, anything touching a shared classifier or backend contract): full chain, plus a deliberate sibling regression sweep and live-verification of every branch.

When unsure, run the heavier tier — a skipped live-verify on a "simple" fix is how a wrong success toast ships.

## Composition — don't reimplement

| Need | Use |
|---|---|
| Which bug to take / is it available | `bug-triage` |
| Prove the fix works in the app | `live-verify` |
| PR title + body | `pr-details` |
| Handle review comments | `pr-comment-triage` |
| Security/architecture audit | `validator-agent` (agent, not skill) — brief it with relevant memory; it cannot read memory itself |
| Recall past lessons for review | grep `{memory_dir}` — phase 5, paste hits into the validator prompt |
| Record a durable lesson | `debug-memory` — phase 7, before the PR, when the cause is reusable |

Each owns its capability. Your job is sequencing them, carrying context between them, and stopping at the checkpoints.

## Reporting

Close with what actually happened: the root cause (`file:line`), the fix and why that shape, validator verdict **and which memories were fed into it**, live-verification evidence per branch, what you deliberately left out of scope, and the PR link. If a step was skipped, say which and why — a silent skip is the failure this skill exists to prevent. In particular, never let "validator APPROVED" stand in for coverage it doesn't have: if no memory reached the audit, say that plainly.
