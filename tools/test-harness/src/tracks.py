"""Track strategies: per-track campaign behavior behind one interface.

The four test tracks share a meta-process (suite → evidence → scored-check
→ record); this module is the single place that knows what differs. The
CLI drivers in evaluator.py call these hooks; nothing here parses argv
beyond reading attributes off the args namespace.
"""

import argparse
import json
import random
import re
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from src import common
from src.common import (
    EvidenceError,
    _err,
    _session_suffix,
    emit,
    iter_evidence,
    load_entries,
    load_results_json,
    log_start,
    run_rep_batched,
    validate_eval_agent,
)
from src.strategies import (
    EvalStrategy,
    HarnessExecutionError,
    Verdict,
    _fail,
    check_harness,
    resolve_strategy,
)


class _HarnessPreflight:
    """Default harness preflight for Track._harness_preflight: the
    strategies implementation. The evaluator's generic run_suite driver
    rebinds track._harness_preflight to its own module-level
    check_harness before pre_spend_gates, so the test suite's historical
    patch point (evaluator.check_harness) keeps working without tracks.py
    ever importing evaluator."""

    def __call__(
        self, name: str, strategy_cls: type[EvalStrategy], model: str | None
    ) -> None:
        check_harness(name, strategy_cls, model)


def _required(args: argparse.Namespace, track: "Track", *names: str) -> None:
    """Runtime replacement for argparse required=True on merged flags
    (Q7a): the first missing flag fails with the exact message."""
    for n in names:
        if getattr(args, n, None) is None:
            flag = f"--{n.replace('_', '-')}"
            _fail(f"{flag} is required with --track {track.name}")


class Track:
    """One track's campaign behavior. Class attributes are track data
    (the registry); methods are the four-step interface plus suite
    internals. All failures print the exact historical message and either
    return an int rc (preferred, matches the suite commands' style) or
    _fail/sys.exit (pre-spend gates, matches load_entries)."""

    # Harness preflight hook called at each track's historical
    # check_harness position inside pre_spend_gates. The default is the
    # strategies implementation; run_suite overwrites it with evaluator's
    # check_harness binding (see _HarnessPreflight above).
    _harness_preflight: Callable[
        [str, type[EvalStrategy], str | None], None
    ] = _HarnessPreflight()

    # ---- identity / registry data ----
    name: str  # manifest key and CLI --track choice, e.g. "retrieval-test"
    inventory_kind: str | None  # "fact" | "rule" | None (Q4a)
    results_noun: str  # envelope word: "not a {noun}-suite results file"
    # ---- suite ----
    agents: tuple[str, ...] = ()  # eval agent names for pre-spend validation
    zero_results_on_empty: bool = False  # trigger: empty input writes zeros
    # ---- scored ----
    supports_scored: bool = True
    multi_results: bool = False  # repeated --results (shape/pressure) (Q6a)
    union_hook: Callable[[Path, dict, dict], str | None] | None = None
    skeleton_header: bool = False  # retrieval/pressure skeletons carry one
    scored_object_phrase: str = "a JSON object"  # pressure says "an object"
    count_arg_names: tuple[str, ...] = ()  # scored-check counts flags, dests
    count_result_names: tuple[str, ...] = ()  # parallel result vocabulary
    sum_keys: dict[str, str] = {}  # result value -> manifest count key
    # ---- meta ----
    supports_meta: bool = False

    # ---- suite hooks ----

    def pre_spend_gates(
        self, args: argparse.Namespace, strategy_cls: type[EvalStrategy]
    ) -> list[Any] | int:
        """Every check that must pass before the first harness invocation,
        in the track's historical order (check_harness included, at the
        position the track has always had it). Returns the validated
        entries, or an int rc with the exact error already printed."""
        raise NotImplementedError

    def write_empty(self, args: argparse.Namespace) -> None:
        """zero_results_on_empty tracks only: write the zeroed envelope and
        the note line, replacing the early return in the old cmd_suite."""

    def install_agents(self, strategy: EvalStrategy, args) -> None:
        """strategy.install(...) calls for every workspace/agent pair."""

    def banner(self, args: argparse.Namespace, n: int) -> list[str]:
        """The emit lines between install and the first entry."""
        raise NotImplementedError

    def run_entry(
        self, strategy: EvalStrategy, entry: Any, args: argparse.Namespace
    ) -> dict | int:
        """Run one entry (all its arms) and return its results record, or
        an int rc when an arm aborts mid-campaign (retrieval's
        catch-and-propagate, Q2a). Per-entry progress lines are emitted
        here, matching each track's historical format."""
        raise NotImplementedError

    def extra_config(self, args: argparse.Namespace) -> dict:
        """Track keys merged into base_config (queries/entries/scenarios
        path, arms, fixture_key, arm, skill_file, ...)."""
        return {}

    def finalize(self, config: dict, results: list[dict]) -> dict:
        """The results file document. Default: {config, entries}; trigger
        overrides with its top-level queries/totals envelope."""
        return {"config": config, "entries": results}

    def done_line(self, n: int, out: Path) -> str:
        """The final emit line after the results write."""
        raise NotImplementedError

    # ---- evidence ----

    def print_evidence(self, args: argparse.Namespace) -> int:
        """The track's evidence printer (extraction only; exit 0 with a
        count line, exit 1 on a malformed file). Trigger's implementation
        reads the queries envelope; the others share load_results_json +
        iter_evidence from common."""
        raise NotImplementedError

    # ---- scored ----

    def skeleton_entry(self, eid: str, extras: dict) -> dict:
        """One scored.json skeleton entry (judgment fields null; the
        mechanically derivable fields pre-filled)."""
        raise NotImplementedError

    def check_scored_entry(
        self,
        scored_path: Path,
        entry: dict,
        arms: set[str],
        extras: dict,
    ) -> int | None:
        """Per-entry scored validation beyond coverage: vocabularies,
        implication rules, verbatim requirements. Returns _err(...) on
        violation, None when the entry passes."""
        raise NotImplementedError

    def scored_signal(self, entry: dict) -> bool:
        """True when the entry carries this track's discriminating
        vocabulary (record --scored track detection)."""
        return False

    # ---- meta ----

    def run_meta(self, args: argparse.Namespace, strategy_cls) -> int:
        """supports_meta tracks only: the session-resume command."""
        raise NotImplementedError


