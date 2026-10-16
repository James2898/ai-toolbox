---
name: live-verify
description: "Live-test a branch's UI changes against the running app (local or another non-production environment) by driving a Playwright MCP browser, then report a pass/fail evidence table. Derives what to test from the git diff (changed files → affected user flows) AND sweeps mirrored siblings for regressions, optionally folding in a validator-agent audit's edge cases (empty-batch, error paths, concurrency). Endpoints and payloads come from the feature's own frontend request layer in the diff, never from recollection. Seeds its own throwaway data (QA-LV- prefix) via the app's API, drives the real UI through the DOM (not screenshot-clicking), captures transient toasts with a MutationObserver, verifies network status codes and response bodies, then auto-cleans up only what it created (incl. orphan sweep by prefix). Strips personal data (ids/statuses only) from all output. Never runs against production or any forbidden host from the project profile. Use whenever the user wants to live-test / live-verify / manually verify a branch's frontend changes, \"test the PR on the running app\", \"verify the fix in the browser\", \"does this actually work live\", concurrency/error-toast behavior, or regression on affected flows."
---

> **Running in Antigravity**: this skill is generated from the Claude Code source.
> - `ask_question` is Antigravity's interactive question tool (Claude Code: AskUserQuestion).
> - Names starting with `mcp__` are Claude Code MCP tool names; use the same server's tool as configured in Antigravity's mcp_config.json.

# Live Verify

Drive the **real running app** to prove a branch's UI changes actually work — end to end, with recorded evidence — instead of trusting unit tests alone. Driving is done with a **Playwright MCP** (`{browser_mcp}`), which launches its own browser; ideally it is configured with an origin allowlist/blocklist that refuses production.

> **Tooling is not a free choice here.** Do **not** use Claude in Chrome, `chrome-devtools-mcp`, Browser MCP, or any MCP that drives the user's own daily Chrome profile — a daily profile carries live production sessions and has no origin guardrail. If the team has standardised on one browser MCP, use that one only. See `references/playwright-mcp.md`.

The deliverable is a **pass/fail evidence table**: per case, the recorded toast text, the network status codes, and the UI state (modal/drawer open? list refreshed?) — each a concrete artifact, not "looks right."

## The core lesson that makes this reliable

**Drive through the DOM, not by clicking screenshot coordinates.** The screenshot coordinate space and the live viewport differ (and on a HiDPI display `devicePixelRatio` skews them again), so coordinate clicks miss small targets like checkboxes. Coordinate-clicking is the usual source of flaky runs; driving through the DOM is the reliable path. Playwright's ref-based `browser_click` is also safe — refs come from the accessibility tree, not pixels. Concretely:

- Click via `element.click()` — a native click fires React's handlers correctly. No coordinates.
- Set controlled inputs with React's native setter, or they won't register:
  ```js
  var setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
  setter.call(input, 'DELETE');
  input.dispatchEvent(new Event('input', { bubbles: true }));
  ```
- **Toasts auto-hide fast** — a screenshot taken a beat late misses them. Install a `MutationObserver` BEFORE the action to record any toast text that appears (pattern in `references/api-and-dom.md`).
- **The network response body is the authoritative signal** for backend behavior (e.g. a bulk endpoint that returns a transport 200 with per-item statuses in the body). The UI toast proves the *frontend* branched correctly on it.

Use `browser_evaluate` for all DOM work. Use screenshots only to *look* (confirm a drawer opened) or to produce PR evidence, never as the primary driver.

## Guardrails (binding)

