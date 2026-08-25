# Writing Skills That Agents Actually Use

Notes from reading the Anthropic skill-authoring docs and comparing them against what we've hit building our own skills. Needs another editing pass. I want to talk through the eval part with the team before we commit to a convention, because that's the part I think we'll skip and then regret.

Sources:

* Skill authoring best practices: [https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)
* Equipping agents for the real world with Agent Skills: [https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)

# TLDR

A skill is a directory with a SKILL.md in it. The frontmatter has a `name` and a `description`, and those two fields are the only part that gets pre-loaded into the system prompt at startup. Everything else is read on demand. So the description is not documentation, it's the router. If it's vague, the skill never fires and you spend an afternoon debugging a prompt when the actual bug is one line of yaml.

The rest of it comes down to four things:

* Be concise, because the context window is shared with everything else the agent needs to know.
* Match how specific your instructions are to how easy the task is to get wrong.
* Split content out into files that only get read when they're needed.
* Build the evals first, before you write the doc.

# Progressive disclosure

Three levels, and it's worth knowing which level your content lands on:

1. Frontmatter `name` and `description`. Always loaded. Costs you tokens on every single request, whether or not the skill is relevant.
2. The SKILL.md body. Loaded once the model decides the skill applies.
3. Bundled files and scripts. Read only when something in SKILL.md points at them.

The useful consequence is that a reference file costs nothing until it's opened. You can bundle a complete API reference, a big pile of examples, a whole dataset, and pay zero context for it right up until the moment it's actually needed. Scripts are even better, because running one only costs you its output and not its source.

Two constraints on how you split things up:

* Keep references one level deep from SKILL.md. If SKILL.md points at advanced.md and advanced.md points at details.md, the model may only partially read the second hop (`head -100` it and move on) and you get truncated instructions with no error anywhere.
* If a reference file is over 100 lines, put a table of contents at the top, so a partial read still shows the full scope of what's in there.

The stated limit for the body is 500 lines. That's a performance guideline, not a hard cap, but it's a reasonable smell test: if you're past it, you've probably got two skills or a reference file you haven't extracted yet.

# Conciseness, and the assumption you should be making

The docs are blunt about this one, and I think it's the thing people get wrong most often. The default assumption is that the model is already smart. So the only thing worth writing down is context it doesn't have: your table names, your conventions, the rule about always excluding test accounts, the reason the deploy script takes that specific flag.

Their example of the failure mode is a skill that opens by explaining what a PDF is before getting to the actual code. Every paragraph has to justify its token cost. "Does the model really need this" is a question you should be asking about each section, not about the doc as a whole.

Related: don't offer four libraries and let the agent pick. Give it the default, then give it the one escape hatch that actually matters ("for scanned PDFs needing OCR, use this instead"). Options are a cost, not a courtesy.

# Degrees of freedom

This is the framing I liked most out of the whole doc. You pick how prescriptive to be based on how fragile the task is:

* High freedom, plain prose instructions. Many valid approaches, the right one depends on context. Code review is the example.
* Medium freedom, pseudocode or a parameterized script. There's a preferred pattern but variation is fine.
* Low freedom, an exact command with no room to improvise. Fragile, error-prone, order matters. Database migrations.

The analogy is a robot on a path. Open field, give it a direction and get out of the way. Narrow bridge with a cliff on both sides, give it exact steps and tell it not to add flags.

This lines up with something we already believe, which is that you should prefer deterministic scripts and commands over inference, and use inference only where you actually need judgment. The docs make the same point from the other direction: a pre-made script is more reliable than generated code, it saves tokens, it saves time, and it's consistent across runs. Even when the model could obviously write the script itself, shipping the script is the better call.

One thing to be explicit about, and we've been sloppy here: say whether a bundled file is meant to be executed or read. "Run `analyze_form.py` to extract the fields" and "see `analyze_form.py` for the extraction algorithm" are different instructions and the model will guess wrong if you don't pick one.

# Feedback loops and verifiable intermediates

