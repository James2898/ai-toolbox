# API + DOM techniques for live verification

All snippets run via the Playwright MCP's `browser_evaluate` on the app page (`{local_url}`, or another non-production host — never production, never `{forbidden_hosts}`). Same-origin, so they use the browser's session cookies. `browser_evaluate` takes a **function** and returns its value serialized, so **return a JSON string** for anything structured.

**Async is supported** — an `async () => { … await fetch(…) … }` works, so prefer plain `fetch` + `await` over the sync-XHR helper below when you just need a result inline. Injected `window.__*` state does not survive a `browser_navigate`; re-inject after navigating.

## Discovering endpoints from the frontend request layer

Never write endpoints or payloads from memory — derive them from the code the UI actually calls, so a test exercises the same contract.

1. **Start from the diff.** For each changed hook/component, follow its imports down to the request function it calls — typically in `{client_layer}` (a `Request.ts`, `api.ts`, `client/*.ts`, a generated SDK, …). Without a profile, grep for the HTTP client: `grep -rnE "axios|fetch\(|\.get\(|\.post\(" <frontend src> | grep -v test`.
2. **Read the request function, not just its name.** Record: method, path (including any trailing slash — some servers redirect a missing slash and drop the body), query params, request body type, and response type.
3. **Read the headers the shared client adds.** Base path, CSRF token, `X-Requested-With`, auth header, content type. Your `req()` helper must send the same ones or the server may reject it for a reason the UI never hits.
4. **Find the list/detail/create/delete endpoints for every entity you will seed**, even if the diff doesn't touch them — you need them for seeding, existence checks and cleanup.
5. **Note constraints that affect seeding.** Required fields (often ≥1 related id), uniqueness rules (an id may only belong to one parent), and which related ids you must look up first (e.g. `GET` a users or categories list and pick ids).
6. **Note the response envelope.** Does a bulk endpoint return transport 200 with per-item statuses in the body, or a real 4xx? This decides what the UI branches on and what you assert.
7. **Cross-check against the API spec or backend handler** if one exists; when they disagree with the frontend, report it rather than picking one.

Record the endpoints you will use at the top of the run's case list, so the evidence table can be traced back to them.

## Core helper: synchronous request

Kept for the case where a genuinely blocking call is simpler to reason about (and as the fallback if a harness ever refuses async). Sync XHR is deprecated and blocks the page thread — acceptable for a short-lived test harness, not for app code. With `browser_evaluate`, `await fetch(...)` is usually the better choice.

```js
function req(method, url, body){
  var x = new XMLHttpRequest();
  x.open(method, url, false); // sync so the result returns inline (see note above)
  // Mirror the headers the app's shared HTTP client sends (see "Discovering endpoints", step 3).
  x.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
  x.setRequestHeader('Content-Type', 'application/json');
  try { x.send(body ? JSON.stringify(body) : null); }
  catch(e){ return { status: 0, err: e.message }; }
  var p = null; try { p = JSON.parse(x.responseText); } catch(_){}
  return { status: x.status, body: p };
}
```

Async equivalent:

```js
async () => {
  const r = await fetch('/api/widgets/', { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
  const body = await r.json().catch(() => null);
  return JSON.stringify({ status: r.status, ids: (body?.items || []).map(i => i.id) });
}
```

## Seeding throwaway data with a prefix

- **Name every seeded entity with the run prefix** `QA-LV-<HHMM>-<role>` (e.g. `QA-LV-1432-grpA`). The prefix is what lets a later run — or a human — recognize and remove leftovers if the in-memory id list is lost.
- **Keep an array of every id you create** on `window.__created` (re-inject after navigation) and in your own notes.
- **Respect the constraints you found** in discovery. If a create fails on a uniqueness rule (e.g. a related id may only be used once), either free that id by deleting a *seeded* entity that holds it, or **skip the case and report it as "not seeded — pool exhausted"** rather than misreporting.
- **Prefer the simplest valid shape.** If a variant of the entity needs fewer related records, seed that one unless the case is about the other variant.
- Never seed by editing pre-existing records.

```js
async () => {
  const prefix = 'QA-LV-' + new Date().toTimeString().slice(0,5).replace(':','') + '-';
  const r = await fetch('/api/widgets/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
    body: JSON.stringify({ name: prefix + 'a' /* plus required fields from the request type */ }),
  });
  const body = await r.json().catch(() => null);
  window.__created = (window.__created || []).concat(body?.id ? [body.id] : []);
  return JSON.stringify({ status: r.status, id: body?.id });
}
```

(`/api/widgets/` is a stand-in — use the real path and body from the request layer.)

## Toast recorder (install BEFORE the action)

Toasts auto-hide, so a late screenshot misses them. **Record by container/role, not by matching expected text** — a text regex silently drops any toast whose wording you didn't anticipate, producing a false "no toast" (and a false FAIL). Capture every toast-ish element's text and filter when *reporting*, not when *recording*, so an unexpected message is still seen:

