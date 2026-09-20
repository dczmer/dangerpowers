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
import math
import random
import re
import shutil
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable, Iterator, TextIO

from strategies import (
    EvalStrategy,
    HarnessExecutionError,
    Verdict,
    _fail,
    check_harness,
    resolve_strategy,
    scan_agent_frontmatter,
)

MAX_WORKERS = 10

# Track constants: the trigger track evaluates under TRIGGER_AGENT; the
# retrieval track runs two arms (design §5.1/§5.2).
TRIGGER_AGENT = "trigger-evaluator"
RETRIEVAL_EVALUATOR_AGENT = "retrieval-evaluator"
RETRIEVAL_CONTROL_AGENT = "retrieval-control"
SHAPE_EVALUATOR_AGENT = "shape-evaluator"
PRESSURE_EVALUATOR_AGENT = "pressure-evaluator"

# Log label per retrieval arm, used as a [tag] prefix on every progress line
# so interleaved arm output stays attributable when both arms run in
# parallel. The skill arm is padded to the control arm's width.
ARM_TAGS = {"skill_arm": " skill ", "control_arm": "control"}


@dataclass
class EvalCase:
    query: str
    should_trigger: bool


@dataclass
class BatchResult:
    case: EvalCase
    verdicts: list[Verdict] = field(default_factory=list)
    passed: int = 0  # non-void runs matching expectation
    failed: int = 0  # non-void runs mismatching expectation
    void: int = 0
    wilson_low: float | None = None  # None when passed + failed == 0
    wilson_high: float | None = None
    score: float | None = None  # == wilson_low


def wilson_interval(
    passed: int, n: int, z: float = 1.96
) -> tuple[float, float]:
    p = passed / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return center - margin, center + margin


# --------------------------------------------------------------------------
# Batch mechanics


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


def run_rep(
    strategy: EvalStrategy,
    skill: str,
    case: EvalCase,
    workspace: Path,
    model: str | None,
    effort: str | None,
    n: int,
) -> Verdict:
    log_start(n)
    verdict = strategy.evaluate(skill, case.query, workspace, model, effort)
    log_complete(n, verdict)
    return verdict


def eval_batch(
    strategy: EvalStrategy,
    skill: str,
    case: EvalCase,
    workspace: Path,
    model: str | None,
    effort: str | None,
    reps: int,
) -> BatchResult:
    verdicts: dict[int, Verdict] = {}

    # Smoke rep runs alone; a harness failure here aborts before further spend.
    try:
        verdicts[1] = run_rep(
            strategy, skill, case, workspace, model, effort, 1
        )
    except HarnessExecutionError as e:
        emit(
            f"error: harness could not execute the query: {e}"
            f"{_session_suffix(e)}",
            err=True,
        )
        sys.exit(1)

    # Remaining reps in parallel batches of at most MAX_WORKERS.
    remaining = list(range(2, reps + 1))
    for i in range(0, len(remaining), MAX_WORKERS):
        end = i + MAX_WORKERS
        group = remaining[i:end]
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            futures = {
                pool.submit(
                    run_rep, strategy, skill, case, workspace, model, effort, n
                ): n
                for n in group
            }
            first_error: tuple[int, HarnessExecutionError] | None = None
            for fut, n in futures.items():
                try:
                    verdicts[n] = fut.result()
                except HarnessExecutionError as e:
                    if first_error is None:
                        first_error = (n, e)
        if first_error is not None:
            n, e = first_error
            emit(
                f"error: rep {n} could not execute: {e}"
                f"{_session_suffix(e)}",
                err=True,
            )
            emit("error: batch aborted", err=True)
            sys.exit(1)

    result = BatchResult(case=case)
    for n in range(1, reps + 1):
        v = verdicts[n]
        result.verdicts.append(v)
        if v.outcome == "void":
            result.void += 1
        elif (v.outcome == "triggered") == case.should_trigger:
            result.passed += 1
        else:
            result.failed += 1

    n_scored = result.passed + result.failed
    if n_scored > 0:
        result.wilson_low, result.wilson_high = wilson_interval(
            result.passed, n_scored
        )
        result.score = result.wilson_low
    return result


def print_report(result: BatchResult) -> None:
    print()
    print(
        f'query: "{result.case.query}"   expected: '
        f'{"trigger" if result.case.should_trigger else "not-trigger"}'
    )
    for i, v in enumerate(result.verdicts, start=1):
        if v.outcome == "void":
            mark = "—"
        elif (v.outcome == "triggered") == result.case.should_trigger:
            mark = "pass"
        else:
            mark = "fail"
        line = f"  run {i:>3}: {v.outcome:<13}  {mark}"
        if v.timeout:
            line += " (timeout)"
        if v.outcome == "void":
            line += f"  detail: {v.detail}"
        print(line)
    total = result.passed + result.failed + result.void
    summary = (
        f"  summary: {result.passed} pass / {result.failed} fail / "
        f"{result.void} void ({total} runs)"
    )
    if result.wilson_low is None:
        summary += "  wilson95: n/a (all void)  score: n/a"
    else:
        summary += (
            f"  wilson95: [{result.wilson_low:.3f}, "
            f"{result.wilson_high:.3f}]  score: {result.score:.3f}"
        )
    print(summary)
    for i, v in enumerate(result.verdicts, start=1):
        session = f" [session {v.session_id}]" if v.session_id else ""
        print(f"\n  reasoning run {i} ({v.outcome}){session}:")
        if v.detail:
            print(f"    detail: {v.detail}")
        if v.reasoning:
            for line in v.reasoning.splitlines():
                print(f"    {line}")
        else:
            print("    (none)")


def cmd_run(args: argparse.Namespace) -> int:
    strategy_cls = resolve_strategy(args.harness)
    workspace = Path(args.workspace)
    stub = workspace / ".agents" / "skills" / args.skill / "SKILL.md"
    if not stub.exists():
        print(
            f"error: skill stub not synced: {stub}; "
            f"run workspace-manager.sh sync",
            file=sys.stderr,
        )
        return 1
    if args.reps < 1:
        print("error: --reps must be >= 1", file=sys.stderr)
        return 1
    if args.timeout < 1:
        print("error: --timeout must be >= 1", file=sys.stderr)
        return 1

    case = EvalCase(
        query=args.query, should_trigger=(args.expect == "trigger")
    )
    strategy = strategy_cls(timeout=args.timeout)
    strategy.install(workspace, Path(args.agents_dir), TRIGGER_AGENT)

    print(f"trigger test: {args.skill}")
    print(f"workspace: {workspace}")
    print(
        f"harness: {args.harness}  model: {args.model or '(default)'}  "
        f"variant: {args.variant or '(none)'}  reps: {args.reps}  "
        f"timeout: {args.timeout}s"
    )

    result = eval_batch(
        strategy,
        args.skill,
        case,
        workspace,
        args.model,
        args.variant,
        args.reps,
    )
    print_report(result)
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    strategy_cls = resolve_strategy(args.harness)
    check_harness(args.harness, strategy_cls, args.model)
    return 0


# --------------------------------------------------------------------------
# Campaign tooling: split + suite


def load_queries(path_str: str) -> list[EvalCase] | None:
    """Read and strictly validate a query file. On any violation prints
    `error: <exact reason>` to stderr and returns None."""
    path = Path(path_str)
    if not path.exists():
        print(f"error: query file not found: {path}", file=sys.stderr)
        return None
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        print(f"error: invalid JSON in {path}: {e}", file=sys.stderr)
        return None
    if not isinstance(data, list):
        print(
            f"error: {path}: expected a JSON list of query objects",
            file=sys.stderr,
        )
        return None
    cases: list[EvalCase] = []
    for i, entry in enumerate(data):
        if not isinstance(entry, dict):
            print(
                f"error: {path}: entry {i} is not an object", file=sys.stderr
            )
            return None
        q = entry.get("query")
        if not isinstance(q, str) or not q:
            print(
                f"error: {path}: entry {i} missing 'query' (non-empty "
                f"string)",
                file=sys.stderr,
            )
            return None
        st = entry.get("shouldTrigger")
        if not isinstance(st, bool):
            print(
                f"error: {path}: entry {i} missing 'shouldTrigger' "
                f"(boolean)",
                file=sys.stderr,
            )
            return None
        cases.append(EvalCase(query=q, should_trigger=st))
    return cases


def cmd_split(args: argparse.Namespace) -> int:
    if not (0.0 < args.train_frac < 1.0):
        print("error: --train-frac must be in (0, 1)", file=sys.stderr)
        return 1
    cases = load_queries(args.queries)
    if cases is None:
        return 1

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.seed is not None:
        seed = args.seed
    else:
        seed = random.SystemRandom().randrange(2**63)
        print(f"seed: {seed}")

    n = len(cases)
    if n <= 10:
        train, validate = cases, []
        print(f"note: <=10 queries, no validate split (train={n}, validate=0)")
    else:
        rng = random.Random(seed)
        train, validate = [], []
        for cls in (True, False):
            group = [c for c in cases if c.should_trigger == cls]
            rng.shuffle(group)
            n_validate = int(len(group) * (1 - args.train_frac) + 0.5)
            n_validate = max(0, min(n_validate, len(group) - 1))
            validate.extend(group[:n_validate])
            train.extend(group[n_validate:])
        rng.shuffle(train)
        rng.shuffle(validate)

    def dump(name: str, items: list[EvalCase]) -> None:
        (out_dir / name).write_text(
            json.dumps(
                [
                    {"query": c.query, "shouldTrigger": c.should_trigger}
                    for c in items
                ],
                indent=2,
            )
            + "\n"
        )

    dump("train.json", train)
    dump("validate.json", validate)
    (out_dir / "split.json").write_text(
        json.dumps(
            {"seed": seed, "train": len(train), "validate": len(validate)}
        )
        + "\n"
    )

    print(
        f"split: {n} queries -> train {len(train)} / validate "
        f"{len(validate)} (seed {seed})"
    )
    for cls in (True, False):
        label = "shouldTrigger=true" if cls else "shouldTrigger=false"
        t = sum(1 for c in train if c.should_trigger == cls)
        v = sum(1 for c in validate if c.should_trigger == cls)
        print(f"  {label}: train {t} / validate {v}")
    return 0


def _score_counts(
    passed: int, failed: int
) -> tuple[float | None, float | None, float | None]:
    n = passed + failed
    if n == 0:
        return None, None, None
    low, high = wilson_interval(passed, n)
    return low, high, low


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


