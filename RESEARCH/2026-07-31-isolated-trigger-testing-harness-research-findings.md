---
artifact: research-findings
date: 2026-07-31
git_commit: 72416a8169ab650a341b4e82e63a03f52bf5591a
branch: dev/sloptime
request: |
  turn this prd into a detailed implementation plan @/home/dave/source/dangerpowers/PRDS/2026-07-31-isolated-trigger-testing-harness.md
source_prd: PRDS/2026-07-31-isolated-trigger-testing-harness.md
status: complete
---

# Research Findings

## 1. Request Summary

Produce an implementation plan for an isolated trigger-testing harness per the source PRD: a single command (`trigger-test.sh [--model MODEL] SCENARIO_TEXT`) that runs one eval scenario inside a temporary workspace containing only frontmatter stubs of the skills and the evaluator agent, detects the outcome mechanically from `opencode run --format json` output, surfaces conflicting skill loads, and replaces the current Task-tool-based harness inside the existing `trigger-testing` skill.

- **In scope:** the trigger-testing skill's harness sections, the `trigger-evaluator` agent, the `.opencode` skills/agents wiring the harness must replicate in a temp workspace, the new script's interface (stub generation, scenario input, model flag, JSON outcome detection, workspace lifecycle), and the skill-update that replaces the old harness.
- **Out of scope:** trigger-testing methodology (eval-set design, train/validation splits, optimization loop, done criteria), pressure-testing harness changes, batch/multi-scenario execution, automated description rewrites, three-way outcome classification.

## 2. File Map

### Implementation
- `/home/dave/source/dangerpowers/skills/trigger-testing/SKILL.md` — the trigger-testing skill; contains the harness to be replaced (only file in the skill directory)
- `/home/dave/source/dangerpowers/agents/trigger-evaluator.md` — the evaluator agent definition the harness runs under
- `/home/dave/source/dangerpowers/.opencode/opencode.jsonc` — opencode config (`permission: {"*": "allow"}`, watcher ignores)

### Tests
- `skills/trigger-testing/SKILL.md` — no automated tests; verification is by trigger-eval campaigns per the skill's own workflow. No test files exist for the harness.
- `/home/dave/source/dangerpowers/skills/writing-prds/trigger-evals/train.json` — existing eval query set (example consumer of the harness)
- `/home/dave/source/dangerpowers/skills/writing-prds/trigger-evals/validation.json` — validation split of the same

### Configuration
- `/home/dave/source/dangerpowers/.opencode/opencode.jsonc` — repo opencode config
- `/home/dave/source/dangerpowers/.opencode/skills/dangerpowers` — symlink → `../../skills`
- `/home/dave/source/dangerpowers/.opencode/agents/dangerpowers` — symlink → `../../agents`

### Type Definitions
- None (shell/markdown/JSON only).

### Documentation
- `/home/dave/source/dangerpowers/AGENTS.md` — repo operational rules (skills under `skills/`, symlink policy)
- `/home/dave/source/dangerpowers/PRDS/2026-07-31-isolated-trigger-testing-harness.md` — source PRD
- `/home/dave/source/dangerpowers/PLANS/2026-07-30-trigger-eval-read-only-agent-plan.md` — prior plan documenting `opencode run --agent trigger-evaluator --format json` usage
- `/home/dave/source/dangerpowers/PLANS/2026-07-30-extract-testing-skills-plan.md` — prior plan containing an mktemp+jq eval-loop skeleton
- `/home/dave/source/dangerpowers/PLANS/2026-07-30-trigger-eval-structural-isolation-plan.md` — prior isolation plan

### Entry Points
- `skills/trigger-testing/SKILL.md` — Harness section (`:113-140`) is the harness entry today; Workflow step 3 smoke test (`:18`)
- The PRD specifies the new entry: `trigger-test.sh [--model MODEL] SCENARIO_TEXT` (PRD `:13`)

### Related Directories
- `/home/dave/source/dangerpowers/skills/` — 15 skill directories; convention `SKILL.md` + optional `references/`, `scripts/`, `test-campaigns/`, `trigger-evals/`
- `/home/dave/source/dangerpowers/agents/` — 2 agent definition files (`trigger-evaluator.md`, `eval-reader.md`)
- `/home/dave/source/dangerpowers/skills/project-bootstrap-nix/scripts/` — 1 file; the only `scripts/` directory in the repo
- `/home/dave/source/dangerpowers/RESEARCH/` — 2 files; `YYYY-MM-DD-<topic>-research-findings.md` / `-context-bundle.md`
- `/home/dave/source/dangerpowers/PLANS/` — 9 files; `YYYY-MM-DD-<topic>-plan.md` / `-phase-N-report.md`

