#!/usr/bin/env python3
"""Tests for the trigger track (src/tracks.py TriggerTrack): the
verdict-logic edge paths (interrupted runs, rejected skill calls, opencode's
silent agent fallback), the single-query cmd_run abort lines, the suite
driver's results envelope (failures/voids with session ids), the empty-query
log mirror, and the evidence --track trigger-test printer (the old
`failures` extractor). subprocess.run is stubbed; no live model is involved.
"""

import argparse
import contextlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import evaluator
from src import strategies
from src.strategies import HarnessExecutionError, Verdict
from src.tracks import TRACKS, cmd_run

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
    ) -> Verdict:
        proc = subprocess.CompletedProcess(
            args=[], returncode=returncode, stdout=stdout, stderr=stderr
        )
        with mock.patch.object(
            strategies.subprocess, "run", return_value=proc
        ):
            return self.strategy.evaluate(SKILL, "test query", self.ws)

    def _evaluate_timeout(self, partial_stdout: str) -> Verdict:
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
        with self.assertRaises(HarnessExecutionError):
            self._evaluate(
                stdout=ndjson(text_event("No skill matched.")), stderr=stderr
            )


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
            rc = TRACKS["trigger-test"].print_evidence(args)
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


class HarnessWorkspaceMixin:
    """Temp workspace with a synced skill stub and a valid evaluator
    agent file, for tests that drive cmd_run/run_suite end to end."""

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
            return evaluator.run_suite(TRACKS["trigger-test"], args)

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
            cmd_run(self._run_args(reps))
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


class EmptyTriggerLogTests(HarnessWorkspaceMixin, unittest.TestCase):
    """§2.7 ordering pin: the campaign-log mirror opens before the
    zero_results_on_empty branch, so an empty trigger campaign still
    creates/truncates the .log and mirrors the note into it."""

    def test_empty_query_file_creates_log_with_note(self):
        queries = self.root / "queries.json"
        queries.write_text("[]")
        out = self.root / "results.json"
        args = argparse.Namespace(
            harness="opencode",
            skill=SKILL,
            agents_dir=str(self.agents_dir),
            workspace=str(self.workspace),
            queries=str(queries),
            out=str(out),
            model=None,
            variant=None,
            reps=None,
            timeout=None,
        )
        with (
            mock.patch.object(evaluator, "check_harness"),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            rc = evaluator.run_suite(TRACKS["trigger-test"], args)
        self.assertEqual(rc, 0)
        log = out.with_suffix(".log")
        self.assertTrue(log.exists())
        self.assertIn("note: empty query file", log.read_text())
        # The zeroed envelope carries the per-track default reps/timeout.
        data = json.loads(out.read_text())
        self.assertEqual(data["queries"], [])
        self.assertEqual(data["totals"]["score"], None)
        self.assertEqual((data["reps"], data["timeout"]), (3, 30))


if __name__ == "__main__":
    unittest.main()
