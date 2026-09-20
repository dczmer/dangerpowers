#!/usr/bin/env python3
"""Fixture-driven tests for the evaluator's verdict logic.

subprocess.run is stubbed; no live model is involved. Covers the signal
edge paths: interrupted runs (subprocess timeout and clean exits with a
missing/unrecognized final report), rejected skill calls, and opencode's
silent agent fallback.
"""

import argparse
import contextlib
import hashlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import evaluator
import strategies

SKILL = "writing-skills"


def ndjson(*events: dict) -> str:
    return "\n".join(json.dumps(e) for e in events) + "\n"


def reasoning_event(text: str) -> dict:
    return {
        "type": "reasoning",
        "sessionID": "s1",
        "part": {"type": "reasoning", "text": text},
    }


def text_event(text: str) -> dict:
    return {
        "type": "text",
        "sessionID": "s1",
        "part": {"type": "text", "text": text},
    }


def skill_tool_event(name: str, status: str) -> dict:
    return {
        "type": "tool_use",
        "sessionID": "s1",
        "part": {
            "type": "tool",
            "tool": "skill",
            "state": {"status": status, "input": {"name": name}},
        },
    }


def session_event(session: str, etype: str, part: dict) -> dict:
    return {"type": etype, "sessionID": session, "part": part}


