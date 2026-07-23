# Objective-driven model and reasoning routing

Read this reference before delegating any job or explaining why an agent received a model or
reasoning effort.

## Keep the chat model honest

The active Codex task owns the lead model and reasoning effort. UltraCode cannot replace that model
mid-task. Treat `swarm.model_policy.lead: inherit` as the honest default, and report the lead model
or effort as unobservable when the runtime does not expose them. A project preference or local
Codex default is not proof of the effective model in an already-open task.

Subagent model and effort overrides are separate decisions. Apply them only when the collaboration
runtime exposes the requested values. When an override requires a fresh or bounded context, send a
complete job brief with the necessary raw evidence. A full-history fork inherits the lead model and
effort; never claim that an explicit override took effect in that case.

## Start a new UltraCode task

When the user can choose the lead before opening a new UltraCode task, recommend
`gpt-5.6-sol` with `medium` effort as the balanced coordination baseline. Sol is appropriate for
planning, cross-job synthesis, authority decisions, and deciding when verification is material;
`medium` avoids spending critical-review effort on every conversational turn.

This is startup guidance, not a runtime override. UltraCode must not change the current task's model
or the user's global Codex configuration. It may change a global default only after a separate,
explicit user request. Once the task is open, report the lead as inherited and report its effective
model or effort only when the runtime exposes them.

## Score the bounded objective

Score each ready job independently. Do not reuse one effort for the whole swarm.

Give each factor `0`, `1`, or `2`:

| Factor | 0 | 1 | 2 |
| --- | --- | --- | --- |
| Ambiguity | exact mechanical instruction | one bounded design choice | unclear cause or competing interpretations |
| Consequence of error | easy local correction | user-visible or multi-file regression | security, data, compatibility, release, or authority impact |
| Coupling | one isolated surface | adjacent dependencies | cross-module, concurrent, lifecycle, or migration coupling |
| Evidence burden | one direct check | several checks or reconciliation | adversarial proof, incomplete observability, or conflicting evidence |
| Reversibility and authority | read-only or trivially reversible | meaningful workspace write | difficult rollback, destructive, external, privileged, or protected boundary |

Map the total to the requested effort:

| Total | Requested effort |
| ---: | --- |
| 0-2 | `low` |
| 3-4 | `medium` |
| 5-6 | `high` |
| 7-8 | `xhigh` |
| 9 | `max` |
| 10 | `ultra` |

Record the factor values and a short plain-language reason in the lead ledger. Show the reason, not
the raw score, unless the user asks for diagnostic detail.

## Apply floors, caps, and escalation

The configured reasoning policy constrains the score:

- start bounded operational jobs at `bounded_default`, normally `low`;
- cap a deterministic, mechanical, directly checked job at `medium` unless new evidence makes its
  classification wrong;
- give each material finding verifier at least `material_verifier_minimum`, normally `high`;
- give security, data-integrity, migration, irreversible, external, privileged, or release-critical
  work at least `critical_minimum`, normally `xhigh`;
- never exceed `maximum`;
- request `max` or `ultra` only when the score qualifies and a critical consequence justifies the
  added reasoning; never use them as routine quality labels.

If a result is `UNKNOWN` because the reasoning was insufficient, or a first repair attempt exposes
materially greater ambiguity, raise the next attempt by one supported effort level and record why.
Do not escalate an environmental failure, missing permission, unavailable tool, or deterministic
test failure that more reasoning cannot fix. After two failed repair-review cycles, stop under the
existing convergence rule instead of continuing to raise effort.

## Choose the model separately

Use the configured exact identifiers only when the runtime exposes them:

| Job | Preferred model |
| --- | --- |
| bounded discovery, documentation, localized implementation, or mechanical validation | `gpt-5.6-terra` |
| complex but bounded implementation | `gpt-5.6-terra` with the scored higher effort |
| architecture, security, migration, data integrity, or high-impact ambiguity | `gpt-5.6-sol` |
| material finding verification and critical integrated review | `gpt-5.6-sol` |

Model strength does not replace effort scoring, and higher effort does not silently turn one model
into another. If the preferred model is unavailable, apply `swarm.model_policy.fallback`, preserve
the requested effort when supported, and report the requested and effective values separately.

## Report every dispatch

For each logical job record:

- requested model and why;
- effective model when observable;
- requested reasoning effort and why;
- effective effort when observable;
- fallback, inheritance, or context constraint;
- the evidence that would justify a later escalation.

Queued jobs have requested values but no effective runtime values yet. Flow and Status must never
invent the effective model or effort before the agent starts or when the runtime hides them.
