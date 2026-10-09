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

from src import strategies

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

    def test_list_tool_call_captured(self):
        # The read-quartet allow-list must be fully observable: a "list"
        # tool_use event lands in ev.tool_calls like read/grep/glob.
        ev = self._parse(
            tool_event(
                "list", {"status": "completed", "input": {"path": "/ws"}}
            ),
        )
        self.assertEqual(ev.tool_calls, [{"tool": "list", "target": "/ws"}])

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

    def test_session_builds_resume_flag(self):
        proc = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=ndjson(text_event("a")), stderr=""
        )
        with mock.patch.object(
            strategies.subprocess, "run", return_value=proc
        ) as run_mock:
            strategies.OpencodeStrategy(timeout=5).execute(
                Path("/tmp/fake-workspace"),
                "pressure-evaluator",
                "why did you choose B?",
                session="sess-42",
            )
        cmd = run_mock.call_args.args[0]
        idx = cmd.index("--session")
        self.assertEqual(cmd[idx + 1], "sess-42")
        # The query stays the final positional argument.
        self.assertEqual(cmd[-1], "why did you choose B?")

    def test_no_session_omits_resume_flag(self):
        proc = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=ndjson(text_event("a")), stderr=""
        )
        with mock.patch.object(
            strategies.subprocess, "run", return_value=proc
        ) as run_mock:
            strategies.OpencodeStrategy(timeout=5).execute(
                Path("/tmp/fake-workspace"),
                "trigger-evaluator",
                "q",
                skill=SKILL,
            )
        self.assertNotIn("--session", run_mock.call_args.args[0])


class CheckModelTests(unittest.TestCase):
    def _models_proc(
        self, returncode: int = 0, stdout: str = "", stderr: str = ""
    ) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=[], returncode=returncode, stdout=stdout, stderr=stderr
        )

    def _check(self, model: str, proc: subprocess.CompletedProcess):
        with mock.patch.object(
            strategies.subprocess, "run", return_value=proc
        ) as run_mock:
            result = strategies.OpencodeStrategy.check_model(model)
        return result, run_mock

    def test_model_found(self):
        proc = self._models_proc(
            stdout="opencode/gpt-5\nopencode/kimi-k2.6\n\n"
        )
        result, run_mock = self._check("opencode/kimi-k2.6", proc)
        self.assertIsNone(result)
        self.assertEqual(run_mock.call_args.args[0], ["opencode", "models"])

    def test_model_not_found(self):
        proc = self._models_proc(stdout="opencode/gpt-5\n")
        result, _ = self._check("opencode/nope", proc)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIn("model 'opencode/nope' not found", result)
        self.assertIn("1 available", result)

    def test_substring_model_does_not_match(self):
        # Exact-line match only: 'kimi-k2.6' must not satisfy a lookup of
        # the different id 'kimi-k2'.
        proc = self._models_proc(stdout="opencode/kimi-k2.6\n")
        result, _ = self._check("opencode/kimi-k2", proc)
        self.assertIsNotNone(result)

    def test_models_nonzero_exit(self):
        proc = self._models_proc(returncode=1, stderr="auth expired")
        result, _ = self._check("opencode/gpt-5", proc)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIn("exited 1", result)
        self.assertIn("auth expired", result)

    def test_models_empty_output(self):
        result, _ = self._check("opencode/gpt-5", self._models_proc())
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIn("printed no models", result)

    def test_base_class_is_noop(self):
        self.assertIsNone(strategies.EvalStrategy.check_model("anything"))


class CheckHarnessTests(unittest.TestCase):
    def _run(self, binary: str | None, model: str | None):
        buf = io.StringIO()
        with (
            mock.patch.object(strategies.shutil, "which", return_value=binary),
            contextlib.redirect_stdout(buf),
            contextlib.redirect_stderr(buf),
        ):
            try:
                strategies.check_harness(
                    "opencode", strategies.OpencodeStrategy, model
                )
            except SystemExit as e:
                return e, buf.getvalue()
        return None, buf.getvalue()

    def test_binary_missing_exits(self):
        e, out = self._run(None, None)
        self.assertIsNotNone(e)
        assert e is not None
        self.assertEqual(e.code, 1)
        self.assertIn("CLI not found on PATH", out)

    def test_model_given_and_valid(self):
        proc = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="opencode/gpt-5\n", stderr=""
        )
        with mock.patch.object(
            strategies.subprocess, "run", return_value=proc
        ):
            e, out = self._run("/usr/bin/opencode", "opencode/gpt-5")
        self.assertIsNone(e)
        self.assertIn("ok: harness 'opencode' available", out)
        self.assertIn("ok: model 'opencode/gpt-5' available", out)

    def test_model_given_and_invalid_exits(self):
        proc = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="opencode/gpt-5\n", stderr=""
        )
        with mock.patch.object(
            strategies.subprocess, "run", return_value=proc
        ):
            e, out = self._run("/usr/bin/opencode", "opencode/nope")
        self.assertIsNotNone(e)
        assert e is not None
        self.assertEqual(e.code, 1)
        self.assertIn("model 'opencode/nope' not found", out)

    def test_model_none_skips_model_check(self):
        with mock.patch.object(strategies.subprocess, "run") as run_mock:
            e, out = self._run("/usr/bin/opencode", None)
        self.assertIsNone(e)
        run_mock.assert_not_called()
        self.assertIn("ok: harness 'opencode' available", out)
        self.assertNotIn("ok: model", out)


