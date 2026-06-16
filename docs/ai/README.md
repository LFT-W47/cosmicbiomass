# `docs/ai/` — Agent & Docs Layer

This directory holds the shared agent-facing documentation for CosmicBiomass: conventions,
reusable skills, an architecture overview, current project state, and a durable knowledge base.
It is checked into the repo so every contributor and coding agent works from the same context.

The repository's entry point ([`AGENTS.md`](../../AGENTS.md)) lives at the **repo root** and
points here.

## Structure

```text
docs/ai/
├── README.md          — this file
├── architecture.md    — module map and how the pieces fit
├── project-state.md   — current priorities, recent changes, open questions
├── conventions/       — binding coding rules (one topic per file)
│   ├── _template.md   — template for new conventions
│   └── code-style-and-tooling.md
├── decisions/         — architectural decision records (ADRs)
│   └── 0001-template.md
├── skills/            — reusable procedures for the agent
└── knowledge/         — durable, cross-linked knowledge base
    ├── index.md       — knowledge map + page-creation rules
    ├── log.md         — chronological history of knowledge updates
    └── concepts/  systems/  datasets/  runbooks/  raw/
```

## What goes where

| Need | Put it in |
|------|-----------|
| A binding coding rule / anti-pattern | `conventions/` |
| A repeatable procedure for the agent | `skills/` |
| How a concept or subsystem works | `knowledge/` (concepts/ systems/) |
| Why a lasting choice was made | `decisions/` (ADRs) |
| The current state of active work | `project-state.md` |
| The high-level code map | `architecture.md` |

## Adding content

- **New convention:** copy `conventions/_template.md`, fill it in, and link it from
  [`AGENTS.md`](../../AGENTS.md) if it's important.
- **New skill:** add a file in `skills/` and link it from [`AGENTS.md`](../../AGENTS.md).
- **New knowledge page:** add a file under `knowledge/{concepts,systems,datasets,runbooks,raw}/`,
  update `knowledge/index.md`, and add a dated entry to `knowledge/log.md`. See
  `knowledge/index.md` for the page-creation rules.
- **New decision:** create `decisions/<NNNN>-<slug>.md` from the ADR template.

## Conventions for this directory

- Markdown-native, one topic per file, cross-link with relative links.
- Keep high-level files short; push detail into focused `knowledge/` pages.
- Don't duplicate the same explanation across files — state it once and link.
