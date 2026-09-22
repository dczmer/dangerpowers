#!/usr/bin/env python3
"""Tests for the shape track (src/tracks.py ShapeTrack): entries-file
validation, arm byte-assembly exactness (v0 span removal, vN replacement),
strict entry x arm serialization in run_entry with per-arm prompt
injection (never workspace byte-states), scored-check (multi-results
union, adoption and gate rules, count gate), record --track shape-test,
and evidence marker triage. Stdlib only; no harness commands are ever
invoked (zero model spend).
"""

import argparse
import io
import json
import subprocess
import tempfile
import threading
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

import evaluator
from src import strategies
from src.strategies import EventStream
from src.tracks import (
    TRACKS,
    assemble_arm_body,
    build_shape_prompt,
    build_shape_run_record,
    load_shape_entries,
    marker_triage_counts,
    verify_arm_bytes,
)

SKILL = "writing-skills"


def ndjson(*events: dict) -> str:
    return "\n".join(json.dumps(e) for e in events) + "\n"


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


FRONTMATTER = "---\nname: demo-skill\n---\n"
SECTION_A = "## Styling\n\nComponents use css modules, never inline"
SECTION_B = "## Testing\n\nTests live next to the component"
VARIANT_A1 = "Never use inline styles."
VARIANT_A2 = (
    "Every component ships as two files: `Name.tsx` and " "`Name.module.css`."
)


def shaping_entry(eid="css-modules", section=SECTION_A, **overrides):
    entry = {
        "id": eid,
        "kind": "shaping",
        "section": section,
        "fixtures": {"application": f"write a component for {eid}"},
        "markers": {"inline_style": "style=\\{\\{"},
        "variants": {"v1": VARIANT_A1, "v2": VARIANT_A2},
    }
    entry.update(overrides)
    return entry


def pattern_entry(eid="hover-states", **overrides):
    entry = {
        "id": eid,
        "kind": "pattern",
        "section": "## Interaction\n\nHover states are CSS pseudo-classes",
        "fixtures": {
            "application": f"build the widget for {eid}",
            "counter-example": f"animate the widget for {eid}",
        },
        "markers": {"hover_hack": "onMouseEnter|onMouseLeave"},
        "restraint_markers": {"keyframe_animation": "@keyframes"},
        "variants": {"v1": "Interactive states are CSS pseudo-classes."},
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
        "date": "2026-09-13",
        "entries": "/tmp/entries.json",
        "arms": ["v0"],
        "fixture_key": "application",
    }
    config.update(config_overrides)
    path.write_text(json.dumps({"config": config, "entries": entries}))
    return path


