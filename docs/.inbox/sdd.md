# References

- https://specdriven.ai/
- https://thoughtworks.medium.com/spec-driven-development-d85995a81387
- https://www.augmentcode.com/guides/what-is-spec-driven-development
- https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html
- https://github.blog/ai-and-ml/generative-ai/spec-driven-development-with-ai-get-started-with-a-new-open-source-toolkit/
- https://github.com/github/spec-kit
- https://openspec.dev/
- https://www.reddit.com/r/BetterOffline/comments/1w2ouje/specdriven_development_is_a_new_beautiful_trend/

---

https://specdriven.ai/

- methodology that prioritizes creation of precise, machine-readable specifications over immediate coding
- defining intent > writing syntax
- specification is primary source of truth from which code, tests, and docs derived
- front-loading clarity to eliminate cost of hallucination and rework caused by vague requirements
- foundational guardrails, explicit clarification, atomic task decomposition
- developer goes from "coder" => "architect + reviewer" (great for my quality complaints, bad for me the programmer)
- Workflow example:
    * **Constitution** establish persistent project principles (tech stack, coding standards, security rules) that serve as immutable context for all AI operations
    * **Specify** capture unambiguous requirements including user stories, acceptance criteria, and constraints. focus on intent, not technical implementation details (PRD?)
    * **Clarify** run a structured pass to surface underspecified areas - edge cases, empty states, error handling - recording answers in the spec before moving on
    * **Plan** translate intent into feasible techincal approach: archtectural decisions, data models, api contracts, dependencies
    * **Tasks** Break work into small, testable, isolated chunks scoped for single PRs (1-4 hrs/each). order by dependencies.
    * **Implement and Iterate** ai generates code and tests from spec/plan slices. humans validate against the spec. post-merge, any changes start by revising the spec first:
        + tests are embedded in specs from the start
        + commit only when validated by ai and human
        + treat specs as version-controlled code
- Key tenets:
    * **specification as truth** begin with spec that covers "what" and "why" from user's perspective; treat as living contract and executable blueprint the ai agents use to generate and validate code, ensuring intent and implementation stay synchronized
    * **up-front clarity and rigor** unambiguous details in the spec, covering biz rules, edge cases, non-functional requirements, architectural planning; outlines the tech stack and integration points upfront to align with existing systems
    * **persistent context** maintain the spec as a single, evolving source of truth across dev sessions to ensure consistency; serves as persistent communication tool between stakeholders, designers, developers
    * **test-driven guardrails** derive automated tests and clear acceptance criteria directly from the spec; validates outputs continuously, catching issues early, inspired by TDD, BDD, and Design by Contract
    * **system integration** explicitly define integration points, arch patterns, constraints in the spec; ensures seamless alignment with current infra, avoids conflicts and promotes secure, efficient development
    * **living specification** treat as dynamic artifacts that update iteratively with new insights and ffedback - both pre and post-implementation; minimizes misunderstandings, reduces rework, supports ongoing maint
    * **structured organization** dedicated structures, constitutions, or guiding principles to enforce consistency. provides persistent rules for ai-generated artifacts and facilitates clearer collaboration.
    * **systematic decomposition** break into small, atomic, testable tasks with tight scoping; enables predictable ai code generation and continuous validation against the spec's criteria.
    * **human orchestration** developer becomes orchestrator and reviewer; incorporate checkpoints to critique specs, plans, and ai outputs for correctness, security, alignment w/ intent.
    * **explicitness** emphasize high specificity in specs to drive secure, efficient workflows; decisions made early guide the process, balancing against anti-patterns like skipping planning
    * **executable intent** specs inherently executable by ai tools; enables direct code generation and validation, evolving development roles in ai-assisted environments
    * **iterative refinement** incorporate feedback loops for spec evolution before implementation begins; drawing from related methodologies helps catch ambiguities early and promotes a flexible yet rigorous pre-code phase
- how the tools work:
    * 1) initialization: transforms user intents to specs. scan existing repositories for interfaces and patterns, then reference the `constitution.md` to generate stories and acceptance criteria. upfront analysis minimizes ambiguity before a single line of code is written
    * 2) execution: tools use ai to produce code, test, and documents derived directly from the artifacts; specs act as living metadata - updating a spec triggers regeneration of affected code; enables automatied consistency checks and contract testing, abstracting away the pitfalls of ad-hoc generation.

- `constitution.md` sounds similar to my idea of `architecture.md` and `project.md` files
- interested in how "updating a spec triggers regeneration of affected code"; idea: "contracts" are modified, system rewrites itself to match the contract changes while maintaining integrity from existing specs
- does this mean agent is constantly mining old specs? or i guess we always update completed specs? either way, that sounds like a ton of processing over many thousand specs over time... context and cost risk?

---


- https://thoughtworks.medium.com/spec-driven-development-d85995a81387

- what is a spec?:
    * sole source of truth? we can discard code entirely?
    * or, elements that driver code generation? executable code is still source of truth, needs maintenance
- early gpt code generation found code generated by setting technical specs, using cot and few-shot produced much higher quality results than plain-text requirements
- recently, ai coding tools have improved; easier to bring functional requirements into the picture
- can we rely on functional requirements alone, or do we still need to pay attention to techincal details?:
    * passing tests can only prove the presence of bugs, never their absence
- a spec is more than a PRD:
    * more explicit technical requirements
    * though, you can split this into spec and "plan"?
