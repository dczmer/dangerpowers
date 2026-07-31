---
artifact: context-bundle
date: 2026-07-31
git_commit: 72416a8169ab650a341b4e82e63a03f52bf5591a
branch: dev/sloptime
request: |
  turn this prd into a detailed implementation plan @/home/dave/source/dangerpowers/PRDS/2026-07-31-isolated-trigger-testing-harness.md
source_research: RESEARCH/2026-07-31-isolated-trigger-testing-harness-research-findings.md
source_prd: PRDS/2026-07-31-isolated-trigger-testing-harness.md
status: complete
---

# Context Bundle

## 1. Goal

Implement an isolated trigger-testing harness per the source PRD: a single command (`trigger-test.sh [--model MODEL] SCENARIO_TEXT`, PRD `PRDS/2026-07-31-isolated-trigger-testing-harness.md:13`) that runs one eval scenario inside a temporary workspace containing only frontmatter stubs of the skills plus the evaluator agent, detects the outcome mechanically from `opencode run --format json` output, surfaces conflicting skill loads, and replaces the current Task-tool-based harness inside the existing `trigger-testing` skill.

- **In scope** (PRD `:97-105`):
  - A new single-scenario trigger-test command implementing isolated, stub-based eval execution.
  - Stub generation (frontmatter-only copies) from a source skills/agents directory.
  - Mechanical outcome detection from structured eval output, including conflict surfacing.
  - Optional model selection, omitted entirely when not specified.
  - Automatic temporary-workspace lifecycle: one workspace created at campaign start, reused across all evals in the campaign, cleaned up at campaign end (FR-002, FR-010, PRD `:85`,`:93`).
  - Updating the `trigger-testing` skill to replace the current harness and commands with the new one (FR-011, PRD `:94`).
- **Out of scope** (PRD `:52-58`,`:106-111`):
  - Trigger-testing methodology: eval-set design, train/validation splits, optimization loop, done criteria.
  - Batch/multi-scenario execution (the invoking skill loops over the eval set itself).
  - Three-way outcome classification; timeouts/step-limit are not distinguished from clean no-loads (FR-012, PRD `:95`).
  - Automated description rewrites in response to detected conflicts.
  - Changes to the evaluator agent's role beyond what isolation requires.
  - Pressure-testing harness changes.
  - Preserving the temporary workspace for post-run debugging.

## 2. Files Retrieved

- `skills/trigger-testing/SKILL.md:113-140` — the Harness section to be replaced; the only harness implementation today (Task-tool dispatch, rep-message detection).
- `skills/trigger-testing/SKILL.md:1-219` — full skill; only file in `skills/trigger-testing/`, so every edit lands here. Dependent sections: Workflow step 3 smoke test (`:18`), Contamination Rules (`:142-145`), Multi-Skill Campaigns (`:158-162`), Common Mistakes (`:164-179`), Results Log Format (`:181-215`).
- `agents/trigger-evaluator.md:1-31` — the evaluator agent the harness runs under; frontmatter (`:1-19`) defines its structural isolation contract (`mode: primary`, `steps: 3`, skill-only permissions).
- `PRDS/2026-07-31-isolated-trigger-testing-harness.md:11-25` — the approved request text specifying the harness mechanics verbatim (temp workspace, `.agents` layout, stubbing, invocation flags, heredoc, JSON detection fields).
- `skills/pressure-testing/SKILL.md:87-118` — the repo's only shipped `opencode run` dispatch idiom (`--dir`, `--agent`, external-cwd permission rejection at `:106`).
- `PLANS/2026-07-30-extract-testing-skills-plan.md:283-296` — mktemp + jq + grep eval-loop skeleton over `--format json` output (plan text, never shipped).
- `PLANS/2026-07-30-trigger-eval-read-only-agent-plan.md:196-201` — grep-based smoke detection over a captured JSON stream and repo-verified validation commands.
- `.opencode/skills/dangerpowers` and `.opencode/agents/dangerpowers` — symlinks to `../../skills` and `../../agents`; the discovery layout the temp workspace must reproduce an equivalent of (PRD `:15`).
- `.opencode/opencode.jsonc:1-15` — repo opencode config (`permission: {"*": "allow"}` at `:3-5`, watcher ignores at `:6-13`).
- `skills/project-bootstrap-nix/scripts/bootstrap.sh:1-84` — the repo's only shipped standalone bash helper script in a skill's `scripts/` directory.
- `skills/writing-prds/trigger-evals/train.json:1-21`, `skills/writing-prds/trigger-evals/validation.json:1-16` — the only existing eval-set instances; consumers of the harness.

