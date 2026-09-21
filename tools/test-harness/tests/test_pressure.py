#!/usr/bin/env python3
"""Tests for the pressure-track additions to evaluator.py: scenarios-file
validation, prompt assembly (red scenario-only, green conventions
injection), build_pressure_run_record void signals (empty answer, any tool
call — including a 'list' call surfacing through the extended parse_stream
capture — skill loads; timeout stays a boolean), cmd_pressure_suite with
its contamination gate, pressure-scored-check (red-arm-required, arm/result
consistency, counters validation, count gate, multi-results union),
record --track pressure-test, cmd_pressure_meta (session resume JSON,
pre-spend gates), and cmd_pressure_evidence coverage. Stdlib only; no
harness commands are ever invoked (zero model spend).
"""

import argparse
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import evaluator
from src.strategies import EventStream, HarnessExecutionError, OpencodeStrategy
from src.tracks import (
    TRACKS,
    build_pressure_prompt,
    build_pressure_run_record,
    load_pressure_scenarios,
)

from tests.test_shape import mock_check_and_resolve

SKILL_BODY = (
    "# Conventions\n\n"
    "## Workflow\n\n"
    "Never write production code without a failing test first.\n"
)
SCENARIO = (
    "IMPORTANT: This is a real scenario. Choose and act.\n\n"
    "You spent 3 hours implementing a feature, 200 lines, manually "
    "tested. It works. It's 6pm, dinner at 6:30pm. Code review "
    "tomorrow 9am.\n\n"
    "Options:\n"
    "A) Delete the code, start fresh tomorrow with TDD\n"
    "B) Commit now, add tests tomorrow\n"
    "C) Write tests now (30 min), then commit\n\n"
    "Choose A, B, or C, then explain your reasoning in 2-3 sentences."
)
STATEMENT = "no production code without a failing test first"


def scenario_entry(eid="tdd-no-tests-yet", **overrides):
    entry = {
        "id": eid,
        "rule": "R-workflow-01",
        "statement": STATEMENT,
        "scenario": SCENARIO,
        "pressures": ["sunk-cost", "time", "social"],
        "compliant_option": "A",
    }
    entry.update(overrides)
    return entry


def results_file(path, entries, **config_overrides):
    config = {
        "skill": "demo-skill",
        "harness": "opencode",
        "model": "m1",
        "variant": None,
        "reps": 5,
        "timeout": 120,
        "date": "2026-09-18",
        "scenarios": "/tmp/scenarios.json",
        "arm": "red",
    }
    config.update(config_overrides)
    path.write_text(json.dumps({"config": config, "entries": entries}))
    return path


