# MindForge Lessons for Vibe Coding

Date: 2026-06-05
Status: Learning artifact — reference for future projects

This document captures lessons learned from building MindForge as a vibe coding project. It is methodology, not a diary entry. Future projects should read this before writing their first line of code.

## 1. Core Lessons from This Project

### Lesson 1: Coding Agents Can Build Complex Systems Fast, But They Don't Judge Whether the Product Is Worth Building

MindForge has 100+ Python files, 13 Web pages, 30+ components, 20+ docs. The coding agent built all of it efficiently. But no agent asked: "does anyone actually need this?"

**Rule**: Before asking an agent to build a system, you must answer the product question yourself. The agent will faithfully implement whatever you tell it to build — including the wrong thing.

### Lesson 2: SDD / TDD / Review / Audit Improve Implementation Quality, But Cannot Replace Product Judgment

MindForge had excellent engineering discipline:
- SPEC documents for every feature
- Test-driven development
- Code review from multiple agent personas
- Multi-modal UX audit

All of this ensured the code was well-written, well-tested, and well-architected. But a well-tested product that nobody needs is still a product nobody needs.

**Rule**: Engineering quality and product value are independent dimensions. High engineering quality cannot compensate for zero product value.

### Lesson 3: Validate the Scenario First, Then Design the Architecture

We designed ADRs, target architecture maps, and layered system architectures before validating that anyone needed the core workflow. Architecture is expensive even when the direction is right. When the direction is wrong, it's a sunk cost amplifier.

**Rule**: Architecture design should only happen after you have evidence that the product scenario is worth pursuing.

### Lesson 4: Just Because Agents Can Build Web / API / Tests Doesn't Mean You Should Build Web / API / Tests

The availability of capable coding agents creates a temptation: "I can build this Web app quickly, so I should." But "can build" is not "should build."

**Rule**: The ease of implementation should not drive scope decisions. User need should.

### Lesson 5: Don't Build Full Product Form for Small Tool Projects from the Start

MindForge started as a "knowledge processing idea" but immediately became a "full Web product with 13 pages." A smaller form (CLI script, markdown pipeline, Obsidian plugin) would have been sufficient for validation.

**Rule**: Start with the smallest form that tests the core hypothesis. Scale up only after validation.

### Lesson 6: Premature Architecture Design Amplifies Sunk Cost

The more architecture you build before validating the product direction, the harder it becomes to stop or pivot. MindForge had target architecture maps, ADRs, design directions — all of which made stopping feel "wasteful" even when stopping was the right decision.

**Rule**: Architecture creates emotional commitment to the direction. Only create that commitment after validating the direction.

### Lesson 7: Review and Red-Team Audit Should Come Early, Not After the System Is Complex

The multi-modal audit (17-section report, display 4/10, extraction 3/10) came after the system was already complex. The audit findings were valuable, but the cost of implementing them was high because the system was already built.

**Rule**: Audit should happen at the idea stage, not the implementation stage. "Does this product make sense?" is cheaper to answer than "does this code work correctly?"

### Lesson 8: Multi-Modal Audit Exposes Real User Experience Problems

The audit methodology (browser experience + code review + prompt analysis + content analysis) revealed problems that unit tests and code review never catch:
- "One-sentence summary" was actually the body prefix (Source Excerpt)
- Tags were not exposed to the API
- Relationship section packaged same-tag as "knowledge graph"
- AI summary was paraphrase, not insight

**Rule**: Audit the product as a user would experience it, not just as code to be reviewed.

### Lesson 9: Stopping a Project Is a Normal Engineering Decision, Not a Failure

MindForge's soft archive is not a failure. It's a recognition that continued investment would be a sunk cost trap. The project produced valuable learning, engineering assets, and methodology. Stopping at the right time is good engineering judgment.

**Rule**: Define kill criteria before starting. Execute them honestly when triggered.

### Lesson 10: Agents Reduce Implementation Cost, But Also Accelerate Wrong Directions

