---
artifact: research-findings
date: 2026-08-05
git_commit: ee02e96e9db3e03f8abb96754577eccfc3173395
branch: dev/sloptime
request: "create a plan based on this prd @/home/dave/source/dangerpowers/PRDS/2026-08-05-merge-trigger-testing-into-writing-skills.md"
source_prd: PRDS/2026-08-05-merge-trigger-testing-into-writing-skills.md
status: complete
---

# Research Findings

## 1. Request Summary

Create an implementation plan for merging the `trigger-testing` skill into the `writing-skills` skill, per the approved PRD.

- **In scope (per PRD §5):** merging `trigger-testing` into `writing-skills` per FR-001–FR-010; deleting the `skills/trigger-testing/` directory and all its contents; relocating and re-pointing the trigger-test harness tooling and evaluator agent; a pressure-test verification campaign against the merged skill (FR-011); a clean-context final review (FR-012).
- **Out of scope (per PRD §5):** a trigger-eval campaign against the merged skill's new description; migrating or preserving `trigger-testing`'s historical campaign logs and eval sets; changes to any other skill's content or references in other skills' files/historical plans; changes to the pressure-testing reference file beyond deduplication/consistency.

## 2. File Map

### Implementation
- `skills/writing-skills/SKILL.md` (208 lines) — merged-skill target; frontmatter description routes pressure-testing and authoring requests; has an Invocation Branch jumping to `references/pressure-testing.md`
- `skills/writing-skills/references/pressure-testing.md` (201 lines) — pressure-testing campaign reference, loaded on demand; the structural model for the merge
- `skills/trigger-testing/SKILL.md` (253 lines) — standalone skill to be merged; contains full trigger-testing campaign workflow
- `skills/trigger-testing/scripts/trigger-test.sh` (343 lines) — bash harness with `init`, `eval`, `batch`, `sync`, `status`, `cleanup` subcommands
- `agents/trigger-evaluator.md` (31 lines) — read-only primary-mode agent for trigger-evaluation reps; only the `skill` tool allowed; copied into campaign workspaces by `trigger-test.sh init`
- `agents/eval-reader.md` (38 lines) — read-only agent for pressure-testing with-skill reps (untouched by merge; referenced by `skills/writing-skills/references/pressure-testing.md:96-99`)

### Tests
- `skills/trigger-testing/scripts/test-trigger-test.sh` (222 lines) — shunit2 test suite for `trigger-test.sh` (fixtures with alpha/beta skill stubs; tests frontmatter extraction, verdicts, conflicts, timeouts, batch pool bounds, void retries)
- `skills/writing-skills/SKILL.md` — no tests found (skill definition; tested via campaigns below)
- `skills/writing-skills/references/pressure-testing.md` — no tests found (reference document)
- `skills/trigger-testing/SKILL.md` — no tests found (skill definition; tested via campaigns below)
- `agents/trigger-evaluator.md` — exercised indirectly by `test-trigger-test.sh` via a stub copy

### Campaign Logs (`skills/*/test-campaigns/`)
- `skills/writing-skills/test-campaigns/2026-07-30-writing-skills.md` — pressure-test campaign log
- `skills/writing-skills/test-campaigns/2026-08-04-writing-skills-trigger.md` — trigger-eval campaign log for the writing-skills description
- `skills/writing-skills/test-campaigns/2026-08-05-writing-skills.md` — pressure-test campaign log against the post-pressure-merge writing-skills skill
- `skills/trigger-testing/test-campaigns/2026-08-03-trigger-testing-trigger.md` — trigger-eval campaign log for trigger-testing's own description (deleted per FR-009)

### Eval Sets (`skills/*/trigger-evals/`)
- `skills/writing-skills/trigger-evals/train.json` — 12 queries (8 should-trigger, 4 should-not)
- `skills/writing-skills/trigger-evals/validation.json` — 7 queries
- `skills/trigger-testing/trigger-evals/train.json` — 11 queries (deleted per FR-009)
- `skills/trigger-testing/trigger-evals/validation.json` — 6 queries (deleted per FR-009)
- Same `train.json`/`validation.json` pair exists in 9 other skills (plan-to-execution, writing-plans, researching-codebase, isolating-worktrees, writing-prds, iterating-plans [also has `all.json`], executing-plans, prompt-shaping, writing-quick-plans) — untouched per FR-009