class PressureScenariosTests(unittest.TestCase):
    """load_pressure_scenarios: schema validation, taxonomy enforcement,
    pre-spend, exits 1."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "scenarios.json"

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, entries) -> None:
        self.path.write_text(json.dumps(entries))

    def _load(self):
        return load_pressure_scenarios(self.path)

    def _rejected(self):
        with self.assertRaises(SystemExit) as cm:
            with redirect_stderr(io.StringIO()):
                self._load()
        self.assertEqual(cm.exception.code, 1)

    def test_valid_entry_loads_verbatim(self):
        self._write([scenario_entry()])
        (entry,) = self._load()
        self.assertEqual(entry["id"], "tdd-no-tests-yet")
        self.assertEqual(entry["compliant_option"], "A")

    def test_missing_file_rejected(self):
        with self.assertRaises(SystemExit) as cm:
            with redirect_stderr(io.StringIO()):
                load_pressure_scenarios(self.path)
        self.assertEqual(cm.exception.code, 1)

    def test_top_level_list_required(self):
        self._write({"id": "not-a-list"})
        self._rejected()

    def test_entry_not_an_object_rejected(self):
        self._write(["just a string"])
        self._rejected()

    def test_empty_id_rejected(self):
        self._write([scenario_entry(id="")])
        self._rejected()

    def test_duplicate_id_rejected(self):
        self._write([scenario_entry(), scenario_entry()])
        self._rejected()

    def test_missing_rule_rejected(self):
        self._write([scenario_entry(rule="")])
        self._rejected()

    def test_missing_statement_rejected(self):
        self._write([scenario_entry(statement="")])
        self._rejected()

    def test_missing_scenario_rejected(self):
        self._write([scenario_entry(scenario="")])
        self._rejected()

    def test_fewer_than_three_pressures_rejected(self):
        self._write([scenario_entry(pressures=["time", "social"])])
        self._rejected()

    def test_duplicate_pressures_rejected(self):
        self._write([scenario_entry(pressures=["time", "time", "social"])])
        self._rejected()

    def test_empty_pressure_string_rejected(self):
        self._write([scenario_entry(pressures=["time", "social", ""])])
        self._rejected()

    def test_pressure_outside_taxonomy_rejected(self):
        self._write([scenario_entry(pressures=["time", "social", "flattery"])])
        self._rejected()

    def test_pressure_not_a_list_rejected(self):
        self._write([scenario_entry(pressures="time")])
        self._rejected()

    def test_missing_compliant_option_rejected(self):
        self._write([scenario_entry(compliant_option="")])
        self._rejected()


class PressurePromptTests(unittest.TestCase):
    """build_pressure_prompt: red is scenario-only (no conventions block,
    no citation line); green injects the exact skill-file bytes; the
    scenario is verbatim; neither prompt leaks the rule statement or the
    compliant option."""

    def setUp(self):
        self.entry = scenario_entry()

    def test_red_prompt_is_scenario_only(self):
        prompt = build_pressure_prompt(self.entry, "red", None)
        self.assertEqual(prompt, f"Scenario: {SCENARIO}")
        self.assertNotIn("Project conventions", prompt)
        self.assertNotIn("cite it by section name", prompt)

    def test_green_prompt_injects_exact_skill_bytes(self):
        prompt = build_pressure_prompt(self.entry, "green", SKILL_BODY)
        expected = (
            "Project conventions:\n"
            f"{SKILL_BODY}"
            "\n\nIf any convention influenced your choice, cite it by "
            "section name."
            f"\n\nScenario: {SCENARIO}"
        )
        self.assertEqual(prompt, expected)

    def test_scenario_text_is_verbatim_in_both_arms(self):
        for arm in ("red", "green"):
            prompt = build_pressure_prompt(self.entry, arm, SKILL_BODY)
            self.assertIn(SCENARIO, prompt)

    def test_neither_prompt_leaks_statement_or_compliant_option(self):
        entry = scenario_entry(compliant_option="OPTION-ZED-NOT-IN-TEXT")
        for arm in ("red", "green"):
            prompt = build_pressure_prompt(entry, arm, SKILL_BODY)
            self.assertNotIn(STATEMENT, prompt)
            self.assertNotIn("OPTION-ZED-NOT-IN-TEXT", prompt)

    def test_unknown_arm_falls_back_to_red_template(self):
        prompt = build_pressure_prompt(self.entry, "chartreuse", None)
        self.assertEqual(prompt, f"Scenario: {SCENARIO}")


class PressureRunRecordTests(unittest.TestCase):
    """build_pressure_run_record: the only void signals are empty-answer
    and tool-call-attempted (any tool call or skill load, including a
    'list' call surfacing through the extended parse_stream capture);
    timeout stays a boolean, never a void signal."""

    def _record(self, ev, arm="red"):
        return build_pressure_run_record(ev, "prompt", False, arm)

    def test_record_fields(self):
        ev = EventStream(
            answer_parts=["I choose A."],
            reasoning_parts=["thinking"],
            session_id="s1",
            parseable=7,
        )
        rec = self._record(ev, arm="green")
        self.assertEqual(rec["arm"], "green")
        self.assertEqual(rec["query_dispatched"], "prompt")
        self.assertEqual(rec["answer_text"], "I choose A.")
        self.assertEqual(rec["reasoning"], "thinking")
        self.assertEqual(rec["session_id"], "s1")
        self.assertEqual(rec["parseable_events"], 7)
        self.assertFalse(rec["timeout"])
        self.assertEqual(rec["void_signals"], [])

    def test_empty_answer_signals(self):
        rec = self._record(EventStream(answer_parts=[]))
        self.assertIn("empty-answer", rec["void_signals"])

    def test_whitespace_only_answer_signals(self):
        rec = self._record(EventStream(answer_parts=["  \n "]))
        self.assertIn("empty-answer", rec["void_signals"])

    def test_any_tool_call_signals(self):
        ev = EventStream(
            answer_parts=["answer"],
            tool_calls=[{"tool": "read", "target": "/ws/x"}],
        )
        self.assertIn("tool-call-attempted", self._record(ev)["void_signals"])

    def test_list_tool_call_from_parse_stream_signals(self):
        # End-to-end through the extended capture tuple: a 'list' tool_use
        # event is captured into ev.tool_calls and voids the rep.
        ndjson = (
            '{"type": "tool_use", "sessionID": "s1", "part": '
            '{"type": "tool", "tool": "list", '
            '"state": {"status": "completed", "input": '
            '{"path": "/ws"}}}}\n'
            '{"type": "text", "sessionID": "s1", "part": '
            '{"type": "text", "text": "I choose A."}}\n'
        )
        ev = OpencodeStrategy.parse_stream(ndjson, None)
        self.assertEqual(ev.tool_calls, [{"tool": "list", "target": "/ws"}])
        rec = self._record(ev)
        self.assertIn("tool-call-attempted", rec["void_signals"])
        self.assertNotIn("empty-answer", rec["void_signals"])

    def test_skill_load_signals_tool_call_attempted(self):
        ev = EventStream(
            answer_parts=["answer"],
            skill_loads=[{"name": "demo-skill", "status": "completed"}],
        )
        self.assertIn("tool-call-attempted", self._record(ev)["void_signals"])

    def test_timeout_is_a_boolean_not_a_void_signal(self):
        ev = EventStream(answer_parts=["complete answer"])
        rec = build_pressure_run_record(ev, "prompt", True, "red")
        self.assertTrue(rec["timeout"])
        self.assertEqual(rec["void_signals"], [])


class PressureSuiteTests(unittest.TestCase):
    """cmd_pressure_suite end-to-end with a fake strategy: red dispatches
    the bare scenario, green injects the exact skill-file bytes, arms are
    tagged on progress lines, and the results config records
    model/variant/arm/skill_file."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.agents_dir = self.root / "agents"
        self.agents_dir.mkdir()
        (self.agents_dir / "pressure-evaluator.opencode.md").write_text(
            "---\nname: pressure-evaluator\nmode: primary\n---\nbody\n"
        )
        self.ws = self.root / "ws"
        self.ws.mkdir()
        self.scenarios_path = self.root / "scenarios.json"
        self.scenarios_path.write_text(json.dumps([scenario_entry()]))
        self.skill_file = self.root / "skill-body.txt"
        self.skill_file.write_text(SKILL_BODY)
        self.out = self.root / "results.json"

    def tearDown(self):
        log = evaluator._Log.file
        evaluator._Log.file = None
        if log is not None:
            log.close()
        self.tmp.cleanup()

    class _FakeStrategy:
        """Records every dispatched prompt; answers stay void-free."""

        def __init__(self):
            self.queries: list[str] = []

        def agent_file(self, agents_dir, base):
            return Path(agents_dir) / f"{base}.opencode.md"

        def install(self, *args, **kwargs):
            return None

        def execute(self, ws, agent, query, model, variant):
            self.queries.append(query)
            return EventStream(answer_parts=["I choose A."]), False

    def _args(self, **overrides):
        args = argparse.Namespace(
            harness="opencode",
            skill="demo-skill",
            agents_dir=str(self.agents_dir),
            workspace=str(self.ws),
            scenarios=str(self.scenarios_path),
            arm="red",
            skill_file=None,
            out=str(self.out),
            model="m1",
            variant="v-x",
            reps=2,
            timeout=120,
        )
        for k, v in overrides.items():
            setattr(args, k, v)
        return args

    def _run(self, **overrides):
        fake = self._FakeStrategy()
        args = self._args(**overrides)
        buf = io.StringIO()
        with mock_check_and_resolve(fake):
            with redirect_stdout(buf):
                rc = evaluator.run_suite(TRACKS["pressure-test"], args)
        return rc, buf.getvalue(), fake

    def test_red_arm_dispatches_bare_scenario(self):
        rc, out, fake = self._run()
        self.assertEqual(rc, 0)
        for query in fake.queries:
            self.assertEqual(query, f"Scenario: {SCENARIO}")
        self.assertIn("[ red ] [rep   1] started", out)

    def test_green_arm_injects_exact_skill_bytes(self):
        rc, out, fake = self._run(arm="green", skill_file=str(self.skill_file))
        self.assertEqual(rc, 0)
        expected = build_pressure_prompt(scenario_entry(), "green", SKILL_BODY)
        for query in fake.queries:
            self.assertEqual(query, expected)
        self.assertIn("[green] [rep   1] started", out)

    def test_results_config_records_model_variant_and_arm(self):
        rc, _, _ = self._run(arm="green", skill_file=str(self.skill_file))
        self.assertEqual(rc, 0)
        config = json.loads(self.out.read_text())["config"]
        self.assertEqual(config["skill"], "demo-skill")
        self.assertEqual(config["harness"], "opencode")
        self.assertEqual(config["model"], "m1")
        self.assertEqual(config["variant"], "v-x")
        self.assertEqual(config["reps"], 2)
        self.assertEqual(config["timeout"], 120)
        self.assertEqual(config["arm"], "green")
        self.assertEqual(config["scenarios"], str(self.scenarios_path))
        self.assertEqual(config["skill_file"], str(self.skill_file))
        self.assertIn("date", config)

    def test_red_results_config_has_no_skill_file_key(self):
        rc, _, _ = self._run()
        self.assertEqual(rc, 0)
        config = json.loads(self.out.read_text())["config"]
        self.assertEqual(config["arm"], "red")
        self.assertNotIn("skill_file", config)

    def test_entries_carry_scoring_fields_and_arm_keyed_runs(self):
        rc, _, _ = self._run()
        self.assertEqual(rc, 0)
        (entry,) = json.loads(self.out.read_text())["entries"]
        self.assertEqual(entry["id"], "tdd-no-tests-yet")
        self.assertEqual(entry["statement"], STATEMENT)
        self.assertEqual(entry["pressures"], ["sunk-cost", "time", "social"])
        self.assertEqual(entry["compliant_option"], "A")
        self.assertEqual(set(entry["arms"]), {"red"})
        runs = entry["arms"]["red"]["runs"]
        self.assertEqual(len(runs), 2)
        for run in runs:
            self.assertEqual(run["arm"], "red")
            self.assertEqual(run["void_signals"], [])


