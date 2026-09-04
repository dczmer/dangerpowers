# Phase 1: Evaluator Script — Implementation Plan

Companion to `developing-a-better-harness.md`, section "Evaluator Script Implementation".
This plan is decision-complete: every choice below is either a locked decision from the
design review or an explicitly registered assumption (see "Assumptions register"). The
implementing agent should not introduce new decisions; anything ambiguous is called out
here with the chosen behavior.

**Scope: the inner core only.** One invocation of the evaluator evaluates ONE query
(`--query` + `--expect`) for `reps` repetitions and reports the batch result — the
diagram's `eval_batch(reps)`. The outer campaign loop that walks a query set, the
train/validate split, and everything downstream are later phases and are NOT built here.

## Locked decisions (from design review with the user)

1. **No custom agent in this phase.** The `trigger-evaluator` agent is not copied into
   the workspace and `--agent` is not passed. It may be added later or dropped.
2. **`--auto` is used.** To keep the workspace harness-agnostic we do NOT write a
   `.opencode/opencode.json` permission config into the workspace. `--auto` auto-approves
   all tool calls. Accepted risk (probe-validated): a triggered run can execute arbitrary
   tools (file reads, web searches were observed). Blast radius is contained by the temp
   workspace, frontmatter-only skill stubs, and the per-run timeout. Runs cost more tokens
   than they would with the restricted agent. This is the documented future fix.
3. **Minimal core scope: single query per invocation.** The script takes exactly one
   `--query`/`--expect` pair and runs `reps` repetitions of it. NOT in scope: the outer
   campaign loop over a query set, queries-file loading, train/validate split,
   fresh-query sanity check, optimization loop, campaign logs, manifest.json,
   artifact management.
4. **Tri-state verdicts + Wilson lower bound scoring.** `Verdict.outcome` is
   `triggered | not-triggered | void`; a query's `score` is the lower bound of the
   95% Wilson score interval over non-void runs.
5. **Report/log output goes to stdout only.** stderr is used only for operational
   error messages (validation failures, exit 1). No run artifacts are written in
   this phase.
6. **`--thinking` is always passed** so the model's reasoning blocks are captured.
   Reasoning text is stored on `Verdict.reasoning` (restoring the design diagram's
   field) and is never used for signal detection or scoring. Reasoning content is
   provider/model-dependent; when a model emits none, the field is empty (not an
   error).
7. **Fail-fast on harness execution failure.** If the harness cannot execute the
   query at all (invalid arguments, nonzero exit, provider/infra error, empty event
   stream), the evaluator aborts: no further reps or batches are started, the error
   is reported to the user on stderr, and the script exits 1. Harness failures are
   NOT void verdicts and never enter scoring. Timeouts remain void verdicts — the
   harness executed, the eval was inconclusive.
8. **Smoke rep first, then parallel batches.** Rep 1 runs alone as a smoke test; a
   harness failure there aborts before any further spend. Remaining reps run in
   parallel batches of at most 10 (`ThreadPoolExecutor(max_workers=10)` over
   subprocesses). Batches run sequentially between groups.
9. **Progress logging.** Emit a log line when a rep starts (with rep number), when a
   rep completes (with its outcome: trigger/no-trigger/void), and on errors.
   Start/complete logs go to stdout (decision 5); errors go to stderr.

## Prerequisite already applied

`skills/trigger-testing-skills/scripts/workspace-manager.sh` was edited: `init` no longer
creates the unused `.agents/agents/` directory (opencode never resolved agents from there).
No other changes to that script in this phase.

## Probe evidence this plan relies on

All validated against the installed opencode CLI with a scratch workspace:

- `opencode run` supports `--pure`, `--auto`, `--format json`, `--dir`, `--model`,
  `--variant`, `--print-logs`, `--log-level` (verified via `--help`).
