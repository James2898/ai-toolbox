---
name: test-data
description: "Generate the test data for a test matrix — SQL INSERT blocks per case with explicit ids and QA-prefixed names, the expected values each case should then show, verification SELECTs that prove the setup, and cleanup DELETEs — grounded in the real DDL (the project's schema and migration files, plus tenant schema routing when the project has one). Writes {qa_out_dir}/<slug>/test-data.sql and test-data.md; never runs SQL unless asked and confirmed, and only against the local DB. Use whenever the user asks for test data, seed data for QA cases, fixtures for a matrix, \"SQL to set up this scenario\", or how to verify the data behind a test case."
---

> **Running in Antigravity**: this skill is generated from the Claude Code source.
> - `ask_question` is Antigravity's interactive question tool (Claude Code: AskUserQuestion).
> - `ARGS` means whatever the user typed after `/<this-skill>`, or the request that triggered it.

# Test Data

For every case in a test matrix, produce the **data that makes the case reachable**, the **values it should then show**, the **query that proves the setup**, and the **cleanup**. Third step of the QA chain: `/test-plan → /test-matrix → /test-data (this) → /export-csv`.

## Project settings

This skill reads the project profile (see the toolbox README): `AI_TOOLBOX_PROFILE`, else `<project root>/.ai-toolbox/profile.yml`. Placeholders used below:

| Placeholder | Profile key | Without a profile |
|---|---|---|
| `{qa_out_dir}` | `docs.qa_out_dir` | `.qa/` (keep it gitignored) |
| `{ddl_paths}` | `database.ddl_paths` | search for migrations or `schema.sql` |
| `{seed_paths}` | `database.seed_paths` | look for seed / master-data files next to the DDL; none if absent |
| `{tenant_routing}` | `database.tenant_routing` | none: ask whether data is split per tenant schema |
| `{local_container}` | `database.local_container` | ask how the local database is reached |
| `{forbidden_hosts}` | `environments.forbidden_hosts` | anything that is not local |

## Inputs

`ARGS`: path to a `test-matrix.md` (default: the newest `{qa_out_dir}/*/test-matrix.md`), or a slug. Flags:

| Flag | Meaning | Default |
|---|---|---|
| `--cases=TM-001,TM-004` | Restrict to listed case ids | all |
| `--schema=<name>` | Target schema (tenant schema in a multi-tenant setup) | resolved in Step 2 |
| `--run` | Execute the generated SQL against the **local** DB after confirmation | off |
| `--out=<dir>` | Output folder | the matrix's folder |

Outputs: `test-data.sql` (runnable, one block per case) and `test-data.md` (expected values + verification queries per case).

## Step 1 — Read the matrix and list the entities

Parse the `## Cases` table. For each case, name the entities its factor values imply (a user with role X, a record in state Y, an entry on date Z). Group cases that share a setup so one block can serve several ids; say so in the file.

Cases that need no data (pure UI state, validation of typed input) get a one-line "no data" entry — do not invent rows for them.

## Step 2 — Resolve the schema from the DDL, never from memory

Column lists come from the DDL, because a guessed column name produces a silent unknown-column / missing-default error at run time and a wrong expectation afterwards.

- Read `{ddl_paths}` (base schema first, then the migrations in order). The latest `CREATE TABLE` / `ALTER TABLE … ADD` for a table wins — grep every path, not just the base file.
- Master/seed rows that already exist locally: `{seed_paths}`. Reuse existing masters (statuses, titles) instead of inserting duplicates.
- If a DDL path is a git submodule, it must be initialised (`git submodule update --init --recursive`); an empty DDL folder means stop and say so.
- **Tenant routing:** if `{tenant_routing}` is set, data may live in a per-tenant schema rather than behind a tenant column on every table. Resolve the target schema the way `{tenant_routing}` describes, with a query, never by assumption — two tenant schemas on the same server can sit at different migration levels. Shared tables live in the common schema it names. If `{tenant_routing}` is empty and the DDL suggests per-tenant schemas, ask.

No profile and nothing found: look for the migrations directory or schema file first (`Glob **/migrations/**`, `schema.sql`, `*.prisma`); if there is none readable, stop and ask rather than guessing columns.

Record the DDL file and line you used for each table in `test-data.md` (Source column).

## Step 3 — Generate per-case blocks

