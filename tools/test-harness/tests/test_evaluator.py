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
import os
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


class SuiteLockTests(unittest.TestCase):
    """The cross-process suite lock (BUGS.md B5): run_suite holds one
    machine-wide lock so two concurrent suite processes can't multiply
    per-rep latency into misattributable empty-answer timeout voids.
    Zero harness runs: the trigger track's empty-queries path reaches
    the lock with no spend."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.lock = self.root / "suite.lock"
        self.env_patcher = mock.patch.dict(
            os.environ, {"EVALUATOR_SUITE_LOCK": str(self.lock)}
        )
        self.env_patcher.start()
        self.workspace = self.root / "ws"
        stub = self.workspace / ".agents" / "skills" / SKILL / "SKILL.md"
        stub.parent.mkdir(parents=True)
        stub.write_text(f"---\nname: {SKILL}\n---\n")
        self.agents_dir = self.root / "agents"
        self.agents_dir.mkdir()
        (self.agents_dir / "trigger-evaluator.opencode.md").write_text(
            "---\nname: trigger-evaluator\n---\n# Agent\n"
        )
        self.queries = self.root / "queries.json"
        self.queries.write_text("[]")
        self.out = self.root / "results.json"

    def tearDown(self):
        self.env_patcher.stop()
        if evaluator._Log.file is not None:
            evaluator._Log.file.close()
            evaluator._Log.file = None
        self.tmp.cleanup()

    def _run_empty_suite(self) -> int:
        args = argparse.Namespace(
            harness="opencode",
            skill=SKILL,
            agents_dir=str(self.agents_dir),
            workspace=str(self.workspace),
            queries=str(self.queries),
            out=str(self.out),
            model=None,
            variant=None,
            reps=3,
            timeout=30,
        )
        with (
            mock.patch.object(
                strategies.shutil, "which", return_value="/usr/bin/opencode"
            ),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            return evaluator.run_suite(TRACKS["trigger-test"], args)

    def test_held_lock_aborts_before_spend(self):
        self.lock.write_text("pid 99999 since 2026-09-22T00:00:00+00:00")
        err = io.StringIO()
        with (
            contextlib.redirect_stderr(err),
            self.assertRaises(SystemExit) as cm,
        ):
            self._run_empty_suite()
        self.assertEqual(cm.exception.code, 1)
        msg = err.getvalue()
        self.assertIn(
            "error: another suite is already running (pid 99999", msg
        )
        self.assertIn(str(self.lock), msg)
        # No results file, and the foreign lock is left untouched.
        self.assertFalse(self.out.exists())
        self.assertEqual(
            self.lock.read_text(),
            "pid 99999 since 2026-09-22T00:00:00+00:00",
        )

    def test_lock_acquired_and_released(self):
        rc = self._run_empty_suite()
        self.assertEqual(rc, 0)
        self.assertFalse(self.lock.exists())

    def test_lock_released_on_exception(self):
        with self.assertRaises(RuntimeError):
            with evaluator._suite_lock():
                self.assertTrue(self.lock.exists())
                self.assertIn(f"pid {os.getpid()}", self.lock.read_text())
                raise RuntimeError("boom")
        self.assertFalse(self.lock.exists())

    def test_nested_acquire_exits_1(self):
        with evaluator._suite_lock():
            err = io.StringIO()
            with (
                contextlib.redirect_stderr(err),
                self.assertRaises(SystemExit) as cm,
            ):
                with evaluator._suite_lock():
                    pass
            self.assertEqual(cm.exception.code, 1)
            self.assertIn("another suite is already running", err.getvalue())
        self.assertFalse(self.lock.exists())


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

    def test_dir_scope_preserves_existing_manifest_keys(self):
        self.manifest.write_text(
            json.dumps(
                {
                    "skill": "test-skill",
                    "trigger-test": {"date": "old", "score": 0.5},
                    "future-test": {"date": "x"},
                }
            )
        )
        self._write_scored([self._retrieval_entry("a", "pass")])
        rc, _out, _err = self._record()
        self.assertEqual(rc, 0)
        data = json.loads(self.manifest.read_text())
        self.assertEqual(data["future-test"], {"date": "x"})
        self.assertEqual(data["trigger-test"]["score"], 0.5)
        entry = data["retrieval-test"]
        self.assertEqual(
            set(entry),
            {
                "date",
                "checksum",
                "passes",
                "fails",
                "gaps",
                "voids",
                "campaign",
            },
        )
        self.assertEqual(entry["date"], "2026-09-14")
        self.assertEqual(entry["campaign"], "campaign-2026-09-14")
        self.assertEqual(entry["passes"], 1)
        self.assertEqual(
            entry["checksum"], evaluator.hash_skill_dir(self.skill_dir)
        )

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
        self.assertIn(
            "mix track vocabularies (pressure-test, shape-test)",
            err,
        )
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

    def test_harness_required_without_span_mode(self):
        ns = argparse.Namespace(
            harness=None, model=None, entries=None, skill_file=None
        )
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            rc = evaluator.cmd_check(ns)
        self.assertEqual(rc, 1)
        self.assertIn("--harness is required", buf.getvalue())


class CheckSpanModeTests(unittest.TestCase):
    """cmd_check --entries/--skill-file (BUGS.md B7): the shape track's
    proposal-time section-span check. Zero harness involvement — the
    preflight mock must never be called in span mode."""

    SECTION = "## Styling\n\nComponents use css modules, never inline"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.entries = self.root / "entries.json"
        self.skill = self.root / "SKILL.md"
        self._write_entries([("css-modules", self.SECTION)])
        self.skill.write_text("# Demo\n\n" + self.SECTION + "\n")

    def tearDown(self):
        self.tmp.cleanup()

    def _write_entries(self, pairs):
        self.entries.write_text(
            json.dumps(
                [
                    {
                        "id": eid,
                        "kind": "shaping",
                        "section": section,
                        "fixtures": {
                            "application": f"write a component for {eid}"
                        },
                        "markers": {"inline_style": "style="},
                        "variants": {"v1": "Never use inline styles."},
                    }
                    for eid, section in pairs
                ]
            )
        )

    def _run(self, entries=True, skill_file=True):
        ns = argparse.Namespace(
            harness=None,
            model=None,
            entries=str(self.entries) if entries else None,
            skill_file=str(self.skill) if skill_file else None,
        )
        buf = io.StringIO()
        with mock.patch.object(evaluator, "check_harness") as check_mock:
            with (
                contextlib.redirect_stdout(buf),
                contextlib.redirect_stderr(buf),
            ):
                rc = evaluator.cmd_check(ns)
        return rc, check_mock, buf.getvalue()

    def test_clean_exits_0_with_per_entry_report(self):
        rc, check_mock, out = self._run()
        self.assertEqual(rc, 0)
        self.assertIn(
            "ok: entry 'css-modules': section span occurs exactly once", out
        )
        self.assertIn("every section span unique", out)
        check_mock.assert_not_called()

    def test_absent_span_exits_1_naming_entry(self):
        self.skill.write_text("# Demo\n\nother text\n")
        rc, _, out = self._run()
        self.assertEqual(rc, 1)
        self.assertIn("entry 'css-modules'", out)
        self.assertIn("occurs 0 times", out)

    def test_duplicated_span_exits_1(self):
        self.skill.write_text(
            "# Demo\n\n" + self.SECTION + "\n\n" + self.SECTION + "\n"
        )
        rc, _, out = self._run()
        self.assertEqual(rc, 1)
        self.assertIn("occurs 2 times", out)

    def test_all_drifted_spans_reported(self):
        other = "## Testing\n\nTests live next to the component"
        self._write_entries([("css-modules", self.SECTION), ("tests", other)])
        self.skill.write_text("# Demo\n\nno spans here\n")
        rc, _, out = self._run()
        self.assertEqual(rc, 1)
        self.assertIn("entry 'css-modules'", out)
        self.assertIn("entry 'tests'", out)

    def test_frontmatter_stripped_before_matching(self):
        self.skill.write_text(
            "---\nname: demo-skill\n---\n# Demo\n\n" + self.SECTION + "\n"
        )
        rc, _, _ = self._run()
        self.assertEqual(rc, 0)

    def test_entries_without_skill_file_rejected(self):
        rc, _, out = self._run(skill_file=False)
        self.assertEqual(rc, 1)
        self.assertIn("must be given together", out)

    def test_skill_file_without_entries_rejected(self):
        rc, _, out = self._run(entries=False)
        self.assertEqual(rc, 1)
        self.assertIn("must be given together", out)

    def test_missing_skill_file_rejected(self):
        self.skill.unlink()
        rc, _, out = self._run()
        self.assertEqual(rc, 1)
        self.assertIn("skill file not found", out)


class SelectTests(unittest.TestCase):
    """cmd_select (BUGS.md B8): track-agnostic filtering of an
    entries/queries/scenarios file to a subset of ids. Envelope
    validation only, input document order preserved, unknown ids a
    named error."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.entries = self.root / "entries.json"
        self.out = self.root / "out.json"
        self._write([("alpha", 1), ("beta", 2), ("gamma", 3)])

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, pairs):
        self.entries.write_text(
            json.dumps([{"id": eid, "n": n} for eid, n in pairs])
        )

    def _run(self, ids):
        ns = argparse.Namespace(
            entries=str(self.entries), ids=ids, out=str(self.out)
        )
        buf = io.StringIO()
        with (
            contextlib.redirect_stdout(buf),
            contextlib.redirect_stderr(buf),
        ):
            rc = evaluator.cmd_select(ns)
        return rc, buf.getvalue()

    def _selected(self):
        return json.loads(self.out.read_text())

    def test_filters_to_named_ids(self):
        rc, out = self._run("alpha,gamma")
        self.assertEqual(rc, 0)
        ids = [e["id"] for e in self._selected()]
        self.assertEqual(ids, ["alpha", "gamma"])
        self.assertIn("select: 2/3 entries ->", out)

    def test_input_document_order_preserved(self):
        rc, _ = self._run("gamma,alpha")
        self.assertEqual(rc, 0)
        ids = [e["id"] for e in self._selected()]
        self.assertEqual(ids, ["alpha", "gamma"])

    def test_entry_objects_carried_verbatim(self):
        rc, _ = self._run("beta")
        self.assertEqual(rc, 0)
        self.assertEqual(self._selected(), [{"id": "beta", "n": 2}])

    def test_unknown_id_exits_1_naming_it(self):
        rc, out = self._run("alpha,delta")
        self.assertEqual(rc, 1)
        self.assertIn("ids not found in", out)
        self.assertIn("delta", out)
        self.assertFalse(self.out.exists())

    def test_empty_ids_rejected(self):
        rc, out = self._run(" , ")
        self.assertEqual(rc, 1)
        self.assertIn("--ids must name at least one id", out)
        self.assertFalse(self.out.exists())

    def test_duplicate_id_in_ids_selects_once(self):
        rc, _ = self._run("beta,beta")
        self.assertEqual(rc, 0)
        self.assertEqual([e["id"] for e in self._selected()], ["beta"])

    def test_missing_output_parent_dirs_created(self):
        # Issue #54: --out naming a not-yet-existing mini-campaign
        # subdir (confirm/, round-2/) is the canonical usage; the
        # command creates the parents rather than crashing.
        self.out = self.root / "confirm" / "round1" / "queries.json"
        rc, out = self._run("alpha")
        self.assertEqual(rc, 0)
        self.assertEqual([e["id"] for e in self._selected()], ["alpha"])
        self.assertIn("select: 1/3 entries ->", out)

    def test_unwritable_output_fails_cleanly(self):
        # A --out whose parent path is a FILE: mkdir cannot succeed,
        # so the failure surfaces as a clean `error:` line (rc 1),
        # never a raw traceback.
        blocker = self.root / "blocker"
        blocker.write_text("x")
        self.out = blocker / "sub" / "out.json"
        rc, out = self._run("alpha")
        self.assertEqual(rc, 1)
        self.assertIn("error: could not write", out)
        self.assertNotIn("Traceback", out)

    def _run_envelope_error(self):
        ns = argparse.Namespace(
            entries=str(self.entries), ids="alpha", out=str(self.out)
        )
        err = io.StringIO()
        with (
            contextlib.redirect_stderr(err),
            self.assertRaises(SystemExit) as cm,
        ):
            evaluator.cmd_select(ns)
        return cm.exception.code, err.getvalue()

    def test_non_list_input_rejected(self):
        self.entries.write_text('{"id": "alpha"}')
        code, err = self._run_envelope_error()
        self.assertEqual(code, 1)
        self.assertIn("expected a JSON list", err)

    def test_duplicate_id_in_input_rejected(self):
        self._write([("alpha", 1), ("alpha", 2)])
        code, err = self._run_envelope_error()
        self.assertEqual(code, 1)
        self.assertIn("duplicate id: alpha", err)