### Documentation
- `PRDS/2026-08-05-merge-trigger-testing-into-writing-skills.md` — the approved PRD for this merge
- `PRDS/2026-08-05-merge-pressure-testing-into-writing-skills.md` — PRD for the completed analogous pressure-testing merge
- `PLANS/2026-08-05-merge-pressure-testing-into-writing-skills-plan.md` — plan for the completed pressure-testing merge (direct template for this merge)
- `README.md:31,50,56,64` — prose describing trigger testing in the workflow narrative (has a "#### Trigger Testing" section header); README is human-edited only per AGENTS.md

### Entry Points
- `skills/writing-skills/SKILL.md:19-24` — Invocation Branch: direct pressure-test requests load `references/pressure-testing.md`; all other requests continue into the authoring body
- `skills/writing-skills/SKILL.md:161-170` — End-of-Flow Prompts: opt-in pressure test and trigger eval after the authoring Checklist passes
- `skills/trigger-testing/SKILL.md:12-29` — standalone trigger-testing workflow entry (9 steps)
- `skills/trigger-testing/scripts/trigger-test.sh:333-343` — CLI dispatcher for the six subcommands

### Related Directories
- `skills/writing-skills/` — 7 files: root 1 (`SKILL.md`); `references/` 1; `test-campaigns/` 3; `trigger-evals/` 2; no `scripts/` directory
- `skills/trigger-testing/` — 6 files: root 1; `scripts/` 2; `test-campaigns/` 1; `trigger-evals/` 2; no `references/` directory
- `skills/writing-skills/references/` naming convention: lowercase kebab-case `.md`; campaign references are `<campaign-name>.md` (`pressure-testing.md`), templates are `<artifact>-template.md`
- `skills/*/test-campaigns/` naming convention: `YYYY-MM-DD-<skill-name>.md` for pressure-test logs, `YYYY-MM-DD-<skill-name>-trigger.md` for trigger-eval logs; two-digit sequence-number variant for same-day repeats (`2026-07-29-01-executing-plans.md`)
- `.worktrees/` — contains duplicate copies of historical PLANS/PRDS/RESEARCH docs and one snapshot copy of `skills/trigger-testing/SKILL.md` under `.worktrees/2026-07-30-extract-testing-skills-phase-2/`; worktree copies describe past states

### Files referencing "trigger-testing" outside `skills/trigger-testing/` (skill files only; historical docs describe past states and are out of scope per PRD §5)
- `skills/writing-skills/SKILL.md:3,159,166` — the only live skill-file references
- `skills/writing-skills/test-campaigns/2026-08-04-writing-skills-trigger.md:39` and `2026-08-05-writing-skills.md:84-94` — historical campaign logs
- `skills/plan-to-execution/test-campaigns/2026-08-03-plan-to-execution-trigger.md:32` — historical campaign log referencing the script path

## 3. Implementation Analysis

- **Overview:** `writing-skills` is a single-file skill (208 lines) with one on-demand reference file (`references/pressure-testing.md`, 201 lines). `trigger-testing` is a standalone skill (253 lines) whose campaign workflow drives a bash harness (`trigger-test.sh`) and a dedicated read-only agent (`agents/trigger-evaluator.md`). The pressure-testing merge already established the target structure: campaign content in a reference file loaded on demand, authoring rules in the main file, back-references from reference file to main file.
- **Entry points:**
  - `skills/writing-skills/SKILL.md:21` — direct pressure-test invocation: "read this entire file for context, then load `references/pressure-testing.md` and begin the campaign against the named target. If the named skill has no `skills/<name>/SKILL.md` in this repo, report that the target cannot be found — do not invent one."
  - `skills/writing-skills/SKILL.md:23` — anti-downgrade rule: skip/shrink requests do NOT downgrade the invocation; "never substitute a review and call it testing".
  - `skills/writing-skills/SKILL.md:165` — End-of-Flow Prompt 1: "Start pressure testing now?" (discipline skills only; skipped for pure-reference skills).
  - `skills/writing-skills/SKILL.md:166` — End-of-Flow Prompt 2: "Run a trigger eval now?" (every skill including pure reference); on yes, "run the `trigger-testing` skill against the new description".
  - `skills/trigger-testing/SKILL.md:12-29` — standalone workflow: read target (16), author eval set + split never asking the user (17), workspace init (18-23), smoke test (24), optimization loop (25), fresh-query check (26), done criteria + log (27), multi-skill advance (28), cleanup always (29).
