# Reference Skills and Retrieval Testing: What It Is, Why It Exists, and How to Run It

> **Disclaimer: AI-generated research**
>
> This document was researched and written by an AI coding assistant on
> 2026-09-11. It is based on the public `obra/superpowers` repository
> (the `writing-skills` SKILL.md, `testing-skills-with-subagents.md`,
> the worked example `examples/CLAUDE_MD_TESTING.md`, and the bundled
> `anthropic-best-practices.md`), plus the local `trigger-testing-skills`
> campaign infrastructure used for the campaign-shape sections.
> Verify against the linked primary sources before citing or relying on
> this document.

## Overview

Reference skills are the fourth type in the superpowers taxonomy: **pure
contextual information with no rule to break** — API docs, syntax guides,
flag tables, command references, limits, error codes. Superpowers defines
the test approach directly:

> **Reference Skills (documentation/APIs)** — Test with: Retrieval
> scenarios (can they find the right information?), Application scenarios
> (can they use what they found correctly?), Gap testing (are common use
> cases covered?). **Success criteria:** Agent finds and correctly
> applies reference information.

Retrieval testing is the only test type that applies to this category,
and its structure differs from the other tracks in one key way: **run a
few simple retrieval tasks, single pass, no iteration.** There is no
RED/GREEN/REFACTOR loop per rule, no pressure stacking, no
rationalization table — because there is no compliance behavior to
harden. The doc itself is the thing under test, and failures are fixed
by **editing the doc** (fill the gap, clarify the section, fix the
organization), never by adding rules.

One apparent contradiction in the superpowers sources is worth
resolving: `testing-skills-with-subagents.md` says "Don't test: pure
reference skills." Read in context, that means don't *pressure-test*
them — the same repo's `writing-skills` checklist still requires testing
reference skills before deployment, just via retrieval.

## Why test reference skills at all

The superpowers rationalization table answers this directly — two of
its entries exist precisely to rebut skipping reference testing:

| Excuse | Reality |
|---|---|
| "It's just a reference" | References can have gaps, unclear sections. Test retrieval. |
| "Academic review is enough" | Reading ≠ using. Test application scenarios. |

The failure modes of a reference doc are real and distinct from
discipline failures:

1. **Gaps** — a common use case isn't covered, so the agent hallucinates
   the missing fact. The most dangerous failure because it's silent.
2. **Unclear sections** — the agent retrieves the right section but
   applies it wrong (ambiguous parameter semantics, look-alike flags,
   v1-vs-v2 endpoints side by side).
3. **Findability/organization failures** — the fact exists but the agent
   can't locate it. Anthropic's best practices document exactly how this
   happens: agents partially read deeply-nested files (`head -100`
   previews), miss connections between files, and never open
   poorly-signaled bundled files. Their guidance — references one level
   deep from SKILL.md, TOCs on 100+ line files, descriptive filenames,
   "test file access patterns: verify the agent can navigate your
   directory structure by testing with real requests" — is essentially a
   list of reference-retrieval failure modes observed in the wild.

The psychology is inverted versus discipline testing: the agent *wants*
to comply; there's no incentive to bypass a fact. So you don't need
pressure — you need to verify the information architecture actually
delivers the fact to a fresh agent that doesn't know where you put it.

There's also a second-order reason: **the baseline doubles as an
ablation signal.** If a fresh agent answers correctly *without* the
skill (the fact is in its training data), that reference entry may be
redundant — which feeds directly into ablation and retirement.

## How to identify reference rules

Real skills are usually mixed, so classification is per-section or
per-claim, not per-skill. Three practical tests:

**1. The violation test (primary).** Ask: *"Is there anything here an
agent could choose to violate?"* Reference content has no compliance
cost and no incentive to bypass — it's a fact the agent needs but
doesn't have. "The retry endpoint returns `Retry-After` in seconds"
can't be violated; it can only be unknown, unfound, or misread.

**2. Linguistic markers.** Reference content is declarative, not
imperative:

- Reference: lookup tables, "X is Y", parameter lists, compat matrices,
  file paths, error code glossaries, syntax blocks.
- Not reference: anything addressed at behavior with "always / never /
  must / prefer" — those are discipline or shaping rules even when they
  appear inside an otherwise reference-flavored doc.

**3. The inversion test.** Try to construct a scenario where the agent
is *tempted* not to follow the statement. If that's nonsensical —
"tempted to believe the rate limit is different"? — it's reference. If
you can construct a genuine temptation (skip the tests, use inline
styles), it's discipline/shaping and belongs to the other test tracks.

**Procedure:** read the skill fully, extract each discrete claim, tag
each one. Everything tagged reference goes onto a **fact inventory** —
the list of lookup targets that becomes the backbone of the test
campaign. In a mixed skill, the reference sections get retrieval tests
in the same campaign cycle where discipline sections get pressure tests;
the tracks don't interfere.

## How to design a retrieval test scenario

**One fact per scenario.** Each scenario has a single correct answer
that exists in the doc. You're testing a lookup, not a workflow.

**Task-shaped, not quiz-shaped.** Superpowers warns even for discipline
tests that academic questions ("what does the skill say about X?") just
get recited — for reference tests they're worse, because reciting isn't
the failure mode. Embed the fact-need in a realistic task: *"Write a
script that syncs records; handle the case where the API returns 429"*
— where correct handling depends on the `Retry-After` convention
documented only in the skill.

