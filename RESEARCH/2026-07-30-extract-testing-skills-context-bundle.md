---
artifact: context-bundle
date: 2026-07-30
git_commit: 5068d47cc65f6f04c56f0cab0e12054b64b91c3d
branch: dev/sloptime
request: turn this prd into a multi-phase plan
source_research: RESEARCH/2026-07-30-extract-testing-skills-research-findings.md
source_prd: PRDS/2026-07-30-extract-testing-skills.md
status: complete
---

# Context Bundle

## 1. Goal

Extract the pressure-testing and trigger-optimization processes out of the `writing-skills` skill into two new standalone, manually invocable skills (`pressure-testing`, `trigger-testing`), and revise `writing-skills` so it retains the testing mandates (Iron Law, Trigger Eval Rule) but never auto-launches campaigns — it directs the user to invoke the new skills manually (`PRDS/2026-07-30-extract-testing-skills.md:43-48`).

- **In scope:** creating `skills/pressure-testing/` and `skills/trigger-testing/`; extracting `skills/writing-skills/references/pressure-testing.md` and `skills/writing-skills/references/trigger-optimizing.md`; revising `skills/writing-skills/SKILL.md` (Testing Discipline Skills section, Trigger Optimization section, testing checklist blocks); single-skill and sequential list-based campaign support in both new skills; description best-practice rules carried by `trigger-testing` from `writing-skills` frontmatter guidance and https://agentskills.io/skill-creation/optimizing-descriptions (`PRDS/2026-07-30-extract-testing-skills.md:96-101`).
- **Out of scope:** self-testing the two new skills; changing testing methodology substance; changing any skill other than `writing-skills` and the two new skills; automating/scheduling campaign execution; deciding where description-writing guidance primarily lives (`PRDS/2026-07-30-extract-testing-skills.md:102-106`).

## 2. Files Retrieved

- `skills/writing-skills/SKILL.md:1-211` — the revision target; contains the two testing mandate sections (`:138-153`, `:155-168`), the two testing checklist blocks (`:197-203`, `:205-211`), and the description best-practice guidance (`:43-70`) that `trigger-testing` must also carry (PRD FR-007).
- `skills/writing-skills/references/pressure-testing.md:1-198` — extraction source for the `pressure-testing` skill; full campaign protocol.
- `skills/writing-skills/references/trigger-optimizing.md:1-185` — extraction source for the `trigger-testing` skill; full eval protocol plus the `trigger-evals/` directory convention (`:183-185`).
- `PRDS/2026-07-30-extract-testing-skills.md:41-136` — approved requirements (FR-001..FR-014), edge cases, success criteria; §9 Open Questions is None (`:134-135`).
- `AGENTS.md:9-16` — repo operating rules: commit real files not symlinks (`:9`); AGENTS.md edits require user confirmation; Pressure Test Pollution section references the full path of the file slated for removal (`:13`).
- `agents/eval-reader.md:1-4` — agent definition the with-skill pressure-test protocol dispatches (`skills/writing-skills/references/pressure-testing.md:87-90`).
- `agents/trigger-evaluator.md:1-4` — trigger-evaluation agent; detection pattern matches `skills/writing-skills/references/trigger-optimizing.md:85,88`.
- `pyproject.toml:7-10` — declares `skills-ref>=0.1.1` (`:9`), providing the `agentskills` CLI used by the validation gate.
- `flake.nix:38` — devShell shellHook `which agentskills || $(uv sync && uv python install)`.
- External (fetched to close a research gap): https://agentskills.io/skill-creation/optimizing-descriptions — description-writing principles and eval-design guidance required by PRD FR-007.
- `skills/prompt-shaping/test-campaigns/2026-07-29-01-prompt-shaping.md:1,3,7,14,21,150` — real campaign log exemplar (per-scenario h3 sections, `-01` same-day disambiguated filename).
- `skills/writing-quick-plans/test-campaigns/2026-07-29-writing-quick-plans.md:96-101` — real campaign log exemplar with hoisted h2 verdict sections (format variation).
- `NOTES.md:95,107` — prose mentions of pressure testing; no path references.

