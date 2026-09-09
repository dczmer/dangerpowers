# Iron Rules in Skills: What They Are, Why They Exist, and Where They Come From

> **Disclaimer: AI-generated research**
>
> This document was researched and written by an AI coding assistant on
> 2026-09-09. It is based on fetches of public web sources (GitHub files,
> search engine results, blogs, skill marketplaces) and a `git log -S`
> history analysis of a local clone of `obra/superpowers`. Claims about
> provenance ("X predates Y", "Z coined this") are inferred from those
> sources and may be incomplete or wrong. Verify against the linked primary
> sources before citing or relying on this document.

## What an iron rule is

In superpowers' `writing-skills` skill, the section is titled "The Iron Law
(Same as TDD)":

> ```
> NO SKILL WITHOUT A FAILING TEST FIRST
> ```
>
> This applies to NEW skills AND EDITS to existing skills. Write skill before
> testing? Delete it. Start over.

An iron rule is a rhetorical device for skill documents: one absolute,
non-negotiable rule, stated as a single sentence (usually in a code block,
often near-all-caps), followed by an explicit enumeration of forbidden
loopholes ("No exceptions: not for 'simple additions', not for 'just adding a
section'… Delete means delete"). It never stands alone — it's the anchor of a
toolkit that the same file describes under "Bulletproofing Skills Against
Rationalization":

1. **Iron rule** — the absolute rule itself
2. **Rationalization table** — verbatim excuses observed in testing, each
   with a rebuttal
3. **Red Flags list** — thought patterns that signal a violation in progress
   ("STOP and Start Over")
4. **Spirit-vs-letter clause** — "Violating the letter of the rules is
   violating the spirit of the rules"

## Why it's needed

It targets a specific, empirically observed failure mode: **an agent that
knows the rule but skips it under pressure** (time pressure, sunk cost,
exhaustion). Soft guidance like "prefer to test first" gets negotiated
away — the agent rationalizes ("it's just a docs update", "I'll test
after"). The writing-skills skill itself frames its whole methodology as TDD
applied to documentation: you run baseline "pressure scenarios" with
subagents *without* the skill, record their exact rationalizations verbatim,
and then write the skill to close those specific loopholes. The iron rule is
the hardened output of that loop.

## How it works

Mechanically, it's **just prompt text** — there's no enforcement. It works
by:

- **Absolute phrasing** with no qualifiers, leaving no interpretive wiggle
  room
- **Explicitly foreclosing workarounds** the author has watched agents try
  ("don't keep it as reference", "don't adapt it")
- **Pre-butting excuses** via the rationalization table, so the agent's own
  likely reasoning appears in-context already refuted
- **Blocking technicality arguments** via the spirit-vs-letter clause

Two important caveats the ecosystem itself has documented:

- The skill's own "Match the Form to the Failure" section warns that
  prohibition-style rules **backfire for shape problems** (wrong output
  format) — they only work for discipline violations.
- It's not actually enforceable. As one comparison of Claude Code frameworks
  put it: "The 'iron law' is not enforceable at the framework level; it is a
  strong instruction that the agent occasionally ignores… Iron, as it turns
  out, bends." The building-agentskills docs make the same point: "Every Iron
  Law begs a mechanism question" — it's decoration unless a hook or CI check
  actually fires.

## Provenance: invented by superpowers, or not?

**The generic term is old; this specific usage traces to superpowers.** The
lineage:

- **Generic English**: "iron law" is a long-standing idiom (iron law of
  wages, Michels' iron law of oligarchy, 1911). "Iron Rule" famously appears
  as Saul Alinsky's iron rule of community organizing: "Never do for others
  what they can do for themselves." Neither is AI-related.
- **Content ancestor**: the TDD iron rule's substance is Robert C. Martin's
  **"Three Laws of TDD"** (The Cycles of TDD, ~2005; Clean Code ch. 9, 2008),
  law #1 being "You may not write production code until you have written a
  failing unit test" — derivative works like kouko-monkey/tdd-iron-law cite
  exactly this.
- **The device itself** (a labeled "Iron Law" section in an agent skill, with
  the exact sentence `NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST`, the
  no-exceptions enumeration, and the surrounding anti-rationalization
  toolkit): `git log -S` on a clone shows it's present in **superpowers'
  very first public commit** (`dd013f6`, 2025-10-09, Jesse Vincent), across
  four skills at once (test-driven-development, systematic-debugging,
  verification-before-completion, creating-skills — now renamed
  writing-skills).
- **Everything else found is downstream of superpowers**:
  toolboxmd/building-agentskills explicitly calls these "the patterns
  superpowers added on top of the agent-skills spec";
  jeffallan/claude-skills, ArcForge wiki, LobeHub, and DeepWiki all quote
  superpowers' exact wording.
- **Anthropic's official guidance doesn't use it**: the vendored
  `anthropic-best-practices.md` in the same directory of the superpowers repo
  contains zero occurrences of "iron".

**Bottom line**: the *phrase* is borrowed from general English, the *TDD
content* descends from Uncle Bob's Three Laws, but the *"iron rule/iron law"
as a named skill-authoring pattern* — an absolute one-sentence prohibition
packaged with rationalization tables and red-flag lists — is a superpowers
invention (Oct 2025) that has since spread through the agent-skills ecosystem
by imitation.

## Sources

- https://github.com/obra/superpowers/blob/main/skills/writing-skills/SKILL.md
- https://github.com/obra/superpowers/blob/main/skills/test-driven-development/SKILL.md
- https://github.com/toolboxmd/building-agentskills/blob/main/docs/05-authoring/iron-laws.md
- https://github.com/jeffallan/claude-skills/blob/main/skills/test-master/references/tdd-iron-laws.md
- https://lobehub.com/skills/kouko-monkey-skills-tdd-iron-law
- https://wiki.gregho.dev/ArcForge/ArcForge-TDD-Iron-Law
- https://deepwiki.com/obra/superpowers/7.5-test-driven-development
- https://www.everydev.ai/p/blog-five-claude-code-frameworks-compared-when-to-use-each-when-to-use-none
- https://www.alinskynow.com/craft.html
- Robert C. Martin, *Clean Code* (2008), ch. 9 — "The Three Laws of TDD"
