"""Deterministic leak gate for a distributable voice profile.

Scans every text file under the given skill directories for three kinds of
leak and fails if any is found:

1. Deny-list terms -- private names (products, services, people, usernames)
   read from a deny-list file that lives *outside* the skill, so the list of
   private terms never ships with the package.
2. Source-citation debris -- doc IDs, PR numbers, and source-bucket paths of
   the kind the original private profile used to cite its evidence.
3. Verbatim overlap -- any run of SHINGLE_WORDS consecutive words shared with
   a source document passed via --source.

Usage:
    python3 check_leaks.py <skill-dir> [<skill-dir> ...] [--source PATH ...]
        [--denylist FILE]

Exit status: 0 = clean, 1 = leak found, 2 = setup error (e.g. missing
skill dir). A missing deny-list is not one of those: it prints a warning
and the term check is skipped for that run, so the remaining checks still
run and their result decides the exit status.
"""

import argparse
import re
import sys
from pathlib import Path

DEFAULT_DENYLIST = Path.home() / ".config" / "writing-in-voice" / "denylist.txt"

# 8 words: idioms and stock technical phrases ("if you want to keep going")
# rarely reach 8 words, while a sentence copied from a source almost always
# does. Lower values flag ordinary English; higher values miss short quotes.
SHINGLE_WORDS = 8

SCAN_SUFFIXES = {".md", ".py", ".json", ".txt"}
SKIP_DIRS = {"__pycache__", ".git"}

CITATION_PATTERNS = [
    (re.compile(r"\b(?:confluence|github)[/_][\w./-]+", re.I), "source-bucket path"),
    (re.compile(r"\bpr-\d{3,}\b", re.I), "PR-number citation"),
    (re.compile(r"\b\d{6,}-[A-Z][\w-]+"), "wiki doc-ID citation"),
    (re.compile(r"\bmanifest\.md\b"), "corpus manifest reference"),
]

WORD_RE = re.compile(r"[a-z0-9']+")


def iter_files(root: Path):
    if root.is_file():
        yield root
        return
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix in SCAN_SUFFIXES and not SKIP_DIRS & set(path.parts):
            yield path


def load_denylist(path: Path) -> list[str]:
    terms = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            terms.append(line)
    return terms


def shingles(text: str) -> set[tuple[str, ...]]:
    words = WORD_RE.findall(text.lower())
    return {tuple(words[i:i + SHINGLE_WORDS]) for i in range(len(words) - SHINGLE_WORDS + 1)}


def scan(skill_dirs: list[Path], denylist: list[str], sources: list[Path]) -> list[str]:
    # Underscores count as separators so snake_case and file-name forms
    # (term_notes.md) still match.
    deny_res = [
        (re.compile(rf"(?<![A-Za-z0-9-]){re.escape(t)}(?![A-Za-z0-9-])", re.I), t) for t in denylist
    ]
    source_shingles: set[tuple[str, ...]] = set()
    for src in sources:
        for path in iter_files(src):
            source_shingles |= shingles(path.read_text(encoding="utf-8", errors="replace"))

    hits = []
    for root in skill_dirs:
        for path in iter_files(root):
            text = path.read_text(encoding="utf-8", errors="replace")
            for lineno, line in enumerate(text.splitlines(), 1):
                for rx, term in deny_res:
                    if rx.search(line):
                        hits.append(f"{path}:{lineno}: deny-list term {term!r}")
                for rx, label in CITATION_PATTERNS:
                    m = rx.search(line)
                    if m:
                        hits.append(f"{path}:{lineno}: {label} {m.group(0)!r}")
            if source_shingles:
                for sh in sorted(shingles(text) & source_shingles):
                    hits.append(f"{path}: verbatim overlap with source: {' '.join(sh)!r}")
    return hits


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("skill_dirs", nargs="+", type=Path)
    ap.add_argument("--source", action="append", default=[], type=Path,
                    help="source doc or directory to check for verbatim overlap (repeatable)")
    ap.add_argument("--denylist", type=Path, default=DEFAULT_DENYLIST)
    args = ap.parse_args()

    denylist: list[str] = []
    if args.denylist.is_file():
        denylist = load_denylist(args.denylist)
    else:
        msg = f"warning: deny-list {args.denylist} not found; " \
            "skipping the term check"
        print(msg, file=sys.stderr)
    for p in args.skill_dirs + args.source:
        if not p.exists():
            print(f"setup error: {p} does not exist", file=sys.stderr)
            return 2

    hits = scan(args.skill_dirs, denylist, args.source)
    for h in hits:
        print(h)
    print(f"{'FAIL' if hits else 'PASS'}: {len(hits)} leak(s) found")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
