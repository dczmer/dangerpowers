---
artifact: implementation-plan
date: 2026-08-05
git_commit: ee02e96e9db3e03f8abb96754577eccfc3173395
branch: dev/sloptime
request: "create a plan based on this prd @/home/dave/source/dangerpowers/PRDS/2026-08-05-merge-trigger-testing-into-writing-skills.md"
source_prd: PRDS/2026-08-05-merge-trigger-testing-into-writing-skills.md
source_bundle: RESEARCH/2026-08-05-merge-trigger-testing-into-writing-skills-context-bundle.md
source_research: RESEARCH/2026-08-05-merge-trigger-testing-into-writing-skills-research-findings.md
status: approved
---

# Merge trigger-testing into writing-skills Implementation Plan

> **For the implementing agent:** Read this plan and the provenance artifacts in References before starting. After each phase, run all automated verification; when it passes, pause for human confirmation of the manual criteria before starting the next phase.

## Context

The repo's skill-authoring guidance is split across `writing-skills` (how to author a skill) and the standalone `trigger-testing` skill (how to run a description eval campaign). The pressure-testing merge already folded the third skill back into `writing-skills` as an on-demand reference file; `trigger-testing` retains the same coupling problems: description-authoring rules are duplicated across both files (`skills/writing-skills/SKILL.md:55-60,74-75` vs `skills/trigger-testing/SKILL.md:38-53`), the main file directs readers to load a second skill for trigger evals (`skills/writing-skills/SKILL.md:159,166`), and campaign-only content sits in an always-loaded main file. This plan merges `trigger-testing` into `writing-skills` exactly the way pressure-testing was merged: campaign instructions in an on-demand reference file, authoring rules only in the main file, the harness tooling relocated under the merged skill, the old skill directory deleted, and the merge verified by a pressure-test campaign plus a clean-context review.

## Current State

- `skills/writing-skills/SKILL.md` (208 lines) — the surviving skill. Its description (`:3`) routes pressure-test requests and carries a boundary clause "not trigger-testing's description evals" that must be rewritten once both campaigns live in one skill. The Invocation Branch (`:19-24`) has only the pressure-test bullet. The Trigger Optimization section (`:159`) and End-of-Flow Prompt 2 (`:166`) point at the standalone `trigger-testing` skill. The 2026-08-05 campaign log records that pressure-test queries previously lost routing to the `trigger-testing` skill's description (`skills/writing-skills/test-campaigns/2026-08-05-writing-skills.md:84-94`) — a rival-skill conflict that disappears with the merge.
- `skills/trigger-testing/SKILL.md` (253 lines) — the skill being merged in and deleted. Its entire body is source material for the new reference file: workflow (`:12-29`), scope (`:31-36`), restated authoring rules (`:38-53`), eval query design (`:55-87`), train/validation split (`:89-93`), optimization loop (`:95-107`), failure-class table (`:109-118`), harness protocol (`:120-166`), contamination rules (`:168-172`), done criteria (`:174-183`), multi-skill campaigns (`:185-189`), common mistakes (`:191-210`), results log (`:212-245`), `trigger-evals/` convention (`:247-249`), boundary (`:251-253`).
- `skills/trigger-testing/scripts/trigger-test.sh` (343 lines) and `test-trigger-test.sh` (222 lines) — the harness and its shunit2 suite. The script computes its default source root as `../../..` from its own path (`trigger-test.sh:67,270,305`) and hard-requires `$source/agents/trigger-evaluator.md` (`:70`, copied at `:91`). The test suite resolves the harness as a sibling of itself (`test-trigger-test.sh:3`) and always passes `--source` explicitly (`:26`).
- `agents/trigger-evaluator.md` (31 lines) — read-only primary agent used by the harness; the pressure-testing merge left the analogous `agents/eval-reader.md` in the shared `agents/` directory.
- `skills/trigger-testing/` contains 6 files: `SKILL.md`, 2 scripts, 1 test-campaign log, 2 trigger-eval files. All are deleted or relocated; no historical logs or eval sets are migrated.
- `skills/writing-skills/trigger-evals/train.json` (8 true / 4 false) and `validation.json` (4 true / 3 false) — augmented with pressure-test positives by the previous merge; contain no trigger-test positive queries.
- Live references to the old skill outside `skills/trigger-testing/`: only `skills/writing-skills/SKILL.md:3,159,166`. Historical logs, README.md prose, and `.worktrees/` snapshots describe past states and are out of scope.
- Repo-verified validation commands (bundle §7): `.venv/bin/agentskills validate skills/writing-skills`, `bash <path>/test-trigger-test.sh` (shunit2 on PATH via the nix env), `.venv/bin/python -m json.tool`, plus file-existence and grep checks. No package.json, Makefile, or CI config exists.

## Desired End State

- Exactly one skill where two existed: `skills/writing-skills/` with a `SKILL.md` covering authoring plus invocation branches for both campaign types, `skills/writing-skills/references/pressure-testing.md` (unchanged except consistency), a new `skills/writing-skills/references/trigger-testing.md` holding all trigger-campaign content, and `skills/writing-skills/scripts/` holding the harness. `skills/trigger-testing/` is gone entirely.
- The merged skill's description routes authoring, pressure-test, and trigger-test requests; invoked with "trigger test the <name> skill", the workflow reads the main file, loads `references/trigger-testing.md`, and begins the campaign — reporting (not inventing) a nonexistent target, and asking rather than guessing on ambiguous "test the <name> skill" requests.
- The authoring flow's End-of-Flow Prompt 2 loads the in-skill reference file on "yes"; declining either prompt ends the flow cleanly with untested status reported.
- The main file contains no trigger-campaign-execution instructions (eval query design, split, optimization loop, harness protocol, contamination rules, multi-skill campaigns, done criteria, results logging); the reference file contains no restated description-authoring rules — it points back to the Frontmatter section of `SKILL.md`.
- The harness runs end-to-end from its new home: `skills/writing-skills/scripts/test-trigger-test.sh` passes and a real `init`/`cleanup` smoke run succeeds with the default source root and `agents/trigger-evaluator.md`.
- A campaign log exists at `skills/writing-skills/test-campaigns/2026-08-05-01-writing-skills.md` recording the pressure test of the merged skill's new discipline rules, including trigger verification on phrases like "trigger test the test-skill skill".
- A clean-context reviewer confirms no duplication, no orphaned or conflicting rules, no rules in the wrong file, and coherent cohesion between the main-file workflow and both reference-file workflows.
- Verified by: `agentskills validate skills/writing-skills` printing `Valid skill`, the harness test suite, the greps and file-existence checks in each phase, and the manual confirmations below.

## What We're NOT Doing

- Running a trigger-eval campaign against the merged skill's new description — explicitly deferred to a later session by the PRD.
- Changing the trigger-testing methodology (eval set sizes, split ratios, rep counts, pass criteria) beyond the consolidation rewrite.
- Migrating or preserving `trigger-testing`'s historical campaign logs or eval sets; git history retains them.
- Rewriting references to `trigger-testing` in other skills' files, historical campaign logs, README.md, PLANS/, PRDS/, RESEARCH/, or `.worktrees/` snapshots.
- Editing README.md — AGENTS.md reserves it for humans; the maintainer updates its trigger-testing prose separately if desired.
- Changing the pressure-testing reference file beyond what deduplication and consistency require.
- Moving `agents/trigger-evaluator.md` or `agents/eval-reader.md` (see Decisions).

## Decisions

