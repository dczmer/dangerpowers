---
artifact: context-bundle
date: 2026-08-05
git_commit: ee02e96e9db3e03f8abb96754577eccfc3173395
branch: dev/sloptime
request: "create a plan based on this prd @/home/dave/source/dangerpowers/PRDS/2026-08-05-merge-trigger-testing-into-writing-skills.md"
source_research: RESEARCH/2026-08-05-merge-trigger-testing-into-writing-skills-research-findings.md
source_prd: PRDS/2026-08-05-merge-trigger-testing-into-writing-skills.md
status: complete
---

# Context Bundle

## 1. Goal

Merge the standalone `trigger-testing` skill into `writing-skills`, mirroring the completed pressure-testing merge: campaign-execution content moves to an on-demand reference file (`skills/writing-skills/references/trigger-testing.md`), description-authoring rules stay only in the main file, the harness tooling survives relocation, the old skill directory is deleted, and the merge is verified by a pressure-test campaign plus a clean-context review (PRD FR-001–FR-012, `PRDS/2026-08-05-merge-trigger-testing-into-writing-skills.md:56-67`).

- **In scope:** the merge itself; deleting `skills/trigger-testing/` entirely (skill definition, campaign logs, eval sets); relocating and re-pointing the harness (`trigger-test.sh`, `test-trigger-test.sh`) and `agents/trigger-evaluator.md`; a pressure-test campaign against the merged skill's new discipline rules; a clean-context subagent review (PRD §5, `PRDS/2026-08-05-merge-trigger-testing-into-writing-skills.md:71-75`).
- **Out of scope:** a trigger-eval campaign against the merged skill's new description (deferred); changing the trigger-testing methodology (eval set sizes, split ratios, rep counts, pass criteria); migrating `trigger-testing`'s historical logs/eval sets; rewriting references in other skills' files or historical plans; changes to the pressure-testing reference beyond dedup/consistency (PRD §5, `PRDS/2026-08-05-merge-trigger-testing-into-writing-skills.md:76-80`; non-goals `:30-35`).

## 2. Files Retrieved

- `skills/writing-skills/SKILL.md:1-208` — merge target. Frontmatter description with pressure-test routing and the boundary clause to rewrite (`:3`); Invocation Branch (`:19-24`); Testing Discipline Skills section (`:145-151`); Trigger Optimization section referencing the standalone skill (`:153-159`); End-of-Flow Prompts (`:161-170`); Checklist (`:181-208`).
- `skills/trigger-testing/SKILL.md:1-253` — merge source. Standalone workflow (`:12-29`); Scope (`:31-36`); restated Description Best Practices (`:38-53`); eval query design (`:55-87`); train/validation split (`:89-93`); failure-class table (`:109-118`); harness protocol (`:120-166`); contamination rules (`:168-172`); done criteria (`:174-183`); multi-skill campaigns (`:185-189`); common mistakes (`:191-210`); results log template (`:212-245`); `trigger-evals/` convention (`:247-249`); boundary (`:251-253`).
- `skills/writing-skills/references/pressure-testing.md:1-201` — the structural model for the new reference file: header load contract (`:1-5`), back-reference style (`:9,120,133,175`), section ordering, Boundary section (`:199-201`).
- `skills/trigger-testing/scripts/trigger-test.sh:1-343` — the harness. CLI usage (`:4-47`); `init` default source-root computation (`:66-68`); hard requirement on `$source/agents/trigger-evaluator.md` (`:70`); workspace creation (`:72-92`); `eval` verdict protocol (`:95-168`); `batch` (`:179-253`); `cleanup` path safety (`:317-331`); dispatcher (`:333-343`).
- `skills/trigger-testing/scripts/test-trigger-test.sh:1-222` — shunit2 suite for the harness; locates the script as a sibling of itself (`:3`); always passes `--source` explicitly to `init` (`:26`).
- `agents/trigger-evaluator.md:1-31` — read-only primary agent (`mode: primary`, `steps: 3`, permission block allowing only `skill`, `:4-18`); one eval query per run (`:23`); reports exact loaded skill name in one line (`:30`).
- `PLANS/2026-08-05-merge-pressure-testing-into-writing-skills-plan.md:1-571` — precedent plan for the analogous merge: phase shape (merge → delete → campaign → clean-context review, `:67-534`), decisions-table style (`:51-61`), verification commands (`:556-563`).
- `agents/eval-reader.md:1-38` — pressure-testing's evaluator agent; remained in `agents/` after the pressure-testing merge (precedent for FR-008 relocation).
- `skills/writing-skills/trigger-evals/train.json`, `skills/writing-skills/trigger-evals/validation.json` — the merged skill's own eval sets (12 train / 7 validation queries); not deleted (FR-009 deletes only `skills/trigger-testing/trigger-evals/`).
- `README.md:31,50,56,64` — prose describing trigger testing; human-edited only per `AGENTS.md` (see §9).

