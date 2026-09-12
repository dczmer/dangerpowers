#!/usr/bin/env python3
"""Tests for the retrieval-track additions to evaluator.py: the dir hasher,
record --scope validation, retrieval query-file validation, run-record
assembly with script-computed void signals, scored-check, and the
control-workspace purity gate. Stdlib only; no harness commands are ever
invoked (zero model spend).
"""

import argparse
import ast
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any
from unittest import mock

import evaluator
from strategies import EventStream


class DirHashTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.skill_dir = self.root / "skill"
        (self.skill_dir / "references").mkdir(parents=True)
        (self.skill_dir / "SKILL.md").write_text("---\nname: x\n---\nbody\n")
        (self.skill_dir / "references" / "ref.md").write_text("ref\n")

    def tearDown(self):
        self.tmp.cleanup()

    def test_deterministic_across_repeats(self):
        first = evaluator.hash_skill_dir(self.skill_dir)
        second = evaluator.hash_skill_dir(self.skill_dir)
        self.assertEqual(first, second)
        self.assertTrue(first.startswith("sha256:"))

    def test_excludes_pycache_and_pyc(self):
        before = evaluator.hash_skill_dir(self.skill_dir)
        pycache = self.skill_dir / "__pycache__"
        pycache.mkdir()
        (pycache / "mod.cpython-314.pyc").write_bytes(b"\x00\x01")
        (self.skill_dir / "stray.pyc").write_bytes(b"\x00\x02")
        self.assertEqual(evaluator.hash_skill_dir(self.skill_dir), before)

    def test_body_edit_changes_hash(self):
        before = evaluator.hash_skill_dir(self.skill_dir)
        (self.skill_dir / "SKILL.md").write_text(
            "---\nname: x\n---\nnew body\n"
        )
        self.assertNotEqual(evaluator.hash_skill_dir(self.skill_dir), before)

    def test_pycache_edit_does_not_change_hash(self):
        before = evaluator.hash_skill_dir(self.skill_dir)
        pycache = self.skill_dir / "__pycache__"
        pycache.mkdir()
        (pycache / "mod.pyc").write_bytes(b"\x00")
        self.assertEqual(evaluator.hash_skill_dir(self.skill_dir), before)

    def test_internal_file_symlink_allowed(self):
        target = self.skill_dir / "references" / "ref.md"
        link = self.skill_dir / "alias.md"
        link.symlink_to(target)
        hashed = evaluator.hash_skill_dir(self.skill_dir)
        self.assertTrue(hashed.startswith("sha256:"))

    def test_escaping_symlink_rejected(self):
        outside = self.root / "outside.md"
        outside.write_text("outside\n")
        (self.skill_dir / "escape.md").symlink_to(outside)
        with self.assertRaises(SystemExit) as cm:
            with redirect_stderr(io.StringIO()):
                evaluator.hash_skill_dir(self.skill_dir)
        self.assertEqual(cm.exception.code, 1)

    def test_symlink_to_dir_rejected(self):
        (self.skill_dir / "dirlink").symlink_to(self.skill_dir / "references")
        with self.assertRaises(SystemExit) as cm:
            with redirect_stderr(io.StringIO()):
                evaluator.hash_skill_dir(self.skill_dir)
        self.assertEqual(cm.exception.code, 1)


class RecordScopeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.skill_dir = self.root / "skill"
        self.skill_dir.mkdir()
        (self.skill_dir / "SKILL.md").write_text(
            "---\nname: test-skill\n---\nbody\n"
        )
        self.manifest = self.root / "manifest.json"

    def tearDown(self):
        self.tmp.cleanup()

    def _record(self, **overrides) -> int:
        args = argparse.Namespace(
            skill="test-skill",
            skill_path=str(self.skill_dir),
            manifest=str(self.manifest),
            scope="dir",
            score=None,
            passes=3,
            fails=1,
            gaps=0,
            voids=2,
            ablations=None,
            campaign=None,
            date="2026-09-12",
        )
        for k, v in overrides.items():
            setattr(args, k, v)
        return evaluator.cmd_record(args)

    def test_frontmatter_with_counts_rejected(self):
        skill_md = self.skill_dir / "SKILL.md"
        rc = self._record(
            scope="frontmatter",
            score=0.8,
            passes=1,
            fails=0,
            gaps=0,
            voids=0,
            skill_path=str(skill_md),
        )
        self.assertEqual(rc, 1)

    def test_dir_with_score_rejected(self):
        rc = self._record(score=0.8)
        self.assertEqual(rc, 1)
        self.assertFalse(self.manifest.exists())

    def test_dir_missing_count_rejected(self):
        rc = self._record(voids=None)
        self.assertEqual(rc, 1)
        self.assertFalse(self.manifest.exists())

    def test_frontmatter_scope_expects_file(self):
        rc = self._record(scope="frontmatter", score=0.8)
        self.assertEqual(rc, 1)

    def test_dir_scope_expects_directory(self):
        skill_md = self.skill_dir / "SKILL.md"
        rc = self._record(skill_path=str(skill_md))
        self.assertEqual(rc, 1)

    def test_dir_writes_retrieval_test_preserving_trigger_key(self):
        self.manifest.write_text(
            json.dumps(
                {
                    "skill": "test-skill",
                    "trigger-test": {"date": "old", "score": 0.5},
                    "future-test": {"date": "x"},
                }
            )
        )
        rc = self._record()
        self.assertEqual(rc, 0)
        data = json.loads(self.manifest.read_text())
        self.assertEqual(data["future-test"], {"date": "x"})
        self.assertEqual(data["trigger-test"]["score"], 0.5)
        entry = data["retrieval-test"]
        self.assertEqual(
            set(entry),
            {"date", "checksum", "passes", "fails", "gaps", "voids"},
        )
        self.assertEqual(entry["date"], "2026-09-12")
        self.assertEqual(entry["passes"], 3)
        self.assertEqual(entry["voids"], 2)
        self.assertEqual(
            entry["checksum"], evaluator.hash_skill_dir(self.skill_dir)
        )

    def test_dir_records_ablations_when_given(self):
        rc = self._record(ablations="fixtures-staged")
        self.assertEqual(rc, 0)
        entry = json.loads(self.manifest.read_text())["retrieval-test"]
        self.assertEqual(entry["ablations"], "fixtures-staged")


class RetrievalQueryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.queries = self.root / "queries.json"
        fixtures = self.root / "fixtures"
        fixtures.mkdir()
        (fixtures / "existing-skill.md").write_text("# fixture\n")

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, entries) -> None:
        self.queries.write_text(json.dumps(entries))

    def _load(self):
        return evaluator.load_retrieval_queries(self.queries)

    def test_valid_file_loads(self):
        self._write(
            [
                {
                    "id": "plain",
                    "query": "what does the skill say?",
                    "expect": ["bullet"],
                },
                {
                    "id": "with-fixture",
                    "query": "edit {RUN_DIR}/existing-skill.md",
                    "expect": ["bullet"],
                    "fixtures": ["existing-skill.md"],
                },
            ]
        )
        entries = self._load()
        self.assertEqual([e["id"] for e in entries], ["plain", "with-fixture"])

    def test_fixtures_without_token_rejected(self):
        self._write(
            [
                {
                    "id": "bad",
                    "query": "no token here",
                    "expect": ["bullet"],
                    "fixtures": ["existing-skill.md"],
                }
            ]
        )
        with self.assertRaises(SystemExit) as cm:
            with redirect_stderr(io.StringIO()):
                self._load()
        self.assertEqual(cm.exception.code, 1)

    def test_token_without_fixtures_rejected(self):
        self._write(
            [
                {
                    "id": "bad",
                    "query": "read {RUN_DIR}/existing-skill.md",
                    "expect": ["bullet"],
                }
            ]
        )
        with self.assertRaises(SystemExit) as cm:
            with redirect_stderr(io.StringIO()):
                self._load()
        self.assertEqual(cm.exception.code, 1)

    def test_missing_fixture_file_rejected(self):
        self._write(
            [
                {
                    "id": "bad",
                    "query": "read {RUN_DIR}/no-such.md",
                    "expect": ["bullet"],
                    "fixtures": ["no-such.md"],
                }
            ]
        )
        with self.assertRaises(SystemExit) as cm:
            with redirect_stderr(io.StringIO()):
                self._load()
        self.assertEqual(cm.exception.code, 1)

    def test_duplicate_id_rejected(self):
        self._write(
            [
                {"id": "dup", "query": "q1", "expect": ["b"]},
                {"id": "dup", "query": "q2", "expect": ["b"]},
            ]
        )
        with self.assertRaises(SystemExit) as cm:
            with redirect_stderr(io.StringIO()):
                self._load()
        self.assertEqual(cm.exception.code, 1)


class FixtureStagingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.fixtures_dir = self.root / "fixtures"
        self.fixtures_dir.mkdir()
        (self.fixtures_dir / "f.md").write_text("fixture\n")
        self.arm_ws = self.root / "ws"

    def tearDown(self):
        self.tmp.cleanup()

    def test_stages_fixtures_and_substitutes_run_dir(self):
        entry = {
            "id": "q1",
            "query": "read {RUN_DIR}/f.md",
            "expect": ["b"],
            "fixtures": ["f.md"],
        }
        dispatched = evaluator.stage_and_dispatch(
            entry, "skill_arm", 1, 2, self.arm_ws, self.fixtures_dir
        )
        run_dir = self.arm_ws / "fixtures" / "q1" / "skill_arm-rep1"
        self.assertEqual(dispatched, f"read {run_dir}/f.md")
        self.assertEqual((run_dir / "f.md").read_text(), "fixture\n")

    def test_single_rep_uses_arm_label(self):
        entry = {
            "id": "q1",
            "query": "read {RUN_DIR}/f.md",
            "expect": ["b"],
            "fixtures": ["f.md"],
        }
        evaluator.stage_and_dispatch(
            entry, "control_arm", 1, 1, self.arm_ws, self.fixtures_dir
        )
        self.assertTrue(
            (self.arm_ws / "fixtures" / "q1" / "control_arm").is_dir()
        )

    def test_no_fixtures_returns_query_verbatim(self):
        entry = {"id": "q1", "query": "plain query", "expect": ["b"]}
        dispatched = evaluator.stage_and_dispatch(
            entry, "skill_arm", 1, 1, self.arm_ws, self.fixtures_dir
        )
        self.assertEqual(dispatched, "plain query")


class RunRecordTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.ws = self.root / "ws"
        self.ws.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def _record(self, ev, arm="skill_arm", skill="demo-skill", **kwargs):
        defaults: dict[str, Any] = dict(
            query_dispatched="the query",
            timed_out=False,
            ws_root=self.ws,
            arm=arm,
            skill=skill,
        )
        defaults.update(kwargs)
        return evaluator.build_run_record(ev, **defaults)

    def test_skill_arm_without_completed_load_signals(self):
        ev = EventStream(answer_parts=["answer"])
        rec = self._record(ev, arm="skill_arm")
        self.assertIn("skill-not-loaded", rec["void_signals"])

    def test_skill_arm_completed_load_no_signal(self):
        ev = EventStream(answer_parts=["answer"], completed_load=True)
        rec = self._record(ev, arm="skill_arm")
        self.assertNotIn("skill-not-loaded", rec["void_signals"])

    def test_control_arm_with_skill_load_signals(self):
        ev = EventStream(
            answer_parts=["answer"],
            skill_loads=[{"name": "demo-skill", "status": "completed"}],
        )
        rec = self._record(ev, arm="control_arm")
        self.assertIn("control-loaded-skill", rec["void_signals"])

    def test_empty_answer_signals(self):
        ev = EventStream(completed_load=True)
        rec = self._record(ev, arm="skill_arm")
        self.assertIn("empty-answer", rec["void_signals"])

    def test_sources_block_extraction(self):
        ev = EventStream(
            answer_parts=[
                "Answer text.\n\nSources consulted:\n- SKILL.md\n"
                "- references/ref.md\n"
            ]
        )
        rec = self._record(ev, arm="control_arm")
        self.assertEqual(
            rec["sources_consulted"], "- SKILL.md\n- references/ref.md"
        )

    def test_no_sources_block_is_none(self):
        ev = EventStream(answer_parts=["no list here"])
        rec = self._record(ev, arm="control_arm")
        self.assertIsNone(rec["sources_consulted"])

    def test_outside_workspace_absolute_target_signals(self):
        ev = EventStream(
            answer_parts=["a"],
            tool_calls=[{"tool": "read", "target": "/etc/hostname"}],
        )
        rec = self._record(ev, arm="control_arm")
        self.assertIn("read-outside-workspace", rec["void_signals"])

    def test_outside_workspace_relative_target_signals(self):
        ev = EventStream(
            answer_parts=["a"],
            tool_calls=[{"tool": "read", "target": "../outside.md"}],
        )
        rec = self._record(ev, arm="control_arm")
        self.assertIn("read-outside-workspace", rec["void_signals"])

    def test_inside_workspace_target_no_signal(self):
        target = str(self.ws / "SKILL.md")
        ev = EventStream(
            answer_parts=["a"],
            tool_calls=[{"tool": "read", "target": target}],
        )
        rec = self._record(ev, arm="control_arm")
        self.assertNotIn("read-outside-workspace", rec["void_signals"])

    def test_other_skill_loads_filters_none_and_target(self):
        ev = EventStream(
            answer_parts=["a"],
            completed_load=True,
            skill_loads=[
                {"name": "demo-skill", "status": "completed"},
                {"name": None, "status": "error"},
                {"name": "other-skill", "status": "completed"},
            ],
        )
        rec = self._record(ev, arm="skill_arm")
        self.assertEqual(rec["other_skill_loads"], ["other-skill"])

    def test_record_fields(self):
        ev = EventStream(
            answer_parts=["part1", "part2"],
            reasoning_parts=["think"],
            tool_calls=[{"tool": "grep", "target": "pat"}],
            session_id="ses-1",
            parseable=7,
            completed_load=True,
        )
        rec = self._record(
            ev,
            arm="skill_arm",
            query_dispatched="dispatched query",
            timed_out=True,
        )
        self.assertEqual(rec["query_dispatched"], "dispatched query")
        self.assertEqual(rec["answer_text"], "part1part2")
        self.assertEqual(
            rec["tool_calls"], [{"tool": "grep", "target": "pat"}]
        )
        self.assertTrue(rec["skill_load_completed"])
        self.assertEqual(rec["reasoning"], "think")
        self.assertEqual(rec["session_id"], "ses-1")
        self.assertTrue(rec["timeout"])
        self.assertEqual(rec["parseable_events"], 7)
        self.assertNotIn("empty-answer", rec["void_signals"])


class ScoredCheckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.results = self.root / "results.json"
        self.results.write_text(
            json.dumps(
                {
                    "config": {"skill": "demo-skill"},
                    "entries": [{"id": "a"}, {"id": "b"}],
                }
            )
        )
        self.scored = self.root / "scored.json"

    def tearDown(self):
        self.tmp.cleanup()

    def _entry(self, eid, **overrides):
        entry = {
            "id": eid,
            "result": "pass",
            "control": "pass",
            "ablation_flag": False,
            "missed_bullets": [],
        }
        entry.update(overrides)
        return entry

    def _check(self, entries) -> int:
        self.scored.write_text(
            json.dumps(
                {
                    "campaign": "campaign-2026-09-12",
                    "skill": "demo-skill",
                    "entries": entries,
                }
            )
        )
        args = argparse.Namespace(
            results=str(self.results), scored=str(self.scored)
        )
        return evaluator.cmd_scored_check(args)

    def test_complete_scored_passes(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = self._check([self._entry("a"), self._entry("b")])
        self.assertEqual(rc, 0)
        self.assertIn("ok:", buf.getvalue())
        self.assertIn("covers 2 entries", buf.getvalue())

    def test_fail_entry_with_classification_passes(self):
        rc = self._check(
            [
                self._entry(
                    "a",
                    result="fail",
                    classification="findability",
                    control="fail",
                    missed_bullets=["missed one"],
                ),
                self._entry("b"),
            ]
        )
        self.assertEqual(rc, 0)

    def test_missing_id_rejected(self):
        self.assertEqual(self._check([self._entry("a")]), 1)

    def test_unknown_id_rejected(self):
        self.assertEqual(
            self._check([self._entry("a"), self._entry("zzz")]), 1
        )

    def test_duplicate_id_rejected(self):
        self.assertEqual(self._check([self._entry("a"), self._entry("a")]), 1)

    def test_bad_verdict_rejected(self):
        bad = self._entry("b", result="failure")
        self.assertEqual(self._check([self._entry("a"), bad]), 1)

    def test_classification_on_pass_rejected(self):
        self.assertEqual(
            self._check(
                [self._entry("a"), self._entry("b", classification="clarity")]
            ),
            1,
        )

    def test_fail_without_classification_rejected(self):
        self.assertEqual(
            self._check(
                [
                    self._entry(
                        "a",
                        result="fail",
                        missed_bullets=["missed one"],
                        control="fail",
                    ),
                    self._entry("b"),
                ]
            ),
            1,
        )

    def test_fail_requires_missed_bullets(self):
        self.assertEqual(
            self._check(
                [
                    self._entry(
                        "a",
                        result="fail",
                        classification="clarity",
                        control="fail",
                        missed_bullets=[],
                    ),
                    self._entry("b"),
                ]
            ),
            1,
        )


class ControlPurityTests(unittest.TestCase):
    """cmd_retrieval_suite pre-spend validation: a control workspace that
    contains the skill aborts with exit 1 before any harness invocation."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.agents_dir = self.root / "agents"
        self.agents_dir.mkdir()
        (self.agents_dir / "retrieval-evaluator.opencode.md").write_text(
            "---\nname: retrieval-evaluator\nmode: primary\n---\n"
            "load {{SKILL_NAME}}\n"
        )
        (self.agents_dir / "retrieval-control.opencode.md").write_text(
            "---\nname: retrieval-control\nmode: primary\n---\nbody\n"
        )
        self.skill_ws = self.root / "skill-ws"
        (self.skill_ws / ".agents" / "skills" / "demo-skill").mkdir(
            parents=True
        )
        self.control_ws = self.root / "control-ws"
        (self.control_ws / ".agents" / "skills" / "demo-skill").mkdir(
            parents=True
        )
        (self.root / "fixtures").mkdir()
        self.queries = self.root / "queries.json"
        self.queries.write_text(
            json.dumps([{"id": "a", "query": "q", "expect": ["b"]}])
        )
        self.out = self.root / "results.json"

    def tearDown(self):
        self.tmp.cleanup()

    def _args(self):
        return argparse.Namespace(
            harness="opencode",
            skill="demo-skill",
            agents_dir=str(self.agents_dir),
            skill_workspace=str(self.skill_ws),
            control_workspace=str(self.control_ws),
            queries=str(self.queries),
            out=str(self.out),
            model=None,
            variant=None,
            reps=1,
            timeout=120,
        )

    def test_control_workspace_skill_presence_exits_1(self):
        with mock.patch.object(evaluator, "check_harness", lambda *a: None):
            with self.assertRaises(SystemExit) as cm:
                with redirect_stderr(io.StringIO()):
                    evaluator.cmd_retrieval_suite(self._args())
        self.assertEqual(cm.exception.code, 1)
        self.assertFalse(self.out.exists())


class GrammarCompatTests(unittest.TestCase):
    def test_evaluator_py_parses_as_python_3_10(self):
        src = Path(evaluator.__file__).read_text()
        ast.parse(src, filename="evaluator.py", feature_version=(3, 10))


if __name__ == "__main__":
    unittest.main()
