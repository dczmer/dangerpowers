"""Tests for skills/tracking-tasks/scripts/tasks.py.

Covers the internal machinery: YAML subset parser/emitter, config
discovery, author resolution, slug generation, next-number computation,
ID resolution, template fidelity, the CLI skeleton (-h), and the
commands: init/new/list/show/next-id, set-state/set, and
validate/links/grep.
"""

# The tasks module is loaded via sys.path below (no installed package).
# pyright: reportMissingImports=false

import datetime
import io
import os
import subprocess
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
        tasks_dir = self.project / "tasks"
        tasks_dir.mkdir()
        (tasks_dir / "tasks.yaml").write_text("artifacts_dir: issues\n")
        nested = self.project / "sub" / "dir"
        nested.mkdir(parents=True)
        cfg = tasks.discover_config(None, None, nested)
        self.assertEqual(cfg.path, tasks_dir / "tasks.yaml")
        # Resolved relative to the project root (the config's grandparent),
        # not the config file's dir.
        self.assertEqual(cfg.artifacts_dir, self.project / "issues")

    def test_flag_beats_walk(self):
        tasks_dir = self.project / "tasks"
        tasks_dir.mkdir()
        (tasks_dir / "tasks.yaml").write_text("artifacts_dir: walked\n")
        other = self.project / "other"
        other.mkdir()
        flagged = other / "tasks.yaml"
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
        tasks_dir = self.project / "tasks"
        tasks_dir.mkdir()
        (tasks_dir / "tasks.yaml").write_text("artifacts_dir: issues\n")
        cfg = tasks.discover_config(None, "elsewhere", self.project)
        self.assertEqual(cfg.artifacts_dir, self.project / "elsewhere")
        absolute = self.project / "abs-dir"
        cfg = tasks.discover_config(None, str(absolute), self.project)
        self.assertEqual(cfg.artifacts_dir, absolute)

    def test_config_author(self):
        tasks_dir = self.project / "tasks"
        tasks_dir.mkdir()
        (tasks_dir / "tasks.yaml").write_text(
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

    def test_slug_capped_at_30_characters(self):
        slug = tasks.slugify("a" * 50)
        self.assertEqual(slug, "a" * 30)

    def test_exactly_30_chars_unchanged(self):
        title = "a" * 28 + " b"
        self.assertEqual(tasks.slugify(title), "a" * 28 + "-b")

    def test_cap_trims_dangling_separator(self):
        # 29 chars then a space: truncation lands on the collapsed '-',
        # which must be stripped so the slug never ends with '-'.
        slug = tasks.slugify("a" * 29 + " b" + "c" * 20)
        self.assertEqual(slug, "a" * 29)
        self.assertFalse(slug.endswith("-"))


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

    def test_installed_entries_are_not_task_ids(self):
        # tasks.py, tasks.yaml, and the templates/ dir live in the
        # artifacts dir but must never resolve as task references.
        for name in ("tasks.py", "tasks.yaml"):
            (self.tasks_dir / name).write_text("x", encoding="utf-8")
        (self.tasks_dir / "templates").mkdir()
        for arg in ("tasks.py", "tasks.yaml", "tasks"):
            with self.subTest(arg=arg):
                with self.assertRaises(tasks.TasksError):
                    tasks.resolve_id(self.tasks_dir, arg)
        # Real task references still resolve alongside the entries.
        self.assertEqual(
            tasks.resolve_id(self.tasks_dir, "001").name, "001_alpha.md"
        )


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

    def test_error_goes_to_stderr(self):
        _, out, err = self.run_cli("show", "001_x.md")
        self.assertEqual(out, "")
        self.assertTrue(err.startswith("tasks.py: error:"))


class TestInit(ProjectFixture):
    def test_creates_config_and_artifacts_dir(self):
        code, out, err = self.run_cli("init")
        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        config = self.project / "tasks" / "tasks.yaml"
        self.assertTrue(config.is_file())
        self.assertTrue((self.project / "tasks").is_dir())
        data = tasks.parse_yaml_subset(config.read_text(encoding="utf-8"))
        self.assertEqual(data, {"artifacts_dir": "tasks"})

    def test_installs_script_and_templates(self):
        code, out, err = self.run_cli("init")
        self.assertEqual((code, err), (0, ""))
        script = self.project / "tasks" / "tasks.py"
        self.assertTrue(script.is_file())
        # Byte-identical copy of the running script, made executable.
        self.assertEqual(
            script.read_bytes(),
            Path(tasks.__file__).read_bytes(),
        )
        self.assertTrue(os.access(script, os.X_OK))
        for name in ("task.md", "bug.md", "subtask.md"):
            installed = self.project / "tasks" / "templates" / name
            self.assertEqual(
                installed.read_bytes(), (TEMPLATES_DIR / name).read_bytes()
            )
        self.assertIn("tasks/tasks.py -h", out)

    def test_second_run_is_noop_success(self):
        self.assertEqual(self.run_cli("init")[0], 0)
        first = (self.project / "tasks" / "tasks.yaml").read_text(
            encoding="utf-8"
        )
        code, out, err = self.run_cli("init")
        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        self.assertEqual(
            (self.project / "tasks" / "tasks.yaml").read_text(
                encoding="utf-8"
            ),
            first,
        )
        self.assertIn("up to date", out)

    def test_rerun_updates_tampered_install(self):
        self.assertEqual(self.run_cli("init")[0], 0)
        script = self.project / "tasks" / "tasks.py"
        tampered = b"# tampered\n" + script.read_bytes()
        script.write_bytes(tampered)
        template = self.project / "tasks" / "templates" / "task.md"
        template.write_text("tampered\n", encoding="utf-8")
        code, out, err = self.run_cli("init")
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(
            script.read_bytes(), Path(tasks.__file__).read_bytes()
        )
        self.assertEqual(
            template.read_bytes(), (TEMPLATES_DIR / "task.md").read_bytes()
        )
        self.assertIn("installed", out)

    def test_installed_copy_runs_standalone(self):
        """The installed script works with no skill dir in the picture:
        init, then new (templates resolve from the installed location)."""
        self.assertEqual(self.run_cli("init", "--author", "Ada")[0], 0)
        script = self.project / "tasks" / "tasks.py"
        env = dict(os.environ, PYTHONPATH="")
        proc = subprocess.run(
            [sys.executable, str(script), "new", "task", "Standalone"],
            cwd=self.project,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        created = self.project / "tasks" / "001_standalone.md"
        self.assertTrue(created.is_file())
        # Re-init from the installed copy: no self-copy, no error.
        proc = subprocess.run(
            [sys.executable, str(script), "init"],
            cwd=self.project,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("already the running script", proc.stdout)

    def test_legacy_config_is_moved(self):
        legacy = self.project / ".tasks.yaml"
        legacy.write_text("artifacts_dir: tasks\nauthor: Bob\n")
        code, out, err = self.run_cli("init")
        self.assertEqual((code, err), (0, ""))
        config = self.project / "tasks" / "tasks.yaml"
        self.assertFalse(legacy.exists())
        self.assertEqual(
            config.read_text(encoding="utf-8"),
            "artifacts_dir: tasks\nauthor: Bob\n",
        )
        self.assertIn("moved", out)

    def test_legacy_config_kept_when_new_config_exists(self):
        legacy = self.project / ".tasks.yaml"
        legacy.write_text("author: Old\n", encoding="utf-8")
        tasks_dir = self.project / "tasks"
        tasks_dir.mkdir()
        (tasks_dir / "tasks.yaml").write_text("author: New\n")
        code, out, err = self.run_cli("init")
        self.assertEqual(code, 0)
        self.assertTrue(legacy.exists())
        self.assertEqual(
            (tasks_dir / "tasks.yaml").read_text(encoding="utf-8"),
            "author: New\n",
        )
        self.assertIn("still exists", err)

    def test_author_and_dir_flags(self):
        code, _, _ = self.run_cli(
            "init", "--author", "Ada Lovelace", "--dir", "issues"
        )
        self.assertEqual(code, 0)
        data = tasks.parse_yaml_subset(
            (self.project / "tasks" / "tasks.yaml").read_text(encoding="utf-8")
        )
        self.assertEqual(data["author"], "Ada Lovelace")
        self.assertEqual(data["artifacts_dir"], "issues")
        self.assertTrue((self.project / "issues").is_dir())

    def test_existing_config_not_overwritten(self):
        tasks_dir = self.project / "tasks"
        tasks_dir.mkdir()
        (tasks_dir / "tasks.yaml").write_text(
            "artifacts_dir: custom\n", encoding="utf-8"
        )
        code, _, _ = self.run_cli("init", "--author", "Ada")
        self.assertEqual(code, 0)
        self.assertEqual(
            (tasks_dir / "tasks.yaml").read_text(encoding="utf-8"),
            "artifacts_dir: custom\n",
        )
        self.assertTrue((self.project / "custom").is_dir())

    def test_config_flag_creates_parent_dirs(self):
        nested = self.project / "nested" / "dir" / "tasks.yaml"
        code, _, err = self.run_cli("init", "--config", str(nested))
        self.assertEqual((code, err), (0, ""))
        self.assertTrue(nested.is_file())
        self.assertTrue((self.project / "nested" / "dir" / "tasks").is_dir())


class TestNew(ProjectFixture):
    def setUp(self):
        super().setUp()
        code, _, err = self.run_cli("init", "--author", "Ada")
        self.assertEqual((code, err), (0, ""))

    def _new(self, *argv) -> tuple:
        """Returns (code, created-path-or-placeholder, stderr)."""
        code, out, err = self.run_cli("new", *argv)
        # On failure stdout is empty; the placeholder is never used there.
        return code, Path(out.strip()), err

    def test_new_task_fills_template(self):
        code, path, err = self._new("task", "Fix: Login Redirect!")
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(path.name, "001_fix-login-redirect.md")
        self.assertTrue(path.is_file())
        fields, body = tasks.read_task(path)
        self.assertEqual(fields["title"], "Fix: Login Redirect!")
        self.assertEqual(fields["type"], "task")
        self.assertEqual(fields["state"], "draft")
        self.assertEqual(fields["author"], "Ada")
        today = datetime.date.today().isoformat()  # noqa: DTZ011
        self.assertEqual(fields["created"], today)
        self.assertEqual(fields["updated"], today)
        self.assertIn("\n# Fix: Login Redirect!\n", body)
        for section in ("## Why", "## How", "## Definition of Done"):
            self.assertIn(section, body)

    def test_global_numbering_across_types(self):
        _, first, _ = self._new("task", "Alpha")
        _, second, _ = self._new("bug", "Beta")
        _, third, _ = self._new("subtask", "Gamma", "--parent", first.name)
        self.assertEqual(
            (first.name, second.name, third.name),
            ("001_alpha.md", "002_beta.md", "003_gamma.md"),
        )
        fields, _ = tasks.read_task(third)
        self.assertEqual(fields["type"], "subtask")
        self.assertEqual(fields["parent"], "001_alpha.md")

    def test_subtask_requires_parent(self):
        code, _, err = self._new("subtask", "Orphan")
        self.assertEqual(code, 1)
        self.assertIn("tasks.py: error:", err)
        self.assertIn("--parent", err)

    def test_subtask_parent_must_exist(self):
        code, _, err = self._new("subtask", "X", "--parent", "099_nope.md")
        self.assertEqual(code, 1)
        self.assertIn("tasks.py: error:", err)

    def test_subtask_parent_cannot_be_subtask(self):
        _, task_path, _ = self._new("task", "Real")
        _, sub_path, _ = self._new(
            "subtask", "Child", "--parent", task_path.name
        )
        code, _, err = self._new(
            "subtask", "Grandchild", "--parent", sub_path.name
        )
        self.assertEqual(code, 1)
        self.assertIn("tasks.py: error:", err)
        self.assertIn("task or bug", err)

    def test_parent_rejected_for_task(self):
        code, _, err = self._new("task", "X", "--parent", "001_a.md")
        self.assertEqual(code, 1)
        self.assertIn("tasks.py: error:", err)

    def test_slug_flag_bypasses_generation(self):
        _, path, _ = self._new("task", "Weird Title!", "--slug", "my-slug")
        self.assertEqual(path.name, "001_my-slug.md")

    def test_slug_collision_is_error(self):
        self._new("task", "First", "--slug", "same")
        # Numbers are unique, so force a filename collision by reusing the
        # number the CLI would otherwise assign (concurrent-new check).
        with mock.patch.object(tasks, "next_number", return_value=1):
            code, _, err = self._new("task", "Second", "--slug", "same")
        self.assertEqual(code, 1)
        self.assertIn("tasks.py: error:", err)
        self.assertIn("collision", err)

    def test_same_slug_different_numbers_is_allowed(self):
        _, first, _ = self._new("task", "First", "--slug", "same")
        _, second, _ = self._new("task", "Second", "--slug", "same")
        self.assertEqual(
            (first.name, second.name), ("001_same.md", "002_same.md")
        )

    def test_invalid_slug_rejected(self):
        code, _, err = self._new("task", "X", "--slug", "bad slug!")
        self.assertEqual(code, 1)
        self.assertIn("tasks.py: error:", err)

    def test_overlong_explicit_slug_rejected(self):
        code, _, err = self._new("task", "X", "--slug", "a" * 31)
        self.assertEqual(code, 1)
        self.assertIn("tasks.py: error:", err)
        self.assertIn("30", err)

    def test_long_title_slug_capped_at_30(self):
        _, path, _ = self._new("task", "word " * 20)
        slug = path.name.removeprefix("001_").removesuffix(".md")
        # 30-char prefix keeps 6 words and ends on the separator
        # after them, which the cap strips: 29 chars.
        self.assertEqual(slug, "word-word-word-word-word-word")
        self.assertLessEqual(len(slug), 30)
        self.assertFalse(slug.endswith("-"))

    def test_unslugifiable_title_requires_slug(self):
        code, _, err = self._new("task", "!!!")
        self.assertEqual(code, 1)
        self.assertIn("--slug", err)

    def test_tags_emitted_as_inline_list(self):
        _, path, _ = self._new("task", "T", "--tags", "cli, auth")
        fields, _ = tasks.read_task(path)
        self.assertEqual(fields["tags"], ["cli", "auth"])
        self.assertIn("tags: [cli, auth]\n", path.read_text(encoding="utf-8"))

    def test_priority_flag(self):
        _, path, _ = self._new("task", "T", "--priority", "high")
        self.assertEqual(tasks.read_task(path)[0]["priority"], "high")

    def test_invalid_priority_rejected(self):
        code, _, err = self._new("task", "T", "--priority", "urgent")
        self.assertEqual(code, 1)
        self.assertIn("invalid choice", err)

    def test_state_flag(self):
        _, path, _ = self._new("task", "T", "--state", "open")
        self.assertEqual(tasks.read_task(path)[0]["state"], "open")

    def test_state_invalid_without_reason_warns(self):
        code, path, err = self._new("task", "T", "--state", "invalid")
        self.assertEqual(code, 0)
        self.assertIn("tasks.py: warning:", err)
        self.assertIn("reason", err)
        fields, _ = tasks.read_task(path)
        self.assertEqual(fields["state"], "invalid")
        self.assertNotIn("reason", fields)

    def test_state_invalid_with_reason_records_it(self):
        _, path, err = self._new(
            "task", "T", "--state", "invalid", "--reason", "wrong premise"
        )
        self.assertEqual(err, "")
        fields, _ = tasks.read_task(path)
        self.assertEqual(fields["reason"], "wrong premise")

    def test_author_flag_beats_config(self):
        _, path, _ = self._new("task", "T", "--author", "Bob")
        self.assertEqual(tasks.read_task(path)[0]["author"], "Bob")

    def test_creates_missing_artifacts_dir(self):
        import shutil

        shutil.rmtree(self.project / "tasks")
        code, path, err = self._new("task", "T")
        self.assertEqual((code, err), (0, ""))
        self.assertTrue(path.is_file())

    def test_numbers_never_reused(self):
        _, first, _ = self._new("task", "A")
        self._new("task", "B")
        first.unlink()
        _, third, _ = self._new("task", "C")
        self.assertEqual(third.name, "003_c.md")

    def test_new_after_999_is_error(self):
        tasks_dir = self.project / "tasks"
        (tasks_dir / "999_last.md").write_text("", encoding="utf-8")
        code, _, err = self._new("task", "Too many")
        self.assertEqual(code, 1)
        self.assertIn("tasks.py: error:", err)
        self.assertIn("999", err)


class TestList(ProjectFixture):
    def setUp(self):
        super().setUp()
        self.run_cli("init", "--author", "Ada")
        self.run_cli("new", "task", "Alpha")
        self.run_cli("new", "bug", "Beta", "--tags", "cli, auth")
        self.run_cli(
            "new",
            "task",
            "Gamma",
            "--state",
            "open",
            "--author",
            "Bob",
            "--tags",
            "cli",
        )

    def _lines(self, *argv):
        code, out, err = self.run_cli("list", *argv)
        self.assertEqual((code, err), (0, ""))
        return out.splitlines()

    def test_lists_all_sorted_by_number(self):
        lines = self._lines()
        self.assertEqual(len(lines), 3)
        self.assertEqual(
            lines,
            [
                "001  draft  task  Alpha",
                "002  draft  bug  Beta",
                "003  open  task  Gamma",
            ],
        )

    def test_filter_state(self):
        self.assertEqual(
            self._lines("--state", "open"),
            [
                "003  open  task  Gamma",
            ],
        )

    def test_filter_state_repeatable_is_or(self):
        lines = self._lines("--state", "draft", "--state", "open")
        self.assertEqual(len(lines), 3)

    def test_filter_type(self):
        self.assertEqual(
            self._lines("--type", "bug"), ["002  draft  bug  Beta"]
        )

    def test_filter_tag(self):
        self.assertEqual(
            self._lines("--tag", "auth"), ["002  draft  bug  Beta"]
        )

    def test_filter_author(self):
        self.assertEqual(
            self._lines("--author", "Bob"), ["003  open  task  Gamma"]
        )

    def test_filters_combine_with_and(self):
        self.assertEqual(
            self._lines("--state", "open", "--tag", "cli"),
            ["003  open  task  Gamma"],
        )
        # AND across flag types: Beta is draft but not authored by Bob.
        self.assertEqual(
            self._lines("--author", "Bob", "--state", "draft"), []
        )

    def test_skips_unparseable_file_with_warning(self):
        tasks_dir = self.project / "tasks"
        tasks_dir.joinpath("009_broken.md").write_text(
            "no frontmatter at all\n", encoding="utf-8"
        )
        code, out, err = self.run_cli("list")
        self.assertEqual(code, 0)
        self.assertEqual(
            out.splitlines(),
            [
                "001  draft  task  Alpha",
                "002  draft  bug  Beta",
                "003  open  task  Gamma",
            ],
        )
        self.assertIn("tasks.py: warning:", err)
        self.assertIn("009_broken.md", err)

    def test_missing_dir_suggests_init(self):
        import shutil

        shutil.rmtree(self.project / "tasks")
        code, out, err = self.run_cli("list")
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("tasks.py: error:", err)
        self.assertIn("init", err)


class TestShow(ProjectFixture):
    def setUp(self):
        super().setUp()
        self.run_cli("init", "--author", "Ada")
        self.run_cli("new", "task", "Alpha")

    def test_show_by_filename_is_verbatim(self):
        path = self.project / "tasks" / "001_alpha.md"
        code, out, err = self.run_cli("show", "001_alpha.md")
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(out, path.read_text(encoding="utf-8"))

    def test_show_by_number(self):
        path = self.project / "tasks" / "001_alpha.md"
        code, out, _ = self.run_cli("show", "001")
        self.assertEqual(code, 0)
        self.assertEqual(out, path.read_text(encoding="utf-8"))

    def test_unknown_id_is_error(self):
        code, out, err = self.run_cli("show", "099")
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("tasks.py: error:", err)

    def test_missing_dir_suggests_init(self):
        import shutil

        shutil.rmtree(self.project / "tasks")
        code, _, err = self.run_cli("show", "001")
        self.assertEqual(code, 1)
        self.assertIn("init", err)


class TestSetState(ProjectFixture):
    def setUp(self):
        super().setUp()
        self.run_cli("init", "--author", "Ada")
        self.run_cli("new", "task", "Alpha")
        self.path = self.project / "tasks" / "001_alpha.md"

    def _read(self):
        return tasks.read_task(self.path)

    def _age_updated(self):
        """Set updated to the past so a refresh is observable."""
        fields, body = self._read()
        fields["updated"] = "2020-01-01"
        self.path.write_text(tasks.render_task(fields, body), encoding="utf-8")

    def test_any_to_any_transitions_allowed(self):
        for state in (
            "open",
            "in-progress",
            "complete",
            "draft",
            "invalid",
            "open",
        ):
            code, _, err = self.run_cli("set-state", "001", state)
            self.assertEqual(code, 0, err)
        self.assertEqual(self._read()[0]["state"], "open")

    def test_updated_refreshed(self):
        self._age_updated()
        code, _, err = self.run_cli("set-state", "001", "open")
        self.assertEqual((code, err), (0, ""))
        fields, _ = self._read()
        today = datetime.date.today().isoformat()  # noqa: DTZ011
        self.assertEqual(fields["updated"], today)
        self.assertEqual(fields["created"], today)

    def test_invalid_without_reason_warns_but_succeeds(self):
        code, _, err = self.run_cli("set-state", "001", "invalid")
        self.assertEqual(code, 0)
        self.assertIn("tasks.py: warning:", err)
        self.assertIn("reason", err)
        self.assertEqual(self._read()[0]["state"], "invalid")

    def test_invalid_with_reason_records_reason(self):
        code, _, err = self.run_cli(
            "set-state", "001", "invalid", "--reason", "superseded"
        )
        self.assertEqual((code, err), (0, ""))
        fields, _ = self._read()
        self.assertEqual(fields["reason"], "superseded")

    def test_reason_set_on_non_invalid_state(self):
        code, _, err = self.run_cli(
            "set-state", "001", "open", "--reason", "extra context"
        )
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(self._read()[0]["reason"], "extra context")

    def test_invalid_state_value_rejected(self):
        code, _, err = self.run_cli("set-state", "001", "bogus")
        self.assertEqual(code, 1)
        self.assertIn("invalid choice", err)

    def test_unknown_id_is_error(self):
        code, _, err = self.run_cli("set-state", "099", "open")
        self.assertEqual(code, 1)
        self.assertIn("tasks.py: error:", err)

    def test_missing_dir_suggests_init(self):
        import shutil

        shutil.rmtree(self.project / "tasks")
        code, _, err = self.run_cli("set-state", "001", "open")
        self.assertEqual(code, 1)
        self.assertIn("init", err)

    def test_body_preserved_byte_for_byte(self):
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(
                "\nHand-written notes.\n"
                "---\n"
                "tricky: line that looks like frontmatter\n"
                "- DEPENDS ON: 002_other.md\n"
                "## Links\n"
            )
        before_body = tasks.parse_task(
            self.path.read_text(encoding="utf-8"), "x"
        )[1]
        code, _, err = self.run_cli("set-state", "001", "in-progress")
        self.assertEqual((code, err), (0, ""))
        after = self.path.read_text(encoding="utf-8")
        self.assertEqual(tasks.parse_task(after, "x")[1], before_body)

    def test_same_state_mutation_is_byte_identical(self):
        before = self.path.read_text(encoding="utf-8")
        code, _, err = self.run_cli("set-state", "001", "draft")
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(self.path.read_text(encoding="utf-8"), before)


class TestSet(ProjectFixture):
    def setUp(self):
        super().setUp()
        self.run_cli("init", "--author", "Ada")
        self.run_cli("new", "task", "Alpha")
        self.path = self.project / "tasks" / "001_alpha.md"

    def _read(self):
        return tasks.read_task(self.path)

    def _age_updated(self):
        fields, body = self._read()
        fields["updated"] = "2020-01-01"
        self.path.write_text(tasks.render_task(fields, body), encoding="utf-8")

    def test_set_title(self):
        code, _, err = self.run_cli("set", "001", "title", "New: Title")
        self.assertEqual((code, err), (0, ""))
        fields, _ = self._read()
        self.assertEqual(fields["title"], "New: Title")
        self.assertIn('title: "New: Title"\n', self.path.read_text())

    def test_set_title_empty_rejected(self):
        code, _, err = self.run_cli("set", "001", "title", "   ")
        self.assertEqual(code, 1)
        self.assertIn("tasks.py: error:", err)
        self.assertIn("non-empty", err)

    def test_set_author(self):
        code, _, _ = self.run_cli("set", "001", "author", "Grace")
        self.assertEqual(code, 0)
        self.assertEqual(self._read()[0]["author"], "Grace")

    def test_set_author_empty_rejected(self):
        code, _, err = self.run_cli("set", "001", "author", "")
        self.assertEqual(code, 1)
        self.assertIn("non-empty", err)

    def test_set_created_rejected(self):
        code, _, err = self.run_cli("set", "001", "created", "2020-01-01")
        self.assertEqual(code, 1)
        self.assertIn("tasks.py: error:", err)
        self.assertIn("created", err)

    def test_unknown_field_rejected_with_list(self):
        code, _, err = self.run_cli("set", "001", "bogus", "x")
        self.assertEqual(code, 1)
        self.assertIn("unknown field", err)
        self.assertIn("title", err)

    def test_set_state_enum_and_warning(self):
        code, _, err = self.run_cli("set", "001", "state", "bogus")
        self.assertEqual(code, 1)
        self.assertIn("state must be one of", err)
        code, _, err = self.run_cli("set", "001", "state", "complete")
        self.assertEqual((code, err), (0, ""))
        code, _, err = self.run_cli("set", "001", "state", "invalid")
        self.assertEqual(code, 0)
        self.assertIn("tasks.py: warning:", err)
        self.assertEqual(self._read()[0]["state"], "invalid")

    def test_set_priority_enum(self):
        code, _, err = self.run_cli("set", "001", "priority", "urgent")
        self.assertEqual(code, 1)
        self.assertIn("priority must be one of", err)
        code, _, err = self.run_cli("set", "001", "priority", "high")
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(self._read()[0]["priority"], "high")

    def test_set_type_enum(self):
        code, _, err = self.run_cli("set", "001", "type", "chore")
        self.assertEqual(code, 1)
        self.assertIn("type must be one of", err)

    def test_set_type_subtask_without_parent_is_error(self):
        code, _, err = self.run_cli("set", "001", "type", "subtask")
        self.assertEqual(code, 1)
        self.assertIn("parent", err)

    def test_set_type_subtask_with_valid_parent(self):
        # A file can carry a parent without being a subtask (e.g. after a
        # bulk edit); `set type subtask` validates the parent and fixes it.
        self.run_cli("new", "task", "Child")
        child = self.project / "tasks" / "002_child.md"
        fields, body = tasks.read_task(child)
        fields["parent"] = "001_alpha.md"
        child.write_text(tasks.render_task(fields, body), encoding="utf-8")
        code, _, err = self.run_cli("set", "002", "type", "subtask")
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(tasks.read_task(child)[0]["type"], "subtask")

    def test_set_type_subtask_with_missing_parent_file(self):
        self.run_cli("new", "task", "Child")
        child = self.project / "tasks" / "002_child.md"
        fields, body = tasks.read_task(child)
        fields["parent"] = "099_nope.md"
        child.write_text(tasks.render_task(fields, body), encoding="utf-8")
        code, _, err = self.run_cli("set", "002", "type", "subtask")
        self.assertEqual(code, 1)
        self.assertIn("parent file not found", err)

    def test_set_type_away_from_subtask_with_parent_is_error(self):
        self.run_cli("new", "subtask", "Child", "--parent", "001_alpha.md")
        code, _, err = self.run_cli("set", "002", "type", "task")
        self.assertEqual(code, 1)
        self.assertIn("parent", err)
        self.assertIn("non-subtask", err)

    def test_set_parent_on_non_subtask_is_error(self):
        code, _, err = self.run_cli("set", "001", "parent", "002_beta.md")
        self.assertEqual(code, 1)
        self.assertIn("subtasks", err)

    def test_set_parent_on_subtask_success(self):
        self.run_cli("new", "bug", "Beta")
        self.run_cli("new", "subtask", "Child", "--parent", "001_alpha.md")
        code, _, err = self.run_cli("set", "003", "parent", "002")
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(self._read_sub()["parent"], "002_beta.md")

    def _read_sub(self):
        fields, _ = tasks.read_task(self.project / "tasks" / "003_child.md")
        return fields

    def test_set_parent_to_subtask_rejected(self):
        self.run_cli("new", "subtask", "Child", "--parent", "001_alpha.md")
        self.run_cli("new", "subtask", "Other", "--parent", "001_alpha.md")
        code, _, err = self.run_cli("set", "002", "parent", "003_other.md")
        self.assertEqual(code, 1)
        self.assertIn("task or bug", err)

    def test_set_parent_nonexistent_rejected(self):
        self.run_cli("new", "subtask", "Child", "--parent", "001_alpha.md")
        code, _, err = self.run_cli("set", "002", "parent", "099_nope.md")
        self.assertEqual(code, 1)
        self.assertIn("tasks.py: error:", err)

    def test_set_tags_comma_separated(self):
        code, _, err = self.run_cli("set", "001", "tags", "cli, auth")
        self.assertEqual((code, err), (0, ""))
        fields, _ = self._read()
        self.assertEqual(fields["tags"], ["cli", "auth"])
        code, _, err = self.run_cli("set", "001", "tags", "")
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(self._read()[0]["tags"], [])

    def test_set_updated_valid_date_not_refreshed(self):
        self._age_updated()
        code, _, err = self.run_cli("set", "001", "updated", "2021-12-31")
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(self._read()[0]["updated"], "2021-12-31")

    def test_set_updated_invalid_rejected(self):
        for bad in ("12/31/2021", "2021-13-40", "2021-02-30", "tomorrow"):
            with self.subTest(bad=bad):
                code, _, err = self.run_cli("set", "001", "updated", bad)
                self.assertEqual(code, 1)
                self.assertIn("tasks.py: error:", err)

    def test_updated_refreshed_on_other_sets(self):
        self._age_updated()
        code, _, err = self.run_cli("set", "001", "priority", "low")
        self.assertEqual((code, err), (0, ""))
        today = datetime.date.today().isoformat()  # noqa: DTZ011
        self.assertEqual(self._read()[0]["updated"], today)

    def test_created_never_modified(self):
        self._age_updated()
        created_before = self._read()[0]["created"]
        for argv in (
            ("set", "001", "title", "X"),
            ("set", "001", "state", "open"),
            ("set", "001", "tags", "a"),
            ("set-state", "001", "complete"),
        ):
            code, _, err = self.run_cli(*argv)
            self.assertEqual(code, 0, err)
        self.assertEqual(self._read()[0]["created"], created_before)

    def test_set_reason(self):
        code, _, err = self.run_cli("set", "001", "reason", "why not")
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(self._read()[0]["reason"], "why not")

    def test_set_reason_empty_rejected(self):
        code, _, err = self.run_cli("set", "001", "reason", "")
        self.assertEqual(code, 1)
        self.assertIn("non-empty", err)

    def test_body_preserved_on_set(self):
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(
                "\nNotes with: colons and # hashes\n"
                "---\n"
                "RELATED TO: 002_beta.md\n"
            )
        before_body = tasks.parse_task(
            self.path.read_text(encoding="utf-8"), "x"
        )[1]
        code, _, err = self.run_cli("set", "001", "priority", "high")
        self.assertEqual((code, err), (0, ""))
        after = self.path.read_text(encoding="utf-8")
        self.assertEqual(tasks.parse_task(after, "x")[1], before_body)

    def test_key_order_canonical_after_set(self):
        self._age_updated()
        self.run_cli("set", "001", "priority", "high")
        self.run_cli("set", "001", "reason", "because")
        keys = [
            line.split(":", 1)[0]
            for line in self.path.read_text(encoding="utf-8")
            .split("---\n")[1]
            .splitlines()
        ]
        self.assertEqual(
            keys,
            [
                "title",
                "type",
                "state",
                "author",
                "created",
                "updated",
                "reason",
                "priority",
            ],
        )


class TestNextId(ProjectFixture):
    def test_missing_dir_suggests_init(self):
        code, out, err = self.run_cli("next-id")
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("tasks.py: error:", err)
        self.assertIn("init", err)

    def test_first_number_is_001(self):
        self.run_cli("init")
        code, out, err = self.run_cli("next-id")
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(out, "001\n")

    def test_increments_after_create(self):
        self.run_cli("init", "--author", "Ada")
        self.run_cli("new", "task", "Alpha")
        code, out, _ = self.run_cli("next-id")
        self.assertEqual(code, 0)
        self.assertEqual(out, "002\n")


def _valid_fields(**overrides):
    """A minimal schema-valid frontmatter."""
    fields = {
        "title": "T",
        "type": "task",
        "state": "draft",
        "author": "Ada",
        "created": "2024-01-01",
        "updated": "2024-01-02",
    }
    fields.update(overrides)
    return fields


class TestValidate(ProjectFixture):
    def setUp(self):
        super().setUp()
        self.tasks_dir = self.project / "tasks"
        self.tasks_dir.mkdir()

    def _write(self, name, fields=None, body="", raw=None):
        path = self.tasks_dir / name
        if raw is not None:
            path.write_text(raw, encoding="utf-8")
        else:
            path.write_text(tasks.render_task(fields, body), encoding="utf-8")
        return path

    def _validate(self, *argv):
        return self.run_cli("validate", *argv)

    def test_valid_corpus_is_clean(self):
        self._write("001_a.md", _valid_fields())
        self._write("002_b.md", _valid_fields(type="bug"))
        self._write(
            "003_c.md",
            _valid_fields(type="subtask", parent="001_a.md"),
        )
        code, out, err = self._validate()
        self.assertEqual((code, out, err), (0, "", ""))

    def test_missing_required_field(self):
        fields = _valid_fields()
        del fields["author"]
        self._write("001_a.md", fields)
        code, out, _ = self._validate()
        self.assertEqual(code, 2)
        self.assertIn("001_a.md", out)
        self.assertIn("missing required field", out)
        self.assertIn("author", out)

    def test_empty_title_and_author_rejected(self):
        self._write("001_a.md", _valid_fields(title="  "))
        self._write("002_b.md", _valid_fields(author=""))
        code, out, _ = self._validate()
        self.assertEqual(code, 2)
        self.assertIn("title must be a non-empty string", out)
        self.assertIn("author must be a non-empty string", out)

    def test_bad_enums(self):
        self._write("001_a.md", _valid_fields(state="bogus"))
        self._write("002_b.md", _valid_fields(type="chore"))
        self._write("003_c.md", _valid_fields(priority="urgent"))
        code, out, _ = self._validate()
        self.assertEqual(code, 2)
        self.assertIn("'bogus' is not one of", out)
        self.assertIn("'chore' is not one of", out)
        self.assertIn("'urgent' is not one of", out)

    def test_bad_dates(self):
        self._write("001_a.md", _valid_fields(created="2024-13-40"))
        self._write("002_b.md", _valid_fields(updated="31/12/2024"))
        code, out, _ = self._validate()
        self.assertEqual(code, 2)
        self.assertIn("created must be a date", out)
        self.assertIn("updated must be a date", out)

    def test_parent_forbidden_on_non_subtask(self):
        self._write("001_a.md", _valid_fields(parent="002_b.md"))
        self._write("002_b.md", _valid_fields())
        code, out, _ = self._validate()
        self.assertEqual(code, 2)
        self.assertIn("'parent' is forbidden on non-subtask", out)

    def test_subtask_requires_parent(self):
        self._write("001_a.md", _valid_fields(type="subtask"))
        code, out, _ = self._validate()
        self.assertEqual(code, 2)
        self.assertIn("parent", out)

    def test_subtask_parent_must_exist(self):
        self._write(
            "001_a.md", _valid_fields(type="subtask", parent="099_nope.md")
        )
        code, out, _ = self._validate()
        self.assertEqual(code, 2)
        self.assertIn("parent file not found", out)

    def test_subtask_parent_cannot_be_subtask(self):
        self._write("001_a.md", _valid_fields())
        self._write(
            "002_b.md", _valid_fields(type="subtask", parent="001_a.md")
        )
        self._write(
            "003_c.md", _valid_fields(type="subtask", parent="002_b.md")
        )
        code, out, _ = self._validate()
        self.assertEqual(code, 2)
        self.assertIn("parents must be task or bug", out)

    def test_invalid_state_without_reason_warns_but_exits_0(self):
        self._write("001_a.md", _valid_fields(state="invalid"))
        code, out, err = self._validate()
        self.assertEqual(code, 0)
        self.assertIn("warning:", out)
        self.assertIn(tasks.WARNING_INVALID_NO_REASON, out)
        self.assertEqual(err, "")

    def test_unknown_key_warns_but_exits_0(self):
        self._write("001_a.md", _valid_fields(zzz="1"))
        code, out, _ = self._validate()
        self.assertEqual(code, 0)
        self.assertIn("unknown frontmatter key 'zzz'", out)

    def test_stray_files_are_errors(self):
        self._write("001_a.md", _valid_fields())
        (self.tasks_dir / "notes.txt").write_text("x", encoding="utf-8")
        (self.tasks_dir / ".DS_Store").write_text("x", encoding="utf-8")
        code, out, _ = self._validate()
        self.assertEqual(code, 2)
        self.assertIn("notes.txt", out)
        self.assertIn(".DS_Store", out)
        self.assertIn("filename does not match", out)

    def test_installed_entries_are_not_stray_files(self):
        self._write("001_a.md", _valid_fields())
        (self.tasks_dir / "tasks.py").write_text("x", encoding="utf-8")
        (self.tasks_dir / "tasks.yaml").write_text(
            "artifacts_dir: tasks\n", encoding="utf-8"
        )
        templates = self.tasks_dir / "templates"
        templates.mkdir()
        (templates / "task.md").write_text("x", encoding="utf-8")
        code, out, err = self._validate()
        self.assertEqual((code, out, err), (0, "", ""))

    def test_dangling_link_target_is_error(self):
        self._write(
            "001_a.md", _valid_fields(), body="DEPENDS ON: 099_nope.md\n"
        )
        code, out, _ = self._validate()
        self.assertEqual(code, 2)
        self.assertIn("dangling", out)
        self.assertIn("099_nope.md", out)

    def test_existing_link_target_is_clean(self):
        self._write("001_a.md", _valid_fields(), body="RELATED TO: 002_b.md\n")
        self._write("002_b.md", _valid_fields())
        self.assertEqual(self._validate()[0], 0)

    def test_links_after_bullets_are_checked(self):
        self._write(
            "001_a.md", _valid_fields(), body="- DEPENDS ON: 099_nope.md\n"
        )
        code, out, _ = self._validate()
        self.assertEqual(code, 2)
        self.assertIn("dangling", out)

    def test_lowercase_token_is_not_a_link(self):
        self._write(
            "001_a.md", _valid_fields(), body="depends on: 099_nope.md\n"
        )
        code, out, _ = self._validate()
        self.assertEqual((code, out), (0, ""))

    def test_specific_ids_skip_stray_files(self):
        self._write("001_a.md", _valid_fields())
        (self.tasks_dir / "notes.txt").write_text("x", encoding="utf-8")
        code, out, _ = self._validate("001")
        self.assertEqual((code, out), (0, ""))

    def test_unparseable_frontmatter_is_error(self):
        self._write("001_a.md", raw="---\ntitle: [broken\n---\n\nbody\n")
        code, out, _ = self._validate()
        self.assertEqual(code, 2)
        self.assertIn("001_a.md", out)

    def test_bad_filename_pattern_is_error(self):
        path = self.tasks_dir / "01_a.md"  # two digits
        path.write_text(
            tasks.render_task(_valid_fields(), ""), encoding="utf-8"
        )
        code, out, _ = self._validate("01_a.md")
        self.assertEqual(code, 2)
        self.assertIn("filename does not match", out)

    def test_tags_must_be_an_inline_list(self):
        self._write("001_a.md", _valid_fields(tags="cli"))
        code, out, _ = self._validate()
        self.assertEqual(code, 2)
        self.assertIn("tags must be an inline list", out)

    def test_missing_dir_suggests_init(self):
        import shutil

        shutil.rmtree(self.tasks_dir)
        code, out, err = self._validate()
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("tasks.py: error:", err)
        self.assertIn("init", err)

    def test_errors_and_warnings_reported_together(self):
        self._write("001_a.md", _valid_fields(state="invalid", zzz="1"))
        self._write("002_b.md", _valid_fields(author=""))
        code, out, _ = self._validate()
        self.assertEqual(code, 2)
        self.assertIn("warning:", out)
        self.assertIn("error:", out)


class TestLinks(ProjectFixture):
    def setUp(self):
        super().setUp()
        self.tasks_dir = self.project / "tasks"
        self.tasks_dir.mkdir()
        self._write(
            "001_a.md",
            "DEPENDS ON: 002_b.md, 003_c.md\n"
            "RELATED TO: 099_missing.md\n"
            "- DUPLICATES: 004_d.md\n",
        )
        self._write("002_b.md", "RELATED TO: 001_a.md\n")
        self._write("003_c.md")
        self._write("004_d.md", "depends on: 001_a.md\nDEPENDS ON 001_a.md\n")
        self._write("005_e.md")

    def _write(self, name, body=""):
        (self.tasks_dir / name).write_text(
            tasks.render_task(_valid_fields(), body), encoding="utf-8"
        )

    def test_outbound_and_inbound(self):
        code, out, err = self.run_cli("links", "001")
        self.assertEqual((code, err), (0, ""))
        self.assertIn("outbound:", out)
        self.assertIn("inbound:", out)
        self.assertIn("DEPENDS ON: 002_b.md", out)
        self.assertIn("DEPENDS ON: 003_c.md", out)
        self.assertIn("RELATED TO: 099_missing.md (dangling)", out)
        self.assertIn("DUPLICATES: 004_d.md", out)
        self.assertIn("002_b.md (RELATED TO)", out)

    def test_inbound_via_bullet_token(self):
        _, out, _ = self.run_cli("links", "003")
        self.assertIn("001_a.md (DEPENDS ON)", out)

    def test_task_with_no_links(self):
        _, out, _ = self.run_cli("links", "005")
        self.assertIn("outbound:\n  (none)", out)
        self.assertIn("inbound:\n  (none)", out)

    def test_token_match_is_exact(self):
        # 004's lowercase / colon-less lines must not be recognized.
        _, out, _ = self.run_cli("links", "004")
        self.assertIn("(none)", out)
        _, out, _ = self.run_cli("links", "001")
        self.assertNotIn("004_d.md (", out)

    def test_unknown_id_is_error(self):
        code, out, err = self.run_cli("links", "099")
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("tasks.py: error:", err)

    def test_missing_dir_suggests_init(self):
        import shutil

        shutil.rmtree(self.tasks_dir)
        code, _, err = self.run_cli("links", "001")
        self.assertEqual(code, 1)
        self.assertIn("init", err)


class TestGrep(ProjectFixture):
    def _fake_rg(self, exit_code=0):
        """A stub `rg` on PATH that echoes its args and exits with a
        fixed code, so passthrough and exit-code propagation are testable
        without a real ripgrep install."""
        bin_dir = self.project / "bin"
        bin_dir.mkdir(exist_ok=True)
        # The stub logs its argv to a file: subprocess output goes to the
        # real fd 1, which redirect_stdout in run_cli cannot capture.
        self.rg_log = self.project / "rg.log"
        script = bin_dir / "rg"
        script.write_text(
            "#!/bin/sh\n"
            f"printf 'rg:%s\\n' \"$*\" >> {self.rg_log}\n"
            f"exit {exit_code}\n",
            encoding="utf-8",
        )
        script.chmod(0o755)
        return mock.patch.dict(os.environ, {"PATH": str(bin_dir)})

    def _rg_log_text(self):
        return self.rg_log.read_text(encoding="utf-8")

    def test_args_passed_through_verbatim(self):
        self.run_cli("init")
        with self._fake_rg(0):
            code, out, err = self.run_cli("grep", "-n", "pattern")
        self.assertEqual((code, out, err), (0, "", ""))
        logged = self._rg_log_text()
        self.assertIn("-n pattern", logged)
        self.assertIn(str(self.project / "tasks"), logged)

    def test_installed_entries_are_excluded(self):
        self.run_cli("init")
        with self._fake_rg(0):
            code, _, _ = self.run_cli("grep", "pattern")
        self.assertEqual(code, 0)
        logged = self._rg_log_text()
        for glob in ("!tasks.py", "!tasks.yaml", "!templates"):
            with self.subTest(glob=glob):
                self.assertIn(glob, logged)

    def test_option_like_args_are_not_eaten_by_argparse(self):
        self.run_cli("init")
        with self._fake_rg(0):
            code, out, _ = self.run_cli("grep", "--files-with-matches", "bug")
        self.assertEqual(code, 0)
        self.assertIn("--files-with-matches bug", self._rg_log_text())

    def test_exit_code_1_propagated(self):
        self.run_cli("init")
        with self._fake_rg(1):
            code, _, _ = self.run_cli("grep", "pattern")
        self.assertEqual(code, 1)

    def test_exit_code_2_propagated(self):
        self.run_cli("init")
        with self._fake_rg(2):
            code, _, _ = self.run_cli("grep", "--bad-flag")
        self.assertEqual(code, 2)

    def test_missing_rg_is_clear_error(self):
        self.run_cli("init")
        empty_bin = self.project / "empty-bin"
        empty_bin.mkdir()
        with mock.patch.dict(os.environ, {"PATH": str(empty_bin)}):
            code, out, err = self.run_cli("grep", "pattern")
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("tasks.py: error:", err)
        self.assertIn("rg", err)

    def test_help_is_tasks_help_not_rg_help(self):
        code, out, _ = self.run_cli("grep", "-h")
        self.assertEqual(code, 0)
        self.assertIn("usage:", out)

    def test_missing_dir_suggests_init(self):
        empty_bin = self.project / "bin"
        empty_bin.mkdir()
        with mock.patch.dict(os.environ, {"PATH": str(empty_bin)}):
            code, out, err = self.run_cli("grep", "pattern")
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("init", err)


if __name__ == "__main__":
    unittest.main()
