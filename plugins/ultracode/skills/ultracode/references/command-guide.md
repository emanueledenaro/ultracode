# UltraCode command guide

This is the canonical detailed guide for `$ultracode-help`. Keep the user-facing wording natural,
but preserve the semantic content and order below.

## Response contract

Strip the `$ultracode-help` or `ultracode-help` invocation token before interpreting the request.
That token invokes the command; it is not the `help` topic. With no remaining explicit topic,
including a bare `Use $ultracode-help` request, return the complete overview in this order:

An explicit Help invocation has precedence over any command name that follows it. For example,
`$ultracode-help flow` explains Flow read-only and must never reconstruct live Flow state.

1. quick choice as a two-column Markdown table;
2. all seven commands, each with four labeled fields and an inline blockquote example;
3. unconfigured-project and Init preflight behavior;
4. models and reasoning effort as a compact table plus honest runtime notes;
5. tickets versus agents as a compact comparison table;
6. authority boundaries;

An explicit command, `models`, or `examples` selects a focused answer. The words `breve` and
`sintetico` request compact wording; they do not remove mandatory content. A compact no-topic
overview still contains all six content areas. Do not end a response while a required semantic block is
missing.

The chat layout is part of the contract. Start with one H1 title. Use H2 headings for the content
areas, H3 headings for individual commands, short labeled paragraphs, GitHub-flavored Markdown
tables, and inline blockquote examples. Do not move all examples to the end or render them as seven
separate fenced code blocks.

## Quick choice

| Need | Use |
| --- | --- |
| An explanation, comparison, or example | `$ultracode-help` |
| Engineering work investigated, built, fixed, or run | `$ultracode` |
| Durable proof that a feature works | `$ultracode-verify` |
| UltraCode project control added | `$ultracode-init` |
| Existing UltraCode control changed or drift repaired | `$ultracode-edit` |
| A quick view of work in progress | `$ultracode-flow` |
| Detailed state, evidence, and blockers | `$ultracode-status` |

Recommend the least powerful command that satisfies the outcome. Help explains; Flow and Status
observe; Init configures; Edit changes that configuration; UltraCode performs engineering work.

## The seven commands

### `$ultracode-help`

**When to use it:** Choose it when deciding where to start, comparing commands, learning the model
policy, or asking for safe examples.

**What you get:** An explanation or recommendation. It is not task execution, a project plan, or a live
state refresh.

**Can it write?:** No. It never writes, initializes, delegates, tests, or builds.

**When confirmation is required:** Never. Help has no write path and also works without
`.ultracode`.

> **Example:** `Use $ultracode-help to explain all seven commands and recommend where I should start.`

### `$ultracode`

**When to use it:** Choose it for an implementation, fix, migration, refactor, broad audit, difficult
diagnosis, or another accountable engineering outcome.

**What you get:** The requested outcome plus visible jobs when useful, changed files, checks actually run,
evidence, blockers, and unknowns.

**Can it write?:** Yes, when the requested engineering outcome requires authorized file changes.
Answers, reviews, audits, and diagnoses remain read-only unless a fix is also requested.

**When confirmation is required:** Authorized change work follows project confirmation rules. Git,
dependencies, external actions, destructive operations, and deployment each require their own
explicit authority.

> **Example:** `Use $ultracode to fix the failing payment webhook tests. Do not commit, deploy, or install dependencies.`

### `$ultracode-verify`

**When to use it:** Choose it to define feature-level acceptance scenarios, prove behavior through
direct evidence, preserve repeated verification attempts, or diagnose why functional coverage is
incomplete.

**What you get:** A durable, closed JSON plan with acceptance criteria, append-only scenario
results, exact evidence sources, and a derived verified, failed, or incomplete outcome.

**Can it write?:** Inspecting and summarizing are read-only. Creating a plan or appending a result
writes only the authorized plan artifact; it does not initialize project control or change product
code automatically.

**When confirmation is required:** The current request and project plan gate must authorize plan
writes. Git, publishing, external requests, deployment, dependencies, destructive operations, and
production actions always require separate explicit authority.

> **Example:** `Use $ultracode-verify to create a durable verification plan for checkout recovery. Do not deploy, publish, or make external requests.`

### `$ultracode-init`

**When to use it:** Choose it when a repository has no UltraCode project control and you want shared,
repeatable guidance and adapters for supported coding tools.

**What you get:** First, an exact read-only proposal with a stable plan ID, files, effects, and preservation
boundaries. After confirmation, it can produce a doctor-valid initialized project.

**Can it write?:** Yes, but discovery and planning never write. Only the apply phase can create or
update the managed project-control files.

