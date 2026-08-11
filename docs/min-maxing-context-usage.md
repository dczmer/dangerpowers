# More Min-Maxing Context Usage

In this document, I'm mainly concerned with context window management, not reducing total overall costs. However, the same techniques you use to manage your context window should also reduce your overall token burn. I've also included a section at the end about some alternative providers and open-weight models to consider.

Claude Code has a rather large system prompt and every skill, MCP, and plugin that you install gets added to that. It's likely that you are starting each session at 10% usage, which is a lot if we intend to keep usage below that 40-60% range.

Use `/context` to see your current context window and what is using space.

## Context Usage in Status Bar

Configure your agent to show the current context usage in the status bar, so you can keep track of how your context window is filling up.

It's very easy to configure Claude `statusline`: https://code.claude.com/docs/en/statusline

Not only will this help you gauge how many tokens your operations are actually using, it also helps you stay out of the "dumb zone" (>40% context usage).

## Advice from Anthropic

Anthropic has some good advice: https://code.claude.com/docs/en/costs#reduce-token-usage

I've included most of the tips from that document, along with some other suggestions, in the sections below.

## Regular (Intentional) Compaction

Compaction is a process where the agent will generate a summary of the current conversation, hopefully excluding irrelevant "noise" like command output, then start a new session and load that summary before continuing. This should result in you keeping your place, while clearing all that junk content out of the context window.

You can compact your conversation at any time using `/compact`.

### Custom Compaction Prompts

If you want to give specific instructions, to make very sure the summary includes certain points, you can also provide a prompt:

`/compact and remember the current test errors`

This is useful because compaction/summarization is a "lossy" compression operation: you lose details every time you do it.

You can also make a custom prompt to generate a summary file on disk, then use `/new` to start a new session and have it read the summary file. This gives you a lot more control over the contents of the summary, but `/compact` already does a decent job.

### Auto-Compaction

When the context window fills to a certain size (configurable), Claude will automatically run `/compact` and keep going.

This often happens at a bad time though, and the default threshold is something like 85% of the context window, which is way beyond the recommended working size of <60%.

You can configure Claude to auto-compact at 60%, but a better approach is to use "Intentional Compaction."

### Intentional Compaction

This is a very simple concept: When your context window gets to around 40% usage, start looking for an opportunity to compact (intentionally).

That's it.

A typical working session might look like:

1. Gather context about the current problem and target code/systems you are working with.
2. Generate an implementation plan, and refine it interactively.
3. Execute the implementation plan.
4. Review and refine the results.

You can compact between each item, keeping the same conversation in memory and reducing your context window usage so it stays relatively low throughout.

Some of these steps might take a _lot_ of context on their own, but we'll see later how to use subagents or other tools to manage this as well.

For large steps, like the execution phase, try asking the agent to "make a multi-phase plan" and ask it to use its internal `todo` tool to keep track of the phases as you go. This gives you more breakpoints where you can compact between steps in the execution plan.

## Choose the Right Model

Opus is really powerful. In fact, it's far more than what you need for most day-to-day work. But to use a smaller model effectively, you have to break it into small tasks and/or create an execution plan and gather all of the working context yourself. Opus can guess at what you are trying to do and gather potential context information on it's own. This makes Opus a crutch for those who don't actually plan and design the context data for their tasks, but also makes it a token-hog because it will eagerly try to gather context information on it's own (and often get it wrong).

A rather surprising note though: Sometimes doing a simple task with Opus is _cheaper_ than doing it with Sonnet! But this isn't something I'd count on. Opus noticeably accumulates more cost during a typical session than Sonnet. Like everything related to AI, it's really cool when it works but it's too inconsistent to reliably count on.

A good rule is to start with Sonnet and then move to Opus when you need to work on something much more complicated or when Sonnet just can't seem to get the job done.

- **Opus**: Architectural work, multi-project work, deep researching and highly complex tasks.
- **Sonnet**: Day-to-day workhorse for most coding tasks. Focus on giving it the right context, don't rely on it to figure things out based on it's training data.
- **Haiku**: Cheap and quick model for simple tasks like summarization, code reviews.

Outside of work, you might be interested in cheaper open-weight models. Here are some that I have worked with:

- **GLM5 and GLM5.1**: These are your Opus replacement. However, z.ai has had some performance and capacity issues recently.
- **Kimi K2.5**: This is what I use 90% of the time on personal projects and research. I use it in place of Sonnet. It's really fast and good at coding tasks. Same caveats apply as when using Sonnet: you have to be explicit, it won't try to guess and collect context for you.
- **Minimax 2.5 and 2.7**: Solid and very fast (and very cheap) Haiku replacement.
- **Qwen3.5, Qwen-coder** are very popular but I've only used them with local Ollama models and my computer doesn't have enough GPU/memory to do it justice.
- Google just released **Gemma 4** but I haven't tried it yet. It's an open-weight model you can run locally or from a provider that specializes in open models.

## Reduce MCP Overhead

Plugins and MCPs require space in your context window. Use `/context` when you start a new session to see how much space they are taking up.

### Use CLI Tools Over MCP

Part of the reason MCP uses so much context space is that the MCP protocol describes all of the server's resources and tools with a JSON schema, and Claude has to load that entire schema into context before it can be used.

#### Example: Playwright MCP vs. Playwright CLI

Playwright MCP works by launching a browser and a system similar to Selenium to control the browser programatically. It can click buttons and interact with rich JavaScript UI components and simulate a user session. This is really useful for verifying your work when developing new UI components. These browsers stay open between calls so you can make additional requests and pick up from where the last request left off.

Playwright CLI works similarly, but it doesn't require you to load an MCP schema into your context. It makes the request from a command line interface and returns just the result: a screenshot of a component, the text content of a page, etc. This gives you a smaller, focused response than the MCP, which includes the entire page source in the working context when you might not need it.

https://github.com/microsoft/playwright-cli

Consider using Playwright CLI and leaving Playwright MCP disabled. When you need to debug or develop a complex UI component, switch to the MCP to provide more context that the agent can use for debugging.

### Disable MCP Servers

If you don't need an MCP for your current session, disable it and start a new session so it's not using any of your initial context window to hold the MCP schema and descriptions.

Use `/mcp` and then navigate to the MCP server(s) you want to disable. Re-enable them when you actually need them.

### Scope MCP Servers to Specific Subagents

This is more advanced, but you can create custom 'agents' for specific tasks and you can configure what MCPs they should have access to: https://code.claude.com/docs/en/sub-agents

So Anthropic recommends you can disable MCPs in your main session and have specific subagents that need the MCPs configured to use them.

## CodeIntelligence (LSP) Plugins for Typed Languages

When you run the OpenCode agent, it will automatically use the available LSP servers in your current environment instead of using Grep and Read to read data into context to understand the code structure. With the LSP interface it can, for example, query `pyright` for information about a Python function or variable without using context in your main conversation.

For Claude Code, you have to manually install a plugin for every LSP from their official plugin marketplace: https://code.claude.com/docs/en/discover-plugins#code-intelligence

## Use Hooks to Offload Processing and Filter Output

https://code.claude.com/docs/en/hooks

Example: Instead of telling Claude to "run unit tests and make a commit," you can use a hook that fires before `git commit` and runs the tests automatically. Since you can control this command, you can also filter the output before returning results to the agent (so it's deterministic and doesn't use tokens).

## Move Instructions from CLAUDE.md to Subdirectories or Extract to Skills (Progressive Disclosure)

Whenever you start a new session, Claude loads the entire contents of the CLAUDE.md (or AGENTS.md) files into context. This includes the top-level CLAUDE.md file in the project root folder, as long as all of the various different places you can add custom context files (`~/.claude/CLAUDE.md`, `~/CLAUDE.md`).

On a complex project, this can contain a lot of context. As you work, you find things to add to the context file and it gets even bigger. Eventually, your CLAUDE.md files are using up too much of your context window before you even begin your session.

Use "Progressive Disclosure" to separate your context into sub-modules:

- The main CLAUDE.md file(s) contain only the critical context that an agent almost always needs to use.
- For specific tasks, issues, and other context, you can link additional context files from CLAUDE.md: `when you see error X, load fix_error_ex.md`. Then these additional files will only load when these specific conditions occur.
- For project/sub-folder specific context, you can create a `CLAUDE.md` file under a subdirectory. The context from that folder will only be loaded when we're working in that directory.

Here is a good blog post about writing an effective CLAUDE.md file: https://www.humanlayer.dev/blog/writing-a-good-claude-md

But even after all of this, on a large project, your context usage will continue to grow along with the project.

Skills are a specific system of Progressive Disclosure: context that is loaded on-demand, when you request to use that skill or when your prompt includes a "trigger" phrase that is associated with that skill.

But once you load the skill, it's part of your context window, so your session will still accumulate more and more context as you load skills.

To manage context bloat from skills:

- Run skill tasks in subagents to keep them isolated from your main session context window.
- Use even more progressive disclosure when designing your skills:
  - The main SKILL.md should only cover the "happy path" of the process.
  - Error handling, corner-cases, and other concerns can be extracted into "reference" files that can be included when those situations are encountered.
- Use skill scripts:
  - Instead of explaining how to do a task in markdown for the agent, if there are steps that can be done easily with a script, just have the skill call a script instead.
  - If you see the agent doing the same large commands repeatedly, tell it to save the command as a script and have the skill use that in the future.

## Write Specific/Descriptive Prompts

A vague prompt with no clear instructions causes Claude to try to dig for information by reading files and loading more and more data into your context window. Instead, tell it exactly what you want, were to find the info it needs, and how to execute important commands. This should result in a more focused and smaller context and improve performance.

Writing a good prompt means being very specific, which leads to techniques like "spec-driven development," where you use the AI to help you write a detailed plan before executing it. Checkout https://github.com/obra/superpowers for one implementation.

## Use AI to Write Deterministic Code

Write scripts and deterministic code that the agent can use in the future, reducing the amount of context required but also eliminating the unpredictability of using inference for things that can be done without AI.

Instead of writing a skill that uses a multi-step prompt to generate and configure a new page, write a skill that uses scripts to do all of the boilerplate stuff and have the prompt use that. Then the skill can focus on using inference for the parts that are not easy to do with a script.

## Pruning and Filtering Command Output (Context Back-Pressure)

https://www.humanlayer.dev/blog/context-efficient-backpressure

Here is the concept:

When the agent runs CLI commands to test, build, explore, or debug, all of the output of those commands become part of the current conversation and take up space in your context window.

Use a process or wrapper script that filters or summarizes the output to reduce the total number of tokens that need to be loaded into your context window.

### RTK

https://github.com/rtk-ai/rtk

RTK is an off-the-shelf solution that wraps the most commonly used Bash tool calls and filters their output automatically. It doesn't cover every possible command, but it covers a lot of CLI commands that agents make frequently.

Some examples lifted directly from their README file:

```
# ls -la (45 lines, ~800 tokens)        # rtk ls (12 lines, ~150 tokens)
drwxr-xr-x  15 user staff 480 ...       my-project/
-rw-r--r--   1 user staff 1234 ...       +-- src/ (8 files)
...                                      |   +-- main.rs
                                         +-- Cargo.toml
```

```
# git push (15 lines, ~200 tokens)       # rtk git push (1 line, ~10 tokens)
Enumerating objects: 5, done.             ok main
Counting objects: 100% (5/5), done.
Delta compression using up to 8 threads
...
```

```
# cargo test (200+ lines on failure)     # rtk test cargo test (~20 lines)
running 15 tests                          FAILED: 2/15 tests
test utils::test_parse ... ok               test_edge_case: assertion failed
test utils::test_format ... ok              test_overflow: panic at utils.rs:18
...
```

Important note: these filters try to show as much important _error_ information as possible, so that the agent can actually use the results to debug. But if there is no error, then you can usually just return "OK" or something very short.

## Talk Like Caveman

Why use many token when few token do trick?

https://dev.to/jakguzik/i-benchmarked-the-viral-caveman-prompt-to-save-llm-tokens-then-my-6-line-version-beat-it-2o81

This is a viral AI trend. I have not actually used it but it is an extension of some common advice I've been seeing for a while: tell Claude to sacrifice grammar for token efficiency.

## Working Efficiently on Complex Tasks

https://code.claude.com/docs/en/costs#work-efficiently-on-complex-tasks

I'm not going to explain this one too much here, because it's worthy of a separate document covering "harness engineering" and advanced context engineering.

Essentially, you can use subagents to split up complicated tasks and keep context usage isolated between them. Think of how you decompose a problem into functions and modules, and apply a similar process by determining which things can happen in isolation and delegating them to subagents.

## What About Bigger Context Windows?

https://www.humanlayer.dev/blog/long-context-isnt-the-answer

The problem isn't the _size_ of the context window, it's about short and focused context windows producing higher quality results.

The "dumb zone" is correlated with the size of the context window, not the relative percent of the entire window that is filled. So 70K tokens on the 200K model is still the "dumb zone" threshold for the 1M model.

If you follow these suggestions closely then you should not need 1M tokens, except in the most extreme cases.

## Additional Providers and Open-Weight Models

