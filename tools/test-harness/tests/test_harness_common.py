#!/usr/bin/env python3
"""Tests for the shared campaign plumbing in evaluator.py (the "Shared
campaign plumbing" section): run_rep_batched's abort policy,
validate_eval_agent's pre-spend gate, counts_gate, union_results, and the
evidence commands' envelope errors. Cases the three tracks pin with only
vocabulary differing are consolidated here as one test per track, sharing
a parameterized helper; per-track policy (vocabularies, prompt bytes, arm
rules) stays in test_retrieval.py / test_shape.py / test_pressure.py.
Stdlib only; no harness commands are ever invoked (zero model spend).
"""

import argparse
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import cast

import evaluator
from src.common import (
    counts_gate,
    run_rep_batched,
    union_results,
    validate_eval_agent,
)
from src.strategies import EvalStrategy, HarnessExecutionError
from src.tracks import (
    TRACKS,
    _pressure_union_hook,
    _retrieval_union_hook,
    _shape_union_hook,
)

# The eval agent each track installs through the shared pre-spend gate.
TRACK_AGENTS = {
    "retrieval": "retrieval-evaluator",
    "shape": "shape-evaluator",
    "pressure": "pressure-evaluator",
}

# Count-gate vocabularies: argparse dests (underscores) vs scored result
# names (hyphens where the track uses them).
COUNTS_VOCABULARY = {
    "retrieval": {
        "arg_names": ("passes", "fails", "gaps", "voids"),
        "result_names": ("pass", "fail", "gap", "void"),
    },
    "shape": {
        "arg_names": ("adopted", "no_failure", "unresolved", "voids"),
        "result_names": ("adopted", "no-failure", "unresolved", "void"),
    },
    "pressure": {
        "arg_names": ("bulletproof", "no_failure", "unresolved", "voids"),
        "result_names": ("bulletproof", "no-failure", "unresolved", "void"),
    },
}

# The evidence command per track and its extra argparse defaults.
EVIDENCE_COMMANDS = {
    "retrieval": ("cmd_retrieval_evidence", {"entry": None}),
    "shape": (
        "cmd_shape_evidence",
        {"entry": None, "arm": None, "compare": False},
    ),
    "pressure": ("cmd_pressure_evidence", {"entry": None, "arm": None}),
}


def cmd_retrieval_evidence(args):
    return evaluator.cmd_evidence(TRACKS["retrieval-test"], args)


def cmd_shape_evidence(args):
    return evaluator.cmd_evidence(TRACKS["shape-test"], args)


def cmd_pressure_evidence(args):
    return evaluator.cmd_evidence(TRACKS["pressure-test"], args)


class RunRepBatchedTests(unittest.TestCase):
    """run_rep_batched: the smoke rep runs alone and a harness error in
    the smoke rep or any batch aborts with the exact stderr lines and
    exit 1; a clean run returns every rep's record in order. Shared by
    the retrieval, shape, and pressure tracks (the trigger track keeps
    its own loop, pinned in test_evaluator.py)."""

    def test_smoke_rep_error_aborts_with_exact_message(self):
        def run_one(n):
            raise HarnessExecutionError("provider 429", "s1")

        stderr = io.StringIO()
        with (
            redirect_stderr(stderr),
            redirect_stdout(io.StringIO()),
            self.assertRaises(SystemExit) as cm,
        ):
            run_rep_batched(run_one, 3, " x ")
        self.assertEqual(cm.exception.code, 1)
        self.assertEqual(
            stderr.getvalue(),
            "error: [ x ] harness could not execute the query: "
            "provider 429 [session s1]\n",
        )

    def test_batch_error_aborts_with_first_error_and_batch_line(self):
        def run_one(n):
            if n == 2:
                raise HarnessExecutionError("provider 429", "s2")
            return {"rep": n}

        stderr = io.StringIO()
        with (
            redirect_stderr(stderr),
            redirect_stdout(io.StringIO()),
            self.assertRaises(SystemExit) as cm,
        ):
            run_rep_batched(run_one, 3, " x ")
        self.assertEqual(cm.exception.code, 1)
        self.assertIn(
            "error: [ x ] rep 2 could not execute: "
            "provider 429 [session s2]",
            stderr.getvalue(),
        )
        self.assertIn("error: batch aborted\n", stderr.getvalue())

    def test_clean_run_returns_records_in_rep_order(self):
        def run_one(n):
            return {"rep": n}

        with redirect_stdout(io.StringIO()):
            runs = run_rep_batched(run_one, 3, " x ")
        self.assertEqual(runs, [{"rep": 1}, {"rep": 2}, {"rep": 3}])


