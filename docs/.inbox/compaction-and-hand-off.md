do i need custom compaction or hand-off implementations?

may need custom compaction for custom agents with specific roles or domains, or if you find your harness' default compaction summary is lacking (like losing operational rules, etc). mostly, for general coding sessions, you don't need to worry so much about custom compaction, just when to intentionally compact.

may need hand-off implementations when passing control from one specialized agent to another. or, when you have a very long-running task that has compacted multiple times, it can be beneficial to transfer context to a new agent session and start with a clean slate.

so i think this is interesting, but not so relevant until you get to writing custom harnesses and agents, and long horizon tasks.

https://github.com/humanlayer/humanlayer/blob/main/.claude/commands/create_handoff.md

from google ai:

---

In agentic development, managing an LLM’s limited context window is one of the most critical engineering hurdles. As an agent executes long-running tasks—running loops, calling tools, and processing large error logs—the context window fills up, leading to high API costs, slower response times, and "context rot" (where the model becomes distracted by its own history). [1, 2] 
To solve this, developers use two primary architectural patterns: Custom Compaction Processes (condensing state within a single session) and Context Hand-offs (transferring state across completely fresh sessions). [1, 3] 

## 1. Custom Compaction Processes (In-Session Compression)
Context compaction is the process of dynamically reducing a long conversation transcript and voluminous tool outputs into a smaller, token-efficient working state without breaking the agent’s execution loop. [2, 4] 
While basic compaction simply triggers a generic summary prompt when a token threshold is crossed, a custom compaction process utilizes specialized orchestration logic tailored to the agent's exact domain. [5, 6] 
## Key Techniques in Custom Compaction:

* Anchored & Verifiable Summarization: Instead of allowing a secondary LLM to write a generic narrative summary, custom compaction forces the model to adhere to strict schemas. It retains highly technical data (like specific error codes, exact code diffs, or active variables) while discarding conversational fluff. [6, 7] 
* Tool-Call Offloading: Large tool responses (e.g., a 2,000-line terminal log or a massive JSON payload) drastically pollute context. Custom compaction replaces these in the active conversation history with reference pointers or summaries, saving the heavy payload to a localized file system where the agent can fetch it only if needed. [1, 8] 
* Logical-Boundary Triggers: Standard compaction is reactive (e.g., "compact when context is 80% full"). Custom compaction is proactive and triggers at logical task boundaries (e.g., after a git commit, when a sub-task transitions from "planning" to "testing", or when a specific state machine changes phases). [3, 7] 
* Safety & Governance Preservation: A core danger of lossy compaction is that system prompts, tool permissions, and guardrails can accidentally get compressed out of existence. Custom compaction routines explicitly segregate security-critical instructions so they are never altered during the reduction phase. [4, 9] 
* 

## 2. Context Hand-off Concepts (Cross-Session Transition)
Compaction alone is often not enough for long-horizon or complex workflows. Eventually, the history is too condensed to be useful, or the agent needs to pivot to an entirely different role. This is where a context hand-off occurs: tearing down the current session completely and spinning up a fresh session with zero historical baggage. [1, 3] 
The primary challenge of a hand-off is the "carry mechanism"—the process of passing critical state across a hard context boundary. [3] 
## Core Concepts of Hand-offs:

* 
* The Handoff Contract: Multi-agent frameworks use strict schemas (often enforced via structured outputs) that mandate exactly what fields must be populated before an agent can pass control to another.
* State Checkpointing & External Artifacts: Instead of relying on an LLM's memory, the agent writes its state to an external, human-readable file (like NOTES.md or a structured state JSON). A new agent session reads this file as its starting prompt.
* The "Zero Context" Test: A perfect hand-off must stand entirely on its own. If a fresh agent reading the hand-off file has to guess why a decision was made, it will suffer from relitigation—re-doing tasks or arguing choices that the previous agent already settled. Therefore, hand-offs must carry not just what was done, but the rationale behind it.
* Role/Sub-agent Isolate-and-Fanout: Hand-offs are commonly used to transfer work from a high-level "Planner Agent" to a specific "Implementation Sub-agent", or to fan out a large task into parallel sessions that run simultaneously before merging their states back together. [3, 10, 11] 
* 

## Direct Comparison: Compaction vs. Hand-off

| Feature | Custom Compaction | Context Hand-off |
|---|---|---|
| Session Boundary | Stays within the same session. The conversation loop is uninterrupted. | Breaks the session. Terminates the old thread and starts completely fresh. |
| Data Nature | Lossy & Synthetic. Relies on LLM-generated summaries or truncated logs. | Structured & Exact. Relies on explicitly saved state files and precise briefs. |
| Primary Risk | Context Drift. Over time, critical context can be accidentally omitted during compression. | Relitigation. The new agent might restart closed loops if the hand-off is poorly written. |
| Best Used For... | Linear, iterative tasks requiring a rolling memory (e.g., continuous debugging). | Major task pivots, phase shifts, or fanning out to specialized sub-agents. |

Are you currently architecting a single-agent system that is running out of tokens, or are you building a multi-agent system that needs to coordinate tasks? I can provide code design patterns or point you toward specific framework implementations (like LangGraph, Microsoft Agent Framework, or OpenAI Agents SDK) depending on your setup.