## 3. Entry / Exit Points

- **Entry:** `skills/writing-skills/SKILL.md:3` — frontmatter `description` is the routing surface that causes the skill to load; the two new skills will each need an equivalent description (PRD FR-007 assigns description best-practice rules to `trigger-testing`).
- **Entry:** `skills/writing-skills/SKILL.md:153` — `**REQUIRED:**` pointer pulling `references/pressure-testing.md` into every authoring run; this is the auto-load mechanism PRD FR-008/FR-010 removes.
- **Entry:** `skills/writing-skills/SKILL.md:168` — `**REQUIRED:**` pointer pulling `references/trigger-optimizing.md` into every authoring run; removed per PRD FR-009/FR-010.
- **Exit:** `skills/writing-skills/SKILL.md:170-211` — the `## Checklist` ends the skill; its testing items (`:198-200`) currently instruct the agent to *perform* campaign steps (run baselines, re-run with skill, close loopholes), which PRD FR-013 requires rewriting into user-directed manual-testing items.
- **Exit (new skills):** both extracted reference files end on their results-log templates (`skills/writing-skills/references/pressure-testing.md:172-198`, `skills/writing-skills/references/trigger-optimizing.md:151-185`); side effect of a campaign run is a log written to `test-campaigns/` in the target skill's directory (`pressure-testing.md:174`, `trigger-optimizing.md:153`).

## 4. Key Code

### Mandates that must be retained unchanged in force (PRD FR-011)
- **Location:** `skills/writing-skills/SKILL.md:140`, `skills/writing-skills/SKILL.md:157`
- **Code:**
  ```markdown
  **The Iron Law: NO SKILL WITHOUT A FAILING TEST FIRST.**
  ```
  ```markdown
  **The Trigger Eval Rule: NO DESCRIPTION SHIPS WITHOUT A PASSING EVAL SET.**
  ```

### Auto-execution checklist items to be rewritten (PRD FR-013)
- **Location:** `skills/writing-skills/SKILL.md:197-203`
- **Code:**
  ```markdown
  **Testing (discipline skills only):**
  - [ ] Baseline scenarios run WITHOUT the skill; rationalizations documented verbatim (RED)
  - [ ] Scenarios re-run WITH the skill; agent complies and cites the skill (GREEN)
  - [ ] New loopholes closed (rule negation + rationalization row + red flag + description symptom) and re-tested (REFACTOR)
  - [ ] Results log written to `test-campaigns/` in the skill's directory
  - [ ] Any rule shipped untested is recorded as untested in the campaign log — never in SKILL.md
  - [ ] No test status, campaign results, or `test-campaigns/` references in SKILL.md
  ```

### Pressure-test dispatch harness
- **Location:** `skills/writing-skills/references/pressure-testing.md:78-90`
- **Code:**
  ```bash
  opencode run --dir <empty-dir-outside-repo> "<scenario>"
  ```
  ```bash
  opencode run --dir <repo-root> --agent eval-reader "$(cat prepend.txt scenario.txt)"
  ```

### Trigger-eval detection harness
- **Location:** `skills/writing-skills/references/trigger-optimizing.md:80-90`
- **Code:**
  ```bash
  opencode run --dir <repo-root> --format json "<query>" > out.json 2>&1
  ```
  ```bash
  grep '"tool":"skill"' out.json | grep -q '"name":"<candidate-skill>"'
  ```
  Detection must be candidate-specific via `input.name`; a sibling skill firing is a FAIL (`trigger-optimizing.md:90`).

### `trigger-evals/` file schema
- **Location:** `skills/writing-skills/references/trigger-optimizing.md:183-185`
- **Code:**
  ```json
  [{"query": "<str>", "should_trigger": true}]
  ```
  Files: `train.json`, `validation.json`, post-selection `YYYY-MM-DD-fresh.json`; committed to source control; never referenced from `SKILL.md`.

