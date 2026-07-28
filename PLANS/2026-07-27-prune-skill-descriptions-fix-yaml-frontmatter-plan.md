---
artifact: implementation-plan
date: 2026-07-27
git_commit: fd2a8ee01eebcf128f01360b2590ca12b8b7be46
branch: master
request: "The skills in the skills/ directory have long, overly detailed descriptions with too much information. They also contain invalid 'mappings' ('Keywords: ...') that are not allowed in YAML front-matter. Analyze each skill description and the agentskills.io spec/best-practices/optimizing/evaluating docs. Present a quick plan to prune these descriptions and fix the invalid front-matter, and how to update the writing-skills skill to avoid producing invalid front-matter and follow best practices, optimize triggering. Current keyword definitions are relevant to trigger advice from agentskills.io."
source_prd: none
source_bundle: none (quick pass)
source_research: none (quick pass)
status: approved
---

# Prune Skill Descriptions, Fix YAML Frontmatter, Update writing-skills Guidance

> **For the implementing agent:** This plan has two phases. Phase 1 rewrites 12 skill `description:` frontmatter lines (verbatim strings below — paste each as the single `description:` line). Phase 2 edits the `writing-skills` body guidance. The phases are file-disjoint and share a parallel group, so they may run as parallel subagents. After both merge, run Final Verification against the integrated tree; do not stop short of it.

## Context

11 of 13 skills fail `agentskills validate` with `Invalid YAML in frontmatter: mapping values are not allowed here`. Every failing description is a one-line plain YAML scalar ending in `Keywords: a, b, c, ...`; the `: ` (colon-space) is parsed as a nested mapping inside a plain scalar, which YAML forbids. `project-bootstrap-nix` validates but uses the same keyword-list style (`Trigger phrases include ...`) and is over-long for the same reasons. Per the agentskills.io spec, the `description` field must be 1–1024 chars and "should describe both what the skill does and when to use it" with "specific keywords that help agents identify relevant tasks" — woven into prose, not appended as a labeled list. Per the optimizing-descriptions guide, descriptions should be imperative ("Use this skill when..."), focus on user intent, be "err on the side of being pushy," and stay concise because every description loads at startup across all skills. The `writing-skills` skill validated but its Frontmatter guidance *produced* the broken pattern: it instructs "describes ONLY when to use — never what the skill does" (contradicts the spec), "third person" (contradicts the imperative-phrasing advice), and "Include keywords an agent would search for" without saying how (authors appended a `Keywords:` list). It also omits the YAML colon-in-scalar pitfall, the 1024-char limit, and any `agentskills validate` step.

## Current State

- `skills/*/SKILL.md` frontmatter `description` fields (13 skills). 11 contain a trailing `Keywords: ...` segment and fail validation; 1 (`project-bootstrap-nix`) validates but uses a `Trigger phrases include ...` list and is over-long; 1 (`writing-skills`) is already concise (129 chars) and valid.
- Validation evidence (`agentskills validate skills/<name>`): 11 print `Invalid YAML in frontmatter` pinpointed at the `Keywords:` token; 2 print `Valid skill`.
- `skills/writing-skills/SKILL.md:45-59` — Frontmatter guidance section that produced the broken pattern.
- `skills/writing-skills/SKILL.md:144-175` — Checklist (Frontmatter + Deployment items) that fails to catch the regression.
- Validation command available and repo-verified: `agentskills validate` (installed at `.venv/bin/agentskills`); `agentskills read-properties` emits JSON with the `description` string (works on valid skills).
- Names of the pipeline are interdependent; descriptions may reference sibling skills by name (e.g., "executing-plans subagent") — keep those references, they aid triggering.

## Desired End State

All 13 skills pass `agentskills validate` ("Valid skill"). Every `description` is a concise imperative paragraph (<1024 chars, most ~250–400) that states what the skill does and when to use it, with trigger keywords woven into natural prose and no `Keywords:`/`Trigger phrases:` label. `writing-skills/SKILL.md` guidance aligns with the agentskills.io spec and includes a YAML-safety rule, a `validate` step in the checklist, and a concise-description rule, so future skill edits do not reintroduce the bug.

## What We're NOT Doing

