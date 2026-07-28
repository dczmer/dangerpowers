# Trigger Optimizing

**Load this reference when:** designing or revising a skill's `description`, before deployment — applies to all skills, including pure reference (which are exempt from pressure testing).

**Core principle:** A skill description causes loading on the right user prompts and not on the wrong ones. If you didn't measure that, you don't know it ships. Eval set first, always.

## Scope

Trigger optimization measures **the decision to load at all** — not compliance after load. It is a separate testing axis from pressure testing:

- Pressure testing gates the **body rules** of discipline skills; trigger evals gate the **description** of every skill.
- It applies to every skill regardless of type — discipline, technique, pattern, and reference. Reference skills (exempt from pressure testing per `SKILL.md:138–149`) are NOT exempt here: a reference skill with a description that fails to trigger is a skill that never loads.
- A skill can pass one axis and fail the other. A perfectly pressure-tested body with a description that never triggers is invisible; a description that triggers perfectly on rules that violate under pressure is untrustworthy. Run both axes; do not substitute one for the other.

## Trigger Eval Query Design

Build **≤5 should-trigger** and **≤5 should-not** queries (≤10 total). Aim for the full cap when the skill's triggering surface is broad; fewer are acceptable when it is trivially unique. The should-nots are the discriminating half — they decide whether the description has any boundary at all.

### Should-trigger axes

Vary queries across these axes so the set exercises the description, not a single phrasing:

| Axis | Variation |
|------|-----------|
| Phrasing formality | "write a PRD" vs. "draft the requirements doc" vs. "I need to spec a feature" |
| Explicitness | names the domain outright vs. describes a need without naming the skill |
| Detail level | bare one-liner vs. buried in a long message with file paths and constraints |
| Complexity | single-step request vs. one link in a larger chain ("after the research is done, also...") |

### Should-not negatives

Use **near-miss** negatives — queries that share keywords or concepts with the skill but need something different. `"What's the weather?"` is a weak negative: it tests nothing, because no skill would trigger on it. A strong negative for `writing-prds` is "help me write a README for this library" — same surface keywords ("write", "documentation"), different need.

Reject weak negatives at design time. A near-miss negative that the description correctly *doesn't* fire on is the highest-signal query in the set.

### Realism tips

Real user prompts look a particular way. Make queries resemble them:

- File paths: `~/Downloads/report_final_v2.xlsx`, `src/services/auth.ts`
- Personal context: "my manager asked me to...", "the oncall paged me about..."
- Specific details: column names, company names, data values, version numbers
- Casual language, abbreviations, occasional typos — not polished prose

A set of polished, keyword-perfect queries overfits: the description will pass on queries that look like the set and fail on real ones.

## Train/Validation Split