**Self-contained.** Embed in the query any code or context the task
refers to — the eval session has no pre-existing files. *"Add retry
handling to the upload script"* sends the agent hunting for a file that
doesn't exist (or stalls it on "which script?"); inline the function
instead.

**Require application, not just lookup.** The fact must be *used* in
the output — applied in code, or used to choose between options. This
tests superpowers' second question ("can they use what they found
correctly?"), not just grep-ability.

**Include distractors.** Place the target fact near similar-but-wrong
facts (v1 vs v2 endpoint, `--force` vs `--force-with-lease`, two
similarly-named config keys). A scenario with no distractors tests
existence, not discrimination.

**Fresh agent, skill loaded, no pressure.** Unlike discipline
scenarios, do **not** stack time/sunk-cost/authority pressure — there
is no rationalization to provoke. The scenario is a plain, realistic
task.

**Objective scoring.** Write the expected outcome as verifiable rubric
bullets, in the style of Anthropic's eval JSON structure:

```json
{
  "query": "Given this upload function — `def upload(path, url): return requests.post(url, data=open(path, 'rb'))` — add retry handling for 429 responses and return the complete updated function inline.",
  "expected_behavior": [
    "Reads the Retry-After header rather than using a fixed backoff",
    "Interprets the value as seconds (per the skill's API reference)",
    "Does not retry on 4xx codes other than 429"
  ]
}
```

**Three scenario families**, one per superpowers question:

1. **Retrieval** — the fact exists; the answer requires that exact fact.
2. **Application** — multi-step; the agent must combine the retrieved
   fact with the task (catches "found it, used it wrong").
3. **Gap probes** — take the top-N real use cases for the reference and
   task them. If the doc doesn't cover one, that's a **doc gap finding,
   not an agent failure** — log it as content to add.

**Keep the baseline.** One no-skill control rep per scenario. If the
agent hallucinates without the skill and succeeds with it, the
reference is proven load-bearing. If it succeeds without the skill,
flag the fact for ablation review.

## How a retrieval testing campaign might look

Modeled on the local `trigger-testing-skills` campaign shape, but much
simpler — no train/validate split, no iterative description revision,
no Wilson scores:

**1. Fact inventory (the analog of `queries.json`).** Extract the
discrete facts from the reference into
`<source-root>/skills-workspace/<skill>/retrieval-tests/facts.json`,
where the source root is the directory containing the `skills/`
directory the skill under test lives in — so artifacts live next to the
skill itself, not necessarily at the repo root (for
`<root>/.opencode/skills/<name>`, artifacts live at
`<root>/.opencode/skills-workspace/`). Each entry has an ID, the doc
section that answers it, and one scenario (query + expected_behavior
rubric). Cover the three families above, weighted toward the
most-common real use cases.

**2. Campaign dir.** `campaign-YYYY-MM-DD[-N]` under
`retrieval-tests/`, persistent and committed — same convention as
trigger-test campaigns. Holds the fact inventory snapshot,
per-scenario result JSON, and logs.

**3. Execution.** Fresh headless harness session per scenario, sterile
workspace, skill synced in via the same `workspace-manager.sh` pattern.
**One rep** suffices for most scenarios — you're not measuring a
probabilistic behavior like triggering; a lookup either lands or it
doesn't. Add reps only if a scenario comes back flaky. One no-skill
control rep per scenario for the ablation signal.

**4. Scoring — capture the navigation trace, not just pass/fail.** This
is the diagnostic gold unique to reference testing. On failure, record
*where the agent looked*: which files it opened, which sections it
read, what it grepped for. Anthropic's "observe how agents navigate
skills" guidance (unexpected exploration paths, missed connections,
overrelied-upon sections, never-opened files) is exactly the failure
taxonomy this trace gives you.

**5. Failure classification → fix mapping** (the reference-track analog
of the form-to-failure table):

| Observed failure | Diagnosis | Fix |
|---|---|---|
| Correct answer exists nowhere in the doc | Gap | Add the content |
| Fact exists; agent never opened the right file/section | Findability | Better headings, TOC, direct link from SKILL.md, one-level-deep references, descriptive filenames |
| Agent read the right section, applied it wrong | Clarity | Rewrite that section; disambiguate look-alike facts; consistent terminology |
| Agent answered correctly *without* the skill | Redundancy | Flag for ablation/retirement review |

**6. Iterate at the doc level, not the rule level.** This is what
"single pass, no iteration" means in practice: no per-rule REFACTOR
loop under pressure. Fix the doc across the whole campaign, then
re-run **only the failed scenarios** to confirm. A scenario that still
fails after a doc fix gets one more doc revision; there's no third
mechanism to reach for.

**7. Record.** Append the campaign result (pass rate, fixes applied,
ablation flags, frontmatter checksum) to a `manifest.json` alongside
the trigger-test manifest, so retrieval status is visible next to
trigger status for the same skill.

## References

- https://github.com/obra/superpowers/blob/main/skills/writing-skills/SKILL.md
- https://github.com/obra/superpowers/blob/main/skills/writing-skills/testing-skills-with-subagents.md
- https://github.com/obra/superpowers/blob/main/skills/writing-skills/examples/CLAUDE_MD_TESTING.md
- https://github.com/obra/superpowers/blob/main/skills/writing-skills/anthropic-best-practices.md
