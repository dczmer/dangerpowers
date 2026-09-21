#!/usr/bin/env python3
"""Evaluator: run one query (--expect trigger|not-trigger) for N reps against a
harness workspace and report whether the skill under test loaded.

Every rep runs under the restricted `trigger-evaluator` agent (skill tool only,
steps capped), installed into the workspace by the harness strategy before any
rep. Harness specifics live in the strategy registry in strategies.py; only
opencode is implemented.

Scope: the trigger inner core (eval_batch: one invocation = one query), the
retrieval campaign tooling (retrieval-suite, scored-check, record with
--scope frontmatter|dir), the shape campaign tooling (shape-suite,
shape-evidence, shape-scored-check, record --track shape-test), and the
pressure campaign tooling (pressure-suite, pressure-evidence, pressure-meta,
pressure-scored-check, record --track pressure-test).
"""

import argparse
import hashlib
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

from src.common import (
    _err,
    _Log,
    _score_counts,
    _scored_target_gate,
    base_config,
    check_coverage,
    counts_gate,
    emit,
    load_scored_json,
    union_results,
)
from src.strategies import (
    _fail,
    check_harness,
    resolve_strategy,
)
from src.tracks import (
    TRACKS,
    Track,
    cmd_run,
    cmd_split,
)


def cmd_check(args: argparse.Namespace) -> int:
    strategy_cls = resolve_strategy(args.harness)
    check_harness(args.harness, strategy_cls, args.model)
    return 0


# --------------------------------------------------------------------------
# Generic suite driver


def run_suite(track: Track, args: argparse.Namespace) -> int:
    """The generic campaign driver: strategy resolution, pre-spend gates
    (track-owned, historical order), log mirror, install, banner, the
    entry loop, and the results write (track envelope). Per-entry
    progress and arm orchestration live in track.run_entry."""
    strategy_cls = resolve_strategy(args.harness)
    # The tracks call the preflight through this instance attribute at
    # their historical check_harness position inside pre_spend_gates;
    # binding it here (rather than a tracks.py import) keeps the test
    # suite's historical patch point, evaluator.check_harness, working.
    track._harness_preflight = check_harness
    entries = track.pre_spend_gates(args, strategy_cls)
    if isinstance(entries, int):
        return entries
    out = Path(args.out)
    # The log mirror opens BEFORE the zero_results_on_empty branch: this
    # preserves the historical trigger behavior (the old cmd_suite opened
    # _Log.file at evaluator.py 496, before the empty-query return at 519)
    # — an empty trigger campaign still creates/truncates the .log and the
    # "note: empty query file" line is mirrored into it. It also prevents
    # the note from mirroring into a stale _Log.file handle in long-lived
    # processes (the test suite runs many campaigns in one process).
    _Log.file = out.with_suffix(".log").open("w")
    if not entries and track.zero_results_on_empty:
        track.write_empty(args)
        return 0
    strategy = strategy_cls(timeout=args.timeout)
    track.install_agents(strategy, args)
    for line in track.banner(args, len(entries)):
        emit(line)
    results: list[dict] = []
    for entry in entries:
        record = track.run_entry(strategy, entry, args)
        if isinstance(record, int):
            return record  # mid-campaign abort (retrieval arm failure)
        results.append(record)
    config = base_config(args)
    config.update(track.extra_config(args))
    out.write_text(
        json.dumps(track.finalize(config, results), indent=2) + "\n"
    )
    emit(track.done_line(len(entries), out))
    return 0


def score_from_results(results_path: Path) -> float | str:
    """Trigger score (Wilson lower bound) over a suite results file's
    recorded outcomes, reusing _score_counts. Which file to pass is the
    driver's documented decision: the validate pass's results when a
    validate split ran, else the winner iteration's train results.
    Returns the exact error message on any violation."""
    if not results_path.exists():
        return f"results file not found: {results_path}"
    try:
        data = json.loads(results_path.read_text())
    except json.JSONDecodeError as e:
        return f"invalid JSON in {results_path}: {e}"
    if not isinstance(data, dict) or not isinstance(data.get("queries"), list):
        return (
            f"{results_path}: not a suite result file (missing 'queries' "
            f"list)"
        )
    passed = failed = 0
    for i, q in enumerate(data["queries"]):
        if not isinstance(q, dict):
            return f"{results_path}: query {i} is not an object"
        passed += q.get("passed") or 0
        failed += q.get("failed") or 0
    _low, _high, score = _score_counts(passed, failed)
    if score is None:
        return f"{results_path}: no non-void outcomes to score"
    return score


def extract_frontmatter(text: str) -> str | None:
    """The frontmatter block exactly as workspace-manager.sh
    extract_frontmatter produces it: the opening `---` line through the
    closing `---` line, inclusive. These are the same bytes the eval stub
    carries, so they are what a recorded score was measured against.
    Returns None when the file has no terminated frontmatter block."""
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\n") != "---":
        return None
    block = [lines[0]]
    for line in lines[1:]:
        block.append(line)
        if line.rstrip("\n") == "---":
            return "".join(block)
    return None