```js
window.__toasts = [];
if (window.__toastObs) window.__toastObs.disconnect();
function isToast(n){
  // Match structurally (role/class), not by copy.
  var cls = (n.className && n.className.toString) ? n.className.toString() : '';
  return n.getAttribute && (
    n.getAttribute('role') === 'alert' ||
    n.getAttribute('role') === 'status' ||
    /toast/i.test(cls) || /alert/i.test(cls) || /snackbar|notification/i.test(cls)
  );
}
window.__toastObs = new MutationObserver(function(muts){
  muts.forEach(function(m){
    Array.prototype.forEach.call(m.addedNodes, function(n){
      if (n.nodeType === 1){
        var hit = isToast(n) ? n : (n.querySelector ? n.querySelector('[role="alert"],[role="status"],[class*="toast"],[class*="Toast"],[class*="alert"],[class*="snackbar"]') : null);
        var t = hit && (hit.innerText || '').trim();
        if (t) window.__toasts.push(t.slice(0, 160));
      }
    });
  });
});
window.__toastObs.observe(document.body, { childList: true, subtree: true });
```

If the structural match proves too broad/narrow for a given screen, inspect one real toast's DOM first (`browser_snapshot` or a quick `querySelector`) and tune `isToast`. Read it back after the action: return `JSON.stringify({ toasts: window.__toasts })`. Re-install after any full page `navigate` (injected state is wiped).

## React-safe input setter

A plain `input.value = 'x'` does NOT trigger React's onChange (controlled inputs revert). Use the native setter + dispatch:

```js
function setReactInput(input, value){
  var proto = input.tagName === 'TEXTAREA' ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
  var setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
  setter.call(input, value);
  input.dispatchEvent(new Event('input', { bubbles: true }));
  input.dispatchEvent(new Event('change', { bubbles: true }));
}
```

## Clicking real controls

`element.click()` fires React handlers correctly (unlike coordinate clicks). Find elements by text or attribute:

```js
// a button by its label
var btn = Array.from(document.querySelectorAll('button'))
  .filter(function(b){ return b.textContent.trim().toLowerCase() === 'delete'; });
// there can be several (toolbar + modal confirm) — the modal confirm is usually the LAST
btn[btn.length - 1].click();

// a checkbox inside the row containing a seeded name
var row = Array.from(document.querySelectorAll('tr')).find(function(r){ return /QA-LV-1432-a/.test(r.innerText); });
var box = row && row.querySelector('input[type="checkbox"]');
if (box && !box.checked) box.click();   // native click toggles + fires onChange; verify box.checked after
```

Always verify state after a click (`box.checked`, or the confirm button's `disabled`) — don't assume.

## Network checks

- **List** with `browser_network_requests`, filter to the endpoint you expect, and confirm the UI fired **exactly** the requests you expect (count matters — a double-submit or a missing refetch shows up here).
- **Read one** with `browser_network_request` to get the response body of the request the UI actually fired. Quote the status and the fields the UI branches on (e.g. per-item statuses), mapped to ids only.
- **Check the absence of requests** too: a guard that should block a call is proven by no request appearing.
- **Console**: `browser_console_messages` after each case; an uncaught error during the action is a finding even if the toast looked right.
- For transport-200 bulk endpoints, the status code alone proves nothing — always read the body.

## The seed → race → cleanup pattern (single-tab concurrency)

To reproduce "entity deleted elsewhere while I was editing" without a second tab:

1. Seed the entity via `req(POST ...)`; record its id.
2. Open its edit UI (navigate to the list, `.click()` its Edit button); make a small edit with `setReactInput`.
3. **Concurrently delete it** via the API — now it's gone server-side while your UI still shows it.
4. Arm the recorder, click Save/Submit/Confirm.
5. Read back: recorded toast + network evidence (the save request should be 404, or a bulk body's per-item status 404) + is the drawer/modal still open + are edits preserved.

## Cleanup

Two layers, because the in-memory id list is lost if the run crashes:

1. **By id** — delete every id you created at the end (and in a `finally`-style pass even if a case failed), using the delete or bulk-delete endpoint you found in discovery.
2. **By prefix (orphan sweep)** — list the entities and delete any whose name starts with the `QA-LV-` prefix, catching anything a crashed earlier run left behind:
   ```js
   async () => {
     const r = await fetch('/api/widgets/?per_page=200', { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
     const list = await r.json().catch(() => null);
     const items = (list && (list.items || list.data || list)) || [];
     const orphanIds = items.filter(i => /^QA-LV-/.test(i.name)).map(i => i.id);
     // delete orphanIds with the real delete endpoint, then confirm each GET → 404
     return JSON.stringify({ orphanIds });
   }
   ```
   Only ever delete `QA-LV-`-prefixed entities. Then verify each deleted id is 404. **Never delete ids you didn't create / that lack the prefix.**

## Personal-data discipline

List and detail responses often embed personal fields (`email`, names). When returning anything from a seed/list call, **map to ids + statuses only** before returning — e.g. `items.map(i => ({ id: i.id, status: i.status }))`. Never let an email reach the transcript, memory, or the report. Note once that the API returns personal data, then proceed.
