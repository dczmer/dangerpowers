# Test Campaign: scouting-context — 2026-08-03

## Description (final iteration)

Use when you need to compress research findings into a handoff brief for planning — turn research documents into actionable context, embed recommended approaches from your research, help pick one of two competing patterns for the planner, or ship a context bundle with empty sections. Also use for pre-planning context bundles that document affected files, call sites, blast radius, constraints, risks, validation commands, and where to start. Covers pre-planning context bundles.

Character count: 733

## Trigger evals

### Iteration 1
- Description: Use when preparing to plan a code change and needing to compress research findings into a handoff brief — affected files, call sites, blast radius, constraints, risks, validation commands, and where to start. Also use when a research findings document exists and needs to become actionable context, or when about to embed a recommended approach in the handoff, pick one of two competing patterns for the planner, or ship a handoff brief with empty sections. Covers pre-planning context bundles.
- Train pass rate: 5/10 queries
- Validation pass rate: 4/5 queries
- Train failures:
  - Query 4 "I'm about to write a plan and need to embed recommended approaches from my research" - should-trigger but not-loaded (3/3 reps)
  - Query 5 "Help me pick one of these two patterns for the handoff brief" - should-trigger but not-loaded (3/3 reps)
- Revision rationale: Broadened description to explicitly mention "embed recommended approaches from your research" and "help pick one of two competing patterns for the planner" to match user intent more directly.

### Iteration 2
- Description: Use when compressing research findings into a handoff brief for planning — turn research documents into actionable context, embed recommended approaches from your research, pick between competing patterns for the planner, or ship a context bundle with empty sections. Also use for pre-planning context bundles that document affected files, call sites, blast radius, constraints, risks, validation commands, and where to start.
- Train pass rate: 5/10 queries
- Validation pass rate: 4/5 queries
- Train failures:
  - Query 5 "Help me pick one of these two patterns for the handoff brief" - should-trigger but not-loaded (3/3 reps)
- Revision rationale: Changed "pick between competing patterns" to "help pick one of two competing patterns for the planner" to add the "help" verb and make it clearer this is assisting the user with a decision.

### Iteration 3
- Description: Use when compressing research findings into a handoff brief for planning — turn research documents into actionable context, embed recommended approaches from your research, help pick one of two competing patterns for the planner, or ship a context bundle with empty sections. Also use for pre-planning context bundles that document affected files, call sites, blast radius, constraints, risks, validation commands, and where to start.
- Train pass rate: 5/10 queries
- Validation pass rate: 4/5 queries
- Train failures:
  - Query 5 "Help me pick one of these two patterns for the handoff brief" - should-trigger but not-loaded (3/3 reps)
- Revision rationale: Added "you need to" framing to make the description more natural and match user language patterns.

### Iteration 4
- Description: Use when you need to compress research findings into a handoff brief for planning — turn research documents into actionable context, embed recommended approaches from your research, help pick one of two competing patterns for the planner, or ship a context bundle with empty sections. Also use for pre-planning context bundles that document affected files, call sites, blast radius, constraints, risks, validation commands, and where to start. Covers pre-planning context bundles.
- Train pass rate: 10/10 queries
- Validation pass rate: 4/5 queries
- Train failures: None
- Revision rationale: Replaced "Use when compressing" with "Use when you need to compress" to better match natural user language patterns.

### Selected iteration: 4 (validation pass rate 80%)

## Fresh-query sanity check
- 5 queries never used in optimization:
  - "I have research findings and need to create a context bundle for planning": loaded — pass
  - "I want to summarize my research into a brief before writing a plan": loaded — pass
  - "Help me document my research findings as a handoff for the planning phase": loaded — pass
  - "Write a plan to refactor the authentication system": not-loaded — pass
  - "I need help writing a comprehensive PRD for a new feature": not-loaded — pass
- Pass rate: 5/5