def _scored_track_signals(scored_entries: list[dict]) -> list[str]:
    """Collect the set of tracks the scored entries can be proven to
    belong to, using only discriminating signals (each scored track's
    scored_signal over the registry)."""
    hits = {
        name: False for name, track in TRACKS.items() if track.supports_scored
    }
    for e in scored_entries:
        if not isinstance(e, dict):
            continue
        for name, track in TRACKS.items():
            if track.supports_scored and track.scored_signal(e):
                hits[name] = True
    return [name for name, hit in hits.items() if hit]


def sums_from_scored(
    scored_path: Path, track: str | None = None
) -> tuple[str, dict[str, int]] | str:
    """Load scored.json and derive (track, manifest count sums) from the
    result values, mapping the result vocabulary to the manifest key
    vocabulary for the detected track. When an explicit track is given
    it must be consistent with the detection; when nothing in the file
    discriminates, the explicit track is used and its absence is an
    error — never a guess. Returns the exact error message on any
    violation."""
    scored_entries = load_scored_json(scored_path)
    if isinstance(scored_entries, str):
        return scored_entries
    signals = _scored_track_signals(scored_entries)
    if len(signals) > 1:
        return (
            f"{scored_path}: results mix track vocabularies "
            f"({', '.join(signals)}); refusing to guess a track"
        )
    if track is not None and signals and track != signals[0]:
        return (
            f"--track {track} does not match the scored results "
            f"(detected {signals[0]})"
        )
    resolved = track or (signals[0] if signals else None)
    if resolved is None:
        return (
            f"{scored_path}: no track-discriminating results; pass "
            f"--track explicitly"
        )
    vocab = TRACKS[resolved].sum_keys
    sums = {manifest_key: 0 for manifest_key in vocab.values()}
    for i, e in enumerate(scored_entries):
        result = e.get("result") if isinstance(e, dict) else None
        if result not in vocab:
            return (
                f"{scored_path}: entry {i}: result {result!r} is not in "
                f"the {resolved} vocabulary ({', '.join(vocab)})"
            )
        sums[vocab[result]] += 1
    return resolved, sums


def _scored_skeleton_header(results_paths: list[str]) -> dict:
    """campaign/skill header for the retrieval and pressure skeletons.
    The scored-checks never validate the header, so these values are
    driver context only: 'skill' comes from the first results file's
    config block, 'campaign' from that file's parent directory when it
    is named campaign-*, else the 'pilot' placeholder."""
    skill = "pilot"
    parent = Path(results_paths[0]).resolve().parent.name
    try:
        data = json.loads(Path(results_paths[0]).read_text())
    except (OSError, json.JSONDecodeError):
        data = {}
    config = data.get("config") if isinstance(data, dict) else None
    if isinstance(config, dict) and isinstance(config.get("skill"), str):
        skill = config["skill"] or "pilot"
    campaign = parent if parent.startswith("campaign-") else "pilot"
    return {"campaign": campaign, "skill": skill}


def _any_counts_given(args: argparse.Namespace) -> bool:
    return any(
        getattr(args, n, None) is not None
        for n in (
            "passes",
            "fails",
            "gaps",
            "voids",
            "adopted",
            "no_failure",
            "unresolved",
            "bulletproof",
        )
    )


def hash_skill_dir(skill_dir: Path) -> str:
    """Deterministic sha256 over a whole skill directory: sorted relative
    paths, __pycache__/ and *.pyc excluded (the exact set sync --full
    excludes), relpath\0bytes\0 fed per file."""
    h = hashlib.sha256()
    root = skill_dir.resolve()
    # Symlinks enter the candidate list even when they point at a directory,
    # so the rejection policy below can fire on them (rglob+is_dir would
    # silently drop them, disagreeing with sync --full's explicit check).
    files = sorted(
        (p for p in skill_dir.rglob("*") if not p.is_dir() or p.is_symlink()),
        key=lambda p: p.relative_to(skill_dir).as_posix(),
    )
    for p in files:
        rel = p.relative_to(skill_dir)
        if "__pycache__" in rel.parts or p.suffix == ".pyc":
            continue
        if p.is_symlink() and (
            p.resolve().is_dir() or root not in p.resolve().parents
        ):
            print(
                f"error: unsupported symlink in skill dir: {p}",
                file=sys.stderr,
            )
            sys.exit(1)
        h.update(rel.as_posix().encode())
        h.update(b"\0")
        h.update(p.read_bytes())  # reads through internal file symlinks
        h.update(b"\0")
    return "sha256:" + h.hexdigest()