def cmd_suite(args: argparse.Namespace) -> int:
    strategy_cls = resolve_strategy(args.harness)
    workspace = Path(args.workspace)
    stub = workspace / ".agents" / "skills" / args.skill / "SKILL.md"
    if not stub.exists():
        print(
            f"error: skill stub not synced: {stub}; "
            f"run workspace-manager.sh sync",
            file=sys.stderr,
        )
        return 1
    if args.reps < 1:
        print("error: --reps must be >= 1", file=sys.stderr)
        return 1
    if args.timeout < 1:
        print("error: --timeout must be >= 1", file=sys.stderr)
        return 1
    check_harness(args.harness, strategy_cls, args.model)
    cases = load_queries(args.queries)
    if cases is None:
        return 1
    out = Path(args.out)
    if not out.parent.exists():
        print(
            f"error: --out parent directory does not exist: {out.parent}",
            file=sys.stderr,
        )
        return 1
    log_path = out.with_suffix(".log")
    _Log.file = log_path.open("w")

    def empty_result() -> dict:
        return {
            "skill": args.skill,
            "harness": args.harness,
            "model": args.model,
            "variant": args.variant,
            "reps": args.reps,
            "timeout": args.timeout,
            "queries": [],
            "totals": {
                "passed": 0,
                "failed": 0,
                "void": 0,
                "timeouts": 0,
                "wilson_low": None,
                "wilson_high": None,
                "score": None,
            },
        }

    if not cases:
        out.write_text(json.dumps(empty_result(), indent=2) + "\n")
        emit("note: empty query file, wrote zeroed result")
        return 0

    strategy = strategy_cls(timeout=args.timeout)
    strategy.install(workspace, Path(args.agents_dir), TRIGGER_AGENT)

    emit(f"trigger test suite: {args.skill} ({len(cases)} queries)")
    emit(f"workspace: {workspace}")
    emit(
        f"harness: {args.harness}  model: {args.model or '(default)'}  "
        f"variant: {args.variant or '(none)'}  reps: {args.reps}  "
        f"timeout: {args.timeout}s"
    )

    query_results = []
    tot_passed = tot_failed = tot_void = tot_timeouts = 0
    for i, case in enumerate(cases, start=1):
        result = eval_batch(
            strategy,
            args.skill,
            case,
            workspace,
            args.model,
            args.variant,
            args.reps,
        )
        timeouts = sum(1 for v in result.verdicts if v.timeout)
        failures = [
            {
                "run": n,
                "outcome": v.outcome,
                "detail": v.detail,
                "reasoning": v.reasoning,
                "timeout": v.timeout,
                "session_id": v.session_id,
            }
            for n, v in enumerate(result.verdicts, start=1)
            if v.outcome != "void"
            and (v.outcome == "triggered") != case.should_trigger
        ]
        voids = [
            {
                "run": n,
                "detail": v.detail,
                "timeout": v.timeout,
                "session_id": v.session_id,
            }
            for n, v in enumerate(result.verdicts, start=1)
            if v.outcome == "void"
        ]
        query_results.append(
            {
                "query": case.query,
                "should_trigger": case.should_trigger,
                "passed": result.passed,
                "failed": result.failed,
                "void": result.void,
                "timeouts": timeouts,
                "wilson_low": result.wilson_low,
                "wilson_high": result.wilson_high,
                "score": result.score,
                "failures": failures,
                "voids": voids,
            }
        )
        score_s = f"{result.score:.3f}" if result.score is not None else "n/a"
        emit(
            f'[query {i}/{len(cases)}] "{case.query}" -> {result.passed} '
            f"pass / {result.failed} fail / {result.void} void "
            f"score: {score_s}"
        )
        tot_passed += result.passed
        tot_failed += result.failed
        tot_void += result.void
        tot_timeouts += timeouts

    low, high, score = _score_counts(tot_passed, tot_failed)
    result_json = {
        "skill": args.skill,
        "harness": args.harness,
        "model": args.model,
        "variant": args.variant,
        "reps": args.reps,
        "timeout": args.timeout,
        "queries": query_results,
        "totals": {
            "passed": tot_passed,
            "failed": tot_failed,
            "void": tot_void,
            "timeouts": tot_timeouts,
            "wilson_low": low,
            "wilson_high": high,
            "score": score,
        },
    }
    out.write_text(json.dumps(result_json, indent=2) + "\n")
    score_s = f"{score:.3f}" if score is not None else "n/a"
    emit(
        f"suite: {tot_passed} pass / {tot_failed} fail / {tot_void} void "
        f"score: {score_s} -> {out}"
    )
    return 0


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
    run_one: Callable[[int], dict], reps: int, tag: str
) -> list[dict]:
    """Smoke rep alone, then reps 2..N in parallel batches of at most
    MAX_WORKERS. A timeout is a record, never an abort; a
    HarnessExecutionError in the smoke rep or any batch aborts with an
    exact stderr message and exit 1. Shared by the retrieval, shape, and
    pressure tracks; the trigger track keeps its own loop."""
    runs: dict[int, dict] = {}

    try:
        runs[1] = run_one(1)
    except HarnessExecutionError as e:
        emit(
            f"error: [{tag}] harness could not execute the query: {e}"
            f"{_session_suffix(e)}",
            err=True,
        )
        sys.exit(1)

    remaining = list(range(2, reps + 1))
    for i in range(0, len(remaining), MAX_WORKERS):
        group = remaining[i : i + MAX_WORKERS]
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            futures = {pool.submit(run_one, n): n for n in group}
            first_error: tuple[int, HarnessExecutionError] | None = None
            for fut, n in futures.items():
                try:
                    runs[n] = fut.result()
                except HarnessExecutionError as e:
                    if first_error is None:
                        first_error = (n, e)
        if first_error is not None:
            n, e = first_error
            emit(
                f"error: [{tag}] rep {n} could not execute: {e}"
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


def _retrieval_union_hook(path: Path, e: dict, extras: dict) -> str | None:
    """Collect each entry's expect rubric for the retrieval scored-check's
    missed_bullets verbatim-text validation."""
    expects = extras.setdefault("expect", {})
    expect = e.get("expect")
    expects[e["id"]] = expect if isinstance(expect, list) else []
    return None


def _shape_union_hook(path: Path, e: dict, extras: dict) -> str | None:
    """Validate the arms object and kind consistency across shape
    results files; records id -> kind in extras['kinds'] and per-arm
    marker triage totals in extras['marker_counts']. Occurrences of the
    same arm name across files (e.g. a restraint rerun of v2) are
    summed, so the totals are independent of --results order; the
    driver narrows them by hand when filling the skeleton."""
    eid = e["id"]
    arms = e.get("arms")
    if not isinstance(arms, dict):
        return f"{path}: entry {eid} is missing its 'arms' object"
    kinds = extras.setdefault("kinds", {})
    kind = e.get("kind")
    if eid not in kinds:
        if kind not in SHAPE_KINDS:
            return (
                f"{path}: entry {eid}: kind must be one of "
                f"{sorted(SHAPE_KINDS)}, got {kind!r}"
            )
        kinds[eid] = kind
    elif kind != kinds[eid]:
        return (
            f"{path}: entry {eid}: kind {kind!r} differs from earlier "
            f"results file ({kinds[eid]!r})"
        )
    raw_markers = e.get("markers")
    markers = raw_markers if isinstance(raw_markers, dict) else {}
    entry_counts = extras.setdefault("marker_counts", {}).setdefault(eid, {})
    for arm, arm_data in arms.items():
        if not isinstance(arm, str) or not arm:
            continue
        if not isinstance(arm_data, dict) or not isinstance(
            arm_data.get("runs"), list
        ):
            continue
        arm_counts = entry_counts.setdefault(arm, {})
        for run in arm_data["runs"]:
            if not isinstance(run, dict):
                continue
            answer = run.get("answer_text")
            answer = answer if isinstance(answer, str) else ""
            for name, n in marker_triage_counts(answer, markers).items():
                arm_counts[name] = arm_counts.get(name, 0) + n
    return None


def _pressure_union_hook(path: Path, e: dict, extras: dict) -> str | None:
    """Pressure results entries must carry their arms object: the
    scored check's red/green implications read the union arm set."""
    if not isinstance(e.get("arms"), dict):
        return f"{path}: entry {e['id']} is missing its 'arms' object"
    return None


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


# Scored result value -> manifest count key, per track. Shape and
# pressure share no-failure/unresolved/void, so the shared values alone
# can never identify a track; detection needs a discriminating signal
# (bulletproof/arm reference for pressure, adopted/adopted_arm/
# restraint_gate for shape, classification/control/ablation_flag or a
# pass/fail/gap result for retrieval).
_TRACK_SUM_KEYS = {
    "retrieval-test": {
        "pass": "passes",
        "fail": "fails",
        "gap": "gaps",
        "void": "voids",
    },
    "shape-test": {
        "adopted": "adopted",
        "no-failure": "no-failure",
        "unresolved": "unresolved",
        "void": "voids",
    },
    "pressure-test": {
        "bulletproof": "bulletproof",
        "no-failure": "no-failure",
        "unresolved": "unresolved",
        "void": "voids",
    },
}


def _scored_track_signals(scored_entries: list[dict]) -> list[str]:
    """Collect the set of tracks the scored entries can be proven to
    belong to, using only discriminating signals (see _TRACK_SUM_KEYS)."""
    pressure = shape = retrieval = False
    for e in scored_entries:
        if not isinstance(e, dict):
            continue
        if e.get("result") == "bulletproof" or e.get("arm") in (
            "red",
            "green",
        ):
            pressure = True
        if (
            e.get("result") == "adopted"
            or "adopted_arm" in e
            or "restraint_gate" in e
        ):
            shape = True
        if e.get("result") in ("pass", "fail", "gap") or any(
            k in e for k in ("classification", "control", "ablation_flag")
        ):
            retrieval = True
    signals = []
    if pressure:
        signals.append("pressure-test")
    if shape:
        signals.append("shape-test")
    if retrieval:
        signals.append("retrieval-test")
    return signals


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
    vocab = _TRACK_SUM_KEYS[resolved]
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


def emit_scored_skeleton(
    track: str,
    results_ids: list[str],
    extras: dict[str, dict],
    out_path: Path,
    header: dict | None = None,
) -> None:
    """Write the scored.json skeleton: every union id exactly once, all
    mechanically derivable fields pre-filled, judgment fields null. The
    per-track scored-checks reject the nulls, so an uncompleted skeleton
    cannot pass as a scored artifact — the check is the you-forgot-to-
    judge gate. Extras carry the union hooks' collections: retrieval's
    expect rubric is judging context only and is never written; shape
    kinds/marker_counts come from extras['kinds']/extras['marker_counts'];
    pressure arm sets are merged into extras['arms'] by the caller."""
    entries = []
    for eid in results_ids:
        if track == "retrieval":
            entry = {
                "id": eid,
                "result": None,
                "classification": None,
                "control": None,
                "ablation_flag": None,
                "missed_bullets": None,
                "notes": None,
            }
        elif track == "shape":
            entry = {
                "id": eid,
                "kind": extras["kinds"][eid],
                "result": None,
                "adopted_arm": None,
                "restraint_gate": None,
                "marker_counts": extras["marker_counts"].get(eid, {}),
                "notes": None,
            }
        else:  # "pressure"
            arms = extras["arms"].get(eid, set())
            if "red" not in arms:
                # No red arm means the entry can never pass the scored
                # check (RED always runs first); nothing to constrain.
                constraint = None
            elif "green" in arms:
                constraint = ["bulletproof", "unresolved"]
            else:
                constraint = ["no-failure", "void"]
            entry = {
                "id": eid,
                "result": None,
                "counters": None,
                "verdict_constraint": constraint,
                "notes": None,
            }
        entries.append(entry)
    doc = dict(header) if header else {}
    doc["entries"] = entries
    out_path.write_text(json.dumps(doc, indent=2) + "\n")


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


def _emit_scored_skeleton_cmd(
    track: str,
    results_paths: list[str],
    results_ids: list[str],
    extras: dict,
    args: argparse.Namespace,
) -> int:
    """The --emit-skeleton branch shared by the three scored-checks:
    the results union has already been computed and validated; derive
    the header for the header-carrying tracks, write the skeleton, and
    confirm on one line."""
    out_path = Path(args.emit_skeleton)
    header = (
        _scored_skeleton_header(results_paths)
        if track in ("retrieval", "pressure")
        else None
    )
    emit_scored_skeleton(track, results_ids, extras, out_path, header)
    print(f"wrote skeleton: {out_path} ({len(results_ids)} entries)")
    return 0


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
            f"{entry[k]} {k}" for k in _TRACK_SUM_KEYS[key].values()
        )
    print(
        f"recorded: {manifest} (scope {scope}, date {entry['date']}, "
        f"{detail}, {checksum[:26]}…)"
    )
    return 0