## 3. Implementation Analysis

- **Overview:** The current harness dispatches eval reps as in-process `Task` tool calls to the `trigger-evaluator` subagent against the live repo; detection is the rep's own final message. The PRD replaces this with an external `opencode run` invocation against a stub-only temp workspace, with detection by parsing the JSON event stream.
- **Entry points:** `skills/trigger-testing/SKILL.md:115` — "Every query — smoke, train, validation, fresh — is dispatched to a subagent via the `Task` tool"; invoke spec at `skills/trigger-testing/SKILL.md:117-122`.
- **Exit points:** `skills/trigger-testing/SKILL.md:130` — detection reads the rep's final message for the loaded skill name; `agents/trigger-evaluator.md:30` — the rep reports the exact skill name or no-match in one line and ends the turn.
- **Data flow (current harness):**
  1. `skills/trigger-testing/SKILL.md:16-17` — runner reads target SKILL.md description, authors eval set into `skills/<name>/trigger-evals/{train,validation}.json`
  2. `skills/trigger-testing/SKILL.md:18` — smoke test: ONE should-trigger query dispatched via `Task` to `trigger-evaluator`; result message read before full runs
  3. `skills/trigger-testing/SKILL.md:119-122` — per-rep `Task` call: `subagent_type: "trigger-evaluator"`, bare-query prompt, neutral description, no `task_id`
  4. `skills/trigger-testing/SKILL.md:124` — reps run from the repo root
  5. `agents/trigger-evaluator.md:5,7` — rep bounded by `steps: 3`, only tool `skill`
  6. `skills/trigger-testing/SKILL.md:130` — exit: rep's one-line final message names the loaded skill or no-match
  7. `skills/trigger-testing/SKILL.md:134` — pass criterion: trigger rate > 0.5 over ≥3 reps for should-trigger, < 0.5 for should-not
  8. `skills/trigger-testing/SKILL.md:183` — results written to `skills/<name>/test-campaigns/YYYY-MM-DD-<skill-name>-trigger.md`
- **Key logic (current harness):** bare-query dispatch (`skills/trigger-testing/SKILL.md:126`) — the prompt contains only the eval query; load-and-stop (`:136`) — a rep that begins the loaded skill's workflow is void; workload isolation (`:128`,`:138`) — structural via the agent's tool permissions and steps cap; rep independence (`:132`); intra-iteration parallel dispatch (`:140`).
- **Key logic (PRD-specified new harness):** temp workspace with `.agents`-style skills/agents subdirectories (PRD `:14-16`); frontmatter-only stubs (PRD `:17`); invocation `opencode run --dir "$TEMPDIR" --agent trigger-evaluator --format json [--model $MODEL] "$SCENARIO"` (PRD `:19-20`); heredoc for direct-string scenarios (PRD `:21`); scenario files placed under the temp dir (PRD `:22`); detection by `type=tool, tool=skill, state.input.name=SKILL_NAME` or `type=text, part.text="Skill loaded: SKILL_NAME"` (PRD `:24`); step-limit/timeout without the signal counts as failed trigger (PRD `:23`); conflict surfacing for wrong/multiple loads (PRD `:25`).
- **Error handling (current):** void-rep convention — a rep that hangs or returns no clear verdict is voided and re-dispatched fresh, never counted (`skills/trigger-testing/SKILL.md:138`); smoke-test gate stops the campaign if the subagent cannot load skills (`skills/trigger-testing/SKILL.md:18`).
- **Configuration & flags:**
  - `agents/trigger-evaluator.md:1-19` — `mode: primary`, `steps: 3`, permission map: `skill: allow`, all of edit/bash/read/grep/glob/list/task/todowrite/webfetch/websearch/question `deny`
  - `.opencode/opencode.jsonc:3-5` — `permission: {"*": "allow"}`
  - `.opencode/skills/dangerpowers -> ../../skills` and `.opencode/agents/dangerpowers -> ../../agents` — namespaced skill/agent discovery via symlink
  - `opencode run --dir <empty-dir-outside-repo> "<scenario>"` used by pressure-testing for skill-stripped baselines (`skills/pressure-testing/SKILL.md:94-97`); `--pure` documented as having no effect on skill stripping (`skills/pressure-testing/SKILL.md:97`)
  - `opencode run --dir <repo-root> --agent eval-reader ...` used by pressure-testing with-skill reps (`skills/pressure-testing/SKILL.md:104-106`)
  - `opencode run --dir <repo-root> --agent trigger-evaluator --format json "<query>"` documented in a prior plan (`PLANS/2026-07-30-trigger-eval-read-only-agent-plan.md:108,119-126`), with grep detection over the JSON stream at `PLANS/2026-07-30-trigger-eval-read-only-agent-plan.md:200`
  - `--model` flag appears only in the source PRD (`PRDS/2026-07-31-isolated-trigger-testing-harness.md:19-20`); no repo documentation of its semantics