- **Tooling.** Only the Playwright MCP named in `{browser_mcp}`. No other browser-automation MCP, and never one attached to the user's daily Chrome profile. If those tools are unavailable, **stop and say so** — do not substitute another browser tool.
- **Environments.** `{local_url}`, or `{baseline_url}` / another non-production environment the user names. **Never production, never any host in `{forbidden_hosts}`.** If the MCP refuses an origin, report it — never route around it.
- **Purpose.** Debugging, bug investigation, performance measurement, e2e test authoring. Not internal-process automation, not production data work.
- **Seed + auto-cleanup, with an identifiable prefix.** Create your own throwaway entities via the app's API, and **name every one with the run prefix `QA-LV-<HHMM>-`** (e.g. `QA-LV-1432-grpA`) so seeded data is recognizable even if the in-memory id list is lost. Delete ONLY what you created; never touch pre-existing data.
- **Deletes hit seeded ids only.** A delete/irreversible step in this skill targets exclusively ids you created *this run*. If a case appears to need deleting or mutating **pre-existing** data, that is outside this skill's remit — **stop and ask the user**; do not proceed on assumed permission. (This skill does not self-authorize destructive actions beyond its own seeded entities.)
- **Personal data.** Local and test APIs often return real-looking personal data (emails, names). Never put it in output, memory, or artifacts — report **ids and statuses only**. If you observe it, note once that the API returns it and move on; do not reproduce values.
- **Credentials.** Never type passwords, never fill a password field, never read one from a file or a manager. Playwright's browser starts logged **out** — ask the user to log in once in its headed window, then continue. If a session expires mid-run, pause and ask; do not attempt to re-auth.
- **Read-only on code.** This skill verifies; it does not edit source, commit, or push.

## Project settings

This skill reads the project profile (see the toolbox README): `AI_TOOLBOX_PROFILE`, else `<project root>/.ai-toolbox/profile.yml`. Placeholders used below:

| Placeholder | Profile key | Without a profile |
|---|---|---|
| `{local_url}` | `environments.local_url` | ask |
| `{baseline_url}` | `environments.baseline_url` | skip; test the local app only |
| `{forbidden_hosts}` | `environments.forbidden_hosts` | never production; ask which hosts that covers |
| `{browser_mcp}` | `environments.browser_mcp` | any Playwright MCP that launches its own browser (`mcp__*playwright*__browser_*`); ask if several exist |
| `{default_base}` | `git.default_base` | the PR's base, else the repo's default branch |
| `{topic_bases}` | `git.topic_bases` | none: use the PR's own base |
| `{client_layer}` | `api.client_layer` | find where the frontend calls the API |
| `{build_logs}` | `commands.build_logs` | skip; rely on the served-bundle grep |
| `{qa_out_dir}` | `docs.qa_out_dir` | `.qa/` (keep it gitignored) |
| `{memory_dir}` | `docs.memory_dir` | Claude Code's auto-memory directory for this project, if one exists; otherwise skip the memory pass and say so |

## Workflow

### Step 0 — Resolve the branch and confirm the env is testable