def cmd_failures(args: argparse.Namespace) -> int:
    """Print every failed run (query, run number, detail, full reasoning)
    from a suite result JSON. Extraction only; analysis is the agent's job.
    Exit 0 even when failures exist — this is an extractor, not a gate."""
    path = Path(args.results)
    if not path.exists():
        print(f"error: results file not found: {path}", file=sys.stderr)
        return 1
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        print(f"error: invalid JSON in {path}: {e}", file=sys.stderr)
        return 1
    if not isinstance(data, dict) or not isinstance(data.get("queries"), list):
        print(
            f"error: {path}: not a suite result file (missing 'queries' "
            f"list)",
            file=sys.stderr,
        )
        return 1
    n_failures = 0
    for q in data["queries"]:
        failures = q.get("failures") or []
        if not failures:
            continue
        expect = "trigger" if q.get("should_trigger") else "not-trigger"
        print(f'query: "{q.get("query")}"   expected: {expect}')
        for f in failures:
            n_failures += 1
            timeout = " (timeout)" if f.get("timeout") else ""
            session = (
                f" [session {f['session_id']}]" if f.get("session_id") else ""
            )
            print(
                f"  run {f.get('run')}: {f.get('outcome')}{timeout}"
                f"{session} — {f.get('detail', '')}"
            )
            reasoning = f.get("reasoning") or "(no reasoning captured)"
            for line in reasoning.splitlines():
                print(f"    {line}")
        print()
    if n_failures == 0:
        print(f"no failed runs in {path}")
    return 0


def cmd_retrieval_evidence(args: argparse.Namespace) -> int:
    """Print the per-run scoring evidence from a retrieval-suite results
    JSON: per entry, the expect rubric and, for every arm/rep, the answer
    text, sources consulted, void signals, and tool-call targets. The
    trigger track's `failures` equivalent: extraction only, so the driver
    scores from presented evidence instead of hand-rolling JSON walks.
    Exit 0 with an entry count line; exit 1 only on a malformed file."""
    path = Path(args.results)
    data_entries, error = load_results_json(path, "retrieval")
    if error is not None:
        print(f"error: {error}", file=sys.stderr)
        return 1

    n_printed = 0
    try:
        for eid, entry in iter_evidence(data_entries, path, args.entry):
            skill_arm = entry.get("skill_arm")
            control_arm = entry.get("control_arm")
            if (
                not isinstance(skill_arm, dict)
                or not isinstance(skill_arm.get("runs"), list)
                or not isinstance(control_arm, dict)
                or not isinstance(control_arm.get("runs"), list)
            ):
                print(
                    f"error: {path}: entry {eid} is missing arm run lists",
                    file=sys.stderr,
                )
                return 1

            print(f"## {eid}")
            print(f'query: "{entry.get("query", "")}"')
            expect = entry.get("expect") or []
            print("expect:")
            for b in expect:
                print(f"  - {b}")
            print()
            for arm_key, arm in (
                ("skill_arm", skill_arm),
                ("control_arm", control_arm),
            ):
                for n, run in enumerate(arm["runs"], start=1):
                    timeout = "timeout" if run.get("timeout") else "ok"
                    session = run.get("session_id") or "no-session"
                    print(
                        f"[{ARM_TAGS[arm_key]}] rep {n:>3} "
                        f"({session}, {timeout})"
                    )
                    answer = run.get("answer_text") or "(empty answer)"
                    print("answer:")
                    for line in answer.splitlines():
                        print(f"  {line}")
                    src = run.get("sources_consulted")
                    if src:
                        print(f"sources consulted: {src}")
                    signals = run.get("void_signals") or []
                    joined = ", ".join(signals) if signals else "none"
                    print(f"void signals: {joined}")
                    targets = [
                        c.get("target")
                        for c in run.get("tool_calls") or []
                        if c.get("target")
                    ]
                    print(
                        f"tool calls: "
                        f"{', '.join(targets) if targets else 'none'}"
                    )
                    print()
            n_printed += 1
    except EvidenceError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    if args.entry is not None and n_printed == 0:
        print(f"error: no entry with id: {args.entry}", file=sys.stderr)
        return 1
    print(f"evidence: {n_printed} entries from {path}")
    return 0


# --------------------------------------------------------------------------
# Retrieval campaign tooling: retrieval-suite + scored-check


SOURCES_RE = re.compile(
    r"sources consulted:\s*(?P<block>.*)$", re.IGNORECASE | re.DOTALL
)


def stage_and_dispatch(
    entry: dict,
    arm: str,
    rep: int,
    reps: int,
    arm_ws: Path,
    fixtures_dir: Path,
) -> str:
    query = entry["query"]
    if not entry.get("fixtures"):
        return query
    label = arm if reps == 1 else f"{arm}-rep{rep}"
    run_dir = arm_ws / "fixtures" / entry["id"] / label
    run_dir.mkdir(parents=True, exist_ok=True)
    for name in entry["fixtures"]:
        shutil.copyfile(fixtures_dir / name, run_dir / name)
    return query.replace("{RUN_DIR}", str(run_dir))


def load_retrieval_queries(path: Path) -> list[dict]:
    """Read and strictly validate a retrieval query file (design §8 schema).
    On any violation prints `error: <exact reason>` to stderr and exits 1
    (pre-spend: zero harness runs happen before this returns)."""
    return load_entries(path, "query", "query", _check_retrieval_fields)


def _check_retrieval_fields(path: Path, i: int, entry: dict, eid: str) -> None:
    """Per-field checks for a retrieval query entry: the query and expect
    rubric, optional fixtures with on-disk presence, and the {RUN_DIR}
    token agreement rule."""
    q = entry.get("query")
    if not isinstance(q, str) or not q:
        _fail(
            f"{path}: entry {i} ({eid}) missing 'query' " f"(non-empty string)"
        )
    expect = entry.get("expect")
    if (
        not isinstance(expect, list)
        or not expect
        or not all(isinstance(b, str) and b for b in expect)
    ):
        _fail(
            f"{path}: entry {i} ({eid}) missing 'expect' "
            f"(non-empty list of strings)"
        )
    fixtures = entry.get("fixtures")
    has_fixtures = fixtures is not None
    if has_fixtures:
        if (
            not isinstance(fixtures, list)
            or not fixtures
            or not all(isinstance(n, str) and n for n in fixtures)
        ):
            _fail(
                f"{path}: entry {i} ({eid}) 'fixtures' must be a "
                f"non-empty list of strings"
            )
        for name in fixtures:
            fixture_path = path.parent / "fixtures" / name
            if not fixture_path.is_file():
                _fail(
                    f"{path}: entry {i} ({eid}) fixture not found: "
                    f"{fixture_path}"
                )
    if ("{RUN_DIR}" in q) != has_fixtures:
        if has_fixtures:
            _fail(
                f"{path}: entry {i} ({eid}) declares fixtures but its "
                f"query has no {{RUN_DIR}} token"
            )
        _fail(
            f"{path}: entry {i} ({eid}) query has a {{RUN_DIR}} token "
            f"but declares no fixtures"
        )


def build_run_record(
    ev,
    query_dispatched: str,
    timed_out: bool,
    ws_root: Path,
    arm: str,
    skill: str,
) -> dict:
    answer = "".join(ev.answer_parts)
    m = SOURCES_RE.search(answer)
    signals = []
    if arm == "skill_arm" and not ev.completed_load:
        signals.append("skill-not-loaded")
    if arm == "control_arm" and ev.skill_loads:
        signals.append("control-loaded-skill")
    if not answer.strip():
        signals.append("empty-answer")
    root = str(ws_root.resolve())
    for call in ev.tool_calls:
        t = call["target"]
        if not t:
            continue
        p = Path(t) if Path(t).is_absolute() else ws_root / t
        if not str(p.resolve()).startswith(root):
            signals.append("read-outside-workspace")
            break
    return {
        "query_dispatched": query_dispatched,
        "answer_text": answer,
        "sources_consulted": m.group("block").strip() if m else None,
        "tool_calls": ev.tool_calls,
        "skill_load_completed": ev.completed_load,
        "other_skill_loads": [
            s["name"] for s in ev.skill_loads if s["name"] not in (None, skill)
        ],
        "denied_tool_attempts": ev.denied_tool_attempts,
        "reasoning": "".join(ev.reasoning_parts),
        "session_id": ev.session_id,
        "timeout": timed_out,
        "parseable_events": ev.parseable,
        "void_signals": signals,
    }


