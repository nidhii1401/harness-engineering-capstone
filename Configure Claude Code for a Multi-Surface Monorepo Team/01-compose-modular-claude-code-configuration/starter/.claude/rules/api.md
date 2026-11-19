---
description: Conventions for API handlers under src/api/
paths:
  - "src/api/**/*"
---

# API handler rules

Loads when editing any file under `src/api/`.

## Handler signature

- Every handler exports a single named function matching the route's HTTP method: `export async function POST(req: Request)`. Do not export default handlers — the router resolves by name.
- Handlers never touch the database directly. All persistence goes through the repository modules in `src/db/` (e.g. `import { getOrder } from "@/db/orders"`). A handler that imports `pg` or `Pool` is a review blocker.

## Error handling

- Throw `ApiError` from `src/api/_lib/error.ts` for every client-visible failure: `throw new ApiError(404, "order_not_found")`. Never return ad-hoc `{ error: "..." }` objects with inconsistent shapes — the error middleware serializes `ApiError` into the canonical `{ code, message }` envelope.
- Validation failures are 400s with a machine-readable `code`; never leak stack traces or SQL errors into the response body.

## Schemas

- Request/response payloads are typed against the Zod schemas in `src/api/_schemas/`. Parse the incoming body with the schema before doing any work — do not hand-roll field checks.
- Never widen a schema with `.passthrough()` or `z.any()` to silence a type error — extend the schema explicitly so the contract stays reviewable.

## Response shape

- Successful responses return the parsed schema type directly; the serializer adds the envelope. Do not hand-build `{ data: ... }` wrappers inside handlers.
- List endpoints always paginate: accept `?cursor=` and `?limit=` (default 50, max 200) and return `{ items, next_cursor }`. Unbounded `SELECT *` responses are not allowed.
- Mutating endpoints (POST/PUT/DELETE) must be idempotent where the client can retry — accept an `Idempotency-Key` header and dedupe on it via the orders repository.
