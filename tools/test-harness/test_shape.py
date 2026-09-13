#!/usr/bin/env python3
"""Tests for the shape-track additions to evaluator.py: entries-file
validation, arm byte-assembly exactness (v0 span removal, vN replacement),
strict entry x arm serialization in cmd_shape_suite with workspace-byte
restoration, shape-scored-check (multi-results union, adoption and gate
rules, count gate), record --track shape-test, and shape-evidence marker
triage. Stdlib only; no harness commands are ever invoked (zero model
spend).
"""

import argparse
import io
import json
import tempfile
import threading
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

import evaluator
from strategies import EventStream

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
        return evaluator.load_shape_entries(self.path)

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
                evaluator.load_shape_entries(self.path)
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
        new_body = evaluator.assemble_arm_body(self.body, self.entry, "v0")
        self.assertEqual(
            new_body,
            "# Demo\n\nintro paragraph\n\n## Later\n\nstill here\n",
        )

    def test_v0_removes_only_one_blank_line(self):
        body = f"pre\n\n{SECTION_A}\n\n\npost\n"
        new_body = evaluator.assemble_arm_body(body, self.entry, "v0")
        self.assertEqual(new_body, "pre\n\n\npost\n")

    def test_v0_span_at_end_without_trailing_blank(self):
        body = f"pre\n\n{SECTION_A}"
        new_body = evaluator.assemble_arm_body(body, self.entry, "v0")
        self.assertEqual(new_body, "pre\n\n")

    def test_vn_replaces_span_keeps_surrounding_bytes(self):
        new_body = evaluator.assemble_arm_body(self.body, self.entry, "v1")
        self.assertEqual(
            new_body,
            "# Demo\n\nintro paragraph\n\n"
            f"{VARIANT_A1}\n\n"
            "## Later\n\nstill here\n",
        )

    def test_vn_variant_text_not_in_body_is_assembled(self):
        entry = shaping_entry(variants={"v1": "totally fresh text"})
        new_body = evaluator.assemble_arm_body(self.body, entry, "v1")
        self.assertIn("totally fresh text", new_body)

    def test_non_unique_span_raises(self):
        body = f"{SECTION_A}\n\n{SECTION_A}\n"
        with self.assertRaises(ValueError):
            evaluator.assemble_arm_body(body, self.entry, "v0")

    def test_absent_span_raises(self):
        with self.assertRaises(ValueError):
            evaluator.assemble_arm_body("nothing here\n", self.entry, "v0")

    def test_verify_v0_rejects_span_left_behind(self):
        with self.assertRaises(ValueError):
            evaluator.verify_arm_bytes(self.body, self.entry, "v0")

    def test_verify_vn_rejects_missing_variant(self):
        with self.assertRaises(ValueError):
            evaluator.verify_arm_bytes(self.body, self.entry, "v1")

    def test_verify_accepts_valid_assemblies(self):
        evaluator.verify_arm_bytes(
            evaluator.assemble_arm_body(self.body, self.entry, "v0"),
            self.entry,
            "v0",
        )
        evaluator.verify_arm_bytes(
            evaluator.assemble_arm_body(self.body, self.entry, "v2"),
            self.entry,
            "v2",
        )