- **Exit points:**
  - `skills/writing-skills/SKILL.md:168` — "declining both ends the flow with no campaign started — a declined pressure test means the skill ships untested, and you say so when reporting back".
  - `skills/writing-skills/references/pressure-testing.md:199-201` — Boundary: campaign ends when each target's log is written; no chaining into other skills.
  - `skills/trigger-testing/SKILL.md:251-253` — standalone boundary section.
- **Data flow (trigger-test campaign as it runs today):**
  1. `skills/trigger-testing/SKILL.md:19-23` — from repo root, run `WS=$(skills/trigger-testing/scripts/trigger-test.sh init) && echo "WORKSPACE=$WS"`; record literal WS_PATH (shell variables do not survive between Bash tool invocations); verify `ls WS_PATH/.agents/skills` lists every skill; `status --skill <candidate> --workspace WS_PATH` must print `in-sync`.
  2. `skills/trigger-testing/scripts/trigger-test.sh:58-93` — `init` creates `/tmp/trigger-test.XXXXXXXXXX` via `mktemp` (line 73); extracts frontmatter-only stubs of every `skills/*/SKILL.md` into `$ws/.agents/skills/<name>/SKILL.md` (lines 77-88); copies `agents/trigger-evaluator.md` to `$ws/.opencode/agents/` (line 91); prints workspace path (line 92). Default source root is computed relative to the script's own location (`trigger-test.sh` cmd_init: `source="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"`).
  3. `skills/trigger-testing/SKILL.md:126-138` — one eval per rep via `trigger-test.sh eval --skill <candidate> --workspace WS_PATH "$(cat <<'EOF' ... EOF)"`, optional `--model`, `--scenario-file`.
  4. `skills/trigger-testing/scripts/trigger-test.sh:95-168` — `eval` runs `timeout <secs> opencode run --dir "$ws" --agent trigger-evaluator --format json ... "$scenario"` (lines 131-132, default timeout 300 at line 96); parses the JSONL event stream with jq for `skill` tool_use calls or `Skill loaded: <name>` text (lines 135-148); computes verdict loaded/not-loaded and conflict none/wrong-skill/additional-skills (lines 150-161); `timed_out: yes` when rc==124 (lines 163-164); prints a 7-field verdict block (lines 166-167).
  5. `skills/trigger-testing/SKILL.md:95-107` — optimization loop ≤3 iterations: evaluate, identify train failures, revise per failure class, `sync --skill <candidate> --workspace WS_PATH` after every revision (lines 101-102), re-check the 1024-char ceiling (line 105), fresh-query sanity check with at-most-one train-expansion re-opt (line 107).
  6. `skills/trigger-testing/SKILL.md:166` — per-iteration rep matrix through `trigger-test.sh batch --skill <candidate> --workspace WS_PATH --scenarios FILE` (one query per line), bounded job pool default `--jobs 2`.
  7. `skills/trigger-testing/scripts/trigger-test.sh:179-253` — `batch` reads one query per non-blank line (lines 203-208); per-rep verdicts to `$ws/.batch.<pid>/scenario-<i>.txt` (lines 212, 246-247); void detection — timeout+not-loaded or unparseable verdict (lines 170-177); serial retry once for void reps, still-void rewritten as `verdict: void` (lines 229-242); ends with a `batch summary:` line (line 252).
  8. `skills/trigger-testing/SKILL.md:212-245` — results log to `test-campaigns/YYYY-MM-DD-<skill-name>-trigger.md` with `-trigger` suffix and NN sequence (line 214); iteration log template with sha256 (lines 218-234); hash command `sed -n 's/^description: //p' ... | sha256sum | cut -c1-12` (line 234); "log is the ONLY place trigger status lives" (line 245).
  9. `skills/trigger-testing/SKILL.md:29` — `cleanup --workspace WS_PATH` always, including aborts; `skills/trigger-testing/scripts/trigger-test.sh:317-331` — `cleanup` `rm -rf`s only paths matching `/tmp/trigger-test.*` (lines 327-330).
