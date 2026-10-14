"""Phase 3 validation: score a candidate text against a format's Layer 1
profile and mechanically scan it for Layer 4 negative-list tells.

Deterministic only -- no LLM judgment anywhere in here, per the plan's §7.4.
`writing-in-voice` calls this; it is the only thing that decides pass/fail. A pass
means "no mechanical tell was found," which is necessary and not sufficient. Two
of the four category-3 structural tells are now measured and gated (tables,
boldface density); the other two are measured but not gated because they did not
separate real docs from AI slop, and the judgment calls stay a human concern.

Usage:
    python3 validate_voice.py --format code-review --file draft.md
    cat draft.md | python3 validate_voice.py --format technical-writing

Exit status: 0 = pass, 1 = fail (any negative-list hit, or a calibrated
structural threshold tripped), 2 = usage/setup error (e.g. missing profile JSON).

Delta and the per-metric z-scores are **informational**, not pass/fail. Phase 4
calibration measured every real held-out doc at Delta 0.3-1.3 against every
format profile and an AI-slop control at 0.67, so no threshold separates the two
(calibration finding 1). The negative-list scan plus
the calibrated structural thresholds are the gate.
"""

import argparse
import json
import re
import sys
from pathlib import Path

import stylometry as sm

# Skill-relative on purpose: this file ships at <skill>/scripts/ and the
# profile ships at <skill>/voice-profile/, so the skill directory works
# wherever it is installed.
PROFILE_DIR = Path(__file__).resolve().parents[1] / "voice-profile"

FORMATS = ["technical-writing", "code-review", "notes"]

# Plan §9, as revised after Phase 4: the failure condition is any negative-list
# hit. Delta is reported for context only.
#
# The old gate was `delta > DELTA_THRESHOLD or hits`, with the threshold at 2.0.
# It never fired on anything: real corpus docs and deliberate AI slop both land
# in the 0.3-1.3 band, so the threshold passed everything and a tighter one would
# have failed the author's own writing. Kept here as the band real docs occupy,
# so `format_report` can say whether a candidate is inside it -- do not turn this
# back into a pass/fail condition without new evidence that Delta separates
# anything.
DELTA_OBSERVED_MAX = 1.3

# Metric-level reporting band: how many stdevs from the bucket mean before a
# metric is called out. Informational, like Delta -- it tells a reviewer which
# knob looks off. Left at 2.0 because tightening it to 1.0 flags most real
# corpus docs (18/29 technical-writing held-out), i.e. it would be noise.
METRIC_Z_REPORT = 2.0


# ---------------------------------------------------------------------------
# Negative list. Every entry is a literal-substring or regex tell drawn from
# the anti-AI-tell checklist (negative-list.md) (categories 1, 2, 4, 6, 7 -- the ones
# that are mechanically checkable). Category 3/5 items are structural or
# require reading sources, so they stay a human-review concern, noted in
# SKILL.md rather than faked here.
#
# `(pattern, category, label)`; patterns are matched case-insensitively.
# ---------------------------------------------------------------------------

_WORD_TELLS_VOCAB = [
    # Legacy/significance puffery
    "stands as", "serves as", "testament", "pivotal role", "enduring",
    "indelible mark", "deeply rooted", "setting the stage for",
    # Superficial-analysis connectors
    "underscoring", "underscores", "underscore",
    "reflecting", "contributing to", "fostering", "resonate with",
    # Promotional puffery
    "boasts a", "boasts", "vibrant", "nestled", "in the heart of",
    "groundbreaking", "renowned", "diverse array",
    # Weasel attributions
    "industry reports", "observers have cited", "experts argue",
    # Early-era drift tells
    "delve", "meticulous", "tapestry", "intricate", "crucial", "garner",
    # Mid/later-era drift tells
    "align with", "showcasing", "emphasizing",
    # Model-family signatures
    "empirical",
]

