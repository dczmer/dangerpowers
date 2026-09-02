# Phase 2b: Campaign Tooling (split + suite) — Implementation Plan

Companion to `developing-a-better-harness.md`, section "Implementing the Campaign and Skill".
This plan is decision-complete: every choice below is either a locked decision from the
design review or an explicitly registered assumption (see "Assumptions register"). The
implementing agent should not introduce new decisions; anything ambiguous is called out
here with the chosen behavior.

**Scope: the deterministic campaign tooling.** `evaluator.py` gains two subcommands:
`split` (stratified train/validate split) and `suite` (run one full query set, emit
structured JSON). Together they are the campaign's units of work — one `suite`
invocation is one train round, the validate pass, or the sanity check. Nothing here
loops, judges, or revises descriptions; that judgment lives in the skill (phase 2c).
Requires phase 2a (`phase-2a-restricted-evaluator-agent-plan.md`) complete: the
strategy registry, `strategy.install()`, the `check` subcommand, and the
`timeout`-flagged `Verdict` already exist and are reused unchanged.
NOT in scope: the SKILL.md campaign rewrite (phase 2c,
`phase-2c-campaign-skill-plan.md`), pi/claude harness strategy implementations,
artifact management (manifest.json, campaign history), retries or token-budget
enforcement.

## Locked decisions (from design review with the user)

Numbering follows the original phase-2 design-review list; decisions owned by the other
phases (harness/agent setup, the skill workflow) live in their own plans.

2. **Deterministic suite-runner.** The campaign loop does not live in the skill.
   `evaluator.py` gains new subcommands (`check` in phase 2a; `split` and `suite`
   here) that do all looping, counting, splitting, aggregation, and scoring. The
   skill performs only judgment steps and consumes only machine-readable output
   (exit codes and JSON files); it never parses prose stdout.
7. **Harness is a required, user-specified parameter** (implemented in phase 2a):
   `--harness` is required on `suite`, exactly as on `run` and `check`.

## Deliverables

- **Modified:** `skills/trigger-testing-skills/scripts/evaluator.py` — new `split` and
  `suite` subcommands (see "CLI contracts"). Nothing else changes: the strategy
  registry, `check`, `run`, signal detection, and `Verdict` are phase 2a.
- **Unchanged:** `skills/trigger-testing-skills/SKILL.md` (rewritten in phase 2c),
  `workspace-manager.sh`, both evaluator-agent files.

Python >= 3.10, standard library only (adds `random` to the phase-2a imports).

## CLI contracts

All harness-taking subcommands require `--harness`. Exit codes everywhere:
`0` = success; `1` = operational/validation error or harness execution failure;
`2` = argparse usage errors.

### `split` (new)

```
usage: evaluator.py split --queries FILE --out-dir DIR
                          [--train-frac 0.6] [--seed N]
```

Deterministic stratified split. Pure function: no harness, no evals.

- Reads and strictly validates the query file: a JSON list of objects, each with
  `query` (non-empty string) and `shouldTrigger` (boolean). Any violation:
  `error: <exact reason>` (file missing, invalid JSON, entry N missing 'query', ...)
  to stderr, exit 1.
- **No-split path (<= 10 queries):** `train.json` = the full set, `validate.json` =
  `[]`; prints `note: <=10 queries, no validate split (train=<n>, validate=0)`.
- **Split path (> 10 queries):** per class (`shouldTrigger` true/false separately):
  shuffle with `random.Random(seed)`, `n_validate = int(len * (1 - train_frac) + 0.5)`
  clamped to `[0, len-1]` for every class size (for a class of 1 the clamp range is
  `[0, 0]`, so its item always stays in train), first `n_validate` go to validate,
  rest to train. Then shuffle train and validate (same RNG). `--train-frac` must be
  in (0, 1); otherwise `error: --train-frac must be in (0, 1)` to stderr, exit 1.
