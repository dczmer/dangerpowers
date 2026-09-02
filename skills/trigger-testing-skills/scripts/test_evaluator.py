#!/usr/bin/env python3
"""Fixture-driven tests for the evaluator's verdict logic.

subprocess.run is stubbed; no live model is involved. Covers the signal
edge paths: interrupted runs (subprocess timeout and step-cap cutoff),
rejected skill calls, and opencode's silent agent fallback.
"""

import json
import subprocess
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


if __name__ == "__main__":
    unittest.main()