- **Key logic — content locations in `skills/trigger-testing/SKILL.md`:**
  - Description Best Practices (restated authoring rules): lines 38-53 — imperative opener (42), WHAT + WHEN (43), err pushy (44), never summarize workflow (45), concise ≤1024 chars (46), weave trigger terms / no Keywords label (47), YAML safety (48), generalize failures (49), front-load boundaries (50), match speech acts (51), anchor with quoted micro-phrases (52), name negative classes by verb category (53).
  - Scope: lines 31-36 — applies to every skill; reference skills NOT exempt; references writing-skills' "Testing Discipline Skills" section at line 36.
  - Eval query design: lines 55-87 — ≤5 should-trigger + ≤5 should-not (57); should-trigger axes table (63-68); near-miss negatives (70-74); body-consistency check (76); realism tips (78-87).
  - Train/validation split: lines 89-93 — ~60/40 into `skills/<skill-name>/trigger-evals/train.json` and `validation.json`; split kept fixed; validation pass rate selects best iteration.
  - Failure-class remediation table: lines 109-118.
  - Harness protocol: lines 120-166 — all queries through the script never to the user (122); workspace lifecycle (124); invoke syntax with heredoc (126-138); bare-query dispatch (140); `trigger-evaluator` agent usage (142); mechanical JSON-stream detection and verdict block (144-156); rep independence (158); pass criterion >0.5 / <0.5 over ≥3 reps, bump to 5 on consecutive-opposite-outcome, ≤25% bump cap (160); load-and-stop and void rules (162); workload isolation + timeout semantics (164); intra-iteration parallelism via `batch --jobs 2` (166).
  - Contamination rules: lines 168-172 — cross-skill visibility expected (170); old repo-root harness rates not comparable (171); globally installed skills leak as environmental noise (172).
  - Done criteria: lines 174-183.
  - Multi-skill campaigns: lines 185-189 — sequential with final-verification regression smoke.
  - Common mistakes table: lines 191-210.
  - `trigger-evals/` directory convention: lines 247-249.
- **Key logic — content locations in `skills/writing-skills/SKILL.md`:**
  - Description-authoring rules: imperative WHAT + WHEN, a few sentences to a short paragraph, ≤1024 chars (line 55); "Use when..." opener with triggering conditions (56); state what the skill produces in one clause (57); never summarize the workflow (58); move anti-pattern enumerations to the body (59); weave trigger terms into prose, never a `Keywords:` label (60); YAML safety — plain scalar cannot contain colon+space, block scalar `description: >` fallback (74); hard 1024-char limit (75); checklist restatement (183-184).
  - Trigger Optimization section: lines 153-159 — Trigger Eval Rule "no description ships without a passing eval set" (155); applies to every skill (157); "Trigger evals are run with the `trigger-testing` skill, offered as an opt-in End-of-Flow Prompt below — never begun unprompted during authoring" (159).
  - Testing Discipline Skills section: lines 145-151 — Iron Law at line 147; campaign process lives in `references/pressure-testing.md` and loads only when a campaign runs; authoring performs no campaign steps (line 151).
  - Checklist Trigger Optimization group: lines 205-208.
- **Error handling:**
  - Cannot-find-target: `skills/writing-skills/SKILL.md:21` — "report that the target cannot be found — do not invent one".
  - Unterminated frontmatter rejection: `skills/trigger-testing/scripts/test-trigger-test.sh:105-115` (test); `trigger-test.sh` validates frontmatter `name` matches directory at lines 85-86.
  - Timeout semantics: `trigger-test.sh:163-164` — `timed_out: yes` when rc==124; void detection and serial retry in batch at lines 170-177, 229-242.
  - Cleanup path safety: `trigger-test.sh:327-330` — `rm -rf` restricted to `/tmp/trigger-test.*`.
- **Configuration & flags:** `trigger-test.sh` CLI usage at lines 4-47: `init [--source DIR]`; `eval --skill NAME [--workspace DIR] [--model PROVIDER/MODEL] [--timeout SECS] [--scenario-file PATH] [SCENARIO_TEXT]`; `batch --skill NAME --scenarios FILE [--jobs N] [--timeout SECS]`; `sync`/`status --skill NAME [--workspace DIR] [--source DIR]`; `cleanup [--workspace DIR]`. `$TRIGGER_TEST_WORKSPACE` env fallback at line 109. `agents/trigger-evaluator.md:4-18` — `mode: primary`, `steps: 3`, permission block allowing only `skill`.

## 4. Patterns & Idioms