## 4. Patterns & Idioms

### Pattern: standalone bash helper script in a skill's `scripts/` directory
- **Location:** `skills/project-bootstrap-nix/scripts/bootstrap.sh:1-84`; pointed at from `skills/project-bootstrap-nix/SKILL.md:41-44`
- **Snippet:**
  ```bash
  #!/usr/bin/env bash
  set -euo pipefail

  if [ $# -ne 1 ]; then
    echo "usage: $0 PROJECT_NAME" >&2
    exit 1
  fi
  PROJECT_NAME="$1"

  cat > flake.nix <<'EOF'
  {
    description = "PROJECT_NAME";
    inputs.flake-utils.url = "github:numtide/flake-utils";
  }
  EOF
  sed -i "s/PROJECT_NAME/$PROJECT_NAME/" flake.nix
  ```
- **Key aspects:** `set -euo pipefail`; usage errors to stderr with non-zero exit; precondition guards; quoted heredoc `<<'EOF'` writing whole files; `sed -i` placeholder substitution.

### Pattern: `opencode run` dispatch commands embedded in a skill
- **Location:** `skills/pressure-testing/SKILL.md:93-97`, `:102-106`
- **Snippet:**
  ```bash
  opencode run --dir <empty-dir-outside-repo> "<scenario>"
  opencode run --dir <repo-root> --agent eval-reader "$(cat prepend.txt scenario.txt)"
  ```
- **Key aspects:** `--dir` for working-directory control; `--agent <name>`; command substitution for prompt assembly.

### Pattern: mktemp + jq eval loop with grep detection over `--format json` output
- **Location:** `PLANS/2026-07-30-extract-testing-skills-plan.md:283-296` (plan text, not shipped code)
- **Snippet:**
  ```bash
  SKILL="<candidate>"
  for q_set in train validation; do
    for f in trigger-evals/${q_set}/*.json; do
      while IFS=$'\t' read -r query should_trigger; do
        out=$(mktemp); opencode run --dir <repo-root> \
          --format json "$query" > "$out" 2>&1
        triggered=$(grep '"tool":"skill"' "$out" | grep -q "\"name\":\"$SKILL\"" && echo yes || echo no)
        rm "$out"
      done < <(jq -rc '.[] | "\(.query)\t\(.should_trigger)"' "$f")
    done
  done
  ```
- **Key aspects:** `mktemp` for output capture; process substitution feeding `jq -rc` rows; grep-based detection of `"tool":"skill"` + `"name":"<candidate>"`; explicit `rm` cleanup (no `trap`-based cleanup exists anywhere in the repo).

### Pattern: grep-based smoke detection on a captured JSON stream
- **Location:** `PLANS/2026-07-30-trigger-eval-read-only-agent-plan.md:200`
- **Snippet:**
  ```bash
  opencode run --dir /home/dave/source/dangerpowers --agent trigger-evaluator --format json "write a PRD for adding a dark mode toggle to the settings page" > /tmp/opencode/trigger-smoke.json 2>&1 && grep '"tool":"skill"' /tmp/opencode/trigger-smoke.json | grep '"name":"writing-prds"'
  ```
- **Key aspects:** redirects stdout+stderr to a file, then greps for the tool event and candidate name.

