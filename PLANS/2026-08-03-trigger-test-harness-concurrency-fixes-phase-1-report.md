---
artifact: implementation-report
date: 2026-08-03
plan: PLANS/2026-08-03-trigger-test-harness-concurrency-fixes-plan.md
phase: 1
status: DONE
git_commit_start: 61c3dcb5a9e9f10ff1529b2317bbd2ac13aa933b
git_commit_end: e97a3e0c2632d6495dbd8bd8d7480457c8303fab
---

# Phase 1: Trigger-Test Harness Concurrency and Staleness Fixes — Implementation Report

## Summary

Implemented all three Changes Required items: `trigger-test.sh` gained `--timeout`/`timed_out` on `eval`, a new bounded-pool `batch` subcommand with serial void-retry, and a new `status` staleness subcommand; a new 12-test shunit2 suite covers the fixture-testable logic against stubbed `opencode` binaries; `SKILL.md` documents the split timeout semantics, batch-driven parallelism, description-sha256 log pinning, two new Common Mistakes rows, and the `status` check in Workflow step 3c. All six automated criteria pass, including the real-model 3-query batch smoke (3/3 loaded, 0 voids) and the init-workspace in-sync/stale check. A live model was available, so evidence for both manual items was also gathered (left unchecked for human sign-off).

## Changes Made

#### 1. Harness script
**File**: `skills/trigger-testing/scripts/trigger-test.sh`
**Changes**: (a) `cmd_eval` parses `--timeout` (default 300), uses it in the `timeout` invocation, and appends `timed_out: yes|no` (yes on rc 124) to the verdict block. (b) New `cmd_batch`: `--scenarios` line-based file (blank lines skipped), results in `$ws/.batch.$$/scenario-<i>.txt`, job pool capped at `--jobs` (default 2) via a running-count + `wait -n` refill loop, void detection via `batch_rep_is_void` (`timed_out: yes` + `verdict: not-loaded`, or missing/unparseable verdict), one serial retry pass per void rep with still-void reps rewritten to `verdict: void`, indexed `=== scenario <i>: <72 chars> ===` blocks and a `batch summary:` line on stdout. (c) New `cmd_status`: reuses sync-style workspace/source resolution, `extract_frontmatter` to a temp file, `diff -q` against the stub, prints `in-sync: <skill>` (exit 0) or `stale: <skill>` (exit 1). `usage()` and dispatch updated for both.

#### 2. Test suite (new)
**File**: `skills/trigger-testing/scripts/test-trigger-test.sh`
**Changes**: Executable shunit2 suite (`#!/usr/bin/env bash`, `. shunit2` at the end). `setUp` builds a mktemp fixture source tree (alpha/beta skills + stub agent) and a real workspace via `init`; `tearDown` runs `cleanup` and removes the fixture. Stub helpers write fake `opencode` binaries (load / no-load / hang / conditional-hang-with-invocation-log / mkdir-lock concurrency counter) into a fixture `bin/` prepended to PATH per test. 12 tests: frontmatter extraction boundary, unterminated-frontmatter rejection (with orphan-workspace cleanup), unknown-subcommand and missing-`--skill` failures, `status` in-sync/stale, load/no-load/sibling-conflict verdict parsing, `--timeout 2` hang → `timed_out: yes` + `exit_code: 124`, 4-scenario pool bound ≤2 at `--jobs 2`, void retry (hang rep runs exactly twice, single `target:` line in void block), and summary-line counts.

#### 3. Skill documentation
**File**: `skills/trigger-testing/SKILL.md`
**Changes**: (a) Workload-isolation paragraph rewritten to the split timeout semantics (load signal present keeps verdict; absent = void, serial retry, never counted), referencing `timed_out:` and batch's automatic handling. (b) Rep-parallelism paragraph now routes the rep matrix through `trigger-test.sh batch` at default `--jobs 2` with raise-only-when-fast guidance; `Parallel group: none` clarification kept. (c) `Description sha256 (first 12):` line added to the iteration log template plus the `sed | sha256sum | cut -c1-12` computation sentence. (d) Two Common Mistakes rows (unbounded fan-out; counting timed-out reps as not-loaded). (e) Workflow step 3c now requires `status --skill <candidate>` to print `in-sync` before evals. Also added `exit_code`/`timed_out` to the Detection verdict-block example.

## Verification

Every Automated Verification criterion from the phase, run exactly as written:

| Criterion | Command | Result |
|-----------|---------|--------|
| agentskills validate prints `Valid skill` | `.venv/bin/agentskills validate skills/trigger-testing` | PASS |
| bash -n exits 0 | `bash -n skills/trigger-testing/scripts/trigger-test.sh` | PASS |
| shellcheck exits 0 on both scripts | `shellcheck skills/trigger-testing/scripts/trigger-test.sh skills/trigger-testing/scripts/test-trigger-test.sh` | PASS |
| shunit2 suite all pass | `skills/trigger-testing/scripts/test-trigger-test.sh` (direct execution — see Issues) | PASS (12/12) |
| status in-sync / stale via init workspace | `trigger-test.sh status --skill trigger-testing --workspace /tmp/trigger-test.3LI2Arfcib` after `init`; then after appending `~` to the live description; then after revert | PASS |
| batch smoke: 3 should-trigger queries, fresh workspace, `--jobs 2` | `trigger-test.sh batch --skill trigger-testing --workspace <WS> --scenarios <3 queries from train.json> --jobs 2` | PASS |

