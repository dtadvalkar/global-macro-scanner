# Multi-Agent Project Bootstrap Guide

Use this guide at the start of any software project when you want Claude, Codex, Cursor, Gemini, Copilot, or future agents to work in the same repository without stepping on each other, losing context, or leaving hidden state behind.

The goal is simple:

- any agent can enter cold
- understand the project quickly
- find the current task
- see what has already been tried
- continue work safely
- hand off cleanly if interrupted

This guide is intentionally project-agnostic. Drop it into the root of a repo, adapt the placeholders, and use it to establish collaboration discipline from day one.

Assumptions:

- Git is the version-control system unless explicitly replaced.
- Repo-root examples assume a branch-based workflow.
- Technology examples use Python where useful, but the workflow applies equally to JavaScript / TypeScript, Go, Ruby, Java, or mixed-language repos.

## Core principle

Agents should collaborate through repo-visible files, not through proprietary memory, chat history, or tool-specific hidden folders.

If the next agent cannot discover the state of the work by reading the repository, the workflow is not yet reliable.

## Non-negotiable rules

1. One shared contract file must exist at the repo root.
2. Any agent-specific instruction files must defer to that shared contract.
3. In-progress work must be documented in git-tracked files.
4. Partial work must always leave a handoff note before the agent stops.
5. Canonical setup, entrypoints, and task ledgers must be easy to find from the root.
6. No important shared context should live only in ignored folders such as `.cursor/`, `.claude/`, `.aider/`, local IDE memory, or chat transcripts.

## What this guide is for

This file is a bootstrap tool, not the permanent shared contract.

Recommended lifecycle:

1. Drop this guide into a new repo at the beginning.
2. Use it to create and align `AGENTS.md`, task docs, and handoff conventions.
3. Once the project-specific collaboration contract is stable, archive this file under `docs/archive/` or remove it.
4. After bootstrapping, `AGENTS.md` should be the authoritative shared contract.

## Recommended root files

These are the minimum files and folders that make multi-agent work predictable:

- `AGENTS.md`
  Shared contract for all agents.
- `README.md`
  Canonical setup and usage guide.
- `DEVELOPMENT.md`
  Engineering workflow, architecture notes, and coding constraints.
- `.env.example`
  Environment variable template derived from actual code, not memory.
- `docs/master_development_plan.md`
  Canonical task ledger or roadmap when the project uses an in-repo ledger.
- `docs/tasks/`
  Shared plans, findings, progress notes, and handoff artifacts.
- `docs/archive/`
  Historical plans and retired one-off docs.

Optional overlays:

- `CLAUDE.md`
- `.cursorrules`
- `GEMINI.md`
- `.github/copilot-instructions.md`

These should be thin overlays, not competing sources of truth.

Language-specific equivalents are fine:

- Python: `.venv`, `requirements.txt`, `pyproject.toml`
- JavaScript / TypeScript: `package.json`, `pnpm-lock.yaml`, `turbo.json`
- Go: `go.mod`
- Java: `pom.xml`, `build.gradle`

The collaboration pattern matters more than the exact stack.

## Recommended collaboration folder structure

```text
repo-root/
  AGENTS.md
  README.md
  DEVELOPMENT.md
  .env.example
  docs/
    master_development_plan.md
    tasks/
      _progress_template.md
      _plan_template.md
      _findings_template.md
    archive/
```

## What goes in `AGENTS.md`

`AGENTS.md` should be the single shared contract across all agents. It should answer:

- what this repo is
- what the real project root is
- what the canonical entrypoints are
- what the canonical setup path is
- where current work is tracked
- how to start a session
- how to end a session
- how to leave a handoff if work is partial
- where the source of truth lives if the task ledger is external

Keep it short enough to scan, but concrete enough to prevent ambiguity.

## Starter `AGENTS.md` template

Copy and adapt this:

