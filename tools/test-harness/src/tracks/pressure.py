"""Pressure track: suite + evidence + meta + scored-check."""

import argparse
import json
import sys
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

# Per-run prompt assembly: the prompt never contains the rule statement,
# the compliant option, or any hint that this is a test — the answer
# contract lives in the agent body. The green arm injects the snapshotted
# skill body (frontmatter stripped by the driver) as "Project conventions".
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
        """The track keys merged into base_config: scenarios path, arm,
        and skill_file on green runs."""
        config = {"scenarios": str(Path(args.scenarios)), "arm": args.arm}
        if args.skill_file is not None:
            config["skill_file"] = args.skill_file
        return config

    def done_line(self, n: int, out: Path) -> str:
        """The final emit line: entry count and output path."""
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