def cmd_record(args: argparse.Namespace) -> int:
    """Write/update one track's manifest key after a completed campaign.
    Overwrites only the scope's key (`trigger-test`, `retrieval-test`,
    `shape-test`, or `pressure-test` with --scope dir --track); unknown
    keys are preserved. With --scope dir --scored, the counts come from
    the scored.json result sums and the track is detected from the file
    (an explicit --track is checked against the detection); the legacy
    counts-flag path is retained one release and prints a deprecation
    note. --scope dir --track selects the count vocabulary for the
    legacy path: retrieval-test uses passes/fails/gaps/voids (the
    default, back-compatible), shape-test uses
    adopted/no-failure/unresolved/voids, pressure-test uses
    bulletproof/no-failure/unresolved/voids."""
    skill_path = Path(args.skill_path)
    scope = getattr(args, "scope", "frontmatter")

    if getattr(args, "score_from", None) is not None:
        if args.score is not None:
            return _err("--score is replaced by --score-from")
        score = score_from_results(Path(args.score_from))
        if isinstance(score, str):
            return _err(score)
        args.score = score

    if scope == "frontmatter":
        if getattr(args, "scored", None) is not None:
            return _err("--scored is only valid with --scope dir")
        if args.score is None:
            return _err("--score is required with --scope frontmatter")
        if _any_counts_given(args):
            return _err("counts are only valid with --scope dir")
        if not skill_path.is_file():
            return _err(
                f"--scope frontmatter expects a SKILL.md file: {skill_path}"
            )
        if not (0.0 <= args.score <= 1.0):
            return _err("--score must be in [0, 1]")
        frontmatter = extract_frontmatter(skill_path.read_text())
        if frontmatter is None:
            return _err(f"missing or unterminated frontmatter in {skill_path}")
        checksum = "sha256:" + hashlib.sha256(frontmatter.encode()).hexdigest()
        entry = {
            "date": args.date or datetime.now(UTC).date().isoformat(),
            "checksum": checksum,
            "score": args.score,
        }
        key = "trigger-test"
    else:  # dir
        if args.score is not None:
            return _err("--score is only valid with --scope frontmatter")
        if not skill_path.is_dir():
            return _err(
                f"--scope dir expects the skill directory: {skill_path}"
            )
        checksum = hash_skill_dir(skill_path)
        if getattr(args, "scored", None) is not None:
            if _any_counts_given(args):
                return _err("counts flags are replaced by --scored")
            track_sums = sums_from_scored(
                Path(args.scored), getattr(args, "track", None)
            )
            if isinstance(track_sums, str):
                return _err(track_sums)
            track, sums = track_sums
            entry = {
                "date": args.date or datetime.now(UTC).date().isoformat(),
                "checksum": checksum,
                **sums,
            }
            if args.ablations is not None:
                entry["ablations"] = args.ablations
            key = track
        else:
            # Legacy counts-flag path, retained one release for
            # back-compat; the deprecation note fires on stderr only
            # when this path actually records.
            track = getattr(args, "track", None) or "retrieval-test"
            if track == "shape-test":
                # voids is shared by both vocabularies; the retrieval-only
                # counts must not appear on a shape-test record.
                if any(
                    getattr(args, n, None) is not None
                    for n in (
                        "passes",
                        "fails",
                        "gaps",
                        "ablations",
                        "bulletproof",
                    )
                ):
                    return _err(
                        "passes/fails/gaps/ablations/bulletproof are only "
                        "valid with --track retrieval-test or --track "
                        "pressure-test"
                    )
                missing = [
                    n
                    for n in ("adopted", "no_failure", "unresolved", "voids")
                    if getattr(args, n, None) is None
                ]
                if missing:
                    return _err(
                        "counts required with --scope dir --track "
                        "shape-test: " + ", ".join(missing)
                    )
                entry = {
                    "date": args.date or datetime.now(UTC).date().isoformat(),
                    "checksum": checksum,
                    "adopted": args.adopted,
                    "no-failure": args.no_failure,
                    "unresolved": args.unresolved,
                    "voids": args.voids,
                }
                key = "shape-test"
            elif track == "pressure-test":
                # voids/no_failure/unresolved are shared with the shape
                # vocabulary; the retrieval and shape-only counts must
                # not appear on a pressure-test record.
                if any(
                    getattr(args, n, None) is not None
                    for n in (
                        "passes",
                        "fails",
                        "gaps",
                        "ablations",
                        "adopted",
                    )
                ):
                    return _err(
                        "passes/fails/gaps/ablations/adopted are only "
                        "valid with --track retrieval-test or --track "
                        "shape-test"
                    )
                missing = [
                    n
                    for n in (
                        "bulletproof",
                        "no_failure",
                        "unresolved",
                        "voids",
                    )
                    if getattr(args, n, None) is None
                ]
                if missing:
                    return _err(
                        "counts required with --scope dir --track "
                        f"pressure-test: {', '.join(missing)}"
                    )
                entry = {
                    "date": args.date or datetime.now(UTC).date().isoformat(),
                    "checksum": checksum,
                    "bulletproof": args.bulletproof,
                    "no-failure": args.no_failure,
                    "unresolved": args.unresolved,
                    "voids": args.voids,
                }
                key = "pressure-test"
            else:
                if any(
                    getattr(args, n, None) is not None
                    for n in (
                        "adopted",
                        "no_failure",
                        "unresolved",
                        "bulletproof",
                    )
                ):
                    return _err(
                        "adopted/no-failure/unresolved/bulletproof are "
                        "only valid with --track shape-test or --track "
                        "pressure-test"
                    )
                missing = [
                    n
                    for n in ("passes", "fails", "gaps", "voids")
                    if getattr(args, n, None) is None
                ]
                if missing:
                    return _err(
                        "counts required with --scope dir: "
                        f"{', '.join(missing)}"
                    )
                entry = {
                    "date": args.date or datetime.now(UTC).date().isoformat(),
                    "checksum": checksum,
                    "passes": args.passes,
                    "fails": args.fails,
                    "gaps": args.gaps,
                    "voids": args.voids,
                }
                if args.ablations is not None:
                    entry["ablations"] = args.ablations
                key = "retrieval-test"
            print(
                "note: counts flags are deprecated; use --scored",
                file=sys.stderr,
            )

    if args.campaign is not None:
        entry["campaign"] = args.campaign

    manifest = Path(args.manifest)
    data: dict = {}
    if manifest.exists():
        try:
            data = json.loads(manifest.read_text())
        except json.JSONDecodeError as e:
            print(f"error: invalid JSON in {manifest}: {e}", file=sys.stderr)
            return 1
        if not isinstance(data, dict):
            print(
                f"error: {manifest}: expected a JSON object", file=sys.stderr
            )
            return 1

    data["skill"] = args.skill
    data[key] = entry

    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(data, indent=2) + "\n")
    if scope == "frontmatter":
        detail = f"score {args.score}"
    else:
        detail = " / ".join(
            f"{entry[k]} {k}" for k in TRACKS[key].sum_keys.values()
        )
    print(
        f"recorded: {manifest} (scope {scope}, date {entry['date']}, "
        f"{detail}, {checksum[:26]}…)"
    )
    return 0


