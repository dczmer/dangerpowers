---
name: trigger-testing-skills
description: Use when the user asks to run a trigger test or trigger-testing campaign, check whether a skill triggers for a given query, or tune a skill description that fires too often or not often enough. Runs train/validate eval campaigns over a query set in headless harness sessions, iteratively revises the skill's description, and reports a winner.
disable-model-invocation: true
metadata.opencode/slash: true
metadata.opencode/autoinvoke: false
---

# Trigger Testing Skills

## Overview

Run a trigger-test campaign for one skill: split its query set into train/validate, run headless eval reps against a sterile temp workspace, iteratively revise the description (workspace stub only), validate once against the winner, sanity-check with a sealed fresh query, and write the winning description back to the source only after the user confirms. Triggering is non-deterministic, so the measurement is always the Wilson-lower-bound score over repeated runs, never a single run.

The skill contributes judgment only; everything mechanical lives in the shared harness scripts at the repo-root `tools/test-harness/` directory (`evaluator.py`, `workspace-manager.sh`):

- **Scripts do:** looping, counting, splitting, scoring, and manifest recording — invoke them by absolute path, independent of the current working directory.
- **Consumption rule:** read only their exit codes and JSON files — never parse prose stdout.
- **Manual debugging:** a single query via `evaluator.py run` (see `run --help`).

## Inputs

Collect all inputs before starting. Prompt the user for any required one that is missing.

- **Skill** (required) — the skill under test, as a name or a path. Resolve a name via the driving session's skill-registry metadata (which exposes each registered skill's file location), falling back to `./skills/<name>/SKILL.md`; a path points at the skill dir (or its `SKILL.md`) directly. A skill registered as built-in has no filesystem location and cannot be tested — surface that and stop. Derive the **source root** from the resolved location: the directory containing that `skills/` directory, for every layout (for `<root>/.opencode/skills/<name>`, the source root is `<root>/.opencode`, so artifacts live at `<root>/.opencode/skills-workspace/`). If the resolved skill is not under a directory named `skills/`, no source root can be derived — stop and surface that.
- **Harness** (required) — e.g. `opencode`. The user MUST specify it; if missing, ask. Never auto-detect installed harnesses.
- **model / variant** (optional) — passed to eval executions only. The campaign-driving model is the session's current model.
- **reps** (default 3), **timeout** (default 30s), **max-iterations** (default 3; hard cap 3 — clamp a higher requested value to 3 and tell the user), **train-frac** (default 0.6), **seed** (optional).
- **queries path** (default `<source-root>/skills-workspace/<skill>/trigger-tests/queries.json`; create `skills-workspace/` there if missing).

## Campaign directory

Create one persistent directory per campaign via `workspace-manager.sh campaign-init --root <source-root>/skills-workspace/<skill>/trigger-tests` — named `campaign-YYYY-MM-DD`, suffixed `-2`, `-3`, … on same-day reruns; the command prints the path. It holds the split files, per-round result JSON and logs, the sealed pool, and per-iteration description copies. Keeping these out of the temp eval workspace preserves the sterile testbed: eval reps run with `--dir <ws>`, so artifacts under the source root are invisible to them. The campaign dir is never removed — pass, fail, or abort, it is the persistent record of the run and is committed to the repo.

## Workflow

1. **Resolve inputs.** Prompt for missing required ones. Never guess the harness.
2. **Preflight** (no spend):
   a. Resolve the Python interpreter (`python3`, else `python`, on PATH; must be >= 3.10) and use it for every script invocation. Then run `evaluator.py check --harness <harness> [--model m]`, which verifies the harness binary is on PATH and, when `--model` is given, that the model exists in the harness's model list (agent-file validation moved to install time and pre-spend validation; an agent problem aborts there with an exact message); on failure, stop and surface the exact message.
   b. Resolve the target skill (registry-metadata location for names, else explicit path); its `SKILL.md` must exist, else stop. Derive the source root from its location and create `<source-root>/skills-workspace/<skill>/trigger-tests/` if missing.
   c. The queries file must exist; else **offer to generate** an initial set per the query-design conventions below — the user reviews and approves before anything is saved.