PI_JSONL = "\n".join(
    json.dumps(e)
    for e in [
        {
            "type": "session",
            "version": 3,
            "id": "abc-123",
            "timestamp": "2026-09-30T21:14:21.285Z",
            "cwd": "/tmp/ws",
        },
        {"type": "agent_start"},
        {
            "type": "message_end",
            "message": {
                "role": "user",
                "content": [{"type": "text", "text": "q"}],
            },
        },
        {
            "type": "message_end",
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "type": "thinking",
                        "thinking": "I should load the skill",
                    },
                    {"type": "toolCall", "id": "t1", "name": "read"},
                ],
            },
        },
        {
            "type": "tool_execution_start",
            "toolCallId": "t1",
            "toolName": "read",
            "args": {"path": "/tmp/ws/.agents/skills/echo-skill/SKILL.md"},
        },
        {
            "type": "tool_execution_end",
            "toolCallId": "t1",
            "toolName": "read",
            "result": {"content": [{"type": "text", "text": "..."}]},
            "isError": False,
        },
        {
            "type": "message_end",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "loaded skill: echo-skill"}
                ],
                "stopReason": "stop",
            },
        },
        {"type": "agent_end", "messages": [], "willRetry": False},
        {"type": "agent_settled"},
    ]
)

PI_SKILL = "echo-skill"


def pi_tool_events(
    tool: str, args: dict, *, is_error: bool = False, tcid: str = "t1"
) -> str:
    """A correlated tool_execution_start/end pair as pi JSONL."""
    return "\n".join(
        [
            json.dumps(
                {
                    "type": "tool_execution_start",
                    "toolCallId": tcid,
                    "toolName": tool,
                    "args": args,
                }
            ),
            json.dumps(
                {
                    "type": "tool_execution_end",
                    "toolCallId": tcid,
                    "toolName": tool,
                    "isError": is_error,
                }
            ),
        ]
    )


def pi_text_event(text: str) -> str:
    return json.dumps(
        {
            "type": "message_end",
            "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": text}],
            },
        }
    )


class ParsePiAgentTests(unittest.TestCase):
    def _parse(self, text: str):
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            try:
                return strategies.parse_pi_agent(text, "agent.pi.md"), None
            except SystemExit as e:
                return None, (e, buf.getvalue())

    def test_full_frontmatter(self):
        cfg, err = self._parse(
            "---\n"
            "name: retrieval-evaluator\n"
            "tools: read,grep,find,ls\n"
            "steps: 30\n"
            "skill: allow\n"
            "---\n"
            "# Agent\n"
            "Body text.\n"
        )
        self.assertIsNone(err)
        assert cfg is not None
        self.assertEqual(cfg["tools"], ["read", "grep", "find", "ls"])
        self.assertEqual(cfg["steps"], 30)
        self.assertEqual(cfg["skill"], "allow")
        self.assertEqual(cfg["body"], "# Agent\nBody text.\n")

    def test_defaults(self):
        # No tools: line -> [] (= --no-tools); no steps: -> 0 (no cap);
        # no skill: -> deny.
        cfg, err = self._parse("---\nname: a\n---\nBody\n")
        self.assertIsNone(err)
        assert cfg is not None
        self.assertEqual(cfg["tools"], [])
        self.assertEqual(cfg["steps"], 0)
        self.assertEqual(cfg["skill"], "deny")
        self.assertEqual(cfg["body"], "Body\n")

    def test_unknown_tool_exits(self):
        _, err = self._parse("---\nname: a\ntools: read,webfetch\n---\nBody\n")
        assert err is not None
        e, msg = err
        self.assertEqual(e.code, 1)
        self.assertIn("unknown pi tool(s): webfetch", msg)

    def test_non_int_steps_exits(self):
        _, err = self._parse("---\nname: a\nsteps: many\n---\nBody\n")
        assert err is not None
        e, msg = err
        self.assertEqual(e.code, 1)
        self.assertIn("steps must be an int >= 0", msg)

    def test_steps_space_before_colon_accepted(self):
        cfg, err = self._parse("---\nname: a\nsteps : 3\n---\nBody\n")
        self.assertIsNone(err)
        assert cfg is not None
        self.assertEqual(cfg["steps"], 3)

    def test_bad_skill_value_exits(self):
        # A typo'd skill: value must fail pre-spend, not silently deny:
        # a mistyped 'allow' would run the whole skill arm control-
        # equivalent.
        _, err = self._parse("---\nname: a\nskill: allowed\n---\nBody\n")
        assert err is not None
        e, msg = err
        self.assertEqual(e.code, 1)
        self.assertIn("skill must be 'allow' or 'deny'", msg)

    def test_empty_body_exits(self):
        _, err = self._parse("---\nname: a\n---\n\n")
        assert err is not None
        e, msg = err
        self.assertEqual(e.code, 1)
        self.assertIn("empty body", msg)


class PiInstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.agents_dir = self.root / "agents"
        self.agents_dir.mkdir()
        self.workspace = self.root / "ws"
        self.workspace.mkdir()
        self.strategy = strategies.PiStrategy()

    def tearDown(self):
        self.tmp.cleanup()

    def _write_agent(self, base: str, extra: str = "") -> Path:
        f = self.agents_dir / f"{base}.pi.md"
        f.write_text(
            "---\n"
            f"name: {base}\n"
            f"{extra}"
            "---\n"
            "# Agent\n"
            "Load {{SKILL_NAME}} first.\n"
        )
        return f

    def test_materialize_holds_config_and_writes_nothing(self):
        self._write_agent("trigger-evaluator", "tools: read\nsteps: 3\n")
        name = self.strategy.install(
            self.workspace, self.agents_dir, "trigger-evaluator"
        )
        self.assertEqual(name, "trigger-evaluator")
        cfg = self.strategy._agent_config("trigger-evaluator")
        self.assertEqual(cfg["tools"], ["read"])
        self.assertEqual(cfg["steps"], 3)
        self.assertIn("Load {{SKILL_NAME}} first.", cfg["body"])
        # pi agents are flag-translated, never installed as files.
        self.assertEqual(list(self.workspace.rglob("*")), [])

    def test_skill_name_substitution_lands_in_held_body(self):
        self._write_agent("retrieval-evaluator", "skill: allow\n")
        self.strategy.install(
            self.workspace,
            self.agents_dir,
            "retrieval-evaluator",
            skill_name="my-skill",
        )
        cfg = self.strategy._agent_config("retrieval-evaluator")
        self.assertIn("Load my-skill first.", cfg["body"])
        self.assertNotIn("{{SKILL_NAME}}", cfg["body"])

    def test_name_mismatch_exits(self):
        f = self.agents_dir / "trigger-evaluator.pi.md"
        f.write_text("---\nname: other-agent\n---\nBody\n")
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            with self.assertRaises(SystemExit) as ctx:
                self.strategy.install(
                    self.workspace, self.agents_dir, "trigger-evaluator"
                )
        self.assertEqual(ctx.exception.code, 1)
        self.assertIn(
            "does not match expected 'trigger-evaluator'", buf.getvalue()
        )

    def test_model_pin_exits(self):
        self._write_agent("trigger-evaluator", "model: gpt-1\n")
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            with self.assertRaises(SystemExit) as ctx:
                self.strategy.install(
                    self.workspace, self.agents_dir, "trigger-evaluator"
                )
        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("pins model config", buf.getvalue())

    def test_missing_file_exits(self):
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            with self.assertRaises(SystemExit) as ctx:
                self.strategy.install(
                    self.workspace, self.agents_dir, "no-such-agent"
                )
        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("evaluator agent file missing", buf.getvalue())


