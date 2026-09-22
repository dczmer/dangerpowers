"""The Track base class and the shared track plumbing.

Track strategies: per-track campaign behavior behind one interface.
The four test tracks share a meta-process (suite → evidence → scored-check
→ record); the track modules are the single place that knows what
differs. The CLI drivers in evaluator.py call these hooks; nothing here
parses argv beyond reading attributes off the args namespace.

This module is the base of the tracks package: every track module
imports from it, and it never imports from a track module.
"""

import argparse
from pathlib import Path
from typing import Any, Callable

from src.strategies import EvalStrategy, _fail, check_harness


class _HarnessPreflight:
    """Default harness preflight for Track._harness_preflight: the
    strategies implementation. The evaluator's generic run_suite driver
    rebinds track._harness_preflight to its own module-level
    check_harness before pre_spend_gates, so the test suite's historical
    patch point (evaluator.check_harness) keeps working without the
    tracks package ever importing evaluator."""

    def __call__(
        self, name: str, strategy_cls: type[EvalStrategy], model: str | None
    ) -> None:
        check_harness(name, strategy_cls, model)


def _required(args: argparse.Namespace, track: "Track", *names: str) -> None:
    """Runtime replacement for argparse required=True on merged flags
    (Q7a): the first missing flag fails with the exact message."""
    for n in names:
        if getattr(args, n, None) is None:
            flag = f"--{n.replace('_', '-')}"
            _fail(f"{flag} is required with --track {track.name}")


class Track:
    """One track's campaign behavior. Class attributes are track data
    (the registry); methods are the four-step interface plus suite
    internals. All failures print the exact historical message and either
    return an int rc (preferred, matches the suite commands' style) or
    _fail/sys.exit (pre-spend gates, matches load_entries)."""

    # Harness preflight hook called at each track's historical
    # check_harness position inside pre_spend_gates. The default is the
    # strategies implementation; run_suite overwrites it with evaluator's
    # check_harness binding (see _HarnessPreflight above).
    _harness_preflight: Callable[
        [str, type[EvalStrategy], str | None], None
    ] = _HarnessPreflight()

    # ---- identity / registry data ----
    name: str  # manifest key and CLI --track choice, e.g. "retrieval-test"
    inventory_kind: str | None  # "fact" | "rule" | None (Q4a)
    results_noun: str  # envelope word: "not a {noun}-suite results file"
    # ---- suite ----
    agents: tuple[str, ...] = ()  # eval agent names for pre-spend validation
    zero_results_on_empty: bool = False  # trigger: empty input writes zeros
    # ---- scored ----
    supports_scored: bool = True
    multi_results: bool = False  # repeated --results (shape/pressure) (Q6a)
    union_hook: Callable[[Path, dict, dict], str | None] | None = None
    skeleton_header: bool = False  # retrieval/pressure skeletons carry one
    scored_object_phrase: str = "a JSON object"  # pressure says "an object"
    count_arg_names: tuple[str, ...] = ()  # scored-check counts flags, dests
    count_result_names: tuple[str, ...] = ()  # parallel result vocabulary
    sum_keys: dict[str, str] = {}  # result value -> manifest count key
    # ---- meta ----
    supports_meta: bool = False

    # ---- suite hooks ----

    def pre_spend_gates(
        self, args: argparse.Namespace, strategy_cls: type[EvalStrategy]
    ) -> list[Any] | int:
        """Every check that must pass before the first harness invocation,
        in the track's historical order (check_harness included, at the
        position the track has always had it). Returns the validated
        entries, or an int rc with the exact error already printed."""
        raise NotImplementedError

    def write_empty(self, args: argparse.Namespace) -> None:
        """zero_results_on_empty tracks only: write the zeroed envelope and
        the note line, replacing the early return in the old cmd_suite."""

    def install_agents(self, strategy: EvalStrategy, args) -> None:
        """strategy.install(...) calls for every workspace/agent pair."""

    def banner(self, args: argparse.Namespace, n: int) -> list[str]:
        """The emit lines between install and the first entry."""
        raise NotImplementedError

    def run_entry(
        self, strategy: EvalStrategy, entry: Any, args: argparse.Namespace
    ) -> dict | int:
        """Run one entry (all its arms) and return its results record, or
        an int rc when an arm aborts mid-campaign (retrieval's
        catch-and-propagate, Q2a). Per-entry progress lines are emitted
        here, matching each track's historical format."""
        raise NotImplementedError

    def extra_config(self, args: argparse.Namespace) -> dict:
        """Track keys merged into base_config (queries/entries/scenarios
        path, arms, fixture_key, arm, skill_file, ...)."""
        return {}

    def finalize(self, config: dict, results: list[dict]) -> dict:
        """The results file document. Default: {config, entries}; trigger
        overrides with its top-level queries/totals envelope."""
        return {"config": config, "entries": results}

    def done_line(self, n: int, out: Path) -> str:
        """The final emit line after the results write."""
        raise NotImplementedError

    # ---- evidence ----

    def print_evidence(self, args: argparse.Namespace) -> int:
        """The track's evidence printer (extraction only; exit 0 with a
        count line, exit 1 on a malformed file). Trigger's implementation
        reads the queries envelope; the others share load_results_json +
        iter_evidence from common."""
        raise NotImplementedError

    # ---- scored ----

    def skeleton_entry(self, eid: str, extras: dict) -> dict:
        """One scored.json skeleton entry (judgment fields null; the
        mechanically derivable fields pre-filled)."""
        raise NotImplementedError

    def check_scored_entry(
        self,
        scored_path: Path,
        entry: dict,
        arms: set[str],
        extras: dict,
    ) -> int | None:
        """Per-entry scored validation beyond coverage: vocabularies,
        implication rules, verbatim requirements. Returns _err(...) on
        violation, None when the entry passes."""
        raise NotImplementedError

    def scored_signal(self, entry: dict) -> bool:
        """True when the entry carries this track's discriminating
        vocabulary (record --scored track detection)."""
        return False

    # ---- meta ----

    def run_meta(self, args: argparse.Namespace, strategy_cls) -> int:
        """supports_meta tracks only: the session-resume command."""
        raise NotImplementedError