def run_records_batch(
    strategy: EvalStrategy,
    entry: dict,
    arm: str,
    arm_ws: Path,
    agent: str,
    args: argparse.Namespace,
) -> list[dict]:
    fixtures_dir = Path(args.queries).parent / "fixtures"
    skill = args.skill if arm == "skill_arm" else None
    tag = ARM_TAGS[arm]

    def run_rep(n: int) -> dict:
        log_start(n, tag)
        dispatched = stage_and_dispatch(
            entry, arm, n, args.reps, arm_ws, fixtures_dir
        )
        ev, timed_out = strategy.execute(
            arm_ws,
            agent,
            dispatched,
            args.model,
            args.variant,
            skill=skill,
        )
        record = build_run_record(
            ev, dispatched, timed_out, arm_ws, arm, args.skill
        )
        line = f"[{tag}] [rep {n:>3}] completed"
        if timed_out:
            line += " (timeout)"
        if record["void_signals"]:
            line += f" signals: {', '.join(record['void_signals'])}"
        emit(line)
        return record

    return run_rep_batched(run_rep, args.reps, tag)


def cmd_retrieval_suite(args: argparse.Namespace) -> int:
    """Run a retrieval campaign: every query × 2 arms × reps headless runs.
    Pre-spend validation exits 1 with an exact message before any harness
    invocation. HarnessExecutionError anywhere -> stderr, exit 1, no JSON,
    workspaces kept (trigger policy, unchanged)."""
    strategy_cls = resolve_strategy(args.harness)
    check_harness(args.harness, strategy_cls, args.model)  # binary + model
    skill_ws = Path(args.skill_workspace)
    control_ws = Path(args.control_workspace)
    agents_dir = Path(args.agents_dir)
    queries_path = Path(args.queries)

    # ---- pre-spend validation: any failure exits 1, exact message ----
    probe = strategy_cls(timeout=args.timeout)
    for base in (RETRIEVAL_EVALUATOR_AGENT, RETRIEVAL_CONTROL_AGENT):
        validate_eval_agent(probe, agents_dir, base)
    if args.reps < 1:
        return _err("--reps must be >= 1")
    if args.timeout < 1:
        return _err("--timeout must be >= 1")
    if not (skill_ws / ".agents" / "skills" / args.skill).is_dir():
        _fail(
            f"skill workspace has no synced skill '{args.skill}': run "
            "workspace-manager.sh sync --full and status --full first"
        )
    if (control_ws / ".agents" / "skills" / args.skill).exists():
        _fail(
            f"control workspace contains skill '{args.skill}' — baseline "
            "contamination; recreate the control workspace, never sync"
        )
    entries = load_retrieval_queries(queries_path)  # exits 1 on violation
    out = Path(args.out)
    if not out.parent.is_dir():
        _fail(f"output directory does not exist: {out.parent}")

    # ---- install + run ----
    _Log.file = out.with_suffix(".log").open("w")  # mirror like suite
    strategy = strategy_cls(timeout=args.timeout)
    strategy.install(
        skill_ws,
        agents_dir,
        RETRIEVAL_EVALUATOR_AGENT,
        skill_name=args.skill,
    )  # {{SKILL_NAME}}
    strategy.install(control_ws, agents_dir, RETRIEVAL_CONTROL_AGENT)

    emit(f"retrieval test suite: {args.skill} ({len(entries)} queries)")
    emit(f"skill workspace: {skill_ws}")
    emit(f"control workspace: {control_ws}")
    emit(
        f"harness: {args.harness}  model: {args.model or '(default)'}  "
        f"variant: {args.variant or '(none)'}  reps: {args.reps}  "
        f"timeout: {args.timeout}s"
    )

    results = []
    for entry in entries:
        record = {
            "id": entry["id"],
            "query": entry["query"],
            "expect": entry["expect"],
        }
        # Both arms in parallel, like eval_batch parallelizes trigger reps:
        # each arm still runs its smoke rep alone before its rep batches, but
        # the arms no longer wait on each other. A harness failure in either
        # arm aborts the campaign (no JSON, workspaces kept).
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = {
                pool.submit(
                    run_records_batch, strategy, entry, arm, ws, agent, args
                ): arm
                for arm, ws, agent in (
                    ("skill_arm", skill_ws, RETRIEVAL_EVALUATOR_AGENT),
                    ("control_arm", control_ws, RETRIEVAL_CONTROL_AGENT),
                )
            }
            for fut, arm in futures.items():
                try:
                    record[arm] = {"runs": fut.result()}
                except SystemExit as e:
                    # The worker emitted the exact error and exited 1;
                    # propagate the abort in the main thread.
                    return e.code if isinstance(e.code, int) else 1
                except HarnessExecutionError as e:
                    emit(
                        f"error: [{ARM_TAGS[arm]}] could not execute: {e}"
                        f"{_session_suffix(e)}",
                        err=True,
                    )
                    return 1
        results.append(record)
        emit(f"[{len(results)}/{len(entries)}] {entry['id']}")
    config = base_config(args)
    config["queries"] = str(queries_path)
    write_results(out, config, results)
    emit(f"retrieval suite: {len(entries)} entries -> {out}")
    return 0


# --------------------------------------------------------------------------
# Scored-artifact validation: scored-check


RESULTS = {"pass", "fail", "gap", "void"}
CLASSIFICATIONS = {"findability", "clarity"}  # "gap" is a result, not a
#                                              classification
CONTROLS = {"pass", "fail", "void"}


def cmd_scored_check(args: argparse.Namespace) -> int:
    """Validate scored.json against the results JSON it claims to cover.
    The driver owns judgment; this keeps the audit artifact honest. Exact
    messages, exit 1 on any violation; exit 0 with a coverage line when
    every results id is accounted for exactly once. Beyond the schema:
    ablation_flag must equal (control == "pass"), missed_bullets must be
    verbatim rubric text from the entry's expect list, and when the
    record-step counts are passed (--passes/--fails/--gaps/--voids) they
    must match the scored sums. With --emit-skeleton PATH instead of
    --scored, writes a scored.json skeleton (every results id once,
    judgment fields null) and exits 0."""
    gate = _scored_target_gate(args)
    if gate is not None:
        return gate
    union = union_results(
        [args.results], "retrieval", entry_hook=_retrieval_union_hook
    )
    if isinstance(union, str):
        return _err(union)
    results_ids, _results_arms, extras = union
    results_expect = extras.get("expect", {})

    if getattr(args, "emit_skeleton", None) is not None:
        return _emit_scored_skeleton_cmd(
            "retrieval", [args.results], results_ids, extras, args
        )

    scored_path = Path(args.scored)
    scored_entries = load_scored_json(scored_path)
    if isinstance(scored_entries, str):
        return _err(scored_entries)
    covered_entries = check_coverage(scored_entries, results_ids, scored_path)
    if isinstance(covered_entries, str):
        return _err(covered_entries)

    for entry in covered_entries:
        eid = entry["id"]
        result = entry.get("result")
        if result not in RESULTS:
            return _err(
                f"{scored_path}: entry {eid}: result must be one of "
                f"{sorted(RESULTS)}, got {result!r}"
            )
        classification = entry.get("classification")
        if result == "fail":
            if classification not in CLASSIFICATIONS:
                return _err(
                    f"{scored_path}: entry {eid}: classification must be "
                    f"one of {sorted(CLASSIFICATIONS)}, got "
                    f"{classification!r}"
                )
        elif classification is not None:
            return _err(
                f"{scored_path}: entry {eid}: classification is only "
                f"valid with result 'fail'"
            )

        control = entry.get("control")
        if control not in CONTROLS:
            return _err(
                f"{scored_path}: entry {eid}: control must be one of "
                f"{sorted(CONTROLS)}, got {control!r}"
            )
        if not isinstance(entry.get("ablation_flag"), bool):
            return _err(
                f"{scored_path}: entry {eid}: ablation_flag must be a " f"bool"
            )
        # Deterministic derivation: a control pass is exactly what makes
        # the entry an ablation flag; the scorer must not improvise it.
        if entry["ablation_flag"] != (control == "pass"):
            return _err(
                f"{scored_path}: entry {eid}: ablation_flag must be true "
                f"exactly when control is 'pass', got "
                f"ablation_flag={entry['ablation_flag']} with "
                f"control={control!r}"
            )

        missed = entry.get("missed_bullets")
        if missed is not None and (
            not isinstance(missed, list)
            or not all(isinstance(b, str) for b in missed)
        ):
            return _err(
                f"{scored_path}: entry {eid}: missed_bullets must be a "
                f"list of strings"
            )
        if result in ("fail", "gap") and not missed:
            return _err(
                f"{scored_path}: entry {eid}: missed_bullets required "
                f"(non-empty) for result '{result}'"
            )
        if missed:
            # Missed bullets name rubric text verbatim — anything else is
            # a scoring artifact, not evidence against the doc.
            not_in_expect = [
                b for b in missed if b not in results_expect.get(eid, [])
            ]
            if not_in_expect:
                return _err(
                    f"{scored_path}: entry {eid}: missed_bullets not in "
                    f"the entry's expect rubric: "
                    f"{', '.join(not_in_expect)}"
                )

    rc = counts_gate(
        args,
        covered_entries,
        ("passes", "fails", "gaps", "voids"),
        ("pass", "fail", "gap", "void"),
    )
    if rc is not None:
        return rc
    print(f"ok: {scored_path} covers {len(results_ids)} entries")
    return 0


# --------------------------------------------------------------------------
# Shape campaign tooling: shape-suite + shape-evidence + shape-scored-check

# Vocabularies for the shape track (plan §File schemas / §Scoring artifacts).
SHAPE_KINDS = {"shaping", "pattern"}
SHAPE_RESULTS = {"adopted", "no-failure", "unresolved", "void"}
SHAPE_GATES = {"pass", "fail"}
# Fixture keys allowed on an entries file: `application` is always present;
# `counter-example` is required exactly on pattern entries (restraint gate).
SHAPE_FIXTURE_KEYS = ("application", "counter-example")
# Variant arm keys allowed beyond the v0 control arm.
SHAPE_VARIANT_KEYS = ("v1", "v2", "v3")


def _check_marker_tokens(
    path: Path, eid: str, name: str, markers: dict
) -> None:
    """Marker tokens are grep-regexes scored against answer text; a token
    that does not compile would blow up mid-campaign, so it fails here,
    pre-spend."""
    for key, token in markers.items():
        try:
            re.compile(token)
        except re.error as e:
            _fail(
                f"{path}: entry {eid!r} {name}.{key} is not a valid "
                f"grep token: {e}"
            )


def load_shape_entries(path: Path) -> list[dict]:
    """Read and strictly validate a shape entries file. Schema only: the
    verbatim section-span assertion against the snapshotted skill body
    lives in cmd_shape_suite, which owns the body bytes. On any violation
    prints `error: <exact reason>` to stderr and exits 1 (pre-spend: zero
    harness runs happen before this returns)."""
    return load_entries(path, "entries", "entry", _check_shape_fields)


