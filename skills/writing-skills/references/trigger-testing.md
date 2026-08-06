# Trigger Testing

Campaign reference for `SKILL.md`. Load this when this skill is invoked to trigger-test an existing skill's description (Invocation Branch) or when the user opts in at the End-of-Flow Prompt.

Input: one target skill name, or a list of target skills. The skill name(s) are the only user input; the campaign runs autonomously from there — no step asks the user anything.

**Core principle:** A skill description causes loading on the right user prompts and not on the wrong ones. If you didn't measure that, you don't know it ships. Eval set first, always.

## Workflow

1. Confirm the target exists: resolve the named skill from the session's loaded skills — its `SKILL.md` lives at `<target-base>/SKILL.md`, where `<target-base>` is the base directory reported when the target skill loads. If the target is not loaded and cannot be found, report that the target cannot be found and stop — never invent a target.
2. Read the target skill's `SKILL.md` and its current frontmatter `description`.
3. Build the eval set per Trigger Eval Query Design; split it per Train/Validation Split into `trigger-evals/train.json` and `trigger-evals/validation.json`. You author every query yourself — never ask the user to supply, confirm, or answer eval queries.
4. Create the campaign workspace. The workspace contains frontmatter-only stubs of every skill in the plugin's `skills/` directory plus the `trigger-evaluator` agent. One workspace per campaign — every eval in this campaign reuses it; never create a workspace per eval, and never run `init` a second time.
   a. From the repo root, run exactly (`<base>` is the writing-skills base directory reported when this skill loaded — paste its absolute path):
      `WS=$(<base>/scripts/trigger-test.sh init) && echo "WORKSPACE=$WS"`
   b. Copy the printed path (it looks like `/tmp/trigger-test.XXXXXXXXXX`) into your working notes as **WS_PATH**. Shell variables do not survive between Bash tool invocations — in every later command, paste the literal WS_PATH wherever the workflow shows `"$WS"`; never rely on `$WS` or `TRIGGER_TEST_WORKSPACE`.
   c. Verify once: `ls WS_PATH/.agents/skills` must list every skill name. If it does not, stop and fix the workspace before any eval. Then confirm the candidate's stub matches the live SKILL.md — `<base>/scripts/trigger-test.sh status --skill <candidate> --workspace WS_PATH` must print `in-sync` (exit 0); re-run it any time mid-campaign you suspect drift, and re-`sync` on `stale`.
   d. If a later command fails with `workspace unset` or you have lost WS_PATH, recover the path from step 4a's output or by running `ls -d /tmp/trigger-test.*` — NEVER recover by re-running `init`. A second `init` creates a different workspace and orphans the first.
5. Smoke-test the harness (see Harness below): run ONE should-trigger query through the harness and read the verdict block before running full campaigns. The smoke run verifies the `trigger-evaluator` agent sees the stub descriptions and can invoke the skill tool — if the eval cannot load any skill, stop and fix the workspace or agent setup before any campaign. The smoke run must also confirm the verdict names the candidate skill specifically, distinguishing it from a sibling.
6. Run the Optimization Loop: evaluate, revise per failure class, repeat — selecting the best iteration by validation pass rate.
7. Run the fresh-query sanity check; at most one train-expansion re-opt.
8. Check the Done Criteria, then write the results log per Results Log Format — one log per target skill.
9. Given a list of skills, advance per Multi-Skill Campaigns.
10. Clean up the workspace: run `<base>/scripts/trigger-test.sh cleanup --workspace WS_PATH` with the literal path recorded in step 4b — always, including when the campaign aborts early. A finished campaign leaves no workspace artifacts behind; if cleanup cannot run because the path is lost, recover it per step 4d, then clean up.

## Scope

Trigger optimization measures **the decision to load at all** — not compliance after load.

- Trigger evals gate the **description** of every skill.
- It applies to every skill regardless of type — discipline, technique, pattern, and reference. Reference skills (exempt from pressure testing per the Scope section of `references/pressure-testing.md`) are NOT exempt here: a reference skill with a description that fails to trigger is a skill that never loads.

## Description Revision Rules

