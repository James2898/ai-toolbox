---
name: pr-comment-triage
description: "Triage new review comments (human OR bot/Devin) on YOUR OWN open PR — the branch you are actively working on. Fetches every comment source via gh, spawns the validator agent (a project-specific one if defined, else validator-agent) in the background as a cross-check, then does an in-depth, code-grounded analysis of each comment — filtered through the PBI scope and verified against siblings and the actual file. Also sweeps the PR's other diff files and direct siblings for the same issue the reviewer caught only once (verified-or-dropped, listed separately). Presents a TABLE with your verdict + proposed action per comment, and offers lesson-worthy patterns to memory. It STOPS there: it never edits code and never posts to GitHub. You decide what to implement and which replies to post. Use when the user says a reviewer (Devin or a human) left comments on their PR, \"there's a new devin comment\", \"check the PR comments\", or similar. Optionally takes a PR number/URL and a PBI name, e.g. `/pr-comment-triage 123 PBI-042`."
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
  - Agent
  - AskUserQuestion
user-invocable: true
---

# PR Comment Triage

React to new review comments on **your own** open pull request — the one on the branch you're actively working on. Comments come from **humans** and from **review bots** such as Devin or Copilot; both are handled, tagged distinctly, and given the treatment each deserves.

The deliverable is a **decision table**: for every comment, an in-depth code-grounded verdict (Agree / Partial / Disagree) plus a proposed action — so you can decide what to implement and which replies to post. This skill **stops at the table**. It never edits code and never posts to GitHub. Those are separate actions with their own explicit permission (see Guardrails).

**Difference from `pr-peer-review`:** that skill reviews a *teammate's* PR in an isolated worktree and never touches your branch. This skill operates on **your current checkout** — the PR you own and are working on — so there is no worktree. It reads your live branch, cross-checks with the validator, and reports. It still changes nothing on its own.

---

## Project settings

This skill reads the project profile (see the toolbox README): `AI_TOOLBOX_PROFILE`, else `<project root>/.ai-toolbox/profile.yml`. Placeholders used below:

| Placeholder | Profile key | Without a profile |
|---|---|---|
| `{pbi_dir}` | `docs.pbi_dir` | ask where PBI or ticket hardcopies are kept; none → proceed unanchored |
| `{default_base}` | `git.default_base` | the remote default branch |
| `{topic_bases}` | `git.topic_bases` | none: always use the PR's own base |
| `{frontend_check}` | `commands.frontend_check` | from `package.json` scripts |
| `{backend_test}` | `commands.backend_test` | from the build files (`go.mod`, `pom.xml`, `pyproject.toml`, …) |
| `{dependent_suites}` | `commands.dependent_suites` | find the importers of each changed package and run their suites too |
| `{comment_labels}` | `review.comment_labels` | no label prefix |
| `{final_reviewer}` | `review.final_reviewer` | whoever reviews this area most often (from past PRs) |

## Inputs

