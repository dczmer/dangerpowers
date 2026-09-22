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
from typing import Literal, NoReturn

Outcome = Literal["triggered", "not-triggered", "void"]


@dataclass
class Verdict:
    outcome: Outcome
    detail: str = ""  # timeout note or signal status
    session_id: str = ""
    reasoning: str = (
        ""  # concatenated --thinking blocks; never used for scoring
    )
    timeout: bool = False  # True for interrupted runs (subprocess timeout or
    # clean exit with the mandated final report missing/unrecognized)


class HarnessExecutionError(Exception):
    """The harness could not execute the query (bad args, nonzero exit,
    provider error, empty event stream, agent fallback). Fatal: aborts the
    batch, exits 1. Never a verdict.

    session_id carries the harness session id when the event stream was
    parsed far enough to yield one ("" otherwise) so abort lines can name
    the failed session for debugging."""

    def __init__(self, message: str, session_id: str = ""):
        super().__init__(message)
        self.session_id = session_id


# --------------------------------------------------------------------------
# Signal detection

REPORT_LOADED_RE = re.compile(
    r"loaded skill:\s*[*_`]*([A-Za-z0-9][\w-]*)", re.IGNORECASE
)
REPORT_NO_MATCH_RE = re.compile(
    r"no skills? (?:matched|matches)\b", re.IGNORECASE
)