# Tells that need a context guard: the bare word is a legitimate part of this
# author's technical vocabulary, and a Phase 4 scan of the real held-out set
# showed the unguarded pattern firing on his own writing. Narrowed, not dropped.
_GUARDED_WORD_TELLS = [
    # "syntax highlighting" is a real feature name; the tell is the connector use.
    (r"(?<!syntax )\bhighlighting\b", "vocabulary", "vocabulary tell: 'highlighting'"),
    # "correlate the log with the ticket" is normal oncall language; the tell is
    # the analytical "X correlates with Y" register.
    (r"\bcorrelat(?:es|ed|ion)\s+(?:strongly|closely|positively|negatively|well)\b",
     "vocabulary", "vocabulary tell: 'correlate' (analytical register)"),
]

_PHRASE_TELLS = [
    (r"\bnot only\b[^.!?]{0,80}?\bbut\b", "phrasing", "negative parallelism: 'not only X but Y'"),
    (r"\bit'?s not just\b[^.!?]{0,80}?,\s*it'?s\b", "phrasing", "negative parallelism: \"it's not just X, it's Y\""),
    # Narrowed in Phase 4 calibration. The unguarded form
    # (r"\bnot\b[^.!?]{0,60}?,\s*but\b") fired on 10 real held-out docs -- the
    # author writes ordinary contrastive prose like "Disco is not part of the
    # auth path, but it is customer-facing" constantly. The AI tell is the
    # *sentence-initial* rhetorical construction, so anchor it there.
    # the AI tell is the *sentence-initial* rhetorical construction, or the
    # "but rather / but instead" continuation -- both anchored here.
    (r"(?:^|(?<=[.!?]\s)|(?<=[.!?]\n))not\b[^.!?]{0,60}?,\s*but\b",
     "phrasing", "absolute negation: sentence-initial 'Not X, but Y'"),
    (r"\bnot\b[^.!?]{0,60}?,?\s*but (?:rather|instead)\b",
     "phrasing", "absolute negation: 'not X, but rather/instead Y'"),
    (r"\bdespite its\b", "phrasing", "formulaic challenges/future opener: 'Despite its ...'"),
    (r"\brefers to\b", "phrasing", "copulative avoidance: 'refers to' in place of is/are"),
    (r"\bcommitment to\b", "tone", "press-release language: 'commitment to ...'"),
    (r"\bbroader significance\b", "tone", "significance inflation: 'broader significance'"),
    (r"\bplays? a (?:key|vital|significant|critical) role\b", "vocabulary", "significance puffery: 'plays a ... role'"),
    # Markup / tool artifacts (category 6)
    (r"contentReference", "artifact", "ChatGPT citation debris: 'contentReference'"),
    (r"oaicite", "artifact", "ChatGPT citation debris: 'oaicite'"),
    (r"\[cite:\s*\d+\]", "artifact", "Gemini citation debris: '[cite: N]'"),
    # Meta/communication leakage (category 7)
    (r"\bas an ai\b", "meta", "assistant self-reference leaked into content"),
    (r"\bknowledge cutoff\b", "meta", "knowledge-cutoff disclaimer leaked into content"),
    (r"\b(?:my )?training data\b", "meta", "training-data disclaimer leaked into content"),
    (r"\bhere(?:'s| is) (?:a|the) (?:revised|draft|rewritten)\b", "meta", "chat scaffolding leaked into content"),
    (r"\blet me know if\b", "meta", "chat scaffolding leaked into content"),
    (r"\[(?:INSERT|TODO|PLACEHOLDER|YOUR)\b[^\]\n]{0,40}\]", "meta", "unfilled placeholder text"),
    (r"\b(?:option 1|option a)\b[^.!?]{0,60}?\b(?:option 2|option b)\b", "meta", "offering multiple phrasing options"),
    # Structural tell that IS mechanically checkable (category 3)
    (r"[“”‘’]", "structure", "curly quotes (corpus uses straight quotes)"),
    (r"[\U0001F300-\U0001FAFF☀-➿]", "structure", "decorative emoji"),
]

NEGATIVE_PATTERNS: list[tuple[str, str, str]] = [
    (rf"\b{re.escape(w)}\b", "vocabulary", f"vocabulary tell: '{w}'") for w in _WORD_TELLS_VOCAB
] + _GUARDED_WORD_TELLS + _PHRASE_TELLS


