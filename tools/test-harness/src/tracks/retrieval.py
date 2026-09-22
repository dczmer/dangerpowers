"""Retrieval track: suite + evidence + scored-check."""

import argparse
import re
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from src.common import (
    EvidenceError,
    _err,
    _fail,
    _session_suffix,
    emit,
    iter_evidence,
    load_entries,
    load_results_json,
    log_start,
    run_rep_batched,
    validate_eval_agent,
)
from src.strategies import EvalStrategy, HarnessExecutionError
from src.tracks.track import Track, _required

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
    """Stage the entry's fixtures into the arm workspace, substitute
    {RUN_DIR}, and return the dispatched query."""
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
    """One retrieval run's record: answer, sources block, void signals,
    and tool-call targets relative to the workspace root."""
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
    """All reps of one (entry, arm) pair via run_rep_batched, with
    arm-tagged progress lines."""
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
# scored-check. "gap" is a result value, not a classification.
RESULTS = {"pass", "fail", "gap", "void"}
CLASSIFICATIONS = {"findability", "clarity"}
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
        """The queries-file path, merged into base_config."""
        return {"queries": str(Path(args.queries))}

    def done_line(self, n: int, out: Path) -> str:
        """The final emit line: entry count and output path."""
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