**When confirmation is required:** Applying the initialization requires one explicit confirmation.
Declining or withholding confirmation leaves the repository unchanged; manual content outside
managed blocks is preserved.

> **Example:** `Use $ultracode-init to inspect this repository and show the exact setup proposal. Do not apply it yet.`

### `$ultracode-edit`

**When to use it:** Choose it to change initialized UltraCode rules, validation commands, visibility,
status policy, model policy, adapters, roles, safety controls, or managed-content drift.

**What you get:** A before-and-after configuration delta, affected projections, preserved content, detected
conflicts, and validation evidence after an approved apply.

**Can it write?:** Yes, but diagnosis and planning are read-only. Only the apply phase can update
the confirmed managed configuration and its dependent projections.

**When confirmation is required:** It writes only an explicitly confirmed, still-current plan.
Drift or stale preconditions stop the apply instead of silently overwriting manual work.

> **Example:** `Use $ultracode-edit to change status detail to concise. Show the delta and wait for confirmation.`

### `$ultracode-flow`

**When to use it:** Choose it to understand current work quickly: objective, phase, active or blocked
tickets, owners, observable agents and models, completion criteria, and next action.

**What you get:** A compact snapshot whose freshness and unknowns are explicit.

**Can it write?:** No. It is always read-only and does not initialize, delegate, resume work, run
checks, or write a status file.

**When confirmation is required:** Never. Flow has no write path.

> **Example:** `Use $ultracode-flow to show active tickets, blockers, and the next action.`

### `$ultracode-status`

**When to use it:** Choose it when Flow is not detailed enough and you need jobs, files, checks,
evidence, drift, blockers, history, or the reason a claim cannot be verified.

**What you get:** A detailed diagnostic report that distinguishes live, stale, missing, failed, blocked,
and verified information.

**Can it write?:** No. It is always read-only and never runs checks or modifies state merely to
refresh the report.

**When confirmation is required:** Never. Status has no write path.

> **Example:** `Use $ultracode-status to explain why validation is blocked and show the available evidence.`

## Unconfigured projects

Read-only Help, Flow, Status, answers, reviews, audits, and diagnoses can work without
`.ultracode`. Missing persistent project control must not trigger initialization merely for
inspection.

`$ultracode-verify` can inspect an existing plan without initialized project control. When the user
authorizes creation, its default `.ultracode/verification/<feature-slug>.json` artifact does not
create config or managed manifests and does not count as project-control initialization.

For requested change work, `$ultracode` preserves the original objective and enters the read-only
`$ultracode-init` baseline preflight. It derives conservative defaults from repository evidence,
shows the exact proposal, and asks once before initialization writes. If confirmed, it validates
the initialized state and then resumes the original objective. If declined or unconfirmed, the
repository and original task remain read-only.

## Models and reasoning effort

| Role | Default request |
| --- | --- |
| New lead task | Sol with `medium` effort |
| Active lead task | Inherit the model and effort of its chat |
| Normal bounded worker | Terra with `low` effort |
| Material verifier | Sol with at least `high` |
| Critical work | At least `xhigh` |

Before opening a new lead task, recommend Sol with `medium` effort when the user can choose those
settings. This is startup guidance only. UltraCode cannot replace the model or effort of an
already-open task and must not change global Codex defaults without a separate explicit request.

The active lead inherits the model and effort of its chat. Normal bounded workers default to Terra
with `low` effort and rise only when ambiguity, consequences, coupling, evidence burden, or
reversibility justify it. Material verifiers use Sol with at least `high`; critical security,
data-integrity, migration, irreversible, external, privileged, or release work uses at least
`xhigh`.

Requested model and effort are routing intent. Effective model and effort are what the runtime
actually assigned. A fallback is the route used when a request cannot be honored. Report effective
values and fallback only when observable; otherwise say they are not observable. A full-history
inheritance constraint, queued job, configured preference, or policy default is not proof of an
effective runtime value.

## Tickets and agents

| Concept | Meaning |
| --- | --- |
| Ticket | One bounded logical job with an accountable owner |
| Agent | A runtime instance that actually exists and is attached to work |

A ticket is the user-facing form of one bounded logical job and reuses that job's ID. Its
responsible owner remains accountable. A live agent is only a currently running runtime instance;
queued work can have a ticket and owner without having an agent. Never invent an agent, model,
effort, or parallel ID to make the view look complete.

## Authority boundaries

Approval to implement does not authorize Git staging, commits, pushes, pull requests, deployment,
dependency changes, external actions, destructive operations, privileged actions, or credential
use. Each protected boundary requires explicit user authority. Read-only commands never acquire
write authority from project configuration.