### Description best-practice rules (PRD FR-007 sources)
- **Location:** `skills/writing-skills/SKILL.md:48-53` — imperative "Use when...", WHAT + WHEN, never summarize the workflow, concise, trigger terms woven into prose, no `Keywords:` label.
- **Location:** `skills/writing-skills/SKILL.md:63-68` — YAML safety: colon-in-scalar pitfall invalidates parsing; 1024-char hard limit.
- **Location:** https://agentskills.io/skill-creation/optimizing-descriptions — imperative phrasing; user intent over implementation; "err on the side of being pushy" (list contexts including when the user doesn't name the domain); concise (few sentences to a short paragraph, ≤1024 chars); ~20 eval queries (8-10 should-trigger, 8-10 should-not); near-miss negatives; 3 runs per query with 0.5 trigger-rate threshold; ~60/40 train/validation split, fixed across iterations; select best iteration by validation pass rate; fresh-query sanity check.

### Campaign log template
- **Location:** `skills/writing-skills/references/pressure-testing.md:178-198`
- **Code:**
  ```markdown
  # Test Campaign: <skill-name> — <date>

  ## Scenario 1: <name>
  **Pressures:** <list>
  **Correct answer:** <option>

  ### Baseline (no skill) — N runs
  - Run 1: chose <X>. Rationalization: "<verbatim>"

  ### With skill — N runs
  - Run 1: chose <X>. Cited: "<section>". Notes: ...

  ### New rationalizations found
  - "<verbatim>" → counter added: <where>

  ### Verdict
  <bulletproof | outstanding loopholes: ...>
  ```

## 5. References & Usages

### `skills/writing-skills/references/pressure-testing.md`
- **Definition:** `skills/writing-skills/references/pressure-testing.md:1`
- **Call sites / dependents:** `skills/writing-skills/SKILL.md:153` (REQUIRED load instruction); `AGENTS.md:13` (full-path reference); `skills/writing-skills/references/trigger-optimizing.md:92` (sibling bash-pattern citation); `skills/writing-skills/references/trigger-optimizing.md:153` (sibling log-format citation); `agents/eval-reader.md:1-4` (agent the protocol dispatches, referenced at `pressure-testing.md:87-90`)

### `skills/writing-skills/references/trigger-optimizing.md`
- **Definition:** `skills/writing-skills/references/trigger-optimizing.md:1`
- **Call sites / dependents:** `skills/writing-skills/SKILL.md:168` (REQUIRED load instruction); `agents/trigger-evaluator.md:32,37` (detection pattern matches `trigger-optimizing.md:85,88`); no other repo references found

### `## Testing Discipline Skills` / `## Trigger Optimization` (writing-skills sections)
- **Definition:** `skills/writing-skills/SKILL.md:138-153`, `skills/writing-skills/SKILL.md:155-168`
- **Call sites / dependents:** checklist blocks at `skills/writing-skills/SKILL.md:197-203` and `:205-211`; `skills/writing-skills/references/trigger-optimizing.md:12` (cites the `SKILL.md:138–149` line range); `trigger-optimizing.md:181` (extends the `SKILL.md:151` rule)

### `agentskills validate`
- **Definition:** `.venv/bin/agentskills` (console script from `skills-ref`, `pyproject.toml:9`)
- **Call sites / dependents:** `skills/writing-skills/SKILL.md:65`, `:70`, `:183`, `:195`

