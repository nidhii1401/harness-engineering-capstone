# E-Commerce Platform — Shared Claude Code Conventions

This file is the **project-level** entry point for the e-commerce monorepo. Every teammate's Claude session loads it automatically.

## Scope: what belongs here vs. elsewhere

| Scope | Location | Shared via git? | Loaded when |
|---|---|---|---|
| Project-level | `./CLAUDE.md` + `.claude/` in this repo | Yes — committed, every teammate gets it | Every session in this repo |
| User-level | `~/.claude/` (e.g. `~/.claude/CLAUDE.md`) | **No — user-level settings are not shared with teammates via version control**; they stay local to each developer's machine | Every session for that user, any repo |
| Directory-level | `CLAUDE.md` in a subdirectory | Yes, if committed | Sessions rooted in that subdirectory |

User-level is the right home for personal preferences that should not leak into the team's shared config — for example, a preferred commit message style or a personal editor theme. Anything the whole team must agree on (API conventions, test rules, review checklists) belongs at project level so it travels with the repo.

## Shared standards (modular via @-imports)

The actual conventions live in focused files so this entry point stays scannable:

@.claude/standards/frontend.md
@.claude/standards/api.md
@.claude/standards/database.md
@.claude/standards/testing.md

Path-scoped rules in [.claude/rules/](.claude/rules/) layer on top of these standards and activate only when Claude is editing matching files (React components, API handlers, test files).

## Repository layout

```
src/components/   React components (functional + hooks)
src/pages/        Top-level routes
src/api/          Node.js API handlers
src/db/           PostgreSQL repository-pattern modules
```

Tests are co-located: `Foo.tsx` lives next to `Foo.test.tsx`.

## Troubleshooting

If a CLAUDE.md instruction isn't being followed, run `/memory` to list exactly which configuration files actually loaded for the current session — it shows the full hierarchy (user-level, project-level, directory-level) so you can spot a file that failed to load or a scope that was shadowed.

## Team workflows

- `/review <pr-ref>` — codified PR review checklist. (You will author this in Exercise 2.)
- `/deploy-check` — read-only pre-deployment validation. (You will author this in Exercise 3.)

For decisions about when to use plan mode vs. direct execution on this codebase, you will produce a team decision doc in Exercise 4.