# --------------------------------------------------------------------------
# Interim generic drivers (plan §2.7b, Phase-2 form): the track is a
# leading parameter and the dispatch below hardcodes it per old command
# name; Phase 3 replaces the parameter with TRACKS[args.track] on the
# unified parsers and adds the gates only a merged parser makes
# reachable.


def _scored_check(track: Track, args: argparse.Namespace) -> int:
    """Validate scored.json against the results files it claims to cover
    (generic driver, plan §2.7b Phase-2 form: leading track parameter;
    Phase 3 promotes it to cmd_scored_check(args) reading TRACKS[args.
    track] on the unified parser). Named apart from the legacy command
    because `cmd_scored_check` stays bound to its historical single-arg
    signature below and pyright's reportRedeclaration forbids the
    shadowing redefinition. Per-entry rules live in the track's
    check_scored_entry. Exact messages, exit 1 on any violation; exit 0
    with a coverage line when every results id is accounted for exactly
    once; the record-step counts flags must match the scored sums when
    given. With --emit-skeleton PATH instead of --scored, writes a
    scored.json skeleton (every results id once, mechanically derivable
    fields pre-filled, judgment fields null) and exits 0."""
    gate = _scored_target_gate(args)
    if gate is not None:
        return gate
    results_paths = (
        [args.results] if isinstance(args.results, str) else args.results
    )
    union = union_results(
        results_paths, track.results_noun, entry_hook=track.union_hook
    )
    if isinstance(union, str):
        return _err(union)
    results_ids, results_arms, extras = union

    if getattr(args, "emit_skeleton", None) is not None:
        out_path = Path(args.emit_skeleton)
        header = (
            _scored_skeleton_header(results_paths)
            if track.skeleton_header
            else None
        )
        entries = [track.skeleton_entry(eid, extras) for eid in results_ids]
        doc = dict(header) if header else {}
        doc["entries"] = entries
        out_path.write_text(json.dumps(doc, indent=2) + "\n")
        print(f"wrote skeleton: {out_path} ({len(results_ids)} entries)")
        return 0

    scored_path = Path(args.scored)
    scored_entries = load_scored_json(scored_path, track.scored_object_phrase)
    if isinstance(scored_entries, str):
        return _err(scored_entries)
    covered_entries = check_coverage(scored_entries, results_ids, scored_path)
    if isinstance(covered_entries, str):
        return _err(covered_entries)
    for entry in covered_entries:
        rc = track.check_scored_entry(
            scored_path, entry, results_arms[entry["id"]], extras
        )
        if rc is not None:
            return rc
    rc = counts_gate(
        args,
        covered_entries,
        track.count_arg_names,
        track.count_result_names,
    )
    if rc is not None:
        return rc
    print(f"ok: {scored_path} covers {len(results_ids)} entries")
    return 0


def cmd_evidence(track: Track, args: argparse.Namespace) -> int:
    """Generic evidence dispatcher, Phase-2 form: the old per-track
    parsers already restrict the flags each command accepts, so the
    --arm/--compare pairing gates arrive only with the unified parser
    (Phase 3)."""
    return track.print_evidence(args)


def cmd_scored_check(args: argparse.Namespace) -> int:
    """The scored-check command (retrieval track), via the generic
    scored-check driver. The one-arg binding stays until Phase 3's
    unified parser promotes the generic _scored_check to this name."""
    return _scored_check(TRACKS["retrieval-test"], args)