The pattern is: run the validator, fix what it reports, run it again, and only move on when it passes. It works with a script as the validator and it works with a style guide as the validator, where the "check" is the model reading the guide and comparing.

The stronger version is plan-validate-execute. For anything batch or destructive, have the agent write its plan out to a structured file first, run a script against the plan, and only then apply it. You catch the bad field name before you've touched 50 records instead of after, the check is machine-verifiable instead of a judgment call, and the agent can iterate on the plan without touching the original.

If you write those validators, make the error messages loud and specific. "Field 'signature_date' not found. Available fields: customer_name, order_total, signature_date_signed" is repairable. "Validation failed" is not.

This is also the honest answer to the rules-are-suggestions problem. Instructions in a prompt are suggestions, and a model under pressure is pretty good at talking itself into a reason your rule doesn't apply this time. A validator that exits non-zero is not a suggestion. If a constraint matters, encode it in something that can fail.

# Build the evals first

Recommended order, and it's inverted from how everyone actually does it:

1. Run the agent on real representative tasks with no skill at all. Write down where it failed.
2. Build three scenarios that test those specific failures.
3. Measure the baseline without the skill.
4. Write the minimum instructions that fix the observed gaps.
5. Run the evals, compare to baseline, iterate.

The point is that you end up solving problems you actually observed instead of ones you imagined. There's no built-in runner for these, so you write your own harness. Their example eval is just a json blob with the skill list, the query, the input files, and a few sentences of expected behavior.

The iteration loop they describe is worth stealing: use one session to author and refine the skill, and a separate fresh session to actually use it on real work. Watch the second one. If it reads files in an order you didn't expect, your structure isn't as obvious as you thought. If it never opens a bundled file, either the file is dead weight or SKILL.md doesn't signal it well enough. If it keeps re-reading the same reference, that content probably belongs in the body. Then take the specific observation back to the authoring session, rather than guessing at a rewrite.

Also: test on every model you plan to run it on. Something that's perfectly clear to Opus can be underspecified for Haiku, and something tuned for Haiku can be over-explained to the point of wasting Opus's context.

# Smaller things worth knowing

* Naming. Gerund form (`processing-pdfs`, `analyzing-spreadsheets`). Lowercase, numbers, hyphens, 64 chars. No `helper` or `utils` or `tools`. "anthropic" and "claude" are reserved words and will be rejected.
* Descriptions get written in third person, always. "Processes Excel files and generates reports", not "I can help you with". The field gets injected into the system prompt and mixing point of view causes discovery problems. Include both what it does and when to use it, with the trigger words a user would actually type.
* Forward slashes in paths, even on Windows.
* No dates or "before August 2025" conditionals in the body. If you need the old behavior documented, put it in a collapsed "old patterns" section.
* Pick one term per concept and use it everywhere. Don't rotate between field, box, element, and control.
* MCP tools need the fully qualified `ServerName:tool_name`. Without the prefix it may not resolve, which gets worse the more servers are connected.
* No magic numbers in bundled scripts. If you can't justify why the timeout is 47, the agent has no way to work out what it should be either.
* Scripts should handle their own error cases instead of failing and leaving the agent to figure it out.

# Questions and concerns

* The three-eval recommendation is a floor, not a number anybody validated. I'd want to know what our own pass rate looks like at three versus ten before we make it a convention.
* No eval runner ships with any of this. Do we build one small harness that every skill in the repo uses, or does each skill own its own tests? I lean toward one harness, but that only works if the expected-behavior rubrics are written consistently.
* The 500-line guideline has no stated failure mode. Is it retrieval quality, is it cost, is it attention? Would change how hard we push back in review on a skill at 600.
* TODO: figure out where our own skills sit on the freedom spectrum right now. My guess is most of them are high-freedom prose where they should be low-freedom scripts, which is exactly the direction that produces the rules-as-suggestions failure.
* TODO: nothing here covers what happens when two skills both match a request. Description-based routing across a hundred skills seems like it has to degrade at some point and I couldn't find a doc that addresses it.
