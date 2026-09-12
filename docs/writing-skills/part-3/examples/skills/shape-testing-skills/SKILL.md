---
name: shape-testing-skills
description: Use when the user asks to run a shape test, micro-test, or wording test against a skill's output-shaping rules, verify that formatting or structure guidance actually holds in generated artifacts, or tune rule phrasing that produces inconsistent, bloated, or wrong-shaped output. Runs a temptation fixture through fresh-context subagents across wording variants with a no-guidance control and reports per-arm convergence with an adopted phrasing.
disable-model-invocation: true
metadata.opencode/slash: true
metadata.opencode/autoinvoke: false
---

# Shape Testing Skills

## Overview

Run one wording micro-test campaign for a single shaping rule — a rule about the *form* of the artifact an agent produces: file layout, styling mechanism, section order, required elements. Shaping failures are composition failures: the agent loaded the skill and followed its discipline rules, but the deliverable violates the output contract because the model's training prior pulled it toward a more common shape (self-contained single files, inline styles, prose summaries).

Micro-tests are unit tests for wording: cheap, single-shot, fresh-context samples that measure a phrasing before you commit to it. One rule per campaign. Discipline rules (compliance cost, rationalization away) and reference content (no rule to violate) are different tracks — if the rule under test is one of those, stop and say so.

## Inputs

Collect all inputs before starting. Prompt the user for any that are missing.

- **Skill path** — filesystem path to the skill under test. The driver reads the body from disk; subagents never load the skill, because the campaign tests wording variants that do not exist on disk. Derive the **source root**: the directory containing the `skills/` directory the skill lives in (for `<root>/.opencode/skills/<name>`, the source root is `<root>/.opencode`).
- **Shaping rule** — the single rule under test, quoted from the skill, or proposed text for guidance not yet authored. Confirm the classification with the user: the expected failure is *complies but wrong-shaped output*, and a competing incentive exists (self-containment, brevity, helpful traceability). A rule the agent skips under pressure is discipline; a documented fact is reference.
- **Fixture** — a self-contained task engineered to tempt the failure (see Fixture design). If the user does not supply one, draft one and get approval before any dispatch.
- **Variants** — wording arms to test. Default set in Variants below; the user may substitute.

## Campaign layout

```
skills-workspace/<skill>/shape-tests/
└── campaign-YYYY-MM-DD/          # or -2, -3 on same-day reruns
    ├── rule.json                 # rule text, markers, classification
    ├── fixture.md                # the verbatim fixture
    ├── variants.json             # arm id → exact guidance text
    ├── samples/                  # <arm>-rep-<n>.md — raw returned outputs
    └── report.md                 # final human-readable report
```

The driver session writes all campaign files. Subagents never touch the filesystem.

## Fixture design

The fixture's job is to tempt the wrong shape. If the fixture contains no temptation, every arm scores clean and you have learned nothing.

Rules for fixtures:

- Self-contained: no references to real files, repos, or context. Every path mentioned is illustrative.
- Never quote the rule text, the markers, or the expected shape — that tests following directions, not shaping under a competing incentive.
- Include at least one requirement the tempting wrong shape cannot satisfy, so the failure is forced into the open. Example: a `PriceTag` component whose badge must darken on hover — inline `style={{}}` cannot express hover, so the agent must either write real CSS (right shape) or reach for an `onMouseEnter`/`useState` hack (worse shape).
- Fixture kinds: an **application** fixture (the standard case) is required. Add a **gap** fixture (deliberately under-specified task) when the guidance might be underspecified, and a **variation** fixture when the rule has parameters worth stressing.

Before dispatching, write the scoring markers into `rule.json`: unambiguous grep tokens for *both* the wrong shapes and the right shape. For the `PriceTag` example:

```json
{
  "markers": {
    "inline_style":      "style=\\{\\{",
    "hover_hack":        "onMouseEnter|onMouseLeave",
    "raw_string_class":  "className=\"",
    "css_module_import": "import styles from",
    "module_css_block":  "\\.module\\.css"
  }
}
```

## Variants

Default arms. The guidance text is swapped into the skill-body section where the rule lives (or would live); the control omits that section entirely.

| Arm | Form | Purpose |
|---|---|---|
| V0 control | *(guidance absent)* | Proves the failure exists. Always run first. |
| V1 prohibition | "Never use inline styles or `style` props." | Expected to backfire or displace the failure; included to demonstrate the effect. |
| V2 recipe | "Every component ships as two files: `Name.tsx` and `Name.module.css`. All class names come from `import styles from './Name.module.css'`. Interactive states (hover, focus, active) are CSS pseudo-classes." | Positive contract: what the output IS, parts in order. |
| V3 recipe + nuance | V2 + "…unless a style is truly one-off." | Expected to degrade V2 to noisy; demonstrates the nuance-clause effect. |

Never test more than 3 variants per round. Never lead with a prohibition as the proposed fix — it is a measurement arm, not a candidate.

## Subagent prompt