class AgentGateTests(unittest.TestCase):
    """validate_eval_agent: the pre-spend gate every campaign suite runs
    before any harness invocation — the agent file must exist, its
    frontmatter name must match, and it must pin no model config. Moved
    out of the shape/pressure pre-spend gate suites and parameterized by
    track agent; the retrieval parameter sets are new coverage (the
    retrieval suite runs the same gate for both of its arms)."""

    class _Probe:
        def agent_file(self, agents_dir, base):
            return Path(agents_dir) / f"{base}.opencode.md"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.agents_dir = Path(self.tmp.name) / "agents"
        self.agents_dir.mkdir()
        # validate_eval_agent types its probe as EvalStrategy; the gate
        # only calls agent_file(), which _Probe implements.
        self.probe = cast(EvalStrategy, self._Probe())

    def _write_agent(self, name, body):
        agent_file = self.agents_dir / f"{name}.opencode.md"
        agent_file.write_text(body)
        return agent_file

    def _assert_aborts(self, name, body, expected_err):
        agent_file = self._write_agent(name, body)
        stderr = io.StringIO()
        with (
            redirect_stderr(stderr),
            self.assertRaises(SystemExit) as cm,
        ):
            validate_eval_agent(self.probe, self.agents_dir, name)
        self.assertEqual(cm.exception.code, 1)
        self.assertEqual(stderr.getvalue(), expected_err.format(f=agent_file))

    def _assert_passes(self, name):
        agent_file = self._write_agent(
            name, f"---\nname: {name}\nmode: primary\n---\nbody\n"
        )
        self.assertEqual(
            validate_eval_agent(self.probe, self.agents_dir, name),
            agent_file,
        )

    def test_agent_gate_missing_file_aborts(self):
        for name in TRACK_AGENTS.values():
            with self.subTest(agent=name):
                stderr = io.StringIO()
                with (
                    redirect_stderr(stderr),
                    self.assertRaises(SystemExit) as cm,
                ):
                    validate_eval_agent(self.probe, self.agents_dir, name)
                self.assertEqual(cm.exception.code, 1)
                self.assertEqual(
                    stderr.getvalue(),
                    "error: evaluator agent file missing: "
                    f"{self.agents_dir / (name + '.opencode.md')}\n",
                )

    def test_agent_gate_name_mismatch_aborts(self):
        for name in TRACK_AGENTS.values():
            with self.subTest(agent=name):
                self._assert_aborts(
                    name,
                    "---\nname: someone-else\n---\nbody\n",
                    "error: agent file {f}: frontmatter name "
                    "'someone-else' does not match expected "
                    f"'{name}'\n",
                )

    def test_agent_gate_model_pin_aborts(self):
        for name in TRACK_AGENTS.values():
            with self.subTest(agent=name):
                self._assert_aborts(
                    name,
                    f"---\nname: {name}\nmodel: gpt-x\n---\nbody\n",
                    "error: agent file {f} pins model config (model); "
                    "eval agents must not pin model/variant/temperature/"
                    "top_p — selection flows through --model/--variant "
                    "only\n",
                )

    def test_agent_gate_accepts_valid_agent(self):
        for name in TRACK_AGENTS.values():
            with self.subTest(agent=name):
                self._assert_passes(name)