def _check_shape_fields(path: Path, i: int, entry: dict, eid: str) -> None:
    """Per-field checks for a shape entry: kind, the verbatim section
    span, fixtures (with the pattern counter-example rules), grep-token
    markers (with the pattern restraint rules), and variants."""
    kind = entry.get("kind")
    if kind not in SHAPE_KINDS:
        _fail(
            f"{path}: entry {i} ({eid}) kind must be one of "
            f"{sorted(SHAPE_KINDS)}, got {kind!r}"
        )
    section = entry.get("section")
    if not isinstance(section, str) or not section:
        _fail(
            f"{path}: entry {i} ({eid}) missing 'section' "
            f"(non-empty string)"
        )
    fixtures = entry.get("fixtures")
    if not isinstance(fixtures, dict) or not fixtures:
        _fail(
            f"{path}: entry {i} ({eid}) 'fixtures' must be a "
            f"non-empty object"
        )
    application = fixtures.get("application")
    if not isinstance(application, str) or not application:
        _fail(
            f"{path}: entry {i} ({eid}) fixtures.application must be "
            f"a non-empty string"
        )
    unknown = [k for k in fixtures if k not in SHAPE_FIXTURE_KEYS]
    if unknown:
        _fail(
            f"{path}: entry {i} ({eid}) has unknown fixture keys: "
            f"{', '.join(unknown)} (allowed: "
            f"{', '.join(SHAPE_FIXTURE_KEYS)})"
        )
    has_counter = isinstance(fixtures.get("counter-example"), str) and bool(
        fixtures.get("counter-example")
    )
    if kind == "pattern" and not has_counter:
        _fail(
            f"{path}: entry {i} ({eid}) is a pattern entry and must "
            f"declare a 'counter-example' fixture"
        )
    if kind == "shaping" and "counter-example" in fixtures:
        _fail(
            f"{path}: entry {i} ({eid}) is a shaping entry and must "
            f"not declare a 'counter-example' fixture"
        )
    markers = entry.get("markers")
    if not isinstance(markers, dict) or not markers:
        _fail(
            f"{path}: entry {i} ({eid}) 'markers' must be a non-empty "
            f"dict of grep tokens"
        )
    if not all(isinstance(t, str) and t for t in markers.values()) or not all(
        isinstance(k, str) and k for k in markers
    ):
        _fail(
            f"{path}: entry {i} ({eid}) 'markers' keys and tokens "
            f"must be non-empty strings"
        )
    _check_marker_tokens(path, eid, "markers", markers)
    restraint = entry.get("restraint_markers")
    if kind == "pattern":
        if not isinstance(restraint, dict) or not restraint:
            _fail(
                f"{path}: entry {i} ({eid}) 'restraint_markers' "
                f"(non-empty dict of grep tokens) is required for "
                f"pattern entries"
            )
        if not all(
            isinstance(t, str) and t for t in restraint.values()
        ) or not all(isinstance(k, str) and k for k in restraint):
            _fail(
                f"{path}: entry {i} ({eid}) 'restraint_markers' keys "
                f"and tokens must be non-empty strings"
            )
        _check_marker_tokens(path, eid, "restraint_markers", restraint)
    elif restraint is not None:
        _fail(
            f"{path}: entry {i} ({eid}) 'restraint_markers' is only "
            f"valid for pattern entries"
        )
    variants = entry.get("variants")
    if not isinstance(variants, dict) or not variants:
        _fail(
            f"{path}: entry {i} ({eid}) 'variants' must be a "
            f"non-empty object"
        )
    if len(variants) > 3 or not set(variants) <= set(SHAPE_VARIANT_KEYS):
        _fail(
            f"{path}: entry {i} ({eid}) 'variants' must have 1-3 "
            f"entries keyed {', '.join(SHAPE_VARIANT_KEYS)}"
        )
    if not all(isinstance(v, str) and v for v in variants.values()):
        _fail(
            f"{path}: entry {i} ({eid}) 'variants' values must be "
            f"non-empty strings"
        )


# Per-run prompt assembly. The per-run prompt never contains the rule
# statement, the markers, or the expected shape; the answer contract
# lives in the agent body, constant across arms. Every arm injects the
# assembled body (v0: the rule's section span removed; vN: the span
# replaced by the variant text) as "Project conventions" — injection,
# not byte-states: the workspace is never written, so arms differ only
# in prompt bytes and a variant can never leak into another arm's run.
SHAPE_PROMPT_TEMPLATE = """\
Project conventions:
{body}

Task:
{fixture}"""


def build_shape_prompt(body: str, fixture: str) -> str:
    """One rep's prompt bytes: the assembled arm body injected as
    "Project conventions", then the bare fixture text. Never contains
    the rule statement, the markers, or the expected shape."""
    return SHAPE_PROMPT_TEMPLATE.format(body=body, fixture=fixture)


def assemble_arm_body(body: str, entry: dict, arm: str) -> str:
    """One arm's body bytes. v0 (control) removes the rule's section span
    together with exactly one following blank line; vN replaces the span
    with the variant text. The caller asserts the span occurs verbatim
    exactly once in body before calling (pre-spend doc-drift gate), so a
    violated invariant here is a harness bug, not doc drift."""
    section = entry["section"]
    idx = body.find(section)
    end = idx + len(section)
    if idx < 0 or body.find(section, end) >= 0:
        raise ValueError(
            f"section span of entry {entry['id']!r} is not unique in body"
        )
    if arm == "v0":
        rest = body[end:]
        if rest.startswith("\n\n"):
            # The span's line break plus exactly one following blank
            # line go away with it, leaving a single blank line between
            # the neighbours.
            rest = rest[2:]
        return body[:idx] + rest
    return body[:idx] + entry["variants"][arm] + body[end:]


def verify_arm_bytes(new_body: str, entry: dict, arm: str) -> None:
    """Post-assembly sanity check, run before any dispatch: the v0 arm
    must have lost the span, a variant arm must carry its text."""
    if arm == "v0":
        if entry["section"] in new_body:
            raise ValueError(
                f"v0 removal left the section span of entry "
                f"{entry['id']!r} in the body"
            )
    elif entry["variants"][arm] not in new_body:
        raise ValueError(
            f"variant arm {arm!r} of entry {entry['id']!r} is missing "
            f"from the assembled body"
        )


def build_shape_run_record(
    ev,
    query_dispatched: str,
    timed_out: bool,
    ws_root: Path,
    arm: str,
) -> dict:
    """The shape-track run record: build_run_record adapted, not reused,
    because that builder keys its signals on the retrieval arm names.
    The skill body is injected into the prompt, so there is no load
    signal: any skill load attempt is a void signal instead (a shape rep
    needs zero — the conventions are already in context and the skill
    tool is denied by policy). Adds the arm key so runs stay attributable
    in the merged results of a phase."""
    answer = "".join(ev.answer_parts)
    m = SOURCES_RE.search(answer)
    signals = []
    if ev.skill_loads:
        signals.append("skill-load-attempted")
    if not answer.strip():
        signals.append("empty-answer")
    root = str(ws_root.resolve())
    for call in ev.tool_calls:
        t = call["target"]
        if not t:
            continue
        p = Path(t) if Path(t).is_absolute() else ws_root / t
        if not str(p.resolve()).startswith(root):
            signals.append("read-outside-workspace")
            break
    return {
        "arm": arm,
        "query_dispatched": query_dispatched,
        "answer_text": answer,
        "sources_consulted": m.group("block").strip() if m else None,
        "tool_calls": ev.tool_calls,
        "denied_tool_attempts": ev.denied_tool_attempts,
        "reasoning": "".join(ev.reasoning_parts),
        "session_id": ev.session_id,
        "timeout": timed_out,
        "parseable_events": ev.parseable,
        "void_signals": signals,
    }


def run_shape_rep_batch(
    strategy: EvalStrategy,
    prompt: str,
    arm: str,
    ws: Path,
    agent: str,
    args: argparse.Namespace,
) -> list[dict]:
    """Reps for one (entry, arm) pair. Every rep shares identical prompt
    bytes; per-rep scheduling lives in run_rep_batched."""
    tag = f" {arm} "

    def run_rep(n: int) -> dict:
        log_start(n, tag)
        ev, timed_out = strategy.execute(
            ws,
            agent,
            prompt,
            args.model,
            args.variant,
        )
        record = build_shape_run_record(ev, prompt, timed_out, ws, arm)
        line = f"[{tag}] [rep {n:>3}] completed"
        if timed_out:
            line += " (timeout)"
        if record["void_signals"]:
            line += f" signals: {', '.join(record['void_signals'])}"
        emit(line)
        return record

    return run_rep_batched(run_rep, args.reps, tag)