Give each subagent this prompt exactly, replacing `{{SKILL CONTEXT}}` and `{{FIXTURE}}`:

    You are in a read-only session: file-modification tools are disabled and
    shell commands that change filesystem or repository state will fail. This
    is expected, not an error — plan around it.

    **Rules:**
    - NEVER create, modify, rename, or delete any file, and NEVER run a
      mutating command: no redirects into files, no git operations, no
      package installs, no rm/mv/mkdir/touch/chmod. Do not scaffold a
      project, save files for later, or verify your answer by building,
      linting, or running it. Producing the answer text is the entire task.
    - NEVER read, search, glob, or list the filesystem to ground your answer.
      The task is fully self-contained. Every path it mentions is
      illustrative — do not attempt to read, confirm, or create it.
    - Follow the project conventions below wherever they bear on the task.
    - Produce the complete artifact(s) inline in your reply: each file as a
      fenced code block prefixed by its path. An answer that exists only on
      disk counts as no answer.
    - Do not ask clarifying questions. Make a reasonable assumption, state it
      in one line, and proceed.
    - End the turn after the artifact(s): no change summary, no verification
      narrative, no offer to save or extend the work.

    Project conventions:
    {{SKILL CONTEXT}}

    Task: {{FIXTURE}}

Build `{{SKILL CONTEXT}}` per arm: the full skill body with frontmatter stripped, with the variant text swapped into the section where the rule lives. The control arm is the same body with that section omitted. Never test the guidance in isolation — wording effects only show up in realistic surrounding context.

The "read-only session" claim is a behavioral guardrail, not a real restriction — the subagent actually has full tools. The rules above, the inline-output requirement, and the timeout in the workflow are the only mitigation against repository mutation.

Do not give the subagent any additional information and do not inform it that this is a test.

## Workflow

1. Read the skill body fully. Confirm with the user that the rule is a shaping rule. Write `rule.json` with the rule text and markers.
2. Write `fixture.md` and `variants.json`. Present them plus the planned spend (round 1: 5 control + 3 variants × 5 reps = 20 samples; cap 30 per rule, 40 for pattern rules) and get user confirmation before dispatching anything.
3. **Control arm first.** Dispatch 5 subagents in parallel in a single message, using the harness's general-purpose subagent type. Score the returns. If the control never exhibits the failure, stop: author nothing. If the rule already exists in the skill, flag it for ablation review — the current model may not need it.
4. **Variant arms.** Dispatch 5 fresh subagents per arm in parallel in a single message. One sample per subagent — never ask one subagent for multiple drafts; the completions anchor each other.
5. Abort any subagent still running after 120 seconds and mark it `void`. A shape run produces inline text only; a run going longer has ignored the no-tools rules and started digging in the repository. It is measuring nothing; kill it.
6. If any run's output or transcript shows a file mutation happened despite the rules: void the run, check `git status` for repository contamination, restore if needed, and note it in the report.
7. Save every returned output verbatim to `samples/` before scoring anything.
8. Score with grep triage over `samples/` (e.g. `grep -c -E 'style=\{\{' samples/v2-*.md`), then READ every flagged sample. Template echoes and quoted counter-examples masquerade as hits; automated counts alone overstate both failure and success.
9. Judge on convergence, not just marker counts: when wording lands, all 5 reps produce the same structure. Five different structures across five reps means the wording is not binding. Adopt the variant that converges on the right shape and beats the control without regressing other markers. Ties go to the shorter phrasing.
10. No converging variant → round 2: change the FORM (prohibition → positive recipe → structural REQUIRED slot in a template), never more words on the same form. Hard cap 2 rounds. Still no convergence after round 2 → escalate to the user; the rule may need restructuring or mechanical enforcement instead of prose.
11. Report, and propose the winning phrasing as an edit to the skill. Write back to the source SKILL.md only after explicit user confirmation.

## Pattern rules

Pattern rules ("when you see X, reframe as Y") are shaping rules with two signature failures the standard flow misses:

- **Silent non-application.** The output is plausible and well-formed; the property is simply absent, so no marker trips. For pattern rules the with/without-control comparison is the primary detector, not a sanity gate: if the leading variant's outputs do not exhibit the property more often than the control, the rule is not binding — change the form.
- **Over-application.** The lens gets forced onto situations that do not call for it. This failure only exists *with* the guidance loaded, so counter-example fixtures need no control arm. Before adopting any variant, run a **restraint gate**: 5 reps against a counter-example fixture (a situation where the pattern should NOT be applied), scored for restraint. A variant that over-applies is disqualified; gate the next-best converging variant the same way. Budget +5 samples per gated variant, cap +10.

## Improving the skill definition

Match the fix to the observed failure. The form that fixes one failure type backfires on another.