class _ProbeStrategy:
    """Satisfies validate_eval_agent's agent_file probe in gate tests
    without any harness binary."""

    def __init__(self, timeout=30):
        self.timeout = timeout

    def agent_file(self, agents_dir, base):
        return Path(agents_dir) / f"{base}.opencode.md"


class VerifyTests(unittest.TestCase):
    """cmd_verify (BUGS.md B9): the end-of-campaign consistency proof
    gating record. Snapshot byte-identity, manifest<->entries wiring,
    skill-body/span checks, and the scored<->results group (the
    scored-check flow reused, full-campaign coverage, record preflight).
    All groups always run — a failing group never hides a later one."""

    SECTION = "Always use CSS modules."

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        # Canonical files.
        self.manifest = self.root / "rules.json"
        self._write_manifest()
        self.entries = self.root / "entries.json"
        self._write_entries([self._shape_entry("css-modules")])
        self.skill_dir = self.root / "demo-skill"
        self.skill_dir.mkdir()
        (self.skill_dir / "SKILL.md").write_text(
            "---\nname: demo-skill\n---\n# Demo\n\n" + self.SECTION + "\n"
        )
        # Campaign dir with byte-identical snapshots.
        self.camp = self.root / "campaign-2026-09-23"
        self.camp.mkdir()
        self._snapshot()
        self.results_control = self.camp / "results-control.json"
        self.results_variants = self.camp / "results-variants.json"
        self._write_shape_results()
        self.scored = self.camp / "scored.json"
        self._write_scored(
            [
                {
                    "id": "css-modules",
                    "kind": "shaping",
                    "result": "adopted",
                    "adopted_arm": "v1",
                    "restraint_gate": None,
                    "marker_counts": {},
                    "notes": None,
                }
            ]
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _write_manifest(self, items=None, excluded=None):
        items = (
            items
            if items is not None
            else [
                {
                    "id": "R-styling-01",
                    "section": "Styling",
                    "kind": "shaping",
                    "statement": "Use CSS modules.",
                    "entries": ["css-modules"],
                }
            ]
        )
        excluded = excluded if excluded is not None else []
        self.manifest.write_text(
            json.dumps(
                {
                    "skill": "demo-skill",
                    "generated": "2026-09-23",
                    "rules": items,
                    "excluded": excluded,
                }
            )
        )

    def _shape_entry(self, eid, rule="R-styling-01", section=None):
        return {
            "id": eid,
            "rule": rule,
            "kind": "shaping",
            "section": section if section is not None else self.SECTION,
            "fixtures": {"application": f"Build a component for {eid}."},
            "markers": {"inline_style": "style="},
            "variants": {"v1": "Never use inline styles."},
        }

    def _write_entries(self, entries):
        self.entries.write_text(json.dumps(entries))

    def _snapshot(self):
        (self.camp / "rules.json").write_bytes(self.manifest.read_bytes())
        (self.camp / "entries.json").write_bytes(self.entries.read_bytes())
        snap_skill = self.camp / "demo-skill"
        snap_skill.mkdir(exist_ok=True)
        (snap_skill / "SKILL.md").write_bytes(
            (self.skill_dir / "SKILL.md").read_bytes()
        )
        (self.camp / "skill-body.txt").write_text(
            "# Demo\n\n" + self.SECTION + "\n"
        )

    def _shape_results_entry(self, eid, arms):
        return {
            "id": eid,
            "kind": "shaping",
            "markers": {"inline_style": "style="},
            "restraint_markers": None,
            "arms": {a: {"runs": [{"answer_text": "ok"}]} for a in arms},
        }

    def _write_shape_results(self, ids=("css-modules",)):
        self.results_control.write_text(
            json.dumps(
                {
                    "config": {"skill": "demo-skill"},
                    "entries": [
                        self._shape_results_entry(eid, ["v0"]) for eid in ids
                    ],
                }
            )
        )
        self.results_variants.write_text(
            json.dumps(
                {
                    "config": {"skill": "demo-skill"},
                    "entries": [
                        self._shape_results_entry(eid, ["v1"]) for eid in ids
                    ],
                }
            )
        )

    def _write_scored(self, entries):
        self.scored.write_text(json.dumps({"entries": entries}))

    def _run(self, **overrides):
        ns = argparse.Namespace(
            track="shape-test",
            manifest=str(self.manifest),
            entries=str(self.entries),
            scored=str(self.scored),
            results=[str(self.results_control), str(self.results_variants)],
            campaign_dir=str(self.camp),
            skill_path=str(self.skill_dir),
        )
        for k, v in overrides.items():
            setattr(ns, k, v)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = evaluator.cmd_verify(ns)
        return rc, out.getvalue(), err.getvalue()

    def test_happy_path(self):
        rc, out, err = self._run()
        self.assertEqual(rc, 0, err)
        self.assertIn("snapshot rules.json byte-identical", out)
        self.assertIn("snapshot entries.json byte-identical", out)
        self.assertIn("snapshot skill dir demo-skill/ matches", out)
        self.assertIn("wiring: 1 entries wired to 1 rules", out)
        self.assertIn("with frontmatter stripped", out)
        self.assertIn("every section span unique", out)
        self.assertIn("results cover all 1 entries", out)
        self.assertIn("covers 1 entries", out)  # scored-check's own line
        self.assertIn(
            "record preflight (nothing written): record --scope dir "
            "would write shape-test: 1 adopted / 0 no-failure / "
            "0 unresolved / 0 voids",
            out,
        )
        self.assertIn("verify: all checks passed", out)

    def test_manifest_snapshot_drift_fails_but_later_groups_run(self):
        (self.camp / "rules.json").write_text("{}")
        rc, out, err = self._run()
        self.assertEqual(rc, 1)
        self.assertIn("differs from canonical", err)
        # Fail-batch: the other groups still ran.
        self.assertIn("wiring: 1 entries wired", out)
        self.assertNotIn("verify: all checks passed", out)

    def test_missing_snapshot_named(self):
        (self.camp / "entries.json").unlink()
        rc, _out, err = self._run()
        self.assertEqual(rc, 1)
        self.assertIn("snapshot missing:", err)
        self.assertIn("entries.json", err)

    def test_skill_dir_snapshot_drift(self):
        (self.camp / "demo-skill" / "SKILL.md").write_text(
            "---\nname: demo-skill\n---\n# Demo\n\nedited\n"
        )
        rc, _out, err = self._run()
        self.assertEqual(rc, 1)
        self.assertIn("snapshot skill dir", err)
        self.assertIn("differs", err)

    def test_scored_outside_campaign_dir_rejected(self):
        other = self.root / "scored.json"
        other.write_text(self.scored.read_text())
        rc, _out, err = self._run(scored=str(other))
        self.assertEqual(rc, 1)
        self.assertIn("--scored must live in the campaign dir", err)

    def test_results_outside_campaign_dir_rejected(self):
        other = self.root / "results-control.json"
        other.write_text(self.results_control.read_text())
        rc, _out, err = self._run(results=[str(other)])
        self.assertEqual(rc, 1)
        self.assertIn("--results must live in the campaign dir", err)

    def test_entry_naming_unknown_rule(self):
        self._write_entries([self._shape_entry("css-modules", "R-nope-99")])
        self._snapshot()
        rc, _out, err = self._run()
        self.assertEqual(rc, 1)
        self.assertIn("names rule 'R-nope-99'", err)
        self.assertIn("does not exist", err)

    def test_rule_entries_not_naming_entry(self):
        self._write_entries([self._shape_entry("renamed-entry")])
        self._snapshot()
        rc, _out, err = self._run()
        self.assertEqual(rc, 1)
        self.assertIn("do not name it", err)
        self.assertIn("does not exist", err)  # stale forward reference

    def test_excluded_id_with_entry_rejected(self):
        self._write_manifest(
            excluded=[
                {
                    "id": "css-modules",
                    "section": "Styling",
                    "kind": "shaping",
                    "reason": "routed out",
                }
            ]
        )
        self._snapshot()
        rc, _out, err = self._run()
        self.assertEqual(rc, 1)
        self.assertIn("excluded id", err)

    def test_item_with_no_entries_rejected(self):
        self._write_manifest(
            items=[
                {
                    "id": "R-styling-01",
                    "section": "Styling",
                    "kind": "shaping",
                    "statement": "Use CSS modules.",
                    "entries": [],
                }
            ]
        )
        self._snapshot()
        rc, _out, err = self._run()
        self.assertEqual(rc, 1)
        self.assertIn("names no entries", err)

    def test_entry_named_by_two_items_rejected(self):
        self._write_manifest(
            items=[
                {
                    "id": "R-styling-01",
                    "section": "Styling",
                    "kind": "shaping",
                    "statement": "Use CSS modules.",
                    "entries": ["css-modules"],
                },
                {
                    "id": "R-styling-02",
                    "section": "Styling",
                    "kind": "shaping",
                    "statement": "No inline styles.",
                    "entries": ["css-modules"],
                },
            ]
        )
        self._snapshot()
        rc, _out, err = self._run()
        self.assertEqual(rc, 1)
        self.assertIn("named by multiple items", err)

    def test_skill_body_mismatch(self):
        (self.camp / "skill-body.txt").write_text(
            "# Demo\n\nAlways use css modules.\n"
        )
        rc, _out, err = self._run()
        self.assertEqual(rc, 1)
        self.assertIn("with its frontmatter stripped", err)

    def test_span_drift_reported(self):
        (self.camp / "skill-body.txt").write_text("# Demo\n\nno spans\n")
        # Identity holds (the source edit is mirrored by hand here);
        # the span assertion is what must fire.
        (self.skill_dir / "SKILL.md").write_text(
            "---\nname: demo-skill\n---\n# Demo\n\nno spans\n"
        )
        (self.camp / "demo-skill" / "SKILL.md").write_text(
            "---\nname: demo-skill\n---\n# Demo\n\nno spans\n"
        )
        rc, _out, err = self._run()
        self.assertEqual(rc, 1)
        self.assertIn("entry 'css-modules'", err)
        self.assertIn("occurs 0 times", err)

    def test_missing_skill_body_is_an_error_on_shape(self):
        (self.camp / "skill-body.txt").unlink()
        rc, _out, err = self._run()
        self.assertEqual(rc, 1)
        self.assertIn("skill-body.txt", err)

    def test_results_not_covering_every_entry_rejected(self):
        second = self._shape_entry("no-nuance", rule="R-content-01")
        self._write_entries([self._shape_entry("css-modules"), second])
        self._write_manifest(
            items=[
                {
                    "id": "R-styling-01",
                    "section": "Styling",
                    "kind": "shaping",
                    "statement": "Use CSS modules.",
                    "entries": ["css-modules"],
                },
                {
                    "id": "R-content-01",
                    "section": "Content",
                    "kind": "shaping",
                    "statement": "No nuance clauses.",
                    "entries": ["no-nuance"],
                },
            ]
        )
        self._snapshot()
        # Results (and scored) cover only the first entry.
        rc, _out, err = self._run()
        self.assertEqual(rc, 1)
        self.assertIn("entries with no results coverage", err)
        self.assertIn("no-nuance", err)

    def test_results_id_with_no_entry_rejected(self):
        self._write_shape_results(ids=("css-modules", "ghost"))
        rc, _out, err = self._run()
        self.assertEqual(rc, 1)
        self.assertIn("results ids with no entry", err)
        self.assertIn("ghost", err)

    def test_scored_inconsistency_fails_group_4(self):
        self._write_scored(
            [
                {
                    "id": "css-modules",
                    "kind": "shaping",
                    "result": "adopted",
                    "adopted_arm": "v9",
                    "restraint_gate": None,
                    "marker_counts": {},
                    "notes": None,
                }
            ]
        )
        rc, out, err = self._run()
        self.assertEqual(rc, 1)
        self.assertIn("adopted_arm", err)
        self.assertNotIn("record preflight", out)

    def test_missing_campaign_dir(self):
        rc, _out, err = self._run(campaign_dir=str(self.root / "nope"))
        self.assertEqual(rc, 1)
        self.assertIn("campaign dir not found", err)


class VerifyRetrievalTests(unittest.TestCase):
    """cmd_verify on the fact kind (retrieval): the N:M covering
    relation — every fact's entries exist, every query is named by at
    least one fact — and no skill-body requirement."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.manifest = self.root / "facts.json"
        self._write_facts(["q1"])
        self.queries = self.root / "queries.json"
        self._write_queries(["q1"])
        self.skill_dir = self.root / "demo-skill"
        self.skill_dir.mkdir()
        (self.skill_dir / "SKILL.md").write_text(
            "---\nname: demo-skill\n---\n# Demo\n\nbody\n"
        )
        self.camp = self.root / "campaign-2026-09-23"
        self.camp.mkdir()
        self._snapshot()
        self.results = self.camp / "results.json"
        self._write_results(["q1"])
        self.scored = self.camp / "scored.json"
        self._write_scored(["q1"])

    def tearDown(self):
        self.tmp.cleanup()

    def _write_facts(self, qids):
        self.manifest.write_text(
            json.dumps(
                {
                    "skill": "demo-skill",
                    "generated": "2026-09-23",
                    "facts": [
                        {
                            "id": "F-demo-01",
                            "section": "Demo",
                            "statement": "a documented fact",
                            "entries": qids,
                        }
                    ],
                    "excluded": [],
                }
            )
        )

    def _write_queries(self, qids):
        self.queries.write_text(
            json.dumps(
                [
                    {"id": q, "query": f"query {q}", "expect": ["bullet"]}
                    for q in qids
                ]
            )
        )

    def _snapshot(self):
        (self.camp / "facts.json").write_bytes(self.manifest.read_bytes())
        (self.camp / "queries.json").write_bytes(self.queries.read_bytes())
        snap_skill = self.camp / "demo-skill"
        snap_skill.mkdir(exist_ok=True)
        (snap_skill / "SKILL.md").write_bytes(
            (self.skill_dir / "SKILL.md").read_bytes()
        )

    def _write_results(self, qids):
        self.results.write_text(
            json.dumps(
                {
                    "config": {"skill": "demo-skill"},
                    "entries": [
                        {
                            "id": q,
                            "query": f"query {q}",
                            "expect": ["bullet"],
                            "skill_arm": {"runs": [{"answer_text": "ok"}]},
                            "control_arm": {"runs": [{"answer_text": "ok"}]},
                        }
                        for q in qids
                    ],
                }
            )
        )

    def _write_scored(self, qids):
        self.scored.write_text(
            json.dumps(
                {
                    "entries": [
                        {
                            "id": q,
                            "result": "pass",
                            "classification": None,
                            "control": "pass",
                            "ablation_flag": True,
                            "missed_bullets": None,
                            "notes": None,
                        }
                        for q in qids
                    ]
                }
            )
        )

    def _run(self, **overrides):
        ns = argparse.Namespace(
            track="retrieval-test",
            manifest=str(self.manifest),
            entries=str(self.queries),
            scored=str(self.scored),
            results=[str(self.results)],
            campaign_dir=str(self.camp),
            skill_path=str(self.skill_dir),
        )
        for k, v in overrides.items():
            setattr(ns, k, v)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = evaluator.cmd_verify(ns)
        return rc, out.getvalue(), err.getvalue()

    def test_happy_path_without_skill_body(self):
        rc, out, err = self._run()
        self.assertEqual(rc, 0, err)
        self.assertIn("snapshot facts.json byte-identical", out)
        self.assertIn("wiring: 1 entries wired to 1 facts", out)
        self.assertNotIn("section span", out)
        self.assertIn(
            "would write retrieval-test: 1 passes / 0 fails / 0 gaps / "
            "0 voids",
            out,
        )
        self.assertIn("verify: all checks passed", out)

    def test_fact_naming_unknown_query(self):
        self._write_facts(["q1", "ghost"])
        self._snapshot()
        rc, _out, err = self._run()
        self.assertEqual(rc, 1)
        self.assertIn("names entry 'ghost'", err)

    def test_query_covered_by_no_fact(self):
        self._write_queries(["q1", "orphan"])
        self._write_results(["q1", "orphan"])
        self._write_scored(["q1", "orphan"])
        self._snapshot()
        rc, _out, err = self._run()
        self.assertEqual(rc, 1)
        self.assertIn("entry 'orphan' is named by no fact", err)


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
            (1, 300),
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
            (5, 300),
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
            (5, 300),
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
            matrix=False,
        )
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            rc = evaluator.cmd_evidence(args)
        self.assertEqual(rc, 1)
        self.assertEqual(
            err.getvalue(),
            "error: --compare is only valid with --track shape-test\n",
        )

    def test_evidence_matrix_only_on_shape(self):
        args = argparse.Namespace(
            track="retrieval-test",
            results="x.json",
            entry=None,
            arm=None,
            compare=False,
            matrix=True,
        )
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            rc = evaluator.cmd_evidence(args)
        self.assertEqual(rc, 1)
        self.assertEqual(
            err.getvalue(),
            "error: --matrix is only valid with --track shape-test\n",
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
                    matrix=False,
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