## 3. Entry / Exit Points

- **Entry (current harness):** `skills/trigger-testing/SKILL.md:113-115` — "Every query — smoke, train, validation, fresh — is dispatched to a subagent via the `Task` tool." Inputs: one eval query string. Side effects: in-process subagent session against the live repo (`:124` "Reps run from the repo root").
- **Entry (smoke test):** `skills/trigger-testing/SKILL.md:18` — Workflow step 3 dispatches ONE should-trigger query through the harness and reads the rep's returned message before full runs; also confirms the rep names the specific skill loaded.
- **Entry (PRD-specified new harness):** `PRDS/2026-07-31-isolated-trigger-testing-harness.md:13` — `trigger-test.sh [--model MODEL] SCENARIO_TEXT`. Inputs: one scenario text (direct argument via `<<'EOF'` heredoc per `:21`, or a file placed under the temp dir per `:22`) plus optional model selector omitted entirely when absent (`:20`). Outputs: binary loaded/not-loaded verdict for the target skill plus surfacing of which skill(s) actually loaded (`:23-25`). Side effects: temp workspace created once per campaign and reused across evals (`:14-16`, FR-002 `:85`), cleaned up at campaign end (FR-010 `:93`).
- **Exit (current detection):** `skills/trigger-testing/SKILL.md:130` — detection reads the rep's one-line final message naming the loaded skill or no-match; contract enforced by `agents/trigger-evaluator.md:30`.
- **Exit (PRD-specified detection):** `PRDS/2026-07-31-isolated-trigger-testing-harness.md:23-24` — parse the JSON event stream for `type=tool, tool=skill, state.input.name=SKILL_NAME` or `type=text, part.text="Skill loaded: SKILL_NAME"`; step limit or timeout without the signal counts as a failed trigger.

## 4. Key Code