- If `--seed` is omitted, one is drawn from `random.SystemRandom`, recorded in
  `split.json`, and **printed** so the campaign record keeps it.
- Writes `<out-dir>/train.json` and `<out-dir>/validate.json` in the same schema as
  the input (`[{"query": ..., "shouldTrigger": ...}]`); creates `--out-dir` if needed.
- Also writes `<out-dir>/split.json` on every path (split and no-split):
  `{"seed": <s>, "train": <a>, "validate": <b>}` — the machine-readable channel the
  skill reads for the seed and the planned-spend sizes (locked decision 2).
- Stdout summary: `split: <n> queries -> train <a> / validate <b> (seed <s>)`
  plus per-class counts.

### `suite` (new)

```
usage: evaluator.py suite --harness NAME --skill NAME --workspace DIR
                          --queries FILE --out FILE
                          [--model MODEL] [--variant EFFORT]
                          [--reps 10] [--timeout 30]
```

Runs one full query set and emits structured results. This is the campaign's unit of
work (one invocation = one train round, or the validate pass, or the sanity check).

- Validates exactly like `run` (stub present, reps/timeout >= 1, evaluator agent
  installed via `strategy.install`) plus: harness supported + binary present + agent
  source asset present (same messages as `check`), query file valid (same rules
  as `split`), `--out` parent writable. Each failure: exact reason to stderr, exit 1.
- Empty query file (`[]`): writes a result JSON with empty `queries` and totals of
  zero counts with null `wilson_*`/`score`, prints a note, exit 0. (The validate
  pass is simply skipped by the skill instead; this path exists so a stray
  invocation is not an error.)
- Execution: queries are processed **sequentially** in file order; each query runs
  through the phase-1 `eval_batch` unchanged (smoke rep alone, then parallel batches
  of <= 10). Parallelism stays within a query to bound provider load.
- Progress on stdout, reusing the phase-1 log formats, plus a per-query line after
  each query completes: `[query i/n] "<query>" -> <p> pass / <f> fail / <v> void
  score: <s>` (`score: n/a` when the query is all-void).
- **Harness failure policy (unchanged from phase 1):** any `HarnessExecutionError`
  aborts the suite immediately — error to stderr, exit 1, **no JSON file written**.
  A partial result file is never produced.
- After all queries: pooled totals over all non-void runs of all queries, one Wilson
  interval on the pool, `score = wilson_low` (nulls when the pool has 0 scored runs),
  and the JSON written to `--out`.

`suite --out` JSON schema:

```json
{
  "skill": "writing-skills",
  "harness": "opencode",
  "model": "...", "variant": null,
  "reps": 10, "timeout": 30,
  "queries": [
    {
      "query": "...", "should_trigger": true,
      "passed": 8, "failed": 1, "void": 1, "timeouts": 1,
      "wilson_low": 0.462, "wilson_high": 0.974, "score": 0.462,
      "failures": [
        {"run": 3, "outcome": "not-triggered", "detail": "...",
         "reasoning": "...", "timeout": false}
      ]
    }
  ],
  "totals": {"passed": 74, "failed": 20, "void": 6, "timeouts": 3,
             "wilson_low": 0.613, "wilson_high": 0.812, "score": 0.613}
}
```

- `failures` contains only non-void runs whose outcome mismatched the expectation,
  with that run's captured reasoning — exactly what the analysis step needs. Void runs
  appear only in the counts. `timeout` on a failure entry marks a mismatch that rests
  on interrupted-run intent evidence (phase-2a locked decision 11).
- `timeouts` counts verdicts with `timeout: true` (any outcome), per query and
  pooled — the analysis step uses it to see how much of a score rests on
  interrupted-run intent.
- Per-query `wilson_*`/`score` are computed as in phase 1 (nulls when a query is all
  void). Totals pool raw counts first, then compute one interval (not an average of
  intervals).

## Error handling policies

- `split` / query-file validation failure → exact reason to stderr, exit 1, before
  any spend. The skill (phase 2c) stops the campaign on this and surfaces the
  message.