| Observed result | Right form | Never |
|---|---|---|
| Control never exhibits the failure | Author nothing; flag an existing rule for ablation re-check | Hardening a phantom "just in case" |
| Prohibition suppresses the token but the failure migrates (inline styles banned → `useState` hover hacks) | Positive recipe: state what the output IS — its parts, in order | Stacking more prohibitions |
| A required element is omitted from an artifact the agent already produces | Structural REQUIRED field or slot in the template it fills in | Prose reminders near the template |
| Behavior should depend on a condition | Conditional keyed to an observable predicate ("if the brief exists, reference it") | Unconditional rule + exemption clauses |
| Reps disagree on the shape (noisy) | Change the form, not more words | Appending nuance clauses ("…unless it matters") |
| Two variants tie on every metric | Adopt the shorter phrasing — skills reload constantly, prose length is a real cost | Merging the two |

Campaign rules:

- One shaping rule per campaign. Rules interact; testing two at once makes attribution impossible.
- Keep fixtures and variant texts verbatim within and across campaigns; editing mid-campaign invalidates every comparison.
- Apply skill edits between campaigns, never mid-campaign.
- A nuance clause appended to a winning recipe degrades it — express a real exception as its own conditional on an observable predicate, and test that as a new variant.
- Exemption clauses do not scope ("this limit doesn't apply to code blocks" still suppresses code blocks). If part of the output must be exempt, restructure so the rule cannot reach it.
- Run with the model that will consume the skill in production, at default temperature. Re-check adopted phrasings on model upgrades via the ablation track.

## Report format

    shape test: react-component-conventions — 2026-09-11
    rule: "styling lives in a co-located CSS module, never inline"
    fixture: campaign-2026-09-11/fixture.md (application)
    samples: 20 (4 arms × 5 reps), 0 void

    arm              inline-style  hover-hack  css-module  shape across 5 reps
    V0 control       4/5           2/5         1/5         noisy — failure exists
    V1 prohibition   1/5           4/5         1/5         displaced, not fixed
    V2 recipe        0/5           0/5         5/5         converged → ADOPT
    V3 recipe+nuance 2/5           0/5         5/5         noisy — "one-off" disagreed

    notes:
    V1 suppressed the banned token but the hover requirement migrated into
    useState mouse-event hacks — a worse shape than the one banned. V3's
    nuance clause reopened the negotiation; reps disagreed on what counts
    as one-off.

    write-back: replace the styling section of skills/react-component-conventions/SKILL.md
    with the V2 text from variants.json [awaiting user confirmation]

## Gotchas

- A fixture with no temptation proves nothing — the same way a pressure scenario without pressure proves nothing. If every arm is clean, suspect the fixture before declaring victory.
- The control arm is the stopping signal. If the baseline never fails, there is nothing to fix — do not author guidance for a phantom failure.
- Never batch samples in one prompt ("give me five drafts"). One fresh-context subagent per sample.
- Never put the rule text, the expected shape, or scoring markers in the fixture or subagent framing. Extra framing contaminates the measurement.
- Grep is triage, not verdict. A sample that writes `// don't use style={{}} here` trips the inline-style grep without being a violation — read every flagged match by hand.
- The "read-only session" claim is a guardrail, not enforcement. If a run mutates the repo anyway: void it, check `git status`, restore if needed, report the contamination.
- Multi-file artifacts need all expected files: a recipe demanding `Name.tsx` + `Name.module.css` fails a rep that returns only one block, even if the returned block looks right.
- An abort after a complete inline answer still scores; an abort with partial output is `void`.
- Don't stack pressure into fixtures (deadlines, sunk cost, authority). That is the discipline track; the temptation here is structural.
- Never let the subagent know this is a test.
- Prohibition arms are measurement instruments for demonstrating displacement — never ship a prohibition as the fix for a shaping failure, even when it suppresses the banned token.

## Checklist

- [ ] Inputs collected; rule confirmed as shaping (complies-but-wrong-shape, competing incentive) with the user
- [ ] Fixture is self-contained, contains a real temptation, and is free of rule text, markers, and expected-shape hints
- [ ] Markers recorded in `rule.json` before dispatch — wrong-shape and right-shape tokens
- [ ] Planned spend (20 samples round 1; cap 30, or 40 for pattern rules) confirmed by the user before dispatch
- [ ] Control arm ran first; campaign stopped with no guidance authored if the control never exhibited the failure
- [ ] 5 fresh subagents per arm, one sample per subagent, dispatched in parallel in a single message, each given exactly the template prompt
- [ ] Every run checked for repository mutation; mutating runs voided and `git status` verified clean
- [ ] All returned outputs saved verbatim to `samples/` before scoring
- [ ] Every flagged grep match read by hand before trusting a verdict
- [ ] Adoption decided on convergence across reps, not marker averages alone; ties to the shorter phrasing
- [ ] Pattern rules: leading variant passed the restraint gate (5 reps on a counter-example fixture) before adoption
- [ ] Round 2 used a changed form, not more words; hard cap 2 rounds respected
- [ ] Report shows per-arm marker counts, convergence verdict, and the adopted phrasing
- [ ] Skill edit applied only after the full campaign and only with user confirmation
