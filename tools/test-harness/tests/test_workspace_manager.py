"""Unit tests for workspace-manager.sh, driven via subprocess in temp dirs."""

import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "workspace-manager.sh"


def run_wm(*args):
    """Run workspace-manager.sh with args; return CompletedProcess."""
    return subprocess.run(
        [str(SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def write_skill(root, name, extra_files=None):
    """Create root/skills/<name>/SKILL.md plus optional extra files."""
    skill_dir = root / "skills" / name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\n"
        f"name: {name}\n"
        "description: test skill\n"
        "---\n"
        "\n"
        "# Body\n"
    )
    for rel, content in (extra_files or {}).items():
        path = skill_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    return skill_dir


class InitPrefixTests(unittest.TestCase):
    def test_init_custom_prefix_prints_matching_path(self):
        proc = run_wm("init", "--prefix", "retrieval-test")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        ws = proc.stdout.strip()
        self.assertRegex(ws, r"^/tmp/retrieval-test\.[A-Za-z0-9]+$")
        self.assertTrue((Path(ws) / ".agents" / "skills").is_dir())
        cleanup = run_wm(
            "cleanup", "--workspace", ws, "--prefix", "retrieval-test"
        )
        self.assertEqual(cleanup.returncode, 0, cleanup.stderr)
        self.assertFalse(Path(ws).exists())

    def test_init_default_prefix(self):
        proc = run_wm("init")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        ws = proc.stdout.strip()
        self.assertTrue(
            ws.startswith("/tmp/trigger-test."), f"unexpected path: {ws}"
        )
        cleanup = run_wm("cleanup", "--workspace", ws)
        self.assertEqual(cleanup.returncode, 0, cleanup.stderr)

    def test_init_unsafe_prefix_rejected(self):
        # '..' passes the charset check (dots are legal); it merely yields
        # odd /tmp/...XXXX names, so it is not in the rejected set.
        for bad in ("a/b", "", "a b"):
            with self.subTest(prefix=bad):
                proc = run_wm("init", "--prefix", bad)
                self.assertEqual(proc.returncode, 1)
                self.assertIn("unsafe --prefix", proc.stderr)


class CleanupPrefixTests(unittest.TestCase):
    def test_cleanup_refuses_foreign_prefix(self):
        proc = run_wm("init", "--prefix", "retrieval-test")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        ws = proc.stdout.strip()
        self.addCleanup(
            run_wm, "cleanup", "--workspace", ws, "--prefix", "retrieval-test"
        )
        # default prefix must not match a retrieval-test.* path
        proc = run_wm("cleanup", "--workspace", ws)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("refusing to remove path outside", proc.stderr)
        self.assertTrue(Path(ws).exists())

    def test_cleanup_refuses_non_tmp_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = run_wm("cleanup", "--workspace", tmp)
            self.assertEqual(proc.returncode, 1)
            self.assertIn("refusing to remove path outside", proc.stderr)
            self.assertTrue(Path(tmp).exists())


class FullSyncStatusTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        tmp = Path(self._tmp.name)
        self.source = tmp / "repo-root"
        self.ws = tmp / "ws"
        (self.ws / ".agents" / "skills").mkdir(parents=True)
        self.skill = "demo-skill"

    def sync(self, *extra):
        return run_wm(
            "sync",
            "--skill",
            self.skill,
            "--source",
            str(self.source),
            "--workspace",
            str(self.ws),
            *extra,
        )

    def status(self, *extra):
        return run_wm(
            "status",
            "--skill",
            self.skill,
            "--source",
            str(self.source),
            "--workspace",
            str(self.ws),
            *extra,
        )

    def test_full_roundtrip_status_ok(self):
        skill_dir = write_skill(
            self.source,
            self.skill,
            extra_files={
                "references/guide.md": "guide text\n",
                "scripts/tool.py": "print('hi')\n",
                "nested/deep.txt": "deep\n",
            },
        )
        (skill_dir / "__pycache__").mkdir()
        (skill_dir / "__pycache__" / "junk.pyc").write_text("junk")
        proc = self.sync("--full")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("synced:", proc.stdout)
        synced = self.ws / ".agents" / "skills" / self.skill
        self.assertEqual(
            (synced / "references" / "guide.md").read_text(), "guide text\n"
        )
        self.assertEqual(
            (synced / "SKILL.md").read_text(),
            (skill_dir / "SKILL.md").read_text(),
        )
        self.assertFalse((synced / "__pycache__").exists())
        proc = self.status("--full")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("full dir matches source", proc.stdout)

    def test_full_status_detects_source_change(self):
        skill_dir = write_skill(
            self.source, self.skill, extra_files={"references/a.md": "a\n"}
        )
        self.assertEqual(self.sync("--full").returncode, 0)
        (skill_dir / "references" / "a.md").write_text("changed\n")
        proc = self.status("--full")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("differs from source", proc.stderr)

    def test_full_status_detects_workspace_change(self):
        write_skill(
            self.source, self.skill, extra_files={"references/a.md": "a\n"}
        )
        self.assertEqual(self.sync("--full").returncode, 0)
        synced = self.ws / ".agents" / "skills" / self.skill
        (synced / "references" / "a.md").write_text("tampered\n")
        proc = self.status("--full")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("differs from source", proc.stderr)

    def test_pycache_difference_ignored(self):
        skill_dir = write_skill(
            self.source, self.skill, extra_files={"code.py": "pass\n"}
        )
        self.assertEqual(self.sync("--full").returncode, 0)
        (skill_dir / "__pycache__").mkdir()
        (skill_dir / "__pycache__" / "code.pyc").write_text("new junk")
        proc = self.status("--full")
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_default_sync_stub_only(self):
        write_skill(
            self.source, self.skill, extra_files={"references/a.md": "a\n"}
        )
        proc = self.sync()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        synced = self.ws / ".agents" / "skills" / self.skill
        self.assertFalse((synced / "references" / "a.md").exists())
        stub = (synced / "SKILL.md").read_text()
        self.assertTrue(stub.startswith("---\n"))
        self.assertNotIn("# Body", stub)
        self.assertEqual(self.status().returncode, 0, proc.stderr)

    def test_default_status_detects_frontmatter_change(self):
        skill_dir = write_skill(self.source, self.skill)
        self.assertEqual(self.sync().returncode, 0)
        text = (skill_dir / "SKILL.md").read_text()
        (skill_dir / "SKILL.md").write_text(
            text.replace("description: test skill", "description: changed")
        )
        proc = self.status()
        self.assertEqual(proc.returncode, 1)
        self.assertIn("out of date", proc.stderr)


class SymlinkPolicyTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        tmp = Path(self._tmp.name)
        self.source = tmp / "repo-root"
        self.ws = tmp / "ws"
        (self.ws / ".agents" / "skills").mkdir(parents=True)

    def test_escaping_symlink_rejected(self):
        skill_dir = write_skill(self.source, "demo-skill")
        outside = self.source / "outside.txt"
        outside.write_text("secret\n")
        (skill_dir / "link.md").symlink_to(outside)
        proc = run_wm(
            "sync",
            "--skill",
            "demo-skill",
            "--source",
            str(self.source),
            "--workspace",
            str(self.ws),
            "--full",
        )
        self.assertEqual(proc.returncode, 1)
        self.assertIn("symlink escapes skill dir", proc.stderr)

    def test_symlink_to_directory_rejected(self):
        skill_dir = write_skill(self.source, "demo-skill")
        sub = skill_dir / "sub"
        sub.mkdir()
        (sub / "f.txt").write_text("f\n")
        (skill_dir / "dirlink").symlink_to(sub, target_is_directory=True)
        proc = run_wm(
            "sync",
            "--skill",
            "demo-skill",
            "--source",
            str(self.source),
            "--workspace",
            str(self.ws),
            "--full",
        )
        self.assertEqual(proc.returncode, 1)
        self.assertIn("symlink to a directory", proc.stderr)

    def test_internal_file_symlink_allowed(self):
        skill_dir = write_skill(
            self.source, "demo-skill", extra_files={"real.md": "real\n"}
        )
        (skill_dir / "alias.md").symlink_to(skill_dir / "real.md")
        proc = run_wm(
            "sync",
            "--skill",
            "demo-skill",
            "--source",
            str(self.source),
            "--workspace",
            str(self.ws),
            "--full",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)


if __name__ == "__main__":
    unittest.main()
