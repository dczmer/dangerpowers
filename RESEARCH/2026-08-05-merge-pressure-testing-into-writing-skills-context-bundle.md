---
artifact: context-bundle
date: 2026-08-05
git_commit: 94a7a06099b91b9d8f8291a41a826b76ef45765a
branch: dev/sloptime
request: "write a plan based on this prd @/home/dave/source/dangerpowers/PRDS/2026-08-05-merge-pressure-testing-into-writing-skills.md"
source_research: RESEARCH/2026-08-05-merge-pressure-testing-into-writing-skills-research-findings.md
source_prd: PRDS/2026-08-05-merge-pressure-testing-into-writing-skills.md
status: complete
---

# Context Bundle

## 1. Goal

Merge the `writing-skills` and `pressure-testing` skills into a single skill named `writing-skills`, per the approved PRD (FR-001 through FR-012 at `PRDS/2026-08-05-merge-pressure-testing-into-writing-skills.md:54-67`):

- **Goals (PRD §2, `PRDS/2026-08-05-merge-pressure-testing-into-writing-skills.md:25-29`):** one skill covering authoring + pressure-testing with no duplication, orphaned instructions, or inconsistency; campaign-execution content in an on-demand reference file (`references/pressure-testing.md`, FR-002 `:57`); pressure-test requests trigger the merged skill without naming a second skill; verified by a pressure-test campaign against the merged skill plus a clean-context review.
- **In scope (PRD §5, `:71-75`):** merging both skills per FR-001–FR-009; deleting the `pressure-testing` skill directory and all its contents; the verification campaign (FR-010) and clean-context review (FR-011); opt-in end-of-flow prompts for pressure testing and trigger eval (FR-004/FR-005).
- **Out of scope (PRD §5, `:76-80`):** any change to `trigger-testing`'s content or structure; merging `trigger-testing`; migrating/preserving `pressure-testing`'s campaign logs and eval sets; changes to any other skill, agent, or tooling. References to the old `pressure-testing` skill in other skills' files are explicitly out of scope (PRD §7, `:96`).

## 2. Files Retrieved

- `skills/writing-skills/SKILL.md` (1-190) — the surviving skill's definition; handoff sections at `:138-152` and checklist at `:181-190` are what FR-004/FR-005 change; content sections at `:72-119` are the ones `pressure-testing` duplicates/cross-references
- `skills/pressure-testing/SKILL.md` (1-223) — the skill being merged in and then deleted; its entire body is the source material for the new `references/pressure-testing.md` (rewritten, not moved verbatim, per FR-009 `PRDS/2026-08-05-merge-pressure-testing-into-writing-skills.md:64`)
- `PRDS/2026-08-05-merge-pressure-testing-into-writing-skills.md` (full) — approved requirements FR-001–FR-012, edge cases §7, success criteria §8
- `RESEARCH/2026-08-05-merge-pressure-testing-into-writing-skills-research-findings.md` (full) — file map, 8 duplication/cross-reference pairs, repo patterns, git history of the original 2026-07-30 split
- `skills/writing-skills/trigger-evals/train.json` / `validation.json` — existing eval sets for the writing-skills description; one train entry is `"create a new skill called pressure-testing"` (`skills/writing-skills/trigger-evals/train.json` line 7); no pressure-test trigger queries exist in either file
- `agents/eval-reader.md` (1-38) — read-only agent the campaign protocol dispatches (`skills/pressure-testing/SKILL.md:100-107`)
- `skills/scouting-context/references/bundle-template.md` — template for this artifact
- `AGENTS.md:9-10` — symlink rule: `.opencode/skills` is a symlink to `skills/`; commit real files only
- `skills/trigger-testing/SKILL.md:36`, `:214` — the two "pressure testing" mentions inside trigger-testing (out of scope but adjacent)

## 3. Entry / Exit Points