class PiBuildCmdTests(unittest.TestCase):
    def setUp(self):
        self.strategy = strategies.PiStrategy()
        self.workspace = Path("/tmp/fake-ws")

    def _install(self, extra: str = "") -> None:
        self.strategy.materialize_agent(
            self.workspace,
            "trigger-evaluator",
            "---\nname: trigger-evaluator\n"
            f"{extra}"
            "---\n# Agent\nDo the report.\n",
        )

    def _cmd(self, **kwargs) -> list[str]:
        defaults = {
            "workspace": self.workspace,
            "agent": "trigger-evaluator",
            "query": "q",
            "model": None,
            "effort": None,
            "skill": None,
            "session": None,
        }
        defaults.update(kwargs)
        return self.strategy.build_cmd(**defaults)

    def test_base_flag_shape(self):
        self._install()
        cmd = self._cmd()
        self.assertEqual(cmd[0], "pi")
        idx = cmd.index("--system-prompt")
        self.assertEqual(cmd[idx + 1], "# Agent\nDo the report.\n")
        self.assertIn("--mode", cmd)
        self.assertEqual(cmd[cmd.index("--mode") + 1], "json")
        self.assertIn("--no-extensions", cmd)
        idx = cmd.index("-e")
        self.assertEqual(cmd[idx + 1], str(strategies.GUARD_EXTENSION))
        self.assertIn("--no-context-files", cmd)
        self.assertIn("--no-prompt-templates", cmd)
        self.assertIn("--no-skills", cmd)

    def test_tools_allowlist_vs_no_tools(self):
        self._install("tools: read,grep,find,ls\n")
        cmd = self._cmd()
        idx = cmd.index("--tools")
        self.assertEqual(cmd[idx + 1], "read,grep,find,ls")
        self.assertNotIn("--no-tools", cmd)
        self._install()  # no tools: line
        cmd = self._cmd()
        self.assertIn("--no-tools", cmd)
        self.assertNotIn("--tools", cmd)

    def test_skill_flag_only_for_allow(self):
        self._install("skill: allow\n")
        cmd = self._cmd(skill=PI_SKILL)
        idx = cmd.index("--skill")
        self.assertEqual(
            cmd[idx + 1],
            str(self.workspace / ".agents" / "skills" / PI_SKILL),
        )
        self._install()  # skill: deny default
        self.assertNotIn("--skill", self._cmd(skill=PI_SKILL))

    def test_skill_allow_without_run_skill_raises(self):
        self._install("skill: allow\n")
        with self.assertRaises(strategies.HarnessExecutionError):
            self._cmd(skill=None)

    def test_session_model_effort_insertion(self):
        self._install()
        cmd = self._cmd(
            model="llama-cpp/gemma-4-26B-A4B",
            effort="high",
            session="sess-42",
        )
        idx = cmd.index("--session")
        self.assertEqual(cmd[idx + 1], "sess-42")
        idx = cmd.index("--model")
        self.assertEqual(cmd[idx + 1], "llama-cpp/gemma-4-26B-A4B")
        idx = cmd.index("--thinking")
        self.assertEqual(cmd[idx + 1], "high")

    def test_double_dash_separator_before_query(self):
        self._install()
        cmd = self._cmd(query="-looks-like-a-flag")
        self.assertEqual(cmd[-2], "--")
        self.assertEqual(cmd[-1], "-looks-like-a-flag")

    def test_run_cwd_is_resolved_workspace(self):
        # run_cwd resolves, matching build_env's EVAL_WS_ROOT, so the
        # guard's root-prefix check holds where the workspace path
        # traverses a symlink.
        self.assertEqual(
            self.strategy.run_cwd(self.workspace),
            str(self.workspace.resolve()),
        )

    def test_build_env_sets_guard_vars(self):
        self._install("steps: 3\n")
        env = self.strategy.build_env(self.workspace, "trigger-evaluator")
        assert env is not None
        self.assertEqual(env["EVAL_WS_ROOT"], str(self.workspace.resolve()))
        self.assertEqual(env["EVAL_MAX_TOOL_CALLS"], "3")

    def test_uninstalled_agent_raises(self):
        with self.assertRaises(strategies.HarnessExecutionError) as ctx:
            self._cmd()
        self.assertIn("was not installed", str(ctx.exception))


