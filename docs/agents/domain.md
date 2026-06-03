# Domain Docs

## Layout

Single-context repo:

- **`CONTEXT.md`** — domain language, architecture overview, technical constraints. Read this first in every session.
- **`docs/adr/`** — Architectural Decision Records. One file per decision, format: `NNN-title.md`

## Consumer Rules

- Always read `CONTEXT.md` before writing or modifying code.
- Before adding a new module or changing a major data structure, check `docs/adr/` for prior decisions.
- When making a significant architectural decision, write a new ADR in `docs/adr/`.
- ADR format: `## Status`, `## Context`, `## Decision`, `## Consequences`