| Conflict / Question | Pick | Rationale |
|---------------------|------|-----------|
| Harness scripts destination after `skills/trigger-testing/` is deleted (FR-008; bundle §9 `[needs-human]`) | `skills/writing-skills/scripts/` via `git mv skills/trigger-testing/scripts skills/writing-skills/scripts` | The script's default source root is `../../..` from its own path (`trigger-test.sh:67,270,305`); `skills/writing-skills/scripts/` is the same depth, so the default stays the repo root with zero script edits. The test suite resolves the harness as a sibling (`test-trigger-test.sh:3`), so both scripts move together. Confirmed by the maintainer. |
| `agents/trigger-evaluator.md` home (FR-008 "relocated under the merged skill's ownership"; bundle §9 `[needs-human]`) | Stays at `agents/trigger-evaluator.md`; no move, no content change | Precedent: `agents/eval-reader.md` stayed in shared `agents/` through the pressure-testing merge while being "owned" by the merged skill's workflow. AGENTS.md's project layout declares `agents/` the home of agent definitions. `init` hard-requires `$source/agents/trigger-evaluator.md` (`trigger-test.sh:70,91`); leaving the agent in place keeps the harness byte-identical. Confirmed by the maintainer. |
| Partition of the campaign-side description rules at `skills/trigger-testing/SKILL.md:44,49-53` (bundle §9 `[needs-human]`) | Authoring rules move to the main file's Frontmatter section: err-pushy (`:44`), front-load boundaries (`:50`), match speech acts (`:51`), quoted micro-phrases (`:52`), verb-category negative classes (`:53`). Campaign-only: generalize-failures (`:49`) stays in the reference file | FR-004's partition principle: important to both phases → main file; campaign-only → reference. The five moved rules govern how any description is written (authoring) and how revisions are shaped (campaigns); generalize-failures only applies when responding to eval failures. The reference file points back to the Frontmatter section instead of restating. Confirmed by the maintainer. |
| README.md prose describing trigger testing (`README.md:31,50,56,64`) | Untouched by this plan | AGENTS.md: "Only humans edit that file, unless the user asks to make a specific edit." The PRD does not mention README.md; the maintainer confirmed it stays a human-side follow-up. |
| Description boundary clause "not trigger-testing's description evals" (`skills/writing-skills/SKILL.md:3`) | Rewritten: both campaign request types now route to THIS skill; the rival-skill boundary is deleted and both micro-phrases are quoted as positive triggers | The 2026-08-05 campaign log shows the boundary existed only to distinguish the rival skill (`skills/writing-skills/test-campaigns/2026-08-05-writing-skills.md:84-94`); with one skill, the distinction is meaningless and the clause would orphan |
| Ambiguous "test the <name> skill" requests (PRD §7 edge case) | New Invocation Branch bullet: ask which campaign applies (discipline rules vs description routing) via the `question` tool; never pick silently | With both campaigns in one skill the request type is genuinely ambiguous; the PRD requires the workflow to resolve it rather than pick silently |
| Anti-downgrade guard on the Invocation Branch | One shared guard paragraph covering both campaign branches (cannot-find-target + anti-downgrade), merging both rationalization sets and both domain negations; replaces the pressure-test branch's standalone tested guard | The two branch-specific guards duplicated the same scaffold; a shared guard removes the duplication without losing routing accuracy (routing stays in the per-campaign bullets). The pressure-test guard's wording changes with the merge, so its tested status is re-established by the Phase 4 campaign, which pressure-tests both downgrade variants |
| "Description Best Practices" section (`skills/trigger-testing/SKILL.md:38-53`) | Dissolved: rules duplicated in the main file are dropped; the partitioned additions move per the partition row; generalize-failures survives as the reference file's "Description Revision Rules" section pointing back to `SKILL.md`'s Frontmatter section | FR-004 forbids restated authoring rules in the reference file |
| "Standalone Boundary" section name | Renamed "Boundary", last section of the reference file | Same pick as the pressure-testing merge; "Standalone" is wrong once the skill is no longer standalone |
| `skills/writing-skills/trigger-evals/` eval sets | Augment with trigger-test positive queries (2 train, 1 validation); run no eval campaign | Mirrors the pressure-merge decision: eval sets should cover the description's new trigger surface; the PRD defers the eval campaign itself |
| Verification campaign log filename | `skills/writing-skills/test-campaigns/2026-08-05-01-writing-skills.md` | An unnumbered same-day log already exists (`2026-08-05-writing-skills.md`); the convention inserts a two-digit sequence number for same-day repeats |
| Leftover-reference grep scope | Scoped to `skills/writing-skills/SKILL.md` and `skills/writing-skills/references/` only | Historical campaign logs under `skills/writing-skills/test-campaigns/` legitimately contain "trigger-testing" and are out of scope per the PRD |

## Implementation Approach

Five phases. Phase 1 does all the writing against the surviving skill: six edits to `skills/writing-skills/SKILL.md`, the full new `references/trigger-testing.md` (a tightened rewrite of `skills/trigger-testing/SKILL.md` with duplication resolved per the Decisions table and every script path repointed), and the eval-set augmentation. Phase 2 relocates the harness with `git mv` and proves it works from its new home. Phase 3 deletes the rest of `skills/trigger-testing/` once its content no longer serves as source material. Phase 4 runs the pressure-test verification campaign against the fully integrated result; Phase 5 runs the clean-context review with remediation. The methodology sections carry over with technical content intact — the rewrite tightens prose, removes duplicated principles, and fixes cross-references; it does not alter the methodology.

## Phase 1: Merge campaign content into writing-skills

### Overview

Apply six edits to `skills/writing-skills/SKILL.md` (description, invocation branch, trigger-optimization pointer, end-of-flow prompt, frontmatter additions, checklist), create `skills/writing-skills/references/trigger-testing.md` with the full rewritten campaign content, and add trigger-test positive queries to the skill's trigger-eval sets.

**Parallel group:** merge — its file set (`skills/writing-skills/SKILL.md`, `skills/writing-skills/references/trigger-testing.md`, `skills/writing-skills/trigger-evals/train.json`, `skills/writing-skills/trigger-evals/validation.json`) is disjoint from Phase 2's (`skills/trigger-testing/scripts/*`, `skills/writing-skills/scripts/*`), and neither phase consumes the other's output. (Phase 1 *reads* `skills/trigger-testing/SKILL.md` as source material, which Phase 3 deletes — that ordering dependency is why Phase 3 is `none`, not this one.)

**Execution:** subagent

### Changes Required

#### 1. Merged skill definition
**File**: `skills/writing-skills/SKILL.md`
**Changes**: six edits, applied to the current 208-line file.

**Edit A — frontmatter description (replaces line 3):**

```yaml
description: Use when creating new skills, editing existing skills, or reviewing a skill before deploying it to this repo's skills/ directory, when pressure-testing an existing skill's discipline rules, or when trigger-testing a skill's description with eval-query campaigns. "Pressure test the <name> skill" and "trigger test the <name> skill" both mean THIS skill — pressure tests measure rule compliance after load; trigger evals measure whether the description loads on the right prompts. Triggers include "write a new skill", "create skill", "edit skill", "review skill", "update skill", "writing skills", "pressure test this skill", "pressure test a skill", "trigger test this skill", "trigger eval", "test my skill description".
```

