#!/usr/bin/env python3
"""Evaluator: run one query (--expect trigger|not-trigger) for N reps against an
opencode workspace and report whether the skill under test loaded.

Scope: the inner core only (eval_batch). One invocation = one query.
"""

import argparse
import json
import math
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

Outcome = Literal["triggered", "not-triggered", "void"]

MAX_WORKERS = 10


@dataclass
class EvalCase:
    query: str
    should_trigger: bool


@dataclass
class Verdict:
    outcome: Outcome
    detail: str = ""        # timeout note or signal status
    session_id: str = ""
    reasoning: str = ""     # concatenated --thinking blocks; never used for scoring


class HarnessExecutionError(Exception):
    """The harness could not execute the query (bad args, nonzero exit, provider
    error, empty event stream). Fatal: aborts the batch, exits 1. Never a verdict."""


@dataclass
class BatchResult:
    case: EvalCase
    verdicts: list[Verdict] = field(default_factory=list)
    passed: int = 0         # non-void runs matching expectation
    failed: int = 0         # non-void runs mismatching expectation
    void: int = 0
    wilson_low: float | None = None   # None when passed + failed == 0
    wilson_high: float | None = None
    score: float | None = None        # == wilson_low


def wilson_interval(passed: int, n: int, z: float = 1.96) -> tuple[float, float]:
    p = passed / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return center - margin, center + margin


class OpencodeStrategy:
    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    def evaluate(self, skill: str, query: str, workspace: Path,
                 model: str | None = None, effort: str | None = None) -> Verdict:
        cmd = ["opencode", "run", "--pure", "--auto", "--thinking",
               "--format", "json", "--dir", str(workspace)]
        if model is not None:
            cmd += ["--model", model]
        if effort is not None:
            cmd += ["--variant", effort]
        cmd.append(query)

        try:
            proc = subprocess.run(cmd, capture_output=True, text=True,
                                  timeout=self.timeout)
        except subprocess.TimeoutExpired:
            return Verdict("void", detail=f"timeout after {self.timeout}s")

        session_id = ""
        reasoning_parts: list[str] = []
        signal_status: str | None = None
        other_skill: str | None = None
        error_message: str | None = None
        parseable = 0

        for line in proc.stdout.splitlines():
            try:
                event = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            parseable += 1
            if not session_id and isinstance(event.get("sessionID"), str):
                session_id = event["sessionID"]
            etype = event.get("type")
            if etype == "reasoning":
                text = event.get("part", {}).get("text")
                if isinstance(text, str):
                    reasoning_parts.append(text)
            elif etype == "tool_use":
                part = event.get("part", {})
                if part.get("tool") == "skill":
                    name = part.get("state", {}).get("input", {}).get("name")
                    if name == skill:
                        signal_status = part.get("state", {}).get("status", "")
                    elif name is not None and other_skill is None:
                        other_skill = name
            elif etype == "error":
                error = event.get("error", {})
                message = error.get("data", {}).get("message")
                if not isinstance(message, str):
                    message = str(error)
                if error_message is None:
                    error_message = message

        reasoning = "\n".join(reasoning_parts)

        # Signal wins over everything.
        if signal_status is not None:
            return Verdict("triggered",
                           detail=f"skill tool invoked (status={signal_status})",
                           session_id=session_id, reasoning=reasoning)

        if error_message is not None:
            raise HarnessExecutionError(error_message)
        if proc.returncode != 0:
            raise HarnessExecutionError(
                f"exit {proc.returncode}: {proc.stderr[-500:]}")
        if parseable == 0:
            raise HarnessExecutionError("no parseable events (exit 0)")

        detail = f"other skill loaded: {other_skill}" if other_skill else ""
        return Verdict("not-triggered", detail=detail,
                       session_id=session_id, reasoning=reasoning)


def log_start(n: int) -> None:
    print(f"[rep {n:>3}] started", flush=True)


def log_complete(n: int, verdict: Verdict) -> None:
    line = f"[rep {n:>3}] completed: {verdict.outcome}"
    if verdict.outcome == "void":
        line += f" ({verdict.detail})"
    print(line, flush=True)


def run_rep(strategy: OpencodeStrategy, skill: str, case: EvalCase,
            workspace: Path, model: str | None, effort: str | None,
            n: int) -> Verdict:
    log_start(n)
    verdict = strategy.evaluate(skill, case.query, workspace, model, effort)
    log_complete(n, verdict)
    return verdict