# ---------------------------------------------------------------------------
# Structural tells (research doc Part 1, category 3). Added per calibration §8
# item 3: once Delta became informational the regex scan was the only mechanical
# check, and these four were being handed to the human unmeasured.
#
# Thresholds are calibrated against all 69 real held-out docs and a deliberate
# AI-slop control. Two of the four separate them; two do not, and those are
# measured and reported rather than faked into a gate -- same discipline as
# finding 1. Measured maxima over real docs vs the slop control:
#
#   signal                 real max   slop   gates?
#   tables per 1k words       0.26   15.87   yes
#   bold emphasis per 1k     15.38   79.37   yes
#   empty sections (count)       2       2   no -- no separation
#   title-case heading ratio   62.5%   63.6%  no -- the author writes these
#
# Thresholds sit above the real maximum, not at a round number, so the author's
# own writing does not trip them.
TABLE_PER_1K_MAX = 2.0
TABLE_MIN_COUNT = 2
BOLD_EMPH_PER_1K_MAX = 20.0
BOLD_EMPH_MIN_COUNT = 3

_FENCE = re.compile(r"^[ \t]*(?:```|~~~).*?(?:^[ \t]*(?:```|~~~)[ \t]*$|\Z)", re.M | re.S)
_HEADING = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t]*#*$", re.M)
_BOLD = re.compile(r"\*\*(?!\s)[^\n*]{1,120}?\*\*")
_BOLD_LABEL = re.compile(r"^[-*+]?\s*\*\*[^\n*]{1,40}:?\*\*:?")
_TABLE_SEP = re.compile(r"^\s*\|?[\s:]*-{3,}[\s:|-]*\|", re.M)
_HEADING_STOP = {
    "a", "an", "the", "and", "or", "but", "for", "nor", "so", "yet", "at", "by",
    "in", "of", "on", "to", "up", "via", "vs", "with", "from", "into", "over",
    "as", "is", "it", "if", "no", "not", "per", "that", "this",
}


def _strip_code(text: str) -> str:
    """Blank out fenced blocks, preserving line numbers. Shell transcripts are
    full of `# comment` lines that parse as headings and `|` that parses as a
    table -- an early version of this scan reported 35 empty sections in a real
    shell tutorial for exactly that reason."""
    return _FENCE.sub(lambda m: "\n" * m.group(0).count("\n"), text)


def _is_title_case(title: str) -> bool:
    """"Title Case Everywhere": at least 3 plain words, every non-stopword one
    capitalized. Tokens with internal caps or non-letters (CustomerView, tp_dump,
    ZTMSP-2539) are skipped -- their casing isn't a stylistic choice."""
    toks = [t for t in title.split() if re.fullmatch(r"[A-Za-z][a-z']*", t)]
    content = [t for t in toks if t.lower() not in _HEADING_STOP]
    if len(toks) < 3 or len(content) < 3:
        return False
    return all(t[0].isupper() for t in content)


def measure_structure(text: str) -> dict:
    """The four category-3 signals, measured. Prose only -- code fences are
    excluded. Reported for every run; only the two calibrated ones gate."""
    body = _strip_code(text)
    n_words = max(1, len(re.findall(r"[A-Za-z']+", body)))
    headings = [(m.start(), len(m.group(1)), m.group(2)) for m in _HEADING.finditer(body)]

    title_case = [h[2] for h in headings if _is_title_case(h[2])]

    empty_sections = []
    for i, (pos, level, title) in enumerate(headings):
        end = headings[i + 1][0] if i + 1 < len(headings) else len(body)
        section = body[pos:end]
        section = section.split("\n", 1)[1] if "\n" in section else ""
        if section.strip():
            continue
        # A heading whose body is empty because a *deeper* heading follows is
        # ordinary nesting, not the tell; the tell is a section with nothing in it.
        if i + 1 < len(headings) and headings[i + 1][1] > level:
            continue
        empty_sections.append(title)

    emphasis = [
        m for m in _BOLD.finditer(body)
        if not _BOLD_LABEL.match(body[body.rfind("\n", 0, m.start()) + 1:m.end()])
    ]
    tables = _TABLE_SEP.findall(body)

    return {
        "words": n_words,
        "headings": len(headings),
        "title_case_headings": title_case,
        "title_case_ratio": (len(title_case) / len(headings) * 100) if headings else 0.0,
        "empty_sections": empty_sections,
        "bold_emphasis": len(emphasis),
        "bold_emphasis_per_1k": len(emphasis) / n_words * 1000,
        "tables": len(tables),
        "tables_per_1k": len(tables) / n_words * 1000,
    }