### Pattern: on-demand reference file (merge model)
- **Location:** `skills/writing-skills/references/pressure-testing.md:1-5`
- **Snippet:**
  ```markdown
  # Pressure Testing

  Campaign reference for `SKILL.md`. Load this when this skill is invoked to pressure-test an existing skill (Invocation Branch) or when the user opts in at the End-of-Flow Prompt.

  Input: one target skill name, or a list of target skills.
  ```
- **Key aspects:** header names the parent file and both load paths (Invocation Branch and End-of-Flow opt-in); states its input; section layout in order: Workflow (:7), Scope (:18), RED-GREEN-REFACTOR (:31), Scenario Design (:39), Execution Protocol (:79), Micro-Tests (:107), Plugging Rationalizations (:118), Meta-Testing (:122), Done Criteria (:137), Campaign-Execution Lessons (:150), Common Mistakes (:156), Multi-Skill Campaigns (:167), Results Log (:171), Boundary (:199).

### Pattern: reference-file back-references to SKILL.md (four styles)
- **Location:** `skills/writing-skills/references/pressure-testing.md:9,120,133,175`
- **Snippets:**
  ```markdown
  1. Confirm the target exists per the Invocation Branch guard in `SKILL.md`.
  ```
  ```markdown
  Record every excuse verbatim. Counter form follows failure type per "Match the Form to the Failure" and "Bulletproofing Discipline Skills" in `SKILL.md` — each excuse gets an explicit negation in the rules, a rationalization-table row, a red-flag entry, and a description symptom, chosen to fit the failure type.
  ```
  ```markdown
  The campaign log is the ONLY place test status lives — the Checklist in `SKILL.md` bars status notes from the skill file itself.
  ```
- **Key aspects:** named-section references by section title; no restated rules; campaign content points back to main-file authoring rules.

### Pattern: direct-invocation branch
- **Location:** `skills/writing-skills/SKILL.md:19-24`
- **Snippet:**
  ```markdown
  ## Invocation Branch

  - **Invoked to pressure-test an existing skill** (e.g. "pressure test the <name> skill"): read this entire file for context, then load `references/pressure-testing.md` and begin the campaign against the named target. If the named skill has no `skills/<name>/SKILL.md` in this repo, report that the target cannot be found — do not invent one.

    A request to skip or shrink the campaign — "just tell me if it looks fine", "run one quick rep", "I already reviewed it", "don't be dogmatic" — does NOT downgrade the invocation. Pressure testing IS the campaign; an eyeball review is not a pressure test no matter who asks, and a single rep is a campaign step with the rigor removed. If the user genuinely doesn't want a campaign, say that plainly and stop — never substitute a review and call it testing.
  - **Anything else** (authoring, editing, reviewing): continue below.
  ```
- **Key aspects:** dedicated section; cannot-find-target inline in the first bullet; indented anti-downgrade sub-paragraph; catch-all "Anything else" bullet routes to authoring.

### Pattern: end-of-flow opt-in prompts
- **Location:** `skills/writing-skills/SKILL.md:161-170`
- **Snippet:**
  ```markdown
  ## End-of-Flow Prompts

  When the Checklist is complete and `agentskills validate` passes, offer each follow-on as its own Yes/No question via the `question` tool:

  1. **Start pressure testing now?** — discipline skills only; skip the question entirely for pure-reference skills with no violable rule. On yes, load `references/pressure-testing.md` and begin the campaign against the skill just authored.
  2. **Run a trigger eval now?** — every skill, including pure reference. On yes, run the `trigger-testing` skill against the new description.

  Both are opt-in. Declining either skips it; declining both ends the flow with no campaign started — a declined pressure test means the skill ships untested, and you say so when reporting back.

  Offer them even when the user has said to skip process, is out of time, or an authority figure waived the steps. "They already declined in advance" is a rationalization — the prompt IS the decline path; staying silent decides for the user, which is the failure, not respect for their time.
  ```
- **Key aspects:** numbered opt-ins with per-item scoping clauses; item 2 currently points at the standalone `trigger-testing` skill (merge target per FR-005); decline-semantics paragraph; anti-rationalization paragraph.