When the optimization loop revises a description, apply the description rules in the Frontmatter section of `SKILL.md` — imperative "Use when..." opener, WHAT + WHEN, no workflow summary, pushy trigger coverage, trigger terms woven into prose, YAML safety, ≤1024 chars, front-loaded boundaries, speech-act framing, quoted micro-phrases, verb-category negative classes. They are not restated here.

One rule is campaign-side only:

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

**Body-consistency check.** Before labeling a query should-not, read the candidate's `SKILL.md` body and confirm its "when to use / when not to use" statements agree with the label. A body that endorses the behavior a negative label forbids (e.g. a body saying "ask clarifying questions when underspecified" paired with a vague-request negative) predicts false-trigger failures that no description edit will fix — the router infers the skill's purpose from the body, and the description cannot outvote it.

### Realism tips

Real user prompts look a particular way. Make queries resemble them:

- File paths: `~/Downloads/report_final_v2.xlsx`, `src/services/auth.ts`
- Personal context: "my manager asked me to...", "the oncall paged me about..."
- Specific details: column names, company names, data values, version numbers
- Casual language, abbreviations, occasional typos — not polished prose

A set of polished, keyword-perfect queries overfits: the description will pass on queries that look like the set and fail on real ones.

## Train/Validation Split

Split the eval queries ~60/40 into `trigger-evals/train.json` and `trigger-evals/validation.json` in the target skill's own directory (where its SKILL.md resides, beside `test-campaigns/`). Shuffle randomly, then **keep the split fixed across iterations** — comparisons are apples-to-apples only if the same queries sit in the same bucket each run. Both sets contain a proportional mix of should-trigger and should-not.

Why split: optimizing against the full set risks overfitting to the exact queries. Train results guide changes; **validation pass rate selects the best iteration**, which may not be the last.

## The Optimization Loop

≤3 iterations. The four steps, in spirit from agentskills.io:

1. **Evaluate current description** on train + validation.
2. **Identify train-set failures only.** Train results guide changes; validation results are set aside — do not tune against them. **Read rep rationales forensically.** The rep's stated justification reveals which clause anchored its decision. If rationales quote phrasing that appears in *no* iteration of your description, the anchor is the skill body or a sibling's description — your edits aren't reaching the decision, and more rewording won't help.
3. **Revise per failure class** (table below), applying the rules in Description Revision Rules. After every description revision, re-sync the workspace stub — the stub is an init-time snapshot and does not track the real `SKILL.md`, so an un-synced next iteration measures the *previous* description and every verdict is garbage:
   `<base>/scripts/trigger-test.sh sync --skill <candidate> --workspace WS_PATH`
4. **Repeat** until all train queries pass or improvement stalls. Select the best iteration by validation pass rate — which may not be the last.

Re-check the 1024-char description ceiling **every iteration**. Descriptions grow during optimization; a passing iteration that blew the ceiling is invalid, not a win.

Then run a **fresh-query sanity check**: 5 queries never used in optimization, run once through the harness. If the selected description fails the fresh check, the train set was unrepresentative — expand train and re-optimize **at most once** (one train expansion; ≤3 iterations on the expanded set, same cap). Expand only if the fresh failure class is absent from train: if train already contains the failing class and it has failed across structurally distinct framings, expansion adds samples of a proven local minimum, not new signal — skip the re-opt and record residuals. Ship the best-validation-pass-rate iteration even if the fresh check still fails — record residuals and defer them to a follow-up plan, mirroring the iteration cap. Do not iterate against the fresh queries themselves (they would become a second train set).

### Failure-class remediation

| Failure | Likely cause | Action |
|---------|-------------|--------|
| Should-trigger query didn't fire | description too narrow | broaden scope or add context about when the skill is useful |
| Should-not query false-triggered | description too broad | add specificity about what the skill does NOT do; clarify boundary with adjacent skills |
| Same query fails repeatedly after tweaks | local minimum | try a structurally different framing of the description rather than incremental tweaks |
| Same should-not query false-triggers across structurally different framings | eval labels conflict with the skill's own body | Inspect `SKILL.md` for body statements that justify the unwanted trigger (e.g. "ask clarifying questions when underspecified"). A description cannot outvote the purpose a router infers from the body. Resolve the policy conflict first — relabel the evals or rewrite the body — before spending more iterations on the description |

**Never paste specific failed-query keywords into the description** — that overfits (the Generalize failures rule in Description Revision Rules). Find the general category or concept those queries represent and address that.

