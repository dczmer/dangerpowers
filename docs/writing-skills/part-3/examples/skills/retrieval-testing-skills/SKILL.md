---
name: retrieval-testing-skills
description: Use when the user asks to run a retrieval test or retrieval-testing campaign against a reference skill, verify that agents can find and correctly apply documented facts, or surface gaps and unclear sections in a reference doc. Runs task-shaped eval queries from a queries file through read-only subagents and reports per-fact pass/fail with failure classifications.
disable-model-invocation: true
metadata.opencode/slash: true
metadata.opencode/autoinvoke: false
---

# Retrieval Testing Skills

## Overview

Run one retrieval-test campaign for a reference skill against a file of eval queries and report the results. Reference content has no rule to violate, so there is nothing to pressure-test: each scenario checks that a fresh agent can find a documented fact and apply it, one run per scenario, and failures are doc failures — fixed by editing the doc, never by adding rules.

The skill under test is force-loaded by instruction in every scenario. Retrieval testing measures the skill *body*; whether the description triggers at all is the separate trigger-testing track.

## Inputs

Collect all inputs before starting. Prompt the user for any that are missing.

- **Skill name** — the reference skill under test. It must appear in this session's available-skills list; subagents can only load skills the parent session can see. If it is not available, stop and tell the user. Resolve its filesystem location and derive the **source root**: the directory containing the `skills/` directory the skill lives in — not necessarily the repo root (for `<root>/.opencode/skills/<name>`, the source root is `<root>/.opencode`).
- **Queries file** — path to a populated `queries.json`. Default convention: `<source-root>/skills-workspace/<skill>/retrieval-tests/queries.json`, so test artifacts live next to the skill under test, wherever it is registered.

After resolving the source root, read the skill under test fully and extract every documented fact into a fact inventory. If the inventory is empty — the skill documents no facts — stop: retrieval testing is not required. Otherwise compare the inventory against the queries file: if any fact lacks a covering query — or the file does not exist at all — offer to generate the missing test queries and expectations. With the user's approval, add them to the queries file following the format below, and explain each generated entry: the documented fact it covers, why you chose that query, and why you chose those expectations.

## Query file format

Each entry tests one documented fact:

```json
[
  {
    "id": "retry-after-header",
    "query": "Given this upload function — `def upload(path, url): return requests.post(url, data=open(path, 'rb'))` — add retry handling for 429 responses and return the complete updated function inline.",
    "expect": [
      "reads the Retry-After header rather than using a fixed backoff",
      "interprets the value as seconds",
      "does not retry on other 4xx codes"
    ]
  }
]
```

- `id` — stable fact identifier; never reuse ids across facts.
- `query` — a realistic, task-shaped prompt that stands alone: self-contained by construction (embed any code or context the task refers to — the eval session has no pre-existing files for the agent to find), never names the section or file holding the fact, never hints at the answer, never quotes rubric text.
- `expect` — objective rubric bullets. A scenario passes only if every bullet is met by the returned answer.

## Subagent prompt

Give each skill-arm subagent this prompt exactly, replacing `{{SKILL NAME}}` and `{{TEST QUERY}}`:

    You are in a read-only session: file-modification tools are disabled and
    shell commands that change filesystem or repository state will fail. This
    is expected, not an error — plan around it.

    **Rules:**
    - Before anything else, load the skill named {{SKILL NAME}} using the skill
      tool. It is your reference documentation for the task; read it, and read
      whatever files it directs you to.
    - Perform the task below. General programming knowledge may fill in the
      basics, but any fact the skill documents must come from the skill.
    - NEVER create, modify, rename, or delete any file. NEVER run a mutating
      command — no redirects into files, no package installs, no git
      operations, no rm/mv/mkdir/chmod. Reading, searching, and loading
      skills is all you may do.
    - If the task asks you to change something, produce the would-be result
      inline instead: complete code in fenced blocks, prose as prose. An
      answer that exists only on disk counts as no answer.
    - Do not ask clarifying questions. Make a reasonable assumption, state it
      in one line, and proceed.
    - Finish with a "Sources consulted:" list naming the exact skill sections
      and files you actually used, then end the turn.

    Task: {{TEST QUERY}}

The control-arm prompt is identical except the first rule is replaced with: "Do NOT load any skill. Answer entirely from your own knowledge." and the "Sources consulted" requirement is dropped.

The "read-only session" claim is a behavioral guardrail, not a real restriction — the subagent actually has full tools. The rules above, the inline-output requirement, and the timeout in the workflow are the only mitigation against repository mutation.

Do not give the subagent any additional information and do not inform it that this is a test.

## Workflow

1. Confirm the skill is available in the session and read the queries file. If it is missing or empty, stop — never invent queries mid-campaign.
2. Dispatch all subagents in parallel in a single message, using the harness's general-purpose subagent type: for each query-file entry, one skill-arm subagent AND one control-arm subagent. Give each exactly the template prompt — no added context, no rubric text, no hint that this is a test.
3. Abort any subagent still running after 120 seconds. Retrieval runs read a doc and write an inline answer; a run going longer has ignored the rules and started real work. It is measuring nothing; kill it.
4. Verify the skill-loaded signal in each skill-arm result — the skill-tool invocation for the exact skill name. No signal → `void` (the doc was never in context; the run measured nothing). A control-arm run that loaded any skill → `void` (contaminated baseline).
5. If any run's output or transcript shows a file mutation happened despite the rules: void the run, check `git status` for repository contamination, restore if needed, and note it in the report.
6. Score each non-void skill-arm run against its rubric, bullet by bullet, using ONLY the returned inline answer — never what the subagent claims it did or found. All bullets met → `pass`; otherwise `fail`, recording exactly which bullets missed.
7. Classify every failed skill-arm run from its "Sources consulted" list (fall back to the session transcript if the list is missing or looks wrong):
   - Fact's home section never consulted, and the fact IS in the doc → `findability`
   - Home section consulted, answer still wrong → `clarity`
   - Fact absent from the doc entirely → `gap`