### Pattern: frontmatter description routing
- **Location:** `skills/writing-skills/SKILL.md:1-4`
- **Snippet:**
  ```yaml
  ---
  name: writing-skills
  description: Use when pressure-testing an existing skill's rules — "pressure test the <name> skill" or "run a pressure-test campaign on a skill" means THIS skill (baseline and with-skill scenario campaigns against a skill's discipline rules), not trigger-testing's description evals — or when creating new skills, editing existing skills, or reviewing a skill before deploying it to this repo's skills/ directory. Triggers include "pressure test this skill", "pressure test a skill", "pressure test the <name> skill", "write a new skill", "create skill", "edit skill", "review skill", "update skill", "writing skills".
  ---
  ```
- **Key aspects:** pressure-test requests front-loaded with quoted micro-phrases; explicit boundary clause "not trigger-testing's description evals" (rewritten per FR-007); authoring triggers in an "or when" clause; "Triggers include" list closes it. For comparison, `skills/trigger-testing/SKILL.md:3`: `description: Use when testing or optimizing a skill's trigger description with eval queries, train and validation splits, and detection-harness campaigns, when a new or edited description needs a passing eval set before it ships, or when running trigger-eval or trigger-test campaigns against one skill or a list of skills run sequentially.`

### Pattern: pressure-test campaign log
- **Location:** `skills/writing-skills/test-campaigns/2026-08-05-writing-skills.md:1-7`
- **Snippet:**
  ```markdown
  # Test Campaign: writing-skills — 2026-08-05

  Campaign against the merged `writing-skills` skill (post pressure-testing merge), pressure-testing its two new discipline rules: the opt-in End-of-Flow Prompts and the Invocation Branch direct jump. Run per `references/pressure-testing.md`. Baselines: stripped config (`opencode run --dir /tmp/opencode/campaign-baseline`, empty dir outside repo; `~/.config/opencode/AGENTS.md` verified absent). With-skill: `opencode run --dir /home/dave/source/dangerpowers --agent eval-reader` with the read-first prepend naming the merged SKILL.md. 5 reps per variant; every output read manually; no void runs observed. With-skill reps ran with repo cwd, so repo AGENTS.md loaded for them (second reinforcement channel, noted per protocol).
  ```
- **Key aspects:** header states campaign target, rules under test, protocol, rep counts; per-scenario subsections `### Baseline (no skill) — 5 runs`, `### With skill (pre-REFACTOR) — 5 runs`, `### New rationalizations found`, `### With skill (REFACTOR re-run) — 5 runs`, `### Verdict`.

### Pattern: trigger-eval campaign log
- **Location:** `skills/writing-skills/test-campaigns/2026-08-04-writing-skills-trigger.md:1-22`
- **Snippet:**
  ```markdown
  # Test Campaign: writing-skills — 2026-08-04

  ## Trigger evals

  ### Iteration 1
  - Description (≤1024 chars): Use when creating new skills, editing existing skills, or reviewing a skill before deploying it. Triggers include "write a new skill", "create skill", "edit skill", "review skill", "update skill", "writing skills".
  - Description sha256 (first 12): 7a2b1c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b
  - Train pass rate: 6/6 queries
  - Validation pass rate: 4/6 queries
  ```
- **Key aspects:** `-trigger` filename suffix; per-iteration blocks with description sha256, train/validation pass rates; selected-iteration line; fresh-query sanity check section.

### Pattern: trigger-eval set files
- **Location:** `skills/trigger-testing/trigger-evals/train.json:1-13`
- **Snippet:**
  ```json
  [
    {"query": "I need to test if my skill description triggers correctly on user prompts", "should_trigger": true},
    {"query": "run a trigger-eval campaign to measure if my skill loads on the right queries", "should_trigger": true},
    {"query": "what's the weather like today?", "should_trigger": false},
    {"query": "write a PRD for this new feature with user stories and acceptance criteria", "should_trigger": false}
  ]
  ```
- **Key aspects:** JSON array of `{"query": "<str>", "should_trigger": <bool>}` objects, one per line; convention documented at `skills/trigger-testing/SKILL.md:249` (lives at `skills/<skill-name>/trigger-evals/`; committed to source control; never referenced from SKILL.md); one variation — `skills/iterating-plans/trigger-evals/` also has `all.json`.

