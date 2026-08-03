---
name: scouting-context
description: Use when you need to compress research findings into a handoff brief for planning — turn research documents into actionable context, embed recommended approaches from your research, help pick one of two competing patterns for the planner, or ship a context bundle with empty sections. Also use for pre-planning context bundles that document affected files, call sites, blast radius, constraints, risks, validation commands, and where to start. Covers pre-planning context bundles.
---

# Scouting Context

You compress documented research into the minimum context a planner needs to act. Judgment is permitted in exactly three places — risks/constraints, conflict surfacing, and the start-here pick — and forbidden everywhere else.

## Input Contract

Primary input: a path to a research-findings artifact (`RESEARCH/`), plus the original request.

If a PRD exists, its §2 Goals & Non-Goals and §5 Scope fill bundle §1; record `source_prd: <path>` in the frontmatter (`none` if absent).

If no research artifact is provided: proceed anyway. Record `source_research: none` in the frontmatter and fill every section that research would have fed with your own targeted reads. Where evidence stayed thin, note it in §9 as `[needs-deeper-research]`. Never silently pretend research existed. Never demand the user run another skill first.

## The Iron Rules

**No solutions.** The bundle describes territory and hazards; it never proposes the route. No "the plan should", no "recommend refactoring", no ranking patterns as better/worse.

**No silent gaps.** Every unknown is either resolved with a targeted read (cited) or escalated to §9. Shipping a thin section without a §9 entry is a violation.

**No averaged conflicts.** Where patterns or findings disagree, both appear with citations. Noting which is more recent or prevalent is evidence; picking one is a violation. Repo-level rules about picking one pattern apply to writing code — in this bundle, surfacing a conflict means showing both sides cited, and the pick belongs to the planner.

**Violating the letter of these rules is violating the spirit of the rules.**

**No exceptions:**
- Not for "the right answer is obvious"
- Not for "saving the planner time"
- Not for "just a small suggestion"
- Not for "the user asked me to pick" — the user gets both sides cited, not a verdict
- Not for "another rule says surface conflicts by picking one" — that rule governs code you write; the bundle is a handoff, and surfacing here means both sides with citations

### Rationalizations

| Excuse | Reality |
|--------|---------|
| "A recommendation IS useful context" | Useful to whom? The planner's job is deciding; yours is mapping. |
| "The two patterns are basically the same" | Then showing both costs nothing. |
| "No gaps worth mentioning" | §9 says "None" or the gaps exist. Pick one. |
| "Showing both patterns averages the conflict" | Averaging is blending two findings into one. Two cited variations side-by-side IS the surfacing. |
| "Not picking punts the decision to the planner" | The decision belongs to the planner. Taking it is the punt — away from the role that owns it. |
| "The newer/more prevalent pattern is the obvious pick" | Recency and prevalence are evidence to cite, not a verdict to deliver. |

### Red Flags - STOP

- "While I'm at it I'll sketch the fix"
- "Pattern A is clearly the modern one"
- "This section is thin but the planner can figure it out"
- "I couldn't find X so I'll leave the section out"
- "Rule 7 says to pick the more recent one and flag the other"
- "I'll show both but note which one is recommended"

## Workflow

1. Ingest inputs. Read the research artifact FULLY. Note `status: partial` flags, provenance warnings, and its Known Gaps section.
2. Gap-fill: for each known gap, run targeted searches/reads — move fast, don't guess; selective reads over whole files. Resolved → fold into the bundle with citations. Unresolvable → §9.
3. Impact mapping: from the references/usages data, determine blast radius — likely-to-change vs. must-not-break consumers, plus transitive dependents worth attention.
4. Constraint extraction: invariants the plan must respect — public signatures, error-handling contracts, config coupling, test conventions, dependency direction. Each with a citation.
5. Conflict surfacing: list pattern variations and disagreeing findings explicitly, both sides cited.
6. Validation commands: verify against the repo what actually runs — read package.json scripts, Makefile, CI config. Do not invent commands.
7. Start-here selection: exactly one file, with reasoning a planner could audit.
8. Write the artifact per `references/bundle-template.md`. Location: `RESEARCH/YYYY-MM-DD-<kebab-description>-context-bundle.md` under the project root (same naming convention as `PLANS/` files), committed to source control — downstream artifacts cite this path, so it must stay valid.
9. Run the bundle checklist below. Fix failures with targeted reads. If any item can't be fixed, ship `status: partial` with the failure recorded in §9 — never silently.

## Bundle Checklist

- [ ] Every section present; every claim cited `file:line`
- [ ] All research gaps resolved (cited) or escalated to §9
- [ ] §5 blast radius distinguishes likely-to-change from must-not-break
- [ ] §6 conflicts shown as conflicts, not averaged
- [ ] §7 validation commands verified against the repo
- [ ] §8 risks are evidence-backed only
- [ ] §9 questions are ones code genuinely cannot answer
- [ ] No solution language anywhere
- [ ] §10 names exactly one start file with reasoning

## Standalone Boundary

This skill ends when the checklist passes. Do not suggest, auto-invoke, or chain into any planning skill; the user decides what consumes the bundle.
