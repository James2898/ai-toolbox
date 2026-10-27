---
name: leak-check
description: "Audit the repository and git diff for sensitive data, secrets, platform tokens, and memory leaks before publishing or committing. Verifies repository visibility (public vs private), confirms MEMORY.md and session notes are untracked and gitignored in public repos, scans for API keys (Claude sk-ant-, Gemini AIza, GitHub, AWS, Slack), private keys, emails, and local user paths. Flags findings by file:line without printing secret values. Use whenever the user asks to check for leaks, audit privacy, verify secrets, check memory hygiene, or before publishing/pushing."
---
# leak-check — privacy, secrets, and repository hygiene

Public repositories must never publish developer identity paths, session memories, or credentials. Private repositories must still protect API keys, tokens, and client secrets. This skill audits your working tree, staged index, and branch commits for leaks before they reach remote repositories.

## Arguments

| Argument | Meaning |
|---|---|
| (none) | branch diff against base (`origin/<base>...HEAD`) + unstaged working tree |
| `--all` | scan the entire repository working tree |
| `--staged` | scan only files staged for commit |
| `--commits` | scan all commit diffs introduced on this branch relative to base |
| `--base=<branch>` | base branch to diff against (default: auto-detected default base) |

## Steps

### 1. Check Repository Visibility
Detect whether the current repository is public or private:
```bash
gh repo view --json isPrivate 2>/dev/null || git remote get-url origin
```
- **Public repo**: Strict hygiene applies. `MEMORY.md`, developer scratchpads, session transcripts, and personal profiles must **never** be tracked or committed to Git, and must be present in `.gitignore`.
- **Private repo**: Internal project notes or `MEMORY.md` may be tracked if deliberate, but credentials, API keys, tokens, and external customer PII are strictly prohibited.

### 2. Memory & Session Hygiene Audit
Check for tracked or unstaged memory files and verify `.gitignore`:
```bash
git ls-files | grep -iE '^(MEMORY\.md|scratch/|\.gemini/|\.claude/settings\.local)'
git check-ignore -q MEMORY.md
```
- If the repository is **public**:
  - `MEMORY.md` tracked in Git $\rightarrow$ **Blocker** (remediate with `git rm --cached MEMORY.md`).
  - `MEMORY.md` missing from `.gitignore` $\rightarrow$ **Blocker** (remediate by adding to `.gitignore`).
  - Personal configuration files tracked (e.g. `.claude/settings.local.json`, `.gemini/GEMINI.md`) $\rightarrow$ **Blocker**.

### 3. Secret & Credential Scan
Run `tools/leak_check.py` or inspect the scope with regexes:
```bash
python3 -I tools/leak_check.py $([ "$1" = "--staged" ] && echo "--staged")
```
Patterns audited:
- **Claude & Anthropic**: `\bsk-ant-(api[0-9]{2}-)?[A-Za-z0-9_-]{20,}\b`, `.claude.json` tokens.
- **Gemini & Google**: `\bAIza[0-9A-Za-z-_]{35}\b`, Antigravity brain transcripts, session artifacts.
- **GitHub**: `\b(gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{50,})\b`.
- **Cloud & Services**: AWS keys (`AKIA[0-9A-Z]{16}`), Slack tokens (`xox[abprs]-`), private keys (`BEGIN [A-Z ]*PRIVATE KEY`).
- **PII & Paths**: Real email addresses, private IP ranges (`10.x`, `192.168.x`, `172.16-31.x`), absolute home paths (`/Users/name`, `/home/name`, `C:\Users\name`).

### 4. Strict Redaction Rule
**Never print or reflect detected secret values** in chat, reports, or commit messages. Report findings strictly by:
- `file:line`
- Pattern name (e.g. `Claude API key`, `GitHub token`, `Private SSH Key`)
- Proposed remediation action

## Report

```markdown
## Leak & Hygiene Audit — <scope> (<YYYY-MM-DD>)

**Repository Visibility:** Public | Private (Source: `gh repo view` / remote URL)
**Memory Hygiene:** Clean | Blocker

### Findings
| # | Severity | file:line | Category | Issue | Remediation |
|---|---|---|---|---|---|
| 1 | blocker | MEMORY.md | Memory Hygiene | Tracked in public repository | `git rm --cached MEMORY.md` |
| 2 | blocker | config.py:12 | Claude API key | Anthropic key in code | Move to environment variable |

### Remediations
1. `git rm --cached MEMORY.md`
2. Add `MEMORY.md` to `.gitignore`
```

Severity:
- **blocker**: Credential, private key, token, or `MEMORY.md` tracked in a public repository.
- **warning**: Unignored scratchpad or non-blocking internal path reference.
- **clean**: Zero findings across visibility, memory hygiene, and credentials.