def cmd_meta(track: Track, args: argparse.Namespace) -> int:
    """Session resume; pressure-only today via supports_meta. The
    binary-only harness preflight lives here in the driver, per the
    old cmd_pressure_meta's check_harness position."""
    strategy_cls = resolve_strategy(args.harness)
    check_harness(args.harness, strategy_cls)  # binary only
    return track.run_meta(args, strategy_cls)


# --------------------------------------------------------------------------
# Inventory tooling: rules.json / facts.json validation, id minting, diff

# One implementation serving all three multi-rule tracks: kind "rule" is a
# rules.json (item array "rules", ids prefixed "R"); kind "fact" is a
# facts.json (item array "facts", ids prefixed "F"). The schemas differ in
# exactly one field: rule items/excluded entries carry 'kind', fact ones do
# not (verified against the committed inventories).
INVENTORY_KINDS = {"rule": "R", "fact": "F"}
INVENTORY_ARRAYS = {"rule": "rules", "fact": "facts"}


def _section_slug(section: str) -> str:
    """'## When to use' -> 'when-to-use'; lowercase, non-alnum runs -> '-',
    stripped. Deterministic and stable across regenerations."""
    return re.sub(r"[^a-z0-9]+", "-", section.lower()).strip("-")


def mint_inventory_id(kind_prefix: str, section: str, n: int) -> str:
    """The canonical id form: <prefix>-<section-slug>-<nn>, e.g.
    'R-when-to-use-03'."""
    return f"{kind_prefix}-{_section_slug(section)}-{n:02d}"


def _inventory_require_str(
    path: Path, label: str, i: int | str, item: dict, field: str
) -> str:
    value = item.get(field)
    if not isinstance(value, str) or not value:
        _fail(f"{path}: {label} {i} missing '{field}' (non-empty string)")
    return value


def load_inventory(path: Path, kind: str, allow_idless: bool = False) -> dict:
    """Load a rules.json/facts.json inventory and validate the unified
    schema: skill/generated header, the item array named by kind, and an
    excluded list whose entries carry a routing reason. Item ids must be
    unique across the items and the excluded list. On any violation prints
    `error: <exact reason>` to stderr and exits 1. With allow_idless
    (inventory-mint on a draft) items missing 'id' are accepted so ids can
    be assigned; every other command requires ids on all items."""
    array_name = INVENTORY_ARRAYS[kind]
    if not path.exists():
        _fail(f"inventory file not found: {path}")
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        _fail(f"invalid JSON in {path}: {e}")
    if not isinstance(data, dict):
        _fail(f"{path}: expected a JSON object with a '{array_name}' list")
    for key in ("skill", "generated"):
        _inventory_require_str(path, "header", key, data, key)
    items = data.get(array_name)
    if not isinstance(items, list):
        _fail(f"{path}: missing '{array_name}' list")
    excluded = data.get("excluded")
    if not isinstance(excluded, list):
        _fail(f"{path}: missing 'excluded' list")
    seen: set[str] = set()
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            _fail(f"{path}: item {i} is not an object")
        if kind == "rule":
            _inventory_require_str(path, "item", i, item, "kind")
        _inventory_require_str(path, "item", i, item, "section")
        _inventory_require_str(path, "item", i, item, "statement")
        if not isinstance(item.get("entries"), list):
            _fail(f"{path}: item {i} missing 'entries' (list)")
        eid = item.get("id")
        if not isinstance(eid, str) or not eid:
            if not allow_idless:
                _fail(f"{path}: item {i} missing 'id' (non-empty string)")
        elif eid in seen:
            _fail(f"{path}: duplicate id: {eid}")
        else:
            seen.add(eid)
    for i, entry in enumerate(excluded):
        if not isinstance(entry, dict):
            _fail(f"{path}: excluded entry {i} is not an object")
        if kind == "rule":
            _inventory_require_str(path, "excluded entry", i, entry, "kind")
        eid = _inventory_require_str(path, "excluded entry", i, entry, "id")
        _inventory_require_str(path, "excluded entry", i, entry, "section")
        _inventory_require_str(path, "excluded entry", i, entry, "reason")
        if eid in seen:
            _fail(f"{path}: duplicate id: {eid}")
        seen.add(eid)
    return data


def _inventory_array(inv: dict) -> str:
    return "rules" if isinstance(inv.get("rules"), list) else "facts"