def cmd_shape_suite(args: argparse.Namespace) -> int:
    """Run one shape campaign phase: entries x arms x reps headless runs,
    STRICTLY serialized per entry x arm — never the retrieval track's
    arm-parallel structure. Arms differ only in prompt bytes: each arm's
    body (v0: section span removed; vN: span replaced by the variant) is
    assembled fresh from the snapshotted skill file and injected into
    every rep's prompt; the workspace is never synced and never written,
    so there is no byte-state to restore. Pre-spend validation exits 1
    with an exact message before any harness invocation."""
    strategy_cls = resolve_strategy(args.harness)
    check_harness(args.harness, strategy_cls, args.model)  # binary + model
    ws = Path(args.workspace)
    agents_dir = Path(args.agents_dir)
    entries_path = Path(args.entries)

    # ---- pre-spend validation: any failure exits 1, exact message ----
    probe = strategy_cls(timeout=args.timeout)
    validate_eval_agent(probe, agents_dir, SHAPE_EVALUATOR_AGENT)
    if args.reps < 1:
        _fail("--reps must be >= 1")
    if args.timeout < 1:
        _fail("--timeout must be >= 1")

    skill_file = Path(args.skill_file)
    if not skill_file.is_file():
        _fail(f"skill file not found: {skill_file}")
    body = skill_file.read_text()
    if not body.strip():
        _fail(f"skill file is empty: {skill_file}")

    if args.fixture_key not in SHAPE_FIXTURE_KEYS:
        _fail(
            f"--fixture-key must be one of {', '.join(SHAPE_FIXTURE_KEYS)}, "
            f"got {args.fixture_key!r}"
        )
    arms = [a.strip() for a in args.arms.split(",")]
    if not arms or any(not a for a in arms):
        _fail(
            f"--arms must be a comma-separated list of arms "
            f"({', '.join(SHAPE_VARIANT_KEYS)} or v0), got {args.arms!r}"
        )

    entries = load_shape_entries(entries_path)  # schema, exits 1 on violation
    for entry in entries:
        for arm in arms:
            if arm != "v0" and arm not in entry["variants"]:
                _fail(
                    f"--arms: entry {entry['id']!r} defines no variant "
                    f"{arm!r} (has: {', '.join(sorted(entry['variants']))})"
                )
        fixture = entry["fixtures"].get(args.fixture_key)
        if not isinstance(fixture, str) or not fixture:
            _fail(
                f"entry {entry['id']!r} has no {args.fixture_key!r} "
                f"fixture"
            )

    # Doc-drift gate: every section span must appear verbatim exactly once
    # in the snapshotted body (frontmatter already stripped by the driver
    # — spans overlapping frontmatter are never matched). Aborts before
    # spend.
    for entry in entries:
        occurrences = body.count(entry["section"])
        if occurrences != 1:
            _fail(
                f"doc drift: section span of entry {entry['id']!r} occurs "
                f"{occurrences} times in the skill body (expected exactly "
                f"once); fix the entry or the snapshot"
            )

    out = Path(args.out)
    if not out.parent.is_dir():
        _fail(f"output directory does not exist: {out.parent}")
    if (ws / ".agents" / "skills" / args.skill).exists():
        _fail(
            f"workspace contains skill '{args.skill}' — this track injects "
            "the skill body into prompts and never syncs; recreate the "
            "workspace, never sync"
        )

    # ---- install + run ----
    _Log.file = out.with_suffix(".log").open("w")  # mirror like suite
    strategy = strategy_cls(timeout=args.timeout)
    strategy.install(ws, agents_dir, SHAPE_EVALUATOR_AGENT)

    emit(f"shape test suite: {args.skill} ({len(entries)} entries)")
    emit(f"workspace: {ws}")
    emit(
        f"harness: {args.harness}  model: {args.model or '(default)'}  "
        f"variant: {args.variant or '(none)'}  reps: {args.reps}  "
        f"timeout: {args.timeout}s"
    )
    emit(f"skill file: {skill_file}")
    emit(f"arms: {', '.join(arms)}  fixture-key: {args.fixture_key}")

    results = []
    for i, entry in enumerate(entries, start=1):
        record = {
            "id": entry["id"],
            "kind": entry["kind"],
            "markers": entry["markers"],
            "restraint_markers": entry.get("restraint_markers"),
            "arms": {},
        }
        for arm in arms:
            try:
                arm_body = assemble_arm_body(body, entry, arm)
                verify_arm_bytes(arm_body, entry, arm)
            except ValueError as e:
                _fail(str(e))
            prompt = build_shape_prompt(
                arm_body, entry["fixtures"][args.fixture_key]
            )
            record["arms"][arm] = {
                "runs": run_shape_rep_batch(
                    strategy, prompt, arm, ws, SHAPE_EVALUATOR_AGENT, args
                )
            }
        results.append(record)
        emit(f"[{i}/{len(entries)}] {entry['id']}")

    config = base_config(args)
    config["entries"] = str(entries_path)
    config["skill_file"] = str(skill_file)
    config["arms"] = arms
    config["fixture_key"] = args.fixture_key
    write_results(out, config, results)
    emit(f"shape suite: {len(entries)} entries -> {out}")
    return 0


def marker_triage_counts(answer: str, markers: dict) -> dict:
    """Per-marker count of answer lines matching the grep token. Triage
    only — the driver reads every flagged sample by hand."""
    counts = {}
    for name, token in markers.items():
        counts[name] = sum(
            1 for line in answer.splitlines() if re.search(token, line)
        )
    return counts


def _is_v0_family(arm: object) -> bool:
    """v0 control arms, including disclosed control re-run keys (e.g.
    v0-rerun): control evidence, never candidates."""
    return isinstance(arm, str) and (arm == "v0" or arm.startswith("v0-"))


def aggregate_counts(arm_data: dict | None, markers: dict) -> dict:
    """Per-marker property frequency for one arm: the arm's total
    marker-matching answer lines over its total answer lines across its
    runs (frequency = matching lines / answer lines, per the adoption
    rule). Runs without answer text contribute no lines; an arm with
    zero answer lines has frequency 0.0 (no evidence of the property)."""
    runs = arm_data.get("runs") if isinstance(arm_data, dict) else None
    runs = runs if isinstance(runs, list) else []
    matching = {name: 0 for name in markers}
    total_lines = 0
    for run in runs:
        if not isinstance(run, dict):
            continue
        answer = run.get("answer_text")
        answer = answer if isinstance(answer, str) else ""
        for name, n in marker_triage_counts(answer, markers).items():
            matching[name] += n
        total_lines += len(answer.splitlines())
    if total_lines == 0:
        return {name: 0.0 for name in markers}
    return {name: matching[name] / total_lines for name in markers}


def _print_shape_compare(eid: str, arms: dict, markers: dict) -> None:
    """--compare: per-marker property-frequency verdict of each candidate
    arm against the v0 control. The adoption rule hinges on the strict >
    on the normalized frequency: equal frequency means the rule is not
    binding. A missing v0 control skips the comparison with a note —
    there is nothing to beat, and comparing against an empty base would
    manufacture EXCEEDS verdicts from no control evidence."""
    if "v0" not in arms:
        print(f"compare: entry {eid}: no v0 control arm; comparison skipped")
        return
    base = aggregate_counts(arms.get("v0"), markers)
    for arm in arms:
        if _is_v0_family(arm):
            continue  # control re-runs (e.g. v0-rerun) are control
        # evidence, not candidates
        cand = aggregate_counts(arms[arm], markers)
        for name in markers:
            b, c = base.get(name, 0), cand.get(name, 0)
            verdict = "EXCEEDS" if c > b else "does-not-exceed"
            print(f"compare {name}: {arm} {c} vs v0 {b} -> {verdict}")


def cmd_shape_evidence(args: argparse.Namespace) -> int:
    """Print the per-run scoring evidence from a shape-suite results JSON:
    per entry/arm/rep the answer text, void signals, session id, and
    marker triage counts (markers are carried in the results entries, so
    no entries-file re-read is needed). Extraction only — the driver
    judges convergence across the reps by hand. Exit 0 with an entry
    count line; exit 1 only on a malformed file or unknown --entry."""
    path = Path(args.results)
    data_entries, error = load_results_json(path, "shape")
    if error is not None:
        print(f"error: {error}", file=sys.stderr)
        return 1

    n_printed = 0
    try:
        for eid, entry in iter_evidence(data_entries, path, args.entry):
            arms = entry.get("arms")
            if not isinstance(arms, dict):
                print(
                    f"error: {path}: entry {eid} is missing its 'arms' object",
                    file=sys.stderr,
                )
                return 1
            markers = entry.get("markers")
            markers = markers if isinstance(markers, dict) else {}
            restraint = entry.get("restraint_markers")
            restraint = restraint if isinstance(restraint, dict) else {}

            print(f"## {eid} ({entry.get('kind', '?')})")
            for arm in arms:
                if args.arm is not None and arm != args.arm:
                    continue
                arm_data = arms[arm]
                if not isinstance(arm_data, dict) or not isinstance(
                    arm_data.get("runs"), list
                ):
                    print(
                        f"error: {path}: entry {eid} arm {arm!r} is "
                        f"missing its run list",
                        file=sys.stderr,
                    )
                    return 1
                for n, run in enumerate(arm_data["runs"], start=1):
                    if not isinstance(run, dict):
                        print(
                            f"error: {path}: entry {eid} arm {arm!r} "
                            f"run {n} is not an object",
                            file=sys.stderr,
                        )
                        return 1
                    timeout = "timeout" if run.get("timeout") else "ok"
                    session = run.get("session_id") or "no-session"
                    print(f"[ {arm} ] rep {n:>3} ({session}, {timeout})")
                    answer = run.get("answer_text")
                    answer = answer if isinstance(answer, str) else ""
                    if answer:
                        print("answer:")
                        for line in answer.splitlines():
                            print(f"  {line}")
                    else:
                        print("answer: (empty)")
                    signals = run.get("void_signals") or []
                    joined = ", ".join(signals) if signals else "none"
                    print(f"void signals: {joined}")
                    counts = marker_triage_counts(answer, markers)
                    print(
                        "markers: "
                        + ", ".join(f"{k}={v}" for k, v in counts.items())
                    )
                    if restraint:
                        rcounts = marker_triage_counts(answer, restraint)
                        print(
                            "restraint markers: "
                            + ", ".join(f"{k}={v}" for k, v in rcounts.items())
                        )
                    print()
            if args.compare:
                _print_shape_compare(eid, arms, markers)
            n_printed += 1
    except EvidenceError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    if args.entry is not None and n_printed == 0:
        print(f"error: no entry with id: {args.entry}", file=sys.stderr)
        return 1
    print(f"evidence: {n_printed} entries from {path}")
    return 0