def scan_structure(structure: dict) -> list[dict]:
    """The gating subset of the structural signals. One hit per tripped
    threshold; same shape as `scan_negative_list` hits so the gate can treat
    them identically. Line numbers aren't meaningful for a density measure, so
    these report 0."""
    hits = []
    if (structure["tables"] >= TABLE_MIN_COUNT
            and structure["tables_per_1k"] > TABLE_PER_1K_MAX):
        hits.append({
            "category": "structure",
            "label": (f"unnecessary tables: {structure['tables']} tables, "
                      f"{structure['tables_per_1k']:.1f} per 1k words "
                      f"(real docs max 0.26)"),
            "match": f"{structure['tables']} tables",
            "line": 0,
        })
    if (structure["bold_emphasis"] >= BOLD_EMPH_MIN_COUNT
            and structure["bold_emphasis_per_1k"] > BOLD_EMPH_PER_1K_MAX):
        hits.append({
            "category": "structure",
            "label": (f"boldface overuse: {structure['bold_emphasis']} rhetorical bolds, "
                      f"{structure['bold_emphasis_per_1k']:.1f} per 1k words "
                      f"(real docs max 15.4; label-style **NOTE:** bolds excluded)"),
            "match": f"{structure['bold_emphasis']} bold spans",
            "line": 0,
        })
    return hits


def scan_negative_list(text: str) -> list[dict]:
    """Mechanical regex scan for Part 1 tells. Returns one hit per (pattern,
    match) with enough context that a reviewer can find and fix it."""
    hits = []
    for pattern, category, label in NEGATIVE_PATTERNS:
        for m in re.finditer(pattern, text, flags=re.IGNORECASE | re.MULTILINE):
            line = text.count("\n", 0, m.start()) + 1
            hits.append({
                "category": category,
                "label": label,
                "match": m.group(0),
                "line": line,
            })
    hits.sort(key=lambda h: (h["line"], h["label"]))
    return hits


def load_profile(fmt: str) -> sm.LayerOneProfile:
    path = PROFILE_DIR / f"layer1-{fmt}.json"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} missing -- this writing-in-voice install is incomplete "
            "or corrupted; reinstall the package"
        )
    raw = json.loads(path.read_text(encoding="utf-8"))
    return sm.LayerOneProfile(
        vocab=raw["vocab"],
        function_word_stats={w: tuple(v) for w, v in raw["function_word_stats"].items()},
        metrics={n: tuple(v) for n, v in raw["metrics"].items()},
    )


def validate(text: str, fmt: str) -> dict:
    profile = load_profile(fmt)
    scores = sm.score_against_profile(text, profile)
    hits = scan_negative_list(text)
    structure = measure_structure(text)
    structural_hits = scan_structure(structure)
    out_of_range = {
        name: z for name, z in scores["metric_z"].items() if abs(z) > METRIC_Z_REPORT
    }
    return {
        "format": fmt,
        "delta": scores["delta"],
        "overall": scores["overall"],
        "metric_z": scores["metric_z"],
        "out_of_range": out_of_range,
        "negative_hits": hits,
        "structure": structure,
        "structural_hits": structural_hits,
        "delta_in_observed_band": scores["delta"] <= DELTA_OBSERVED_MAX,
        "passed": not hits and not structural_hits,
    }