## Harness

Every query — smoke, train, validation, fresh — is executed by `<base>/scripts/trigger-test.sh` (the writing-skills base directory reported when this skill loaded) inside the campaign's isolated workspace. Queries are NEVER sent to the user. The `question` tool plays no role in this campaign; if you are about to ask the user an eval query, you have confused the measurement target — the workspace eval is the subject under test, not the user.

**Workspace lifecycle:** one workspace per campaign, created in Workflow step 4, reused for every eval, removed in Workflow step 10 — including on abort. The workspace holds frontmatter-only stubs of every skill plus the `trigger-evaluator` agent; skill bodies, the repo codebase, and the repo `AGENTS.md` are absent by construction. Stubs are an init-time snapshot: whenever the candidate's description changes during the optimization loop, run `trigger-test.sh sync --skill <candidate> --workspace WS_PATH` before the next eval — never re-run `init` to pick up a revision.

**Invoke:** one eval per rep, pasting the literal WS_PATH recorded in Workflow step 4b (`$WS` does not survive between shell invocations):

```bash
<base>/scripts/trigger-test.sh eval --skill <candidate> --workspace /tmp/trigger-test.XXXXXXXXXX "$(cat <<'EOF'
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
exit_code: <exit code of the opencode run>
timed_out: yes | no
```

A run that ends or hits its step limit without a load signal for the candidate is **not-loaded**; a run killed by the timeout guard follows the split semantics in Workload isolation below — load signal already present keeps the verdict, absent is void. Detection **must** be candidate-specific: an eval where a *sibling* skill fired instead of the candidate reports `verdict: not-loaded` with `conflict: wrong-skill` — "any skill fired" is the failure mode the smoke test caught (`prompt-shaping` stealing routing from `writing-prds`). The `conflict_skills` field names what actually loaded — target-plus-extras (`additional-skills`) or the wrong skill (`wrong-skill`) — so over-similar descriptions can be reworked.

**Rep independence:** every rep is a fresh `opencode run` session. Workspace reuse carries no context between reps — the workspace holds only static stubs and the agent definition, so a reused workspace cannot change an eval's outcome relative to running it alone.

**Pass criterion:** should-trigger query passes when trigger rate > 0.5 over ≥3 reps; should-not passes when rate < 0.5. Reps ≥3 per query. **Bump to 5 reps only on consecutive-opposite-outcome** — a 3-of-3 split across trigger / no-trigger (≥2 distinct outcomes over the 3 baseline reps). Borderline verdicts no longer rest on agent judgment alone; record the 3 per-rep outcomes and a one-line rationale in the campaign log. **Bump rate cap: ≤25% of queries per iteration** may be bumped.

**Load-and-stop (per rep):** the rep measures the load decision only. In the isolated workspace a loaded skill is a frontmatter stub — there is no body to execute — so post-load workflow execution is impossible by construction, and the `trigger-evaluator` agent's report-and-stop rule (`agents/trigger-evaluator.md`) remains as a second enforcement layer. An eval whose verdict block is missing or unparseable (script error, missing workspace, non-JSON output) is void — fix the cause, re-dispatch a fresh replacement, and never count it, same convention as error/hang voids.

**Workload isolation (per rep):** two structural layers. The stub-only workspace removes skill bodies, the codebase, and anything to analyze; the `trigger-evaluator` agent's skill-only tool surface and `steps` cap bound every rep's cost — that is the abort mechanism, and it is structural, not procedural. Timeout semantics split on the load signal: a timed-out rep whose event stream already contains the candidate's load signal keeps its verdict — the measurement happened before the kill; a timed-out rep with no load signal is **void** — the outcome is unknown, so retry it serially and never count it as not-loaded (counting it fabricates a false negative). The verdict block's `timed_out: yes|no` field marks which reps the guard killed; `trigger-test.sh batch` applies the void rule and serial retry automatically. Only a missing or unparseable verdict block joins timeout-without-load in the void class per Load-and-stop above.

