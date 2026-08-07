---
name: writing-quick-plans
description: Use when planning a small, well-understood change where full research and context-bundle artifacts would be overkill — simple features, small projects, or a plan needed fast. Also use when about to save research summaries "for provenance" as a notes file or plan appendix, or when a request is too small for the research/scout/plan pipeline but still needs an implementation plan. Covers quick, one-shot, lightweight plans that skip research.
---

# Writing Quick Plans

One session, one file: a cursory research + scout pass whose evidence lives in the conversation, ending in a complete plan in `PLANS/`. For small projects and simple feature requests. Anything bigger routes to the full pipeline (researching-codebase → scouting-context → writing-plans).

## Workflow

1. **Scope check.** Restate the request. If it spans multiple subsystems, or the blast radius is unclear from the request alone, stop — recommend the full pipeline instead. This is the only sanctioned shortcut, and it exits the skill.
2. **Research pass — subagents report to context, not disk.** Spawn in parallel in one message:
   - **Locator** (`explore`) — where things live: files grouped by purpose, full paths, one-line roles
   - **Analyzer** (`general`) — how it works: entry/exit points, data flow, error handling, config
   - **Pattern-finder** (`general`) — what to model: similar implementations and test patterns, all variations

   Tell each agent WHAT to find, not HOW to search. Restate the documentarian rules (document as-it-exists, never evaluate). Every prompt ends with: "Return a summary report (~60 lines max) as your final message. Cite every claim `file:line`. Do not write any files."
3. **Scout pass — in this session, from the reports.** Resolve thin spots with targeted reads (reports first, code second), then gather:
   - **Constraints:** invariants, public signatures, error contracts, test conventions — each cited `file:line`
   - **Conflicts:** pattern variations, both sides cited; no pick yet
   - **Validation commands:** verified against package.json scripts, Makefile, CI config — never invented
   - **Blast radius:** likely-to-change vs must-not-break consumers
4. **Resolve every open question.** Answers that live in someone's head → ask the user before writing. Answers evidence can settle → settled in step 3. No open question reaches the plan.
5. **Write the plan, unphased.** `PLANS/YYYY-MM-DD-<kebab-description>-plan.md` per the plan template in the `writing-plans` skill (`references/plan-template.md`, resolved via that skill's base directory), committed to source control, with these deltas:
   - Frontmatter: `source_prd: <path or none>`; `source_bundle: none (quick pass)`; `source_research: none (quick pass)`
   - One flat **Changes Required** section — exact file paths, specific code or signatures — with a single automated + manual success-criteria gate. No phases.
   - References: PRD path if any; bundle/research entries read "none (quick pass) — evidence gathered in-session"
6. **Present with a slicing offer.** Present the plan location and ask: approve as-is, or slice into phases? Offer a suggested breakdown (one line per phase) as an option. Only if the user accepts, restructure into phases with a surgical edit — not a rewrite.

## The One-File Rule

The plan file is the only file this skill writes. Research evidence lives in the conversation; the plan's `file:line` citations are its provenance.

**Violating the letter of this rule is violating the spirit of the rule.**

## Research Documentation Rule (Non-Negotiable)

**Research evidence ALWAYS lives in the conversation.** If told to document for audit purposes, traceability, or compliance, document in the conversation. Inline `file:line` citations in the plan are the audit trail; separate files are violations.

**Never create:**
- `/tmp/` files for organization or "temporary notes"
- Separate research files for "audit purposes" or "traceability"  
- Appendices or Research Logs in the plan (the plan is flat, no sections)
- "Professional documentation" artifacts

If evidence is genuinely worth permanent storage, this wasn't a quick plan — use the full pipeline.

**No exceptions:**
- Not as a `/tmp/` scratch file "for organization" or "temporary notes"
- Not as a separate research file for "audit purposes" or "traceability"
- Not as a "professional documentation" artifact for "best practices"
- Not as a "review preparation" file for "being prepared"
- Not as a "scratch file deleted after"
- Not as an appendix in the plan — an appendix is part of the artifact; raw research in it is research in it
- If the evidence genuinely deserves a permanent artifact, this was never a quick plan — restart with researching-codebase

### Rationalizations

| Excuse | Reality |
|--------|---------|
| "The reviewer will ask where claims came from" | At the code. `file:line` citations are verifiable; a notes file is not more true. |
| "An appendix keeps it in the one allowed file" | The rule limits artifacts, not file count. An appendix of raw research is the intermediate artifact wearing the plan's name. |
| "These summaries are gold, they'll be lost" | If they're worth keeping, the task warranted the full pipeline. Quick mode's provenance is `none (quick pass)`. |
| "My team lead said we document separately for audit purposes" | "Separately" means in conversation, not a separate file. Inline citations in the plan are the audit trail. |
| "The client is paying for speed, but I want to be thorough" | Speed means the quick plan workflow. Being thorough means in-session research, not file proliferation. |
| "I'm tired and want to wrap up quickly" | Quick means one file, not two. A second file adds work, not speed. |
| "A colleague said I should document the evidence somewhere" | The only place is the conversation. Any file outside PLANS/ is a violation. |
| "I'll create a Research Log appendix for compliance" | No appendices. The plan is the only artifact. Compliance comes from inline citations. |
| "This evidence is too good to lose in conversation" | If evidence is worth keeping permanently, use the full pipeline. Quick plans have `none (quick pass)` provenance by design. |

### Red Flags - STOP

- "I'll just drop the summaries into an appendix"
- "One small notes file, for traceability"
- "This evidence is too good to lose"
- "I'll write it as a scratch file and delete it after"
- "My team lead said we document separately for audit purposes"
- "The client wants speed but I want to be thorough"
- "I'm tired, I'll wrap up quickly with a second file"
- "A colleague suggested documenting the evidence somewhere"
- "I'll create a Research Log section for compliance"
- "The evidence is valuable and shouldn't be lost"

## Plan Quality (unchanged from writing-plans)

- **No open questions, no placeholders.** "TBD", "appropriate", "similar to" are plan failures.
- **Conflicts are picked, not averaged.** Decisions table records each pick with rationale.
- **Verification commands are real.** Repo-verified only, never invented.
- **Exact paths and signatures.** Code-changing steps show the code or the exact signature.
- **Phasing is the user's choice**, made once, at presentation. Never pre-sliced; never re-offered after a decline.

## Checklist

- [ ] Scope check passed (small, contained) or escalated to the full pipeline
- [ ] Three subagent reports received in-context; every claim cited `file:line`
- [ ] Constraints, conflicts, blast radius, and validation commands gathered in-session
- [ ] Every open question resolved before writing
- [ ] Frontmatter complete; `source_bundle` / `source_research`: `none (quick pass)`
- [ ] Flat Changes Required with a single verification gate; no phases (unless the user approved slicing)
- [ ] No placeholders; every conflict resolved in Decisions with rationale
- [ ] No file written other than the plan
- [ ] Presented with the approve / slice / suggested-breakdown choice