class CountsGateTests(unittest.TestCase):
    """counts_gate: when the record-step counts are given they must be
    all four together and equal the scored sums. Moved out of the three
    per-track scored-check suites and parameterized by track vocabulary;
    every previously pinned scenario (matching passes, mismatch
    rejected, partial rejected) stays pinned per track."""

    def _entries(self, track):
        rn = COUNTS_VOCABULARY[track]["result_names"]
        return [{"id": "a", "result": rn[0]}, {"id": "b", "result": rn[1]}]

    def _args(self, track, **counts):
        arg_names = COUNTS_VOCABULARY[track]["arg_names"]
        args = argparse.Namespace(**{n: counts.get(n) for n in arg_names})
        return args

    def _assert_matching_passes(self, track):
        arg_names = COUNTS_VOCABULARY[track]["arg_names"]
        rc = counts_gate(
            self._args(track, **dict(zip(arg_names, (1, 1, 0, 0)))),
            self._entries(track),
            arg_names,
            COUNTS_VOCABULARY[track]["result_names"],
        )
        self.assertIsNone(rc)

    def _assert_mismatch_rejected(self, track):
        arg_names = COUNTS_VOCABULARY[track]["arg_names"]
        result_names = COUNTS_VOCABULARY[track]["result_names"]
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            rc = counts_gate(
                self._args(track, **dict(zip(arg_names, (2, 0, 0, 0)))),
                self._entries(track),
                arg_names,
                result_names,
            )
        self.assertEqual(rc, 1)
        computed = " / ".join(
            f"{n} {r}" for n, r in zip((1, 1, 0, 0), result_names)
        )
        got = " / ".join(
            f"{n} {r}" for n, r in zip((2, 0, 0, 0), result_names)
        )
        self.assertEqual(
            stderr.getvalue(),
            "error: counts do not match scored results: "
            f"computed {computed}, got {got}\n",
        )

    def _assert_partial_rejected(self, track):
        arg_names = COUNTS_VOCABULARY[track]["arg_names"]
        flags = "/".join(f"--{n.replace('_', '-')}" for n in arg_names)
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            rc = counts_gate(
                self._args(track, **{arg_names[0]: 1}),
                self._entries(track),
                arg_names,
                COUNTS_VOCABULARY[track]["result_names"],
            )
        self.assertEqual(rc, 1)
        self.assertEqual(
            stderr.getvalue(), f"error: {flags} must be given together\n"
        )

    def test_counts_gate_matching_passes_retrieval(self):
        self._assert_matching_passes("retrieval")

    def test_counts_gate_matching_passes_shape(self):
        self._assert_matching_passes("shape")

    def test_counts_gate_matching_passes_pressure(self):
        self._assert_matching_passes("pressure")

    def test_counts_gate_mismatch_rejected_retrieval(self):
        self._assert_mismatch_rejected("retrieval")

    def test_counts_gate_mismatch_rejected_shape(self):
        self._assert_mismatch_rejected("shape")

    def test_counts_gate_mismatch_rejected_pressure(self):
        self._assert_mismatch_rejected("pressure")

    def test_counts_gate_partial_rejected_retrieval(self):
        self._assert_partial_rejected("retrieval")

    def test_counts_gate_partial_rejected_shape(self):
        self._assert_partial_rejected("shape")

    def test_counts_gate_partial_rejected_pressure(self):
        self._assert_partial_rejected("pressure")


class UnionResultsTests(unittest.TestCase):
    """union_results: an id appearing in N results files enters the union
    exactly once, with its arm keys unioned across files. Moved out of
    the shape/pressure scored-check suites and parameterized by track;
    the retrieval parameter set is new coverage (retrieval passes a
    single --results and ignores the arm map)."""

    def _fixtures(self, track, root):
        if track == "retrieval":
            first = [
                {"id": "a", "expect": ["b1"]},
                {"id": "b", "expect": []},
            ]
            second = [{"id": "a", "expect": ["b2"]}, {"id": "c"}]
        elif track == "shape":
            first = [
                {"id": "a", "kind": "shaping", "arms": {"v0": {"runs": []}}},
                {"id": "p", "kind": "pattern", "arms": {"v0": {"runs": []}}},
            ]
            second = [
                {
                    "id": "a",
                    "kind": "shaping",
                    "arms": {"v1": {"runs": []}, "v2": {"runs": []}},
                }
            ]
        else:
            first = [
                {"id": "a", "arms": {"red": {"runs": []}}},
                {"id": "n", "arms": {"red": {"runs": []}}},
            ]
            second = [{"id": "a", "arms": {"green": {"runs": []}}}]
        f1 = root / f"{track}-1.json"
        f2 = root / f"{track}-2.json"
        f1.write_text(json.dumps({"entries": first}))
        f2.write_text(json.dumps({"entries": second}))
        return [str(f1), str(f2)]

    def _assert_dedupe(self, track, expected_ids, expected_arms):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        paths = self._fixtures(track, Path(tmp.name))
        hook = {
            "retrieval": _retrieval_union_hook,
            "shape": _shape_union_hook,
            "pressure": _pressure_union_hook,
        }[track]
        out = union_results(paths, track, entry_hook=hook)
        if isinstance(out, str):
            self.fail(f"union_results returned an error: {out}")
        ids, arms, extras = out
        self.assertEqual(ids, expected_ids)
        self.assertEqual(len(ids), len(set(ids)))
        for eid, arm_set in expected_arms.items():
            self.assertEqual(arms[eid], arm_set)
        if track == "shape":
            self.assertEqual(extras["kinds"], {"a": "shaping", "p": "pattern"})
        if track == "retrieval":
            self.assertEqual(extras["expect"], {"a": ["b2"], "b": [], "c": []})

    def test_union_dedupe_retrieval(self):
        self._assert_dedupe("retrieval", ["a", "b", "c"], {})

    def test_union_dedupe_shape(self):
        self._assert_dedupe(
            "shape", ["a", "p"], {"a": {"v0", "v1", "v2"}, "p": {"v0"}}
        )

    def test_union_dedupe_pressure(self):
        self._assert_dedupe(
            "pressure", ["a", "n"], {"a": {"red", "green"}, "n": {"red"}}
        )


