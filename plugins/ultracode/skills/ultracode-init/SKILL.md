---
name: ultracode-init
description: Guided, safe initialization of UltraCode project control for Codex and Claude Code. Use when the user explicitly invokes `$ultracode-init`, asks to adopt UltraCode in a repository, or wants shared AI documentation, rules, skills, reviewers, model and objective-driven reasoning policy, configuration, and status structure generated from the real project without copying machine-local settings.
---

# UltraCode Init

Initialize the current repository through inspection, a short interview, a reviewable proposal, and idempotent writes. Never clone another project's domain facts.

## Read the canonical protocol

Read these sibling resources completely before proposing files:

- `../ultracode/references/project-adapter.md`
- `../ultracode/references/command-interface.md`
- `../ultracode/references/control-and-status.md`
- `../ultracode/references/swarm-protocol.md`
- `../ultracode/references/reasoning-routing.md`
- `../ultracode/references/project-config.schema.json`
- `../ultracode/references/managed-manifest.schema.json`

Follow active repository instructions. Invoking this skill authorizes a configuration proposal, not arbitrary code changes, Git operations, dependency changes, or overwriting existing AI guidance.

## Inspect before asking

Work read-only first:

1. Find repository roots, active `AGENTS.md` files, manifests, source and test roots, CI, build files, existing docs, and Git status.
2. Inspect existing `.ultracode`, `.agents`, `.codex`, `.claude`, `CLAUDE.md`, and `CLAUDE.local.md` structures.
3. Detect real commands and label each `VERIFIED`, `INFERRED`, or `UNKNOWN`. Explain these as
   confirmed by evidence, found but not executed, or not verifiable. Do not execute write-producing
   commands merely to discover them.
4. Detect user-owned or generated files. Never import local settings, permission allowlists, locks, PIDs, credentials, absolute paths, caches, or session artifacts.
5. If a valid `.ultracode/config.json` already exists, stop initialization and route the request to `$ultracode-edit` unless the user explicitly requests a migration or repair.

## Run the guided interview

Propose detected answers and ask only what cannot be safely inferred. Use the product's structured question mechanism when available; otherwise ask concise questions. Ask one to three related questions per turn.

When `$ultracode` enters this skill automatically for change work in an uninitialized project, use
**baseline preflight mode** instead of the full interview:

- preserve the original task and return to it after initialization;
- infer project name, mission, stack, targets, commands, and minimal canonical context from current
  repository evidence;
- use conservative defaults: confirmation before writes, phase-and-barrier updates, standard
  detail, visible jobs/files/checks, conversation-only status, explicit-only sensitive authority,
  data-driven decomposition, automatic concurrency, safety cap `1000`, inherited lead model,
  `gpt-5.6-terra` bounded agents, `gpt-5.6-sol` verifiers, objective-driven reasoning with `low`
  bounded default, `high` material-verifier minimum, `xhigh` critical minimum, maximum `ultra`, and
  model-policy fallback `inherit`;
- enable the Codex adapter; enable Claude only when existing project evidence or the user request
  shows that Claude is in scope;
- mark discovered but unexecuted commands `INFERRED`; do not run them merely to upgrade evidence;
- do not create optional rules, roles, or skills without a recurring need;
- generate the deterministic proposal immediately and bundle reversible assumptions into its
  explanation;
- ask a separate question only when a protected boundary or material ambiguity makes the proposal
  unsafe. Otherwise ask once for confirmation of the complete initialization plan.

Cover:

1. project name, mission, supported target, and non-goals;
2. stack, source/test/generated/local-only areas, architecture invariants, and real commands;
3. completion evidence and high-risk actions requiring confirmation;
4. adapters: Codex, Claude Code, or both; default to both when requested;
5. control profile: plan gate, commentary detail, update cadence, visible agents/files/checks, and status persistence (`conversation-only`, `local`, or `tracked`);
6. model policy by role (`strongest-available`, `balanced-available`, or `inherit`), or exact model IDs when the user explicitly supplies them; record the exact ID but use it only when the runtime exposes it, otherwise apply the configured fallback and report the effective model;
7. objective-driven reasoning policy: bounded default, material-verifier and critical floors, and
   maximum effort. Explain that UltraCode scores each bounded job rather than fixing one effort for
   the entire swarm;
