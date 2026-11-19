"""Deterministic tool-output pruning for the verbose `lookup_order` response.

The "Tool Context Pruning" pattern: application-side filtering
of a verbose tool result so only the fields needed for the immediate decision survive
into context. For return/refund reasoning, exactly five fields matter — order identity,
when it was placed, what it cost, whether it shipped, and the return-window deadline.

Why each kept field is the only one that matters for return/refund reasoning:
  - order_id: identifies which order the return/refund applies to — without it the
    agent cannot correlate the customer's request with a specific purchase.
  - order_date: anchors the start of the return window, so the agent can tell whether
    the customer is still inside the eligible period.
  - order_total_usd: caps the refundable amount, so the agent can quote a refund figure
    and flag orders that exceed policy limits.
  - fulfillment_status: decides the routing — shipped orders go through return/refund
    flow while unshipped orders should be cancelled instead.
  - return_eligible_until: the hard deadline for eligibility; the agent must compare it
    against today's date before promising any refund.

Implementation: deterministic field selection (no LLM call). The pruner has no
`anthropic` import — enforced by an AST audit.
"""
from __future__ import annotations

# The exact 5 fields, in OUTPUT ORDER. These are the only fields the pruner
# returns; everything else in the raw response is dropped. The output dict
# preserves this declaration order.
KEPT_FIELDS: tuple[str, ...] = (
    "order_id",
    "order_date",
    "order_total_usd",
    "fulfillment_status",
    "return_eligible_until",
)


class PrunerMissingFieldError(KeyError):
    """Raised when the raw tool response is missing one of the required kept fields."""


def prune_lookup_order(raw: dict) -> dict:
    missing = [name for name in KEPT_FIELDS if name not in raw]
    if missing:
        raise PrunerMissingFieldError(
            f"lookup_order response missing required fields: {', '.join(missing)}"
        )
    return {name: raw[name] for name in KEPT_FIELDS}
