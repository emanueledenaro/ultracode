---
name: ultracode-verify
description: Create, inspect, execute, and maintain a durable feature-level functional verification plan with evidence-backed scenario results. Use when the user explicitly invokes `$ultracode-verify`, asks to prove that a feature works, wants reusable acceptance scenarios, or needs a persistent verification record. Use only the statuses planned, passed, failed, not-run, and not-applicable; fail closed on incomplete or inconsistent evidence. Do not select this skill when the request explicitly invokes `$ultracode-help`; `verify` is then only a Help topic.
---

# UltraCode Verify

## Respect explicit Help precedence

If the request explicitly invokes `$ultracode-help` or `ultracode-help`, do not inspect, create,
execute, or update a verification plan. Read `../ultracode-help/SKILL.md` and answer `verify` as a
read-only Help topic.

Create and maintain feature-level functional verification as a durable project artifact. Read
`../ultracode/references/feature-verification.md`,
`../ultracode/references/feature-verification-plan.schema.json`, and
`../ultracode/references/command-interface.md` completely before acting.

## Select the operation

Classify the request as one or more of:

- **Create:** derive acceptance criteria and scenarios, preview the exact plan path and content, then
  write only when the current request and project control authorize it.
- **Inspect:** validate and explain an existing plan read-only.
- **Execute:** run only the authorized local scenarios, record direct evidence, and append results.
- **Record:** append a supplied result only after checking that its evidence supports that status.
- **Reconcile:** detect stale, incomplete, contradictory, duplicated, or orphaned plan content without
  silently repairing it.
- **Summarize:** derive the current feature outcome from the latest scenario results without changing
  the plan.

Never create or update a plan merely because another command mentions validation. A durable write
requires an explicit verification-plan request or already-authorized feature work whose task
contract includes maintaining that plan.

## Use the durable plan format

Default to `.ultracode/verification/<feature-slug>.json` unless the user or repository defines a
different portable project-relative path. Creating this artifact does not initialize UltraCode
project control and must not create `.ultracode/config.json` or `.ultracode/managed.json`.

Use schema version 1. The plan contains one feature objective, explicit scope, acceptance criteria,
and scenarios. Each scenario maps to one or more acceptance criteria and has an append-only
`results` history. The latest result is its current status; never add a second summary status that
can drift from the history.

Use exactly these lower-case statuses:

The exact status set is `planned`, `passed`, `failed`, `not-run`, and `not-applicable`.

- `planned`: the scenario is defined but has not run;
- `passed`: the scenario ran and direct evidence supports its expected behavior;
- `failed`: the scenario ran and direct evidence contradicts its expected behavior;
- `not-run`: the scenario was intentionally not executed and has a concrete reason;
- `not-applicable`: the scenario does not apply to the current feature scope and has a concrete
  reason.

Do not invent synonyms, normalize casing, or use task, check, evidence, or configuration states as
scenario statuses.

## Fail closed before writing or claiming a result

Validate the complete artifact against the bundled schema and the semantic rules in
`feature-verification.md`. Stop without writing when any of these conditions is present:

- the JSON is malformed, has unknown fields, or uses a status outside the exact five-value set;
- IDs are duplicated, an acceptance-criterion reference is missing, or a criterion has no scenario;
- the first scenario result is not `planned`, history timestamps are not ordered, or `updated_at`
  predates a recorded result;
- `passed` or `failed` lacks direct evidence, or its evidence outcome disagrees with the status;
- `planned`, `not-run`, or `not-applicable` contains execution evidence;
- `not-run` or `not-applicable` lacks a non-empty reason;
- an existing plan changed since inspection, contains manual drift, or would require dropping prior
  results.

Report the exact inconsistency and the smallest user decision or evidence needed. Do not overwrite an
invalid plan with a clean replacement.

## Build meaningful scenarios

1. Derive acceptance criteria from the requested behavior, repository contracts, and user-visible
   boundaries. Keep assumptions explicit.
2. Cover the success path, relevant failure paths, state transitions, permissions, persistence, and
   regression boundaries in proportion to feature risk.
3. Give each scenario a deterministic procedure and observable expected result. A build or exit code
   is evidence only when it directly proves that scenario.
4. Map every acceptance criterion to at least one scenario. A `not-applicable` scenario does not by
   itself satisfy a criterion.
5. Begin every scenario history with one `planned` result and no evidence.

Do not turn code structure, a worker's unsupported statement, or a green unrelated suite into
functional proof.

## Record evidence honestly

Append one result; never rewrite or delete earlier results. For `passed` and `failed`, record at
least one concrete evidence item with its kind, source, observed behavior, outcome, and capture time.
Use `supports` only for `passed` and `contradicts` only for `failed`.

If execution was blocked or skipped, append `not-run` with the exact reason and no fabricated
evidence. Use `not-applicable` only when scope makes the scenario irrelevant, not to hide a failure
or missing environment. A later authorized run may append a new result; the full history remains.

After every append, update `updated_at`, revalidate the entire artifact, re-read the on-disk file to
detect stale-plan drift, then write atomically when the available file tools support it. Preserve
unrelated user changes.

## Derive the feature outcome

Report one derived outcome, not another persisted status:

- **VERIFIED:** every applicable scenario's latest result is `passed`, and every acceptance
  criterion has at least one latest `passed` scenario;
- **FAILED:** at least one latest scenario result is `failed`;
- **INCOMPLETE:** any latest result is `planned` or `not-run`, required evidence is missing, criterion
  coverage is incomplete, or the plan is inconsistent;
- **NO APPLICABLE SCENARIOS:** every latest result is `not-applicable`; never present this as
  verification.

When failed and incomplete conditions coexist, lead with the failure and also disclose the
incomplete coverage. Never claim the feature is verified from a partial selection unless the user
explicitly narrowed the plan scope and the artifact records that scope.

## Preserve authority

Plan inspection and summarization stay read-only. Creating or updating the JSON plan is a project
write and follows the current request plus repository confirmation policy. Running a scenario does
not authorize Git staging, commits, pushes, pull requests, package publishing, deployment, external
requests, destructive operations, dependency changes, credential use, purchases, or production
writes. Obtain separate explicit authority for each protected boundary.

Do not automatically fix product code when a scenario fails. Report the failed behavior and offer to
route an authorized fix through `$ultracode`; after a fix, append a new verification result rather
than erasing the failure.

## Integrate with UltraCode control views

When `$ultracode-flow` is active, expose the plan path, derived outcome, counts by latest status, the
current or next scenario, blocker, and next verification action without changing the plan.

When `$ultracode-status` is active, expose schema and semantic validity, scope, criterion coverage,
scenario histories, evidence sources, derived outcome, drift, and remaining gaps without changing
or rerunning anything.

When `$ultracode` owns feature work, reconcile any in-scope verification plan before final
completion. A `failed`, `planned`, `not-run`, inconsistent, or uncovered required scenario prevents
an unqualified verified claim.
