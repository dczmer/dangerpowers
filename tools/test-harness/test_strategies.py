#!/usr/bin/env python3
"""Tests for strategies.py: frontmatter scanning, agent install,
parse_stream evidence capture, execute() timeout behavior, and the
G6 Python-3.10 grammar gate.

All agent files are synthetic fixtures in temp dirs — never the real
skill agent files. subprocess.run is stubbed; no live model is involved.
"""

import ast
import contextlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import strategies

SKILL = "writing-skills"


def ndjson(*events: dict) -> str:
    return "\n".join(json.dumps(e) for e in events) + "\n"


def event(etype: str, part: dict) -> dict:
    return {"type": etype, "sessionID": "s1", "part": part}


def text_event(text: str) -> dict:
    return event("text", {"type": "text", "text": text})


def tool_event(tool: str, state: dict) -> dict:
    return event("tool_use", {"type": "tool", "tool": tool, "state": state})


class ScanFrontmatterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, text: str) -> Path:
        f = self.root / "agent.opencode.md"
        f.write_text(text)
        return f

    def _scan(self, path: Path):
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            try:
                strategies.scan_agent_frontmatter(path)
            except SystemExit as e:
                return e, buf.getvalue()
        return None, buf.getvalue()

    def test_name_found(self):
        info = strategies.scan_agent_frontmatter(
            self._write("---\nname: my-agent\nmode: primary\n---\nbody\n")
        )
        self.assertEqual(info, {"name": "my-agent", "pins": []})

    def test_pins_detected(self):
        info = strategies.scan_agent_frontmatter(
            self._write(
                "---\nname: my-agent\nmodel: gpt-x\ntop_p: 0.5\n" "---\nbody\n"
            )
        )
        self.assertEqual(info["name"], "my-agent")
        self.assertEqual(info["pins"], ["model", "top_p"])

    def test_missing_frontmatter_exits(self):
        e, err = self._scan(self._write("no frontmatter here\n"))
        self.assertIsNotNone(e)
        assert e is not None
        self.assertEqual(e.code, 1)
        self.assertIn("missing frontmatter block", err)

    def test_missing_name_exits(self):
        e, err = self._scan(self._write("---\ndescription: x\n---\nbody\n"))
        self.assertIsNotNone(e)
        assert e is not None
        self.assertEqual(e.code, 1)
        self.assertIn("no 'name:'", err)


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.agents_dir = self.root / "agents"
        self.agents_dir.mkdir()
        self.workspace = self.root / "ws"

    def tearDown(self):
        self.tmp.cleanup()

    def _write_agent(
        self, base: str, name: str | None = None, extra: str = ""
    ) -> Path:
        text = (
            "---\n"
            f"name: {name or base}\n"
            f"{extra}"
            "---\n"
            "# Agent\n"
            "Load {{SKILL_NAME}} first.\n"
        )
        f = self.agents_dir / f"{base}.opencode.md"
        f.write_text(text)
        return f

    def _install(self, base: str, **kwargs):
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            try:
                return (
                    strategies.OpencodeStrategy().install(
                        self.workspace, self.agents_dir, base, **kwargs
                    ),
                    None,
                    buf.getvalue(),
                )
            except SystemExit as e:
                return None, e, buf.getvalue()

    def _dest(self, base: str) -> Path:
        return self.workspace / ".opencode" / "agent" / f"{base}.md"

    def test_templating_substitution(self):
        self._write_agent("retrieval-evaluator")
        name, err, _ = self._install(
            "retrieval-evaluator", skill_name="my-skill"
        )
        self.assertIsNone(err)
        self.assertEqual(name, "retrieval-evaluator")
        text = self._dest("retrieval-evaluator").read_text()
        self.assertIn("Load my-skill first.", text)
        self.assertNotIn("{{SKILL_NAME}}", text)

    def test_verbatim_when_skill_name_none(self):
        self._write_agent("trigger-evaluator")
        name, err, _ = self._install("trigger-evaluator")
        self.assertIsNone(err)
        self.assertEqual(name, "trigger-evaluator")
        self.assertIn(
            "{{SKILL_NAME}}", self._dest("trigger-evaluator").read_text()
        )

    def test_dest_path(self):
        self._write_agent("trigger-evaluator")
        self._install("trigger-evaluator")
        self.assertTrue(self._dest("trigger-evaluator").is_file())
        self.assertFalse((self.workspace / "trigger-evaluator.md").exists())

    def test_name_mismatch_exits(self):
        self._write_agent("trigger-evaluator", name="other-agent")
        _, e, err = self._install("trigger-evaluator")
        self.assertIsNotNone(e)
        assert e is not None
        self.assertEqual(e.code, 1)
        self.assertIn("does not match expected 'trigger-evaluator'", err)

    def test_model_pin_exits(self):
        self._write_agent("trigger-evaluator", extra="model: gpt-1\n")
        _, e, err = self._install("trigger-evaluator")
        self.assertIsNotNone(e)
        assert e is not None
        self.assertEqual(e.code, 1)
        self.assertIn("pins model config", err)
        self.assertIn("model", err)

    def test_missing_file_exits(self):
        _, e, err = self._install("no-such-agent")
        self.assertIsNotNone(e)
        assert e is not None
        self.assertEqual(e.code, 1)
        self.assertIn("evaluator agent file missing", err)


