#!/usr/bin/env python3
"""Tests for evaluator.py's generic drivers: cmd_record (the frontmatter
scope, the --scored counts path, and the score-from computation),
cmd_check, and the unified --track CLI shape (the _required gate's
first-missing-flag contract, the per-track reps/timeout defaults, the
merged-parser pairing gates, and the legacy-subcommand invalid choices).
Stdlib only; no harness commands are ever invoked (zero model spend).
"""

import argparse
import contextlib
import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import evaluator
from src import strategies
from src.common import _score_counts
from src.tracks import TRACKS

SKILL = "writing-skills"


class RecordTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.skill_md = self.root / "SKILL.md"
        self.skill_md.write_text("---\nname: test-skill\n---\nbody\n")
        self.manifest = self.root / "trigger-tests" / "manifest.json"

    def tearDown(self):
        self.tmp.cleanup()

    def _record(self, **overrides) -> int:
        args = argparse.Namespace(
            skill="test-skill",
            skill_path=str(self.skill_md),
            manifest=str(self.manifest),
            score=0.81,
            campaign="campaign-2026-09-02",
            date=None,
        )
        for k, v in overrides.items():
            setattr(args, k, v)
        return evaluator.cmd_record(args)

    def test_creates_manifest_with_schema(self):
        rc = self._record()
        self.assertEqual(rc, 0)
        data = json.loads(self.manifest.read_text())
        self.assertEqual(data["skill"], "test-skill")
        entry = data["trigger-test"]
        self.assertEqual(set(entry), {"date", "checksum", "score", "campaign"})
        self.assertEqual(entry["score"], 0.81)
        self.assertEqual(entry["campaign"], "campaign-2026-09-02")

    def test_checksum_is_frontmatter_sha256(self):
        self._record()
        data = json.loads(self.manifest.read_text())
        frontmatter = evaluator.extract_frontmatter(self.skill_md.read_text())
        self.assertIsNotNone(frontmatter)
        assert frontmatter is not None  # narrowing for the type checker
        expected = "sha256:" + hashlib.sha256(frontmatter.encode()).hexdigest()
        self.assertEqual(data["trigger-test"]["checksum"], expected)

    def test_body_edit_does_not_change_checksum(self):
        self._record()
        first = json.loads(self.manifest.read_text())["trigger-test"]
        self.skill_md.write_text("---\nname: test-skill\n---\nnew body\n")
        self._record()
        second = json.loads(self.manifest.read_text())["trigger-test"]
        self.assertEqual(first["checksum"], second["checksum"])

    def test_frontmatter_edit_changes_checksum(self):
        self._record()
        first = json.loads(self.manifest.read_text())["trigger-test"]
        self.skill_md.write_text(
            "---\nname: test-skill\ndescription: x\n---" "\nbody\n"
        )
        self._record()
        second = json.loads(self.manifest.read_text())["trigger-test"]
        self.assertNotEqual(first["checksum"], second["checksum"])

    def test_missing_frontmatter_refused_untouched(self):
        self.skill_md.write_text("no frontmatter here\n")
        rc = self._record()
        self.assertEqual(rc, 1)
        self.assertFalse(self.manifest.exists())

    def test_update_preserves_unknown_keys(self):
        self.manifest.parent.mkdir(parents=True)
        self.manifest.write_text(
            json.dumps(
                {
                    "future-test": {"date": "x"},
                    "trigger-test": {
                        "date": "old",
                        "checksum": "sha256:old",
                        "score": 0.5,
                    },
                }
            )
        )
        rc = self._record(score=0.9)
        self.assertEqual(rc, 0)
        data = json.loads(self.manifest.read_text())
        self.assertEqual(data["future-test"], {"date": "x"})
        self.assertEqual(data["trigger-test"]["score"], 0.9)

    def test_malformed_manifest_refused_untouched(self):
        self.manifest.parent.mkdir(parents=True)
        self.manifest.write_text("not json")
        rc = self._record()
        self.assertEqual(rc, 1)
        self.assertEqual(self.manifest.read_text(), "not json")

    def test_missing_skill_file(self):
        rc = self._record(skill_path=str(self.root / "no-such-SKILL.md"))
        self.assertEqual(rc, 1)
        self.assertFalse(self.manifest.exists())

    def test_campaign_omitted_when_not_given(self):
        rc = self._record(campaign=None)
        self.assertEqual(rc, 0)
        entry = json.loads(self.manifest.read_text())["trigger-test"]
        self.assertNotIn("campaign", entry)

    def test_score_out_of_range(self):
        self.assertEqual(self._record(score=1.5), 1)
        self.assertFalse(self.manifest.exists())


