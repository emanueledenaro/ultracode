# User control and status

Read this reference whenever UltraCode is active, project status is persisted, or the user asks where the work stands.

Use [command-interface.md](command-interface.md) for user-facing vocabulary, ticket explanations,
model reporting, and the distinction between the concise Flow view and detailed Status view.

## State machine

Use these phases:

```text
INTAKE -> ANALYSIS -> PLAN -> IMPLEMENTATION -> VALIDATION -> REVIEW -> COMPLETE
```

`WAITING_FOR_AUTHORIZATION` and `BLOCKED` are explicit side states. A task may skip phases that do not apply, but never imply that a skipped validation or review passed.

## Conversation is the live control surface

The lead posts a compact snapshot:

- when work starts;
- after the initial repository inspection;
- after decomposition and before the first fan-out;
- after each wave, discovery barrier, and verification barrier;
- before an action requiring authority;
- after implementation, validation, and review;
- before final handoff;
- at least once during each long-running interval allowed by the host, targeting 60 seconds.

Each update answers six questions:

1. What is the objective?
2. Which phase is active?
3. What is complete?
4. What is active or queued?
5. What evidence, files, or blockers changed?
6. What happens next?

Do not expose chain-of-thought or dump raw transcripts. Summarize decisions and evidence.

## Apply configuration deterministically

Precedence is: higher-level instructions, current user request and authority, applicable repository rules, then `.ultracode/config.json`. Configuration can narrow presentation or add confirmation gates; it cannot authorize a side effect forbidden or absent from the current task.

| Field | Operational behavior |
| --- | --- |
| `control.plan_gate: follow-repository` | Follow the active repository confirmation rule; if none exists, use the current request's authority. |
| `control.plan_gate: confirm-before-write` | Inspect and preview first, then obtain explicit confirmation before the first project write. |
| `control.plan_gate: autonomous-within-authority` | Proceed without an extra plan confirmation only inside the already authorized, reversible scope. |
| `control.updates: phase-only` | Update on phase transitions, authorization waits, blockers, and the host's long-work interval. |
| `control.updates: phase-and-barrier` | Also update after every fan-out, discovery, verification, validation, and review barrier. |
| `control.updates: detailed` | Also update after each execution wave or material graph change. |
| `control.detail` | Controls prose density only: compact counts, standard key job rows, or detailed job and finding tables. |
| `show_agent_jobs: false` | Hide routine job rows, but still disclose whether agents are active plus aggregate active/queued/done counts and any ownership conflict. |
| `show_files: false` | Hide routine path lists, but still show dirty-boundary violations, active writer ownership, and files requiring user action. |
| `show_validation: false` | Collapse passed checks to a count; never hide failed, blocked, unavailable, or not-run required checks. |
| `persistent_status` | Apply the persistence modes below without changing task authority. |
| `authority.status_writes` | `change-tasks-only` permits configured status snapshots only during authorized change work; `explicit-per-task` requires current-task permission. |
| `swarm.concurrency: auto` | Use currently available platform capacity. |
| `swarm.concurrency: N` | Run at most `N` delegated instances concurrently, clamped to actual platform capacity; total logical coverage is unchanged. |
| `swarm.hard_safety_cap` | Pause when the projected logical graph exceeds the circuit breaker; never use it as a target. |
| `swarm.model_policy` | Keeps the lead inherited from the active chat, prefers `gpt-5.6-terra` for bounded agents and `gpt-5.6-sol` for verifiers when exposed, otherwise uses `fallback`; always report requested and effective models separately. |
| `swarm.reasoning_policy` | Selects effort per bounded objective with `reasoning-routing.md`; bounded work starts from the configured default, material verification and critical work respect their floors, and `max` or `ultra` require qualifying critical evidence. |

No visibility preference may hide a blocker, authorization request, material unknown, failed required check, or evidence that changes the conclusion.

## User steering, pause, and stop

The newest user direction is a control event, not another queued job.

- **Redirect:** stop dispatching invalidated jobs, cancel or interrupt only the work made obsolete, preserve reusable results and all filesystem changes, recompute the graph, and show the delta.
- **Pause:** start no new jobs. Let only an atomic operation that is unsafe to interrupt reach a safe boundary, then reconcile agent state and files.
- **Stop:** immediately cancel queued jobs and request interruption of active jobs. Do not delete worktrees, kill unrelated processes, revert files, or discard partial work unless separately authorized.
- **Resume:** reconstruct truth from live agent state, the task ledger, the filesystem, and validation artifacts. Never assume an agent that was active before a pause is still running.

After pause, stop, or redirect, report cancelled, completed, still-active, and unknown jobs; files already changed; validation invalidated; and whether any background work could not be stopped. Claim `STOPPED` only after no live job can still change the conclusion or shared files.

## Use real progress, not percentages

Report milestone counts and actual graph state:

- plan steps complete / total;
- unit and lens jobs done / active / queued;
- findings confirmed / refuted / unknown / awaiting verification;
- validation checks passed / failed / blocked / not run;
- review state and synthesis owner.

Do not invent an ETA or percentage. If total work can grow after discovery, say that the inventory is still open.

## Logical jobs versus live instances

Always distinguish:

- **logical jobs:** full derived coverage;
- **live instances:** currently running agents allowed by the platform;
- **waves:** queued execution batches.

Example: `37 logical jobs; 3 live agents; wave 2 active; 21 queued`. Never imply that queued jobs were dropped.

## Persistent status modes

`control.persistent_status` supports:

- `conversation-only`: write no status artifact;
- `local`: write the configured status path only for authorized change work and keep it outside the tracked surface;
- `tracked`: update the configured status path only when the current request authorizes repository writes.

Read-only Answer, Review, Audit, Diagnose, Monitor, and Status requests remain read-only. Configuration alone does not silently convert them into write tasks. If the persisted file cannot be updated, continue with conversation status and label the file snapshot stale.

For `local` mode, initialization may add the exact status path to `.git/info/exclude` only after explicit permission. Never edit `.gitignore` silently.

## Status document schema

When persistence is authorized, use this shape:

```markdown
# UltraCode status

- Task: <stable task id>
- Objective: <one sentence>
- Phase: <state>
- Updated: <ISO-8601 timestamp with timezone>
- Authority: <read-only/change/monitor plus pending gates>

## Progress

- Completed: <milestones>
- Active: <milestones>
- Next: <next concrete action>

## Swarm

- Independent units: <count>
- Orthogonal lenses: <count>
- Logical jobs: <total>
- Live agents: <count>
- Waves: <current/known>
- Synthesis owner: <S-001 owner>

| ID | Type | Scope | Responsible | Live agent | Requested model | Effective model | Requested effort | Effective effort | Routing reason | State | Dependencies | Done when | Result |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

## Findings

| ID | Claim | Source jobs | Verifier | State | Evidence |
| --- | --- | --- | --- | --- | --- |

## Files

- <path>: <owner and state>

## Validation

- <check>: PASSED/FAILED/BLOCKED/NOT AVAILABLE/NOT RUN

## Blockers and authorization

- <item or none>
```

Keep the file concise. Store detailed evidence in task artifacts or the final report, not in status.

## Status precedence and staleness

For `$ultracode-status`, prefer live task state, then lead plan, then the persisted snapshot. Display its timestamp. Mark `STALE` when it predates known work, conflicts with live state, or belongs to another task.

An unchanged external process is not a status failure. A missing test is `NOT AVAILABLE`; a skipped test is `NOT RUN`; a failed command is `FAILED`; a permission or environment boundary is `BLOCKED`.