class PiSkillMdTests(unittest.TestCase):
    """_pi_skill_md must accept workspace-relative stub reads, not just
    absolute ones (campaign-2026-10-06: relative reads of
    .agents/skills/<skill>/SKILL.md mis-signaled skill-not-loaded),
    without letting look-alike prefixes match."""

    def _m(self, path: str, skill: str = PI_SKILL) -> bool:
        return strategies._pi_skill_md(path, skill)

    def test_absolute_path(self):
        self.assertTrue(self._m(f"/tmp/ws/.agents/skills/{PI_SKILL}/SKILL.md"))

    def test_relative_exact(self):
        self.assertTrue(self._m(f".agents/skills/{PI_SKILL}/SKILL.md"))

    def test_dot_slash_relative(self):
        self.assertTrue(self._m(f"./.agents/skills/{PI_SKILL}/SKILL.md"))

    def test_nested_relative(self):
        self.assertTrue(self._m(f"work/.agents/skills/{PI_SKILL}/SKILL.md"))

    def test_non_stub_file_rejected(self):
        self.assertFalse(self._m(f".agents/skills/{PI_SKILL}/references/x.md"))

    def test_lookalike_prefix_rejected(self):
        self.assertFalse(self._m(f"not-.agents/skills/{PI_SKILL}/SKILL.md"))

    def test_other_skill_rejected(self):
        self.assertFalse(self._m(".agents/skills/other/SKILL.md"))

    def test_suffix_lookalike_skill_rejected(self):
        self.assertFalse(self._m(".agents/skills/echo-skill-evil/SKILL.md"))


class PiOtherSkillTests(unittest.TestCase):
    """_pi_other_skill extracts the skill name from any stub read under
    the workspace .agents/skills tree — absolute or relative — so a
    control-arm agent loading a skill by relative path still trips the
    control-loaded-skill signal."""

    def _n(self, path: str):
        return strategies._pi_other_skill(path)

    def test_absolute(self):
        self.assertEqual(
            self._n("/tmp/ws/.agents/skills/other/SKILL.md"), "other"
        )

    def test_relative(self):
        self.assertEqual(self._n(".agents/skills/other/SKILL.md"), "other")

    def test_dot_slash_relative(self):
        self.assertEqual(self._n("./.agents/skills/other/SKILL.md"), "other")

    def test_lookalike_prefix_rejected(self):
        self.assertIsNone(self._n("not-.agents/skills/other/SKILL.md"))

    def test_non_stub_file_rejected(self):
        self.assertIsNone(self._n(".agents/skills/other/references/x.md"))

    def test_buried_skill_md_rejected(self):
        self.assertIsNone(self._n(".agents/skills/other/docs/SKILL.md"))

    def test_plain_file_rejected(self):
        self.assertIsNone(self._n("/tmp/ws/README.md"))


class PiParseStreamTests(unittest.TestCase):
    def _parse(self, stdout: str, skill=PI_SKILL) -> strategies.EventStream:
        return strategies.PiStrategy.parse_stream(stdout, skill)

    def test_session_header_id(self):
        ev = self._parse(PI_JSONL)
        self.assertEqual(ev.session_id, "abc-123")

    def test_thinking_and_text_accumulation(self):
        ev = self._parse(PI_JSONL)
        self.assertEqual(ev.reasoning_parts, ["I should load the skill"])
        self.assertEqual(ev.answer_parts, ["loaded skill: echo-skill"])

    def test_report_regexes(self):
        ev = self._parse(PI_JSONL)
        self.assertEqual(ev.report_loaded, PI_SKILL)
        ev = self._parse(pi_text_event("No skill matched the query."))
        self.assertTrue(ev.report_no_match)

    def test_completed_load(self):
        ev = self._parse(PI_JSONL)
        self.assertTrue(ev.completed_load)
        self.assertFalse(ev.attempted_load)
        self.assertEqual(
            ev.skill_loads,
            [{"name": PI_SKILL, "status": "completed"}],
        )

    def test_completed_load_via_relative_skill_read(self):
        # Regression (campaign-2026-10-06): agents read the stub by a
        # workspace-relative path; that read is a load, not a
        # skill-not-loaded void.
        stdout = PI_JSONL.replace(
            f"/tmp/ws/.agents/skills/{PI_SKILL}/SKILL.md",
            f".agents/skills/{PI_SKILL}/SKILL.md",
        )
        ev = self._parse(stdout)
        self.assertTrue(ev.completed_load)
        self.assertFalse(ev.attempted_load)
        self.assertEqual(
            ev.skill_loads,
            [{"name": PI_SKILL, "status": "completed"}],
        )

    def test_attempted_load_on_error(self):
        stdout = pi_tool_events(
            "read",
            {"path": f"/tmp/ws/.agents/skills/{PI_SKILL}/SKILL.md"},
            is_error=True,
        )
        ev = self._parse(stdout)
        self.assertTrue(ev.attempted_load)
        self.assertFalse(ev.completed_load)
        self.assertEqual(
            ev.skill_loads, [{"name": PI_SKILL, "status": "error"}]
        )

    def test_attempted_load_via_dangling_start(self):
        # Timeout partial stream: the read started but never ended.
        dangling = json.dumps(
            {
                "type": "tool_execution_start",
                "toolCallId": "t9",
                "toolName": "read",
                "args": {
                    "path": f"/tmp/ws/.agents/skills/{PI_SKILL}/SKILL.md"
                },
            }
        )
        ev = self._parse(dangling)
        self.assertTrue(ev.attempted_load)
        self.assertFalse(ev.completed_load)

    def test_other_skill_read(self):
        stdout = pi_tool_events(
            "read", {"path": "/tmp/ws/.agents/skills/other-skill/SKILL.md"}
        )
        ev = self._parse(stdout)
        self.assertEqual(ev.other_skill, "other-skill")
        self.assertEqual(
            ev.skill_loads, [{"name": "other-skill", "status": "completed"}]
        )
        self.assertFalse(ev.completed_load)
        self.assertFalse(ev.attempted_load)

    def test_other_skill_read_relative(self):
        # Same defect class as the relative target-skill read: a
        # control agent loading a skill by workspace-relative path must
        # still surface as an other-skill load, not a plain tool call.
        stdout = pi_tool_events(
            "read", {"path": ".agents/skills/other-skill/SKILL.md"}
        )
        ev = self._parse(stdout)
        self.assertEqual(ev.other_skill, "other-skill")
        self.assertEqual(
            ev.skill_loads, [{"name": "other-skill", "status": "completed"}]
        )
        self.assertEqual(ev.tool_calls, [])
        self.assertFalse(ev.completed_load)
        self.assertFalse(ev.attempted_load)

    def test_non_skill_tool_calls(self):
        stdout = "\n".join(
            [
                pi_tool_events("read", {"path": "/tmp/ws/README.md"}),
                pi_tool_events("grep", {"pattern": "retry"}, tcid="t2"),
                pi_tool_events("find", {"path": "/tmp/ws/src"}, tcid="t3"),
                pi_tool_events("ls", {"path": "/tmp/ws"}, tcid="t4"),
            ]
        )
        ev = self._parse(stdout)
        self.assertEqual(
            ev.tool_calls,
            [
                {"tool": "read", "target": "/tmp/ws/README.md"},
                {"tool": "grep", "target": "retry"},
                {"tool": "find", "target": "/tmp/ws/src"},
                {"tool": "ls", "target": "/tmp/ws"},
            ],
        )
        self.assertEqual(ev.skill_loads, [])

    def test_auto_retry_end_sets_error(self):
        stdout = json.dumps(
            {"type": "auto_retry_end", "success": False, "finalError": "429"}
        )
        ev = self._parse(stdout)
        self.assertEqual(ev.error_message, "429")

    def test_message_update_error_sets_error(self):
        stdout = json.dumps(
            {
                "type": "message_update",
                "assistantMessageEvent": {"type": "error", "error": "boom"},
            }
        )
        ev = self._parse(stdout)
        self.assertEqual(ev.error_message, "boom")

    def test_garbage_lines_skipped_and_parseable_counts(self):
        stdout = "garbage\n" + PI_JSONL + "\nnot json either"
        ev = self._parse(stdout)
        self.assertEqual(ev.parseable, 9)


