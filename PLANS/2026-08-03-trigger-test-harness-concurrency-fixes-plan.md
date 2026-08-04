---
artifact: implementation-plan
date: 2026-08-03
git_commit: 2af4f72
branch: dev/sloptime
request: "write a quick-plan to implement these fixes. do not implement now." (fixes: description-hash staleness detection, timeout-as-void semantics, bounded-parallel batch mode with backoff for trigger-test.sh and the trigger-testing skill)
source_prd: none
source_bundle: none (quick pass)
source_research: none (quick pass)
status: approved
---

# Trigger-Test Harness Concurrency and Staleness Fixes Implementation Plan

## Context

A verification round against `skills/writing-plans/test-campaigns/2026-08-03-writing-plans-trigger.md` exposed three harness weaknesses:

1. **Stale logs are undetectable.** The logged description differed from the live `skills/writing-plans/SKILL.md:3` description (edited after the campaign closed). No campaign log records a hash of the description under test — only verbatim pastes (`skills/trigger-testing/test-campaigns/2026-08-03-trigger-testing-trigger.md:14,24`) — so staleness can only be found by eyeball-diffing.
2. **Timeouts masquerade as measurements.** `trigger-test.sh:115` hardcodes `timeout 300`; exit 124 is emitted as `exit_code` but the verdict logic (`trigger-test.sh:139-145`) reports `not-loaded` regardless. On a saturated local model, an overload-induced timeout silently records a false negative. `skills/trigger-testing/SKILL.md:162` codifies this ("killed by the script's timeout guard and reports not-loaded"), tracing to FR-012 in `PRDS/2026-07-31-isolated-trigger-testing-harness.md:95`.
3. **Unbounded parallel fan-out overloads local models.** `skills/trigger-testing/SKILL.md:164` instructs the runner to launch the entire rep matrix as concurrent background jobs with no cap and no backoff. No script implements bounded parallelism — no `xargs -P`, `wait -n`, or job pool exists anywhere in the repo. The verification run launched 15 concurrent evals; all 15 exited 124.

## Current State

- `skills/trigger-testing/scripts/trigger-test.sh` (202 lines) has four subcommands: `init`, `eval`, `sync`, `cleanup` (`trigger-test.sh:194-202`). `eval` runs exactly one scenario with a hardcoded 300s timeout (`:115`), parses the JSONL event stream for skill-load signals (`:118-132`), and prints a six-line verdict block ending in `exit_code` (`:147-148`).
- `skills/trigger-testing/SKILL.md` documents: timeout-killed runs report not-loaded (`:162`); ad-hoc concurrent background jobs for the rep matrix (`:164`); a Results Log Format whose iteration block pastes the description verbatim with no hash (`:214-227`); a Common Mistakes table (`:189-206`) with no row for overload or staleness.
- Validation infrastructure: no Makefile, no CI. Shell tooling is available system-wide via the nix store: **shellcheck 0.11.0** and **shunit2 2.1.8** (both on PATH). The one pre-existing check command is `agentskills validate skills/<name>` (`.venv/bin/agentskills`, per `skills/writing-skills/SKILL.md:70`). No shunit2 suites exist yet — this plan introduces the first; there is no established test-file location convention.
- `agents/trigger-evaluator.md:5` caps eval reps at `steps: 3` with only the `skill` tool allowed (`:6-18`).

## Desired End State

- `trigger-test.sh eval` accepts `--timeout SECS` (default 300) and emits a `timed_out: yes|no` line in the verdict block.
- New `batch` subcommand: bounded job pool (default `--jobs 2`), per-rep verdict files, automatic serial retry of timed-out-without-load reps, indexed verdict blocks plus a summary line on stdout.
- New `status` subcommand: diffs a workspace stub against the live `SKILL.md` frontmatter and reports `in-sync` or `stale` (exit 0/1).
- `skills/trigger-testing/SKILL.md` updated: timeout/void semantics, batch-driven parallelism replacing the ad-hoc fan-out paragraph, description-sha256 line in the Results Log Format, new Common Mistakes rows.
- New shunit2 suite `skills/trigger-testing/scripts/test-trigger-test.sh` covers the script's pure and fixture-testable logic; `shellcheck` runs clean on both script files.
- All changes validated by the shunit2 suite, shellcheck, a behavioral smoke run through a fresh workspace, and `agentskills validate skills/trigger-testing`.