- With `--format json`, stdout is an NDJSON event stream. A skill load appears as:
  ```json
  {"type":"tool_use","sessionID":"...","part":{"type":"tool","tool":"skill",
    "state":{"status":"completed","input":{"name":"<skill>"}, ...}}}
  ```
  This event is the trigger signal. The final assistant text ("no skill matched." etc.)
  is NOT used as a signal.
- Provider failures appear as `{"type":"error","error":{"data":{"message":"..."}}}`
  (observed with an unreachable provider).
- With `--thinking`, reasoning blocks appear in the same stdout stream as
  `{"type":"reasoning","part":{"type":"reasoning","text":"..."}}` events (verified
  with `gpt-5.4-nano`). `--print-logs --log-level DEBUG` does NOT surface reasoning
  content — stderr logs are operational only (session/permission/file-touch lines).
- Skills placed at `<workspace>/.agents/skills/<name>/SKILL.md` are discovered when the
  session runs with `--dir <workspace>` (cwd may be anywhere).
- Without `--auto` and without a permission allowance, the skill tool call itself is
  auto-rejected headless ("The user rejected permission to use this specific tool call"),
  which is why `--auto` is required in this phase's configuration.

## Deliverable

One new file: `skills/trigger-testing-skills/scripts/evaluator.py`

- Python >= 3.10, standard library only (`argparse`, `dataclasses`, `json`, `math`,
  `pathlib`, `subprocess`, `sys`, `typing`). Run with the repo venv: `.venv/bin/python3`.
- Shebang `#!/usr/bin/env python3`; make executable (`chmod +x`) for consistency with
  `workspace-manager.sh`.

## CLI contract

```
usage: evaluator.py run --skill NAME --workspace DIR
                        --query TEXT --expect trigger|not-trigger
                        [--model MODEL] [--variant EFFORT] [--reps N]
                        [--timeout SECONDS]
```

Implemented with `argparse` subparsers; `run` is the only subcommand (leaves room for
later subcommands when the outer campaign loop is built).

| arg         | required | default | meaning                                        |
|-------------|----------|---------|------------------------------------------------|
| `--skill`     | yes | —      | skill under test; stub must exist in workspace |
| `--workspace` | yes | —      | workspace dir from workspace-manager `init`    |
| `--query`     | yes | —       | the exact test query, verbatim                 |
| `--expect`    | yes | —       | `trigger` or `not-trigger`                     |
| `--model`     | no  | —       | passed as `--model`; omitted from command if unset |
| `--variant`   | no  | —       | passed as `--variant`; omitted from command if unset |
| `--reps`      | no  | 10      | repetitions of the query                       |
| `--timeout`   | no  | 30      | per-run timeout in seconds                     |

Validation before any eval runs (each failure: exact reason to stderr, exit 1):

- `workspace/.agents/skills/<skill>/SKILL.md` must exist, else:
  `error: skill stub not synced: <path>; run workspace-manager.sh sync`
- `--reps` >= 1, `--timeout` >= 1.

Exit codes: `0` = batch ran to completion (regardless of pass/fail counts);
`1` = operational/validation error OR harness execution failure (batch aborted,
see locked decision 7); `2` = argparse usage errors (argparse default).

## Data structures

```python
from dataclasses import dataclass, field
from typing import Literal

Outcome = Literal["triggered", "not-triggered", "void"]

@dataclass
class EvalCase:
    query: str
    should_trigger: bool

@dataclass
class Verdict:
    outcome: Outcome
    detail: str = ""        # timeout note or signal status
    session_id: str = ""
    reasoning: str = ""     # concatenated --thinking blocks; never used for scoring

class HarnessExecutionError(Exception):
    """The harness could not execute the query (bad args, nonzero exit, provider
    error, empty event stream). Fatal: aborts the batch, exits 1. Never a verdict."""

@dataclass
class BatchResult:
    case: EvalCase
    verdicts: list[Verdict] = field(default_factory=list)
    passed: int = 0         # non-void runs matching expectation
    failed: int = 0         # non-void runs mismatching expectation
    void: int = 0
    wilson_low: float | None = None   # None when passed + failed == 0
    wilson_high: float | None = None
    score: float | None = None        # == wilson_low
```

