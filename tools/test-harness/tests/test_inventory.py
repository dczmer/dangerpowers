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
):
    return {
        "id": eid,
        "section": section,
        "kind": kind,
        "statement": statement,
        "entries": ["entry-a"] if entries is None else entries,
    }


def _fact_item(
    eid="F-overview-01",
    section="Overview",
    statement="statement one",
    entries=None,
):
    return {
        "id": eid,
        "section": section,
        "statement": statement,
        "entries": ["entry-a"] if entries is None else entries,
    }


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

    def _args(self, path, out, kind="rule"):
        return argparse.Namespace(inventory=str(path), kind=kind, out=str(out))

    def _mint(self, data, name="draft.json", kind="rule"):
        path = self.write_json(data, name=name)
        out = self.dir / "minted.json"
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            rc = evaluator.cmd_inventory_mint(self._args(path, out, kind))
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


if __name__ == "__main__":
    unittest.main()
