---
name: ultracode-edit
description: Safely modify an initialized UltraCode repository configuration and its managed Codex or Claude Code projections. Use when the user explicitly invokes `$ultracode-edit`, wants to change project AI rules, commands, control visibility, status persistence, model policy, safety cap, roles, skills, or adapters, or needs to repair configuration drift without losing manual edits.
---

# UltraCode Edit

Change the smallest configuration surface and regenerate only affected managed artifacts. Preserve user-authored content and make drift visible.

## Load and diagnose read-only

Read completely:

- `../ultracode/references/project-adapter.md`
- `../ultracode/references/control-and-status.md`
- `../ultracode/references/swarm-protocol.md`
- `../ultracode/references/project-config.schema.json`
- `../ultracode/references/managed-manifest.schema.json`

Then read `.ultracode/config.json`, `.ultracode/managed.json`, active `AGENTS.md`, and enabled adapter trees. Run the available `project_doctor.py` or `project_doctor.ps1` before editing. If UltraCode is not initialized, route to `$ultracode-init`. Classify the request as config-only, documentation, adapter regeneration, role or skill change, schema migration, or drift repair. Inspect Git status and preserve pre-existing changes.

## Resolve intent and drift

When the change is incomplete, ask one to three concise questions. Never ask for an agent count. Allow changes to model policy, visibility, persistence, approval gates, technical concurrency, adapters, stable roles, commands, or the safety circuit breaker. `data-driven` decomposition, one verifier per material finding, and one synthesis are protocol invariants; changing them requires a plugin or schema migration, not a project edit.

Use `.ultracode/managed.json` to compare current SHA-256 values:

- unchanged managed artifact: safe to regenerate;
- edits outside a managed block: preserve automatically;
- edits inside a managed block or a changed generated file: show the conflict and ask whether to adopt the manual content into the canonical source, replace the projection, or leave it untouched;
- missing adapter: recreate only when its adapter remains enabled;
- unknown file: never claim ownership.

Do not silently overwrite drift, broaden ownership, lower authority gates, enable external actions, or change tracked/local persistence.

## Preview and apply

Before writing, show the config delta, affected canonical files, projections to regenerate, preserved files, and validation plan. Respect repository confirmation rules.

Apply in this order:

1. update `.ultracode/config.json` while preserving unknown forward-compatible keys;
2. update canonical content in `AGENTS.md` and `.agents`;
3. regenerate only dependent `.codex` and `.claude` projections;
4. recompute affected entries in `.ultracode/managed.json`;
5. update status persistence only with the required authority;
6. never touch local settings, locks, credentials, caches, or unrelated project code.

If disabling an adapter would remove files: Do not delete automatically. Present the exact managed paths and require explicit deletion scope; otherwise disable the adapter and leave files in place with a warning.

## Validate and report

Run the project doctor again, inspect the final diff, and distinguish `PASSED`, `DRIFT`, `FAILED`, and `NOT RUN`. Report what changed, what manual content was preserved, which projections were regenerated, remaining unknowns, and whether a new Codex or Claude session is needed to reload changed skills or agents.