[1] [https://addyosmani.com](https://addyosmani.com/blog/agent-harness-engineering/)
[2] [https://www.youtube.com](https://www.youtube.com/watch?v=J5y_ginvvKo)
[3] [https://www.aihero.dev](https://www.aihero.dev/ai-coding-dictionary/handoff)
[4] [https://nhimg.org](https://nhimg.org/glossary/context-compaction/)
[5] [https://platform.claude.com](https://platform.claude.com/cookbook/tool-use-automatic-context-compaction)
[6] [https://arxiv.org](https://arxiv.org/html/2607.21503)
[7] [https://medium.com](https://medium.com/predict/context-management-for-ai-agents-the-definitive-guie-ad2c859fa5e9)
[8] [https://jxnl.co](https://jxnl.co/writing/2025/08/30/context-engineering-compaction/)
[9] [https://agenticoding.ai](https://agenticoding.ai/context-engineering)
[10] [https://www.anthropic.com](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
[11] [https://www.augmentcode.com](https://www.augmentcode.com/guides/agentic-workflow-patterns-coordinating-agents)

---

NOTES:

---

# Agentic Context Management: Solving Agent Memory and Cost by Treating Them as Lifecycle and Architecture Problems

https://arxiv.org/html/2607.21503

this seems to be about memory systems for production agents, but much of it is still relevant context for working with coding agents.


>  The incumbent response treats this as a storage and retrieval problem. We argue that this framing is too narrow. We propose that actively managing what an agent holds in mind is a lifecycle, not merely a store

- deciding what to remember
- extracting and structuring it
- choosing the right store for the data type
- carving optimal redundancies (?)
- conscious consolidation
- forgetting stale information while maintaining provenance
- deciding what is relevant for the current turn
- anticipating what will be needed next
- compacting context to fit a budget without losing what is important or compromising recall

Agentic Context Management (ACM), 5 primitives:
1. architecting
2. ingesting
3. scoping
4. anticipating
5. compaction and consolidation

> naïve context accumulation grows token cost quadratically in conversation length, crude summarization buys linear cost at the price of an accuracy cliff and only validated compaction achieves linear cost with preserved fidelity

> consider the things a production agent platform must decide turn by turn: (a) which of the things just said are worth retaining at all (b) in what structure should these be retained (c) which small fraction of everything retained belongs in this turn’s context (d) what is the next turn likely to need (e) what should happen when the relevant context exceeds the budget the model can use meaningfully.

- which things worth retaining?
- in what structure should these be retained
- which retained data belongs in this turns' context
- what is the next turn likely to need
- what should happen when the relevant context exceeds teh budget the model can use meaningfully

> We define Agentic Context Management as the discipline of deciding what an agent should hold in context, when, for how long, and at what cost, across the full lifecycle from context-acquisition to context-retirement. It comprises five primitives.

Architecting: decide how to model the memory, what should be stored, how long it should live, etc. before a single memory is stored

Ingesting: "retrieval quality is bounded by ingestion quality" - raw signals => structured, retrievable memory.

Scoping: of everything the system knows, what info relevant for the future, and at what scope?

Anticipating: "If an agent never asks for it, they are unlikely to retrieve it." - speculative pre-fetching. TODO: is this like `pi-observational-memory`? "retrieval answers “what is relevant to a search query or the moment,” anticipatory retrieval answers “what will be relevant next”.

Compacting and Consolidation: "Crucially, compaction should be verifiable: a compaction that silently drops a critical fact is worse than no compaction"

---

# Context Management for AI Agents: The Definitive Guide

https://medium.com/predict/context-management-for-ai-agents-the-definitive-guie-ad2c859fa5e9

> Context drift kills agents before context limits do. 65% of enterprise AI agent failures in 2025 were attributable to degraded or lost context during multi-step reasoning, not raw window exhaustion

Paywalled :(

---

# Agent Harness Engineering

https://addyosmani.com/blog/agent-harness-engineering/

> Roughly: anytime you find an agent makes a mistake, you take the time to engineer a solution such that the agent never makes that mistake again.

this speaks to me. this is the same realization i made while working on my own trigger-testing harness and with my connect-4 skill optimization experiment. _Recognize/anticipate when the agent is going to make a bad decision, and take that decision away._

> Moving them into a different harness, with better tools for your codebase, a tighter prompt, and sharper back-pressure, can unlock capability the original harness was leaving on the floor.

this is a good article for when we get into harness engineering as a concept later

on long-horizon tasks: "compaction alone wasn’t sufficient for long tasks; sometimes you need to start fresh with a structured brief."

---

# Handoff

https://www.aihero.dev/ai-coding-dictionary/handoff

> Transferring agent context from one session to another, with no return path.


---

# Context Compaction

https://nhimg.org/glossary/context-compaction/

> In practice, the harness usually performs two reductions, not one. First it removes or offloads stale tool traces that no longer need to be replayed. Then it summarizes the surviving sections while leaving the most recent turns intact. The raw transcript may remain available outside the model call, but only the compact working set reaches the next request.

summarization is a lossy process, and then summarizing a summary leads to degradation.

you don't control what/how compaction happens unless you implement it yourself.

---

# Context Engineering

https://agenticoding.ai/context-engineering