class PiExecuteTests(unittest.TestCase):
    def setUp(self):
        self.strategy = strategies.PiStrategy(timeout=5)
        self.workspace = Path("/tmp/fake-ws")
        self.strategy.materialize_agent(
            self.workspace,
            "trigger-evaluator",
            "---\nname: trigger-evaluator\n---\n# Agent\nReport.\n",
        )

    def _proc(
        self, returncode: int = 0, stdout: str = PI_JSONL, stderr: str = ""
    ) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=[], returncode=returncode, stdout=stdout, stderr=stderr
        )

    def test_timeout_returns_partial_stream(self):
        # Lines through tool_execution_start only: the read dangles.
        partial = "\n".join(PI_JSONL.splitlines()[:5])
        err = subprocess.TimeoutExpired(cmd=["pi"], timeout=5, output=partial)
        with mock.patch.object(strategies.subprocess, "run", side_effect=err):
            ev, timed_out = self.strategy.execute(
                self.workspace, "trigger-evaluator", "q", skill=PI_SKILL
            )
        self.assertTrue(timed_out)
        self.assertTrue(ev.attempted_load)  # dangling read = partial load
        self.assertEqual(ev.session_id, "abc-123")

    def test_nonzero_exit_raises_with_session_id(self):
        proc = self._proc(returncode=1, stderr="boom")
        with mock.patch.object(
            strategies.subprocess, "run", return_value=proc
        ):
            with self.assertRaises(strategies.HarnessExecutionError) as ctx:
                self.strategy.execute(
                    self.workspace, "trigger-evaluator", "q", skill=PI_SKILL
                )
        self.assertIn("exit 1", str(ctx.exception))
        self.assertEqual(ctx.exception.session_id, "abc-123")

    def test_zero_parseable_events_raises(self):
        proc = self._proc(stdout="not json\n")
        with mock.patch.object(
            strategies.subprocess, "run", return_value=proc
        ):
            with self.assertRaises(strategies.HarnessExecutionError) as ctx:
                self.strategy.execute(
                    self.workspace, "trigger-evaluator", "q", skill=PI_SKILL
                )
        self.assertIn("no parseable events", str(ctx.exception))

    def test_classify_completed_load_is_triggered(self):
        proc = self._proc()
        with mock.patch.object(
            strategies.subprocess, "run", return_value=proc
        ):
            verdict = self.strategy.evaluate(PI_SKILL, "q", self.workspace)
        self.assertEqual(verdict.outcome, "triggered")
        self.assertEqual(verdict.session_id, "abc-123")

    def test_classify_no_match_report_is_not_triggered(self):
        stdout = pi_text_event("no skill matched")
        proc = self._proc(stdout=stdout)
        with mock.patch.object(
            strategies.subprocess, "run", return_value=proc
        ):
            verdict = self.strategy.evaluate(PI_SKILL, "q", self.workspace)
        self.assertEqual(verdict.outcome, "not-triggered")
        self.assertEqual(verdict.detail, "agent reported no skill matched")