### `trigger-evaluator` agent frontmatter (structural isolation contract)
- **Location:** `agents/trigger-evaluator.md:1-19`
- **Code:**
  ```yaml
  ---
  name: trigger-evaluator
  description: Read-only agent for trigger-evaluation reps. Receives one eval query per run and decides whether it triggers a skill load. The skill tool is its only tool — file, shell, web, todo, and agent tools are all denied and iterations are capped — so post-load execution is structurally impossible.
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

### SKILL.md two-field frontmatter (the stub content)
- **Location:** `skills/trigger-testing/SKILL.md:1-4`; identical structure in all 15 `skills/*/SKILL.md:1-4`
- **Code:**
  ```yaml
  ---
  name: trigger-testing
  description: Use when testing or optimizing a skill's trigger description with eval queries, train and validation splits, and detection-harness campaigns, when a new or edited description needs a passing eval set before it ships, or when running trigger-eval or trigger-test campaigns against one skill or a list of skills run sequentially.
  ---
  ```

### Eval-set JSON row format (harness input data)
- **Location:** `skills/writing-prds/trigger-evals/train.json:1-21`; format convention at `skills/trigger-testing/SKILL.md:215`
- **Code:**
  ```json
  [
    {"query": "i need to write a product requirements document for a new feature", "should_trigger": true},
    {"query": "help me write a README for this library", "should_trigger": false}
  ]
  ```

### mktemp + jq + grep eval-loop skeleton (plan text, never shipped)
- **Location:** `PLANS/2026-07-30-extract-testing-skills-plan.md:283-296`
- **Code:**
  ```bash
  SKILL="<candidate>"
  for q_set in train validation; do
    for f in trigger-evals/${q_set}/*.json; do
      while IFS=$'\t' read -r query should_trigger; do
        out=$(mktemp); opencode run --dir <repo-root> \
          --format json "$query" > "$out" 2>&1
        triggered=$(grep '"tool":"skill"' "$out" | grep -q "\"name\":\"$SKILL\"" && echo yes || echo no)
        # record (query, should_trigger, triggered)
        rm "$out"
      done < <(jq -rc '.[] | "\(.query)\t\(.should_trigger)"' "$f")
    done
  done
  ```

### grep smoke detection on a captured JSON stream
- **Location:** `PLANS/2026-07-30-trigger-eval-read-only-agent-plan.md:200`
- **Code:**
  ```bash
  opencode run --dir /home/dave/source/dangerpowers --agent trigger-evaluator --format json "write a PRD for adding a dark mode toggle to the settings page" > /tmp/opencode/trigger-smoke.json 2>&1 && grep '"tool":"skill"' /tmp/opencode/trigger-smoke.json | grep '"name":"writing-prds"'
  ```

### Standalone bash helper script conventions (only shipped instance)
- **Location:** `skills/project-bootstrap-nix/scripts/bootstrap.sh:1-84`; invoked from `skills/project-bootstrap-nix/SKILL.md:41-44`
- **Code:**
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

## 5. References & Usages

### `trigger-evaluator` (agent)
- **Definition:** `agents/trigger-evaluator.md:1-31`
- **Call sites / dependents:** `skills/trigger-testing/SKILL.md:18` (smoke test), `:119` (dispatch target), `:128` (workload isolation), `:136` (load-and-stop enforcement channel); discovered by opencode via `.opencode/agents/dangerpowers -> ../../agents`; referenced in `PLANS/2026-07-30-trigger-eval-read-only-agent-plan.md:32,108`.

### Harness section of trigger-testing skill
- **Definition:** `skills/trigger-testing/SKILL.md:113-140`
- **Call sites / dependents:** Workflow step 3 smoke test (`skills/trigger-testing/SKILL.md:18`); Multi-Skill Campaigns regression smoke (`:162`); Common Mistakes rows referencing harness rules (`:171`,`:174-178`); Contamination Rules (`:144-145`, which assume reps run from the repo root so `AGENTS.md` is in context).

### `skills/<name>/trigger-evals/` convention
- **Definition:** `skills/trigger-testing/SKILL.md:85`,`:213-215`
- **Call sites / dependents:** `skills/writing-prds/trigger-evals/train.json:1-21`, `skills/writing-prds/trigger-evals/validation.json:1-16` (only existing instances).

### Campaign log format (`-trigger` suffix)
- **Definition:** `skills/trigger-testing/SKILL.md:183-209`
- **Call sites / dependents:** `skills/writing-prds/test-campaigns/2026-07-30-writing-prds-trigger.md:1-58`; `skills/pressure-testing/test-campaigns/2026-07-30-trigger-testing.md`.

### `.opencode` symlinks (skill/agent discovery)
- **Definition:** `.opencode/skills/dangerpowers -> ../../skills`, `.opencode/agents/dangerpowers -> ../../agents`
- **Call sites / dependents:** documented at `AGENTS.md:9`; the PRD's stub workspace must reproduce an equivalent discovery layout (PRD `:15`); pressure-testing's baseline relies on `--dir` outside the repo to strip skills (`skills/pressure-testing/SKILL.md:94-97`).

### `opencode run` CLI flags
- **Definition:** no CLI documentation in repo; usages at `skills/pressure-testing/SKILL.md:94-106` (`--dir`, `--agent`), `PLANS/2026-07-30-trigger-eval-read-only-agent-plan.md:108,200` (`--format json`), PRD `:19-20` (`--model`).
- **Call sites / dependents:** pressure-testing baseline/with-skill dispatch (`skills/pressure-testing/SKILL.md:95`,`:104`); the new harness specified by the PRD.

### Blast Radius
- **Likely to change:** `skills/trigger-testing/SKILL.md` — FR-011 (PRD `:94`) requires the harness replacement to land inside this skill; its Harness section (`:113-140`), smoke test (`:18`), Contamination Rules (`:144-145`), and Common Mistakes rows (`:171`,`:174-178`) all describe the current Task-based harness.
- **Likely to change:** a new script file under `skills/trigger-testing/` — the PRD names a `trigger-test.sh` command (PRD `:13`); the repo's only precedent for skill-bundled scripts is `skills/project-bootstrap-nix/scripts/bootstrap.sh:1-84` with convention at `skills/writing-skills/SKILL.md:123-132`.
- **Possibly touched:** `agents/trigger-evaluator.md` — the temp workspace must contain the evaluator agent (FR-003, PRD `:86`); PRD non-goal forbids changes to the agent's role beyond what isolation requires (PRD `:57`).
- **Must not break:** `skills/pressure-testing/SKILL.md:87-118` — shares the `opencode run --dir/--agent` dispatch idiom and the `eval-reader`/`trigger-evaluator` agent family; PRD declares pressure-testing harness changes out of scope (PRD `:58`).
- **Must not break:** `skills/writing-prds/trigger-evals/{train,validation}.json` and `skills/writing-prds/test-campaigns/2026-07-30-writing-prds-trigger.md` — the eval-set row format (`skills/trigger-testing/SKILL.md:215`) and campaign-log format (`:183-209`) are consumed by existing artifacts.
- **Must not break:** `.opencode/skills/dangerpowers` and `.opencode/agents/dangerpowers` symlinks — `AGENTS.md:9` forbids committing the symlinks; the real files under `skills/` and `agents/` are the stub source (FR-004, PRD `:87`).
- **Transitive dependents worth attention:** `agents/eval-reader.md:1-9` — sibling agent sharing the frontmatter permission-map convention (`agents/trigger-evaluator.md:6-19`); `AGENTS.md` — Contamination Rule 2 (`skills/trigger-testing/SKILL.md:145`) treats its presence in rep context as deployment reality, which a temp workspace removes.

## 6. Patterns & Idioms

### Pattern: standalone bash helper script in a skill's `scripts/` directory
- **Location:** `skills/project-bootstrap-nix/scripts/bootstrap.sh:1-84`; pointed at from `skills/project-bootstrap-nix/SKILL.md:41-44`; convention at `skills/writing-skills/SKILL.md:123-132`
- **Snippet:** see §4.
- **Key aspects:** `set -euo pipefail`; usage errors to stderr with non-zero exit; precondition guards; quoted heredoc `<<'EOF'` writing whole files; `sed -i` placeholder substitution. Only shipped instance of `scripts/` in the repo (`skills/project-bootstrap-nix/scripts/` is the sole scripts directory).

### Pattern: `opencode run` dispatch commands embedded in a skill
- **Location:** `skills/pressure-testing/SKILL.md:93-97`,`:102-106`
- **Snippet:**
  ```bash
  opencode run --dir <empty-dir-outside-repo> "<scenario>"
  opencode run --dir <repo-root> --agent eval-reader "$(cat prepend.txt scenario.txt)"
  ```
- **Key aspects:** `--dir` for working-directory control; `--agent <name>`; command substitution for prompt assembly. Documented caveat at `:106`: from an external cwd, `Read` of repo files by absolute path hits `external_directory` permission auto-rejection. `--pure` documented as having no effect on skill stripping (`:97`).

### Pattern: grep-based detection over `--format json` output
- **Location:** `PLANS/2026-07-30-extract-testing-skills-plan.md:283-296` (eval loop), `PLANS/2026-07-30-trigger-eval-read-only-agent-plan.md:200` (smoke)
- **Snippet:** see §4.
- **Key aspects:** capture stdout+stderr to a file, grep for `"tool":"skill"` then `"name":"<candidate>"`; detection is candidate-specific, matching `skills/trigger-testing/SKILL.md:130` ("Detection must be candidate-specific"). Both are plan text, not shipped code.

### Pattern: `<<'EOF'` quoted heredoc
- **Location:** `skills/project-bootstrap-nix/scripts/bootstrap.sh:24-29`; spec at PRD `:21`
- **Key aspects:** quoted delimiter prevents shell expansion; PRD `:21` mandates it for direct-string scenarios to avoid escaping/quoting hazards.

### Pattern: eval-set JSON arrays
- **Location:** `skills/writing-prds/trigger-evals/train.json:1-21`; convention at `skills/trigger-testing/SKILL.md:215`
- **Key aspects:** flat JSON arrays of `{"query": str, "should_trigger": bool}`; committed to source control; live beside the skill under test.

### Pattern: campaign log conventions
- **Location:** spec at `skills/trigger-testing/SKILL.md:183-209`; real example `skills/writing-prds/test-campaigns/2026-07-30-writing-prds-trigger.md:1-58`
- **Key aspects:** filename `test-campaigns/YYYY-MM-DD-<skill-name>-trigger.md` (two-digit sequence on same-day collision); H1 title, no YAML frontmatter; campaign log is the only place trigger status lives, never referenced from SKILL.md (`skills/trigger-testing/SKILL.md:211`).

### Conflicting Variations

- **Rep dispatch mechanism.**
  - **Variation A:** `skills/trigger-testing/SKILL.md:115-122` — in-process `Task` tool calls to the `trigger-evaluator` subagent, bare-query prompt, no `task_id`. Evidence: the shipped harness, in the skill today.
  - **Variation B:** `PRDS/2026-07-31-isolated-trigger-testing-harness.md:19` — external `opencode run --dir "$TEMPDIR" --agent trigger-evaluator --format json` subprocess; same shape as pressure-testing's shipped dispatch at `skills/pressure-testing/SKILL.md:95`,`:104`.
  - **Conflict:** the PRD (FR-011, `:94`) requires replacing A with B inside the skill; the skill's smoke test (`:18`) and Common Mistakes rows (`:174-178`) are written against A.

- **Rep working directory / context.**
  - **Variation A:** `skills/trigger-testing/SKILL.md:124` — "Reps run from the repo root"; Contamination Rule 2 (`:145`) states repo `AGENTS.md` loads in every rep and must not be stripped, as "part of the deployment reality for this repo's skill library."
  - **Variation B:** `PRDS/2026-07-31-isolated-trigger-testing-harness.md:12,14` — evals run from a temporary workspace containing only stubs, isolated from the real repository (FR-002, `:85`).
  - **Conflict:** B removes `AGENTS.md` and the real codebase from rep context; Rule 2's rationale (constant across iterations, deployment reality) was written for A. Recorded absolute trigger rates (e.g. `skills/writing-prds/test-campaigns/2026-07-30-writing-prds-trigger.md`) were measured under A.

- **Outcome detection channel.**
  - **Variation A:** `skills/trigger-testing/SKILL.md:130` — read the rep's one-line final message; enforced by the agent definition `agents/trigger-evaluator.md:30`.
  - **Variation B:** `PRDS/2026-07-31-isolated-trigger-testing-harness.md:24` — parse the JSON event stream for `type=tool, tool=skill, state.input.name=SKILL_NAME` or `type=text, part.text="Skill loaded: SKILL_NAME"`; grep-based precedent at `PLANS/2026-07-30-trigger-eval-read-only-agent-plan.md:200`.
  - **Conflict:** A depends on agent compliance; B is mechanical. The smoke test's second job (`skills/trigger-testing/SKILL.md:18` — "detection under this harness is the rep's own report (not a greppable event stream)") is explicitly predicated on A.

- **Temp-file cleanup.**
  - **Variation A:** `PLANS/2026-07-30-extract-testing-skills-plan.md:294` — explicit `rm "$out"` after each read. Evidence: the only cleanup idiom in the repo; plan text, never shipped.
  - **Variation B:** none — no `trap`-based cleanup exists anywhere in the repo (research §7, `RESEARCH/2026-07-31-isolated-trigger-testing-harness-research-findings.md:256`).
  - **Conflict:** FR-010 (PRD `:93`) requires automatic workspace cleanup at campaign end; no local idiom models automatic cleanup.

- **Skill/agent discovery layout inside the temp workspace.**
  - **Variation A:** repo reality — `.opencode/skills/dangerpowers -> ../../skills` and `.opencode/agents/dangerpowers -> ../../agents` namespaced symlinks (`AGENTS.md:9`).
  - **Variation B:** PRD `:15` — "create a .agents under $TESTDIR directory with skills/ and agents/ subdirectories."
  - **Conflict:** the names differ (`.opencode` vs `.agents`) and which layout opencode discovers inside `--dir` is not documented in the repo (research §7, `RESEARCH/2026-07-31-isolated-trigger-testing-harness-research-findings.md:257`).

## 7. Testing

- **How similar code is tested:** no automated test framework exists in this repo for skills. Verification convention is campaign logs (`skills/trigger-testing/SKILL.md:183-209`; example `skills/writing-prds/test-campaigns/2026-07-30-writing-prds-trigger.md:1-58`) plus the trigger-testing skill's smoke-then-matrix workflow (`skills/trigger-testing/SKILL.md:18`,`:140`).
- **Tests covering affected code:** none found for `skills/trigger-testing/SKILL.md`, `agents/trigger-evaluator.md`, or any harness code.
- **Validation commands** (verified against the repo):
  - `agentskills validate skills/trigger-testing` — from `PLANS/2026-07-30-trigger-eval-read-only-agent-plan.md:198`; convention "must print `Valid skill`" at `skills/writing-skills/SKILL.md:70`. The `agentskills` executable is provided by the `skills-ref` dependency (`pyproject.toml:9`) installed in `.venv` by the dev shell (`flake.nix:36-40`); present at `.venv/bin/agentskills`.
  - `opencode run --dir /home/dave/source/dangerpowers --agent trigger-evaluator --format json "<query>" > /tmp/opencode/trigger-smoke.json 2>&1 && grep '"tool":"skill"' /tmp/opencode/trigger-smoke.json | grep '"name":"<skill>"'` — grep smoke detection, from `PLANS/2026-07-30-trigger-eval-read-only-agent-plan.md:200`.
  - `git status --porcelain` — from `PLANS/2026-07-30-trigger-eval-read-only-agent-plan.md:201` (verifies no workload executed).
  - `jq` is available in the dev shell (`flake.nix:21`) for JSON event-stream parsing.
  - No `package.json`, `Makefile`, or CI config exists in this repo; no lint/typecheck scripts exist for shell/markdown content.

## 8. Constraints & Risks

### Invariants the plan must respect
- **Evaluator agent contract:** `agents/trigger-evaluator.md:1-19` — `mode: primary`, `steps: 3`, only tool `skill`, all other tools denied. The harness's workload isolation is structural via this definition (`skills/trigger-testing/SKILL.md:128`,`:138`); the temp workspace must carry this agent (FR-003, PRD `:86`), and PRD non-goal limits changes to its role (PRD `:57`).
- **Candidate-specific detection:** `skills/trigger-testing/SKILL.md:130` — a sibling skill firing is a FAIL for the candidate, not a pass; PRD `:24-25` carries the same requirement into JSON detection plus conflict surfacing (FR-009, `:92`).
- **Bare-query dispatch:** `skills/trigger-testing/SKILL.md:126` — the dispatch prompt contains only the eval query; no framing, skill names, or test indication. Applies to however the scenario reaches the evaluator (PRD `:21-22`).
- **Rep independence:** `skills/trigger-testing/SKILL.md:122`,`:132` — every rep is a fresh session; workspace reuse across evals "must not change any eval's outcome relative to running it alone" (PRD `:130`).
- **Description YAML safety:** `skills/trigger-testing/SKILL.md:42` and `skills/writing-skills/SKILL.md:66-70` — plain scalar, no colon+space, 1024-char hard limit; `agentskills validate skills/<name>` must print `Valid skill` (`skills/writing-skills/SKILL.md:70`). Stub generation must preserve frontmatter verbatim (PRD `:17`).
- **Eval-set format:** `skills/trigger-testing/SKILL.md:215` — JSON arrays of `{"query": str, "should_trigger": bool}` at `skills/<skill-name>/trigger-evals/`; existing instances at `skills/writing-prds/trigger-evals/`.
- **Campaign log conventions:** `skills/trigger-testing/SKILL.md:183-211` — `-trigger` suffix, H1 no frontmatter, status lives only in logs, never in SKILL.md (`:211`).
- **Symlink policy:** `AGENTS.md:9` — never commit `.opencode` symlinks; commit real files under `skills/` and `agents/`.
- **Repo opencode config coupling:** `.opencode/opencode.jsonc:3-5` — `permission: {"*": "allow"}` applies at the repo root; a temp workspace outside the repo does not inherit this config (research §3, `RESEARCH/2026-07-31-isolated-trigger-testing-harness-research-findings.md:78`).
- **External-directory permission boundary:** `skills/pressure-testing/SKILL.md:106` — opencode rejects access to files outside the run's `--dir`; this is why PRD `:22` requires scenario files to live under the temp dir.
- **Fail loudly on bad sources:** PRD `:129` — missing or malformed skills in the source directory must fail the harness, not run against a partial stub set.

### Dependencies / ordering
- Stub generation depends on the source directory layout (`skills/`, `agents/` real files; FR-004, PRD `:87`) and on the discovery layout the temp workspace must present (unverified — see risks).
- The `trigger-testing` skill update (FR-011) depends on the harness command existing; the skill's smoke test (`skills/trigger-testing/SKILL.md:18`), Contamination Rules (`:144-145`), and Common Mistakes (`:171`,`:174-178`) reference harness mechanics and stay consistent only if updated together.
- `jq` and `opencode` (1.18.3) are present in the dev environment (`flake.nix:21`; `agentskills` at `.venv/bin/agentskills` via `pyproject.toml:9`).

### Likely failure modes (evidence-backed)
- **`opencode run` flag semantics unverified.** `--dir`, `--agent`, `--format json` appear only in skill text and prior plans (`skills/pressure-testing/SKILL.md:94-106`; `PLANS/2026-07-30-trigger-eval-read-only-agent-plan.md:108,200`); `--model` appears only in the PRD (`PRDS/2026-07-31-isolated-trigger-testing-harness.md:19-20`). The JSON event-stream schema (`state.input.name`, `part.text`) is specified only by PRD `:24`; no captured example output exists in the repo to confirm field paths (research §7, `RESEARCH/2026-07-31-isolated-trigger-testing-harness-research-findings.md:254`). Detection written against an unconfirmed schema can silently report every eval as not-loaded.
- **No frontmatter-stub generation implementation exists.** No awk/sed/python frontmatter extraction code exists in the repo; the stubbing mechanism must be written new (research §7, `RESEARCH/2026-07-31-isolated-trigger-testing-harness-research-findings.md:255`). Malformed stubs risk violating the YAML-safety constraints (`skills/writing-skills/SKILL.md:66-70`) or leaking body content, which is the failure the PRD exists to prevent (PRD `:35-40`).
- **No automatic-cleanup idiom.** FR-010 (PRD `:93`) has no local pattern to model; the only cleanup idiom is explicit `rm` (`PLANS/2026-07-30-extract-testing-skills-plan.md:294`); no `trap`-based cleanup exists anywhere in the repo (research §7, `RESEARCH/2026-07-31-isolated-trigger-testing-harness-research-findings.md:256`).
- **Temp-workspace discovery layout unverified.** The repo discovers skills/agents via `.opencode/skills/dangerpowers -> ../../skills` namespaced symlinks (`AGENTS.md:9`); the PRD says "create a .agents under $TESTDIR" (PRD `:15`). Whether opencode discovers `.agents/skills`, `.opencode/skills`, or another layout inside `--dir` is not documented in the repo (research §7, `RESEARCH/2026-07-31-isolated-trigger-testing-harness-research-findings.md:257`). A wrong layout yields evals with zero skills visible — indistinguishable from all-negative results under FR-008 (PRD `:91`).
- **Baseline comparability shift.** Recorded campaign results (e.g. `skills/writing-prds/test-campaigns/2026-07-30-writing-prds-trigger.md:1-58`) were measured with reps running from the repo root with `AGENTS.md` in context (`skills/trigger-testing/SKILL.md:124`,`:145`); the isolated workspace removes both, so absolute trigger rates under the new harness may not compare to recorded ones.

### Conflicting findings
- Dispatch mechanism, rep working directory, detection channel, cleanup idiom, and discovery layout conflicts are each shown with both sides cited in §6 Conflicting Variations. No averaging applied; the picks belong to the planner.

## 9. Open Questions

- `[needs-deeper-research]` — What are the exact semantics of `opencode run` flags `--dir`, `--agent`, `--format json`, and `--model`, and what is the exact JSON event-stream schema (field paths for tool events and text parts)? `--model` and the schema are specified only by the PRD (`PRDS/2026-07-31-isolated-trigger-testing-harness.md:19-24`); no repo documentation or captured example output exists (`RESEARCH/2026-07-31-isolated-trigger-testing-harness-research-findings.md:254`). Not resolved here per phase instructions; answering requires opencode documentation or an empirical run.
- `[needs-deeper-research]` — Which directory layout does opencode discover for skills and agents inside a `--dir` workspace: `.agents/skills` + `.agents/agents` (PRD `:15`), `.opencode/skills` + `.opencode/agents` (repo layout, `AGENTS.md:9`), or either? Undocumented in the repo (`RESEARCH/2026-07-31-isolated-trigger-testing-harness-research-findings.md:257`).
- `[needs-deeper-research]` — Does an agent definition copied into a temp workspace retain its `permission` map and `steps` cap when the repo's `opencode.jsonc` (`permission: {"*": "allow"}`, `.opencode/opencode.jsonc:3-5`) is absent, or does the workspace need its own config? No repo evidence either way.
- `[needs-deeper-research]` — What mechanism should generate frontmatter-only stubs (no existing implementation, `RESEARCH/2026-07-31-isolated-trigger-testing-harness-research-findings.md:255`) and what automatic-cleanup mechanism satisfies FR-010 given no `trap` idiom exists locally (`RESEARCH/2026-07-31-isolated-trigger-testing-harness-research-findings.md:256`)? Both are implementation choices with no repo precedent to cite.

## 10. Start Here

- **Start:** `skills/trigger-testing/SKILL.md` — FR-011 (PRD `:94`) requires the harness replacement to land inside this skill, and it is the only file in `skills/trigger-testing/` (research §2, `RESEARCH/2026-07-31-isolated-trigger-testing-harness-research-findings.md:24`). Its Harness section (`:113-140`) is the code being replaced, and four other sections — smoke test (`:18`), Contamination Rules (`:144-145`), Multi-Skill regression smoke (`:162`), Common Mistakes (`:171`,`:174-178`) — depend on harness mechanics and define the consistency surface any plan must account for. Every other affected file (`agents/trigger-evaluator.md`, the new script, the eval-set consumers) is reachable from references inside this file.