def format_report(result: dict) -> str:
    lines = [
        f"# Voice validation -- {result['format']}",
        "",
        f"Result: **{'PASS' if result['passed'] else 'FAIL'}** "
        f"({len(result['negative_hits'])} negative-list hits, "
        f"{len(result['structural_hits'])} structural hits -- "
        "together the only failure condition)",
        "",
        "## Informational (not pass/fail)",
        "",
        f"Delta: {result['delta']:.3f} -- "
        + ("inside" if result["delta_in_observed_band"] else "**outside**")
        + f" the {DELTA_OBSERVED_MAX} band that real corpus docs occupy. Delta does not"
        " separate this author's writing from generic AI prose (calibration finding 1),"
        " so treat it as context, not evidence the voice landed.",
        f"Overall score: {result['overall']:.3f}",
        "",
    ]

    if result["out_of_range"]:
        lines.append(f"## Metrics beyond +/-{METRIC_Z_REPORT} stdev of target")
        lines.append("")
        lines.append("| Metric | z |")
        lines.append("|---|---|")
        for name, z in sorted(result["out_of_range"].items(), key=lambda kv: -abs(kv[1])):
            lines.append(f"| {name} | {z:+.2f} |")
        lines.append("")
    else:
        lines.append(f"All Layer 1 metrics within +/-{METRIC_Z_REPORT} stdev of target.")
        lines.append("")

    s = result["structure"]
    lines.append("## Structural signals (category 3)")
    lines.append("")
    lines.append("| Signal | Measured | Gates? |")
    lines.append("|---|---|---|")
    lines.append(f"| tables | {s['tables']} ({s['tables_per_1k']:.2f}/1k words) "
                 f"| yes, above {TABLE_PER_1K_MAX}/1k |")
    lines.append(f"| rhetorical boldface | {s['bold_emphasis']} "
                 f"({s['bold_emphasis_per_1k']:.2f}/1k words) "
                 f"| yes, above {BOLD_EMPH_PER_1K_MAX}/1k |")
    lines.append(f"| title-case headings | {len(s['title_case_headings'])} of "
                 f"{s['headings']} ({s['title_case_ratio']:.0f}%) "
                 "| no -- real docs reach 62%, eyeball it |")
    lines.append(f"| empty sections | {len(s['empty_sections'])} "
                 "| no -- no separation from real docs, eyeball it |")
    lines.append("")
    if s["title_case_headings"]:
        lines.append("Title-case headings: "
                     + ", ".join(f"`{t}`" for t in s["title_case_headings"][:8]))
        lines.append("")
    if s["empty_sections"]:
        lines.append("Empty sections: "
                     + ", ".join(f"`{t}`" for t in s["empty_sections"][:8]))
        lines.append("")

    lines.append("## The gate -- negative list plus calibrated structural thresholds")
    lines.append("")

    if result["structural_hits"]:
        lines.append(f"### {len(result['structural_hits'])} structural hits")
        lines.append("")
        for h in result["structural_hits"]:
            lines.append(f"- {h['label']}")
        lines.append("")

    if result["negative_hits"]:
        lines.append(f"### {len(result['negative_hits'])} negative-list hits -- hard constraint, any one of these fails the run")
        lines.append("")
        lines.append("| Line | Category | Tell | Matched |")
        lines.append("|---|---|---|---|")
        for h in result["negative_hits"]:
            lines.append(f"| {h['line']} | {h['category']} | {h['label']} | `{h['match']}` |")
        lines.append("")
    elif not result["structural_hits"]:
        lines.append("No negative-list or structural hits.")
        lines.append("")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--format", required=True, choices=FORMATS)
    ap.add_argument("--file", help="candidate text file; omit to read stdin")
    ap.add_argument("--json", action="store_true", help="emit raw JSON instead of a markdown report")
    args = ap.parse_args(argv)

    text = Path(args.file).read_text(encoding="utf-8") if args.file else sys.stdin.read()
    if not text.strip():
        print("error: candidate text is empty", file=sys.stderr)
        return 2

    try:
        result = validate(text, args.format)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(result, indent=1) if args.json else format_report(result))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