## What We're NOT Doing

- **No changes to pressure-testing.** Its fan-out is agent-dispatched via the task tool (`skills/pressure-testing/SKILL.md:89`), not `trigger-test.sh`; it shares no harness code with trigger-testing.
- **No description change to trigger-testing**, so no trigger-eval re-campaign is required for it.
- **No changes to `agents/trigger-evaluator.md`** — its step cap and tool surface are unchanged.
- **No bats framework** introduced; shunit2 (already on PATH) is the test runner.
- **No retroactive hash annotation** of existing campaign logs.
- **No edits to PRDS/2026-07-31-isolated-trigger-testing-harness.md** — FR-012's timeout-as-not-loaded decision is superseded here; the plan's Decisions table records the supersession.

## Decisions

| Conflict / Question | Pick | Rationale |
|---------------------|------|-----------|
| Where does concurrency control live: runner agent ad-hoc (current `SKILL.md:164`) vs. script `batch` subcommand | Script `batch` subcommand | The ad-hoc approach produced a 15/15 timeout sweep in the verification round. Backoff logic in tested bash runs the same way every campaign; an agent improvising it does not. |
| Timeout semantics: not-loaded (FR-012, `SKILL.md:162`) vs. void | Split: timeout **with** a detected load keeps its verdict; timeout **without** a load is void and retried | The load decision is the measurement (`SKILL.md:158`). If the load signal is in the event stream, the measurement happened; if the run was killed first, the outcome is unknown and counting it as not-loaded fabricates a false negative. Mirrors the existing void convention for unparseable verdicts (`SKILL.md:160`). |
| Default `--jobs` value | 2 | The failure mode was observed on a local model; 2 is safe there and still halves wall time vs. serial. Remote-model users pass `--jobs` higher. |
| Backoff strategy | Halve concurrency on any void rep, floor 1; retries always serial with a fresh timeout | Simple, monotone, and terminates. Exponential backoff on *time* is wrong here — the resource is concurrency slots, not delay. |
| Batch scenario input format | `--scenarios FILE`, one query per line, blank lines skipped | Eval queries are single-line by convention (existing `trigger-evals/*.json` all are); a line-based file is trivially writable by the runner via the Write tool and avoids shell-quoting a 15-query argv. |
| Hash algorithm and length for log pinning | sha256, first 12 hex chars, computed over the raw description scalar | Matches `git rev-parse --short` conventions; 12 chars is ample to detect drift. |
| Include a `status` subcommand or document manual diff | Include `status` | ~15 lines of bash reusing `extract_frontmatter` (`trigger-test.sh:36-42`); makes mid-campaign drift checks mechanical instead of a remembered rule. |
| Whether `eval` prints `void` itself on timeout | No — `eval` adds `timed_out: yes|no`; only `batch` and the runner apply the void rule | A timeout after a detected load is a valid measurement; `eval` cannot know the caller's retry budget. Appending one line to the verdict block is backward-compatible — nothing parses the block mechanically downstream. |
| Test file location (no existing convention) | `skills/trigger-testing/scripts/test-trigger-test.sh`, beside the script under test | Only two scripts exist in the repo and neither has tests; co-locating in `scripts/` keeps the suite discoverable and mirrors the `trigger-evals/` beside-the-skill convention. |
| How to test `batch`/`eval` without a real model | Stub `opencode` on PATH inside the shunit2 suite: a fake executable emitting canned JSONL event streams (load, no-load, hang-for-timeout via `sleep`) | The script invokes `opencode run` by name (`trigger-test.sh:115`), so PATH injection needs no script changes and exercises the real parsing/verdict/timeout code paths. |

## Implementation Approach

Two files change: `skills/trigger-testing/scripts/trigger-test.sh` (new flags + two subcommands) and `skills/trigger-testing/SKILL.md` (semantics, parallelism guidance, log format, mistakes table). Script first, then skill text to match the shipped behavior, then behavioral validation through a real workspace.

## Changes Required

#### 1. `skills/trigger-testing/scripts/trigger-test.sh`

**File:** `skills/trigger-testing/scripts/trigger-test.sh`

**Changes:**

a. **`eval`: add `--timeout` flag and `timed_out` verdict field.** In `cmd_eval` (`:81-149`): parse `--timeout` into `local timeout_s=300`; replace `timeout 300 opencode run` (`:115`) with `timeout "$timeout_s" opencode run`; after the run compute `timed_out=no` and set `timed_out=yes` when `rc=124`; append `timed_out: %s` to the printf at `:147-148`.