class ShapeEntriesTests(unittest.TestCase):
    """load_shape_entries: schema validation, pre-spend, exits 1."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "entries.json"

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, entries) -> None:
        self.path.write_text(json.dumps(entries))

    def _load(self):
        return load_shape_entries(self.path)

    def _rejected(self):
        with self.assertRaises(SystemExit) as cm:
            with redirect_stderr(io.StringIO()):
                self._load()
        self.assertEqual(cm.exception.code, 1)

    def test_valid_shaping_and_pattern_entries_load(self):
        self._write([shaping_entry(), pattern_entry()])
        entries = self._load()
        self.assertEqual(
            [e["id"] for e in entries], ["css-modules", "hover-states"]
        )

    def test_missing_file_rejected(self):
        with self.assertRaises(SystemExit) as cm:
            with redirect_stderr(io.StringIO()):
                load_shape_entries(self.path)
        self.assertEqual(cm.exception.code, 1)

    def test_top_level_list_required(self):
        self._write({"id": "not-a-list"})
        self._rejected()

    def test_duplicate_id_rejected(self):
        self._write([shaping_entry(), shaping_entry()])
        self._rejected()

    def test_kind_outside_vocabulary_rejected(self):
        self._write([shaping_entry(kind="discipline")])
        self._rejected()

    def test_missing_section_rejected(self):
        self._write([shaping_entry(section="")])
        self._rejected()

    def test_missing_application_fixture_rejected(self):
        self._write([shaping_entry(fixtures={})])
        self._rejected()

    def test_unknown_fixture_key_rejected(self):
        self._write(
            [
                shaping_entry(
                    fixtures={
                        "application": "q",
                        "variation": "not allowed in v1",
                    }
                )
            ]
        )
        self._rejected()

    def test_pattern_without_counter_example_rejected(self):
        entry = pattern_entry()
        del entry["fixtures"]["counter-example"]
        self._write([entry])
        self._rejected()

    def test_pattern_with_empty_counter_example_rejected(self):
        entry = pattern_entry()
        entry["fixtures"]["counter-example"] = ""
        self._write([entry])
        self._rejected()

    def test_shaping_with_counter_example_rejected(self):
        entry = shaping_entry(
            fixtures={
                "application": "q",
                "counter-example": "shaping entries must not carry one",
            }
        )
        self._write([entry])
        self._rejected()

    def test_empty_markers_rejected(self):
        self._write([shaping_entry(markers={})])
        self._rejected()

    def test_invalid_grep_token_rejected(self):
        self._write([shaping_entry(markers={"bad": "([unclosed"})])
        self._rejected()

    def test_pattern_without_restraint_markers_rejected(self):
        entry = pattern_entry()
        del entry["restraint_markers"]
        self._write([entry])
        self._rejected()

    def test_shaping_with_restraint_markers_rejected(self):
        entry = shaping_entry(restraint_markers={"x": "y"})
        self._write([entry])
        self._rejected()

    def test_no_variants_rejected(self):
        self._write([shaping_entry(variants={})])
        self._rejected()

    def test_more_than_three_variants_rejected(self):
        self._write(
            [
                shaping_entry(
                    variants={
                        "v1": "a",
                        "v2": "b",
                        "v3": "c",
                        "v4": "d",
                    }
                )
            ]
        )
        self._rejected()

    def test_variant_keys_outside_v1_v3_rejected(self):
        self._write([shaping_entry(variants={"control": "a"})])
        self._rejected()

    def test_empty_variant_text_rejected(self):
        self._write([shaping_entry(variants={"v1": ""})])
        self._rejected()


class ArmAssemblyTests(unittest.TestCase):
    """assemble_arm_body / verify_arm_bytes: the byte-exactness spec —
    v0 removes the span plus exactly one following blank line, vN replaces
    the span, and the frontmatter bytes are a caller-side prefix that must
    never be touched."""

    def setUp(self):
        self.body = (
            "# Demo\n\n"
            "intro paragraph\n\n"
            f"{SECTION_A}\n\n"
            "## Later\n\nstill here\n"
        )
        self.entry = shaping_entry()

    def test_v0_removes_span_and_one_blank_line(self):
        new_body = assemble_arm_body(self.body, self.entry, "v0")
        self.assertEqual(
            new_body,
            "# Demo\n\nintro paragraph\n\n## Later\n\nstill here\n",
        )

    def test_v0_removes_only_one_blank_line(self):
        body = f"pre\n\n{SECTION_A}\n\n\npost\n"
        new_body = assemble_arm_body(body, self.entry, "v0")
        self.assertEqual(new_body, "pre\n\n\npost\n")

    def test_v0_span_at_end_without_trailing_blank(self):
        body = f"pre\n\n{SECTION_A}"
        new_body = assemble_arm_body(body, self.entry, "v0")
        self.assertEqual(new_body, "pre\n\n")

    def test_vn_replaces_span_keeps_surrounding_bytes(self):
        new_body = assemble_arm_body(self.body, self.entry, "v1")
        self.assertEqual(
            new_body,
            "# Demo\n\nintro paragraph\n\n"
            f"{VARIANT_A1}\n\n"
            "## Later\n\nstill here\n",
        )

    def test_vn_variant_text_not_in_body_is_assembled(self):
        entry = shaping_entry(variants={"v1": "totally fresh text"})
        new_body = assemble_arm_body(self.body, entry, "v1")
        self.assertIn("totally fresh text", new_body)

    def test_non_unique_span_raises(self):
        body = f"{SECTION_A}\n\n{SECTION_A}\n"
        with self.assertRaises(ValueError):
            assemble_arm_body(body, self.entry, "v0")

    def test_absent_span_raises(self):
        with self.assertRaises(ValueError):
            assemble_arm_body("nothing here\n", self.entry, "v0")

    def test_verify_v0_rejects_span_left_behind(self):
        with self.assertRaises(ValueError):
            verify_arm_bytes(self.body, self.entry, "v0")

    def test_verify_vn_rejects_missing_variant(self):
        with self.assertRaises(ValueError):
            verify_arm_bytes(self.body, self.entry, "v1")

    def test_verify_accepts_valid_assemblies(self):
        verify_arm_bytes(
            assemble_arm_body(self.body, self.entry, "v0"),
            self.entry,
            "v0",
        )
        verify_arm_bytes(
            assemble_arm_body(self.body, self.entry, "v2"),
            self.entry,
            "v2",
        )


class ShapeRunRecordTests(unittest.TestCase):
    """build_shape_run_record: the retrieval builder adapted — the arm
    key is recorded, any skill-load attempt is a void signal (the
    conventions are injected; there is no load signal on this track),
    and control-loaded-skill does not exist here."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self.tmp.name) / "ws"
        self.ws.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def _record(self, ev, arm="v0"):
        return build_shape_run_record(ev, "the prompt", False, self.ws, arm)

    def test_arm_key_recorded(self):
        rec = self._record(EventStream(answer_parts=["a"]), arm="v2")
        self.assertEqual(rec["arm"], "v2")

    def test_skill_load_attempt_signals_on_every_arm(self):
        ev = EventStream(
            answer_parts=["a"],
            skill_loads=[{"name": "demo-skill", "status": "completed"}],
        )
        for arm in ("v0", "v1", "v3"):
            rec = self._record(ev, arm=arm)
            self.assertIn("skill-load-attempted", rec["void_signals"])

    def test_no_control_loaded_skill_signal_on_any_arm(self):
        ev = EventStream(
            answer_parts=["a"],
            skill_loads=[{"name": "demo-skill", "status": "completed"}],
        )
        for arm in ("v0", "v1", "v3"):
            rec = self._record(ev, arm=arm)
            self.assertNotIn("control-loaded-skill", rec["void_signals"])

    def test_no_load_no_signal(self):
        # The conventions are injected: a run with no load attempt at all
        # carries no void signal (contrast: the old skill-not-loaded).
        rec = self._record(EventStream(answer_parts=["a"]), arm="v1")
        self.assertEqual(rec["void_signals"], [])

    def test_timeout_is_a_field_not_a_void_signal(self):
        ev = EventStream(answer_parts=["complete answer"])
        rec = self._record(ev)
        self.assertTrue(rec["timeout"] is False)
        ev_timeout = EventStream(answer_parts=["complete answer"])
        rec = build_shape_run_record(
            ev_timeout, "the prompt", True, self.ws, "v0"
        )
        self.assertTrue(rec["timeout"])
        self.assertEqual(rec["void_signals"], [])


