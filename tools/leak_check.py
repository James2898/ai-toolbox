#!/usr/bin/env python3
"""Fail if anything that should stay private is about to be published.

    python3 -I tools/leak_check.py            # scan the whole working tree
    python3 -I tools/leak_check.py --staged   # scan only files staged for commit

Two pattern sets:
- Generic patterns, kept in this file: secrets, tokens, private keys, emails,
  absolute home paths, private IP addresses.
- Private patterns: names that must never appear (employer, products, internal hosts,
  colleagues, schema names). They are NOT stored in this public repo, because listing
  them here would publish them. Put one regular expression per line in the file named
  by AI_TOOLBOX_LEAK_PATTERNS (default: ~/.config/ai-toolbox/leak-patterns.txt).
  Lines starting with # are comments. Matching is case-insensitive.

Exit codes: 0 clean, 1 findings, 2 setup error (for example a missing private pattern file,
so a check without private patterns is never mistaken for a clean one).
"""
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PRIVATE = Path(os.environ.get("AI_TOOLBOX_LEAK_PATTERNS", "~/.config/ai-toolbox/leak-patterns.txt")).expanduser()
SKIP_DIRS = {".git", "__pycache__"}
SKIP_FILES = {Path("tools/leak_check.py")}

GENERIC = [
    ("private key", r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    ("GitHub token", r"\bgh[pousr]_[A-Za-z0-9]{20,}"),
    ("AWS key", r"\bAKIA[0-9A-Z]{16}\b"),
    ("Slack token", r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),
    ("API key assignment", r"(?i)\b(api[_-]?key|secret|token|passw(or)?d)\s*[:=]\s*['\"][^'\"\s]{12,}['\"]"),
    ("email address", r"\b[A-Za-z0-9._%+-]+@(?!example\.(com|org|test)\b)[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    ("absolute home path", r"/(Users|home)/[A-Za-z0-9._-]+/"),
    ("private IP", r"\b(10\.\d{1,3}|192\.168|172\.(1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}\b"),
]


def load_private():
    if not PRIVATE.exists():
        print(f"setup error: private pattern file not found: {PRIVATE}\n"
              "Create it (one regex per line) or set AI_TOOLBOX_LEAK_PATTERNS.", file=sys.stderr)
        sys.exit(2)
    pats = []
    for i, line in enumerate(PRIVATE.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if line and not line.startswith("#"):
            pats.append((f"private pattern #{i}", f"(?i){line}"))
    return pats


ALLOW = Path(os.environ.get("AI_TOOLBOX_LEAK_ALLOW", "~/.config/ai-toolbox/leak-allow.txt")).expanduser()


def load_allow():
    """Optional private allow-list: `<path glob><TAB><regex>` per line. A finding is ignored when
    the file matches the glob and the line matches the regex (e.g. a generic ID convention that
    happens to collide with a private pattern). Kept private for the same reason as the patterns."""
    rules = []
    if ALLOW.exists():
        for line in ALLOW.read_text(encoding="utf-8").splitlines():
            if line.strip() and not line.startswith("#") and "\t" in line:
                glob, rx = line.split("\t", 1)
                rules.append((glob.strip(), re.compile(rx.strip())))
    return rules


def files(staged):
    """Staged files, or everything git would publish (tracked + untracked, minus .gitignore'd)."""
    if staged:
        cmd = ["git", "-C", str(ROOT), "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"]
    else:
        cmd = ["git", "-C", str(ROOT), "ls-files", "--cached", "--others", "--exclude-standard", "-z"]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout.split("\0")
    return [ROOT / p for p in out if p and not SKIP_DIRS & set(Path(p).parts)]


def main(argv):
    patterns = [(n, re.compile(p)) for n, p in GENERIC + load_private()]
    allow = load_allow()
    findings = 0
    for f in files("--staged" in argv):
        rel = f.relative_to(ROOT)
        if rel in SKIP_FILES or not f.exists():
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for ln, line in enumerate(text.splitlines(), 1):
            if any(rel.match(g) and arx.search(line) for g, arx in allow):
                continue
            for name, rx in patterns:
                if rx.search(line):
                    findings += 1
                    # print the pattern name, never the matched private text itself
                    print(f"{rel}:{ln}: {name}")
    if findings:
        print(f"\n{findings} finding(s). Generalize or remove them before committing.")
        return 1
    print("leak check: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
