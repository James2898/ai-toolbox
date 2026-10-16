# Playwright MCP — connecting and driving the app

## Which server (binding)

Use **only** the Playwright MCP named in the project profile (`environments.browser_mcp`), or, without a profile, a Playwright MCP that launches its own browser. Tool names surface as something like:

```
mcp__playwright__browser_*
mcp__plugin_<plugin>_playwright__browser_*
```

Do **not** add another browser-automation MCP, and do **not** use a browser MCP that drives the user's own daily Chrome profile. One browser MCP means the safety configuration has a single place to live; a daily profile carries live production sessions.

### Why an origin guardrail matters

The bare `@playwright/mcp` can be started with an origin allowlist/blocklist:

```
--allowed-origins  <non-production hosts, ';'-separated>
--blocked-origins  <production hosts, ';'-separated>
```

Configured that way, **production is refused at the MCP layer** — not by your carefulness, but structurally. The hosts to block are the ones in `environments.forbidden_hosts`; the local and non-production environments should match the allowlist.

If the configured server has **no** blocklist, you are the only guardrail: check every URL against `{forbidden_hosts}` before navigating, and mention the missing guardrail in the report.

If a navigation is refused as an origin violation, that is the guardrail doing its job. **Do not work around it** — stop and tell the user which origin was blocked.

### Permitted use

Debugging, bug investigation, performance measurement, and e2e test authoring. **Not** for automating internal business processes, and **never** against production. Environments: local and other non-production environments only.

## Connecting

1. **Load the tools** (deferred). One ToolSearch call for the core set, with the server's real prefix:
   ```
   ToolSearch: select:<prefix>browser_navigate,<prefix>browser_evaluate,<prefix>browser_snapshot,<prefix>browser_click,<prefix>browser_type,<prefix>browser_take_screenshot,<prefix>browser_network_requests,<prefix>browser_network_request,<prefix>browser_console_messages,<prefix>browser_wait_for
   ```
   `browser_evaluate` is the workhorse; the rest support it.

2. **Navigate**: `browser_navigate {url:"{local_url}"}`. Playwright launches its **own** browser — separate from the user's Chrome, with no access to their daily cookies or sessions. That isolation is the point; it also means you start logged **out**.

3. **Authentication — the user does it, never you.** Playwright's browser has no app session on a first run. When it lands on a login page:
   - **Ask the user to log in once in the headed Playwright window.** Never type credentials, never fill a password field, never read one from anywhere.
   - If the server is **not** started with `--isolated`, Playwright keeps a persistent profile of its own and that login survives between runs. With `--isolated`, expect to re-login every session (or for the team to supply a saved storage-state).
   - If a run starts on the login page mid-flow, the session expired: pause and ask, do not attempt to re-auth.

4. **If the page renders blank**, read `browser_console_messages` and `browser_network_requests` — a blocked bundle (`ERR_BLOCKED_BY_CLIENT`), a certificate error on a local HTTPS host, or a failed login redirect are the usual causes. Report it rather than switching tools.

## Tool map

| Need | Use |
|---|---|
| Run JS in the page | `browser_evaluate` |
| Click / type | `browser_click`, `browser_type` (refs from `browser_snapshot`) — or `.click()` inside `browser_evaluate` |
| See page structure | `browser_snapshot` (accessibility tree with refs) |
| Network evidence | `browser_network_requests` (list), `browser_network_request` (one, **with body**) |
| Console / JS errors | `browser_console_messages` |
| Screenshot to a real file | `browser_take_screenshot {filename, scale:"css"}` |
| Wait for a condition | `browser_wait_for` |

Two capabilities worth exploiting:

- **Response bodies are readable.** `browser_network_request` returns a single request's body, so a bulk endpoint's per-item status can be read from *the request the UI actually fired* — not only corroborated by a separate seeding call.
- **Screenshots produce real files.** `browser_take_screenshot {filename}` writes to disk (cwd or `.playwright-mcp/`).

## Driving reliably

**Drive through the DOM.** Prefer `browser_evaluate` with `querySelector` + `.click()` over coordinate clicking. Playwright's ref-based `browser_click` is also safe (refs come from the accessibility tree, not pixels) — but for React controlled inputs use the native setter inside `browser_evaluate`:

```js
() => {
  const input = document.querySelector('input[name="confirm"]');
  const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
  setter.call(input, 'DELETE');
  input.dispatchEvent(new Event('input', { bubbles: true }));
  input.dispatchEvent(new Event('change', { bubbles: true }));
}
```

`browser_evaluate` takes a **function**, not a bare statement string — and each call is a fresh evaluation, so anything you stash on `window` (a recorder, an id list) persists only until the next navigation. Re-inject after `browser_navigate`.

## Gotchas

- **Toasts auto-hide fast.** Install the `MutationObserver` recorder via `browser_evaluate` *before* the action, then read `window.__toasts` back in a later call. A screenshot taken a beat late misses the toast entirely.
- **A navigation wipes injected state.** Prefer refreshing inside the app (its own search/refetch) over a full navigate when you need the recorder alive.
- **Close the browser when done**: `browser_close`. Leaving it open holds a profile and, on a shared machine, a live session.
- **Data fetching settles asynchronously** (React Query, SWR, …) — use `browser_wait_for` rather than a bare sleep where possible.
