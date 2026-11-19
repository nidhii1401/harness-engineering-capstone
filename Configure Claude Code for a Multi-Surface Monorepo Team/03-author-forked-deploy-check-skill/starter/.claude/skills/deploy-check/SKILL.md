---
name: deploy-check
description: Read-only pre-deployment validation — working tree, migrations, and CI status
context: fork
argument-hint: "[target-branch] (defaults to main)"
allowed-tools:
  - Read
  - Grep
  - Glob
  - TodoWrite
  - Task
  - Bash(git status:*)
  - Bash(git diff:*)
  - Bash(git log:*)
  - Bash(git show:*)
  - Bash(gh pr view:*)
  - Bash(gh pr checks:*)
  - Bash(gh pr list:*)
---

# /deploy-check

Runs the team's pre-deployment validation checklist against the current working tree and the branch you're about to ship. Read-only by design — this skill never modifies files, never pushes, never deploys. It returns a single structured summary so the calling session can decide whether to proceed.

## Why this is a skill (not a CLAUDE.md addition)

A skill is **on-demand, forked, and task-specific** — you invoke `/deploy-check` only in the minutes before a deploy, and its verbose intermediate output (file enumeration, diff parsing, check traces) has no value once the verdict is known. CLAUDE.md guidance is **always-loaded and universal** — conventions like "tests are co-located" or "throw `ApiError` for validation failures" must be present in every session to shape behavior. Rule of thumb: on-demand / forked / task-specific → skill; always-loaded / universal → CLAUDE.md. Dumping everything into CLAUDE.md produces a 600-line monolith that burns context on every session for rules that matter once a week.

## Why `context: fork`

The goal of `context: fork` is to keep verbose intermediate output **out of the main session / conversation**. A deploy check walks the working tree, inspects diffs, and runs several enumeration passes — none of that has any value to the calling session once we know whether to ship; only the structured summary should return to the main conversation. `context: fork` is a Claude Code product feature operating at the skill-invocation layer, conceptually analogous to the *Branching Reality* pattern: establish a shared starting point, then branch into isolated explorations whose working output never flows back into the parent. Session-level forking (`fork_session`) applies the same pattern to a whole session — the skill fork is the same idea scoped to a single invocation.

## Checks

Run all three. Each check produces a pass-or-fail verdict; if any fails, the overall summary is **fail**.

### Check 1 — Clean working tree

- Detect: run `git status --porcelain` against the repo root.
- Pass: the command returns empty output — no modified, staged, or untracked files.
- Fail: any output line. Surface the first few paths in `detail` so the author knows what to commit or stash before shipping.

### Check 2 — Migrations cover new repository usage

- Detect: diff the branch against the target (`git diff <target>...HEAD --name-only`), collect new `import`/`require` references to `src/db/*` modules, and verify each touched repository has a corresponding migration file added in the same diff.
- Pass: every new repository dependency is backed by a migration file in the branch, or no new repository imports exist.
- Fail: a repository module is imported by new code but no migration file was added. Surface the module name and the missing migration in `detail`.

### Check 3 — CI checks green on the open PR

- Detect: run `gh pr view --json statusCheckRollup` for the current branch's open PR.
- Pass: every required status check reports `SUCCESS` (or `SKIPPED` for optional checks).
- Fail: any required check reports `FAILURE`, `ERROR`, or `PENDING` past its expected duration. Surface the failing check names in `detail`.

## Output format

Return exactly this shape to the main session:

```
verdict: pass | fail
checks:
  - name: <check-name>
    status: pass | fail
    detail: <one line or empty>
```

Do not include the raw `git status`, raw diff hunks, or full check logs in the returned summary — those stay in the fork. If the author wants to investigate a failed check, they can re-invoke the skill targeting that single check or run the underlying command themselves.

## Personalization

This skill is project-scoped (`.claude/skills/deploy-check/`) so the whole team runs the same pre-deploy checklist. A teammate who wants a stricter personal variant — say, one that additionally fails when the diff exceeds 500 lines without a long enough PR description — can create a parallel skill at `~/.claude/skills/deploy-check-strict/` under a different name. Their variant stays local, is never committed to the repo, and does not affect teammates.

## What this skill deliberately does not do

- It never pushes, deploys, or runs migrations. The `allowed-tools` allowlist is read-only by construction; even if a future maintainer adds `Write` here, the team's `/review` command should catch the change.
- It does not run the test suite. Tests have their own pre-merge gate in CI; duplicating that here would slow every deploy check without adding signal.
- It does not check for secrets in code. That's the job of the `gitleaks` pre-commit hook, which fails the commit, not the deploy.