Anthropic and OpenAI are not the only game in town. The rise of low cost, open-weight models from Chinese companies (and now Google) provide an alternate, more affordable solution for personal and professional use.

### OpenCode Zen and OpenCode Go

https://opencode.ai/zen

Zen is metered, pay-as-you-go access to many models. Tokens for commercial models are provided at-cost. This is a great way to get started since you can put $20 on your account and have access to all of the popular frontier models as well as very cheap access to a lot of open-weight models.

They usually have at least one free model, which you can use without even adding a credit card. When companies want to test their new models and get user feedback, they sometimes become available as free models here for a short time. Most recently, I was able to use GLM5 completely free for a few weeks, which was very nice.

https://opencode.ai/go

Go is a $10/mo plan that provides access to 3 of the most popular open-weight models: GLM5, Kimi K2.5, and MiniMax 2.5. There are rolling usage limit windows, but this gives a surprising amount of usage, especially if you stick to Kimi.

If you blow through your limits on Go, you can have it switch to metered tokens from your Zen budget automatically.

At some point you might reach those limits and need more tokens though… And if you are an OpenClaw user then this definitely won't be enough for you.

### GLM (z.ai)

https://z.ai/subscribe

GLM5 and GLM5.1 are highly regarded and often compared to Claude Opus 4.6. A GLM plan gives you something like 30x usage for a 1/5 of the cost of a Claude Pro Max plan.

Well, it used to at least. Since Claude started strictly limiting their Max plans, a lot of people have jumped ship to z.ai. So it's no surprise that the usage limits went down, and the prices went up.

The major issue with this provider seems to be that it can't handle the traffic the model is getting, and the company cannot secure enough compute to properly support it. 429 errors, usage limits, slow service have been plaguing this otherwise great model since launch. You can run them locally though, if you have the hardware.

GLM models are multi-modal: they also support images and vision.

### Kimi

Kimi K2.5 is my personal choice for most tasks. It's fast, it's cheap, and it does a really good job (if you give it the right context).

It's available from many providers and you can run it locally.

The Kimi K2.6 beta was just announced and it sounds like a marked improvement in the next release.

I use it from my OpenCode Go subscription but they have official plans as well: https://kimik2.com/pricing

### MiniMax

I've been using MiniMax as my Haiku replacement, but it looks like the new version, 2.7, is a pretty big advancement that brings multi-modal capabilities.

https://platform.minimax.io/subscribe/token-plan

Supposedly these plans are very fast and have very generous usage limits (at least for now).

### Alibaba

When Alibaba launched it's coding plan, it stated with a $3/mo. plan with access to a lot of open models, including their line of Qwen models. But then the price jumped to $10/mo. a couple of weeks later. Now it's $50/mo.

https://www.alibabacloud.com/help/en/model-studio/coding-plan

It does include a lot more than most offerings though, like their "DeepResearch" tools and more diverse types of special-purpose models.

### Ollama Cloud

https://ollama.com/pricing

Interesting hybrid approach. You run `ollama` locally, but the actual work is outsourced to their own hosted infrastructure on AMD compute units. The pricing is based on hardware usage costs, not on fixed token costs. The quotas are quite generous and you can access a lot of the BIG open-weight models for really cheap.

### Local LLMs

If you have the hardware, you can run your own local LLMs. I've experimented with Ollama and Llama.cpp so far. And checkout https://huggingface.co/models for a public repository of thousands of models you can install.

On a 16GB AMD card, I can comfortably run a simple "quantized" model for simple tasks and even for agentic programming in OpenCode. But at that size, it's not really suited for complex tasks or long running sessions. Still, it's good for reviews, summarization, other simple tasks that I can offload from the main providers. I'm currently using Qwen3.5-9B but I want to checkout Gemma4 soon.

I have an integrated AMD Ryzen CPU and 64GB of DDR4 ram as well. I can run a much bigger model but the performance in quite slow compared to the pure GPU option.

I find that Ollama models often have errors in OpenCode or Claude where they fail to make tool calls and the agent gets stuck. I moved to Llama.cpp and I don't see any of those errors now, and it makes it easier to run a wider variety of models from huggingface.co compared to Ollama.

Configuration tips:

1. Set your context window to an appropriate value. You probably want at least 128K for agentic/coding work. Ollama defaults to 4K which isn't very helpful.
2. Configure the model parameters: `top_n`, `top_k`, `presence_penalty`, `temperature`, etc. You can usually find the suggested configuration to use on the model pages on huggingface.co. These are much easier to configure with Llama.cpp compared to Ollama.
