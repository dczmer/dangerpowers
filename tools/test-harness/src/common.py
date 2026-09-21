"""Shared campaign primitives for the evaluator tracks.

State-free helpers plus the two pieces of module state every track shares
(_Log.file campaign-log mirror, _EMIT_LOCK serialization). Track classes
in tracks.py and the CLI drivers in evaluator.py both import from here;
nothing in this module knows about tracks.
"""

import argparse
import json
import math
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Iterator, TextIO

from src.strategies import (
    EvalStrategy,
    HarnessExecutionError,
    Verdict,
    _fail,
    scan_agent_frontmatter,
)

MAX_WORKERS = 10


def wilson_interval(
    passed: int, n: int, z: float = 1.96
) -> tuple[float, float]:
    p = passed / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return center - margin, center + margin


class _Log:
    """Campaign log handle; set by cmd_suite, None under `run`."""

    file: TextIO | None = None


_EMIT_LOCK = threading.Lock()


def emit(msg: str = "", *, err: bool = False) -> None:
    """Print a progress line; also mirror it to the campaign log if set.
    Serialized: arms and reps log concurrently from worker threads."""
    with _EMIT_LOCK:
        print(msg, file=sys.stderr if err else sys.stdout, flush=True)
        if _Log.file is not None:
            _Log.file.write(msg + "\n")
            _Log.file.flush()


def _session_suffix(e: HarnessExecutionError) -> str:
    """` [session <id>]` for abort lines when the harness emitted a
    session id before failing, else ""."""
    return f" [session {e.session_id}]" if e.session_id else ""


def log_start(n: int, tag: str | None = None) -> None:
    prefix = f"[{tag}] " if tag else ""
    emit(f"{prefix}[rep {n:>3}] started")


def log_complete(n: int, verdict: Verdict) -> None:
    line = f"[rep {n:>3}] completed: {verdict.outcome}"
    if verdict.timeout:
        line += " (timeout)"
    if verdict.outcome == "void":
        line += f" ({verdict.detail})"
    emit(line)


def _score_counts(
    passed: int, failed: int
) -> tuple[float | None, float | None, float | None]:
    n = passed + failed
    if n == 0:
        return None, None, None
    low, high = wilson_interval(passed, n)
    return low, high, low


