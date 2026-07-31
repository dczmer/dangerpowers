---
artifact: implementation-plan
date: 2026-07-31
git_commit: 72416a8169ab650a341b4e82e63a03f52bf5591a
branch: dev/sloptime
request: |
  turn this prd into a detailed implementation plan @/home/dave/source/dangerpowers/PRDS/2026-07-31-isolated-trigger-testing-harness.md
source_prd: PRDS/2026-07-31-isolated-trigger-testing-harness.md
source_bundle: RESEARCH/2026-07-31-isolated-trigger-testing-harness-context-bundle.md
source_research: RESEARCH/2026-07-31-isolated-trigger-testing-harness-research-findings.md
status: approved
---

# Isolated Trigger-Testing Harness Implementation Plan

> **For the implementing agent:** Read this plan and the provenance artifacts in References before starting. After each phase, run all automated verification; when it passes, pause for human confirmation of the manual criteria before starting the next phase.

## Context

Trigger-testing measures whether a skill's description causes the agent to load that skill for a given scenario phrase. The current harness dispatches in-process `Task`-tool reps to the `trigger-evaluator` subagent against the live repo (`skills/trigger-testing/SKILL.md:113-140`). This fails in both directions: when the skill loads, its body starts the real workflow and the eval never yields a clean verdict; when it doesn't load, the rep derails into codebase analysis or user interviews, hangs, or hits its step limit (PRD `PRDS/2026-07-31-isolated-trigger-testing-harness.md:35-38`). The root cause is that reps see real skill bodies in a real working directory. The fix: run each eval in an isolated temporary workspace where skills exist only as frontmatter stubs, detect the outcome mechanically from the run's JSON event stream, and surface conflicting skill loads — packaged as a single command, `trigger-test.sh`, that replaces the current harness inside the existing `trigger-testing` skill.

## Current State

- The harness to be replaced lives at `skills/trigger-testing/SKILL.md:113-140` (Task-tool dispatch, rep-message detection); dependent sections: smoke test (`:18`), Contamination Rules (`:142-145`), Multi-Skill regression smoke (`:162`), Common Mistakes (`:171`,`:174-178`).
- The evaluator agent is `agents/trigger-evaluator.md:1-19` — `mode: primary`, `steps: 3`, only tool `skill`, everything else denied. Its contract is unchanged by this plan.
- The repo's only shipped standalone bash helper is `skills/project-bootstrap-nix/scripts/bootstrap.sh:1-84` (`set -euo pipefail`, usage to stderr, `<<'EOF'` heredocs) — the script convention this plan follows.
- The repo's only shipped `opencode run` dispatch idiom is `skills/pressure-testing/SKILL.md:93-106` (`--dir`, `--agent`). A grep-based JSON-stream detection precedent exists as plan text at `PLANS/2026-07-30-trigger-eval-read-only-agent-plan.md:200`.
- Skill/agent discovery in the repo works via namespaced symlinks `.opencode/skills/dangerpowers -> ../../skills` and `.opencode/agents/dangerpowers -> ../../agents` (`AGENTS.md:9`).
- Verified during planning against the installed CLI (opencode 1.18.3) and https://opencode.ai/docs:
  - `opencode run --help` confirms `--dir`, `--agent`, `--model` (`provider/model` format), `--format json` ("raw JSON events"), and `--auto` (auto-approve permissions not explicitly denied).
  - Skills docs: project skills are discovered at `.opencode/skills/<name>/SKILL.md`, `.claude/skills/<name>/SKILL.md`, and `.agents/skills/<name>/SKILL.md`; skill `name` must match its directory; global skills at `~/.config/opencode/skills`, `~/.claude/skills`, `~/.agents/skills` load in every run.
  - Agents docs: project agents are discovered at `.opencode/agents/<name>.md` (no `.agents/agents` path is documented); the markdown frontmatter `permission` map and `steps` cap are honored per agent.
- Not yet verified (built into Phase 1 as empirical checkpoints): the exact JSON event-stream schema (field paths for tool events and text parts — no captured example exists in the repo, research §7), whether a non-git temp dir is scanned for project skills, and whether the agent's permission map behaves identically without the repo's `opencode.jsonc` (`permission: {"*": "allow"}`, `.opencode/opencode.jsonc:3-5`).
- No frontmatter-stub generation or `trap`-based cleanup code exists anywhere in the repo (research §7); both are written new in Phase 2.
- Validation tooling: `agentskills` at `.venv/bin/agentskills` (via `pyproject.toml:9`), `jq`, `bash`, `realpath`, `mktemp`, `timeout` all present in the dev shell (`flake.nix:21`).

## Desired End State

- `skills/trigger-testing/scripts/trigger-test.sh` exists and runs one scenario per invocation in an isolated stub-only workspace, printing a machine-readable verdict block (`verdict: loaded | not-loaded` plus conflict surfacing).
- One command produces a loaded/not-loaded verdict for a target skill with no manual transcript inspection; known-trigger scenarios report loaded, known-negatives report not-loaded.
- No eval run can execute any workflow step (stubs have no bodies) or derail into codebase analysis (the workspace has no codebase).
- Runs that load the wrong skill or multiple skills visibly report which skills loaded.
- A campaign creates exactly one workspace regardless of eval count, reuses it for every eval, and leaves no workspace artifacts after it ends.
- The `trigger-testing` skill's full campaign flow executes entirely through the new harness with no remaining references to the Task-tool harness.
- Verification: the Final Verification commands below all pass; `agentskills validate skills/trigger-testing` prints `Valid skill`.