8. Compare each scenario against its control run: control passed → flag the fact for ablation review. Control failed and skill arm passed → the doc is confirmed load-bearing for that fact.
9. Account for every entry in the queries file. Never drop a scenario from the report because it was inconvenient or void.

## Improving the skill definition

Fix failures by editing the doc — never by adding behavioral rules, prohibitions, or "always read X first" discipline clauses. A reference failure means the information architecture failed, not the agent.

| Classification | Right fix | Never |
|---|---|---|
| `gap` | Add the missing content where a fresh agent would look for it | A rule forbidding the hallucination |
| `findability` | Better headings, a TOC, a quick-reference row, a direct link from SKILL.md, one-level-deep references, descriptive filenames. Agents partially read nested files (`head -n 100` previews) — move important reference content above line 100 | "Always read X first" clauses |
| `clarity` | Rewrite the section; disambiguate look-alike facts; consistent terminology | Prohibition lists |
| ablation flag | Re-run that scenario next campaign; retire the entry if the baseline keeps passing | Deleting on a single control pass |

Campaign rules:

- Fix between campaigns, never mid-campaign: complete the full pass, then apply edits. Mid-campaign doc edits invalidate every later result.
- Present recommended edits to the user and apply them only after confirmation.
- After edits land, re-run ONLY the failed scenarios (with their controls) as a mini-campaign to confirm.
- Keep queries verbatim across campaigns; editing a query invalidates comparison. If a query is bad — asks for nothing, depends on context the bare session lacks — prune it and say so in the report.
- A scenario still failing after a doc fix gets one more doc revision. Still failing after that: surface it to the user — the fact likely needs restructuring, not rewording.

## Report format

    retrieval test: acme-api — 2026-09-11
    queries: skills-workspace/acme-api/retrieval-tests/queries.json (6 entries)

    id                    result   control
    retry-after-header    pass     fail (load-bearing)
    upload-chunk-size     fail     fail
    oauth-refresh-flow    pass     fail (load-bearing)
    error-code-table      pass     pass → ablation flag
    webhook-signatures    gap      —
    pagination-cursor     void     —

    summary: 3 pass / 1 fail / 1 gap / 1 void (6 scenarios)

    failures:
    upload-chunk-size — missed bullet: "uses 4 MiB chunks". Sources consulted:
      "Authentication", "Errors"; never opened "Uploads". classification:
      findability. recommended fix: add an Uploads row to the quick-reference
      table in SKILL.md.

    gaps:
    webhook-signatures — common use case absent from the doc. recommended
      fix: add a webhook signature verification section.

    ablation flags:
    error-code-table — control answered correctly without the skill;
      re-check next campaign, retire if the baseline keeps passing.

## Gotchas

- Never name the section or file holding the fact in a query — that tests following directions, not retrieval.
- Never put rubric text in a subagent prompt; score from the returned answer only. Extra framing contaminates the measurement.
- Never provide additional information, besides the prescribed prompt text to the subagent.
- Never let the subagent know that this is a test.
- The read-only claim is a guardrail, not enforcement. If a run mutates the repo anyway: void it, check `git status`, restore if needed, report the contamination.
- "It clearly used the doc" is not evidence. Only the returned inline answer is scored, bullet by bullet.
- A missing skill-load signal is `void`, not `fail` — the doc was never in context.
- A control pass is a flag, not a verdict: one clean baseline answer doesn't prove redundancy, it schedules a re-check.
- Don't stack pressure or obstacles into retrieval queries — that's the discipline track. Plain, realistic tasks only.
- Keep the query verbatim within and across campaigns; editing it invalidates comparison with earlier campaigns.
- A skill that is not available in the current session cannot be tested this way. Confirm availability before dispatching.

## Checklist

- [ ] Inputs collected; skill confirmed available in the session; queries file exists, is non-empty, and covers the fact inventory — any generated entries explained and approved by the user
- [ ] Every query is task-shaped, self-contained, and free of section hints and rubric text
- [ ] Two subagents per entry (skill arm + control arm), dispatched in parallel in a single message, each given exactly the template prompt
- [ ] Every skill-arm run verified for the skill-loaded signal; missing signal → void
- [ ] Every run checked for repository mutation; mutating runs voided and `git status` verified clean
- [ ] Scoring from the returned inline answer only, bullet by bullet; pass requires all bullets
- [ ] Every failure classified (gap / findability / clarity) from the sources-consulted list, with transcript fallback
- [ ] Control passes flagged for ablation review, not auto-retired
- [ ] Every queries-file entry accounted for in the report — none dropped
- [ ] Report shows per-scenario results, summary counts, failure classifications, and recommended doc fixes
- [ ] Doc edits applied only after the full pass completes and only with user confirmation; failed scenarios re-run afterwards