## 3. Entry / Exit Points

- **Entry:** `skills/writing-skills/SKILL.md:19-24` — Invocation Branch: a direct pressure-test request reads the whole main file, loads `references/pressure-testing.md`, begins the campaign; cannot-find-target reported, never invented. FR-006 requires an equivalent branch for trigger-test requests loading `references/trigger-testing.md`.
- **Entry:** `skills/writing-skills/SKILL.md:161-170` — End-of-Flow Prompts: opt-in `question`-tool prompts after the Checklist passes; prompt 2 (`:166`) currently says "run the `trigger-testing` skill against the new description" — FR-005 requires it to load the in-skill reference file instead.
- **Entry:** `skills/trigger-testing/SKILL.md:12-29` — standalone 9-step campaign workflow (read target, author eval set without asking the user, workspace init, smoke test, optimization loop, fresh-query check, done criteria + log, multi-skill advance, cleanup always). This is the content the new reference file carries.
- **Entry:** `skills/trigger-testing/scripts/trigger-test.sh:333-343` — CLI dispatcher for `init|eval|batch|sync|status|cleanup`; invoked from the campaign workflow, never directly by users.
- **Exit:** `skills/writing-skills/SKILL.md:168` — declining both prompts ends the flow with no campaign started; a declined pressure test is reported as untested.
- **Exit:** `skills/writing-skills/references/pressure-testing.md:199-201` — Boundary: campaign ends when each target's log is written; no chaining. `skills/trigger-testing/SKILL.md:251-253` carries an equivalent standalone boundary.
- **Exit:** `skills/trigger-testing/SKILL.md:29` — `cleanup --workspace WS_PATH` runs always, including aborts; `trigger-test.sh:327-330` restricts `rm -rf` to `/tmp/trigger-test.*`.

## 4. Key Code

### Harness default source-root computation (relocation-sensitive)
- **Location:** `skills/trigger-testing/scripts/trigger-test.sh:66-70`
- **Code:**
  ```bash
  if [ -z "$source" ]; then
    source="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
  fi
  [ -d "$source/skills" ] || { echo "error: no skills/ directory under source: $source" >&2; exit 1; }
  [ -f "$source/agents/trigger-evaluator.md" ] || { echo "error: missing agent definition: $source/agents/trigger-evaluator.md" >&2; exit 1; }
  ```
- The default source root is the script's own location up three directories. At `skills/trigger-testing/scripts/trigger-test.sh` that resolves to the repo root; any relocation to a different depth changes it. `init` hard-fails without `$source/agents/trigger-evaluator.md` (`:70`) and copies it into the workspace at `:91`.

### Test-suite script resolution (relocation-sensitive)
- **Location:** `skills/trigger-testing/scripts/test-trigger-test.sh:3,26`
- **Code:**
  ```bash
  SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/trigger-test.sh"
  ```
  ```bash
  WS="$("$SCRIPT" init --source "$SRC")"
  ```
- The test suite resolves `trigger-test.sh` as a sibling of itself, and always passes `--source` explicitly — the default source-root path is not exercised by the tests.