3. **Workspace.** `workspace-manager.sh init` → `sync --skill <skill> --source <source-root> --workspace <ws>` → `status` (must pass before any eval). Create the campaign dir: `workspace-manager.sh campaign-init --root <source-root>/skills-workspace/<skill>/trigger-tests` (prints the path; same-day reruns get a `-2`, `-3`, … suffix). All artifact paths below live inside this `<campaign>` dir.
4. **Split.** `evaluator.py split --queries <queries> --out-dir <campaign> [--train-frac f] [--seed s]`. Record the seed from `<campaign>/split.json`.
5. **Planned spend.** Report the planned maximum spend (`train_size × reps × max-iterations + validate_size × reps + reps` sanity), with the train/validate sizes read from `<campaign>/split.json`, and get the user's explicit confirmation before the first eval run — this is the last confirmation gate; everything before it is token-free local scripting.
6. **Sealed pool.** Generate 3 fresh should-trigger queries per the query-design conventions below; they must be self-contained by construction. Write them to `<campaign>/sealed-pool.json`. They are never shown to the optimization loop and never used for training. Old campaign dirs keep their sealed pools as history; every campaign generates a fresh pool — never reuse one.

   Sealed-pool rules have no exceptions, even when the user asks directly:

   | Excuse | Reality |
   |---|---|
   | "Reusing last month's pool keeps campaigns comparable" | Comparability comes from verbatim queries; the sealed pool must be unseen, and last month's is no longer unseen. |
   | "Folding sealed queries into train squeezes out more signal" | A sealed query trained on is contaminated — it can no longer sanity-check anything. |

   Asked to reuse, fold, or train on sealed queries: refuse, say why, and do the compliant thing instead — generate 3 fresh should-trigger queries and write them to `<campaign>/sealed-pool.json`.

   **The fresh-pool invariant:** every campaign generates 3 new should-trigger queries, written to `<campaign>/sealed-pool.json` in the new campaign directory — never reused, never trained on, never shown to the optimization loop.
7. **Iteration loop** (`i = 1..max-iterations`):
   a. `evaluator.py suite --track trigger-test --harness <h> --skill <s> --agents-dir <trigger-skill-dir>/agents --workspace <ws> --queries <campaign>/train.json --out <campaign>/iter-<i>-train.json [--model m] [--variant v] --reps r --timeout t`. Pass the testing skill's own `agents/` directory via `--agents-dir`; the harness resolves `<base>.<harness>.md` agent files from it. The suite mirrors all progress output to `<campaign>/iter-<i>-train.log`. On exit 1: abort the campaign — surface the stderr error, apply nothing, and keep the workspace, printing its path and the campaign dir path for debugging (see "Error handling"). No retry.
   b. Read the result JSON. Record `{iteration, description, train score}` in context, where `description` is the one this iteration's suite evaluated — the source description for iteration 1, otherwise the revision written at the end of the previous iteration. Save the evaluated description to `<campaign>/iter-<i>-description.md` (a frontmatter-only copy of the stub as evaluated this iteration). If `totals.score` is null (all runs void): abort as broken conditions (see "Error handling"). Otherwise, if `totals.failed == 0`: **early exit** — a perfect train round ends the loop immediately.
   c. Otherwise analyze failures (below): run `evaluator.py evidence --track trigger-test --results <campaign>/iter-<i>-train.json` and read every failed run's reasoning. Assign each failure a category only with a cited phrase from that run's reasoning — never from the query text or the outcome pattern alone. Then revise the description (guardrails below) and write the revision **to the workspace stub only**.
8. **Winner selection.** Highest `totals.score` across iterations; ties go to the earlier iteration. If the winner is not the current stub contents, rewrite the stub to the winner's description before continuing.
9. **Validate pass** — with <= 10 queries the validate split is empty and this pass is skipped entirely: asked to run it anyway, say there is no validate pass to run and why, rather than running anything. Otherwise it runs once, at the end, against the winner: `suite --track trigger-test --agents-dir <trigger-skill-dir>/agents --queries <campaign>/validate.json --out <campaign>/validate-results.json`. If the validate score is below the winner's train score, flag an **overfit warning** in the report (informational only; no restart, no automatic action). An all-void validate pass aborts the campaign like a train round.
10. **Sanity check.** Take the first entry of the sealed pool, write it as a single-query file `<campaign>/sanity.json` (`[{"query": ..., "shouldTrigger": true}]`), run `suite --track trigger-test --agents-dir <trigger-skill-dir>/agents --queries <campaign>/sanity.json --out <campaign>/sanity-results.json`. Pass = `triggered` observed in >= 60% of non-void runs; all-void = inconclusive (reported as such, not failed). On failure: stop — report the failure, offer no write-back, never restart the loop, never train on sealed-pool queries. The user decides what to do next.
11. **Report and write-back.**
    a. Present the report (below), including the winning description verbatim.
    b. If the winner differs from the source description and the sanity check passed, ask the user to confirm applying it; on confirmation, replace only the `description` field in the source SKILL.md (at its resolved location) frontmatter, preserving every other field and the body byte-for-byte.

