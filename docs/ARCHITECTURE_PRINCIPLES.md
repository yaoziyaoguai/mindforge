# Architecture Principles

MindForge is a local-first, CLI-first, single-machine personal learning memory tool. AI output stays `ai_draft` until explicit human approval. The default path is fake provider and safe-by-default. MindForge is not RAG by default, not an Obsidian plugin, and not a Web UI.

## Module Rules

- Keep modules high-cohesion and low-coupling.
- Prefer stable inputs and structured outputs over hidden CLI state.
- Keep CLI commands thin: parse arguments, call services, render output.
- Service modules must not depend on Typer or Rich.
- Presenter modules may depend on Rich, but must not do business decisions.
- Context modules resolve config/path context, but must not do business work.
- Safety policy modules describe boundaries and pure checks, but must not change state.
- Tests should protect user behavior and module boundaries, not incidental implementation details.

## Anti-Patterns

- Splitting files only to reduce line count.
- Creating an anemic helper module with no domain meaning.
- Moving copied code into a new file without stable input/output.
- Calling `console.print` from service code.
- Doing ranking/filtering/business decisions in presenters.
- Reading real `.env` from context or service modules.
- Writing files from safety policy.
- Turning one large file into many low-cohesion fragments.

## Worthwhile Splits

A split is worth doing when it reduces cognitive load, strengthens a boundary, makes behavior easier to test directly, lowers the blast radius of future changes, and keeps CLI user behavior unchanged.
