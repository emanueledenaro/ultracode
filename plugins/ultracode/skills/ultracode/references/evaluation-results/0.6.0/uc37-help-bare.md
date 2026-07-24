# UC-37: bare Help

## Evaluation context

- Evaluation date: 2026-07-24
- Worktree payload: UltraCode `0.6.0+codex.20260724065223`
- Installed cache observed during evaluation: UltraCode `0.5.3+codex.20260724011735`
- Mode: read-only behavioral evaluation; no project tests or builds

## Raw request

```text
Use $ultracode-help
```

## Full raw response

~~~markdown
# UltraCode command guide

## Quick choice

| Your goal | Use |
| --- | --- |
| Explain, compare, or see examples | `$ultracode-help` |
| Investigate, build, fix, or run engineering work | `$ultracode` |
| Create durable evidence that a feature works | `$ultracode-verify` |
| Add UltraCode project control | `$ultracode-init` |
| Change existing UltraCode control or repair drift | `$ultracode-edit` |
| Quickly view work in progress | `$ultracode-flow` |
| Inspect detailed state, evidence, and blockers | `$ultracode-status` |

Choose the least powerful command that satisfies the outcome: Help explains; Flow and Status observe; Verify records feature-level proof; Init configures; Edit changes configuration; UltraCode performs engineering work.

## The seven commands

### `$ultracode-help`

**When to use it:** When choosing where to start, comparing commands, learning model policy, or requesting safe examples.

**What you get:** An explanation or recommendation, without executing work or refreshing live task state.

**Can it write?:** No. It never writes, initializes, delegates, tests, or builds.

**When confirmation is required:** Never.

> **Example:** `Use $ultracode-help to explain all seven commands and recommend where I should start.`

### `$ultracode`

**When to use it:** For implementations, fixes, migrations, refactors, broad audits, difficult diagnoses, or another accountable engineering outcome.

**What you get:** The requested outcome, visible jobs when useful, changed files, checks actually run, evidence, blockers, and unknowns.

**Can it write?:** Yes, when the requested and authorized outcome requires changes. Answers, reviews, audits, and diagnoses remain read-only unless a fix is requested.

**When confirmation is required:** According to the project plan gate. Git, dependencies, external actions, destructive operations, and deployment require separate explicit authority.

> **Example:** `Use $ultracode to fix the failing payment webhook tests. Do not commit, deploy, or install dependencies.`

### `$ultracode-verify`

**When to use it:** To define feature acceptance scenarios, prove behavior with direct evidence, preserve repeated verification attempts, or diagnose incomplete functional coverage.

**What you get:** A durable closed JSON plan with acceptance criteria, append-only scenario results, exact evidence sources, and a derived verified, failed, or incomplete outcome.

**Can it write?:** Inspection is read-only. Creating a plan or appending a result writes only the authorized plan artifact; it does not initialize project control or automatically change product code.

**When confirmation is required:** The request and project plan gate must authorize plan writes. Git, publishing, external requests, deployment, dependencies, destructive operations, and production actions require separate authority.

> **Example:** `Use $ultracode-verify to create a durable verification plan for checkout recovery. Do not deploy, publish, or make external requests.`

### `$ultracode-init`

**When to use it:** When a repository has no UltraCode project control and you want shared, repeatable guidance and supported adapters.

**What you get:** First, an exact read-only proposal with a stable plan ID, files, effects, and preservation boundaries. After confirmation, it can initialize and validate the project.

**Can it write?:** Yes, but discovery and planning are read-only. Only the apply phase changes managed project-control files.

**When confirmation is required:** Once, before applying the initialization. Without confirmation, the repository remains unchanged.

> **Example:** `Use $ultracode-init to inspect this repository and show the exact setup proposal. Do not apply it yet.`

### `$ultracode-edit`

**When to use it:** To change initialized rules, validation commands, visibility, status policy, model policy, adapters, roles, safety controls, or repair managed-content drift.

**What you get:** A before-and-after delta, affected projections, preserved content, conflicts, and validation evidence after an approved apply.

**Can it write?:** Yes, but diagnosis and planning are read-only. Only the apply phase changes the confirmed configuration and projections.

**When confirmation is required:** Before applying a still-current plan. Drift or stale preconditions stop the apply.

> **Example:** `Use $ultracode-edit to change status detail to concise. Show the delta and wait for confirmation.`

### `$ultracode-flow`

**When to use it:** To quickly understand the objective, phase, active or blocked tickets, owners, observable agents and models, completion criteria, and next action.

**What you get:** A compact snapshot with explicit freshness and unknowns.

**Can it write?:** No. It does not initialize, delegate, resume work, run checks, or write status.

**When confirmation is required:** Never.

> **Example:** `Use $ultracode-flow to show active tickets, blockers, and the next action.`

### `$ultracode-status`

**When to use it:** When Flow is insufficient and you need detailed jobs, files, checks, evidence, drift, blockers, history, or reasons a claim cannot be verified.

**What you get:** A diagnostic report distinguishing live, stale, missing, failed, blocked, and verified information.

**Can it write?:** No. It does not run checks or modify state merely to refresh its report.

**When confirmation is required:** Never.

