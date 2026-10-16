---
name: pbi-analyze
description: "Create a durable hardcopy of a PBI (Product Backlog Item) with an appended analysis, so pr-peer-review and other reviewers have a stable reference of what the PR is supposed to satisfy. Takes pasted PBI text, writes <docs-dir>/<PBI-ID>-<slug>.md (default pbi-docs/) containing the verbatim PBI plus a structured analysis (acceptance criteria, scope/out-of-scope, ambiguities & risks, codebase-aware notes). Use when the user wants to save/analyze a PBI, create a PBI reference, or prep a PBI for PR review."
---
# PBI Analyze

Turn a pasted PBI into a durable, analyzed reference document. The output is the source of truth a reviewer (especially the `pr-peer-review` skill) reads to judge whether a PR actually satisfies the backlog item.

The document has two parts:
1. **Verbatim PBI** — an unaltered hardcopy of what the user pasted, so the original is never lost or paraphrased.
2. **Analysis** — appended below, structured into four sections.

---

## Input

- **Pasted text only.** The user provides the PBI body directly in the prompt.
- If no PBI content was pasted, ask the user to paste it. Do not invent or fetch one.

---

## Step 1 — Identify the PBI (ID + slug)

The filename is keyed on **both** an ID and a title slug so it can be found either way: `<PBI-ID>-<slug>.md`.

1. **PBI ID** — look for an explicit ticket key in the pasted text (e.g. `PBI-042`, `JIRA-123`, `#456`, `TASK-007`). 
   - If found, use it verbatim (normalize to uppercase, keep the original separator, e.g. `PBI-042`).
   - If none is present, ask the user for the ID. If they don't have one, fall back to `PBI-<YYYYMMDD>` using today's date.
2. **Slug** — derive a kebab-case slug from the PBI title (first heading or the obvious title line). Lowercase, alphanumeric + hyphens, max ~6 words. E.g. "Add CSV export to dashboard" → `add-csv-export-to-dashboard`.
   - If the title is unclear, ask the user for a short title.

Final filename example: `<docs-dir>/PBI-042-add-csv-export-to-dashboard.md` (`docs.pbi_dir` from the project profile, default `pbi-docs/`).

**Collision check:** if `<docs-dir>/<PBI-ID>-*.md` already exists, surface it to the user and ask whether to overwrite, version (`-v2`), or abort. Never silently clobber an existing PBI hardcopy.

---

## Step 2 — Write the hardcopy + analysis

**Where it goes:** the project profile's `docs.pbi_dir`; without a profile, default to `pbi-docs/` in the repo root. If the project already has a home for specs/tickets (`docs/specs/`, `tickets/`, `.github/specs/`, …), prefer that — check before creating a new folder, so the hardcopy lands where the team already looks. The user can also name a directory explicitly. Create the directory if it doesn't exist, then write the file with this structure:

```markdown
# <PBI-ID> — <PBI Title>

- **Saved:** <YYYY-MM-DD>
- **Source:** Pasted PBI text

---

## PBI (verbatim)

<the user's pasted content, reproduced exactly — do not edit, summarize, or reformat the substance>

---

## Analysis

### Acceptance Criteria
Derive a testable checklist. Each item must be objectively verifiable against a PR — phrase as something a reviewer can mark pass/fail. Pull explicit criteria from the PBI first; where the PBI implies a requirement without stating it as a criterion, add it and mark it `(derived)`.

- [ ] <criterion 1>
- [ ] <criterion 2 (derived)>
- ...

### Scope & Out-of-Scope
- **In scope:** what this PBI explicitly covers.
- **Out of scope:** what it explicitly or implicitly does NOT cover — the boundary a reviewer uses to flag scope creep in the PR.

### Ambiguities & Risks
Open questions, underspecified behavior, edge cases the PBI doesn't address, and risks a reviewer should watch for. Be specific — cite the part of the PBI that's vague. If the PBI is fully unambiguous in some area, say so rather than padding.

### Codebase-Aware Notes
Scan the repo for the files, components, endpoints, and patterns this PBI most likely touches. List concrete `file:path` references the PR is expected to modify, plus any existing code that should be reused rather than reinvented. If a referenced concept has no obvious home in the codebase, flag it as net-new. Verify paths actually exist before listing them — do not guess file names.
```

Keep the verbatim section truly verbatim. The analysis is yours; the PBI is theirs.

---

## Step 3 — Report back

- Print the file path: `<docs-dir>/<PBI-ID>-<slug>.md`.
- Give a 2–3 line summary: how many acceptance criteria, the biggest ambiguity, and the main files the PR is expected to touch.
- Mention that `pr-peer-review` can now reference this PBI by its ID or slug.

---

## Guardrails

- Verbatim PBI section must not be altered, summarized, or "cleaned up."
- Never overwrite an existing PBI hardcopy without asking.
- Codebase-Aware Notes must cite only paths that exist — verify, don't guess.
- Do not commit or push the file unless the user asks.
- Acceptance criteria must be testable; vague aspirational statements belong in Ambiguities, not Acceptance Criteria.