# --------------------------------------------------------------------------
# Trigger track: run / split / suite / failures


TRIGGER_AGENT = "trigger-evaluator"


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


def run_rep(
    strategy: EvalStrategy,
    skill: str,
    case: EvalCase,
    workspace: Path,
    model: str | None,
    effort: str | None,
    n: int,
) -> Verdict:
    common.log_start(n)
    verdict = strategy.evaluate(skill, case.query, workspace, model, effort)
    common.log_complete(n, verdict)
    return verdict


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

    result = TRIGGER_TRACK._run_query_batch(strategy, case, workspace, args)
    print_report(result)
    return 0


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


class TriggerTrack(Track):
    """The trigger track: one invocation = one query, should_trigger
    scored with a Wilson lower bound per query. Results envelope is the
    historical top-level {skill, harness, ..., queries, totals} — no
    config wrapper, no date key."""

    name = "trigger-test"
    inventory_kind = None
    results_noun = "trigger"
    agents = (TRIGGER_AGENT,)
    zero_results_on_empty = True
    supports_scored = False
    # The per-query progress line's [i/n] position: the generic driver
    # passes no index into run_entry, so pre_spend_gates seeds these.
    _i: int = 0
    _n: int = 0

    def _score_query(
        self, case: EvalCase, verdicts: list[Verdict]
    ) -> BatchResult:
        """The scoring half of the deleted eval_batch: tally pass/fail/
        void, Wilson over non-void runs."""
        result = BatchResult(case=case)
        for v in verdicts:
            result.verdicts.append(v)
            if v.outcome == "void":
                result.void += 1
            elif (v.outcome == "triggered") == case.should_trigger:
                result.passed += 1
            else:
                result.failed += 1

        n_scored = result.passed + result.failed
        if n_scored > 0:
            result.wilson_low, result.wilson_high = common.wilson_interval(
                result.passed, n_scored
            )
            result.score = result.wilson_low
        return result

    def _query_record(self, case: EvalCase, result: BatchResult) -> dict:
        """One query's results entry incl. failures/voids extraction and
        the per-query progress emit."""
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
        record = {
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
        score_s = f"{result.score:.3f}" if result.score is not None else "n/a"
        common.emit(
            f'[query {self._i}/{self._n}] "{case.query}" -> '
            f"{result.passed} pass / {result.failed} fail / "
            f"{result.void} void score: {score_s}"
        )
        return record

    def _run_query_batch(
        self,
        strategy: EvalStrategy,
        case: EvalCase,
        workspace: Path,
        args: argparse.Namespace,
    ) -> BatchResult:
        """run_rep_batched over a run_one closure (the old run_rep body)
        + _score_query. Replaces eval_batch; the batch mechanics duplicate
        of run_rep_batched is deleted."""

        def run_one(n: int) -> Verdict:
            return run_rep(
                strategy,
                args.skill,
                case,
                workspace,
                args.model,
                args.variant,
                n,
            )

        verdicts = common.run_rep_batched(run_one, args.reps, None)
        return self._score_query(case, verdicts)

    def pre_spend_gates(
        self, args: argparse.Namespace, strategy_cls: type[EvalStrategy]
    ) -> list[EvalCase] | int:
        """Order preserved from the old cmd_suite: stub-synced check
        (returns 1) → --reps → --timeout → check_harness → load_queries →
        --out parent; the empty case is handled by the driver via
        zero_results_on_empty. The merged-parser --workspace/--queries
        requirement and the historical 3/30 reps/timeout defaults are
        applied here (Q7a)."""
        _required(args, self, "workspace", "queries")
        if args.reps is None:
            args.reps = 3
        if args.timeout is None:
            args.timeout = 30
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
        self._harness_preflight(args.harness, strategy_cls, args.model)
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
        self._i = 0
        self._n = len(cases)
        return cases

    def write_empty(self, args: argparse.Namespace) -> None:
        """The zeroed envelope + 'note: empty query file' line."""
        out = Path(args.out)

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

        out.write_text(json.dumps(empty_result(), indent=2) + "\n")
        common.emit("note: empty query file, wrote zeroed result")

    def install_agents(self, strategy: EvalStrategy, args) -> None:
        """strategy.install(...) calls for every workspace/agent pair."""
        strategy.install(
            Path(args.workspace), Path(args.agents_dir), TRIGGER_AGENT
        )

    def banner(self, args: argparse.Namespace, n: int) -> list[str]:
        """The emit lines between install and the first entry."""
        return [
            f"trigger test suite: {args.skill} ({n} queries)",
            f"workspace: {Path(args.workspace)}",
            f"harness: {args.harness}  model: {args.model or '(default)'}  "
            f"variant: {args.variant or '(none)'}  reps: {args.reps}  "
            f"timeout: {args.timeout}s",
        ]

    def run_entry(
        self, strategy: EvalStrategy, entry: EvalCase, args: argparse.Namespace
    ) -> dict | int:
        """One EvalCase through _run_query_batch → _query_record."""
        workspace = Path(args.workspace)
        result = self._run_query_batch(strategy, entry, workspace, args)
        self._i += 1
        return self._query_record(entry, result)

    def finalize(self, config: dict, results: list[dict]) -> dict:
        """The queries/totals envelope. Totals are recomputed from results
        here (no instance state): passed/failed/void/timeouts sums +
        _score_counts over passed/failed. The historical trigger envelope
        carries the base keys top-level, without the config wrapper and
        without the date key."""
        tot_passed = sum(r["passed"] for r in results)
        tot_failed = sum(r["failed"] for r in results)
        tot_void = sum(r["void"] for r in results)
        tot_timeouts = sum(r["timeouts"] for r in results)
        low, high, score = common._score_counts(tot_passed, tot_failed)
        return {
            "skill": config["skill"],
            "harness": config["harness"],
            "model": config["model"],
            "variant": config["variant"],
            "reps": config["reps"],
            "timeout": config["timeout"],
            "queries": results,
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

    def done_line(self, n: int, out: Path) -> str:
        """The final emit line after the results write. The totals come
        from the results file just written (done_line receives only
        (n, out) from the generic driver)."""
        totals = json.loads(Path(out).read_text())["totals"]
        score_s = (
            f"{totals['score']:.3f}" if totals["score"] is not None else "n/a"
        )
        return (
            f"suite: {totals['passed']} pass / {totals['failed']} fail / "
            f"{totals['void']} void score: {score_s} -> {out}"
        )

    def print_evidence(self, args: argparse.Namespace) -> int:
        """Print every failed run (query, run number, detail, full
        reasoning) from a suite result JSON. Extraction only; analysis is
        the agent's job. Exit 0 even when failures exist — this is an
        extractor, not a gate."""
        path = Path(args.results)
        if not path.exists():
            print(f"error: results file not found: {path}", file=sys.stderr)
            return 1
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError as e:
            print(f"error: invalid JSON in {path}: {e}", file=sys.stderr)
            return 1
        if not isinstance(data, dict) or not isinstance(
            data.get("queries"), list
        ):
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
                    f" [session {f['session_id']}]"
                    if f.get("session_id")
                    else ""
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


TRIGGER_TRACK = TriggerTrack()


# --------------------------------------------------------------------------
# Retrieval track: retrieval-suite + retrieval-evidence + scored-check

# Track constants: the retrieval track evaluates under
# RETRIEVAL_EVALUATOR_AGENT and baselines under RETRIEVAL_CONTROL_AGENT
# (design §5.1/§5.2).
RETRIEVAL_EVALUATOR_AGENT = "retrieval-evaluator"
RETRIEVAL_CONTROL_AGENT = "retrieval-control"

# Log label per retrieval arm, used as a [tag] prefix on every progress
# line so interleaved arm output stays attributable when both arms run in
# parallel. The skill arm is padded to the control arm's width.
ARM_TAGS = {"skill_arm": " skill ", "control_arm": "control"}

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
    """Read and strictly validate a retrieval query file (design §8
    schema). On any violation prints `error: <exact reason>` to stderr
    and exits 1 (pre-spend: zero harness runs happen before this
    returns)."""
    return load_entries(path, "query", "query", _check_retrieval_fields)


def _check_retrieval_fields(path: Path, i: int, entry: dict, eid: str) -> None:
    """Per-field checks for a retrieval query entry: the query and
    expect rubric, optional fixtures with on-disk presence, and the
    {RUN_DIR} token agreement rule."""
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


def _retrieval_union_hook(path: Path, e: dict, extras: dict) -> str | None:
    """Collect each entry's expect rubric for the retrieval scored-check's
    missed_bullets verbatim-text validation."""
    expects = extras.setdefault("expect", {})
    expect = e.get("expect")
    expects[e["id"]] = expect if isinstance(expect, list) else []
    return None


# Scored result values and parallel vocabularies for the retrieval
# scored-check.
RESULTS = {"pass", "fail", "gap", "void"}
CLASSIFICATIONS = {"findability", "clarity"}  # "gap" is a result, not a
#                                              classification
CONTROLS = {"pass", "fail", "void"}


class RetrievalTrack(Track):
    """Retrieval: entries x 2 arms (skill/control) x reps, arms in
    parallel, two workspaces, contamination gates."""

    name = "retrieval-test"
    inventory_kind = "fact"
    results_noun = "retrieval"
    agents = (RETRIEVAL_EVALUATOR_AGENT, RETRIEVAL_CONTROL_AGENT)
    skeleton_header = True
    count_arg_names = ("passes", "fails", "gaps", "voids")
    count_result_names = ("pass", "fail", "gap", "void")
    sum_keys = {
        "pass": "passes",
        "fail": "fails",
        "gap": "gaps",
        "void": "voids",
    }
    # staticmethod is load-bearing: instance access must not bind self,
    # because cmd_scored_check passes entry_hook=track.union_hook.
    union_hook = staticmethod(_retrieval_union_hook)
    # The per-entry progress line's [i/n] position: the generic driver
    # passes no index into run_entry, so pre_spend_gates seeds these
    # (same pattern as TriggerTrack).
    _i: int = 0
    _n: int = 0

    def pre_spend_gates(
        self, args: argparse.Namespace, strategy_cls: type[EvalStrategy]
    ) -> list[dict] | int:
        """Order preserved from the old cmd_retrieval_suite: check_harness
        → agent validation → --reps → --timeout → skill-ws sync check →
        control contamination → load queries → --out parent. Returns the
        validated entries, or an int rc with the exact error already
        printed. The merged-parser flag requirement and the historical
        1/120 reps/timeout defaults are applied here (Q7a)."""
        _required(
            args, self, "skill_workspace", "control_workspace", "queries"
        )
        if args.reps is None:
            args.reps = 1
        if args.timeout is None:
            args.timeout = 120
        self._harness_preflight(args.harness, strategy_cls, args.model)
        skill_ws = Path(args.skill_workspace)
        control_ws = Path(args.control_workspace)
        agents_dir = Path(args.agents_dir)
        queries_path = Path(args.queries)

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
                f"control workspace contains skill '{args.skill}' — "
                "baseline contamination; recreate the control workspace, "
                "never sync"
            )
        entries = load_retrieval_queries(queries_path)  # exits 1 on error
        out = Path(args.out)
        if not out.parent.is_dir():
            _fail(f"output directory does not exist: {out.parent}")
        self._i = 0
        self._n = len(entries)
        return entries

    def install_agents(self, strategy: EvalStrategy, args) -> None:
        """strategy.install(...) calls for every workspace/agent pair."""
        strategy.install(
            Path(args.skill_workspace),
            Path(args.agents_dir),
            RETRIEVAL_EVALUATOR_AGENT,
            skill_name=args.skill,
        )  # {{SKILL_NAME}}
        strategy.install(
            Path(args.control_workspace),
            Path(args.agents_dir),
            RETRIEVAL_CONTROL_AGENT,
        )

    def banner(self, args: argparse.Namespace, n: int) -> list[str]:
        """The emit lines between install and the first entry."""
        return [
            f"retrieval test suite: {args.skill} ({n} queries)",
            f"skill workspace: {Path(args.skill_workspace)}",
            f"control workspace: {Path(args.control_workspace)}",
            f"harness: {args.harness}  model: {args.model or '(default)'}  "
            f"variant: {args.variant or '(none)'}  reps: {args.reps}  "
            f"timeout: {args.timeout}s",
        ]

    def run_entry(
        self, strategy: EvalStrategy, entry: dict, args: argparse.Namespace
    ) -> dict | int:
        """One entry's two arms in parallel, like eval_batch parallelized
        trigger reps: each arm still runs its smoke rep alone before its
        rep batches, but the arms no longer wait on each other. A harness
        failure in either arm aborts the campaign (no JSON, workspaces
        kept): SystemExit from a worker is caught and propagated as an
        int rc, a HarnessExecutionError from an arm future is emitted and
        returns 1 — the Q2a nested-parallel pattern; every other track
        aborts on the main thread."""
        skill_ws = Path(args.skill_workspace)
        control_ws = Path(args.control_workspace)
        record = {
            "id": entry["id"],
            "query": entry["query"],
            "expect": entry["expect"],
        }
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
        self._i += 1
        emit(f"[{self._i}/{self._n}] {entry['id']}")
        return record

    def extra_config(self, args: argparse.Namespace) -> dict:
        return {"queries": str(Path(args.queries))}

    def done_line(self, n: int, out: Path) -> str:
        return f"retrieval suite: {n} entries -> {out}"

    def print_evidence(self, args: argparse.Namespace) -> int:
        """Print the per-run scoring evidence from a retrieval-suite
        results JSON: per entry, the expect rubric and, for every
        arm/rep, the answer text, sources consulted, void signals, and
        tool-call targets. The trigger track's `failures` equivalent:
        extraction only, so the driver scores from presented evidence
        instead of hand-rolling JSON walks. Exit 0 with an entry count
        line; exit 1 only on a malformed file."""
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
                        f"error: {path}: entry {eid} is missing arm run "
                        f"lists",
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

    def skeleton_entry(self, eid: str, extras: dict) -> dict:
        """One scored.json skeleton entry (judgment fields null; the
        mechanically derivable fields pre-filled). Retrieval carries no
        derivable judgment context; the expect rubric is judging context
        only and is never written."""
        return {
            "id": eid,
            "result": None,
            "classification": None,
            "control": None,
            "ablation_flag": None,
            "missed_bullets": None,
            "notes": None,
        }

    def check_scored_entry(
        self,
        scored_path: Path,
        entry: dict,
        arms: set[str],
        extras: dict,
    ) -> int | None:
        """The retrieval scored-check's per-entry body: vocabularies, the
        ablation_flag derivation, and missed_bullets verbatim against the
        expect rubric collected from the results union (extras['expect']).
        Returns _err(...) on violation, None when the entry passes."""
        eid = entry["id"]
        results_expect = extras.get("expect", {})
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
        return None

    def scored_signal(self, entry: dict) -> bool:
        """True when the entry carries the retrieval vocabulary (record
        --scored track detection; wired into _scored_track_signals in a
        later phase)."""
        return entry.get("result") in ("pass", "fail", "gap") or any(
            k in entry for k in ("classification", "control", "ablation_flag")
        )


RETRIEVAL_TRACK = RetrievalTrack()


# --------------------------------------------------------------------------
# Shape track: shape-suite + shape-evidence + shape-scored-check

SHAPE_EVALUATOR_AGENT = "shape-evaluator"

# Vocabularies for the shape track (plan §File schemas / §Scoring
# artifacts).
SHAPE_KINDS = {"shaping", "pattern"}
SHAPE_RESULTS = {"adopted", "no-failure", "unresolved", "void"}
SHAPE_GATES = {"pass", "fail"}
# Fixture keys allowed on an entries file: `application` is always
# present; `counter-example` is required exactly on pattern entries
# (restraint gate).
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
    lives in ShapeTrack.pre_spend_gates, which owns the body bytes. On
    any violation prints `error: <exact reason>` to stderr and exits 1
    (pre-spend: zero harness runs happen before this returns)."""
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


class ShapeTrack(Track):
    """Shape: entries x arms (v0 control + variants) x reps, strictly
    serial, prompt-injection arms, doc-drift gate."""

    name = "shape-test"
    inventory_kind = "rule"
    results_noun = "shape"
    agents = (SHAPE_EVALUATOR_AGENT,)
    multi_results = True
    count_arg_names = ("adopted", "no_failure", "unresolved", "voids")
    count_result_names = ("adopted", "no-failure", "unresolved", "void")
    sum_keys = {
        "adopted": "adopted",
        "no-failure": "no-failure",
        "unresolved": "unresolved",
        "void": "voids",
    }
    # staticmethod is load-bearing: instance access must not bind self,
    # because cmd_scored_check passes entry_hook=track.union_hook.
    union_hook = staticmethod(_shape_union_hook)
    # The per-entry progress line's [i/n] position: the generic driver
    # passes no index into run_entry, so pre_spend_gates seeds these
    # (same pattern as TriggerTrack).
    _i: int = 0
    _n: int = 0
    # pre_spend_gates stashes for run_entry/banner/extra_config: the
    # snapshotted skill body and the parsed --arms list.
    _body: str = ""
    _arms: list[str] = []

    def pre_spend_gates(
        self, args: argparse.Namespace, strategy_cls: type[EvalStrategy]
    ) -> list[dict] | int:
        """Order preserved from the old cmd_shape_suite: check_harness →
        agent validation → --reps → --timeout → skill_file exists/
        non-empty → --fixture-key → --arms → load entries → per-entry
        arm/variant + fixture gates → doc-drift gate → --out parent →
        contamination. Returns the validated entries, or an int rc with the
        exact error already printed. The merged-parser flag requirement and
        the historical 5/120 reps/timeout defaults are applied here (Q7a)."""
        _required(args, self, "workspace", "entries", "skill_file", "arms")
        if args.reps is None:
            args.reps = 5
        if args.timeout is None:
            args.timeout = 120
        self._harness_preflight(args.harness, strategy_cls, args.model)
        ws = Path(args.workspace)
        agents_dir = Path(args.agents_dir)
        entries_path = Path(args.entries)

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
                f"--fixture-key must be one of "
                f"{', '.join(SHAPE_FIXTURE_KEYS)}, "
                f"got {args.fixture_key!r}"
            )
        arms = [a.strip() for a in args.arms.split(",")]
        if not arms or any(not a for a in arms):
            _fail(
                f"--arms must be a comma-separated list of arms "
                f"({', '.join(SHAPE_VARIANT_KEYS)} or v0), got "
                f"{args.arms!r}"
            )

        entries = load_shape_entries(entries_path)  # exits 1 on violation
        for entry in entries:
            for arm in arms:
                if arm != "v0" and arm not in entry["variants"]:
                    _fail(
                        f"--arms: entry {entry['id']!r} defines no variant "
                        f"{arm!r} (has: "
                        f"{', '.join(sorted(entry['variants']))})"
                    )
            fixture = entry["fixtures"].get(args.fixture_key)
            if not isinstance(fixture, str) or not fixture:
                _fail(
                    f"entry {entry['id']!r} has no {args.fixture_key!r} "
                    f"fixture"
                )

        # Doc-drift gate: every section span must appear verbatim exactly
        # once in the snapshotted body (frontmatter already stripped by
        # the driver — spans overlapping frontmatter are never matched).
        # Aborts before spend.
        for entry in entries:
            occurrences = body.count(entry["section"])
            if occurrences != 1:
                _fail(
                    f"doc drift: section span of entry {entry['id']!r} "
                    f"occurs {occurrences} times in the skill body "
                    f"(expected exactly once); fix the entry or the "
                    f"snapshot"
                )

        out = Path(args.out)
        if not out.parent.is_dir():
            _fail(f"output directory does not exist: {out.parent}")
        if (ws / ".agents" / "skills" / args.skill).exists():
            _fail(
                f"workspace contains skill '{args.skill}' — this track "
                "injects the skill body into prompts and never syncs; "
                "recreate the workspace, never sync"
            )

        self._body = body
        self._arms = arms
        self._i = 0
        self._n = len(entries)
        return entries

    def install_agents(self, strategy: EvalStrategy, args) -> None:
        """strategy.install(...) calls for every workspace/agent pair."""
        strategy.install(
            Path(args.workspace), Path(args.agents_dir), SHAPE_EVALUATOR_AGENT
        )

    def banner(self, args: argparse.Namespace, n: int) -> list[str]:
        """The emit lines between install and the first entry."""
        return [
            f"shape test suite: {args.skill} ({n} entries)",
            f"workspace: {Path(args.workspace)}",
            f"harness: {args.harness}  model: {args.model or '(default)'}  "
            f"variant: {args.variant or '(none)'}  reps: {args.reps}  "
            f"timeout: {args.timeout}s",
            f"skill file: {Path(args.skill_file)}",
            f"arms: {', '.join(self._arms)}  fixture-key: "
            f"{args.fixture_key}",
        ]

    def run_entry(
        self, strategy: EvalStrategy, entry: dict, args: argparse.Namespace
    ) -> dict | int:
        """One entry x arm, STRICTLY serialized — never the retrieval
        track's arm-parallel structure. Arms differ only in prompt bytes:
        each arm's body (v0: section span removed; vN: span replaced by
        the variant) is assembled fresh from the snapshotted skill file
        and injected into every rep's prompt; the workspace is never
        synced and never written, so there is no byte-state to restore."""
        ws = Path(args.workspace)
        record = {
            "id": entry["id"],
            "kind": entry["kind"],
            "markers": entry["markers"],
            "restraint_markers": entry.get("restraint_markers"),
            "arms": {},
        }
        for arm in self._arms:
            try:
                arm_body = assemble_arm_body(self._body, entry, arm)
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
        self._i += 1
        emit(f"[{self._i}/{self._n}] {entry['id']}")
        return record

    def extra_config(self, args: argparse.Namespace) -> dict:
        return {
            "entries": str(Path(args.entries)),
            "skill_file": str(Path(args.skill_file)),
            "arms": self._arms,
            "fixture_key": args.fixture_key,
        }

    def done_line(self, n: int, out: Path) -> str:
        return f"shape suite: {n} entries -> {out}"

    def print_evidence(self, args: argparse.Namespace) -> int:
        """Print the per-run scoring evidence from a shape-suite results
        JSON: per entry/arm/rep the answer text, void signals, session
        id, and marker triage counts (markers are carried in the results
        entries, so no entries-file re-read is needed). Extraction only —
        the driver judges convergence across the reps by hand. Exit 0
        with an entry count line; exit 1 only on a malformed file or
        unknown --entry."""
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
                        f"error: {path}: entry {eid} is missing its "
                        f"'arms' object",
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
                                + ", ".join(
                                    f"{k}={v}" for k, v in rcounts.items()
                                )
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

    def skeleton_entry(self, eid: str, extras: dict) -> dict:
        """One scored.json skeleton entry: kind and per-arm marker_counts
        pre-filled from the union extras, judgment fields null."""
        return {
            "id": eid,
            "kind": extras["kinds"][eid],
            "result": None,
            "adopted_arm": None,
            "restraint_gate": None,
            "marker_counts": extras["marker_counts"].get(eid, {}),
            "notes": None,
        }

    def check_scored_entry(
        self,
        scored_path: Path,
        entry: dict,
        arms: set[str],
        extras: dict,
    ) -> int | None:
        """The shape scored-check's per-entry body: kind consistency with
        the results union, vocabularies, the adopted_arm and
        restraint_gate rules, and marker_counts/notes types. kinds come
        from extras['kinds'], arms is the entry's union arm set. Returns
        _err(...) on violation, None when the entry passes."""
        eid = entry["id"]
        results_kinds = extras.get("kinds", {})
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
            if adopted_arm not in arms:
                return _err(
                    f"{scored_path}: entry {eid}: adopted_arm "
                    f"{adopted_arm!r} is not an arm present in this "
                    f"entry's results ({', '.join(sorted(arms))})"
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
        return None

    def scored_signal(self, entry: dict) -> bool:
        """True when the entry carries the shape vocabulary (record
        --scored track detection)."""
        return (
            entry.get("result") == "adopted"
            or "adopted_arm" in entry
            or "restraint_gate" in entry
        )


SHAPE_TRACK = ShapeTrack()


# --------------------------------------------------------------------------
# Pressure track: pressure-suite + pressure-evidence + pressure-meta +
# pressure-scored-check

# Track constants: the pressure track runs one arm per invocation and
# evaluates under PRESSURE_EVALUATOR_AGENT.
PRESSURE_EVALUATOR_AGENT = "pressure-evaluator"

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
# prefix on every progress line: "[ red ]" / "[green]".
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


def _pressure_union_hook(path: Path, e: dict, extras: dict) -> str | None:
    """Pressure results entries must carry their arms object: the
    scored check's red/green implications read the union arm set. The
    hook also records the union arm keys per id in extras['arms'], so
    the generic driver's --emit-skeleton path can derive the
    verdict_constraint hint (the old pressure command stashed the union
    arm map into extras explicitly before emitting)."""
    arms = e.get("arms")
    if not isinstance(arms, dict):
        return f"{path}: entry {e['id']} is missing its 'arms' object"
    extras.setdefault("arms", {}).setdefault(e["id"], set()).update(
        a for a in arms if isinstance(a, str) and a
    )
    return None


class PressureTrack(Track):
    """Pressure: entries x one arm per invocation (red/green), prompts
    only, plus the unique session-resume meta command."""

    name = "pressure-test"
    inventory_kind = "rule"
    results_noun = "pressure"
    agents = (PRESSURE_EVALUATOR_AGENT,)
    multi_results = True
    skeleton_header = True
    scored_object_phrase = "an object"  # the one wording shim, now data
    count_arg_names = ("bulletproof", "no_failure", "unresolved", "voids")
    count_result_names = ("bulletproof", "no-failure", "unresolved", "void")
    sum_keys = {
        "bulletproof": "bulletproof",
        "no-failure": "no-failure",
        "unresolved": "unresolved",
        "void": "voids",
    }
    # staticmethod is load-bearing: instance access must not bind self,
    # because cmd_scored_check passes entry_hook=track.union_hook.
    union_hook = staticmethod(_pressure_union_hook)
    supports_meta = True
    # The per-entry progress line's [i/n] position: the generic driver
    # passes no index into run_entry, so pre_spend_gates seeds these
    # (same pattern as the other tracks).
    _i: int = 0
    _n: int = 0
    # pre_spend_gates stashes for run_entry (the ONE allowed per-run
    # instance state): the green arm's skill body bytes, None on red.
    _skill_text: str | None = None

    def pre_spend_gates(
        self, args: argparse.Namespace, strategy_cls: type[EvalStrategy]
    ) -> list[dict] | int:
        """Order preserved from the old cmd_pressure_suite: check_harness
        → agent validation → --arm validity → green/red --skill-file
        rules → load scenarios → --reps → --timeout → --out parent →
        contamination. Returns the validated entries, or an int rc with the
        exact error already printed. The merged-parser flag requirement and
        the historical 5/120 reps/timeout defaults are applied here (Q7a)."""
        _required(args, self, "workspace", "scenarios", "arm")
        if args.reps is None:
            args.reps = 5
        if args.timeout is None:
            args.timeout = 120
        ws = Path(args.workspace)
        agents_dir = Path(args.agents_dir)
        scenarios_path = Path(args.scenarios)

        self._harness_preflight(args.harness, strategy_cls, args.model)
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
            if args.skill_file is None:  # gated above; keeps type narrow
                _fail("--skill-file is required with --arm green")
            skill_file = Path(args.skill_file)
            if not skill_file.is_file():
                _fail(f"skill file not found: {skill_file}")
            skill_text = skill_file.read_text()
            if not skill_text.strip():
                _fail(f"skill file is empty: {skill_file}")

        entries = load_pressure_scenarios(scenarios_path)  # exits 1 on error
        if args.reps < 1:
            _fail("--reps must be >= 1")
        if args.timeout < 1:
            _fail("--timeout must be >= 1")
        out = Path(args.out)
        if not out.parent.is_dir():
            _fail(f"output directory does not exist: {out.parent}")
        if (ws / ".agents" / "skills" / args.skill).exists():
            _fail(
                f"workspace contains skill '{args.skill}' — this track "
                "injects the skill body into prompts and never syncs; "
                "recreate the workspace, never sync"
            )

        self._skill_text = skill_text
        self._i = 0
        self._n = len(entries)
        return entries

    def install_agents(self, strategy: EvalStrategy, args) -> None:
        """strategy.install(...) calls for every workspace/agent pair."""
        strategy.install(
            Path(args.workspace),
            Path(args.agents_dir),
            PRESSURE_EVALUATOR_AGENT,
        )

    def banner(self, args: argparse.Namespace, n: int) -> list[str]:
        """The emit lines between install and the first entry."""
        lines = [
            f"pressure test suite: {args.skill} ({n} scenarios, "
            f"{args.arm} arm)",
            f"workspace: {Path(args.workspace)}",
            f"harness: {args.harness}  model: {args.model or '(default)'}  "
            f"variant: {args.variant or '(none)'}  reps: {args.reps}  "
            f"timeout: {args.timeout}s",
        ]
        if args.skill_file is not None:
            lines.append(f"skill file: {args.skill_file}")
        return lines

    def run_entry(
        self, strategy: EvalStrategy, entry: dict, args: argparse.Namespace
    ) -> dict | int:
        """One entry's single arm: reps of the arm's prompt bytes. The
        workspace is never synced and never written; arms differ only in
        prompt bytes."""
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
                        Path(args.workspace),
                        PRESSURE_EVALUATOR_AGENT,
                        args,
                        self._skill_text,
                    )
                }
            },
        }
        self._i += 1
        emit(f"[{self._i}/{self._n}] {entry['id']}")
        return record

    def extra_config(self, args: argparse.Namespace) -> dict:
        config = {"scenarios": str(Path(args.scenarios)), "arm": args.arm}
        if args.skill_file is not None:
            config["skill_file"] = args.skill_file
        return config

    def done_line(self, n: int, out: Path) -> str:
        return f"pressure suite: {n} entries -> {out}"

    def print_evidence(self, args: argparse.Namespace) -> int:
        """Print the per-run scoring evidence from a pressure-suite
        results JSON: per entry the statement, pressures, and compliant
        option, and per arm/rep the full answer text, void signals, and
        session id. Never extracts the choice letter — the driver reads
        every answer and judges choice + citation by hand. Exit 0 with
        an entry count line; exit 1 only on a malformed file or unknown
        --entry."""
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
                        f"error: {path}: entry {eid} is missing its "
                        f"'arms' object",
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
                compliant = entry.get("compliant_option", "?")
                print(f"compliant_option: {compliant}")
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

    def skeleton_entry(self, eid: str, extras: dict) -> dict:
        """One scored.json skeleton entry: the verdict_constraint hint
        derived from the red/green arm union (judgment fields null)."""
        arms = extras["arms"].get(eid, set())
        if "red" not in arms:
            # No red arm means the entry can never pass the scored check
            # (RED always runs first); nothing to constrain.
            constraint = None
        elif "green" in arms:
            constraint = ["bulletproof", "unresolved"]
        else:
            constraint = ["no-failure", "void"]
        return {
            "id": eid,
            "result": None,
            "counters": None,
            "verdict_constraint": constraint,
            "notes": None,
        }

    def check_scored_entry(
        self,
        scored_path: Path,
        entry: dict,
        arms: set[str],
        extras: dict,
    ) -> int | None:
        """The pressure scored-check's per-entry body: the result
        vocabulary, the red/green arm implications from the union arm
        set, and counters/notes types. Returns _err(...) on violation,
        None when the entry passes."""
        eid = entry["id"]
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
        return None

    def scored_signal(self, entry: dict) -> bool:
        """True when the entry carries the pressure vocabulary (record
        --scored track detection)."""
        return entry.get("result") == "bulletproof" or entry.get("arm") in (
            "red",
            "green",
        )

    def run_meta(self, args: argparse.Namespace, strategy_cls) -> int:
        """Resume one violating rep's session with the meta question and
        write the reply JSON. The agent is re-installed idempotently
        (re-running the frontmatter assertions); the driver passes the
        same --model/--variant as the original suite run. A harness
        error from a dead session follows the house policy: stderr with
        the [session <id>] suffix, exit 1, no JSON. The harness
        preflight lives in the generic meta driver."""
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


PRESSURE_TRACK = PressureTrack()

# The registry: one instance per track per process, built from the same
# module singletons the Phase-2 interim dispatch and tests reference (a
# second instance would split mutable module state like _Log and the
# per-run track state).
TRACKS: dict[str, Track] = {
    t.name: t
    for t in (TRIGGER_TRACK, RETRIEVAL_TRACK, SHAPE_TRACK, PRESSURE_TRACK)
}