> **Example:** `Use $ultracode-status to explain why validation is blocked and show the available evidence.`

## Unconfigured projects

Read-only Help, Flow, Status, answers, reviews, audits, and diagnoses work without `.ultracode`; inspection does not trigger initialization.

Verify can inspect an existing verification plan without project control. An authorized default verification artifact under `.ultracode/verification/` does not itself initialize project control.

For requested change work, `$ultracode` preserves the original objective and enters a read-only Init preflight. It presents the exact initialization proposal and asks before writing. If confirmed, it validates the initialized state and resumes the original objective; otherwise everything remains read-only.

## Models and reasoning effort

| Role | Default request |
| --- | --- |
| New lead task | Sol with `medium` effort |
| Active lead task | Inherit its chat’s model and effort |
| Normal bounded worker | Terra with `low` effort |
| Material verifier | Sol with at least `high` |
| Critical work | At least `xhigh` |

Sol with `medium` is startup guidance only when the user can choose settings before opening a new lead task. UltraCode cannot replace the model or effort of an active task or change global defaults without a separate explicit request.

Workers normally request Terra `low`; ambiguity or consequence can justify more effort. Material verification requests Sol at least `high`. Security, data-integrity, migration, irreversible, external, privileged, or release-critical work uses at least `xhigh`.

Requested model and effort express routing intent. Effective values are what the runtime actually assigns; fallback is the route used when a request cannot be honored. Effective values and fallback must be reported only when observable. No current effective runtime values are asserted here.

## Tickets and agents

| Concept | Meaning |
| --- | --- |
| Ticket | A bounded logical job with an accountable owner |
| Agent | A runtime instance that actually exists and is attached to work |

Queued work can have a ticket and owner without a live agent. UltraCode must not invent agents, models, effort, or parallel identifiers.

## Authorization boundaries

Implementation approval does not authorize Git staging, commits, pushes, pull requests, deployment, dependency changes, external actions, destructive operations, privileged actions, or credential use. Each protected boundary requires explicit authority, and read-only commands never acquire write authority from configuration.
~~~

## Evaluation verdict

**Worktree payload: PASS.**

The worktree response:

- selects the complete overview for the bare invocation;
- preserves the required six content areas in semantic order;
- includes all seven commands in the required order;
- gives every command the four required labeled fields;
- places one copyable blockquote example directly in every command subsection;
- includes the required two-column quick-choice table;
- includes compact model-routing and ticket-versus-agent tables;
- distinguishes startup guidance, inheritance, requested versus effective routing, fallback, and runtime visibility;
- preserves the read-only and explicit-authority boundaries without inventing runtime state.

**Currently installed payload: FAIL for the seven-command criterion.**

The verdict above is specifically for the worktree `0.6.0` payload. The installed
`0.5.3+codex.20260724011735` cache observed during evaluation is stale: its Help skill and command
guide still define six commands and omit `$ultracode-verify`. An invocation resolved against that
installed cache cannot satisfy UC-37 until the `0.6.0` payload is installed or reloaded.

## Side-effect checklist

| Action | Result |
| --- | --- |
| Initialized project control | No |
| Delegated work through Help | No |
| Ran project tests, builds, or declared project checks | No |
| Changed a model, effort, global default, or other setting | No |
| Wrote or modified project files during the Help evaluation | No |

The evaluation used only read-only source inspection, SHA-256 comparison, diff inspection, and
`git status`. Existing dirty-worktree changes were preserved.

## Source file references

### Worktree `0.6.0`

- `plugins/ultracode/skills/ultracode-help/SKILL.md:8-13` — strict read-only boundary and required references.
- `plugins/ultracode/skills/ultracode-help/SKILL.md:17-33` — invocation-token stripping and bare-request mode selection.
- `plugins/ultracode/skills/ultracode-help/SKILL.md:40-72` — six content areas, seven-command order, required fields, tables, and adjacent examples.
- `plugins/ultracode/skills/ultracode-help/SKILL.md:88-100` — pre-send completeness checklist.
- `plugins/ultracode/skills/ultracode/references/command-guide.md:8-30` — complete-overview response contract and Markdown layout.
- `plugins/ultracode/skills/ultracode/references/command-guide.md:34-160` — quick-choice table and all seven command definitions.
- `plugins/ultracode/skills/ultracode/references/command-guide.md:162-221` — unconfigured-project behavior, model routing, tickets versus agents, and authority boundaries.
- `plugins/ultracode/skills/ultracode/references/reasoning-routing.md` — requested/effective routing, fallback, inheritance, and runtime-visibility rules.

### Stale installed `0.5.3` cache

- `${INSTALLED_PLUGIN_CACHE}/skills/ultracode-help/SKILL.md:19-20` — recognized topics omit `verify`.
- `${INSTALLED_PLUGIN_CACHE}/skills/ultracode-help/SKILL.md:41-44` — installed Help requires six commands.
- `${INSTALLED_PLUGIN_CACHE}/skills/ultracode/references/command-guide.md:15-16` — installed guide requires six commands.
- `${INSTALLED_PLUGIN_CACHE}/skills/ultracode/references/command-guide.md:34-46` — installed quick-choice table and command section omit `$ultracode-verify`.
