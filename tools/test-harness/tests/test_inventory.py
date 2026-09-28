#!/usr/bin/env python3
"""Tests for the inventory tooling in evaluator.py (the "Inventory
tooling" section): load_inventory's unified rules.json/facts.json schema,
inventory-mint's document-order per-section id assignment and byte-
identical re-mint stability, and inventory-diff's new/changed/deleted/
excluded buckets. Stdlib only; no harness commands are ever invoked
(zero model spend)."""

import argparse
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import evaluator


def _rule_item(
    eid="R-overview-01",
    section="Overview",
    kind="discipline",
    statement="statement one",
    entries=None,
    **extra,
):
    item = {
        "id": eid,
        "section": section,
        "kind": kind,
        "statement": statement,
        "entries": ["entry-a"] if entries is None else entries,
    }
    item.update(extra)
    return item


def _fact_item(
    eid="F-overview-01",
    section="Overview",
    statement="statement one",
    entries=None,
    **extra,
):
    item = {
        "id": eid,
        "section": section,
        "statement": statement,
        "entries": ["entry-a"] if entries is None else entries,
    }
    item.update(extra)
    return item


def _excluded(
    eid="R-overview-99", section="Overview", kind: str | None = "discipline"
):
    entry = {
        "id": eid,
        "section": section,
        "reason": "routing reason",
    }
    if kind is not None:
        entry["kind"] = kind
    return entry


def _rule_inv(items=None, excluded=None):
    return {
        "skill": "test-skill",
        "generated": "2026-09-20",
        "rules": [_rule_item()] if items is None else items,
        "excluded": [] if excluded is None else excluded,
    }


def _fact_inv(items=None, excluded=None):
    return {
        "skill": "test-skill",
        "generated": "2026-09-20",
        "facts": [_fact_item()] if items is None else items,
        "excluded": [] if excluded is None else excluded,
    }


