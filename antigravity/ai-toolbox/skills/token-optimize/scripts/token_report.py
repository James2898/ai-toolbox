#!/usr/bin/env python3
"""Measure prompt-like files and check that a rewrite kept its load-bearing parts.

Usage:
  token_report.py <path> [<path> ...] [--only GLOB] [--json]
  token_report.py --check ORIGINAL REWRITE [--json]

Measurement is a heuristic: tokens ~= chars / 4 (roughly +-20% for English prose,
worse for CJK text and code). Use it to rank and compare, not as billing truth.
"""
import fnmatch
import json
import re
import sys
from pathlib import Path

TEXT_SUFFIXES = {".md", ".txt", ".yaml", ".yml", ".json"}

FILLER_PATTERNS = [
    r"\bthis skill (will|is designed to|helps?)\b",
    r"\blet'?s (begin|start|dive|delve)\b",
    r"\bin order to\b",
    r"\bplease note that\b",
    r"\bit is important to (note|remember)\b",
    r"\bas (mentioned|stated) (above|earlier|before)\b",
    r"\bfeel free to\b",
    r"\bsimply\b",
    r"\bbasically\b",
]
SHOUT_PATTERN = re.compile(r"\b(MUST|NEVER|ALWAYS|CRITICAL|IMPORTANT)\b")


def est_tokens(text: str) -> int:
    return round(len(text) / 4)


def split_frontmatter(text: str):
    """Return (frontmatter, body). Frontmatter is '' when absent."""
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return text[: end + 4], text[end + 4 :]
    return "", text


def description_of(frontmatter: str) -> str:
    m = re.search(r"^description:\s*(.*)$", frontmatter, re.M)
    if not m:
        return ""
    value = m.group(1).strip()
    # Multi-line block scalars (| or >) — take the indented continuation lines.
    if value in ("|", ">", "|-", ">-"):
        lines = []
        for line in frontmatter[m.end() :].splitlines()[1:]:
            if line.startswith((" ", "\t")):
                lines.append(line.strip())
            else:
                break
        value = " ".join(lines)
    return value.strip('"').strip("'")


