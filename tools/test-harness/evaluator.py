#!/usr/bin/env python3
"""Evaluator: command-line driver for the skill-testing harness.

Subcommands: check (harness/model validation); run and split (single-query
trigger probing: one invocation = one query, N reps under the restricted
`trigger-evaluator` agent); suite, evidence, scored-check, and meta (the
unified --track campaign commands for trigger-test, retrieval-test,
shape-test, and pressure-test); record (manifest recording from frontmatter
scores, --score-from results, or --scored files); and inventory-check /
inventory-mint / inventory-diff (discipline-rule inventories).

Per-track campaign behavior lives behind the Track interface in
src/tracks.py; shared campaign primitives (rep batching, evidence
extraction, scored validation) live in src/common.py. Harness specifics
live in the strategy registry in src/strategies.py; only opencode is
implemented.
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


# Historical listing order of the mixed-vocabulary error message
# (pressure-first, as since the per-track scored checks were introduced);
# registry iteration order would surface retrieval-first instead.
_SCORED_TRACK_ORDER = ("pressure-test", "shape-test", "retrieval-test")


def _scored_track_signals(scored_entries: list[dict]) -> list[str]:
    """Collect the set of tracks the scored entries can be proven to
    belong to, using only discriminating signals (each scored track's
    scored_signal over the registry), listed in the historical
    _SCORED_TRACK_ORDER."""
    hits = {
        name: False for name, track in TRACKS.items() if track.supports_scored
    }
    for e in scored_entries:
        if not isinstance(e, dict):
            continue
        for name, track in TRACKS.items():
            if track.supports_scored and track.scored_signal(e):
                hits[name] = True
    return [name for name in _SCORED_TRACK_ORDER if hits.get(name, False)]


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
    (an explicit --track is checked against the detection); the counts
    flags are rejected (`counts flags are replaced by --scored`) and
    --scored is required with --scope dir."""
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
        if _any_counts_given(args):
            return _err("counts flags are replaced by --scored")
        if getattr(args, "scored", None) is None:
            return _err("--scored is required with --scope dir")
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
# Generic drivers (plan §3.2): the track comes off the unified parser's
# --track; the gates that only a merged parser makes reachable live here.

_ALL_COUNT_DESTS = (
    "passes",
    "fails",
    "gaps",
    "voids",
    "adopted",
    "bulletproof",
    "no_failure",
    "unresolved",
)


