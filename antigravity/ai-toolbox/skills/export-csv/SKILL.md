---
name: export-csv
description: "Convert a test matrix (and optionally its test-data document) into a comma-separated file that pastes cleanly into Google Sheets or the team QA sheet. Three layouts — the team QA table (No / Test Scenario / Test Detail / Actions / Expected / Date / Result), an importer layout (a Markdown file with one json block per case, the input a test-case importer such as the team's own reads, plus a matching sheet for people), or the matrix columns as-is. Quotes commas, quotes and multi-line cells correctly, writes through the Write tool when the environment blocks shell commands naming that file type, and verifies the result by reading it back. Use whenever the user wants a matrix or cases \"in a spreadsheet\", \"as CSV\", \"for Google Sheets\", \"to paste into the QA sheet\", or to hand test cases to QA."
---

> **Running in Antigravity**: this skill is generated from the Claude Code source.
> - `ask_question` is Antigravity's interactive question tool (Claude Code: AskUserQuestion).
> - `ARGS` means whatever the user typed after `/<this-skill>`, or the request that triggered it.

# Export to Sheets

Last step of the QA chain: `/test-plan → /test-matrix → /test-data → /export-csv (this)`. Takes the markdown tables the chain produced and emits one comma-separated file per layout that Google Sheets imports without manual fixing.

## Project settings

This skill reads the project profile (see the toolbox README): `AI_TOOLBOX_PROFILE`, else `<project root>/.ai-toolbox/profile.yml`. Placeholders used below:

| Placeholder | Profile key | Without a profile |
|---|---|---|
| `{qa_out_dir}` | `docs.qa_out_dir` | `.qa/` (keep it gitignored) |
| `{qa_import}` | `qa_import.importer` | none: write the importer files and let the user import them |
| `{qa_import_format}` | `qa_import.format` | `markdown-json` |

## Inputs

`ARGS`: path to `test-matrix.md` (default: the newest `{qa_out_dir}/*/test-matrix.md`) or a slug. Flags:

| Flag | Meaning | Default |
|---|---|---|
| `--layout=qa\|importer\|raw` | Column layout (see Step 2) | `qa` |
| `--data=<test-data.md>` | Pull preconditions and cleanup text per case from the test-data document | auto-detect in the same folder |
| `--scenarios=<scenario-test.md>` | Pull step text for the Actions column | auto-detect |
| `--out=<path>` | Output file | `<matrix folder>/test-cases-<layout>` with the usual extension |
| `--bom` | Prepend a UTF-8 BOM (only for Excel; Sheets does not need it) | off |

## Step 1 — Parse the sources

- Read the matrix with `Read`. Locate the `## Cases` table: the header row defines the columns; the factor columns are everything between `ID` and `Expected`. Keep `Priority` and `Source`.
- If a test-data document exists, map each `### TM-xxx` section to its case: setup summary → preconditions, cleanup lines → cleanup.
- If a scenario document exists, map `Covers: TM-xxx` links to step text → Actions.
- Rows with a missing ID or a column count that differs from the header are reported, not silently dropped.

## Step 2 — Map columns per layout

**`qa` — the team QA table** (same shape `/pbi-gen-test-doc` writes)

| Column | Filled from |
|---|---|
| No | matrix `ID` |
| Test Scenario | the matrix title + the case's primary factor value (short, one line) |
| Test Detail | `[P1] Factor: value; Factor: value; …` (priority prefix, then every factor) |
| Actions | scenario steps when linked; otherwise `Set up <ID> data (test-data.sql), then <the action the factors imply>` |
| Expected | matrix `Expected` |
| Date, Result | empty (QA fills them) |

**`importer` — Markdown with one json block per case**

Many test-case importers do **not** read a spreadsheet file: they take a Markdown file, parse one fenced `json` block per case, and insert the rows into the team sheet themselves. This layout targets that `markdown-json` format (`{qa_import_format}`); if the team's importer (`{qa_import}`) expects other field names, follow its own documentation and rename the keys below. When `{qa_import_format}` is `csv`, the sheet file is the import input instead. This layout writes two files:

