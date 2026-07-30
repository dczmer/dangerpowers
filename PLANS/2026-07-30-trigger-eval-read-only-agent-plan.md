---
artifact: implementation-plan
date: 2026-07-30
git_commit: 8057632415de54903cf71489d700eb40ba11c6a9
branch: dev/sloptime
request: Implement the recommended changes from the trigger-testing/trigger-evaluator analysis: wire the trigger-evaluator agent into the trigger-testing harness so triggered skills cannot execute their workloads during eval reps, and strip the agent file down to an in-run behavior contract so it no longer conflicts with or duplicates the skill's detection rules.
source_prd: none
source_bundle: none (quick pass)
source_research: none (quick pass)
status: approved
---

# Trigger-Eval Read-Only Agent Implementation Plan

> **For the implementing agent:** Read this plan before starting. After completing the changes, run all automated verification; when it passes, pause for human confirmation of the manual criteria.

## Context

The trigger-testing skill's harness runs eval reps with the default full-tool agent (`skills/trigger-testing/SKILL.md:110`), so when a should-trigger query fires a skill, that skill actually executes its workflow — writing files, dispatching agents — on every rep of a 60+ invocation campaign. The pressure-testing skill already solved the equivalent problem by running with-skill reps under the read-only `eval-reader` agent (`skills/pressure-testing/SKILL.md:104-107`). A `trigger-evaluator` agent exists (`agents/trigger-evaluator.md`) but is wired into nothing, and its instructions conflict with the trigger-testing skill: it claims ownership of JSON detection, returns prose verdicts nothing consumes, and instructs the in-run agent to read the candidate's SKILL.md directly — which produces no skill-load event and would void reps as false negatives.

## Current State

- Harness invoke command has no `--agent` flag: `skills/trigger-testing/SKILL.md:110`.
- Eval loop skeleton has no `--agent` flag: `skills/trigger-testing/SKILL.md:129-131`.
- Early-abort policy (SKILL.md:141) tells the runner to "stop reading the response once the rep is decided" — not implementable: the harness is a blocking `opencode run ... > out.json 2>&1` invocation that runs to completion.
- `agents/trigger-evaluator.md:10-13,30` — role bullets "Read the skill description" / "Read the skill file if referenced": a direct `Read` of the candidate file fires no `tool_use skill` event, so the rep scores NOT_TRIGGERED incorrectly.
- `agents/trigger-evaluator.md:32-43` — JSON detection pattern and TRIGGERED/NOT_TRIGGERED/SIBLING_ROUTED report format duplicate the skill's runner-side detection (SKILL.md:118-120), which is the authoritative, candidate-specific channel.
- `agents/trigger-evaluator.md:26` — "Report skill load events to the user": stale assumption; headless reps have no user, output goes to the NDJSON stream.
- Nothing in the repo references `trigger-evaluator` outside RESEARCH/ notes — no existing consumer to break (verified by repo-wide grep).
- The old `skills/writing-skills/references/` duplicates of these protocols no longer exist; `skills/trigger-testing/SKILL.md` is the only copy (verified: references dir absent).
- Skill validation command, repo-verified at `skills/writing-skills/SKILL.md:70`: `agentskills validate skills/<name>` must print `Valid skill`.
- `--agent` flag mechanics verified for `opencode run` at `skills/pressure-testing/SKILL.md:89,104`.

## Desired End State

1. `skills/trigger-testing/SKILL.md` harness invokes reps with `--agent trigger-evaluator` (invoke command + eval loop skeleton), the early-abort section describes the real mechanism (read-only workload isolation, void-and-redispatch on hangs), the smoke-test step verifies the agent can fire the skill tool, and Common Mistakes gains a full-tool-agent row.
2. `agents/trigger-evaluator.md` is a stripped in-run behavior contract: read-only, never read a candidate SKILL.md directly, load-or-decline via the skill tool, execute nothing from a loaded skill body, end the turn. No detection pattern, no report format.
3. A smoke rep confirms the `tool_use skill` event fires under `--agent trigger-evaluator` and `git status` stays clean (no workload executed).

## What We're NOT Doing

- Not changing detection mechanics — runner-side NDJSON grep on `input.name` stays the sole authority.
- Not touching `skills/pressure-testing/SKILL.md`, `agents/eval-reader.md`, or any other skill or agent.
- Not running a full trigger campaign — one smoke rep only.
- Not modifying README.md or AGENTS.md.
- Not changing opencode configuration or the skill tool itself.

## Decisions