class ShapeSuiteTests(unittest.TestCase):
    """The shape suite end-to-end with a fake strategy: entries x arms run
    strictly serialized (spend discipline — never the retrieval track's
    arm-parallel structure), every rep's prompt carries that arm's
    injected body assembled fresh from the snapshotted skill file, no
    skill= is passed, and the workspace is never written. The results
    config records model/variant for attribution."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.agents_dir = self.root / "agents"
        self.agents_dir.mkdir()
        (self.agents_dir / "shape-evaluator.opencode.md").write_text(
            "---\nname: shape-evaluator\nmode: primary\n---\nbody\n"
        )
        self.ws = self.root / "ws"
        self.ws.mkdir()
        self.body = "# Demo\n\n" + SECTION_A + "\n\n" + SECTION_B + "\n"
        self.skill_body = self.root / "skill-body.txt"
        self.skill_body.write_text(self.body)
        self.entries_path = self.root / "entries.json"
        self.out = self.root / "results.json"

    def tearDown(self):
        log = evaluator._Log.file
        evaluator._Log.file = None
        if log is not None:
            log.close()
        self.tmp.cleanup()

    class _FakeStrategy:
        """Records each dispatch's prompt so the test can assert the
        arm sequence and injected bytes; brief sleep lets rep batches
        overlap within an arm without ever overlapping across arms."""

        def __init__(self):
            self.lock = threading.Lock()
            self.queries: list[str] = []
            self.skills: list[str | None] = []
            self.active = 0
            self.max_active = 0

        def agent_file(self, agents_dir, base):
            return Path(agents_dir) / f"{base}.opencode.md"

        def install(self, *args, **kwargs):
            return None

        def execute(self, ws, agent, query, model, variant, skill=None):
            with self.lock:
                self.active += 1
                self.max_active = max(self.max_active, self.active)
            try:
                with self.lock:
                    self.queries.append(query)
                    self.skills.append(skill)
                time.sleep(0.02)
                return (EventStream(answer_parts=["answer"]), False)
            finally:
                with self.lock:
                    self.active -= 1

    def _write_entries(self, entries) -> None:
        self.entries_path.write_text(json.dumps(entries))

    def _args(self, **overrides):
        args = argparse.Namespace(
            harness="opencode",
            skill="demo-skill",
            agents_dir=str(self.agents_dir),
            workspace=str(self.ws),
            entries=str(self.entries_path),
            skill_file=str(self.skill_body),
            arms="v0,v1",
            out=str(self.out),
            fixture_key="application",
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
                rc = evaluator.run_suite(TRACKS["shape-test"], args)
        return rc, buf.getvalue(), fake

    def test_entries_x_arms_serialized_and_prompts_carry_arm_bodies(self):
        self._write_entries(
            [
                shaping_entry(eid="a", section=SECTION_A),
                shaping_entry(
                    eid="b", section=SECTION_B, variants={"v1": "B variant"}
                ),
            ]
        )
        rc, _, fake = self._run()
        self.assertEqual(rc, 0)

        def label(query):
            if "B variant" in query:
                return ("b", "v1")
            if VARIANT_A1 in query:
                return ("a", "v1")
            if SECTION_A not in query:
                return ("a", "v0")
            if SECTION_B not in query:
                return ("b", "v0")
            raise AssertionError("prompt carries no arm body")

        labels = [label(q) for q in fake.queries]
        # Entries x arms run strictly serialized: each (entry, arm) batch
        # is contiguous.
        self.assertEqual(
            labels,
            [
                ("a", "v0"),
                ("a", "v0"),
                ("a", "v1"),
                ("a", "v1"),
                ("b", "v0"),
                ("b", "v0"),
                ("b", "v1"),
                ("b", "v1"),
            ],
        )
        # Every dispatch injects an arm body: conventions header, the
        # snapshot-derived body differing per arm, then the bare fixture.
        for query, (eid, _arm) in zip(fake.queries, labels):
            self.assertTrue(query.startswith("Project conventions:\n"))
            self.assertTrue(
                query.endswith(f"Task:\nwrite a component for {eid}")
            )
        # v0 arms have their entry's section removed; v1 arms carry the
        # variant text in its place.
        for query, (eid, arm) in zip(fake.queries, labels):
            if arm == "v0":
                section = SECTION_A if eid == "a" else SECTION_B
                self.assertNotIn(section, query)
            else:
                variant = VARIANT_A1 if eid == "a" else "B variant"
                self.assertIn(variant, query)
        # The workspace is never written: no synced skill, no byte state.
        self.assertFalse((self.ws / ".agents").exists())

    def test_reps_within_one_arm_batch_parallelize(self):
        self._write_entries([shaping_entry(eid="a", section=SECTION_A)])
        rc, _, fake = self._run(reps=3)
        self.assertEqual(rc, 0)
        self.assertGreaterEqual(fake.max_active, 2)

    def test_prompt_is_injected_conventions_and_no_skill_passed(self):
        self._write_entries([shaping_entry(eid="a", section=SECTION_A)])
        rc, _, fake = self._run()
        self.assertEqual(rc, 0)
        for query in fake.queries:
            self.assertIn("\n\nTask:\nwrite a component for a", query)
        for skill in fake.skills:
            self.assertIsNone(skill)

    def test_results_keyed_by_arm_with_config(self):
        self._write_entries([shaping_entry(eid="a", section=SECTION_A)])
        rc, _, _ = self._run()
        self.assertEqual(rc, 0)
        data = json.loads(self.out.read_text())
        config = data["config"]
        self.assertEqual(config["skill"], "demo-skill")
        self.assertEqual(config["model"], "m1")
        self.assertEqual(config["variant"], "v-x")
        self.assertEqual(config["reps"], 2)
        self.assertEqual(config["timeout"], 120)
        self.assertEqual(config["arms"], ["v0", "v1"])
        self.assertEqual(config["fixture_key"], "application")
        self.assertEqual(config["entries"], str(self.entries_path))
        self.assertEqual(config["skill_file"], str(self.skill_body))
        self.assertIn("date", config)
        (entry,) = data["entries"]
        self.assertEqual(entry["id"], "a")
        self.assertEqual(entry["kind"], "shaping")
        self.assertEqual(entry["markers"], {"inline_style": "style=\\{\\{"})
        self.assertIsNone(entry["restraint_markers"])
        self.assertEqual(set(entry["arms"]), {"v0", "v1"})
        for arm in ("v0", "v1"):
            runs = entry["arms"][arm]["runs"]
            self.assertEqual(len(runs), 2)
            for run in runs:
                self.assertEqual(run["arm"], arm)
                self.assertEqual(run["void_signals"], [])

    def test_progress_lines_are_arm_tagged(self):
        self._write_entries([shaping_entry(eid="a", section=SECTION_A)])
        rc, out, _ = self._run()
        self.assertEqual(rc, 0)
        self.assertIn("[ v0 ] [rep   1] started", out)
        self.assertIn("[ v1 ] [rep   1] started", out)
        self.assertIn("[ v0 ] [rep   1] completed", out)

    def test_abort_leaves_no_workspace_byte_state(self):
        self._write_entries([shaping_entry(eid="a", section=SECTION_A)])
        args = self._args()

        class _Aborting(self._FakeStrategy):
            def execute(self, ws, agent, query, model, variant, skill=None):
                if len(self.queries) == 1:
                    raise RuntimeError("boom")
                return super().execute(ws, agent, query, model, variant, skill)

        fake = _Aborting()
        with mock_check_and_resolve(fake):
            with redirect_stdout(io.StringIO()):
                with redirect_stderr(io.StringIO()):
                    with self.assertRaises(RuntimeError):
                        evaluator.run_suite(TRACKS["shape-test"], args)
        # Nothing to restore: the workspace never carries a byte state.
        self.assertFalse((self.ws / ".agents").exists())


class _BlockingStrategy:
    """Stand-in for a harness strategy in pre-spend gate tests: agent_file
    resolves like a real strategy, but execute() raising proves the gate
    fired before any harness invocation."""

    def agent_file(self, agents_dir, base):
        return Path(agents_dir) / f"{base}.opencode.md"

    def install(self, *args, **kwargs):
        return None

    def execute(self, *args, **kwargs):
        raise AssertionError("harness invoked despite a pre-spend gate")


class mock_check_and_resolve:
    """Patches check_harness away and resolve_strategy to a factory
    returning the given fake strategy instance (a blocking strategy when
    None — pre-spend gate tests must never reach execute())."""

    def __init__(self, fake):
        self.fake = fake if fake is not None else _BlockingStrategy()
        self._patches = []

    def __enter__(self):
        self._patches.append(
            mock.patch.object(evaluator, "check_harness", lambda *a: None)
        )
        self._patches.append(
            mock.patch.object(
                evaluator,
                "resolve_strategy",
                lambda h: lambda timeout=30: self.fake,
            )
        )
        for p in self._patches:
            p.start()

    def __exit__(self, *exc):
        for p in self._patches:
            p.stop()


class ShapePreSpendGateTests(unittest.TestCase):
    """ShapeTrack.pre_spend_gates validation: every violation exits 1 with
    an exact message before any harness invocation (the strategy factory
    raises if it is ever called after the gates — the assertions on
    SystemExit/return code prove the gate fired first)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.agents_dir = self.root / "agents"
        self.agents_dir.mkdir()
        (self.agents_dir / "shape-evaluator.opencode.md").write_text(
            "---\nname: shape-evaluator\nmode: primary\n---\nbody\n"
        )
        self.ws = self.root / "ws"
        self.ws.mkdir()
        # The driver-produced snapshot: body bytes, frontmatter already
        # stripped (the drift gate matches spans against these bytes).
        self.skill_body = self.root / "skill-body.txt"
        self.skill_body.write_text("# Demo\n\n" + SECTION_A + "\n")
        self.entries_path = self.root / "entries.json"
        self.entries_path.write_text(
            json.dumps([shaping_entry(eid="a", section=SECTION_A)])
        )
        self.out = self.root / "results.json"

    def tearDown(self):
        evaluator._Log.file = None
        self.tmp.cleanup()

    def _run(self):
        args = argparse.Namespace(
            harness="opencode",
            skill="demo-skill",
            agents_dir=str(self.agents_dir),
            workspace=str(self.ws),
            entries=str(self.entries_path),
            skill_file=str(self.skill_body),
            arms="v0",
            out=str(self.out),
            fixture_key="application",
            model=None,
            variant=None,
            reps=1,
            timeout=120,
        )
        with mock_check_and_resolve(None):
            with redirect_stdout(io.StringIO()):
                with redirect_stderr(io.StringIO()):
                    return evaluator.run_suite(TRACKS["shape-test"], args)

    def test_span_absent_from_body_exits_1(self):
        self.skill_body.write_text("# Demo\n\nother text\n")
        with self.assertRaises(SystemExit) as cm:
            self._run()
        self.assertEqual(cm.exception.code, 1)
        self.assertFalse(self.out.exists())

    def test_span_occurring_twice_exits_1(self):
        self.skill_body.write_text(
            "# Demo\n\n" + SECTION_A + "\n\n" + SECTION_A + "\n"
        )
        with self.assertRaises(SystemExit) as cm:
            self._run()
        self.assertEqual(cm.exception.code, 1)
        self.assertFalse(self.out.exists())

    def test_synced_skill_in_workspace_exits_1(self):
        # Contamination gate: the workspace must stay sterile — this
        # track injects the body and never syncs.
        skill_dir = self.ws / ".agents" / "skills" / "demo-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            FRONTMATTER + "# Demo\n\n" + SECTION_A + "\n"
        )
        with self.assertRaises(SystemExit) as cm:
            self._run()
        self.assertEqual(cm.exception.code, 1)
        self.assertFalse(self.out.exists())

    def test_counter_example_fixture_key_on_shaping_entry_exits_1(self):
        with self.assertRaises(SystemExit) as cm:
            args = argparse.Namespace(
                harness="opencode",
                skill="demo-skill",
                agents_dir=str(self.agents_dir),
                workspace=str(self.ws),
                entries=str(self.entries_path),
                skill_file=str(self.skill_body),
                arms="v0",
                out=str(self.out),
                fixture_key="counter-example",
                model=None,
                variant=None,
                reps=1,
                timeout=120,
            )
            with mock_check_and_resolve(None):
                with redirect_stdout(io.StringIO()):
                    with redirect_stderr(io.StringIO()):
                        evaluator.run_suite(TRACKS["shape-test"], args)
        self.assertEqual(cm.exception.code, 1)
        self.assertFalse(self.out.exists())

    def test_arm_not_defined_by_entry_exits_1(self):
        with self.assertRaises(SystemExit) as cm:
            args = argparse.Namespace(
                harness="opencode",
                skill="demo-skill",
                agents_dir=str(self.agents_dir),
                workspace=str(self.ws),
                entries=str(self.entries_path),
                skill_file=str(self.skill_body),
                arms="v3",
                out=str(self.out),
                fixture_key="application",
                model=None,
                variant=None,
                reps=1,
                timeout=120,
            )
            with mock_check_and_resolve(None):
                with redirect_stdout(io.StringIO()):
                    with redirect_stderr(io.StringIO()):
                        evaluator.run_suite(TRACKS["shape-test"], args)
        self.assertEqual(cm.exception.code, 1)

    def test_invalid_fixture_key_exits_1(self):
        with self.assertRaises(SystemExit) as cm:
            args = argparse.Namespace(
                harness="opencode",
                skill="demo-skill",
                agents_dir=str(self.agents_dir),
                workspace=str(self.ws),
                entries=str(self.entries_path),
                skill_file=str(self.skill_body),
                arms="v0",
                out=str(self.out),
                fixture_key="gap",
                model=None,
                variant=None,
                reps=1,
                timeout=120,
            )
            with mock_check_and_resolve(None):
                with redirect_stdout(io.StringIO()):
                    with redirect_stderr(io.StringIO()):
                        evaluator.run_suite(TRACKS["shape-test"], args)
        self.assertEqual(cm.exception.code, 1)

    def test_reps_below_one_exits_1(self):
        with self.assertRaises(SystemExit) as cm:
            args = argparse.Namespace(
                harness="opencode",
                skill="demo-skill",
                agents_dir=str(self.agents_dir),
                workspace=str(self.ws),
                entries=str(self.entries_path),
                skill_file=str(self.skill_body),
                arms="v0",
                out=str(self.out),
                fixture_key="application",
                model=None,
                variant=None,
                reps=0,
                timeout=120,
            )
            with mock_check_and_resolve(None):
                with redirect_stdout(io.StringIO()):
                    with redirect_stderr(io.StringIO()):
                        evaluator.run_suite(TRACKS["shape-test"], args)
        self.assertEqual(cm.exception.code, 1)


