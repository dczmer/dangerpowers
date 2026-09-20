# Harness Merge: Detailed Implementation Plan

Source analysis: `docs/writing-skills/part-3/deterministic-work-audit.md`
(findings 1–6 enumerated below). All line numbers verified against
`tools/test-harness/evaluator.py` (3,185 lines) at the time of writing.
Plan only — nothing applied.

**Findings map** (audit → phase):

| Finding | Audit says | Addressed by |
|---|---|---|
| 1 | Manifest diffing is deterministic set logic, done by hand | Phase 2 (`inventory-diff`) |
| 2 | `scored.json` derivations are deterministic conditional logic, LLM-authored | Phase 3.1 (`--emit-skeleton`) |
| 3 | Report count arithmetic LLM-counted, checked only "when given" | Phase 3.2 (`record --scored`) |
| 4 | Cost-formula arithmetic in proposal cards | Phase 4.2 — **rejected** (concur with audit's "or accept as residue") |
| 5 | Section-anchored id numbering is deterministic allocation | Phase 2 (`inventory-mint`) |
| 6 | Pattern-rule frequency EXCEED comparison | Phase 4.1 (`shape-evidence --compare`) |

## 0. Current state and merge map

Duplication inventory (verified line ranges):

```
evaluator.py
├── rep-batch skeleton (smoke rep → ThreadPoolExecutor batches → first_error → exit 1)
│     ├── run_records_batch        1146–1218   (retrieval)
│     ├── run_shape_rep_batch      1787–1856   (shape)      ~73 lines each,
│     └── run_pressure_rep_batch   2484–2553   (pressure)   skeleton ≈ 50 lines ×3
├── pre-spend agent gate (exists + frontmatter name + no pins)
│     ├── retrieval (looped ×2 agents)  1235–1251
│     ├── shape                          1876–1892
│     └── pressure                       2569–2585
├── contamination gate (one policy, 3 messages)
│     ├── retrieval  1256–1265  (ws-has-skill AND control-ws-lacks-skill)
│     ├── shape      1948–1953  (ws-lacks-skill)
│     └── pressure   2614–2619  (ws-lacks-skill)
├── results-file write (config block + entries)
│     ├── 1328–1346, 1996–2017, 2663–2678
├── evidence preamble (load JSON, validate entries/id, iterate, --entry filter)
│     ├── retrieval 910–955, shape 2040–2098, pressure 2690–2729
├── union-dedupe results merger
│     ├── shape    2152–2199  (with kind-consistency check)
│     └── pressure 2846–2879  (near-verbatim, no kind check)
└── counts gate ("when given", all-or-none, equals scored sums)
      ├── retrieval 1500–1522, shape 2299–2322, pressure 2955–2978
```

Target architecture after all phases:

```
                    ┌────────────────────────────────────────────┐
                    │              evaluator.py                   │
                    │                                             │
                    │  SHARED CORE (new section)                  │
                    │  validate_eval_agent()                      │
                    │  run_rep_batched()     write_results()      │
                    │  iter_evidence()       load_results_json()  │
                    │  union_results()       load_scored_json()   │
                    │  check_coverage()      counts_gate()        │
                    │  check_contamination()                      │
                    │  inventory_load/mint/diff  (Phase 2)        │
                    │  scored skeleton emitters  (Phase 3)        │
                    └───────┬──────────┬──────────┬─────────────┘
                            │          │          │
              ┌─────────────┘          │          └─────────────┐
        ┌─────▼─────┐          ┌───────▼──────┐         ┌───────▼──────┐
        │ retrieval │          │    shape     │         │   pressure   │
        │  policy:  │          │   policy:    │         │   policy:    │
        │ prompt/   │          │ arm bodies,  │         │ red/green    │
        │ signals,  │          │ markers,     │         │ prompts,     │
        │ 2 ws,     │          │ doc-drift    │         │ meta resume, │
        │ expect    │          │ gate, kinds  │         │ taxonomy     │
        └───────────┘          └──────────────┘         └──────────────┘
        (trigger track stays separate — principled asymmetry, untouched)
```

**Rule throughout: merge plumbing, never policy.** Arm vocabularies,
void-signal vocabularies, prompt construction, serialization order, and
verdict sets stay per-track.

**Verification policy (applies after every step in every phase).**
Every step, no exceptions:

- **Standard gate** — whole-project scope, run from the repo root. All
  Python in the project lives under `tools/test-harness/`, so these
  cover everything; the test suite is never scoped down to the files a
  step touched:

```bash
( cd tools/test-harness && uv run python -m unittest discover -p 'test_*.py' ) 2>&1 | tail -3
# ↑ must run from inside tools/test-harness: the hyphenated directory
#   name is not importable, so `discover -s tools/test-harness` from the
#   repo root fails with ImportError. Baseline: "Ran 315 tests ... OK".
uv run flake8 tools/test-harness
uv run ruff check tools/test-harness
uv run black --check tools/test-harness
uv run pyright tools/test-harness
```

- **Domain additions, whole-project scope, whenever that domain is
  touched:** any `.sh` → `shellcheck tools/test-harness/*.sh` and
  `bash -n <file>`; any mermaid diagram edited in a SKILL.md → validate
  with `mermaidx`.
- **Real-eval policy** — whenever a step is verified with an actual
  model run, always `--harness opencode --model llama.cpp/gemma-4-26B-A4B
  --timeout 300`, with pre-flight `uv run python tools/test-harness/evaluator.py check
  --harness opencode --model llama.cpp/gemma-4-26B-A4B`. Every artifact
  (workspaces, queries/entries/scenarios excerpts, results, scored.json,
  manifest copies) lives under a `mktemp -d` directory; **nothing is
  written under `skills-workspace/` or anywhere in the repo during
  verification** — committed artifacts are inputs, read-only.
- **Mini-campaign rule** — at the end of Phase 1 and at every later
  phase that changes eval or scoring behavior, run the mini pilot
  campaigns for the affected track(s) (exact commands in each phase's
  checklist), and finish with the full end-to-end verification (Phase 5).
  Keep them minimal but covering the changes since the last
  mini-campaign. Steps that change only pure file-processing (no harness
  interaction) verify with synthetic JSON round-trips instead of model
  spend.

---

## Phase 1 — Extract the plumbing (pure refactor, no behavior change)

Six helpers, all added to `evaluator.py` in a new clearly-marked section.
Keeping them in `evaluator.py` (not a new module) preserves the test
files' import surface and the single-file script model the skills document.

**Prerequisite (do this first):** extend the typing import at 26 —
`from typing import TextIO` becomes
`from typing import Callable, Iterator, TextIO` — the new signatures use
`Callable` (1.2, 1.5) and `Iterator` (1.4).

### Step 1.1 — `validate_eval_agent()`

**Replaces:** 1235–1251 (retrieval, looped over two agents), 1876–1892
(shape), 2569–2585 (pressure).

**New code** (insert after `_err` at 613–615):

```python
def validate_eval_agent(
    probe: EvalStrategy, agents_dir: Path, expected_name: str
) -> Path:
    """Pre-spend gate: the agent file exists, its frontmatter name
    matches, and it pins no model config. Any failure exits 1 with an
    exact message before any harness invocation."""
    agent_file = probe.agent_file(agents_dir, expected_name)
    if not agent_file.exists():
        _fail(f"evaluator agent file missing: {agent_file}")
    info = scan_agent_frontmatter(agent_file)  # exits on bad frontmatter
    if info["name"] != expected_name:
        _fail(
            f"agent file {agent_file}: frontmatter name "
            f"'{info['name']}' does not match expected '{expected_name}'"
        )
    if info["pins"]:
        _fail(
            f"agent file {agent_file} pins model config "
            f"({', '.join(info['pins'])}); eval agents must not pin "
            "model/variant/temperature/top_p — selection flows "
            "through --model/--variant only"
        )
    return agent_file
```

**Diff at call sites** — shape (1875–1892):

```diff
     probe = strategy_cls(timeout=args.timeout)
-    agent_file = probe.agent_file(agents_dir, SHAPE_EVALUATOR_AGENT)
-    ... (the ~15-line inline gate block deleted — it is verbatim the
-        helper body above)
+    validate_eval_agent(probe, agents_dir, SHAPE_EVALUATOR_AGENT)
```

Retrieval (1235–1251) becomes:

```python
    for base in (RETRIEVAL_EVALUATOR_AGENT, RETRIEVAL_CONTROL_AGENT):
        validate_eval_agent(probe, agents_dir, base)
```

⚠️ **Message-fidelity check:** the shape/pressure blocks wrap the
name-mismatch message as `...does not match expected '<name>'` across two
f-strings; retrieval uses one. The extracted helper produces
byte-identical output for all three (concatenation is equivalent), but
the tests pin exact stderr — run the suite immediately after this step
and diff any failure messages before proceeding.

**Verification checklist (1.1):**

1. Standard gate (315 tests, four lint/type commands).
2. One real eval exercising the refactored gate. The trigger `run`
   command installs `TRIGGER_AGENT` without this gate, so use a
   one-entry `shape-suite` — the lightest real path through
   `validate_eval_agent` (exact commands, all artifacts in a throwaway
   dir):

```bash
uv run python tools/test-harness/evaluator.py check \
  --harness opencode --model llama.cpp/gemma-4-26B-A4B   # pre-flight
TMP=$(mktemp -d)
python3 -c "import json; d=json.load(open('skills-workspace/shape-testing-skills/shape-tests/entries.json')); print(json.dumps(d[:1], indent=2))" \
  > "$TMP/entries.json"                                  # excerpt, repo untouched
mkdir -p "$TMP/ws"
uv run python tools/test-harness/evaluator.py shape-suite \
  --harness opencode --model llama.cpp/gemma-4-26B-A4B --timeout 300 \
  --skill shape-testing-skills --agents-dir agents \
  --workspace "$TMP/ws" --entries "$TMP/entries.json" \
  --skill-file skills/shape-testing-skills/SKILL.md \
  --arms v0 --out "$TMP/results.json" --reps 1
# expect: suite exits 0 and $TMP/results.json exists with 1 entry × v0
# × 1 rep recorded (write_results path exercised)
rm -rf "$TMP"
```

### Step 1.2 — `run_rep_batched()` (largest extraction, ~150 lines saved)

The three loops share this exact skeleton:

```
            run_rep_batched(run_one, reps, tag)
                      │
        ┌─────────────▼─────────────┐
        │ smoke rep: run_one(1)     │  HarnessExecutionError →
        │ alone, before any spend   │  exact stderr + sys.exit(1)
        └─────────────┬─────────────┘
                      │
        ┌─────────────▼─────────────┐
        │ reps 2..N in groups of    │  per group: ThreadPoolExecutor
        │ MAX_WORKERS (10)          │  collect first_error only
        └─────────────┬─────────────┘
                      │
              first_error set? ──yes──► exact stderr, "batch aborted",
                      │                  sys.exit(1)
                      no
        ┌─────────────▼─────────────┐
        │ return [runs[1..N]]       │
        └───────────────────────────┘
```

**New code** (replaces the shared skeleton at 1183–1218, 1822–1856,
2519–2553):

```python
def run_rep_batched(
    run_one: Callable[[int], dict], reps: int, tag: str
) -> list[dict]:
    """Smoke rep alone, then reps 2..N in parallel batches of at most
    MAX_WORKERS. A timeout is a record, never an abort; a
    HarnessExecutionError in the smoke rep or any batch aborts with an
    exact stderr message and exit 1. Shared by the retrieval, shape, and
    pressure tracks; the trigger track keeps its own loop."""
    runs: dict[int, dict] = {}

    try:
        runs[1] = run_one(1)
    except HarnessExecutionError as e:
        emit(
            f"error: [{tag}] harness could not execute the query: {e}"
            f"{_session_suffix(e)}",
            err=True,
        )
        sys.exit(1)

    remaining = list(range(2, reps + 1))
    for i in range(0, len(remaining), MAX_WORKERS):
        group = remaining[i : i + MAX_WORKERS]
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            futures = {pool.submit(run_one, n): n for n in group}
            first_error: tuple[int, HarnessExecutionError] | None = None
            for fut, n in futures.items():
                try:
                    runs[n] = fut.result()
                except HarnessExecutionError as e:
                    if first_error is None:
                        first_error = (n, e)
        if first_error is not None:
            n, e = first_error
            emit(
                f"error: [{tag}] rep {n} could not execute: {e}"
                f"{_session_suffix(e)}",
                err=True,
            )
            emit("error: batch aborted", err=True)
            sys.exit(1)

    return [runs[n] for n in range(1, reps + 1)]
```

**Diff** — `run_shape_rep_batch` (1787–1856) shrinks to a closure:

```diff
 def run_shape_rep_batch(
     strategy: EvalStrategy,
     prompt: str,
     arm: str,
     ws: Path,
     agent: str,
     args: argparse.Namespace,
 ) -> list[dict]:
-    """Reps for one (entry, arm) pair. ... (docstring kept, trimmed)"""
+    """Reps for one (entry, arm) pair. Every rep shares identical prompt
+    bytes; per-rep scheduling lives in run_rep_batched."""
     tag = f" {arm} "
-    runs: dict[int, dict] = {}

     def run_rep(n: int) -> dict:
         log_start(n, tag)
@@ (execute + build_shape_run_record + progress line, unchanged)
         emit(line)
         return record

-    # Smoke rep runs alone; ... (48 lines of batch skeleton deleted)
-    try:
-        runs[1] = run_rep(1)
-    except HarnessExecutionError as e:
-        ...
-    return [runs[n] for n in range(1, args.reps + 1)]
+    return run_rep_batched(run_rep, args.reps, tag)
```

Same transformation at 1146–1218 (retrieval: closure keeps
`stage_and_dispatch` + `skill=` kwarg) and 2484–2553 (pressure: closure
keeps the pre-built `prompt`).

⚠️ **Subtlety — retrieval's `SystemExit` propagation:**
`run_rep_batched` calls `sys.exit(1)` inside worker threads. Retrieval's
arm-parallel pool at 1302–1325 already catches `SystemExit` from
`run_records_batch` and propagates the code (1315–1318); that path is
preserved unchanged because the exit still surfaces through
`fut.result()` the same way. The test pinning this
(`test_retrieval.py` abort tests) must still pass.

**Verification checklist (1.2):**

1. Standard gate.
2. Minimal batch eval covering the refactored areas (`run_rep_batched`
   smoke-rep + batch loop, `write_results` envelope) via the trigger
   `suite` command with a two-query throwaway file:

```bash
TMP=$(mktemp -d)
cat > "$TMP/queries.json" <<'EOF'
[
  {"query": "<one known-trigger train query for any skill>",
   "shouldTrigger": true},
  {"query": "<one known not-trigger query>",
   "shouldTrigger": false}
]
EOF
WS=$(tools/test-harness/workspace-manager.sh init --prefix pilot-trigger)
tools/test-harness/workspace-manager.sh sync \
  --skill trigger-testing-skills --source skills/trigger-testing-skills \
  --workspace "$WS"
uv run python tools/test-harness/evaluator.py suite \
  --harness opencode --model llama.cpp/gemma-4-26B-A4B --timeout 300 \
  --skill trigger-testing-skills --agents-dir agents \
  --workspace "$WS" --queries "$TMP/queries.json" \
  --out "$TMP/results.json" --reps 2
uv run python tools/test-harness/evaluator.py failures \
  --results "$TMP/results.json"
# expect: exit 0; results.json has a config block (six shared keys) and
# per-query outcome records whose counts match the failures summary
tools/test-harness/workspace-manager.sh cleanup --workspace "$WS"
rm -rf "$TMP"
```

### Step 1.3 — `write_results()`

**Replaces:** 1328–1346, 1996–2017, 2676–2678.

```python
def write_results(out: Path, config: dict, entries: list[dict]) -> None:
    out.write_text(
        json.dumps({"config": config, "entries": entries}, indent=2) + "\n"
    )
```

Plus a `base_config(args) -> dict` returning the six shared keys
(`skill/harness/model/variant/reps/timeout/date`,
1331–1338 = 1999–2006 = 2663–2670 verbatim), which each call site then
extends with its track-specific keys (`queries` /
`entries, skill_file, arms, fixture_key` /
`scenarios, arm[, skill_file]`).

### Step 1.4 — Shared evidence preamble

**Replaces:** the load/validate/iterate prologues at 910–955, 2040–2083,
2690–2729 (~45 lines ×3).

```python
def load_results_json(path: Path, track: str) -> list[dict]:
    """Load a *-suite results file and validate the envelope: object with
    an 'entries' list, every entry an object with a non-empty string id.
    Prints exact errors and returns exit-1 via _err-compatible failure
    (raises SystemExit through _fail)."""
    ...

def iter_evidence(
    data_entries: list[dict], entry_filter: str | None
) -> Iterator[tuple[str, dict]]:
    """Yield (eid, entry) pairs honoring --entry, after envelope
    validation."""
```

Each `cmd_*_evidence` keeps only its printing body (retrieval's
rubric/sources block 957–992, shape's marker lines 2085–2132, pressure's
statement/pressures block 2731–2776).

⚠️ These commands use `print(..., file=sys.stderr); return 1` rather than
`_fail`/`sys.exit` — the helper must **return an error string or use the
same return-1 style**, not `_fail`, or exit-code tests break. Design it
to return `(entries, error)` or raise a private `EvidenceError` caught in
each cmd.

### Step 1.5 — Shared scored-check core

**Replaces:** union-dedupe loops 2152–2199 / 2846–2879; scored-envelope
loads 2201–2213 / 2881–2893 / 1398–1409; coverage checks 2292–2297 /
2948–2953 / 1493–1498; counts gates 1500–1522 / 2299–2322 / 2955–2978.

```python
def union_results(
    paths: list[str], track: str,
    entry_hook: Callable[[Path, dict, dict], None] | None = None,
) -> tuple[list[str], dict[str, set[str]], dict[str, dict]]:
    """Union with dedupe over repeated results files: an id appearing in
    N files is scored exactly once. Returns (ordered ids, id -> arm-key
    set, id -> hook-collected extras). entry_hook (e.g. shape's kind
    consistency check, 2185–2198) runs per first-seen entry."""

def load_scored_json(scored_path: Path) -> list[dict]: ...

def check_coverage(
    scored_entries: list[dict], results_ids: list[str], scored_path: Path
) -> list[dict]:
    """Exactly-once: rejects non-object entries, missing/duplicate/
    unknown ids; errors on union ids with no scored entry. Returns the
    validated scored entries for per-track field checks."""

def counts_gate(
    args: argparse.Namespace,
    scored_entries: list[dict],
    arg_names: tuple[str, ...],      # ("adopted", "no_failure", ...)
    result_names: tuple[str, ...],   # ("adopted", "no-failure", ...)
) -> int | None:
    """When the record-step counts are given: all-or-none, and equal to
    the scored sums. Returns _err(...) on violation, None when the gate
    passes or no counts were given."""
```

Shape's scored-check keeps its per-entry body (adopted_arm rules
2242–2265, restraint_gate 2267–2280) via an `entry_hook` that validates
`kind` and records `results_kinds`; pressure keeps verdict↔arm
implications 2917–2933. Retrieval (single `--results`, no arms) calls
`union_results` with one path and ignores the arm map.

