# Phase 3b: Failure Evidence — Implementation Plan

Follow-up to phase 3 (artifact management). Origin: in the phase-3 live
validation, the driving agent categorized train failures from query text and
outcome patterns alone, grepping suite summary lines instead of reading the
per-failure `reasoning` that the suite JSON already captures. Three
countermeasures, approved by the user (2026-09-02): a deterministic extractor
subcommand, a prescriptive analysis procedure in SKILL.md, and auditable
evidence lines in the campaign report. This plan is decision-complete; the
implementing agent should not introduce new decisions.

**Scope:** `evaluator.py failures` subcommand + unit tests + SKILL.md
procedure/report/checklist edits. NOT in scope: storing reasoning for passing
or void runs in the suite JSON (failures-only remains the storage contract);
any change to `.log` capture (user confirmed logs are fine as-is);
pi/claude harness strategies.

**Line-number caveat.** Line numbers are as of the phase-3 live-validation
state (2026-09-02, post phase-3 implementation) and are paired with file
paths and section/heading names throughout. Per AGENTS.md, the path + heading
references are authoritative.

## Why this works (the three loopholes)

1. **Easiest-path loophole** → the extractor makes consulting reasoning
   strictly less work than skimming summaries, and guarantees completeness
   (no cherry-picked failures).
2. **Ambiguity loophole** → the workflow step becomes a procedure with a
   forbidden shortcut ("never categorize from query text alone").
3. **Audit loophole** → the report must quote the deciding phrase per failed
   run, so heuristic-only analysis is visible to human reviewers.

## Deliverables

- **Modified:** `skills/trigger-testing-skills/scripts/evaluator.py` — new
  `failures` subcommand.
- **Modified:** `skills/trigger-testing-skills/scripts/test_evaluator.py` —
  new `FailuresTests` class.
- **Modified:** `skills/trigger-testing-skills/SKILL.md` — workflow step 7c,
  "Failure analysis" section, "Report format" section, checklist.
- **Unchanged:** `workspace-manager.sh`, suite JSON schema, `.log` capture,
  manifest, `AGENTS.md`, `docs/README.md` (phase plans are not indexed there).

## Step 1 — `evaluator.py`: `failures` subcommand

File: `skills/trigger-testing-skills/scripts/evaluator.py`.

**1a. `cmd_failures`**, placed after `cmd_record`'s `return 0` (currently
line 766), before `main()` (currently line 769):

```python
def cmd_failures(args: argparse.Namespace) -> int:
    """Print every failed run (query, run number, detail, full reasoning)
    from a suite result JSON. Extraction only; analysis is the agent's job.
    Exit 0 even when failures exist — this is an extractor, not a gate."""
    path = Path(args.results)
    if not path.exists():
        print(f"error: results file not found: {path}", file=sys.stderr)
        return 1
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        print(f"error: invalid JSON in {path}: {e}", file=sys.stderr)
        return 1
    if not isinstance(data, dict) or not isinstance(data.get("queries"), list):
        print(f"error: {path}: not a suite result file (missing 'queries' "
              f"list)", file=sys.stderr)
        return 1
    n_failures = 0
    for q in data["queries"]:
        failures = q.get("failures") or []
        if not failures:
            continue
        expect = "trigger" if q.get("should_trigger") else "not-trigger"
        print(f'query: "{q.get("query")}"   expected: {expect}')
        for f in failures:
            n_failures += 1
            timeout = " (timeout)" if f.get("timeout") else ""
            print(f"  run {f.get('run')}: {f.get('outcome')}{timeout} — "
                  f"{f.get('detail', '')}")
            reasoning = f.get("reasoning") or "(no reasoning captured)"
            for line in reasoning.splitlines():
                print(f"    {line}")
        print()
    if n_failures == 0:
        print(f"no failed runs in {path}")
    return 0
```

Works on any suite result file (`iter-<i>-train.json`,
`validate-results.json`, `sanity-results.json`) — the schema is shared.
Full reasoning, never truncated; queries print in file order, runs in stored
order.

**1b. Argparse** in `main()`, after the `record` subparser block (currently
lines 805–811):

```python
    failures = sub.add_parser("failures")
    failures.add_argument("--results", required=True)
```

**1c. Dispatch** (currently lines 815–822): insert before
`return cmd_run(args)`:

```python
    if args.command == "failures":
        return cmd_failures(args)
```

## Step 2 — `test_evaluator.py`: `FailuresTests`

File: `skills/trigger-testing-skills/scripts/test_evaluator.py` (unittest;
run from the scripts dir).

**2a. Imports** (currently lines 9–15): add `contextlib` and `io` to the
stdlib import block (alphabetical: `contextlib` before `hashlib`, `io` before
`json`).

**2b. New `FailuresTests` class**, inserted after `RecordTests` (ends
currently line 209), before the `if __name__ == "__main__"` guard:

