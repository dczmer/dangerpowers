#!/usr/bin/env python3
"""Harness strategy layer for the evaluator.

Defines the verdict vocabulary (Verdict, EventStream, HarnessExecutionError),
the harness-neutral signal classification (classify), the EvalStrategy
protocol, and the strategy registry. Only opencode is implemented.

Imported by evaluator.py; nothing here imports evaluator.
"""

import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

Outcome = Literal["triggered", "not-triggered", "void"]

SKILL_DIR = Path(__file__).resolve().parents[1]
AGENTS_DIR = SKILL_DIR / "agents"


@dataclass
class Verdict:
    outcome: Outcome
    detail: str = ""  # timeout note or signal status
    session_id: str = ""
    reasoning: str = (
        ""  # concatenated --thinking blocks; never used for scoring
    )
    timeout: bool = False  # True for interrupted runs (subprocess timeout or
    # step-cap cutoff)


class HarnessExecutionError(Exception):
    """The harness could not execute the query (bad args, nonzero exit,
    provider error, empty event stream, agent fallback). Fatal: aborts the
    batch, exits 1. Never a verdict."""


# --------------------------------------------------------------------------
# Signal detection

REPORT_LOADED_RE = re.compile(
    r"loaded skill:\s*[*_`]*([A-Za-z0-9][\w-]*)", re.IGNORECASE
)
REPORT_NO_MATCH_RE = re.compile(r"no skill matched", re.IGNORECASE)


@dataclass
class EventStream:
    """Structured result of parsing one event stream (complete or partial).
    Harness-neutral: each strategy's parser normalizes its own event schema
    into this record, and classify() operates only on these fields."""

    session_id: str = ""
    reasoning_parts: list[str] = field(default_factory=list)
    completed_load: bool = False  # skill tool_use on target, status completed
    attempted_load: bool = False  # skill tool_use on target, other status
    other_skill: str | None = None
    report_loaded: str | None = (
        None  # skill named by the mandated final report
    )
    report_no_match: bool = False  # mandated report said no skill matched
    error_message: str | None = None
    parseable: int = 0


def intent_in_reasoning(reasoning: str, skill: str) -> bool:
    """Strict intent phrases only — never a bare mention of the skill name,
    since not-trigger reasoning names the target while rejecting it."""
    s = re.escape(skill)
    patterns = [
        rf"\bloading\b[^\n.]*[*_`]*{s}\b",
        rf"\bload\b[^\n.]*\bthe\b[^\n.]*[*_`]*{s}[*_`]*[^\n.]*\bskill\b",
        rf"\b(?:should|will|need to|must)\s+load\b[^\n.]*[*_`]*{s}\b",
        rf"\binvok(?:e|ing)\b[^\n.]*[*_`]*{s}\b",
    ]
    return any(re.search(p, reasoning, re.IGNORECASE) for p in patterns)


def classify(
    ev: EventStream,
    skill: str,
    *,
    interrupted_cause: str | None = None,
    returncode: int = 0,
    stderr: str = "",
) -> Verdict:
    """Apply the signal-detection precedence to a parsed stream.

    interrupted_cause is set for subprocess timeouts (partial stream).
    """
    reasoning = "\n".join(ev.reasoning_parts)

    # Rule 1: a completed load wins, even in the partial stream of an
    # interrupted run.
    if ev.completed_load:
        return Verdict(
            "triggered",
            detail="skill tool completed load",
            session_id=ev.session_id,
            reasoning=reasoning,
        )

    if interrupted_cause is not None:
        # Rule 3a: subprocess timeout — classify the partial stream.
        return _interrupted_verdict(ev, skill, interrupted_cause, reasoning)

    if ev.error_message is not None:
        raise HarnessExecutionError(ev.error_message)
    if returncode != 0:
        raise HarnessExecutionError(f"exit {returncode}: {stderr[-500:]}")
    if ev.parseable == 0:
        raise HarnessExecutionError("no parseable events (exit 0)")

    if ev.report_loaded is None and not ev.report_no_match:
        # Rule 3b: clean, normally-exited run without the mandated final
        # report = step-cap cutoff; the full stream is the partial stream.
        return _interrupted_verdict(
            ev, skill, "step-cap cutoff (final report missing)", reasoning
        )

    # Rule 2: completed run, no completed load, report present.
    if ev.attempted_load:
        detail = "attempted load of target did not complete"
    elif ev.other_skill is not None:
        detail = f"other skill loaded: {ev.other_skill}"
    elif ev.report_no_match:
        detail = "agent reported no skill matched"
    elif ev.report_loaded is not None:
        detail = (
            f"agent reported loading '{ev.report_loaded}' without a "
            f"completed load"
        )
    else:
        detail = ""
    return Verdict(
        "not-triggered",
        detail=detail,
        session_id=ev.session_id,
        reasoning=reasoning,
    )