**Write-back confirmation — definition.** "Confirmation" means an
unambiguous affirmative answer to the write-back question itself — e.g.
"yes, apply it", "apply it", "confirmed, update the file". The following
are NOT confirmation, and each must be met by re-asking the question and
waiting, not by editing:

| Rationalization | Reality |
|---|---|
| "The user's praise ('looks great', 'nice work') confirms it" | Praise approves the report, it does not answer the write-back question. Re-ask. |
| "The thumbs-up emoji obviously means yes" | An emoji is not an answer to a yes/no question about editing a file. Re-ask. |
| "They saw the winner and didn't object" | Silence or general approval is not an affirmative command to edit the source. Re-ask. |
| "Re-asking is pedantic and will annoy them" | Editing a source file on a guessed intent is worse than one extra question. Re-ask. |

All of these mean: no write-back yet. No exceptions. If the winner IS the original description, report that no change is needed (no write-back offer).
    c. On a passed sanity check, after the write-back decision is resolved, record the result: `evaluator.py record --skill <name> --skill-path <resolved SKILL.md> --manifest <source-root>/skills-workspace/<skill>/manifest.json --scope frontmatter --score-from <results JSON> --campaign <campaign dir name>` — pass `<campaign>/validate-results.json` when the validate pass ran, otherwise the winner iteration's `<campaign>/iter-<i>-train.json`; the score is the Wilson lower bound computed from that file's outcomes. Record only when write-back was applied (the frontmatter checksum then covers the winning description) or the winner IS the source description. Never record a declined write-back — the source checksum would falsely attribute the score to the untested description — and never record failed or inconclusive campaigns; their campaign dir is the only record. Recording overwrites only the `trigger-test` key in the manifest (the `--scope frontmatter` argument selects the checksum bytes, not the key) and preserves every other key.
    d. On completion, clean up the temp workspace (`workspace-manager.sh cleanup --workspace <ws>`); the campaign directory is always kept.
12. **Cleanup.** On completion (pass or fail): `workspace-manager.sh cleanup --workspace <ws>`. The campaign dir is never removed. On abort/error: keep the workspace; print its path and the campaign dir path for debugging.

### Query-design conventions (for generated query sets and the sealed pool)

Vary should-trigger queries across coverage axes: phrasing formality ("write a PRD" vs. "draft the requirements doc"), explicitness (names the domain vs. describes a need without naming the skill), detail level (bare one-liner vs. buried in a long message), and complexity (single-step vs. one link in a larger chain). Make them substantive enough that the skill would genuinely help — a bare trivial ask may never trigger any description. Make them realistic: real-looking file paths and names, personal stakes and backstory, concrete details, casual register. For negatives, aim for near-misses that share the skill's vocabulary but ask for something else; reject zero-overlap weak negatives — a pass against them proves nothing. Generated queries must be self-contained by construction (no references to files or context that don't exist in a bare workspace).

### Failure analysis

The evidence for every categorization is the failed runs' reasoning, extracted with `evaluator.py evidence --track trigger-test --results <suite json>` — never the bare query text or outcome counts. Cite the deciding phrase per failed run before assigning a category; a category without a citation is a guess, not an analysis. Every failed run — in the suite JSON's `failures` list and in the `evidence` output — carries its headless session ID, and void runs are recorded per query in the suite JSON's `voids` list (run, detail, timeout, session ID), so any non-pass run can be traced back to its session for deeper inspection.