def cmd_scored_check(args: argparse.Namespace) -> int:
    """Validate scored.json against the results files it claims to cover
    (generic driver; per-entry rules live in the track's
    check_scored_entry). With --emit-skeleton PATH, write the skeleton.
    Exact messages, exit 1 on any violation, coverage line on success."""
    track = TRACKS[args.track]
    gate = _scored_target_gate(args)
    if gate is not None:
        return gate
    if not track.multi_results and len(args.results) != 1:
        return _err(
            f"exactly one --results file is valid with --track {track.name}"
        )
    foreign = [
        n
        for n in _ALL_COUNT_DESTS
        if n not in track.count_arg_names
        and getattr(args, n, None) is not None
    ]
    if foreign:
        flags = "/".join(f"--{n.replace('_', '-')}" for n in foreign)
        return _err(
            f"counts flags {flags} are only valid with their own track "
            f"(not --track {track.name})"
        )
    union = union_results(
        args.results, track.results_noun, entry_hook=track.union_hook
    )
    if isinstance(union, str):
        return _err(union)
    results_ids, results_arms, extras = union

    if getattr(args, "emit_skeleton", None) is not None:
        out_path = Path(args.emit_skeleton)
        header = (
            _scored_skeleton_header(args.results)
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
    covered = check_coverage(scored_entries, results_ids, scored_path)
    if isinstance(covered, str):
        return _err(covered)
    for entry in covered:
        rc = track.check_scored_entry(
            scored_path, entry, results_arms[entry["id"]], extras
        )
        if rc is not None:
            return rc
    rc = counts_gate(
        args, covered, track.count_arg_names, track.count_result_names
    )
    if rc is not None:
        return rc
    print(f"ok: {scored_path} covers {len(results_ids)} entries")
    return 0


def cmd_evidence(args: argparse.Namespace) -> int:
    """Generic evidence dispatcher: flag/track pairing gates, then the
    track's printer."""
    track = TRACKS[args.track]
    if args.arm is not None and track.name not in (
        "shape-test",
        "pressure-test",
    ):
        return _err(
            "--arm is only valid with --track shape-test or "
            "--track pressure-test"
        )
    if args.compare and track.name != "shape-test":
        return _err("--compare is only valid with --track shape-test")
    return track.print_evidence(args)


def cmd_meta(args: argparse.Namespace) -> int:
    """Session resume; pressure-only today via supports_meta."""
    track = TRACKS[args.track]
    if not track.supports_meta:
        return _err(f"--track {args.track} does not support meta")
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
    suite.add_argument(
        "--track",
        required=True,
        choices=[t.name for t in TRACKS.values()],
    )
    suite.add_argument("--harness", required=True)
    suite.add_argument("--skill", required=True)
    suite.add_argument("--agents-dir", required=True)
    suite.add_argument("--out", required=True)
    suite.add_argument("--model")
    suite.add_argument("--variant")
    # No parser defaults: each track applies its historical default as
    # the first lines of pre_spend_gates. A parser default would make
    # args.reps/args.timeout never-None and flatten all four tracks to
    # one default.
    suite.add_argument("--reps", type=int)
    suite.add_argument("--timeout", type=int)
    # per-track flags (Q7a: historical names kept); required status is
    # enforced per track inside pre_spend_gates
    suite.add_argument("--workspace")  # trigger, shape, pressure
    suite.add_argument("--queries")  # trigger, retrieval
    suite.add_argument("--skill-workspace")  # retrieval
    suite.add_argument("--control-workspace")  # retrieval
    suite.add_argument("--entries")  # shape
    suite.add_argument("--skill-file")  # shape, pressure
    suite.add_argument("--arms")  # shape
    suite.add_argument("--fixture-key", default="application")  # shape
    suite.add_argument("--scenarios")  # pressure
    suite.add_argument("--arm")  # pressure

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
        help="manifest key for --scope dir (with --scored, checked "
        "against the detected track)",
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

    evidence = sub.add_parser("evidence")
    evidence.add_argument(
        "--track", required=True, choices=[t.name for t in TRACKS.values()]
    )
    evidence.add_argument("--results", required=True)
    evidence.add_argument("--entry")
    # free-form: shape arms are v0/variant names, pressure's are
    # red/green; the tracks' printers validate (no argparse choices —
    # the old shape-evidence --arm took any arm name)
    evidence.add_argument("--arm")
    evidence.add_argument("--compare", action="store_true")

    scored = sub.add_parser("scored-check")
    scored.add_argument(
        "--track",
        required=True,
        choices=[n for n, t in TRACKS.items() if t.supports_scored],
    )
    scored.add_argument("--results", action="append", required=True)
    scored.add_argument("--scored")
    scored.add_argument("--emit-skeleton")
    for dest in _ALL_COUNT_DESTS:
        scored.add_argument(f"--{dest.replace('_', '-')}", type=int)

    meta = sub.add_parser("meta")
    meta.add_argument(
        "--track",
        required=True,
        choices=[n for n, t in TRACKS.items() if t.supports_meta],
    )
    meta.add_argument("--harness", required=True)
    meta.add_argument("--agents-dir", required=True)
    meta.add_argument("--workspace", required=True)
    meta.add_argument("--session", required=True)
    meta.add_argument("--question", required=True)
    meta.add_argument("--out", required=True)
    meta.add_argument("--model")
    meta.add_argument("--variant")
    meta.add_argument("--timeout", type=int, default=120)

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
    if args.command == "suite":
        return run_suite(TRACKS[args.track], args)
    if args.command == "evidence":
        return cmd_evidence(args)
    if args.command == "scored-check":
        return cmd_scored_check(args)
    if args.command == "meta":
        return cmd_meta(args)
    handlers = {
        "check": cmd_check,
        "split": cmd_split,
        "record": cmd_record,
        "inventory-check": cmd_inventory_check,
        "inventory-mint": cmd_inventory_mint,
        "inventory-diff": cmd_inventory_diff,
    }
    if args.command in handlers:
        return handlers[args.command](args)
    return cmd_run(args)  # "run"


if __name__ == "__main__":
    sys.exit(main())