class EvidenceEnvelopeTests(unittest.TestCase):
    """The evidence commands' shared envelope: a missing results file or
    a non-list 'entries' envelope exits 1 with the exact track-qualified
    message. Moved out of the per-track evidence suites and parameterized
    by track; the retrieval missing-file case is new coverage."""

    def _run(self, track, results_path):
        cmd, extra = EVIDENCE_COMMANDS[track]
        args = argparse.Namespace(results=str(results_path), **extra)
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = globals()[cmd](args)
        return rc

    def _assert_malformed_envelope(self, track):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "results.json"
        path.write_text('{"entries": "nope"}')
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            rc = self._run(track, path)
        self.assertEqual(rc, 1)
        self.assertEqual(
            stderr.getvalue(),
            f"error: {path}: not a {track}-suite results file "
            "(missing 'entries' list)\n",
        )

    def _assert_missing_file(self, track):
        path = Path(self._tmpdir()) / "nope.json"
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            rc = self._run(track, path)
        self.assertEqual(rc, 1)
        self.assertEqual(
            stderr.getvalue(), f"error: results file not found: {path}\n"
        )

    def _tmpdir(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return tmp.name

    def test_evidence_malformed_envelope_rejected_retrieval(self):
        self._assert_malformed_envelope("retrieval")

    def test_evidence_malformed_envelope_rejected_shape(self):
        self._assert_malformed_envelope("shape")

    def test_evidence_malformed_envelope_rejected_pressure(self):
        self._assert_malformed_envelope("pressure")

    def test_evidence_missing_file_rejected_retrieval(self):
        self._assert_missing_file("retrieval")

    def test_evidence_missing_file_rejected_shape(self):
        self._assert_missing_file("shape")

    def test_evidence_missing_file_rejected_pressure(self):
        self._assert_missing_file("pressure")


# The scored-check command per track and its count-gate argparse dests
# (all None in these tests: the emit path never reaches the gate).
SCORED_COMMANDS = {
    "retrieval": ("cmd_scored_check", ("passes", "fails", "gaps", "voids")),
    "shape": (
        "cmd_shape_scored_check",
        ("adopted", "no_failure", "unresolved", "voids"),
    ),
    "pressure": (
        "cmd_pressure_scored_check",
        ("bulletproof", "no_failure", "unresolved", "voids"),
    ),
}


def cmd_scored_check(args):
    return evaluator.cmd_scored_check(args)


def cmd_shape_scored_check(args):
    return evaluator._scored_check(TRACKS["shape-test"], args)


def cmd_pressure_scored_check(args):
    return evaluator._scored_check(TRACKS["pressure-test"], args)


class SkeletonEmitTests(unittest.TestCase):
    """--emit-skeleton on the three scored-checks: the emit writes an
    object envelope with every union id exactly once, mechanically
    derivable fields pre-filled (shape kind + per-arm marker_counts,
    pressure verdict_constraint hints), and every judgment field null;
    the existing checks reject the nulls (emit rc 0, check rc 1); and
    --scored / --emit-skeleton conflict or are both absent. The
    retrieval expect rubric is never written into the skeleton."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def _results(self, track):
        """Per-track committed-shaped results files. Returns the
        --results value (str for retrieval, list otherwise)."""
        if track == "retrieval":
            path = self.root / "results.json"
            path.write_text(
                json.dumps(
                    {
                        "config": {"skill": "demo-skill"},
                        "entries": [
                            {"id": "a", "expect": ["b1", "b2"]},
                            {"id": "b", "expect": []},
                        ],
                    }
                )
            )
            return str(path)
        if track == "shape":
            control = self.root / "control.json"
            control.write_text(
                json.dumps(
                    {
                        "config": {"skill": "demo-skill"},
                        "entries": [
                            {
                                "id": "a",
                                "kind": "shaping",
                                "markers": {"inline_style": "style"},
                                "arms": {
                                    "v0": {
                                        "runs": [
                                            {"answer_text": "style one\nxx"},
                                            {"answer_text": "clean"},
                                        ]
                                    }
                                },
                            }
                        ],
                    }
                )
            )
            variants = self.root / "variants.json"
            variants.write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "id": "a",
                                "kind": "shaping",
                                "markers": {"inline_style": "style"},
                                "arms": {
                                    "v1": {"runs": [{"answer_text": "style"}]},
                                    "v2": {"runs": [{"answer_text": "ok"}]},
                                },
                            },
                            {
                                "id": "p",
                                "kind": "pattern",
                                "markers": {"hover_hack": "onMouse"},
                                "arms": {
                                    "v1": {
                                        "runs": [
                                            {"answer_text": "onMouseEnter"}
                                        ]
                                    }
                                },
                            },
                        ]
                    }
                )
            )
            # A restraint rerun of v2: same arm name across files sums
            # (order-independent totals; the driver narrows by hand).
            restraint = self.root / "restraint.json"
            restraint.write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "id": "a",
                                "kind": "shaping",
                                "markers": {"inline_style": "style"},
                                "arms": {
                                    "v2": {"runs": [{"answer_text": "style!"}]}
                                },
                            }
                        ]
                    }
                )
            )
            return [str(control), str(variants), str(restraint)]
        red = self.root / "red.json"
        red.write_text(
            json.dumps(
                {
                    "config": {"skill": "demo-skill"},
                    "entries": [
                        {"id": "r1", "arms": {"red": {"runs": []}}},
                        {"id": "r2", "arms": {"red": {"runs": []}}},
                    ],
                }
            )
        )
        green = self.root / "green.json"
        green.write_text(
            json.dumps(
                {"entries": [{"id": "r1", "arms": {"green": {"runs": []}}}]}
            )
        )
        return [str(red), str(green)]

    def _run(self, track, results, *, scored=None, emit=None):
        cmd, counts_names = SCORED_COMMANDS[track]
        ns = {"scored": scored, "emit_skeleton": emit}
        if track == "retrieval":
            ns["results"] = results
        else:
            ns["results"] = list(results)
        for name in counts_names:
            ns[name] = None
        args = argparse.Namespace(**ns)
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            rc = globals()[cmd](args)
        return rc, stdout.getvalue(), stderr.getvalue()

    def _emit(self, track):
        results = self._results(track)
        out = self.root / "skeleton.json"
        rc, stdout, stderr = self._run(track, results, emit=str(out))
        self.assertEqual(rc, 0, stderr)
        self.assertIn("wrote skeleton:", stdout)
        return json.loads(out.read_text())

    def test_emit_skeleton_retrieval(self):
        doc = self._emit("retrieval")
        self.assertEqual(set(doc), {"campaign", "skill", "entries"})
        # Parent dir is not campaign-*: placeholder; skill from config.
        self.assertEqual(doc["campaign"], "pilot")
        self.assertEqual(doc["skill"], "demo-skill")
        self.assertEqual([e["id"] for e in doc["entries"]], ["a", "b"])
        for entry in doc["entries"]:
            for field in (
                "result",
                "classification",
                "control",
                "ablation_flag",
                "missed_bullets",
                "notes",
            ):
                self.assertIsNone(entry[field])
            # The expect rubric is judging context, never scored output.
            self.assertNotIn("expect", entry)

    def test_emit_skeleton_shape(self):
        doc = self._emit("shape")
        self.assertEqual(set(doc), {"entries"})
        by_id = {e["id"]: e for e in doc["entries"]}
        self.assertEqual(list(by_id), ["a", "p"])
        self.assertEqual(by_id["a"]["kind"], "shaping")
        self.assertEqual(by_id["p"]["kind"], "pattern")
        # v2 appears in two files: the counts sum across occurrences.
        self.assertEqual(
            by_id["a"]["marker_counts"],
            {
                "v0": {"inline_style": 1},
                "v1": {"inline_style": 1},
                "v2": {"inline_style": 1},
            },
        )
        self.assertEqual(
            by_id["p"]["marker_counts"], {"v1": {"hover_hack": 1}}
        )
        for entry in by_id.values():
            for field in ("result", "adopted_arm", "restraint_gate", "notes"):
                self.assertIsNone(entry[field])

    def test_emit_skeleton_pressure(self):
        doc = self._emit("pressure")
        self.assertEqual(set(doc), {"campaign", "skill", "entries"})
        self.assertEqual(doc["campaign"], "pilot")
        self.assertEqual(doc["skill"], "demo-skill")
        by_id = {e["id"]: e for e in doc["entries"]}
        self.assertEqual(list(by_id), ["r1", "r2"])
        # red+green implies bulletproof|unresolved; red only the others.
        self.assertEqual(
            by_id["r1"]["verdict_constraint"],
            ["bulletproof", "unresolved"],
        )
        self.assertEqual(
            by_id["r2"]["verdict_constraint"], ["no-failure", "void"]
        )
        for entry in by_id.values():
            self.assertIsNone(entry["result"])
            self.assertIsNone(entry["counters"])
            self.assertIsNone(entry["notes"])

    def test_emit_skeleton_header_campaign_derived(self):
        campaign_dir = self.root / "campaign-2099-01-01"
        campaign_dir.mkdir()
        results = self.root / "results.json"
        results.write_text(
            json.dumps(
                {
                    "config": {"skill": "demo-skill"},
                    "entries": [{"id": "a", "expect": []}],
                }
            )
        )
        nested = campaign_dir / "results.json"
        nested.write_text(results.read_text())
        out = self.root / "skel.json"
        rc, _, stderr = self._run("retrieval", str(nested), emit=str(out))
        self.assertEqual(rc, 0, stderr)
        doc = json.loads(out.read_text())
        self.assertEqual(doc["campaign"], "campaign-2099-01-01")
        self.assertEqual(doc["skill"], "demo-skill")

    def _assert_roundtrip_rejected(self, track):
        results = self._results(track)
        out = self.root / "skeleton.json"
        rc, _, stderr = self._run(track, results, emit=str(out))
        self.assertEqual(rc, 0, stderr)
        rc, _, stderr = self._run(track, results, scored=str(out))
        self.assertEqual(rc, 1)
        self.assertIn("result must be one of", stderr)

    def test_emit_then_check_rejected_retrieval(self):
        self._assert_roundtrip_rejected("retrieval")

    def test_emit_then_check_rejected_shape(self):
        self._assert_roundtrip_rejected("shape")

    def test_emit_then_check_rejected_pressure(self):
        self._assert_roundtrip_rejected("pressure")

    def _assert_conflict(self, track):
        results = self._results(track)
        out = self.root / "skeleton.json"
        rc, _, stderr = self._run(
            track, results, scored=str(out), emit=str(out)
        )
        self.assertEqual(rc, 1)
        self.assertIn(
            "--scored and --emit-skeleton are mutually exclusive", stderr
        )

    def test_emit_and_scored_conflict_retrieval(self):
        self._assert_conflict("retrieval")

    def test_emit_and_scored_conflict_shape(self):
        self._assert_conflict("shape")

    def test_emit_and_scored_conflict_pressure(self):
        self._assert_conflict("pressure")

    def _assert_neither(self, track):
        rc, _, stderr = self._run(track, self._results(track))
        self.assertEqual(rc, 1)
        self.assertIn("one of --scored or --emit-skeleton is required", stderr)

    def test_neither_scored_nor_emit_retrieval(self):
        self._assert_neither("retrieval")

    def test_neither_scored_nor_emit_shape(self):
        self._assert_neither("shape")

    def test_neither_scored_nor_emit_pressure(self):
        self._assert_neither("pressure")


if __name__ == "__main__":
    unittest.main()