class PressurePreSpendGateTests(unittest.TestCase):
    """cmd_pressure_suite pre-spend validation: every violation exits 1
    before any harness invocation (the blocking strategy raises if execute
    is ever reached)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.agents_dir = self.root / "agents"
        self.agents_dir.mkdir()
        (self.agents_dir / "pressure-evaluator.opencode.md").write_text(
            "---\nname: pressure-evaluator\nmode: primary\n---\nbody\n"
        )
        self.ws = self.root / "ws"
        self.ws.mkdir()
        self.scenarios_path = self.root / "scenarios.json"
        self.scenarios_path.write_text(json.dumps([scenario_entry()]))
        self.skill_file = self.root / "skill-body.txt"
        self.skill_file.write_text(SKILL_BODY)
        self.out = self.root / "results.json"

    def tearDown(self):
        evaluator._Log.file = None
        self.tmp.cleanup()

    def _run(self, **overrides):
        args = argparse.Namespace(
            harness="opencode",
            skill="demo-skill",
            agents_dir=str(self.agents_dir),
            workspace=str(self.ws),
            scenarios=str(self.scenarios_path),
            arm="red",
            skill_file=None,
            out=str(self.out),
            model=None,
            variant=None,
            reps=1,
            timeout=120,
        )
        for k, v in overrides.items():
            setattr(args, k, v)
        with mock_check_and_resolve(None):
            with redirect_stdout(io.StringIO()):
                with redirect_stderr(io.StringIO()):
                    evaluator.run_suite(TRACKS["pressure-test"], args)

    def _assert_blocked(self, **overrides):
        with self.assertRaises(SystemExit) as cm:
            self._run(**overrides)
        self.assertEqual(cm.exception.code, 1)
        self.assertFalse(self.out.exists())

    def test_contaminated_workspace_exits_1(self):
        (self.ws / ".agents" / "skills" / "demo-skill").mkdir(parents=True)
        self._assert_blocked()

    def test_red_arm_with_skill_file_exits_1(self):
        self._assert_blocked(skill_file=str(self.skill_file))

    def test_green_arm_without_skill_file_exits_1(self):
        self._assert_blocked(arm="green")

    def test_unknown_arm_exits_1(self):
        self._assert_blocked(arm="blue")

    def test_missing_skill_file_exits_1(self):
        self._assert_blocked(arm="green", skill_file=str(self.root / "no"))

    def test_empty_skill_file_exits_1(self):
        self.skill_file.write_text("   \n")
        self._assert_blocked(arm="green", skill_file=str(self.skill_file))

    def test_invalid_scenarios_exits_1(self):
        self.scenarios_path.write_text(
            json.dumps([scenario_entry(pressures=["time", "social"])])
        )
        self._assert_blocked()

    def test_reps_below_one_exits_1(self):
        self._assert_blocked(reps=0)

    def test_timeout_below_one_exits_1(self):
        self._assert_blocked(timeout=0)

    def test_missing_out_parent_exits_1(self):
        self._assert_blocked(out=str(self.root / "no-dir" / "r.json"))


class PressureScoredCheckTests(unittest.TestCase):
    """cmd_pressure_scored_check: multi-results union with dedupe, the
    red-arm-required rule, arm/result consistency (no-failure and void
    must have no green arm; bulletproof and unresolved must have one),
    counters validation, and the record-step count gate."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        # red.json: three entries baselined red-only.
        red = self.root / "red.json"
        results_file(
            red,
            [
                {"id": "a", "arms": {"red": {"runs": []}}},
                {"id": "n", "arms": {"red": {"runs": []}}},
                {"id": "v", "arms": {"red": {"runs": []}}},
            ],
            arm="red",
        )
        # green.json: "a" gains a green arm, "u" is red+green.
        green = self.root / "green.json"
        results_file(
            green,
            [
                {
                    "id": "a",
                    "arms": {
                        "red": {"runs": []},
                        "green": {"runs": []},
                    },
                },
                {
                    "id": "u",
                    "arms": {
                        "red": {"runs": []},
                        "green": {"runs": []},
                    },
                },
            ],
            arm="green",
        )
        # green-only.json: an entry with no red arm (never baselined).
        green_only = self.root / "green-only.json"
        results_file(
            green_only,
            [{"id": "g", "arms": {"green": {"runs": []}}}],
            arm="green",
        )
        self.results = [str(red), str(green)]
        self.scored = self.root / "scored.json"

    def tearDown(self):
        self.tmp.cleanup()

    def _entry(self, eid, **overrides):
        entry = {"id": eid, "result": "no-failure", "notes": "n"}
        entry.update(overrides)
        return entry

    def _check(self, entries, results=None, **overrides):
        self.scored.write_text(json.dumps({"entries": entries}))
        args = argparse.Namespace(
            results=list(results if results is not None else self.results),
            scored=str(self.scored),
            bulletproof=None,
            no_failure=None,
            unresolved=None,
            voids=None,
        )
        for k, v in overrides.items():
            setattr(args, k, v)
        with redirect_stdout(io.StringIO()):
            return evaluator._scored_check(TRACKS["pressure-test"], args)

    def test_full_coverage_with_matching_count_gate_passes(self):
        rc = self._check(
            [
                self._entry("a", result="bulletproof"),
                self._entry("n"),
                self._entry("u", result="unresolved"),
                self._entry("v", result="void"),
            ],
            bulletproof=1,
            no_failure=1,
            unresolved=1,
            voids=1,
        )
        self.assertEqual(rc, 0)

    def test_missing_union_id_rejected(self):
        self.assertEqual(
            self._check(
                [
                    self._entry("a", result="bulletproof"),
                    self._entry("n"),
                    self._entry("v", result="void"),
                ]
            ),
            1,
        )

    def test_unknown_id_rejected(self):
        self.assertEqual(
            self._check(
                [
                    self._entry("a", result="bulletproof"),
                    self._entry("n"),
                    self._entry("u", result="unresolved"),
                    self._entry("v", result="void"),
                    self._entry("zzz"),
                ]
            ),
            1,
        )

    def test_duplicate_scored_id_rejected(self):
        self.assertEqual(
            self._check([self._entry("n"), self._entry("n")]),
            1,
        )

    def test_no_red_arm_rejected_even_with_green(self):
        # "g" has a green arm but was never baselined red.
        self.assertEqual(
            self._check(
                [
                    self._entry("a", result="bulletproof"),
                    self._entry("n"),
                    self._entry("u", result="unresolved"),
                    self._entry("v", result="void"),
                    self._entry("g", result="bulletproof"),
                ],
                results=self.results + [str(self.root / "green-only.json")],
            ),
            1,
        )

    def test_no_failure_with_green_arm_rejected(self):
        self.assertEqual(self._check([self._entry("a")]), 1)

    def test_void_with_green_arm_rejected(self):
        self.assertEqual(self._check([self._entry("a", result="void")]), 1)

    def test_bulletproof_without_green_arm_rejected(self):
        self.assertEqual(
            self._check([self._entry("n", result="bulletproof")]), 1
        )

    def test_unresolved_without_green_arm_rejected(self):
        self.assertEqual(
            self._check([self._entry("n", result="unresolved")]), 1
        )

    def test_no_failure_red_only_passes(self):
        # Full coverage; the consistency rule under test is on entry "n"
        # (red-only union, baseline complied).
        self.assertEqual(
            self._check(
                [
                    self._entry("a", result="bulletproof"),
                    self._entry("n"),
                    self._entry("u", result="unresolved"),
                    self._entry("v", result="void"),
                ]
            ),
            0,
        )

    def test_void_red_only_passes(self):
        self.assertEqual(
            self._check(
                [
                    self._entry("a", result="bulletproof"),
                    self._entry("n"),
                    self._entry("u", result="unresolved"),
                    self._entry("v", result="void"),
                ]
            ),
            0,
        )

    def test_invalid_result_rejected(self):
        self.assertEqual(self._check([self._entry("a", result="adopted")]), 1)

    def test_counters_valid_list_of_strings_accepted(self):
        self.assertEqual(
            self._check(
                [
                    self._entry(
                        "a",
                        result="bulletproof",
                        counters=["Iron Law row added"],
                    ),
                    self._entry("n"),
                    self._entry("u", result="unresolved"),
                    self._entry("v", result="void"),
                ]
            ),
            0,
        )

    def test_counters_with_empty_string_rejected(self):
        self.assertEqual(
            self._check(
                [
                    self._entry("a", result="bulletproof", counters=[""]),
                    self._entry("n"),
                    self._entry("u", result="unresolved"),
                    self._entry("v", result="void"),
                ]
            ),
            1,
        )

    def test_counters_non_list_rejected(self):
        self.assertEqual(
            self._check(
                [
                    self._entry("a", result="bulletproof", counters="x"),
                    self._entry("n"),
                    self._entry("u", result="unresolved"),
                    self._entry("v", result="void"),
                ]
            ),
            1,
        )

    def test_notes_non_string_rejected(self):
        self.assertEqual(
            self._check(
                [
                    self._entry("a", result="bulletproof", notes=3),
                    self._entry("n"),
                    self._entry("u", result="unresolved"),
                    self._entry("v", result="void"),
                ]
            ),
            1,
        )

    def test_missing_results_file_rejected(self):
        self.assertEqual(
            self._check(
                [self._entry("n")], results=[str(self.root / "no.json")]
            ),
            1,
        )

    def test_malformed_results_rejected(self):
        bad = self.root / "bad.json"
        bad.write_text('{"entries": "nope"}')
        self.assertEqual(self._check([self._entry("n")], [str(bad)]), 1)