8. stable project roles or specialist skills only when a recurring bounded workflow justifies them.

Do not ask how many swarm agents to use. Explain that problem structure derives logical jobs; concurrency is a platform limit; `hard_safety_cap` is only a circuit breaker. Default the cap to `1000` unless project policy requires a lower safety bound.

## Present the proposal before writing

Resolve a Python interpreter without changing dependencies. Try the repository's verified Python
command first. In Codex Desktop, if Python is not on `PATH`, call
`codex_app.load_workspace_dependencies` and use the returned bundled Python executable. Never persist its
machine-local absolute path in project files. If no interpreter is available, report the
configurator as `NOT AVAILABLE` and stop before writes; do not replace the deterministic plan with
hand-authored files.

Create the deterministic read-only preview with `../ultracode/scripts/project_configurator.py plan --project-root <project-root> --proposal <proposal.json>`. The proposal contains the complete desired config and every canonical file; generated adapters, managed blocks, and the manifest are derived. Show confirmed project facts, unresolved unknowns, the returned `plan_id`, exact files or managed blocks, conflicts, canonical sources versus generated adapters, status persistence, roles or skills, and command evidence. Plan before apply and respect repository confirmation gates. If existing content conflicts with the proposal, stop and ask which rule should remain.

Explain the proposal in plain language before showing technical paths. Separate:

1. what UltraCode discovered from the repository;
2. choices already confirmed by the user;
3. what will be created or changed and why;
4. existing content that will be preserved;
5. conflicts or unknowns that need a decision;
6. checks that will prove initialization succeeded;
7. the exact write awaiting confirmation.

Do not present a raw plan ID or file list as if it explained the proposal.

## Generate safely

Use the layout and marker rules in `project-adapter.md`. Apply the confirmed plan only with `project_configurator.py apply`, passing the unchanged proposal and confirmed `plan_id`. Never hand-edit derived adapters around the configurator or reinterpret a stale plan.

1. Create `.ultracode/config.json` conforming to `project-config.schema.json`, including its complete canonical `artifacts` registry.
2. Create `.ultracode/managed.json` conforming to `managed-manifest.schema.json`, with SHA-256 records for the config and every generated file or managed block.
3. Add or update only the UltraCode managed block in `AGENTS.md`; preserve all content outside it.
4. Create canonical shared guidance under `.agents/context`, `.agents/rules`, `.agents/reviewers`, and `.agents/skills` only when needed.
5. Generate Codex projections under `.codex/agents` and Claude projections under `.claude`. Use `.claude/CLAUDE.md` to import `@../AGENTS.md`; do not duplicate the root contract.
6. Keep `.codex/config.toml` absent unless a verified Codex-specific setting is required. Never place Claude settings there.
7. Never create or modify `.claude/settings.local.json`, `CLAUDE.local.md`, scheduled-task locks, permission allowlists, or machine-local credentials.
8. For `local` status persistence, request explicit permission before adding `.ultracode/status.md` to `.git/info/exclude`; never silently edit `.gitignore`.
9. Generate no empty role, rule, or skill merely to make the tree look complete.
10. Perform no automatic delete. Disabling an adapter leaves old managed files in place until the user authorizes exact removal paths.

Prefer patch-based, localized edits. Never overwrite an existing whole file when a managed block or new adapter suffices.

## Validate and hand off

Run the available project doctor from the sibling UltraCode skill:

- Python: `../ultracode/scripts/project_doctor.py <project-root>`
- Windows PowerShell: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ../ultracode/scripts/project_doctor.ps1 -ProjectRoot <project-root>`

Then inspect the final diff and confirm no local or session files entered the tracked surface. Report
the outcome first, then created files, preserved files, unknown commands, status mode, adapter
state, evidence, and any drift or blocker. Explain what each unknown or blocker means and what is
needed next. Tell the user that `$ultracode-edit` changes the setup, `$ultracode-flow` gives the
quick live view, `$ultracode-status` gives the detailed diagnostic view, and `$ultracode-help`
explains commands, models, reasoning, and examples read-only.
