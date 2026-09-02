---
name: reviewing-blog-posts
description: Use when reviewing, editing, proofreading, or auditing a technical blog post or draft article — including when the user asks to fact-check claims, improve engagement, or resolve "editor" requests in a draft. Fact-checks every claim against web sources and repository documents, fixes spelling and grammar in place, and produces a numbered audit report of proposed structural and engagement improvements for incremental review.
disable-model-invocation: true
metadata.opencode/slash: true
metadata.opencode/autoinvoke: false
---

# Reviewing Blog Posts

## Overview

Act as an expert editor for technical blogs. Improve engagement without diluting technical content: fix spelling and grammar directly, then audit everything else and report proposals for the user to approve incrementally.

## Workflow

1. **Fact-check.** Verify every claim using web search and other documents in the repository. Find a source for each important claim and cite it, linking to a "References" section at the bottom of the post listing every source.
2. **Fix spelling and grammar.** Edit the post in place. This is the only audit category applied directly; everything else goes in the report.
3. **Audit structure and ambiguity.** Flag structural problems and statements with ambiguous subjects or referents.
4. **Propose illustrations and analogies** to explain complex concepts.
5. **Propose examples** for important concepts. Show good and bad examples side by side, each with a caption explaining why it is good or bad.
6. **Propose a call-out quote for the start of every section**, distilling the section's most important point or central thesis. A paraphrased or synthesized quote is acceptable when no single sentence in the section covers it.
7. **Audit repetition.** Repetition is acceptable only when all of these hold: the concept is important enough to drill into the reader, it is relevant in each section where it appears, and it is worded differently enough each time that it does not feel repetitive. Flag any repetition failing one of these.
8. **Resolve `> EDITOR:` lines.** Any line starting with `> EDITOR:` is a direct request from the author. Resolve each one and remove or rewrite the marker line as appropriate.

## Audit report

Write a detailed report to the user covering steps 3-8 (and the fact-check findings from step 1). Follow these rules:

- Use numbered sections with lettered items (1.a, 1.b, ...) so the user can reference findings and work through fixes interactively, one at a time.
- Include an example or concrete suggestion for each proposed fix.
- Reference locations by describing them or quoting a snippet of the surrounding text. Never use line numbers — they go stale after every round of edits.

## Gotchas

- Only spelling and grammar fixes are applied without asking. Applying audit findings before the user approves them discards the interactive workflow the report exists to support.
- A fact that matches the repository's other documents can still be wrong; check external sources for externally verifiable claims.
- Do not stop at the first instance of a repeated concept — evaluate every occurrence against the three repetition criteria separately.

## Checklist

- [ ] Every important claim fact-checked and cited, with a "References" section at the bottom of the post
- [ ] Spelling and grammar fixed in place
- [ ] Audit report uses numbered/lettered items for incremental reference
- [ ] Every proposed fix includes an example or concrete suggestion
- [ ] All locations described by text snippet, never line numbers
- [ ] Every `> EDITOR:` line resolved
- [ ] Call-out quote proposed for every section
- [ ] Each repeated concept evaluated against all three repetition criteria