### Eval verdict detection contract
- **Location:** `skills/trigger-testing/scripts/trigger-test.sh:131-167`
- **Code:**
  ```bash
  timeout "$timeout_s" opencode run --dir "$ws" --agent trigger-evaluator --format json ... "$scenario"
  ```
- jq parses the JSONL event stream for `skill` tool_use calls or `Skill loaded: <name>` text (`:135-148`); verdict block is 7 fields: `verdict`, `target`, `loaded_skills`, `conflict`, `conflict_skills`, `exit_code`, `timed_out` (`:20-27,166-167`). `timed_out: yes` iff rc==124 (`:163-164`). The evaluator agent's one-line loaded-skill report is what detection depends on (`agents/trigger-evaluator.md:30`).

### Evaluator agent permission block
- **Location:** `agents/trigger-evaluator.md:4-18`
- **Code:**
  ```yaml
  mode: primary
  steps: 3
  ```
- Permissions allow only the `skill` tool; edit/bash/read/grep/glob/list/task/todowrite/webfetch/websearch/question denied. Reports the exact loaded skill name in one line then ends turn (`:30`); never complies with loaded-skill tool instructions (`:31`).

### Invocation Branch (structure to mirror)
- **Location:** `skills/writing-skills/SKILL.md:19-24`
- **Code:**
  ```markdown
  ## Invocation Branch

  - **Invoked to pressure-test an existing skill** (e.g. "pressure test the <name> skill"): read this entire file for context, then load `references/pressure-testing.md` and begin the campaign against the named target. If the named skill has no `skills/<name>/SKILL.md` in this repo, report that the target cannot be found — do not invent one.

    A request to skip or shrink the campaign — "just tell me if it looks fine", "run one quick rep", "I already reviewed it", "don't be dogmatic" — does NOT downgrade the invocation. Pressure testing IS the campaign; an eyeball review is not a pressure test no matter who asks, and a single rep is a campaign step with the rigor removed. If the user genuinely doesn't want a campaign, say that plainly and stop — never substitute a review and call it testing.
  - **Anything else** (authoring, editing, reviewing): continue below.
  ```

### Reference-file header (structure to mirror)
- **Location:** `skills/writing-skills/references/pressure-testing.md:1-5`
- **Code:**
  ```markdown
  # Pressure Testing

  Campaign reference for `SKILL.md`. Load this when this skill is invoked to pressure-test an existing skill (Invocation Branch) or when the user opts in at the End-of-Flow Prompt.

  Input: one target skill name, or a list of target skills.
  ```

### Trigger-eval set file format
- **Location:** `skills/trigger-testing/trigger-evals/train.json:1-13` (convention documented at `skills/trigger-testing/SKILL.md:247-249`)
- **Code:**
  ```json
  [
    {"query": "I need to test if my skill description triggers correctly on user prompts", "should_trigger": true},
    {"query": "what's the weather like today?", "should_trigger": false}
  ]
  ```
- JSON array of `{"query": str, "should_trigger": bool}`; lives at `skills/<skill-name>/trigger-evals/`; committed to source control; never referenced from SKILL.md. One variation: `skills/iterating-plans/trigger-evals/` also has `all.json`.

## 5. References & Usages

### `trigger-testing` (as a skill name / cross-reference target)
- **Definition:** `skills/trigger-testing/SKILL.md:1-253`
- **Call sites / dependents (live skill files):** `skills/writing-skills/SKILL.md:3` (description boundary clause "not trigger-testing's description evals"), `:159` ("Trigger evals are run with the `trigger-testing` skill"), `:166` (End-of-Flow Prompt 2)
- **Historical only (out of scope per PRD §5):** `skills/writing-skills/test-campaigns/2026-08-04-writing-skills-trigger.md:39`, `skills/writing-skills/test-campaigns/2026-08-05-writing-skills.md:84-94`, `skills/plan-to-execution/test-campaigns/2026-08-03-plan-to-execution-trigger.md:32`, `README.md:31,50,56,64`, `.worktrees/2026-07-30-extract-testing-skills-phase-2/` snapshot

