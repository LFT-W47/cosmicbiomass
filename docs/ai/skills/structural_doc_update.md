# Skill: Structural Doc Update

After a major structural change lands, update the **smallest coherent set** of docs/knowledge
files needed to keep the agent layer accurate. Treat this layer as living project memory.

## When to use

- After a change to: package/module structure, subsystem ownership, data/control flow, config
  or API semantics, durable conventions, entry points, or a major architectural decision.

**Not** for: local bug fixes, narrow refactors with unchanged semantics, test-only changes, or
tiny renames that don't change how the system is understood.

## Guiding rule

> Update the docs/knowledge layer **only if** the change alters the mental model a future
> contributor or agent needs to work correctly.

## Process

1. **Understand the change.** From the diff/commits: what changed structurally, which parts of
   the mental model are now stale, which files are affected, and whether a genuinely new
   durable concept/system now exists. Don't edit yet.
2. **Map to files** — update each only when its trigger is met:
   - root [`AGENTS.md`](../../../AGENTS.md) — commands, layout, workflow, or entry points changed
   - [`../architecture.md`](../architecture.md) — component map, flow, patterns, or responsibilities changed
   - [`../project-state.md`](../project-state.md) — add a concise "now" entry if it matters for ongoing work
   - [`../conventions/`](../conventions/) — a binding rule changed or an example became wrong
   - [`../decisions/`](../decisions/) — the change reflects a lasting decision (write/supersede an ADR)
   - [`../knowledge/`](../knowledge/) — a concept/system page is now stale, or a new durable one exists
3. **Plan the smallest patch.** Prefer patching existing pages over duplicating; prefer links
   over bloat. Create a new knowledge page only if the concept is durable, recurring, and
   awkward to fold into an existing page.
4. **Apply edits.** For knowledge changes, also update `knowledge/index.md` (if you added a
   page) and add a dated entry to the top of `knowledge/log.md`.
5. **Lint pass.** Check the touched files for contradictions, stale claims, orphan pages,
   missing cross-links, outdated paths, and duplicated explanations. Fix the obvious ones.
6. **Report** what you changed, what you deliberately left alone, and any follow-up needed.

## Constraints

- No documentation rewrite sprees. Surgical edits only.
- Keep `AGENTS.md` practical and `project-state.md` a "now" page.
- Don't duplicate information better captured elsewhere — link instead.
- Preserve the repo's existing tone.
