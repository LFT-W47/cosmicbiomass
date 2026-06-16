# Skill: Session Close

Propose an update to [`../project-state.md`](../project-state.md) summarising what changed
during the current session. **Propose — never write — until the human confirms.**

## When to use

- At the end of a session that produced substantive changes (new conventions, completed
  work, architectural decisions, notable refactors, new knowledge pages).
- When the human says "run session_close", "close the session", or similar.

Skip it for sessions that only touched code with no impact on the project's "now" state.

## Process

1. Gather the session's material changes from the working tree (not memory):
   - `git log` / `git diff --stat` since the last state update,
   - plans/tasks that started, completed, or were abandoned,
   - new or substantially edited conventions / ADRs / knowledge pages,
   - decisions recorded in conversation.
2. Sort each item into the four `project-state.md` sections:
   - **Current priorities** — promote finished items off; add newly-started work.
   - **Recent changes** — a dated bullet, newest first, matching the file's style.
   - **Open questions** — carry forward unresolved items; drop answered ones.
   - **Decisions made** — durable choices with a one-line rationale (large ones → an ADR).
3. Update the `Last updated:` line to today's date.
4. Show the proposal as a **unified diff** against `project-state.md`.
5. Ask: **"Apply this update? (yes / edit / no)"**
   - `yes` → write the file. `edit` → revise and re-show. `no` → discard.
6. Do **not** commit or push — releases here are tag-driven and human-initiated.

## Output format

```text
Session close — proposed project-state.md update
------------------------------------------------
Summary of what this session produced
  • <bullet>
  • <bullet>

Proposed diff:
<unified diff against project-state.md>

Apply this update? (yes / edit / no)
```

## Notes

- The skill is a proposal engine, not a policy enforcer.
- Keep `project-state.md` a "now" page — don't let it grow into a second `CHANGELOG.md`.