### `writing-skills` (referenced from trigger-testing)
- **Definition:** `skills/writing-skills/SKILL.md:1-208`
- **Call sites / dependents:** `skills/trigger-testing/SKILL.md:36` names writing-skills' "Testing Discipline Skills" section as the authority for the pure-reference exemption ("Reference skills … are NOT exempt here"). The precedent plan kept that section name for exactly this reason (`PLANS/2026-08-05-merge-pressure-testing-into-writing-skills-plan.md:54`).

### `trigger-test.sh`
- **Definition:** `skills/trigger-testing/scripts/trigger-test.sh:333-343`
- **Call sites / dependents:** `skills/trigger-testing/SKILL.md:19-23` (init), `:101-102` (sync), `:126-138` (eval), `:166` (batch), `:29` (cleanup); tested by `skills/trigger-testing/scripts/test-trigger-test.sh:1-222`; historical log reference at `skills/plan-to-execution/test-campaigns/2026-08-03-plan-to-execution-trigger.md:32`

### `trigger-evaluator` agent
- **Definition:** `agents/trigger-evaluator.md:1-31`
- **Call sites / dependents:** copied by `skills/trigger-testing/scripts/trigger-test.sh:91`; invoked by `trigger-test.sh:131-132` (`--agent trigger-evaluator`); documented at `skills/trigger-testing/SKILL.md:142`; stub copy in `skills/trigger-testing/scripts/test-trigger-test.sh:25`

### `eval-reader` agent
- **Definition:** `agents/eval-reader.md:1-38`
- **Call sites / dependents:** `skills/writing-skills/references/pressure-testing.md:96-99`; no dependents in trigger-testing. Stayed in `agents/` through the pressure-testing merge.

### Blast Radius
- **Likely to change:** `skills/writing-skills/SKILL.md` — description (`:3`), Invocation Branch (`:19-24`), Trigger Optimization section (`:153-159`), End-of-Flow Prompts (`:161-170`), Checklist trigger group (`:205-208`)
- **Likely to change:** `skills/trigger-testing/SKILL.md` — source material for the new reference file, then deleted (FR-009, FR-010)
- **Likely to change:** `skills/trigger-testing/scripts/trigger-test.sh`, `test-trigger-test.sh`, `agents/trigger-evaluator.md` — relocated/re-pointed (FR-008); new reference file `skills/writing-skills/references/trigger-testing.md` created (FR-002)
- **Must not break:** `skills/writing-skills/references/pressure-testing.md` — depends on Invocation Branch and End-of-Flow Prompts section names/semantics at `:3,9`; out of scope except dedup/consistency (PRD §5)
- **Must not break:** 11 other skills' `trigger-evals/` directories (plan-to-execution, writing-plans, researching-codebase, isolating-worktrees, writing-prds, iterating-plans, executing-plans, prompt-shaping, writing-quick-plans, plus writing-skills' own) — untouched per FR-009
- **Must not break:** the harness protocol's runtime behavior — every skill's campaign capability depends on `trigger-test.sh` init/eval/batch/sync/status/cleanup semantics (SC-007, `PRDS/2026-08-05-merge-trigger-testing-into-writing-skills.md:106`)
- **Transitive dependents worth attention:** `.opencode/skills` and `.opencode/agents` are symlinks to `skills/` and `agents/` (`AGENTS.md`); directory deletion and agent moves resolve through them automatically — but committing the symlinks themselves is forbidden (`AGENTS.md`)

## 6. Patterns & Idioms

### Pattern: on-demand reference file (merge model)
- **Location:** `skills/writing-skills/references/pressure-testing.md:1-5`
- **Snippet:** see §4 "Reference-file header".
- **Key aspects:** header names the parent file and both load paths (Invocation Branch, End-of-Flow opt-in); states its input; section order: Workflow, Scope, methodology, Done Criteria, Common Mistakes, Multi-Skill Campaigns, Results Log, Boundary (`PLANS/2026-08-05-merge-pressure-testing-into-writing-skills-plan.md:150-352`).