```python
class FailuresTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.results = Path(self.tmp.name) / "iter-1-train.json"

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, queries: list) -> None:
        self.results.write_text(json.dumps({"queries": queries}))

    def _run(self, path: Path | None = None) -> tuple[int, str]:
        args = argparse.Namespace(results=str(path or self.results))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = evaluator.cmd_failures(args)
        return rc, buf.getvalue()

    def _failure(self, run: int = 2, reasoning: str = "it looked\nrelevant"):
        return {"run": run, "outcome": "triggered",
                "detail": "skill tool completed load",
                "reasoning": reasoning, "timeout": False}

    def test_extracts_failed_runs_with_reasoning(self):
        # query + expectation header; run line with detail; reasoning lines
        # indented; rc == 0 (failures present is not an error)
    def test_query_without_failures_produces_no_block(self):
        # passing query absent from output entirely
    def test_no_failures_reports_none(self):
        # empty failures everywhere -> "no failed runs" line, rc == 0
    def test_missing_reasoning_marker(self):
        # reasoning == "" -> "(no reasoning captured)"
    def test_missing_file(self):
        # rc == 1
    def test_invalid_json(self):
        # write "not json"; rc == 1
    def test_missing_queries_key(self):
        # write {"totals": {}}; rc == 1
```

## Step 3 — `SKILL.md`: prescriptive analysis + evidence in the report

File: `skills/trigger-testing-skills/SKILL.md`. Edits in file order.

**3a. Workflow step 7c** (currently line 79). Replace:

```markdown
   c. Otherwise analyze failures (below), revise the description (guardrails below), and write the revision **to the workspace stub only**.
```

with:

```markdown
   c. Otherwise analyze failures (below): run `evaluator.py failures --results <campaign>/iter-<i>-train.json` and read every failed run's reasoning. Assign each failure a category only with a cited phrase from that run's reasoning — never from the query text or the outcome pattern alone. Then revise the description (guardrails below) and write the revision **to the workspace stub only**.
```

**3b. "Failure analysis" section** (currently starts line 90). Insert a new
paragraph immediately after the section heading, before the timeouts
paragraph:

```markdown
The evidence for every categorization is the failed runs' reasoning, extracted with `evaluator.py failures --results <suite json>` — never the bare query text or outcome counts. Cite the deciding phrase per failed run before assigning a category; a category without a citation is a guess, not an analysis.
```

**3c. "Report format" section** (currently starts line 112). In the example
block, add one evidence line under each `failure categories:` line:

```
iter 1: train score 0.593  (16 pass / 8 fail / 3 void)
        failure categories: mostly too-narrow (implicit asks); one local minimum
        failure evidence: "turn this outline into a skill" run 2 — "an outline
          isn't a request to build anything" -> too narrow
```

Annotate in the paragraph below the block (where `manifest:` line behavior is
described): one `failure evidence:` line per failed run, quoting the deciding
phrase (≤ 15 words) from that run's reasoning; iterations with zero failures
omit the line.

**3d. Checklist** (currently starts line 160). Add after the
"Each iteration's evaluated description saved to
<campaign>/iter-<i>-description.md" item:

```markdown
- [ ] Every failure category backed by a cited phrase from the run's reasoning (via `evaluator.py failures`)
```

## Verification (exact commands; no harness spend)

```bash
# 1. Unit tests (cwd must be the scripts dir for `import evaluator`)
cd /home/dave/source/dangerpowers/skills/trigger-testing-skills/scripts
python3 test_evaluator.py -v
```

```bash
# 2. Smoke against real phase-3 campaign data: iter-1 had 3 failures on the
#    near-miss query, with reasoning
cd /home/dave/source/dangerpowers
python3 skills/trigger-testing-skills/scripts/evaluator.py failures \
  --results skills-workspace/writing-skills/trigger-tests/campaign-2026-09-02/iter-1-train.json
# expect: one query block ("which skills will help me with writing?",
# expected: not-trigger), 3 run lines, reasoning under each
```

```bash
# 3. No-failures path: sanity passed 3/3
python3 skills/trigger-testing-skills/scripts/evaluator.py failures \
  --results skills-workspace/writing-skills/trigger-tests/campaign-2026-09-02/sanity-results.json
# expect: "no failed runs in ...", exit 0
```

```bash
# 4. Error paths
python3 skills/trigger-testing-skills/scripts/evaluator.py failures \
  --results /tmp/does-not-exist.json; echo "exit=$?"   # expect exit=1
python3 skills/trigger-testing-skills/scripts/evaluator.py failures \
  --results skills-workspace/writing-skills/trigger-tests/manifest.json
echo "exit=$?"   # expect exit=1 (valid JSON, no 'queries' list)
```

Live validation: none required; the subcommand is exercised naturally by the
next real campaign (step 7c now prescribes it).

## Assumptions register (flag any you want reversed before implementation)

1. `--results` flag rather than a positional arg, for consistency with the
   other subcommands' all-flags style.
2. Failures-only extraction: the suite JSON stores reasoning only inside
   `failures[]`; this plan does not extend storage to passes/voids.
3. Exit 0 when failures exist (extractor, not a gate); exit 1 only for
   missing file / invalid JSON / wrong shape.
4. Full untruncated reasoning in output (bounded in practice to ~1 KB per
   run; truncation would undermine the analysis the command exists for).
5. Evidence lines are per failed run with a ≤ 15-word quote; the report
   example shows one line, the annotation states the rule.
6. The prescriptive procedure attaches to the train loop (step 7c) only;
   validate/sanity failure reporting is unchanged.
7. No `AGENTS.md` or `docs/README.md` changes.