def _interrupted_verdict(
    ev: EventStream, skill: str, cause: str, reasoning: str
) -> Verdict:
    """Rule 3: interrupted run, no completed load. Clear intent evidence
    counts as a pass flagged with timeout: true; otherwise void."""
    intent = []
    if ev.report_loaded == skill:
        intent.append("report names target")
    if ev.attempted_load:
        intent.append("attempted skill call on target")
    if intent_in_reasoning(reasoning, skill):
        intent.append("intent phrase in reasoning")
    if intent:
        return Verdict(
            "triggered",
            detail=f"{cause}; intent evidence: {', '.join(intent)}",
            session_id=ev.session_id,
            reasoning=reasoning,
            timeout=True,
        )
    return Verdict(
        "void",
        detail=f"{cause}; no intent evidence",
        session_id=ev.session_id,
        reasoning=reasoning,
        timeout=True,
    )


def _as_text(data: str | bytes | None) -> str:
    if data is None:
        return ""
    if isinstance(data, bytes):
        return data.decode(errors="replace")
    return data


def _reject_agent_fallback(stderr: str) -> None:
    """opencode silently falls back to the default agent (exit 0, stderr
    warning only) when --agent names an unknown or non-primary agent. A run
    under the wrong agent is contamination, not data: abort."""
    low = stderr.lower()
    if "falling back to default agent" in low or re.search(
        r"agent\b[^\n]*\bnot found", low
    ):
        raise HarnessExecutionError(
            "harness fell back to the default agent (evaluator agent not "
            f"usable): {stderr.strip()[:300]}"
        )


# --------------------------------------------------------------------------
# Strategy protocol and registry


class EvalStrategy:
    """Base class for harness strategies."""

    binary: str  # CLI binary name, used by the preflight check
    agent_name: str  # passed to the harness per rep
    agent_source: Path  # .../agents/trigger-evaluator.<harness>.md
    agent_dest: str  # workspace-relative install path

    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    def install(self, workspace: Path) -> None:
        raise NotImplementedError

    def evaluate(
        self,
        skill: str,
        query: str,
        workspace: Path,
        model: str | None = None,
        effort: str | None = None,
    ) -> Verdict:
        raise NotImplementedError