### Pattern: reference-file back-references to SKILL.md
- **Location:** `skills/writing-skills/references/pressure-testing.md:9,120,133,175`
- **Snippet:**
  ```markdown
  Record every excuse verbatim. Counter form follows failure type per "Match the Form to the Failure" and "Bulletproofing Discipline Skills" in `SKILL.md` — each excuse gets an explicit negation in the rules, a rationalization-table row, a red-flag entry, and a description symptom, chosen to fit the failure type.
  ```
- **Key aspects:** named-section references by section title; no restated rules. FR-004 requires the same for description-authoring rules.

### Pattern: campaign log naming
- **Location:** `skills/trigger-testing/SKILL.md:214`; `skills/writing-skills/test-campaigns/2026-08-04-writing-skills-trigger.md`
- **Key aspects:** pressure-test logs `test-campaigns/YYYY-MM-DD-<skill-name>.md`; trigger-eval logs carry a `-trigger` suffix (`YYYY-MM-DD-<skill-name>-trigger.md`); two-digit sequence variant for same-day repeats (`2026-07-29-01-executing-plans.md`). Logs live in the skill-under-test's own directory. Trigger-eval log iteration template with description sha256 at `skills/trigger-testing/SKILL.md:218-234`; hash command `sed -n 's/^description: //p' ... | sha256sum | cut -c1-12` (`:234`).

### Pattern: harness invocation protocol
- **Location:** `skills/trigger-testing/SKILL.md:19-23,126-138`
- **Snippet:**
  ````markdown
  ```bash
  skills/trigger-testing/scripts/trigger-test.sh eval --skill <candidate> --workspace /tmp/trigger-test.XXXXXXXXXX "$(cat <<'EOF'
  <eval query, verbatim>
  EOF
  )"
  ```
  ````
- **Key aspects:** script path is relative to repo root in every documented invocation; literal WS_PATH pasted into later commands because shell variables do not survive between Bash tool invocations (`:88` of research findings; `skills/trigger-testing/SKILL.md:19-23`). Every documented path changes if the script relocates.

### Conflicting Variations

- **Description-authoring rules, Variation A (main file):** `skills/writing-skills/SKILL.md:55-60,74-75` — imperative WHAT + WHEN, "Use when..." opener, never summarize workflow, weave trigger terms (no `Keywords:` label), YAML safety, ≤1024 chars.
- **Description-authoring rules, Variation B (restated in the skill being merged):** `skills/trigger-testing/SKILL.md:38-53` — "Description Best Practices" restating the same rules (imperative opener `:42`, WHAT + WHEN `:43`, no workflow summary `:45`, ≤1024 `:46`, weave trigger terms `:47`, YAML safety `:48`) plus campaign-side additions (generalize failures `:49`, front-load boundaries `:50`, match speech acts `:51`, quoted micro-phrases `:52`, negative classes by verb category `:53`).
- **Conflict:** the two files state overlapping authoring rules with different granularity — a duplication pair that can drift. FR-004 (`PRDS/2026-08-05-merge-trigger-testing-into-writing-skills.md:59`) assigns authoring rules to the main file only and requires the reference file to point back rather than restate; which of the campaign-side additions (`:49-53`) count as authoring rules vs campaign-only content is a partitioning judgment the PRD does not enumerate line-by-line.

- **Evaluator-agent home, Variation A (pressure-testing precedent):** `agents/eval-reader.md` remained in the shared `agents/` directory after the pressure-testing merge; it is referenced from the in-skill reference file (`skills/writing-skills/references/pressure-testing.md:96-99`).
- **Evaluator-agent home, Variation B (PRD wording):** FR-008 says the tooling is "relocated under the merged skill's ownership; all references to its old location are fixed" (`PRDS/2026-08-05-merge-trigger-testing-into-writing-skills.md:63`).
- **Conflict:** "under the merged skill's ownership" could read as `skills/writing-skills/` (scripts/ subdir or agent moved into the skill) or as merely "owned by the merged skill's workflows" with `agents/trigger-evaluator.md` staying in `agents/` per the eval-reader precedent. Technical coupling: `trigger-test.sh:70,91` requires the agent at `$source/agents/trigger-evaluator.md` where `$source` defaults to repo root via the script's own `../../..` (`:66-68`) — a move to `skills/writing-skills/scripts/` preserves that depth; other destinations change it. No evidence resolves which reading the maintainer intends.