class ShapeRunRecordTests(unittest.TestCase):
    """build_shape_run_record: the retrieval builder adapted — the arm
    key is recorded, skill-not-loaded fires for EVERY arm without a
    completed load (v0 included), and control-loaded-skill does not exist
    on this track."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self.tmp.name) / "ws"
        self.ws.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def _record(self, ev, arm="v0"):
        return evaluator.build_shape_run_record(
            ev, "the fixture", False, self.ws, arm, "demo-skill"
        )

    def test_arm_key_recorded(self):
        rec = self._record(EventStream(answer_parts=["a"]), arm="v2")
        self.assertEqual(rec["arm"], "v2")

    def test_v0_without_completed_load_signals(self):
        rec = self._record(EventStream(answer_parts=["a"]), arm="v0")
        self.assertIn("skill-not-loaded", rec["void_signals"])

    def test_no_control_loaded_skill_signal_on_any_arm(self):
        ev = EventStream(
            answer_parts=["a"],
            skill_loads=[{"name": "demo-skill", "status": "completed"}],
        )
        for arm in ("v0", "v1", "v3"):
            rec = self._record(ev, arm=arm)
            self.assertNotIn("control-loaded-skill", rec["void_signals"])

    def test_completed_load_no_signal(self):
        ev = EventStream(answer_parts=["a"], completed_load=True)
        rec = self._record(ev, arm="v1")
        self.assertNotIn("skill-not-loaded", rec["void_signals"])

    def test_timeout_is_a_field_not_a_void_signal(self):
        ev = EventStream(answer_parts=["complete answer"], completed_load=True)
        rec = evaluator.build_shape_run_record(
            ev, "the fixture", True, self.ws, "v0", "demo-skill"
        )
        self.assertTrue(rec["timeout"])
        self.assertEqual(rec["void_signals"], [])


class ShapeSuiteTests(unittest.TestCase):
    """cmd_shape_suite end-to-end with a fake strategy: entries x arms run
    strictly serialized (the multi-rule attribution invariant — never the
    retrieval track's arm-parallel structure), the workspace skill carries
    exactly one arm's byte state at a time and is restored afterwards, the
    per-run prompt is the bare fixture text, and skill= is passed on every
    arm. The results config records model/variant for attribution."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.agents_dir = self.root / "agents"
        self.agents_dir.mkdir()
        (self.agents_dir / "shape-evaluator.opencode.md").write_text(
            "---\nname: shape-evaluator\nmode: primary\n---\n"
            "load {{SKILL_NAME}}\n"
        )
        self.ws = self.root / "ws"
        skill_dir = self.ws / ".agents" / "skills" / "demo-skill"
        skill_dir.mkdir(parents=True)
        self.original = (
            FRONTMATTER + "# Demo\n\n" + SECTION_A + "\n\n" + SECTION_B + "\n"
        )
        (skill_dir / "SKILL.md").write_text(self.original)
        self.entries_path = self.root / "entries.json"
        self.out = self.root / "results.json"

    def tearDown(self):
        log = evaluator._Log.file
        evaluator._Log.file = None
        if log is not None:
            log.close()
        self.tmp.cleanup()

    class _FakeStrategy:
        """Records the workspace skill bytes at dispatch time so the test
        can assert the byte-state sequence; brief sleep lets rep batches
        overlap within an arm without ever overlapping across arms."""

        def __init__(self, skill_md: Path, original: str):
            self.skill_md = skill_md
            self.original = original
            self.lock = threading.Lock()
            self.states: list[str] = []
            self.queries: list[str] = []
            self.skills: list[str] = []
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
                snapshot = self.skill_md.read_text()
                with self.lock:
                    self.states.append(snapshot)
                    self.queries.append(query)
                    self.skills.append(skill if skill is not None else "")
                time.sleep(0.02)
                return (
                    EventStream(
                        answer_parts=["answer"],
                        completed_load=skill is not None,
                    ),
                    False,
                )
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
        fake = self._FakeStrategy(
            self.ws / ".agents" / "skills" / "demo-skill" / "SKILL.md",
            self.original,
        )
        args = self._args(**overrides)
        buf = io.StringIO()
        with mock_check_and_resolve(fake):
            with redirect_stdout(buf):
                rc = evaluator.cmd_shape_suite(args)
        return rc, buf.getvalue(), fake

    def test_entries_x_arms_serialized_and_bytes_restored(self):
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

        def label(snapshot):
            if "B variant" in snapshot:
                return ("b", "v1")
            if VARIANT_A1 in snapshot:
                return ("a", "v1")
            if SECTION_A not in snapshot:
                return ("a", "v0")
            if SECTION_B not in snapshot:
                return ("b", "v0")
            raise AssertionError("snapshot carries no arm byte state")

        labels = [label(s) for s in fake.states]
        # Entries x arms run strictly serialized: each (entry, arm) batch
        # is contiguous, and the workspace is restored between arms.
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
        # Every dispatch runs against an arm byte state: frontmatter
        # preserved byte-for-byte, body differing from the synced original.
        for snapshot in fake.states:
            self.assertTrue(snapshot.startswith(FRONTMATTER))
            self.assertNotEqual(snapshot, self.original)
        # v0 arms have their entry's section removed; v1 arms carry the
        # variant text in its place.
        for snapshot, (eid, arm) in zip(fake.states, labels):
            if arm == "v0":
                section = SECTION_A if eid == "a" else SECTION_B
                self.assertNotIn(section, snapshot)
            else:
                variant = VARIANT_A1 if eid == "a" else "B variant"
                self.assertIn(variant, snapshot)
        # Workspace restored to the original synced bytes after the suite.
        skill_md = self.ws / ".agents" / "skills" / "demo-skill" / "SKILL.md"
        self.assertEqual(skill_md.read_text(), self.original)

    def test_reps_within_one_arm_batch_parallelize(self):
        self._write_entries([shaping_entry(eid="a", section=SECTION_A)])
        rc, _, fake = self._run(reps=3)
        self.assertEqual(rc, 0)
        self.assertGreaterEqual(fake.max_active, 2)

    def test_prompt_is_bare_fixture_text_and_skill_passed(self):
        self._write_entries([shaping_entry(eid="a", section=SECTION_A)])
        rc, _, fake = self._run()
        self.assertEqual(rc, 0)
        for query in fake.queries:
            self.assertEqual(query, "write a component for a")
        for skill in fake.skills:
            self.assertEqual(skill, "demo-skill")

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

    def test_workspace_restored_on_abort(self):
        self._write_entries([shaping_entry(eid="a", section=SECTION_A)])
        args = self._args()

        class _Aborting(self._FakeStrategy):
            def execute(self, ws, agent, query, model, variant, skill=None):
                if len(self.states) == 1:
                    raise RuntimeError("boom")
                return super().execute(ws, agent, query, model, variant, skill)

        fake = _Aborting(
            self.ws / ".agents" / "skills" / "demo-skill" / "SKILL.md",
            self.original,
        )
        with mock_check_and_resolve(fake):
            with redirect_stdout(io.StringIO()):
                with redirect_stderr(io.StringIO()):
                    with self.assertRaises(RuntimeError):
                        evaluator.cmd_shape_suite(args)
        skill_md = self.ws / ".agents" / "skills" / "demo-skill" / "SKILL.md"
        self.assertEqual(skill_md.read_text(), self.original)


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
    """cmd_shape_suite pre-spend validation: every violation exits 1 with
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
        skill_dir = self.ws / ".agents" / "skills" / "demo-skill"
        skill_dir.mkdir(parents=True)
        self.skill_md = skill_dir / "SKILL.md"
        self.skill_md.write_text(FRONTMATTER + "# Demo\n\n" + SECTION_A + "\n")
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
                    return evaluator.cmd_shape_suite(args)

    def test_span_absent_from_body_exits_1(self):
        self.skill_md.write_text(FRONTMATTER + "# Demo\n\nother text\n")
        with self.assertRaises(SystemExit) as cm:
            self._run()
        self.assertEqual(cm.exception.code, 1)
        self.assertFalse(self.out.exists())

    def test_span_occurring_twice_exits_1(self):
        self.skill_md.write_text(
            FRONTMATTER + "# Demo\n\n" + SECTION_A + "\n\n" + SECTION_A + "\n"
        )
        with self.assertRaises(SystemExit) as cm:
            self._run()
        self.assertEqual(cm.exception.code, 1)
        self.assertFalse(self.out.exists())

    def test_span_overlapping_frontmatter_never_matched(self):
        # The section text exists ONLY inside the frontmatter block; the
        # drift gate strips frontmatter first, so occurrences in the body
        # are 0 and the campaign aborts pre-spend.
        self.skill_md.write_text(
            f"---\nname: demo-skill\ndescription: {SECTION_A}\n---\n# Demo\n"
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
                        evaluator.cmd_shape_suite(args)
        self.assertEqual(cm.exception.code, 1)
        self.assertFalse(self.out.exists())

    def test_agent_file_with_model_pin_exits_1(self):
        (self.agents_dir / "shape-evaluator.opencode.md").write_text(
            "---\nname: shape-evaluator\nmodel: gpt-x\n---\nbody\n"
        )
        with self.assertRaises(SystemExit) as cm:
            self._run()
        self.assertEqual(cm.exception.code, 1)
        self.assertFalse(self.out.exists())

    def test_agent_file_name_mismatch_exits_1(self):
        (self.agents_dir / "shape-evaluator.opencode.md").write_text(
            "---\nname: someone-else\n---\nbody\n"
        )
        with self.assertRaises(SystemExit) as cm:
            self._run()
        self.assertEqual(cm.exception.code, 1)

    def test_arm_not_defined_by_entry_exits_1(self):
        with self.assertRaises(SystemExit) as cm:
            args = argparse.Namespace(
                harness="opencode",
                skill="demo-skill",
                agents_dir=str(self.agents_dir),
                workspace=str(self.ws),
                entries=str(self.entries_path),
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
                        evaluator.cmd_shape_suite(args)
        self.assertEqual(cm.exception.code, 1)

    def test_invalid_fixture_key_exits_1(self):
        with self.assertRaises(SystemExit) as cm:
            args = argparse.Namespace(
                harness="opencode",
                skill="demo-skill",
                agents_dir=str(self.agents_dir),
                workspace=str(self.ws),
                entries=str(self.entries_path),
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
                        evaluator.cmd_shape_suite(args)
        self.assertEqual(cm.exception.code, 1)

    def test_reps_below_one_exits_1(self):
        with self.assertRaises(SystemExit) as cm:
            args = argparse.Namespace(
                harness="opencode",
                skill="demo-skill",
                agents_dir=str(self.agents_dir),
                workspace=str(self.ws),
                entries=str(self.entries_path),
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
                        evaluator.cmd_shape_suite(args)
        self.assertEqual(cm.exception.code, 1)


class ShapeScoredCheckTests(unittest.TestCase):
    """cmd_shape_scored_check: multi-results union with dedupe, adoption
    discipline (adopted_arm rules), the pattern restraint-gate rule, and
    the record-step count gate."""

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
            return evaluator.cmd_shape_scored_check(args)

    def test_union_dedupe_id_in_two_files_scored_once(self):
        rc = self._check(
            [
                self._entry("a", result="adopted", adopted_arm="v2"),
                self._entry(
                    "p",
                    result="adopted",
                    adopted_arm="v1",
                    restraint_gate="pass",
                ),
            ]
        )
        self.assertEqual(rc, 0)

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
            results=[self.results[0], str(bad)],
            scored=str(self.scored),
            adopted=None,
            no_failure=None,
            unresolved=None,
            voids=None,
        )
        with redirect_stdout(io.StringIO()):
            self.assertEqual(evaluator.cmd_shape_scored_check(args), 1)

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

    def test_count_gate_matching_passes(self):
        rc = self._check(
            [
                self._entry("a", result="adopted", adopted_arm="v2"),
                self._entry("p"),
            ],
            adopted=1,
            no_failure=1,
            unresolved=0,
            voids=0,
        )
        self.assertEqual(rc, 0)

    def test_count_gate_mismatch_rejected(self):
        rc = self._check(
            [
                self._entry("a", result="adopted", adopted_arm="v2"),
                self._entry("p"),
            ],
            adopted=2,
            no_failure=0,
            unresolved=0,
            voids=0,
        )
        self.assertEqual(rc, 1)

    def test_partial_count_gate_rejected(self):
        rc = self._check([self._entry("a"), self._entry("p")], adopted=0)
        self.assertEqual(rc, 1)


class ShapeRecordTests(unittest.TestCase):
    """record --track shape-test: the shape vocabulary lands under the
    shape-test manifest key, the retrieval vocabulary is rejected on this
    track, and omitting --track keeps the back-compatible retrieval-test
    default."""

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
        with redirect_stdout(io.StringIO()):
            return evaluator.cmd_record(args)

    def test_shape_track_writes_shape_key_and_preserves_others(self):
        self.manifest.write_text(
            json.dumps(
                {
                    "skill": "test-skill",
                    "trigger-test": {"date": "old", "score": 0.5},
                    "retrieval-test": {"date": "old", "passes": 1},
                }
            )
        )
        rc = self._record()
        self.assertEqual(rc, 0)
        data = json.loads(self.manifest.read_text())
        self.assertEqual(data["trigger-test"]["score"], 0.5)
        self.assertEqual(data["retrieval-test"]["passes"], 1)
        entry = data["shape-test"]
        self.assertEqual(
            set(entry),
            {
                "date",
                "checksum",
                "adopted",
                "no-failure",
                "unresolved",
                "voids",
                "campaign",
            },
        )
        self.assertEqual(entry["adopted"], 2)
        self.assertEqual(entry["no-failure"], 1)
        self.assertEqual(entry["voids"], 0)
        self.assertEqual(
            entry["checksum"], evaluator.hash_skill_dir(self.skill_dir)
        )

    def test_missing_shape_count_rejected(self):
        rc = self._record(voids=None)
        self.assertEqual(rc, 1)
        self.assertFalse(self.manifest.exists())

    def test_retrieval_vocabulary_on_shape_track_rejected(self):
        rc = self._record(passes=1)
        self.assertEqual(rc, 1)
        self.assertFalse(self.manifest.exists())

    def test_shape_count_on_retrieval_track_rejected(self):
        rc = self._record(
            track="retrieval-test",
            passes=1,
            fails=0,
            gaps=0,
        )
        self.assertEqual(rc, 1)

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
            no_failure=None,
            unresolved=None,
            ablations=None,
            campaign=None,
            date="2026-09-13",
        )
        # No 'track' attribute at all — the phase-1 back-compat path.
        with redirect_stdout(io.StringIO()):
            rc = evaluator.cmd_record(args)
        self.assertEqual(rc, 0)
        data = json.loads(self.manifest.read_text())
        self.assertIn("retrieval-test", data)
        self.assertNotIn("shape-test", data)


class ShapeEvidenceTests(unittest.TestCase):
    """cmd_shape_evidence: extraction with marker triage counts, arm and
    entry filters, and rejection of malformed results."""

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
            results=str(self.results), entry=None, arm=None
        )
        for k, v in overrides.items():
            setattr(args, k, v)
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = evaluator.cmd_shape_evidence(args)
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

    def test_malformed_results_rejected(self):
        self.results.write_text('{"entries": "nope"}')
        rc, _ = self._run()
        self.assertEqual(rc, 1)

    def test_missing_results_file_rejected(self):
        rc, _ = self._run(results=str(self.root / "nope.json"))
        self.assertEqual(rc, 1)


class MarkerTriageTests(unittest.TestCase):
    def test_counts_lines_matching_token(self):
        answer = "a style={{x}}\nb plain\nc style={{y}}\n"
        counts = evaluator.marker_triage_counts(
            answer, {"inline_style": "style=\\{\\{"}
        )
        self.assertEqual(counts, {"inline_style": 2})

    def test_empty_answer_zeroes_all_markers(self):
        counts = evaluator.marker_triage_counts(
            "", {"inline_style": "style", "other": "x"}
        )
        self.assertEqual(counts, {"inline_style": 0, "other": 0})


if __name__ == "__main__":
    unittest.main()