- Not editing skill bodies, references, scripts, or behavior — frontmatter `description` only (plus `writing-skills` body guidance).
- Not adding `compatibility`, `license`, `metadata`, or `allowed-tools` fields.
- Not changing `name` fields (all already valid).
- Not running pressure-test campaigns — this is a metadata/guidance fix, not a discipline-rule change with a failing baseline.

## Decisions

| Conflict / Question | Pick | Rationale |
|---------------------|------|-----------|
| Keep the "tempted to Z" symptom-list style in descriptions? | Keep one highest-value symptom; drop the rest | Optimizing-descriptions: a few sentences to a short paragraph; every token competes at startup. The 1-most-discriminating symptom stays as a trigger; exhaustive enumerations move to the body (where they already largely live). |
| Keep the `Keywords:` list at all? | Remove entirely; weave terms into prose | (1) The `: ` breaks YAML parsing. (2) Spec's "Good example" weaves trigger terms into the sentence. (3) A labeled list re-reads as a keyword dump, not natural intent. Current keyword terms are preserved as embedded prose so the trigger signal is not lost. |
| Spec says "describe what the skill does AND when"; writing-skills says "ONLY when — never what". | Spec wins | auditable against the published specification; the "never what" rule caused descriptions to omit scope that aids matching. Writing-skills guidance is updated to align. |
| writing-skills says "third person"; optimizing guide says imperative "Use when...". | Imperative | The optimizing-descriptions guide explicitly recommends imperative phrasing; "Use when..." is already the dominant opener in this repo, so this codifies existing style. |
| Reclassify project-bootstrap-nix (validates but over-long / keyword-list style)? | Prune it too | User asked to prune "long, overly detailed descriptions" — bootstrap qualifies (359 chars, list-style) even though its YAML happens to parse (no `: ` after "Trigger phrases include"). Consistency across all 13. |
| Block-scalar (`description: >`) or plain scalar for the fixed descriptions? | Plain scalar, single line | Plain scalars under 1024 chars with no inner `: ` are simplest and safest; block scalars invite multi-line drift. The YAML-safety rule documents the block-scalar fallback for the rare case it's needed. |

## Implementation Approach

Two edit groups touching disjoint files:

1. **Description rewrites (12 skills)** — each `description:` line replaced one-for-one with the verbatim string below. No other frontmatter field touched. Lines 1–4 of each `SKILL.md` only.
2. **writing-skills body guidance** — Frontmatter section rewritten, a "Description YAML safety" subsection added, and two checklist sections amended. `skills/writing-skills/SKILL.md` only.

Group 1 (Phase 1) and Group 2 (Phase 2) are file-disjoint — Phase 1 touches line 3 of 12 skill files (not writing-skills); Phase 2 touches lines 45–175 of `skills/writing-skills/SKILL.md` only — so they share the `skills-frontmatter` parallel group and may run as parallel subagents. Each phase has its own verification gate; Final Verification runs against the whole integrated tree after both merge.

## Phase 1: Description rewrites

### Overview

Rewrite the `description:` frontmatter line on each of the 12 broken/over-long skills (all except `writing-skills`, whose description is already correct). Each replacement string is given verbatim — paste it as the single `description:` line. The frontmatter fence (`---` lines 1 and 4) and `name:` line are unchanged. No skill body is touched.

**Parallel group:** skills-frontmatter

**Execution:** subagent

### Changes Required

#### A. Description rewrites — `skills/<name>/SKILL.md` (line 3 each)

For each skill below, replace the entire `description:` line (line 3) with the verbatim string shown. The frontmatter fence (`---` lines 1 and 4) and `name:` line are unchanged.

**File**: `skills/executing-plans/SKILL.md`
```yaml
description: Use when an approved implementation plan in PLANS/ is ready to execute, or when dispatched as a subagent to implement a single phase of a plan. Also use when about to edit code outside an assigned phase, deviate from the plan when code doesn't match it, edit the plan file during parallel execution, or report a phase done without verification evidence. Covers plan execution, phase implementation, and implementer-subagent runs.
```

**File**: `skills/isolating-worktrees/SKILL.md`
```yaml
description: Use when starting feature work that needs an isolated checkout, or when setting up workspaces for executing-plans phase executors (especially parallel ones). Use when you need the correct `git worktree add` commands and procedures for linked worktrees under .worktrees/ and branch isolation.
```