class PiCheckModelTests(unittest.TestCase):
    LIST_MODELS_STDOUT = (
        "PROVIDER MODEL ID\n"
        "llama-cpp gemma-4-26B-A4B\n"
        "anthropic claude-sonnet-4-5\n"
    )

    def _proc(
        self,
        returncode: int = 0,
        stdout: str = LIST_MODELS_STDOUT,
        stderr: str = "",
    ) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=[], returncode=returncode, stdout=stdout, stderr=stderr
        )

    def _check(self, model: str, proc: subprocess.CompletedProcess):
        with mock.patch.object(
            strategies.subprocess, "run", return_value=proc
        ) as run_mock:
            result = strategies.PiStrategy.check_model(model)
        return result, run_mock

    def test_exact_provider_id_accepted(self):
        result, run_mock = self._check(
            "llama-cpp/gemma-4-26B-A4B", self._proc()
        )
        self.assertIsNone(result)
        self.assertEqual(run_mock.call_args.args[0], ["pi", "--list-models"])

    def test_bare_id_rejected(self):
        result, _ = self._check("gemma-4-26B-A4B", self._proc())
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIn("exact provider/id", result)

    def test_unknown_pair_rejected(self):
        result, _ = self._check("llama-cpp/nope", self._proc())
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIn("model 'llama-cpp/nope' not found", result)
        self.assertIn("2 available", result)

    def test_pi_offline_env_passed(self):
        _, run_mock = self._check("llama-cpp/gemma-4-26B-A4B", self._proc())
        env = run_mock.call_args.kwargs["env"]
        self.assertEqual(env["PI_OFFLINE"], "1")

    def test_list_models_nonzero_exit(self):
        proc = self._proc(returncode=1, stderr="auth expired")
        result, _ = self._check("llama-cpp/gemma-4-26B-A4B", proc)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIn("exited 1", result)

    def test_headerless_list_still_parses(self):
        # The header row is skipped by name, not position, so a pi that
        # drops the header doesn't shift every row into the void.
        stdout = "llama-cpp gemma-4-26B-A4B\n" "anthropic claude-sonnet-4-5\n"
        result, _ = self._check(
            "llama-cpp/gemma-4-26B-A4B", self._proc(stdout=stdout)
        )
        self.assertIsNone(result)

    def test_multiword_model_id_accepted(self):
        # Everything after the provider token joins into the id.
        stdout = "llama-cpp my model v2\n"
        result, _ = self._check(
            "llama-cpp/my model v2", self._proc(stdout=stdout)
        )
        self.assertIsNone(result)

    def test_columnar_list_parses_model_column_only(self):
        # pi >= 0.99 prints context/max-out/thinking/images columns; the
        # trailing columns must not join into the id.
        stdout = (
            "provider        model                context  max-out  "
            "thinking  images\n"
            "llama-cpp       gemma-4-26B-A4B      63.5K    32K      "
            "yes       no\n"
            "anthropic       claude-sonnet-4-5    200K     64K      "
            "yes       no\n"
        )
        result, _ = self._check(
            "llama-cpp/gemma-4-26B-A4B", self._proc(stdout=stdout)
        )
        self.assertIsNone(result)
        result, _ = self._check(
            "llama-cpp/gemma-4-26B-A4B 63.5K 32K yes no",
            self._proc(stdout=stdout),
        )
        self.assertIsNotNone(result)

    def test_list_models_empty_output(self):
        result, _ = self._check(
            "llama-cpp/gemma-4-26B-A4B", self._proc(stdout="\n")
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIn("printed no models", result)


class PiCheckVersionTests(unittest.TestCase):
    def _check(self, stdout: str):
        proc = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=stdout, stderr=""
        )
        with mock.patch.object(
            strategies.subprocess, "run", return_value=proc
        ):
            return strategies.PiStrategy.check_version()

    def test_below_floor_warns(self):
        result = self._check("0.99.0\n")
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIn("below the tested floor 0.99.1", result)

    def test_at_floor_is_silent(self):
        self.assertIsNone(self._check("0.99.1\n"))

    def test_unparseable_is_silent(self):
        self.assertIsNone(self._check("dev-main\n"))


class RegistryTests(unittest.TestCase):
    def test_registry_keys(self):
        self.assertEqual(
            set(strategies.STRATEGIES), {"opencode", "pi", "claude"}
        )

    def test_resolve_pi(self):
        self.assertIs(strategies.resolve_strategy("pi"), strategies.PiStrategy)

    def test_resolve_claude(self):
        self.assertIs(
            strategies.resolve_strategy("claude"), strategies.ClaudeStrategy
        )

    def test_unsupported_message_names_both(self):
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            with self.assertRaises(SystemExit) as ctx:
                strategies.resolve_strategy("nope")
        self.assertEqual(ctx.exception.code, 1)
        err = buf.getvalue()
        self.assertIn("opencode", err)
        self.assertIn("pi", err)


class SkillDestRootTests(unittest.TestCase):
    def test_opencode_and_pi_share_agents_skills(self):
        self.assertEqual(
            strategies.skill_dest_root("opencode"), ".agents/skills"
        )
        self.assertEqual(strategies.skill_dest_root("pi"), ".agents/skills")

    def test_claude_uses_dot_claude_skills(self):
        self.assertEqual(
            strategies.skill_dest_root("claude"), ".claude/skills"
        )

    def test_unknown_harness_falls_back_to_agents_skills(self):
        self.assertEqual(strategies.skill_dest_root("nope"), ".agents/skills")


CLAUDE_SKILL = "echo-skill"


def claude_assistant_event(content: list[dict]) -> dict:
    return {
        "type": "assistant",
        "message": {"role": "assistant", "content": content},
    }


def claude_user_tool_result(
    tcid: str,
    *,
    command_name: str,
    success: bool = True,
    is_error: bool = False,
) -> dict:
    return {
        "type": "user",
        "message": {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tcid,
                    "is_error": is_error,
                }
            ],
        },
        "tool_use_result": {
            "commandName": command_name,
            "success": success,
        },
    }


CLAUDE_NDJSON = "\n".join(
    json.dumps(e)
    for e in [
        {
            "type": "system",
            "subtype": "init",
            "session_id": "claude-sess-1",
        },
        claude_assistant_event(
            [
                {"type": "thinking", "thinking": "I should load the skill"},
                {
                    "type": "tool_use",
                    "id": "t1",
                    "name": "Skill",
                    "input": {"skill": CLAUDE_SKILL},
                },
            ]
        ),
        claude_user_tool_result(
            "t1", command_name=CLAUDE_SKILL, success=True, is_error=False
        ),
        claude_assistant_event(
            [{"type": "text", "text": "loaded skill: echo-skill"}]
        ),
        {"type": "result", "is_error": False, "result": "ok"},
    ]
)


