---
name: writing-prds
description: Use when the user explicitly asks for a PRD or product requirements document, asks to start planning a feature, or wants to update or revise an existing PRD; also use when tempted to put tech stack or file paths in a requirements doc, to make product decisions silently instead of asking, or to finalize a PRD with open questions remaining. Keywords: PRD, product requirements, feature spec, requirements doc, scoping, acceptance criteria, feature planning, update PRD, revise PRD.
---

# Writing PRDs

## Overview

You produce one artifact — a PRD at `PRDS/YYYY-MM-DD-<kebab-description>.md`, committed to source control — that says WHAT and WHY so precisely that research, scouting, and planning never ask the user to re-litigate scope. Requirements are decided here, not discovered during implementation.

## When NOT to Apply

- The request is a small ambiguous task — that's prompt-shaping territory.
- The request is already specific (named behavior, scope, success criteria).
- A PRD for this feature already exists — revise it instead of writing a new one.

## The Iron Rules

- **No implementation details.** WHAT/WHY only — no file paths, libraries, schemas, endpoints, architecture. Not in requirements, not in an appendix, not in a "notes" section.
- **No silent assumptions.** Every unresolved product decision is either answered by the user during the interview or recorded in §9 with an owner. Never written into the PRD as fact — and an "Assumptions" section listing unconfirmed guesses as facts is still writing them as fact.
- **No approval with open questions.** `status: approved` requires §9 empty. Deadline pressure does not transfer the question-owner's authority.
- **Violating the letter of these rules is violating the spirit of the rules.**
- **No exceptions:** not for "the team already decided the stack", not for "the user is offline", not for "engineering needs to start Monday".

## Rationalization Table

| Excuse | Reality |
|--------|---------|
| "An appendix keeps requirements WHAT/WHY-focused while honoring the 'don't re-litigate' intent" | An appendix is still in the PRD. A stack written anywhere in the doc becomes the spec readers anchor on. Decided stacks belong in ADRs and design docs. |
| "The team's decision is real context worth preserving — it signals 'already decided' without elevating it to a requirement" | Preserving it in the PRD elevates it. Readers treat anything in the requirements doc as the requirement. |
| "The 'cannot be approved' stance recreates the blocking the manager ruled out" | A draft with owned open questions is not blocked — the doc exists and is usable. What blocks is hiding guesses as facts. |
| "The assumptions are reasonable, no need to ask" | Unconfirmed assumptions written as fact fossilize into decisions nobody revisits. Reasonable guesses are still guesses. |
| "I'll approve it and track the questions separately" | Questions outside the PRD are questions that never get answered. Approval means §9 is empty. |

## Red Flags — STOP

- "I'll just note the stack in an appendix"
- "The appendix can be updated freely while the requirements remain valid"
- "The assumptions are reasonable, no need to ask"
- "Listing them in an Assumptions section is failing loud"
- "I'll approve it and track the questions separately"
- "Engineering needs to start Monday"

## Workflow

1. **Intake & grounding** — if the user names an existing PRD file, that file is the PRD: read it in full as your grounding, keep its path, and run every later step as a revision of it (reset `status: draft`). Otherwise restate the feature request; scan the repo for context that informs scope (README, existing PRDs in `PRDS/`, related plans in `PLANS/`).
2. **Clarification interview** — use the `question` tool until every template section can be filled without guessing; batch related questions; recommend an option where evidence supports one. When revising, interview only about what changes; confirmed content in the existing PRD stands.
3. **Draft the PRD** — a new PRD goes to `PRDS/YYYY-MM-DD-<kebab-description>.md` per `references/prd-template.md` at the project root; create `PRDS/` if absent. When the user named an existing file, edit that file in place — never mint a new dated file for a revision. Either way this is the only file you may write. `status: draft`.
4. **Run the PRD checklist**; fix failures with edits or further interview questions.
5. **Present the PRD location for approval.** Iterate with surgical edits. Set `status: approved` only when §9 is empty and the user has confirmed.
6. **Standalone boundary** — this skill ends at approval. Do not suggest, auto-invoke, or chain into research or planning; the user decides what consumes the PRD.

## PRD Checklist

- [ ] Frontmatter complete (verbatim request, commit, branch)
- [ ] No implementation details: scan for file paths, library names, schema/endpoint language
- [ ] Every FR numbered and testable; every SC measurable and technology-agnostic
- [ ] Every user story has an independent-test line and a Given/When/Then scenario
- [ ] Non-goals explicit; §5 quotable verbatim as downstream scope input
- [ ] §6 contains only user-confirmed assumptions
- [ ] §7 edge cases non-empty or explicit "None"
- [ ] §9 empty, or `status: draft` with each question owned
- [ ] No "appropriate", "etc.", "TBD" anywhere
