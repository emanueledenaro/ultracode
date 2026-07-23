# UltraCode command guide

Use this as the canonical user-facing guide for UltraCode commands. It explains what each command does without implying that a command was run or that runtime-only facts are known.

## Decision path

```text
Need an explanation, comparison, or example?             -> $ultracode-help
Need work investigated, built, fixed, reviewed, or run?  -> $ultracode
Need project control added for Codex and Claude Code?     -> $ultracode-init
Need existing UltraCode control changed or drift repaired?-> $ultracode-edit
Need a quick live view of current work?                  -> $ultracode-flow
Need the detailed evidence and diagnostic view?          -> $ultracode-status
```

If the requested outcome is only an explanation, review, audit, or diagnosis, use Help or UltraCode read-only. If a change is needed in a project without `.ultracode`, `$ultracode` keeps the original objective and first prepares the read-only `$ultracode-init` proposal; it never initializes silently.

## `$ultracode-help`

**What it does:** Explains the six commands, the control model, models and effort, safety boundaries, and copyable prompts.

**Use it when:** You are deciding where to start, do not know what a command means, or want a safe example.

**Writes and confirmation:** Never writes, initializes, delegates, runs tests or builds, or changes the task. It works even when `.ultracode` does not exist.

**Result:** A recommendation and explanation, not a plan, state refresh, or execution.

**Compared with:** Help describes commands; Flow and Status describe a real task only when state is available.

```text
Use $ultracode-help to explain whether I need init or edit.
```

## `$ultracode`

**What it does:** Leads engineering work end to end: classifies the request, inspects relevant evidence, derives bounded jobs when useful, keeps ownership visible, verifies material findings, implements authorized changes, and reports validation evidence.

**Use it when:** You want an implementation, fix, migration, refactor, broad audit, difficult diagnosis, or another engineering outcome that needs accountable orchestration.

**Writes and confirmation:** Read-only requests remain read-only. For changes, it follows the repository's confirmation and authority boundaries. Git, dependency, external, destructive, and deployment actions each require explicit user authority; implementation authority does not imply them.

**Result:** The requested engineering outcome plus visible jobs, changed files, checks actually run, evidence, blockers, and unknowns.

**Compared with:** Use Init only to establish project control, Edit only to change existing control, Flow/Status only to inspect progress, and Help only to choose or understand commands.

```text
Use $ultracode to fix the failing payment webhook tests. Do not commit, deploy, or install dependencies.
```

## `$ultracode-init`

**What it does:** Inspects a repository and proposes shared UltraCode project control for Codex and Claude Code: canonical guidance, adapters, configuration, and managed-content tracking.

**Use it when:** The repository has no UltraCode control and you want repeatable AI project guidance, or you explicitly want to inspect the initialization proposal.

**Writes and confirmation:** Discovery and deterministic planning are read-only. It shows the plan ID, exact files, practical effects, and preservation boundaries; it writes only after one explicit confirmation. Existing manual content outside managed blocks stays preserved.

**Result:** Either a read-only proposal or, after confirmation and validation, an initialized project. A declined or unconfirmed proposal leaves the repository unchanged.

**Compared with:** Init creates baseline control. Edit changes control that already exists. `$ultracode` can route change work through Init's read-only preflight when control is missing.

```text
Use $ultracode-init to inspect this repository and show the exact setup proposal. Do not apply it yet.
```

## `$ultracode-edit`

**What it does:** Safely changes initialized UltraCode configuration and only the dependent Codex or Claude projections.

**Use it when:** You need to change project rules, validation commands, visibility, status policy, model policy, adapters, roles, safety cap, or repair managed-content drift.

**Writes and confirmation:** It diagnoses first, presents a before-and-after delta and conflicts, then writes only a confirmed plan. It never silently overwrites manual managed-content changes; unsafe or stale plans stop on conflict.

**Result:** A narrow configuration change with preserved manual content, regenerated dependent projections, doctor evidence, or a clear conflict requiring a decision.

**Compared with:** Edit is not for product code. Use `$ultracode` for engineering work and Init when no project control exists.

```text
Use $ultracode-edit to change the project status detail to concise. Show the delta and wait for confirmation.
```

## `$ultracode-flow`

**What it does:** Gives a short live control view: objective, phase, ticket counts, active or blocked tickets, owner, live agent when available, model/effort visibility, blockers, completion criteria, and next action.

**Use it when:** You need to understand what is happening now quickly.

**Writes and confirmation:** Always read-only. It does not start, resume, initialize, delegate, test, build, or write a status file.

**Result:** A compact, freshness-labelled snapshot. Persisted state is labelled stale when it is not current live state.

**Compared with:** Flow is concise and action-oriented. Status is the full diagnostic and evidence view. Help is the command guide, not a task snapshot.

```text
Use $ultracode-flow to show the active tickets, blockers, and next action.
```

## `$ultracode-status`

**What it does:** Gives the detailed read-only diagnostic view: jobs, files, checks, evidence, configuration drift, blockers, and next action.

**Use it when:** Flow is not enough and you need to know what happened, what proves it, or why something is blocked.

**Writes and confirmation:** Always read-only. It does not refresh state by running tests, builds, delegation, initialization, or writes.

**Result:** A detailed evidence-backed report that labels missing, stale, or unavailable information honestly.

**Compared with:** Status goes deeper than Flow. It does not replace `$ultracode` for execution or Help for choosing commands.

```text
Use $ultracode-status to explain why the validation ticket is blocked and show the available evidence.
```

## Models, effort, and user control

For a new UltraCode task, the recommended lead baseline is Sol with medium effort when those choices
are available. UltraCode does not change the model of an already-open task and does not rewrite the
user's global Codex configuration without a separate explicit request.

UltraCode starts with the model and effort of the chat where it is opened. A normal subagent defaults to Terra with low effort. Increase effort only because the objective requires it, not because more effort looks reassuring. Verifiers use Sol with at least high effort; critical verification or reasoning uses at least xhigh effort.

Requested model and effort are the routing intent. Effective model and effort are what the runtime actually assigned. A fallback is used when the requested route cannot be used. Report effective values and fallbacks only when the runtime exposes them; otherwise say they are not observable. Do not convert a configured preference into an observed runtime fact.

The user remains in control. Tickets map to bounded jobs and explain why work exists; they are not a second hidden tracker. An owner is accountable for a ticket, while a live agent is only a currently running runtime instance. Explicit authority is still required for Git, deployment, external actions, dependencies, and destructive operations.