class _TmpCase(unittest.TestCase):
    """Base for the command tests: a throwaway dir plus helpers to write
    inventory files and capture _fail's exact stderr line."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)

    def write_json(self, data, name="inventory.json"):
        path = self.dir / name
        path.write_text(json.dumps(data, indent=2) + "\n")
        return path

    def fail_message(self, fn, *args, **kwargs):
        """Run fn expecting its _fail exit; return the exact stderr line."""
        stderr = io.StringIO()
        with (
            redirect_stderr(stderr),
            redirect_stdout(io.StringIO()),
            self.assertRaises(SystemExit) as cm,
        ):
            fn(*args, **kwargs)
        self.assertEqual(cm.exception.code, 1)
        return stderr.getvalue()


class SectionSlugTests(unittest.TestCase):
    """_section_slug / mint_inventory_id: the slug is lowercase, non-alnum
    runs collapse to '-', stripped; ids are <prefix>-<slug>-<nn>."""

    def test_heading_slug(self):
        self.assertEqual(
            evaluator._section_slug("## When to use"), "when-to-use"
        )

    def test_punctuation_runs_collapse(self):
        self.assertEqual(
            evaluator._section_slug("Rule inventory: gotchas (v2)!"),
            "rule-inventory-gotchas-v2",
        )

    def test_mint_format(self):
        self.assertEqual(
            evaluator.mint_inventory_id("R", "When to use", 3),
            "R-when-to-use-03",
        )
        self.assertEqual(
            evaluator.mint_inventory_id("F", "Overview", 12), "F-overview-12"
        )


class LoadInventoryTests(_TmpCase):
    """load_inventory: the unified schema both committed inventory shapes
    satisfy, and every rejection with its exact message."""

    def test_rule_shape_accepted(self):
        path = self.write_json(
            _rule_inv(items=[_rule_item()], excluded=[_excluded()])
        )
        inv = evaluator.load_inventory(path, "rule")
        self.assertEqual(len(inv["rules"]), 1)
        self.assertEqual(len(inv["excluded"]), 1)

    def test_fact_shape_accepted_without_kind(self):
        path = self.write_json(
            _fact_inv(items=[_fact_item()], excluded=[_excluded(kind=None)])
        )
        inv = evaluator.load_inventory(path, "fact")
        self.assertEqual(len(inv["facts"]), 1)

    def test_missing_file(self):
        stderr = self.fail_message(
            evaluator.load_inventory, self.dir / "nope.json", "rule"
        )
        self.assertEqual(
            stderr,
            f"error: inventory file not found: {self.dir / 'nope.json'}\n",
        )

    def test_invalid_json(self):
        path = self.dir / "bad.json"
        path.write_text("{not json")
        stderr = self.fail_message(evaluator.load_inventory, path, "rule")
        self.assertTrue(stderr.startswith(f"error: invalid JSON in {path}: "))

    def test_not_an_object(self):
        path = self.write_json([1, 2, 3], name="list.json")
        stderr = self.fail_message(evaluator.load_inventory, path, "rule")
        self.assertEqual(
            stderr,
            f"error: {path}: expected a JSON object with a 'rules' list\n",
        )

    def test_deleted_header_key(self):
        data = _rule_inv()
        del data["skill"]
        path = self.write_json(data)
        stderr = self.fail_message(evaluator.load_inventory, path, "rule")
        self.assertEqual(
            stderr,
            f"error: {path}: header skill missing 'skill' "
            "(non-empty string)\n",
        )

    def test_missing_generated(self):
        data = _rule_inv()
        del data["generated"]
        path = self.write_json(data)
        stderr = self.fail_message(evaluator.load_inventory, path, "rule")
        self.assertEqual(
            stderr,
            f"error: {path}: header generated missing 'generated' "
            "(non-empty string)\n",
        )

    def test_missing_item_array_for_kind(self):
        path = self.write_json(_rule_inv())
        stderr = self.fail_message(evaluator.load_inventory, path, "fact")
        self.assertEqual(stderr, f"error: {path}: missing 'facts' list\n")

    def test_missing_excluded_list(self):
        data = _rule_inv()
        del data["excluded"]
        path = self.write_json(data)
        stderr = self.fail_message(evaluator.load_inventory, path, "rule")
        self.assertEqual(stderr, f"error: {path}: missing 'excluded' list\n")

    def test_item_not_an_object(self):
        path = self.write_json(_rule_inv(items=["nope"]))
        stderr = self.fail_message(evaluator.load_inventory, path, "rule")
        self.assertEqual(stderr, f"error: {path}: item 0 is not an object\n")

    def test_rule_item_requires_kind_fact_item_does_not(self):
        item = _rule_item()
        del item["kind"]
        path = self.write_json(_rule_inv(items=[item]))
        stderr = self.fail_message(evaluator.load_inventory, path, "rule")
        self.assertEqual(
            stderr,
            f"error: {path}: item 0 missing 'kind' (non-empty string)\n",
        )
        fact_path = self.write_json(_fact_inv(), name="fact.json")
        evaluator.load_inventory(fact_path, "fact")  # no kind required: ok

    def test_item_missing_statement(self):
        item = _rule_item()
        del item["statement"]
        path = self.write_json(_rule_inv(items=[item]))
        stderr = self.fail_message(evaluator.load_inventory, path, "rule")
        self.assertEqual(
            stderr,
            f"error: {path}: item 0 missing 'statement' (non-empty string)\n",
        )

    def test_item_entries_must_be_list(self):
        item = _rule_item(entries="not-a-list")
        path = self.write_json(_rule_inv(items=[item]))
        stderr = self.fail_message(evaluator.load_inventory, path, "rule")
        self.assertEqual(
            stderr, f"error: {path}: item 0 missing 'entries' (list)\n"
        )

    def test_item_requires_id_unless_idless_allowed(self):
        item = _rule_item()
        del item["id"]
        path = self.write_json(_rule_inv(items=[item]))
        stderr = self.fail_message(evaluator.load_inventory, path, "rule")
        self.assertEqual(
            stderr,
            f"error: {path}: item 0 missing 'id' (non-empty string)\n",
        )
        inv = evaluator.load_inventory(path, "rule", allow_idless=True)
        self.assertNotIn("id", inv["rules"][0])

    def test_excluded_requires_id_unless_idless_allowed(self):
        entry = _excluded()
        del entry["id"]
        path = self.write_json(_rule_inv(excluded=[entry]))
        stderr = self.fail_message(evaluator.load_inventory, path, "rule")
        self.assertEqual(
            stderr,
            f"error: {path}: excluded entry 0 missing 'id' "
            "(non-empty string)\n",
        )
        inv = evaluator.load_inventory(path, "rule", allow_idless=True)
        self.assertNotIn("id", inv["excluded"][0])

    def test_excluded_requires_reason(self):
        entry = _excluded()
        del entry["reason"]
        path = self.write_json(_rule_inv(excluded=[entry]))
        stderr = self.fail_message(evaluator.load_inventory, path, "rule")
        self.assertEqual(
            stderr,
            f"error: {path}: excluded entry 0 missing 'reason' "
            "(non-empty string)\n",
        )

    def test_duplicate_id_within_items(self):
        path = self.write_json(
            _rule_inv(items=[_rule_item(), _rule_item(statement="other")])
        )
        stderr = self.fail_message(evaluator.load_inventory, path, "rule")
        self.assertEqual(
            stderr, f"error: {path}: duplicate id: R-overview-01\n"
        )

    def test_duplicate_id_item_vs_excluded(self):
        path = self.write_json(
            _rule_inv(excluded=[_excluded(eid="R-overview-01")])
        )
        stderr = self.fail_message(evaluator.load_inventory, path, "rule")
        self.assertEqual(
            stderr, f"error: {path}: duplicate id: R-overview-01\n"
        )

    def test_status_and_streak_accepted(self):
        item = _rule_item(status="ablation", ablation_streak=2)
        path = self.write_json(_rule_inv(items=[item]))
        inv = evaluator.load_inventory(path, "rule")
        self.assertEqual(inv["rules"][0]["status"], "ablation")
        self.assertEqual(inv["rules"][0]["ablation_streak"], 2)

    def test_removed_status_accepted_on_excluded(self):
        entry = {
            **_excluded(),
            "status": "removed",
            "ablation_streak": 0,
        }
        path = self.write_json(_rule_inv(excluded=[entry]))
        evaluator.load_inventory(path, "rule")

    def test_status_outside_vocabulary_rejected(self):
        item = _rule_item(status="archived", ablation_streak=1)
        path = self.write_json(_rule_inv(items=[item]))
        stderr = self.fail_message(evaluator.load_inventory, path, "rule")
        self.assertEqual(
            stderr,
            f"error: {path}: item 0 (R-overview-01) status must be "
            "'ablation' or 'removed', got 'archived'\n",
        )

    def test_status_without_streak_rejected(self):
        item = _rule_item(status="ablation")
        path = self.write_json(_rule_inv(items=[item]))
        stderr = self.fail_message(evaluator.load_inventory, path, "rule")
        self.assertEqual(
            stderr,
            f"error: {path}: item 0 (R-overview-01) ablation_streak must "
            "be an int >= 0 when status is present, got None\n",
        )

    def test_bool_streak_rejected(self):
        item = _rule_item(status="removed", ablation_streak=True)
        path = self.write_json(_rule_inv(items=[item]))
        stderr = self.fail_message(evaluator.load_inventory, path, "rule")
        self.assertIn("ablation_streak must be an int >= 0", stderr)

    def test_negative_streak_rejected(self):
        item = _rule_item(status="ablation", ablation_streak=-1)
        path = self.write_json(_rule_inv(items=[item]))
        stderr = self.fail_message(evaluator.load_inventory, path, "rule")
        self.assertIn("ablation_streak must be an int >= 0", stderr)

    def test_streak_without_status_rejected(self):
        item = _rule_item(ablation_streak=0)
        path = self.write_json(_rule_inv(items=[item]))
        stderr = self.fail_message(evaluator.load_inventory, path, "rule")
        self.assertEqual(
            stderr,
            f"error: {path}: item 0 (R-overview-01) has ablation_streak "
            "but no status\n",
        )

    def test_fact_item_status_validated(self):
        item = _fact_item(status="ablation")  # no streak
        path = self.write_json(_fact_inv(items=[item]), name="facts.json")
        stderr = self.fail_message(evaluator.load_inventory, path, "fact")
        self.assertIn("ablation_streak must be an int >= 0", stderr)


class InventoryCheckCommandTests(_TmpCase):
    """cmd_inventory_check: validates and reports id stats on stdout."""

    def _args(self, path, kind="rule"):
        return argparse.Namespace(inventory=str(path), kind=kind)

    def test_check_reports_stats(self):
        path = self.write_json(
            _rule_inv(
                items=[
                    _rule_item(),
                    _rule_item(eid="R-other-01", section="B"),
                ],
                excluded=[_excluded()],
            )
        )
        stdout = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(io.StringIO()):
            rc = evaluator.cmd_inventory_check(self._args(path))
        self.assertEqual(rc, 0)
        self.assertEqual(
            stdout.getvalue(),
            f"{path}: 2 rules in 2 sections, 1 excluded\n",
        )

    def test_check_rejects_idless_draft(self):
        item = _rule_item()
        del item["id"]
        path = self.write_json(_rule_inv(items=[item]))
        stderr = self.fail_message(
            evaluator.cmd_inventory_check, self._args(path)
        )
        self.assertEqual(
            stderr,
            f"error: {path}: item 0 missing 'id' (non-empty string)\n",
        )


class InventoryMintCommandTests(_TmpCase):
    """cmd_inventory_mint: document-order per-section numbering, byte-
    identical re-mint stability."""

    def _args(self, path, out, kind="rule", carry=None):
        return argparse.Namespace(
            inventory=str(path),
            kind=kind,
            out=str(out),
            carry=None if carry is None else str(carry),
        )

    def _mint(self, data, name="draft.json", kind="rule", carry=None):
        path = self.write_json(data, name=name)
        out = self.dir / "minted.json"
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            rc = evaluator.cmd_inventory_mint(
                self._args(path, out, kind, carry=carry)
            )
        self.assertEqual(rc, 0)
        return path, out

    def test_mint_assigns_ids_document_order_per_section(self):
        draft = _rule_inv(
            items=[
                _rule_item(eid="", section="Overview"),
                _rule_item(eid="", section="Inputs"),
                _rule_item(eid="", section="Overview"),
            ]
        )
        for item in draft["rules"]:
            del item["id"]
        _, out = self._mint(draft)
        minted = json.loads(out.read_text())
        self.assertEqual(
            [item["id"] for item in minted["rules"]],
            ["R-overview-01", "R-inputs-01", "R-overview-02"],
        )

    def test_mint_heading_slug_id_format(self):
        draft = _rule_inv(
            items=[
                _rule_item(eid="", section="## When to use"),
                _rule_item(eid="", section="## When to use"),
                _rule_item(eid="", section="## When to use"),
            ]
        )
        for item in draft["rules"]:
            del item["id"]
        _, out = self._mint(draft)
        minted = json.loads(out.read_text())
        self.assertEqual(
            [item["id"] for item in minted["rules"]],
            [
                "R-when-to-use-01",
                "R-when-to-use-02",
                "R-when-to-use-03",
            ],
        )

    def test_mint_fact_kind_uses_f_prefix(self):
        draft = _fact_inv(items=[_fact_item(eid="")])
        del draft["facts"][0]["id"]
        _, out = self._mint(draft, name="facts.json", kind="fact")
        minted = json.loads(out.read_text())
        self.assertEqual(minted["facts"][0]["id"], "F-overview-01")

    def test_mint_keeps_existing_ids_and_skips_their_numbers(self):
        draft = _rule_inv(
            items=[
                _rule_item(eid="R-overview-07"),
                _rule_item(eid="", statement="second"),
            ]
        )
        del draft["rules"][1]["id"]
        _, out = self._mint(draft)
        minted = json.loads(out.read_text())
        self.assertEqual(
            [item["id"] for item in minted["rules"]],
            ["R-overview-07", "R-overview-01"],
        )

    def test_mint_assigns_ids_to_idless_excluded(self):
        draft = _rule_inv(
            items=[_rule_item()],
            excluded=[_excluded(eid="", section="Overview")],
        )
        del draft["excluded"][0]["id"]
        _, out = self._mint(draft)
        minted = json.loads(out.read_text())
        self.assertEqual(minted["excluded"][0]["id"], "R-overview-02")
        self.assertEqual(list(minted["excluded"][0].keys())[0], "id")

    def test_mint_never_collides_with_excluded_ids(self):
        """The B1 repro: an id-less item plus excluded 'R-content-01' in
        the same section used to mint the item 'R-content-01' — a
        duplicate that only surfaced at the next command. The shared
        per-section pool now skips the excluded number."""
        draft = _rule_inv(
            items=[_rule_item(eid="", section="Content")],
            excluded=[_excluded(eid="R-content-01", section="Content")],
        )
        del draft["rules"][0]["id"]
        _, out = self._mint(draft)
        minted = json.loads(out.read_text())
        self.assertEqual(minted["rules"][0]["id"], "R-content-02")
        evaluator.load_inventory(out, "rule")  # no duplicate-id error

    def test_mint_idless_item_and_excluded_share_section_pool(self):
        draft = _rule_inv(
            items=[_rule_item(eid="")],
            excluded=[_excluded(eid="")],
        )
        del draft["rules"][0]["id"]
        del draft["excluded"][0]["id"]
        _, out = self._mint(draft)
        minted = json.loads(out.read_text())
        self.assertEqual(minted["rules"][0]["id"], "R-overview-01")
        self.assertEqual(minted["excluded"][0]["id"], "R-overview-02")
        evaluator.load_inventory(out, "rule")

    def test_mint_fact_kind_excluded_without_kind_field(self):
        draft = _fact_inv(
            items=[_fact_item(eid="")],
            excluded=[_excluded(eid="", kind=None)],
        )
        del draft["facts"][0]["id"]
        del draft["excluded"][0]["id"]
        _, out = self._mint(draft, name="facts.json", kind="fact")
        minted = json.loads(out.read_text())
        self.assertEqual(minted["facts"][0]["id"], "F-overview-01")
        self.assertEqual(minted["excluded"][0]["id"], "F-overview-02")
        self.assertNotIn("kind", minted["excluded"][0])
        evaluator.load_inventory(out, "fact")

    def test_remint_after_excluded_mint_is_byte_identical(self):
        draft = _rule_inv(
            items=[_rule_item(eid="")],
            excluded=[_excluded(eid="")],
        )
        del draft["rules"][0]["id"]
        del draft["excluded"][0]["id"]
        path = self.write_json(draft)
        first = self.dir / "first.json"
        second = self.dir / "second.json"
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(
                evaluator.cmd_inventory_mint(self._args(path, first)), 0
            )
            self.assertEqual(
                evaluator.cmd_inventory_mint(self._args(first, second)), 0
            )
        self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_remint_is_byte_identical(self):
        inv = _rule_inv(
            items=[_rule_item(), _rule_item(eid="R-other-01", section="B")],
            excluded=[_excluded()],
        )
        path = self.write_json(inv)
        first = self.dir / "first.json"
        second = self.dir / "second.json"
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(
                evaluator.cmd_inventory_mint(self._args(path, first)), 0
            )
            self.assertEqual(
                evaluator.cmd_inventory_mint(self._args(first, second)), 0
            )
        self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_mint_on_fully_ided_file_passes_bytes_through(self):
        """The stability rule: a file that already has every id comes out
        byte-identical, whatever its house formatting (the committed
        inventories do not round-trip through json.dumps)."""
        raw = (
            '{"skill": "s", "generated": "g", "rules": [{"id": "R-a-01", '
            '"section": "A", "kind": "discipline", "statement": "s", '
            '"entries": []}], "excluded": []}\n'
        )
        path = self.dir / "house-style.json"
        path.write_text(raw)
        out = self.dir / "out.json"
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            rc = evaluator.cmd_inventory_mint(self._args(path, out))
        self.assertEqual(rc, 0)
        self.assertEqual(out.read_text(), raw)

    def test_mint_creates_missing_output_parent_dirs(self):
        # Issue #54: --out naming not-yet-existing subdirs works (the
        # record convention), instead of crashing FileNotFoundError.
        path = self.write_json(_rule_inv())
        out = self.dir / "nested" / "dir" / "minted.json"
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            rc = evaluator.cmd_inventory_mint(self._args(path, out))
        self.assertEqual(rc, 0)
        self.assertTrue(out.is_file())

    def test_mint_unwritable_output_fails_cleanly(self):
        blocker = self.dir / "blocker"
        blocker.write_text("x")
        out = blocker / "sub" / "out.json"
        stderr = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(stderr):
            rc = evaluator.cmd_inventory_mint(
                self._args(self.write_json(_rule_inv()), out)
            )
        self.assertEqual(rc, 1)
        self.assertIn("error: could not write", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())


class InventoryMintCarryTests(_TmpCase):
    """inventory-mint --carry: status/ablation_streak carry forward onto
    surviving ids; old items whose status is 'removed' are re-appended
    verbatim (their rule text is already deleted from the doc, so the
    fresh draft never contains them); dropped ablation/status-less items
    stay dropped."""

    def _mint(self, draft, old, name="draft.json", kind="rule"):
        path = self.write_json(draft, name=name)
        old_path = self.write_json(old, name="old.json")
        out = self.dir / "minted.json"
        stdout = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(io.StringIO()):
            rc = evaluator.cmd_inventory_mint(
                argparse.Namespace(
                    inventory=str(path),
                    kind=kind,
                    out=str(out),
                    carry=str(old_path),
                )
            )
        self.assertEqual(rc, 0)
        return path, out, stdout.getvalue()

    def test_surviving_id_keeps_status(self):
        draft = _rule_inv(items=[_rule_item()])
        old = _rule_inv(
            items=[_rule_item(status="ablation", ablation_streak=1)]
        )
        _, out, _ = self._mint(draft, old)
        (item,) = json.loads(out.read_text())["rules"]
        self.assertEqual(item["status"], "ablation")
        self.assertEqual(item["ablation_streak"], 1)

    def test_removed_item_absent_from_draft_is_reappended(self):
        removed = _rule_item(
            eid="R-gone-01",
            section="Gone",
            status="removed",
            ablation_streak=3,
        )
        draft = _rule_inv(items=[_rule_item()])
        old = _rule_inv(items=[_rule_item(), removed])
        _, out, _ = self._mint(draft, old)
        items = json.loads(out.read_text())["rules"]
        self.assertEqual(
            [i["id"] for i in items], ["R-overview-01", "R-gone-01"]
        )
        self.assertEqual(items[1], removed)

    def test_dropped_ablation_item_is_not_reappended(self):
        ablation = _rule_item(
            eid="R-gone-01",
            section="Gone",
            status="ablation",
            ablation_streak=1,
        )
        draft = _rule_inv(items=[_rule_item()])
        old = _rule_inv(items=[_rule_item(), ablation])
        _, out, _ = self._mint(draft, old)
        items = json.loads(out.read_text())["rules"]
        self.assertEqual([i["id"] for i in items], ["R-overview-01"])

    def test_carry_noop_is_byte_identical(self):
        # No mints and no carries: the raw input bytes pass through.
        inv = _rule_inv(items=[_rule_item()])
        raw = json.dumps(inv, indent=2) + "\n"
        path = self.dir / "canonical.json"
        path.write_text(raw)
        old_path = self.write_json(_rule_inv(), name="old.json")
        out = self.dir / "out.json"
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            rc = evaluator.cmd_inventory_mint(
                argparse.Namespace(
                    inventory=str(path),
                    kind="rule",
                    out=str(out),
                    carry=str(old_path),
                )
            )
        self.assertEqual(rc, 0)
        self.assertEqual(out.read_bytes(), raw.encode())

    def test_carry_fact_kind(self):
        draft = _fact_inv(items=[_fact_item()])
        old = _fact_inv(
            items=[_fact_item(status="removed", ablation_streak=5)]
        )
        path, out, _ = self._mint(draft, old, name="facts.json", kind="fact")
        self.assertTrue(path.exists())
        (item,) = json.loads(out.read_text())["facts"]
        self.assertEqual(item["status"], "removed")
        self.assertEqual(item["ablation_streak"], 5)


class InventoryDiffTests(unittest.TestCase):
    """inventory_diff: the four buckets, the resurrect case, and the
    deleted-vs-excluded distinction. Pure function, no I/O."""

    def test_no_op_diff_is_empty(self):
        inv = _rule_inv(items=[_rule_item()], excluded=[_excluded()])
        diff = evaluator.inventory_diff(inv, json.loads(json.dumps(inv)))
        self.assertEqual(
            diff, {"new": [], "changed": [], "deleted": [], "excluded": []}
        )

    def test_new_bucket(self):
        old = _rule_inv(items=[_rule_item()])
        new_item = _rule_item(eid="R-inputs-01", section="Inputs")
        new = _rule_inv(items=[_rule_item(), new_item])
        diff = evaluator.inventory_diff(old, new)
        self.assertEqual(diff["new"], [new_item])
        self.assertEqual(diff["changed"], [])
        self.assertEqual(diff["deleted"], [])

    def test_changed_bucket_reports_fields(self):
        old = _rule_inv(items=[_rule_item()])
        new_item = _rule_item(statement="reworded", entries=["other"])
        new = _rule_inv(items=[new_item])
        diff = evaluator.inventory_diff(old, new)
        self.assertEqual(len(diff["changed"]), 1)
        change = diff["changed"][0]
        self.assertEqual(change["id"], "R-overview-01")
        self.assertEqual(change["fields"], ["statement", "entries"])
        self.assertEqual(change["old"]["statement"], "statement one")
        self.assertEqual(change["new"]["statement"], "reworded")

    def test_kind_difference_counts_as_changed(self):
        old = _rule_inv(items=[_rule_item()])
        new = _rule_inv(items=[_rule_item(kind="pattern")])
        diff = evaluator.inventory_diff(old, new)
        self.assertEqual(diff["changed"][0]["fields"], ["kind"])

    def test_deleted_bucket(self):
        old = _rule_inv(items=[_rule_item()])
        new = _rule_inv(items=[])
        diff = evaluator.inventory_diff(old, new)
        self.assertEqual(
            [item["id"] for item in diff["deleted"]], ["R-overview-01"]
        )

    def test_moved_to_excluded_is_not_deleted(self):
        """An old item that lands in new.excluded is a 'newly-excluded'
        state change, not a deletion."""
        old = _rule_inv(items=[_rule_item()])
        moved = _excluded(eid="R-overview-01")
        new = _rule_inv(items=[], excluded=[moved])
        diff = evaluator.inventory_diff(old, new)
        self.assertEqual(diff["deleted"], [])
        self.assertEqual(
            diff["excluded"], [{**moved, "status": "newly-excluded"}]
        )

    def test_resurrected_item_is_annotated_not_new(self):
        old = _rule_inv(items=[], excluded=[_excluded(eid="R-overview-01")])
        item = _rule_item()
        new = _rule_inv(items=[item])
        diff = evaluator.inventory_diff(old, new)
        self.assertEqual(diff["new"], [])
        self.assertEqual(
            diff["excluded"],
            [{**_excluded(eid="R-overview-01"), "status": "resurrected"}],
        )

    def test_still_excluded_is_omitted(self):
        """A no-op exclusion appears in no bucket, keeping a no-op diff
        empty in all four."""
        entry = _excluded()
        old = _rule_inv(excluded=[entry])
        new = _rule_inv(excluded=[json.loads(json.dumps(entry))])
        diff = evaluator.inventory_diff(old, new)
        self.assertEqual(diff["excluded"], [])

    def test_fact_shape_diff(self):
        old = _fact_inv(items=[_fact_item()])
        new = _fact_inv(items=[_fact_item(statement="changed")])
        diff = evaluator.inventory_diff(old, new)
        self.assertEqual(len(diff["changed"]), 1)
        self.assertEqual(diff["changed"][0]["fields"], ["statement"])

    def test_status_and_streak_are_silent_metadata(self):
        # status/ablation_streak never join the changed-fields
        # comparison: close-out bookkeeping must not surface as drift.
        old = _rule_inv(items=[_rule_item()])
        new = _rule_inv(
            items=[_rule_item(status="ablation", ablation_streak=2)]
        )
        diff = evaluator.inventory_diff(old, new)
        self.assertEqual(
            diff, {"new": [], "changed": [], "deleted": [], "excluded": []}
        )


class InventoryDiffCommandTests(_TmpCase):
    """cmd_inventory_diff: JSON to --out or stdout, and the exit-1 gates
    (schema, slug drift on new ids, changed-item invariant)."""

    def _args(self, old, new, kind="rule", out=None):
        return argparse.Namespace(
            old=str(old),
            new=str(new),
            kind=kind,
            out=None if out is None else str(out),
        )

    def test_diff_writes_json_to_out(self):
        old_path = self.write_json(_rule_inv(), name="old.json")
        new_path = self.write_json(_rule_inv(), name="new.json")
        out = self.dir / "diff.json"
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            rc = evaluator.cmd_inventory_diff(
                self._args(old_path, new_path, out=out)
            )
        self.assertEqual(rc, 0)
        diff = json.loads(out.read_text())
        self.assertEqual(diff["new"], [])
        self.assertEqual(diff["changed"], [])

    def test_diff_prints_json_to_stdout_without_out(self):
        old_path = self.write_json(_rule_inv(), name="old.json")
        new_item = _rule_item(eid="R-inputs-01", section="Inputs")
        new_path = self.write_json(
            _rule_inv(items=[_rule_item(), new_item]), name="new.json"
        )
        stdout = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(io.StringIO()):
            rc = evaluator.cmd_inventory_diff(self._args(old_path, new_path))
        self.assertEqual(rc, 0)
        diff = json.loads(stdout.getvalue())
        self.assertEqual([item["id"] for item in diff["new"]], ["R-inputs-01"])

    def test_schema_violation_exits_1(self):
        old_path = self.write_json(_rule_inv(), name="old.json")
        broken = _rule_inv()
        del broken["skill"]
        new_path = self.write_json(broken, name="new.json")
        stderr = self.fail_message(
            evaluator.cmd_inventory_diff, self._args(old_path, new_path)
        )
        self.assertEqual(
            stderr,
            f"error: {new_path}: header skill missing 'skill' "
            "(non-empty string)\n",
        )

    def test_slug_drift_on_new_id_exits_1(self):
        old_path = self.write_json(_rule_inv(), name="old.json")
        drifted = _rule_item(eid="R-wrong-slug-01", section="Overview")
        new_path = self.write_json(
            _rule_inv(items=[_rule_item(), drifted]), name="new.json"
        )
        stderr = io.StringIO()
        with (
            redirect_stderr(stderr),
            redirect_stdout(io.StringIO()),
        ):
            rc = evaluator.cmd_inventory_diff(self._args(old_path, new_path))
        self.assertEqual(rc, 1)
        self.assertEqual(
            stderr.getvalue(),
            f"error: {new_path}: item 1 id 'R-wrong-slug-01' does not match "
            "its section 'Overview' (expected 'R-overview-<nn>')\n",
        )

    def test_drifted_id_known_to_old_is_grandfathered(self):
        """The silent-mis-diff-proof property at unit scale: an id that
        --old already knows keeps its historical slug without error, so a
        no-op diff on unmodified copies stays a no-op (the committed
        inventories carry exactly this drift)."""
        old_path = self.write_json(
            _rule_inv(items=[_rule_item(eid="R-historic-01")]), name="old.json"
        )
        reworded = _rule_item(eid="R-historic-01", statement="reworded")
        new_path = self.write_json(
            _rule_inv(items=[reworded]), name="new.json"
        )
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            rc = evaluator.cmd_inventory_diff(self._args(old_path, new_path))
        self.assertEqual(rc, 0)

    def test_one_statement_change_reports_exactly_one_changed(self):
        """The synthetic edit round-trip: one statement edit surfaces as
        exactly one changed item, so the buckets fire on real content."""
        old_path = self.write_json(
            _rule_inv(
                items=[_rule_item(), _rule_item(eid="R-other-01", section="B")]
            ),
            name="old.json",
        )
        new_path = self.write_json(
            _rule_inv(
                items=[
                    _rule_item(statement="edited statement"),
                    _rule_item(eid="R-other-01", section="B"),
                ]
            ),
            name="new.json",
        )
        out = self.dir / "diff.json"
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            rc = evaluator.cmd_inventory_diff(
                self._args(old_path, new_path, out=out)
            )
        self.assertEqual(rc, 0)
        diff = json.loads(out.read_text())
        self.assertEqual(len(diff["changed"]), 1)
        self.assertEqual(diff["changed"][0]["id"], "R-overview-01")
        self.assertEqual(diff["changed"][0]["fields"], ["statement"])
        self.assertEqual(diff["new"], [])
        self.assertEqual(diff["deleted"], [])
        self.assertEqual(diff["excluded"], [])

    def test_diff_creates_missing_output_parent_dirs(self):
        # Issue #54: --out naming not-yet-existing subdirs works (the
        # record convention), instead of crashing FileNotFoundError.
        old_path = self.write_json(_rule_inv(), name="old.json")
        new_path = self.write_json(_rule_inv(), name="new.json")
        out = self.dir / "nested" / "dir" / "diff.json"
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            rc = evaluator.cmd_inventory_diff(
                self._args(old_path, new_path, out=out)
            )
        self.assertEqual(rc, 0)
        self.assertTrue(out.is_file())

    def test_diff_unwritable_output_fails_cleanly(self):
        old_path = self.write_json(_rule_inv(), name="old.json")
        new_path = self.write_json(_rule_inv(), name="new.json")
        blocker = self.dir / "blocker"
        blocker.write_text("x")
        stderr = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(stderr):
            rc = evaluator.cmd_inventory_diff(
                self._args(old_path, new_path, out=blocker / "sub" / "d.json")
            )
        self.assertEqual(rc, 1)
        self.assertIn("error: could not write", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())


class InventoryUpdateTests(_TmpCase):
    """cmd_inventory_update: the deterministic close-out. A control pass
    auto-marks a status-less item (ablation, streak 0) or increments an
    existing streak; a control fail clears an ablation item entirely
    (load-bearing — back to normal testing) or resets a removed item's
    streak with a regression-failure line; voids and uncovered items
    are untouched."""

    def _run(self, inv, scored_entries, kind="rule"):
        path = self.write_json(inv)
        scored = self.write_json({"entries": scored_entries}, name="s.json")
        out = self.dir / "out.json"
        stdout = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(io.StringIO()):
            rc = evaluator.cmd_inventory_update(
                argparse.Namespace(
                    manifest=str(path),
                    kind=kind,
                    scored=str(scored),
                    out=str(out),
                )
            )
        self.assertEqual(rc, 0)
        return json.loads(out.read_text()), stdout.getvalue()

    def test_control_pass_auto_marks_statusless_item(self):
        inv = _rule_inv(items=[_rule_item()])
        updated, out = self._run(
            inv, [{"id": "entry-a", "result": "no-failure"}]
        )
        (item,) = updated["rules"]
        self.assertEqual(item["status"], "ablation")
        self.assertEqual(item["ablation_streak"], 0)
        self.assertIn(
            "inventory-update: 1 auto-marked, 0 streaks incremented, "
            "0 streaks reset, 0 regression failures",
            out,
        )

    def test_control_pass_increments_existing_streak(self):
        inv = _rule_inv(
            items=[_rule_item(status="ablation", ablation_streak=2)]
        )
        updated, out = self._run(
            inv, [{"id": "entry-a", "result": "no-failure"}]
        )
        (item,) = updated["rules"]
        self.assertEqual(item["status"], "ablation")
        self.assertEqual(item["ablation_streak"], 3)
        self.assertIn("1 streaks incremented", out)

    def test_control_fail_clears_ablation_item(self):
        inv = _rule_inv(
            items=[_rule_item(status="ablation", ablation_streak=2)]
        )
        updated, out = self._run(inv, [{"id": "entry-a", "result": "adopted"}])
        (item,) = updated["rules"]
        self.assertNotIn("status", item)
        self.assertNotIn("ablation_streak", item)
        self.assertIn(
            "load-bearing: R-overview-01 — control failed; status "
            "cleared (back to normal testing)",
            out,
        )
        self.assertIn("1 streaks reset", out)

    def test_control_fail_on_removed_resets_and_reports(self):
        inv = _rule_inv(
            items=[_rule_item(status="removed", ablation_streak=4)]
        )
        updated, out = self._run(
            inv, [{"id": "entry-a", "result": "bulletproof"}]
        )
        (item,) = updated["rules"]
        self.assertEqual(item["status"], "removed")
        self.assertEqual(item["ablation_streak"], 0)
        self.assertIn(
            "regression failure: R-overview-01 — control failed; "
            "the deletion may have been wrong",
            out,
        )
        self.assertIn("1 regression failures", out)

    def test_void_control_leaves_streak_untouched(self):
        inv = _rule_inv(
            items=[_rule_item(status="ablation", ablation_streak=2)]
        )
        updated, out = self._run(inv, [{"id": "entry-a", "result": "void"}])
        (item,) = updated["rules"]
        self.assertEqual(item["ablation_streak"], 2)
        self.assertIn(
            "inventory-update: 0 auto-marked, 0 streaks incremented, "
            "0 streaks reset, 0 regression failures",
            out,
        )

    def test_item_without_scored_entries_untouched(self):
        inv = _rule_inv(
            items=[_rule_item(status="ablation", ablation_streak=1)]
        )
        updated, _out = self._run(inv, [])
        (item,) = updated["rules"]
        self.assertEqual(item["ablation_streak"], 1)

    def test_any_fail_beats_any_pass(self):
        inv = _rule_inv(items=[_rule_item(entries=["e1", "e2"])])
        updated, out = self._run(
            inv,
            [
                {"id": "e1", "result": "no-failure"},
                {"id": "e2", "result": "adopted"},
            ],
        )
        (item,) = updated["rules"]
        self.assertNotIn("status", item)

    def test_fact_kind_reads_the_control_field(self):
        inv = _fact_inv(
            items=[_fact_item(status="ablation", ablation_streak=1)]
        )
        updated, _out = self._run(
            inv, [{"id": "entry-a", "control": "pass"}], kind="fact"
        )
        (item,) = updated["facts"]
        self.assertEqual(item["ablation_streak"], 2)

    def test_fact_kind_control_fail_clears_ablation(self):
        inv = _fact_inv(
            items=[_fact_item(status="ablation", ablation_streak=1)]
        )
        updated, out = self._run(
            inv, [{"id": "entry-a", "control": "fail"}], kind="fact"
        )
        (item,) = updated["facts"]
        self.assertNotIn("status", item)
        self.assertIn("load-bearing: F-overview-01", out)

    def test_fact_kind_control_void_untouched(self):
        inv = _fact_inv(
            items=[_fact_item(status="ablation", ablation_streak=1)]
        )
        updated, _out = self._run(
            inv, [{"id": "entry-a", "control": "void"}], kind="fact"
        )
        (item,) = updated["facts"]
        self.assertEqual(item["ablation_streak"], 1)

    def test_scored_file_missing_is_a_clean_error(self):
        path = self.write_json(_rule_inv())
        stderr = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(stderr):
            rc = evaluator.cmd_inventory_update(
                argparse.Namespace(
                    manifest=str(path),
                    kind="rule",
                    scored=str(self.dir / "nope.json"),
                    out=str(self.dir / "out.json"),
                )
            )
        self.assertEqual(rc, 1)
        self.assertIn("error: scored file not found:", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