Split the ~20 queries ~60/40 into `trigger-evals/train.json` and `trigger-evals/validation.json` (sibling to `test-campaigns/` in the skill's directory). Shuffle randomly, then **keep the split fixed across iterations** — comparisons are apples-to-apples only if the same queries sit in the same bucket each run. Both sets contain a proportional mix of should-trigger and should-not.

Why split: optimizing against the full set risks overfitting to the exact queries. Train results guide changes; **validation pass rate selects the best iteration**, which may not be the last.

## The Optimization Loop

≤3 iterations. The four steps, in spirit from agentskills.io:

1. **Evaluate current description** on train + validation.
2. **Identify train-set failures only.** Train results guide changes; validation results are set aside — do not tune against them.
3. **Revise per failure class** (table below).
4. **Repeat** until all train queries pass or improvement stalls. Select the best iteration by validation pass rate — which may not be the last.

Re-check the 1024-char description ceiling **every iteration**. Descriptions grow during optimization; a passing iteration that blew the ceiling is invalid, not a win.

Then run a **fresh-query sanity check**: 5 queries never used in optimization, run once through the harness. If the selected description fails the fresh check, the train set was unrepresentative — expand train and re-optimize **at most once** (one train expansion; ≤3 iterations on the expanded set, same cap). Ship the best-validation-pass-rate iteration even if the fresh check still fails — record residuals and defer them to a follow-up plan, mirroring the iteration cap. Do not iterate against the fresh queries themselves (they would become a second train set).

### Failure-class remediation

| Failure | Likely cause | Action |
|---------|-------------|--------|
| Should-trigger query didn't fire | description too narrow | broaden scope or add context about when the skill is useful |
| Should-not query false-triggered | description too broad | add specificity about what the skill does NOT do; clarify boundary with adjacent skills |
| Same query fails repeatedly after tweaks | local minimum | try a structurally different framing of the description rather than incremental tweaks |

**Never paste specific failed-query keywords into the description** — that overfits. Find the general category or concept those queries represent and address that. (Cross-reference: this is the same principle already encoded in `SKILL.md`'s Frontmatter guidance — weave trigger terms into prose, never enumerate them as a labeled list — see `SKILL.md:53`.)

## opencode Harness

Verified mechanics from this plan's smoke test.

**Invoke:** `opencode run --dir <repo-root> --format json "<query>" > out.json 2>&1`.

`--format json` is the only JSON-shaped option (there is no `--json` flag). Output is NDJSON. A skill load appears as one event:

```
{"type":"tool_use","part":{"type":"tool","tool":"skill","input":{"name":"<skill>"}, ...}}
```

**Detect a candidate trigger:** `grep '"tool":"skill"' out.json | grep -q '"name":"<candidate-skill>"'`.

Detection **must** be candidate-specific via `input.name`. A rep where a *sibling* skill fired instead of the candidate is a FAIL, not a pass — "any skill fired" is the failure mode the smoke test caught (`prompt-shaping` stole routing from `writing-prds`).

**Eval loop skeleton** (matching `pressure-testing.md`'s inline bash pattern):

```bash
SKILL="<candidate>"
for q_set in train validation; do
  for f in trigger-evals/${q_set}/*.json; do
    while IFS= read -r query; do
      should_trigger=$(jq -r '.should_trigger' <<<"$row")
      out=$(mktemp); opencode run --dir /home/dave/source/dangerpowers \
        --format json "$query" > "$out" 2>&1
      triggered=$(grep '"tool":"skill"' "$out" | grep -q "\"name\":\"$SKILL\"" && echo yes || echo no)
      # record (query, should_trigger, triggered)
      rm "$out"
    done < <(jq -rc '.[] | "\(.query)\t\(.should_trigger)"' "$f")
  done
done
```

**Pass criterion:** should-trigger query passes when trigger rate > 0.5 over ≥3 reps; should-not passes when rate < 0.5. Reps ≥3 per query. **Bump to 5 reps only on consecutive-opposite-outcome** — a 3-of-3 split across trigger / no-trigger (≥2 distinct outcomes over the 3 baseline reps). Borderline verdicts no longer rest on agent judgment alone; record the 3 per-rep outcomes and a one-line rationale in the campaign log. **Bump rate cap: ≤25% of queries per iteration** may be bumped.

**Early-abort policy (per rep, both directions):** stop reading the response once the rep is decided — do not wait for completion. **Should-trigger:** once `tool_use skill <candidate>` appears in the stream, the rep is decided — record the verdict and stop. **Should-not:** once the agent emits substantive non-skill work, the rep is decided — record the verdict and stop. This is a per-rep policy, not a tip; it cuts output tokens materially on decided reps.

**Intra-iteration rep parallelism:** dispatch the per-iteration rep matrix in parallel (e.g. `xargs -P N` or a small job queue). Reps within one iteration are interchangeable; the next iteration depends on the previous iteration's *failures*, so inter-iteration stays serial. This is within-phase bash fan-out and does not violate a plan's `Execution: inline` / `Parallel group: none` declarations — those govern inter-phase parallelism, not intra-phase fan-out.

## Contamination Rules

1. **Do not strip skills via `XDG_CONFIG_HOME=$(mktemp -d)`.** That strips the candidate being measured. Trigger evals run with the repo's full skill set present, because that is the deployment reality — sibling routing competition is the cost the eval catches (the smoke test caught it). This is the opposite of pressure-test baselines, which strip skills to isolate the rule under test.
2. **Verify the global `~/.config/opencode/AGENTS.md` is empty or absent before each campaign.** If it isn't, subagent baselines may be primed by global rules bleeding through; flag and resolve before trusting results. (This mirrors the repo top-level `AGENTS.md` "Pressure Test Pollution" note.)
3. **Cross-skill description visibility is expected, not contamination.** Per repo `AGENTS.md`, these skills ship together, so a sibling routing win on a should-trigger rep is a real measurement, not an error to be filtered out.

## Done Criteria

A trigger eval is bulletproof when:

- All train queries pass over the run (≥3 reps each, >0.5 trigger rate for should-trigger, <0.5 for should-not).
- Validation pass rate is the **highest** across iterations tried — not just the last iteration.
- Fresh-query sanity check (5 queries never used in optimization) passes; at most 1 train-expansion re-opt was performed if the first fresh check failed.
- Description is still ≤1024 chars.

The selected description may not be the last iteration — it is the one with the best validation pass rate.

## Multi-Skill Campaigns

When a plan campaigns multiple skills in sequence against a shared live `SKILL.md:3` state, selecting the best-validation-pass-rate iteration may change an earlier skill's description to a non-final (earlier) iteration. A later phase's campaign runs against the live state of all skills, including just-campaigned earlier skills — so a later phase's regression can route differently than the earlier phase's measurement assumed, and recorded pass rates no longer hold.

**Final-Verification regression smoke:** in the plan's Final Verification, re-run 1 rep of each campaigned skill's canonical should-trigger smoke query against the final pinned description state (~12 reps for a 12-skill plan). Report any cross-phase routing regression. This is cheap insurance against the assertion that file-disjoint edits can't cross-talk — true for *files* but not for *routing behavior* when the candidate description itself changed mid-campaign.

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Optimizing against the full eval set (no split) | Use train/validation split; select best iteration by validation pass rate |
| Pasting failed-query keywords into the description | Find the general category, not the specific query |
| Stopping at the last iteration | Compare validation pass rates across all iterations; pick the best |
| Treating a sibling skill firing as "any skill fired, pass" | Detection must check `input.name` against the candidate specifically |
| Forgetting the 1024-char ceiling mid-optimization | Re-check every iteration; descriptions grow |
| Stripping skills via `XDG_CONFIG_HOME` for "clean" baselines | Wrong approach for trigger evals — keeps the candidate out. Trigger-eval baselines measure the candidate's routing rate against siblings |
| Skipping the smoke-test (1-rep dispatch) before running the full campaign | Run ONE rep through the harness and read its output before dispatching the full 60+ invocations |

## Results Log Format

Trigger eval logs extend the existing campaign log format (which lives at `pressure-testing.md:172`). Save trigger campaigns to `test-campaigns/YYYY-MM-DD-<skill-name>-trigger.md` — the `-trigger` suffix distinguishes them from discipline pressure-test campaigns at `test-campaigns/YYYY-MM-DD-<skill-name>.md`.

Two optional sections, appended in addition to or in place of `## Baseline` / `## With skill` when the campaign is trigger-focused:

```markdown
## Trigger evals

### Iteration 1
- Description (≤1024 chars): <paste verbatim>
- Train pass rate: <N>/<M> queries
- Validation pass rate: <N>/<M> queries
- Train failures: <list queries+failure type>
- Revision rationale: <one paragraph>

### Iteration 2 — <…>

### Selected iteration: <N> (validation pass rate <X>)
```

And:

```markdown
## Fresh-query sanity check
- 5 queries never used in optimization:
  - <query>: <triggered candidate | sibling | not triggered> — pass | fail
- Pass rate: <N>/<M>
```

The campaign log is the ONLY place trigger status lives. Never add trigger status, verdicts, `test-campaigns/`, or `trigger-evals/` references to `SKILL.md` — `SKILL.md` is loaded into working context on every run, and status notes there bloat context and invite agents to read the logs. (Extends the existing rule at `SKILL.md:151`.)

### `trigger-evals/` directory convention

The `trigger-evals/` directory lives beside `test-campaigns/` in the skill's host directory and holds `train.json`, `validation.json`, and any post-selection `YYYY-MM-DD-fresh.json`. Files are JSON arrays of `{"query": "<str>", "should_trigger": <bool>}` objects (matching the agentskills.io schema). Committed to source control like `test-campaigns/` — `trigger-evals/` is NOT gitignored. Linked from the campaign index by filename; never referenced from `SKILL.md`. The first trigger campaign creates the directory; this plan creates none.