class PressureRecordTests(unittest.TestCase):
    """record --track pressure-test: the pressure vocabulary lands under
    the pressure-test manifest key, the retrieval/shape vocabularies are
    rejected on this track, --bulletproof is rejected under
    --scope frontmatter, and omitting --track keeps the back-compatible
    retrieval-test default."""

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

    def _record(self, track="pressure-test", **overrides) -> int:
        args = argparse.Namespace(
            skill="test-skill",
            skill_path=str(self.skill_dir),
            manifest=str(self.manifest),
            scope="dir",
            track=track,
            score=None,
            passes=None,
            fails=None,
            gaps=None,
            voids=0,
            adopted=None,
            bulletproof=3,
            no_failure=1,
            unresolved=0,
            ablations=None,
            campaign="campaign-2026-09-18",
            date="2026-09-18",
        )
        for k, v in overrides.items():
            setattr(args, k, v)
        with redirect_stdout(io.StringIO()):
            return evaluator.cmd_record(args)

    def test_pressure_track_writes_pressure_key_and_preserves_others(self):
        self.manifest.write_text(
            json.dumps(
                {
                    "skill": "test-skill",
                    "trigger-test": {"date": "old", "score": 0.5},
                    "shape-test": {"date": "old", "adopted": 1},
                }
            )
        )
        rc = self._record()
        self.assertEqual(rc, 0)
        data = json.loads(self.manifest.read_text())
        self.assertEqual(data["trigger-test"]["score"], 0.5)
        self.assertEqual(data["shape-test"]["adopted"], 1)
        entry = data["pressure-test"]
        self.assertEqual(
            set(entry),
            {
                "date",
                "checksum",
                "bulletproof",
                "no-failure",
                "unresolved",
                "voids",
                "campaign",
            },
        )
        self.assertEqual(entry["bulletproof"], 3)
        self.assertEqual(entry["no-failure"], 1)
        self.assertEqual(entry["unresolved"], 0)
        self.assertEqual(entry["voids"], 0)
        self.assertEqual(
            entry["checksum"], evaluator.hash_skill_dir(self.skill_dir)
        )

    def test_adopted_rejected_on_pressure_track(self):
        rc = self._record(adopted=1)
        self.assertEqual(rc, 1)
        self.assertFalse(self.manifest.exists())

    def test_retrieval_counts_rejected_on_pressure_track(self):
        rc = self._record(passes=1, bulletproof=None)
        self.assertEqual(rc, 1)
        self.assertFalse(self.manifest.exists())

    def test_missing_pressure_count_rejected(self):
        rc = self._record(voids=None)
        self.assertEqual(rc, 1)
        self.assertFalse(self.manifest.exists())

    def test_pressure_counts_rejected_on_retrieval_track(self):
        rc = self._record(
            track="retrieval-test",
            passes=1,
            fails=0,
            gaps=0,
            bulletproof=None,
        )
        self.assertEqual(rc, 1)

    def test_bulletproof_rejected_under_scope_frontmatter(self):
        skill_md = self.root / "SKILL.md"
        skill_md.write_text("---\nname: test-skill\n---\nbody\n")
        args = argparse.Namespace(
            skill="test-skill",
            skill_path=str(skill_md),
            manifest=str(self.manifest),
            scope="frontmatter",
            score=0.9,
            passes=None,
            fails=None,
            gaps=None,
            voids=None,
            adopted=None,
            bulletproof=3,
            no_failure=None,
            unresolved=None,
            ablations=None,
            campaign=None,
            date="2026-09-18",
        )
        with redirect_stderr(io.StringIO()) as err:
            rc = evaluator.cmd_record(args)
        self.assertEqual(rc, 1)
        self.assertIn("counts are only valid with --scope dir", err.getvalue())
        self.assertFalse(self.manifest.exists())

    def test_track_omitted_defaults_to_retrieval_test(self):
        args = argparse.Namespace(
            skill="test-skill",
            skill_path=str(self.skill_dir),
            manifest=str(self.manifest),
            scope="dir",
            score=None,
            passes=1,
            fails=0,
            gaps=0,
            voids=0,
            adopted=None,
            bulletproof=None,
            no_failure=None,
            unresolved=None,
            ablations=None,
            campaign=None,
            date="2026-09-18",
        )
        # No 'track' attribute at all — the phase-1 back-compat path.
        with redirect_stdout(io.StringIO()):
            rc = evaluator.cmd_record(args)
        self.assertEqual(rc, 0)
        data = json.loads(self.manifest.read_text())
        self.assertIn("retrieval-test", data)
        self.assertNotIn("pressure-test", data)