@dataclass
class EventStream:
    """Structured result of parsing one event stream (complete or partial).
    Harness-neutral: each strategy's parser normalizes its own event schema
    into this record, and classify() operates only on these fields."""

    session_id: str = ""
    reasoning_parts: list[str] = field(default_factory=list)
    answer_parts: list[str] = field(default_factory=list)
    tool_calls: list[dict] = field(default_factory=list)
    skill_loads: list[dict] = field(default_factory=list)
    # Permanently empty: opencode emits no denied-attempt event type —
    # denied tools are absent from the model's toolset, so nothing ever
    # appends here (verified in campaign-2026-09-12-2, 32 runs). Kept
    # only for results.json schema stability.
    denied_tool_attempts: list[dict] = field(default_factory=list)
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
        raise HarnessExecutionError(ev.error_message, session_id=ev.session_id)
    if returncode != 0:
        raise HarnessExecutionError(
            f"exit {returncode}: {stderr[-500:]}",
            session_id=ev.session_id,
        )
    if ev.parseable == 0:
        raise HarnessExecutionError("no parseable events (exit 0)")

    if ev.report_loaded is None and not ev.report_no_match:
        # A completed load of a DIFFERENT skill (and no attempt on the
        # target) is positive evidence the target did not trigger, even
        # when the mandated report is missing or unrecognized.
        if ev.other_skill is not None and not ev.attempted_load:
            return Verdict(
                "not-triggered",
                detail=(
                    f"other skill loaded: {ev.other_skill} "
                    "(final report missing or unrecognized)"
                ),
                session_id=ev.session_id,
                reasoning=reasoning,
            )
        # Rule 3b: clean, normally-exited run with no mandated report and
        # no load evidence either way; the full stream is the partial
        # stream.
        return _interrupted_verdict(
            ev, skill, "final report missing or unrecognized", reasoning
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
# Agent resolution: frontmatter scan + pre-spend assertions


MODEL_PIN_KEYS = ("model", "variant", "temperature", "top_p")


def _fail(message: str) -> NoReturn:
    print(f"error: {message}", file=sys.stderr)
    sys.exit(1)


def scan_agent_frontmatter(agent_file: Path) -> dict:
    """Stdlib line-scan of an agent file's YAML frontmatter.

    pyyaml is deliberately NOT used: scripts run on any python3 >= 3.10 on
    PATH (trigger SKILL.md preflight contract). Returns {"name", "pins"}."""
    try:
        lines = agent_file.read_text().splitlines()
    except OSError as e:
        _fail(f"could not read agent file {agent_file}: {e}")
    if not lines or lines[0].strip() != "---":
        _fail(f"agent file {agent_file}: missing frontmatter block")
    name = None
    pins: list[str] = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        m = re.match(r"^name:\s*(\S+)\s*$", line)
        if m:
            name = m.group(1)
        for key in MODEL_PIN_KEYS:
            if re.match(rf"^{key}\s*:", line):
                pins.append(key)
    if name is None:
        _fail(f"agent file {agent_file}: frontmatter has no 'name:'")
    return {"name": name, "pins": pins}


# --------------------------------------------------------------------------
# Strategy protocol and registry


class EvalStrategy:
    """Base class for harness strategies."""

    binary: str  # CLI binary name, used by the preflight check
    harness: str  # also the agent-file suffix, e.g. "opencode"
    agent_install_dir: str  # workspace-relative, e.g. ".opencode/agent"

    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    def agent_file(self, agents_dir: Path, base: str) -> Path:
        """The harness-specific agent file path for an agent base name."""
        return agents_dir / f"{base}.{self.harness}.md"

    def install(
        self,
        workspace: Path,
        agents_dir: Path,
        base: str,
        *,
        skill_name: str | None = None,
    ) -> str:
        """Resolve, validate, install one eval agent. Pre-spend: every
        failure exits 1 with an exact message. Returns the agent name —
        file base == frontmatter name == CLI value, by construction."""
        source = self.agent_file(agents_dir, base)
        if not source.exists():
            _fail(f"evaluator agent file missing: {source}")
        info = scan_agent_frontmatter(source)
        if info["name"] != base:
            _fail(
                f"agent file {source}: frontmatter name "
                f"'{info['name']}' does not match expected '{base}'"
            )
        if info["pins"]:
            _fail(
                f"agent file {source} pins model config "
                f"({', '.join(info['pins'])}); eval agents must not pin "
                "model/variant/temperature/top_p — selection flows "
                "through --model/--variant only"
            )
        text = source.read_text()
        if skill_name is not None:
            text = text.replace("{{SKILL_NAME}}", skill_name)
        dest = workspace / self.agent_install_dir / f"{base}.md"
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(text)
        except OSError as e:
            _fail(f"could not install evaluator agent to {dest}: {e}")
        return base

    @staticmethod
    def parse_stream(stdout: str, skill: str | None) -> EventStream:
        raise NotImplementedError

    @classmethod
    def check_model(cls, model: str) -> str | None:
        """Harness-specific model validation: return None when the model
        is resolvable by this harness, else an error message. Default is
        a no-op for strategies with no model enumeration; overrides use
        the harness CLI (see OpencodeStrategy)."""
        return None

    def execute(
        self,
        workspace: Path,
        agent: str,
        query: str,
        model: str | None = None,
        effort: str | None = None,
        skill: str | None = None,
        session: str | None = None,
    ) -> tuple[EventStream, bool]:
        """One headless eval run. Returns (parsed stream, timed_out).
        Timeout yields a partial stream, never an exception.
        HarnessExecutionError = operational failure, never a verdict.
        session resumes an existing harness session (pressure-meta)."""
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
            agent,
        ]
        if session is not None:
            cmd += ["--session", session]
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
            )
        except subprocess.TimeoutExpired as e:
            return self.parse_stream(_as_text(e.stdout), skill), True
        _reject_agent_fallback(proc.stderr)
        ev = self.parse_stream(proc.stdout, skill)
        if ev.error_message is not None:
            raise HarnessExecutionError(
                ev.error_message, session_id=ev.session_id
            )
        if proc.returncode != 0:
            raise HarnessExecutionError(
                f"exit {proc.returncode}: {proc.stderr[-500:]}",
                session_id=ev.session_id,
            )
        if ev.parseable == 0:
            raise HarnessExecutionError("no parseable events (exit 0)")
        return ev, False

    def evaluate(
        self,
        skill: str,
        query: str,
        workspace: Path,
        model: str | None = None,
        effort: str | None = None,
    ) -> Verdict:
        """One headless trigger evaluation: execute then classify.
        Subclasses implement."""
        raise NotImplementedError


