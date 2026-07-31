---
artifact: implementation-report
date: 2026-07-31
plan: PLANS/2026-07-31-isolated-trigger-testing-harness-plan.md
phase: 1
status: DONE
git_commit_start: 69a5c7de827c98e8a8439ed704f74d432944f03f
git_commit_end: 69a5c7de827c98e8a8439ed704f74d432944f03f
---

# Phase 1: Verify opencode CLI Behavior Empirically — Implementation Report

## Summary

All five checkpoints ran against opencode 1.18.3 and all four automated criteria pass. The plan's default assumptions held for discovery layout (`.agents/skills` + `.opencode/agents` in a non-git temp dir works first try), permissions (no `--auto` needed), global leakage (none observed), and the `--model` flag. Checkpoint A produced one significant falsification: the JSON event stream's tool-event type is `tool_use`, not `tool`, and the captured stream contains a non-JSON stderr line that breaks naive `jq` parsing — Phase 2's jq filter must skip invalid lines and match `tool_use`. No repo files were touched; all scratch lived under `/tmp`.

## Changes Made

No repo files (as specified by the phase). Scratch artifacts only:

#### 1. Schema spike capture
**File**: `/tmp/opencode/trigger-schema-spike.json`
**Changes**: captured `--format json` event stream of a `trigger-evaluator` run against the live repo (Checkpoint A)

#### 2. Layout spike capture + workspace path record
**File**: `/tmp/opencode/trigger-layout-spike.json`, `/tmp/opencode/trigger-layout-spike.ws`
**Changes**: captured event stream of a run inside a `mktemp -d /tmp/trigger-layout-spike.XXXXXXXXXX` stub workspace (Checkpoints B–D); the `.ws` file only records the temp path so it could be reused across shell invocations

#### 3. Model spike capture
**File**: `/tmp/opencode/trigger-model-spike.json`
**Changes**: captured event stream of a `--model opencode/big-pickle` run with a known-negative query (Checkpoint E)

The spike workspace (`/tmp/trigger-layout-spike.1RwpppYlhh`) was removed after Checkpoint E per the plan's cleanup instruction.

## Verification

Every Automated Verification criterion from the phase, run exactly as written:

| Criterion | Command | Result |
|-----------|---------|--------|
| CLI identity confirmed | `opencode --version` | PASS |
| Schema spike produced a load signal | `grep -q '"tool":"skill"' /tmp/opencode/trigger-schema-spike.json && grep -q '"name":"writing-prds"' /tmp/opencode/trigger-schema-spike.json && echo SCHEMA-SPIKE-OK` | PASS |
| Layout spike produced a load signal | `grep -q '"name":"writing-prds"' /tmp/opencode/trigger-layout-spike.json && echo LAYOUT-SPIKE-OK` | PASS |
| Model flag accepted | `test -s /tmp/opencode/trigger-model-spike.json && echo MODEL-SPIKE-OK` | PASS |

Output evidence:

```text
$ opencode --version
1.18.3

$ grep -q '"tool":"skill"' ... && grep -q '"name":"writing-prds"' ... && echo SCHEMA-SPIKE-OK
SCHEMA-SPIKE-OK

$ grep -q '"name":"writing-prds"' /tmp/opencode/trigger-layout-spike.json && echo LAYOUT-SPIKE-OK
LAYOUT-SPIKE-OK

$ test -s /tmp/opencode/trigger-model-spike.json && echo MODEL-SPIKE-OK
MODEL-SPIKE-OK
```

### Checkpoint A record — JSON event-schema facts (verbatim)

- **Line-delimited?** Yes, one JSON object per line — **but** the first captured line can be non-JSON stderr noise (`[rtk] rtk binary not found in PATH — plugin disabled`, emitted by a local plugin on every `opencode` invocation). Raw `jq` on the captured file fails with `jq: parse error: Invalid numeric literal at line 1, column 5`. Any jq filter must skip invalid lines first (e.g., `jq -R 'fromjson? // empty'`). Event types observed in the streams: `step_start`, `step_finish`, `text`, `tool_use`.
- **Tool-event type discriminator: `"tool_use"`** — NOT `"tool"`. The plan's expected `select(.type=="tool")` (and Phase 2's `select(.type? == "tool")`) matches nothing in the real stream. This is a falsification of the plan's default; the Phase 2 jq selector for the type check is one of the named adjustable selectors.
- **Tool name field path: `.part.tool`** (value `"skill"`). `.part.type` is also `"tool"` on these events.
- **Skill input name field path: `.part.state.input.name`** (value `"writing-prds"`).
- **Text content field path: `.part.text`** on `.type=="text"` events.
- Additional reliable load signals observed: `.part.state.title` == `"Loaded skill: writing-prds"` and `.part.state.metadata.name` == `"writing-prds"` on the `tool_use` event.
- The agent's one-line text report is **not stable**: the live-repo run produced `**writing-prds** loaded successfully.` while the isolated-workspace run produced `Skill loaded: writing-prds`. The documented `startswith("Skill loaded: ")` text fallback matched only the latter; the mechanical `tool_use` event matched both.