class ParseClaudeAgentTests(unittest.TestCase):
    def _parse(self, text: str):
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            try:
                return (
                    strategies.parse_claude_agent(text, "agent.claude.md"),
                    None,
                )
            except SystemExit as e:
                return None, (e, buf.getvalue())

    def test_full_frontmatter(self):
        cfg, err = self._parse(
            "---\n"
            "name: retrieval-evaluator\n"
            "description: Does the thing.\n"
            "tools: Read,Grep,Skill\n"
            "steps: 30\n"
            "skill: allow\n"
            "---\n"
            "# Agent\n"
            "Body text.\n"
        )
        self.assertIsNone(err)
        assert cfg is not None
        self.assertEqual(cfg["tools"], ["Read", "Grep", "Skill"])
        self.assertEqual(cfg["steps"], 30)
        self.assertEqual(cfg["skill"], "allow")
        self.assertEqual(cfg["description"], "Does the thing.")
        self.assertEqual(cfg["body"], "# Agent\nBody text.\n")

    def test_defaults(self):
        cfg, err = self._parse("---\nname: a\ndescription: d\n---\nBody\n")
        self.assertIsNone(err)
        assert cfg is not None
        self.assertEqual(cfg["tools"], [])
        self.assertEqual(cfg["steps"], 0)
        self.assertEqual(cfg["skill"], "deny")
        self.assertEqual(cfg["body"], "Body\n")

    def test_unknown_tool_exits(self):
        _, err = self._parse(
            "---\nname: a\ndescription: d\ntools: Read,ls\n---\nBody\n"
        )
        assert err is not None
        e, msg = err
        self.assertEqual(e.code, 1)
        self.assertIn("unknown claude tool(s): ls", msg)

    def test_non_int_steps_exits(self):
        _, err = self._parse(
            "---\nname: a\ndescription: d\nsteps: many\n---\nBody\n"
        )
        assert err is not None
        e, msg = err
        self.assertEqual(e.code, 1)
        self.assertIn("steps must be an int >= 0", msg)

    def test_bad_skill_value_exits(self):
        _, err = self._parse(
            "---\nname: a\ndescription: d\nskill: allowed\n---\nBody\n"
        )
        assert err is not None
        e, msg = err
        self.assertEqual(e.code, 1)
        self.assertIn("skill must be 'allow' or 'deny'", msg)

    def test_empty_body_exits(self):
        _, err = self._parse("---\nname: a\ndescription: d\n---\n\n")
        assert err is not None
        e, msg = err
        self.assertEqual(e.code, 1)
        self.assertIn("empty body", msg)

    def test_missing_description_exits(self):
        _, err = self._parse("---\nname: a\n---\nBody\n")
        assert err is not None
        e, msg = err
        self.assertEqual(e.code, 1)
        self.assertIn("missing 'description:'", msg)


class ClaudeBuildCmdTests(unittest.TestCase):
    def setUp(self):
        self.strategy = strategies.ClaudeStrategy()
        self.workspace = Path(tempfile.mkdtemp())

    def _install(self, extra: str = "") -> None:
        self.strategy.materialize_agent(
            self.workspace,
            "trigger-evaluator",
            "---\nname: trigger-evaluator\n"
            "description: Does the thing.\n"
            f"{extra}"
            "---\n# Agent\nDo the report.\n",
        )

    def _cmd(self, **kwargs) -> list[str]:
        defaults = {
            "workspace": self.workspace,
            "agent": "trigger-evaluator",
            "query": "q",
            "model": None,
            "effort": None,
            "skill": None,
            "session": None,
        }
        defaults.update(kwargs)
        return self.strategy.build_cmd(**defaults)

    def test_base_flag_shape(self):
        self._install()
        cmd = self._cmd()
        self.assertEqual(cmd[0], "claude")
        self.assertIn("--restricted", cmd)
        idx = cmd.index("--setting-sources")
        self.assertEqual(cmd[idx + 1], "")
        idx = cmd.index("--agent")
        self.assertEqual(cmd[idx + 1], "trigger-evaluator")
        idx = cmd.index("--agents")
        agents = json.loads(cmd[idx + 1])
        self.assertEqual(
            agents["trigger-evaluator"],
            {
                "description": "Does the thing.",
                "prompt": "# Agent\nDo the report.\n",
            },
        )

    def test_tools_allowlist_vs_empty(self):
        self._install("tools: Read,Grep\n")
        cmd = self._cmd()
        idx = cmd.index("--tools")
        self.assertEqual(cmd[idx + 1], "Read,Grep")
        self._install()  # no tools: line
        cmd = self._cmd()
        idx = cmd.index("--tools")
        self.assertEqual(cmd[idx + 1], "")

    def test_skill_deny_adds_disallowed(self):
        self._install()  # skill: deny default
        cmd = self._cmd()
        idx = cmd.index("--disallowedTools")
        self.assertEqual(cmd[idx + 1], "Skill")

    def test_skill_allow_omits_disallowed(self):
        self._install("skill: allow\n")
        cmd = self._cmd()
        self.assertNotIn("--disallowedTools", cmd)

    def test_steps_adds_settings_guard(self):
        self._install("steps: 3\n")
        cmd = self._cmd()
        self.assertIn("--settings", cmd)
        idx = cmd.index("--settings")
        settings_path = Path(cmd[idx + 1])
        self.assertTrue(settings_path.exists())
        data = json.loads(settings_path.read_text())
        self.assertIn("PreToolUse", data["hooks"])

    def test_zero_steps_omits_settings_guard(self):
        self._install()  # steps default 0
        cmd = self._cmd()
        self.assertNotIn("--settings", cmd)

    def test_session_model_effort_insertion(self):
        self._install()
        cmd = self._cmd(model="sonnet", effort="high", session="sess-42")
        idx = cmd.index("--resume")
        self.assertEqual(cmd[idx + 1], "sess-42")
        idx = cmd.index("--model")
        self.assertEqual(cmd[idx + 1], "sonnet")
        idx = cmd.index("--effort")
        self.assertEqual(cmd[idx + 1], "high")

    def test_double_dash_separator_before_query(self):
        self._install()
        cmd = self._cmd(query="-looks-like-a-flag")
        self.assertEqual(cmd[-2], "--")
        self.assertEqual(cmd[-1], "-looks-like-a-flag")

    def test_run_cwd_is_resolved_workspace(self):
        self.assertEqual(
            self.strategy.run_cwd(self.workspace),
            str(self.workspace.resolve()),
        )

    def test_build_env_sets_guard_vars(self):
        self._install("steps: 3\n")
        env = self.strategy.build_env(self.workspace, "trigger-evaluator")
        assert env is not None
        self.assertEqual(env["EVAL_MAX_TOOL_CALLS"], "3")
        self.assertIn("CLAUDE_EVAL_COUNTER_FILE", env)

    def test_uninstalled_agent_raises(self):
        with self.assertRaises(strategies.HarnessExecutionError) as ctx:
            self._cmd()
        self.assertIn("was not installed", str(ctx.exception))