### Pattern: eval-set JSON files
- **Location:** `skills/writing-prds/trigger-evals/train.json:1-22`; convention at `skills/trigger-testing/SKILL.md:215`
- **Snippet:**
  ```json
  [
    {"query": "i need to write a product requirements document for a new feature", "should_trigger": true},
    {"query": "help me write a README for this library", "should_trigger": false}
  ]
  ```
- **Key aspects:** flat JSON arrays of `{"query": str, "should_trigger": bool}`; committed to source control; live beside the skill under test.

### Pattern: SKILL.md frontmatter (the stub content)
- **Location:** `skills/trigger-testing/SKILL.md:1-4`; identical two-field structure in `skills/writing-prds/SKILL.md:1-4`, `skills/prompt-shaping/SKILL.md:1-4`, `skills/researching-codebase/SKILL.md:1-4`
- **Snippet:**
  ```yaml
  ---
  name: trigger-testing
  description: Use when testing or optimizing a skill's trigger description with eval queries...
  ---
  ```
- **Key aspects:** exactly `name` and `description` fields between `---` delimiters; description is a plain YAML scalar with a 1024-char hard limit and no colon+space (`skills/trigger-testing/SKILL.md:42`); a frontmatter-only stub preserves this block verbatim.

### Pattern: agent definition frontmatter
- **Location:** `agents/trigger-evaluator.md:1-19`, `agents/eval-reader.md:1-9`
- **Snippet:**
  ```yaml
  ---
  name: trigger-evaluator
  description: Read-only agent for trigger-evaluation reps...
  mode: primary
  steps: 3
  permission:
    skill: allow
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
  ```
- **Key aspects:** fields `name`, `description`, `mode`, optional `steps`, `permission` map; body follows as markdown.

### Pattern: campaign log conventions
- **Location:** spec at `skills/trigger-testing/SKILL.md:183-209`; real example `skills/writing-prds/test-campaigns/2026-07-30-writing-prds-trigger.md:1-58`
- **Key aspects:** filename `test-campaigns/YYYY-MM-DD-<skill-name>-trigger.md` (two-digit sequence number on same-day collision); H1 title `# Test Campaign: <skill-name> — <date>`; no YAML frontmatter; sections `## Trigger evals` (per-iteration bullets), `## Fresh-query sanity check`; campaign log is the only place trigger status lives, never referenced from SKILL.md (`skills/trigger-testing/SKILL.md:211`).

### Pattern: skills referencing companion files
- **Location:** `skills/executing-plans/SKILL.md:96`, `skills/researching-codebase/SKILL.md:82`, `skills/project-bootstrap-nix/SKILL.md:41-44`; convention at `skills/writing-skills/SKILL.md:123-132`
- **Key aspects:** heavy reference to `references/`, reusable tools to `scripts/`, referenced one level deep from SKILL.md.

### Testing Patterns
No automated test framework exists in this repo for skills. Verification convention is campaign logs (see campaign-log pattern above) plus the trigger-testing skill's own smoke-then-matrix workflow (`skills/trigger-testing/SKILL.md:18`,`:140`). The prior isolation plan's verification command is the grep-based smoke detection quoted above (`PLANS/2026-07-30-trigger-eval-read-only-agent-plan.md:200`).

### Pattern Usage Map
| Pattern | Used at |
|---------|---------|
| Standalone bash helper script | `skills/project-bootstrap-nix/scripts/bootstrap.sh` (only shipped instance) |
| `opencode run` dispatch in skills | `skills/pressure-testing/SKILL.md:94-106` |
| mktemp + jq + grep detection loop | `PLANS/2026-07-30-extract-testing-skills-plan.md:283-296` |
| grep smoke detection on JSON stream | `PLANS/2026-07-30-trigger-eval-read-only-agent-plan.md:200` |
| `<<'EOF'` heredoc | `skills/project-bootstrap-nix/scripts/bootstrap.sh:24`; spec at PRD `:21` |
| Eval-set JSON arrays | `skills/writing-prds/trigger-evals/{train,validation}.json` |
| SKILL.md two-field frontmatter | all 15 `skills/*/SKILL.md:1-4` |
| Agent frontmatter with permissions | `agents/trigger-evaluator.md:1-19`, `agents/eval-reader.md:1-9` |
| Campaign log (H1, no frontmatter, `-trigger` suffix) | `skills/writing-prds/test-campaigns/2026-07-30-writing-prds-trigger.md` |
| `scripts/` + invoke step in SKILL.md | `skills/project-bootstrap-nix/SKILL.md:41-44` |