class OpencodeStrategy(EvalStrategy):
    binary = "opencode"
    harness = "opencode"
    agent_install_dir = ".opencode/agent"
    agent_name = "trigger-evaluator"  # trigger-track eval agent base name

    @staticmethod
    def parse_stream(stdout: str, skill: str | None) -> EventStream:
        """Normalize opencode's `run --format json` NDJSON event schema into
        an EventStream. This is the opencode-specific adapter; classify() and
        everything downstream of it are harness-agnostic."""
        ev = EventStream()
        for line in stdout.splitlines():
            try:
                event = json.loads(line)
            except (json.JSONDecodeError, ValueError):
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
                    ev.answer_parts.append(text)
                    m = REPORT_LOADED_RE.search(text)
                    if m and ev.report_loaded is None:
                        ev.report_loaded = m.group(1)
                    if REPORT_NO_MATCH_RE.search(text):
                        ev.report_no_match = True
            elif etype == "tool_use":
                tool = part.get("tool")
                state = part.get("state")
                if not isinstance(state, dict):
                    state = {}
                inp = state.get("input")
                if not isinstance(inp, dict):
                    inp = {}
                if tool == "skill":
                    ev.skill_loads.append(
                        {
                            "name": inp.get("name"),
                            "status": state.get("status"),
                        }
                    )
                    name = inp.get("name")
                    if name is not None and name == skill:
                        if state.get("status") == "completed":
                            ev.completed_load = True
                        else:
                            ev.attempted_load = True
                    elif name is not None and ev.other_skill is None:
                        ev.other_skill = name
                elif tool in ("read", "grep", "glob", "list"):
                    ev.tool_calls.append(
                        {
                            "tool": tool,
                            "target": inp.get("filePath")
                            or inp.get("path")
                            or inp.get("pattern")
                            or "",
                        }
                    )
            elif etype == "error":
                error = event.get("error", {})
                message = error.get("data", {}).get("message")
                if not isinstance(message, str):
                    message = str(error)
                if ev.error_message is None:
                    ev.error_message = message
        return ev

    def evaluate(
        self,
        skill: str,
        query: str,
        workspace: Path,
        model: str | None = None,
        effort: str | None = None,
    ) -> Verdict:
        """execute under the trigger-evaluator agent, then classify; a
        timeout yields the interrupted-run classification."""
        ev, timed_out = self.execute(
            workspace, self.agent_name, query, model, effort, skill=skill
        )
        if timed_out:
            return classify(
                ev,
                skill,
                interrupted_cause=f"timeout after {self.timeout}s",
            )
        return classify(ev, skill)

    @classmethod
    def check_model(cls, model: str) -> str | None:
        """Exact-line match of the --model value against `opencode
        models`, which prints one provider/model id per line — the same
        id namespace `opencode run --model` accepts. Distinguishes "the
        enumeration failed" (provider config broken) from "model not in
        the list" (typo); availability/auth is the smoke rep's job."""
        try:
            proc = subprocess.run(
                [cls.binary, "models"],
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError:
            return f"harness CLI '{cls.binary}' not found on PATH"
        if proc.returncode != 0:
            return (
                f"'{cls.binary} models' exited {proc.returncode}: "
                f"{proc.stderr.strip()[:300]}"
            )
        ids = {
            line.strip() for line in proc.stdout.splitlines() if line.strip()
        }
        if not ids:
            return f"'{cls.binary} models' printed no models"
        if model not in ids:
            return (
                f"model '{model}' not found via '{cls.binary} models' "
                f"({len(ids)} available)"
            )
        return None


STRATEGIES: dict[str, type[EvalStrategy]] = {"opencode": OpencodeStrategy}


def resolve_strategy(name: str) -> type[EvalStrategy]:
    """The strategy class for a harness name; exits 1 on an unsupported
    name."""
    cls = STRATEGIES.get(name)
    if cls is None:
        supported = ", ".join(sorted(STRATEGIES))
        print(
            f"error: unsupported harness '{name}' (supported: {supported})",
            file=sys.stderr,
        )
        sys.exit(1)
    return cls


def check_harness(
    name: str, strategy_cls: type[EvalStrategy], model: str | None = None
) -> None:
    """Preflight: CLI on PATH; with a model, the strategy validates it
    (for opencode: exact match against `opencode models`). Verifies the
    binary and the model selection exist, not that the provider is
    configured — the smoke rep covers configuration."""
    resolved = shutil.which(strategy_cls.binary)
    if resolved is None:
        print(
            f"error: harness '{name}' CLI not found on PATH "
            f"(looked for '{strategy_cls.binary}')",
            file=sys.stderr,
        )
        sys.exit(1)
    print(
        f"ok: harness '{name}' available "
        f"({strategy_cls.binary}: {resolved})"
    )
    if model is None:
        return
    problem = strategy_cls.check_model(model)
    if problem is not None:
        print(
            f"error: harness '{name}': {problem}",
            file=sys.stderr,
        )
        sys.exit(1)
    print(f"ok: model '{model}' available on harness '{name}'")