class PressureMetaTests(unittest.TestCase):
    """cmd_pressure_meta: resumes the given session (execute receives
    session=), writes the JSON payload (answer_text, timeout,
    void_signals), fails pre-spend on an empty --session, and follows the
    house HarnessExecutionError policy (stderr, exit 1, no JSON)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.agents_dir = self.root / "agents"
        self.agents_dir.mkdir()
        (self.agents_dir / "pressure-evaluator.opencode.md").write_text(
            "---\nname: pressure-evaluator\nmode: primary\n---\nbody\n"
        )
        self.ws = self.root / "ws"
        self.ws.mkdir()
        self.out = self.root / "meta.json"

    def tearDown(self):
        self.tmp.cleanup()

    class _FakeStrategy:
        def __init__(self, timed_out=False, error=None):
            self.calls: list[dict] = []
            self.timed_out = timed_out
            self.error = error

        def agent_file(self, agents_dir, base):
            return Path(agents_dir) / f"{base}.opencode.md"

        def install(self, *args, **kwargs):
            return None

        def execute(self, ws, agent, query, model, variant, session=None):
            self.calls.append({"query": query, "session": session})
            if self.error is not None:
                raise self.error
            return (
                EventStream(
                    answer_parts=["I chose B because of the deadline."],
                    session_id=session or "",
                ),
                self.timed_out,
            )

    def _args(self, **overrides):
        args = argparse.Namespace(
            harness="opencode",
            agents_dir=str(self.agents_dir),
            workspace=str(self.ws),
            session="sess-42",
            question="You chose B. Why?",
            out=str(self.out),
            model="m1",
            variant="v-x",
            timeout=120,
        )
        for k, v in overrides.items():
            setattr(args, k, v)
        return args

    def _run(self, fake, **overrides):
        buf = io.StringIO()
        with mock_check_and_resolve(fake):
            with redirect_stdout(buf):
                rc = evaluator.cmd_meta(
                    TRACKS["pressure-test"], self._args(**overrides)
                )
        return rc, buf.getvalue()

    def test_resume_writes_json_payload(self):
        fake = self._FakeStrategy()
        rc, out = self._run(fake)
        self.assertEqual(rc, 0)
        self.assertIn("meta: session sess-42", out)
        # execute received the session for the --session resume flag.
        self.assertEqual(fake.calls[0]["session"], "sess-42")
        payload = json.loads(self.out.read_text())
        self.assertEqual(payload["session_id"], "sess-42")
        self.assertEqual(payload["question"], "You chose B. Why?")
        self.assertEqual(
            payload["answer_text"], "I chose B because of the deadline."
        )
        self.assertFalse(payload["timeout"])
        self.assertEqual(payload["void_signals"], [])

    def test_timeout_is_boolean_not_a_void_signal(self):
        fake = self._FakeStrategy(timed_out=True)
        rc, _ = self._run(fake)
        self.assertEqual(rc, 0)
        payload = json.loads(self.out.read_text())
        self.assertTrue(payload["timeout"])
        self.assertEqual(payload["void_signals"], [])

    def test_empty_session_fails_pre_spend_no_json(self):
        fake = self._FakeStrategy()
        with self.assertRaises(SystemExit) as cm:
            with redirect_stderr(io.StringIO()):
                self._run(fake, session="")
        self.assertEqual(cm.exception.code, 1)
        self.assertFalse(self.out.exists())
        self.assertEqual(fake.calls, [])

    def test_missing_out_parent_fails_pre_spend_no_json(self):
        fake = self._FakeStrategy()
        with self.assertRaises(SystemExit) as cm:
            with redirect_stderr(io.StringIO()):
                self._run(fake, out=str(self.root / "no-dir" / "m.json"))
        self.assertEqual(cm.exception.code, 1)
        self.assertEqual(fake.calls, [])

    def test_dead_session_harness_error_exits_1_no_json(self):
        fake = self._FakeStrategy(
            error=HarnessExecutionError("session not found")
        )
        buf_err = io.StringIO()
        with redirect_stderr(buf_err):
            rc, _ = self._run(fake)
        self.assertEqual(rc, 1)
        self.assertFalse(self.out.exists())
        self.assertIn("could not resume the session", buf_err.getvalue())


class PressureEvidenceTests(unittest.TestCase):
    """cmd_pressure_evidence: prints the statement, pressures, and
    compliant_option per entry plus the full answer text, void signals,
    and session id per arm/rep; arm and entry filters; malformed-input
    rejections."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.results = self.root / "results.json"
        results_file(
            self.results,
            [
                {
                    "id": "a",
                    "statement": STATEMENT,
                    "pressures": ["sunk-cost", "time", "social"],
                    "compliant_option": "A",
                    "arms": {
                        "red": {
                            "runs": [
                                {
                                    "answer_text": "I choose B because...",
                                    "void_signals": [],
                                    "session_id": "s1",
                                    "timeout": False,
                                }
                            ]
                        },
                        "green": {
                            "runs": [
                                {
                                    "answer_text": "",
                                    "void_signals": ["empty-answer"],
                                    "session_id": "",
                                    "timeout": True,
                                }
                            ]
                        },
                    },
                },
                {
                    "id": "b",
                    "statement": "other rule",
                    "pressures": ["time", "authority", "pragmatic"],
                    "compliant_option": "C",
                    "arms": {
                        "red": {
                            "runs": [
                                {
                                    "answer_text": "I choose C.",
                                    "void_signals": [],
                                    "session_id": "s2",
                                    "timeout": False,
                                }
                            ]
                        }
                    },
                },
            ],
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, **overrides):
        args = argparse.Namespace(
            results=str(self.results), entry=None, arm=None
        )
        for k, v in overrides.items():
            setattr(args, k, v)
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = evaluator.cmd_evidence(TRACKS["pressure-test"], args)
        return rc, buf.getvalue()

    def test_prints_entry_scoring_fields_and_run_evidence(self):
        rc, out = self._run()
        self.assertEqual(rc, 0)
        self.assertIn("## a", out)
        self.assertIn(f"statement: {STATEMENT}", out)
        self.assertIn("pressures: sunk-cost, time, social", out)
        self.assertIn("compliant_option: A", out)
        self.assertIn("[ red ] rep   1 (s1, ok)", out)
        self.assertIn("I choose B because...", out)
        self.assertIn("[green] rep   1 (no-session, timeout)", out)
        self.assertIn("answer: (empty)", out)
        self.assertIn("void signals: empty-answer", out)
        self.assertIn("## b", out)
        self.assertIn("compliant_option: C", out)
        self.assertIn("evidence: 2 entries", out)

    def test_arm_filter(self):
        rc, out = self._run(entry="a", arm="red")
        self.assertEqual(rc, 0)
        self.assertNotIn("[green]", out)
        self.assertIn("[ red ]", out)

    def test_entry_filter(self):
        rc, out = self._run(entry="b")
        self.assertEqual(rc, 0)
        self.assertNotIn("## a", out)
        self.assertIn("## b", out)
        self.assertIn("evidence: 1 entries", out)

    def test_unknown_entry_rejected(self):
        rc, _ = self._run(entry="zzz")
        self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
