---
name: pr-peer-review
description: Peer-review a teammate's pull request without disturbing your local branch. Fetches the PR branch into an isolated git worktree (your current branch and working tree are never touched), runs the validator agent audit there (a project-specific one if defined, else validator-agent) in parallel with fetching existing PR comments (human + review bots such as Devin or Copilot) via gh, then produces a tabulated Markdown report that opens with a plain-language Bug & Fix summary, then tabulates each comment with why it was flagged, its thread status (replied/fixed/declined/open), and your own in-depth, code-grounded local review. Designed to run unattended after launch. Use when the user wants to review a PR, peer-review a branch, or audit a teammate's PR. Invoke with a PR number/URL and optionally the PBI name, e.g. `/pr-peer-review 123 PBI-042` or `/pr-peer-review https://github.com/org/repo/pull/123`.
---

# PR Peer Review

Produce a reviewer's report for a teammate's pull request. The report tabulates every existing PR comment (from humans and from review bots such as Devin), explains why each was flagged, records the thread status, and adds your own independently-researched local review for each — grounded in the actual code, not surface-level reasoning.

**This skill never touches your current branch.** It fetches the PR into a throwaway git **worktree** (a separate directory), audits there, and removes it when done — so you can launch it and go do other work in your normal checkout while it runs. The validator audit and the comment fetch run **in parallel**: spawn the validator in the background against the worktree, fetch + research comments in the foreground, then merge.

---

## Project settings

This skill reads the project profile (see the toolbox README): `AI_TOOLBOX_PROFILE`, else `<project root>/.ai-toolbox/profile.yml`. Placeholders used below:

| Placeholder | Profile key | Without a profile |
|---|---|---|
| `{pbi_dir}` | `docs.pbi_dir` | ask where PBI or ticket hardcopies are kept |
| `{default_base}` | `git.default_base` | the remote default branch |
| `{topic_bases}` | `git.topic_bases` | none: always use the PR's own base |
| `{frontend_dir}` | `project.frontend_dir` | the directory holding `package.json` (`.` in a single-package repo); skip if none |
| `{frontend_check}` | `commands.frontend_check` | from `package.json` scripts |
| `{backend_test}` | `commands.backend_test` | from the build files (`go.mod`, `pom.xml`, `pyproject.toml`, …) |
| `{dependent_suites}` | `commands.dependent_suites` | find the importers of each changed package and run their suites too |
| `{comment_labels}` | `review.comment_labels` | no label prefix |
| `{final_reviewer}` | `review.final_reviewer` | whoever reviews this area most often (from past PRs) |
| `{inline_only}` | `review.inline_comments_only` | false: a short summary review comment is allowed |

## Inputs

- **Required — PR:** a PR number (`123`) or full PR URL (`https://github.com/org/repo/pull/123`) as the first argument.
- **Optional — PBI name:** the PBI ID or title words as the second argument (e.g. `PBI-042`), so the skill can resolve the PBI reference with no mid-run question and run fully unattended. If omitted, the skill asks once at the start, then runs unattended.
- If no PR argument is given, ask the user for the PR number/URL. Do **not** silently fall back to the current branch.

---

## Preconditions — verify before doing anything

1. **`gh` is authenticated.** Run `gh auth status`. If not logged in, stop and tell the user to run `gh auth login`.
2. **Inside a git repo.** Run `git rev-parse --git-dir`. If not, stop and tell the user to run from the repo.
3. **No dirty-tree check needed.** Because the PR is fetched into a separate worktree (Step 1), the user's current branch and uncommitted changes are never touched — do **not** prompt to stash or abort, and do **not** switch branches.

Per the user's global rules: never commit, never push, never operate on the default branch. This skill is read-and-report only — it must not modify PR code or post anything to GitHub. The worktree is a read-only audit copy; never commit or push from it.

---

## Step 0 — Locate the PBI reference

Before reviewing, the review must be anchored to the PBI the PR is meant to satisfy.