- **Entry:** `skills/writing-skills/SKILL.md:3` — frontmatter `description` trigger (FR-006 requires updating it so pressure-test requests trigger the merged skill; must not copy pressure-testing's description text per FR-006 `PRDS/2026-08-05-merge-pressure-testing-into-writing-skills.md:61`)
- **Entry:** `skills/pressure-testing/SKILL.md:3` — current pressure-test trigger description; this entry point disappears when the directory is deleted (FR-008)
- **Entry:** `skills/writing-skills/SKILL.md:14-17` — Placement decision precedes all authoring
- **Exit:** `skills/writing-skills/SKILL.md:144` and `:152` — current end-of-flow: unconditional direction to run `pressure-testing`/`trigger-testing` manually, "Never begin any campaign step as part of authoring"; FR-004/FR-005 (`PRDS/...:59-60`) replace this with opt-in prompts, and FR-007 (`:62`) requires a direct jump to campaign instructions when invoked to pressure-test an existing skill
- **Exit:** `skills/pressure-testing/SKILL.md:221-223` — Standalone Boundary; campaign ends when logs are written, no chaining
- **Early exit:** `skills/pressure-testing/SKILL.md:16`, `:35` — no violable rule → pressure testing does not apply (PRD §7 `:93` requires this scope rule to survive the merge)
- **Early exit:** `skills/pressure-testing/SKILL.md:18` — baseline shows no failure → stop

## 4. Key Code

### Current writing-skills frontmatter (to be edited per FR-006)
- **Location:** `skills/writing-skills/SKILL.md:1-4`
- **Code:**
  ```yaml
  ---
  name: writing-skills
  description: Use when creating new skills, editing existing skills, or reviewing a skill before deploying it to this repo's skills/ directory. Triggers include "write a new skill", "create skill", "edit skill", "review skill", "update skill", "writing skills".
  ---
  ```

### Description YAML safety contract (any new description must satisfy)
- **Location:** `skills/writing-skills/SKILL.md:65-70`
- **Code:**
  ```markdown
  - **Colon-in-scalar:** a plain scalar cannot contain `key: value` (a colon followed by a space). ... Weave keywords into prose instead. If a list-like term is genuinely unavoidable, switch to a YAML block scalar (`description: >`) — but plain prose is preferred.
  - **Length:** hard limit 1024 chars.

  Always run `agentskills validate skills/<name>` before finishing; it must print `Valid skill`.
  ```

### Current unconditional handoff (what FR-004/FR-005 replace)
- **Location:** `skills/writing-skills/SKILL.md:144`
- **Code:**
  ```markdown
  **Testing is part of the skill-creation process, but the agent does not run it.** Tell the user the skill must be pressure-tested and direct them to run the `pressure-testing` skill manually to complete the process. Never begin any campaign step as part of authoring.
  ```

### Named cross-reference into writing-skills (must be resolved in merge, FR-009)
- **Location:** `skills/pressure-testing/SKILL.md:140`
- **Code:**
  ```markdown
  Which counter form to use depends on the failure type — follow "Match the Form to the Failure" in the writing-skills skill. Prohibitions only for discipline failures; wrong-shaped output gets a recipe, not a "don't" list.
  ```

### Skill directory structure convention (the new reference file must fit)
- **Location:** `skills/writing-skills/SKILL.md:123-132`
- **Code:**
  ```markdown
  skills/
    skill-name/
      SKILL.md              # Required. Overview + workflow.
      references/           # Heavy reference (100+ lines), loaded on demand
        some-topic.md
      scripts/              # Reusable tools
  ```
  `:132` — "Keep principles, patterns, and short code inline. Move heavy reference to `references/` and reusable tools to `scripts/`, referenced one level deep from SKILL.md."

### Opt-in gate pattern (existing repo convention for FR-004/FR-005 prompts)
- **Location:** `skills/project-bootstrap-nix/SKILL.md:52-53`
- **Code:**
  ```markdown
  3. Interview the user for optional extras using the `question` tool. Ask each question below and act on the answers:
  - **Create a default opencode config?** Ask using the `question` tool (Yes/No). If yes, create `.opencode/opencode.jsonc` with these contents:
  ```
  Each optional follow-on is its own Yes/No question; "no" ends the flow without the extra (also `skills/prd-to-plan/SKILL.md:35`, `skills/iterating-plans/SKILL.md:78`).

### Campaign results-log template (lives in the content to be moved)
- **Location:** `skills/pressure-testing/SKILL.md:195-219` — naming `test-campaigns/YYYY-MM-DD-<skill-name>.md`, same-day `-NN-` sequence; `:197` — the campaign log is the ONLY place test status lives; template at `:199-219`.

## 5. References & Usages

### `writing-skills` (skill)
- **Definition:** `skills/writing-skills/SKILL.md:2`
- **Call sites / dependents:** `skills/pressure-testing/SKILL.md:140` (named cross-reference to "Match the Form to the Failure"); `skills/writing-skills/trigger-evals/train.json` (trigger queries); `skills/trigger-testing/SKILL.md:36` (references "the writing-skills skill's Testing Discipline Skills section" by name); `README.md`/`NOTES.md` mentions (documentation, out of scope)

### `pressure-testing` (skill)
- **Definition:** `skills/pressure-testing/SKILL.md:2`
- **Call sites / dependents:** `skills/writing-skills/SKILL.md:144`, `:182` (in-scope handoff directions to fix); `skills/writing-skills/test-campaigns/2026-08-04-writing-skills-trigger.md` and `skills/writing-skills/trigger-evals/train.json` (in-scope files containing the name); `skills/trigger-testing/SKILL.md` (`:36`, `:214` — out of scope per PRD §7); `agents/eval-reader.md:3`, `:13` (describes itself as a "pressure testing" agent — generic phrase, not a skill reference); `README.md`, `NOTES.md`, 10 `PLANS/` files, 3 `PRDS/` files, 4 `RESEARCH/` files (docs/history, out of scope); `AGENTS.md` has no match (`RESEARCH/...:63`)

### "Match the Form to the Failure" (section)
- **Definition:** `skills/writing-skills/SKILL.md:72-86`
- **Call sites / dependents:** `skills/pressure-testing/SKILL.md:140` (only caller)

### `eval-reader` (agent)
- **Definition:** `agents/eval-reader.md:1-8` (mode: primary; edit/bash/question denied)
- **Call sites / dependents:** `skills/pressure-testing/SKILL.md:100-107` (with-skill run evaluation); the merged reference file's execution protocol must keep pointing at this agent or the campaign flow breaks

### Blast Radius
- **Likely to change:** `skills/writing-skills/SKILL.md` — all merge edits land here (description FR-006, branch FR-007, end-of-flow prompts FR-004/005, cross-reference fixes FR-009)
- **Likely to change:** `skills/writing-skills/references/pressure-testing.md` — new file receiving rewritten campaign content (FR-002); the directory currently has no `references/` (`RESEARCH/...:51`)
- **Likely to change:** `skills/writing-skills/trigger-evals/train.json` / `validation.json` — FR-006 changes the description; existing sets contain no pressure-test trigger queries (`skills/writing-skills/trigger-evals/train.json` lines 1-9; whether they must be updated is a planning decision, PRD states no separate trigger-eval campaign is required — `PRDS/...:87`)
- **Likely to be deleted:** `skills/pressure-testing/` — entire directory, 6 files (`RESEARCH/...:52`), per FR-008
- **Must not break:** `agents/eval-reader.md` — consumer expectation: the campaign protocol at `skills/pressure-testing/SKILL.md:100-107` depends on it; the moved reference must keep a valid pointer
- **Must not break:** `skills/writing-skills/SKILL.md:72-119` — "Match the Form to the Failure" and "Bulletproofing Discipline Skills" are the authoring guidance the campaign content duplicates; FR-012 (`PRDS/...:67`) forbids duplicated/contradictory guidance between main file and reference file
- **Transitive dependents worth attention:** `skills/trigger-testing/SKILL.md:36` — names writing-skills' "Testing Discipline Skills" section; `:214` — references discipline pressure-test campaign log naming. Both out of scope per PRD §7 (`PRDS/...:96`), but a section rename in the merged skill would make `:36` stale
- **Symlink surface:** `.opencode/skills` is a symlink to `skills/` (`AGENTS.md:9`); deletion/addition of real directories propagates automatically; the symlinks themselves must never be committed

## 6. Patterns & Idioms

### Pattern: on-demand reference file loaded from a workflow step
- **Location:** `skills/researching-codebase/SKILL.md:82`, `skills/scouting-context/SKILL.md:64`, `skills/writing-plans/SKILL.md:64`, `skills/writing-prds/SKILL.md:49`, `skills/executing-plans/SKILL.md:96`
- **Snippet (researching-codebase):**
  ```markdown
  5. Write the artifact per `references/findings-template.md`. Location: `RESEARCH/YYYY-MM-DD-<kebab-description>-research-findings.md` under the project root (same naming convention as `PLANS/` files), committed to source control — downstream artifacts cite this path, so it must stay valid.
  ```
- **Key aspects:** no standalone "load on demand" section; the reference is named inline in the workflow step that uses it; paths relative to the skill's own directory. Convention defined at `skills/writing-skills/SKILL.md:127` ("references/ # Heavy reference (100+ lines), loaded on demand") and `:132` (one level deep).
- **Variation:** `skills/writing-quick-plans/SKILL.md:25` references another skill's reference file via cross-skill relative path (`writing-plans/references/plan-template.md`).

### Pattern: conditional workflow branching on invocation reason
- **Location:** `skills/writing-prds/SKILL.md:47`, `skills/executing-plans/SKILL.md:22`, `skills/pressure-testing/SKILL.md:14-16`, `skills/trigger-testing/SKILL.md:14`, `skills/plan-to-execution/SKILL.md:21-24`
- **Snippet (pressure-testing):**
  ```markdown
  Input: one target skill name, or a list of target skills.
  1. Read the target skill's `SKILL.md` fully. Check Scope — if the skill has no violable rule, pressure testing does not apply; say so and move on.
  ```
- **Key aspects:** branch stated at the first workflow step; each branch names its condition and procedure; missing-input branches stop or ask. FR-007 (`PRDS/...:62`) requires a branch on "invoked to pressure-test an existing skill" that jumps to the reference file after reading the main file.

### Pattern: opt-in user gate via the question tool
- **Location:** `skills/project-bootstrap-nix/SKILL.md:52-53`, `skills/prd-to-plan/SKILL.md:35`, `skills/iterating-plans/SKILL.md:78`
- **Key aspects:** each optional follow-on is its own Yes/No question via the `question` tool; "no" continues or ends the flow cleanly. FR-004/FR-005 require two such prompts (pressure testing, trigger eval) at the end of the authoring flow.

### Pattern: frontmatter shape
- **Location:** every SKILL.md in the repo (15 files), e.g. `skills/writing-skills/SKILL.md:1-4`
- **Key aspects:** exactly two fields, `name` and `description`, in all 15 skills (`RESEARCH/...:160`).

### Conflicting Variations
- **Variation A (current state):** `skills/writing-skills/SKILL.md:144`, `:152`, `:182`, `:188` — end-of-flow is an unconditional direction to run `pressure-testing`/`trigger-testing` manually; "Never begin any campaign step as part of authoring" (`:144`).
- **Variation B (required state):** `PRDS/2026-08-05-merge-pressure-testing-into-writing-skills.md:59-62` — FR-004/FR-005 make both prompts opt-in via question tool; FR-007 requires jumping directly into the campaign when invoked to pressure-test an existing skill.
- **Conflict:** the current "the agent does not run it / never begin any campaign step" stance (`skills/writing-skills/SKILL.md:144`, `:185`, `:190`) directly contradicts the PRD's direct-jump requirement (FR-007); the merged skill must reconcile authoring-time opt-in with invocation-reason branching, and the PRD does not say whether the "never begin any campaign step" language survives in any form.

### Duplication / cross-reference pairs the merge must resolve (FR-009, FR-012)
- Baseline-first principle: `skills/pressure-testing/SKILL.md:8`, `:114` ↔ `skills/writing-skills/SKILL.md:12`
- RED-GREEN-REFACTOR: `skills/pressure-testing/SKILL.md:37-43` ↔ `skills/writing-skills/SKILL.md:140-142`
- Rationalization counters: `skills/pressure-testing/SKILL.md:133-138` ↔ `skills/writing-skills/SKILL.md:105-117`
- Spirit-vs-letter: `skills/pressure-testing/SKILL.md:153` ↔ `skills/writing-skills/SKILL.md:101-104`
- No test status in SKILL.md: `skills/pressure-testing/SKILL.md:197` ↔ `skills/writing-skills/SKILL.md:183-184`
- Untested-content prohibition: `skills/pressure-testing/SKILL.md:45` ↔ `skills/writing-skills/SKILL.md:12`, `:142`

## 7. Testing

- **How similar code is tested:** skills are verified by pressure-test campaigns whose logs follow the template at `skills/pressure-testing/SKILL.md:199-219`; example: `skills/writing-plans/test-campaigns/2026-07-29-writing-plans.md` (headers `# Test Campaign: <name> — <date>`, `## Scenario N`, `### Baseline (no skill) — 5 runs`, `### With skill — 5 runs`, `### New rationalizations found`, `### Verdict`). FR-010 requires such a campaign against the merged `writing-skills` itself, including verification that it triggers on phrases like "pressure test the test-skill skill" (`PRDS/...:65`); SC-004 requires the log to exist (`PRDS/...:103`).
- **Clean-context review:** FR-011 (`PRDS/...:66`) requires a subagent with clean context to review the merged skill; SC-003/SC-005 (`PRDS/...:102,104`) define what it confirms.
- **Tests covering affected code:** none found — no automated test suite for skill content; `pyproject.toml:1-12` declares only `ruff` and `skills-ref` dependencies; no `.github/` CI, no `Makefile`, no `package.json` scripts at repo root.
- **Validation commands:**
  - `agentskills validate skills/<name>` must print `Valid skill` — cited at `skills/writing-skills/SKILL.md:70`, `:167`, `:179`; binary confirmed present at `.venv/bin/agentskills` (provides `validate`, `read-properties`, `to-prompt` subcommands; the venv comes from the `uv`/`skills-ref` toolchain in `pyproject.toml:9-12` and is auto-provisioned by the `flake.nix` devShell `shellHook`)
  - Git history check for the original split: commits `634fb99`, `6163c31` (`RESEARCH/...:193-195`); `6163c31` shows the precedent of deleting a `skills/writing-skills/references/pressure-testing.md` (-198 lines) — i.e. this exact reference-file path existed before the 2026-07-30 split and was deleted by it

## 8. Constraints & Risks

- **Invariants the plan must respect:**
  - Frontmatter is exactly `name` + `description`, plain prose preferred, no colon-space in plain scalar, ≤1024 chars (`skills/writing-skills/SKILL.md:65-68`); all 15 skills follow this (`RESEARCH/...:160`)
  - FR-003: campaign-execution-only instructions must not appear in the merged main file (`PRDS/...:58`) — enumerated as: scenario design, execution protocol, rationalization plugging, results logging, multi-skill campaigns, done criteria (`PRDS/...:27`)
  - FR-002 names the reference file exactly: `references/pressure-testing.md` within the skill directory (`PRDS/...:57`); convention requires one level deep from SKILL.md (`skills/writing-skills/SKILL.md:132`)
  - Scope rule must survive: pure-reference skills are not pressure-testable (`skills/pressure-testing/SKILL.md:31-35`; PRD §7 `:93`)
  - Missing-target edge case: campaign flow must surface a nonexistent target skill rather than inventing one (PRD §7 `:95`)
  - The campaign log is the only place test status lives; SKILL.md must never reference `test-campaigns/` (`skills/pressure-testing/SKILL.md:197`, `skills/writing-skills/SKILL.md:184`)
  - FR-006: new trigger phrases must be added but pressure-testing's description text (`skills/pressure-testing/SKILL.md:3`) must not be copied (`PRDS/...:61`)
  - `.opencode/skills` symlink rule (`AGENTS.md:9`) — operate on real files under `skills/` only
- **Dependencies / ordering:**
  - The reference file content depends on the duplication-resolution decisions (which of the 8 pairs above lives in main vs reference) — FR-009 requires rewriting, not verbatim move (`PRDS/...:64`)
  - FR-010's verification campaign can only run after the merged skill exists; the campaign verifies triggering on the new phrases, so the description change (FR-006) precedes it
  - FR-011's clean-context review follows the completed merge (SC-005 `PRDS/...:104`)
  - Deletion of `skills/pressure-testing/` (FR-008) removes the repo's only copy of campaign methodology; any content dropped during the rewrite is unrecoverable except via git history
- **Likely failure modes (evidence-backed):**
  - Headless permission auto-rejection fails silently in campaign runs; only manual output reading catches void runs (`skills/pressure-testing/SKILL.md:174`, `:116`) — affects the FR-010 verification campaign
  - Baseline cwd check: baselines must run outside the repo or `AGENTS.md` auto-loads (`skills/pressure-testing/SKILL.md:175`)
  - With-skill cwd asymmetry: with-skill reps load repo AGENTS.md, a second reinforcement channel to note in logs (`skills/pressure-testing/SKILL.md:176`)
  - Same-day campaign log collisions require `-NN-` sequence numbers (`skills/pressure-testing/SKILL.md:195`)
  - Colon-in-scalar YAML pitfall invalidated 11 skills in this repo previously (`skills/writing-skills/SKILL.md:67`) — the FR-006 description edit touches exactly this surface
- **Conflicting findings:**
  - Current writing-skills forbids the agent from performing any campaign step during authoring (`skills/writing-skills/SKILL.md:144`, `:185`, `:190`); FR-007 requires jumping directly into the campaign when invoked to pressure-test (`PRDS/...:62`). Both cited in §6 Conflicting Variations; the boundary between "authoring flow" and "pressure-test invocation" is undefined in the PRD beyond FR-007's "after reading the entirety of the merged skill's main file for context."
  - `skills/trigger-testing/SKILL.md:36` names writing-skills' "Testing Discipline Skills" section as the authority for the pure-reference exemption; the PRD requires that section's content to survive (scope rule, §7 `:93`) but forbids touching trigger-testing (`:77`). Whether the merged skill keeps a section by that name is a planning decision with a stale-reference hazard either way.

## 9. Open Questions

None. Both research Known Gaps were resolved by targeted reads: `skills/trigger-testing/SKILL.md`'s two pressure-testing mentions are at `:36` and `:214` (recorded in §5/§8, out of scope per PRD §7); the `writing-skills` trigger-eval files were sampled (`skills/writing-skills/trigger-evals/train.json` lines 1-9, `validation.json` lines 1-6) — no pressure-test trigger queries exist, and the PRD explicitly states no separate trigger-eval campaign is required (`PRDS/...:87`), leaving eval-set updates a planning decision, not an open question.

## 10. Start Here

- **Start:** `skills/writing-skills/SKILL.md` — it is the surviving skill, the target of FR-003/004/005/006/007/009 edits, and it already contains the authoring-side half of every duplication pair (§6). A planner must first decide, section by section, what stays in this main file versus what moves to `references/pressure-testing.md` (FR-003's six enumerated categories vs the current `:138-152` handoff sections and `:181-190` checklist); every other artifact (new reference file, deletion, campaign, review) follows from that partition.