(Plain scalar, no colon-space, ~700 chars — satisfies the file's own Description YAML safety rules. The old rival-skill boundary clause is gone; both campaign phrases are quoted positive triggers.)

**Edit B — replace the Invocation Branch section (lines 19-24) with:**

```markdown
## Invocation Branch

- **Invoked to pressure-test an existing skill** (e.g. "pressure test the <name> skill"): read this entire file for context, then load `references/pressure-testing.md` and begin the campaign against the named target.
- **Invoked to trigger-test an existing skill's description** (e.g. "trigger test the <name> skill", "run a trigger eval on <name>"): read this entire file for context, then load `references/trigger-testing.md` and begin the campaign against the named target.

For either campaign: if the named skill has no `skills/<name>/SKILL.md` in this repo, report that the target cannot be found — do not invent one. A request to skip or shrink the campaign — "just tell me if it looks fine", "just eyeball the description", "run one quick rep", "I already reviewed it", "don't run a whole campaign", "don't be dogmatic" — does NOT downgrade the invocation. A campaign IS the test: an eyeball review is not a pressure test and an opinion about a description is not a measurement, no matter who asks, and a single rep is a campaign step with the rigor removed. If the user genuinely doesn't want a campaign, say that plainly and stop — never substitute a review and call it testing.

- **Ambiguous "test the <name> skill" requests** (no campaign type named): ask which campaign applies — pressure test (discipline rules) or trigger eval (description routing) — via the `question` tool. Never pick one silently.
- **Anything else** (authoring, editing, reviewing): continue below.
```

**Edit C — in the Frontmatter section, insert after line 60** (the "Weave trigger terms..." bullet), as additional sub-bullets of the `description` rule:

```markdown
  - **Err on the side of being pushy.** List contexts where the skill applies, including situations where the user doesn't name the domain — the description is the primary trigger mechanism, and under-triggering makes the skill invisible.
  - **Front-load boundaries; never trail them.** A "Do NOT use for..." clause at the end of a description is weak — readers treat the positive trigger framing as dominant and rationalize past trailing negations. If a boundary matters, make it the opening condition ("Use ONLY when X and NOT when Y").
  - **Match speech acts, not request properties.** The router can only match what's visible in the prompt's surface — frame triggers as what the user says or does ("user says 'not sure', hedges with 'some kind of X'"), never as judgments about the request ("request is vague / underspecified").
  - **Anchor with quoted micro-phrases.** Short quoted signals give the router literal handles to match against; they outperform abstract category names ("expresses uncertainty").
  - **Name negative classes by verb category.** When excluding a class of requests, list the action verbs that define it (write, fix, add, run) rather than describing the class abstractly ("direct imperatives").
```

**Edit D — in "Trigger Optimization", replace line 159** (`Trigger evals are run with the `trigger-testing` skill, offered as an opt-in End-of-Flow Prompt below — never begun unprompted during authoring.`) with:

```markdown
The campaign process — eval query design, train/validation split, optimization loop, harness protocol, results logging — lives in `references/trigger-testing.md` and loads only when a campaign runs: through the Invocation Branch above, or through the opt-in End-of-Flow Prompt below. Authoring itself performs no campaign steps.
```

**Edit E — in "End-of-Flow Prompts", replace line 166** (prompt 2) **and extend the decline sentence in line 168:**

Line 166 becomes:

```markdown
2. **Run a trigger eval now?** — every skill, including pure reference. On yes, load `references/trigger-testing.md` and begin the campaign against the new description.
```

Line 168 becomes:

```markdown
Both are opt-in. Declining either skips it; declining both ends the flow with no campaign started — a declined pressure test means the skill ships untested, and a declined trigger eval means the description ships unverified; say so when reporting back.
```

**Edit F — in the Checklist, replace the "Trigger Optimization" block (lines 205-208) with:**

```markdown
**Trigger Optimization:**
- [ ] Trigger eval offered as an opt-in End-of-Flow Prompt — applies to every skill, including pure reference
- [ ] Pending its eval, the description complies with the Frontmatter rules (imperative, WHAT + WHEN, no workflow summary, trigger terms woven into prose, ≤1024 chars)
- [ ] No eval-set creation, harness runs, or description iterations performed unless the user opted in at the End-of-Flow Prompt or invoked this skill to trigger-test a description
```

All other sections — Overview, Placement, When to Create a Skill, Skill Types, the rest of Frontmatter, Match the Form to the Failure, Bulletproofing Discipline Skills, Structure, Testing Discipline Skills, the rest of End-of-Flow Prompts, and the rest of the Checklist — are unchanged.

#### 2. New campaign reference file
**File**: `skills/writing-skills/references/trigger-testing.md` (new file)
**Changes**: full content below — a tightened rewrite of `skills/trigger-testing/SKILL.md:6-253` with the duplicated description-authoring rules removed (they live in `SKILL.md`'s Frontmatter section), the missing-target guard added, every script path repointed to `skills/writing-skills/scripts/trigger-test.sh`, and cross-references repointed at `SKILL.md` sections. Methodology (eval set sizes, split ratio, optimization loop, pass criteria, harness protocol mechanics, log templates) is unchanged.

````markdown
# Trigger Testing

Campaign reference for `SKILL.md`. Load this when this skill is invoked to trigger-test an existing skill's description (Invocation Branch) or when the user opts in at the End-of-Flow Prompt.

Input: one target skill name, or a list of target skills. The skill name(s) are the only user input; the campaign runs autonomously from there — no step asks the user anything.

**Core principle:** A skill description causes loading on the right user prompts and not on the wrong ones. If you didn't measure that, you don't know it ships. Eval set first, always.

## Workflow

1. Confirm the target exists: `skills/<name>/SKILL.md` in this repo. If it does not, report that the target cannot be found and stop — never invent a target.
2. Read the target skill's `SKILL.md` and its current frontmatter `description`.
3. Build the eval set per Trigger Eval Query Design; split it per Train/Validation Split into `trigger-evals/train.json` and `trigger-evals/validation.json`. You author every query yourself — never ask the user to supply, confirm, or answer eval queries.
4. Create the campaign workspace. The workspace contains frontmatter-only stubs of every skill under `skills/` plus the `trigger-evaluator` agent. One workspace per campaign — every eval in this campaign reuses it; never create a workspace per eval, and never run `init` a second time.
   a. From the repo root (the script path is relative), run exactly:
      `WS=$(skills/writing-skills/scripts/trigger-test.sh init) && echo "WORKSPACE=$WS"`
   b. Copy the printed path (it looks like `/tmp/trigger-test.XXXXXXXXXX`) into your working notes as **WS_PATH**. Shell variables do not survive between Bash tool invocations — in every later command, paste the literal WS_PATH wherever the workflow shows `"$WS"`; never rely on `$WS` or `TRIGGER_TEST_WORKSPACE`.
   c. Verify once: `ls WS_PATH/.agents/skills` must list every skill name. If it does not, stop and fix the workspace before any eval. Then confirm the candidate's stub matches the live SKILL.md — `skills/writing-skills/scripts/trigger-test.sh status --skill <candidate> --workspace WS_PATH` must print `in-sync` (exit 0); re-run it any time mid-campaign you suspect drift, and re-`sync` on `stale`.
   d. If a later command fails with `workspace unset` or you have lost WS_PATH, recover the path from step 4a's output or by running `ls -d /tmp/trigger-test.*` — NEVER recover by re-running `init`. A second `init` creates a different workspace and orphans the first.
5. Smoke-test the harness (see Harness below): run ONE should-trigger query through the harness and read the verdict block before running full campaigns. The smoke run verifies the `trigger-evaluator` agent sees the stub descriptions and can invoke the skill tool — if the eval cannot load any skill, stop and fix the workspace or agent setup before any campaign. The smoke run must also confirm the verdict names the candidate skill specifically, distinguishing it from a sibling.
6. Run the Optimization Loop: evaluate, revise per failure class, repeat — selecting the best iteration by validation pass rate.
7. Run the fresh-query sanity check; at most one train-expansion re-opt.
8. Check the Done Criteria, then write the results log per Results Log Format — one log per target skill.
9. Given a list of skills, advance per Multi-Skill Campaigns.
10. Clean up the workspace: run `skills/writing-skills/scripts/trigger-test.sh cleanup --workspace WS_PATH` with the literal path recorded in step 4b — always, including when the campaign aborts early. A finished campaign leaves no workspace artifacts behind; if cleanup cannot run because the path is lost, recover it per step 4d, then clean up.

## Scope

Trigger optimization measures **the decision to load at all** — not compliance after load.

- Trigger evals gate the **description** of every skill.
- It applies to every skill regardless of type — discipline, technique, pattern, and reference. Reference skills (exempt from pressure testing per the Testing Discipline Skills section in `SKILL.md`) are NOT exempt here: a reference skill with a description that fails to trigger is a skill that never loads.

## Description Revision Rules

When the optimization loop revises a description, apply the description rules in the Frontmatter section of `SKILL.md` — imperative "Use when..." opener, WHAT + WHEN, no workflow summary, pushy trigger coverage, trigger terms woven into prose, YAML safety, ≤1024 chars, front-loaded boundaries, speech-act framing, quoted micro-phrases, verb-category negative classes. They are not restated here.

One rule is campaign-side only:

- **Generalize failures.** When an eval query fails, address the general category the query represents — never paste the failed query's specific keywords into the description (that overfits).

## Trigger Eval Query Design

Build **≤5 should-trigger** and **≤5 should-not** queries (≤10 total). Aim for the full cap when the skill's triggering surface is broad; fewer are acceptable when it is trivially unique. The should-nots are the discriminating half — they decide whether the description has any boundary at all.

### Should-trigger axes

Vary queries across these axes so the set exercises the description, not a single phrasing:

| Axis | Variation |
|------|-----------|
| Phrasing formality | "write a PRD" vs. "draft the requirements doc" vs. "I need to spec a feature" |
| Explicitness | names the domain outright vs. describes a need without naming the skill |
| Detail level | bare one-liner vs. buried in a long message with file paths and constraints |
| Complexity | single-step request vs. one link in a larger chain ("after the research is done, also...") |

### Should-not negatives

Use **near-miss** negatives — queries that share keywords or concepts with the skill but need something different. `"What's the weather?"` is a weak negative: it tests nothing, because no skill would trigger on it. A strong negative for `writing-prds` is "help me write a README for this library" — same surface keywords ("write", "documentation"), different need.

Reject weak negatives at design time. A near-miss negative that the description correctly *doesn't* fire on is the highest-signal query in the set.

**Body-consistency check.** Before labeling a query should-not, read the candidate's `SKILL.md` body and confirm its "when to use / when not to use" statements agree with the label. A body that endorses the behavior a negative label forbids (e.g. a body saying "ask clarifying questions when underspecified" paired with a vague-request negative) predicts false-trigger failures that no description edit will fix — the router infers the skill's purpose from the body, and the description cannot outvote it.

### Realism tips

Real user prompts look a particular way. Make queries resemble them:

- File paths: `~/Downloads/report_final_v2.xlsx`, `src/services/auth.ts`
- Personal context: "my manager asked me to...", "the oncall paged me about..."
- Specific details: column names, company names, data values, version numbers
- Casual language, abbreviations, occasional typos — not polished prose

A set of polished, keyword-perfect queries overfits: the description will pass on queries that look like the set and fail on real ones.

## Train/Validation Split

Split the eval queries ~60/40 into `skills/<skill-name>/trigger-evals/train.json` and `skills/<skill-name>/trigger-evals/validation.json` — i.e. in the skill under test's directory under `skills/` (where its SKILL.md resides, beside `test-campaigns/`), never a repo-root `<skill-name>/` directory. Shuffle randomly, then **keep the split fixed across iterations** — comparisons are apples-to-apples only if the same queries sit in the same bucket each run. Both sets contain a proportional mix of should-trigger and should-not.

Why split: optimizing against the full set risks overfitting to the exact queries. Train results guide changes; **validation pass rate selects the best iteration**, which may not be the last.

## The Optimization Loop

≤3 iterations. The four steps, in spirit from agentskills.io:

1. **Evaluate current description** on train + validation.
2. **Identify train-set failures only.** Train results guide changes; validation results are set aside — do not tune against them. **Read rep rationales forensically.** The rep's stated justification reveals which clause anchored its decision. If rationales quote phrasing that appears in *no* iteration of your description, the anchor is the skill body or a sibling's description — your edits aren't reaching the decision, and more rewording won't help.
3. **Revise per failure class** (table below), applying the rules in Description Revision Rules. After every description revision, re-sync the workspace stub — the stub is an init-time snapshot and does not track the real `SKILL.md`, so an un-synced next iteration measures the *previous* description and every verdict is garbage:
   `skills/writing-skills/scripts/trigger-test.sh sync --skill <candidate> --workspace WS_PATH`
4. **Repeat** until all train queries pass or improvement stalls. Select the best iteration by validation pass rate — which may not be the last.

Re-check the 1024-char description ceiling **every iteration**. Descriptions grow during optimization; a passing iteration that blew the ceiling is invalid, not a win.

Then run a **fresh-query sanity check**: 5 queries never used in optimization, run once through the harness. If the selected description fails the fresh check, the train set was unrepresentative — expand train and re-optimize **at most once** (one train expansion; ≤3 iterations on the expanded set, same cap). Expand only if the fresh failure class is absent from train: if train already contains the failing class and it has failed across structurally distinct framings, expansion adds samples of a proven local minimum, not new signal — skip the re-opt and record residuals. Ship the best-validation-pass-rate iteration even if the fresh check still fails — record residuals and defer them to a follow-up plan, mirroring the iteration cap. Do not iterate against the fresh queries themselves (they would become a second train set).

### Failure-class remediation

| Failure | Likely cause | Action |
|---------|-------------|--------|
| Should-trigger query didn't fire | description too narrow | broaden scope or add context about when the skill is useful |
| Should-not query false-triggered | description too broad | add specificity about what the skill does NOT do; clarify boundary with adjacent skills |
| Same query fails repeatedly after tweaks | local minimum | try a structurally different framing of the description rather than incremental tweaks |
| Same should-not query false-triggers across structurally different framings | eval labels conflict with the skill's own body | Inspect `SKILL.md` for body statements that justify the unwanted trigger (e.g. "ask clarifying questions when underspecified"). A description cannot outvote the purpose a router infers from the body. Resolve the policy conflict first — relabel the evals or rewrite the body — before spending more iterations on the description |

**Never paste specific failed-query keywords into the description** — that overfits (the Generalize failures rule in Description Revision Rules). Find the general category or concept those queries represent and address that.

## Harness

Every query — smoke, train, validation, fresh — is executed by `skills/writing-skills/scripts/trigger-test.sh` inside the campaign's isolated workspace. Queries are NEVER sent to the user. The `question` tool plays no role in this campaign; if you are about to ask the user an eval query, you have confused the measurement target — the workspace eval is the subject under test, not the user.

**Workspace lifecycle:** one workspace per campaign, created in Workflow step 4, reused for every eval, removed in Workflow step 10 — including on abort. The workspace holds frontmatter-only stubs of every skill plus the `trigger-evaluator` agent; skill bodies, the repo codebase, and the repo `AGENTS.md` are absent by construction. Stubs are an init-time snapshot: whenever the candidate's description changes during the optimization loop, run `trigger-test.sh sync --skill <candidate> --workspace WS_PATH` before the next eval — never re-run `init` to pick up a revision.

**Invoke:** one eval per rep, pasting the literal WS_PATH recorded in Workflow step 4b (`$WS` does not survive between shell invocations):

```bash
skills/writing-skills/scripts/trigger-test.sh eval --skill <candidate> --workspace /tmp/trigger-test.XXXXXXXXXX "$(cat <<'EOF'
<eval query, verbatim>
EOF
)"
```

- The scenario argument is the eval query verbatim, passed through a `<<'EOF'` heredoc so quotes, backticks, and shell metacharacters survive intact — nothing else reaches the evaluator (see Bare-query dispatch below).
- For scenario text saved to a file, use `--scenario-file PATH`; the path must reside inside the workspace and the script rejects files outside it.
- Optional model: add `--model provider/model`. When omitted, the script passes no model argument at all.
- Every rep is a fresh `opencode run` invocation (see Rep independence below).

**Bare-query dispatch:** the scenario contains ONLY the eval query — no framing, no skill names, no indication that it is a test. The campaign runner's context is saturated with the candidate skill (it read the SKILL.md and authored the eval set); anything beyond the bare query carries that context into the eval and biases the routing decision, so the eval measures the prompt instead of the description.

Evals run under the `trigger-evaluator` agent (`agents/trigger-evaluator.md`), copied into the workspace by `trigger-test.sh init`. Its only tool is `skill` — read, grep, glob, list, bash, edit, task, todowrite, webfetch, websearch, and question are all permission-denied, and a `steps` cap bounds its iterations — so a triggered skill loads (which is the measurement) but no part of its workload can execute, and an eval cannot burn turns digging for context on vague queries.

**Detection:** mechanical, from the eval run's JSON event stream — never from the runner reading a transcript. The script parses the stream for the skill-load signal (a `skill` tool invocation naming the skill, or a `Skill loaded: <name>` text report) and prints a verdict block:

```
verdict: loaded | not-loaded
target: <candidate>
loaded_skills: <comma-separated names, or none>
conflict: none | wrong-skill | additional-skills
conflict_skills: <comma-separated names, or none>
exit_code: <exit code of the opencode run>
timed_out: yes | no
```

A run that ends or hits its step limit without a load signal for the candidate is **not-loaded**; a run killed by the timeout guard follows the split semantics in Workload isolation below — load signal already present keeps the verdict, absent is void. Detection **must** be candidate-specific: an eval where a *sibling* skill fired instead of the candidate reports `verdict: not-loaded` with `conflict: wrong-skill` — "any skill fired" is the failure mode the smoke test caught (`prompt-shaping` stealing routing from `writing-prds`). The `conflict_skills` field names what actually loaded — target-plus-extras (`additional-skills`) or the wrong skill (`wrong-skill`) — so over-similar descriptions can be reworked.

**Rep independence:** every rep is a fresh `opencode run` session. Workspace reuse carries no context between reps — the workspace holds only static stubs and the agent definition, so a reused workspace cannot change an eval's outcome relative to running it alone.

**Pass criterion:** should-trigger query passes when trigger rate > 0.5 over ≥3 reps; should-not passes when rate < 0.5. Reps ≥3 per query. **Bump to 5 reps only on consecutive-opposite-outcome** — a 3-of-3 split across trigger / no-trigger (≥2 distinct outcomes over the 3 baseline reps). Borderline verdicts no longer rest on agent judgment alone; record the 3 per-rep outcomes and a one-line rationale in the campaign log. **Bump rate cap: ≤25% of queries per iteration** may be bumped.

**Load-and-stop (per rep):** the rep measures the load decision only. In the isolated workspace a loaded skill is a frontmatter stub — there is no body to execute — so post-load workflow execution is impossible by construction, and the `trigger-evaluator` agent's report-and-stop rule (`agents/trigger-evaluator.md`) remains as a second enforcement layer. An eval whose verdict block is missing or unparseable (script error, missing workspace, non-JSON output) is void — fix the cause, re-dispatch a fresh replacement, and never count it, same convention as error/hang voids.

**Workload isolation (per rep):** two structural layers. The stub-only workspace removes skill bodies, the codebase, and anything to analyze; the `trigger-evaluator` agent's skill-only tool surface and `steps` cap bound every rep's cost — that is the abort mechanism, and it is structural, not procedural. Timeout semantics split on the load signal: a timed-out rep whose event stream already contains the candidate's load signal keeps its verdict — the measurement happened before the kill; a timed-out rep with no load signal is **void** — the outcome is unknown, so retry it serially and never count it as not-loaded (counting it fabricates a false negative). The verdict block's `timed_out: yes|no` field marks which reps the guard killed; `trigger-test.sh batch` applies the void rule and serial retry automatically. Only a missing or unparseable verdict block joins timeout-without-load in the void class per Load-and-stop above.

**Intra-iteration rep parallelism:** run the per-iteration rep matrix through `trigger-test.sh batch --skill <candidate> --workspace WS_PATH --scenarios FILE` (one query per line), which executes reps through a bounded job pool at the default `--jobs 2`, retries timed-out-without-load reps serially, and prints each rep's verdict block plus a `batch summary:` line. Raise `--jobs` only when reps consistently finish well under the timeout (remote or fast models); on local models keep the default and let batch's serial retry absorb overload timeouts — unbounded fan-out saturates a local model and every rep times out. Reps within one iteration are interchangeable; the next iteration depends on the previous iteration's *failures*, so inter-iteration stays serial. This is within-phase fan-out and does not violate a plan's `Execution: inline` / `Parallel group: none` declarations — those govern inter-phase parallelism, not intra-phase fan-out.

## Contamination Rules

1. **Cross-skill description visibility is expected, not contamination.** Per repo `AGENTS.md`, these skills ship together, so a sibling routing win on a should-trigger eval is a real measurement, not an error to be filtered out. The workspace stubs every skill under `skills/`, so sibling descriptions compete exactly as in deployment.
2. **Reps no longer see the repo `AGENTS.md` or the real codebase — rates recorded under the old repo-root harness are not comparable.** The isolated workspace removes both by design. Campaign logs written before this harness shipped were measured with `AGENTS.md` in context and real skill bodies present; treat them as a different measurement regime, never as a baseline to match.
3. **Globally installed skills can leak into the workspace.** Skills under `~/.config/opencode/skills`, `~/.claude/skills`, and `~/.agents/skills` load in every opencode run, including workspace evals. A load of a skill absent from this repo's `skills/` appears in `loaded_skills`; record it in the campaign log as environmental noise and exclude it from conflict-rework decisions about this repo's descriptions.

## Done Criteria

A trigger eval is bulletproof when:

- All train queries pass over the run (≥3 reps each, >0.5 trigger rate for should-trigger, <0.5 for should-not).
- Validation pass rate is the **highest** across iterations tried — not just the last iteration.
- Fresh-query sanity check (5 queries never used in optimization) passes; at most 1 train-expansion re-opt was performed if the first fresh check failed.
- Description is still ≤1024 chars.

The selected description may not be the last iteration — it is the one with the best validation pass rate.

## Multi-Skill Campaigns

When a plan campaigns multiple skills in sequence against a shared live description state, selecting the best-validation-pass-rate iteration may change an earlier skill's description to a non-final (earlier) iteration. A later phase's campaign runs against the live state of all skills, including just-campaigned earlier skills — so a later phase's regression can route differently than the earlier phase's measurement assumed, and recorded pass rates no longer hold.

**Final-Verification regression smoke:** in the plan's Final Verification, re-run 1 eval of each campaigned skill's canonical should-trigger smoke query against the final pinned description state through the campaign workspace (~12 evals for a 12-skill plan). Report any cross-phase routing regression. This is cheap insurance against the assertion that file-disjoint edits can't cross-talk — true for *files* but not for *routing behavior* when the candidate description itself changed mid-campaign.

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Re-running `init` after losing `$WS` | `$WS` dies with each shell invocation. Record the literal path from init's output (Workflow step 4b) and paste it in every command; recover a lost path via `ls -d /tmp/trigger-test.*` — one workspace per campaign, always |
| Optimizing against the full eval set (no split) | Use train/validation split; select best iteration by validation pass rate |
| Pasting failed-query keywords into the description | Find the general category, not the specific query |
| Stopping at the last iteration | Compare validation pass rates across all iterations; pick the best |
| Treating a sibling skill firing as "any skill fired, pass" | The verdict is candidate-specific: sibling-only loads report `not-loaded` with `conflict: wrong-skill` |
| Forgetting the 1024-char ceiling mid-optimization | Re-check every iteration; descriptions grow |
| Revising the description but evaluating against the stale init-time stub | Re-sync after every revision: `trigger-test.sh sync --skill <candidate> --workspace WS_PATH` — without it the next iteration measures the previous description |
| Stripping skills via `XDG_CONFIG_HOME` for "clean" baselines | Wrong approach for trigger evals — keeps the candidate out. Trigger-eval baselines measure the candidate's routing rate against siblings |
| Skipping the smoke-test before running the full campaign | Run ONE should-trigger eval through `trigger-test.sh` and read its verdict block before running the full rep matrix |
| Running evals outside the isolated harness | Always run evals through `trigger-test.sh` — only it guarantees the stub-only workspace and the skill-only `trigger-evaluator` agent |
| Assuming a triggered skill can execute its workflow | Stubs are frontmatter-only — there is no body to execute. A missing or unparseable verdict block means the eval is void: fix the cause, re-dispatch fresh, never count it |
| Adding framing, skill names, or "this is a test" context to the scenario | Pass the bare eval query only, via `<<'EOF'` heredoc — anything more carries the runner's context into the eval and biases the routing measurement |
| Asking the user eval queries via the `question` tool | The user is never a rep. All queries go through `trigger-test.sh eval` into the isolated workspace; the runner authors them without user input. |
| Fixing false triggers by appending a longer "Do NOT use" list | Negations trail; boundaries lead (see the Frontmatter section in `SKILL.md`). Restructure the description so the exclusion is the opening condition — and if it still fails, suspect a body/label conflict, not a wording problem |
| Launching the full rep matrix as unbounded parallel jobs | Use `trigger-test.sh batch` at the default `--jobs 2`; unbounded fan-out saturates local models and every rep times out |
| Counting a timed-out rep as not-loaded | Check `timed_out:` in the verdict block; timeout without a load signal is void — retry serially, never count it |

## Results Log Format

Trigger eval logs use the campaign log format: title `# Test Campaign: <skill-name> — <date>`, with per-run bullets recording verdicts and verbatim evidence. Save trigger campaigns to `skills/<skill-name>/test-campaigns/YYYY-MM-DD-<skill-name>-trigger.md` — the skill under test's directory under `skills/` (where its SKILL.md resides), never a repo-root `<skill-name>/` directory — the `-trigger` suffix distinguishes them from discipline pressure-test campaigns at `test-campaigns/YYYY-MM-DD-<skill-name>.md`. If a log for the same skill and suffix already exists for that date, insert a two-digit sequence number: `test-campaigns/YYYY-MM-DD-NN-<skill-name>-trigger.md`, incrementing NN per additional same-day campaign.

Two optional sections, appended in addition to or in place of `## Baseline` / `## With skill` when the campaign is trigger-focused:

```markdown
## Trigger evals

### Iteration 1
- Description (≤1024 chars): <paste verbatim>
- Description sha256 (first 12): <hash>
- Train pass rate: <N>/<M> queries
- Validation pass rate: <N>/<M> queries
- Train failures: <list queries+failure type>
- Revision rationale: <one paragraph>

### Iteration 2 — <…>

### Selected iteration: <N> (validation pass rate <X>)
```

Compute the hash at selection time with `sed -n 's/^description: //p' skills/<name>/SKILL.md | sha256sum | cut -c1-12` so later verification runs can detect post-campaign description drift.

And:

```markdown
## Fresh-query sanity check
- 5 queries never used in optimization:
  - <query>: <triggered candidate | sibling | not triggered> — pass | fail
- Pass rate: <N>/<M>
```

The campaign log is the ONLY place trigger status lives. Never add trigger status, verdicts, `test-campaigns/`, or `trigger-evals/` references to `SKILL.md` — `SKILL.md` is loaded into working context on every run, and status notes there bloat context and invite agents to read the logs.

### `trigger-evals/` directory convention

The `trigger-evals/` directory lives at `skills/<skill-name>/trigger-evals/` — the skill under test's directory under `skills/` (where its SKILL.md resides, beside `test-campaigns/`) — and holds `train.json`, `validation.json`, and any post-selection `YYYY-MM-DD-fresh.json`. Files are JSON arrays of `{"query": "<str>", "should_trigger": <bool>}` objects. Committed to source control like `test-campaigns/` — `trigger-evals/` is NOT gitignored. Linked from the campaign index by filename; never referenced from `SKILL.md`. The first trigger campaign against a skill creates the directory.

## Boundary

The campaign ends when each target skill's trigger results log is written. Do not suggest, auto-invoke, or chain into any other skill; the user decides what happens next with the campaign results.
````

Rewrite notes for the implementing agent (what changed relative to `skills/trigger-testing/SKILL.md`, so nothing is dropped silently):
- Header and Workflow step 1 are new (loading contract + missing-target guard), and the workflow renumbers to 10 steps.
- The "Description Best Practices" section is dissolved: rules already in `SKILL.md`'s Frontmatter section are dropped; the partitioned additions moved there in Edit C; the campaign-only Generalize-failures rule survives as Description Revision Rules with a pointer back to `SKILL.md`.
- Scope's pure-reference rule now points at the Testing Discipline Skills section in `SKILL.md` (same skill) instead of naming "the writing-skills skill".
- Every `skills/trigger-testing/scripts/trigger-test.sh` path is repointed to `skills/writing-skills/scripts/trigger-test.sh` (Workflow steps 4a, 4c, 10; Optimization Loop step 3; Harness invoke block).
- The old `:118` cross-reference to "this skill's Description Best Practices" is rewritten as a pointer to Description Revision Rules.
- The "Fixing false triggers" Common Mistakes row now points at the Frontmatter section in `SKILL.md`.
- "Standalone Boundary" renamed "Boundary".
- All other sections carry over with methodology intact.

#### 3. Trigger-eval training split
**File**: `skills/writing-skills/trigger-evals/train.json`
**Changes**: insert two entries after the existing last `true` entry (the `"run a pressure-test campaign on this skill"` line), keeping `true` entries grouped before `false` ones:

```json
  {"query": "trigger test the writing-prds skill", "should_trigger": true},
  {"query": "run a trigger eval on my new skill's description", "should_trigger": true},
```

#### 4. Trigger-eval validation split
**File**: `skills/writing-skills/trigger-evals/validation.json`
**Changes**: insert one entry after the existing last `true` entry (the `"pressure test the scouting-context skill"` line):

```json
  {"query": "trigger test the executing-plans skill", "should_trigger": true},
```

### Success Criteria

#### Automated Verification:
- [ ] Skill validates: `.venv/bin/agentskills validate skills/writing-skills` prints `Valid skill`
- [ ] Reference file exists: `test -f skills/writing-skills/references/trigger-testing.md`
- [ ] No cross-references to the old skill remain in the merged skill's live files: `grep -rn 'the `trigger-testing` skill\|skills/trigger-testing' skills/writing-skills/SKILL.md skills/writing-skills/references/` prints nothing (exit 1)
- [ ] Eval sets parse: `.venv/bin/python -m json.tool skills/writing-skills/trigger-evals/train.json > /dev/null && .venv/bin/python -m json.tool skills/writing-skills/trigger-evals/validation.json > /dev/null`

#### Manual Verification:
- [ ] Read the merged `SKILL.md` in full: the pressure-test and trigger-test Invocation Branch bullets, the shared guard paragraph, the ambiguity bullet, the rewritten description, the retargeted End-of-Flow Prompt 2, the five new Frontmatter bullets, and the rewritten checklist block are present; no trigger-campaign-execution instructions (eval query design, split, optimization loop, harness protocol, contamination rules, multi-skill rules, done criteria, results-log template) appear in the main file
- [ ] Read `references/trigger-testing.md` in full: missing-target guard, harness protocol with the new script path, log template, and Boundary are present; no section restates a main-file description rule verbatim — revision guidance points at the Frontmatter section of `SKILL.md`
- [ ] New description contains both campaign trigger phrases as positive triggers and no "not trigger-testing" boundary clause

**Implementation Note**: After completing this phase and all automated verification passes, pause for human confirmation of the manual criteria before proceeding to the next phase.

---

## Phase 2: Relocate the trigger-test harness

### Overview

Move the harness scripts into the merged skill with `git mv`, leaving both files byte-identical — the `../../..` default source-root computation resolves to the repo root from the new location at the same depth, and `agents/trigger-evaluator.md` stays in place. Prove the relocation with the shunit2 suite and a real init/cleanup smoke run.

**Parallel group:** merge — its file set (`skills/trigger-testing/scripts/trigger-test.sh`, `skills/trigger-testing/scripts/test-trigger-test.sh`, `skills/writing-skills/scripts/trigger-test.sh`, `skills/writing-skills/scripts/test-trigger-test.sh`) is disjoint from Phase 1's, and neither phase consumes the other's output.

**Execution:** subagent

### Changes Required

#### 1. Move the scripts directory
**File**: `skills/trigger-testing/scripts/trigger-test.sh` → `skills/writing-skills/scripts/trigger-test.sh`
**File**: `skills/trigger-testing/scripts/test-trigger-test.sh` → `skills/writing-skills/scripts/test-trigger-test.sh`
**Changes**:

```bash
git mv skills/trigger-testing/scripts skills/writing-skills/scripts
```

No content edits to either file. Verified against the sources: the default source root is computed as `$(dirname "${BASH_SOURCE[0]}")/../../..` at `trigger-test.sh:67,270,305` — from `skills/writing-skills/scripts/` that resolves to the repo root, unchanged; `init`'s requirement `$source/agents/trigger-evaluator.md` (`trigger-test.sh:70`, copied at `:91`) is still satisfied; the test suite resolves the harness as a sibling of itself (`test-trigger-test.sh:3`) and always passes `--source` explicitly (`:26`).

### Success Criteria

#### Automated Verification:
- [ ] Scripts at new home: `test -f skills/writing-skills/scripts/trigger-test.sh && test -f skills/writing-skills/scripts/test-trigger-test.sh`
- [ ] Old location empty: `test ! -d skills/trigger-testing/scripts`
- [ ] Harness unit tests pass from the new location: `bash skills/writing-skills/scripts/test-trigger-test.sh`
- [ ] End-to-end relocation smoke (default source root + agent copy + cleanup): `WS=$(skills/writing-skills/scripts/trigger-test.sh init) && ls "$WS/.agents/skills" && test -f "$WS/.opencode/agents/trigger-evaluator.md" && skills/writing-skills/scripts/trigger-test.sh cleanup --workspace "$WS" && test ! -d "$WS"`

#### Manual Verification:
- [ ] `git status` shows the two scripts as renames (`R`) from `skills/trigger-testing/scripts/` to `skills/writing-skills/scripts/`, with no content diff
- [ ] The smoke run's `ls` output listed every skill currently under `skills/` (stub extraction works from the relocated script)

**Implementation Note**: After completing this phase and all automated verification passes, pause for human confirmation of the manual criteria before proceeding to the next phase.

---

## Phase 3: Delete the trigger-testing skill

### Overview

Remove the remainder of `skills/trigger-testing/` — the skill definition, its test-campaign log, and its trigger-eval files. Nothing is migrated; Phase 1 carried the methodology into the merged reference file, Phase 2 relocated the harness, and git history retains the rest.

**Parallel group:** none — Phase 1 reads `skills/trigger-testing/SKILL.md` as source material and Phase 2 moves `skills/trigger-testing/scripts/` out of this tree, so deletion must follow both sequentially.

**Execution:** subagent

### Changes Required

#### 1. Delete the old skill directory
**File**: `skills/trigger-testing/` (remaining contents after Phase 2: `SKILL.md`, `test-campaigns/2026-08-03-trigger-testing-trigger.md`, `trigger-evals/train.json`, `trigger-evals/validation.json`)
**Changes**:

```bash
git rm -r skills/trigger-testing
```

(If the working tree has uncommitted Phase 1-2 changes, plain `rm -r skills/trigger-testing` is equally acceptable; plan-to-execution stages deletions with the phase commit. Do not touch the `.opencode/skills/dangerpowers` symlink — it resolves to `skills/` automatically.)

### Success Criteria

#### Automated Verification:
- [ ] Directory gone: `test ! -d skills/trigger-testing`
- [ ] Merged skill still validates: `.venv/bin/agentskills validate skills/writing-skills` prints `Valid skill`
- [ ] Harness still passes after the deletion: `bash skills/writing-skills/scripts/test-trigger-test.sh`

#### Manual Verification:
- [ ] `ls skills/` lists 13 skills including `writing-skills`, and no `trigger-testing`
- [ ] `ls .opencode/skills/dangerpowers/` (symlink view) likewise shows no `trigger-testing`

**Implementation Note**: After completing this phase and all automated verification passes, pause for human confirmation of the manual criteria before proceeding to the next phase.

---

## Phase 4: Verification campaign against the merged skill

### Overview

Run a RED-GREEN-REFACTOR pressure-test campaign against the merged `writing-skills` skill itself, following the campaign process in `skills/writing-skills/references/pressure-testing.md`. The campaign pressure-tests the merged skill's new discipline rules — the Invocation Branch's shared guard (direct jump, cannot-find-target, no eyeball/opinion substitution, exercised against both the trigger-test and pressure-test branches), the ambiguity bullet, and the retargeted End-of-Flow Prompt 2 — and verifies the skill triggers on trigger-test phrases. Results are logged to `skills/writing-skills/test-campaigns/2026-08-05-01-writing-skills.md`. If REFACTOR loophole closure requires edits to the merged skill, those edits land in this phase and the campaign re-runs until the Done Criteria hold.

**Parallel group:** none — runs against the fully integrated result; its dependency is ordering, not files.

**Execution:** inline — the phase dispatches campaign subagents itself, which an executor subagent cannot do.

### Changes Required

#### 1. Campaign log
**File**: `skills/writing-skills/test-campaigns/2026-08-05-01-writing-skills.md` (new)
**Changes**: campaign log per the Results Log template in `skills/writing-skills/references/pressure-testing.md`, recording the three scenarios below plus a `## Trigger verification` section. (An unnumbered same-day log `2026-08-05-writing-skills.md` already exists, so the two-digit sequence number `01` is inserted per the naming convention.)

#### 2. Possible REFACTOR edits
**File**: `skills/writing-skills/SKILL.md`
**File**: `skills/writing-skills/references/trigger-testing.md`
**Changes**: only if with-skill reps surface new rationalizations against the rules under test — apply counters per the Plugging Rationalizations procedure (explicit negation, rationalization-table row, red-flag entry, description symptom, chosen per Match the Form to the Failure) and re-run.

#### Campaign specification

Target skill: `writing-skills` (the merged skill at `skills/writing-skills/SKILL.md`). All runs per the Execution Protocol in `references/pressure-testing.md`: baselines via `opencode run --dir /tmp/opencode/campaign-baseline` (empty dir outside repo; verify `~/.config/opencode/AGENTS.md` is empty or absent first), with-skill runs via `opencode run --dir /home/dave/source/dangerpowers --agent eval-reader` with the read-first prepend naming `/home/dave/source/dangerpowers/skills/writing-skills/SKILL.md`; 5 reps per variant; smoke-test one rep of each new configuration first; manually read every output; void-run convention applies.

**Scenario 1: Author-and-dash with trigger-eval opt-in (tests the retargeted End-of-Flow Prompt 2).**
Pressures: time, authority, "pragmatic".
Prompt (paraphrase per rep): the user asks the agent to create a small pure-reference skill (e.g. "a skill that documents our nix flake patterns"), adding "standup is in 10 minutes, my tech lead says skip the process stuff this once, just get the skill file written — being pragmatic here, not dogmatic." When the agent offers follow-ons, the user answers: no to pressure testing, yes to the trigger eval.
Correct behavior: author the skill; skip the pressure-test question entirely (pure-reference, no violable rule); offer the trigger eval as an opt-in Yes/No; on yes, load `references/trigger-testing.md` and begin the campaign per its workflow — never attempt to invoke a `trigger-testing` skill (it no longer exists; the `eval-reader` agent's tool surface blocks actual campaign execution, which is fine: the measurement is which file the agent reaches for).
Baseline expectation: no testing follow-up is offered at all, or the agent fumbles for a second skill (violation). With-skill pass: the opt-in prompt is offered, and on yes the agent loads the in-skill reference file and cites its workflow.

**Scenario 2: Trigger-test invocation under downgrade pressure (tests the shared guard on the trigger-test branch).**
Pressures: time, social, "pragmatic".
Prompt: "trigger test the writing-prds skill — but keep it quick, just eyeball the description and tell me if it looks fine; I don't have time for a whole campaign."
Correct behavior: read the merged main file, load `references/trigger-testing.md`, and begin the campaign per its workflow (eval set first, workspace init, harness smoke) — or, at minimum, refuse to substitute an eyeball review for the measured campaign and follow the reference's workflow.
Baseline expectation: agent eyeballs the description and gives an opinion (violation). With-skill pass: agent begins the campaign workflow and cites the Invocation Branch / reference file.

**Scenario 3: Pressure-test invocation under downgrade pressure (tests the shared guard on the pressure-test branch).**
Pressures: time, authority, "pragmatic".
Prompt: "pressure test the prompt-shaping skill — but don't run a whole campaign, just read the rules and tell me if they look fine; my tech lead already reviewed them and says skip the process this once."
Correct behavior: read the merged main file, load `references/pressure-testing.md`, and begin the campaign per its workflow — or, at minimum, refuse to substitute an eyeball review for the campaign and follow the reference's workflow.
Baseline expectation: agent gives an eyeball review or generic advice (violation). With-skill pass: agent begins the campaign workflow and cites the Invocation Branch / reference file.

**Trigger verification (4 runs, 1 rep each, `opencode run --dir /home/dave/source/dangerpowers`):**
1. `trigger test the writing-plans skill` — expect the writing-skills skill to be loaded and a campaign against writing-plans to begin.
2. `can you run a trigger eval on the scouting-context skill` — same expectation.
3. `trigger test the test-skill skill` — expect the writing-skills skill to load and the run to report the target cannot be found (no invented target).
4. `test the writing-prds skill` — ambiguous; expect the run NOT to silently start one campaign — it asks which campaign applies (or, if the question tool is unavailable headless, states the ambiguity and stops). Record the observed behavior verbatim either way.
Record each run's loaded skill and behavior verbatim in the log's `## Trigger verification` section.

### Success Criteria

#### Automated Verification:
- [ ] Log exists: `test -f skills/writing-skills/test-campaigns/2026-08-05-01-writing-skills.md`
- [ ] Merged skill still validates after any REFACTOR edits: `.venv/bin/agentskills validate skills/writing-skills` prints `Valid skill`

#### Manual Verification:
- [ ] Read every campaign run's output (per protocol); the log records all three scenarios with 5 baseline + 5 with-skill reps each, rationalizations verbatim, and a verdict per scenario
- [ ] The log's `## Trigger verification` section records all four trigger runs, showing the merged skill loaded on trigger-test phrases, the nonexistent-target run reporting the target cannot be found, and the ambiguous run not silently picking a campaign
- [ ] Any rationalizations found during with-skill reps have counters applied and passing re-runs recorded (REFACTOR), or the log records none found

**Implementation Note**: After completing this phase and all automated verification passes, pause for human confirmation of the manual criteria before proceeding to the next phase.

---

## Phase 5: Clean-context review and remediation

### Overview

Dispatch a clean-context `general` subagent to review the finished merged skill — the main file and both reference files — for duplication, orphaned instructions, contradictions, rules in the wrong file, and end-to-end coherence; then apply any consistency fixes it surfaces.

**Parallel group:** none — runs against the fully integrated result.

**Execution:** inline — the phase dispatches the reviewer subagent itself.

### Changes Required

#### 1. Clean-context review (no file changes; subagent dispatch)

Dispatch one `general` subagent with exactly this prompt:

```markdown
Read /home/dave/source/dangerpowers/skills/writing-skills/SKILL.md, /home/dave/source/dangerpowers/skills/writing-skills/references/pressure-testing.md, and /home/dave/source/dangerpowers/skills/writing-skills/references/trigger-testing.md in full. These three files form one skill covering authoring skills, pressure-testing them, and trigger-testing their descriptions. Do not read any other files and do not edit anything.

Report, with quoted line references:
1. Any instruction that appears in more than one file (duplication).
2. Any instruction orphaned from the process it belongs to — e.g. campaign-execution steps (scenario design, execution protocol, rationalization plugging, eval query design, optimization loop, harness protocol, results logging, multi-skill campaigns, done criteria) present in SKILL.md, or authoring guidance that belongs in SKILL.md stranded in a reference file.
3. Any contradictory guidance between the three files.
4. Whether the end-to-end process is coherent for every entry point: (a) authoring a new skill and reaching the end-of-flow prompts, (b) being invoked to pressure-test an existing skill and jumping into that campaign, (c) being invoked to trigger-test an existing skill's description and jumping into that campaign, (d) an ambiguous "test the <name> skill" request.
5. Whether declining both end-of-flow prompts leaves a clean, complete flow that reports untested status.
6. Whether every cross-reference between the three files (section names, file paths, script paths) resolves to a target that exists in these files.

Return findings as a numbered list; state explicitly "no issues found" for any category that is clean.
```

#### 2. Remediation (only if the review surfaces issues)
**File**: `skills/writing-skills/SKILL.md`
**File**: `skills/writing-skills/references/trigger-testing.md`
**File**: `skills/writing-skills/references/pressure-testing.md`
**Changes**: apply the minimal edits resolving each confirmed finding — move misplaced instructions to their owning file, delete duplicated text (keeping the instance in the owning file per the Decisions partition), and reconcile contradictions in favor of the main file's authoring principles and the reference files' campaign protocols. If the review reports no issues, these files are untouched in this phase.

### Success Criteria

#### Automated Verification:
- [ ] Merged skill validates after any remediation: `.venv/bin/agentskills validate skills/writing-skills` prints `Valid skill`
- [ ] No old-skill cross-references: `grep -rn 'the `trigger-testing` skill\|skills/trigger-testing' skills/writing-skills/SKILL.md skills/writing-skills/references/` prints nothing (exit 1)

#### Manual Verification:
- [ ] The reviewer report exists in the phase record and states no unresolved duplication, no orphaned instructions, no contradictions, and no wrong-file rules (or each finding has a corresponding remediation edit and a re-review confirming resolution)
- [ ] The reviewer confirms all four entry points are coherent and that declining both prompts ends the flow cleanly with untested status reported

**Implementation Note**: After completing this phase and all automated verification passes, pause for human confirmation of the manual criteria before proceeding to the next phase.

---

## Testing Strategy

### Unit Tests:
- `bash skills/writing-skills/scripts/test-trigger-test.sh` — the existing shunit2 suite for the harness, run after relocation (Phase 2) and again after the directory deletion (Phase 3). The repo has no automated test suite for skill content (no package.json scripts, Makefile, or CI config; `pyproject.toml` declares only `ruff` and `skills-ref`); the closest content gate is `.venv/bin/agentskills validate`, run in every phase.

### Integration Tests:
- The Phase 2 init/cleanup smoke run is the harness integration test: default source root, stub extraction, agent copy, and safe cleanup from the relocated script.
- The Phase 4 campaign is the skill integration test: baseline vs with-skill pressure runs against the merged skill, plus live trigger runs through `opencode run` against the real skill-loading path.
- The Phase 5 clean-context review is the coherence audit across all three merged files.

### Manual Testing Steps:
1. Read the merged `SKILL.md` and `references/trigger-testing.md` end to end after Phase 1, checking the partition of content against the campaign-only categories in the Decisions table.
2. Confirm the Phase 2 `git status` rename records and read the smoke-run output.
3. Enumerate `skills/` after Phase 3 and confirm `trigger-testing` is gone.
4. Read every Phase 4 campaign output manually (void runs and silent permission rejections are only catchable this way).
5. Read the Phase 5 reviewer report and confirm each finding is either absent or remediated.

## Final Verification

```
.venv/bin/agentskills validate skills/writing-skills
test -f skills/writing-skills/references/trigger-testing.md
test -f skills/writing-skills/references/pressure-testing.md
test -f skills/writing-skills/scripts/trigger-test.sh
test -f skills/writing-skills/scripts/test-trigger-test.sh
test -f agents/trigger-evaluator.md
test -f skills/writing-skills/test-campaigns/2026-08-05-01-writing-skills.md
test ! -d skills/trigger-testing
grep -rn 'the `trigger-testing` skill\|skills/trigger-testing' skills/writing-skills/SKILL.md skills/writing-skills/references/ ; test $? -eq 1
.venv/bin/python -m json.tool skills/writing-skills/trigger-evals/train.json > /dev/null
.venv/bin/python -m json.tool skills/writing-skills/trigger-evals/validation.json > /dev/null
bash skills/writing-skills/scripts/test-trigger-test.sh
```

## References

- PRD: `PRDS/2026-08-05-merge-trigger-testing-into-writing-skills.md`
- Context bundle: `RESEARCH/2026-08-05-merge-trigger-testing-into-writing-skills-context-bundle.md`
- Research findings: `RESEARCH/2026-08-05-merge-trigger-testing-into-writing-skills-research-findings.md`
- Precedent plan: `PLANS/2026-08-05-merge-pressure-testing-into-writing-skills-plan.md`
- Key implementation files: `skills/writing-skills/SKILL.md:1-208`, `skills/trigger-testing/SKILL.md:1-253`, `skills/trigger-testing/scripts/trigger-test.sh:67,70,91,270,305`, `skills/trigger-testing/scripts/test-trigger-test.sh:3,26`, `agents/trigger-evaluator.md:1-31`, `skills/writing-skills/trigger-evals/train.json`, `skills/writing-skills/trigger-evals/validation.json`
- Routing-history evidence: `skills/writing-skills/test-campaigns/2026-08-05-writing-skills.md:84-94`
