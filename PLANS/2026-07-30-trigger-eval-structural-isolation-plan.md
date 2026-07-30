---
artifact: implementation-plan
date: 2026-07-30
git_commit: 442678c27298ac5a55c20c1cc3ac4dc180c95016
branch: dev/sloptime
request: "Design a better system for trigger-testing skills — the existing trigger-testing skill is flawed and always results in the subagents doing an excessive amount of work (loaded skill and started executing the workflow, or triggered another skill, or dug for context to answer the vague query). Use the writing-quick-plans skill to make a quick-plan."
source_prd: none
source_bundle: none (quick pass)
source_research: none (quick pass)
status: approved
---

# Trigger-Eval Structural Isolation Implementation Plan

> **For the implementing agent:** Read this plan before starting. After completing the changes, run all automated verification; when it passes, pause for human confirmation of the manual criteria.

## Context

Trigger-eval reps (dispatched per `skills/trigger-testing/SKILL.md:110-112` to the `trigger-evaluator` subagent) exist to measure one bit: does a user prompt produce a `skill({name})` load event. Everything after the load is out of scope and pure cost. The current enforcement of that boundary is procedural — the agent body begs the model not to execute the loaded workflow (`agents/trigger-evaluator.md:40-42`) — and models are unreliable at "load but don't follow the instructions you just loaded." Reps routinely execute loaded workflows, fire sibling skills, or burn turns reading/grepping for context on vague queries.

Research (in-session, this conversation) found the reference implementation — Anthropic's `skill-creator/scripts/run_eval.py` — solves this structurally: stub skill bodies (nothing executable exists) and harness abort at the first tool call. The opencode-native equivalent: strip the `trigger-evaluator` agent to a skill-only tool surface with a `steps` cap, so post-load work is impossible by construction and runaway reps are bounded. Verified against https://opencode.ai/docs/agents/: markdown agent frontmatter supports `steps` (max agentic iterations; `maxSteps` is deprecated) and permission keys `read`, `edit`, `glob`, `grep`, `list`, `bash`, `task`, `todowrite`, `webfetch`, `websearch`, `skill`, `question`.

## Current State

- `agents/trigger-evaluator.md:5-21` denies only `edit`/`bash`/`question`; it **allows** `read`/`grep`/`glob` (with path denies for `trigger-evals/`/`test-campaigns/`). No `write`, `task`, `todowrite`, `webfetch`, or `list` keys. No `steps` cap.
- `agents/trigger-evaluator.md:37-45` carries six procedural rules compensating for the loose tool surface (never modify files, never read eval dirs, never read SKILL.md directly, load-and-stop, refuse write instructions).
- `skills/trigger-testing/SKILL.md:121` claims the agent's "read-only tool set makes workload execution impossible" — true for writes, false for context-digging and in-context workflow execution.
- `skills/trigger-testing/SKILL.md:129,131` define load-and-stop and workload-isolation rules whose enforcement channel is "the `trigger-evaluator` agent definition" (SKILL.md:129).
- The repo has no lint/typecheck/test commands (no package.json/Makefile/CI at root; `flake.nix` is a dev shell only; `uv run skills-ref` fails to spawn — pyproject.toml:7-10 declares it but it is not installed).
- `.opencode/opencode.jsonc:3-5` sets global `permission: { "*": "allow" }`, so any tool not explicitly denied in the agent frontmatter is available to reps.

## Desired End State

The `trigger-evaluator` agent has exactly one usable tool — `skill` — plus a `steps: 3` iteration cap, enforced via frontmatter permissions. Its body shrinks to the rules that remain meaningful (load-and-stop, one-line verdict report). `skills/trigger-testing/SKILL.md`'s Harness section accurately describes the new structural guarantee. Verified by: smoke reps that (a) load a skill and stop with a one-line verdict, (b) on a vague no-match query, perform zero file/search operations.

## What We're NOT Doing