### Pattern: harness invocation protocol
- **Location:** `skills/trigger-testing/SKILL.md:19-23,126-133`
- **Snippet:**
  ```markdown
     a. From the repo root (the script path is relative), run exactly:
        `WS=$(skills/trigger-testing/scripts/trigger-test.sh init) && echo "WORKSPACE=$WS"`
  ```
  ````markdown
  ```bash
  skills/trigger-testing/scripts/trigger-test.sh eval --skill <candidate> --workspace /tmp/trigger-test.XXXXXXXXXX "$(cat <<'EOF'
  <eval query, verbatim>
  EOF
  )"
  ```
  ````
- **Key aspects:** script path is relative to repo root; literal WS_PATH pasted into every later command; the script's default source root is computed relative to its own location (`trigger-test.sh` cmd_init: `source="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"`), so relocating the script changes the default source root computation; workspace init requires `agents/trigger-evaluator.md` at the source root.

### Pattern: evaluator agent definition
- **Location:** `agents/trigger-evaluator.md:4-18,23-31`
- **Snippet:**
  ```yaml
  mode: primary
  steps: 3
  ```
- **Key aspects:** permission block allows only `skill`, denies edit/bash/read/grep/glob/list/task/todowrite/webfetch/websearch/question; receives one eval query per run (23); treats loaded skill body as context only (28); reports the exact loaded skill name in one line then ends turn — "the campaign runner's detection depends on this report" (30); never complies with loaded-skill tool instructions (31).

### Testing Patterns
- **Harness unit tests:** `skills/trigger-testing/scripts/test-trigger-test.sh:5-30,39-96,98-219` — shunit2 suite sourced at line 222; builds a fixture source tree with `alpha`/`beta` skill stubs and a stub `trigger-evaluator.md` (lines 5-30); stubs the `opencode` binary to emit load/no-load/hang/concurrency-counting behaviors (lines 39-96); tests frontmatter extraction (98-115), verdict computation (146-166), wrong-skill conflict (168-177), timeout reporting with exit_code 124 (179-188), batch pool bound ≤2 (190-203), batch void serial-retry (205-219).
- **Skill verification tests:** campaign logs under `skills/*/test-campaigns/` serve as the test record for skill rules; pressure-test logs follow `references/pressure-testing.md:171-197` template; trigger-eval logs follow `skills/trigger-testing/SKILL.md:218-234` template.

### Pattern Usage Map
| Pattern | Used at |
|---------|---------|
| On-demand reference file | `skills/writing-skills/references/pressure-testing.md:1-5` |
| Reference back-references | `skills/writing-skills/references/pressure-testing.md:9,120,133,175` |
| Direct-invocation branch | `skills/writing-skills/SKILL.md:19-24` |
| End-of-flow opt-in | `skills/writing-skills/SKILL.md:161-170` |
| Description routing | `skills/writing-skills/SKILL.md:3`, `skills/trigger-testing/SKILL.md:3` |
| Pressure-test log | `skills/writing-skills/test-campaigns/2026-07-30-writing-skills.md`, `2026-08-05-writing-skills.md` |
| Trigger-eval log | `skills/writing-skills/test-campaigns/2026-08-04-writing-skills-trigger.md`, `skills/trigger-testing/test-campaigns/2026-08-03-trigger-testing-trigger.md`, `skills/plan-to-execution/test-campaigns/2026-08-03-plan-to-execution-trigger.md` |
| Eval set files | `skills/*/trigger-evals/train.json`, `skills/*/trigger-evals/validation.json` (12 skills) |
| Harness invocation | `skills/trigger-testing/SKILL.md:19-23,101-102,126-138,166`; `skills/plan-to-execution/test-campaigns/2026-08-03-plan-to-execution-trigger.md:32` |
| Evaluator agent | `agents/trigger-evaluator.md`; copied by `skills/trigger-testing/scripts/trigger-test.sh:91` |

## 5. References & Usages

### `writing-skills` SKILL.md references to `trigger-testing`
- **Definition:** n/a (cross-references)
- **Call sites / dependents:**
  - `skills/writing-skills/SKILL.md:3` — frontmatter boundary clause "not trigger-testing's description evals"
  - `skills/writing-skills/SKILL.md:159` — "Trigger evals are run with the `trigger-testing` skill, offered as an opt-in End-of-Flow Prompt below"
  - `skills/writing-skills/SKILL.md:166` — End-of-Flow Prompt 2: "run the `trigger-testing` skill against the new description"