class ClaudeParseStreamTests(unittest.TestCase):
    def _parse(
        self, stdout: str, skill=CLAUDE_SKILL
    ) -> strategies.EventStream:
        return strategies.ClaudeStrategy.parse_stream(stdout, skill)

    def test_session_header_id(self):
        ev = self._parse(CLAUDE_NDJSON)
        self.assertEqual(ev.session_id, "claude-sess-1")

    def test_thinking_and_text_accumulation(self):
        ev = self._parse(CLAUDE_NDJSON)
        self.assertEqual(ev.reasoning_parts, ["I should load the skill"])
        self.assertEqual(ev.answer_parts, ["loaded skill: echo-skill"])

    def test_report_regex(self):
        ev = self._parse(CLAUDE_NDJSON)
        self.assertEqual(ev.report_loaded, CLAUDE_SKILL)

    def test_completed_load(self):
        ev = self._parse(CLAUDE_NDJSON)
        self.assertTrue(ev.completed_load)
        self.assertFalse(ev.attempted_load)
        self.assertEqual(
            ev.skill_loads,
            [{"name": CLAUDE_SKILL, "status": "completed"}],
        )

    def test_attempted_load_on_error(self):
        stdout = "\n".join(
            json.dumps(e)
            for e in [
                claude_assistant_event(
                    [
                        {
                            "type": "tool_use",
                            "id": "t1",
                            "name": "Skill",
                            "input": {"skill": CLAUDE_SKILL},
                        }
                    ]
                ),
                claude_user_tool_result(
                    "t1",
                    command_name=CLAUDE_SKILL,
                    success=False,
                    is_error=True,
                ),
            ]
        )
        ev = self._parse(stdout)
        self.assertTrue(ev.attempted_load)
        self.assertFalse(ev.completed_load)
        self.assertEqual(
            ev.skill_loads, [{"name": CLAUDE_SKILL, "status": "error"}]
        )

    def test_attempted_load_via_dangling_tool_use(self):
        # Timeout partial stream: the Skill call started but no paired
        # tool_result ever arrived.
        dangling = json.dumps(
            claude_assistant_event(
                [
                    {
                        "type": "tool_use",
                        "id": "t9",
                        "name": "Skill",
                        "input": {"skill": CLAUDE_SKILL},
                    }
                ]
            )
        )
        ev = self._parse(dangling)
        self.assertTrue(ev.attempted_load)
        self.assertFalse(ev.completed_load)

    def test_other_skill_load(self):
        stdout = json.dumps(
            claude_assistant_event(
                [
                    {
                        "type": "tool_use",
                        "id": "t1",
                        "name": "Skill",
                        "input": {"skill": "other-skill"},
                    }
                ]
            )
        )
        ev = self._parse(stdout)
        self.assertEqual(ev.other_skill, "other-skill")

    def test_non_skill_tool_calls(self):
        stdout = json.dumps(
            claude_assistant_event(
                [
                    {
                        "type": "tool_use",
                        "id": "t1",
                        "name": "Read",
                        "input": {"file_path": "/tmp/ws/README.md"},
                    }
                ]
            )
        )
        ev = self._parse(stdout)
        self.assertEqual(
            ev.tool_calls,
            [{"tool": "Read", "target": "/tmp/ws/README.md"}],
        )
        self.assertEqual(ev.skill_loads, [])

    def test_result_error_sets_error_message(self):
        stdout = json.dumps(
            {"type": "result", "is_error": True, "result": "boom"}
        )
        ev = self._parse(stdout)
        self.assertEqual(ev.error_message, "boom")

    def test_garbage_lines_skipped_and_parseable_counts(self):
        stdout = "garbage\n" + CLAUDE_NDJSON + "\nnot json either"
        ev = self._parse(stdout)
        self.assertEqual(ev.parseable, 5)


class ClaudeCheckModelTests(unittest.TestCase):
    def test_known_alias_accepted(self):
        self.assertIsNone(strategies.ClaudeStrategy.check_model("sonnet"))

    def test_known_full_id_accepted(self):
        self.assertIsNone(
            strategies.ClaudeStrategy.check_model("claude-sonnet-5")
        )

    def test_claude_prefixed_id_accepted(self):
        self.assertIsNone(
            strategies.ClaudeStrategy.check_model("claude-opus-9-9")
        )

    def test_bedrock_prefixed_id_accepted(self):
        self.assertIsNone(
            strategies.ClaudeStrategy.check_model(
                "us.anthropic.claude-sonnet-5"
            )
        )

    def test_unknown_model_rejected(self):
        result = strategies.ClaudeStrategy.check_model("gpt-4")
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIn("not recognized", result)


class ClaudeCheckVersionTests(unittest.TestCase):
    def _check(self, stdout: str):
        proc = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=stdout, stderr=""
        )
        with mock.patch.object(
            strategies.subprocess, "run", return_value=proc
        ):
            return strategies.ClaudeStrategy.check_version()

    def test_below_floor_warns(self):
        result = self._check("2.1.282 (Claude Code)\n")
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIn("below the tested floor 2.1.283", result)

    def test_at_floor_is_silent(self):
        self.assertIsNone(self._check("2.1.283 (Claude Code)\n"))

    def test_unparseable_is_silent(self):
        self.assertIsNone(self._check("dev-main\n"))


class GrammarGateTests(unittest.TestCase):
    def test_strategies_py_parses_with_py310_grammar(self):
        src = Path(strategies.__file__).read_text()
        ast.parse(src, filename="strategies.py", feature_version=(3, 10))


if __name__ == "__main__":
    unittest.main()