**Per-track vs shared, after 1.5:**

```
union_results / load_scored_json / check_coverage / counts_gate   ← shared
  ├─ retrieval: result vocabulary, classification, control,
  │             ablation_flag derivation check, missed_bullets    ← per-track
  ├─ shape:     kind hook, adopted_arm rules, restraint_gate      ← per-track
  └─ pressure:  red/green arm implications, counters              ← per-track
```

**Verification checklist (1.3–1.5, combined):** these steps change only
pure file-processing (results/scored JSON handling), so they verify with
synthetic round-trips against **copies** of committed campaign artifacts
in a throwaway dir — no model spend. 1.3 and 1.2's mini eval already
exercised `write_results` on the write path; here the read/validate paths
are the subject.

1. Standard gate.
2. Evidence preambles (1.4) — positive and negative against a copy of a
   real results file:

```bash
TMP=$(mktemp -d)
C=skills-workspace/shape-testing-skills/shape-tests/campaign-2026-09-14
cp "$C/results-control.json" "$TMP/results.json"
uv run python tools/test-harness/evaluator.py shape-evidence \
  --results "$TMP/results.json"                      # expect exit 0
python3 -c "import json; d=json.load(open('$TMP/results.json')); d['entries'][0].pop('id'); json.dump(d, open('$TMP/broken.json','w'))"
uv run python tools/test-harness/evaluator.py shape-evidence \
  --results "$TMP/broken.json"                       # expect exit 1, exact envelope error
```