| Conflict / Question | Pick | Rationale |
|---------------------|------|-----------|
| Where do eval-running rules live: agent vs skill | Skill keeps harness/orchestration; agent keeps only the in-run behavior contract | The agent runs *inside* the rep with no Bash/task tools — it cannot loop reps, compute pass rates, or manage iterations |
| Detection: agent prose report vs runner JSON grep | Runner-side grep on `input.name` stays sole authority | Candidate-specific guarantee (`skills/trigger-testing/SKILL.md:118-120`); agent prose can misreport or echo templates — pressure-testing warns automated text-matching overstates both failure and success (`skills/pressure-testing/SKILL.md:116`) |
| Agent's TRIGGERED/NOT_TRIGGERED report format | Delete | Nothing consumes it; duplicated logic drifts |
| Early-abort by "stopping reading the stream" | Replace with structural workload isolation + void-on-hang | A blocking `opencode run > file` cannot be aborted by reading less; prevention must come from the agent's read-only tool set |
| In-run agent reading the candidate's SKILL.md for context | Explicitly forbidden in the agent's rules | A direct `Read` fires no `tool_use skill` event → false-negative NOT_TRIGGERED; the eval measures description-triggered loading only |

## Implementation Approach

Two surgical file edits, then a smoke rep. Edit the agent contract first so the skill's new harness instructions reference a file that already says the right thing; then update the skill; then verify.

## Changes Required

#### 1. Rewrite the trigger-evaluator agent contract
**File**: `agents/trigger-evaluator.md`
**Changes**: full-file replacement with the stripped behavior contract below (frontmatter description updated; detection pattern, report format, "read the skill file" workflow, and "report to the user" rule removed; skill-load-then-stop rule added).

```markdown
---
name: trigger-evaluator
description: Read-only agent for trigger-evaluation reps. Receives one eval query per run and decides whether it triggers a skill load, but cannot execute any loaded skill's workflow — no write, edit, or bash access.
---

# Trigger Evaluation Agent

You are the in-run agent for skill trigger-evaluation reps. A campaign runner dispatches you with a single evaluation query and measures your behavior from the harness's JSON event stream. Detection is the runner's job, not yours.

**Tools available:**
- Read: Yes (for general file context the query genuinely requires)
- Glob: Yes
- Grep: Yes
- Bash: No
- Write: No
- Edit: No

**Rules:**
- NEVER modify any files or run state-changing commands.
- NEVER read a skill's SKILL.md directly. Trigger evals measure whether the skill *description* causes a load through the skill tool. A direct Read of a skill file produces no load event and voids the rep.
- If the query matches a skill, invoke the skill tool to load it. After loading, DO NOT execute any workflow, procedure, or instruction from the loaded skill body — the rep measures the load decision only.
- If no skill matches, answer the query briefly within your read-only means. Do not attempt any implementation.
- After the load decision (load or no-load), end the turn.

**If a loaded skill instructs you to write, edit, run commands, or dispatch agents:**
- Do not comply. Report that you cannot do so and stop.
```

#### 2. Harness invoke command gains `--agent trigger-evaluator`
**File**: `skills/trigger-testing/SKILL.md`
**Changes**: replace line 110:

Old:
```
**Invoke:** `opencode run --dir <repo-root> --format json "<query>" > out.json 2>&1`.
```

New:
```
**Invoke:** `opencode run --dir <repo-root> --agent trigger-evaluator --format json "<query>" > out.json 2>&1`.

Reps MUST run under the `trigger-evaluator` agent (`agents/trigger-evaluator.md`). Its read-only tool set makes workload execution impossible: a triggered skill loads (which is the measurement) but cannot write files, run commands, or dispatch agents. The skill-load `tool_use` event is emitted by the harness regardless of which agent is in the run, so detection is unaffected.
```

#### 3. Eval loop skeleton gains the flag
**File**: `skills/trigger-testing/SKILL.md`
**Changes**: in the skeleton (lines 129-131), replace:

Old:
```
      out=$(mktemp); opencode run --dir <repo-root> \
        --format json "$query" > "$out" 2>&1
```

New:
```
      out=$(mktemp); opencode run --dir <repo-root> \
        --agent trigger-evaluator --format json "$query" > "$out" 2>&1
```

#### 4. Rewrite the early-abort policy as workload isolation
**File**: `skills/trigger-testing/SKILL.md`
**Changes**: replace the entire early-abort paragraph (line 141):

Old:
```
**Early-abort policy (per rep, both directions):** stop reading the response once the rep is decided — do not wait for completion. **Should-trigger:** once `tool_use skill <candidate>` appears in the stream, the rep is decided — record the verdict and stop. **Should-not:** once the agent emits substantive non-skill work, the rep is decided — record the verdict and stop. This is a per-rep policy, not a tip; it cuts output tokens materially on decided reps.
```