Vibe coding makes building fast. But "building the wrong thing fast" is worse than "building the wrong thing slow" — because fast implementation creates more code to throw away and more emotional attachment to keep going.

**Rule**: Slow down on product decisions. Speed up on implementation only after the direction is validated.

## 2. Startup Checklist for Future Projects

Before writing any code for a new project, answer these questions:

| Question | Why It Matters |
|----------|---------------|
| **Who is the target user?** | "Everyone" is not a user. Be specific: "developers who manage project documentation" or "researchers who organize academic notes." |
| **What is the specific scenario?** | "Knowledge management" is too broad. "Import a 5000-word research article and extract 3 actionable principles" is specific. |
| **How do users solve this now?** | If they're happy with their current solution, they won't switch. |
| **Why are existing tools not enough?** | If Claude + Obsidian already solves 80% of the problem, you need to explain the remaining 20% compellingly. |
| **What is the minimum manual validation?** | Can you simulate the workflow with a script, a prompt, and a markdown file? If yes, do that first. |
| **Can you validate without writing code?** | Try the workflow manually: paste text into Claude, ask it to distill, review the output, save to a file. Does it feel valuable? |
| **Is CLI / script sufficient?** | If the core value is in the processing pipeline, a Web UI adds cost without adding value for validation. |
| **Why must there be a Web frontend?** | Web adds installation cost (npm, build, serve), maintenance cost (pages, components, dependencies), and distribution cost. Justify each. |
| **Why must there be a backend?** | If the processing can be done as a CLI script, a backend adds complexity without adding value. |
| **Why must there be a database?** | If YAML files or markdown work, a database adds operational complexity. |
| **What signal must appear before architecture is allowed?** | "3 users completed the core workflow manually and said they'd use it again" is a good signal. |
| **What signal must appear before UI productization?** | "Users complete the CLI workflow consistently and ask for a visual interface" is a good signal. |
| **Under what conditions should we stop?** | Define 3-5 kill criteria before starting. Execute them honestly. |

## 3. Project Startup Principles for Coding Agents

When using a coding agent (Claude Code, Cursor Agent, etc.) to start a new project, follow these principles:

### Don't Default To

- **Don't default to building a Web frontend**. Web is the most expensive form factor. Start with CLI or script.
- **Don't default to building a backend**. If the processing is local, a backend is unnecessary infrastructure.
- **Don't default to a complete schema design**. Schema should evolve from usage, not be designed before validation.
- **Don't default to a complex documentation system**. Docs are good, but don't let doc-writing substitute for product validation.
- **Don't default to multi-page UI**. One page (or zero pages) is enough for validation.

### Do First

- **Build the smallest useful workflow**. If the core value is "import → distill → approve," build that as a script. Not a Web app.
- **Do real dogfooding**. Use the tool yourself for a real task. If you don't enjoy using it, no one else will.
- **Define kill criteria before starting**. "If X users can't complete the core workflow in Y minutes, stop."
- **Do a product red team before implementation**. "Why would this product fail?" is a cheaper question than "does this code have bugs?"

### Then

- **After validation, write SDD**. Now that you know the direction is right, document the architecture.
- **After SDD, write tests**. Now that you know what to build, test-drive the implementation.
- **After tests, implement**. Now that you know what to build and how to verify it, let the agent build it.

### The Recommended First Phase

For any future vibe coding project:

1. **One-sentence user scenario**: "As a [specific user], I want to [specific action] so that [specific outcome]."
2. **Manual workflow validation**: Simulate the entire workflow by hand. Does it feel valuable?
3. **Minimum CLI / script validation**: Write a script that does the core processing. Does the output feel useful?
4. **Real dogfood**: Use it for a real task, at least 3 times. Would you use it again?
5. **Then decide Web / backend / architecture**: Only if the above steps validate value should you invest in product form.

---

These lessons were earned through honest work and an honest stop. They are preserved here so that future projects can benefit without repeating the same mistakes.