- `suite` harness execution failure (e.g. provider 429, agent-fallback warning per
  phase 2a) → abort the suite immediately: error to stderr, exit 1, no JSON file
  written. No retries this phase.
- Empty query file → not an error: zeroed result JSON, note on stdout, exit 0.

## Exact validation commands

Run from the repo root. Use a cheap model and small reps.

```bash
# 1. split: real file, stratification, seed print, reproducibility
python3 skills/.../evaluator.py split \
  --queries skills-workspace/writing-skills/trigger-tests/queries.json \
  --out-dir /tmp/tt-split --seed 42
# expected: "split: 16 queries -> train ... / validate ... (seed 42)"; both files
# valid; split.json records {"seed": 42, "train": 9, "validate": 7}; rerun with
# --seed 42 produces identical files; different seed differs.
# Also: a 4-query file -> no-split note, validate.json == [],
# split.json {"seed": <s>, "train": 4, "validate": 0}.

# 2. suite: two-query file, verify JSON structure and pooled math by hand
WS="$(skills/trigger-testing-skills/scripts/workspace-manager.sh init)"
skills/trigger-testing-skills/scripts/workspace-manager.sh sync \
  --skill writing-skills --source . --workspace "$WS"
# fixture for 2-3 (labels don't affect the structural checks):
cat > /tmp/tt-two-queries.json <<'EOF'
[
  {"query": "create a skill to drive my webapp using playwright", "shouldTrigger": true},
  {"query": "what does the writing-skills skill do?", "shouldTrigger": false}
]
EOF
python3 skills/.../evaluator.py suite --harness opencode \
  --skill writing-skills --workspace "$WS" \
  --queries /tmp/tt-two-queries.json --out /tmp/tt-suite.json \
  --model kimi-for-coding/k3 --variant minimal --reps 3 --timeout 60
# expected: exit 0; progress lines per rep and per query; /tmp/tt-suite.json matches
# the schema (including per-query and totals "timeouts");
# totals.passed+failed+void == 6; score == pooled wilson_low.

# 3. suite abort path: unreachable provider -> exit 1, NO JSON file
python3 skills/.../evaluator.py suite --harness opencode \
  --skill writing-skills --workspace "$WS" \
  --queries /tmp/tt-two-queries.json --out /tmp/tt-should-not-exist.json \
  --model ollama/nonexistent --reps 3
# expected: exit 1; stderr names the failure; /tmp/tt-should-not-exist.json absent.

skills/trigger-testing-skills/scripts/workspace-manager.sh cleanup --workspace "$WS"
```

## Assumptions register (flag any you want reversed before implementation)

Numbering follows the original phase-2 register; assumptions owned by the other phases
are in their own plans.

1. Set-level score = pooled Wilson lower bound over all non-void runs in the set;
   per-query breakdown always present in the JSON for analysis.
2. Split: stratified by `shouldTrigger`, default train-frac 0.6, per-class validate
   count `int(n*(1-frac)+0.5)` clamped to `[0, n-1]` for every class size, so a
   class of >= 2 keeps >= 1 in train and a class of 1 always stays in train.
   Seeded; seed printed and written to `split.json`
   (with the train/validate sizes); re-drawn each campaign.
3. <= 10 queries -> no split; validate pass skipped (by the skill, phase 2c); winner
   by train score alone.
14. Sequential across queries; parallelism only within a query's reps.
19. `suite --out` is required; the skill consumes only exit codes and JSON files,
    never prose stdout.

## Known limitations / accepted risks

- Queries are processed sequentially within a suite by design (parallelism stays
  within a query's reps) to bound provider load; a large query set × reps is wall-clock
  bound by this.
- No retries/backoff: a provider rate limit aborts the suite with exit 1 and no JSON
  written. The campaign-level policy on that failure (keep workspace and scratch,
  surface the error) is phase 2c.