New:
```
**Workload isolation (per rep):** reps run under `--agent trigger-evaluator`, so a triggered skill's workload cannot execute — that is the abort mechanism, and it is structural, not procedural. Do not try to "stop" a rep mid-run: the harness invocation is blocking and runs to completion, and verdicts come from the finished rep's JSON stream. If a rep hangs (e.g. loaded skill content loops the agent into endless reads), kill it, void the rep, and re-dispatch a fresh replacement — mirroring the pressure-testing void-run convention. Never count a killed rep.
```

#### 5. Smoke-test step verifies the agent can fire the skill tool
**File**: `skills/trigger-testing/SKILL.md`
**Changes**: replace Workflow step 3 (line 18):

Old:
```
3. Smoke-test the harness: run ONE query through the opencode Harness and read its output before dispatching full runs.
```

New:
```
3. Smoke-test the harness: run ONE should-trigger query through the opencode Harness and read its output before dispatching full runs. The smoke rep also verifies the `trigger-evaluator` agent can invoke the skill tool and receives skill descriptions in context — if the `tool_use skill` event cannot fire under the agent, stop and fix the agent configuration before any campaign.
```

#### 6. Common Mistakes row
**File**: `skills/trigger-testing/SKILL.md`
**Changes**: append one row to the Common Mistakes table (after line 177):

```
| Running reps with the default full-tool agent | Always pass `--agent trigger-evaluator` — under the default agent a triggered skill executes its real workload on every rep |
```

### Success Criteria

#### Automated Verification:
- [ ] Skill validates: `agentskills validate skills/trigger-testing` prints `Valid skill`
- [ ] Flag present in both harness locations: `grep -c -- '--agent trigger-evaluator' skills/trigger-testing/SKILL.md` prints at least `2`
- [ ] Old invoke command gone: `grep -c 'opencode run --dir <repo-root> --format json' skills/trigger-testing/SKILL.md` prints `0`
- [ ] Agent contract stripped: `grep -c 'SIBLING_ROUTED' agents/trigger-evaluator.md` prints `0`
- [ ] Direct-read prohibition present: `grep -c 'NEVER read a skill' agents/trigger-evaluator.md` prints at least `1`
- [ ] Early-abort language gone: `grep -c 'Early-abort policy' skills/trigger-testing/SKILL.md` prints `0`

#### Manual Verification:
- [ ] Smoke rep fires the load event under the agent: run `opencode run --dir /home/dave/source/dangerpowers --agent trigger-evaluator --format json "write a PRD for adding a dark mode toggle to the settings page" > /tmp/opencode/trigger-smoke.json 2>&1`, then `grep '"tool":"skill"' /tmp/opencode/trigger-smoke.json | grep '"name":"writing-prds"'` returns a match
- [ ] No workload executed: `git status --porcelain` after the smoke rep shows no new or modified files attributable to the rep
- [ ] The smoke rep's output shows the agent did NOT begin drafting the PRD after the load event

**Implementation Note**: After completing all changes and automated verification passes, pause for human confirmation of the manual criteria (the smoke rep) before considering the plan done.

---

## Testing Strategy

### Unit Tests:
- None — markdown-only change in a repo with no test suite for skill content.

### Integration Tests:
- The smoke rep in Manual Verification is the integration test: it exercises the full harness path (`opencode run --agent trigger-evaluator --format json`) end to end against a real should-trigger query.

### Manual Testing Steps:
1. Run the three manual verification bullets above in order.
2. Read the smoke rep's JSON output manually (per both testing skills' standing rule: never trust automated pattern-matching alone) to confirm the agent loaded the skill and then stopped.

## Final Verification

`agentskills validate skills/trigger-testing`
`grep -c -- '--agent trigger-evaluator' skills/trigger-testing/SKILL.md`
`opencode run --dir /home/dave/source/dangerpowers --agent trigger-evaluator --format json "write a PRD for adding a dark mode toggle to the settings page" > /tmp/opencode/trigger-smoke.json 2>&1 && grep '"tool":"skill"' /tmp/opencode/trigger-smoke.json | grep '"name":"writing-prds"'`
`git status --porcelain`

## References

- PRD: none
- Context bundle: none (quick pass) — evidence gathered in-session
- Research findings: none (quick pass) — evidence gathered in-session
- Key implementation files: `skills/trigger-testing/SKILL.md:110,118-120,129-131,141,18,177`; `agents/trigger-evaluator.md:10-13,26,30,32-43`; `skills/pressure-testing/SKILL.md:104-107,116`; `skills/writing-skills/SKILL.md:70`