### `trigger-testing` SKILL.md references to `writing-skills`
- **Definition:** n/a (cross-references)
- **Call sites / dependents:**
  - `skills/trigger-testing/SKILL.md:36` — "Reference skills (exempt from pressure testing per the writing-skills skill's Testing Discipline Skills section) are NOT exempt here"
  - `skills/trigger-testing/SKILL.md:118` — internal self-reference to its own Description Best Practices (not to writing-skills)
  - No other references found.

### `trigger-test.sh`
- **Definition:** `skills/trigger-testing/scripts/trigger-test.sh:333-343` (dispatcher)
- **Call sites / dependents:**
  - `skills/trigger-testing/SKILL.md:19-23` (init), `:101-102` (sync), `:126-138` (eval), `:166` (batch), `:29` (cleanup)
  - `skills/plan-to-execution/test-campaigns/2026-08-03-plan-to-execution-trigger.md:32` — historical log: "Eval script: skills/trigger-testing/scripts/trigger-test.sh"
  - Tested by `skills/trigger-testing/scripts/test-trigger-test.sh:1-222`

### `trigger-evaluator` agent
- **Definition:** `agents/trigger-evaluator.md:1-31`
- **Call sites / dependents:**
  - `skills/trigger-testing/scripts/trigger-test.sh:91` — copied into campaign workspaces by `init`
  - `skills/trigger-testing/scripts/trigger-test.sh:131-132` — invoked via `opencode run --agent trigger-evaluator`
  - `skills/trigger-testing/SKILL.md:142` — agent usage in harness protocol
  - `skills/trigger-testing/scripts/test-trigger-test.sh:5-30` — stub copy in test fixtures

### `eval-reader` agent
- **Definition:** `agents/eval-reader.md:1-38`
- **Call sites / dependents:** `skills/writing-skills/references/pressure-testing.md:96-99` (pressure-testing protocol); no dependents in trigger-testing

### `End-of-Flow Prompts` section
- **Definition:** `skills/writing-skills/SKILL.md:161-170`
- **Call sites / dependents:** `skills/writing-skills/references/pressure-testing.md:3` (header load condition); `skills/writing-skills/test-campaigns/2026-08-05-writing-skills.md` (pressure-tested rules); PRD FR-005

### `Invocation Branch` section
- **Definition:** `skills/writing-skills/SKILL.md:19-24`
- **Call sites / dependents:** `skills/writing-skills/references/pressure-testing.md:3,9` (header load condition; workflow step 1); PRD FR-006

### `trigger-evals/` convention
- **Definition:** `skills/trigger-testing/SKILL.md:247-249`
- **Call sites / dependents:** 12 skills hold `trigger-evals/` directories (listed in §2); no references from any SKILL.md body (per the convention "never referenced from SKILL.md", `skills/trigger-testing/SKILL.md:249`)

## 6. Agent Provenance

| Sub-agent | Asked to | Outcome |
|-----------|----------|---------|
| Locator (explore) | Map all files under both skill dirs, evaluator agents, cross-references, naming conventions | Complete; 13 files across both skills, 2 agents, full cross-reference list with file:line, naming conventions for references/, test-campaigns/, trigger-evals/, scripts/ |
| Analyzer (general) | Explain HOW writing-skills SKILL.md, pressure-testing.md, trigger-testing SKILL.md, harness scripts, and evaluator agents work | Complete; section-by-section analysis of all five areas, every claim cited file:line |
| Pattern-finder (general) | Extract the 8 patterns to model from the pressure-testing merge | Complete; all 8 patterns with verbatim snippets and file:line; noted that FR-009 deletion requires a new home for `trigger-test.sh` and its `agents/trigger-evaluator.md` dependency |

## 7. Known Gaps

- The exact intended new location for `trigger-test.sh`, `test-trigger-test.sh`, and `agents/trigger-evaluator.md` after the `skills/trigger-testing/` deletion is not specified in the PRD beyond "relocated under the merged skill's ownership" (FR-008); the pressure-testing merge precedent (`agents/eval-reader.md` stayed in `agents/`) and the script's self-relative source-root computation (`trigger-test.sh` cmd_init `../../..`) are documented in §3-§4, but the destination choice is a planning decision.
- Whether `README.md:31,50,56,64` (which describes trigger testing in prose) is updated is outside agent control: AGENTS.md states only humans edit README.md unless the user asks for a specific edit; the PRD does not mention README.md.
