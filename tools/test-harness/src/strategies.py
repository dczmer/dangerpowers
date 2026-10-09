#!/usr/bin/env python3
"""Harness strategy layer for the evaluator.

Defines the verdict vocabulary (Verdict, EventStream, HarnessExecutionError),
the harness-neutral signal classification (classify), the EvalStrategy
protocol, and the strategy registry. opencode and pi are implemented.

Imported by evaluator.py; nothing here imports evaluator.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, NoReturn

Outcome = Literal["triggered", "not-triggered", "void"]

# The shared per-run timeout default (seconds) for the long-form tracks
# (shape/pressure/retrieval suite and meta) — calibrated against slow
# local endpoints under the suite's 10-way rep concurrency, where 120 s
# drowned clean runs in empty-answer timeout voids (53/70 at 120 s, 0/70
# at 300 s; BUGS.md B3). Trigger stays at its own 30 s: its queries are
# short single-shot loads under a restricted agent. Only endpoint
# latency should ever move this number; raise --timeout per invocation
# for a slower endpoint rather than editing it.
DEFAULT_TIMEOUT = 300


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
    agent_name: str  # trigger-track eval agent base name

    def __init__(self, timeout: int = DEFAULT_TIMEOUT):
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
        self.materialize_agent(workspace, base, text)
        return base

    def materialize_agent(self, workspace: Path, base: str, text: str) -> None:
        """Make the agent usable by execute(). Default: copy the file
        into the harness's workspace agent dir (opencode). pi overrides
        this: its agent config is flag-translated and held in-process —
        pi has no agent files or --agent flag."""
        dest = workspace / self.agent_install_dir / f"{base}.md"
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(text)
        except OSError as e:
            _fail(f"could not install evaluator agent to {dest}: {e}")

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

    @classmethod
    def check_version(cls) -> str | None:
        """Optional harness-version advisory: return a warning string
        or None. Default no-op (opencode pins nothing)."""
        return None

    def build_cmd(
        self,
        workspace: Path,
        agent: str,
        query: str,
        model: str | None,
        effort: str | None,
        skill: str | None,
        session: str | None,
    ) -> list[str]:
        """The harness argv for one eval run. Subclasses implement."""
        raise NotImplementedError

    def run_cwd(self, workspace: Path) -> str | None:
        """subprocess cwd for the run; None keeps the evaluator's cwd
        (opencode anchors with --dir instead)."""
        return None

    def build_env(self, workspace: Path, agent: str) -> dict | None:
        """subprocess env for the run; None inherits the evaluator's
        environment (opencode needs nothing)."""
        return None

    def check_stderr(self, stderr: str) -> None:
        """Post-run stderr inspection: raise HarnessExecutionError on
        silent-contamination signals. Default no-op (opencode overrides
        with the agent-fallback rejection)."""

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
        cmd = self.build_cmd(
            workspace, agent, query, model, effort, skill, session
        )
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=False,
                cwd=self.run_cwd(workspace),
                env=self.build_env(workspace, agent),
            )
        except FileNotFoundError:
            raise HarnessExecutionError(
                f"harness CLI '{self.binary}' not found on PATH"
            )
        except subprocess.TimeoutExpired as e:
            return self.parse_stream(_as_text(e.stdout), skill), True
        self.check_stderr(proc.stderr)
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
        """One headless trigger evaluation: execute under the
        trigger-evaluator agent, then classify; a timeout yields the
        interrupted-run classification."""
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

    def build_cmd(
        self,
        workspace: Path,
        agent: str,
        query: str,
        model: str | None,
        effort: str | None,
        skill: str | None,
        session: str | None,
    ) -> list[str]:
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
        return cmd

    def check_stderr(self, stderr: str) -> None:
        _reject_agent_fallback(stderr)

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


# --------------------------------------------------------------------------
# pi strategy


PI_TOOL_NAMES = frozenset(
    {"read", "bash", "edit", "write", "grep", "find", "ls"}
)

# The guard extension shipped beside this file; loaded explicitly with
# -e, which pi honors even under --no-extensions.
GUARD_EXTENSION = Path(__file__).resolve().parent.parent / ("pi-eval-guard.ts")


def parse_pi_agent(text: str, source: str) -> dict:
    """Parse a .pi.md eval-agent document (frontmatter + body).

    Returns {"tools": list[str], "steps": int, "skill": "allow"|"deny",
    "body": str}. Exits 1 with an exact message on any violation —
    install-time is pre-spend. Stdlib line-scan, same discipline as
    scan_agent_frontmatter (no pyyaml). tools: is a comma-separated
    allowlist of pi built-in tool names (empty = --no-tools); steps: is
    the guard's tool-call cap (0 = no cap); skill: allow|deny selects
    whether the workspace skill is advertised via --skill."""
    lines = text.splitlines(keepends=True)
    tools: list[str] = []
    steps = 0
    skill = "deny"
    i = 1  # caller guarantees lines[0] == "---" (scan ran first)
    while i < len(lines) and lines[i].rstrip("\n") != "---":
        line = lines[i].rstrip("\n")
        m = re.match(r"^tools:\s*(.*)$", line)
        if m:
            tools = [t.strip() for t in m.group(1).split(",") if t.strip()]
            unknown = [t for t in tools if t not in PI_TOOL_NAMES]
            if unknown:
                _fail(
                    f"agent file {source}: unknown pi tool(s): "
                    f"{', '.join(unknown)} (known: "
                    f"{', '.join(sorted(PI_TOOL_NAMES))})"
                )
        if re.match(r"^steps\s*:", line):
            m = re.match(r"^steps\s*:\s*(\d+)\s*$", line)
            if m is None:
                _fail(
                    f"agent file {source}: steps must be an int >= 0 "
                    f"(got: {line.strip()})"
                )
            steps = int(m.group(1))
        if re.match(r"^skill\s*:", line):
            m = re.match(r"^skill:\s*(allow|deny)\s*$", line)
            if m is None:
                _fail(
                    f"agent file {source}: skill must be 'allow' or "
                    f"'deny' (got: {line.strip()})"
                )
            skill = m.group(1)
        i += 1
    body = "".join(lines[i + 1 :]) if i < len(lines) else ""
    if not body.strip():
        _fail(
            f"agent file {source}: empty body (the body is the eval "
            "agent's system prompt)"
        )
    return {"tools": tools, "steps": steps, "skill": skill, "body": body}


def _pi_skill_md(path: str, skill: str) -> bool:
    """True when a read-tool path is exactly the target skill's stub:
    <anything>/.agents/skills/<skill>/SKILL.md (normalized separators).
    The pi system prompt advertises skills by absolute location inside
    the workspace's .agents/skills tree, but agents also read the stub
    by a workspace-relative path — those reads are a load too
    (campaign-2026-10-06: relative reads mis-signaled skill-not-loaded
    on 3 of 4 skill runs). Match both, requiring a path boundary so a
    look-alike prefix ('not-.agents/...') can't satisfy the tail."""
    tail = os.path.normpath(f".agents/skills/{skill}/SKILL.md")
    normalized = os.path.normpath(path)
    return normalized.endswith(tail) and (
        len(normalized) == len(tail) or normalized[-len(tail) - 1] == os.sep
    )