### Checkpoint B record — winning discovery layout

The plan default worked on the first attempt; **no fallback ladder step was needed**:

- Stub at `WORKSPACE/.agents/skills/writing-prds/SKILL.md` (frontmatter-only, produced by the plan's exact `awk` extractor) — discovered and loaded.
- Agent at `WORKSPACE/.opencode/agents/trigger-evaluator.md` — resolved by `--agent trigger-evaluator`.
- The workspace was a plain `mktemp -d` directory, **not** a git worktree; no `git init` was required.
- The loaded stub's output confirms frontmatter-only delivery: `<skill_content name="writing-prds">` contained an empty body and `dir: /tmp/trigger-layout-spike.1RwpppYlhh/.agents/skills/writing-prds`.

### Checkpoint C record — permission behavior without repo config

The layout-spike workspace has no `opencode.jsonc`. The run completed non-interactively (exit 0, `state.status == "completed"` on the skill `tool_use`) with no permission prompt blocking; `grep -ci 'permission'` over the stream found 0 matches. **`--auto` was NOT needed** — Phase 2 must not add it.

### Checkpoint D record — global-skill leakage

`grep -o '"name":"[a-z0-9-]*"'` over the layout-spike stream yielded only `"name":"writing-prds"`. **No globally installed skill was loaded** in any of the three spike runs. One nuance: in the model-spike run the agent's text response referenced the globally available built-in skill `customize-opencode` by name while explaining a no-load decision — global skill descriptions are visible to the evaluator, but none were loaded.

### Checkpoint E record — model flag

`--model "$(opencode models | head -1)"` resolved to `opencode/big-pickle` (the `[rtk]` plugin warning goes to stderr, so the stdout capture is clean). The run completed (exit 0); the known-negative README query produced no skill load, and the run stream contains only `step_start`/`step_finish`/`text` events. The spike workspace was removed with `rm -rf` afterwards.

Manual Verification items are listed here unchecked, for the human:

- [ ] Phase report records the three JSON field paths from Checkpoint A verbatim
- [ ] Phase report records the winning discovery layout from Checkpoint B (or the stop-and-report escalation)
- [ ] Phase report records whether `--auto` was needed (Checkpoint C) and which global skills, if any, leaked (Checkpoint D)

## Deviations

| Plan said | What was done instead | Why it was forced |
|-----------|----------------------|-------------------|
| None | — | All checkpoint commands ran exactly as written; the only addition was a scratch file (`/tmp/opencode/trigger-layout-spike.ws`) recording the mktemp path so it persisted across shell invocations. |

## Issues & Concerns

- **Phase 2 jq filter will fail as written against the real stream.** The plan's Phase 2 script uses `select(.type? == "tool")` and runs `jq -rs` directly on a capture that includes stderr (`> "$out" 2>&1`). Checkpoint A shows (a) the type is `tool_use`, and (b) the captured file can contain a non-JSON first line that makes `jq -rs` exit with a parse error before any selector runs. The plan anticipates selector adjustment ("a falsification here means editing those selectors only"), and this report records the verified selectors above. The Phase 2 executor will need to (1) match `tool_use` (or drop the type check and key on `.part.tool == "skill"`) and (2) make the jq pipeline tolerant of non-JSON lines. Both changes stay within the plan's named adjustable surface (jq selectors/constants), but the controller should be aware the parse-tolerance change is slightly beyond a literal "selector" edit.
- **Text fallback is unreliable.** `Skill loaded: <name>` matched only one of two load runs; the mechanical `tool_use` signal (or `.part.state.title` / `.part.state.metadata.name`) should be treated as primary, exactly as the plan's Decisions table intends.
- **Plan header `git_commit` (72416a8…) ≠ HEAD (69a5c7de…).** The repo has moved since the plan was written. No drift affecting Phase 1 was observed (the agent file and `writing-prds` frontmatter behaved as the plan describes), noted for the controller.

## Follow-ups

- Human to confirm the three Manual Verification items above before Phase 2 begins.
- Phase 2 executor: apply the Checkpoint A selectors verbatim (`.type=="tool_use"` / `.part.tool` / `.part.state.input.name` / `.part.text`) and make the jq pipeline skip non-JSON lines; do NOT add `--auto` (Checkpoint C); keep the `.agents/skills` + `.opencode/agents` layout (Checkpoint B).
- Controller: decide whether the jq parse-tolerance fix requires a plan note via iterating-plans or is covered by the plan's "adjust selectors" clause.