**Isolate first.** Give each case (or shared setup) its own slice of data, so blocks coexist and cases run in any order, side by side, without re-seeding between them:
- its own matching key (application, alias, category — whatever the feature filters on), named `qa-td-<caseid>-…`;
- its own date, one calendar day per case, listed in a table at the top of the file, so per-day aggregates and syncs never see another case's rows;
- shared actors (one test user, one group) only where the feature cannot tell cases apart by key or date — and say why.

Sequential blocks are the fallback, not the default. Use them only for factors that are **tenant-wide by nature**, such as a global setting like a time step or a limit. Put those cases in a separate `-- SEQUENTIAL` section at the end; each block saves the current values, applies its own, and restores them in its cleanup.

For each case (or shared setup) write a block in `test-data.sql`:

```sql
-- =====================================================================
-- TM-001  <one-line case summary>   (also serves: TM-002, TM-003)
-- Schema: <schema>   Needs: <tables>
-- =====================================================================
-- setup
INSERT INTO `<table>` (`id`, `<tenant_col>`, `name`, `created_at`, …)
VALUES (900001, <tenant_id>, 'QA-TD-TM001-<entity>', '2026-10-15 00:00:00', …);
-- verify
SELECT … FROM `<table>` WHERE `id` = 900001;   -- expect 1 row: <values>
-- cleanup
DELETE FROM `<child>` WHERE `parent_id` = 900001;
DELETE FROM `<table>` WHERE `id` = 900001;
```

Rules for the rows:
- **Explicit primary keys in a reserved range** (`900000+`, or the table's max + a wide margin) and names prefixed `QA-TD-<caseid>-` so every row is attributable and sweepable.
- **Synthetic values only.** No real customer names, emails, account numbers or anything copied from production exports; `qa.td.tm001@example.test` style emails.
- **Dependency order**: parents before children in setup, reverse in cleanup; every FK you reference must be either an existing master row (cite it) or inserted above.
- **Explicit timestamps and time zone.** State the assumed zone once at the top of the file; time-based fixtures (logs, attendance, schedules) break when wall-clock vs UTC is left implicit.
- **Idempotent**: each block starts with its own cleanup (guarded DELETEs) so re-running does not duplicate.
- **Cleanup deletes only what the block inserted**, by its reserved keys or its `QA-TD-` names. Never use a broad filter such as "all entries of this user on this date", which would also remove rows created during testing.
- **Shared-table changes restore themselves.** Any UPDATE to a tenant-wide or shared row records the original value first and restores it in that block's cleanup, with no hand-typed values. If the restore depends on session state (user variables), say so and print a manual fallback statement with the literal original values.
- Mark any value you had to assume (an enum code, a default) with `-- (assumed: …)` and list it in Open questions.

## Step 4 — Expected values and verification queries

In `test-data.md`, per case:

```markdown
### TM-001 — <summary>
| Entity | Key | Setup value | Expected on screen / API |
|---|---|---|---|
Verification:
```sql
SELECT … ;  -- expect: <rows / values>
```
Source: `<ddl file:line>`
```

The verification query must distinguish "setup worked" from "feature worked": one query for the inserted state, and where the case has a side effect (sync writes, status change), a second query for the post-condition.

## Step 5 — Optional execution (`--run`)

Only against the local database, only after `ask_question` shows the schema, the tables and the row counts about to be inserted. Reach it through `{local_container}` when set (for example `docker exec -i {local_container} <db client> <schema> < file`); take credentials from the project's compose/config files or the user, never from this skill. Refuse anything that is not local, and always refuse `{forbidden_hosts}` and any shared, staging or production database. After running, execute the verification queries and paste the results into `test-data.md` under "Run log".

## Step 6 — Report

Print: files written, cases with data / shared setups / no-data cases, which cases are isolated and which sit in the sequential section (with why), any shared-table changes and how they are restored, tables touched, assumptions, and the next command:

```
/export-csv {qa_out_dir}/<slug>/test-matrix.md --data={qa_out_dir}/<slug>/test-data.md
```

## Notes

- A table missing locally (table-not-found error) is either the wrong schema or an unapplied migration — check the tenant routing (`{tenant_routing}`) first, then the migration list.
- When the DDL for a table is not merged yet (feature still in a PR), say so and generate against the PR's DDL with a `-- (unmerged DDL: <path>)` marker.
- Keep `test-data.sql` runnable top to bottom; the `.md` is for humans and for `/export-csv`'s Preconditions column.