class VerdictTests(unittest.TestCase):
    def setUp(self):
        self.strategy = strategies.OpencodeStrategy(timeout=30)
        self.ws = Path("/tmp/fake-workspace")

    def _evaluate(
        self, stdout: str = "", stderr: str = "", returncode: int = 0
    ) -> evaluator.Verdict:
        proc = subprocess.CompletedProcess(
            args=[], returncode=returncode, stdout=stdout, stderr=stderr
        )
        with mock.patch.object(
            strategies.subprocess, "run", return_value=proc
        ):
            return self.strategy.evaluate(SKILL, "test query", self.ws)

    def _evaluate_timeout(self, partial_stdout: str) -> evaluator.Verdict:
        err = subprocess.TimeoutExpired(
            cmd=["opencode"], timeout=30, output=partial_stdout
        )
        with mock.patch.object(strategies.subprocess, "run", side_effect=err):
            return self.strategy.evaluate(SKILL, "test query", self.ws)

    def test_timeout_with_intent_partial_stream(self):
        # Interrupted run with clear intent evidence but no completed load:
        # triggered, flagged timeout: true.
        partial = ndjson(
            reasoning_event(
                "I should load the `writing-skills` skill for this."
            )
        )
        verdict = self._evaluate_timeout(partial)
        self.assertEqual(verdict.outcome, "triggered")
        self.assertTrue(verdict.timeout)

    def test_timeout_with_completed_load(self):
        # A completed load in the partial stream wins outright (no timeout
        # flag).
        partial = ndjson(skill_tool_event(SKILL, "completed"))
        verdict = self._evaluate_timeout(partial)
        self.assertEqual(verdict.outcome, "triggered")
        self.assertFalse(verdict.timeout)

    def test_timeout_without_intent_is_void(self):
        partial = ndjson(reasoning_event("The user wants a poem about Paris."))
        verdict = self._evaluate_timeout(partial)
        self.assertEqual(verdict.outcome, "void")
        self.assertTrue(verdict.timeout)

    def test_rejected_skill_call_is_not_triggered(self):
        # status="error" is an attempted load, never a completed one. With the
        # mandated report present the run is completed -> not-triggered.
        stdout = ndjson(
            skill_tool_event(SKILL, "error"),
            text_event("No skill matched — the query is about cooking."),
        )
        verdict = self._evaluate(stdout)
        self.assertEqual(verdict.outcome, "not-triggered")
        self.assertFalse(verdict.timeout)
        self.assertIn("did not complete", verdict.detail)

    def test_completed_load_completed_run(self):
        stdout = ndjson(
            skill_tool_event(SKILL, "completed"),
            text_event(f"Loaded skill: **{SKILL}** — done."),
        )
        verdict = self._evaluate(stdout)
        self.assertEqual(verdict.outcome, "triggered")
        self.assertFalse(verdict.timeout)

    def test_step_cap_cutoff_with_intent(self):
        # Clean exit, parseable events, no error, but no mandated report and
        # no completed load -> rule-3 step-cap intent path.
        stdout = ndjson(
            reasoning_event("I should load the `writing-skills` skill here.")
        )
        verdict = self._evaluate(stdout)
        self.assertEqual(verdict.outcome, "triggered")
        self.assertTrue(verdict.timeout)

    def test_step_cap_cutoff_with_attempted_load(self):
        # Attempted (non-completed) skill call on the target is intent
        # evidence under rule 3.
        stdout = ndjson(skill_tool_event(SKILL, "pending"))
        verdict = self._evaluate(stdout)
        self.assertEqual(verdict.outcome, "triggered")
        self.assertTrue(verdict.timeout)

    def test_step_cap_cutoff_without_intent_is_void(self):
        # A bare mention of the skill name is not intent evidence.
        stdout = ndjson(
            reasoning_event(
                "This is not about writing-skills at all; it is a cooking "
                "question."
            )
        )
        verdict = self._evaluate(stdout)
        self.assertEqual(verdict.outcome, "void")
        self.assertTrue(verdict.timeout)

    def test_other_skill_completed_load_without_report_is_not_triggered(self):
        # Clean exit, a completed load of a DIFFERENT skill, and no
        # mandated report: positive evidence the target did not trigger,
        # not a void (observed in campaign-2026-09-13-3).
        stdout = ndjson(
            skill_tool_event("customize-opencode", "completed"),
            text_event("customize-opencode"),
        )
        verdict = self._evaluate(stdout)
        self.assertEqual(verdict.outcome, "not-triggered")
        self.assertFalse(verdict.timeout)
        self.assertIn("customize-opencode", verdict.detail)

    def test_no_match_report_present_tense_variant(self):
        # The detector accepts paraphrased no-match reports
        # ("No skill matches this request.") — observed voids in
        # campaign-2026-09-13-3 rested on this phrasing.
        stdout = ndjson(text_event("No skill matches this request."))
        verdict = self._evaluate(stdout)
        self.assertEqual(verdict.outcome, "not-triggered")
        self.assertFalse(verdict.timeout)
        self.assertIn("no skill matched", verdict.detail)

    def test_no_match_report_bare_variant(self):
        stdout = ndjson(text_event("No skill matches."))
        verdict = self._evaluate(stdout)
        self.assertEqual(verdict.outcome, "not-triggered")
        self.assertFalse(verdict.timeout)

    def test_empty_finish_without_load_or_report_is_void(self):
        # Clean exit after a target-less turn with no report and no load
        # evidence (provider returned empty content): still void.
        stdout = ndjson(reasoning_event(""))
        verdict = self._evaluate(stdout)
        self.assertEqual(verdict.outcome, "void")
        self.assertTrue(verdict.timeout)

    def test_agent_fallback_stderr_aborts(self):
        stderr = (
            f'agent "{self.strategy.agent_name}" not found. '
            f"Falling back to default agent\n"
        )
        with self.assertRaises(evaluator.HarnessExecutionError):
            self._evaluate(
                stdout=ndjson(text_event("No skill matched.")), stderr=stderr
            )


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
    and the legacy counts-flag path keeps working with a stderr
    deprecation note."""

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

    def test_legacy_counts_path_emits_deprecation_note(self):
        rc, _out, err = self._record(
            scored=None, passes=1, fails=0, gaps=0, voids=0
        )
        self.assertEqual(rc, 0)
        self.assertIn("note: counts flags are deprecated; use --scored", err)
        self.assertIn("retrieval-test", json.loads(self.manifest.read_text()))

    def test_legacy_shape_path_still_rejects_ablations(self):
        # --ablations stays a retrieval-only field on the legacy path.
        rc, _out, err = self._record(
            scored=None,
            track="shape-test",
            adopted=1,
            no_failure=0,
            unresolved=0,
            voids=0,
            ablations="x",
        )
        self.assertEqual(rc, 1)
        self.assertIn("ablations", err)


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
        _low, _high, expected = evaluator._score_counts(3, 3)
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
        _low, _high, expected = evaluator._score_counts(4, 1)
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


class FailuresTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.results = Path(self.tmp.name) / "iter-1-train.json"

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, queries: list) -> None:
        self.results.write_text(json.dumps({"queries": queries}))

    def _run(self, path: Path | None = None) -> tuple[int, str]:
        args = argparse.Namespace(results=str(path or self.results))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = evaluator.cmd_failures(args)
        return rc, buf.getvalue()

    def _failure(self, run: int = 2, reasoning: str = "it looked\nrelevant"):
        return {
            "run": run,
            "outcome": "triggered",
            "detail": "skill tool completed load",
            "reasoning": reasoning,
            "timeout": False,
        }

    def test_extracts_failed_runs_with_reasoning(self):
        self._write(
            [
                {
                    "query": "q1",
                    "should_trigger": False,
                    "failures": [self._failure()],
                }
            ]
        )
        rc, out = self._run()
        self.assertEqual(rc, 0)
        self.assertIn('query: "q1"   expected: not-trigger', out)
        self.assertIn("run 2: triggered — skill tool completed load", out)
        self.assertIn("    it looked\n    relevant", out)

    def test_session_id_printed_when_present(self):
        # New-format results (post session-tracking) name the headless
        # session on each failure line; the old format (no key) is covered
        # by test_extracts_failed_runs_with_reasoning.
        failure = self._failure()
        failure["session_id"] = "s1"
        self._write(
            [
                {
                    "query": "q1",
                    "should_trigger": False,
                    "failures": [failure],
                }
            ]
        )
        rc, out = self._run()
        self.assertEqual(rc, 0)
        self.assertIn(
            "run 2: triggered [session s1] — skill tool completed load", out
        )

    def test_query_without_failures_produces_no_block(self):
        self._write(
            [
                {"query": "q-pass", "should_trigger": True, "failures": []},
                {
                    "query": "q-fail",
                    "should_trigger": True,
                    "failures": [self._failure()],
                },
            ]
        )
        rc, out = self._run()
        self.assertEqual(rc, 0)
        self.assertNotIn("q-pass", out)
        self.assertIn("q-fail", out)

    def test_no_failures_reports_none(self):
        self._write([{"query": "q1", "should_trigger": True, "failures": []}])
        rc, out = self._run()
        self.assertEqual(rc, 0)
        self.assertIn("no failed runs", out)

    def test_missing_reasoning_marker(self):
        self._write(
            [
                {
                    "query": "q1",
                    "should_trigger": True,
                    "failures": [self._failure(reasoning="")],
                }
            ]
        )
        rc, out = self._run()
        self.assertEqual(rc, 0)
        self.assertIn("(no reasoning captured)", out)

    def test_missing_file(self):
        rc, _ = self._run(Path(self.tmp.name) / "nope.json")
        self.assertEqual(rc, 1)

    def test_invalid_json(self):
        self.results.write_text("not json")
        rc, _ = self._run()
        self.assertEqual(rc, 1)

    def test_missing_queries_key(self):
        self.results.write_text(json.dumps({"totals": {}}))
        rc, _ = self._run()
        self.assertEqual(rc, 1)


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


class HarnessWorkspaceMixin:
    """Temp workspace with a synced skill stub and a valid evaluator
    agent file, for tests that drive cmd_run/cmd_suite end to end."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.workspace = self.root / "ws"
        stub = self.workspace / ".agents" / "skills" / SKILL / "SKILL.md"
        stub.parent.mkdir(parents=True)
        stub.write_text(f"---\nname: {SKILL}\n---\n")
        self.agents_dir = self.root / "agents"
        self.agents_dir.mkdir()
        (self.agents_dir / "trigger-evaluator.opencode.md").write_text(
            "---\nname: trigger-evaluator\n---\n# Agent\n"
        )

    def tearDown(self):
        if evaluator._Log.file is not None:
            evaluator._Log.file.close()
            evaluator._Log.file = None
        self.tmp.cleanup()

    def _proc(self, stdout: str) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=[], returncode=0, stdout=stdout, stderr=""
        )

    def _triggered(self, session: str) -> str:
        return ndjson(
            session_event(
                session,
                "tool_use",
                {
                    "type": "tool",
                    "tool": "skill",
                    "state": {
                        "status": "completed",
                        "input": {"name": SKILL},
                    },
                },
            ),
            session_event(
                session,
                "text",
                {"type": "text", "text": f"Loaded skill: {SKILL}"},
            ),
        )

    def _no_match(self, session: str) -> str:
        return ndjson(
            session_event(
                session,
                "text",
                {"type": "text", "text": "No skill matched this request."},
            )
        )

    def _void(self, session: str) -> str:
        return ndjson(
            session_event(
                session,
                "reasoning",
                {
                    "type": "reasoning",
                    "text": "The user wants a poem about Paris.",
                },
            )
        )