def eval_batch(strategy: OpencodeStrategy, skill: str, case: EvalCase,
               workspace: Path, model: str | None, effort: str | None,
               reps: int) -> BatchResult:
    verdicts: dict[int, Verdict] = {}

    # Smoke rep runs alone; a harness failure here aborts before further spend.
    try:
        verdicts[1] = run_rep(strategy, skill, case, workspace, model, effort, 1)
    except HarnessExecutionError as e:
        print(f"error: harness could not execute the query: {e}", file=sys.stderr)
        sys.exit(1)

    # Remaining reps in parallel batches of at most MAX_WORKERS.
    remaining = list(range(2, reps + 1))
    for i in range(0, len(remaining), MAX_WORKERS):
        group = remaining[i:i + MAX_WORKERS]
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            futures = {
                pool.submit(run_rep, strategy, skill, case, workspace,
                            model, effort, n): n
                for n in group
            }
            first_error: tuple[int, str] | None = None
            for fut, n in futures.items():
                try:
                    verdicts[n] = fut.result()
                except HarnessExecutionError as e:
                    if first_error is None:
                        first_error = (n, str(e))
        if first_error is not None:
            n, detail = first_error
            print(f"error: rep {n} could not execute: {detail}", file=sys.stderr)
            print("error: batch aborted", file=sys.stderr)
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
        result.wilson_low, result.wilson_high = wilson_interval(result.passed,
                                                                n_scored)
        result.score = result.wilson_low
    return result


def print_report(skill: str, workspace: Path, model: str | None,
                 variant: str | None, reps: int, timeout: int,
                 result: BatchResult) -> None:
    print()
    print(f'query: "{result.case.query}"   expected: '
          f'{"trigger" if result.case.should_trigger else "not-trigger"}')
    for i, v in enumerate(result.verdicts, start=1):
        if v.outcome == "void":
            mark = "—"
        elif (v.outcome == "triggered") == result.case.should_trigger:
            mark = "pass"
        else:
            mark = "fail"
        line = f"  run {i:>3}: {v.outcome:<13}  {mark}"
        if v.outcome == "void":
            line += f"  detail: {v.detail}"
        print(line)
    total = result.passed + result.failed + result.void
    summary = (f"  summary: {result.passed} pass / {result.failed} fail / "
               f"{result.void} void ({total} runs)")
    if result.wilson_low is None:
        summary += "  wilson95: n/a (all void)  score: n/a"
    else:
        summary += (f"  wilson95: [{result.wilson_low:.3f}, "
                    f"{result.wilson_high:.3f}]  score: {result.score:.3f}")
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
    workspace = Path(args.workspace)
    stub = workspace / ".agents" / "skills" / args.skill / "SKILL.md"
    if not stub.exists():
        print(f"error: skill stub not synced: {stub}; "
              f"run workspace-manager.sh sync", file=sys.stderr)
        return 1
    if args.reps < 1:
        print("error: --reps must be >= 1", file=sys.stderr)
        return 1
    if args.timeout < 1:
        print("error: --timeout must be >= 1", file=sys.stderr)
        return 1

    case = EvalCase(query=args.query,
                    should_trigger=(args.expect == "trigger"))
    strategy = OpencodeStrategy(timeout=args.timeout)

    print(f"trigger test: {args.skill}")
    print(f"workspace: {workspace}")
    print(f"model: {args.model or '(default)'}  variant: "
          f"{args.variant or '(none)'}  reps: {args.reps}  "
          f"timeout: {args.timeout}s")

    result = eval_batch(strategy, args.skill, case, workspace,
                        args.model, args.variant, args.reps)
    print_report(args.skill, workspace, args.model, args.variant,
                 args.reps, args.timeout, result)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="evaluator.py")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--skill", required=True)
    run.add_argument("--workspace", required=True)
    run.add_argument("--query", required=True)
    run.add_argument("--expect", required=True,
                     choices=["trigger", "not-trigger"])
    run.add_argument("--model")
    run.add_argument("--variant")
    run.add_argument("--reps", type=int, default=10)
    run.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()
    return cmd_run(args)


if __name__ == "__main__":
    sys.exit(main())