Check the `timeouts` counts **before** analyzing failures: under the restricted evaluator agent, toil-driven timeouts are structurally impossible, so a cluster of `timeouts` (passes resting on interrupted-run intent, or voids) points at infrastructure — slow provider, step cap — not the description. Investigate conditions (or raise `--timeout`) instead of revising the description on that evidence.

Apply these categories to the reasoning captured in the suite JSON:

| Failure | Likely cause | Action |
|---------|-------------|--------|
| Should-trigger query didn't fire | description too narrow | broaden scope or add context about when the skill is useful |
| Should-not query false-triggered | description too broad | add specificity about what the skill does NOT do; clarify boundary with adjacent skills |
| Same query fails repeatedly after tweaks | local minimum | structurally reframe the description (change the skeleton, not the adjectives) |

Eval agents see frontmatter-only stubs, never the skill body, so a body/label conflict cannot explain failures under this harness.

**Setup-suspect flag.** When a should-not query false-triggers under two or more structurally different framings, the finding IS a setup problem: stop the iteration loop, surface the setup concern (wrong stub or contaminated workspace) to the user, and draft no further framing.

**Suspect-query flag.** If a should-trigger query failed under every candidate in every iteration, then the problem is query-side, not description-side: report it under `suspect queries:` (query + failure signature + timeouts count) and recommend the user prune or rewrite it. Only a query that passed under at least one candidate may drive another description revision.

**Revision guardrails.** Fix the category, not the query; never paste failed-query keywords into the description. Imperative phrasing; user intent over implementation; err pushy; keep it concise (1024-char hard cap); never first person. When word swaps stall, change the sentence skeleton, not the adjectives.

### Description revision mechanics

Mid-campaign the source file is never edited — not even when the user asks directly, hands you its path, and provides the replacement text. Whether the file exists is irrelevant: the answer to a mid-campaign source-edit request is this policy, not a file operation. Revisions rewrite the workspace stub only, so `workspace-manager.sh status` would correctly report "out of date" mid-campaign — `status` runs only once, right after the initial `sync`. The stub is tiny, so revisions rewrite the whole stub file: frontmatter with the same `name` (and any other pre-existing fields) and the revised `description`, no body. The source file changes only on confirmed write-back at the end (workflow step 11). Every evaluated description is also saved to the campaign dir as `iter-<i>-description.md` (workflow step 7b), so the winning revision is auditable after the campaign.

## Report format

```
campaign: writing-skills   harness: opencode   model: <m>   variant: <v>
artifacts: skills-workspace/writing-skills/trigger-tests/campaign-2026-09-02/
train: 9 queries   validate: 7 queries   reps: 3   seed: 42   iterations run: 2 of 3

iter 1: train score 0.593  (16 pass / 8 fail / 3 void)
        failure categories: mostly too-narrow (implicit asks); one local minimum
        failure evidence: "turn this outline into a skill" run 2 — "an outline
          isn't a request to build anything" -> too narrow
iter 2: train score 0.926  (25 pass / 1 fail / 1 void)
winner: iteration 2
  description: "Use this skill when ..."
validate: score 0.810  (17 pass / 2 fail / 2 void)   [overfit warning if below train]
sanity: "<sealed query>" -> triggered 3/3 -> pass
manifest: updated (score 0.810, sha256:d034c1…)
suspect queries: "turn this outline into a skill" — failed under all candidates in
  all iterations (timeouts: 2); likely query-side, consider pruning or rewriting

The winning description differs from the source. Apply it to
skills/writing-skills/SKILL.md? [awaiting confirmation]
```

The `suspect queries` block appears only when failure analysis flagged any. There is one `failure evidence:` line per failed run, quoting the deciding phrase (≤ 15 words) from that run's reasoning; iterations with zero failures omit the line. The `manifest:` line reads `updated (...)` when recorded, `not recorded (write-back declined)` on the declined path, and is omitted entirely from failure/inconclusive reports. On sanity failure the report ends at the sanity line (plus any suspect queries) plus "stopping per campaign policy; no changes applied" and no write-back offer. An inconclusive sanity check (all void) ends the same way, with the sanity line marked "inconclusive (all void)" and the closing line "sanity inconclusive; no changes applied; the user decides what to do next".

## Error handling