1. **Get the PBI name.** If it was passed as the second argument, use it directly (no question). Otherwise **ask the user once**: "Which PBI does this PR implement? Give the ID or title." (This is the only mandatory upfront interaction — after it's answered, the rest runs unattended.)
2. **Search `{pbi_dir}/`** for a match — these are hardcopies produced by the `pbi-analyze` skill, named `<PBI-ID>-<slug>.md`:
   ```bash
   ls {pbi_dir}/ 2>/dev/null
   # then match the user's input against filenames, case-insensitive, against both the ID and the slug
   ```
   - Match on the ID segment (`PBI-042`) or any word in the slug. If exactly one file matches, use it.
   - If multiple match, list them and ask the user to pick.
3. **If no match is found, surface to the user** — do not proceed blind. Say the PBI isn't in `{pbi_dir}/` and offer:
   - (a) run the `pbi-analyze` skill now to create the hardcopy (ask them to paste the PBI content), then continue; or
   - (b) proceed **without** a PBI reference, with an explicit note in the report that the review was not anchored to acceptance criteria.
4. Once found, **read the PBI hardcopy** — in particular its **Acceptance Criteria**, **Scope & Out-of-Scope**, and **Codebase-Aware Notes** sections. These feed the review: you'll check the PR against the acceptance criteria and flag scope creep against the scope boundary.

Record the PBI file path and title for the report header.

---

## Step 1 — Resolve the PR and fetch it into an isolated worktree

**Never switch the current branch.** Fetch the PR into a separate worktree directory so the user's checkout is untouched and they can keep working.

```bash
# Resolve PR metadata (URL accepted directly; a bare number resolves against the current repo's default remote).
gh pr view <PR> --json number,title,author,headRefName,baseRefName,url,state,isDraft
```

Capture `number`, `title`, `author.login`, `headRefName`, `baseRefName`, `url`.

Fetch the PR head into a local ref and add a worktree for it (no branch switch in the main checkout):

```bash
git fetch origin pull/<number>/head:pr-<number>-review
git worktree add ../pr-<number>-review pr-<number>-review
```

- The audit directory is `../pr-<number>-review` (a sibling of the repo, outside the working tree). Call this `$WT`.
- All code reading, `tsc`/`eslint`, grep, and the validator agent audit run **inside `$WT`** — never in the user's checkout.
- If the worktree path already exists from a prior run, remove it first: `git worktree remove ../pr-<number>-review --force 2>/dev/null`.
- If `git fetch origin pull/...` fails (e.g. non-GitHub remote like GitLab, where the `pull/` ref scheme differs), fall back to fetching the head branch by name: `git fetch origin <headRefName>` then `git worktree add $WT origin/<headRefName>`.

Confirm the worktree exists (`ls $WT`) before continuing. Do not run `git checkout`/`gh pr checkout` in the main repo at any point.

#### Step 1-mem — Load review memory BEFORE reviewing (MANDATORY)

This skill has historically only *written* to memory (Step 5.5). Reading it is the half that prevents repeat findings. Do this before forming any verdict:

Use the user's memory or lessons file, if the tool keeps one (if there is none, say so in the report and continue):

```bash
MEM=<the user's memory or lessons directory>
sed -n '1,80p' "$MEM/<index file>"       # the index, if there is one — scan section headers
grep -rln '<feature keyword>' "$MEM"     # e.g. select, locale, react-query, spec
```

Then read in full any memory matching (a) the files in the diff, (b) the rules you are about to cite, and (c) **the reviewer who reviews this area** (often `{final_reviewer}`).

Three rules for using what you find:

1. **A memory's correction block outranks its original claim.** Read the whole file, not the first paragraph — several carry `CORRECTION (date)` sections that reverse the headline. Cite the *current* state.
2. **Reviewer-policy memories outrank the checked-in rules file.** `.claude/rules/*` can be stale; a memory recording what a specific reviewer required with a blocking label (from `{comment_labels}`, e.g. `[MUST]`) is evidence of what is actually enforced. If a memory says "reviewer X enforces Y ahead of the rules file", apply Y.
3. **Never argue past a memory without recording why.** If you conclude a memory does not apply, state the reason explicitly in the report. If the reason is "the rule text is permissive" or "precedent exists", you must additionally satisfy the precedent test below — permissive rule text is the single most common way a real policy gets reasoned away.

**Precedent test (when rule text and in-repo practice disagree):** counting files is not evidence. Date the precedent with `git log` and check *direction of travel* — post-rule **additions** vs **removals**:

```bash
git log --since=<rule date> --diff-filter=A --name-only <base> -- '<glob>'   # additions
git log --since=<rule date> --diff-filter=D --name-only <base> -- '<glob>'   # removals
```

And check **provenance of the additions**: who authored them, in which feature area, and was that area reviewed by the same reviewer? Post-rule additions by a different author in an unrelated area are **not** evidence that this PR's reviewer tolerates the pattern. A file merely *touched* after the rule date is not an addition.

> Why this is a hard gate: on a past review, component specs were judged acceptable from permissive rule wording ("not required") plus 17 in-repo precedents. The area's lead reviewer then required, with a blocking label, that they be deleted. The precedent check would not have flipped it outright — two specs *were* added post-rule — but both were by another author in an unrelated feature area, never reviewed by that reviewer, while the memory index already carried a "reviewer policy ahead of the rules file" entry covering exactly this case. The failure was not missing data; it was weighing repo-wide precedent above reviewer-specific enforcement, and never writing down that a memory was being argued past.

## Step 1a — Pin the base branch (MANDATORY — do not skip)

**Never type a base branch name from memory, and never assume the repo default (`{default_base}`).** Many PRs stack on a feature-train branch; diffing against the default silently imports other people's already-merged commits and makes you attribute their files to this author.

```bash
BASE=$(gh pr view <number> --json baseRefName --jq .baseRefName)
git fetch origin "$BASE"
echo "BASE=$BASE"                                   # echo it — you will use it everywhere
git diff --name-only "origin/$BASE...<head-sha>" | wc -l
```

- Use `origin/$BASE...<head>` for **every** diff, file list, and PR-authored/pre-existing classification. Never hardcode `{default_base}`.
- **Sanity gate:** if the file count is wildly larger than the PR's stated "N files changed" on GitHub, you are on the wrong base — stop and re-derive. (A 24-file PR showing ~150 files is the tell.)
- **Attribution proof — prefer blob identity over content diffs.** Identical hashes mean the file carries zero PR changes, full stop:
  ```bash
  git rev-parse "origin/$BASE:<path>"   # vs
  git rev-parse "<head-sha>:<path>"
  ```
- Confirm a suspect commit belongs to the base, not this PR: `git merge-base --is-ancestor <sha> "origin/$BASE"` → ancestor = not this PR's work.
- **A rebase is not an excuse.** If a claim looks stale, check `git log --oneline "origin/$BASE..<old-head>" -- <path>`. If the PR's own commits never touched the file, the claim was wrong when posted — retract it, don't call it drift.

> Why this is a hard gate: on a past review the base was a long-lived feature train (`{topic_bases}`), not the default branch. Diffing against the default branch swept in ~66 already-merged commits, inflated 24 files to ~150, and produced a published comment attributing two untouched files to the author. It was the third wrong claim in one comment — and upstream of the other two, so the careful "verify in depth" pass just re-audited the wrong file list.

### Step 1b — Prep the worktree so the validator can build

A fresh worktree has **no `node_modules`**, so `tsc`/`eslint`/`jest` can't run there. For JS/TS projects, **symlink** the main checkout's installed modules into the worktree instead of re-installing (a full `npm ci` costs minutes; the deps are identical — same lockfile, same tree):

```bash
# {frontend_dir} = the JS package root, relative to the repo root ("." in a single-package repo).
MAIN_NM="<main-repo-root>/{frontend_dir}/node_modules"
WT_NM="$WT/{frontend_dir}/node_modules"
[ -d "$MAIN_NM" ] && [ ! -e "$WT_NM" ] && ln -s "$MAIN_NM" "$WT_NM"
```

- Symlink (don't copy): shared, read-only for the audit. Do **not** run `npm install`/`npm ci` in the worktree (it would mutate the shared dir and trip the package-op permission `ask`).
- If the repo has no single JS root or modules aren't installed in the main checkout, skip this and note in the report that the build wasn't run.
- For the **background** validator to run unattended (see Step 2a), the project's `.claude/settings.local.json` must allowlist this `ln -s … pr-*-review/{frontend_dir}/node_modules` plus read-only git inside `pr-*-review` worktrees. Without that allowlist a background sub-agent's Bash is denied with no one to approve it, and it stalls — add the allowlist once per project.

---

## Step 2 — Launch the two workstreams in parallel

### 2a. Validator audit (background)

Spawn the local validator sub-agent in the **background** so it runs while you fetch comments.

**Use a project-specific validator agent if the project defines one, else `validator-agent`.** A project-specific auditor applies that project's own frontend/backend checklists (its `.claude/rules/*`) that the generic `validator-agent` does not.

```
Agent(
  subagent_type: "<project validator agent, else validator-agent>",
  description: "Audit PR branch",
  run_in_background: true,
  prompt: "Audit the PR branch checked out in the worktree at <$WT> (headRef <headRefName>,
           PR #<number>: <title>) against its base branch <baseRefName>. cd into <$WT> first —
           do NOT operate on any other checkout. Run your full security, performance, and
           architecture audit on the diff (git diff <baseRefName>...HEAD inside the worktree).
           Return your APPROVED / APPROVED WITH CONDITIONS / BLOCKED verdict plus the itemized
           findings list (severity, file:line, description).

           Use `git -C <$WT> …` for all git reads (do not `cd` then run a bare compound command —
           that can miss the permission allowlist). If any Bash call is denied, do NOT try to spawn
           a further sub-agent to work around it (you'll stall) — return what you have plus a one-line
           note that the build/diff step was blocked, so the foreground reviewer can fall back."
)
```

> If no project-specific validator is registered, use the generic `validator-agent`; if neither exists, tell the user and offer to fall back to the project's lint/test command — do not invent an audit. Always name in the report which validator agent actually ran.
>
> **If the background validator returns blocked-on-permissions or stalls** (e.g. Bash denied inside the worktree, no allowlist entry): stop it, and run its intended read-only sweep yourself in the foreground (you can Bash inside `$WT`). Note in the report that the validator agent could not complete and the verdict is your own manual sweep. This has happened on a real review before the worktree allowlist + symlink fix landed.

### 2b. Fetch PR comments (foreground)

Pull **all** comment sources — they live in different GitHub APIs and a single command misses some:

```bash
# 1. Review thread comments (inline, on code lines) — include resolution state via GraphQL
gh api graphql -f query='
  query($owner:String!, $repo:String!, $pr:Int!) {
    repository(owner:$owner, name:$repo) {
      pullRequest(number:$pr) {
        reviewThreads(first:100) {
          nodes {
            isResolved
            isOutdated
            comments(first:50) {
              nodes { author{login} body path line createdAt url }
            }
          }
        }
      }
    }
  }' -F owner=<owner> -F repo=<repo> -F pr=<number>

# 2. Issue-level comments (general PR conversation, not tied to a line)
gh pr view <PR> --json comments

# 3. Top-level reviews (approve/request-changes summaries with bodies)
gh api repos/<owner>/<repo>/pulls/<number>/reviews
```

Get `<owner>` / `<repo>` from `gh repo view --json owner,name` or by parsing the PR URL.

**Identify the author of each comment.** Tag review bots (such as Devin or Copilot) distinctly — their logins typically end in `[bot]` (e.g. `devin-ai-integration[bot]`). Match defensively on a known bot name or a `[bot]` suffix and label the column accordingly (bot name vs `Human`).

---

## Step 3 — Determine status per comment (auto-infer)

For each comment, infer **Status** from thread state plus the diff — do not ask the user to fill it:

| Signal | Status |
| --- | --- |
| `isResolved: true` on the thread | `Resolved` (then sub-classify Fixed vs Declined below) |
| Thread has a reply from the PR author after the comment | `Replied` |
| The flagged code was changed in a later commit to address the comment | `Fixed` |
| Author replied disagreeing / closing without change | `Declined` |
| No reply, not resolved, code unchanged | `Open` |

To classify **Fixed vs Declined** on a resolved/replied thread: read the file at `path:line` on the PR branch and check whether the flagged issue still exists. If the code was changed to address it → `Fixed`. If unchanged but resolved → likely `Declined` (or resolved-as-wontfix); note the reply text.

When you genuinely cannot determine status from the available signals, write `Undetermined — <one line on what's missing>` rather than guessing. Never leave it blank.

---

## Step 4 — Your in-depth local review per comment

This is the core deliverable. For **each** comment, do real research before writing the "My Local Review" cell:

1. **Read the actual code** at the comment's `path:line` **inside the worktree `$WT`** (and surrounding context — the function, not just the line). All file reads, greps, and `tsc`/`eslint` runs happen in `$WT`, never in the user's checkout. When citing in the report, cite the repo-relative `path:line` (strip the `$WT/` prefix) so links resolve in the user's normal checkout.
2. **Trace the concern**: is the flagged issue real? Reproduce the reasoning from the code, not from the comment's claim. Check callers, related tests, error paths.
3. **Cross-reference** the validator findings (Step 2a) when they land — if the validator independently flagged the same spot, say so; if it contradicts the comment, surface that.
4. **Cross-reference the PBI** (Step 0) — if the comment touches behavior tied to an acceptance criterion, note whether the criterion is still satisfied after the change. Flag if a comment's resolution breaks a criterion or drifts outside the PBI's scope.
5. **Form an independent verdict**: Agree / Partially agree / Disagree, with the technical reason and a `file:line` citation.

Keep the table cell to a tight verdict + reason. If a comment needs deep analysis, put a short verdict in the table and write the full reasoning in a **per-comment Research Appendix** section below the table, linked from the table (e.g. `see §C3`). The user explicitly wants in-depth research, not one-line hand-waves — err toward the appendix for anything non-trivial.

Do **not** dump raw reasoning into the status column. Status is the thread state; your analysis goes in "My Local Review" / the appendix.

---

## Step 5 — Collect the validator result

Once the foreground comment work is done, retrieve the background validator agent's output (it will notify on completion). Fold its verdict and findings into:
- a **Validator Audit** section in the report, and
- cross-references inside individual comment rows where the validator hit the same code.

If the validator is still running when comments are done, wait for it before writing the final report.

> **The validator is diff-scoped and runs no tests.** Its verdict is never evidence that the suites pass. When the PR changes behaviour other packages depend on, run the affected suites yourself inside `$WT` (`{backend_test}` / `{frontend_check}`) — the changed package **and** its dependants (`{dependent_suites}`) — and record the result in the Validator Audit section. If they cannot run in the worktree, say so rather than implying coverage.

---

## Step 5.5 — Route resolved Devin comments to @debug-memory

Resolved Devin-bot comments are a source of repeatable lessons — if Devin caught a real bug and it was fixed, that pattern is worth recording so it isn't reintroduced.

1. From the comment set, select every comment where **author = Devin** AND **status = `Fixed`** (resolved *and* the code was actually changed to address it). 
   - Exclude `Declined` Devin comments (false positives / wontfix — not lessons).
   - Exclude style nits with no correctness impact.
2. For each candidate, judge **lesson-worthiness**: it must be a genuine bug, security issue, or anti-pattern — something a future change could plausibly reintroduce. A one-off typo or a purely cosmetic change is not lesson-worthy.
3. **If one or more candidates survive**, invoke `@debug-memory` **once** (batched — not one call per comment) so it filters duplicates and decides what to persist:
   ```
   Agent(
     subagent_type: "debug-memory",
     description: "Record PR review lessons",
     prompt: "From PR #<number> (<title>), the Devin bot flagged these issues that were
              confirmed and FIXED. Evaluate each for a durable lesson and record any that
              aren't already recorded (skip duplicates and task-specific noise):
              <for each: file:line · what Devin flagged · how it was fixed · the underlying
               root cause as you understand it from reading the code>"
   )
   ```
4. **If no candidate survives**, do not spawn `@debug-memory` — note `no lessons recorded` in the report. (Matches debug-memory's own no-op-on-clean-run contract.)
5. Record in the report which comments were routed and `@debug-memory`'s outcome (entries written, or "no new entries").

> If `debug-memory` is not available in this project's agent registry, skip this step and note it in the report — do not invent memory entries yourself.

---

## Step 6 — Write the report

Write to `pr-reviews/PR-<number>-peer-review.md` in the repo root (create the `pr-reviews/` directory if absent). Use this structure.

**Always open the report with a `## Bug & Fix in Plain Terms` section** — placed **first**, immediately after the header block, before everything else. Two short paragraphs a non-engineer can grasp: (1) **The bug** — what was wrong and what the user saw/experienced; (2) **The fix** — what the PR changed to correct it, in everyday language, plus the size of the change (e.g. "1 file, ~14 lines, CSS-only"). No `file:line` citations, no jargon. This is mandatory for every report, PBI or not — if the PR is a feature rather than a bug fix, title the two paragraphs **The goal** / **The change** instead, but keep the section.

Write the **Summary of Changes** section after the Bug & Fix section (it is the slightly more detailed distillation). Write both **last** (after the PBI Compliance table and comment analysis are done) but place them at the **top** of the file. Derive the PBI comparison from the compliance table, but state it in prose a non-engineer could follow; do not just restate the table.

```markdown
# PR #<number> — Peer Review: <title>

- **Author:** <author>
- **Branch:** `<headRefName>` → `<baseRefName>`
- **PR:** <url>
- **Reviewed by:** <git user.name>
- **Date:** <YYYY-MM-DD>
- **PBI reference:** `{pbi_dir}/<PBI-ID>-<slug>.md` — <PBI title>  (or: _none — review not anchored to a PBI_)
- **Validator verdict:** <APPROVED / APPROVED WITH CONDITIONS / BLOCKED>  (<which validator agent ran, e.g. `validator-agent`>)

## Bug & Fix in Plain Terms

> Mandatory, first section. Two short plain-language paragraphs, no file:line, no jargon.
> For a feature PR, use **The goal** / **The change** headings instead of Bug / Fix.

- **The bug:** <what was wrong and what the user saw/experienced, in everyday language — e.g. "In the member-selection table, the row checkboxes sat too high while the header 'select all' checkbox was centered, so the column looked misaligned.">
- **The fix:** <what the PR changed to correct it, plainly, + change size — e.g. "Added a small CSS style that centers the row checkboxes the same way the header one already was. 1 file, ~14 lines, CSS-only — no logic or data touched.">

## Summary of Changes

> Plain-language overview for a quick read — **before** the technical PBI Compliance table.
> Keep it non-technical: what changed and why, in terms a reviewer (or PM) can grasp in 30 seconds.
> No file:line citations here — those live in the tables below.

- **What this PR does:** <1–3 sentences: the change in plain language — what was built/modified/removed and the goal behind it.>
- **What changed (high level):** <bulleted list of the meaningful changes, grouped by area, each one short sentence — e.g. "Reworked the orders mock API into a stateful in-memory store", "Renamed `getItems` → `listItems` across consumers". Skip mechanical noise.>
- **How it measures against the PBI:** <2–3 sentences in prose comparing the PR to the PBI goal: does it advance the PBI, fully satisfy it, only partially, or sit adjacent to it? Call out the single most important match and the single most important gap/deviation in plain words — e.g. "Backs the PBI's create/edit ACs with a correct mock; one deviation — it makes the admin field optional, which the PBI lists as required.">
- **Bottom line:** <one sentence: your overall read — looks good / good with caveats / has a blocking concern.>

## PBI Compliance

Check the PR against the acceptance criteria from the PBI hardcopy. Omit this section only if no PBI was found (Step 0b).

| Acceptance Criterion | Met? | Evidence |
|----------------------|------|----------|
| <criterion 1> | ✅ / ❌ / ⚠️ Partial | `file:line` — how the PR satisfies (or fails) it |
| ... |

Note any **scope creep**: changes in the PR that fall outside the PBI's stated scope.

## Existing Comments

| # | Author | Type | Location | Comment (why flagged) | Status | My Local Review |
|---|--------|------|----------|------------------------|--------|-----------------|
| C1 | Devin | Bot | `api/handler.go:42` | Unchecked error on DB write — potential silent data loss | Fixed | Agree. Confirmed `err` was unhandled in the original; now wrapped at L44. ✔ |
| C2 | jdoe | Human | `web/cart.tsx:88` | Race condition on quantity update | Open | Partially agree — real race, but narrower than described. see §C2 |
| ... |

## Validator Audit (@<validator agent that ran>)

<!-- Name the validator agent that actually ran: the project-specific one if defined, else @validator-agent. -->


<verdict + itemized findings: severity · file:line · description>

## Research Appendix

### §C2 — Race condition on quantity update
<in-depth analysis: code trace, callers, repro reasoning, citation, independent verdict>

...

## Lessons Recorded (@debug-memory)
<which resolved+fixed Devin comments were routed to @debug-memory, and its outcome:
 entries written, or "no new entries". If no candidates qualified: "no lessons recorded".>

## Reviewer Summary
<2–4 sentences: overall state of the PR, count of agree/disagree, blocking items, recommendation>
```

**Status legend** to include under the table: `Open` · `Replied` · `Fixed` · `Declined` · `Resolved` · `Undetermined`.

---

## Step 7 — Close out

- Tell the user the report path and give a one-line summary (e.g. "8 comments: 5 fixed, 1 open, 2 you disagree with; validator = APPROVED WITH CONDITIONS").
- **Remove the worktree** — the user's branch was never changed, so there's nothing to switch back: `git worktree remove ../pr-<number>-review --force` and `git branch -D pr-<number>-review` (the local review ref). Confirm the user's current branch is unchanged.
- Write the report into the **user's checkout** at `pr-reviews/PR-<number>-peer-review.md` (not into `$WT`, which is about to be deleted).
- Do not commit the report or push anything unless the user explicitly asks.

---

## Follow-up mode — drafting comments to post on the PR (on explicit request only)

The report itself is never posted. When the user then asks to "draft the comments", produce paste-ready comment text under these rules:

- **Own findings only.** Draft comments solely for issues the reviewer flagged independently (the "My Own Findings" section). Do **not** draft replies to Devin/bot threads or restate other reviewers' points — this is a teammate's PR, and those threads are the author's to handle. (This differs from `pr-comment-triage`, which is for the user's own PRs.)
- **Inline comments.** Every drafted comment anchors to a `file:line`. When `{inline_only}` is true, never draft a summary/overall review comment.
- **Label prefix** on every comment from `{comment_labels}` (e.g. `[MUST]` / `[IMO]` / `[nits]` / `[ASK]`), per the repo's PR-template semantics. No labels configured → no prefix.
- **Tone: short, factual, no emotion, no praise.** State the finding, the evidence, the ask. A few sentences max.
- **In-depth backing required.** Before drafting a comment that cites a convention against the PR, verify precedent in the repo: grep for the pattern the comment relies on and classify **every** match — the full distribution, not the first sibling found (on a past review a "use the sibling's safe form" comment died on the full sweep: the criticized form was the 11-of-13 majority). When existing code contradicts the convention, **date the precedent with `git log` vs. the convention's date** — the newer one governs new code, and the comment should acknowledge the older precedent rather than pretend the repo is clean. A comment that flags the house-majority pattern is noise — withdraw it.
- **Convention provenance check.** A rule that exists only in the reviewer's personal memory/feedback (not in `.claude/rules/`, the project's documented guidelines, or the PR template) is a personal practice, not a team rule — it cannot back a blocking label (e.g. `[MUST]`) on a teammate's PR. Verify where the rule is codified before citing it.
- The user posts the comments themselves; this skill never posts to GitHub.

---

## Scenario Handling Contract (mandatory — do not improvise)

These scenarios have a fixed, agreed handling. When you encounter one, follow the prescribed behavior exactly — do not invent an alternative flow. This contract is binding; deviating from it is a defect.

| # | Trigger | Required handling |
|---|---------|-------------------|
| S1 | PBI found in `{pbi_dir}/`, PR exists | Anchor the review to that PBI: read its AC/scope/notes, produce the PBI Compliance table, cross-reference comments to acceptance criteria. |
| S2 | PBI not found for the name given | Surface to the user. Offer exactly two options: (a) paste PBI now → run `pbi-analyze` → resume; (b) proceed unanchored with an explicit "not anchored to a PBI" note in the report. Never proceed silently. |
| S3 | User's name matches >1 PBI | List all matches numbered, ask the user to pick. Do not auto-pick. |
| S4 | Reviewing without disturbing the user's work | Never switch the user's branch or stash. Fetch the PR into a separate worktree (`$WT`), audit there, remove it at the end. The user's checkout and uncommitted changes stay untouched throughout — no dirty-tree prompt. |
| S5 | Comment status inference | Auto-infer per the Step 3 table. Never ask the user to fill status. When undeterminable, write `Undetermined — <reason>`, never blank. |
| S6 | Devin bot comment you disagree with | Record an independent verdict (Agree/Partial/Disagree) with a `file:line` trace and put the reasoning in the appendix. Do not defer to the bot. |
| S7 | Validator returns BLOCKED | Surface the blocking findings as the top items of the report, including net-new findings not present in any existing comment. |
| S8 | About to say a rule/memory does NOT apply | Write the reason in the report. If the reason is permissive rule text or in-repo precedent, run the direction-of-travel + provenance check (Step 1-mem) first. Reviewer-specific enforcement outranks repo-wide precedent. |
| S9 | Any claim that a file/line is "PR-authored" | Derive the base with `gh pr view --json baseRefName` (Step 1a) — never assume `{default_base}`. Classify with `origin/$BASE...<head>`, and prove attribution with blob identity (`git rev-parse`). Identical hashes = zero PR changes. |
| S10 | Resolved + fixed Devin comment | Evaluate for a lesson and route qualifying ones to `@debug-memory` once, per Step 5.5. |

If a real situation does not match any scenario above, handle it conservatively (surface to the user rather than guessing) and note it — do not silently extend the contract.

---

## Guardrails

- Read-only on GitHub: never post comments, never resolve threads, never push.
- Never operate on or modify the default branch.
- **Never switch the user's branch or stash their work.** All PR code lives in the worktree `$WT`; the user's checkout is never touched. Always remove `$WT` on completion (and on failure — clean up before surfacing the error).
- Every "My Local Review" verdict must cite a `file:line`. No citation = mark it `Undetermined` and say what you'd need.
- Tag bot vs human accurately; when unsure of bot identity, label `Human?` rather than mislabeling.
- Resolved+fixed Devin comments must be evaluated for `@debug-memory` lessons (Step 5.5) — never skip silently; if none qualify, state "no lessons recorded."
- The Scenario Handling Contract above is binding — follow the prescribed handling for any scenario it covers.