class SuiteTests(HarnessWorkspaceMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.queries = self.root / "queries.json"
        self.queries.write_text(
            json.dumps([{"query": "q1", "shouldTrigger": True}])
        )
        self.out = self.root / "results.json"

    def _run_suite(self, procs: list) -> int:
        args = argparse.Namespace(
            harness="opencode",
            skill=SKILL,
            agents_dir=str(self.agents_dir),
            workspace=str(self.workspace),
            queries=str(self.queries),
            out=str(self.out),
            model=None,
            variant=None,
            reps=len(procs),
            timeout=30,
        )
        with (
            mock.patch.object(strategies.subprocess, "run", side_effect=procs),
            mock.patch.object(
                strategies.shutil, "which", return_value="/usr/bin/opencode"
            ),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            return evaluator.cmd_suite(args)

    def test_failures_and_voids_carry_session_ids(self):
        # rep 1 passes (smoke rep); reps 2 and 3 run concurrently and may
        # consume the two remaining streams in either order, so the run
        # numbers are asserted as a set.
        procs = [
            self._proc(self._triggered("s-pass")),
            self._proc(self._no_match("s-fail")),
            self._proc(self._void("s-void")),
        ]
        rc = self._run_suite(procs)
        self.assertEqual(rc, 0)
        q = json.loads(self.out.read_text())["queries"][0]
        self.assertEqual(q["passed"], 1)
        self.assertEqual(q["failed"], 1)
        self.assertEqual(q["void"], 1)

        self.assertEqual(len(q["failures"]), 1)
        failure = q["failures"][0]
        self.assertEqual(failure["outcome"], "not-triggered")
        self.assertEqual(failure["session_id"], "s-fail")

        self.assertEqual(len(q["voids"]), 1)
        void = q["voids"][0]
        self.assertEqual(void["session_id"], "s-void")
        self.assertTrue(void["timeout"])
        self.assertIn("final report missing", void["detail"])

        self.assertEqual({failure["run"], void["run"]}, {2, 3})

    def test_passing_runs_leave_failures_and_voids_empty(self):
        rc = self._run_suite([self._proc(self._triggered("s1"))])
        self.assertEqual(rc, 0)
        q = json.loads(self.out.read_text())["queries"][0]
        self.assertEqual(q["failures"], [])
        self.assertEqual(q["voids"], [])


class AbortSessionTests(HarnessWorkspaceMixin, unittest.TestCase):
    def _run_args(self, reps: int) -> argparse.Namespace:
        return argparse.Namespace(
            harness="opencode",
            skill=SKILL,
            agents_dir=str(self.agents_dir),
            workspace=str(self.workspace),
            query="q",
            expect="trigger",
            model=None,
            variant=None,
            reps=reps,
            timeout=30,
        )

    def _error_proc(self, session: str) -> subprocess.CompletedProcess:
        err_event = {
            "type": "error",
            "sessionID": session,
            "error": {"data": {"message": "provider 429"}},
        }
        return self._proc(ndjson(err_event))

    def _run_expecting_abort(self, procs, reps: int) -> str:
        buf = io.StringIO()
        with (
            mock.patch.object(strategies.subprocess, "run", **procs),
            contextlib.redirect_stderr(buf),
            contextlib.redirect_stdout(io.StringIO()),
            self.assertRaises(SystemExit),
        ):
            evaluator.cmd_run(self._run_args(reps))
        return buf.getvalue()

    def test_smoke_abort_line_carries_session_id(self):
        err = self._run_expecting_abort(
            {"return_value": self._error_proc("s1")}, reps=1
        )
        self.assertIn("provider 429", err)
        self.assertIn("[session s1]", err)

    def test_batch_abort_line_carries_session_id(self):
        ok = self._proc(ndjson(skill_tool_event(SKILL, "completed")))
        err = self._run_expecting_abort(
            {"side_effect": [ok, self._error_proc("s2")]}, reps=2
        )
        self.assertIn("rep 2 could not execute", err)
        self.assertIn("[session s2]", err)


class ShapeInjectionTests(unittest.TestCase):
    """Shape track: prompt injection (not byte-states). Covers arm body
    assembly, the injected prompt, the new void signals, and the
    end-to-end suite path with a sterile workspace."""

    BODY = (
        "# Conventions\n"
        "\n"
        "## Styling\n"
        "Always use CSS modules.\n"
        "\n"
        "## Layout\n"
        "One file per component.\n"
    )
    # The span covers the whole section, heading included — the form the
    # doc-drift gate and assemble_arm_body are designed around.
    SECTION = "## Styling\nAlways use CSS modules."
    ENTRY = {
        "id": "R-styling-01",
        "kind": "shaping",
        "section": SECTION,
        "fixtures": {
            "application": "Build a Badge component.",
            "counter-example": "Build a plain div.",
        },
        "variants": {"v1": "Never use inline styles."},
    }

    def test_v0_removes_span_and_one_blank_line(self):
        arm_body = evaluator.assemble_arm_body(self.BODY, self.ENTRY, "v0")
        self.assertNotIn(self.SECTION, arm_body)
        # Neighbour sections keep exactly one blank line between them.
        self.assertIn("# Conventions\n\n## Layout", arm_body)

    def test_variant_replaces_span(self):
        arm_body = evaluator.assemble_arm_body(self.BODY, self.ENTRY, "v1")
        self.assertIn("Never use inline styles.", arm_body)
        self.assertNotIn(self.SECTION, arm_body)

    def test_non_unique_span_raises(self):
        body = self.BODY + "\n" + self.SECTION + "\n"
        with self.assertRaises(ValueError):
            evaluator.assemble_arm_body(body, self.ENTRY, "v0")

    def test_verify_arm_bytes_catches_bad_assembly(self):
        with self.assertRaises(ValueError):
            evaluator.verify_arm_bytes(self.BODY, self.ENTRY, "v0")
        with self.assertRaises(ValueError):
            evaluator.verify_arm_bytes(self.BODY, self.ENTRY, "v1")
        ok = evaluator.assemble_arm_body(self.BODY, self.ENTRY, "v0")
        evaluator.verify_arm_bytes(ok, self.ENTRY, "v0")  # no raise

    def test_prompt_injects_conventions_and_fixture(self):
        arm_body = evaluator.assemble_arm_body(self.BODY, self.ENTRY, "v0")
        prompt = evaluator.build_shape_prompt(
            arm_body, self.ENTRY["fixtures"]["application"]
        )
        self.assertTrue(prompt.startswith("Project conventions:\n"))
        self.assertIn(arm_body, prompt)
        self.assertTrue(prompt.endswith("Task:\nBuild a Badge component."))
        self.assertNotIn(self.SECTION, prompt)

    def _ev(self, events: list[dict]):
        return strategies.OpencodeStrategy.parse_stream(ndjson(*events), None)

    def test_skill_load_attempt_is_void_signal(self):
        ev = self._ev(
            [
                skill_tool_event("anything", "completed"),
                text_event("the artifact"),
            ]
        )
        record = evaluator.build_shape_run_record(
            ev, "p", False, Path("/"), "v0"
        )
        self.assertIn("skill-load-attempted", record["void_signals"])
        self.assertNotIn("empty-answer", record["void_signals"])

    def test_clean_run_has_no_signals(self):
        ev = self._ev([text_event("the artifact")])
        record = evaluator.build_shape_run_record(
            ev, "p", False, Path("/"), "v0"
        )
        self.assertEqual(record["void_signals"], [])
        self.assertNotIn("skill_load_completed", record)


class ShapeSuiteEndToEndTests(unittest.TestCase):
    """cmd_shape_suite with a stubbed harness: injection lands in the
    dispatched prompt and the sterile workspace is never written."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.workspace = self.root / "ws"
        self.workspace.mkdir()
        self.agents_dir = self.root / "agents"
        self.agents_dir.mkdir()
        (self.agents_dir / "shape-evaluator.opencode.md").write_text(
            "---\nname: shape-evaluator\n---\n# Agent\n"
        )
        self.skill_body = self.root / "skill-body.txt"
        self.skill_body.write_text(
            "# Conventions\n\n## Styling\nAlways use CSS modules.\n"
        )
        self.entries = self.root / "entries.json"
        self.entries.write_text(
            json.dumps(
                [
                    {
                        "id": "R-styling-01",
                        "rule": "R-styling-01",
                        "kind": "shaping",
                        "section": "Always use CSS modules.",
                        "fixtures": {"application": "Build a Badge."},
                        "markers": {"inline-style": r"style="},
                        "variants": {"v1": "Never use inline styles."},
                    }
                ]
            )
        )
        self.out = self.root / "results.json"

    def tearDown(self):
        if evaluator._Log.file is not None:
            evaluator._Log.file.close()
            evaluator._Log.file = None
        self.tmp.cleanup()

    def _args(self) -> argparse.Namespace:
        return argparse.Namespace(
            harness="opencode",
            skill=SKILL,
            agents_dir=str(self.agents_dir),
            workspace=str(self.workspace),
            entries=str(self.entries),
            skill_file=str(self.skill_body),
            arms="v0,v1",
            out=str(self.out),
            fixture_key="application",
            model=None,
            variant=None,
            reps=1,
            timeout=30,
        )

    def _answer(self, session: str) -> str:
        part = {"type": "text", "text": "artifact"}
        return ndjson(session_event(session, "text", part))

    def _proc(self, stdout: str) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=[], returncode=0, stdout=stdout, stderr=""
        )

    def test_injection_lands_and_workspace_stays_sterile(self):
        with (
            mock.patch.object(
                strategies.subprocess,
                "run",
                return_value=self._proc(self._answer("s1")),
            ),
            mock.patch.object(
                strategies.shutil, "which", return_value="/usr/bin/opencode"
            ),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            rc = evaluator.cmd_shape_suite(self._args())
        self.assertEqual(rc, 0)
        data = json.loads(self.out.read_text())
        self.assertEqual(data["config"]["skill_file"], str(self.skill_body))
        runs_v0 = data["entries"][0]["arms"]["v0"]["runs"]
        runs_v1 = data["entries"][0]["arms"]["v1"]["runs"]
        # v0 injects the body minus the rule span; v1 injects the variant.
        dispatched_v0 = runs_v0[0]["query_dispatched"]
        dispatched_v1 = runs_v1[0]["query_dispatched"]
        self.assertNotIn("Always use CSS modules.", dispatched_v0)
        self.assertIn("Never use inline styles.", dispatched_v1)
        for runs in (runs_v0, runs_v1):
            self.assertTrue(
                runs[0]["query_dispatched"].startswith(
                    "Project conventions:\n"
                )
            )
            self.assertEqual(runs[0]["void_signals"], [])
        # Nothing was synced or written into the workspace.
        self.assertFalse((self.workspace / ".agents").exists())

    def test_synced_skill_fails_contamination_gate(self):
        stub = self.workspace / ".agents" / "skills" / SKILL / "SKILL.md"
        stub.parent.mkdir(parents=True)
        stub.write_text("---\nname: x\n---\n")
        buf = io.StringIO()
        with (
            mock.patch.object(
                strategies.shutil, "which", return_value="/usr/bin/opencode"
            ),
            contextlib.redirect_stderr(buf),
            contextlib.redirect_stdout(io.StringIO()),
            self.assertRaises(SystemExit),
        ):
            evaluator.cmd_shape_suite(self._args())
        self.assertIn("never sync", buf.getvalue())

    def test_missing_skill_file_fails_pre_spend(self):
        args = self._args()
        args.skill_file = str(self.root / "absent.txt")
        buf = io.StringIO()
        with (
            mock.patch.object(
                strategies.shutil, "which", return_value="/usr/bin/opencode"
            ),
            contextlib.redirect_stderr(buf),
            contextlib.redirect_stdout(io.StringIO()),
            self.assertRaises(SystemExit),
        ):
            evaluator.cmd_shape_suite(args)
        self.assertIn("skill file not found", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