## What We're NOT Doing

- Changing trigger-testing methodology: eval-set design, train/validation splits, the optimization loop, done criteria.
- Batch or multi-scenario execution (the invoking skill loops over the eval set itself).
- Distinguishing timeout/step-limit failures from clean no-loads in the verdict (verdict stays binary).
- Automatically rewriting conflicting skill descriptions; the harness only surfaces conflicts.
- Changes to the `trigger-evaluator` agent's role, permissions, or step cap beyond copying it into the workspace.
- Pressure-testing harness changes (`skills/pressure-testing/SKILL.md` untouched).
- Preserving the temporary workspace for post-run debugging.
- Touching `.opencode/` symlinks, `AGENTS.md`, or any skill other than `trigger-testing`.

## Decisions

| Conflict / Question | Pick | Rationale |
|---------------------|------|-----------|
| Rep dispatch: in-process `Task` calls (`skills/trigger-testing/SKILL.md:115-122`) vs external `opencode run` subprocess (PRD `:19`, same shape as `skills/pressure-testing/SKILL.md:95,104`) | `opencode run --dir <workspace> --agent trigger-evaluator --format json` subprocess | PRD mandates replacement; in-process reps see real skill bodies and share the runner's context — the exact failure the PRD exists to fix (PRD `:35-40`). |
| Rep working directory/context: repo root with `AGENTS.md` (`skills/trigger-testing/SKILL.md:124,145`) vs isolated stub workspace (PRD `:12,14`) | Isolated stub workspace | PRD mandates isolation. Contamination Rule 2 is rewritten; recorded pre-isolation trigger rates are declared a different measurement regime, not a baseline (bundle §8 risk). |
| Outcome detection: rep's one-line final message (`skills/trigger-testing/SKILL.md:130`) vs JSON event-stream parse (PRD `:24`) | JSON event-stream parse, with the agent's `Skill loaded: <name>` text report kept as a secondary signal | Mechanical detection removes agent-compliance dependence (PRD `:23-24`); the text fallback preserves the existing agent contract (`agents/trigger-evaluator.md:30`) as belt-and-suspenders. |
| Workspace cleanup: explicit `rm` idiom (only repo precedent, `PLANS/2026-07-30-extract-testing-skills-plan.md:294`) vs `trap` (no repo precedent) | Explicit `init`/`cleanup` subcommands; the skill workflow mandates cleanup at campaign end including on abort; per-rep output files live inside the workspace and die with it | A `trap` inside a single-eval script would destroy the shared workspace after one eval, violating one-workspace-per-campaign. Cleanup belongs to the campaign lifecycle, which the invoking skill owns; explicit subcommands are auditable and satisfy automatic cleanup via the workflow contract. |
| Temp-workspace discovery layout: `.opencode/skills` (repo reality) vs `.agents/skills` (PRD `:15`) | `.agents/skills/<name>/SKILL.md` for stubs; `.opencode/agents/trigger-evaluator.md` for the agent | Both are documented discovery paths (opencode skills/agents docs); `.agents/skills` matches the PRD verbatim, and `.opencode/agents` is the only documented project-agent path. Phase 1 Checkpoint B empirically confirms against opencode 1.18.3 with defined fallbacks (`.opencode/skills`, then `git init` in the workspace) before Phase 2 begins. |
| Stub-generation mechanism (no repo precedent, research §7) | `awk` extractor that prints the frontmatter block verbatim (both `---` delimiters), failing on missing/unterminated frontmatter, plus a `name:`-matches-directory check | Frontmatter-only stubs must preserve the block verbatim (PRD `:17`) and opencode requires `name` to match the directory (skills docs); fail-loud on malformed sources is required (PRD `:129`). |
| Target-skill identification: PRD command shape `trigger-test.sh [--model MODEL] SCENARIO_TEXT` carries no target | Required `--skill NAME` option in eval mode | Candidate-specific detection (invariant, `skills/trigger-testing/SKILL.md:130`) is impossible without the target name; the PRD's "something like" phrasing (`:13`) permits the addition. |
| Scenario-file handling (PRD `:22`) | `--scenario-file PATH`; script validates the realpath is inside the workspace (rejects otherwise) and passes the file's contents as the eval message | Satisfies the in-workspace requirement literally and keeps the bare-query rule: the evaluator receives only the query text, never a path or framing. |
| Run-away eval protection | `timeout 300` wraps the `opencode run` invocation; on timeout there is no load signal, so the verdict is not-loaded | Matches the binary-verdict rule (timeout/step-limit count as failed trigger, PRD `:23`) while guaranteeing a hung run cannot hang the campaign. `timeout` is coreutils, present in the dev shell. |
| Global-skill leakage into the workspace (`~/.config/opencode/skills` etc. always load, per skills docs) | Accept and surface: non-repo skill loads appear in `loaded_skills`; the rewritten Contamination Rule 3 requires recording them in the campaign log as environmental noise | opencode strips globals only via unsupported hacks (`--pure` has no effect on skill stripping, `skills/pressure-testing/SKILL.md:97`); conflict surfacing (PRD `:25`) already covers the observability requirement. Phase 1 Checkpoint D measures whether any globals actually leak. |

## Implementation Approach