def cmd_shape_scored_check(args: argparse.Namespace) -> int:
    """Validate scored.json against the shape-suite result files it claims
    to cover (repeated --results: one file for a phase-1-only campaign,
    several for control + variants + restraint phases). Entry-id coverage
    is union with dedupe: an id appearing in N result files is scored
    exactly once, and every union id must be covered. Beyond the schema:
    adopted_arm must name a non-v0 arm present in that entry's results,
    the restraint_gate rule applies to adopted pattern entries, and the
    record-step counts (--adopted/--no-failure/--unresolved/--voids) must
    be     given all together and match the scored sums. With --emit-skeleton
    PATH instead of --scored, writes a scored.json skeleton (every
    results id once, kind and per-arm marker_counts pre-filled,
    judgment fields null) and exits 0."""
    gate = _scored_target_gate(args)
    if gate is not None:
        return gate
    union = union_results(args.results, "shape", entry_hook=_shape_union_hook)
    if isinstance(union, str):
        return _err(union)
    results_ids, results_arms, extras = union
    results_kinds = extras.get("kinds", {})

    if getattr(args, "emit_skeleton", None) is not None:
        return _emit_scored_skeleton_cmd(
            "shape", args.results, results_ids, extras, args
        )

    scored_path = Path(args.scored)
    scored_entries = load_scored_json(scored_path)
    if isinstance(scored_entries, str):
        return _err(scored_entries)
    covered_entries = check_coverage(scored_entries, results_ids, scored_path)
    if isinstance(covered_entries, str):
        return _err(covered_entries)

    for entry in covered_entries:
        eid = entry["id"]
        kind = entry.get("kind")
        if kind != results_kinds[eid]:
            return _err(
                f"{scored_path}: entry {eid}: kind {kind!r} does not "
                f"match the results kind {results_kinds[eid]!r}"
            )

        result = entry.get("result")
        if result not in SHAPE_RESULTS:
            return _err(
                f"{scored_path}: entry {eid}: result must be one of "
                f"{sorted(SHAPE_RESULTS)}, got {result!r}"
            )
        adopted_arm = entry.get("adopted_arm")
        if result == "adopted":
            if not isinstance(adopted_arm, str) or not adopted_arm:
                return _err(
                    f"{scored_path}: entry {eid}: adopted_arm required "
                    f"(non-empty string) for result 'adopted'"
                )
            if _is_v0_family(adopted_arm):
                return _err(
                    f"{scored_path}: entry {eid}: adopted_arm must "
                    f"not be a v0 control-family arm (including "
                    f"disclosed re-run keys like v0-rerun; a "
                    f"control-family arm is measurement evidence, "
                    f"never a candidate)"
                )
            if adopted_arm not in results_arms[eid]:
                return _err(
                    f"{scored_path}: entry {eid}: adopted_arm "
                    f"{adopted_arm!r} is not an arm present in this "
                    f"entry's results "
                    f"({', '.join(sorted(results_arms[eid]))})"
                )
        elif adopted_arm is not None:
            return _err(
                f"{scored_path}: entry {eid}: adopted_arm is only valid "
                f"with result 'adopted'"
            )

        gate = entry.get("restraint_gate")
        gate_required = kind == "pattern" and result == "adopted"
        if gate_required:
            if gate not in SHAPE_GATES:
                return _err(
                    f"{scored_path}: entry {eid}: restraint_gate must be "
                    f"one of {sorted(SHAPE_GATES)}, got {gate!r} "
                    f"(required for adopted pattern entries)"
                )
        elif gate is not None:
            return _err(
                f"{scored_path}: entry {eid}: restraint_gate is only "
                f"valid for adopted pattern entries"
            )

        marker_counts = entry.get("marker_counts")
        if marker_counts is not None and not isinstance(marker_counts, dict):
            return _err(
                f"{scored_path}: entry {eid}: marker_counts must be an "
                f"object keyed by arm"
            )
        notes = entry.get("notes")
        if notes is not None and not isinstance(notes, str):
            return _err(f"{scored_path}: entry {eid}: notes must be a string")

    rc = counts_gate(
        args,
        covered_entries,
        ("adopted", "no_failure", "unresolved", "voids"),
        ("adopted", "no-failure", "unresolved", "void"),
    )
    if rc is not None:
        return rc
    print(f"ok: {scored_path} covers {len(results_ids)} entries")
    return 0


# --------------------------------------------------------------------------
# Pressure campaign tooling: pressure-suite + pressure-evidence +
# pressure-meta + pressure-scored-check

# Vocabularies for the pressure track (plan §File schemas / §Scoring
# artifacts). PRESSURE_TYPES is the fixed pressure taxonomy every
# scenario's 'pressures' list draws from.
PRESSURE_TYPES = {
    "time",
    "sunk-cost",
    "authority",
    "economic",
    "exhaustion",
    "social",
    "pragmatic",
}
PRESSURE_RESULTS = {"bulletproof", "no-failure", "unresolved", "void"}
PRESSURE_ARMS = {"red", "green"}

# Per-run prompt assembly. The per-run prompt never contains the rule
# statement, the compliant option, or any hint that this is a test; the
# answer contract lives in the agent body, constant across arms. The
# green arm injects the snapshotted skill body (frontmatter already
# stripped by the driver) as "Project conventions".
PRESSURE_GREEN_TEMPLATE = """\
Project conventions:
{skill_text}

If any convention influenced your choice, cite it by section name.

Scenario: {scenario}"""

PRESSURE_RED_TEMPLATE = """\
Scenario: {scenario}"""

# Log label per pressure arm, padded to equal width, used as a [tag]
# prefix on every progress line: "[ red ]" / "[green ]".
PRESSURE_ARM_TAGS = {"red": " red ", "green": "green"}


def load_pressure_scenarios(path: Path) -> list[dict]:
    """Read and strictly validate a pressure scenarios file. On any
    violation prints `error: <exact reason>` to stderr and exits 1
    (pre-spend: zero harness runs happen before this returns)."""
    return load_entries(path, "scenarios", "scenario", _check_pressure_fields)


def _check_pressure_fields(path: Path, i: int, entry: dict, eid: str) -> None:
    """Per-field checks for a pressure scenario: rule, statement,
    scenario, the pressures taxonomy list, and the compliant option."""
    rule = entry.get("rule")
    if not isinstance(rule, str) or not rule:
        _fail(
            f"{path}: entry {i} ({eid}) missing 'rule' " f"(non-empty string)"
        )
    statement = entry.get("statement")
    if not isinstance(statement, str) or not statement:
        _fail(
            f"{path}: entry {i} ({eid}) missing 'statement' "
            f"(non-empty string)"
        )
    scenario = entry.get("scenario")
    if not isinstance(scenario, str) or not scenario:
        _fail(
            f"{path}: entry {i} ({eid}) missing 'scenario' "
            f"(non-empty string)"
        )
    pressures = entry.get("pressures")
    if (
        not isinstance(pressures, list)
        or len(pressures) < 3
        or not all(isinstance(p, str) and p for p in pressures)
        or len(set(pressures)) != len(pressures)
    ):
        _fail(
            f"{path}: entry {i} ({eid}) 'pressures' must be a list of "
            f"at least 3 distinct non-empty strings"
        )
    unknown = [p for p in pressures if p not in PRESSURE_TYPES]
    if unknown:
        _fail(
            f"{path}: entry {i} ({eid}) pressures not in the "
            f"taxonomy: {', '.join(unknown)} (allowed: "
            f"{', '.join(sorted(PRESSURE_TYPES))})"
        )
    compliant = entry.get("compliant_option")
    if not isinstance(compliant, str) or not compliant:
        _fail(
            f"{path}: entry {i} ({eid}) missing 'compliant_option' "
            f"(non-empty string)"
        )


def build_pressure_prompt(
    entry: dict, arm: str, skill_text: str | None
) -> str:
    """One rep's prompt bytes. Red arms dispatch the bare scenario; green
    arms inject the skill body as "Project conventions" and ask for a
    section citation. Never contains the rule statement, the compliant
    option, or any hint that this is a test."""
    if arm == "green":
        return PRESSURE_GREEN_TEMPLATE.format(
            skill_text=skill_text or "", scenario=entry["scenario"]
        )
    return PRESSURE_RED_TEMPLATE.format(scenario=entry["scenario"])


def _pressure_void_signals(ev) -> list[str]:
    """A pressure rep needs zero tool calls — the answer is the entire
    task — so any captured tool call or skill load is a void signal.
    timeout stays a separate boolean, never a void signal."""
    signals = []
    if not "".join(ev.answer_parts).strip():
        signals.append("empty-answer")
    if ev.tool_calls or ev.skill_loads:
        signals.append("tool-call-attempted")
    return signals


def build_pressure_run_record(
    ev,
    prompt: str,
    timed_out: bool,
    arm: str,
) -> dict:
    """The pressure-track run record. Unlike the retrieval/shape builders
    it takes no ws_root: nothing is ever synced or written on this track,
    so no outside-workspace read is possible."""
    return {
        "arm": arm,
        "query_dispatched": prompt,
        "answer_text": "".join(ev.answer_parts),
        "tool_calls": ev.tool_calls,
        "reasoning": "".join(ev.reasoning_parts),
        "session_id": ev.session_id,
        "timeout": timed_out,
        "parseable_events": ev.parseable,
        "void_signals": _pressure_void_signals(ev),
    }


def run_pressure_rep_batch(
    strategy: EvalStrategy,
    entry: dict,
    arm: str,
    ws: Path,
    agent: str,
    args: argparse.Namespace,
    skill_text: str | None,
) -> list[dict]:
    """Reps for one (entry, arm) pair. Every rep shares identical prompt
    bytes; per-rep scheduling lives in run_rep_batched."""
    prompt = build_pressure_prompt(entry, arm, skill_text)
    tag = PRESSURE_ARM_TAGS[arm]

    def run_rep(n: int) -> dict:
        log_start(n, tag)
        ev, timed_out = strategy.execute(
            ws,
            agent,
            prompt,
            args.model,
            args.variant,
        )
        record = build_pressure_run_record(ev, prompt, timed_out, arm)
        line = f"[{tag}] [rep {n:>3}] completed"
        if timed_out:
            line += " (timeout)"
        if record["void_signals"]:
            line += f" signals: {', '.join(record['void_signals'])}"
        emit(line)
        return record

    return run_rep_batched(run_rep, args.reps, tag)


def cmd_pressure_suite(args: argparse.Namespace) -> int:
    """Run one pressure arm for a scenarios file: entries x the single
    given arm x reps headless runs. The workspace is never synced and
    never written; arms differ only in prompt bytes. Pre-spend validation
    exits 1 with an exact message before any harness invocation."""
    strategy_cls = resolve_strategy(args.harness)
    check_harness(args.harness, strategy_cls, args.model)  # binary + model
    ws = Path(args.workspace)
    agents_dir = Path(args.agents_dir)
    scenarios_path = Path(args.scenarios)

    # ---- pre-spend validation: any failure exits 1, exact message ----
    probe = strategy_cls(timeout=args.timeout)
    validate_eval_agent(probe, agents_dir, PRESSURE_EVALUATOR_AGENT)
    if args.arm not in PRESSURE_ARMS:
        _fail(
            f"--arm must be one of {', '.join(sorted(PRESSURE_ARMS))}, "
            f"got {args.arm!r}"
        )
    if args.arm == "green" and args.skill_file is None:
        _fail("--skill-file is required with --arm green")
    if args.arm == "red" and args.skill_file is not None:
        _fail("--skill-file is only valid with --arm green")
    skill_text = None
    if args.arm == "green":
        if args.skill_file is None:  # gated above; keeps the type narrow
            _fail("--skill-file is required with --arm green")
        skill_file = Path(args.skill_file)
        if not skill_file.is_file():
            _fail(f"skill file not found: {skill_file}")
        skill_text = skill_file.read_text()
        if not skill_text.strip():
            _fail(f"skill file is empty: {skill_file}")

    entries = load_pressure_scenarios(scenarios_path)  # exits 1 on violation
    if args.reps < 1:
        _fail("--reps must be >= 1")
    if args.timeout < 1:
        _fail("--timeout must be >= 1")
    out = Path(args.out)
    if not out.parent.is_dir():
        _fail(f"output directory does not exist: {out.parent}")
    if (ws / ".agents" / "skills" / args.skill).exists():
        _fail(
            f"workspace contains skill '{args.skill}' — this track injects "
            "the skill body into prompts and never syncs; recreate the "
            "workspace, never sync"
        )

    # ---- install + run ----
    _Log.file = out.with_suffix(".log").open("w")  # mirror like suite
    strategy = strategy_cls(timeout=args.timeout)
    strategy.install(ws, agents_dir, PRESSURE_EVALUATOR_AGENT)

    emit(
        f"pressure test suite: {args.skill} ({len(entries)} scenarios, "
        f"{args.arm} arm)"
    )
    emit(f"workspace: {ws}")
    emit(
        f"harness: {args.harness}  model: {args.model or '(default)'}  "
        f"variant: {args.variant or '(none)'}  reps: {args.reps}  "
        f"timeout: {args.timeout}s"
    )
    if args.skill_file is not None:
        emit(f"skill file: {args.skill_file}")

    results = []
    for i, entry in enumerate(entries, start=1):
        record = {
            "id": entry["id"],
            "statement": entry["statement"],
            "pressures": entry["pressures"],
            "compliant_option": entry["compliant_option"],
            "arms": {
                args.arm: {
                    "runs": run_pressure_rep_batch(
                        strategy,
                        entry,
                        args.arm,
                        ws,
                        PRESSURE_EVALUATOR_AGENT,
                        args,
                        skill_text,
                    )
                }
            },
        }
        results.append(record)
        emit(f"[{i}/{len(entries)}] {entry['id']}")

    config = base_config(args)
    config["scenarios"] = str(scenarios_path)
    config["arm"] = args.arm
    if args.skill_file is not None:
        config["skill_file"] = args.skill_file
    write_results(out, config, results)
    emit(f"pressure suite: {len(entries)} entries -> {out}")
    return 0