def _err(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 1


# --------------------------------------------------------------------------
# Shared campaign plumbing (retrieval / shape / pressure tracks)


def validate_eval_agent(
    probe: EvalStrategy, agents_dir: Path, expected_name: str
) -> Path:
    """Pre-spend gate: the agent file exists, its frontmatter name
    matches, and it pins no model config. Any failure exits 1 with an
    exact message before any harness invocation."""
    agent_file = probe.agent_file(agents_dir, expected_name)
    if not agent_file.exists():
        _fail(f"evaluator agent file missing: {agent_file}")
    info = scan_agent_frontmatter(agent_file)  # exits on bad frontmatter
    if info["name"] != expected_name:
        _fail(
            f"agent file {agent_file}: frontmatter name "
            f"'{info['name']}' does not match expected '{expected_name}'"
        )
    if info["pins"]:
        _fail(
            f"agent file {agent_file} pins model config "
            f"({', '.join(info['pins'])}); eval agents must not pin "
            "model/variant/temperature/top_p — selection flows "
            "through --model/--variant only"
        )
    return agent_file


def run_rep_batched(
    run_one: Callable[[int], Any], reps: int, tag: str | None
) -> list[Any]:
    """Smoke rep alone, then reps 2..N in parallel batches of at most
    MAX_WORKERS. A timeout is a record, never an abort; a
    HarnessExecutionError in the smoke rep or any batch aborts with an
    exact stderr message and exit 1. Shared by all four tracks. tag is
    the [tag] prefix on error lines; None (trigger) omits the prefix."""
    prefix = f"[{tag}] " if tag else ""
    runs: dict[int, Any] = {}

    try:
        runs[1] = run_one(1)
    except HarnessExecutionError as e:
        emit(
            f"error: {prefix}harness could not execute the query: {e}"
            f"{_session_suffix(e)}",
            err=True,
        )
        sys.exit(1)

    remaining = list(range(2, reps + 1))
    for i in range(0, len(remaining), MAX_WORKERS):
        group = remaining[i : i + MAX_WORKERS]
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            futures = {pool.submit(run_one, n): n for n in group}
            first_error: tuple[int, Any] | None = None
            for fut, n in futures.items():
                try:
                    runs[n] = fut.result()
                except HarnessExecutionError as e:
                    if first_error is None:
                        first_error = (n, e)
        if first_error is not None:
            n, e = first_error
            emit(
                f"error: {prefix}rep {n} could not execute: {e}"
                f"{_session_suffix(e)}",
                err=True,
            )
            emit("error: batch aborted", err=True)
            sys.exit(1)

    return [runs[n] for n in range(1, reps + 1)]


def base_config(args: argparse.Namespace) -> dict:
    """The six config keys every campaign results file shares; each
    track's call site extends the returned dict with its own keys."""
    return {
        "skill": args.skill,
        "harness": args.harness,
        "model": args.model,
        "variant": args.variant,
        "reps": args.reps,
        "timeout": args.timeout,
        "date": datetime.now(UTC).date().isoformat(),
    }


def write_results(out: Path, config: dict, entries: list[dict]) -> None:
    out.write_text(
        json.dumps({"config": config, "entries": entries}, indent=2) + "\n"
    )


class EvidenceError(Exception):
    """A malformed entry inside an evidence command's results file.
    Evidence commands print the exact message to stderr and return 1 —
    they never _fail/sys.exit, so this is raised instead."""


def load_results_json(path: Path, track: str) -> tuple[list[dict], str | None]:
    """Load a *-suite results file and validate the envelope: an object
    with an 'entries' list. Returns ([], exact error message) on
    failure — the caller prints it to stderr and returns 1, matching
    the evidence commands' historical exit style."""
    if not path.exists():
        return [], f"results file not found: {path}"
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        return [], f"invalid JSON in {path}: {e}"
    if not isinstance(data, dict) or not isinstance(data.get("entries"), list):
        return [], (
            f"{path}: not a {track}-suite results file "
            f"(missing 'entries' list)"
        )
    return data["entries"], None


def iter_evidence(
    data_entries: list[dict], path: Path, entry_filter: str | None
) -> Iterator[tuple[str, dict]]:
    """Yield (eid, entry) pairs honoring --entry, after per-entry
    envelope validation. Raises EvidenceError with the exact message on
    a malformed entry."""
    for i, entry in enumerate(data_entries):
        if not isinstance(entry, dict):
            raise EvidenceError(f"{path}: entry {i} is not an object")
        eid = entry.get("id")
        if not isinstance(eid, str) or not eid:
            raise EvidenceError(
                f"{path}: entry {i} missing 'id' (non-empty string)"
            )
        if entry_filter is not None and eid != entry_filter:
            continue
        yield eid, entry


def union_results(
    paths: list[str],
    track: str,
    entry_hook: Callable[[Path, dict, dict], str | None] | None = None,
) -> tuple[list[str], dict[str, set[str]], dict[str, dict]] | str:
    """Union with dedupe over repeated results files: an id appearing
    in N files is scored exactly once. Returns (ordered ids, id ->
    arm-key set, id -> hook-collected extras); entry_hook runs per
    entry occurrence and returns an exact error message on violation.
    On any failure returns the error message (caller passes it to
    _err)."""
    results_ids: list[str] = []
    results_arms: dict[str, set[str]] = {}
    extras: dict[str, dict] = {}
    for results_str in paths:
        results_path = Path(results_str)
        if not results_path.exists():
            return f"results file not found: {results_path}"
        try:
            data = json.loads(results_path.read_text())
        except json.JSONDecodeError as e:
            return f"invalid JSON in {results_path}: {e}"
        if not isinstance(data, dict) or not isinstance(
            data.get("entries"), list
        ):
            return (
                f"{results_path}: not a {track}-suite results file "
                f"(missing 'entries' list)"
            )
        for i, e in enumerate(data["entries"]):
            eid = e.get("id") if isinstance(e, dict) else None
            if not isinstance(eid, str) or not eid:
                return (
                    f"{results_path}: results entry {i} missing 'id' "
                    f"(non-empty string)"
                )
            arms = e.get("arms") if isinstance(e, dict) else None
            arm_keys = (
                {a for a in arms if isinstance(a, str) and a}
                if isinstance(arms, dict)
                else set()
            )
            if eid not in results_arms:
                results_ids.append(eid)
            results_arms.setdefault(eid, set()).update(arm_keys)
            if entry_hook is not None:
                hook_error = entry_hook(results_path, e, extras)
                if hook_error is not None:
                    return hook_error
    return results_ids, results_arms, extras


def load_scored_json(
    scored_path: Path, object_phrase: str = "a JSON object"
) -> list[dict] | str:
    """Load scored.json and validate its envelope. Returns the entries
    list, or the exact error message. object_phrase carries the one
    per-track wording difference in the envelope error (pressure says
    "an object")."""
    if not scored_path.exists():
        return f"scored file not found: {scored_path}"
    try:
        scored = json.loads(scored_path.read_text())
    except json.JSONDecodeError as e:
        return f"invalid JSON in {scored_path}: {e}"
    if not isinstance(scored, dict) or not isinstance(
        scored.get("entries"), list
    ):
        return (
            f"{scored_path}: expected {object_phrase} with an 'entries' list"
        )
    return scored["entries"]


def check_coverage(
    scored_entries: list[dict], results_ids: list[str], scored_path: Path
) -> list[dict] | str:
    """Exactly-once coverage: rejects non-object entries and missing/
    duplicate/unknown ids, and union ids with no scored entry. Returns
    the scored entries for per-track field checks, or the exact error
    message."""
    covered: set[str] = set()
    for i, entry in enumerate(scored_entries):
        if not isinstance(entry, dict):
            return f"{scored_path}: entry {i} is not an object"
        eid = entry.get("id")
        if not isinstance(eid, str) or not eid:
            return f"{scored_path}: entry {i} missing 'id' (non-empty string)"
        if eid in covered:
            return f"{scored_path}: duplicate id: {eid}"
        if eid not in results_ids:
            return f"{scored_path}: unknown id: {eid}"
        covered.add(eid)
    missing = [eid for eid in results_ids if eid not in covered]
    if missing:
        return (
            f"{scored_path}: missing scored entries for results ids: "
            f"{', '.join(missing)}"
        )
    return scored_entries


def _scored_target_gate(args: argparse.Namespace) -> int | None:
    """--scored / --emit-skeleton exclusivity: argparse cannot express
    it (both are plain optional paths), so exactly one must be given.
    Returns _err(...) on violation, None when exactly one is set."""
    emit = getattr(args, "emit_skeleton", None)
    if args.scored is None and emit is None:
        return _err("one of --scored or --emit-skeleton is required")
    if args.scored is not None and emit is not None:
        return _err("--scored and --emit-skeleton are mutually exclusive")
    return None


def counts_gate(
    args: argparse.Namespace,
    scored_entries: list[dict],
    arg_names: tuple[str, ...],
    result_names: tuple[str, ...],
) -> int | None:
    """When the record-step counts are given: all-or-none, and equal to
    the scored sums. Returns _err(...) on violation, None when the gate
    passes or no counts were given."""
    given = [getattr(args, n, None) for n in arg_names]
    if not any(c is not None for c in given):
        return None
    flags = "/".join(f"--{n.replace('_', '-')}" for n in arg_names)
    if not all(c is not None for c in given):
        return _err(f"{flags} must be given together")
    computed = {
        r: sum(1 for e in scored_entries if e.get("result") == r)
        for r in result_names
    }
    if tuple(given) != tuple(computed[r] for r in computed):
        shown = " / ".join(f"{computed[r]} {r}" for r in result_names)
        got = " / ".join(f"{g} {r}" for g, r in zip(given, result_names))
        return _err(
            f"counts do not match scored results: computed {shown}, "
            f"got {got}"
        )
    return None


def load_entries(
    path: Path,
    file_noun: str,
    item_noun: str,
    field_hook: Callable[[Path, int, dict, str], None] | None = None,
) -> list[dict]:
    """Shared envelope validator for the campaign input files (retrieval
    queries, shape entries, pressure scenarios): file-exists -> JSON
    parse -> list-of-objects -> unique non-empty 'id'. On any violation
    prints `error: <exact reason>` to stderr and exits 1 (pre-spend:
    zero harness runs happen before this returns). Per-field checks
    stay in the per-track field_hook, which runs between the envelope
    checks and the append so multi-violation error order is unchanged.
    file_noun/item_noun carry the two per-track wording differences
    ("query file"/"query objects", "entries file"/"entry objects",
    "scenarios file"/"scenario objects")."""
    if not path.exists():
        _fail(f"{file_noun} file not found: {path}")
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        _fail(f"invalid JSON in {path}: {e}")
    if not isinstance(data, list):
        _fail(f"{path}: expected a JSON list of {item_noun} objects")
    entries: list[dict] = []
    seen: set[str] = set()
    for i, entry in enumerate(data):
        if not isinstance(entry, dict):
            _fail(f"{path}: entry {i} is not an object")
        eid = entry.get("id")
        if not isinstance(eid, str) or not eid:
            _fail(f"{path}: entry {i} missing 'id' (non-empty string)")
        if eid in seen:
            _fail(f"{path}: duplicate id: {eid}")
        seen.add(eid)
        if field_hook is not None:
            field_hook(path, i, entry, eid)
        entries.append(entry)
    return entries