**Intra-iteration rep parallelism:** run the per-iteration rep matrix through `trigger-test.sh batch --skill <candidate> --workspace WS_PATH --scenarios FILE` (one query per line), which executes reps through a bounded job pool at the default `--jobs 2`, retries timed-out-without-load reps serially, and prints each rep's verdict block plus a `batch summary:` line. Raise `--jobs` only when reps consistently finish well under the timeout (remote or fast models); on local models keep the default and let batch's serial retry absorb overload timeouts — unbounded fan-out saturates a local model and every rep times out. Reps within one iteration are interchangeable; the next iteration depends on the previous iteration's *failures*, so inter-iteration stays serial. This is within-phase fan-out and does not violate a plan's `Execution: inline` / `Parallel group: none` declarations — those govern inter-phase parallelism, not intra-phase fan-out.

## Contamination Rules

1. **Cross-skill description visibility is expected, not contamination.** These skills ship together in the same plugin, so a sibling routing win on a should-trigger eval is a real measurement, not an error to be filtered out. The workspace stubs every skill in the plugin's `skills/` directory, so sibling descriptions compete exactly as in deployment.
2. **Reps no longer see the repo `AGENTS.md` or the real codebase — rates recorded under the old repo-root harness are not comparable.** The isolated workspace removes both by design. Campaign logs written before this harness shipped were measured with `AGENTS.md` in context and real skill bodies present; treat them as a different measurement regime, never as a baseline to match.
3. **Globally installed skills can leak into the workspace.** Skills under `~/.config/opencode/skills`, `~/.claude/skills`, and `~/.agents/skills` load in every opencode run, including workspace evals. A load of a skill not shipped in this plugin appears in `loaded_skills`; record it in the campaign log as environmental noise and exclude it from conflict-rework decisions about the plugin's descriptions.

## Done Criteria

A trigger eval is bulletproof when:

- All train queries pass over the run (≥3 reps each, >0.5 trigger rate for should-trigger, <0.5 for should-not).
- Validation pass rate is the **highest** across iterations tried — not just the last iteration.
- Fresh-query sanity check (5 queries never used in optimization) passes; at most 1 train-expansion re-opt was performed if the first fresh check failed.
- Description is still ≤1024 chars.

The selected description may not be the last iteration — it is the one with the best validation pass rate. If no iteration meets all criteria within the caps, ship the best-validation-pass-rate iteration anyway per The Optimization Loop, and report the description as tested-with-residuals rather than bulletproof.

## Multi-Skill Campaigns

When invoked with a list of target skills, campaign them sequentially — one skill at a time, in the order given. For each skill, run the full campaign (Workflow steps 1-8, 10) and write its results log before advancing to the next; verify the log file exists before starting the next skill. Do not interleave evals across skills, and do not campaign skills in parallel.

When a plan campaigns multiple skills in sequence against a shared live description state, selecting the best-validation-pass-rate iteration may change an earlier skill's description to a non-final (earlier) iteration. A later phase's campaign runs against the live state of all skills, including just-campaigned earlier skills — so a later phase's regression can route differently than the earlier phase's measurement assumed, and recorded pass rates no longer hold.