### Blast Radius
- **Likely to change:** `skills/writing-skills/SKILL.md` — sections `:138-168` and checklist `:197-211` revised per PRD FR-010..FR-013; `skills/writing-skills/references/pressure-testing.md` — removed per FR-008; `skills/writing-skills/references/trigger-optimizing.md` — removed per FR-009; `skills/pressure-testing/` and `skills/trigger-testing/` — created per FR-001/FR-004; `AGENTS.md:13` — holds a full path into the file being removed.
- **Must not break:** `agents/eval-reader.md` — consumed by the extracted protocol (`pressure-testing.md:87-90`); `agents/trigger-evaluator.md` — detection pattern paralleled at `trigger-optimizing.md:85,88`; the 11 other skills in `skills/` — PRD non-goal forbids changing them (`PRDS/2026-07-30-extract-testing-skills.md:52`); `.opencode/skills/dangerpowers` and `.opencode/agents/dangerpowers` symlinks — commit real files only (`AGENTS.md:9`).
- **Transitive dependents worth attention:** `AGENTS.md:13` — dangling full-path reference after removal, and AGENTS.md edits require user confirmation per the repo's operational rules; `NOTES.md:95,107` — prose-only mentions, no dangling path.

## 6. Patterns & Idioms

### Pattern: standalone skill anatomy
- **Location:** `skills/researching-codebase/SKILL.md:1-4,82,97-99`
- **Snippet:**
  ```markdown
  ---
  name: researching-codebase
  description: Use when asked to research, explore, map, or explain how part of a codebase works, find where features live, locate entry points or call sites, or gather code context before planning. Also use when about to answer codebase questions from memory or a single grep, or to flag problems and suggest improvements while researching. Covers "how does X work" exploration without unsolicited improvement notes.
  ---
  ```
- **Key aspects:** two-field frontmatter; skeleton `# Title`, `## The Iron Rules` (with `### Rationalizations`, `### Red Flags - STOP`), `## Workflow`, checklist, `## Standalone Boundary`. Per PRD FR-001/FR-004 the new skills are authored with this process minus testing campaigns.

### Pattern: SKILL.md ↔ reference reciprocal pointers
- **Location:** `skills/writing-skills/SKILL.md:153`, `skills/writing-skills/references/pressure-testing.md:3`
- **Snippet:**
  ```markdown
  **REQUIRED:** See `references/pressure-testing.md` for scenario design, execution protocol, meta-testing, done criteria, and the results-log format.
  ```
  ```markdown
  **Load this reference when:** creating or editing a discipline-enforcing skill, before deployment.
  ```
- **Key aspects:** after extraction, these pointers are exactly what FR-008..FR-010 eliminate from `writing-skills`; cross-skill by-name reference is the established alternative (`skills/prd-to-plan/SKILL.md:8`, `skills/executing-plans/SKILL.md:20`).

### Pattern: sequential list processing
- **Location:** `skills/plan-to-execution/SKILL.md:45-52,59-63`; variation `skills/writing-skills/references/trigger-optimizing.md:133-137`
- **Key aspects:** iterate the list in order, one item at a time, per-item completion artifacts verified before advancing; the trigger-optimizing variation adds a Final-Verification regression smoke across campaigned skills. PRD FR-003/FR-006 require sequential list support in both new skills.

### Pattern: frontmatter description styles (variations, all in active use)
- **Variation A:** `skills/scouting-context/SKILL.md:3` — "Use when ... Also use when about to ..." violation-symptom triggers; evidence: also used in writing-plans, writing-quick-plans.
- **Variation B:** `skills/prompt-shaping/SKILL.md:3` — adds a "Does not apply when..." boundary clause.
- **Variation C:** `skills/project-bootstrap-nix/SKILL.md:3`, `skills/writing-skills/SKILL.md:3` — append `Triggers include "..."` quoted-phrase lists.
- **Conflict:** no conflict; all three satisfy the `writing-skills` description rules (`skills/writing-skills/SKILL.md:48-53`).

### Conflicting Variations: eval-set size and iteration budget
- **Variation A (repo):** `skills/writing-skills/references/trigger-optimizing.md:17` — "Build **≤5 should-trigger** and **≤5 should-not** queries (≤10 total)"; `trigger-optimizing.md:53-64` — "≤3 iterations" plus at most one train-expansion re-opt.
- **Variation B (external):** https://agentskills.io/skill-creation/optimizing-descriptions — "Aim for about 20 queries: 8-10 that should trigger and 8-10 that shouldn't"; "Five iterations is usually enough."
- **Conflict:** the repo's eval-set cap (≤10 queries) and iteration cap (≤3) disagree with the external guidance (~20 queries, ~5 iterations) that PRD FR-007 requires `trigger-testing` to incorporate. The repo file already notes its loop is "in spirit from agentskills.io" (`trigger-optimizing.md:55`). Which numbers the new skill carries is a planner decision; both sources are cited here.