3. Scored core (1.5) — positive and negative against a real results +
   scored pair:

```bash
uv run python tools/test-harness/evaluator.py shape-scored-check \
  --results "$C/results-control.json" --results "$C/results-restraint.json" \
  --scored "$C/scored.json"                          # expect exit 0
uv run python tools/test-harness/evaluator.py shape-scored-check \
  --results "$TMP/results.json" \
  --scored "$C/scored.json"                          # expect exit 1: coverage
  # mismatch (scored.json lists union ids not in the single results file)
rm -rf "$TMP"
```

Repeat the negative/positive pair with `retrieval-evidence` /
`scored-check` (retrieval campaign `skills-workspace/shape-testing-skills/retrieval-tests/campaign-2026-09-15/`)
and `pressure-evidence` / `pressure-scored-check` (pressure campaign
`skills-workspace/shape-testing-skills/pressure-tests/campaign-2026-09-19/`)
so all three shared consumers are covered, not just shape's.

### Step 1.6 — Table-driven `load_entries()`

The three validators (`load_retrieval_queries` 1030–~1100,
`load_shape_entries` 1556–~1694, `load_pressure_scenarios` 2367–~2435)
share: file-exists → JSON parse → list-of-objects → unique non-empty
`id` → per-field checks. The full schema-table design — the contingent
stretch goal, **not** the committed scope (see the note after the block) —
would declare per-track schemas:

```python
ENTRY_SCHEMAS = {
    "retrieval": {
        "fields": {
            "query": {"type": str, "nonempty": True},
            "expect": {"type": list, "item_type": str},
        },
    },
    "shape": {
        "fields": {
            "kind": {"one_of": sorted(SHAPE_KINDS)},
            "section": {"type": str, "nonempty": True},
            "fixtures": {"custom": _validate_shape_fixtures},
            "markers": {"custom": _check_marker_tokens},
            ...
        },
    },
    "pressure": {
        "fields": {
            "statement": {"type": str, "nonempty": True},
            "pressures": {"one_of_items": sorted(PRESSURE_TYPES)},
            "scenario": {"type": str, "nonempty": True},
            "compliant_option": {"type": str, "nonempty": True},
        },
    },
}
```

**Default scope: extract only the envelope.** Implement
`load_entries()` as a shared envelope validator (file-exists → JSON parse
→ list-of-objects → unique non-empty `id`, with the exact
entry-index-and-id-qualified messages tests pin) and keep the three
per-track field validators as thin wrappers over it. That alone is ~40%
of the duplicated lines with ~0% of the risk, because the per-field
messages stay byte-identical by never moving.

The full schema table above is a **stretch goal, not the plan**: attempt
it only after the envelope version lands green, and adopt it only if
every per-field message reproduces byte-identically on the first try.
If any message drifts, stop and keep the envelope version — the marginal
lines saved do not justify debugging message fidelity across 315 pinned
tests.

### Step 1.7 — Consolidate shared-behavior tests (mandatory anti-drift step)

This step is the **load-bearing justification for Phase 1** — without it,
Phase 1 just relocates the drift, and the refactor is arguably net-negative
value against ~950 lines of stderr-pinned churn. It is a hard dependency
of Phase 1's done criteria, not an optional follow-up, and lands in the
same PR as 1.1–1.5 (see sequencing below). Create
`tools/test-harness/test_harness_common.py` and **move** (not copy) the
tests that pin shared behavior out of `test_retrieval.py` (952 lines),
`test_shape.py` (1,346), `test_pressure.py` (1,216):

- smoke-rep-abort and batch-abort cases (one per helper, not three)
- agent-gate message cases
- counts-gate all-or-none and mismatch cases (parameterized by track
  vocabulary)
- union-dedupe cases
- evidence-envelope error cases

Per-track files keep only policy tests (vocabularies, prompt bytes, arm
rules).

**Phase 1 done criteria:** PR 1 (1.1–1.5 + 1.7) green — 315 tests pass
(count grows only via the new common-test additions; **moved tests are
moved, not duplicated, and no existing case is dropped**), all four
lint/type commands clean, and:

```bash
git diff --stat   # expect ≈ -450/+250 lines in evaluator.py,
                  # new test_harness_common.py ~400 lines, per-track
                  # test files shrink correspondingly
```

PR 2 (1.6, envelope-only by default) then lands independently: tests
still 315+ with only envelope cases added.

**End-of-phase-1 mini pilot campaigns (all four tracks, real evals).**
After 1.6 + 1.7 land, run one minimal pilot per test type and verify
scoring end-to-end: per-entry tallies agree with the raw outcomes, a
driver-filled throwaway scored.json passes its `*-scored-check`, and the
same file with one counts flag deliberately wrong fails it. All commands
below; every artifact stays in `$TMP`, committed fixtures are read-only
inputs, and the standard gate has already run.

Common pre-flight (once):

```bash
uv run python tools/test-harness/evaluator.py check \
  --harness opencode --model llama.cpp/gemma-4-26B-A4B
TMP=$(mktemp -d)
```

**Trigger pilot** — outcome tally correctness:

```bash
cat > "$TMP/queries.json" <<'EOF'
[
  {"query": "<one known-trigger train query for trigger-testing-skills>",
   "shouldTrigger": true},
  {"query": "<one known not-trigger query>",
   "shouldTrigger": false}
]
EOF
WS=$(tools/test-harness/workspace-manager.sh init --prefix pilot-trigger)
tools/test-harness/workspace-manager.sh sync \
  --skill trigger-testing-skills --source skills/trigger-testing-skills \
  --workspace "$WS"
uv run python tools/test-harness/evaluator.py suite \
  --harness opencode --model llama.cpp/gemma-4-26B-A4B --timeout 300 \
  --skill trigger-testing-skills --agents-dir agents \
  --workspace "$WS" --queries "$TMP/queries.json" \
  --out "$TMP/trigger-results.json" --reps 2
uv run python tools/test-harness/evaluator.py failures \
  --results "$TMP/trigger-results.json"
# scoring verification: per-query pass/fail in the failures summary
# matches the recorded rep verdicts in trigger-results.json
tools/test-harness/workspace-manager.sh cleanup --workspace "$WS"
```

**Retrieval pilot** — evidence tallies + scored round-trip:

```bash
SWS="$TMP/ws-skill"; CWS="$TMP/ws-control"; mkdir -p "$SWS" "$CWS"
tools/test-harness/workspace-manager.sh sync --full \
  --skill retrieval-testing-skills --source skills/retrieval-testing-skills \
  --workspace "$SWS"
python3 -c "import json; d=json.load(open('skills-workspace/retrieval-testing-skills/retrieval-tests/queries.json')); print(json.dumps(d[:2] if isinstance(d, list) else d, indent=2))" \
  > "$TMP/queries.json"
uv run python tools/test-harness/evaluator.py retrieval-suite \
  --harness opencode --model llama.cpp/gemma-4-26B-A4B --timeout 300 \
  --skill retrieval-testing-skills --agents-dir agents \
  --skill-workspace "$SWS" --control-workspace "$CWS" \
  --queries "$TMP/queries.json" --out "$TMP/retrieval-results.json" --reps 1
uv run python tools/test-harness/evaluator.py retrieval-evidence \
  --results "$TMP/retrieval-results.json"
# write $TMP/scored.json: {"campaign": "pilot", "skill": "retrieval-testing-skills",
# "entries": [...]} — one entry per union id, judgment fields filled to
# match the evidence output (see retrieval SKILL.md's scored.json contract)
uv run python tools/test-harness/evaluator.py scored-check \
  --results "$TMP/retrieval-results.json" --scored "$TMP/scored.json"   # expect exit 0
uv run python tools/test-harness/evaluator.py scored-check \
  --results "$TMP/retrieval-results.json" --scored "$TMP/scored.json" \
  --passes 99                                                            # expect exit 1: counts gate
```

**Shape pilot** — evidence tallies + scored round-trip:

```bash
python3 -c "import json; d=json.load(open('skills-workspace/shape-testing-skills/shape-tests/entries.json')); print(json.dumps(d[:2], indent=2))" \
  > "$TMP/entries.json"
mkdir -p "$TMP/ws-shape"
uv run python tools/test-harness/evaluator.py shape-suite \
  --harness opencode --model llama.cpp/gemma-4-26B-A4B --timeout 300 \
  --skill shape-testing-skills --agents-dir agents \
  --workspace "$TMP/ws-shape" --entries "$TMP/entries.json" \
  --skill-file skills/shape-testing-skills/SKILL.md \
  --arms v0:v1 --out "$TMP/shape-results.json" --reps 1
uv run python tools/test-harness/evaluator.py shape-evidence \
  --results "$TMP/shape-results.json"
# write $TMP/scored.json: {"entries": [...]} with one entry per union id
# (entry ids, NOT rule ids — see the envelope note in 3.1), judgment
# fields filled to match evidence
uv run python tools/test-harness/evaluator.py shape-scored-check \
  --results "$TMP/shape-results.json" --scored "$TMP/scored.json"       # expect exit 0
uv run python tools/test-harness/evaluator.py shape-scored-check \
  --results "$TMP/shape-results.json" --scored "$TMP/scored.json" \
  --voids 99                                                             # expect exit 1: counts gate
```

**Pressure pilot** — evidence tallies + scored round-trip:

```bash
python3 -c "import json; d=json.load(open('skills-workspace/shape-testing-skills/pressure-tests/scenarios.json')); print(json.dumps(d[:2], indent=2))" \
  > "$TMP/scenarios.json"
mkdir -p "$TMP/ws-pressure"
uv run python tools/test-harness/evaluator.py pressure-suite \
  --harness opencode --model llama.cpp/gemma-4-26B-A4B --timeout 300 \
  --skill pressure-testing-skills --agents-dir agents \
  --workspace "$TMP/ws-pressure" --scenarios "$TMP/scenarios.json" \
  --arm v0 --skill-file skills/pressure-testing-skills/SKILL.md \
  --out "$TMP/pressure-results.json" --reps 1
uv run python tools/test-harness/evaluator.py pressure-evidence \
  --results "$TMP/pressure-results.json"
# write $TMP/scored.json: {"campaign": ..., "skill": ..., "entries": [...]}
# with judgment fields + counters filled to match evidence
uv run python tools/test-harness/evaluator.py pressure-scored-check \
  --results "$TMP/pressure-results.json" --scored "$TMP/scored.json"    # expect exit 0
uv run python tools/test-harness/evaluator.py pressure-scored-check \
  --results "$TMP/pressure-results.json" --scored "$TMP/scored.json" \
  --bulletproof 99                                                       # expect exit 1: counts gate
rm -rf "$TMP"
```

Exit-code discipline: each `expect exit 1` line is part of the
checklist — a check that wrongly passes the negative case is itself a
failure.

---

## Phase 2 — The `inventory` command (implements findings 1 + 5)

Highest-value **new** code: one implementation serving all three
multi-rule tracks. `rules.json` and `facts.json` are the same file modulo
array name and id prefix:

```
rules.json (pressure/shape)                facts.json (retrieval)
{                                          {
  "skill": ...,  "generated": ...,           "skill": ...,  "generated": ...,
  "rules": [ {id, section, kind,             "facts": [ {id, section,
              statement, entries} ],                    statement, entries} ],
  "excluded": [ {id, section, kind,          "excluded": [ {id, section,
                 reason} ]                              reason} ]
}                                          }
   id: R-<section-slug>-<nn>                  id: F-<section-slug>-<nn>
```

### New code in `evaluator.py`

```python
# --------------------------------------------------------------------------
# Inventory tooling: rules.json / facts.json validation, id minting, diff

INVENTORY_KINDS = {"rule": "R", "fact": "F"}

def _section_slug(section: str) -> str:
    """'## When to use' -> 'when-to-use'; lowercase, non-alnum runs -> '-',
    stripped. Deterministic and stable across regenerations."""

def mint_inventory_id(kind_prefix: str, section: str, n: int) -> str:
    return f"{kind_prefix}-{_section_slug(section)}-{n:02d}"

def load_inventory(path: Path, kind: str) -> dict:
    """Validate the unified schema (header, item array named by kind,
    excluded-with-reason), exact messages, exit 1 on violation."""

def inventory_diff(old: dict, new: dict) -> dict:
    """Set logic over ids:
      new:       in new, not in old
      changed:   in both, statement/entries/kind differ
      deleted:   in old, not in new (and not in old.excluded)
      excluded:  new.excluded, annotated 'still-excluded' | 'newly-excluded'
                 | 'resurrected' (was excluded, back in items)
    Pure function; no I/O."""

def cmd_inventory_check(args) -> int: ...   # validate + report id stats
def cmd_inventory_mint(args) -> int: ...    # assign ids to an id-less draft
def cmd_inventory_diff(args) -> int: ...    # print diff JSON to --out/stdout
```

Id minting is **document-order per section**: items are grouped by
`section` in file order, numbered `01..` within each section. Stability
rule (documented in the command's help and later in the SKILL.md edits):
re-running `inventory-mint` on an unchanged file is a byte-identical
no-op — this is what makes `inventory-diff` silent-mis-diff-proof.

### Argparse wiring (insert into `main()` after the `pressure_scored` block, 3148)

```python
    inv = sub.add_parser("inventory-check")
    inv.add_argument("--inventory", required=True)
    inv.add_argument("--kind", required=True, choices=["rule", "fact"])

    mint = sub.add_parser("inventory-mint")
    mint.add_argument("--inventory", required=True)
    mint.add_argument("--kind", required=True, choices=["rule", "fact"])
    mint.add_argument("--out", required=True)

    idiff = sub.add_parser("inventory-diff")
    idiff.add_argument("--old", required=True)
    idiff.add_argument("--new", required=True)
    idiff.add_argument("--kind", required=True, choices=["rule", "fact"])
    idiff.add_argument("--out")
```

Dispatch arms added to the if-chain at 3150–3181.

### Behavior diagram

```
 old rules.json ──┐
                  ├─► inventory-diff ──► { new: [...], changed: [...],
 new rules.json ──┘        │              deleted: [...], excluded: [...] }
                          │                     │
                          │              driver edits skill body,
                          │              regenerates inventory,
                          │              diff confirms only intended rules
                          ▼              changed
                   exit 1 + exact message on:
                   schema violation, duplicate id,
                   id/section mismatch (slug drift),
                   "changed" item whose id does not exist in old
```

### Tests (`test_harness_common.py` or new `test_inventory.py`)

- schema acceptance for both `rule` and `fact` shapes, and rejection
  cases with exact messages
- mint: id format `R-when-to-use-03`; re-mint idempotence
  (byte-identical)
- diff: each of the four buckets; resurrect case; deleted-vs-excluded
  distinction
- slug edge cases: punctuation, repeated sections (two items in one
  section number independently)

**Phase 2 done criteria:**

1. Standard gate (315 + new inventory tests, four lint/type commands).
2. The inventory commands never touch eval paths, so no model spend —
   verify against **copies** of the three committed inventories in a
   throwaway dir (a no-op diff on unmodified copies is the
   silent-mis-diff-proof test):

```bash
TMP=$(mktemp -d)
for inv in \
  "skills-workspace/shape-testing-skills/shape-tests/rules.json rule" \
  "skills-workspace/shape-testing-skills/pressure-tests/campaign-2026-09-19/rules.json rule" \
  "skills-workspace/shape-testing-skills/retrieval-tests/campaign-2026-09-15/facts.json fact"; do
  set -- $inv
  cp "$1" "$TMP/$(basename "$1")"
  uv run python tools/test-harness/evaluator.py inventory-check \
    --inventory "$TMP/$(basename "$1")" --kind "$2"     # expect exit 0
  uv run python tools/test-harness/evaluator.py inventory-mint \
    --inventory "$TMP/$(basename "$1")" --kind "$2" --out "$TMP/minted.json"
  uv run python tools/test-harness/evaluator.py inventory-mint \
    --inventory "$TMP/minted.json" --kind "$2" --out "$TMP/minted2.json"
  cmp "$TMP/minted.json" "$TMP/minted2.json"   # re-mint idempotence: byte-identical
  uv run python tools/test-harness/evaluator.py inventory-diff \
    --old "$TMP/$(basename "$1")" --new "$TMP/minted.json" --kind "$2" \
    --out "$TMP/diff.json"
  python3 -c "import json; d=json.load(open('$TMP/diff.json')); assert not any(d[k] for k in ('new','changed','deleted','excluded')), d; print('diff empty: ok')"
done
```

3. Negative cases (expect exit 1, exact messages): a schema-broken
   copy (delete the header), a duplicate-id copy, and a `changed` item
   whose id does not exist in `--old`.

4. One synthetic edit round-trip: copy `rules.json`, change one
   statement, and confirm `inventory-diff` reports exactly one
   `changed` item — the diff buckets fire on real content, not just on
   structure.

**Same-PR doc edit (finding 1 is only half-fixed otherwise):** the three
SKILL.md files each describe the hand-diff workflow this command replaces
(pressure lines 114–116, shape lines 99–101, retrieval lines 71–76 per
the audit). Update those steps in the same PR to say: mint/refresh ids
with `inventory-mint`, then read `inventory-diff` JSON and make the
proposals — the LLM proposes, the script diffs. Landing the commands but
leaving the docs describing hand-diffing recreates exactly the
script/doc drift Phase 3 guards against.

Scope split verified against the docs: the `rules.json`/`facts.json`
**JSON examples stay** (the file format is unchanged — only id minting
moves to the script); what gets replaced is the id-anchoring **prose**:
retrieval line 221 and shape lines 126–127 teach section-anchored id
numbering as LLM work, and retrieval line 36 / pressure lines 168+201
say "regenerate the manifest" as if the LLM renumbers. Those sentences
become "draft the inventory id-less (ids are minted by
`inventory-mint`), then regenerate via the script".