class ParseStreamTests(unittest.TestCase):
    def _parse(self, *events: dict, skill=SKILL) -> strategies.EventStream:
        return strategies.OpencodeStrategy.parse_stream(ndjson(*events), skill)

    def test_answer_concatenation(self):
        ev = self._parse(text_event("Hello "), text_event("world."))
        self.assertEqual(ev.answer_parts, ["Hello ", "world."])
        self.assertEqual("".join(ev.answer_parts), "Hello world.")

    def test_read_grep_glob_targets(self):
        ev = self._parse(
            tool_event(
                "read",
                {"status": "completed", "input": {"filePath": "/ws/SKILL.md"}},
            ),
            tool_event(
                "grep",
                {"status": "completed", "input": {"pattern": "retry-after"}},
            ),
            tool_event(
                "glob", {"status": "completed", "input": {"pattern": "*.md"}}
            ),
        )
        self.assertEqual(
            ev.tool_calls,
            [
                {"tool": "read", "target": "/ws/SKILL.md"},
                {"tool": "grep", "target": "retry-after"},
                {"tool": "glob", "target": "*.md"},
            ],
        )

    def test_skill_load_log(self):
        ev = self._parse(
            tool_event(
                "skill", {"status": "completed", "input": {"name": SKILL}}
            ),
            tool_event(
                "skill", {"status": "error", "input": {"name": "other-skill"}}
            ),
        )
        self.assertEqual(
            ev.skill_loads,
            [
                {"name": SKILL, "status": "completed"},
                {"name": "other-skill", "status": "error"},
            ],
        )
        # The trigger-track classification fields still derive from the
        # same events.
        self.assertTrue(ev.completed_load)
        self.assertEqual(ev.other_skill, "other-skill")

    def test_trigger_regexes_still_fire(self):
        ev = self._parse(
            text_event(f"Loaded skill: **{SKILL}** — done."),
            text_event("No skill matched the query."),
        )
        self.assertEqual(ev.report_loaded, SKILL)
        self.assertTrue(ev.report_no_match)

    def test_denied_hook_removed_field_stays_empty(self):
        # opencode never emits denied-attempt events (dead code pruned in
        # Phase 11); the parse branch is gone, so even a hypothetical
        # denied event leaves the field empty.
        denied = {"type": "tool_denied", "part": {}}
        ev = self._parse(denied, text_event("No skill matched."))
        self.assertEqual(ev.denied_tool_attempts, [])
        self.assertTrue(ev.report_no_match)


class ExecuteTests(unittest.TestCase):
    def _execute(
        self, proc: subprocess.CompletedProcess
    ) -> strategies.HarnessExecutionError:
        with mock.patch.object(
            strategies.subprocess, "run", return_value=proc
        ):
            with self.assertRaises(strategies.HarnessExecutionError) as ctx:
                strategies.OpencodeStrategy(timeout=5).execute(
                    Path("/tmp/fake-workspace"),
                    "trigger-evaluator",
                    "q",
                    skill=SKILL,
                )
            return ctx.exception

    def test_timeout_returns_partial_stream(self):
        partial = ndjson(text_event("partial answer"))
        err = subprocess.TimeoutExpired(
            cmd=["opencode"], timeout=5, output=partial
        )
        with mock.patch.object(strategies.subprocess, "run", side_effect=err):
            ev, timed_out = strategies.OpencodeStrategy(timeout=5).execute(
                Path("/tmp/fake-workspace"),
                "trigger-evaluator",
                "query",
                skill=SKILL,
            )
        self.assertTrue(timed_out)
        self.assertEqual("".join(ev.answer_parts), "partial answer")
        self.assertGreater(ev.parseable, 0)
        self.assertEqual(ev.session_id, "s1")

    def test_error_event_raises_with_session_id(self):
        err_event = {
            "type": "error",
            "sessionID": "s1",
            "error": {"data": {"message": "provider 429"}},
        }
        proc = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=ndjson(err_event), stderr=""
        )
        e = self._execute(proc)
        self.assertIn("provider 429", str(e))
        self.assertEqual(e.session_id, "s1")

    def test_nonzero_exit_raises_with_session_id(self):
        proc = subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stdout=ndjson(text_event("partial answer")),
            stderr="boom",
        )
        e = self._execute(proc)
        self.assertIn("exit 1", str(e))
        self.assertEqual(e.session_id, "s1")

    def test_zero_parseable_events_raises(self):
        proc = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="not json\n", stderr=""
        )
        e = self._execute(proc)
        self.assertIn("no parseable events", str(e))
        self.assertEqual(e.session_id, "")


class GrammarGateTests(unittest.TestCase):
    def test_strategies_py_parses_with_py310_grammar(self):
        src = Path(strategies.__file__).read_text()
        ast.parse(src, filename="strategies.py", feature_version=(3, 10))


if __name__ == "__main__":
    unittest.main()