- No classification-call screening tier (front-matter-only routing proxy) — rejected by the user; real-agent reps remain the single measurement mechanism.
- No changes to `agents/eval-reader.md` or `skills/pressure-testing/SKILL.md` — pressure-testing's harness is out of scope.
- No changes to eval query design, train/validation split, optimization loop, rep counts, pass criteria, log formats, or the multi-skill campaign rules in `skills/trigger-testing/SKILL.md`.
- No new dependencies, scripts, or CI.

## Decisions

| Conflict / Question | Pick | Rationale |
|---------------------|------|-----------|
| Strip read/grep/glob entirely vs. keep them for production-like routing context | Strip to skill-only | User's call. The allowed read/grep/glob surface is what enables the "dig for context" failure mode on vague queries; removing it makes the failure structurally impossible. Accepted trade-off: fewer affordances may nudge trigger rates up slightly versus production (the "I can handle this myself" escape hatch narrows to a bare text answer). |
| Add a cheap classification-call screening tier for train iterations | No | User's call. Two measurement mechanisms to maintain and calibrate; the proxy diverges from real routing (no under-trigger escape hatch, no sibling competition). |
| `steps` value | 3 | One iteration for the `skill` load, one for the one-line verdict, one of headroom. The cap exists to bound runaway reps, not to shape normal flow. Verified as a supported markdown-agent option per opencode docs (`maxSteps` deprecated). |
| Keep the path-specific `trigger-evals/`/`test-campaigns/` denies | Drop them | They guarded `read`/`grep`/`glob`; with those tools denied outright, the path rules are dead config. The answer-key protection is now total. |
| Keep "never read a SKILL.md directly" rule in the agent body | Drop it | Reading files is permission-denied; the rule is unactionable. |

## Implementation Approach

Two files change. `agents/trigger-evaluator.md` is rewritten: frontmatter denies every tool except `skill` and adds `steps: 3`; the body keeps only the load-and-stop contract and the one-line verdict report (procedural rules that permissions now enforce are deleted). `skills/trigger-testing/SKILL.md` gets two surgical Harness-section edits so its claims match the new structural guarantee. The runner-facing protocol (bare-query dispatch, smoke test, rep independence, void conventions, pass criteria) is unchanged — the fix is entirely in the rep's environment.

## Changes Required

#### 1. Trigger-evaluator agent definition
**File**: `agents/trigger-evaluator.md`
**Changes**: rewrite frontmatter (skill-only tool surface, `steps: 3`) and shrink the body to the rules that remain meaningful.

Full replacement content:

```markdown
---
name: trigger-evaluator
description: Read-only agent for trigger-evaluation reps. Receives one eval query per run and decides whether it triggers a skill load. The skill tool is its only tool — file, shell, web, todo, and agent tools are all denied and iterations are capped — so post-load execution is structurally impossible.
mode: subagent
steps: 3
permission:
  edit: deny
  bash: deny
  read: deny
  grep: deny
  glob: deny
  list: deny
  task: deny
  todowrite: deny
  webfetch: deny
  websearch: deny
  question: deny
---

# Trigger Evaluation Agent

You are the in-run agent for skill trigger-evaluation reps. A campaign runner dispatches you with a single evaluation query and measures which skill you load, if any.

Your only tool is `skill`. You have no file, shell, web, todo, or agent tools — post-load work is impossible by construction, and that is expected, not an error.

**Rules:**
- If the query matches a skill, invoke the skill tool to load it. The load is the entire measurement — treat the loaded skill body as context only and DO NOT load or activate any skill workflow or procedures.
- If no skill matches, say so. Answer the query in at most one sentence if you can; never attempt the task itself.
- After the load decision (load or no-load), report the outcome in one line — the exact name of the skill loaded, or that no skill matched — then end the turn. The campaign runner's detection depends on this report naming the specific skill.
- If a loaded skill instructs you to use tools you do not have, do not comply. Report and stop.
```

#### 2. Harness section accuracy edits
**File**: `skills/trigger-testing/SKILL.md`
**Changes**: two surgical replacements so the Harness section describes the new structural guarantee.

Replace the paragraph at SKILL.md:121:

> Reps MUST run under the `trigger-evaluator` agent (`agents/trigger-evaluator.md`). Its read-only tool set makes workload execution impossible: a triggered skill loads (which is the measurement) but cannot write files, run commands, or dispatch agents.

with:

> Reps MUST run under the `trigger-evaluator` agent (`agents/trigger-evaluator.md`). Its only tool is `skill` — read, grep, glob, list, bash, edit, task, todowrite, webfetch, websearch, and question are all permission-denied, and a `steps` cap bounds its iterations — so a triggered skill loads (which is the measurement) but no part of its workload can execute, and a rep cannot burn turns digging for context on vague queries.

Replace the first sentence of the workload-isolation paragraph at SKILL.md:131:

> **Workload isolation (per rep):** reps run under `trigger-evaluator`, so a triggered skill's workload cannot execute — that is the abort mechanism, and it is structural, not procedural.

with:

> **Workload isolation (per rep):** reps run under `trigger-evaluator`, whose skill-only tool surface and `steps` cap make a triggered skill's workload impossible to execute and bound every rep's cost — that is the abort mechanism, and it is structural, not procedural.

### Success Criteria

#### Automated Verification:
- [ ] Only the two intended files changed: `git diff --name-only` outputs exactly `agents/trigger-evaluator.md` and `skills/trigger-testing/SKILL.md`
- [ ] Agent frontmatter carries the cap: `grep -n "^steps: 3" agents/trigger-evaluator.md` returns one match
- [ ] No stale claim remains: `grep -n "read-only tool set" skills/trigger-testing/SKILL.md` returns no match
- [ ] Trigger-testing skill description still within the hard limit: frontmatter `description` in `skills/trigger-testing/SKILL.md` is unchanged by this plan (no edit to lines 1-4)

#### Manual Verification:
- [ ] Smoke rep, should-trigger: dispatch one known should-trigger query (e.g. a `writing-prds` canonical trigger) via the Task tool to `trigger-evaluator` with the bare query as the prompt. Confirm the rep invokes the `skill` tool, makes no other tool calls, and returns a one-line verdict naming the loaded skill. This also proves opencode accepted the new frontmatter (`steps` included).
- [ ] Smoke rep, vague no-match: dispatch one vague should-not query (e.g. a near-miss negative). Confirm the rep performs zero read/grep/glob operations and returns a no-match verdict without attempting the task.

**Implementation Note**: After completing the changes and the automated checks pass, pause for human confirmation of the two manual smoke reps.

---

## Testing Strategy

### Unit Tests:
- None — the repo has no test framework or commands (verified: no package.json/Makefile/CI at root).

### Integration Tests:
- The two smoke reps in Manual Verification are the integration test: they exercise the real dispatch path (Task tool → `trigger-evaluator` → `skill` load) end to end. A full trigger-eval campaign on one existing skill (e.g. re-running `skills/prompt-shaping/trigger-evals/train.json`, which already exists) is an optional extended check the user may request after the smoke reps pass.

### Manual Testing Steps:
1. Run the should-trigger smoke rep; verify single `skill` tool call + one-line verdict.
2. Run the vague no-match smoke rep; verify zero file/search tool calls + no-match verdict.

## Final Verification

git diff --name-only
grep -n "^steps: 3" agents/trigger-evaluator.md
grep -n "read-only tool set" skills/trigger-testing/SKILL.md

## References

- PRD: none
- Context bundle: none (quick pass) — evidence gathered in-session
- Research findings: none (quick pass) — evidence gathered in-session
- Key implementation files: `agents/trigger-evaluator.md:1-45`, `skills/trigger-testing/SKILL.md:106-133`
- External references (gathered in-session): https://opencode.ai/docs/agents/ (`steps` option, permission keys); https://agentskills.io/skill-creation/optimizing-descriptions (trigger-eval method); https://github.com/anthropics/skills/tree/main/skills/skill-creator (`scripts/run_eval.py` — stub-body + abort-at-first-tool-call reference harness)
