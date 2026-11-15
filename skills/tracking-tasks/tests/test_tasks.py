"""Phase 1 tests for skills/tracking-tasks/scripts/tasks.py.

Covers the internal machinery: YAML subset parser/emitter, config
discovery, author resolution, slug generation, next-number computation,
ID resolution, template fidelity, and the CLI skeleton (-h, stubs).
"""

# The tasks module is loaded via sys.path below (no installed package).
# pyright: reportMissingImports=false

import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import tasks  # noqa: E402

TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"


class ProjectFixture(unittest.TestCase):
    """Temp project dir + in-process CLI runner."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.project = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def run_cli(self, *argv):
        """Run tasks.main in-process; returns (code, stdout, stderr)."""
        out, err = io.StringIO(), io.StringIO()
        code = 0
        with redirect_stdout(out), redirect_stderr(err):
            try:
                code = tasks.main([str(a) for a in argv], cwd=self.project)
            except SystemExit as exc:
                code = exc.code if isinstance(exc.code, int) else 1
        return code, out.getvalue(), err.getvalue()


class TestParseYamlSubset(unittest.TestCase):
    def test_plain_scalars(self):
        data = tasks.parse_yaml_subset("a: one\nb: two\n")
        self.assertEqual(data, {"a": "one", "b": "two"})

    def test_empty_value(self):
        self.assertEqual(tasks.parse_yaml_subset("a:\n"), {"a": ""})

    def test_double_quoted_with_escapes(self):
        data = tasks.parse_yaml_subset(r'a: "x: y # z \"q\" n\n"')
        self.assertEqual(data["a"], 'x: y # z "q" n\n')

    def test_single_quoted_no_escapes(self):
        data = tasks.parse_yaml_subset("a: 'it''s \\n literal'")
        self.assertEqual(data["a"], "it's \\n literal")

    def test_colon_and_hash_inside_quotes(self):
        data = tasks.parse_yaml_subset('a: "x: y" # comment')
        self.assertEqual(data["a"], "x: y")

    def test_comment_stripped_outside_quotes(self):
        data = tasks.parse_yaml_subset("a: value  # trailing\n# full line\n")
        self.assertEqual(data, {"a": "value"})

    def test_hash_without_space_is_still_a_comment(self):
        # Subset rule: '#' outside quotes always starts a comment.
        data = tasks.parse_yaml_subset("a: value#cut")
        self.assertEqual(data, {"a": "value"})

    def test_plain_value_may_contain_colon_when_spaced(self):
        data = tasks.parse_yaml_subset("a: 10:30")
        self.assertEqual(data["a"], "10:30")

    def test_inline_list(self):
        data = tasks.parse_yaml_subset("tags: [cli, auth, 'x, y']")
        self.assertEqual(data["tags"], ["cli", "auth", "x, y"])

    def test_empty_inline_list(self):
        self.assertEqual(tasks.parse_yaml_subset("tags: []"), {"tags": []})

    def test_frontmatter_marker_skipped(self):
        data = tasks.parse_yaml_subset("---\na: one\n---\n")
        self.assertEqual(data, {"a": "one"})

    def test_rejects_indented_nesting(self):
        with self.assertRaises(tasks.YamlError):
            tasks.parse_yaml_subset("a:\n  b: c\n")

    def test_rejects_dash_lines(self):
        with self.assertRaises(tasks.YamlError):
            tasks.parse_yaml_subset("a: one\n- b\n")

    def test_rejects_duplicate_keys(self):
        with self.assertRaises(tasks.YamlError):
            tasks.parse_yaml_subset("a: one\na: two\n")

    def test_rejects_unterminated_quote(self):
        with self.assertRaises(tasks.YamlError):
            tasks.parse_yaml_subset('a: "unterminated')

    def test_rejects_bad_escape(self):
        with self.assertRaises(tasks.YamlError):
            tasks.parse_yaml_subset(r'a: "bad \q escape"')


class TestEmitYaml(unittest.TestCase):
    def test_canonical_order_required_then_optional(self):
        fields = {
            "tags": ["cli"],
            "state": "draft",
            "title": "T",
            "type": "task",
            "created": "2024-01-01",
            "updated": "2024-01-01",
            "author": "A",
        }
        emitted = tasks.emit_yaml(fields)
        keys = [line.split(":", 1)[0] for line in emitted.splitlines()]
        self.assertEqual(
            keys,
            [
                "title",
                "type",
                "state",
                "author",
                "created",
                "updated",
                "tags",
            ],
        )

    def test_unknown_keys_after_canonical_sorted(self):
        fields = {"title": "T", "zzz": "1", "aaa": "2"}
        emitted = tasks.emit_yaml(fields)
        keys = [line.split(":", 1)[0] for line in emitted.splitlines()]
        self.assertEqual(keys, ["title", "aaa", "zzz"])

    def test_plain_scalars_unquoted(self):
        self.assertEqual(tasks.emit_yaml({"a": "hello"}), "a: hello\n")

    def test_quoting_triggers(self):
        cases = {
            "a: b": '"a: b"',
            "a#b": '"a#b"',
            "a[b]": '"a[b]"',
            " padded ": '" padded "',
            "": '""',
            "'lead": '"\'lead"',
        }
        for value, rendered in cases.items():
            with self.subTest(value=value):
                self.assertEqual(
                    tasks.emit_yaml({"k": value}), f"k: {rendered}\n"
                )

    def test_double_quote_escaping_round_trip(self):
        value = 'say "hi" \\ end'
        emitted = tasks.emit_yaml({"k": value})
        self.assertEqual(tasks.parse_yaml_subset(emitted)["k"], value)

    def test_tags_emitted_inline(self):
        emitted = tasks.emit_yaml({"tags": ["a", "b c"]})
        self.assertEqual(emitted, "tags: [a, b c]\n")

    def test_tags_items_quoted_when_required(self):
        emitted = tasks.emit_yaml({"tags": ["a:b", "c#d"]})
        self.assertEqual(emitted, 'tags: ["a:b", "c#d"]\n')

    def test_empty_list(self):
        self.assertEqual(tasks.emit_yaml({"tags": []}), "tags: []\n")

    def test_round_trip_tricky_fields(self):
        fields = {
            "title": 'Fix: login "redirect" #2',
            "type": "bug",
            "state": "open",
            "author": "A B",
            "created": "2024-01-01",
            "updated": "2024-02-03",
            "reason": "contains: colon and # hash",
            "tags": ["x", "y: z"],
        }
        self.assertEqual(
            tasks.parse_yaml_subset(tasks.emit_yaml(fields)), fields
        )


class TestTemplates(unittest.TestCase):
    def _read(self, name):
        return (TEMPLATES_DIR / name).read_text(encoding="utf-8")

    def test_all_templates_exist(self):
        for name in ("task.md", "bug.md", "subtask.md"):
            self.assertTrue((TEMPLATES_DIR / name).is_file(), name)

    def test_task_template(self):
        text = self._read("task.md")
        self.assertTrue(text.startswith("---\n"))
        self.assertIn('title: "{{title}}"', text)
        self.assertIn("type: task", text)
        self.assertIn('author: "{{author}}"', text)
        self.assertIn("created: {{date}}", text)
        self.assertIn("updated: {{date}}", text)
        self.assertIn("\n# {{title}}\n", text)
        for section in (
            "## Why",
            "## How",
            "## Definition of Done",
            "## Links",
        ):
            self.assertIn(section, text)
        self.assertNotIn("{{parent}}", text)

    def test_bug_template(self):
        text = self._read("bug.md")
        self.assertTrue(text.startswith("---\n"))
        self.assertIn("type: bug", text)
        for section in (
            "# {{title}}",
            "## Summary",
            "## Steps to Reproduce",
            "## Expected Behavior",
            "## Actual Behavior",
            "## Environment",
            "## Links",
        ):
            self.assertIn(section, text)

    def test_subtask_template(self):
        text = self._read("subtask.md")
        self.assertTrue(text.startswith("---\n"))
        self.assertIn("type: subtask", text)
        self.assertIn('parent: "{{parent}}"', text)
        self.assertIn("## Description", text)
        self.assertIn("## Definition of Done", text)

    def test_frontmatter_is_parseable_after_substitution(self):
        for name in ("task.md", "bug.md", "subtask.md"):
            text = self._read(name)
            front = text.split("---\n", 2)[1]
            filled = (
                front.replace("{{title}}", "T")
                .replace("{{author}}", "A")
                .replace("{{date}}", "2024-01-01")
                .replace("{{parent}}", "001_x.md")
            )
            with self.subTest(name=name):
                self.assertIsInstance(tasks.parse_yaml_subset(filled), dict)


class TestDiscoverConfig(ProjectFixture):
    def test_defaults_when_no_config(self):
        cfg = tasks.discover_config(None, None, self.project)
        self.assertIsNone(cfg.path)
        self.assertEqual(cfg.artifacts_dir, self.project / "tasks")
        self.assertIsNone(cfg.author)

    def test_upward_walk_finds_config(self):
        (self.project / ".tasks.yaml").write_text("artifacts_dir: issues\n")
        nested = self.project / "sub" / "dir"
        nested.mkdir(parents=True)
        cfg = tasks.discover_config(None, None, nested)
        self.assertEqual(cfg.path, self.project / ".tasks.yaml")
        # Resolved relative to the config file's dir (§2).
        self.assertEqual(cfg.artifacts_dir, self.project / "issues")

    def test_flag_beats_walk(self):
        (self.project / ".tasks.yaml").write_text("artifacts_dir: walked\n")
        other = self.project / "other"
        other.mkdir()
        flagged = other / ".tasks.yaml"
        flagged.write_text("artifacts_dir: flagged\n")
        cfg = tasks.discover_config(str(flagged), None, self.project)
        self.assertEqual(cfg.path, flagged)
        self.assertEqual(cfg.artifacts_dir, other / "flagged")

    def test_missing_flagged_config_is_error(self):
        with self.assertRaises(tasks.TasksError):
            tasks.discover_config(
                str(self.project / "nope.yaml"), None, self.project
            )

    def test_dir_flag_overrides(self):
        (self.project / ".tasks.yaml").write_text("artifacts_dir: issues\n")
        cfg = tasks.discover_config(None, "elsewhere", self.project)
        self.assertEqual(cfg.artifacts_dir, self.project / "elsewhere")
        absolute = self.project / "abs-dir"
        cfg = tasks.discover_config(None, str(absolute), self.project)
        self.assertEqual(cfg.artifacts_dir, absolute)

    def test_config_author(self):
        (self.project / ".tasks.yaml").write_text(
            "artifacts_dir: tasks\nauthor: Ada Lovelace\n"
        )
        cfg = tasks.discover_config(None, None, self.project)
        self.assertEqual(cfg.author, "Ada Lovelace")


class TestResolveAuthor(ProjectFixture):
    def test_flag_beats_config(self):
        author = tasks.resolve_author(
            "Flag Author", "Config Author", self.project
        )
        self.assertEqual(author, "Flag Author")

    def test_config_used_when_no_flag(self):
        author = tasks.resolve_author(None, "Config Author", self.project)
        self.assertEqual(author, "Config Author")

    def test_git_fallback(self):
        with mock.patch.object(
            tasks, "_git_config_user_name", return_value="Git Author"
        ):
            author = tasks.resolve_author(None, None, self.project)
        self.assertEqual(author, "Git Author")

    def test_user_env_fallback(self):
        with mock.patch.object(
            tasks, "_git_config_user_name", return_value=None
        ):
            with mock.patch.dict(os.environ, {"USER": "env-user"}):
                author = tasks.resolve_author(None, None, self.project)
        self.assertEqual(author, "env-user")

    def test_all_fail_mentions_author_flag(self):
        with mock.patch.object(
            tasks, "_git_config_user_name", return_value=None
        ):
            with mock.patch.dict(os.environ, {}, clear=True):
                with self.assertRaises(tasks.TasksError) as ctx:
                    tasks.resolve_author(None, None, self.project)
        self.assertIn("--author", str(ctx.exception))


class TestSlugify(unittest.TestCase):
    def test_spec_example(self):
        self.assertEqual(
            tasks.slugify("Fix: Login Redirect!"), "fix-login-redirect"
        )

    def test_runs_collapse_and_edges_stripped(self):
        self.assertEqual(
            tasks.slugify("  --Weird__ title-- "), "weird__-title"
        )

    def test_underscores_and_hyphens_preserved(self):
        self.assertEqual(tasks.slugify("a_b-c d"), "a_b-c-d")

    def test_only_invalid_chars(self):
        self.assertEqual(tasks.slugify("!!!"), "")


class TestNextNumber(ProjectFixture):
    def test_missing_dir_is_empty(self):
        self.assertEqual(tasks.next_number(self.project / "tasks"), 1)

    def test_empty_dir(self):
        d = self.project / "tasks"
        d.mkdir()
        self.assertEqual(tasks.next_number(d), 1)

    def test_gap_never_backfilled(self):
        d = self.project / "tasks"
        d.mkdir()
        (d / "001_a.md").write_text("")
        (d / "003_c.md").write_text("")
        self.assertEqual(tasks.next_number(d), 4)

    def test_stray_files_ignored(self):
        d = self.project / "tasks"
        d.mkdir()
        (d / "notes.txt").write_text("")
        (d / "99_two-digits.md").write_text("")
        (d / "abc.md").write_text("")
        self.assertEqual(tasks.next_number(d), 1)

    def test_max_999_is_hard_error(self):
        d = self.project / "tasks"
        d.mkdir()
        (d / "999_last.md").write_text("")
        with self.assertRaises(tasks.TasksError):
            tasks.next_number(d)


class TestResolveId(ProjectFixture):
    def setUp(self):
        super().setUp()
        self.tasks_dir = self.project / "tasks"
        self.tasks_dir.mkdir()
        (self.tasks_dir / "001_alpha.md").write_text("a")
        (self.tasks_dir / "002_gamma.md").write_text("g")
        (self.tasks_dir / "003_beta.md").write_text("b")

    def test_exact_filename(self):
        path = tasks.resolve_id(self.tasks_dir, "002_gamma.md")
        self.assertEqual(path.name, "002_gamma.md")

    def test_three_digit_number(self):
        path = tasks.resolve_id(self.tasks_dir, "003")
        self.assertEqual(path.name, "003_beta.md")

    def test_unique_prefix(self):
        path = tasks.resolve_id(self.tasks_dir, "001_al")
        self.assertEqual(path.name, "001_alpha.md")

    def test_ambiguous_prefix_lists_matches(self):
        with self.assertRaises(tasks.TasksError) as ctx:
            tasks.resolve_id(self.tasks_dir, "00")
        message = str(ctx.exception)
        self.assertIn("ambiguous", message)
        for name in ("001_alpha.md", "002_gamma.md", "003_beta.md"):
            self.assertIn(name, message)

    def test_unknown_number(self):
        with self.assertRaises(tasks.TasksError):
            tasks.resolve_id(self.tasks_dir, "099")

    def test_unknown_prefix(self):
        with self.assertRaises(tasks.TasksError):
            tasks.resolve_id(self.tasks_dir, "zzz")

    def test_missing_dir_suggests_init(self):
        with self.assertRaises(tasks.TasksError) as ctx:
            tasks.resolve_id(self.project / "absent", "001")
        self.assertIn("init", str(ctx.exception))


class TestCliSkeleton(ProjectFixture):
    def test_top_level_help(self):
        code, out, err = self.run_cli("-h")
        self.assertEqual(code, 0)
        self.assertIn("usage:", out)
        self.assertEqual(err, "")

    def test_subcommand_help(self):
        for cmd in (
            "init",
            "new",
            "list",
            "show",
            "set-state",
            "set",
            "validate",
            "links",
            "grep",
            "next-id",
        ):
            with self.subTest(cmd=cmd):
                code, out, _ = self.run_cli(cmd, "-h")
                self.assertEqual(code, 0)
                self.assertIn("usage:", out)

    def test_no_subcommand_is_usage_error(self):
        code, out, err = self.run_cli()
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("usage:", err)

    def test_stub_command_not_implemented(self):
        code, out, err = self.run_cli("next-id")
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("tasks.py: error:", err)
        self.assertIn("not implemented", err)

    def test_stub_error_goes_to_stderr(self):
        _, out, err = self.run_cli("show", "001_x.md")
        self.assertEqual(out, "")
        self.assertTrue(err.startswith("tasks.py: error:"))


if __name__ == "__main__":
    unittest.main()
