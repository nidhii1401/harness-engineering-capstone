# Plan mode vs. direct execution — team decision guide

Choosing between Claude Code's **plan mode** (investigate and propose before changing anything) and **direct execution** (change code immediately) is the single biggest leverage point in how the team uses the harness day-to-day. The wrong mode at either extreme costs us: plan mode for trivial fixes is friction; direct execution for architectural changes burns context and produces rework.

> Anchor talk: Knight-Webb, "SWE Is Becoming Plan and Review" — the curriculum's Module 8 anchor talk framing why SWE work is shifting toward plan-and-review discipline.

This doc walks four concrete decisions against our codebase: one plan-mode example, one direct-execution example, one Explore-subagent example, and one combined-workflow example.

---

## 1. Plan-mode example

**Scenario:** extract a shared `useCart(userId)` hook out of three components that currently duplicate cart-fetching logic — `src/components/Cart/Cart.tsx`, `src/components/Checkout/Checkout.tsx`, and `src/components/MiniCart/MiniCart.tsx`.

**Why plan mode:** this is a multi-file refactor with several valid approaches (hook signature, where loading state lives, whether MiniCart needs the full cart or a count). Getting the abstraction wrong means re-touching all three components. Plan mode lets Claude investigate the three call sites, propose the hook contract, and get approval before any file changes — the point is to **prevent costly rework** by settling the interface before the mechanical edits begin.

---

## 2. Direct-execution example

**Scenario:** add a `min: 0` validation to the quantity field in the order-creation handler in `src/api/orders/handler.ts`.

**Why direct execution:** this is a simple, well-scoped change to one function — the schema parse call already exists, and the diff is a single added constraint. The bar for direct execution is that you can already describe the change in one sentence and predict the patch; planning here would be pure friction.

---

## 3. Explore-subagent example

**Scenario:** before refactoring the refund flow, we need an inventory of every `processRefund` call site — the answer spans `src/api/orders/refund.ts`, `src/api/billing/issue.ts`, and `src/services/payment.ts`.

**Why Explore:** this is a discovery task whose intermediate output (every grep hit, every file read, every false positive) has no value once the call-site list exists. An Explore sub-agent isolates that verbose discovery output and returns only the summary to the main session, preserving main-conversation context. The sub-agent writes its working notes to a scratchpad file (e.g. tmp/refund-callsites.md) using the **scratchpad pattern**, so the full inventory survives even if the main session's context window is later compacted.

---

## 4. Combined workflow — plan mode for investigation, then direct execution

**Scenario:** rename `findById` to `getById` on the orders repository in `src/db/orders.ts` to match the team convention (get* for single-row reads, find* for multi-row).

**Why combined:** the investigation question — "where is `findById` called, and are any call sites dynamic lookups grep would miss?" — is exactly what plan mode is for. Once the call-site list is in hand, the rename itself is mechanical keystrokes. The flow: (1) plan mode investigates and proposes the call-site inventory and rename plan; (2) you approve the plan; (3) direct execution applies the rename across the listed files and runs the test suite. This is **combining plan mode for investigation with direct execution for implementation** — the modes are stages of one task, not alternatives.

---

## Quick reference

| Situation | Mode |
|-----------|------|
| Single function, fix is obvious, you can predict the diff | Direct execution |
| Multi-file refactor, API shape is debatable | Plan mode |
| Discovery / inventory across the codebase, you'll throw away the intermediate steps | Explore subagent |
| Investigation-then-mechanical-change | Plan mode → direct execution |
| Architectural decision (which database, which queue) | Plan mode, possibly with a fork to compare options |

When in doubt: plan mode is recoverable (you can switch to execution), but direct execution on a complex change is not. Default to plan when uncertain.
