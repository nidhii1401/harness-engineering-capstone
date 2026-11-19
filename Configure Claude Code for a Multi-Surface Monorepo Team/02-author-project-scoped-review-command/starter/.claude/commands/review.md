---
description: Team PR review against repo conventions — read-only diff analysis
argument-hint: "<pr-ref | diff-range | file-path>"
allowed-tools:
  - Read
  - Grep
  - Glob
  - TodoWrite
  - Task
  - Bash(git diff:*)
  - Bash(git log:*)
  - Bash(git show:*)
  - Bash(git status:*)
  - Bash(git blame:*)
  - Bash(gh pr diff:*)
  - Bash(gh pr view:*)
  - Bash(gh pr checks:*)
  - Bash(gh pr list:*)
---

# /review — team PR review

You are reviewing the diff identified by `$ARGUMENTS` against this repository's conventions. Apply the path-scoped rules in `.claude/rules/` (they auto-load based on the files touched) and the shared standards in `.claude/standards/`.

## Phase 1 — Interview pattern

Before reporting findings, interview the author whenever intent is ambiguous. Ask clarifying questions FIRST — a confidently-wrong verdict is worse than a delayed one. Trigger the interview (do not report yet) when the diff shows any of:

- **Dependency changes** — `package.json`, `pyproject.toml`, or lockfile diffs. Ask why the bump is needed and whether the new version's breaking changes were checked.
- **Public API or schema changes** — response-shape edits in `src/api/_schemas/`, new/changed columns in `src/db/`, or renamed exports consumed by other surfaces. Ask whether downstream callers were updated.
- **Refactors with no test changes** — a large move/rename with zero `*.test.*` edits. Ask whether existing tests still cover the moved behavior or whether coverage intentionally moved elsewhere.
- **Multi-surface changes** — one PR touching API + components + DB at once. Ask which surface is the source of truth for the new behavior so findings attach to the right layer.

If none of these triggers fire, proceed directly to Phase 2.

## Phase 2 — Review criteria

**Must report** — these categories always produce a finding:

- **Bugs** — logic errors, missing `await` on promises, race conditions, off-by-one errors, unhandled promise rejections.
- **Security** — raw SQL built from user input, missing auth checks on handlers, secrets or tokens committed to the diff, `dangerouslySetInnerHTML` with unsanitized data.
- **Convention violations** — anything the path-scoped rules in `.claude/rules/` or standards in `.claude/standards/` explicitly forbid (e.g. handler importing `pg` directly, snapshot tests, `setTimeout` in tests).
- **Breaking changes** — renamed/removed exports, changed function signatures, altered API response shapes without a versioning story.
- **Migration safety** — destructive schema changes without a backfill plan, non-idempotent migrations, missing rollback notes.

**Skip** — these categories must NOT produce findings:

- Formatting and whitespace — Prettier/ESLint own this; do not comment on it.
- Naming bikeshed when the existing name is accurate and consistent with neighbors.
- Personal stylistic preferences not encoded in `.claude/rules/` or `.claude/standards/`.
- `TODO`/`FIXME` comments that already reference a tracked ticket.

## Phase 3 — Bundling: interacting vs. independent findings

**Interacting findings** overlap or affect the same fix — bundle them into ONE detailed message with all context so the author sees the whole problem at once. Example: a missing `await` and a missing transaction wrapper on the same function — the fix rewrites the same three lines, so splitting them would force the author to reconcile two comments about one edit.

**Independent findings** live in separate functions or files with no shared fix — report them SEQUENTIALLY as discrete items so each piece of feedback is independently actionable.

Heuristic: if fixing finding A changes the code that finding B references, they are interacting — bundle. If the fixes touch disjoint lines, they are independent — report separately.

## Phase 4 — Output format

For each finding, produce:

```
[severity] path/to/file.ts:line
finding: <one-sentence description>
fix: <one-sentence recommendation>
```

Severity is `bug` | `security` | `convention` | `breaking`. End with a one-line verdict: `approve`, `comment`, or `request-changes`.

## Examples

**Example 1 — independent findings.**

Input: `/review 412` — the diff adds `src/api/orders/handler.ts` with two unrelated problems: the handler returns `{ status: 404, body: { error: "not found" } }` instead of throwing `ApiError`, and a second handler in the same file calls `pool.query("SELECT ... WHERE id = " + req.params.id)` directly.

Output:

```
[convention] src/api/orders/handler.ts:18
finding: handler returns an ad-hoc error shape instead of throwing ApiError
fix: throw new ApiError(404, "order_not_found") so the error middleware emits the canonical envelope

[security] src/api/orders/handler.ts:42
finding: raw SQL concatenates req.params.id — SQL injection risk and bypasses the repository layer
fix: use the orders repository lookup with a parameterized query
```

Verdict: `request-changes`.

**Example 2 — interacting findings.**

Input: `/review 415` — the diff rewrites `refundOrder` in `src/api/orders/refund.ts`: the `paymentService.refund()` call is missing `await`, the DB write is not wrapped in `withTransaction`, and the order-status update runs before the payment call resolves.

Output:

```
[bug] src/api/orders/refund.ts:55-78
finding: three coupled defects in refundOrder — missing await on paymentService.refund(), missing withTransaction wrapper around the order + ledger writes, and the status update ordered before payment resolution
fix: rewrite the function body as a single transaction: await payment first, then update order status and ledger inside withTransaction, with compensating rollback on payment failure
```

Verdict: `request-changes`.

## Notes

- This command is project-scoped (`.claude/commands/review.md`) so everyone on the team gets the same review. If you want to layer personal preferences (e.g. a stricter accessibility check on your own PRs), put a `~/.claude/commands/review-strict.md` in your home directory — it will not affect teammates.
- If a finding requires running code or modifying files to verify, ask the author to run a specific check rather than attempting it from the review session. This command's `allowed-tools` are read-only by design.