def _pi_other_skill(path: str) -> str | None:
    """Skill name when a read-tool path is exactly some skill's stub
    (.../.agents/skills/<name>/SKILL.md), else None. Accepts absolute
    and workspace-relative paths, with the same boundary discipline as
    _pi_skill_md — a look-alike directory ('not-.agents/...') or a
    SKILL.md buried deeper in a skill dir is not a stub read."""
    parts = os.path.normpath(path).split(os.sep)
    for i, part in enumerate(parts[:-3]):
        if (
            part == ".agents"
            and parts[i + 1] == "skills"
            and parts[i + 3] == "SKILL.md"
        ):
            return parts[i + 2] or None
    return None


class PiStrategy(EvalStrategy):
    """pi harness: agents are translated into CLI flags (--system-prompt
    + --tools allowlist + guard env), never installed as files — pi has
    no --agent concept. Skill loading in pi IS reading SKILL.md, so the
    trigger signal is a successful read of the stub (D3)."""

    binary = "pi"
    harness = "pi"
    agent_install_dir = ""  # unused: materialize_agent holds config
    agent_name = "trigger-evaluator"
    MIN_VERSION = (0, 99, 1)  # the probed floor (D6)

    def __init__(self, timeout: int = DEFAULT_TIMEOUT):
        super().__init__(timeout)
        self._agents: dict[str, dict] = {}

    def materialize_agent(self, workspace: Path, base: str, text: str) -> None:
        self._agents[base] = parse_pi_agent(text, f"{base}.pi.md")

    def _agent_config(self, agent: str) -> dict:
        cfg = self._agents.get(agent)
        if cfg is None:
            raise HarnessExecutionError(
                f"agent '{agent}' was not installed (pi strategy holds "
                "agent config in-process; install runs before execute)"
            )
        return cfg

    def build_cmd(
        self,
        workspace: Path,
        agent: str,
        query: str,
        model: str | None,
        effort: str | None,
        skill: str | None,
        session: str | None,
    ) -> list[str]:
        cfg = self._agent_config(agent)
        cmd = [
            self.binary,
            "--mode",
            "json",
            "--system-prompt",
            cfg["body"],
            "--no-extensions",
            "-e",
            str(GUARD_EXTENSION),
            "--no-context-files",
            "--no-prompt-templates",
        ]
        if cfg["tools"]:
            cmd += ["--tools", ",".join(cfg["tools"])]
        else:
            cmd += ["--no-tools"]
        cmd.append("--no-skills")
        if cfg["skill"] == "allow":
            if not skill:
                raise HarnessExecutionError(
                    f"agent '{agent}' has skill: allow but no skill was "
                    "named for this run"
                )
            cmd += [
                "--skill",
                str(Path(workspace) / ".agents" / "skills" / skill),
            ]
        if session is not None:
            cmd += ["--session", session]
        if model is not None:
            cmd += ["--model", model]
        if effort is not None:
            cmd += ["--thinking", effort]
        # -- : end option parsing so a query starting with '-' or '@'
        # can never be read as a flag. (pi still treats post--- tokens
        # as messages; see review point R7 for the '@' caveat.)
        cmd += ["--", query]
        return cmd

    def run_cwd(self, workspace: Path) -> str | None:
        # Resolved, matching build_env's EVAL_WS_ROOT: a model-built
        # absolute path under the workspace must satisfy the guard's
        # root-prefix check even where the workspace path traverses a
        # symlink (e.g. macOS /tmp -> /private/tmp).
        return str(Path(workspace).resolve())

    def build_env(self, workspace: Path, agent: str) -> dict | None:
        cfg = self._agent_config(agent)
        env = dict(os.environ)
        env["EVAL_WS_ROOT"] = str(Path(workspace).resolve())
        env["EVAL_MAX_TOOL_CALLS"] = str(cfg["steps"])
        return env

    @staticmethod
    def parse_stream(stdout: str, skill: str | None) -> EventStream:
        """Normalize pi's `--mode json` JSONL into an EventStream.
        message_end carries the authoritative content blocks (thinking,
        text); tool_execution_start/end correlate by toolCallId (end
        events carry no args); a read of the target stub with
        isError=false is the completed load (D3)."""
        ev = EventStream()
        pending: dict[str, tuple[str, dict]] = {}
        for line in stdout.splitlines():
            try:
                event = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            ev.parseable += 1
            etype = event.get("type")
            if etype == "session":
                if not ev.session_id and isinstance(event.get("id"), str):
                    ev.session_id = event["id"]
            elif etype == "message_end":
                msg = event.get("message")
                if not isinstance(msg, dict) or msg.get("role") != (
                    "assistant"
                ):
                    continue
                content = msg.get("content")
                if not isinstance(content, list):
                    continue
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    btype = block.get("type")
                    if btype == "thinking":
                        text = block.get("thinking")
                        if isinstance(text, str):
                            ev.reasoning_parts.append(text)
                    elif btype == "text":
                        text = block.get("text")
                        if not isinstance(text, str):
                            continue
                        ev.answer_parts.append(text)
                        m = REPORT_LOADED_RE.search(text)
                        if m and ev.report_loaded is None:
                            ev.report_loaded = m.group(1)
                        if REPORT_NO_MATCH_RE.search(text):
                            ev.report_no_match = True
            elif etype == "tool_execution_start":
                tcid = event.get("toolCallId")
                if isinstance(tcid, str):
                    args = event.get("args")
                    pending[tcid] = (
                        event.get("toolName") or "",
                        args if isinstance(args, dict) else {},
                    )
            elif etype == "tool_execution_end":
                tcid = event.get("toolCallId")
                tool, args = pending.pop(
                    tcid, (event.get("toolName") or "", {})
                )
                is_error = bool(event.get("isError"))
                path = args.get("path")
                if tool == "read" and isinstance(path, str) and path:
                    if skill and _pi_skill_md(path, skill):
                        ev.skill_loads.append(
                            {
                                "name": skill,
                                "status": (
                                    "error" if is_error else "completed"
                                ),
                            }
                        )
                        if is_error:
                            ev.attempted_load = True
                        else:
                            ev.completed_load = True
                    elif (name := _pi_other_skill(path)) is not None:
                        ev.skill_loads.append(
                            {
                                "name": name,
                                "status": (
                                    "error" if is_error else "completed"
                                ),
                            }
                        )
                        if ev.other_skill is None:
                            ev.other_skill = name
                    else:
                        ev.tool_calls.append({"tool": tool, "target": path})
                elif tool in ("grep", "find", "ls"):
                    target = args.get("path") or args.get("pattern") or ""
                    ev.tool_calls.append({"tool": tool, "target": target})
            elif etype == "auto_retry_end":
                if event.get("success") is False and ev.error_message is None:
                    ev.error_message = str(
                        event.get("finalError") or "provider retry exhausted"
                    )
            elif etype == "message_update":
                sub = event.get("assistantMessageEvent")
                if (
                    isinstance(sub, dict)
                    and sub.get("type") == "error"
                    and ev.error_message is None
                ):
                    ev.error_message = str(
                        sub.get("error")
                        or sub.get("reason")
                        or "provider stream error"
                    )
        # A read of the target that started but never ended (timeout
        # partial stream) is an attempted load — the opencode
        # "tool_use with a non-completed status" equivalent.
        for tool, args in pending.values():
            if tool == "read" and skill:
                path = args.get("path")
                if isinstance(path, str) and _pi_skill_md(path, skill):
                    ev.attempted_load = True
        return ev

    @classmethod
    def check_model(cls, model: str) -> str | None:
        """Exact provider/id match against `pi --list-models` (offline;
        the cached catalog is enough — probe-verified 0.5 s). pi's
        --model resolves patterns fuzzily, so the exact-pair
        requirement is what keeps a typo from silently running the
        wrong model (D5)."""
        env = dict(os.environ, PI_OFFLINE="1")
        try:
            proc = subprocess.run(
                [cls.binary, "--list-models"],
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )
        except FileNotFoundError:
            return f"harness CLI '{cls.binary}' not found on PATH"
        if proc.returncode != 0:
            return (
                f"'{cls.binary} --list-models' exited "
                f"{proc.returncode}: {proc.stderr.strip()[:300]}"
            )
        ids = set()
        # Columnar rows (pi >= 0.99): a header names the columns, so the
        # model id is the single token in the model column; the context /
        # max-out / thinking / images columns that follow are not part of
        # the id. Headerless output keeps the join-all-tokens behavior so
        # multi-word ids in an older pi still parse.
        has_header = any(
            (line.split() or [""])[0].lower() == "provider"
            for line in proc.stdout.splitlines()
        )
        for line in proc.stdout.splitlines():
            parts = line.split()
            # Skip the header row by name, not position, so a future pi
            # that drops the header still parses.
            if len(parts) < 2 or parts[0].lower() == "provider":
                continue
            if has_header:
                ids.add(f"{parts[0]}/{parts[1]}")
            else:
                ids.add(f"{parts[0]}/{' '.join(parts[1:])}")
        if not ids:
            return f"'{cls.binary} --list-models' printed no models"
        if model not in ids:
            return (
                f"model '{model}' not found via '{cls.binary} "
                f"--list-models' ({len(ids)} available); pi requires an "
                "exact provider/id value"
            )
        return None

    @classmethod
    def check_version(cls) -> str | None:
        """Warn-only floor check (D6): pi is pre-1.0 and the skills-
        section behavior this strategy depends on was verified at
        MIN_VERSION and at main."""
        try:
            proc = subprocess.run(
                [cls.binary, "--version"],
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError:
            return None  # the which() preflight reports the miss
        m = re.match(r"^(\d+)\.(\d+)\.(\d+)", proc.stdout.strip())
        if m is None:
            return None  # unparseable: no opinion
        version = tuple(int(g) for g in m.groups())
        if version < cls.MIN_VERSION:
            floor = ".".join(str(n) for n in cls.MIN_VERSION)
            return (
                f"harness 'pi' version {proc.stdout.strip()} is below "
                f"the tested floor {floor}; the pi strategy was probe-"
                "verified at the floor — upgrade pi or proceed with "
                "caution"
            )
        return None


# --------------------------------------------------------------------------
# claude strategy

CLAUDE_TOOL_NAMES = frozenset(
    {"Read", "Bash", "Edit", "Write", "Grep", "Glob", "WebFetch", "Skill"}
)


def parse_claude_agent(text: str, source: str) -> dict:
    """Parse a .claude.md eval-agent document (frontmatter + body).

    Returns {"tools": list[str], "steps": int, "skill": "allow"|"deny",
    "description": str, "body": str}. Exits 1 with an exact message on
    any violation — install-time is pre-spend. Stdlib line-scan, same
    discipline as scan_agent_frontmatter/parse_pi_agent (no pyyaml).
    tools: is a comma-separated allowlist of Claude Code built-in tool
    names (empty = --tools ""); steps: is the guard hook's tool-call cap
    (0 = no cap); skill: allow|deny selects whether the Skill tool is
    advertised (--disallowedTools Skill when deny)."""
    lines = text.splitlines(keepends=True)
    tools: list[str] = []
    steps = 0
    skill = "deny"
    description = ""
    i = 1  # caller guarantees lines[0] == "---" (scan ran first)
    while i < len(lines) and lines[i].rstrip("\n") != "---":
        line = lines[i].rstrip("\n")
        m = re.match(r"^tools:\s*(.*)$", line)
        if m:
            tools = [t.strip() for t in m.group(1).split(",") if t.strip()]
            unknown = [t for t in tools if t not in CLAUDE_TOOL_NAMES]
            if unknown:
                _fail(
                    f"agent file {source}: unknown claude tool(s): "
                    f"{', '.join(unknown)} (known: "
                    f"{', '.join(sorted(CLAUDE_TOOL_NAMES))})"
                )
        if re.match(r"^steps\s*:", line):
            m = re.match(r"^steps\s*:\s*(\d+)\s*$", line)
            if m is None:
                _fail(
                    f"agent file {source}: steps must be an int >= 0 "
                    f"(got: {line.strip()})"
                )
            steps = int(m.group(1))
        if re.match(r"^skill\s*:", line):
            m = re.match(r"^skill:\s*(allow|deny)\s*$", line)
            if m is None:
                _fail(
                    f"agent file {source}: skill must be 'allow' or "
                    f"'deny' (got: {line.strip()})"
                )
            skill = m.group(1)
        m = re.match(r"^description:\s*(.*)$", line)
        if m:
            description = m.group(1).strip()
        i += 1
    body = "".join(lines[i + 1 :]) if i < len(lines) else ""
    if not body.strip():
        _fail(
            f"agent file {source}: empty body (the body is the eval "
            "agent's system prompt)"
        )
    if not description:
        _fail(
            f"agent file {source}: missing 'description:' (required by "
            "--agents)"
        )
    return {
        "tools": tools,
        "steps": steps,
        "skill": skill,
        "description": description,
        "body": body,
    }


class ClaudeStrategy(EvalStrategy):
    """Claude Code harness: agents are translated into an inline
    --agents JSON object plus --restricted/--tools/--disallowedTools —
    Claude Code has no on-disk agent-file concept exposed to --print, so
    (like pi) agent config is held in-process rather than materialized
    as files. Skill loading is a dedicated `Skill` tool whose paired
    tool_use_result carries an explicit success flag — the cleanest
    completed-load signal of the three strategies."""

    binary = "claude"
    harness = "claude"
    agent_install_dir = ""  # unused: materialize_agent holds config
    agent_name = "trigger-evaluator"
    MIN_VERSION = (2, 1, 283)  # the probed floor

    def __init__(self, timeout: int = DEFAULT_TIMEOUT):
        super().__init__(timeout)
        self._agents: dict[str, dict] = {}

    def materialize_agent(self, workspace: Path, base: str, text: str) -> None:
        self._agents[base] = parse_claude_agent(text, f"{base}.claude.md")

    def _agent_config(self, agent: str) -> dict:
        cfg = self._agents.get(agent)
        if cfg is None:
            raise HarnessExecutionError(
                f"agent '{agent}' was not installed (claude strategy holds "
                "agent config in-process; install runs before execute)"
            )
        return cfg

    def _guard_settings_path(self, workspace: Path, steps: int) -> Path | None:
        """Write a per-workspace --settings file wiring the PreToolUse
        step-cap hook; None when the agent sets steps: 0 (no cap)."""
        if steps <= 0:
            return None
        guard = Path(__file__).resolve().parent.parent / "claude-eval-guard.py"
        settings = workspace / ".claude-eval-settings.json"
        settings.write_text(
            json.dumps(
                {
                    "hooks": {
                        "PreToolUse": [
                            {
                                "matcher": "*",
                                "hooks": [
                                    {
                                        "type": "command",
                                        "command": f"python3 {guard}",
                                    }
                                ],
                            }
                        ]
                    }
                }
            )
        )
        return settings

    def build_cmd(
        self,
        workspace: Path,
        agent: str,
        query: str,
        model: str | None,
        effort: str | None,
        skill: str | None,
        session: str | None,
    ) -> list[str]:
        cfg = self._agent_config(agent)
        agents_json = json.dumps(
            {agent: {"description": cfg["description"], "prompt": cfg["body"]}}
        )
        cmd = [
            self.binary,
            "-p",
            "--output-format",
            "stream-json",
            "--verbose",
            "--restricted",
            "--setting-sources",
            "",
            "--agent",
            agent,
            "--agents",
            agents_json,
        ]
        cmd += ["--tools", ",".join(cfg["tools"]) if cfg["tools"] else ""]
        if cfg["skill"] == "deny":
            cmd += ["--disallowedTools", "Skill"]
        guard_settings = self._guard_settings_path(workspace, cfg["steps"])
        if guard_settings is not None:
            cmd += ["--settings", str(guard_settings)]
        if session is not None:
            cmd += ["--resume", session]
        if model is not None:
            cmd += ["--model", model]
        if effort is not None:
            cmd += ["--effort", effort]
        cmd += ["--", query]
        return cmd

    def run_cwd(self, workspace: Path) -> str | None:
        return str(Path(workspace).resolve())

    def build_env(self, workspace: Path, agent: str) -> dict | None:
        cfg = self._agent_config(agent)
        env = dict(os.environ)
        env["EVAL_MAX_TOOL_CALLS"] = str(cfg["steps"])
        # One counter file per execute() call, not per workspace: reps
        # run concurrently in threads (run_rep_batched), so a shared
        # counter would double-count across reps.
        counter = workspace / f".claude-eval-counter-{uuid.uuid4().hex}"
        env["CLAUDE_EVAL_COUNTER_FILE"] = str(counter)
        return env

    def check_stderr(self, stderr: str) -> None:
        low = stderr.lower()
        if "plugin" in low and "loaded" in low:
            raise HarnessExecutionError(
                f"harness loaded ambient plugins despite --restricted "
                f"(evaluator isolation broken): {stderr.strip()[:300]}"
            )

    @staticmethod
    def parse_stream(stdout: str, skill: str | None) -> EventStream:
        """Normalize claude's `--output-format stream-json` NDJSON into
        an EventStream. Skill tool_use/tool_result pairs correlate by
        tool_use_id (result arrives on a LATER `user` event, not inline
        on the tool_use block) — same two-pass shape as PiStrategy's
        toolCallId correlation."""
        ev = EventStream()
        # tool_use_id -> (tool name, Skill target or None)
        pending: dict[str, tuple[str, str | None]] = {}
        for line in stdout.splitlines():
            try:
                event_ = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            ev.parseable += 1
            etype = event_.get("type")
            if etype == "system" and event_.get("subtype") == "init":
                sid = event_.get("session_id")
                if not ev.session_id and isinstance(sid, str):
                    ev.session_id = sid
            elif etype == "assistant":
                msg = event_.get("message", {})
                for block in msg.get("content", []):
                    if not isinstance(block, dict):
                        continue
                    btype = block.get("type")
                    if btype == "thinking":
                        text = block.get("thinking")
                        if isinstance(text, str) and text:
                            ev.reasoning_parts.append(text)
                    elif btype == "text":
                        text = block.get("text")
                        if isinstance(text, str):
                            ev.answer_parts.append(text)
                            m = REPORT_LOADED_RE.search(text)
                            if m and ev.report_loaded is None:
                                ev.report_loaded = m.group(1)
                            if REPORT_NO_MATCH_RE.search(text):
                                ev.report_no_match = True
                    elif btype == "tool_use":
                        tcid = block.get("id")
                        name = block.get("name")
                        target = None
                        if name == "Skill":
                            target = (block.get("input") or {}).get("skill")
                            if target is not None and target != skill:
                                if ev.other_skill is None:
                                    ev.other_skill = target
                        if isinstance(tcid, str) and isinstance(name, str):
                            pending[tcid] = (name, target)
                        if name in ("Read", "Grep", "Glob", "Bash"):
                            inp = block.get("input") or {}
                            ev.tool_calls.append(
                                {
                                    "tool": name,
                                    "target": inp.get("file_path")
                                    or inp.get("path")
                                    or inp.get("pattern")
                                    or "",
                                }
                            )
            elif etype == "user":
                msg = event_.get("message", {})
                for block in msg.get("content", []):
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") != "tool_result":
                        continue
                    tcid = block.get("tool_use_id")
                    pending_entry = (
                        pending.pop(tcid, None)
                        if isinstance(tcid, str)
                        else None
                    )
                    tool = pending_entry[0] if pending_entry else None
                    if tool != "Skill":
                        continue
                    result = event_.get("tool_use_result") or {}
                    name = result.get("commandName")
                    success = bool(result.get("success"))
                    is_error = bool(block.get("is_error"))
                    ev.skill_loads.append(
                        {
                            "name": name,
                            "status": (
                                "completed"
                                if success and not is_error
                                else "error"
                            ),
                        }
                    )
                    if name == skill:
                        if success and not is_error:
                            ev.completed_load = True
                        else:
                            ev.attempted_load = True
                    elif is_error:
                        ev.denied_tool_attempts.append(
                            {"tool": "Skill", "target": name or ""}
                        )
            elif etype == "result":
                if ev.error_message is None and event_.get("is_error"):
                    ev.error_message = str(
                        event_.get("result")
                        or "claude reported an error result"
                    )
        # A Skill call that started but never got a paired result
        # (timeout partial stream) is an attempted load.
        for tool, target in pending.values():
            if tool == "Skill" and target == skill:
                ev.attempted_load = True
        return ev

    @classmethod
    def check_model(cls, model: str) -> str | None:
        """Soft check only: claude has no model-listing subcommand
        (`claude models` just prompts the LLM in text — probe-verified).
        Accepts the known alias/full-id set from the system prompt;
        anything else is let through for the smoke rep to catch, same
        honesty standard as a documented gap, not a silent guess."""
        known = {
            "sonnet",
            "opus",
            "fable",
            "haiku",
            "claude-sonnet-5",
            "claude-opus-5-5",
            "claude-fable-5-1",
            "claude-haiku-4-5-20251001",
        }
        if model in known:
            return None
        if re.match(r"^(claude-|us\.anthropic\.|eu\.anthropic\.)", model):
            return None
        return (
            f"model '{model}' not recognized against the known claude "
            "alias/id set (no live enumeration exists; this is a soft "
            "check — if the id is valid, the smoke rep will confirm it)"
        )

    @classmethod
    def check_version(cls) -> str | None:
        try:
            proc = subprocess.run(
                [cls.binary, "--version"],
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError:
            return None
        m = re.match(r"^(\d+)\.(\d+)\.(\d+)", proc.stdout.strip())
        if m is None:
            return None
        version = tuple(int(g) for g in m.groups())
        if version < cls.MIN_VERSION:
            floor = ".".join(str(n) for n in cls.MIN_VERSION)
            return (
                f"harness 'claude' version {proc.stdout.strip()} is below "
                f"the tested floor {floor}; the claude strategy was probe-"
                "verified at the floor — upgrade claude or proceed with "
                "caution"
            )
        return None


STRATEGIES: dict[str, type[EvalStrategy]] = {
    "opencode": OpencodeStrategy,
    "pi": PiStrategy,
    "claude": ClaudeStrategy,
}

# workspace-relative dir a synced skill lives under, keyed by --harness
# name (not strategy_cls: tests stand strategy_cls up as a bare factory
# callable in pre-spend-gate fixtures, so the dest root is resolved from
# the harness string instead). workspace-manager.sh sync/status write
# here via --dest-root; the trigger/retrieval/shape/pressure tracks
# check it before a run.
SKILL_DEST_ROOTS: dict[str, str] = {
    "opencode": ".agents/skills",
    "pi": ".agents/skills",
    "claude": ".claude/skills",
}


def skill_dest_root(harness: str) -> str:
    """The workspace-relative skill directory for a harness name."""
    return SKILL_DEST_ROOTS.get(harness, ".agents/skills")


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
    warning = strategy_cls.check_version()
    if warning is not None:
        print(f"warning: {warning}", file=sys.stderr)
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