## 5. References & Usages

### `trigger-evaluator` (agent)
- **Definition:** `agents/trigger-evaluator.md:1-31`
- **Call sites / dependents:** `skills/trigger-testing/SKILL.md:119` (dispatch target), `:128`,`:18`; discovered by opencode via `.opencode/agents/dangerpowers -> ../../agents`; referenced in `PLANS/2026-07-30-trigger-eval-read-only-agent-plan.md:32,108`

### Harness section of trigger-testing skill
- **Definition:** `skills/trigger-testing/SKILL.md:113-140`
- **Call sites / dependents:** Workflow step 3 smoke test (`skills/trigger-testing/SKILL.md:18`); Multi-Skill Campaigns regression smoke (`:162`); Common Mistakes table rows referencing harness rules (`:171`,`:174-178`); Contamination Rules (`:144-145`, which assume reps run from repo root)

### `skills/<name>/trigger-evals/` convention
- **Definition:** `skills/trigger-testing/SKILL.md:85`,`:215`
- **Call sites / dependents:** `skills/writing-prds/trigger-evals/train.json`, `skills/writing-prds/trigger-evals/validation.json` (only existing instances)

### Campaign log format (`-trigger` suffix)
- **Definition:** `skills/trigger-testing/SKILL.md:183-209`
- **Call sites / dependents:** `skills/writing-prds/test-campaigns/2026-07-30-writing-prds-trigger.md:1-58`; `skills/pressure-testing/test-campaigns/2026-07-30-trigger-testing.md`

### `.opencode` symlinks
- **Definition:** `.opencode/skills/dangerpowers -> ../../skills`, `.opencode/agents/dangerpowers -> ../../agents`
- **Call sites / dependents:** documented at `AGENTS.md:9`; the PRD's stub workspace must reproduce an equivalent discovery layout (PRD `:15`); pressure-testing's baseline relies on `--dir` outside the repo to strip skills (`skills/pressure-testing/SKILL.md:94-97`)

### `opencode run` CLI flags
- **Definition:** no CLI documentation in repo; usages at `skills/pressure-testing/SKILL.md:94-106` (`--dir`, `--agent`), `PLANS/2026-07-30-trigger-eval-read-only-agent-plan.md:108,200` (`--format json`), PRD `:19-20` (`--model`)
- **Call sites / dependents:** pressure-testing baseline/with-skill dispatch; the new harness specified by the PRD

## 6. Agent Provenance

| Sub-agent | Asked to | Outcome |
|-----------|----------|---------|
| Locator | Map trigger-testing skill, agents, .opencode wiring, scripts, artifact directories, harness-related files | Complete; found the sole scripts/ instance, symlink layout, and all prior plan artifacts |
| Analyzer | Explain current harness mechanics, trigger-evaluator agent, skill/agent discovery, shared conventions with pressure-testing, SKILL.md frontmatter format, documented opencode CLI usage | Complete; all claims cited file:line; noted current harness uses Task dispatch, not `opencode run` |
| Pattern-finder | Collect working snippets for shell scripting, heredocs, frontmatter handling, jq/grep JSON detection, campaign logs, companion-file conventions, agent frontmatter | Complete; noted no frontmatter-stripping code and no trap-based cleanup exist in the repo today |

## 7. Known Gaps

- **`opencode run` flag semantics are not documented in the repo.** `--dir`, `--agent`, `--format json` appear in skills and prior plans; `--model` appears only in the PRD. Exact JSON event-stream schema (field paths like `state.input.name`) is specified only by PRD `:24`; no captured example output exists in the repo to confirm it.
- **Frontmatter-stub generation has no existing implementation.** No awk/sed/python frontmatter extraction code exists in the repo; the stubbing mechanism must be written new.
- **No trap-based cleanup pattern exists in the repo.** FR-010 (automatic cleanup) has no local idiom to model; the only cleanup idiom is explicit `rm` (`PLANS/2026-07-30-extract-testing-skills-plan.md:294`).
- **Skill discovery layout inside a temp workspace is unverified.** The repo uses `.opencode/skills/dangerpowers -> ../../skills` symlinks; the PRD says "create a .agents under $TESTDIR" (PRD `:15`). Whether opencode discovers `.agents/skills`, `.opencode/skills`, or another layout inside `--dir` is not documented in the repo.
