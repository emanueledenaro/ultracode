# Routing and delegation

Read this reference for Focused, Deep, or Critical execution after reading `swarm-protocol.md` for
delegated Deep or Critical work. Read `reasoning-routing.md` before selecting a subagent model,
reasoning effort, or context mode.

The role classes, gates, templates, and protocols here are runtime-neutral: they say what a job is
and what must be true before it is delegated, not which API creates the agent. On Claude Code, read
[the Claude Code runtime adapter](claude-code-runtime.md) for the concrete mechanism, and the
"Delegate on Claude Code" section below for the mapping this reference depends on.

## Route by bounded responsibility

| Need | Preferred execution | Write access | Model and effort policy |
| --- | --- | --- | --- |
| Locate entry points or explain architecture | explorer | Read-only | Terra; score the bounded question, normally `low` |
| Inspect one real data unit | explorer | Read-only | Terra; score the unit, normally `low` |
| Cover an orthogonal risk lens | specialist explorer or reviewer | Read-only | Terra or Sol by impact; objective-driven effort |
| Implement one independent component | worker | Exclusive workspace scope | Terra; raise effort by coupling and risk |
| Verify one material finding | fresh adversarial verifier | Read-only | Sol; at least the configured verifier minimum |
| Review an integrated diff | fresh review-specialized agent | Read-only | Sol for material changes; objective-driven effort |
| Synthesize final evidence | exactly one lead or synthesizer | Lead-owned | inherit the active chat unless a fresh synthesizer is explicitly selected |

Use configured role classes by default. Preserve an exact model identifier when the user explicitly
supplies it, select it only when the platform exposes that identifier reliably, and otherwise apply
the configured fallback while reporting the effective model. Record requested and effective
reasoning effort separately. Do not treat a project default as proof of a live runtime value.

## Delegate on Claude Code

Claude Code creates every subagent through the `Agent` tool (`Task` is an accepted alias). Map the
row you selected above onto its parameters:

| Row | `subagent_type` | Model | Isolation |
| --- | --- | --- | --- |
| explorer | `ultracode-explorer`, or built-in `Explore` | omit to inherit, or `sonnet` | none; read-only |
| specialist explorer or reviewer | `ultracode-reviewer` | `opus` for material impact | none; read-only |
| worker | `ultracode-worker` | omit to inherit, or `sonnet` | `worktree` only when workers would contend for paths |
| fresh adversarial verifier | `ultracode-verifier` | `opus` | none; read-only |
| fresh review-specialized agent | `ultracode-reviewer` | `opus` | none; read-only |
| lead or synthesizer | not delegated | lead-owned | not applicable |

Pass the scored value from `reasoning-routing.md` as `effort`, clamping `ultra` to `max`. Pass the
full job template from this reference as `prompt`.

Three properties of this runtime change how the templates must be written:

1. **A subagent starts from a fresh context.** It does not inherit the lead's conversation. This is
   what makes an `ultracode-verifier` verdict independent evidence rather than an echo. It also
   means a brief that says "the finding above" or "the same scope" transfers nothing: inline the
   claim and the raw evidence, or cite exact paths.
2. **The subagent's final message is the return value.** It goes to the lead, not to the user. State
   the required status payload in the brief instead of expecting a human-facing summary.
3. **Concurrency comes from one message.** Several `Agent` calls in a single assistant message run
   concurrently; the same calls split across messages serialize. Dispatch a whole wave at once.

Claude Code publishes no fixed concurrency ceiling, and it varies by version and account. Do not
state a number as fact — dispatch, observe what starts, and keep the remainder `QUEUED`.

When a shipped role agent is unavailable, `general-purpose` with the identical brief is an
acceptable substitute and `Explore` is an acceptable read-only substitute for discovery; record the
substitution. Running the job in the lead context is not a substitute: disclose it and never promote
that result to independent confirmation.

## Delegation gates

Delegate only when all are true:

1. The job has a stable ID and concrete deliverable.
2. Its boundary can be stated without transferring the whole problem.
3. Its dependency state is ready.
4. Parallel execution cannot create overlapping writes.
5. The lead can verify the result from files, logs, tests, captures, or cited evidence.
6. The job adds coverage, independence, or useful context isolation.
7. The requested model and reasoning effort follow `reasoning-routing.md`, and the chosen context
   mode can actually apply those overrides.

Do not delegate the final authority decision, destructive or external action, two writes to the same files, a vague request such as "fix everything," or a truth claim with no verification path.

## Explorer job template

Include:

- job ID and one specific question;
- exact scope or enumerated data unit;
- read-only requirement;
- expected files, symbols, call paths, commands, or other evidence;
- instruction to separate facts, assumptions, and unknowns;
- instruction not to explore unrelated surfaces;
- required status payload for the lead ledger.

Example:

```text
Job U-014. In read-only mode, determine where authentication is enforced for
the API routes under <scope>. Return the call path, exact files and symbols,
existing tests, material findings, and unresolved ambiguity. Do not propose or
implement a fix.
```

## Worker job template

Include:

- job ID and exclusive file or module ownership;
- required behavior, invariants, and non-goals;
- applicable repository instructions and specialist skills;
- required checks and evidence;
- reminder that other work may be concurrent;
- instruction not to revert others and to adapt to visible changes.

Example:

```text
Job U-021. Own only <files/modules>. Implement <behavior> and preserve
<invariants>. Run <checks>. You are not alone in the codebase: do not revert
other edits, and adapt to concurrent changes. Return changed files, checks,
material findings, and remaining uncertainty.
```

## Verifier job template

Pass the claim and raw evidence without a preferred verdict:

```text
Job V-007 verifies finding F-007 in read-only mode. Independently test this
claim: <claim>. Confirmation criteria: <criteria>. Refutation criteria:
<criteria>. Inspect <raw artifacts>. Return CONFIRMED, REFUTED, or UNKNOWN with
exact evidence. Do not rely on the discovering agent's conclusion.
```

Use one verifier per deduplicated material finding. When a fresh agent is unavailable, disclose that the result is not independent and do not promote it to independent confirmation.

On Claude Code a subagent never inherits the lead conversation, so `ultracode-verifier` is fresh by
construction. That guarantee only holds if the brief carries its own evidence: a verifier that has
to ask what the claim was cannot verify it.

## Independent integrated review template

```text
Review these changed paths or raw diff against the acceptance criteria and
applicable AGENTS.md files. Work read-only. Reconstruct the risk surface from
the artifacts. Report actionable correctness, regression, security,
compatibility, and validation gaps first, with file and line evidence. State
directly when no actionable finding is supported.
```

## Wave and queue protocol

1. Count all dependency-ready logical jobs.
2. Inspect actual available agent capacity.
3. Dispatch only what fits; keep every remainder visible as `QUEUED`. On Claude Code, issue the
   whole wave as parallel `Agent` calls in one message, or it will not run in parallel.
4. Continue useful lead work while agents run.
5. At each barrier, collect outcomes and inspect writes.
6. Recompute the graph only from new evidence; explain added or cancelled jobs.
7. Dispatch the next wave until required jobs reach a terminal state.
8. Do not equate a platform slot limit with a total-agent limit.

## Nested delegation

The lead may assign a parent agent a subtree only when this materially improves scale. The parent receives:

- an explicit list or derivation rule for descendant job IDs;
- a maximum subtree circuit breaker;
- ownership and authority boundaries;
- required child status and evidence format;
- a prohibition on hidden or overlapping descendants.

All descendants appear in the root ledger. A child may not expand scope, authorize writes, or create its own unbounded swarm.

## Integration protocol

1. Wait for every result needed by the next decision.
2. Inspect changed files directly; shared filesystem visibility is not verification.
3. Normalize and deduplicate findings before spawning verifiers.
4. Reconcile results against repository evidence and reject unsupported claims.
5. Send narrow follow-ups when continuity helps; prefer fresh contexts for adversarial verification.
6. Interrupt non-responsive work after a bounded useful wait and inspect any filesystem effects.
7. Never relabel lead self-review as independent.
8. Never finish while a live job can change the conclusion or files.
9. Use exactly one synthesis owner after required barriers.
