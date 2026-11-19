---
description: Conventions for co-located test files (*.test.ts / *.test.tsx)
paths:
  - "**/*.test.tsx"
  - "**/*.test.ts"
---

# Test file rules

Loads when editing any co-located test file, on top of the React or API rules that also match.

## Assertion style

- Use explicit `expect(...)` assertions on behavior, never snapshot tests (`toMatchSnapshot`) — snapshots hide regressions behind auto-updates. If a render is complex, assert on specific accessible roles/text instead.
- One behavior per `it(...)` block. A test named "handles errors and retries and logs" is three tests.

## Test data

- Build fixtures with the shared builders in `tests/` helpers — never inline raw object literals that duplicate production shapes. If a required field is added to a type, builders should be the only place that needs updating.
- No `setTimeout`/`sleep` in tests. Async behavior is awaited via the promise or mocked timers (`vi.useFakeTimers`), never wall-clock waits.

## Forbidden

- Mocking the database layer (`src/db/*`) — tests exercise repositories against the test schema; mock only external services (payment provider, email).
- `it.skip` / `describe.skip` without a linked ticket in a comment — skipped tests rot silently.
- `expect(true).toBe(true)`-style tautologies and assertions on mock call counts as the *only* check — assert the observable outcome the user or caller sees.
- Importing from `src/` via deep relative paths (`../../../src/...`) — use the `@/` alias so test imports mirror production imports.

## Naming

- Test names read as behavior sentences: `it("rejects refund when order is already refunded")`, not `it("test refund")`.
- Group related cases under `describe` blocks named after the unit under test (`describe("Cart")`), matching the file name of the module being tested.
