"""Trigger track: run / split / suite / failures."""

import argparse
import json
import random
import sys
from dataclasses import dataclass, field
from pathlib import Path

from src import common
from src.strategies import EvalStrategy, Verdict, resolve_strategy
from src.tracks.track import Track, _required

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
    """One trigger rep: logged start/completion around strategy.evaluate."""
    common.log_start(n)
    verdict = strategy.evaluate(skill, case.query, workspace, model, effort)
    common.log_complete(n, verdict)
    return verdict


def print_report(result: BatchResult) -> None:
    """The human-readable per-run report after a cmd_run batch."""
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
    """The single-query trigger probe: one case, N reps, printed report."""
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
    """Split a query file into stratified train/validate sets."""
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