Three sequential phases. Phase 1 empirically pins the four facts the repo cannot document (JSON event schema, temp-workspace discovery layout, agent-permission behavior without repo config, global-skill leakage) using live `opencode run` spikes under `/tmp`, with explicit checkpoints and fallbacks; it touches no repo files. Phase 2 writes the harness script `skills/trigger-testing/scripts/trigger-test.sh` — `init` (mktemp workspace + awk stub generation + agent copy), `eval` (heredoc-safe scenario dispatch, optional model, jq-based mechanical detection, conflict surfacing, timeout guard), and `cleanup` (guarded removal) — and verifies it against known-trigger and known-negative scenarios. Phase 3 rewrites the harness-dependent sections of `skills/trigger-testing/SKILL.md` (Workflow, Harness, Contamination Rules, Multi-Skill smoke, Common Mistakes) to drive all evals through the script, then validates the skill and runs an integrated smoke through the updated workflow. The phases are strictly ordered: Phase 2 consumes Phase 1's verified facts, and Phase 3's verification runs against the integrated result.

## Phase 1: Verify opencode CLI Behavior Empirically

### Overview

Resolve the four bundle §9 items that require live verification before any code is written: the `--format json` event schema, the discovery layout opencode 1.18.3 honors inside a `--dir` temp workspace, the evaluator agent's permission behavior without the repo's `opencode.jsonc`, and global-skill leakage. All work happens in scratch directories under `/tmp`; this phase changes no repo files. Findings are recorded in the phase report; Phase 2 assumes the defaults below and adjusts only the isolated constants/jq selectors named here if a checkpoint falsifies them.

**Parallel group:** none

**Execution:** subagent

### Changes Required

No repo files. Scratch only: `/tmp/opencode/trigger-schema-spike.json`, `/tmp/opencode/trigger-layout-spike.json`, and a `mktemp -d /tmp/trigger-layout-spike.XXXXXXXXXX` workspace.

#### 1. JSON event-schema spike (Checkpoint A)
**Commands**:
```bash
opencode --version
opencode run --dir /home/dave/source/dangerpowers --agent trigger-evaluator --format json "i need to write a product requirements document for a new feature" > /tmp/opencode/trigger-schema-spike.json 2>&1
grep '"tool":"skill"' /tmp/opencode/trigger-schema-spike.json
jq -c 'select(.type=="tool")' /tmp/opencode/trigger-schema-spike.json
jq -c 'select(.type=="text")' /tmp/opencode/trigger-schema-spike.json
```
**Record**: whether the stream is one JSON object per line (line-delimited `jq` works); the exact field path of the tool name (expected `.tool` or `.part.tool`); the exact field path of the skill input name (expected `.state.input.name` or `.part.state.input.name`); the exact field path of text content (expected `.text` or `.part.text`). These three paths are the only schema facts Phase 2's jq filter depends on; the filter in Phase 2 is written to match both documented nestings, so a falsification here means editing those selectors only.