class ShapeScoredCheckTests(unittest.TestCase):
    """The shape scored-check (cmd_scored_check over ShapeTrack):
    multi-results union with dedupe, adoption discipline (adopted_arm
    rules), the pattern restraint-gate rule, and the record-step count
    gate."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        run = {"answer_text": "a", "void_signals": [], "session_id": "s"}
        control = self.root / "control.json"
        results_file(
            control,
            [
                {
                    "id": "a",
                    "kind": "shaping",
                    "arms": {"v0": {"runs": [run]}},
                },
                {
                    "id": "p",
                    "kind": "pattern",
                    "arms": {"v0": {"runs": [run]}},
                },
            ],
        )
        variants = self.root / "variants.json"
        results_file(
            variants,
            [
                {
                    "id": "a",
                    "kind": "shaping",
                    "arms": {
                        "v1": {"runs": [run]},
                        "v2": {"runs": [run]},
                    },
                },
                {
                    "id": "p",
                    "kind": "pattern",
                    "arms": {"v1": {"runs": [run]}},
                },
            ],
            arms=["v1", "v2"],
        )
        self.results = [str(control), str(variants)]
        self.scored = self.root / "scored.json"

    def tearDown(self):
        self.tmp.cleanup()

    def _entry(self, eid, **overrides):
        entry = {
            "id": eid,
            "kind": "shaping" if eid == "a" else "pattern",
            "result": "no-failure",
            "marker_counts": {"v0": {"inline_style": 2}},
            "notes": "n",
        }
        entry.update(overrides)
        return entry

    def _check(self, entries, **overrides):
        self.scored.write_text(json.dumps({"entries": entries}))
        args = argparse.Namespace(
            track="shape-test",
            results=list(self.results),
            scored=str(self.scored),
            adopted=None,
            no_failure=None,
            unresolved=None,
            voids=None,
        )
        for k, v in overrides.items():
            setattr(args, k, v)
        with redirect_stdout(io.StringIO()):
            return evaluator.cmd_scored_check(args)

    def test_missing_union_id_rejected(self):
        self.assertEqual(
            self._check(
                [self._entry("a", result="adopted", adopted_arm="v2")]
            ),
            1,
        )

    def test_unknown_id_rejected(self):
        self.assertEqual(
            self._check(
                [
                    self._entry("a", result="adopted", adopted_arm="v2"),
                    self._entry("p"),
                    self._entry("zzz"),
                ]
            ),
            1,
        )

    def test_kind_mismatch_across_results_rejected(self):
        bad = self.root / "bad.json"
        run = {"answer_text": "a", "void_signals": [], "session_id": "s"}
        results_file(
            bad,
            [{"id": "a", "kind": "pattern", "arms": {"v0": {"runs": [run]}}}],
        )
        self.scored.write_text(
            json.dumps(
                {
                    "entries": [
                        self._entry("a", result="adopted", adopted_arm="v2"),
                        self._entry("p"),
                    ]
                }
            )
        )
        args = argparse.Namespace(
            track="shape-test",
            results=[self.results[0], str(bad)],
            scored=str(self.scored),
            adopted=None,
            no_failure=None,
            unresolved=None,
            voids=None,
        )
        with redirect_stdout(io.StringIO()):
            self.assertEqual(evaluator.cmd_scored_check(args), 1)

    def test_kind_mismatch_vs_results_rejected(self):
        self.assertEqual(
            self._check(
                [
                    self._entry("a", kind="pattern"),
                    self._entry("p"),
                ]
            ),
            1,
        )

    def test_adopted_requires_adopted_arm(self):
        self.assertEqual(
            self._check(
                [self._entry("a", result="adopted"), self._entry("p")]
            ),
            1,
        )

    def test_adopted_arm_v0_rejected(self):
        self.assertEqual(
            self._check(
                [
                    self._entry("a", result="adopted", adopted_arm="v0"),
                    self._entry("p"),
                ]
            ),
            1,
        )

    def test_adopted_arm_v0_rerun_rejected(self):
        run = {"answer_text": "a", "void_signals": [], "session_id": "s"}
        rerun = self.root / "control-rerun.json"
        results_file(
            rerun,
            [
                {
                    "id": "a",
                    "kind": "shaping",
                    "arms": {"v0-rerun": {"runs": [run]}},
                }
            ],
            arms=["v0-rerun"],
        )
        self.results.append(str(rerun))
        self.assertEqual(
            self._check(
                [
                    self._entry("a", result="adopted", adopted_arm="v0-rerun"),
                    self._entry("p"),
                ]
            ),
            1,
        )

    def test_adopted_arm_not_in_results_rejected(self):
        self.assertEqual(
            self._check(
                [
                    self._entry("a", result="adopted", adopted_arm="v9"),
                    self._entry("p"),
                ]
            ),
            1,
        )

    def test_adopted_arm_on_non_adopted_rejected(self):
        self.assertEqual(
            self._check(
                [self._entry("a", adopted_arm="v2"), self._entry("p")]
            ),
            1,
        )

    def test_pattern_adopted_requires_gate(self):
        self.assertEqual(
            self._check(
                [
                    self._entry("a", result="adopted", adopted_arm="v2"),
                    self._entry("p", result="adopted", adopted_arm="v1"),
                ]
            ),
            1,
        )

    def test_pattern_adopted_with_gate_passes(self):
        self.assertEqual(
            self._check(
                [
                    self._entry("a", result="adopted", adopted_arm="v2"),
                    self._entry(
                        "p",
                        result="adopted",
                        adopted_arm="v1",
                        restraint_gate="fail",
                    ),
                ]
            ),
            0,
        )

    def test_gate_on_non_adopted_pattern_rejected(self):
        self.assertEqual(
            self._check(
                [self._entry("a"), self._entry("p", restraint_gate="pass")]
            ),
            1,
        )

    def test_gate_on_shaping_entry_rejected(self):
        self.assertEqual(
            self._check(
                [
                    self._entry(
                        "a",
                        result="adopted",
                        adopted_arm="v2",
                        restraint_gate="pass",
                    ),
                    self._entry("p"),
                ]
            ),
            1,
        )

    def test_invalid_result_rejected(self):
        self.assertEqual(
            self._check([self._entry("a", result="gap"), self._entry("p")]),
            1,
        )

    def test_bad_marker_counts_rejected(self):
        self.assertEqual(
            self._check(
                [
                    self._entry("a", marker_counts=["not", "dict"]),
                    self._entry("p"),
                ]
            ),
            1,
        )


class ShapeRecordTests(unittest.TestCase):
    """record --track shape-test: the counts flags are rejected on the
    dir scope (`counts flags are replaced by --scored` / `--scored is
    required with --scope dir`)."""

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

    def _record(self, track="shape-test", **overrides) -> int:
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
            adopted=2,
            no_failure=1,
            unresolved=0,
            ablations=None,
            campaign="campaign-2026-09-13",
            date="2026-09-13",
        )
        for k, v in overrides.items():
            setattr(args, k, v)
        err = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(err):
            rc = evaluator.cmd_record(args)
        self.last_err = err.getvalue()
        return rc

    def test_counts_flags_replaced_by_scored(self):
        rc = self._record()
        self.assertEqual(rc, 1)
        self.assertIn("counts flags are replaced by --scored", self.last_err)
        self.assertFalse(self.manifest.exists())

    def test_missing_scored_rejected(self):
        rc = self._record(
            voids=None, adopted=None, no_failure=None, unresolved=None
        )
        self.assertEqual(rc, 1)
        self.assertIn("--scored is required with --scope dir", self.last_err)
        self.assertFalse(self.manifest.exists())


class ShapeEvidenceTests(unittest.TestCase):
    """ShapeTrack.print_evidence: extraction with marker triage counts,
    arm and entry filters, and rejection of malformed results."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.results = self.root / "results.json"
        results_file(
            self.results,
            [
                {
                    "id": "a",
                    "kind": "shaping",
                    "markers": {"inline_style": "style=\\{\\{"},
                    "restraint_markers": None,
                    "arms": {
                        "v0": {
                            "runs": [
                                {
                                    "answer_text": "<div style={{x: 1}}>",
                                    "void_signals": [],
                                    "session_id": "s1",
                                    "timeout": False,
                                }
                            ]
                        },
                        "v1": {
                            "runs": [
                                {
                                    "answer_text": "clean",
                                    "void_signals": ["skill-not-loaded"],
                                    "session_id": "",
                                    "timeout": True,
                                }
                            ]
                        },
                    },
                },
                {
                    "id": "p",
                    "kind": "pattern",
                    "markers": {"hover_hack": "onMouseEnter"},
                    "restraint_markers": {"keyframes": "@keyframes"},
                    "arms": {
                        "v1": {
                            "runs": [
                                {
                                    "answer_text": "@keyframes spin {}",
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
            track="shape-test",
            results=str(self.results),
            entry=None,
            arm=None,
            compare=False,
        )
        for k, v in overrides.items():
            setattr(args, k, v)
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = evaluator.cmd_evidence(args)
        return rc, buf.getvalue()

    def test_prints_runs_with_marker_triage(self):
        rc, out = self._run()
        self.assertEqual(rc, 0)
        self.assertIn("## a (shaping)", out)
        self.assertIn("[ v0 ] rep   1 (s1, ok)", out)
        self.assertIn("inline_style=1", out)
        self.assertIn("[ v1 ] rep   1 (no-session, timeout)", out)
        self.assertIn("void signals: skill-not-loaded", out)
        self.assertIn("## p (pattern)", out)
        self.assertIn("restraint markers: keyframes=1", out)
        self.assertIn("evidence: 2 entries", out)

    def test_arm_filter(self):
        rc, out = self._run(entry="a", arm="v1")
        self.assertEqual(rc, 0)
        self.assertNotIn("[ v0 ]", out)
        self.assertIn("[ v1 ]", out)

    def test_unknown_entry_rejected(self):
        rc, _ = self._run(entry="zzz")
        self.assertEqual(rc, 1)

    def test_compare_exceeds_only_on_strictly_greater_frequency(self):
        results_file(
            self.results,
            [
                {
                    "id": "a",
                    "kind": "pattern",
                    "markers": {"m": "TODO"},
                    "restraint_markers": None,
                    "arms": {
                        # pooled: 2 matching / 4 answer lines = 0.5
                        "v0": {
                            "runs": [
                                {
                                    "answer_text": "TODO\nline",
                                    "void_signals": [],
                                    "session_id": "s1",
                                    "timeout": False,
                                },
                                {
                                    "answer_text": "TODO\nline",
                                    "void_signals": [],
                                    "session_id": "s2",
                                    "timeout": False,
                                },
                            ]
                        },
                        # 2/2 = 1.0 -> EXCEEDS
                        "v1": {
                            "runs": [
                                {
                                    "answer_text": "TODO\nTODO",
                                    "void_signals": [],
                                    "session_id": "s3",
                                    "timeout": False,
                                }
                            ]
                        },
                        # 1/2 = 0.5 -> tie, does-not-exceed
                        "v2": {
                            "runs": [
                                {
                                    "answer_text": "TODO\nline",
                                    "void_signals": [],
                                    "session_id": "s4",
                                    "timeout": False,
                                }
                            ]
                        },
                        # 0/2 = 0.0 -> does-not-exceed
                        "v3": {
                            "runs": [
                                {
                                    "answer_text": "line\nline",
                                    "void_signals": [],
                                    "session_id": "s5",
                                    "timeout": False,
                                }
                            ]
                        },
                    },
                }
            ],
        )
        rc, out = self._run(entry="a", compare=True)
        self.assertEqual(rc, 0)
        self.assertIn("compare m: v1 1.0 vs v0 0.5 -> EXCEEDS", out)
        self.assertIn("compare m: v2 0.5 vs v0 0.5 -> does-not-exceed", out)
        self.assertIn("compare m: v3 0.0 vs v0 0.5 -> does-not-exceed", out)
        self.assertEqual(out.count("compare m:"), 3)

    def test_compare_skips_v0_family_arms_as_candidates(self):
        results_file(
            self.results,
            [
                {
                    "id": "a",
                    "kind": "pattern",
                    "markers": {"m": "TODO"},
                    "restraint_markers": None,
                    "arms": {
                        "v0": {
                            "runs": [
                                {
                                    "answer_text": "TODO\nline",
                                    "void_signals": [],
                                    "session_id": "s1",
                                    "timeout": False,
                                }
                            ]
                        },
                        "v0-rerun": {
                            "runs": [
                                {
                                    "answer_text": "TODO\nTODO",
                                    "void_signals": [],
                                    "session_id": "s2",
                                    "timeout": False,
                                }
                            ]
                        },
                    },
                }
            ],
        )
        rc, out = self._run(entry="a", compare=True)
        self.assertEqual(rc, 0)
        self.assertNotIn("compare m:", out)

    def test_compare_without_v0_control_skips_with_note(self):
        results_file(
            self.results,
            [
                {
                    "id": "a",
                    "kind": "pattern",
                    "markers": {"m": "TODO"},
                    "restraint_markers": None,
                    "arms": {
                        "v1": {
                            "runs": [
                                {
                                    "answer_text": "TODO\nTODO",
                                    "void_signals": [],
                                    "session_id": "s1",
                                    "timeout": False,
                                }
                            ]
                        }
                    },
                }
            ],
        )
        rc, out = self._run(entry="a", compare=True)
        self.assertEqual(rc, 0)
        self.assertIn("compare: entry a: no v0 control arm", out)
        self.assertNotIn("compare m:", out)

    def test_compare_off_leaves_output_unchanged(self):
        rc, out = self._run()
        self.assertEqual(rc, 0)
        self.assertNotIn("compare", out)


class MarkerTriageTests(unittest.TestCase):
    def test_counts_lines_matching_token(self):
        answer = "a style={{x}}\nb plain\nc style={{y}}\n"
        counts = marker_triage_counts(answer, {"inline_style": "style=\\{\\{"})
        self.assertEqual(counts, {"inline_style": 2})

    def test_empty_answer_zeroes_all_markers(self):
        counts = marker_triage_counts(
            "", {"inline_style": "style", "other": "x"}
        )
        self.assertEqual(counts, {"inline_style": 0, "other": 0})


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
        arm_body = assemble_arm_body(self.BODY, self.ENTRY, "v0")
        self.assertNotIn(self.SECTION, arm_body)
        # Neighbour sections keep exactly one blank line between them.
        self.assertIn("# Conventions\n\n## Layout", arm_body)

    def test_variant_replaces_span(self):
        arm_body = assemble_arm_body(self.BODY, self.ENTRY, "v1")
        self.assertIn("Never use inline styles.", arm_body)
        self.assertNotIn(self.SECTION, arm_body)

    def test_non_unique_span_raises(self):
        body = self.BODY + "\n" + self.SECTION + "\n"
        with self.assertRaises(ValueError):
            assemble_arm_body(body, self.ENTRY, "v0")

    def test_verify_arm_bytes_catches_bad_assembly(self):
        with self.assertRaises(ValueError):
            verify_arm_bytes(self.BODY, self.ENTRY, "v0")
        with self.assertRaises(ValueError):
            verify_arm_bytes(self.BODY, self.ENTRY, "v1")
        ok = assemble_arm_body(self.BODY, self.ENTRY, "v0")
        verify_arm_bytes(ok, self.ENTRY, "v0")  # no raise

    def test_prompt_injects_conventions_and_fixture(self):
        arm_body = assemble_arm_body(self.BODY, self.ENTRY, "v0")
        prompt = build_shape_prompt(
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
        record = build_shape_run_record(ev, "p", False, Path("/"), "v0")
        self.assertIn("skill-load-attempted", record["void_signals"])
        self.assertNotIn("empty-answer", record["void_signals"])

    def test_clean_run_has_no_signals(self):
        ev = self._ev([text_event("the artifact")])
        record = build_shape_run_record(ev, "p", False, Path("/"), "v0")
        self.assertEqual(record["void_signals"], [])
        self.assertNotIn("skill_load_completed", record)


class ShapeSuiteEndToEndTests(unittest.TestCase):
    """The shape suite with a stubbed harness: injection lands in the
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
            redirect_stdout(io.StringIO()),
        ):
            rc = evaluator.run_suite(TRACKS["shape-test"], self._args())
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
            redirect_stderr(buf),
            redirect_stdout(io.StringIO()),
            self.assertRaises(SystemExit),
        ):
            evaluator.run_suite(TRACKS["shape-test"], self._args())
        self.assertIn("never sync", buf.getvalue())

    def test_missing_skill_file_fails_pre_spend(self):
        args = self._args()
        args.skill_file = str(self.root / "absent.txt")
        buf = io.StringIO()
        with (
            mock.patch.object(
                strategies.shutil, "which", return_value="/usr/bin/opencode"
            ),
            redirect_stderr(buf),
            redirect_stdout(io.StringIO()),
            self.assertRaises(SystemExit),
        ):
            evaluator.run_suite(TRACKS["shape-test"], args)
        self.assertIn("skill file not found", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
