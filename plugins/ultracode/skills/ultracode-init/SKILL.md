---
name: ultracode-init
description: Guided, safe initialization of UltraCode project control for Codex and Claude Code. Use when the user explicitly invokes `$ultracode-init`, asks to adopt UltraCode in a repository, or wants a shared AI documentation, rules, skills, reviewer, configuration, and status structure generated from the real project without copying machine-local settings.
---

# UltraCode Init

Initialize the current repository through inspection, a short interview, a reviewable proposal, and idempotent writes. Never clone another project's domain facts.

## Read the canonical protocol

Read these sibling resources completely before proposing files:

- `../ultracode/references/project-adapter.md`
- `../ultracode/references/control-and-status.md`
- `../ultracode/references/swarm-protocol.md`
- `../ultracode/references/project-config.schema.json`
- `../ultracode/references/managed-manifest.schema.json`

Follow active repository instructions. Invoking this skill authorizes a configuration proposal, not arbitrary code changes, Git operations, dependency changes, or overwriting existing AI guidance.

## Inspect before asking

Work read-only first:

1. Find repository roots, active `AGENTS.md` files, manifests, source and test roots, CI, build files, existing docs, and Git status.
2. Inspect existing `.ultracode`, `.agents`, `.codex`, `.claude`, `CLAUDE.md`, and `CLAUDE.local.md` structures.
3. Detect real commands and label each `VERIFIED`, `INFERRED`, or `UNKNOWN`. Do not execute write-producing commands merely to discover them.
4. Detect user-owned or generated files. Never import local settings, permission allowlists, locks, PIDs, credentials, absolute paths, caches, or session artifacts.
5. If a valid `.ultracode/config.json` already exists, stop initialization and route the request to `$ultracode-edit` unless the user explicitly requests a migration or repair.

## Run the guided interview

Propose detected answers and ask only what cannot be safely inferred. Use the product's structured question mechanism when available; otherwise ask concise questions. Ask one to three related questions per turn.

Cover:

1. project name, mission, supported target, and non-goals;
2. stack, source/test/generated/local-only areas, architecture invariants, and real commands;
3. completion evidence and high-risk actions requiring confirmation;
4. adapters: Codex, Claude Code, or both; default to both when requested;
5. control profile: plan gate, commentary detail, update cadence, visible agents/files/checks, and status persistence (`conversation-only`, `local`, or `tracked`);
6. model policy by role (`strongest-available`, `balanced-available`, or `inherit`), never brittle model IDs unless the user explicitly supplies them;
7. stable project roles or specialist skills only when a recurring bounded workflow justifies them.

Do not ask how many swarm agents to use. Explain that problem structure derives logical jobs; concurrency is a platform limit; `hard_safety_cap` is only a circuit breaker. Default the cap to `1000` unless project policy requires a lower safety bound.

## Present the proposal before writing

Show confirmed project facts, unresolved unknowns, exact files or managed blocks, canonical sources versus generated adapters, status persistence, roles or skills, and command evidence. Respect repository confirmation gates. If existing content conflicts with the proposal, show the conflict and ask which rule should remain.

## Generate safely

Use the layout and marker rules in `project-adapter.md`.

1. Create `.ultracode/config.json` conforming to `project-config.schema.json`, including its complete canonical `artifacts` registry.
2. Create `.ultracode/managed.json` conforming to `managed-manifest.schema.json`, with SHA-256 records for the config and every generated file or managed block.
3. Add or update only the UltraCode managed block in `AGENTS.md`; preserve all content outside it.
4. Create canonical shared guidance under `.agents/context`, `.agents/rules`, `.agents/reviewers`, and `.agents/skills` only when needed.
5. Generate Codex projections under `.codex/agents` and Claude projections under `.claude`. Use `.claude/CLAUDE.md` to import `@../AGENTS.md`; do not duplicate the root contract.
6. Keep `.codex/config.toml` absent unless a verified Codex-specific setting is required. Never place Claude settings there.
7. Never create or modify `.claude/settings.local.json`, `CLAUDE.local.md`, scheduled-task locks, permission allowlists, or machine-local credentials.
8. For `local` status persistence, request explicit permission before adding `.ultracode/status.md` to `.git/info/exclude`; never silently edit `.gitignore`.
9. Generate no empty role, rule, or skill merely to make the tree look complete.

Prefer patch-based, localized edits. Never overwrite an existing whole file when a managed block or new adapter suffices.

## Validate and hand off

Run the available project doctor from the sibling UltraCode skill:

- Python: `../ultracode/scripts/project_doctor.py <project-root>`
- Windows PowerShell: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ../ultracode/scripts/project_doctor.ps1 -ProjectRoot <project-root>`

Then inspect the final diff and confirm no local or session files entered the tracked surface. Report created files, preserved files, unknown commands, status mode, adapter state, and any drift or blocker. Tell the user that `$ultracode-edit` changes the setup and `$ultracode-status` explains live work.
