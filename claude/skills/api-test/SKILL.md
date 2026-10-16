---
name: api-test
description: Write endpoint test cases as concrete request/response pairs for an API endpoint or feature — happy paths, each validation failure, auth and permission (401/403 by persona), cross-company isolation, not-found, conflict/consistency, duplicates, pagination and filter params, trailing-slash and header traps — each with method, URL, headers, body, expected status, expected body shape and side effects, derived from the real contract (the API spec, the frontend request layer, and the backend handler's request/response shapes and error codes, located through the project profile). Writes {qa_out_dir}/<slug>/api-test.md; sends requests only on request and only to the local app. Use whenever the user asks for API test cases, endpoint tests, request/response examples, contract tests, "what should this endpoint return when…", or wants an endpoint checked against its spec.
allowed-tools:
  - Bash
  - Read
  - Write
  - Glob
  - Grep
  - AskUserQuestion
user-invocable: true
---

# API Test Cases

Produce request/response pairs a reviewer or a test author can execute verbatim. Sidecar of the QA chain; output goes to `{qa_out_dir}/<slug>/api-test.md`.

## Project settings

This skill reads the project profile (see the toolbox README): `AI_TOOLBOX_PROFILE`, else `<project root>/.ai-toolbox/profile.yml`. Placeholders used below:

| Placeholder | Profile key | Without a profile |
|---|---|---|
| `{qa_out_dir}` | `docs.qa_out_dir` | `.qa/` (keep it gitignored) |
| `{api_spec}` | `docs.api_spec` | search for `openapi*.y*ml` or `swagger*` |
| `{client_layer}` | `api.client_layer` | find where the frontend calls the API |
| `{handler_layer}` | `api.handler_layer` | find the backend route handlers |
| `{local_url}` | `environments.local_url` | ask |
| `{forbidden_hosts}` | `environments.forbidden_hosts` | never production |

## Inputs

`$ARGUMENTS`: an endpoint (`GET /api/v1/orders`), a feature name (`orders`), a frontend request file, a backend handler file, a PR number, or a slug. Flags: `--out=<dir>`, `--persona=<role>` (restrict personas), `--run` (execute against the local app after confirmation). Nothing provided → ask.

## Step 1 — Locate the contract (and note disagreements)

Read all layers that describe the endpoint; they are supposed to agree, and when they do not, that is a finding to report rather than a choice to make silently.

| Layer | Where | What it gives |
|---|---|---|
| Spec | `{api_spec}`: find the path and method | request/response schema, documented statuses |
| FE client | the feature's request function under `{client_layer}` | the exact URL, params, request body type, response type |
| FE transport | the shared HTTP client the request functions use | headers the app always sends (content type, session cookie, custom headers) |
| BE handler | `{handler_layer}` | request binding and validation rules, response shape, permission checks |
| BE business logic | the service layer behind the handler | business errors and their error codes |
| Tests | tests next to the handler | the exact status codes and error-body shape the team asserts |

Without a profile, find them in this order: OpenAPI or route file → controller → validation → existing tests.

## Step 2 — Enumerate the cases

| Category | Derive from | Typical expectation |
|---|---|---|
| Happy — minimal | required fields only | 200/201 + response shape |
| Happy — full | every optional field | same, optional fields echoed |
| Validation — missing | each `required` field, one case per field | 400/422 + the error key for that field |
| Validation — type/format/boundary | length limits, numeric min/max and max+1, date formats and ranges, enum outside the set | error key per rule |
| Auth — no session | request without the cookie | 401 (or the app's actual redirect — check a test) |
| Permission | each persona lacking the gate flag | 403 (the project's permission error) |
| Tenant isolation | an id belonging to another company | 404 or 403 — whichever the code does; never 200 |
| Not found | unknown id | 404 (`NewNoResourceErr`) |
| Consistency / conflict | duplicate name, invalid state transition, deleted parent | 409/400 with `NewConsistencyErr` key |
| Idempotency | same write twice | second response documented |
| Pagination | `page`/`perPage` defaults, last page, out of range, perPage above the cap | counts + total |
| Filters | multi-value params: check whether the backend combines them with OR or AND, and test one case with two values | the documented match set |
| Sorting | each sortable column, asc/desc, invalid column | order or 400 |
| Transport traps | trailing slash on a write (a redirect can drop the body), missing custom headers (hand-built requests often fail with 403) | documented, so nobody debugs them twice |

Skip categories the endpoint cannot hit (a GET has no body validation); say so in one line.

## Step 3 — Write each case

```markdown
### AT-001 — <category>: <summary>
- **Persona:** <role + permission flags>   **Source:** `<file:line>` / `openapi.yaml#<path>`
- **Request**
  `<METHOD> <URL with params>`
  Headers: `Content-Type: application/json`, session cookie, <custom headers from the transport layer>
  ```json
  { … }
  ```
- **Expected**
  Status: `<code>`
  Body shape: `{ field: type, … }` — list fields and types, not a full payload, unless a value is the point
  Error key: `<project error code>` (if any)
- **Side effects:** <rows created/updated → `/test-data` case ids, or "none">
- **Notes:** <spec/code disagreement, assumption marked 推測>
```

Headers matter: copy what the app's HTTP client sends. Requests built by hand without them can fail with 403 in the local environment, and that failure looks like a permission bug.

## Step 4 — Optional execution (`--run`)

Only against `{local_url}` (the branch under test), with a session cookie the user supplies, after `AskUserQuestion` lists the requests about to be sent (writes included). Never a host in `{forbidden_hosts}`, and never a shared or production environment. Record `Actual: <status> <body excerpt>` under each case; a mismatch with Expected is a finding (spec drift, code bug, or wrong expectation — say which you think and why).

## Step 5 — Write and report

File header:

```markdown
# API Tests — <endpoint / feature>
- **Contract sources:** <spec path>, <frontend request file>, <handler>, <tests>
- **Date:** <YYYY-MM-DD>   **Cases:** <n>   **Spec vs code disagreements:** <n or none>

## Disagreements
| Where | Spec says | Code does | Suggested fix |

## Cases
<AT-001 … >
```

Report: path, case count by category, disagreements, and whether `--run` happened.

## Notes

- Personas are roles plus flags; never real accounts or real credentials.
- Response "shape" means fields and types. Full payloads go stale with every fixture change.
- Pair with `/test-data` for cases that need rows to exist first, and `/regression-test` when the endpoint has other consumers.
