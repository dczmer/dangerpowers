---
name: trigger-testing
description: Use when testing or optimizing a skill's trigger description with eval queries, train and validation splits, and detection-harness campaigns, when a new or edited description needs a passing eval set before it ships, or when running trigger-eval campaigns against one skill or a list of skills run sequentially.
---

# Trigger Testing

**Core principle:** A skill description causes loading on the right user prompts and not on the wrong ones. If you didn't measure that, you don't know it ships. Eval set first, always.

Run this campaign when a skill's description is designed or revised, before the skill ships, or any time an existing skill's trigger behavior needs measuring. Applies to every skill, including pure reference.

## Workflow

Input: one target skill name, or a list of target skills. The skill name(s) are the only user input; the campaign runs autonomously from there — no step asks the user anything.

1. Read the target skill's `SKILL.md` and its current frontmatter `description`.
2. Build the eval set per Trigger Eval Query Design; split it per Train/Validation Split into `trigger-evals/train.json` and `trigger-evals/validation.json`. You author every query yourself — never ask the user to supply, confirm, or answer eval queries.
3. Smoke-test the harness (see Harness below): dispatch ONE should-trigger query as a `Task` tool call to the `trigger-evaluator` subagent and read the rep's returned message before dispatching full runs. The smoke rep verifies the `trigger-evaluator` subagent receives skill descriptions in context and can invoke the skill tool — if the subagent cannot load skills, stop and fix the agent configuration before any campaign. Because detection under this harness is the rep's own report (not a greppable event stream), the smoke run must also confirm the rep names the specific skill it loaded, distinguishing the candidate from a sibling.
4. Run the Optimization Loop: evaluate, revise per failure class, repeat — selecting the best iteration by validation pass rate.
5. Run the fresh-query sanity check; at most one train-expansion re-opt.
6. Check the Done Criteria, then write the results log per Results Log Format — one log per target skill.
7. Given a list of skills, advance per Multi-Skill Campaigns.

## Scope

Trigger optimization measures **the decision to load at all** — not compliance after load. It is a separate testing axis from pressure testing:

- Pressure testing gates the **body rules** of discipline skills; trigger evals gate the **description** of every skill.
- It applies to every skill regardless of type — discipline, technique, pattern, and reference. Reference skills (exempt from pressure testing per the writing-skills skill's Testing Discipline Skills section) are NOT exempt here: a reference skill with a description that fails to trigger is a skill that never loads.
- A skill can pass one axis and fail the other. A perfectly pressure-tested body with a description that never triggers is invisible; a description that triggers perfectly on rules that violate under pressure is untrustworthy. Run both axes; do not substitute one for the other.

## Description Best Practices

Rules for writing and revising skill descriptions:

- **Imperative opener.** Start with "Use when..." plus concrete triggering conditions and symptoms.
- **WHAT + WHEN.** State what the skill produces (one clause) so the agent can match user intent, and when to use it. Write for user intent, not implementation mechanics.
- **Err on the side of being pushy.** List contexts where the skill applies, including situations where the user doesn't name the domain — the description is the primary trigger mechanism, and under-triggering makes the skill invisible.
- **Never summarize the workflow.** A description that summarizes the process becomes a shortcut agents follow instead of reading the skill body.
- **Concise.** A few sentences to a short paragraph, hard limit 1024 chars. Every token competes with all other skills' descriptions at startup. Move exhaustive anti-pattern enumerations into the body; keep only the most discriminating trigger or symptom in the description.
- **Weave trigger terms into prose** (error messages, symptoms, synonyms, tool names). Never append a `Keywords:` or `Trigger phrases:` label.
- **YAML safety.** The description is a YAML scalar: a plain scalar cannot contain a colon followed by a space, and the 1024-char limit is hard. Prefer plain prose; use a block scalar (`description: >`) only if a list-like term is genuinely unavoidable.
- **Generalize failures.** When an eval query fails, address the general category the query represents — never paste the failed query's specific keywords into the description (that overfits).

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

Split the eval queries ~60/40 into `trigger-evals/train.json` and `trigger-evals/validation.json` (sibling to `test-campaigns/` in the skill's directory). Shuffle randomly, then **keep the split fixed across iterations** — comparisons are apples-to-apples only if the same queries sit in the same bucket each run. Both sets contain a proportional mix of should-trigger and should-not.

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

**Never paste specific failed-query keywords into the description** — that overfits. Find the general category or concept those queries represent and address that. (Cross-reference: this is the same principle encoded in this skill's Description Best Practices — weave trigger terms into prose, never enumerate them as a labeled list.)

## Harness

Every query — smoke, train, validation, fresh — is dispatched to a subagent via the `Task` tool. Queries are NEVER sent to the user. The `question` tool plays no role in this campaign; if you are about to ask the user an eval query, you have confused the measurement target — the subagent rep is the subject under test, not the user.

**Invoke:** one `Task` tool call per rep, with these exact parameters:

- `subagent_type`: `"trigger-evaluator"` (defined in `agents/trigger-evaluator.md`) — always; never `general` or another agent.
- `prompt`: the eval query verbatim, as the entire prompt — nothing else (see Bare-query dispatch below).
- `description`: a neutral 3–5 word bookkeeping label (e.g. `"trigger rep: should-trigger"`). This labels the task for the runner, so keep the candidate skill's name and expected verdict out of it.
- Never set `task_id` — every rep is a fresh session (see Rep independence below).

Reps run from the repo root.

**Bare-query dispatch:** the dispatch prompt contains ONLY the eval query — no framing, no skill names, no indication that it is a test. The campaign runner's context is saturated with the candidate skill (it read the SKILL.md and authored the eval set); anything beyond the bare query carries that context into the rep and biases the routing decision, so the rep measures the prompt instead of the description.

Reps MUST run under the `trigger-evaluator` agent (`agents/trigger-evaluator.md`). Its read-only tool set makes workload execution impossible: a triggered skill loads (which is the measurement) but cannot write files, run commands, or dispatch agents.

**Detection:** the rep's final message reports which skill it loaded (the skill tool's `name` input) or that no skill matched. Detection **must** be candidate-specific. A rep where a *sibling* skill fired instead of the candidate is a FAIL, not a pass — "any skill fired" is the failure mode the smoke test caught (`prompt-shaping` stole routing from `writing-prds`).

**Rep independence:** every rep is a fresh task invocation — never resume a prior rep's session. Reps share no context with each other or with later iterations.

**Pass criterion:** should-trigger query passes when trigger rate > 0.5 over ≥3 reps; should-not passes when rate < 0.5. Reps ≥3 per query. **Bump to 5 reps only on consecutive-opposite-outcome** — a 3-of-3 split across trigger / no-trigger (≥2 distinct outcomes over the 3 baseline reps). Borderline verdicts no longer rest on agent judgment alone; record the 3 per-rep outcomes and a one-line rationale in the campaign log. **Bump rate cap: ≤25% of queries per iteration** may be bumped.

**Load-and-stop (per rep):** the rep measures the load decision only. After the skill tool returns, the rep MUST report the loaded skill's exact name (or the no-match decision) in one line and end the turn. The loaded skill body is context only — the rep must not load or activate any skill workflow or procedures: do not begin step 1, do not create todos from its checklist, do not follow its process, do not narrate "starting" the workflow. A rep that begins executing a loaded skill's workflow is void — re-dispatch a fresh replacement and never count it, same convention as error/hang voids. Because dispatch is bare-query, no prompt framing may carry this rule into the rep; the `trigger-evaluator` agent definition is the enforcement channel, which is why every rep MUST run under that agent and no other.

**Workload isolation (per rep):** reps run under `trigger-evaluator`, so a triggered skill's workload cannot execute — that is the abort mechanism, and it is structural, not procedural. If a rep hangs or fails to return a clear load/no-load verdict (error, or a report that names neither a loaded skill nor a no-match decision), void it and re-dispatch a fresh replacement — mirroring the pressure-testing void-run convention. Never count a voided rep.

**Intra-iteration rep parallelism:** dispatch the per-iteration rep matrix in parallel in one message — multiple `Task` calls in a single assistant message, each configured per the Invoke spec above. Reps within one iteration are interchangeable; the next iteration depends on the previous iteration's *failures*, so inter-iteration stays serial. This is within-phase fan-out and does not violate a plan's `Execution: inline` / `Parallel group: none` declarations — those govern inter-phase parallelism, not intra-phase fan-out.

## Contamination Rules

1. **Cross-skill description visibility is expected, not contamination.** Per repo `AGENTS.md`, these skills ship together, so a sibling routing win on a should-trigger rep is a real measurement, not an error to be filtered out.
2. **Repo `AGENTS.md` loads in every rep — do not strip it.** Reps run from the repo root, so the repo's rules file is in context. It is constant across iterations, so it cannot bias the train/validation comparisons that select the winning description, and it is part of the deployment reality for this repo's skill library. If `AGENTS.md` names the candidate skill verbatim, record that in the campaign log — absolute trigger rates for that skill may read high relative to deployments without it.

## Done Criteria

A trigger eval is bulletproof when:

- All train queries pass over the run (≥3 reps each, >0.5 trigger rate for should-trigger, <0.5 for should-not).
- Validation pass rate is the **highest** across iterations tried — not just the last iteration.
- Fresh-query sanity check (5 queries never used in optimization) passes; at most 1 train-expansion re-opt was performed if the first fresh check failed.
- Description is still ≤1024 chars.

The selected description may not be the last iteration — it is the one with the best validation pass rate.

## Multi-Skill Campaigns

When a plan campaigns multiple skills in sequence against a shared live description state, selecting the best-validation-pass-rate iteration may change an earlier skill's description to a non-final (earlier) iteration. A later phase's campaign runs against the live state of all skills, including just-campaigned earlier skills — so a later phase's regression can route differently than the earlier phase's measurement assumed, and recorded pass rates no longer hold.

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
| Skipping the smoke-test (1-rep dispatch) before running the full campaign | Run ONE rep through the harness and read its output before dispatching the full rep matrix |
| Running reps with a full-tool agent | Always dispatch the `trigger-evaluator` subagent — under a full-tool agent a triggered skill executes its real workload on every rep |
| Rep begins the loaded skill's workflow after the load event | The rep's job ends at the load decision — report the skill name and stop. A workflow-executing rep is void; re-dispatch and never count it |
| Adding framing, skill names, or "this is a test" context to the rep dispatch prompt | Dispatch the bare eval query only — anything more carries the runner's context into the rep and biases the routing measurement |
| Asking the user eval queries via the `question` tool | The user is never a rep. All queries go to `trigger-evaluator` subagents via `Task`; the runner authors them without user input. |

## Results Log Format

Trigger eval logs use the campaign log format: title `# Test Campaign: <skill-name> — <date>`, with per-run bullets recording verdicts and verbatim evidence. Save trigger campaigns to `test-campaigns/YYYY-MM-DD-<skill-name>-trigger.md` — the `-trigger` suffix distinguishes them from discipline pressure-test campaigns at `test-campaigns/YYYY-MM-DD-<skill-name>.md`. If a log for the same skill and suffix already exists for that date, insert a two-digit sequence number: `test-campaigns/YYYY-MM-DD-NN-<skill-name>-trigger.md`, incrementing NN per additional same-day campaign.

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

The campaign log is the ONLY place trigger status lives. Never add trigger status, verdicts, `test-campaigns/`, or `trigger-evals/` references to `SKILL.md` — `SKILL.md` is loaded into working context on every run, and status notes there bloat context and invite agents to read the logs.

### `trigger-evals/` directory convention

The `trigger-evals/` directory lives beside `test-campaigns/` in the skill's host directory and holds `train.json`, `validation.json`, and any post-selection `YYYY-MM-DD-fresh.json`. Files are JSON arrays of `{"query": "<str>", "should_trigger": <bool>}` objects. Committed to source control like `test-campaigns/` — `trigger-evals/` is NOT gitignored. Linked from the campaign index by filename; never referenced from `SKILL.md`. The first trigger campaign creates the directory; this plan creates none.

## Standalone Boundary

This skill ends when each target skill's trigger results log is written. Do not suggest, auto-invoke, or chain into any other skill; the user decides what happens next with the campaign results.