- **Optional — PR:** a PR number (`123`) or full URL as the first argument. If omitted, resolve the PR from the **current branch** (`gh pr view --json ...` with no number resolves the current branch's PR). If the current branch has no PR, stop and ask the user for the number/URL.
- **Optional — PBI name:** the PBI ID or title words (e.g. `PBI-042`) as the second argument, so the run is fully unattended. If omitted, try to auto-resolve from the branch/PR (Step 0); only ask if that fails.

---

## Preconditions — verify before doing anything

1. **`gh` is authenticated** — `gh auth status`. If not, stop and tell the user to run `gh auth login`.
2. **Inside a git repo** — `git rev-parse --git-dir`. If not, stop.
3. **This is the user's own PR on the current branch.** Do not switch branches, do not stash, do not touch the working tree. Read-only against the live checkout.

Per the user's global rules and the lessons below: fetch the real comments (never work from memory), present a table, and **STOP** — do not implement fixes and do not post replies without explicit per-item permission.

---

## Step 0 — Resolve the PR and its PBI

1. **Resolve the PR:**
   ```bash
   # bare number, URL, or (no arg) the current branch's PR
   gh pr view [<PR>] --json number,title,author,headRefName,baseRefName,url,state,isDraft
   gh repo view --json owner,name   # for the api calls below
   ```
   Capture `number`, `title`, `headRefName`, `baseRefName`, `url`, `<owner>`, `<repo>`.

   **Load review memory FIRST (MANDATORY).** Before judging any comment, read the user's memory or lessons file, if the tool keeps one: scan its index and `grep -rln '<feature keyword>'` it; read in full anything matching the diff's files, the rules you plan to cite, or **the reviewer who reviews this area** (often `{final_reviewer}`). No memory store → say so in the summary and continue. Read each match whole — a `CORRECTION (date)` block outranks the file's headline claim. A memory recording what a specific reviewer required with a blocking label (from `{comment_labels}`, e.g. `[MUST]`) outranks the checked-in `.claude/rules/*`, which can be stale. If you conclude a memory doesn't apply, say so explicitly with the reason; "the rule text is permissive" or "precedent exists" additionally requires the direction-of-travel check (`git log --diff-filter=A` vs `-D` since the rule date) **plus** provenance — who added the post-rule instances, in which area, reviewed by whom. Precedent from another author in an unrelated feature area is not evidence this reviewer tolerates it.

   **Pin the base before any diff (MANDATORY).** Never type a base name from memory or assume the repo default (`{default_base}`) — PRs that stack on a feature-train branch (`{topic_bases}`) will otherwise pull in other people's already-merged commits:
   ```bash
   BASE=$(gh pr view [<PR>] --json baseRefName --jq .baseRefName)
   git fetch origin "$BASE"
   echo "BASE=$BASE"
   ```
   Use `origin/$BASE...HEAD` for every diff and every PR-authored/pre-existing call. Sanity gate: if the changed-file count is far above the PR's stated "N files changed", you are on the wrong base — re-derive before continuing. For attribution, prefer blob identity (`git rev-parse "origin/$BASE:<path>"` vs `git rev-parse "HEAD:<path>"`) — identical hashes mean zero PR changes.

2. **Resolve the PBI** (for the scope filter — this is the strongest decline heuristic for bot comments):
   - If passed as the 2nd argument, use it.
   - Else infer from the branch name / PR title (e.g. a `PBI-042` / `bug-85` token) and search `{pbi_dir}/`:
     ```bash
     ls {pbi_dir}/ 2>/dev/null
     ```
     Match case-insensitively against the ID segment and the slug. One match → use it. Multiple → list and ask. **No match → proceed unanchored**, and note in the report that comments could not be filtered against a PBI scope boundary (bot scope-decline heuristics are weaker without it).
   - If found, read the hardcopy's **Acceptance Criteria**, **Scope / Out-of-Scope**, and any `(UI only)` / `scaffolded` / `no backend persistence` caveats. These feed the per-comment verdicts.

---

## Step 1 — Launch the two workstreams in parallel

### 1a. Validator cross-check (background)

Spawn **a project-specific validator agent if the project defines one, else `validator-agent`** in the background against the **current branch** so it runs while you fetch and analyze comments. It's a cross-check: when it independently flags the same spot a comment does, that corroborates the comment; when it contradicts one, surface that.

```
Agent(
  subagent_type: "<project validator agent, else validator-agent>",
  description: "Cross-check current PR branch",
  run_in_background: true,
  prompt: "Audit the current branch (PR #<number>: <title>) against its base <baseRefName>.
           Run the full security / performance / architecture audit on the diff
           (git diff <baseRefName>...HEAD). Return APPROVED / APPROVED WITH CONDITIONS /
           BLOCKED plus itemized findings (severity, file:line, description). Read-only —
           do not edit, commit, or push. If a Bash call is denied, return what you have
           plus a one-line note rather than spawning a further sub-agent."
)
```

> If no project-specific validator is registered, use the generic `validator-agent`; if neither exists, skip and note it — do not invent an audit. Name the validator that actually ran in the report.

> **The validator is diff-scoped and runs NO tests.** It cannot see a suite in another package that your change broke, so its verdict is never evidence that CI is green. When a comment claims a test fails (or when the PR changed backend behavior and no comment has covered the test surface yet), **run the affected suites yourself** (`{backend_test}` / `{frontend_check}`) before writing the verdict row — the changed package **and** its dependants (`{dependent_suites}`; e.g. a business-logic change also means the handler/API packages that call it). A reviewer-reported failure gets reproduced locally, not taken on faith and not dismissed.

### 1b. Fetch ALL comment sources (foreground)

Comments live in three different GitHub APIs — one command misses some. Pull all three:

```bash
# 1. Inline review-thread comments (on code lines) + resolution state via GraphQL
gh api graphql -f query='
  query($owner:String!, $repo:String!, $pr:Int!) {
    repository(owner:$owner, name:$repo) {
      pullRequest(number:$pr) {
        reviewThreads(first:100) {
          nodes {
            isResolved isOutdated
            comments(first:50) { nodes { author{login} body path line createdAt url } }
          }
        }
      }
    }
  }' -F owner=<owner> -F repo=<repo> -F pr=<number>

# 2. Issue-level comments (general PR conversation)
gh api repos/<owner>/<repo>/issues/<number>/comments --paginate

# 3. Top-level reviews (approve / request-changes summaries with bodies)
gh api repos/<owner>/<repo>/pulls/<number>/reviews --paginate
```

**Tag each comment's author:** review bots (such as Devin or Copilot) typically have logins ending in `[bot]` (e.g. `devin-ai-integration[bot]`). Match defensively on a known bot name or a `[bot]` suffix → label with the bot's name (Bot). Everything else → **`Human`** with the login.

**Focus on what's actionable.** If the user said "there's a *new* comment", prioritize open/unresolved threads and comments newer than the last time they were addressed. Still list resolved ones briefly, but don't spend deep analysis on already-closed threads.

---

## Step 2 — Analyze each comment in depth (the core work)

For **each** comment, do real research before writing its row. Never work from the comment's claim alone — verify against the code.

1. **Read the actual code** at the comment's `path:line` on the current branch (and its surrounding context — the whole function, callers, related tests, error paths). Cite `file:line`.

2. **Verify the comment's premise is true.** A comment (bot *or* human) can be built on a wrong claim about the code. Reproduce the reasoning from the file, not the comment. If the premise is false, that alone can be the verdict — with the source citation that disproves it. *(A declined finding is a claim about the code and needs the same source-check as an accepted one.)*

3. **Filter bot comments through the PBI scope.** Devin raises legitimate engineering that frequently cuts across PBI boundaries. Before accepting or declining a bot comment, check the PBI's Out-of-Scope / UI-only / scaffolded caveats. Classify along these decline axes:
   - **Out-of-Scope by PBI boundary** → decline with a verbatim PBI citation.
   - **UI-only / scaffolded caveat** → decline when the comment assumes real persistence/data the PBI deferred.
   - **Multi-part comment** → split it; apply only the in-scope parts, decline the rest with citations.
   - **Premature specificity** → in-scope by AC but the specific solution is premature because an adjacent next PBI may reshape it AND the path isn't user-visible today → decline citing the next-PBI dependency (not Out-of-Scope).
   - Preserve **scope-protective patterns already in the code** (`dirty` flags, mock fixtures, blank placeholder routes with deferral TODOs) even when Devin flags them — they exist by design.

4. **Verify consistency/perf findings against the sibling + call-frequency + whole component** before agreeing:
   - Does the code **mirror an established sibling** (look for a `// mirrors X` comment)? If the sibling does the same thing, the pattern is intentional precedent, not a slip.
   - What's the **call frequency** of the "hot" line — once-per-click vs per-row-per-render? O(n) on a discrete event is usually negligible.
   - Is the proposed fix **actually free** (no exhaustive-deps churn, no divergence from the mirrored pattern, no new dual reads)?
   - For **referential-stability / `React.memo`** findings: sweep the WHOLE component's non-primitive props. If siblings share the "defect", "odd gap" is false. A lone unstable prop with no live `React.memo` consuming it is a no-op — don't dress it as memo-safety. "Not `useCallback`'d" is not itself a defect if the reference never escapes the hook.

5. **Watch for known bot false-positive modes.** Devin miscounts multi-byte **CJK (kanji/kana)** characters and can raise a 🔴 "unterminated string literal / syntax error" on a perfectly valid line. When a 🔴 claims a string is unterminated AND the line has CJK, open the line and count quotes yourself, or note that `type-check` would fail loudly on a real one. Devin is strong on real DRY/dedup findings, weak on exact byte/char counting.

6. **Don't claim precedent you haven't verified.** If you're about to say "reviewer X also asked for this" / "this is rule-backed", grep the PR's actual comments and `.claude/rules/` first. Topic ≠ proximity — a sibling comment on the same file about a *different* topic is not precedent. Cross-PR human precedent (e.g. a senior reviewer's `[MUST]` that clearly generalizes) IS legitimate — label it as such.

7. **Weight by author:**
   - **Human comment** → carries direct reviewer authority. Default toward addressing it; if you disagree, say so with a citation, but frame it as pushback to a person, not a dismissal.
   - **Bot comment** → no inherent authority; stands or falls on the code + PBI. Form your own verdict; do not defer to the bot.

8. **Cross-reference the validator** (Step 1a) when it lands — corroboration or contradiction per spot.

9. **Form an independent verdict** per comment: **Agree / Partial / Disagree**, with the technical reason and a `file:line`. Keep the table cell tight; put any deep trace in the Research Appendix and link it (`see §C2`).

### Calibration — do not inflate

- Tier each finding: **✅ rule-backed** (a PR comment or a `.claude/rules/` line you can cite) · **🟡 inferred** (analogy to a rule, labeled as inference) · **🟢 taste** (your call only). Don't dress taste as rule-backed.
- The comments set the agenda — you're triaging *their* findings, not manufacturing new ones. Add a net-new finding only if the validator surfaced it or it's a real blocker; put those in a separate "Net-new (not yet commented)" mini-section, clearly marked.
- **Default to closing non-blocking findings now** when the deferral rationale is "mock can't fail" / "real API lands later" / "dead code until a later ticket" — this user prefers shipping the whole thing over a long tail of 🟡. **Counter-trigger:** if closing needs architectural change outside task scope, that's creep — keep deferring.

---

## Step 2.5 — Sweep for the same issue the reviewer caught only once

When a reviewer (bot or human) flags a real issue, the **same defect often sits in a sibling file or another file in this PR's diff** that they didn't happen to look at. Sweep for those — but under a strict verify bar, because this is exactly where findings get inflated.

Run the sweep **only for comments you verdicted ✅ Agree or 🟡 Partial** (a real issue worth propagating). Skip it for ❌ Disagree / false-positive comments — there's nothing to propagate.

**Scope — bounded, two places only:**
1. **Other files changed in this PR's diff** — `git diff <baseRefName>...HEAD --name-only`. These are in-scope by definition (you already own them in this PR).
2. **Direct siblings of the flagged file** — same directory, the mirrored `hooks/`/`services/` counterpart, and the create↔edit twin (e.g. `ItemCreateModal` ↔ `ItemEditModal`). Look for a `// mirrors X` comment to find the intended sibling.

Do **not** grep the whole repo. A repo-wide hit is almost always pre-existing and outside this PR's scope — that's scope creep, not a sweep.

**Verify bar — each candidate must survive, else DROP it (do not list raw grep hits):**
- Read the file. Confirm the pattern is genuinely the same defect, not a superficial text match.
- Check it isn't an **intentional mirror** — if the sibling deliberately does this (documented `// mirrors X`, or a deliberate read/write representation split), it's precedent, not a bug.
- Check **call-frequency / whole-component** the same way as Step 2.4 — O(n) on a once-per-click path isn't the reviewer's finding repeated.
- Confirm the **fix is free** (no deps churn, no divergence from a mirrored pattern).

A candidate that fails any check is dropped silently — it never reaches the table. Only verified survivors are listed.

**Scope filter still applies.** Run each survivor through the PBI (Step 2.3). If a sibling hit is out-of-scope or pre-existing on base and not part of this PR's rule-sweep, mark it **deferred with the reason** rather than forcing it in — the user decides per-item.

Survivors go in their **own section below the comment table** (Step 4), clearly labeled as *your* sweep findings, **not** reviewer-raised — never fold them into the reviewer's comment rows (keeps comment lineage honest).

If the sweep finds nothing verified, say so in one line — don't manufacture hits to look thorough.

---

## Step 3 — Determine status per comment (auto-infer, never ask)

| Signal | Status |
| --- | --- |
| `isResolved: true` | `Resolved` (sub-classify Fixed vs Declined by reading the code at `path:line`) |
| Author replied after the comment | `Replied` |
| Flagged code changed in a later commit to address it | `Fixed` |
| Reply disagreeing / closing without change | `Declined` |
| No reply, not resolved, code unchanged | `Open` |

When genuinely undeterminable, write `Undetermined — <what's missing>`, never blank. Status is the thread state — your analysis goes in the verdict column, not here.

---

## Step 4 — Present the table and STOP

Output to the chat (this is a decision aid, not a file deliverable — unlike `pr-peer-review`). Structure:

**Open with a 2–4 sentence plain-language summary:** how many comments, from whom, and your headline read (e.g. "6 comments — 2 Devin, 4 human; 3 you'd apply, 2 decline with citations, 1 needs your call").

**Then the decision table:**

```markdown
| # | Author | Type | Location | Comment (why flagged) | Status | Verdict | Proposed action |
|---|--------|------|----------|------------------------|--------|---------|-----------------|
| C1 | Devin | Bot | `web/foo.tsx:42` | Inline JSX alloc re-renders table | Open | ✅ Agree (rule-backed: frontend rules file:119 + bot precedent) | Extract to useCallback in the hook |
| C2 | jdoe | Human | `api/bar.go:88` | Suggests NotFound guard | Open | 🟡 Partial | In-scope part: log; guard is next PBI — decline that part w/ citation |
| C3 | Devin | Bot | `mock/Data.ts:29` | 🔴 unterminated string on `'凛'` | Open | ❌ Disagree | False positive — CJK miscount; line parses, tsc clean. No change |
```

Columns: **Verdict** = Agree/Partial/Disagree + tier (✅/🟡/🟢) + one-line reason with citation. **Proposed action** = what you'd do (implement / decline-with-reason / defer / needs-user-decision) — a *proposal*, not something you execute.

**Then, if the sweep (Step 2.5) found verified survivors:** a separate **Sweep — same issue, not yet commented** section below the comment table. Same columns, but the "Comment" column says which reviewer finding it propagates from (e.g. *"same as C1, not flagged here"*), and it's visually distinct from reviewer-raised rows. Out-of-scope/pre-existing siblings appear here marked `deferred — <reason>`. If the sweep found nothing, one line: *"Sweep: no unflagged siblings with the same issue."*

```markdown
### Sweep — same issue, not yet commented (my finding, not the reviewer's)
| # | Origin | Location | Same issue as | Verdict | Proposed action |
|---|--------|----------|---------------|---------|-----------------|
| S1 | PR diff | `web/bar.tsx:51` | C1 (inline JSX alloc) | ✅ Agree | Same extract; reviewer didn't flag this file |
| S2 | Sibling | `.../EditModal/hooks/useX.ts:29` | C1 | 🟡 deferred | Pre-existing on base, out of this PR's scope — note only |
```

**Then, if the validator has returned:** a short **Validator cross-check** block — its verdict, and which comment rows it corroborated or contradicted (plus any net-new findings, clearly marked as not-yet-commented). If it's still running when the analysis is done, wait for it before finalizing.

**Then a Research Appendix** for any comment whose verdict needed deep tracing (`§C2 …`).

**Status legend:** `Open` · `Replied` · `Fixed` · `Declined` · `Resolved` · `Undetermined`.

---

## Step 4.5 — Offer lesson-worthy findings to memory (analysis-time, opt-in)

Some lessons surface during **analysis**, before any code is touched — and they're exactly the kind your memory already collects. After the table, scan the run for two capture-worthy categories:

1. **A new bot false-positive pattern** — a Devin (or other automated reviewer) finding that collapsed under verification in a way that would recur, e.g. a new class of miscount/hallucination beyond the known CJK-string one. One-off noise doesn't qualify — it must be a *pattern* a future PR would hit again.
2. **A decline whose reasoning generalizes** — you declined a comment for a reason that isn't PR-specific (a PBI-scope boundary that will recur, a sibling-mirroring pattern the reviewer misread, a rule interaction). If the *reason* would apply to a future comment on a different PR, it's worth a memory.

Do **not** capture: comment-specific facts, taste calls, anything already covered by an existing memory (grep the memory store first), or confirmed-and-fixed lessons — those are handled only if/when you implement (Step 5, via `@debug-memory` on your say-so).

**Offer, then write on the user's OK — never auto-write.** If one or more candidates survive, add a short block after the table:

```
Lesson candidates for memory (say which to save):
  L1 — <proposed name-slug> · <one-line: the pattern + why it recurs>
  L2 — <proposed name-slug> · <one-line>
```

Write a candidate to the user's memory or lessons file **only after the user picks it** — following that store's existing format (one entry per fact with its why and how-to-apply, linked to related existing entries, plus an index line if the store keeps an index). If no candidate qualifies, say nothing about memory (no noise). Never spawn `@debug-memory` for these analysis-time patterns — write them directly on approval; reserve `@debug-memory` for post-fix confirmed lessons in Step 5.

---

**Then STOP.** End with: *"Tell me which to implement and which replies to draft"* (and, if there were lesson candidates, *"…and which lessons to save"*). Do not edit code. Do not post anything. Do not write memory before the user picks. This hard stop is deliberate — the user decides.

---

## Step 5 — On explicit follow-up only

The user drives everything past the table. Handle each request with its own scope:

- **"Implement C1"** (or "proceed with C1") → authorizes the **code change for C1 only**. Make it, following the project's existing patterns. It does **not** authorize posting a reply on the C1 thread.
- **"Draft the reply to C1 / C3"** → produce a **paste-ready ```markdown fenced block** (verdict up front — applied / partially applied / declining — then 1–3 bullets with reasoning; cite the PBI Out-of-Scope verbatim when that's the decline basis). Keep it concise. Do **not** post it — the user pastes it, or explicitly says "post it".
- **"Post the reply to C1"** → posting is a separate, high-consequence action (public, attributed to the user). Confirm the exact target thread, then post to **that thread only** via `gh api .../replies`. "Post to C1" never covers C2.
- **Resolved + fixed Devin comments** worth a durable lesson → offer to route them to `@debug-memory` once (batched), per the peer-review pattern. Don't auto-run it.

Never generalize one approval to the next comment. Code-fix permission ≠ reply permission ≠ post permission.

---

## Scenario Handling Contract (binding — do not improvise)

| # | Trigger | Required handling |
|---|---------|-------------------|
| S1 | User: "check the PR comments" / "new devin comment" | Fetch real comments (all 3 APIs), analyze, present TABLE, STOP. Never implement on sight. |
| S2 | PBI resolves | Filter every **bot** comment through Out-of-Scope / UI-only / scaffolded caveats before accept/decline; split multi-part comments. |
| S3 | PBI not found | Proceed unanchored; note that bot scope-decline heuristics are weaker; still analyze against code + rules. |
| S4 | About to decline a comment on a "it'd break lint / it's intentional" claim | Open the file and verify the blocker actually exists first. A decline needs the same source-check as an accept. |
| S5 | Perf/consistency/`React.memo` finding | Check sibling (`// mirrors X`), call-frequency, whole-component prop sweep, and fix-is-free before agreeing. Downgrade to 🟢/drop if any fails. |
| S6 | Devin 🔴 "unterminated string" on a line with CJK | Treat as likely false positive; verify by reading the line / noting tsc would fail. Don't escalate or "fix". |
| S7 | About to claim "reviewer X also asked for this" | Grep the actual PR comments first. No hit → don't claim precedent (topic ≠ proximity). |
| S8 | Human vs bot comment | Human = direct authority, default to addressing; bot = stands on code+PBI, form own verdict, don't defer. Tag the column accurately. |
| S9 | User says "implement Cn" | Code change for Cn ONLY. Does not authorize a thread reply. |
| S10 | User says "reply to Cn" | Draft a paste-ready markdown block. Do NOT post without a further explicit "post it". Posting targets that one thread only. |
| S11 | Non-blocking 🟡 deferred on "mock can't fail / API later" | Recommend closing now (this user's preference), unless it needs out-of-scope architectural change. |
| S12 | A new bot false-positive pattern, or a decline whose reasoning generalizes, surfaces during analysis | Offer it as a memory candidate after the table (Step 4.5). Write it only on the user's pick — never auto-write. Grep the memory store first to skip duplicates; if none qualify, stay silent. |
| S13 | User implements a comment (Step 5) and the confirmed-fixed change is a durable lesson | Offer to route to `@debug-memory` once, batched. Don't auto-run. (Distinct from S12: post-fix, via debug-memory; S12 is analysis-time, written directly.) |
| S14 | A comment verdicted ✅/🟡 could recur in a sibling / another diff file | Sweep (Step 2.5): PR-diff files + direct siblings only, never repo-wide. Full sibling-verify each hit or DROP it. List survivors in their OWN section, never merged into reviewer rows. Out-of-scope siblings → `deferred` with reason. Nothing verified → say so, don't manufacture. |

If a real situation matches none of these, handle it conservatively (surface to the user) and note it — do not silently extend the contract.

---

## Guardrails

- **Read-only until told otherwise.** Fetch + analyze + table is the whole default job. No code edits, no `gh api .../replies`, no `gh pr comment`, no resolving threads, **no memory writes** — each needs its own explicit go-ahead. Memory candidates are *offered* (Step 4.5); written only on the user's pick.
- **Never work from memory of the comments** — always fetch the live threads first.
- **Never switch the user's branch or stash their work** — this operates on the live checkout, read-only.
- **Never operate on or modify the default branch.**
- **Verify before asserting** — every verdict (agree *or* disagree) cites a `file:line`. No citation → mark `Undetermined` and say what's missing.
- **Don't inflate.** 1–4 rule-backed items is normal; a padded list buries the real ones. Tier by ✅/🟡/🟢 honestly.
- **Tag bot vs human accurately**; when unsure of bot identity, label `Human?` rather than mislabel.
- The Scenario Handling Contract is binding.