def measure(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    fm, body = split_frontmatter(text)
    desc = description_of(fm)
    lines = text.splitlines()
    nonblank = [l.strip() for l in lines if l.strip() and not l.strip().startswith(("|", "-", "#", "```"))]
    seen, dupes = set(), 0
    for l in nonblank:
        if len(l) > 40:
            if l in seen:
                dupes += 1
            seen.add(l)
    filler = sum(len(re.findall(p, text, re.I)) for p in FILLER_PATTERNS)
    shouts = len(SHOUT_PATTERN.findall(text))
    paragraphs = [p for p in re.split(r"\n\s*\n", body) if p.strip() and not p.strip().startswith("```")]
    longest_para = max((len(p) for p in paragraphs), default=0)
    fences = text.count("```") // 2
    return {
        "file": str(path),
        "chars": len(text),
        "lines": len(lines),
        "est_tokens": est_tokens(text),
        "description_tokens": est_tokens(desc),
        # disable-model-invocation keeps the description out of the always-loaded skill list
        "user_only": bool(re.search(r"^disable-model-invocation:\s*true\s*$", fm, re.M)),
        "filler_hits": filler,
        "shout_caps": shouts,
        "duplicate_lines": dupes,
        "longest_paragraph_chars": longest_para,
        "code_fences": fences,
    }


def collect(paths, only):
    files = []
    for p in paths:
        p = Path(p).expanduser()
        if p.is_dir():
            for f in sorted(p.rglob("*")):
                if f.is_file() and f.suffix in TEXT_SUFFIXES and "node_modules" not in f.parts:
                    if only is None or fnmatch.fnmatch(f.name, only) or fnmatch.fnmatch(f.parent.name, only):
                        files.append(f)
        elif p.is_file():
            files.append(p)
        else:
            print(f"warning: {p} not found", file=sys.stderr)
    return files


# ---------- invariant extraction for --check ----------

GATE_WORDS = re.compile(r"\b(confirm|approve|approval|ask the user|askuserquestion|never|do not|don't|must not|stop)\b", re.I)


def invariants(text: str) -> dict:
    spans = set(re.findall(r"`([^`\n]+)`", text))
    flags = set(re.findall(r"(?<![\w-])(--?[a-zA-Z][\w-]*)", text))
    paths = {s for s in re.findall(r"(?<![\w])((?:~|\.{1,2})?/[\w./~\-{}<>*]+)", text) if len(s) > 2}
    gates = {l.strip() for l in text.splitlines() if GATE_WORDS.search(l) and len(l.strip()) > 15}
    headings = [l.strip() for l in text.splitlines() if l.startswith("#")]
    return {"spans": spans, "flags": flags, "paths": paths, "gates": gates, "headings": headings}


def check(original: Path, rewrite: Path) -> dict:
    a = invariants(original.read_text(encoding="utf-8", errors="replace"))
    b_text = rewrite.read_text(encoding="utf-8", errors="replace")
    b = invariants(b_text)
    missing = {
        "spans": sorted(a["spans"] - b["spans"]),
        "flags": sorted(a["flags"] - b["flags"]),
        "paths": sorted(p for p in a["paths"] if p not in b_text),
        # gate lines are compared loosely: the rewrite must still contain each gate's key phrase
        "gates": sorted(g for g in a["gates"] if not any(w in b_text.lower() for w in _keywords(g))),
    }
    ok = not any(missing.values())
    return {
        "original": str(original),
        "rewrite": str(rewrite),
        "before_tokens": est_tokens(original.read_text(encoding="utf-8", errors="replace")),
        "after_tokens": est_tokens(b_text),
        "headings_before": len(a["headings"]),
        "headings_after": len(b["headings"]),
        "missing": missing,
        "verdict": "PASS" if ok else "FAIL",
    }


def _keywords(line: str):
    words = [w.lower() for w in re.findall(r"[A-Za-z][A-Za-z\-]{3,}", line)]
    stop = {"that", "this", "with", "from", "they", "then", "when", "only", "into", "each", "user", "will"}
    return [w for w in words if w not in stop][:4] or [line.lower()[:20]]


def main(argv):
    as_json = "--json" in argv
    argv = [a for a in argv if a != "--json"]
    if "--check" in argv:
        i = argv.index("--check")
        try:
            orig, new = Path(argv[i + 1]).expanduser(), Path(argv[i + 2]).expanduser()
        except IndexError:
            print(__doc__)
            return 2
        result = check(orig, new)
        if as_json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"{result['verdict']}  {orig.name} -> {new.name}  ~{result['before_tokens']} -> ~{result['after_tokens']} tokens")
            for k, v in result["missing"].items():
                for item in v:
                    print(f"  missing {k[:-1]}: {item}")
        return 0 if result["verdict"] == "PASS" else 1

    only = None
    if "--only" in argv:
        i = argv.index("--only")
        only = argv[i + 1]
        del argv[i : i + 2]
    paths = argv[1:]
    if not paths:
        print(__doc__)
        return 2
    rows = [measure(f) for f in collect(paths, only)]
    rows.sort(key=lambda r: -r["est_tokens"])
    if as_json:
        print(json.dumps(rows, indent=2, ensure_ascii=False))
        return 0
    print(f"{'est_tok':>8} {'desc_tok':>8} {'lines':>6} {'fill':>5} {'caps':>5} {'dup':>4}  file")
    for r in rows:
        print(f"{r['est_tokens']:>8} {r['description_tokens']:>8} {r['lines']:>6} {r['filler_hits']:>5} {r['shout_caps']:>5} {r['duplicate_lines']:>4}  {r['file']}")
    total = sum(r["est_tokens"] for r in rows)
    desc_total = sum(r["description_tokens"] for r in rows if not r["user_only"])
    hidden = sum(r["description_tokens"] for r in rows if r["user_only"])
    print(f"\n{len(rows)} files, ~{total} tokens total; ~{desc_total} tokens of descriptions are loaded every session"
          f" (~{hidden} more in user-only skills, loaded only when invoked).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