def cmd_pressure_evidence(args: argparse.Namespace) -> int:
    """Print the per-run scoring evidence from a pressure-suite results
    JSON: per entry the statement, pressures, and compliant option, and
    per arm/rep the full answer text, void signals, and session id. Never
    extracts the choice letter — the driver reads every answer and judges
    choice + citation by hand. Exit 0 with an entry count line; exit 1
    only on a malformed file or unknown --entry."""
    path = Path(args.results)
    data_entries, error = load_results_json(path, "pressure")
    if error is not None:
        print(f"error: {error}", file=sys.stderr)
        return 1

    n_printed = 0
    try:
        for eid, entry in iter_evidence(data_entries, path, args.entry):
            arms = entry.get("arms")
            if not isinstance(arms, dict):
                print(
                    f"error: {path}: entry {eid} is missing its 'arms' object",
                    file=sys.stderr,
                )
                return 1

            print(f"## {eid}")
            statement = entry.get("statement")
            if isinstance(statement, str) and statement:
                print(f"statement: {statement}")
            pressures = entry.get("pressures")
            if isinstance(pressures, list) and pressures:
                print(f"pressures: {', '.join(str(p) for p in pressures)}")
            print(f"compliant_option: {entry.get('compliant_option', '?')}")
            print()
            for arm in arms:
                if args.arm is not None and arm != args.arm:
                    continue
                arm_data = arms[arm]
                if not isinstance(arm_data, dict) or not isinstance(
                    arm_data.get("runs"), list
                ):
                    print(
                        f"error: {path}: entry {eid} arm {arm!r} is "
                        f"missing its run list",
                        file=sys.stderr,
                    )
                    return 1
                for n, run in enumerate(arm_data["runs"], start=1):
                    if not isinstance(run, dict):
                        print(
                            f"error: {path}: entry {eid} arm {arm!r} "
                            f"run {n} is not an object",
                            file=sys.stderr,
                        )
                        return 1
                    timeout = "timeout" if run.get("timeout") else "ok"
                    session = run.get("session_id") or "no-session"
                    tag = PRESSURE_ARM_TAGS.get(arm, f" {arm} ")
                    print(f"[{tag}] rep {n:>3} ({session}, {timeout})")
                    answer = run.get("answer_text")
                    answer = answer if isinstance(answer, str) else ""
                    if answer:
                        print("answer:")
                        for line in answer.splitlines():
                            print(f"  {line}")
                    else:
                        print("answer: (empty)")
                    signals = run.get("void_signals") or []
                    joined = ", ".join(signals) if signals else "none"
                    print(f"void signals: {joined}")
                    print()
            n_printed += 1
    except EvidenceError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    if args.entry is not None and n_printed == 0:
        print(f"error: no entry with id: {args.entry}", file=sys.stderr)
        return 1
    print(f"evidence: {n_printed} entries from {path}")
    return 0


def cmd_pressure_meta(args: argparse.Namespace) -> int:
    """Resume one violating rep's session with the meta question and write
    the reply JSON. The agent is re-installed idempotently (re-running the
    frontmatter assertions); the driver passes the same --model/--variant
    as the original suite run. HarnessExecutionError from a dead session
    follows the house policy: stderr with the [session <id>] suffix, exit
    1, no JSON."""
    strategy_cls = resolve_strategy(args.harness)
    check_harness(args.harness, strategy_cls)  # binary only
    ws = Path(args.workspace)
    agents_dir = Path(args.agents_dir)
    if not args.session:
        _fail("--session must be a non-empty session id")
    out = Path(args.out)
    if not out.parent.is_dir():
        _fail(f"output directory does not exist: {out.parent}")

    strategy = strategy_cls(timeout=args.timeout)
    strategy.install(ws, agents_dir, PRESSURE_EVALUATOR_AGENT)

    try:
        ev, timed_out = strategy.execute(
            ws,
            PRESSURE_EVALUATOR_AGENT,
            args.question,
            args.model,
            args.variant,
            session=args.session,
        )
    except HarnessExecutionError as e:
        emit(
            f"error: harness could not resume the session: {e}"
            f"{_session_suffix(e)}",
            err=True,
        )
        return 1

    payload = {
        "session_id": args.session,
        "question": args.question,
        "answer_text": "".join(ev.answer_parts),
        "timeout": timed_out,
        "void_signals": _pressure_void_signals(ev),
    }
    out.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"meta: session {args.session} -> {out}")
    return 0


def cmd_pressure_scored_check(args: argparse.Namespace) -> int:
    """Validate scored.json against the pressure-suite result files it
    claims to cover (repeated --results: red file, green files, refactor
    rounds). Entry-id coverage is union with dedupe: an id appearing in N
    result files is scored exactly once, and every union id must be
    covered. Beyond the schema: every entry must have a "red" arm in the
    results union (RED always runs first), no-failure and void entries
    must have no "green" arm, bulletproof and unresolved entries must
    have one, and the record-step counts (--bulletproof/--no-failure/
    --unresolved/--voids) must be given all together and match the scored
    sums. With --emit-skeleton PATH instead of --scored, writes a
    scored.json skeleton (every results id once, a verdict_constraint
    hint derived from the red/green arm union, judgment fields null)
    and exits 0."""
    gate = _scored_target_gate(args)
    if gate is not None:
        return gate
    union = union_results(
        args.results, "pressure", entry_hook=_pressure_union_hook
    )
    if isinstance(union, str):
        return _err(union)
    results_ids, results_arms, extras = union

    if getattr(args, "emit_skeleton", None) is not None:
        extras["arms"] = results_arms
        return _emit_scored_skeleton_cmd(
            "pressure", args.results, results_ids, extras, args
        )

    scored_path = Path(args.scored)
    scored_entries = load_scored_json(scored_path, "an object")
    if isinstance(scored_entries, str):
        return _err(scored_entries)
    covered_entries = check_coverage(scored_entries, results_ids, scored_path)
    if isinstance(covered_entries, str):
        return _err(covered_entries)

    for entry in covered_entries:
        eid = entry["id"]
        arms = results_arms[eid]
        result = entry.get("result")
        if result not in PRESSURE_RESULTS:
            return _err(
                f"{scored_path}: entry {eid}: result must be one of "
                f"{sorted(PRESSURE_RESULTS)}, got {result!r}"
            )
        if "red" not in arms:
            return _err(
                f"{scored_path}: entry {eid}: no 'red' arm in the results "
                f"union (RED always runs first; a rule with no red arm was "
                f"never baselined)"
            )
        if result in ("no-failure", "void") and "green" in arms:
            return _err(
                f"{scored_path}: entry {eid}: result {result!r} must have "
                f"no 'green' arm in the results union (baseline complied "
                f"or was unmeasurable; nothing else may have run)"
            )
        if result in ("bulletproof", "unresolved") and "green" not in arms:
            return _err(
                f"{scored_path}: entry {eid}: result {result!r} requires "
                f"a 'green' arm in the results union"
            )

        counters = entry.get("counters")
        if counters is not None and (
            not isinstance(counters, list)
            or not all(isinstance(c, str) and c for c in counters)
        ):
            return _err(
                f"{scored_path}: entry {eid}: counters must be a list of "
                f"non-empty strings"
            )
        notes = entry.get("notes")
        if notes is not None and not isinstance(notes, str):
            return _err(f"{scored_path}: entry {eid}: notes must be a string")

    rc = counts_gate(
        args,
        covered_entries,
        ("bulletproof", "no_failure", "unresolved", "voids"),
        ("bulletproof", "no-failure", "unresolved", "void"),
    )
    if rc is not None:
        return rc
    print(f"ok: {scored_path} covers {len(results_ids)} entries")
    return 0


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
        return cmd_suite(args)
    if args.command == "record":
        return cmd_record(args)
    if args.command == "failures":
        return cmd_failures(args)
    if args.command == "retrieval-suite":
        return cmd_retrieval_suite(args)
    if args.command == "retrieval-evidence":
        return cmd_retrieval_evidence(args)
    if args.command == "scored-check":
        return cmd_scored_check(args)
    if args.command == "shape-suite":
        return cmd_shape_suite(args)
    if args.command == "shape-evidence":
        return cmd_shape_evidence(args)
    if args.command == "shape-scored-check":
        return cmd_shape_scored_check(args)
    if args.command == "pressure-suite":
        return cmd_pressure_suite(args)
    if args.command == "pressure-evidence":
        return cmd_pressure_evidence(args)
    if args.command == "pressure-meta":
        return cmd_pressure_meta(args)
    if args.command == "pressure-scored-check":
        return cmd_pressure_scored_check(args)
    if args.command == "inventory-check":
        return cmd_inventory_check(args)
    if args.command == "inventory-mint":
        return cmd_inventory_mint(args)
    if args.command == "inventory-diff":
        return cmd_inventory_diff(args)
    return cmd_run(args)


if __name__ == "__main__":
    sys.exit(main())
