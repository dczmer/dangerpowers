---
artifact: implementation-report
date: 2026-07-31
plan: PLANS/2026-07-31-isolated-trigger-testing-harness-plan.md
phase: 2
status: DONE
git_commit_start: 9d4735e6c922bd5e6e1a2851dc66e47c3bd1af13
git_commit_end: bfd46c7 (HEAD after the phase commit; hash advances by one amend that only records this line)
---

# Phase 2: Implement the trigger-test.sh Harness Script — Implementation Report

## Summary

Created `skills/trigger-testing/scripts/trigger-test.sh` (executable) exactly as specified in the plan, with the two named adjustments forced by Phase 1 Checkpoint A: the tool-event type selector matches `tool_use` (not `tool`), and the jq pipeline tolerates the non-JSON stderr line captured in the stream via `jq -R 'fromjson? // empty' | jq -s`. The Phase-1-verified `.agents/skills` + `.opencode/agents` layout was kept, and `--auto` was NOT added (Checkpoint C falsified the need). All 9 automated criteria pass; known-trigger, scenario-file, metacharacter, known-negative, and `--model` evals all produced correct verdict blocks (evidence below for the human's manual items).

## Changes Made

#### 1. The harness script
**File**: `skills/trigger-testing/scripts/trigger-test.sh` (new, mode 0755)
**Changes**: created with the plan's exact content (`init` / `eval` / `cleanup` subcommands, awk frontmatter extractor, fail-loud source validation, scenario-file realpath containment check, `timeout 300` guard, verdict-block printf), plus the two plan-sanctioned selector adjustments in `cmd_eval`'s detection pipeline:
- `select(.type? == "tool")` → `select(.type? == "tool_use")` — Phase 1 Checkpoint A falsified the plan default; verified stream type is `tool_use` (phase-1 report, "Checkpoint A record").
- `jq -rs '<filter>' "$out"` → `jq -R 'fromjson? // empty' "$out" | jq -s '<filter>'` — the captured stream (`> "$out" 2>&1`) begins with a non-JSON stderr line (`[rtk] rtk binary not found in PATH — plugin disabled`) that makes raw `jq -rs` exit with a parse error; the two-stage pipeline skips invalid lines, then applies the plan's filter verbatim.
- The field-path selectors (`.part.tool`, `.part.state.input.name`, `.part.text`, with both documented nestings) were kept exactly as the plan wrote them; they match the Phase-1-verified paths.
- No other deviation: `.agents/skills` + `.opencode/agents` layout retained (Checkpoint B confirmed the default), `--auto` not added (Checkpoint C: not needed).

## Verification

Every Automated Verification criterion from the phase, run exactly as written:

| Criterion | Command | Result |
|-----------|---------|--------|
| Syntax check passes | `bash -n skills/trigger-testing/scripts/trigger-test.sh` | PASS |
| Workspace init succeeds and lays out stubs and agent | `WS=$(skills/trigger-testing/scripts/trigger-test.sh init) && test -f "$WS/.agents/skills/trigger-testing/SKILL.md" && test -f "$WS/.opencode/agents/trigger-evaluator.md" && echo INIT-OK` | PASS |
| Stubs are frontmatter-only | `! grep -q '^# Trigger Testing' "$WS/.agents/skills/trigger-testing/SKILL.md" && echo STUB-OK` | PASS |
| Bad source fails loudly | `skills/trigger-testing/scripts/trigger-test.sh init --source /tmp/opencode 2>/dev/null && echo BAD \|\| echo FAIL-LOUD-OK` | PASS |
| Known-trigger eval produces a verdict block | `skills/trigger-testing/scripts/trigger-test.sh eval --skill writing-prds --workspace "$WS" "i need to write a product requirements document for a new feature" \| grep -q '^verdict: ' && echo VERDICT-OK` | PASS |
| Scenario-file path enforced | `skills/trigger-testing/scripts/trigger-test.sh eval --skill writing-prds --workspace "$WS" --scenario-file /etc/hostname 2>/dev/null && echo BAD \|\| echo REJECT-OK` | PASS |
| In-workspace scenario file accepted | `printf 'draft a PRD for a dark mode toggle' > "$WS/scenario.txt" && ... eval --scenario-file "$WS/scenario.txt" \| grep -q '^verdict: ' && echo FILE-OK` | PASS |
| Cleanup removes the workspace and only the workspace | `skills/trigger-testing/scripts/trigger-test.sh cleanup --workspace "$WS" && test ! -d "$WS" && echo CLEANUP-OK` | PASS |
| No repo side effects from eval runs | `git status --porcelain` | PASS — shows only `?? skills/trigger-testing/scripts/` |

Output evidence:

```text
$ bash -n skills/trigger-testing/scripts/trigger-test.sh && echo SYNTAX-OK
SYNTAX-OK

$ WS=$(skills/trigger-testing/scripts/trigger-test.sh init)  # WS=/tmp/trigger-test.Md9exoMjWL
INIT-OK
STUB-OK
$ ls "$WS/.agents/skills"
executing-plans  isolating-worktrees  iterating-plans  plan-to-execution
prd-to-plan  pressure-testing  project-bootstrap-nix  prompt-shaping
researching-codebase  scouting-context  trigger-testing  writing-plans
writing-prds  writing-quick-plans  writing-skills

FAIL-LOUD-OK

# Known-trigger eval verdict block (also confirms jq tolerates the
# non-JSON first line, which is present in the captured stream):
$ head -1 "$WS/.trigger-test-last-run.jsonl"
[rtk] rtk binary not found in PATH — plugin disabled
verdict: loaded
target: writing-prds
loaded_skills: writing-prds
conflict: none
conflict_skills: none
exit_code: 0

REJECT-OK

# In-workspace scenario-file eval:
verdict: loaded
target: writing-prds
loaded_skills: writing-prds
conflict: none
conflict_skills: none
exit_code: 0
FILE-OK

CLEANUP-OK
$ git status --porcelain
?? skills/trigger-testing/scripts/
$ ls -d /tmp/trigger-test.* 2>/dev/null || echo NO-WORKSPACE-LEFT
NO-WORKSPACE-LEFT
```

Evidence gathered for the human's Manual Verification items (boxes left unchecked per contract):

```text
# MV1 — known-trigger eval: verdict: loaded, target: writing-prds (block above)

# MV2 — known-negative eval:
$ trigger-test.sh eval --skill writing-prds --workspace "$WS" "what's the weather like in Paris this weekend?"
verdict: not-loaded
target: writing-prds
loaded_skills: none
conflict: none
conflict_skills: none
exit_code: 0

# MV3 — metacharacter scenario `my manager said "spec the `auth` flow" — draft requirements?`:
verdict: loaded
target: writing-prds
loaded_skills: writing-prds
conflict: none
conflict_skills: none
exit_code: 0
# The scenario arrived as a single intact argument (quoting survived the shell;
# opencode accepted it and the evaluator routed to writing-prds). Note: the JSON
# event stream does not echo the user prompt, so verbatim-intactness is evidenced
# by the successful single-argument dispatch + load, not by a stream grep.

# MV4 — --model eval (`--model "$(opencode models | head -1)"` → opencode/big-pickle):
verdict: loaded
target: writing-prds
loaded_skills: writing-prds
conflict: none
conflict_skills: none
exit_code: 0
# Evals without --model (all other runs above) also complete; no empty model
# argument is passed (model_args array expansion).

# MV5 — no run in this phase reported conflict: wrong-skill or additional-skills;
# every conflict_skills was `none`.
```

Manual Verification items are listed here unchecked, for the human:

- [ ] The known-trigger eval reports `verdict: loaded` with `target: writing-prds`
- [ ] A known-negative eval (`--skill writing-prds`, scenario `"what's the weather like in Paris this weekend?"`) reports `verdict: not-loaded`
- [ ] A quoted/metacharacter scenario (e.g. `"my manager said \"spec the \`auth\` flow\" — draft requirements?"`) reaches the evaluator intact and produces a verdict block
- [ ] An eval with `--model "$(opencode models | head -1)"` completes and produces a verdict block; an eval without `--model` also completes (no empty model argument passed)
- [ ] If any run reports `conflict: wrong-skill` or `additional-skills`, the `conflict_skills` field names the actually-loaded skill(s)

## Deviations

| Plan said | What was done instead | Why it was forced |
|-----------|----------------------|-------------------|
| jq filter matches `select(.type? == "tool")` | `select(.type? == "tool_use")` | Phase 1 Checkpoint A falsified the plan default; the real stream's tool-event type is `tool_use`. The plan's executor note names this an adjustable selector. |
| `loaded="$(jq -rs '<filter>' "$out")"` | `loaded="$(jq -R 'fromjson? // empty' "$out" \| jq -s '<filter>')"` | The captured stream contains a non-JSON stderr first line that makes raw `jq` exit with a parse error before any selector runs. Phase 1 report §Issues flagged this as slightly beyond a literal selector edit; the dispatcher explicitly authorized it ("the jq filter must tolerate invalid lines"). |

## Issues & Concerns

- **The JSON event stream does not echo the user prompt.** Manual item 3 ("scenario reaches the evaluator intact") cannot be proven from the stream itself; evidence is the successful single-argument dispatch and correct routing. Noted so the human knows what the evidence does and does not show.
- **`opencode models` emits the `[rtk]` plugin warning on stderr.** It does not contaminate `$(opencode models | head -1)` (stderr is not captured), and the script's own stdout verdict block stays clean — but a campaign runner capturing `2>&1` around the script would see the line. No action needed for this phase; Phase 3's skill text already invokes the script with stdout-only verdict reading.

## Follow-ups

- Human to confirm the five Manual Verification items above (evidence provided) before Phase 3 begins.
- Phase 3 executor: the script's `printf` verdict block includes an `exit_code` field beyond the five fields the plan's Harness-section replacement documents (`verdict`, `target`, `loaded_skills`, `conflict`, `conflict_skills`). This matches the plan's script content verbatim (the plan itself specifies `exit_code` in the printf) — no action needed, but Phase 3's manual criterion "verdict-block field names match the script's printf output exactly" should account for it.