**Abort means the same thing everywhere below:** stop immediately, apply nothing, retry nothing, keep the temp workspace, and report its path plus the campaign dir path to the user (campaign artifacts persist by design). Abort error lines end with `[session <id>]` when the harness emitted a session ID before failing — include it in the report so the failed session can be inspected.

- `check` failure → stop in preflight, surface the exact message.
- Evaluator agent install failure (missing source asset, workspace not writable) → the script exits 1 before any spend; surface the message and stop.
- An opencode "agent not found / falling back to default agent" warning on stderr → the tooling raises `HarnessExecutionError`: the suite aborts and no JSON is written (a run under the wrong agent is contamination, not data). Treat as a campaign abort.
- `split` / query-file validation failure → stop before spend, surface the message.
- `suite` exit 1 (harness execution failure, e.g. provider 429) → abort the campaign: surface the stderr error, keep the workspace; print its path and the campaign dir path (campaign artifacts persist by design), apply nothing. No retries.
- Suite totals with 0 scored runs (all void) → broken conditions: abort as above (a campaign of timeouts measures nothing). Applies to train rounds and the validate pass alike, and is checked before the zero-failures early exit; the sanity check is the only exception (all-void = inconclusive).
- Sanity inconclusive (all void) → reported as inconclusive; not a pass, not a restart; the user decides.

## Gotchas

- The harness is always user-specified; never infer it from the environment.
- Eval reps run under the restricted `trigger-evaluator` agent, installed into each workspace by the evaluator itself; never run reps as the default agent and never re-add `--auto`.
- A `triggered` verdict resting on interrupted-run intent (`timeout: true`) is a pass but weaker evidence; check the `timeouts` counts before trusting a score.
- Revisions touch the workspace stub only; the source file changes only on confirmed write-back at the end.
- Never restart the loop after a sanity failure; never train on sealed-pool queries.
- Never fabricate workspace files for a query, and never rewrite a query to make it pass — a query that fails under every candidate is flagged as suspect in the report, not fixed mid-campaign.
- The validate set runs once, at the end, against the winner; it is not part of the optimization loop.
- With <= 10 queries the validate split is empty — there is no validate pass to run; say so, and why, instead of running anything.
- Keep queries verbatim across the whole campaign; editing mid-campaign invalidates comparisons.
- Early exit only on a perfect train round; never on a "good enough" majority.
- Campaign artifacts (split files, result JSON, logs, sealed pool, per-iteration description copies) live in the persistent campaign dir under `trigger-tests/`; never inside the temp eval workspace.
- The manifest is written only by `evaluator.py record`, only after a passed sanity check and a resolved write-back decision; never hand-write or edit it mid-campaign. One manifest per skill lives at `skills-workspace/<skill>/manifest.json`; `record` overwrites only its own track's key (`trigger-test` or `retrieval-test`) and preserves everything else.
- For the trigger track, the manifest checksum hashes the frontmatter block only (`record --scope frontmatter`) — the same bytes the eval stub carries — so body-only edits never invalidate a recorded score.

## Checklist

- [ ] Harness explicitly specified by the user; `check` passed before any spend
- [ ] Evaluator agent installed per workspace by `run`/`suite` (strategy.install); an agent-fallback warning aborts, never runs under the default agent
- [ ] Planned-spend report confirmed by the user
- [ ] Workspace synced and `status` clean before the first suite run
- [ ] Campaign dir created via campaign-init; every artifact path points inside it
- [ ] Split seed recorded; sealed pool written before iteration 1
- [ ] Every suite run's JSON read from `--out`; no prose parsing
- [ ] Each iteration's evaluated description saved to <campaign>/iter-<i>-description.md
- [ ] Every failure category backed by a cited phrase from the run's reasoning (via `evaluator.py evidence --track trigger-test`)
- [ ] Early exit only on zero train failures; max 3 iterations
- [ ] Winner = highest train score; stub matches winner before validate/sanity
- [ ] Validate once; overfit warning if below winner's train score
- [ ] Sanity via single-query suite; failure stops with no write-back offer
- [ ] Suspect queries (failed under every candidate in every iteration) flagged in the report, each with its timeouts count
- [ ] Write-back only after explicit user confirmation
- [ ] Manifest recorded via `record --scope frontmatter` on sanity pass after the write-back decision; declined write-back NOT recorded
- [ ] Workspace removed on completion (kept and reported on abort); campaign dir always kept