class OpencodeStrategy(EvalStrategy):
    binary = "opencode"
    agent_name = "trigger-evaluator"
    agent_source = AGENTS_DIR / "trigger-evaluator.opencode.md"
    agent_dest = ".opencode/agent/trigger-evaluator.md"

    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    @staticmethod
    def parse_stream(stdout: str, skill: str) -> EventStream:
        """Normalize opencode's `run --format json` NDJSON event schema into
        an EventStream. This is the opencode-specific adapter; classify() and
        everything downstream of it are harness-agnostic."""
        ev = EventStream()
        for line in stdout.splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError, ValueError:
                continue
            ev.parseable += 1
            if not ev.session_id and isinstance(event.get("sessionID"), str):
                ev.session_id = event["sessionID"]
            etype = event.get("type")
            part = event.get("part")
            if not isinstance(part, dict):
                part = {}
            if etype == "reasoning":
                text = part.get("text")
                if isinstance(text, str):
                    ev.reasoning_parts.append(text)
            elif etype == "text":
                text = part.get("text")
                if isinstance(text, str):
                    m = REPORT_LOADED_RE.search(text)
                    if m and ev.report_loaded is None:
                        ev.report_loaded = m.group(1)
                    if REPORT_NO_MATCH_RE.search(text):
                        ev.report_no_match = True
            elif etype == "tool_use":
                if part.get("tool") == "skill":
                    state = part.get("state")
                    if not isinstance(state, dict):
                        state = {}
                    inp = state.get("input")
                    if not isinstance(inp, dict):
                        inp = {}
                    name = inp.get("name")
                    if name == skill:
                        if state.get("status") == "completed":
                            ev.completed_load = True
                        else:
                            ev.attempted_load = True
                    elif name is not None and ev.other_skill is None:
                        ev.other_skill = name
            elif etype == "error":
                error = event.get("error", {})
                message = error.get("data", {}).get("message")
                if not isinstance(message, str):
                    message = str(error)
                if ev.error_message is None:
                    ev.error_message = message
        return ev

    def install(self, workspace: Path) -> None:
        """Copy the restricted evaluator agent into the workspace. Idempotent:
        every invocation re-copies. Any failure is an operational error before
        any spend."""
        if not self.agent_source.exists():
            print(
                f"error: evaluator agent file missing: {self.agent_source}",
                file=sys.stderr,
            )
            sys.exit(1)
        dest = workspace / self.agent_dest
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(self.agent_source, dest)
        except OSError as e:
            print(
                f"error: could not install evaluator agent to {dest}: {e}",
                file=sys.stderr,
            )
            sys.exit(1)
        if not dest.exists():
            print(
                f"error: evaluator agent install failed: {dest} not created",
                file=sys.stderr,
            )
            sys.exit(1)

    def evaluate(
        self,
        skill: str,
        query: str,
        workspace: Path,
        model: str | None = None,
        effort: str | None = None,
    ) -> Verdict:
        cmd = [
            self.binary,
            "run",
            "--pure",
            "--thinking",
            "--format",
            "json",
            "--dir",
            str(workspace),
            "--agent",
            self.agent_name,
        ]
        if model is not None:
            cmd += ["--model", model]
        if effort is not None:
            cmd += ["--variant", effort]
        cmd.append(query)

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=False,
            )
        except FileNotFoundError:
            raise HarnessExecutionError(
                f"harness CLI '{self.binary}' not found on PATH"
            ) from None
        except subprocess.TimeoutExpired as e:
            stderr = _as_text(e.stderr)
            _reject_agent_fallback(stderr)
            ev = self.parse_stream(_as_text(e.stdout), skill)
            return classify(
                ev, skill, interrupted_cause=f"timeout after {self.timeout}s"
            )

        _reject_agent_fallback(proc.stderr)
        ev = self.parse_stream(proc.stdout, skill)
        return classify(
            ev, skill, returncode=proc.returncode, stderr=proc.stderr
        )


STRATEGIES: dict[str, type[EvalStrategy]] = {"opencode": OpencodeStrategy}


def resolve_strategy(name: str) -> type[EvalStrategy]:
    cls = STRATEGIES.get(name)
    if cls is None:
        supported = ", ".join(sorted(STRATEGIES))
        print(
            f"error: unsupported harness '{name}' (supported: {supported})",
            file=sys.stderr,
        )
        sys.exit(1)
    return cls


def check_harness(name: str, strategy_cls: type[EvalStrategy]) -> None:
    """Preflight: CLI on PATH and evaluator-agent source present. Verifies the
    binary exists, not that it is configured — the smoke rep covers
    configuration."""
    resolved = shutil.which(strategy_cls.binary)
    if resolved is None:
        print(
            f"error: harness '{name}' CLI not found on PATH "
            f"(looked for '{strategy_cls.binary}')",
            file=sys.stderr,
        )
        sys.exit(1)
    if not strategy_cls.agent_source.exists():
        print(
            f"error: evaluator agent file missing: "
            f"{strategy_cls.agent_source}",
            file=sys.stderr,
        )
        sys.exit(1)
    print(
        f"ok: harness '{name}' available "
        f"({strategy_cls.binary}: {resolved})"
    )