```md
# AGENTS.md — Shared Contract for Coding Agents

This is the shared project contract for all coding agents working in this repository.

## Project identity

- Repository root: `[describe the real project root]`
- Primary entrypoint: `[main command or file]`
- Secondary entrypoints: `[only if validated]`

## Environment and dependencies

- Canonical environment: `[.venv / nvm / mise / asdf / container / other]`
- Canonical dependency file: `[requirements.txt / pyproject.toml / package.json / go.mod / pom.xml / etc.]`
- Canonical secrets file: `[.env or equivalent]`
- Canonical env template: `.env.example`

## Canonical docs

- `README.md`: setup and usage
- `DEVELOPMENT.md`: engineering workflow
- `docs/master_development_plan.md`: task ledger, if the ledger is in-repo
- `docs/tasks/`: shared plans, findings, and progress notes

If the real task ledger is external, link it here explicitly and explain how agents should read and update it.

## Start of session

1. Read `AGENTS.md`.
2. Read the relevant overlay if one exists.
3. Run `git log --oneline -20`.
4. Run `git status --short`.
5. Read the canonical task ledger.
6. Check `docs/tasks/` for open `*_plan.md`, `*_progress.md`, and `*_findings.md`.

## End of session

1. Update `docs/master_development_plan.md` if status changed.
2. If work is partial, create or update a `docs/tasks/*_progress.md` note before stopping.
3. Do not leave critical context only in chat history or proprietary memory.
4. Use clear commit messages.

## Partial-work handoff discipline

- Unfinished work must leave a repo-visible handoff note.
- Use `docs/tasks/_progress_template.md` when starting a new progress note.
- Include files touched, commands run, blockers, and the next recommended step.
- If the worktree is already dirty, do not assume those changes are yours.
- Before editing a shared progress note, sync or inspect the latest repo state so you do not overwrite another agent's handoff.
```

## What goes in agent-specific overlays

Only keep things that are genuinely specific to that agent:

- tool behavior
- planning quirks
- IDE-specific features
- output formatting constraints
- memory caveats

Do not duplicate:

- project root
- setup instructions
- canonical task ledger
- handoff location
- architecture map

If those are repeated across multiple files, they will drift.

## Recommended rules for shared task state

Use `docs/master_development_plan.md` for the high-level roadmap and task status when the project keeps that ledger in the repo.

If the real source of truth is external, such as GitHub Issues, Linear, Jira, or another tracker, `AGENTS.md` must link to it and explain:

- where to look
- how to interpret task state
- whether agents should mirror important context back into repo docs

Use `docs/tasks/` for work-in-progress artifacts:

- `*_plan.md`
  For scoped implementation plans.
- `*_progress.md`
  For partial-work handoffs and execution state.
- `*_findings.md`
  For experiments, benchmarks, investigation notes, and lessons learned.

This separation matters:

- the master plan explains what the project is doing overall
- task docs explain what happened during the current slice of work

## Required handoff discipline

This is the rule that makes interruption-safe collaboration possible.

Whenever an agent stops before the work is fully finished, it must leave or update a `*_progress.md` note in `docs/tasks/`.

Before updating a shared progress note:

- inspect the current worktree
- inspect the latest version of the note
- do not overwrite another agent's handoff blindly
- if necessary, append a new dated section instead of rewriting someone else's state

That note should include:

- task name
- date
- owner or agent name in a stable format such as `tool-name (model-if-known)`
- current status
- files touched
- commands run
- what changed
- blockers or failures
- next recommended step
- any unrelated local changes that the next agent should not overwrite

If this rule is consistently followed, another agent can resume the work with very little friction.

## Starter progress-note template

Create `docs/tasks/_progress_template.md` with something like this:

```md
# Progress Note Template

## Task

- Short task name:
- Owner / agent: `tool-name (model-if-known)`
- Date:

## Status

- Current status:
- Confidence:

## Files touched

- `path/to/file`

## Commands run

```text
command here
```

## What changed

- Brief summary of work completed so far.

## Blockers or failures

- What failed, if anything.
- What remains uncertain.

## Next recommended step

- The best next action for the next agent to take.

## Notes for the next agent

- Mention unrelated local changes, risky areas, or verification gaps.
```

## Hidden state to eliminate early

At the start of a project, look for tool-specific locations where important work might otherwise disappear:

- `.cursor/plans/`
- `.claude/`
- `.aider*`
- `.continue/`
- editor-only scratchpads
- ignored planning folders

You do not need to ban these tools. You only need to ensure that anything another agent will need is copied into visible, git-tracked docs.

Important distinction:

- shared context such as plans, findings, and progress must be git-tracked
- private tool settings, permission caches, and local convenience files can remain private

Examples of legitimate private state:

- `.claude/settings.local.json`
- editor keybindings or workspace settings
- local approval caches
- personal shell history

## Environment hygiene

Create `.env.example` from the source code that actually reads environment variables.

Do not build it from memory.

Check:

- settings modules
- config loaders
- startup scripts
- deployment manifests

This avoids the common failure where documentation says a variable exists but the code expects a different one.

Examples by stack:

- Python: settings modules, `os.getenv`, dotenv loaders
- JavaScript / TypeScript: `process.env`, config wrappers, framework env loaders
- Go: config packages, env readers, startup wiring
- Java: Spring config, environment property readers

## Commit and worktree hygiene

To keep multi-agent work safe:

- inspect `git status --short` before multi-file edits
- sync with the latest repo state before editing shared handoff docs when possible
- do not overwrite unrelated local changes
- do not assume uncommitted changes are yours
- do not leave broad refactors half-explained
- do not rename or relocate canonical files casually

If the worktree is dirty and the intent is unclear, leave a note in the progress doc.

## Documentation hygiene

At project start, make the hierarchy explicit:

- `README.md` explains setup and usage
- `DEVELOPMENT.md` explains engineering expectations
- `AGENTS.md` explains multi-agent collaboration
- `docs/master_development_plan.md` tracks roadmap and task status
- `docs/tasks/` tracks active work
- `docs/archive/` stores historical context

If multiple files all try to explain the same thing, drift will happen.

## Recommended startup checklist for a new project

When bootstrapping a new repo, do this early:

1. Create `AGENTS.md`.
2. Create `.env.example` from actual code.
3. Create `docs/master_development_plan.md`.
4. Create `docs/tasks/` and `docs/archive/`.
5. Add `_progress_template.md` under `docs/tasks/`.
6. Add thin agent overlays only if needed.
7. Remove or stop relying on hidden planning state.
8. Make sure `README.md`, `DEVELOPMENT.md`, and `AGENTS.md` point to the same canonical paths.

Optional but recommended:

9. Add one short example of a past handoff failure or drift problem the project wants to avoid.

## Recommended audit checklist for an existing project

If the repo already exists, audit it with these questions:

- Is there one clear shared contract file?
- Does every active doc agree on the project root?
- Are setup instructions accurate today?
- Is there a visible master task ledger?
- Is there a shared place for in-progress work?
- Are any active plans trapped in ignored folders?
- Could a new agent resume work after an interruption without asking for hidden context?

Any “no” answer identifies a handoff risk.

## Common failure mode to avoid

One of the most common multi-agent failures is duplicated guidance drifting over time.

Typical example:

- one file says the project root is `app/`
- another file says the project root is the repository root
- a third file points to an outdated setup path

The result is wasted time, incorrect edits, and broken handoffs.

The fix is simple:

- keep one shared contract file
- keep overlays thin
- correct stale docs before promoting them as authoritative

## Definition of success

You know the setup is working when this is true:

- a fresh agent can enter the repo and find the correct instructions quickly
- the current task is discoverable from repo files
- partial work is documented before an agent stops
- another agent can continue without guessing what happened
- no important context is trapped in private memory or hidden folders

That is the standard to aim for in every new project.
