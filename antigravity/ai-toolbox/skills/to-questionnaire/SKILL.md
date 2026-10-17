---
name: to-questionnaire
description: "Turn open questions (from design-grill, a PBI analysis, requirements open questions, or a pasted list) into a Markdown questionnaire a PO, lead or designer can answer without the conversation: grouped by topic, each question with its context, choices with a recommended default, what happens if unanswered, and an answer field. Writes a file; never sends it. Use when the user wants to send questions to the PO, lead or designer, make a questionnaire or question sheet, or collect answers asynchronously."
---

> **Running in Antigravity**: this skill is generated from the Claude Code source.
> - `ask_question` is Antigravity's interactive question tool (Claude Code: AskUserQuestion).

# to-questionnaire — questions someone else can answer cold

The reader was not in the conversation. Each question must stand on its own: what we are building, what is undecided, the realistic choices, and what we will do if they do not answer.

## Arguments

| Argument | Meaning |
|---|---|
| source | a design-grill result in chat, a PBI hardcopy, a requirements file with open questions, or pasted questions |
| `--for=<role>` | who answers: `po`, `lead`, `designer`, `backend`, … (shapes wording and which questions go in) |
| `--lang=<code>` | write the questionnaire in that language; keep code identifiers as they are |
| `--due=<date>` | the answer-by date used in "if unanswered" lines |

## Project settings

Reads the project profile (`AI_TOOLBOX_PROFILE`, else `<project root>/.ai-toolbox/profile.yml`): `docs.pbi_dir` (default `pbi-docs/`) is where the file is written next to its PBI.

## Steps

### 1. Collect and filter

Gather the questions from the source. Keep only the ones this role can decide: a PO decides behaviour, scope and priority; a lead decides architecture and rollout; a designer decides what the user sees; a backend owner decides contracts. Move the rest to an "Asked elsewhere" list at the end. Drop any question the PBI, the project rules or the code already answers, and say which source answered it.

Done when: each kept question has an owner role and no source already answers it.

### 2. Rewrite each question for a cold reader

For each question:

- **Context**: one or two sentences on the situation, in product words (screens, users, data), with no code paths unless the reader is technical.
- **Question**: one decision, no compound questions.
- **Choices**: two to four, each with its consequence in one line. Mark the recommended one with ★ and say why in one line.
- **If unanswered by {due}**: the choice we will proceed with.
- **Answer**: an empty field, with room for a note.

Order: questions that block work first, then those that change behaviour, then wording and polish.

Done when: every question reads correctly without the rest of the file.

### 3. Write the file

Write `{pbi_dir}/<PBI-ID>-questions-<role>.md`, or `questions-<role>-<YYYY-MM-DD>.md` in the current folder when there is no PBI:

```markdown
# Questions for <role> — <feature>   (answer by <due>)

<Two-line summary of the feature and why these questions matter now.>

**Quick path:** reply "all ★" to accept every recommendation.

## <Topic>

### Q1. <question>   — blocks work
<context>

| | Choice | What it means |
|---|---|---|
| ★ | A | … |
|   | B | … |

If unanswered by <due>: we go with A.

**Answer:**
**Note:**
```

Show the file path and the question count. Do not send, post or share it; the user decides how it travels. When answers come back, offer to fold them into the PBI hardcopy or requirements.

## Boundaries

No customer or employee personal data, credentials or unpublished financial figures in the questionnaire; it is written to be forwarded.