### Conflicting Variations: campaign log section structure
- **Variation A:** `skills/writing-skills/references/pressure-testing.md:178-198` — per-scenario `### Baseline` / `### With skill` / `### Verdict` under h2 scenario headers; matches `skills/prompt-shaping/test-campaigns/2026-07-29-01-prompt-shaping.md:7,14,21`.
- **Variation B:** `skills/writing-quick-plans/test-campaigns/2026-07-29-writing-quick-plans.md:96-101` — hoists `## New rationalizations found` and `## Verdict` to h2, variable run counts.
- **Conflict:** template prescribes per-scenario h3 verdicts; one shipped log uses hoisted h2 verdicts. Both exist in the repo today.

### Pattern: boundary declarations
- **Location:** `skills/researching-codebase/SKILL.md:97-99` (dedicated `## Standalone Boundary`), `skills/writing-prds/SKILL.md:52` (boundary as workflow step)
- **Key aspects:** `writing-skills` currently has neither a Boundary nor a Red Flags section; it ends on `## Checklist` (`skills/writing-skills/SKILL.md:170`).

## 7. Testing

- **How similar code is tested:** skills are validated structurally with `agentskills validate skills/<name>`, which must print `Valid skill` (`skills/writing-skills/SKILL.md:70`); behaviorally via the campaign protocols being extracted (out of scope to run per PRD §5, `PRDS/2026-07-30-extract-testing-skills.md:103`). Real campaign logs exist as format exemplars: `skills/prompt-shaping/test-campaigns/2026-07-29-01-prompt-shaping.md:1`, `skills/writing-quick-plans/test-campaigns/2026-07-29-writing-quick-plans.md:96-101`.
- **Tests covering affected code:** none found — `skills/writing-skills/test-campaigns/` exists but is empty; no `trigger-evals/` directory exists anywhere in the repo.
- **Validation commands (verified against the repo):**
  - `agentskills validate skills/<name>` — CLI provided by `skills-ref>=0.1.1` (`pyproject.toml:9`); entry point present at `.venv/bin/agentskills`; installed via `uv sync` in the devShell (`flake.nix:38`). Required to print `Valid skill` per `skills/writing-skills/SKILL.md:70`; PRD SC-006 requires all three skills pass.
  - No Makefile and no `.github/` CI config exist in this repo (verified by directory listing); there are no other repo-defined check commands.

## 8. Constraints & Risks

### Invariants the plan must respect
- Iron Law and Trigger Eval Rule text retained at full force (`skills/writing-skills/SKILL.md:140`, `:157`; PRD FR-011).
- Untested items are recorded in campaign logs only, never in SKILL.md (`skills/writing-skills/SKILL.md:149,151,166`; `skills/writing-skills/references/trigger-optimizing.md:181`).
- Pure-reference skills are exempt from pressure testing (`skills/writing-skills/SKILL.md:149`) but NOT from trigger evals (`skills/writing-skills/references/trigger-optimizing.md:12`) — the asymmetry must survive the rewrite (PRD §7, `PRDS/2026-07-30-extract-testing-skills.md:118`).
- Revised `writing-skills` must contain no dangling references to removed material (PRD §6, `PRDS/2026-07-30-extract-testing-skills.md:114`).
- New skills live under `skills/` in this repo per `AGENTS.md` and PRD §6 (`PRDS/2026-07-30-extract-testing-skills.md:113`); real files committed, never the `.opencode` symlinks (`AGENTS.md:9`).
- Every operational rule removed from `writing-skills` must be accounted for in exactly one new skill or intentionally retained (PRD FR-014, SC-005).
- `agentskills validate` must pass on all three skills (`skills/writing-skills/SKILL.md:70`; PRD SC-006); descriptions ≤1024 chars with no colon-in-plain-scalar (`skills/writing-skills/SKILL.md:63-68`).