---

## Phase 3 — Push derivation upstream (findings 2 + 3; touches SKILL.md text)

This phase changes scripts **and** four skill documents (retrieval,
shape, pressure, trigger), so it lands as one coordinated pass.

### Step 3.1 — Skeleton emission on the scored-checks

Each `*-scored-check` gains `--emit-skeleton PATH`: instead of validating
an existing scored.json, it **writes** one derived from the results
union, then exits 0.

What is mechanically derivable from results alone (verified against the
builders):

| Field | Derivable? | Source |
|---|---|---|
| entry ids, coverage order | yes | `union_results` |
| retrieval `expect` rubric echo | in-memory only | results entries carry `expect` (1296), but **no scored.json field holds an echo** (verified against the real artifact: entry keys are `id/result/missed_bullets/classification/control/ablation_flag/notes`). The skeleton may load `expect` as context for the driver's judging aid; it must **not** be written into the file |
| shape `kind`, `marker_counts` per arm | yes | results carry `kind`/`markers`; counts via `marker_triage_counts` (2022) |
| pressure arm presence per entry | yes | `results_arms` union |
| pressure verdict **constraints** | partly | red+no-green ⇒ `no-failure`∨`void`; red+green ⇒ `bulletproof`∨`unresolved` — emit as a `"verdict_constraint"` hint, not a value |
| retrieval `control`, `ablation_flag` | **no** | `control` is driver judgment; `ablation_flag` derives from it. Skeleton emits `control: null` and `ablation_flag: null`; the existing check (1458) already enforces consistency once filled |
| classification, notes, counters, adopted_arm choice, verdicts | no | judgment — emitted as `null` |

```python
def emit_scored_skeleton(
    track: str,
    results_ids: list[str],
    extras: dict[str, dict],   # from union_results entry_hook
    out_path: Path,
) -> None:
    """Write the scored.json skeleton: every union id exactly once, all
    mechanically derivable fields pre-filled, judgment fields null."""
```

Judgment-field `null`s are rejected by the existing per-track validators,
so a skeleton **cannot** be accidentally checked in uncompleted — the
check that already exists becomes the "you forgot to judge" gate for free.

**Envelope shapes the emitters must target** (verified against
`evaluator.py` and real artifacts): all three scored files are JSON
**objects with an `entries` list** — retrieval and pressure also carry
`campaign`/`skill` headers; shape is `{"entries": [...]}` with no
header. ⚠️ The shape SKILL.md's current example (407–412) is **wrong on
both counts**: it shows a bare top-level array and uses rule ids
(`R-styling-01`) where entry ids belong (`proposal-cards-fixed-layout`);
as written it would fail `shape-scored-check` as `unknown id`. The 3.4
doc pass fixes the example; the skeleton emitters must emit the object
envelope, never the array.

**Verification checklist (3.1):**

1. Standard gate + new skeleton tests.
2. Skeleton round-trip on committed results (no model spend — the
   results already exist; this covers changes since the end-of-phase-1
   shape pilot):

```bash
TMP=$(mktemp -d)
C=skills-workspace/shape-testing-skills/shape-tests/campaign-2026-09-14
uv run python tools/test-harness/evaluator.py shape-scored-check \
  --results "$C/results-control.json" \
  --emit-skeleton "$TMP/scored.json"      # writes skeleton, exits 0
python3 -c "import json; d=json.load(open('$TMP/scored.json')); assert isinstance(d, dict) and isinstance(d.get('entries'), list); assert all(e['result'] is None for e in d['entries']); print('envelope + null judgment fields: ok')"
uv run python tools/test-harness/evaluator.py shape-scored-check \
  --results "$C/results-control.json" --scored "$TMP/scored.json"
# expect exit 1: null judgment fields rejected — the you-forgot-to-
# judge gate must fire on an unmodified skeleton
```

3. Repeat the round-trip for `scored-check` (retrieval results) and
   `pressure-scored-check` (pressure results) so all three emitters are
   covered, then a real eval spot-check: re-run the **shape mini pilot**
   (end-of-phase-1 commands) but source scored.json from
   `--emit-skeleton` + fill instead of writing it from scratch — the
   documented 3.4 workflow end-to-end.

### Step 3.2 — Unconditional counts: `record` reads scored.json

Today the LLM types four numbers twice (scored.json, then
`--passes/--fails/...`) and the optional gate catches mismatches. Invert
it:

**Diff in `cmd_record`** (dir branch, 698–808) and argparse (3026–3051):

```diff
     record.add_argument("--score", type=float)
+    record.add_argument(
+        "--scored",
+        help="scored.json to take the track counts from (replaces the "
+        "counts flags with --scope dir)",
+    )
     record.add_argument("--passes", type=int)
     ...
```

```python
    else:  # dir
        if args.scored is not None:
            if _any_counts_given(args):
                return _err("counts flags are replaced by --scored")
            track, sums = sums_from_scored(Path(args.scored))
            # sums_from_scored: load + validate via load_scored_json,
            # count result values, map the result vocabulary to the
            # manifest key vocabulary for the detected track
            entry = {
                "date": ...,
                "checksum": hash_skill_dir(skill_path),
                **sums,
            }
            key = track
        else:
            # legacy argv path retained one release for back-compat,
            # emitting a deprecation note on stderr
```

`--track` handling (three pinned decisions):

- **Argparse default changes** from `"retrieval-test"` to `None` so an
  explicit flag is distinguishable from the default. Legacy path with no
  `--track` keeps today's behavior (retrieval).
- **Track detection from the scored file**, required when `--scored` is
  given. Vocabulary alone is *not* sufficient — shape and pressure share
  `no-failure`/`unresolved`/`void`, so an all-void campaign is
  ambiguous. Detection rule: any entry with `result == "bulletproof"`
  (or a red/green arm reference) ⇒ pressure; any entry with
  `result == "adopted"` (or `adopted_arm`/`restraint_gate` keys) ⇒
  shape; neither provable ⇒ **error out asking for explicit `--track`**,
  never guess. Retrieval is distinguishable by `classification`/
  `control`/`ablation_flag` keys.
- **Explicit `--track` is checked consistent** with the detection and
  errors on mismatch. `--track` stays accepted on the legacy path
  unchanged for one release, then removal is a separate decision.

`--ablations` is a **free-text field, not a count** (argparse 3049 has
no `type=int`; stored verbatim at 806–807). It is untouched by
`sums_from_scored`: accepted as-is on both the legacy and `--scored`
paths, independent of the four sums. Do not try to derive it.

The counts gates in the three scored-checks keep working for the legacy
path but the SKILL.md documents stop mentioning counts flags entirely —
the "gates record" language becomes unconditional **by construction**
because the numbers now have exactly one source.

**Verification checklist (3.2):**

1. Standard gate + new `record --scored` / track-detection tests.
2. Record against a **copy** of a real manifest (the committed manifest
   is never the target of verification runs):