**Final-Verification regression smoke:** in the plan's Final Verification, re-run 1 eval of each campaigned skill's canonical should-trigger smoke query against the final pinned description state through the campaign workspace (~12 evals for a 12-skill plan). Report any cross-phase routing regression. This is cheap insurance against the assertion that file-disjoint edits can't cross-talk — true for *files* but not for *routing behavior* when the candidate description itself changed mid-campaign.

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Re-running `init` after losing `$WS` | `$WS` dies with each shell invocation. Record the literal path from init's output (Workflow step 4b) and paste it in every command; recover a lost path via `ls -d /tmp/trigger-test.*` — one workspace per campaign, always |
| Optimizing against the full eval set (no split) | Use train/validation split; select best iteration by validation pass rate |
| Pasting failed-query keywords into the description | Find the general category, not the specific query |
| Stopping at the last iteration | Compare validation pass rates across all iterations; pick the best |
| Treating a sibling skill firing as "any skill fired, pass" | The verdict is candidate-specific: sibling-only loads report `not-loaded` with `conflict: wrong-skill` |
| Forgetting the 1024-char ceiling mid-optimization | Re-check every iteration; descriptions grow |
| Revising the description but evaluating against the stale init-time stub | Re-sync after every revision: `trigger-test.sh sync --skill <candidate> --workspace WS_PATH` — without it the next iteration measures the previous description |
| Stripping skills via `XDG_CONFIG_HOME` for "clean" baselines | Wrong approach for trigger evals — keeps the candidate out. Trigger-eval baselines measure the candidate's routing rate against siblings |
| Skipping the smoke-test before running the full campaign | Run ONE should-trigger eval through `trigger-test.sh` and read its verdict block before running the full rep matrix |
| Running evals outside the isolated harness | Always run evals through `trigger-test.sh` — only it guarantees the stub-only workspace and the skill-only `trigger-evaluator` agent |
| Assuming a triggered skill can execute its workflow | Stubs are frontmatter-only — there is no body to execute. A missing or unparseable verdict block means the eval is void: fix the cause, re-dispatch fresh, never count it |
| Adding framing, skill names, or "this is a test" context to the scenario | Pass the bare eval query only, via `<<'EOF'` heredoc — anything more carries the runner's context into the eval and biases the routing measurement |
| Asking the user eval queries via the `question` tool | The user is never a rep. All queries go through `trigger-test.sh eval` into the isolated workspace; the runner authors them without user input. |
| Fixing false triggers by appending a longer "Do NOT use" list | Negations trail; boundaries lead (see the Frontmatter section in `SKILL.md`). Restructure the description so the exclusion is the opening condition — and if it still fails, suspect a body/label conflict, not a wording problem |
| Launching the full rep matrix as unbounded parallel jobs | Use `trigger-test.sh batch` at the default `--jobs 2`; unbounded fan-out saturates local models and every rep times out |
| Counting a timed-out rep as not-loaded | Check `timed_out:` in the verdict block; timeout without a load signal is void — retry serially, never count it |

## Results Log Format

Trigger eval logs use the campaign log format: title `# Test Campaign: <skill-name> — <date>`, with per-run bullets recording verdicts and verbatim evidence. Save trigger campaigns to `test-campaigns/YYYY-MM-DD-<skill-name>-trigger.md` in the target skill's own directory (where its SKILL.md resides) — the `-trigger` suffix distinguishes them from discipline pressure-test campaigns at `test-campaigns/YYYY-MM-DD-<skill-name>.md`. If a log for the same skill and suffix already exists for that date, insert a two-digit sequence number: `test-campaigns/YYYY-MM-DD-NN-<skill-name>-trigger.md`, incrementing NN per additional same-day campaign.

Two optional sections, appended in addition to or in place of `## Baseline` / `## With skill` when the campaign is trigger-focused:

```markdown
## Trigger evals

### Iteration 1
- Description (≤1024 chars): <paste verbatim>
- Description sha256 (first 12): <hash>
- Train pass rate: <N>/<M> queries
- Validation pass rate: <N>/<M> queries
- Train failures: <list queries+failure type>
- Revision rationale: <one paragraph>

### Iteration 2 — <…>

### Selected iteration: <N> (validation pass rate <X>)
```

Compute the hash at selection time with `sed -n 's/^description: //p' <target-skill-base>/SKILL.md | sha256sum | cut -c1-12` so later verification runs can detect post-campaign description drift.

And:

```markdown
## Fresh-query sanity check
- 5 queries never used in optimization:
  - <query>: <triggered candidate | sibling | not triggered> — pass | fail
- Pass rate: <N>/<M>
```

The campaign log is the ONLY place trigger status lives. Never add trigger status, verdicts, `test-campaigns/`, or `trigger-evals/` references to `SKILL.md` — `SKILL.md` is loaded into working context on every run, and status notes there bloat context and invite agents to read the logs.

### `trigger-evals/` directory convention

The `trigger-evals/` directory lives in the target skill's own directory (where its SKILL.md resides, beside `test-campaigns/`) and holds `train.json`, `validation.json`, and any post-selection `YYYY-MM-DD-fresh.json`. Files are JSON arrays of `{"query": "<str>", "should_trigger": <bool>}` objects. Committed to source control like `test-campaigns/` — `trigger-evals/` is NOT gitignored. Linked from the campaign index by filename; never referenced from `SKILL.md`. The first trigger campaign against a skill creates the directory.

## Boundary

The campaign ends when each target skill's trigger results log is written. Do not suggest, auto-invoke, or chain into any other skill; the user decides what happens next with the campaign results.