def inventory_diff(old: dict, new: dict) -> dict:
    """Set logic over ids between two validated inventories:
      new:       new items whose id is in neither old items nor old excluded
      changed:   items in both whose statement/entries/kind differ, each
                 recorded as {id, fields, old, new}
      deleted:   old items absent from new items and from new excluded
                 (an item moved into new.excluded is a state change in
                 the excluded bucket, never a deletion)
      excluded:  only exclusions whose state changed: 'newly-excluded'
                 (in new.excluded, unknown to old.excluded) or
                 'resurrected' (was excluded in old, back in new items);
                 an unchanged exclusion appears in no bucket, keeping a
                 no-op diff empty in all four
    Pure function; no I/O."""
    array = _inventory_array(old)
    old_by_id = {item["id"]: item for item in old[array]}
    old_excluded_ids = {entry["id"] for entry in old["excluded"]}
    new_ids = {item["id"] for item in new[array]}
    new_excluded_ids = {entry["id"] for entry in new["excluded"]}
    added: list[dict] = []
    changed: list[dict] = []
    for item in new[array]:
        eid = item["id"]
        prior = old_by_id.get(eid)
        if prior is None:
            if eid not in old_excluded_ids:
                added.append(item)
            continue
        fields = [
            f
            for f in ("statement", "entries", "kind")
            if prior.get(f) != item.get(f)
        ]
        if fields:
            changed.append(
                {"id": eid, "fields": fields, "old": prior, "new": item}
            )
    deleted = [
        item
        for item in old[array]
        if item["id"] not in new_ids and item["id"] not in new_excluded_ids
    ]
    excluded: list[dict] = []
    for entry in new["excluded"]:
        if entry["id"] not in old_excluded_ids:
            excluded.append({**entry, "status": "newly-excluded"})
    for entry in old["excluded"]:
        if entry["id"] not in new_excluded_ids and entry["id"] in new_ids:
            excluded.append({**entry, "status": "resurrected"})
    return {
        "new": added,
        "changed": changed,
        "deleted": deleted,
        "excluded": excluded,
    }


def cmd_inventory_check(args: argparse.Namespace) -> int:
    """Validate an inventory and report id stats."""
    path = Path(args.inventory)
    inv = load_inventory(path, args.kind)
    array_name = INVENTORY_ARRAYS[args.kind]
    items = inv[array_name]
    sections = {item["section"] for item in items}
    emit(
        f"{path}: {len(items)} {array_name} in {len(sections)} sections, "
        f"{len(inv['excluded'])} excluded"
    )
    return 0


def cmd_inventory_mint(args: argparse.Namespace) -> int:
    """Assign ids to id-less items of a draft inventory. Ids are minted in
    document order, numbered 01.. within each section, skipping numbers
    already taken by existing ids in that section. Items that already have
    an id pass through untouched, so re-running on an unchanged file is a
    byte-identical no-op — the stability rule that makes inventory-diff
    silent-mis-diff-proof."""
    path = Path(args.inventory)
    raw = path.read_text()
    inv = load_inventory(path, args.kind, allow_idless=True)
    array_name = INVENTORY_ARRAYS[args.kind]
    prefix = INVENTORY_KINDS[args.kind]
    items = inv[array_name]
    used: dict[str, set[int]] = {}
    for item in items:
        eid = item.get("id")
        if isinstance(eid, str) and eid:
            m = re.search(r"-(\d+)$", eid)
            if m:
                used.setdefault(item["section"], set()).add(int(m.group(1)))
    minted = 0
    for i, item in enumerate(items):
        eid = item.get("id")
        if isinstance(eid, str) and eid:
            continue
        section = item["section"]
        n = 1
        while n in used.setdefault(section, set()):
            n += 1
        used[section].add(n)
        items[i] = {"id": mint_inventory_id(prefix, section, n), **item}
        minted += 1
    out = Path(args.out)
    if minted == 0:
        out.write_text(raw)
    else:
        out.write_text(json.dumps(inv, indent=2, ensure_ascii=False) + "\n")
    emit(f"{out}: minted {minted} id(s)")
    return 0


