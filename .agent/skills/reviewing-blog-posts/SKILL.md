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

1. **Fact-check.**
   - Verify every claim using web search and other documents in the repository. A claim that matches the repository's documents can still be wrong — externally verifiable claims also need an external source.
   - Cite a source for each important claim.
   - List every source in a "References" section at the bottom of the post, and link each citation to it.
2. **Fix spelling and grammar.** Edit the post in place. This is the only audit category applied directly; everything else goes in the report.
3. **Audit structure and ambiguity.** Flag structural problems and statements with ambiguous subjects or referents.
4. **Propose illustrations and analogies** to explain complex concepts.
5. **Propose examples** for important concepts. Each example proposal is a 'Bad / Good / Why' block: the bad version, the good version beside it, and a one-sentence caption under each naming why it fails or works.
6. **Propose a call-out quote for the start of every section.** The report has one 'Call-out quote' item per section of the post — no section skipped — each holding a one-sentence quote (paraphrase allowed) that distills that section's central thesis.
7. **Audit repetition.** Repetition is acceptable only when all of these hold:
   - the concept is important enough to drill into the reader
   - it is relevant in each section where it appears
   - it is worded differently enough each time that it does not feel repetitive

   Evaluate every occurrence of a repeated concept against all three criteria separately. Flag any repetition failing one of these.
8. **Resolve `> EDITOR:` lines.** Any line starting with `> EDITOR:` is a direct request from the author. Resolve each one and remove or rewrite the marker line as appropriate.
9. **Audit markdown formatting.** Flag any link not written as `[label](url)` — malformed link markup renders as raw text or a dead element in HTML. Flag any multi-line code block with lines longer than 80 characters — code blocks are not word-wrapped when rendered to HTML, so a long line forces an annoying horizontal scrollbar. The 80-character limit applies to code blocks only, not to blockquotes or other preformatted elements.

## Audit report

Write a detailed report to the user covering steps 3-9 (and the fact-check findings from step 1). Follow these rules:

- The audit report's skeleton is numbered sections with lettered items: `1. <category>` -> `1.a <one finding>`, `1.b <one finding>`, `2. <category>` -> `2.a <one finding>`. Every finding is exactly one lettered item. Findings never appear as bare bullets or prose paragraphs.
- Include an example or concrete suggestion for each proposed fix.
- Reference locations by describing them or quoting a snippet of the surrounding text. Never use line numbers — they go stale after every round of edits.
- Report how each `> EDITOR:` directive was resolved — a resolution the author can't see is indistinguishable from one that never happened.

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
- [ ] Every link verified to use `[label](url)` format
- [ ] Every multi-line code block checked for lines over 80 characters