1. `git branch --show-current` and `git log --oneline <base>..HEAD` (base is the PR's base — one of `{topic_bases}` or `{default_base}`; infer from the branch, or ask).
2. Confirm the **served bundle** — not just the source — contains the change. Grep a signature symbol from the diff in the working tree first; then confirm it reached the browser: after connecting (Step 2), grep the loaded JS for the same signature (a new locale key or function name), or check the frontend build has no error (`{build_logs}`). A watch-mode build usually rebuilds, but a mid-build/errored bundle serves stale code and yields a misleading result. If you can't confirm the signature is served, say so before testing rather than reporting a false pass/fail.
3. Confirm the services behind `{local_url}` are up (e.g. `docker ps`, or the dev server's process).
4. **Apply the env traps from stored memory** (the grep in Step 1 — run it first if you have not). Local environments tend to have recurring, already-diagnosed failure modes that silently produce false passes and false failures; check the ones that apply before driving anything, and say which you checked.

### Step 1 — Derive the test plan (diff → flows + sibling sweep + memory + validator dims)

Run these in parallel:

- **Diff → affected flows.** `git diff <base>...HEAD --name-only`. Map each changed file to a user-facing flow. A hook like `useDeleteWidgets.ts` → the widget list bulk-delete flow. A drawer hook → that drawer's open/edit/save. Read the changed files to enumerate the *branches* the change introduces (e.g. all-success / partial / all-failed) — each branch is a case.
  - **Endpoints for the plan come from the DIFF, not from recollection.** (Distinct from the stored-memory pass below — that supplies env traps and past bugs, never endpoint shapes.) Derive the endpoints and payloads from the feature's own request functions in `{client_layer}` touched or called by the diff; `references/api-and-dom.md` explains how. The reference file holds the *technique* (DOM/toast/request snippets), which is feature-agnostic — never a fixed endpoint list.
- **Sibling sweep (regression).** Find mirrored/adjacent code the change could affect — look for `// mirrors X` comments, the create↔edit twin, the parent↔child counterpart (e.g. a list and its nested items). If the change touches a shared classifier or pattern, the sibling flow is a regression case. (Bounded: PR-diff files + direct siblings only, never repo-wide — same discipline as pr-comment-triage's sweep.)
- **Stored memory (env traps + past bugs).** Grep `{memory_dir}` for the files, components and feature area in the diff, plus the env itself. Nothing in this chain reads memory automatically, so lessons already paid for silently fail to reach the test plan unless you pull them:
  ```bash
  grep -rilE "<component>|<feature>|verify|env|bundle" {memory_dir}
  ```
  Two kinds earn their place in the plan. **Env/harness traps** become preconditions to check before trusting any result — the stale served bundle, browser-cached bundles giving false negatives, SSO/login env quirks, multi-tenant routing. **Past bugs in this area** become regression cases: a bug previously fixed in the flow you are about to touch is exactly what a live pass should re-prove. Skip keyword-only matches; an irrelevant memory just inflates the case list.
- **Validator dimensions (optional but recommended).** Spawn `validator-agent` in the background against the diff (brief it with the same memory hits — it cannot read memory itself). Turn its findings and edge-cases (empty-batch, error/404 paths, concurrency races, permission tiers) into additional live cases. Fold in when it returns. If no validator agent is available, skip and say so.

Produce a short **numbered case list** before touching the app: each case = a precondition to seed, an action to drive, and the expected evidence (toast text / network status / UI state). For anything you're unsure the diff intends, read the code — don't guess the expected outcome.

### Step 2 — Start the Playwright browser

See `references/playwright-mcp.md` for the exact call sequence, the tool map, and the auth story. In short:

1. `ToolSearch` for the server's core set — `{browser_mcp}` tools `browser_{navigate,evaluate,snapshot,click,type,take_screenshot,network_requests,console_messages,wait_for}`. If no permitted server resolves, **stop** — say the Playwright MCP isn't available rather than reaching for another browser tool.
2. `browser_navigate {url:"{local_url}"}` (or the non-production host under test — never production, never `{forbidden_hosts}`).
3. **If it lands on a login page**, ask the user to log in once in the headed Playwright window, then continue. Never type credentials. If the MCP keeps a persistent Playwright-owned profile, that login normally survives later runs.

### Step 3 — Seed → drive → capture, per case

For each case, do everything through `browser_evaluate` on the app page (same-origin, uses the browser's session cookies). See `references/api-and-dom.md` for the reusable snippets: the `req()` helper, the toast-recorder, the React-safe input setter, and how to find endpoints/payloads in `{client_layer}`. Note `browser_evaluate` takes a **function**, and injected `window.__*` state dies on navigation — re-inject after any `browser_navigate`.

The reliable loop:

1. **Arm evidence capture first.** Install the toast `MutationObserver` — BEFORE the action, or you miss the transient toast.
2. **Seed the precondition** via API `req(...)` — create the entities this case needs; record their ids in your cleanup list. For a **concurrency race**, seed the entity, open its edit UI, then delete it via API mid-flow so the subsequent save/confirm hits the now-gone entity (this is how you reproduce "already deleted elsewhere" in a single tab — no second tab needed, which is more robust).
3. **Drive the real UI** through the DOM: `.click()` the real buttons/checkboxes, set inputs with the native setter. Confirm the drawer/modal opened by reading the DOM (find the confirm input / submit button), not by eyeballing a screenshot.
4. **Read back the evidence**: the recorder's captured toast text, whether the modal/drawer is still open (query for its element), whether the list refreshed (count), and the network evidence — `browser_network_requests` for the list, then `browser_network_request` on the matching entry to read **the response body of the request the UI actually fired**. That last part matters: a bulk endpoint's per-item statuses can be quoted from the observed request itself, rather than only corroborated by a separate `req()` call. The toast + UI state remain the direct proof the frontend branched correctly; the body is why.
5. **Screenshot the decisive moment (if the user wants PR evidence).** Ask up front whether screenshots are wanted; if yes, capture at the moment the evidence is visible — the toast on screen, the modal still open.
   - `browser_take_screenshot {filename: "<case>.png", scale: "css"}` writes a real file to the cwd (or `.playwright-mcp/`); `mv` it into `{qa_out_dir}/live-verify/<slug>/`. `browser_resize` first if the layout needs a sane width.
   - The verification and the screenshot happen in the *same* Playwright browser, so a transient toast fired by your driving IS visible to the screenshot. Still fire the shot immediately after the confirming click; toasts auto-hide in seconds. If you missed it, re-run the case rather than shipping a shot without the toast.
   Name files by case (`all-gone-danger.png`, `mixed-warning.png`) so they're self-describing in the PR.
6. **Record** the row: case, expected, observed toast/status/UI, screenshot path (if taken), PASS/FAIL.

### Step 4 — Cleanup (with orphan recovery)

Delete every id you created (and only those), via the API. Then **sweep for orphans**: list the relevant entities and delete any whose name carries the `QA-LV-` prefix — this catches entities seeded by a run that crashed before its in-memory id list could be used. The prefix is what makes leftover test data recognizable across sessions, so the in-memory list is a convenience, not the only safety net. Only ever delete `QA-LV-`-prefixed entities you can confirm are test data; never delete anything without the prefix. Report what was cleaned and confirm the seeded set is gone (each id → 404).

### Step 5 — Report

Present the evidence table and a one-line verdict per bug/flow. Structure:

```markdown
## Live verification — <branch>

| # | Case | Expected | Toast (recorded) | Network | UI state | Verdict |
|---|------|----------|------------------|---------|----------|---------|
| 1 | all-success delete | success toast + refresh | "…deleted successfully" | 200, items[200] | modal closed, list -1 | ✅ |
| 2 | concurrent-delete | error toast + stays open | "…error…" | 200, items[404] | modal open, edits kept | ✅ |

**Regression (sibling flows):** …
**Memory applied:** … (which stored lessons shaped the plan — env traps checked, past-bug regressions re-proved; say "none applicable" rather than omitting the line)
**Validator cross-check:** … (if run)
**Seeded/cleaned:** created ids […], all deleted. No pre-existing data touched.
**Personal data:** API responses include personal fields; output kept to ids/statuses only.
```

**If screenshots were taken**, add a ready-to-paste PR-evidence snippet after the table. GitHub can't take image files from the CLI — the user drags each file into the PR description where the placeholder sits, and GitHub replaces it with the hosted image:

```markdown
### Live verification evidence
| Case | Screenshot |
|---|---|
| all-gone → danger toast, modal stays | *(drag `{qa_out_dir}/live-verify/<slug>/all-gone-danger.png` here)* |
| mixed → warning with count | *(drag `mixed-warning.png` here)* |
```

Also check the screenshots before handing them over: **no personal data visible** (real names/emails in table rows count) — if a shot shows personal data, either crop it or re-run the case against seeded `QA-LV-` entities only.

Then STOP — report only; do not change code or open PRs. If a case FAILED, describe the exact observed vs expected and where in the diff the gap is; let the user decide the fix.

## When a case can't be driven from the UI

If a flow genuinely can't be reached by the DOM (missing fixture data, a picker with no options, a state the UI can't produce), say so and fall back to the **API-level proof**: call the endpoint directly and assert the response shape the UI branches on (e.g. a per-item status envelope). Mark it clearly as "backend-condition verified, UI branch inferred from unit tests" rather than claiming a full live pass. Don't manufacture a green result.

## Reference files

- `references/playwright-mcp.md` — which MCP to use and why, the origin guardrail, connecting, the auth story, the tool map, and gotchas.
- `references/api-and-dom.md` — reusable JS snippets (req helper, toast recorder, React-safe setter), how to discover endpoints/payloads from the frontend request layer, and the seed→race→cleanup pattern.