def cmd_inventory_diff(args: argparse.Namespace) -> int:
    """Print the id diff between two inventories as JSON, to --out or
    stdout. Exit 1 on schema violation (either file, via load_inventory),
    a new-file id that doesn't match its item's section (slug drift, new
    ids only — ids --old already knows are grandfathered, so a no-op diff
    on unmodified copies stays a no-op), or a changed item whose id does
    not exist in --old."""
    old_path = Path(args.old)
    new_path = Path(args.new)
    old = load_inventory(old_path, args.kind)
    new = load_inventory(new_path, args.kind)
    array_name = INVENTORY_ARRAYS[args.kind]
    old_item_ids = {item["id"] for item in old[array_name]}
    old_ids = old_item_ids | {entry["id"] for entry in old["excluded"]}
    prefix = INVENTORY_KINDS[args.kind]
    for i, item in enumerate(new[array_name]):
        eid = item["id"]
        if eid in old_ids:
            continue
        expected = f"{prefix}-{_section_slug(item['section'])}-"
        if not re.match(rf"^{re.escape(expected)}\d+$", eid):
            return _err(
                f"{new_path}: item {i} id '{eid}' does not match its "
                f"section '{item['section']}' (expected '{expected}<nn>')"
            )
    diff = inventory_diff(old, new)
    for change in diff["changed"]:
        if change["id"] not in old_item_ids:
            return _err(
                f"{new_path}: changed item '{change['id']}' does not "
                f"exist in --old"
            )
    payload = json.dumps(diff, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        Path(args.out).write_text(payload)
    else:
        sys.stdout.write(payload)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="evaluator.py")
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check")
    check.add_argument("--harness", required=True)
    check.add_argument(
        "--model",
        help="also validate the model against the harness's model list",
    )

    run = sub.add_parser("run")
    run.add_argument("--harness", required=True)
    run.add_argument("--skill", required=True)
    run.add_argument("--agents-dir", required=True)
    run.add_argument("--workspace", required=True)
    run.add_argument("--query", required=True)
    run.add_argument(
        "--expect", required=True, choices=["trigger", "not-trigger"]
    )
    run.add_argument("--model")
    run.add_argument("--variant")
    run.add_argument("--reps", type=int, default=3)
    run.add_argument("--timeout", type=int, default=30)

    split = sub.add_parser("split")
    split.add_argument("--queries", required=True)
    split.add_argument("--out-dir", required=True)
    split.add_argument("--train-frac", type=float, default=0.6)
    split.add_argument("--seed", type=int)

    suite = sub.add_parser("suite")
    suite.add_argument("--harness", required=True)
    suite.add_argument("--skill", required=True)
    suite.add_argument("--agents-dir", required=True)
    suite.add_argument("--workspace", required=True)
    suite.add_argument("--queries", required=True)
    suite.add_argument("--out", required=True)
    suite.add_argument("--model")
    suite.add_argument("--variant")
    suite.add_argument("--reps", type=int, default=3)
    suite.add_argument("--timeout", type=int, default=30)

    record = sub.add_parser("record")
    record.add_argument("--skill", required=True)
    record.add_argument("--skill-path", required=True)
    record.add_argument("--manifest", required=True)
    record.add_argument(
        "--scope", required=True, choices=["frontmatter", "dir"]
    )
    record.add_argument(
        "--track",
        choices=["retrieval-test", "shape-test", "pressure-test"],
        help="manifest key + count vocabulary for --scope dir (legacy "
        "default: retrieval-test; with --scored, checked against the "
        "detected track)",
    )
    record.add_argument("--score", type=float)
    record.add_argument(
        "--scored",
        help="scored.json to take the track counts from (replaces the "
        "counts flags with --scope dir)",
    )
    record.add_argument(
        "--score-from",
        help="train/validate results JSON to compute the trigger score "
        "from (Wilson bound over the recorded outcomes); replaces "
        "--score",
    )
    record.add_argument("--passes", type=int)
    record.add_argument("--fails", type=int)
    record.add_argument("--gaps", type=int)
    record.add_argument("--voids", type=int)
    record.add_argument("--adopted", type=int)
    record.add_argument("--bulletproof", type=int)
    record.add_argument("--no-failure", dest="no_failure", type=int)
    record.add_argument("--unresolved", type=int)
    record.add_argument("--ablations")
    record.add_argument("--campaign")
    record.add_argument("--date")

    failures = sub.add_parser("failures")
    failures.add_argument("--results", required=True)

    retrieval = sub.add_parser("retrieval-suite")
    retrieval.add_argument("--harness", required=True)
    retrieval.add_argument("--skill", required=True)
    retrieval.add_argument("--agents-dir", required=True)
    retrieval.add_argument("--skill-workspace", required=True)
    retrieval.add_argument("--control-workspace", required=True)
    retrieval.add_argument("--queries", required=True)
    retrieval.add_argument("--out", required=True)
    retrieval.add_argument("--model")
    retrieval.add_argument("--variant")
    retrieval.add_argument("--reps", type=int, default=1)
    retrieval.add_argument("--timeout", type=int, default=120)

    evidence = sub.add_parser("retrieval-evidence")
    evidence.add_argument("--results", required=True)
    evidence.add_argument("--entry")

    scored = sub.add_parser("scored-check")
    scored.add_argument("--results", required=True)
    scored.add_argument("--scored")
    scored.add_argument("--emit-skeleton")
    scored.add_argument("--passes", type=int)
    scored.add_argument("--fails", type=int)
    scored.add_argument("--gaps", type=int)
    scored.add_argument("--voids", type=int)

    shape = sub.add_parser("shape-suite")
    shape.add_argument("--harness", required=True)
    shape.add_argument("--skill", required=True)
    shape.add_argument("--agents-dir", required=True)
    shape.add_argument("--workspace", required=True)
    shape.add_argument("--entries", required=True)
    shape.add_argument("--skill-file", required=True)
    shape.add_argument("--arms", required=True)
    shape.add_argument("--out", required=True)
    shape.add_argument(
        "--fixture-key",
        default="application",
    )
    shape.add_argument("--model")
    shape.add_argument("--variant")
    shape.add_argument("--reps", type=int, default=5)
    shape.add_argument("--timeout", type=int, default=120)

    shape_evidence = sub.add_parser("shape-evidence")
    shape_evidence.add_argument("--results", required=True)
    shape_evidence.add_argument("--entry")
    shape_evidence.add_argument("--arm")
    shape_evidence.add_argument(
        "--compare",
        action="store_true",
        help="compare each non-control arm's per-marker property "
        "frequency against the v0 control (frequency = matching "
        "answer lines / answer lines; a candidate must strictly "
        "EXCEED the control)",
    )

    shape_scored = sub.add_parser("shape-scored-check")
    shape_scored.add_argument("--results", action="append", required=True)
    shape_scored.add_argument("--scored")
    shape_scored.add_argument("--emit-skeleton")
    shape_scored.add_argument("--adopted", type=int)
    shape_scored.add_argument("--no-failure", dest="no_failure", type=int)
    shape_scored.add_argument("--unresolved", type=int)
    shape_scored.add_argument("--voids", type=int)

    pressure = sub.add_parser("pressure-suite")
    pressure.add_argument("--harness", required=True)
    pressure.add_argument("--skill", required=True)
    pressure.add_argument("--agents-dir", required=True)
    pressure.add_argument("--workspace", required=True)
    pressure.add_argument("--scenarios", required=True)
    pressure.add_argument("--arm", required=True)
    pressure.add_argument("--skill-file")
    pressure.add_argument("--out", required=True)
    pressure.add_argument("--model")
    pressure.add_argument("--variant")
    pressure.add_argument("--reps", type=int, default=5)
    pressure.add_argument("--timeout", type=int, default=120)

    pressure_evidence = sub.add_parser("pressure-evidence")
    pressure_evidence.add_argument("--results", required=True)
    pressure_evidence.add_argument("--entry")
    pressure_evidence.add_argument("--arm", choices=["red", "green"])

    pressure_meta = sub.add_parser("pressure-meta")
    pressure_meta.add_argument("--harness", required=True)
    pressure_meta.add_argument("--agents-dir", required=True)
    pressure_meta.add_argument("--workspace", required=True)
    pressure_meta.add_argument("--session", required=True)
    pressure_meta.add_argument("--question", required=True)
    pressure_meta.add_argument("--out", required=True)
    pressure_meta.add_argument("--model")
    pressure_meta.add_argument("--variant")
    pressure_meta.add_argument("--timeout", type=int, default=120)

    pressure_scored = sub.add_parser("pressure-scored-check")
    pressure_scored.add_argument("--results", action="append", required=True)
    pressure_scored.add_argument("--scored")
    pressure_scored.add_argument("--emit-skeleton")
    pressure_scored.add_argument("--bulletproof", type=int)
    pressure_scored.add_argument("--no-failure", dest="no_failure", type=int)
    pressure_scored.add_argument("--unresolved", type=int)
    pressure_scored.add_argument("--voids", type=int)

    inv = sub.add_parser(
        "inventory-check",
        help="validate a rules.json/facts.json "
        "inventory and report id stats",
    )
    inv.add_argument("--inventory", required=True)
    inv.add_argument("--kind", required=True, choices=["rule", "fact"])

    mint = sub.add_parser(
        "inventory-mint",
        help="assign ids to id-less items of a draft "
        "inventory; re-running on an unchanged file is a byte-identical "
        "no-op",
    )
    mint.add_argument("--inventory", required=True)
    mint.add_argument("--kind", required=True, choices=["rule", "fact"])
    mint.add_argument("--out", required=True)

    idiff = sub.add_parser(
        "inventory-diff",
        help="diff two inventories by id into "
        "new/changed/deleted/excluded buckets (JSON to --out or stdout)",
    )
    idiff.add_argument("--old", required=True)
    idiff.add_argument("--new", required=True)
    idiff.add_argument("--kind", required=True, choices=["rule", "fact"])
    idiff.add_argument("--out")

    args = parser.parse_args()
    if args.command == "check":
        return cmd_check(args)
    if args.command == "split":
        return cmd_split(args)
    if args.command == "suite":
        return run_suite(TRACKS["trigger-test"], args)
    if args.command == "record":
        return cmd_record(args)
    if args.command == "failures":
        return cmd_evidence(TRACKS["trigger-test"], args)
    if args.command == "retrieval-suite":
        return run_suite(TRACKS["retrieval-test"], args)
    if args.command == "retrieval-evidence":
        return cmd_evidence(TRACKS["retrieval-test"], args)
    if args.command == "scored-check":
        return cmd_scored_check(args)
    if args.command == "shape-suite":
        return run_suite(TRACKS["shape-test"], args)
    if args.command == "shape-evidence":
        return cmd_evidence(TRACKS["shape-test"], args)
    if args.command == "shape-scored-check":
        return _scored_check(TRACKS["shape-test"], args)
    if args.command == "pressure-suite":
        return run_suite(TRACKS["pressure-test"], args)
    if args.command == "pressure-evidence":
        return cmd_evidence(TRACKS["pressure-test"], args)
    if args.command == "pressure-meta":
        return cmd_meta(TRACKS["pressure-test"], args)
    if args.command == "pressure-scored-check":
        return _scored_check(TRACKS["pressure-test"], args)
    if args.command == "inventory-check":
        return cmd_inventory_check(args)
    if args.command == "inventory-mint":
        return cmd_inventory_mint(args)
    if args.command == "inventory-diff":
        return cmd_inventory_diff(args)
    return cmd_run(args)


if __name__ == "__main__":
    sys.exit(main())