Relevant output excerpts:

```text
$ .venv/bin/agentskills validate skills/trigger-testing
Valid skill: skills/trigger-testing

$ skills/trigger-testing/scripts/test-trigger-test.sh
Ran 12 tests.
OK

$ WS=$(... init) && trigger-test.sh status --skill trigger-testing --workspace $WS
in-sync: trigger-testing            (rc=0)
# after appending one char to the live description:
stale: trigger-testing              (rc=1)
# after reverting:
in-sync: trigger-testing            (rc=0)

$ trigger-test.sh batch --skill trigger-testing --workspace $WS --scenarios smoke-scenarios.txt --jobs 2
=== scenario 0: I need to test if my skill description triggers correctly on user prompt ===
verdict: loaded ... exit_code: 0 / timed_out: no
=== scenario 1: run a trigger-eval campaign to measure if my skill loads on the right qu ===
verdict: loaded ... exit_code: 0 / timed_out: no
=== scenario 2: I'm designing a new skill and need to validate its trigger behavior befo ===
verdict: loaded ... exit_code: 0 / timed_out: no
batch summary: 3 scenarios, 0 void after serial retry
```

Manual Verification items are listed here unchecked, for the human (a live model WAS available; observed evidence inline, not counted as automated criteria):

- [ ] During the batch smoke run, `pgrep -c -f "opencode run --dir"` never exceeds 2 (pool bound holds).
  Observed: with the pattern as written the count hit 6 — the unanchored pattern also matches the `timeout 300 opencode run …` wrapper processes and the polling shell's own cmdline. Re-measured with an anchored pattern `pgrep -c -f "^opencode run --dir"` during a 3-scenario `--jobs 2` batch: **max = 2**. Recommend the human re-confirm with the anchored pattern.
- [ ] A deliberately tiny `--timeout 1` batch run produces void verdicts retried serially and reported as `void` in the summary, never counted as not-loaded.
  Observed: 3-scenario batch at `--timeout 1` → all three final blocks `verdict: void` / `timed_out: yes`, summary `batch summary: 3 scenarios, 3 void after serial retry`. No rep was counted not-loaded.

## Deviations

| Plan said | What was done instead | Why it was forced |
|-----------|----------------------|-------------------|
| `eval` writes its JSONL to `$ws/.trigger-test-last-run.jsonl` (pre-existing, plan silent) | Per-eval unique path via `mktemp "$ws/.trigger-test-run.XXXXXXXX.jsonl"` | Batch's parallel `cmd_eval` jobs all truncate+write the same file and then parse it — concurrent reps would interleave JSONL and corrupt each other's verdicts. Plan's desired end state (working bounded parallelism) requires this. No other file references the old path (only two historical PLANS docs). |
| SKILL.md Changes a–e (specific paragraphs) | Also updated the Detection paragraph sentence "A run that ends, times out, … is not-loaded" and added `exit_code`/`timed_out` to the verdict-block example | The old sentence directly contradicts the new void semantics shipped in the same section; the block example was already missing `exit_code` and now `timed_out`. Same-section consistency edits within the plan's intent ("skill text to match the shipped behavior"). |
| Job pool loop unspecified | Running-count variable + `wait -n \|\| true` instead of `jobs -pr` polling | `jobs` in command substitution is unreliable and a nonzero background job under `set -e` would abort `wait -n`; the count-based loop is deterministic and shellcheck-clean. |

## Issues & Concerns

- **`shunit2 <file>` invocation form does not work in this environment.** The `shunit2` on PATH (nix store, resholved) is the library script itself, not a runner wrapper — `shunit2 skills/.../test-trigger-test.sh` runs the library standalone and reports "unknown failure … Ran 0 tests". The plan anticipated this ("or direct execution of the suite file"); direct execution runs 12/12 OK and is the command recorded above and in Testing Strategy.
- **Pre-existing: `init` leaks its half-built workspace on failure** (e.g. unterminated frontmatter mid-loop) — the mktemp dir is orphaned with no printed path. The test suite cleans up after its own deliberate failure case. Suggested owner: a future hardening pass on `trigger-test.sh init` (trap-based cleanup on error).
- Fixed during execution: the void-block rewrite initially duplicated the `target:` line (caught by the real `--timeout 1` smoke, not the suite); fixed in the awk filter and a regression assertion added to `test_batch_void_retry`.

## Follow-ups

- Human: perform the two Manual Verification items (observed evidence above may inform but not replace sign-off); note the pgrep pattern anchoring caveat.
- Human/controller: flip the phase's Automated Verification checkboxes in the plan file (subagent mode — plan left untouched).
- Optional future hardening (out of scope): `init` cleanup-on-failure trap; Testing Strategy docs could record "direct execution" as the canonical suite invocation since `shunit2 <file>` is a no-op runner here.