b. **New `batch` subcommand.** Signature: `batch --skill NAME [--workspace DIR] [--model P/M] --scenarios FILE [--jobs N] [--timeout SECS]`. Behavior:
- Defaults: `jobs=2`, `timeout=300`. Validate `--scenarios` file exists; read non-blank lines into an indexed array.
- Create a results dir inside the workspace: `"$ws/.batch.$$"`; per-rep output at `.batch.$$/scenario-<i>.txt`.
- Job pool loop: launch up to `$jobs` background `cmd_eval`-equivalent invocations (call `cmd_eval` directly with output redirected), using `wait -n` to refill slots as jobs finish.
- After the pool drains, scan each verdict file: a rep is **void** when `timed_out: yes` AND `verdict: not-loaded`, or when the verdict block is missing/unparseable.
- Retry pass: rerun every void rep **serially** (jobs=1, fresh timeout each), overwriting its verdict file. Reps still void after the serial retry are reported as `verdict: void`.
- Stdout: for each scenario, `=== scenario <i>: <first 72 chars of query> ===` followed by its final verdict block; then one summary line: `batch summary: <n> scenarios, <k> void after serial retry`.
- Update `usage()` (`:4-33`) and the command dispatch case (`:196-202`).

c. **New `status` subcommand.** Signature: `status --skill NAME [--workspace DIR] [--source DIR]`. Reuse the workspace/source resolution from `cmd_sync` (`:151-167`). Extract the live frontmatter via `extract_frontmatter` to a temp file, `diff -q` against `"$ws/.agents/skills/$skill/SKILL.md"`; print `in-sync: <skill>` and exit 0 on match, `stale: <skill>` and exit 1 on difference. Add to `usage()` and dispatch.

#### 2. `skills/trigger-testing/scripts/test-trigger-test.sh` (new)

**File:** `skills/trigger-testing/scripts/test-trigger-test.sh`

**Changes:** shunit2 suite, executable, `#!/usr/bin/env bash` shebang, sourced `shunit2` at the end. A `setUp` fixture creates a throwaway workspace via `mktemp -d` with a minimal `.agents/skills/<name>/SKILL.md` stub set; `tearDown` removes it. A `stub-opencode` helper writes a fake `opencode` executable into a fixture `bin/` dir prepended to PATH per-test, emitting canned JSONL: a `tool_use` skill-load event (load case), a text-only stream (no-load case), or `sleep 999` (hang case).

Tests:
- `extract_frontmatter`: extracts up to the closing `---`; exits 1 on missing/unterminated frontmatter.
- `usage`/dispatch: unknown subcommand exits non-zero; `eval` without `--skill` fails.
- `status`: in-sync stub prints `in-sync` / exit 0; after editing the live source description, prints `stale` / exit 1.
- `eval` verdict parsing (stubbed opencode): load case → `verdict: loaded`; no-load case → `verdict: not-loaded`; sibling-load case → `conflict: wrong-skill`.
- `eval` timeout: `--timeout 2` against the hanging stub → `timed_out: yes`, `exit_code: 124`.
- `batch` pool bound: 4 scenarios at `--jobs 2` with the stubbed opencode recording its max concurrency (atomic mkdir lock counter) → observed max ≤ 2.
- `batch` void retry: scenarios including the hang case at `--timeout 2` → hanging rep retried serially, final block reports `verdict: void`, summary line counts it.
- `batch` summary: `batch summary: <n> scenarios, <k> void after serial retry` present and counts correct.

#### 3. `skills/trigger-testing/SKILL.md`

**File:** `skills/trigger-testing/SKILL.md`

**Changes:**

a. **Workload isolation paragraph (`:162`).** Replace "A hung `opencode run` is killed by the script's timeout guard and reports not-loaded" with the split semantics: a timed-out rep whose event stream already contains the candidate's load signal keeps its verdict; a timed-out rep with no load signal is **void** — retry serially, never count it. Reference the new `timed_out:` verdict field.

b. **Intra-iteration rep parallelism paragraph (`:164`).** Replace the ad-hoc background-jobs instruction with: run the rep matrix through `trigger-test.sh batch --scenarios FILE` at the default `--jobs 2`; raise `--jobs` only when reps consistently finish well under the timeout (remote/fast models); on local models keep the default and let batch's serial retry absorb timeouts. Keep the sentence clarifying that intra-phase fan-out does not violate `Parallel group: none`.