- a good "spec" (not necessarily a single document/phase):
    * - domain-oriented ubiquitous
    * clear structure, common style given/when/then
    * strive for completeness, yet conciseness
    * cover critical path w/out enumerating cases
    * aim for clarity and determinism
    * "many emphasize separating biz reqs from tech specs. however, in practice, defining the boundary between the two is often unclear."
- SDD in practice:
    * practices can vary, depending on the tools yo use; kiro and spec-kit offere predefined workflows; otherwise, need to find one for yourself
    * in planning phase:
        + reqs analyzed using an ai agent to generate design and implementation plans
        + reviewing and validating the specs is an iterative process requiring human+ai
    * finalized specs handed to agent to generate code, using custom rules, etc.
    * specs either discarded or kept (and possibly maintained after implementation)
- SDD = waterfall?:
    * waterfall = excessively long feedback cycles; disconnect between design and implementation
    * problems with ai coding are different: easy generation makes it easy to overlook good engineering practices, resulting in too much unmaintainable code
    * important: serious requirement analysis, prudent software design, necessary architectural constraints, human-in-the-loop governance
- spec drift and hallucination are inherently difficult to avoid; still need highly deterministic ci/cd practices to ensure software quality and safeguard our architectures
- challenges of SDD:
    * generation from spec to code non deterministic, depends on model and harness used, etc; poses challenges to upgrades and maintenance.
    * spec drift and hallucination
    * to keep the specs? or unnecessary trouble, context, slow down feedback cycles?

---

Spec-driven development (SDD) introduces upfront planning, documentation, and review overhead rather than jumping straight into code. [1] (https://hiddedesmet.com/the-hidden-costs-of-spec-driven-development), [2] (https://www.orderfactory.com/articles/spec-driven-development.html)

The Hidden Costs of Spec-Driven Design

• Planning Tax: Time spent writing, structuring, and refining declarative specifications or markdown documents before any code is generated. [1] (https://www.orderfactory.com/articles/spec-driven-development.html), [2] (https://hiddedesmet.com/the-hidden-costs-of-spec-driven-development)
• Review & Bottleneck Tax: Human reviewers must thoroughly vet long spec documents, user stories, and generated plans. For example, one test case showed a spec framework generated 2,500 lines of markdown for 689 lines of code, requiring 3.5 hours of review time compared to a much faster iterative approach. [1] (https://www.youtube.com/watch?v=wgV-tEYLEts), [2] (https://www.youtube.com/watch?v=iHjlRB93okg&t=234), [3] (https://hiddedesmet.com/the-hidden-costs-of-spec-driven-development)
• Context Maintenance Tax: Keeping specs synchronized with codebase changes; when specs go out of date, they become "spec drift" or inaccurate fiction. [1] (https://www.youtube.com/watch?v=iHjlRB93okg&t=234), [2] (https://hiddedesmet.com/the-hidden-costs-of-spec-driven-development)
• False Precision Tax: Spending excessive effort locking down exact implementation contracts for systems or user requirements that are still fluid or exploratory. [1] (https://hiddedesmet.com/the-hidden-costs-of-spec-driven-development)
• Token & Compute Overhead: In AI-assisted workflows, heavy spec frameworks consume significantly more LLM tokens and generation steps for planning and multi-agent loops than simple prompt-and-iterate ("vibe coding") workflows. [1] (https://levelup.gitconnected.com/token-economics-of-spec-driven-development-caching-routing-and-break-even-6707f907e7f1), [2] (https://www.youtube.com/watch?v=wgV-tEYLEts)
• Morale & Agility Tax: Heavy processes can bog down small fixes, spikes, or proof-of-concept work where the paperwork outweighs the actual coding effort. [1] (https://www.augmentcode.com/guides/what-is-spec-driven-development), [2] (https://hiddedesmet.com/the-hidden-costs-of-spec-driven-development), [3] (https://www.youtube.com/watch?v=iHjlRB93okg&t=234)

When the Overhead Pays Off vs. Fails

• When it wins: Complex, multi-role enterprise systems, long-term architectures, or high-risk domains where a wrong decision is expensive to reverse and architectural drift must be strictly governed. [1] (https://ranthebuilder.cloud/blog/i-tested-three-spec-driven-ai-tools-here-s-my-honest-take/), [2] (https://www.infoq.com/articles/spec-driven-development/), [3] (https://niotechone.com/blog/custom-software-development-cost-in-india/)
• When it fails: Small bug fixes, throwaway prototypes, solo quick tasks, or fast-moving exploratory phases where informal iteration is 5x to 10x faster. [1] (https://www.augmentcode.com/guides/what-is-spec-driven-development), [2] (https://www.youtube.com/watch?v=iHjlRB93okg&t=234)
To help tailor this to your project, tell me:
• What kind of project or feature are you planning to build?
• How large is your team (solo, small startup, or enterprise)?


---

https://www.augmentcode.com/guides/what-is-spec-driven-development

https://www.augmentcode.com/guides/living-specs-vs-static-specs

https://www.augmentcode.com/guides/spec-as-source-of-truth-rebuildable-codebase



---

- https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html

---

- https://github.blog/ai-and-ml/generative-ai/spec-driven-development-with-ai-get-started-with-a-new-open-source-toolkit/
- https://github.com/github/spec-kit


---

- https://openspec.dev/

---

- https://www.reddit.com/r/BetterOffline/comments/1w2ouje/specdriven_development_is_a_new_beautiful_trend/