## 7. Testing

- **How similar code is tested:** the harness has a shunit2 suite, `skills/trigger-testing/scripts/test-trigger-test.sh:1-222` (sources `shunit2` at `:222`; fixtures with alpha/beta skill stubs at `:5-30`; stubbed `opencode` binary at `:39-96`; covers frontmatter extraction, verdict computation, wrong-skill conflict, timeout/exit-124, batch pool bound, void serial-retry at `:98-219`). Skill content itself has no unit tests — campaign logs under `skills/*/test-campaigns/` are the test record (pressure-test template `skills/writing-skills/references/pressure-testing.md:171-197`; trigger-eval template `skills/trigger-testing/SKILL.md:218-234`).
- **Tests covering affected code:** `skills/trigger-testing/scripts/test-trigger-test.sh` covers `trigger-test.sh`. No tests cover `SKILL.md` files, `references/*.md`, or `agents/*.md`.
- **Validation commands (verified against the repo):**
  - `.venv/bin/agentskills validate skills/writing-skills` — must print `Valid skill`; binary verified present at `.venv/bin/agentskills`; usage contract at `skills/writing-skills/SKILL.md:77,185,197`
  - `bash skills/trigger-testing/scripts/test-trigger-test.sh` — shunit2 suite; `shunit2` verified on PATH via the nix env (`/nix/store/...-shunit2-2.1.8/bin/shunit2`); path changes with relocation
  - `.venv/bin/python -m json.tool skills/writing-skills/trigger-evals/train.json > /dev/null` (and `validation.json`) — eval-set parse check; precedent at `PLANS/2026-08-05-merge-pressure-testing-into-writing-skills-plan.md:561-562`; `.venv/bin/python` verified present
  - `test ! -d skills/trigger-testing` — deletion check; precedent at `PLANS/2026-08-05-merge-pressure-testing-into-writing-skills-plan.md:559`
  - `rg -n 'trigger-testing' skills/writing-skills/` — leftover-reference check; precedent grep at `PLANS/2026-08-05-merge-pressure-testing-into-writing-skills-plan.md:560`
  - No package.json, Makefile, or CI config exists in this repo; `pyproject.toml:8` declares only `ruff` and `skills-ref` tooling.

## 8. Constraints & Risks

- **Invariants the plan must respect:**
  - `trigger-test.sh` computes its default source root as `../../..` from its own path (`skills/trigger-testing/scripts/trigger-test.sh:66-68`); any relocation to a directory at a different depth breaks `init` unless callers pass `--source`.
  - `init` hard-fails without `$source/agents/trigger-evaluator.md` (`trigger-test.sh:70`) and copies that exact path into the workspace (`:91`); the agent's location and the script's source-root computation are coupled.
  - `test-trigger-test.sh` resolves the harness as a sibling of itself (`test-trigger-test.sh:3`); the two scripts must move together or the test breaks.
  - The eval-verdict contract (7-field block, `timed_out` on rc==124) is load-bearing for the campaign workflow's pass criteria (`trigger-test.sh:20-27,163-167`; `skills/trigger-testing/SKILL.md:160`).
  - Description is a YAML plain scalar: no colon+space, ≤1024 chars, or `agentskills validate` fails and the skill will not load (`skills/writing-skills/SKILL.md:72-77`).
  - Campaign logs are the ONLY place test status lives; no status notes or `test-campaigns/` references in SKILL.md (`skills/writing-skills/references/pressure-testing.md:175`; `skills/trigger-testing/SKILL.md:245`).
  - `trigger-evals/` directories are never referenced from any SKILL.md body (`skills/trigger-testing/SKILL.md:249`).
  - The pure-reference rule — trigger evals apply to every skill including pure reference — must survive intact (PRD edge case, `PRDS/2026-08-05-merge-trigger-testing-into-writing-skills.md:96`; currently stated at `skills/writing-skills/SKILL.md:157,166` and `skills/trigger-testing/SKILL.md:36`).
  - `skills/trigger-testing/SKILL.md:36` names the "Testing Discipline Skills" section of writing-skills; renaming that section would stale cross-references (precedent decision at `PLANS/2026-08-05-merge-pressure-testing-into-writing-skills-plan.md:54`).
  - `.opencode/skills` and `.opencode/agents` are symlinks; never commit the symlinks, commit real files (`AGENTS.md`).
  - README.md is human-edited only (`AGENTS.md`).