Note: the diagram's `Results.description` field is intentionally omitted — it exists for
the optimization loop's version comparison, which is out of scope this phase.

## Strategy: command construction and verdict parsing

```python
class OpencodeStrategy:
    def __init__(self, timeout: int = 30): ...

    def evaluate(self, skill: str, query: str, workspace: Path,
                 model: str | None = None, effort: str | None = None) -> Verdict:
        cmd = ["opencode", "run", "--pure", "--auto", "--thinking",
               "--format", "json", "--dir", str(workspace)]
        if model is not None:
            cmd += ["--model", model]
        if effort is not None:
            cmd += ["--variant", effort]
        cmd.append(query)
        ...
```

Execution:

```python
proc = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout)
```

- `subprocess.TimeoutExpired` → `Verdict("void", detail=f"timeout after {self.timeout}s")`.
  (`subprocess.run` kills the child on timeout.)

Parsing rules, applied in this exact precedence order:

1. Scan every line of `proc.stdout`; `json.loads` each, skip lines that fail to parse.
   Remember the first `sessionID` seen on any event.
2. Events with `type == "reasoning"`: append `part.text` to a list; at the end join
   with `"\n"` into `Verdict.reasoning`. Never used for signal detection or scoring.
3. **Signal (wins over everything):** any event with `type == "tool_use"` whose
   `part.tool == "skill"` and `part.state.input.name == skill`
   → `Verdict("triggered", detail=f"skill tool invoked (status=<state.status>)",
   session_id=<sessionID>)`. The event's completion status is recorded but not required
   (matches the existing skill's abort-after-signal rule).
4. A `tool_use` for `tool == "skill"` with a DIFFERENT `input.name` is not our signal;
   remember the other name for rule 6.
5. Any event with `type == "error"` → remember `error.data.message`
   (fallback: `str(error)`); keep scanning.
6. End of stream, no signal, evaluated in this order:
   - error event seen, OR `proc.returncode != 0`, OR zero parseable events
     → `raise HarnessExecutionError(detail)` where detail is the remembered error
     message, else `exit <returncode>: <last 500 chars of stderr>`, else
     `"no parseable events (exit 0)"`. (Signal still wins: a run that loaded the
     skill before erroring is `triggered`, not an abort.)
   - otherwise → `Verdict("not-triggered", session_id=<sessionID>)`,
     with `detail=f"other skill loaded: <name>"` if rule 4 fired.

Per-run stderr from opencode is captured but otherwise ignored; it only feeds
`HarnessExecutionError` detail. `--print-logs` / `--log-level` are NOT passed
(assumption, see register).

## Batch loop and scoring

```python
def eval_batch(strategy: OpencodeStrategy, skill: str, case: EvalCase,
               workspace: Path, model: str | None, effort: str | None,
               reps: int) -> BatchResult:
    ...
```

Execution order (locked decisions 7 and 8):

1. **Smoke rep (rep 1) runs alone.** If it raises `HarnessExecutionError`, print
   `error: harness could not execute the query: <detail>` to stderr and exit 1 —
   no further reps are attempted. A `void` (timeout) smoke rep does NOT abort.
2. **Remaining reps (2..N) run in parallel batches of at most 10.** Each batch uses
   `ThreadPoolExecutor(max_workers=10)`; batches are sequential between groups
   (e.g. `--reps 25` → smoke rep + batches of 10, 10, 4).
3. **Harness failure inside a batch:** in-flight reps are allowed to settle, no new
   batches are started, the first error is reported on stderr as
   `error: rep <n> could not execute: <detail>` followed by `error: batch aborted`,
   exit 1.
4. Verdicts are stored by rep number so the final report is deterministic.

Progress logs on stdout, printed as events happen (completion order may differ from
rep order under parallelism):

```
[rep  1] started
[rep  1] completed: triggered
[rep  3] started
[rep  2] started
[rep  3] completed: not-triggered
[rep  4] completed: void (timeout after 30s)
```

Exact formats: start = `[rep {n:>3}] started`; complete =
`[rep {n:>3}] completed: {outcome}` with ` ({detail})` appended for voids.
Print with `flush=True`.

- Non-void run scores as pass iff `(outcome == "triggered") == case.should_trigger`.
- Voids are counted separately and never enter the pass rate.
- Wilson score interval (95%, z = 1.96) over `n = passed + failed` (voids excluded):

```python
def wilson_interval(passed: int, n: int, z: float = 1.96) -> tuple[float, float]:
    p = passed / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return center - margin, center + margin
```

- If `n == 0` (all runs void): `wilson_low = wilson_high = score = None`.
- `score = wilson_low` (locked decision 4).

## Report format (stdout only)

Everything below is printed to stdout. stderr carries only operational error
messages (the validation failures listed under "CLI contract").

Header (printed first, before the smoke rep), then live progress logs (see "Batch
loop and scoring"), then the report block after all reps complete, in rep-number
order regardless of completion order (mirrors the existing skill's report format,
plus the interval/score):

```
trigger test: <skill>
workspace: <path>
model: <model or "(default)">  variant: <variant or "(none)">  reps: <n>  timeout: <n>s

query: "<query>"   expected: trigger|not-trigger
  run  1: triggered      pass
  run  2: not-triggered  fail
  run  3: void           —  detail: timeout after 30s
  summary: 8 pass / 1 fail / 1 void (10 runs)  wilson95: [0.462, 0.974]  score: 0.462
```

If the batch aborts on a harness failure, no report block is printed — the error
lines on stderr are the report.

Formatting rules: `run` index right-aligned width 3; outcome left-aligned width 13
(`"not-triggered"` is the longest); then `pass`, `fail`, or `—`; void lines append
`  detail: <detail>`. When `n == 0`: `wilson95: n/a (all void)  score: n/a`.
There is no overall/campaign line — one invocation covers exactly one query.

## Exact validation commands

Run from the repo root (`/home/dave/source/dangerpowers`):

```bash
# 1. Build a workspace by hand (workspace is managed manually this phase)
WS="$(skills/trigger-testing-skills/scripts/workspace-manager.sh init)"
skills/trigger-testing-skills/scripts/workspace-manager.sh sync \
  --skill writing-skills --source . --workspace "$WS"
skills/trigger-testing-skills/scripts/workspace-manager.sh status \
  --skill writing-skills --source . --workspace "$WS"
# expected: "ok: writing-skills stub matches source"

# 2. Smoke run, positive case: 3 reps, cheap model
.venv/bin/python3 skills/trigger-testing-skills/scripts/evaluator.py run \
  --skill writing-skills --workspace "$WS" \
  --query "turn this outline into a skill" --expect trigger \
  --model opencode/gpt-5.4-nano --reps 3 --timeout 60
# expected: exit 0; report on stdout; runs mostly "triggered"/pass.

# 3. Smoke run, negative case
.venv/bin/python3 skills/trigger-testing-skills/scripts/evaluator.py run \
  --skill writing-skills --workspace "$WS" \
  --query "what is the capital of France?" --expect not-trigger \
  --model opencode/gpt-5.4-nano --reps 3 --timeout 60
# expected: exit 0; runs "not-triggered"/pass.

# 4. Harness-failure path: unreachable provider -> smoke rep aborts the batch
.venv/bin/python3 skills/trigger-testing-skills/scripts/evaluator.py run \
  --skill writing-skills --workspace "$WS" \
  --query "turn this outline into a skill" --expect trigger \
  --model ollama/nonexistent --reps 5
# expected: exit 1; exactly one "[rep  1] started" log; stderr names the provider
# failure; NO further reps attempted; no report block.

# 5. Void path: force timeouts with a 1s timeout
.venv/bin/python3 skills/trigger-testing-skills/scripts/evaluator.py run \
  --skill writing-skills --workspace "$WS" \
  --query "turn this outline into a skill" --expect trigger \
  --model opencode/gpt-5.4-nano --reps 3 --timeout 1
# expected: exit 0; smoke rep voids but does NOT abort; all 3 runs report
# "void" (timeout after 1s); summary shows "wilson95: n/a (all void)  score: n/a".

# 6. Cleanup
skills/trigger-testing-skills/scripts/workspace-manager.sh cleanup --workspace "$WS"
```

Note: running the full `skills-workspace/writing-skills/trigger-tests/queries.json`
set is intentionally NOT shown here — iterating a query file is the outer campaign
loop, a later phase. For broader manual validation, invoke the script once per query.

## Assumptions register (flag any you want reversed before implementation)

1. **Wilson interval is computed over non-void runs only** (n = pass + fail). Voids are
   reported, never scored. Matches the existing skill's "neither pass nor fail" rule.
2. **`--variant` is a free-form passthrough**; no effort enum. The design doc's enum
   sentence trails off, and valid values are provider/model-specific ("high, max,
   minimal" per CLI help). Invalid values surface as harness errors → batch abort
   (locked decision 7).
3. **`--print-logs` / `--log-level INFO` from the design's command block are omitted.**
   They only affect stderr noise; parsing uses the JSON stdout stream. Easy to add later
   behind a `--verbose` flag if wanted. (`--thinking` IS always passed — locked
   decision 6 — because it adds reasoning events to the parseable stdout stream;
   reasoning content is provider/model-dependent and may be absent.)
4. **`Results.description` is omitted** (see Data structures note).
5. **Parallelism is threads over subprocesses** (`ThreadPoolExecutor`, batches of
   ≤10 — locked decision 8). Rate-limit/backoff handling is out of scope: provider
   429s surface as `type:"error"` events → harness failure → batch abort (decision 7).
6. **Timeouts are the only remaining source of void verdicts.** Everything that
   prevents the query from executing at all is a harness failure that aborts
   (decision 7). Rationale: a void means "ran, inconclusive"; a harness failure
   means the whole campaign's conditions are broken and results would be garbage.
7. **Exit 0 with zero parseable events is a harness failure**, not a not-trigger:
   an empty stream means we cannot confirm the query ever executed.
8. **Report and logs to stdout only** (locked decision 5); stderr carries only
   operational error messages and harness-failure aborts. No machine-readable
   summary is emitted in this phase.
9. **Exit code 0 even when evals fail.** There is no pass threshold yet; thresholds
   belong to the optimization-loop phase. (Harness failures still exit 1.)
10. **The opencode detection signal is the `tool_use` event only.** The final assistant
    text is never parsed (matches the existing skill's "signal is the only evidence").
11. **Live progress logs print in completion order; the final report block is in
    rep-number order** so reports stay deterministic and diffable.

## Known limitations / accepted risks

- `--auto` lets a triggered session run arbitrary tools inside the workspace (locked
  decision 2). Mitigations: disposable temp workspace, frontmatter-only stubs, timeout.
- Without the restricted agent, the default agent may attempt extra (blocked or
  auto-approved) steps after loading the skill, burning tokens. Observed ~13k tokens /
  ~$0.002 per run with a nano model when it wandered; ~1.5k tokens / ~$0.0003 when it
  stopped immediately.
- `opencode run` startup dominates run time; the 30s default timeout is generous.
- Parallel batches multiply provider load by up to 10x; rate limits surface as
  harness failures and abort the batch (no retry/backoff in this phase).
