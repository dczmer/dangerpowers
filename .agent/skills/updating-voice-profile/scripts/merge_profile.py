"""Fold new documents into a writing-in-voice Layer 1 profile.

Layer 1 stores, per format, a weighted mean and weighted population stdev for
every function word and numeric metric, plus the total weight they were built
from. That is enough to merge new docs in exactly, without the original
corpus: combine the two weighted means, and combine E[x^2] the same way.

After merging (or with --render-only) this regenerates layer1-<format>.md from
the JSON so the markdown targets the drafting model reads never drift from the
numbers the validator scores against.

Usage:
    python3 merge_profile.py --format notes --docs a.md b.md [--weight 0.3] [--dry-run]
    python3 merge_profile.py --format notes --render-only

Exit status: 0 = ok, 2 = setup error (unknown format, missing profile,
profile without total_weight, unreadable or empty docs).
"""

import argparse
import json
import math
import sys
from pathlib import Path

DEFAULT_SKILL_DIR = Path(__file__).resolve().parents[2] / "writing-in-voice"

# Matches the original corpus build: docs the author fully wrote count 1.0,
# secondary docs (mostly others' text with the author's comments mixed in)
# count 0.3 so they shape the profile without dominating it.
SECONDARY_WEIGHT = 0.3

# How many function words the markdown table shows. The validator uses all of
# them; the drafting model only needs the top of the distribution.
TOP_FUNCTION_WORDS = 15


def merge_stat(old: list[float], w_old: float, new: tuple[float, float], w_new: float) -> list[float]:
    (m1, s1), (m2, s2) = old, new
    total = w_old + w_new
    mean = (w_old * m1 + w_new * m2) / total
    ex2 = (w_old * (s1 ** 2 + m1 ** 2) + w_new * (s2 ** 2 + m2 ** 2)) / total
    return [mean, math.sqrt(max(ex2 - mean ** 2, 0.0))]


def render_markdown(fmt: str, raw: dict) -> str:
    lines = [
        f"# Layer 1 Stylometry -- {fmt}",
        "",
        f"Profile built from {raw['doc_count']} docs, total weight {raw['total_weight']:.1f} "
        f"(primary docs 1.0, secondary docs {SECONDARY_WEIGHT}).",
        "",
        "## Numeric target ranges (mean +/- stdev)",
        "",
        "| Metric | Target mean | Target stdev |",
        "|---|---|---|",
    ]
    for name, (mean, stdev) in raw["metrics"].items():
        lines.append(f"| {name} | {mean:.3f} | {stdev:.3f} |")
    lines += [
        "",
        "## Top function words by frequency",
        "",
        "| Word | Mean freq /1000 words | Stdev |",
        "|---|---|---|",
    ]
    top = sorted(raw["function_word_stats"].items(), key=lambda kv: -kv[1][0])[:TOP_FUNCTION_WORDS]
    for word, (mean, stdev) in top:
        lines.append(f"| {word} | {mean:.3f} | {stdev:.3f} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--format", required=True)
    ap.add_argument("--docs", nargs="*", default=[])
    ap.add_argument("--weight", type=float, default=1.0,
                    help=f"per-doc weight: 1.0 for primary docs, {SECONDARY_WEIGHT} for secondary")
    ap.add_argument("--skill-dir", type=Path, default=DEFAULT_SKILL_DIR)
    ap.add_argument("--dry-run", action="store_true", help="print the changes, write nothing")
    ap.add_argument("--render-only", action="store_true", help="only regenerate the markdown")
    args = ap.parse_args()

    sys.path.insert(0, str(args.skill_dir / "scripts"))
    try:
        import stylometry as sm
        import validate_voice as vv
    except ImportError as e:
        print(f"setup error: cannot import writing-in-voice scripts from {args.skill_dir}: {e}",
              file=sys.stderr)
        return 2

    if args.format not in vv.FORMATS:
        print(f"setup error: format must be one of {vv.FORMATS}", file=sys.stderr)
        return 2
    json_path = args.skill_dir / "voice-profile" / f"layer1-{args.format}.json"
    md_path = json_path.with_suffix(".md")
    if not json_path.is_file():
        print(f"setup error: {json_path} missing", file=sys.stderr)
        return 2
    raw = json.loads(json_path.read_text(encoding="utf-8"))
    if "total_weight" not in raw or "doc_count" not in raw:
        print(f"setup error: {json_path} has no total_weight/doc_count; cannot merge exactly",
              file=sys.stderr)
        return 2

    if not args.render_only:
        if not args.docs:
            print("setup error: --docs is required unless --render-only", file=sys.stderr)
            return 2
        try:
            docs = sm.load_docs(args.docs)
        except OSError as e:
            print(f"setup error: {e}", file=sys.stderr)
            return 2
        empty = [d.identity for d in docs if not d.words]
        if empty:
            print(f"setup error: no words in {empty}", file=sys.stderr)
            return 2
        for d in docs:
            d.weight = args.weight

        new = sm.build_profile(docs, raw["vocab"])
        w_old, w_new = raw["total_weight"], args.weight * len(docs)
        merged_metrics = {
            name: merge_stat(raw["metrics"][name], w_old, new.metrics[name], w_new)
            for name in raw["metrics"]
        }
        for name, (mean, stdev) in merged_metrics.items():
            old_mean, old_stdev = raw["metrics"][name]
            print(f"{name}: mean {old_mean:.3f} -> {mean:.3f}, stdev {old_stdev:.3f} -> {stdev:.3f}")
        print(f"total_weight: {w_old:.1f} -> {w_old + w_new:.1f}; "
              f"doc_count: {raw['doc_count']} -> {raw['doc_count'] + len(docs)}")
        if args.dry_run:
            return 0

        raw["function_word_stats"] = {
            w: merge_stat(raw["function_word_stats"][w], w_old, new.function_word_stats[w], w_new)
            for w in raw["vocab"]
        }
        raw["metrics"] = merged_metrics
        raw["total_weight"] = w_old + w_new
        raw["doc_count"] += len(docs)
        json_path.write_text(json.dumps(raw, indent=1) + "\n", encoding="utf-8")

    md_path.write_text(render_markdown(args.format, raw), encoding="utf-8")
    print(f"wrote {md_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