```bash
TMP=$(mktemp -d)
cp skills-workspace/shape-testing-skills/manifest.json "$TMP/manifest.json"
# $TMP/scored.json: a filled throwaway scored.json (from the 3.1 spot-check)
uv run python tools/test-harness/evaluator.py record \
  --skill shape-testing-skills \
  --skill-path skills/shape-testing-skills \
  --manifest "$TMP/manifest.json" \
  --scope dir --scored "$TMP/scored.json" \
  --campaign pilot --date 2026-01-01
# expect: exit 0; the new entry's counts equal the scored.json sums;
# no counts flags were typed
python3 -c "import json; e=json.load(open('$TMP/manifest.json'))['shape-test']; print(e['adopted'], e['no-failure'], e['unresolved'], e['voids'])"
# negative: legacy counts flags + --scored together -> exit 1;
# legacy counts flags alone -> exit 0 with a stderr deprecation note
```

3. Track-detection negatives: an all-void scored.json with no
   track-discriminating keys must error asking for `--track`, never
   guess; explicit `--track` inconsistent with detection errors.

### Step 3.3 — Trigger score-selection: `--score-from`

Encode the SKILL.md line-82 rule ("validate score; the winner's train
score when no validate set exists") once:

```python
    record.add_argument(
        "--score-from",
        help="train/validate results JSON to compute the trigger score "
        "from (Wilson bound over the recorded outcomes)",
    )
```

```python
    if args.score_from is not None:
        if args.score is not None:
            return _err("--score is replaced by --score-from")
        args.score = score_from_results(Path(args.score_from))  # reuses
        # _score_counts (429) over the results file's outcomes
```

Placement: before the scope branches in `cmd_record`, so the computed
score flows into the `--scope frontmatter` path (trigger records — the
dir branch's "`--score` is only valid with `--scope dir`" check must
see an already-computed `args.score`, not the raw flag).

**What moves to the script vs what stays with the driver:** the Wilson
bound computation moves into `score_from_results`; the *choice of which
results file to pass* stays a documented driver decision — the trigger
SKILL.md rule is "validate score when the validate pass ran, else the
winner iteration's train score", i.e. the driver passes
`validate-results.json` when a validate split exists and
`iter-<winner>-train.json` otherwise. So 3.4 below keeps **one prose
line** for file selection in the trigger SKILL.md; only the
score-computation fallback prose moves to the command's help text.

**Verification checklist (3.3):**

1. Standard gate + new `--score-from` tests.
2. Trigger mini campaign (real eval — this is the affected track's
   mini-campaign for the phase), then record with `--score-from` against
   a manifest copy:

```bash
# reuse the end-of-phase-1 trigger pilot commands to produce
# $TMP/trigger-results.json (two queries, --reps 2)
cp skills-workspace/trigger-testing-skills/manifest.json "$TMP/manifest.json"
uv run python tools/test-harness/evaluator.py record \
  --skill trigger-testing-skills \
  --skill-path skills/trigger-testing-skills \
  --manifest "$TMP/manifest.json" \
  --scope dir --score-from "$TMP/trigger-results.json" \
  --campaign pilot --date 2026-01-01
# expect: exit 0; the manifest score equals the Wilson bound over the
# recorded outcomes; passing --score alongside --score-from -> exit 1
```

3. File-selection rule: point `--score-from` at a validate-less results
   file per the documented fallback (winner's train JSON) and confirm
   the record succeeds — the script computes, the driver chooses.

### Step 3.4 — SKILL.md edits (same pass)

In `skills/retrieval-testing-skills/SKILL.md`,
`skills/shape-testing-skills/SKILL.md`,
`skills/pressure-testing-skills/SKILL.md`:

- replace the "author scored.json by hand, then check" steps with "run
  `*-scored-check --emit-skeleton`, fill the null judgment fields, then
  check"
- **fix the shape scored.json example** (407–412): bare array →
  `{"entries": [...]}` object, and rule ids (`R-styling-01`) → entry
  ids — it is wrong today (B-findings from the wiring audit; verified
  against the check at 2204–2213 and the real artifact)
- **replace pressure line 336** ("The harness writes the file" — wrong
  today, half-wrong after this phase): the accurate sentence is "the
  harness emits the skeleton; the driver fills the judgment fields
  (result, counters, notes)"
- delete counts-flag language — scope is wider than the record steps:
  the scored-check sections (retrieval 180–181, shape 240, pressure
  339), the quick references (shape 71–72, pressure 67–68), and the
  checklists (retrieval 286, shape 454, pressure 609) all carry
  counts/`--track` wording that becomes meaningless; record now takes
  `--scored $CAMP/scored.json`, with `--track` optional/auto-detected
- delete "when given" phrasing around the counts gate (gate is now
  structurally unreachable on the documented path)

In `skills/trigger-testing-skills/SKILL.md`: `--score <validate score;
the winner's train score when no validate set exists>` →
`--score-from <results JSON>` in the record step, **keeping one prose
line for file selection** (validate-results.json when the validate pass
ran, else the winner iteration's train JSON — per 3.3 above); the
Wilson-computation prose moves to the command's help text.

**Phase 3 done criteria:** 315+ tests plus new
skeleton/`--scored`/`--score-from` tests; the 3.1–3.3 verification
checklists all green (including the negative cases); the four skill docs
and the script agree — run each command the four SKILL.md files now
document against its `--help` output and confirm the flags exist as
written:

```bash
for c in run suite retrieval-suite scored-check shape-suite \
         shape-evidence shape-scored-check pressure-suite \
         pressure-evidence pressure-scored-check record; do
  uv run python tools/test-harness/evaluator.py "$c" --help | head -3
done
```

plus `mermaidx` validation if any SKILL.md mermaid diagram was edited in
the pass.

---

## Phase 4 — The small ones (findings 4 + 6)

### Step 4.1 — `shape-evidence --compare`

All inputs already exist in `cmd_shape_evidence` (2121–2131 computes
per-rep counts per arm). Add the comparison the adoption rule hinges on —
winner's marker frequency must **strictly exceed** control's:

**Diff** in `cmd_shape_evidence` (after the per-arm run loop, ~2132):

```diff
+        if args.compare:
+            base = aggregate_counts(arms.get("v0"), markers)
+            for arm in arms:
+                if arm == "v0" or arm.startswith("v0-"):
+                    continue   # control re-runs (e.g. v0-rerun) are
+                               # control evidence, not candidates
+                cand = aggregate_counts(arms[arm], markers)
+                for name in markers:
+                    b, c = base.get(name, 0), cand.get(name, 0)
+                    verdict = "EXCEEDS" if c > b else "does-not-exceed"
+                    print(f"compare {name}: {arm} {c} vs v0 {b} -> {verdict}")
```

where `aggregate_counts` sums `marker_triage_counts` over the arm's runs
and normalizes per-rep (frequency = matching lines / answer lines, per
the adoption rule's definition — confirm the exact denominator against
`skills/shape-testing-skills/SKILL.md` before implementing; the strict
`>` on the normalized value is the load-bearing part). Argparse:
`shape_evidence.add_argument("--compare", action="store_true")` after
3102.

**Re-run arm keys:** real shape results can carry control re-run arms
keyed like `v0-rerun` (a disclosed mid-campaign re-run of the control;
see the shape SKILL.md gotcha at 435–438 and the real artifact
`skills-workspace/shape-testing-skills/shape-tests/campaign-2026-09-14/scored.json`).
The candidate loop must skip these — only keys that are **not** the
control and **not** a control re-run suffix participate in the
comparison; a `v0-rerun` arm is control evidence, not a variant
candidate. Same filter applies when `union_results`' arm map feeds
per-arm reporting.

**Same-PR doc edit (atomic with the code, as in Phase 3):** update the
`shape-evidence` command line and the evidence-reading/adoption step in
`skills/shape-testing-skills/SKILL.md` to mention `--compare` and to say
the driver reads the script-emitted EXCEEDS/does-not-exceed comparison
rather than hand-comparing frequencies (audit finding 6: a strict-`>`
tie boundary decided by LLM arithmetic is a coin flip). Without this
edit the command and the documented workflow drift — the same
script/doc-drift failure mode Phase 3's risk register calls out.

**Verification checklist (4.1):**

1. Standard gate + new `--compare` tests.
2. Synthetic re-run-key check (no model spend — the committed campaign
   contains a control re-run results file):

```bash
TMP=$(mktemp -d)
C=skills-workspace/shape-testing-skills/shape-tests/campaign-2026-09-14
uv run python tools/test-harness/evaluator.py shape-evidence \
  --results "$C/results-control-rerun.json" --compare \
  > "$TMP/compare.txt" 2>/dev/null
# expect: exit 0; ZERO 'compare' lines — every arm in the file is
# v0/v0-rerun (control family) and no candidate comparison fires
grep -c '^compare ' "$TMP/compare.txt" || echo "0 compare lines: ok"
```

3. Real-eval spot-check: re-run the **shape mini pilot** with
   `--arms v0:v1` and confirm `--compare` prints per-marker
   EXCEEDS/does-not-exceed verdicts whose strict-`>` boundary the driver
   would otherwise have to compute by hand.

### Step 4.2 — Cost helper: **recommend skip** (concur with the original analysis)

Shape's cost (`3×(5+15) + (5+15+10) = 90`) is fully determined by
`entries.json`, but pressure's is contingent on mid-campaign observation.
A helper would restate a two-term multiplication at confirmation time
without removing judgment. If desired later, a shape-only
`shape-cost --entries E --reps N` is ~15 lines — but it is not worth a
code path now.

**Phase 4 done criteria:** standard gate green; 4.1 checklist complete
(synthetic re-run-key negative + shape mini pilot spot-check); the
`--compare` flag appears in `shape-evidence --help` exactly as the
SKILL.md documents it.

---

## Phase 5 — Final end-to-end verification (no code changes)

Run once after Phase 4, before considering the plan complete. Real evals
per policy; **every artifact under `$TMP`**; committed fixtures and
manifests are read-only inputs. Target skill:
**trigger-testing-skills** — the smallest library skill by inventory
(5 shape entries, 10 pressure rules/scenarios, 17 retrieval queries;
vs 8/16/58 for shape-testing-skills), which minimizes full-campaign
spend while exercising every track and every phase's change. Roughly
85–90 headless runs total; expect hours, not minutes, on a local
endpoint. If anything fails, do not merge — that phase's own checklist
is the debugging entry point.

### 5.1 Full gate and fixture staging

```bash
( cd tools/test-harness && uv run python -m unittest discover -p 'test_*.py' ) 2>&1 | tail -3
uv run flake8 tools/test-harness
uv run ruff check tools/test-harness
uv run black --check tools/test-harness
uv run pyright tools/test-harness
shellcheck tools/test-harness/*.sh
uv run python tools/test-harness/evaluator.py check \
  --harness opencode --model llama.cpp/gemma-4-26B-A4B   # pre-flight

TMP=$(mktemp -d)
T=trigger-testing-skills
SW=skills-workspace/$T
cp "$SW/retrieval-tests/queries.json" "$TMP/queries.json"
cp "$SW/retrieval-tests/facts.json"  "$TMP/facts.json"
cp "$SW/shape-tests/entries.json"    "$TMP/entries.json"
cp "$SW/pressure-tests/scenarios.json" "$TMP/scenarios.json"
cp "$SW/pressure-tests/rules.json"   "$TMP/rules.json"
cp "$SW/manifest.json"               "$TMP/manifest.json"
```

### 5.2 Full campaigns, all four tracks (real evals, reps minimal)

Reps are repetition, not scope: the full item pools run at `--reps 1`,
except one shape invocation at `--reps 2` to exercise the smoke-rep +
batch path of the shared `run_rep_batched` (1.2) in a real run.

**Trigger** — trigger-testing-skills has no committed trigger pool, so
the pool is authored in `$TMP` (the track's unit is the query, not the
rule; six hand-written labels are the minimal honest pool):

```bash
cat > "$TMP/trigger-queries.json" <<'EOF'
[
  {"query": "Run a trigger test campaign and tune my skill description",
   "shouldTrigger": true},
  {"query": "Check whether these queries trigger my skill",
   "shouldTrigger": true},
  {"query": "Write a new skill from scratch", "shouldTrigger": false},
  {"query": "Debug why my python tests are failing", "shouldTrigger": false},
  {"query": "Split my query set into train and validate", "shouldTrigger": true},
  {"query": "Proofread this blog post draft", "shouldTrigger": false}
]
EOF
WS=$(tools/test-harness/workspace-manager.sh init --prefix final-trigger)
tools/test-harness/workspace-manager.sh sync --skill "$T" \
  --source "skills/$T" --workspace "$WS"
uv run python tools/test-harness/evaluator.py suite \
  --harness opencode --model llama.cpp/gemma-4-26B-A4B --timeout 300 \
  --skill "$T" --agents-dir agents --workspace "$WS" \
  --queries "$TMP/trigger-queries.json" \
  --out "$TMP/trigger-results.json" --reps 1
tools/test-harness/workspace-manager.sh cleanup --workspace "$WS"
uv run python tools/test-harness/evaluator.py failures \
  --results "$TMP/trigger-results.json"
# scoring check: per-query outcome in the summary matches the recorded
# rep verdicts in trigger-results.json
```

**Retrieval** — all 17 queries, both arms (retrieval's documented
arm-parallel structure), one rep:

```bash
mkdir -p "$TMP/ws-skill" "$TMP/ws-control"
tools/test-harness/workspace-manager.sh sync --full --skill "$T" \
  --source "skills/$T" --workspace "$TMP/ws-skill"
uv run python tools/test-harness/evaluator.py retrieval-suite \
  --harness opencode --model llama.cpp/gemma-4-26B-A4B --timeout 300 \
  --skill "$T" --agents-dir agents \
  --skill-workspace "$TMP/ws-skill" --control-workspace "$TMP/ws-control" \
  --queries "$TMP/queries.json" --out "$TMP/retrieval-results.json" --reps 1
uv run python tools/test-harness/evaluator.py retrieval-evidence \
  --results "$TMP/retrieval-results.json" > "$TMP/retrieval-evidence.txt"
```

**Shape** — all 5 entries; arms per variant-set group (entries declare
heterogeneous variant sets — `v1` everywhere, `v2` everywhere, `v3` on
2 — so no single `--arms` covers the pool; per-group invocations are the
real campaign's shape and compose through multi-file union at check
time). Invocation 1 carries `--reps 2` for the batch path; arms and
entries stay strictly serial per the skill:

```bash
mkdir -p "$TMP/ws-shape"
uv run python tools/test-harness/evaluator.py shape-suite \
  --harness opencode --model llama.cpp/gemma-4-26B-A4B --timeout 300 \
  --skill "$T" --agents-dir agents --workspace "$TMP/ws-shape" \
  --entries "$TMP/entries.json" --skill-file "skills/$T/SKILL.md" \
  --arms v0,v1 --out "$TMP/shape-results-v0v1.json" --reps 2
uv run python tools/test-harness/evaluator.py shape-suite \
  --harness opencode --model llama.cpp/gemma-4-26B-A4B --timeout 300 \
  --skill "$T" --agents-dir agents --workspace "$TMP/ws-shape" \
  --entries "$TMP/entries.json" --skill-file "skills/$T/SKILL.md" \
  --arms v2 --out "$TMP/shape-results-v2.json" --reps 1
python3 -c "import json; d=json.load(open('$TMP/entries.json')); print(json.dumps([e for e in d if 'v3' in e.get('variants',{})], indent=2))" \
  > "$TMP/entries-v3.json"
uv run python tools/test-harness/evaluator.py shape-suite \
  --harness opencode --model llama.cpp/gemma-4-26B-A4B --timeout 300 \
  --skill "$T" --agents-dir agents --workspace "$TMP/ws-shape" \
  --entries "$TMP/entries-v3.json" --skill-file "skills/$T/SKILL.md" \
  --arms v3 --out "$TMP/shape-results-v3.json" --reps 1
uv run python tools/test-harness/evaluator.py shape-evidence \
  --results "$TMP/shape-results-v0v1.json" --compare \
  > "$TMP/shape-evidence.txt"
# expect: per-marker EXCEEDS/does-not-exceed lines for v1 vs v0 only —
# compare lines never name v0; (the v0-rerun skip itself was verified
# synthetically in 4.1)
```

**Pressure** — all 10 rules, RED then GREEN as separate serial
invocations (the skill's arm seriality is driver-level: one `--arm` per
invocation, read the counters between):

```bash
mkdir -p "$TMP/ws-pressure"
for arm in red green; do
  uv run python tools/test-harness/evaluator.py pressure-suite \
    --harness opencode --model llama.cpp/gemma-4-26B-A4B --timeout 300 \
    --skill "$T" --agents-dir agents --workspace "$TMP/ws-pressure" \
    --scenarios "$TMP/scenarios.json" --arm "$arm" \
    --skill-file "skills/$T/SKILL.md" \
    --out "$TMP/pressure-results-$arm.json" --reps 1
  uv run python tools/test-harness/evaluator.py pressure-evidence \
    --results "$TMP/pressure-results-$arm.json" \
    > "$TMP/pressure-evidence-$arm.txt"
done
```

### 5.3 Scoring + record keeping (Phases 2, 3, 4 exercised together)

Per track: emit the skeleton (3.1) → fill the null judgment fields from
the evidence output (driver work, per the 3.4 docs) → check → record
into the single `$TMP/manifest.json` copy (3.2, 3.3) → assert the
manifest counts equal the scored sums:

```bash
uv run python tools/test-harness/evaluator.py scored-check \
  --results "$TMP/retrieval-results.json" \
  --emit-skeleton "$TMP/scored-retrieval.json"
uv run python tools/test-harness/evaluator.py shape-scored-check \
  --results "$TMP/shape-results-v0v1.json" \
  --results "$TMP/shape-results-v2.json" \
  --results "$TMP/shape-results-v3.json" \
  --emit-skeleton "$TMP/scored-shape.json"
uv run python tools/test-harness/evaluator.py pressure-scored-check \
  --results "$TMP/pressure-results-red.json" \
  --results "$TMP/pressure-results-green.json" \
  --emit-skeleton "$TMP/scored-pressure.json"
# negative (must exit 1): each skeleton as-is, unfilled — the
# you-forgot-to-judge gate
# then fill every null judgment field in the three files to match the
# evidence outputs, and:
uv run python tools/test-harness/evaluator.py scored-check \
  --results "$TMP/retrieval-results.json" --scored "$TMP/scored-retrieval.json"
uv run python tools/test-harness/evaluator.py shape-scored-check \
  --results "$TMP/shape-results-v0v1.json" --results "$TMP/shape-results-v2.json" \
  --results "$TMP/shape-results-v3.json" --scored "$TMP/scored-shape.json"
uv run python tools/test-harness/evaluator.py pressure-scored-check \
  --results "$TMP/pressure-results-red.json" --results "$TMP/pressure-results-green.json" \
  --scored "$TMP/scored-pressure.json"
# all three must exit 0 — multi-file union with per-arm dedupe (1.5) is
# exercised by the three shape files sharing entry ids across arms

uv run python tools/test-harness/evaluator.py record \
  --skill "$T" --skill-path "skills/$T" --manifest "$TMP/manifest.json" \
  --scope dir --scored "$TMP/scored-retrieval.json" --campaign final-verify
uv run python tools/test-harness/evaluator.py record \
  --skill "$T" --skill-path "skills/$T" --manifest "$TMP/manifest.json" \
  --scope dir --scored "$TMP/scored-shape.json" --campaign final-verify
uv run python tools/test-harness/evaluator.py record \
  --skill "$T" --skill-path "skills/$T" --manifest "$TMP/manifest.json" \
  --scope dir --scored "$TMP/scored-pressure.json" --campaign final-verify
uv run python tools/test-harness/evaluator.py record \
  --skill "$T" --skill-path "skills/$T/SKILL.md" --manifest "$TMP/manifest.json" \
  --scope frontmatter --score-from "$TMP/trigger-results.json" \
  --campaign final-verify
# track detection (3.2) is exercised three times above: three different
# track vocabularies recorded into the same manifest with no --track
# flag; the trigger record uses --scope frontmatter per the trigger
# SKILL.md (the manifest's trigger-test key is created by this record —
# no committed trigger campaign exists yet)

TMPD="$TMP" python3 - <<'EOF'
import json, os
tmp = os.environ["TMPD"]
m = json.load(open(f"{tmp}/manifest.json"))

r = json.load(open(f"{tmp}/scored-retrieval.json"))["entries"]
sums = {k: 0 for k in ("pass", "fail", "gap", "void")}
for e in r:
    assert e["result"] in sums, e["result"]
    sums[e["result"]] += 1
e = m["retrieval-test"]
for result, key in (("pass", "passes"), ("fail", "fails"),
                    ("gap", "gaps"), ("void", "voids")):
    assert e[key] == sums[result], (key, e[key], sums[result])

for track, scored_file in (("shape-test", "scored-shape.json"),
                           ("pressure-test", "scored-pressure.json")):
    s = json.load(open(f"{tmp}/{scored_file}"))["entries"]
    sums = {k: 0 for k in ("adopted", "no-failure", "unresolved", "voids")}
    for ent in s:
        key = ent["result"].replace("_", "-")
        assert key in sums, (track, ent["result"])
        sums[key] += 1
    e = m[track]
    for k, v in sums.items():
        assert e[k] == v, (track, k, e[k], v)

assert isinstance(m["trigger-test"]["score"], float)
print("record keeping: all four tracks recorded; counts == scored sums")
EOF
```

Inventory round-trip (Phase 2) on the target skill's two inventories —
mint idempotence, empty self-diff, and one synthetic change:

```bash
uv run python tools/test-harness/evaluator.py inventory-check \
  --inventory "$TMP/rules.json" --kind rule            # expect exit 0
uv run python tools/test-harness/evaluator.py inventory-mint \
  --inventory "$TMP/rules.json" --kind rule --out "$TMP/rules-minted.json"
uv run python tools/test-harness/evaluator.py inventory-mint \
  --inventory "$TMP/rules-minted.json" --kind rule --out "$TMP/rules-minted2.json"
cmp "$TMP/rules-minted.json" "$TMP/rules-minted2.json"   # byte-identical
uv run python tools/test-harness/evaluator.py inventory-diff \
  --old "$TMP/rules.json" --new "$TMP/rules-minted.json" --kind rule \
  --out "$TMP/rules-diff.json"
python3 -c "import json; d=json.load(open('$TMP/rules-diff.json')); assert not any(d[k] for k in ('new','changed','deleted','excluded')), d; print('rules self-diff empty: ok')"
python3 -c "
import json
d = json.load(open('$TMP/rules.json'))
d['rules'][0]['statement'] += ' (synthetic final-verify edit)'
json.dump(d, open('$TMP/rules-edited.json', 'w'))
"
uv run python tools/test-harness/evaluator.py inventory-diff \
  --old "$TMP/rules.json" --new "$TMP/rules-edited.json" --kind rule \
  --out "$TMP/rules-edit-diff.json"
python3 -c "import json; d=json.load(open('$TMP/rules-edit-diff.json')); assert len(d['changed']) == 1, d; print('exactly one changed rule: ok')"
# repeat the check+mint+diff-empty trio for "$TMP/facts.json" --kind fact
rm -rf "$TMP"
```

### 5.4 Coverage matrix (every phase → exercised here)

| Plan element | Verified in Phase 5 by |
|---|---|
| 1.1 `validate_eval_agent` | every suite invocation's pre-spend gate (retrieval ×2 agents, shape, pressure) |
| 1.2 `run_rep_batched` | shape invocation 1 (`--reps 2`, smoke + batch); retrieval/pressure suites (reps path) |
| 1.3 `write_results` | every `*-results.json` envelope written |
| 1.4 `iter_evidence`/`load_results_json` | every `*-evidence` invocation |
| 1.5 `union_results`/`check_coverage`/`load_scored_json` | three shape results files with shared entry ids; scored checks over multi-file unions |
| 1.6 `load_entries` | every suite's fixture validation (heterogeneous shape variant sets included) |
| 1.7 test consolidation | 5.1 full gate |
| Phase 2 inventory | 5.3 rules + facts round-trip |
| 3.1 `--emit-skeleton` | 5.3 skeleton emission (three tracks) + unfilled-skeleton negative |
| 3.2 `record --scored` + track detection | 5.3 three same-manifest records, no `--track` |
| 3.3 `--score-from` | 5.3 trigger record |
| 4.1 `--compare` | 5.2 shape evidence `--compare` (v0/v1) |
| 4.2 cost helper | n/a (rejected — nothing to verify) |
| Parallelism invariants | shape/pressure suites keep arms/rules serial (single-arm pressure invocations, per-pair shape batches); retrieval keeps arm-parallelism |
| Record keeping end-to-end | 5.3 manifest assertion block |

**Phase 5 done criteria:** 5.1 gate green; all four campaigns' scoring
checks pass; the 5.3 manifest assertion block prints its success line;
both inventory diffs behave as asserted. Then — and only then — the plan
is fully verified.

---

## Sequencing, PRs, and risk register

```
PR 1 (Phase 1.1–1.5 + 1.7)  pure refactor + test consolidation ──► 315
                            tests must pass, none dropped (1.7 is the
                            point of the refactor; not separable)
PR 2 (Phase 1.6)        envelope-only load_entries (schema table is a
                        contingent stretch goal, not committed)
PR 3 (Phase 2)          inventory command + 3 SKILL.md inventory-step
                        edits (retrieval/shape/pressure) in the same PR
                        ── atomic
PR 4 (Phase 3)          skeleton + record --scored + 4 SKILL.md edits  ── atomic
PR 5 (Phase 4.1)        shape-evidence --compare + shape SKILL.md doc
                        edit in the same PR  ── atomic
Phase 5                 no code — final end-to-end verification (all
                        gates, full campaigns on trigger-testing-skills,
                        scoring + record-keeping assertions; everything
                        in a temp dir, nothing committed)
```

| Risk | Mitigation |
|---|---|
| Exact stderr messages pinned by 315 tests drift during extraction | Run the suite after **each** step, not each phase; diff failure text before moving on |
| Step 1.6 schema-table can't reproduce message fidelity | Schema table is a contingent stretch goal; the committed plan extracts only the envelope, which keeps per-field messages byte-identical by never moving them |
| `sys.exit(1)` inside threads behaves differently after refactor | Retrieval's `SystemExit` propagation at 1315–1318 preserved; its abort tests are the canary |
| Phase 3 `--scored` breaks in-flight campaign docs | Legacy argv path kept one release with a stderr deprecation note |
| Phase 3 script/SKILL.md drift | Land script + doc edits in the same PR; verify by walking each SKILL.md's command sequence against `--help` |
| Test consolidation silently drops a per-track case | Move tests with `git mv`-style discipline; test **count must not decrease** in PR 1 (315 + new − 0 removed) |

**Totals:** six shared helpers + one inventory implementation
(~3 commands) + one command-signature change (`record --scored`) + eight
SKILL.md touch-points across four distinct documents (3 in PR 3, 4 in
PR 4, 1 in PR 5), against **~950–1,000 lines** of verified per-track
duplication in `evaluator.py`. Be honest about the trade: PR 1 nets only
≈ −200 lines against ~950 lines of stderr-exact-pinned churn.
The refactor is justified by the anti-drift test consolidation (1.7) and
by Phases 2–4 moving deterministic work off the LLM — not by line
count. If 1.7 were dropped, Phase 1 should not happen.
