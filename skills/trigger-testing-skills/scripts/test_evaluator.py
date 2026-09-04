#!/usr/bin/env python3
"""Fixture-driven tests for the evaluator's verdict logic.

subprocess.run is stubbed; no live model is involved. Covers the signal
edge paths: interrupted runs (subprocess timeout and step-cap cutoff),
rejected skill calls, and opencode's silent agent fallback.
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

SKILL = "writing-skills"


def ndjson(*events: dict) -> str:
    return "\n".join(json.dumps(e) for e in events) + "\n"


def reasoning_event(text: str) -> dict:
    return {"type": "reasoning", "sessionID": "s1",
            "part": {"type": "reasoning", "text": text}}


def text_event(text: str) -> dict:
    return {"type": "text", "sessionID": "s1",
            "part": {"type": "text", "text": text}}


def skill_tool_event(name: str, status: str) -> dict:
    return {"type": "tool_use", "sessionID": "s1",
            "part": {"type": "tool", "tool": "skill",
                     "state": {"status": status, "input": {"name": name}}}}


class VerdictTests(unittest.TestCase):
    def setUp(self):
        self.strategy = evaluator.OpencodeStrategy(timeout=30)
        self.ws = Path("/tmp/fake-workspace")

    def _evaluate(self, stdout: str = "", stderr: str = "",
                  returncode: int = 0) -> evaluator.Verdict:
        proc = subprocess.CompletedProcess(args=[], returncode=returncode,
                                           stdout=stdout, stderr=stderr)
        with mock.patch.object(evaluator.subprocess, "run", return_value=proc):
            return self.strategy.evaluate(SKILL, "test query", self.ws)

    def _evaluate_timeout(self, partial_stdout: str) -> evaluator.Verdict:
        err = subprocess.TimeoutExpired(cmd=["opencode"], timeout=30,
                                        output=partial_stdout)
        with mock.patch.object(evaluator.subprocess, "run", side_effect=err):
            return self.strategy.evaluate(SKILL, "test query", self.ws)

    def test_timeout_with_intent_partial_stream(self):
        # Interrupted run with clear intent evidence but no completed load:
        # triggered, flagged timeout: true.
        partial = ndjson(reasoning_event(
            "I should load the `writing-skills` skill for this."))
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
        stdout = ndjson(reasoning_event(
            "I should load the `writing-skills` skill here."))
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
        stdout = ndjson(reasoning_event(
            "This is not about writing-skills at all; it is a cooking "
            "question."))
        verdict = self._evaluate(stdout)
        self.assertEqual(verdict.outcome, "void")
        self.assertTrue(verdict.timeout)

    def test_agent_fallback_stderr_aborts(self):
        stderr = (f'agent "{self.strategy.agent_name}" not found. '
                  f'Falling back to default agent\n')
        with self.assertRaises(evaluator.HarnessExecutionError):
            self._evaluate(stdout=ndjson(text_event("No skill matched.")),
                           stderr=stderr)


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
            skill="test-skill", skill_path=str(self.skill_md),
            manifest=str(self.manifest), score=0.81,
            campaign="campaign-2026-09-02", date=None)
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
        self.skill_md.write_text("---\nname: test-skill\ndescription: x\n---"
                                 "\nbody\n")
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
        self.manifest.write_text(json.dumps(
            {"future-test": {"date": "x"},
             "trigger-test": {"date": "old", "checksum": "sha256:old",
                              "score": 0.5}}))
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
        return {"run": run, "outcome": "triggered",
                "detail": "skill tool completed load",
                "reasoning": reasoning, "timeout": False}

    def test_extracts_failed_runs_with_reasoning(self):
        self._write([{"query": "q1", "should_trigger": False,
                      "failures": [self._failure()]}])
        rc, out = self._run()
        self.assertEqual(rc, 0)
        self.assertIn('query: "q1"   expected: not-trigger', out)
        self.assertIn("run 2: triggered — skill tool completed load", out)
        self.assertIn("    it looked\n    relevant", out)

    def test_query_without_failures_produces_no_block(self):
        self._write([{"query": "q-pass", "should_trigger": True,
                      "failures": []},
                     {"query": "q-fail", "should_trigger": True,
                      "failures": [self._failure()]}])
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
        self._write([{"query": "q1", "should_trigger": True,
                      "failures": [self._failure(reasoning="")]}])
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


if __name__ == "__main__":
    unittest.main()