c. **Results Log Format (`:208-227`).** In the iteration block, add a line directly under `Description (≤1024 chars):` — `Description sha256 (first 12): <hash>` — and add one sentence to the section prose: compute with `sed -n 's/^description: //p' skills/<name>/SKILL.md | sha256sum | cut -c1-12` at selection time so later verification runs can detect post-campaign description drift.

d. **Common Mistakes table (`:189-206`).** Add two rows:
   - "Launching the full rep matrix as unbounded parallel jobs" → "Use `trigger-test.sh batch` at the default `--jobs 2`; unbounded fan-out saturates local models and every rep times out"
   - "Counting a timed-out rep as not-loaded" → "Check `timed_out:` in the verdict block; timeout without a load signal is void — retry serially, never count it"

e. **Workflow step 3 (`:19-23`).** Add to step 3c's verification: `trigger-test.sh status --skill <candidate> --workspace WS_PATH` as the mechanical check that a stub matches the live SKILL.md before any eval round (also usable mid-campaign).

### Success Criteria

#### Automated Verification:
- `agentskills validate skills/trigger-testing` prints `Valid skill`.
- `bash -n skills/trigger-testing/scripts/trigger-test.sh` exits 0.
- `shellcheck skills/trigger-testing/scripts/trigger-test.sh skills/trigger-testing/scripts/test-trigger-test.sh` exits 0.
- `shunit2 skills/trigger-testing/scripts/test-trigger-test.sh` (or direct execution of the suite file) — all tests pass.
- `skills/trigger-testing/scripts/trigger-test.sh status --skill trigger-testing --workspace <WS>` after `init` prints `in-sync`; after appending a character to the live SKILL.md description (then reverting), prints `stale` and exits 1.
- A `batch` run of 3 should-trigger queries from `skills/trigger-testing/trigger-evals/train.json` against a fresh workspace at default `--jobs 2` completes with 3 verdict blocks, a `timed_out:` line in each, and a `batch summary:` line showing 0 voids.

#### Manual Verification:
- During the batch smoke run, `pgrep -c -f "opencode run --dir"` never exceeds 2 (pool bound holds).
- A deliberately tiny `--timeout 1` batch run produces void verdicts that are retried serially and reported as `void` in the summary, never counted as not-loaded.

## Testing Strategy

### Unit Tests:
The shunit2 suite `skills/trigger-testing/scripts/test-trigger-test.sh` (change 2 above), run via `shunit2 skills/trigger-testing/scripts/test-trigger-test.sh`. Covers frontmatter extraction, argument validation, `status` in-sync/stale, verdict parsing, `timed_out` on timeout, the batch pool bound, and void retry — all against stubbed `opencode` binaries, no model required. Plus `shellcheck` clean on both script files.

### Integration Tests:
The `batch` and `status` smoke runs in Success Criteria, executed against a real `init` workspace with the full 15-skill stub set — this exercises init → status → batch → cleanup end to end.

### Manual Testing Steps:
1. `init` a workspace; confirm `status` reports in-sync for all skills spot-checked.
2. Run the 3-query batch smoke (real model); confirm verdicts, `timed_out` fields, summary line, and the concurrency bound via `pgrep`.
3. Run the `--timeout 1` void-retry check (stubbed or real).
4. `cleanup` the workspace; confirm `/tmp/trigger-test.*` dir removed.
5. Run one real should-trigger eval from `skills/writing-plans/trigger-evals/validation.json` through `batch` to confirm no regression in detection behavior.

## Final Verification

`agentskills validate skills/trigger-testing` prints `Valid skill`; `bash -n` and `shellcheck` pass on both script files; the shunit2 suite passes; all smoke steps in Testing Strategy completed with the workspace cleaned up. No other skill's SKILL.md or script was modified.

## References

- PRD: none
- Bundle: none (quick pass) — evidence gathered in-session
- Research: none (quick pass) — evidence gathered in-session
- Superseded decision: FR-012 timeout semantics in `PRDS/2026-07-31-isolated-trigger-testing-harness.md:95`
- Origin log: `skills/writing-plans/test-campaigns/2026-08-03-writing-plans-trigger.md`
