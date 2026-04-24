Archived from `.cursor/plans/CLAUDE_ONE_SHOT_CLEANUP_BRIEF.md` on 2026-04-23 so this historical cleanup brief is visible to all agents.

# One-shot cleanup brief for Claude (Global Macro Scanner)

This archived file preserves a bounded cleanup brief that originally lived under `.cursor/plans/`.
It is retained for historical context only and must not be used as a live workflow document.

## Purpose

Execute cleanup in small, reviewable batches with hard stop points.

Goals:

- remove verified junk first
- avoid speculative moves
- preserve historical-but-useful files
- keep docs accurate as paths change

## First read

Before doing anything else:

1. Open the canonical cleanup plan.
2. Read the policy section once.
3. Execute only the requested batch from the runbook.

## Preconditions

1. Working directory must be the repo root.
2. Use the project virtual environment for Python commands.
3. If `.venv` is missing, stop and report.
4. Do not edit `.env` or change DB credentials in this task.

## Multi-agent safety rules

Before moving or deleting files:

1. Check `git status --short`
2. If a target file already has local modifications, stop and report instead of relocating it
3. Check code references, doc references, and subprocess or path references

## Execution rules

- Complete one batch per session unless the maintainer explicitly says otherwise.
- Before deleting anything, list it first.
- Before moving any `.py` file, run a repo-wide reference check.
- If canonical ownership is ambiguous, skip and report evidence instead of guessing.

## Progress log

After each completed batch, append a short note to `docs/tasks/global_macro_cleanup_progress.md`.

## Stop conditions

Stop immediately and report on ambiguous results, merge conflicts, active local modifications, unclear canonical ownership, or verification evidence that a candidate is still used.