#### 2. Discovery-layout spike (Checkpoint B)
**Commands**:
```bash
WS_SPIKE=$(mktemp -d /tmp/trigger-layout-spike.XXXXXXXXXX)
mkdir -p "$WS_SPIKE/.agents/skills/writing-prds" "$WS_SPIKE/.opencode/agents"
awk 'NR==1 { if ($0 != "---") exit 1; print; next } { print; if ($0 == "---") { found=1; exit } } END { if (!found) exit 1 }' /home/dave/source/dangerpowers/skills/writing-prds/SKILL.md > "$WS_SPIKE/.agents/skills/writing-prds/SKILL.md"
cp /home/dave/source/dangerpowers/agents/trigger-evaluator.md "$WS_SPIKE/.opencode/agents/trigger-evaluator.md"
opencode run --dir "$WS_SPIKE" --agent trigger-evaluator --format json "i need to write a product requirements document for a new feature" > /tmp/opencode/trigger-layout-spike.json 2>&1
grep '"name":"writing-prds"' /tmp/opencode/trigger-layout-spike.json
```
**Record**: whether the stub skill was visible and loaded, and whether `--agent trigger-evaluator` resolved from `.opencode/agents/`. Fallback ladder if the load signal is absent: (1) retry with the stub at `.opencode/skills/writing-prds/SKILL.md` instead of `.agents/skills/`; (2) if still absent, run `git init "$WS_SPIKE"` (make the workspace a git worktree, per the docs' walk-up-to-worktree discovery) and retry; (3) if the agent name is unrecognized, confirm `trigger-evaluator.md` frontmatter parses. Record the winning combination. If no combination works, STOP and report — the plan needs amendment before Phase 2.

#### 3. Permission behavior without repo config (Checkpoint C)
Read directly from the layout spike: the spike workspace has no `opencode.jsonc`. **Record**: whether the run completed non-interactively without permission prompts blocking (expected: the agent's own frontmatter `permission` map applies, `skill: allow` loads immediately, everything else is denied). If a prompt blocks the run, retry once with `--auto` appended and record that Phase 2 must add `--auto` to the invocation.

#### 4. Global-skill leakage (Checkpoint D)
**Command**:
```bash
grep -o '"name":"[a-z0-9-]*"' /tmp/opencode/trigger-layout-spike.json | sort -u
```
**Record**: any skill names in the stream other than `writing-prds` — these are globally installed skills leaking into the workspace, and Phase 3's Contamination Rule 3 (already written to handle this) applies.

#### 5. Model-flag acceptance (Checkpoint E)
**Commands**:
```bash
opencode models
opencode run --dir "$WS_SPIKE" --agent trigger-evaluator --format json --model "$(opencode models | head -1)" "help me write a README for this library" > /tmp/opencode/trigger-model-spike.json 2>&1
```
**Record**: that `--model` is accepted in `provider/model` form and the run completes. Clean up: `rm -rf "$WS_SPIKE"`.

### Success Criteria

#### Automated Verification:
- [ ] CLI identity confirmed: `opencode --version` prints `1.18.3`
- [ ] Schema spike produced a load signal: `grep -q '"tool":"skill"' /tmp/opencode/trigger-schema-spike.json && grep -q '"name":"writing-prds"' /tmp/opencode/trigger-schema-spike.json && echo SCHEMA-SPIKE-OK`
- [ ] Layout spike produced a load signal (after the fallback ladder if needed): `grep -q '"name":"writing-prds"' /tmp/opencode/trigger-layout-spike.json && echo LAYOUT-SPIKE-OK`
- [ ] Model flag accepted: `test -s /tmp/opencode/trigger-model-spike.json && echo MODEL-SPIKE-OK`

#### Manual Verification:
- [ ] Phase report records the three JSON field paths from Checkpoint A verbatim
- [ ] Phase report records the winning discovery layout from Checkpoint B (or the stop-and-report escalation)
- [ ] Phase report records whether `--auto` was needed (Checkpoint C) and which global skills, if any, leaked (Checkpoint D)

**Implementation Note**: After completing this phase and all automated verification passes, pause for human confirmation of the manual criteria before proceeding to the next phase.

---

## Phase 2: Implement the trigger-test.sh Harness Script

### Overview

Create `skills/trigger-testing/scripts/trigger-test.sh` implementing the full harness: workspace `init` with frontmatter-only stub generation and fail-loud source validation, single-scenario `eval` with mechanical JSON detection and conflict surfacing, and guarded `cleanup`. Uses the Phase-1-verified discovery layout (default `.agents/skills` + `.opencode/agents`) and JSON field paths (filter written against both documented nestings; adjust selectors only if Checkpoint A falsified them). Adds `--auto` to the invocation only if Checkpoint C required it.

**Parallel group:** none

**Execution:** subagent

### Changes Required

#### 1. The harness script
**File**: `skills/trigger-testing/scripts/trigger-test.sh` (new file, executable)
**Changes**: create with this exact content:

```bash
#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
usage:
  trigger-test.sh init [--source DIR]
  trigger-test.sh eval --skill NAME [--workspace DIR] [--model PROVIDER/MODEL] [--scenario-file PATH] [SCENARIO_TEXT]
  trigger-test.sh cleanup [--workspace DIR]

init    creates one campaign workspace and prints its path on stdout:
        frontmatter-only stubs of every skills/<name>/SKILL.md under SOURCE
        go to WORKSPACE/.agents/skills/<name>/SKILL.md, and
        SOURCE/agents/trigger-evaluator.md is copied to
        WORKSPACE/.opencode/agents/. SOURCE defaults to the repository
        root containing this script.
eval    runs one scenario in the workspace and prints a verdict block:
          verdict: loaded | not-loaded
          target: <skill>
          loaded_skills: <comma-separated names, or none>
          conflict: none | wrong-skill | additional-skills
          conflict_skills: <comma-separated names, or none>
        The workspace comes from --workspace or $TRIGGER_TEST_WORKSPACE.
cleanup removes the workspace (--workspace or $TRIGGER_TEST_WORKSPACE).
EOF
  exit 1
}

extract_frontmatter() {
  awk '
    NR==1 { if ($0 != "---") exit 1; print; next }
    { print; if ($0 == "---") { found=1; exit } }
    END { if (!found) exit 1 }
  ' "$1"
}

cmd_init() {
  local source=""
  while [ $# -gt 0 ]; do
    case "$1" in
      --source) source="$2"; shift 2 ;;
      *) usage ;;
    esac
  done
  if [ -z "$source" ]; then
    source="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
  fi
  [ -d "$source/skills" ] || { echo "error: no skills/ directory under source: $source" >&2; exit 1; }
  [ -f "$source/agents/trigger-evaluator.md" ] || { echo "error: missing agent definition: $source/agents/trigger-evaluator.md" >&2; exit 1; }

  local ws
  ws="$(mktemp -d /tmp/trigger-test.XXXXXXXXXX)"
  mkdir -p "$ws/.agents/skills" "$ws/.opencode/agents"

  local count=0 skill_dir name src
  for skill_dir in "$source"/skills/*/; do
    src="$skill_dir/SKILL.md"
    [ -f "$src" ] || { echo "error: missing SKILL.md in $skill_dir" >&2; exit 1; }
    name="$(basename "$skill_dir")"
    mkdir -p "$ws/.agents/skills/$name"
    if ! extract_frontmatter "$src" > "$ws/.agents/skills/$name/SKILL.md"; then
      echo "error: missing or unterminated frontmatter in $src" >&2; exit 1
    fi
    grep -q "^name: $name\$" "$ws/.agents/skills/$name/SKILL.md" \
      || { echo "error: frontmatter name does not match directory in $src" >&2; exit 1; }
    count=$((count + 1))
  done
  [ "$count" -gt 0 ] || { echo "error: no skills found under $source/skills" >&2; exit 1; }

  cp "$source/agents/trigger-evaluator.md" "$ws/.opencode/agents/trigger-evaluator.md"
  echo "$ws"
}

cmd_eval() {
  local skill="" ws="" model="" scenario_file="" scenario=""
  while [ $# -gt 0 ]; do
    case "$1" in
      --skill) skill="$2"; shift 2 ;;
      --workspace) ws="$2"; shift 2 ;;
      --model) model="$2"; shift 2 ;;
      --scenario-file) scenario_file="$2"; shift 2 ;;
      -*) usage ;;
      *) scenario="$1"; shift ;;
    esac
  done
  [ -n "$skill" ] || { echo "error: --skill NAME is required" >&2; usage; }
  ws="${ws:-${TRIGGER_TEST_WORKSPACE:-}}"
  [ -n "$ws" ] && [ -d "$ws/.agents/skills/$skill" ] \
    || { echo "error: workspace unset or has no stub for skill '$skill': ${ws:-<unset>}" >&2; exit 1; }

  if [ -n "$scenario_file" ]; then
    local real_ws real_file
    real_ws="$(realpath "$ws")"
    real_file="$(realpath "$scenario_file")"
    case "$real_file" in
      "$real_ws"/*) ;;
      *) echo "error: scenario file must reside inside the workspace: $scenario_file" >&2; exit 1 ;;
    esac
    scenario="$(cat -- "$scenario_file")"
  fi
  [ -n "$scenario" ] || { echo "error: no scenario text provided" >&2; usage; }

  local model_args=()
  [ -n "$model" ] && model_args=(--model "$model")

  local out="$ws/.trigger-test-last-run.jsonl"
  local rc=0
  timeout 300 opencode run --dir "$ws" --agent trigger-evaluator --format json \
    ${model_args[@]+"${model_args[@]}"} "$scenario" > "$out" 2>&1 || rc=$?

  local loaded
  loaded="$(jq -rs '
    [ .[] | .. | objects
      | select(.type? == "tool")
      | select((.tool? // .part?.tool?) == "skill")
      | (.state?.input?.name // .part?.state?.input?.name)
      | strings ]
    + [ .[] | .. | objects
      | select(.type? == "text")
      | (.text? // .part?.text?)
      | strings
      | select(startswith("Skill loaded: "))
      | ltrimstr("Skill loaded: ") ]
    | unique
  ' "$out")"

  local target_loaded others verdict conflict loaded_csv
  target_loaded="$(jq -r --arg s "$skill" 'if index($s) then "yes" else "no" end' <<<"$loaded")"
  others="$(jq -r --arg s "$skill" '[.[] | select(. != $s)] | join(",")' <<<"$loaded")"
  loaded_csv="$(jq -r 'if length == 0 then "none" else join(",") end' <<<"$loaded")"

  if [ "$target_loaded" = "yes" ]; then
    verdict="loaded"
    if [ -n "$others" ]; then conflict="additional-skills"; else conflict="none"; fi
  else
    verdict="not-loaded"
    if [ -n "$others" ]; then conflict="wrong-skill"; else conflict="none"; fi
  fi

  printf 'verdict: %s\ntarget: %s\nloaded_skills: %s\nconflict: %s\nconflict_skills: %s\nexit_code: %s\n' \
    "$verdict" "$skill" "$loaded_csv" "$conflict" "${others:-none}" "$rc"
}

cmd_cleanup() {
  local ws=""
  while [ $# -gt 0 ]; do
    case "$1" in
      --workspace) ws="$2"; shift 2 ;;
      *) usage ;;
    esac
  done
  ws="${ws:-${TRIGGER_TEST_WORKSPACE:-}}"
  [ -n "$ws" ] || { echo "error: no workspace given" >&2; exit 1; }
  case "$ws" in
    /tmp/trigger-test.*) rm -rf -- "$ws" ;;
    *) echo "error: refusing to remove non-trigger-test path: $ws" >&2; exit 1 ;;
  esac
}

[ $# -ge 1 ] || usage
cmd="$1"; shift
case "$cmd" in
  init) cmd_init "$@" ;;
  eval) cmd_eval "$@" ;;
  cleanup) cmd_cleanup "$@" ;;
  *) usage ;;
esac
```

Note for the executor: if Phase 1 Checkpoint B falsified `.agents/skills`, replace the two `.agents/skills` path constants (in `cmd_init` and the `cmd_eval` stub check) with the verified layout; if Checkpoint C required `--auto`, insert `--auto` into the `opencode run` invocation after `--format json`. Record any such adjustment in the phase report. No other deviation is permitted.

### Success Criteria

#### Automated Verification:
- [ ] Syntax check passes: `bash -n skills/trigger-testing/scripts/trigger-test.sh`
- [ ] Workspace init succeeds and lays out stubs and agent: `WS=$(skills/trigger-testing/scripts/trigger-test.sh init) && test -f "$WS/.agents/skills/trigger-testing/SKILL.md" && test -f "$WS/.opencode/agents/trigger-evaluator.md" && echo INIT-OK` (adjust `.agents/skills` to the Phase-1-verified layout if falsified)
- [ ] Stubs are frontmatter-only (no body headings leak): `! grep -q '^# Trigger Testing' "$WS/.agents/skills/trigger-testing/SKILL.md" && echo STUB-OK`
- [ ] Bad source fails loudly: `skills/trigger-testing/scripts/trigger-test.sh init --source /tmp/opencode 2>/dev/null && echo BAD || echo FAIL-LOUD-OK` (expect `FAIL-LOUD-OK`: `/tmp/opencode` has no `skills/` directory)
- [ ] Known-trigger eval produces a verdict block: `skills/trigger-testing/scripts/trigger-test.sh eval --skill writing-prds --workspace "$WS" "i need to write a product requirements document for a new feature" | grep -q '^verdict: ' && echo VERDICT-OK`
- [ ] Scenario-file path enforced: `skills/trigger-testing/scripts/trigger-test.sh eval --skill writing-prds --workspace "$WS" --scenario-file /etc/hostname 2>/dev/null && echo BAD || echo REJECT-OK` (expect `REJECT-OK`)
- [ ] In-workspace scenario file accepted: `printf 'draft a PRD for a dark mode toggle' > "$WS/scenario.txt" && skills/trigger-testing/scripts/trigger-test.sh eval --skill writing-prds --workspace "$WS" --scenario-file "$WS/scenario.txt" | grep -q '^verdict: ' && echo FILE-OK`
- [ ] Cleanup removes the workspace and only the workspace: `skills/trigger-testing/scripts/trigger-test.sh cleanup --workspace "$WS" && test ! -d "$WS" && echo CLEANUP-OK`
- [ ] No repo side effects from eval runs: `git status --porcelain` shows only `skills/trigger-testing/scripts/trigger-test.sh`

#### Manual Verification:
- [ ] The known-trigger eval reports `verdict: loaded` with `target: writing-prds`
- [ ] A known-negative eval (`--skill writing-prds`, scenario `"what's the weather like in Paris this weekend?"`) reports `verdict: not-loaded`
- [ ] A quoted/metacharacter scenario (e.g. `"my manager said \"spec the \`auth\` flow\" — draft requirements?"`) reaches the evaluator intact and produces a verdict block
- [ ] An eval with `--model "$(opencode models | head -1)"` completes and produces a verdict block; an eval without `--model` also completes (no empty model argument passed)
- [ ] If any run reports `conflict: wrong-skill` or `additional-skills`, the `conflict_skills` field names the actually-loaded skill(s)

**Implementation Note**: After completing this phase and all automated verification passes, pause for human confirmation of the manual criteria before proceeding to the next phase.

---

## Phase 3: Replace the Harness Inside the trigger-testing Skill

### Overview

Rewrite the harness-dependent sections of `skills/trigger-testing/SKILL.md` so every eval execution goes through `trigger-test.sh`: the Workflow gains workspace init/cleanup steps and a JSON-verdict smoke test; the Harness section replaces Task-tool dispatch and rep-message detection with the script invocation and verdict block; Contamination Rule 2 is rewritten for the post-isolation measurement regime and a new Rule 3 covers global-skill leakage; the Multi-Skill regression smoke and the affected Common Mistakes rows are updated. Nothing else in the skill changes — methodology sections (query design, splits, optimization loop, done criteria, results log format) stay verbatim.

**Parallel group:** none

**Execution:** inline

### Changes Required

#### 1. Workflow section — steps 3–9
**File**: `skills/trigger-testing/SKILL.md`
**Changes**: replace the numbered list at `skills/trigger-testing/SKILL.md:16-22` (items 1–7) with:

```markdown
1. Read the target skill's `SKILL.md` and its current frontmatter `description`.
2. Build the eval set per Trigger Eval Query Design; split it per Train/Validation Split into `trigger-evals/train.json` and `trigger-evals/validation.json`. You author every query yourself — never ask the user to supply, confirm, or answer eval queries.
3. Create the campaign workspace: run `WS=$(skills/trigger-testing/scripts/trigger-test.sh init)`. The workspace contains frontmatter-only stubs of every skill under `skills/` plus the `trigger-evaluator` agent. One workspace per campaign — every eval in this campaign reuses it; never create a workspace per eval.
4. Smoke-test the harness (see Harness below): run ONE should-trigger query through the harness and read the verdict block before running full campaigns. The smoke run verifies the `trigger-evaluator` agent sees the stub descriptions and can invoke the skill tool — if the eval cannot load any skill, stop and fix the workspace or agent setup before any campaign. The smoke run must also confirm the verdict names the candidate skill specifically, distinguishing it from a sibling.
5. Run the Optimization Loop: evaluate, revise per failure class, repeat — selecting the best iteration by validation pass rate.
6. Run the fresh-query sanity check; at most one train-expansion re-opt.
7. Check the Done Criteria, then write the results log per Results Log Format — one log per target skill.
8. Given a list of skills, advance per Multi-Skill Campaigns.
9. Clean up the workspace: run `skills/trigger-testing/scripts/trigger-test.sh cleanup --workspace "$WS"` — always, including when the campaign aborts early. A finished campaign leaves no workspace artifacts behind.
```

#### 2. Harness section — full replacement
**File**: `skills/trigger-testing/SKILL.md`
**Changes**: replace the entire Harness section at `skills/trigger-testing/SKILL.md:113-140` with:

````markdown
## Harness

Every query — smoke, train, validation, fresh — is executed by `skills/trigger-testing/scripts/trigger-test.sh` inside the campaign's isolated workspace. Queries are NEVER sent to the user. The `question` tool plays no role in this campaign; if you are about to ask the user an eval query, you have confused the measurement target — the workspace eval is the subject under test, not the user.

**Workspace lifecycle:** one workspace per campaign, created in Workflow step 3, reused for every eval, removed in Workflow step 9 — including on abort. The workspace holds frontmatter-only stubs of every skill plus the `trigger-evaluator` agent; skill bodies, the repo codebase, and the repo `AGENTS.md` are absent by construction.

**Invoke:** one eval per rep:

```bash
skills/trigger-testing/scripts/trigger-test.sh eval --skill <candidate> --workspace "$WS" "$(cat <<'EOF'
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
```

A run that ends, times out, or hits its step limit without a load signal for the candidate is **not-loaded**; the verdict is binary and does not distinguish those cases. Detection **must** be candidate-specific: an eval where a *sibling* skill fired instead of the candidate reports `verdict: not-loaded` with `conflict: wrong-skill` — "any skill fired" is the failure mode the smoke test caught (`prompt-shaping` stealing routing from `writing-prds`). The `conflict_skills` field names what actually loaded — target-plus-extras (`additional-skills`) or the wrong skill (`wrong-skill`) — so over-similar descriptions can be reworked.

**Rep independence:** every rep is a fresh `opencode run` session. Workspace reuse carries no context between reps — the workspace holds only static stubs and the agent definition, so a reused workspace cannot change an eval's outcome relative to running it alone.

**Pass criterion:** should-trigger query passes when trigger rate > 0.5 over ≥3 reps; should-not passes when rate < 0.5. Reps ≥3 per query. **Bump to 5 reps only on consecutive-opposite-outcome** — a 3-of-3 split across trigger / no-trigger (≥2 distinct outcomes over the 3 baseline reps). Borderline verdicts no longer rest on agent judgment alone; record the 3 per-rep outcomes and a one-line rationale in the campaign log. **Bump rate cap: ≤25% of queries per iteration** may be bumped.

**Load-and-stop (per rep):** the rep measures the load decision only. In the isolated workspace a loaded skill is a frontmatter stub — there is no body to execute — so post-load workflow execution is impossible by construction, and the `trigger-evaluator` agent's report-and-stop rule (`agents/trigger-evaluator.md`) remains as a second enforcement layer. An eval whose verdict block is missing or unparseable (script error, missing workspace, non-JSON output) is void — fix the cause, re-dispatch a fresh replacement, and never count it, same convention as error/hang voids.

**Workload isolation (per rep):** two structural layers. The stub-only workspace removes skill bodies, the codebase, and anything to analyze; the `trigger-evaluator` agent's skill-only tool surface and `steps` cap bound every rep's cost — that is the abort mechanism, and it is structural, not procedural. A hung `opencode run` is killed by the script's timeout guard and reports not-loaded; only a missing or unparseable verdict block makes the eval void per Load-and-stop above.

**Intra-iteration rep parallelism:** run the per-iteration rep matrix as concurrent background shell jobs — each its own `trigger-test.sh eval` invocation writing its own verdict block — then wait for all jobs and collect the blocks. Reps within one iteration are interchangeable; the next iteration depends on the previous iteration's *failures*, so inter-iteration stays serial. This is within-phase fan-out and does not violate a plan's `Execution: inline` / `Parallel group: none` declarations — those govern inter-phase parallelism, not intra-phase fan-out.
````

#### 3. Contamination Rules — replace Rule 2, add Rule 3
**File**: `skills/trigger-testing/SKILL.md`
**Changes**: replace the section body at `skills/trigger-testing/SKILL.md:142-145` with:

```markdown
## Contamination Rules

1. **Cross-skill description visibility is expected, not contamination.** Per repo `AGENTS.md`, these skills ship together, so a sibling routing win on a should-trigger eval is a real measurement, not an error to be filtered out. The workspace stubs every skill under `skills/`, so sibling descriptions compete exactly as in deployment.
2. **Reps no longer see the repo `AGENTS.md` or the real codebase — rates recorded under the old repo-root harness are not comparable.** The isolated workspace removes both by design. Campaign logs written before this harness shipped were measured with `AGENTS.md` in context and real skill bodies present; treat them as a different measurement regime, never as a baseline to match.
3. **Globally installed skills can leak into the workspace.** Skills under `~/.config/opencode/skills`, `~/.claude/skills`, and `~/.agents/skills` load in every opencode run, including workspace evals. A load of a skill absent from this repo's `skills/` appears in `loaded_skills`; record it in the campaign log as environmental noise and exclude it from conflict-rework decisions about this repo's descriptions.
```

#### 4. Multi-Skill Campaigns — regression smoke wording
**File**: `skills/trigger-testing/SKILL.md`
**Changes**: replace the sentence at `skills/trigger-testing/SKILL.md:162` beginning "**Final-Verification regression smoke:**" with:

```markdown
**Final-Verification regression smoke:** in the plan's Final Verification, re-run 1 eval of each campaigned skill's canonical should-trigger smoke query against the final pinned description state through the campaign workspace (~12 evals for a 12-skill plan). Report any cross-phase routing regression. This is cheap insurance against the assertion that file-disjoint edits can't cross-talk — true for *files* but not for *routing behavior* when the candidate description itself changed mid-campaign.
```

#### 5. Common Mistakes — six rows
**File**: `skills/trigger-testing/SKILL.md`
**Changes**: in the table at `skills/trigger-testing/SKILL.md:166-179`, replace the six harness-related rows with:

```markdown
| Treating a sibling skill firing as "any skill fired, pass" | The verdict is candidate-specific: sibling-only loads report `not-loaded` with `conflict: wrong-skill` |
| Skipping the smoke-test before running the full campaign | Run ONE should-trigger eval through `trigger-test.sh` and read its verdict block before running the full rep matrix |
| Running evals outside the isolated harness | Always run evals through `trigger-test.sh` — only it guarantees the stub-only workspace and the skill-only `trigger-evaluator` agent |
| Assuming a triggered skill can execute its workflow | Stubs are frontmatter-only — there is no body to execute. A missing or unparseable verdict block means the eval is void: fix the cause, re-dispatch fresh, never count it |
| Adding framing, skill names, or "this is a test" context to the scenario | Pass the bare eval query only, via `<<'EOF'` heredoc — anything more carries the runner's context into the eval and biases the routing measurement |
| Asking the user eval queries via the `question` tool | The user is never a rep. All queries go through `trigger-test.sh eval` into the isolated workspace; the runner authors them without user input. |
```

### Success Criteria

#### Automated Verification:
- [ ] Skill validates: `agentskills validate skills/trigger-testing` prints `Valid skill`
- [ ] No old-harness tokens remain: `! grep -nE 'subagent_type|task_id|Task tool call' skills/trigger-testing/SKILL.md && echo HARNESS-REPLACED`
- [ ] Description still within limits (frontmatter untouched, confirmed by validation): `agentskills validate skills/trigger-testing`
- [ ] Integrated smoke through the updated workflow: `WS=$(skills/trigger-testing/scripts/trigger-test.sh init) && skills/trigger-testing/scripts/trigger-test.sh eval --skill writing-prds --workspace "$WS" "i need to write a product requirements document for a new feature" && skills/trigger-testing/scripts/trigger-test.sh cleanup --workspace "$WS" && test ! -d "$WS" && echo INTEGRATED-SMOKE-OK`
- [ ] No workspace artifacts remain: `ls -d /tmp/trigger-test.* 2>/dev/null || echo NO-WORKSPACE-LEFT`

#### Manual Verification:
- [ ] Reading the updated Workflow end-to-end, every eval execution goes through `trigger-test.sh` and no instruction references the Task-tool harness
- [ ] The verdict-block field names in the Harness section match the script's `printf` output exactly (`verdict`, `target`, `loaded_skills`, `conflict`, `conflict_skills`)
- [ ] The integrated smoke eval reports `verdict: loaded` for the known writing-prds should-trigger query

**Implementation Note**: After completing this phase and all automated verification passes, pause for human confirmation of the manual criteria before proceeding to the next phase.

---

## Testing Strategy

### Unit Tests:
- None — this repo has no automated test framework for skills or shell scripts (bundle §7). Script correctness is verified by the Phase 2 automated checks: syntax (`bash -n`), stub-layout assertions, fail-loud source validation, scenario-file path rejection, and cleanup guards.

### Integration Tests:
- Phase 1 spikes verify the runtime contract (schema, layout, permissions, model flag) against the real `opencode` 1.18.3 CLI before code exists.
- Phase 2 verifies known-trigger (loaded) and known-negative (not-loaded) scenarios end-to-end in a real workspace, plus metacharacter-heavy scenario passthrough.
- Phase 3's integrated smoke runs the updated skill workflow's workspace lifecycle end-to-end and asserts no artifacts remain.

### Manual Testing Steps:
1. After Phase 2: run one should-trigger and one should-not query from `skills/writing-prds/trigger-evals/train.json` through the script and confirm verdicts match their `should_trigger` labels.
2. After Phase 3: follow the updated `trigger-testing` skill's Workflow steps 3, 4, and 9 by hand for `writing-prds` and confirm the smoke-test gate reads the verdict block and the workspace is cleaned up.
3. Confirm a deliberately conflicting scenario (one whose wording matches two skills) reports the actually-loaded skill(s) in `conflict_skills`.

## Final Verification

```
agentskills validate skills/trigger-testing
bash -n skills/trigger-testing/scripts/trigger-test.sh
WS=$(skills/trigger-testing/scripts/trigger-test.sh init) && skills/trigger-testing/scripts/trigger-test.sh eval --skill writing-prds --workspace "$WS" "i need to write a product requirements document for a new feature" && skills/trigger-testing/scripts/trigger-test.sh cleanup --workspace "$WS" && test ! -d "$WS"
! grep -nE 'subagent_type|task_id' skills/trigger-testing/SKILL.md
ls -d /tmp/trigger-test.* 2>/dev/null && echo WORKSPACE-LEAK || echo NO-WORKSPACE-LEAK
git status --porcelain
```

## Open Questions

None. The bundle §9 items were resolved during planning as follows: opencode CLI flag semantics and agent/skill discovery paths were verified against `opencode run --help` (1.18.3) and https://opencode.ai/docs/agents/ + /docs/skills/; the residual facts that only a live run can confirm (exact JSON event-schema field paths, non-git temp-dir discovery, permission behavior without repo config, global-skill leakage) are built into Phase 1 as Checkpoints A–E with concrete commands and a defined fallback ladder, with a stop-and-report escalation if the fallbacks are exhausted. The stub-generation and cleanup mechanisms had no repo precedent to verify and were decided in the Decisions table (awk extractor + init/cleanup subcommands).

## References

- PRD: `PRDS/2026-07-31-isolated-trigger-testing-harness.md`
- Context bundle: `RESEARCH/2026-07-31-isolated-trigger-testing-harness-context-bundle.md`
- Research findings: `RESEARCH/2026-07-31-isolated-trigger-testing-harness-research-findings.md`
- Key implementation files:
  - `skills/trigger-testing/SKILL.md:113-140` (harness being replaced), `:16-22` (workflow), `:142-145` (contamination rules), `:162` (multi-skill smoke), `:166-179` (common mistakes)
  - `agents/trigger-evaluator.md:1-19` (agent contract copied into the workspace)
  - `skills/project-bootstrap-nix/scripts/bootstrap.sh:1-84` (script conventions)
  - `skills/pressure-testing/SKILL.md:93-106` (`opencode run` dispatch idiom)
  - `PLANS/2026-07-30-trigger-eval-read-only-agent-plan.md:200` (grep detection precedent)
  - `.opencode/opencode.jsonc:3-5` (repo permission config absent from workspaces)