**File**: `skills/iterating-plans/SKILL.md`
```yaml
description: Use when a human has reviewed an existing plan in PLANS/ and returns with edits before execution starts, or when time has passed since the plan was approved and the codebase may have drifted. Also use when about to edit a plan from memory, apply feedback without verifying the plan's facts still hold, or treat an edited plan as still approved. Covers updating, revising, and detecting stale file:line references in plans.
```

**File**: `skills/plan-to-execution/SKILL.md`
```yaml
description: Use when an approved implementation plan in PLANS/ is ready to be executed end to end. Orchestrates one executing-plans subagent per phase, runs plan-declared independent phases in parallel inside isolated git worktrees, checkpoints each phase as a commit, resumes interrupted runs, and runs the plan's final test and audit commands. Also use when about to implement a phase inline, reclassify a phase's declared execution mode, run independent phases sequentially, or proceed to review, cleanup, or PR creation before the plan's tests pass.
```

**File**: `skills/prd-to-plan/SKILL.md`
```yaml
description: Use when a PRD exists in PRDS/ and an implementation plan is needed. Drives researching-codebase, scouting-context, and writing-plans from a single invocation, delegating phases to subagents where safe and managing user feedback on the plan until accepted for human review. Also use when about to invoke the pipeline skills manually one by one, reuse a pre-existing artifact without asking, start the pipeline on a draft PRD, or edit a plan directly instead of routing feedback through iterating-plans.
```

**File**: `skills/prompt-shaping/SKILL.md`
```yaml
description: Use when a user's request is vague, underspecified, or incomplete but reasonable assumptions can be made from context. Also use when about to start coding on an ambiguous request without confirming scope, or when a high-level request like "add caching" or "clean this up" leaves boundaries undefined. Covers clarifying unclear intent and scoping assumptions.
```

**File**: `skills/researching-codebase/SKILL.md`
```yaml
description: Use when asked to research, explore, map, or explain how part of a codebase works, find where features live, locate entry points or call sites, or gather code context before planning. Also use when about to answer codebase questions from memory or a single grep, or to flag problems and suggest improvements while researching. Covers "how does X work" exploration without unsolicited improvement notes.
```

**File**: `skills/scouting-context/SKILL.md`
```yaml
description: Use when preparing to plan a code change and needing to compress research findings into a handoff brief — affected files, call sites, blast radius, constraints, risks, validation commands, and where to start. Also use when a research findings document exists and needs to become actionable context, or when about to embed a recommended approach in the handoff, pick one of two competing patterns for the planner, or ship a handoff brief with empty sections. Covers pre-planning context bundles.
```

**File**: `skills/writing-plans/SKILL.md`
```yaml
description: Use when research findings or a context bundle exist and an implementation plan in PLANS/ is needed before changing code. Also use when about to plan with unresolved open questions, write plan steps that say what to do without showing how, leave a pattern conflict unpicked, declare every phase's parallel group none without assessing file-set overlap, pick a side of a team-standard or vendor question on usage counts alone, or edit anything other than the plan file while planning. Covers implementation plans, phases, and plan approval.
```

**File**: `skills/writing-prds/SKILL.md`
```yaml
description: Use when the user explicitly asks for a PRD or product requirements document, asks to start planning a feature, or wants to update or revise an existing PRD. Also use when about to put tech stack or file paths in a requirements doc, make product decisions silently instead of asking, or finalize a PRD with open questions remaining. Covers feature specs, requirements docs, scoping, and acceptance criteria.
```

**File**: `skills/writing-quick-plans/SKILL.md`
```yaml
description: Use when planning a small, well-understood change where full research and context-bundle artifacts would be overkill — simple features, small projects, or a plan needed fast. Also use when about to save research summaries "for provenance" as a notes file or plan appendix, or when a request is too small for the research/scout/plan pipeline but still needs an implementation plan. Covers quick, one-shot, lightweight plans that skip research.
```

**File**: `skills/project-bootstrap-nix/SKILL.md`
```yaml
description: Use when bootstrapping a new project in a fresh git repository. Also use when about to guess a project name from a directory name, use a placeholder name, overwrite an existing flake.nix/.envrc/.gitignore, or run `git add -A` on files you didn't create. Triggers include "bootstrap a new project" or "create a new project called NAME".
```