class RecordScoredTests(unittest.TestCase):
    """record --scope dir --scored: the manifest counts come from the
    scored.json result sums (one source of truth), the track is detected
    from discriminating signals and never guessed, an explicit --track is
    checked against the detection, --ablations passes through verbatim,
    and the counts flags are rejected (`counts flags are replaced by
    --scored`)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.skill_dir = self.root / "skill"
        self.skill_dir.mkdir()
        (self.skill_dir / "SKILL.md").write_text(
            "---\nname: test-skill\n---\nbody\n"
        )
        self.manifest = self.root / "manifest.json"
        self.scored = self.root / "scored.json"

    def tearDown(self):
        self.tmp.cleanup()

    def _write_scored(self, entries):
        self.scored.write_text(json.dumps({"entries": entries}))

    def _record(self, **overrides) -> tuple[int, str, str]:
        args = argparse.Namespace(
            skill="test-skill",
            skill_path=str(self.skill_dir),
            manifest=str(self.manifest),
            scope="dir",
            track=None,
            score=None,
            scored=str(self.scored),
            passes=None,
            fails=None,
            gaps=None,
            voids=None,
            adopted=None,
            bulletproof=None,
            no_failure=None,
            unresolved=None,
            ablations=None,
            campaign="campaign-2026-09-14",
            date="2026-09-14",
        )
        for k, v in overrides.items():
            setattr(args, k, v)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = evaluator.cmd_record(args)
        return rc, out.getvalue(), err.getvalue()

    @staticmethod
    def _retrieval_entry(eid, result):
        return {
            "id": eid,
            "result": result,
            "classification": "findability" if result == "fail" else None,
            "control": "pass",
            "ablation_flag": True,
            "missed_bullets": ["b"] if result in ("fail", "gap") else None,
            "notes": None,
        }

    def test_scored_retrieval_sums_and_key(self):
        self._write_scored(
            [
                self._retrieval_entry("a", "pass"),
                self._retrieval_entry("b", "pass"),
                self._retrieval_entry("c", "fail"),
                self._retrieval_entry("d", "gap"),
                self._retrieval_entry("e", "void"),
            ]
        )
        rc, _out, err = self._record()
        self.assertEqual(rc, 0)
        entry = json.loads(self.manifest.read_text())["retrieval-test"]
        self.assertEqual(entry["passes"], 2)
        self.assertEqual(entry["fails"], 1)
        self.assertEqual(entry["gaps"], 1)
        self.assertEqual(entry["voids"], 1)
        self.assertEqual(
            entry["checksum"], evaluator.hash_skill_dir(self.skill_dir)
        )
        self.assertNotIn("deprecated", err)

    def test_scored_shape_sums_and_key(self):
        self._write_scored(
            [
                {
                    "id": "a",
                    "kind": "shaping",
                    "result": "adopted",
                    "adopted_arm": "v1",
                    "restraint_gate": None,
                    "marker_counts": {},
                    "notes": None,
                },
                {"id": "b", "kind": "pattern", "result": "no-failure"},
            ]
        )
        rc, _out, _err = self._record()
        self.assertEqual(rc, 0)
        entry = json.loads(self.manifest.read_text())["shape-test"]
        self.assertEqual(entry["adopted"], 1)
        self.assertEqual(entry["no-failure"], 1)
        self.assertEqual(entry["unresolved"], 0)
        self.assertEqual(entry["voids"], 0)

    def test_scored_pressure_sums_and_key(self):
        self._write_scored(
            [
                {"id": "a", "result": "bulletproof"},
                {"id": "b", "result": "no-failure"},
                {"id": "c", "result": "void"},
            ]
        )
        rc, _out, _err = self._record()
        self.assertEqual(rc, 0)
        entry = json.loads(self.manifest.read_text())["pressure-test"]
        self.assertEqual(entry["bulletproof"], 1)
        self.assertEqual(entry["no-failure"], 1)
        self.assertEqual(entry["unresolved"], 0)
        self.assertEqual(entry["voids"], 1)

    def test_scored_with_counts_flags_rejected(self):
        self._write_scored([self._retrieval_entry("a", "pass")])
        rc, _out, err = self._record(passes=1)
        self.assertEqual(rc, 1)
        self.assertIn("counts flags are replaced by --scored", err)
        self.assertFalse(self.manifest.exists())

    def test_scored_all_void_ambiguous_asks_for_track(self):
        # void + notes alone discriminate nothing: shape and pressure
        # share the whole vocabulary, retrieval cannot be proven either.
        self._write_scored(
            [{"id": "a", "result": "void"}, {"id": "b", "result": "void"}]
        )
        rc, _out, err = self._record()
        self.assertEqual(rc, 1)
        self.assertIn("--track", err)
        self.assertFalse(self.manifest.exists())

    def test_scored_all_void_with_explicit_track_passes(self):
        self._write_scored([{"id": "a", "result": "void"}])
        rc, _out, _err = self._record(track="pressure-test")
        self.assertEqual(rc, 0)
        entry = json.loads(self.manifest.read_text())["pressure-test"]
        self.assertEqual(entry["voids"], 1)

    def test_scored_explicit_track_mismatch_rejected(self):
        self._write_scored([{"id": "a", "result": "adopted"}])
        rc, _out, err = self._record(track="pressure-test")
        self.assertEqual(rc, 1)
        self.assertIn("does not match the scored results", err)
        self.assertFalse(self.manifest.exists())

    def test_scored_explicit_track_consistent_passes(self):
        self._write_scored([{"id": "a", "result": "adopted"}])
        rc, _out, _err = self._record(track="shape-test")
        self.assertEqual(rc, 0)
        self.assertIn("shape-test", json.loads(self.manifest.read_text()))

    def test_scored_mixed_vocabularies_rejected(self):
        self._write_scored(
            [
                {"id": "a", "result": "bulletproof"},
                {"id": "b", "result": "adopted"},
            ]
        )
        rc, _out, err = self._record()
        self.assertEqual(rc, 1)
        self.assertIn("refusing to guess", err)
        self.assertFalse(self.manifest.exists())

    def test_scored_result_outside_vocabulary_rejected(self):
        entries = [self._retrieval_entry("a", "pass")]
        entries[0]["result"] = "weird"
        self._write_scored(entries)
        rc, _out, err = self._record()
        self.assertEqual(rc, 1)
        self.assertIn("not in the retrieval-test vocabulary", err)

    def test_ablations_passthrough_on_scored_path(self):
        self._write_scored([self._retrieval_entry("a", "pass")])
        rc, _out, _err = self._record(ablations="arm-rerun-of-v2")
        self.assertEqual(rc, 0)
        entry = json.loads(self.manifest.read_text())["retrieval-test"]
        self.assertEqual(entry["ablations"], "arm-rerun-of-v2")
        self.assertEqual(entry["passes"], 1)

    def test_counts_flags_without_scored_rejected(self):
        # The counts flags stay parseable but can no longer record:
        # without --scored they fail with the exact replacement error.
        rc, _out, err = self._record(scored=None, passes=1, fails=0)
        self.assertEqual(rc, 1)
        self.assertIn("counts flags are replaced by --scored", err)
        self.assertFalse(self.manifest.exists())


class RecordScoreFromTests(unittest.TestCase):
    """record --score-from: the trigger score is computed once, in the
    script (Wilson bound over the results file's recorded outcomes), and
    flows into the --scope frontmatter record; the driver only chooses
    which results file to pass (validate results when a validate split
    ran, else the winner iteration's train results)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.skill_md = self.root / "SKILL.md"
        self.skill_md.write_text("---\nname: test-skill\n---\nbody\n")
        self.manifest = self.root / "manifest.json"
        self.results = self.root / "iter-2-train.json"

    def tearDown(self):
        self.tmp.cleanup()

    def _write_results(self, queries):
        self.results.write_text(json.dumps({"queries": queries}))

    @staticmethod
    def _query(passed, failed, void=0):
        return {"passed": passed, "failed": failed, "void": void}

    def _record(self, **overrides) -> tuple[int, str]:
        args = argparse.Namespace(
            skill="test-skill",
            skill_path=str(self.skill_md),
            manifest=str(self.manifest),
            scope="frontmatter",
            track=None,
            score=None,
            scored=None,
            score_from=str(self.results),
            passes=None,
            fails=None,
            gaps=None,
            voids=None,
            adopted=None,
            bulletproof=None,
            no_failure=None,
            unresolved=None,
            ablations=None,
            campaign="campaign-2026-09-02",
            date=None,
        )
        for k, v in overrides.items():
            setattr(args, k, v)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = evaluator.cmd_record(args)
        return rc, out.getvalue()

    def test_score_from_computed_into_frontmatter_record(self):
        self._write_results(
            [
                self._query(2, 0),
                self._query(1, 1),
                self._query(0, 2, void=3),
            ]
        )
        rc, _out = self._record()
        self.assertEqual(rc, 0)
        entry = json.loads(self.manifest.read_text())["trigger-test"]
        _low, _high, expected = _score_counts(3, 3)
        self.assertIsNotNone(expected)
        assert expected is not None  # narrowing for the type checker
        self.assertEqual(entry["score"], expected)
        self.assertEqual(entry["campaign"], "campaign-2026-09-02")

    def test_score_from_works_on_validate_less_file(self):
        # The documented fallback: no validate split, so the driver
        # passes the winner iteration's train file — same computation.
        self._write_results([self._query(4, 1)])
        rc, _out = self._record()
        self.assertEqual(rc, 0)
        entry = json.loads(self.manifest.read_text())["trigger-test"]
        _low, _high, expected = _score_counts(4, 1)
        self.assertIsNotNone(expected)
        assert expected is not None
        self.assertEqual(entry["score"], expected)

    def test_score_and_score_from_conflict(self):
        self._write_results([self._query(1, 0)])
        rc, _out = self._record(score=0.9)
        self.assertEqual(rc, 1)
        self.assertFalse(self.manifest.exists())

    def test_score_from_with_scope_dir_rejected(self):
        self._write_results([self._query(1, 0)])
        skill_dir = self.root / "skill-dir"
        skill_dir.mkdir()
        rc, _out = self._record(scope="dir", skill_path=str(skill_dir))
        self.assertEqual(rc, 1)
        self.assertFalse(self.manifest.exists())

    def test_score_from_missing_file(self):
        rc, _out = self._record(score_from=str(self.root / "no.json"))
        self.assertEqual(rc, 1)
        self.assertFalse(self.manifest.exists())

    def test_score_from_not_a_results_file(self):
        self.results.write_text(json.dumps({"entries": []}))
        rc, _out = self._record()
        self.assertEqual(rc, 1)
        self.assertFalse(self.manifest.exists())

    def test_score_from_all_void_outcomes(self):
        self._write_results([self._query(0, 0, void=3)])
        rc, _out = self._record()
        self.assertEqual(rc, 1)
        self.assertFalse(self.manifest.exists())


class CheckCommandTests(unittest.TestCase):
    def _cmd_check(self, model: str | None):
        ns = argparse.Namespace(harness="opencode", model=model)
        buf = io.StringIO()
        with mock.patch.object(evaluator, "check_harness") as check_mock:
            with (
                contextlib.redirect_stdout(buf),
                contextlib.redirect_stderr(buf),
            ):
                rc = evaluator.cmd_check(ns)
        return rc, check_mock, buf.getvalue()

    def test_model_forwarded_to_check_harness(self):
        rc, check_mock, out = self._cmd_check("opencode/gpt-5")
        self.assertEqual(rc, 0)
        check_mock.assert_called_once_with(
            "opencode", strategies.OpencodeStrategy, "opencode/gpt-5"
        )

    def test_model_omitted_defaults_to_none(self):
        rc, check_mock, _ = self._cmd_check(None)
        self.assertEqual(rc, 0)
        check_mock.assert_called_once_with(
            "opencode", strategies.OpencodeStrategy, None
        )


class _ProbeStrategy:
    """Satisfies validate_eval_agent's agent_file probe in gate tests
    without any harness binary."""

    def __init__(self, timeout=30):
        self.timeout = timeout

    def agent_file(self, agents_dir, base):
        return Path(agents_dir) / f"{base}.opencode.md"


class UnifiedCliGateTests(unittest.TestCase):
    """The unified --track CLI (plan §3.3/§3.4): the _required gate's
    first-missing-flag contract, the per-track reps/timeout defaults
    applied when the merged parser leaves them None, and the pairing
    gates only a merged parser makes reachable. Zero harness runs: the
    preflight is stubbed and every assertion fires pre-spend."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.agents_dir = self.root / "agents"
        self.agents_dir.mkdir()
        for base in (
            "trigger-evaluator",
            "retrieval-evaluator",
            "retrieval-control",
            "shape-evaluator",
            "pressure-evaluator",
        ):
            (self.agents_dir / f"{base}.opencode.md").write_text(
                f"---\nname: {base}\n---\n# Agent\n"
            )

    def tearDown(self):
        self.tmp.cleanup()

    def _gates(self, track, args):
        """Run one track's pre-spend gates with the harness preflight
        stubbed. Tracks are singletons: the previous preflight is
        restored so later tests keep their historical patch point."""
        preflight = track._harness_preflight
        track._harness_preflight = lambda *a: None
        try:
            return track.pre_spend_gates(args, _ProbeStrategy)
        finally:
            track._harness_preflight = preflight

    def _assert_required_gate(self, track_name, args, first_flag):
        err = io.StringIO()
        with (
            contextlib.redirect_stderr(err),
            self.assertRaises(SystemExit) as cm,
        ):
            self._gates(TRACKS[track_name], args)
        # Runtime gate (Q7a): exit 1 with the exact message, not
        # argparse's exit-2 "the following arguments are required".
        self.assertEqual(cm.exception.code, 1)
        self.assertEqual(
            err.getvalue(),
            f"error: --{first_flag} is required with --track {track_name}\n",
        )

    def test_required_gate_first_missing_flag_wins(self):
        # Each track's declared order decides which of two missing
        # flags fires (§3.3: first missing flag wins).
        common = {
            "harness": "opencode",
            "skill": SKILL,
            "agents_dir": str(self.agents_dir),
            "model": None,
            "variant": None,
            "reps": None,
            "timeout": None,
            "out": str(self.root / "results.json"),
        }
        self._assert_required_gate(
            "trigger-test",
            argparse.Namespace(workspace=None, queries=None, **common),
            "workspace",
        )
        self._assert_required_gate(
            "retrieval-test",
            argparse.Namespace(
                skill_workspace=None,
                control_workspace=None,
                queries=None,
                **common,
            ),
            "skill-workspace",
        )
        self._assert_required_gate(
            "shape-test",
            argparse.Namespace(
                workspace=str(self.root / "ws"),
                entries=None,
                skill_file=None,
                arms=None,
                **common,
            ),
            "entries",
        )
        self._assert_required_gate(
            "pressure-test",
            argparse.Namespace(
                workspace=str(self.root / "ws"),
                scenarios=None,
                arm=None,
                **common,
            ),
            "scenarios",
        )

    def _assert_defaults(self, track_name, args, expected):
        entries = self._gates(TRACKS[track_name], args)
        self.assertNotIsInstance(entries, int)
        self.assertEqual(
            (args.reps, args.timeout),
            expected,
            f"--track {track_name} must apply its historical defaults",
        )

    def test_trigger_default_reps_timeout(self):
        ws = self.root / "trigger-ws"
        stub = ws / ".agents" / "skills" / SKILL / "SKILL.md"
        stub.parent.mkdir(parents=True)
        stub.write_text(f"---\nname: {SKILL}\n---\n")
        queries = self.root / "trigger-queries.json"
        queries.write_text("[]")
        self._assert_defaults(
            "trigger-test",
            argparse.Namespace(
                harness="opencode",
                skill=SKILL,
                agents_dir=str(self.agents_dir),
                workspace=str(ws),
                queries=str(queries),
                out=str(self.root / "trigger-results.json"),
                model=None,
                variant=None,
                reps=None,
                timeout=None,
            ),
            (3, 30),
        )

    def test_retrieval_default_reps_timeout(self):
        skill_ws = self.root / "retrieval-skill-ws"
        (skill_ws / ".agents" / "skills" / SKILL).mkdir(parents=True)
        control_ws = self.root / "retrieval-control-ws"
        control_ws.mkdir()
        queries = self.root / "retrieval-queries.json"
        queries.write_text(
            json.dumps([{"id": "a", "query": "q", "expect": ["b"]}])
        )
        self._assert_defaults(
            "retrieval-test",
            argparse.Namespace(
                harness="opencode",
                skill=SKILL,
                agents_dir=str(self.agents_dir),
                skill_workspace=str(skill_ws),
                control_workspace=str(control_ws),
                queries=str(queries),
                out=str(self.root / "retrieval-results.json"),
                model=None,
                variant=None,
                reps=None,
                timeout=None,
            ),
            (1, 120),
        )

    def test_shape_default_reps_timeout(self):
        section = "Always use CSS modules."
        skill_body = self.root / "shape-body.txt"
        skill_body.write_text("# Conventions\n\n" + section + "\n")
        entries = self.root / "shape-entries.json"
        entries.write_text(
            json.dumps(
                [
                    {
                        "id": "R-styling-01",
                        "rule": "R-styling-01",
                        "kind": "shaping",
                        "section": section,
                        "fixtures": {"application": "Build a Badge."},
                        "markers": {"inline-style": "style="},
                        "variants": {"v1": "Never use inline styles."},
                    }
                ]
            )
        )
        ws = self.root / "shape-ws"
        ws.mkdir()
        self._assert_defaults(
            "shape-test",
            argparse.Namespace(
                harness="opencode",
                skill=SKILL,
                agents_dir=str(self.agents_dir),
                workspace=str(ws),
                entries=str(entries),
                skill_file=str(skill_body),
                arms="v0",
                fixture_key="application",
                out=str(self.root / "shape-results.json"),
                model=None,
                variant=None,
                reps=None,
                timeout=None,
            ),
            (5, 120),
        )

    def test_pressure_default_reps_timeout(self):
        scenarios = self.root / "pressure-scenarios.json"
        scenarios.write_text(
            json.dumps(
                [
                    {
                        "id": "s1",
                        "rule": "R-workflow-01",
                        "statement": "no failing test, no production code",
                        "scenario": "The refactor is half done and green.",
                        "pressures": ["sunk-cost", "time", "social"],
                        "compliant_option": "A",
                    }
                ]
            )
        )
        ws = self.root / "pressure-ws"
        ws.mkdir()
        self._assert_defaults(
            "pressure-test",
            argparse.Namespace(
                harness="opencode",
                skill=SKILL,
                agents_dir=str(self.agents_dir),
                workspace=str(ws),
                scenarios=str(scenarios),
                arm="red",
                skill_file=None,
                out=str(self.root / "pressure-results.json"),
                model=None,
                variant=None,
                reps=None,
                timeout=None,
            ),
            (5, 120),
        )

    def _scored_args(self, track_name, results, **counts):
        ns = {
            "track": track_name,
            "results": results,
            "scored": str(self.root / "scored.json"),
            "emit_skeleton": None,
        }
        for dest in evaluator._ALL_COUNT_DESTS:
            ns[dest] = counts.get(dest)
        return argparse.Namespace(**ns)

    def test_scored_check_foreign_counts_flags_rejected(self):
        # Each counts vocabulary belongs to its own track; a foreign
        # flag fails with the exact merged-parser message pre-union.
        cases = (
            ("retrieval-test", {"adopted": 1}, "--adopted"),
            ("shape-test", {"passes": 1}, "--passes"),
            ("pressure-test", {"gaps": 1}, "--gaps"),
        )
        for track_name, counts, flag in cases:
            with self.subTest(track=track_name):
                err = io.StringIO()
                with contextlib.redirect_stderr(err):
                    rc = evaluator.cmd_scored_check(
                        self._scored_args(
                            track_name,
                            [str(self.root / "nope.json")],
                            **counts,
                        )
                    )
                self.assertEqual(rc, 1)
                self.assertEqual(
                    err.getvalue(),
                    f"error: counts flags {flag} are only valid with "
                    f"their own track (not --track {track_name})\n",
                )

    def test_scored_check_retrieval_rejects_multiple_results(self):
        # Retrieval's single --results contract, enforced at runtime now
        # that one parser serves every track.
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            rc = evaluator.cmd_scored_check(
                self._scored_args(
                    "retrieval-test",
                    ["a.json", "b.json"],
                )
            )
        self.assertEqual(rc, 1)
        self.assertEqual(
            err.getvalue(),
            "error: exactly one --results file is valid with --track "
            "retrieval-test\n",
        )

    def test_evidence_compare_only_on_shape(self):
        args = argparse.Namespace(
            track="trigger-test",
            results="x.json",
            entry=None,
            arm=None,
            compare=True,
        )
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            rc = evaluator.cmd_evidence(args)
        self.assertEqual(rc, 1)
        self.assertEqual(
            err.getvalue(),
            "error: --compare is only valid with --track shape-test\n",
        )

    def test_evidence_arm_only_on_shape_or_pressure(self):
        for track_name in ("trigger-test", "retrieval-test"):
            with self.subTest(track=track_name):
                args = argparse.Namespace(
                    track=track_name,
                    results="x.json",
                    entry=None,
                    arm="red",
                    compare=False,
                )
                err = io.StringIO()
                with contextlib.redirect_stderr(err):
                    rc = evaluator.cmd_evidence(args)
                self.assertEqual(rc, 1)
                self.assertEqual(
                    err.getvalue(),
                    "error: --arm is only valid with --track shape-test "
                    "or --track pressure-test\n",
                )

    def test_meta_rejects_non_meta_track_with_exit_2(self):
        # supports_meta tracks are the argparse choices, so a non-meta
        # track is an invalid choice, exit 2 — never a runtime gate.
        argv = [
            "evaluator.py",
            "meta",
            "--track",
            "retrieval-test",
            "--harness",
            "opencode",
            "--agents-dir",
            "a",
            "--workspace",
            "w",
            "--session",
            "s",
            "--question",
            "q",
            "--out",
            "o",
        ]
        err = io.StringIO()
        with (
            mock.patch.object(sys, "argv", argv),
            contextlib.redirect_stderr(err),
            self.assertRaises(SystemExit) as cm,
        ):
            evaluator.main()
        self.assertEqual(cm.exception.code, 2)
        self.assertIn("invalid choice", err.getvalue())

    def test_legacy_subcommand_names_are_invalid_choices(self):
        # Q9a hard removal: every old per-track command name is gone.
        for name in (
            "failures",
            "retrieval-suite",
            "retrieval-evidence",
            "shape-suite",
            "shape-evidence",
            "shape-scored-check",
            "pressure-suite",
            "pressure-evidence",
            "pressure-meta",
            "pressure-scored-check",
        ):
            with self.subTest(name=name):
                err = io.StringIO()
                with (
                    mock.patch.object(sys, "argv", ["evaluator.py", name]),
                    contextlib.redirect_stderr(err),
                    self.assertRaises(SystemExit) as cm,
                ):
                    evaluator.main()
                self.assertEqual(cm.exception.code, 2)
                self.assertIn("invalid choice", err.getvalue())


if __name__ == "__main__":
    unittest.main()