- **Dependencies / ordering:** the merge rewrite must read `skills/trigger-testing/SKILL.md` as source material before the directory is deleted (same read/delete ordering as the precedent plan, `PLANS/2026-08-05-merge-pressure-testing-into-writing-skills-plan.md:73`); the pressure-test verification campaign (FR-011) and clean-context review (FR-012) run only against the fully integrated result.
- **Likely failure modes:**
  - Stale script paths: every documented harness invocation uses a repo-root-relative path (`skills/trigger-testing/SKILL.md:19-23,101-102,126-138,166`); relocation without rewriting all of them leaves a dead protocol.
  - Void campaign runs fail silently: headless permission auto-rejection exits 0 with near-empty output; only manually reading outputs catches it (`skills/writing-skills/references/pressure-testing.md:302` — Campaign-Execution Lessons).
  - Workspace drift: the workspace stub is an init-time snapshot; `sync` must run after every description revision or evals measure a stale description (`trigger-test.sh` usage text `:35-40`; `skills/trigger-testing/SKILL.md:101-102`).
  - Ambiguous "test the X skill" requests: with both campaigns in one skill, the workflow must resolve discipline-rules vs description-routing rather than picking silently (PRD edge case, `PRDS/2026-08-05-merge-trigger-testing-into-writing-skills.md:94`).
- **Conflicting findings:** see §6 — description-authoring rules duplicated across both files at different granularity; evaluator-agent home (shared `agents/` precedent vs FR-008 "under the merged skill's ownership"). Both sides cited there.

## 9. Open Questions

- `[needs-human]` — Destination for the harness tooling after `skills/trigger-testing/` is deleted (FR-008 "relocated under the merged skill's ownership"). Evidence: `trigger-test.sh`'s default source root (`../../..` from its own path, `:66-68`) stays correct if the scripts land at `skills/writing-skills/scripts/`; the eval-reader precedent kept its agent in the shared `agents/` directory; `init` requires the evaluator agent at `$source/agents/trigger-evaluator.md` (`:70,91`). The PRD does not name a destination.
- `[needs-human]` — Whether `README.md:31,50,56,64` (prose describing trigger testing, including a "#### Trigger Testing" header) is updated after the merge. AGENTS.md reserves README.md for humans; the PRD does not mention it.
- `[needs-human]` — Which of the campaign-side description rules at `skills/trigger-testing/SKILL.md:49-53` (generalize failures, front-load boundaries, match speech acts, quoted micro-phrases, negative classes by verb category) are authoring rules belonging in the main file vs campaign-only content for the reference file; FR-004 sets the partition principle but does not enumerate these five lines.

## 10. Start Here

- **Start:** `skills/writing-skills/SKILL.md` — it is the surviving file every merge requirement lands in first: the description rewrite (FR-007, `:3`), the new trigger-testing invocation branch (FR-006, `:19-24`), the Trigger Optimization section's pointer to the standalone skill (FR-005/FR-010, `:159`), and the End-of-Flow Prompt 2 retarget (FR-005, `:166`). The precedent merge plan likewise made the surviving skill's main file its Phase 1 primary edit target (`PLANS/2026-08-05-merge-pressure-testing-into-writing-skills-plan.md:79-144`), and the reference file's content cannot be partitioned until the main file's final rule set is known.