Note: `skills/writing-skills/SKILL.md` line 3 is already correct — do **not** edit its frontmatter description. Only its body (group B) changes.

### Success Criteria

#### Automated Verification:
- [x] The 12 Phase-1 skills validate: `for n in executing-plans isolating-worktrees iterating-plans plan-to-execution prd-to-plan prompt-shaping researching-codebase scouting-context writing-plans writing-prds writing-quick-plans project-bootstrap-nix; do agentskills validate "skills/$n"; done` — every line prints `Valid skill: ...`
- [x] No Phase-1 description exceeds 1024 chars: `for n in executing-plans isolating-worktrees iterating-plans plan-to-execution prd-to-plan prompt-shaping researching-codebase scouting-context writing-plans writing-prds writing-quick-plans project-bootstrap-nix; do agentskills read-properties "skills/$n" | python3 -c "import json,sys; p=json.load(sys.stdin); d=p['description']; print(p['name'], len(d), 'OK' if len(d)<=1024 else 'OVER')"; done` — every line ends `OK`
- [x] No Phase-1 frontmatter contains a `Keywords:`/`Trigger phrases:` label: `for n in executing-plans isolating-worktrees iterating-plans plan-to-execution prd-to-plan prompt-shaping researching-codebase scouting-context writing-plans writing-prds writing-quick-plans project-bootstrap-nix; do agentskills read-properties "skills/$n" | python3 -c "import json,sys; p=json.load(sys.stdin); assert 'Keywords:' not in p['description'] and 'Trigger phrases:' not in p['description'], p['name']"; done` — exits 0

#### Manual Verification:
- [ ] Spot-check 3 rewritten descriptions read as natural prose (not a keyword dump) and still surface the skill's main trigger.

**Implementation Note**: After completing this phase and all automated verification passes, pause for human confirmation of the manual criteria before proceeding to the next phase.

---

## Phase 2: writing-skills guidance

### Overview

Rewrite the `writing-skills/SKILL.md` body so it stops producing the broken frontmatter pattern: align the Frontmatter section with the agentskills.io spec, add a Description YAML-safety subsection, and amend the checklist. Only `skills/writing-skills/SKILL.md` lines 45–175 are touched; its frontmatter `description:` (line 3) is unchanged.

**Parallel group:** skills-frontmatter

**Execution:** subagent

### Changes Required

#### B. writing-skills guidance — `skills/writing-skills/SKILL.md`

**B1.** Replace the Frontmatter bullet block and its yaml example (`skills/writing-skills/SKILL.md:48-59`):

Old:
```
- `description`: third person, describes ONLY when to use — never what the skill does or how it works.
  - Start with "Use when..." plus concrete triggering conditions and symptoms.
  - **Never summarize the workflow.** A description that summarizes the process becomes a shortcut agents follow instead of reading the skill body. (Tested failure mode in superpowers: a description saying "code review between tasks" caused an agent to do one review when the skill required two.)
  - Include keywords an agent would search for: error messages, symptoms, synonyms, tool names.

```yaml
# Bad: summarizes workflow
description: Use when writing skills — drafts frontmatter, structures the body, runs the checklist

# Good: triggering conditions only
description: Use when creating new skills, editing existing skills, or reviewing a skill before deployment
```
```

New:
```
- `description`: imperative ("Use when..."), describes WHAT the skill does AND WHEN to use it — a few sentences to a short paragraph, ≤1024 chars.
  - Start with "Use when..." plus concrete triggering conditions and symptoms.
  - State what the skill produces (one clause) so the agent can match user intent, not just internal mechanics.
  - **Never summarize the workflow.** A description that summarizes the process becomes a shortcut agents follow instead of reading the skill body. (Tested failure mode in superpowers: a description saying "code review between tasks" caused an agent to do one review when the skill required two.)
  - Keep it concise. Every token competes with all other skills' descriptions at startup. Move exhaustive anti-pattern enumerations into the body; keep only the most discriminating trigger or symptom in the description.
  - Weave trigger terms (error messages, symptoms, synonyms, tool names) into the prose. Never append a `Keywords:` or `Trigger phrases:` label — see Description YAML safety below.

```yaml
# Bad: summarizes workflow
description: Use when writing skills — drafts frontmatter, structures the body, runs the checklist