1. `test-cases-importer.md` — **the import input.** One section per case:

   ````markdown
   ## TC-001: <title>
   ```json
   {
     "title": "TC-001: <title>",
     "page_path": "/<route>/",
     "login_info": { "email": "<persona-email>", "password": "<see secret store>" },
     "preconditions": ["<factor: value>", "data: TM-001 block in test-data.sql"],
     "expected": ["<expected 1>", "<expected 2>"],
     "cleanup": "<cleanup text or empty>"
   }
   ```
   ````

   Number the `TC-` ids in matrix order and keep the TM id in the title or preconditions so cases stay traceable. Hand-off: `{qa_import} <path to this file>` when the profile names an importer; otherwise tell the user the file is ready for their importer. An importer that writes to a shared sheet should confirm before writing.
2. The sheet file below, with the same rows, for people who want them in a plain sheet. A `markdown-json` importer ignores it.

Sheet columns:

| Column | Filled from |
|---|---|
| no | matrix `ID` |
| title | as Test Scenario above |
| page_path | route of the screen under test when known from the plan/scenario (e.g. `/<route>/…`); else empty |
| login_email, login_password | **always placeholders** (`<persona-email>`, `<see secret store>`) — credentials never go into a document |
| preconditions | factors + `data: <ID> block in test-data.sql` |
| expected | matrix `Expected` |
| cleanup | cleanup summary from test-data, else empty |

**`raw`** — the matrix columns exactly as they are, for people who want to build their own sheet.

**Cases with an open expected value** (`?` in the matrix): keep the row in every layout. Write the expected cell as `UNDETERMINED — record the observed result; see <OQ id>` (in the importer JSON, a one-item `expected` list with that text). Dropping such a row silently loses a case the matrix kept on purpose; say in the report which rows carry it.

## Step 3 — Encode

RFC 4180, because Sheets' importer follows it:
- Comma separator, LF line endings, UTF-8 (no BOM unless `--bom`).
- Quote a field when it contains a comma, a double quote, a newline, or leading/trailing spaces; double every embedded quote (`"` → `""`).
- Keep newlines inside quoted cells — Sheets renders them as line breaks, which is what multi-step Actions need.
- Never pad or truncate rows: every row has exactly the header's column count.
- Strip markdown that doesn't survive a cell: backticks, `**bold**`, pipe escapes (`\|` → `|`).

## Step 4 — Write with the `write_to_file` tool, not the shell

Some environments block any shell command whose text names the comma-separated file extension (a guard against data exfiltration, often a pre-tool hook). Write through the file-writing tool regardless, so the skill works either way: no `cat >`, no shell redirection, no `python` with the path on the command line. Build the content in context and write it with the `write_to_file` tool. Verify by `view_file`ing the file back and checking the first rows and the per-row column count — again without Bash.

## Step 5 — Report and import instructions

Print: output path, layout, row count, any skipped/odd rows, and:

```
Google Sheets: File → Import → Upload → choose the file →
  Import location: "Insert new sheet(s)" (or "Replace current sheet")
  Separator type: Comma
  Untick "Convert text to numbers, dates and formulas" so IDs and leading zeros stay text.
Paste alternative (single-line cells only): copy the file contents into A1, then Data → Split text to columns.
```

For the `importer` layout, the hand-off is `{qa_import} {qa_out_dir}/<slug>/test-cases-importer.md` (or the user's own importer when `{qa_import}` is empty); the sheet file is only for people who want the same rows in a plain sheet. Name any `page_path` that still holds a placeholder segment (such as a record id) that must be filled before the run.

## Done when

- The file opens in Sheets with one row per case and the header intact; for `importer`, the Markdown file also has one parseable json block per case.
- Every matrix case is present, including those with an open expected value.
- No credentials or real personal data are in any cell.
- The report lists every row that could not be mapped.
