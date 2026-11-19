# Reflection Brief — Harness Engineering Capstone

**Name:** Jyoti Kumari
**Date:** 2026-11-19

> All sections are filled with figures from real runs: System 1 `runs/20261119_193929/`, System 2 `runs/20261119-194207/`, System 4 live shift run (2026-11-19). Evidence copies live under `capstone-evidence/`.

**Environment**

- Model(s): `claude-sonnet-4-5-20250929` via the course proxy (`ANTHROPIC_BASE_URL=https://claude.vocareum.com`) for Systems 1, 2, 4; recorded fixtures also exercised for System 4 offline
- OS / Python: Windows 11 / Python 3.13, per-system venvs (`anthropic==0.39.0` for System 1, `0.69.0` for System 2)
- Approx. API spend: ~$1.10 total (System 1 run reported $0.4262 estimated; Systems 2 and 4 similar magnitude)

---

## Part 1 — Per-system

### System 1 — Agentic loop

1. **Loop control.** From `runs/20261119_193929/traces/claim_02_stolen_bike.jsonl`, the `stop_reason` sequence was `tool_use → tool_use → tool_use → end_turn` (4 turns). The continue-vs-stop decision lives in `claims_intake/loop.py::run` — it triages on `response.stop_reason`: `end_turn` returns the final state, `tool_use` executes the tool batch and loops, anything else raises `UnexpectedStopReason`. No string matching, no iteration cap.

2. **Anti-pattern.** `tests/test_antipatterns.py` AST-audits for four patterns; the sharpest is the **integer-literal iteration cap** — a `for _ in range(N)` or `while i < N` bound on agent turns. If the loop used it, a claim needing more turns than the cap would be silently truncated mid-investigation instead of terminating on `end_turn` — the cap decides *when to stop*, which is exactly the job `stop_reason` already does correctly.

3. **Tool design.** `lookup_policy` and `record_claim_fact` overlap on claim context but differ in direction: lookup *reads* the policy book, record *writes* session facts. Their descriptions state that boundary explicitly ("retrieve the governing policy text" vs "persist a fact the customer stated"), so the model routes by intent, not by guessing from schemas. A structured tool error (`{"is_error": true, "error_category": ..., "is_retryable": ...}`) lets the agent *recover in-loop* — e.g. retry with corrected args or ask a clarification — whereas a generic exception string gives it nothing actionable to branch on.

4. **Your numbers.** From `runs/20261119_193929/summary.md`: the full 8-claim run cost **$0.4262** estimated; claim_02_stolen_bike took **4 turns**, 13,848 input / 708 output tokens, $0.0522. Outcomes: 4 routed, 4 escalated — including claim_06_low_confidence_escalation which correctly escalated after 6 turns and 2 clarifications. Turn counts (2–6) match the README's expectation that simple claims terminate fast and ambiguous ones spend turns on clarification.

### System 2 — Context strategy

5. **The reduction.** From `runs/20261119-194207/budget.json`: baseline_tokens = **38,708**, assembled_tokens = **16,783**, reduction = **56.64%** (token counting via the SDK `messages.count_tokens` endpoint). The `active` section dominates assembled tokens (15,789 of 16,783) because it is preserved **byte-exact** — fidelity is non-negotiable while the issue is still open; resolved sections are cheap because they were summarized.

6. **Summarize vs preserve.** The rule: **resolved** segments get LLM-summarized (3-part outcome/facts/resolution); the **active** segment is copied byte-exact. Cited numbers from `budget.json`: `resolved_refund` = 320 tokens, `resolved_subscription` = 488, `case_facts` = 204, vs `active` = 15,789 — a ~30–70× asymmetry. The strategy pays full price only for the live thread.

7. **Facts block.** In `runs/20261119-194207/`, `eval.jsonl` passed **6/6** questions while `eval_control.jsonl` (case-facts block stripped) went **1/2** on the held-out pair — Q1 still passed (the answer survives in transcript prose) but **Q6 regressed to FAIL**. Q6 asks for the exact structured status token `in_progress`, which exists only in the case-facts block. That proves the persistent facts block is load-bearing: it carries machine-readable state the summarizer would otherwise lose.

### System 3 — Claude Code config

