"""Shape track: suite + evidence + scored-check."""

import argparse
import re
import sys
from pathlib import Path

from src.common import (
    EvidenceError,
    _err,
    _fail,
    emit,
    iter_evidence,
    load_entries,
    load_results_json,
    log_start,
    run_rep_batched,
    validate_eval_agent,
)
from src.strategies import EvalStrategy
from src.tracks.retrieval import SOURCES_RE
from src.tracks.track import Track, _required

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


# Per-run prompt assembly: the prompt never contains the rule statement,
# the markers, or the expected shape — the answer contract lives in the
# agent body, constant across arms. Arms differ only in the injected body
# bytes; the workspace is never written, so a variant can never leak into
# another arm's run.
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
            continue  # v0-family arms are control evidence, not candidates
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
        """The track keys merged into base_config: entries/skill_file
        paths, arms, and fixture_key."""
        return {
            "entries": str(Path(args.entries)),
            "skill_file": str(Path(args.skill_file)),
            "arms": self._arms,
            "fixture_key": args.fixture_key,
        }

    def done_line(self, n: int, out: Path) -> str:
        """The final emit line: entry count and output path."""
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