# Good: what + when, keywords woven
description: Use when creating new skills, editing existing skills, or reviewing a skill before deployment. Covers frontmatter and body structure for skill files.
```
```

**B2.** Insert a new subsection immediately after the yaml example block above (i.e., after `skills/writing-skills/SKILL.md` current line 59, before the `## Match the Form to the Failure` heading at line 61). New content:

```
### Description YAML safety

The `description` is a YAML scalar. Two pitfalls that break parsing (`agentskills validate` fails and the skill will not load):

- **Colon-in-scalar:** a plain scalar cannot contain `key: value` (a colon followed by a space). Appending `Keywords: ...` or `Trigger phrases: ...` inside a one-line plain-scalar description is the exact failure that invalidated 11 skills in this repo. Weave keywords into prose instead. If a list-like term is genuinely unavoidable, switch to a YAML block scalar (`description: >`) — but plain prose is preferred.
- **Length:** hard limit 1024 chars. Long descriptions also bloat every agent run since all descriptions load at startup. Keep to a short paragraph.

Always run `agentskills validate skills/<name>` before finishing; it must print `Valid skill`.
```

**B3.** Replace the Frontmatter checklist items (`skills/writing-skills/SKILL.md:153-156`):

Old:
```
**Frontmatter:**
- [ ] `name` is hyphens/lowercase, gerund or verb-first
- [ ] `description` starts with "Use when...", third person, triggers/symptoms only — no workflow summary
- [ ] Keywords included (error messages, symptoms, synonyms, tools)
```

New:
```
**Frontmatter:**
- [ ] `name` is hyphens/lowercase, gerund or verb-first
- [ ] `description` starts with "Use when...", imperative, states WHAT + WHEN — no workflow summary
- [ ] Trigger terms woven into prose; no `Keywords:`-style label; ≤1024 chars
- [ ] `agentskills validate skills/<name>` prints `Valid skill`
```

**B4.** Amend the Deployment checklist (`skills/writing-skills/SKILL.md:166-167`):

Old:
```
**Deployment:**
- [ ] Placement decided per the Placement rule (prompt > repo direction > `question` tool with `.opencode/skills/` default)
```

New:
```
**Deployment:**
- [ ] Placement decided per the Placement rule (prompt > repo direction > `question` tool with `.opencode/skills/` default)
- [ ] `agentskills validate skills/<name>` passes (`Valid skill`)
```

### Success Criteria

#### Automated Verification:
- [x] writing-skills still validates (frontmatter untouched): `agentskills validate skills/writing-skills` prints `Valid skill: ...`
- [x] writing-skills description unchanged and ≤1024 chars: `agentskills read-properties skills/writing-skills | python3 -c "import json,sys; p=json.load(sys.stdin); assert p['description']=='Use when creating new skills, editing existing skills, or reviewing a skill before deploying it to this repo\'s skills/ directory.' and len(p['description'])<=1024"`

#### Manual Verification:
- [ ] Confirm `skills/writing-skills/SKILL.md` renders coherently — the new "### Description YAML safety" subsection sits between the frontmatter yaml example and "## Match the Form to the Failure".
- [ ] `git diff skills/writing-skills/SKILL.md` shows only the 4 intended edits (B1–B4) plus the inserted subsection; no other body lines changed.

**Implementation Note**: After completing this phase and all automated verification passes, pause for human confirmation of the manual criteria.

## Final Verification

- `for d in skills/*/; do agentskills validate "$d"; done`
- `for d in skills/*/; do agentskills read-properties "$d" | python3 -c "import json,sys; p=json.load(sys.stdin); d=p['description']; print(p['name'], len(d), 'OK' if len(d)<=1024 else 'OVER')"; done`
- `grep -rnE '^[[:space:]]*description:.*Keywords:' skills/ ` (expect: no matches)

## References

- PRD: none
- Context bundle: none (quick pass) — evidence gathered in-session
- Research findings: none (quick pass) — evidence gathered in-session
- Spec & guidance consulted: https://agentskills.io/specification#frontmatter , https://agentskills.io/skill-creation/optimizing-descriptions , https://agentskills.io/skill-creation/best-practices , https://agentskills.io/skill-creation/evaluating-skills
- Key implementation files: `skills/*/SKILL.md:3` (description lines); `skills/writing-skills/SKILL.md:45-59` (Frontmatter guidance), `:144-175` (checklist)