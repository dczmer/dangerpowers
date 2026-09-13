#!/usr/bin/env python3
"""Evaluator: run one query (--expect trigger|not-trigger) for N reps against a
harness workspace and report whether the skill under test loaded.

Every rep runs under the restricted `trigger-evaluator` agent (skill tool only,
steps capped), installed into the workspace by the harness strategy before any
rep. Harness specifics live in the strategy registry in strategies.py; only
opencode is implemented.

Scope: the trigger inner core (eval_batch: one invocation = one query), the
retrieval campaign tooling (retrieval-suite, scored-check, record with
--scope frontmatter|dir), and the shape campaign tooling (shape-suite,
shape-evidence, shape-scored-check, record --track shape-test).
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
from typing import TextIO

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
    check_harness(args.harness, strategy_cls)
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
    check_harness(args.harness, strategy_cls)
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
    Overwrites only the scope's key (`trigger-test`, `retrieval-test`, or
    `shape-test` with --scope dir --track); unknown keys are preserved.
    --scope dir --track selects the count vocabulary: retrieval-test uses
    passes/fails/gaps/voids (the default, back-compatible), shape-test
    uses adopted/no-failure/unresolved/voids."""
    skill_path = Path(args.skill_path)
    scope = getattr(args, "scope", "frontmatter")

    if scope == "frontmatter":
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
        track = getattr(args, "track", "retrieval-test")
        if track == "shape-test":
            # voids is shared by both vocabularies; the retrieval-only
            # counts must not appear on a shape-test record.
            if any(
                getattr(args, n, None) is not None
                for n in ("passes", "fails", "gaps", "ablations")
            ):
                return _err(
                    "passes/fails/gaps/ablations are only valid with "
                    "--track retrieval-test"
                )
            missing = [
                n
                for n in ("adopted", "no_failure", "unresolved", "voids")
                if getattr(args, n, None) is None
            ]
            if missing:
                return _err(
                    "counts required with --scope dir --track shape-test: "
                    + ", ".join(missing)
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
        else:
            if any(
                getattr(args, n, None) is not None
                for n in ("adopted", "no_failure", "unresolved")
            ):
                return _err(
                    "adopted/no-failure/unresolved are only valid with "
                    "--track shape-test"
                )
            missing = [
                n
                for n in ("passes", "fails", "gaps", "voids")
                if getattr(args, n, None) is None
            ]
            if missing:
                return _err(
                    f"counts required with --scope dir: {', '.join(missing)}"
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
    elif getattr(args, "track", "retrieval-test") == "shape-test":
        detail = (
            f"{args.adopted} adopted / {args.no_failure} no-failure / "
            f"{args.unresolved} unresolved / {args.voids} void"
        )
    else:
        detail = (
            f"{args.passes} pass / {args.fails} fail / "
            f"{args.gaps} gap / {args.voids} void"
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
    if not path.exists():
        print(f"error: results file not found: {path}", file=sys.stderr)
        return 1
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        print(f"error: invalid JSON in {path}: {e}", file=sys.stderr)
        return 1
    if not isinstance(data, dict) or not isinstance(data.get("entries"), list):
        print(
            f"error: {path}: not a retrieval-suite results file "
            f"(missing 'entries' list)",
            file=sys.stderr,
        )
        return 1

    n_printed = 0
    for i, entry in enumerate(data["entries"]):
        if not isinstance(entry, dict):
            print(
                f"error: {path}: entry {i} is not an object", file=sys.stderr
            )
            return 1
        eid = entry.get("id")
        if not isinstance(eid, str) or not eid:
            print(
                f"error: {path}: entry {i} missing 'id' (non-empty string)",
                file=sys.stderr,
            )
            return 1
        if args.entry is not None and eid != args.entry:
            continue
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
                    f"[{ARM_TAGS[arm_key]}] rep {n:>3} ({session}, {timeout})"
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
                    f"tool calls: {', '.join(targets) if targets else 'none'}"
                )
                print()
        n_printed += 1

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
    if not path.exists():
        _fail(f"query file not found: {path}")
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        _fail(f"invalid JSON in {path}: {e}")
    if not isinstance(data, list):
        _fail(f"{path}: expected a JSON list of query objects")
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
        q = entry.get("query")
        if not isinstance(q, str) or not q:
            _fail(
                f"{path}: entry {i} ({eid}) missing 'query' "
                f"(non-empty string)"
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
        entries.append(entry)
    return entries


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
    runs: dict[int, dict] = {}

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

    # Smoke rep runs alone; a harness failure here aborts before further
    # spend. A timeout is a record, never an abort (design §7).
    try:
        runs[1] = run_rep(1)
    except HarnessExecutionError as e:
        emit(
            f"error: [{tag}] harness could not execute the query: {e}"
            f"{_session_suffix(e)}",
            err=True,
        )
        sys.exit(1)

    # Remaining reps in parallel batches of at most MAX_WORKERS.
    remaining = list(range(2, args.reps + 1))
    for i in range(0, len(remaining), MAX_WORKERS):
        group = remaining[i : i + MAX_WORKERS]
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            futures = {pool.submit(run_rep, n): n for n in group}
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

    return [runs[n] for n in range(1, args.reps + 1)]


def cmd_retrieval_suite(args: argparse.Namespace) -> int:
    """Run a retrieval campaign: every query × 2 arms × reps headless runs.
    Pre-spend validation exits 1 with an exact message before any harness
    invocation. HarnessExecutionError anywhere -> stderr, exit 1, no JSON,
    workspaces kept (trigger policy, unchanged)."""
    strategy_cls = resolve_strategy(args.harness)
    check_harness(args.harness, strategy_cls)  # binary only
    skill_ws = Path(args.skill_workspace)
    control_ws = Path(args.control_workspace)
    agents_dir = Path(args.agents_dir)
    queries_path = Path(args.queries)

    # ---- pre-spend validation: any failure exits 1, exact message ----
    probe = strategy_cls(timeout=args.timeout)
    for base in (RETRIEVAL_EVALUATOR_AGENT, RETRIEVAL_CONTROL_AGENT):
        f = probe.agent_file(agents_dir, base)
        if not f.exists():
            _fail(f"evaluator agent file missing: {f}")
        info = scan_agent_frontmatter(f)  # exits on bad frontmatter
        if info["name"] != base:
            _fail(
                f"agent file {f}: frontmatter name "
                f"'{info['name']}' does not match expected '{base}'"
            )
        if info["pins"]:
            _fail(
                f"agent file {f} pins model config "
                f"({', '.join(info['pins'])}); eval agents must not pin "
                "model/variant/temperature/top_p — selection flows "
                "through --model/--variant only"
            )
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
    out.write_text(
        json.dumps(
            {
                "config": {
                    "skill": args.skill,
                    "harness": args.harness,
                    "model": args.model,
                    "variant": args.variant,
                    "reps": args.reps,
                    "timeout": args.timeout,
                    "date": datetime.now(UTC).date().isoformat(),
                    "queries": str(queries_path),
                },
                "entries": results,
            },
            indent=2,
        )
        + "\n"
    )
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
    must match the scored sums."""
    results_path = Path(args.results)
    scored_path = Path(args.scored)
    if not results_path.exists():
        return _err(f"results file not found: {results_path}")
    try:
        results = json.loads(results_path.read_text())
    except json.JSONDecodeError as e:
        return _err(f"invalid JSON in {results_path}: {e}")
    if not isinstance(results, dict) or not isinstance(
        results.get("entries"), list
    ):
        return _err(
            f"{results_path}: not a retrieval-suite results file "
            f"(missing 'entries' list)"
        )
    results_ids: list[str] = []
    results_expect: dict[str, list[str]] = {}
    for i, e in enumerate(results["entries"]):
        eid = e.get("id") if isinstance(e, dict) else None
        if not isinstance(eid, str) or not eid:
            return _err(
                f"{results_path}: results entry {i} missing 'id' "
                f"(non-empty string)"
            )
        results_ids.append(eid)
        expect = e.get("expect") if isinstance(e, dict) else None
        results_expect[eid] = expect if isinstance(expect, list) else []

    if not scored_path.exists():
        return _err(f"scored file not found: {scored_path}")
    try:
        scored = json.loads(scored_path.read_text())
    except json.JSONDecodeError as e:
        return _err(f"invalid JSON in {scored_path}: {e}")
    if not isinstance(scored, dict) or not isinstance(
        scored.get("entries"), list
    ):
        return _err(
            f"{scored_path}: expected a JSON object with an 'entries' list"
        )

    covered: set[str] = set()
    for i, entry in enumerate(scored["entries"]):
        if not isinstance(entry, dict):
            return _err(f"{scored_path}: entry {i} is not an object")
        eid = entry.get("id")
        if not isinstance(eid, str) or not eid:
            return _err(
                f"{scored_path}: entry {i} missing 'id' (non-empty string)"
            )
        if eid in covered:
            return _err(f"{scored_path}: duplicate id: {eid}")
        if eid not in results_ids:
            return _err(f"{scored_path}: unknown id: {eid}")
        covered.add(eid)

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

    missing = [eid for eid in results_ids if eid not in covered]
    if missing:
        return _err(
            f"{scored_path}: missing scored entries for results ids: "
            f"{', '.join(missing)}"
        )

    # Optional count gate: when the record-step counts are given, they
    # must equal what the scored entries actually sum to.
    given = [
        getattr(args, n, None) for n in ("passes", "fails", "gaps", "voids")
    ]
    if any(c is not None for c in given):
        if not all(c is not None for c in given):
            return _err(
                "--passes/--fails/--gaps/--voids must be given together"
            )
        computed = {
            r: sum(1 for e in scored["entries"] if e.get("result") == r)
            for r in ("pass", "fail", "gap", "void")
        }
        if tuple(given) != tuple(computed[r] for r in computed):
            return _err(
                f"counts do not match scored results: computed "
                f"{computed['pass']} pass / {computed['fail']} fail / "
                f"{computed['gap']} gap / {computed['void']} void, got "
                f"{given[0]} pass / {given[1]} fail / {given[2]} gap / "
                f"{given[3]} void"
            )
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
    verbatim section-span assertion against the synced skill body lives in
    cmd_shape_suite, which owns the body bytes. On any violation prints
    `error: <exact reason>` to stderr and exits 1 (pre-spend: zero harness
    runs happen before this returns)."""
    if not path.exists():
        _fail(f"entries file not found: {path}")
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        _fail(f"invalid JSON in {path}: {e}")
    if not isinstance(data, list):
        _fail(f"{path}: expected a JSON list of entry objects")
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
        has_counter = isinstance(
            fixtures.get("counter-example"), str
        ) and bool(fixtures.get("counter-example"))
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
        if not all(
            isinstance(t, str) and t for t in markers.values()
        ) or not all(isinstance(k, str) and k for k in markers):
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
        entries.append(entry)
    return entries


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
            rest = rest[1:]  # consume exactly one following blank line
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
    skill: str,
) -> dict:
    """The shape-track run record: build_run_record adapted, not reused,
    because that builder keys its signals on the retrieval arm names.
    Every shape arm loads the skill, so skill-not-loaded fires for any arm
    without a completed load; the retrieval track's control-loaded-skill
    signal does not exist here. Adds the arm key so runs stay attributable
    in the merged results of a phase."""
    answer = "".join(ev.answer_parts)
    m = SOURCES_RE.search(answer)
    signals = []
    if not ev.completed_load:
        signals.append("skill-not-loaded")
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


def run_shape_rep_batch(
    strategy: EvalStrategy,
    entry: dict,
    arm: str,
    ws: Path,
    agent: str,
    args: argparse.Namespace,
) -> list[dict]:
    """Reps for one (entry, arm) pair, dispatched only while the workspace
    skill carries that arm's byte state. The per-run prompt is the bare
    fixture text keyed by --fixture-key — never rule text, markers, or
    expected shape. The smoke rep runs alone; remaining reps batch at most
    MAX_WORKERS wide. Only reps within one arm batch parallelize: entries x
    arms are strictly serialized by cmd_shape_suite (the multi-rule
    attribution invariant)."""
    fixture_text = entry["fixtures"][args.fixture_key]
    tag = f" {arm} "
    runs: dict[int, dict] = {}

    def run_rep(n: int) -> dict:
        log_start(n, tag)
        ev, timed_out = strategy.execute(
            ws,
            agent,
            fixture_text,
            args.model,
            args.variant,
            skill=args.skill,
        )
        record = build_shape_run_record(
            ev, fixture_text, timed_out, ws, arm, args.skill
        )
        line = f"[{tag}] [rep {n:>3}] completed"
        if timed_out:
            line += " (timeout)"
        if record["void_signals"]:
            line += f" signals: {', '.join(record['void_signals'])}"
        emit(line)
        return record

    # Smoke rep runs alone; a harness failure here aborts before further
    # spend. A timeout is a record, never an abort (retrieval policy).
    try:
        runs[1] = run_rep(1)
    except HarnessExecutionError as e:
        emit(
            f"error: [{tag}] harness could not execute the query: {e}"
            f"{_session_suffix(e)}",
            err=True,
        )
        sys.exit(1)

    remaining = list(range(2, args.reps + 1))
    for i in range(0, len(remaining), MAX_WORKERS):
        group = remaining[i : i + MAX_WORKERS]
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            futures = {pool.submit(run_rep, n): n for n in group}
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

    return [runs[n] for n in range(1, args.reps + 1)]


def cmd_shape_suite(args: argparse.Namespace) -> int:
    """Run one shape campaign phase: entries x arms x reps headless runs,
    STRICTLY serialized per entry x arm — never the retrieval track's
    arm-parallel structure. At any moment the workspace skill differs
    from the intact synced skill by exactly one rule's section (the
    multi-rule attribution invariant); the original synced bytes are
    restored after each arm and on abort. Pre-spend validation exits 1
    with an exact message before any harness invocation."""
    strategy_cls = resolve_strategy(args.harness)
    check_harness(args.harness, strategy_cls)  # binary only
    ws = Path(args.workspace)
    agents_dir = Path(args.agents_dir)
    entries_path = Path(args.entries)

    # ---- pre-spend validation: any failure exits 1, exact message ----
    probe = strategy_cls(timeout=args.timeout)
    agent_file = probe.agent_file(agents_dir, SHAPE_EVALUATOR_AGENT)
    if not agent_file.exists():
        _fail(f"evaluator agent file missing: {agent_file}")
    info = scan_agent_frontmatter(agent_file)  # exits on bad frontmatter
    if info["name"] != SHAPE_EVALUATOR_AGENT:
        _fail(
            f"agent file {agent_file}: frontmatter name "
            f"'{info['name']}' does not match expected "
            f"'{SHAPE_EVALUATOR_AGENT}'"
        )
    if info["pins"]:
        _fail(
            f"agent file {agent_file} pins model config "
            f"({', '.join(info['pins'])}); eval agents must not pin "
            "model/variant/temperature/top_p — selection flows "
            "through --model/--variant only"
        )
    if args.reps < 1:
        _fail("--reps must be >= 1")
    if args.timeout < 1:
        _fail("--timeout must be >= 1")

    skill_md = ws / ".agents" / "skills" / args.skill / "SKILL.md"
    if not skill_md.is_file():
        _fail(
            f"skill workspace has no synced skill '{args.skill}': run "
            "workspace-manager.sh sync --full and status --full first"
        )

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
    # in the synced body (frontmatter stripped — spans overlapping
    # frontmatter are never matched). Aborts before spend.
    original_text = skill_md.read_text()
    frontmatter = extract_frontmatter(original_text)
    body = (
        original_text[len(frontmatter) :]
        if frontmatter is not None
        else original_text
    )
    for entry in entries:
        occurrences = body.count(entry["section"])
        if occurrences != 1:
            _fail(
                f"doc drift: section span of entry {entry['id']!r} occurs "
                f"{occurrences} times in the synced skill body (expected "
                f"exactly once); fix the entry or re-sync"
            )

    out = Path(args.out)
    if not out.parent.is_dir():
        _fail(f"output directory does not exist: {out.parent}")

    # ---- install + run ----
    _Log.file = out.with_suffix(".log").open("w")  # mirror like suite
    strategy = strategy_cls(timeout=args.timeout)
    strategy.install(
        ws,
        agents_dir,
        SHAPE_EVALUATOR_AGENT,
        skill_name=args.skill,
    )  # {{SKILL_NAME}}

    emit(f"shape test suite: {args.skill} ({len(entries)} entries)")
    emit(f"workspace: {ws}")
    emit(
        f"harness: {args.harness}  model: {args.model or '(default)'}  "
        f"variant: {args.variant or '(none)'}  reps: {args.reps}  "
        f"timeout: {args.timeout}s"
    )
    emit(f"arms: {', '.join(arms)}  fixture-key: {args.fixture_key}")

    results = []
    try:
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
                    new_body = assemble_arm_body(body, entry, arm)
                    verify_arm_bytes(new_body, entry, arm)
                except ValueError as e:
                    _fail(str(e))
                skill_md.write_text((frontmatter or "") + new_body)
                record["arms"][arm] = {
                    "runs": run_shape_rep_batch(
                        strategy, entry, arm, ws, SHAPE_EVALUATOR_AGENT, args
                    )
                }
                # Restore the synced bytes before the next arm.
                skill_md.write_text(original_text)
            results.append(record)
            emit(f"[{i}/{len(entries)}] {entry['id']}")
    finally:
        # Restore on completion AND on abort: the workspace must never be
        # left carrying a variant byte state.
        skill_md.write_text(original_text)

    out.write_text(
        json.dumps(
            {
                "config": {
                    "skill": args.skill,
                    "harness": args.harness,
                    "model": args.model,
                    "variant": args.variant,
                    "reps": args.reps,
                    "timeout": args.timeout,
                    "date": datetime.now(UTC).date().isoformat(),
                    "entries": str(entries_path),
                    "arms": arms,
                    "fixture_key": args.fixture_key,
                },
                "entries": results,
            },
            indent=2,
        )
        + "\n"
    )
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


def cmd_shape_evidence(args: argparse.Namespace) -> int:
    """Print the per-run scoring evidence from a shape-suite results JSON:
    per entry/arm/rep the answer text, void signals, session id, and
    marker triage counts (markers are carried in the results entries, so
    no entries-file re-read is needed). Extraction only — the driver
    judges convergence across the reps by hand. Exit 0 with an entry
    count line; exit 1 only on a malformed file or unknown --entry."""
    path = Path(args.results)
    if not path.exists():
        print(f"error: results file not found: {path}", file=sys.stderr)
        return 1
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        print(f"error: invalid JSON in {path}: {e}", file=sys.stderr)
        return 1
    if not isinstance(data, dict) or not isinstance(data.get("entries"), list):
        print(
            f"error: {path}: not a shape-suite results file "
            f"(missing 'entries' list)",
            file=sys.stderr,
        )
        return 1

    n_printed = 0
    for i, entry in enumerate(data["entries"]):
        if not isinstance(entry, dict):
            print(
                f"error: {path}: entry {i} is not an object", file=sys.stderr
            )
            return 1
        eid = entry.get("id")
        if not isinstance(eid, str) or not eid:
            print(
                f"error: {path}: entry {i} missing 'id' (non-empty string)",
                file=sys.stderr,
            )
            return 1
        if args.entry is not None and eid != args.entry:
            continue
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
                    f"error: {path}: entry {eid} arm {arm!r} is missing "
                    f"its run list",
                    file=sys.stderr,
                )
                return 1
            for n, run in enumerate(arm_data["runs"], start=1):
                if not isinstance(run, dict):
                    print(
                        f"error: {path}: entry {eid} arm {arm!r} run {n} "
                        f"is not an object",
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
        n_printed += 1

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
    be given all together and match the scored sums."""
    results_ids: list[str] = []
    results_kinds: dict[str, str] = {}
    results_arms: dict[str, set[str]] = {}
    for results_str in args.results:
        results_path = Path(results_str)
        if not results_path.exists():
            return _err(f"results file not found: {results_path}")
        try:
            data = json.loads(results_path.read_text())
        except json.JSONDecodeError as e:
            return _err(f"invalid JSON in {results_path}: {e}")
        if not isinstance(data, dict) or not isinstance(
            data.get("entries"), list
        ):
            return _err(
                f"{results_path}: not a shape-suite results file "
                f"(missing 'entries' list)"
            )
        for i, e in enumerate(data["entries"]):
            eid = e.get("id") if isinstance(e, dict) else None
            if not isinstance(eid, str) or not eid:
                return _err(
                    f"{results_path}: results entry {i} missing 'id' "
                    f"(non-empty string)"
                )
            kind = e.get("kind")
            arms = e.get("arms") if isinstance(e, dict) else None
            if not isinstance(arms, dict):
                return _err(
                    f"{results_path}: entry {eid} is missing its 'arms' "
                    f"object"
                )
            arm_keys = {a for a in arms if isinstance(a, str) and a}
            if eid not in results_kinds:
                if kind not in SHAPE_KINDS:
                    return _err(
                        f"{results_path}: entry {eid}: kind must be one "
                        f"of {sorted(SHAPE_KINDS)}, got {kind!r}"
                    )
                results_ids.append(eid)
                results_kinds[eid] = kind
            elif kind != results_kinds[eid]:
                return _err(
                    f"{results_path}: entry {eid}: kind {kind!r} differs "
                    f"from earlier results file "
                    f"({results_kinds[eid]!r})"
                )
            results_arms.setdefault(eid, set()).update(arm_keys)

    scored_path = Path(args.scored)
    if not scored_path.exists():
        return _err(f"scored file not found: {scored_path}")
    try:
        scored = json.loads(scored_path.read_text())
    except json.JSONDecodeError as e:
        return _err(f"invalid JSON in {scored_path}: {e}")
    if not isinstance(scored, dict) or not isinstance(
        scored.get("entries"), list
    ):
        return _err(
            f"{scored_path}: expected a JSON object with an 'entries' list"
        )

    covered: set[str] = set()
    for i, entry in enumerate(scored["entries"]):
        if not isinstance(entry, dict):
            return _err(f"{scored_path}: entry {i} is not an object")
        eid = entry.get("id")
        if not isinstance(eid, str) or not eid:
            return _err(
                f"{scored_path}: entry {i} missing 'id' (non-empty string)"
            )
        if eid in covered:
            return _err(f"{scored_path}: duplicate id: {eid}")
        if eid not in results_kinds:
            return _err(f"{scored_path}: unknown id: {eid}")
        covered.add(eid)
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
            if adopted_arm == "v0":
                return _err(
                    f"{scored_path}: entry {eid}: adopted_arm must not "
                    f"be the v0 control arm (a prohibition/absence arm is "
                    f"a measurement instrument, never a candidate)"
                )
            if adopted_arm not in results_arms[eid]:
                return _err(
                    f"{scored_path}: entry {eid}: adopted_arm "
                    f"{adopted_arm!r} is not an arm present in this "
                    f"entry's results ({', '.join(sorted(results_arms[eid]))})"
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

    missing = [eid for eid in results_ids if eid not in covered]
    if missing:
        return _err(
            f"{scored_path}: missing scored entries for results ids: "
            f"{', '.join(missing)}"
        )

    # Optional count gate: when the record-step counts are given, they
    # must be all four together and equal what the scored entries sum to.
    count_names = ("adopted", "no_failure", "unresolved", "voids")
    given = [getattr(args, n, None) for n in count_names]
    if any(c is not None for c in given):
        if not all(c is not None for c in given):
            return _err(
                "--adopted/--no-failure/--unresolved/--voids must be "
                "given together"
            )
        computed = {
            r: sum(1 for e in scored["entries"] if e.get("result") == r)
            for r in ("adopted", "no-failure", "unresolved", "void")
        }
        if tuple(given) != tuple(computed[r] for r in computed):
            return _err(
                f"counts do not match scored results: computed "
                f"{computed['adopted']} adopted / "
                f"{computed['no-failure']} no-failure / "
                f"{computed['unresolved']} unresolved / "
                f"{computed['void']} void, got "
                f"{given[0]} adopted / {given[1]} no-failure / "
                f"{given[2]} unresolved / {given[3]} void"
            )
    print(f"ok: {scored_path} covers {len(results_ids)} entries")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="evaluator.py")
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check")
    check.add_argument("--harness", required=True)

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
        default="retrieval-test",
        choices=["retrieval-test", "shape-test"],
        help="manifest key + count vocabulary for --scope dir "
        "(default: retrieval-test)",
    )
    record.add_argument("--score", type=float)
    record.add_argument("--passes", type=int)
    record.add_argument("--fails", type=int)
    record.add_argument("--gaps", type=int)
    record.add_argument("--voids", type=int)
    record.add_argument("--adopted", type=int)
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
    scored.add_argument("--scored", required=True)
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

    shape_scored = sub.add_parser("shape-scored-check")
    shape_scored.add_argument("--results", action="append", required=True)
    shape_scored.add_argument("--scored", required=True)
    shape_scored.add_argument("--adopted", type=int)
    shape_scored.add_argument("--no-failure", dest="no_failure", type=int)
    shape_scored.add_argument("--unresolved", type=int)
    shape_scored.add_argument("--voids", type=int)

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
    return cmd_run(args)


if __name__ == "__main__":
    sys.exit(main())