### Dependencies / ordering
- The new skills' content derives from the two reference files; `writing-skills` revisions (pointer removal, checklist rewrite) depend on the extraction being complete so no operational rule is stranded (PRD FR-008/FR-009 say "once extracted").
- `AGENTS.md:13` references `skills/writing-skills/references/pressure-testing.md` by full path; removal of that file creates a dangling reference in a file whose edits require user confirmation per the repo's operational rules.

### Likely failure modes
- **Drifting line-number citations:** extracted content cites `writing-skills` SKILL.md by line number — `pressure-testing.md:123` → `SKILL.md` "Match the Form to the Failure"; `trigger-optimizing.md:12` → `SKILL.md:138–149`; `trigger-optimizing.md:74` → `SKILL.md:53`; `trigger-optimizing.md:135` → `SKILL.md:3`; `trigger-optimizing.md:181` → `SKILL.md:151`. Revising SKILL.md shifts those line numbers.
- **Sibling citations becoming cross-skill references:** `trigger-optimizing.md:92` and `:153` cite `pressure-testing.md` by filename; after extraction these point across skill boundaries.
- **Broken bash in the eval-loop skeleton:** `trigger-optimizing.md:98` reads each line into `query` (`while IFS= read -r query`), but `trigger-optimizing.md:99` expands `$row`, which is never assigned in the snippet.
- **Untested directory convention:** the `trigger-evals/` convention (`trigger-optimizing.md:183-185`) has zero in-repo instances; no `trigger-evals/` directory exists anywhere.
- **Auto-launch residue:** auto-execution lives not only in the two `**REQUIRED:**` pointers (`SKILL.md:153,168`) but also in checklist items that instruct the agent to perform campaign steps (`SKILL.md:198-200`); PRD SC-007 checks for any instruction that triggers automatic execution.

### Conflicting findings
- Eval-set size and iteration caps: repo `trigger-optimizing.md:17,53-64` (≤10 queries, ≤3 iterations) vs. external agentskills.io guidance (~20 queries, ~5 iterations) — both cited in §6; the pick belongs to the planner.
- Campaign log structure: template h3-per-scenario (`pressure-testing.md:178-198`) vs. hoisted h2 in a shipped log (`skills/writing-quick-plans/test-campaigns/2026-07-29-writing-quick-plans.md:96-101`) — both cited in §6.

## 9. Open Questions

- `[needs-human]` — `AGENTS.md:13` holds a full path to the reference file being removed; the repo's operational rules require user confirmation before editing AGENTS.md. Should the plan include an AGENTS.md update, and if so, what should the Pressure Test Pollution section point at?
- `[needs-human]` — the `-01` same-day disambiguation variant in campaign log filenames is observed in two files (`skills/prompt-shaping/test-campaigns/2026-07-29-01-prompt-shaping.md:1`) with no defining rule text in either reference file; whether the new skills should document it is a judgment call.
- `[needs-human]` — where description-writing guidance primarily lives when it appears in both `writing-skills` and `trigger-testing` is explicitly declared a planning decision, out of scope for requirements (`PRDS/2026-07-30-extract-testing-skills.md:106,121`); flagged here so the planner does not treat duplication as an error.

## 10. Start Here

- **Start:** `skills/writing-skills/SKILL.md` — it is the single hub every deliverable touches: it holds the mandates to retain (`:140,157`), the two auto-load pointers to remove (`:153,168`), the checklist blocks to rewrite (`:197-211`), and the description rules FR-007 copies into `trigger-testing` (`:43-70`). Both extraction sources are reachable only through it, and every line-number citation that will drift (`trigger-optimizing.md:12,74,135,181`) points into it — so a planner must fix its final shape before reasoning about extraction boundaries.
