---
name: ultracode-edit
description: Safely modify an initialized UltraCode repository configuration and its managed Codex or Claude Code projections. Use when the user explicitly invokes `$ultracode-edit`, wants to change project AI rules, commands, control visibility, status persistence, model or objective-driven reasoning policy, safety cap, roles, skills, or adapters, or needs to repair configuration drift without losing manual edits. Do not select this skill when the request explicitly invokes `$ultracode-help`; `edit` is then only a Help topic.
---

# UltraCode Edit

## Respect explicit Help precedence

If the request explicitly invokes `$ultracode-help` or `ultracode-help`, stop before diagnosis or
configuration work. Read `../ultracode-help/SKILL.md` and answer `edit` as a read-only Help topic.

Change the smallest configuration surface and regenerate only affected managed artifacts. Preserve user-authored content and make drift visible.

## Load and diagnose read-only

Read completely:

- `../ultracode/references/project-adapter.md`
- `../ultracode/references/command-interface.md`
- `../ultracode/references/control-and-status.md`
- `../ultracode/references/swarm-protocol.md`
- `../ultracode/references/reasoning-routing.md`
- `../ultracode/references/project-config.schema.json`
- `../ultracode/references/managed-manifest.schema.json`

Then read `.ultracode/config.json`, `.ultracode/managed.json`, active `AGENTS.md`, and enabled adapter trees. Run the available `project_doctor.py` or `project_doctor.ps1` before editing. If UltraCode is not initialized, route to `$ultracode-init`. Classify the request as config-only, documentation, adapter regeneration, role or skill change, schema migration, or drift repair. Inspect Git status and preserve pre-existing changes.

## Resolve intent and drift

When the change is incomplete, ask one to three concise questions. Never ask for an agent count.
Allow changes to model policy, objective-driven reasoning defaults and floors, visibility,
persistence, approval gates, technical concurrency, adapters, stable roles, commands, or the
safety circuit breaker. `data-driven` decomposition, objective-based effort selection, one verifier
per material finding, and one synthesis are protocol invariants; changing them requires a plugin or
schema migration, not a project edit.

Use `.ultracode/managed.json` to compare current SHA-256 values:

- unchanged managed artifact: safe to regenerate;
- edits outside a managed block: preserve automatically;
- edits inside a managed block or a changed generated file: show the conflict and ask whether to adopt the manual content into the canonical source, replace the projection, or leave it untouched;
- missing adapter: recreate only when its adapter remains enabled;
- unknown file: never claim ownership.

Do not silently overwrite drift, broaden ownership, lower authority gates, enable external actions, or change tracked/local persistence.

## Preview and apply

Resolve a Python interpreter without changing dependencies. Try the repository's verified Python
command first. In Codex Desktop, if Python is not on `PATH`, call
`codex_app.load_workspace_dependencies` and use the returned bundled Python executable. Never persist its
machine-local absolute path. If no interpreter is available, report the configurator as
`NOT AVAILABLE` and stop before writes.

Build the edit proposal from the diagnosed state and run `../ultracode/scripts/project_configurator.py plan --project-root <project-root> --proposal <proposal.json>`. Before writing, show its `plan_id`, config delta, affected canonical files, projections to regenerate, preserved files, conflicts, and validation plan. Plan before apply and respect repository confirmation rules.

Explain the delta in plain language before technical detail. Show:

1. the requested outcome;
2. each meaningful setting as `before -> after`, with its practical effect;
3. canonical content that changes and projections regenerated from it;
4. manual content and unrelated files that remain untouched;
5. drift or conflicts, why they matter, and the available resolution;
6. checks that will prove the edit succeeded;
7. the exact write awaiting confirmation.

Do not reduce a conflict to a hash mismatch or a raw path. Explain what changed, who owns it, and
why UltraCode stopped.

Run `project_configurator.py apply` with the unchanged proposal and confirmed plan only. If managed content, filesystem ownership, path safety, or the plan preconditions changed, stop on `CONFLICT` or `FAILED`; do not reinterpret the request or overwrite drift.

Apply in this order:

1. update `.ultracode/config.json` while preserving unknown forward-compatible keys;
2. update canonical content in `AGENTS.md` and `.agents`;
3. regenerate only dependent `.codex` and `.claude` projections;
4. recompute affected entries in `.ultracode/managed.json`;
5. update status persistence only with the required authority;
6. never touch local settings, locks, credentials, caches, or unrelated project code.

If disabling an adapter would remove files: Do not delete automatically. Present the exact managed paths and require explicit deletion scope; otherwise disable the adapter and leave files in place with a warning. The configurator performs no automatic delete.

## Validate and report

Run the project doctor again, inspect the final diff, and distinguish `PASSED`, `DRIFT`,
`FAILED`, and `NOT RUN`. Explain each non-passing state in the user's language. Report the
outcome first, what changed, its practical effect, what manual content was preserved, which
projections were regenerated, remaining unknowns, and whether a new Codex or Claude session is
needed to reload changed skills or agents.