8. **Path-scoped rules.** `.claude/rules/tests.md` frontmatter:
   ```yaml
   paths:
     - "**/*.test.tsx"
     - "**/*.test.ts"
   ```
   A glob beats a directory-level CLAUDE.md for cross-cutting conventions because test files live *next to* sources (`Cart.tsx` / `Cart.test.tsx`) — a directory CLAUDE.md can't express "load these rules only for `*.test.*` anywhere in the tree." The glob fires exactly on the file being edited, in both `src/components/` and `src/api/`.

9. **Forked skill.** `.claude/skills/deploy-check/SKILL.md` frontmatter:
   ```yaml
   context: fork
   allowed-tools:
     - Read
     - Bash(git status:*)
     - Bash(gh pr view:*)
     ...
   ```
   Forking keeps the verbose enumeration (diff walks, check traces) out of the main conversation — only the structured verdict returns. Read-only tools mean the skill *cannot* push or edit even if the model tries. Without `context: fork`, every deploy check would dump its working output into the session you're trying to keep clean; without the allowlist, a "read-only" check could mutate the repo.

10. **Scope.** Validator printed `OK` (`capstone-evidence/system-3-monorepo-config/validator.log`). Project-level: `./CLAUDE.md` + `.claude/` (committed, shared). User-level example: a personal `~/.claude/commands/review-strict.md` — noted in `.claude/commands/review.md` Notes section — stays local and never affects teammates.

### System 4 — Orchestration

11. **Push work down.** Offline run (`capstone-evidence/system-4-quality-monitoring/shift-run.log`): `run_shift` pulled **17 new defects** via `WarmStore.defects_since(since_ts)` — an indexed SQL query (`idx_defects_ts` on `ts`, verified by `EXPLAIN QUERY PLAN` in `tests/test_us01_tiered_state.py`) — out of **40 total** warm-tier rows. The model never sees full history because `gather_new_defects` is a pure SQL pass-through (AST-audited: no Python-side filtering) and the prompt carries only the delta plus the ≤5KB `HotState`.

12. **Crash recovery.** `shift_monitor/recovery.py::decide` returns `"resume"` only when the manifest is incomplete AND the last step is ≤ `STALE_RESUME_THRESHOLD_MINUTES = 30` old (`<=`, so exactly 30 min still resumes); otherwise `"fresh"`. Fresh-with-injected-summary is more reliable than resume because a stale partial's findings may contradict current state — the manifest preserves what was *learned*, not the dead session's context.

13. **Small state.** `hot_state.json` after the live shift run: **446 bytes** (evidence copy: `capstone-evidence/system-4-quality-monitoring/hot_state-live.json`), far under the 5,120-byte `HOT_STATE_BYTE_BUDGET`. The budget matters because this state is injected into *every* shift prompt, indefinitely — an unbounded state would silently grow the per-shift token cost forever; the cap forces SQL pre-filtering (`_trim_to_budget` sheds alerts first).

---

## Part 2 — Synthesis

14. **Three layers.**
    - **Model:** `claims_intake/loop.py` — the agent decides tool calls turn-by-turn.
    - **Harness:** `retail_context/assemble.py` + `pruner.py` — deterministic code owns what the model sees (5-field prune, byte-exact active segment, position-aware layout).
    - **Orchestration:** `shift_monitor/manifest.py` + `recovery.py` — durable JSONL manifest + resume/fresh decision across process crashes and shift boundaries.

15. **Deterministic vs prompt.** Guaranteed in code: terminal-tool routing in `claims_intake/tools.py` (exactly one of `route_to_adjuster`/`escalate_to_human` may fire), read-only `allowed-tools` in `.claude/skills/deploy-check/SKILL.md`, atomic writes via tempfile+fsync+`os.replace` in `shift_monitor/state.py`, the 5,120-byte hot-state budget. Guided by prompt: the claims system prompt's process flow, the compression prompt's 3-part summary shape. Rule of thumb: **invariants and side effects belong in code; judgment and phrasing belong in prompts.**

16. **Context, two faces.** System 2 manages context *intra-session*: 38,708 baseline tokens → 16,783 assembled (**56.64% reduction**, `runs/20261119-194207/budget.json`). System 4 manages it *cross-session*: 40 warm-tier defects → 17-row SQL delta + 446-byte `HotState` per shift (live run, 2026-11-19). Same principle — never let raw history reach the model — different mechanism: lossy summarization/pruning within a session vs indexed pre-filtering and durable small state across sessions.
