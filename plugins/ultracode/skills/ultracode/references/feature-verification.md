# Feature verification

Use this contract whenever `$ultracode-verify` creates, inspects, executes, updates, or summarizes a
durable feature verification plan.

## Artifact and path

The canonical artifact is JSON conforming to `feature-verification-plan.schema.json`. Default to the
portable project-relative path `.ultracode/verification/<feature-slug>.json`. A repository or user
may choose another portable project-relative path. Never use an absolute, parent-traversing,
backslash, home-relative, or machine-local path.

The artifact is user-owned project content, not a generated adapter and not an entry in
`.ultracode/managed.json`. Creating it does not initialize UltraCode project control. Inspecting or
summarizing it is read-only; creating or appending results is a project write governed by current
authority and the active plan gate.

## Closed plan model

The plan has these exact root fields:

- `schema_version`: integer `1`;
- `plan_id`: stable lower-case `verify-*` identifier;
- `feature`: short feature name;
- `objective`: observable behavior being verified;
- `scope`: non-empty array of concrete in-scope boundaries;
- `acceptance_criteria`: non-empty array of unique `AC-*` IDs and statements;
- `scenarios`: non-empty array of unique `FV-*` scenarios;
- `created_at` and `updated_at`: RFC 3339 timestamps with timezone and whole-second precision.

Each scenario contains exactly `id`, `title`, `criterion_ids`, `procedure`, `expected`, and
`results`. `criterion_ids` and `procedure` are non-empty. Every referenced criterion must exist, and
every criterion must be referenced by at least one scenario.

`results` is an append-only history. The first result is `planned`; the latest result is the
scenario's current status. Timestamps are non-decreasing, and `updated_at` cannot predate the latest
result. Never delete earlier results or persist a separate current-status field.

## Exact status semantics

Only these lower-case statuses are valid:

| Status | Evidence | Reason | Meaning |
| --- | --- | --- | --- |
| `planned` | empty | null | Defined but not executed |
| `passed` | one or more `supports` items | null | Direct evidence supports expected behavior |
| `failed` | one or more `contradicts` items | null | Direct evidence contradicts expected behavior |
| `not-run` | empty | required | Intentionally not executed for the recorded reason |
| `not-applicable` | empty | required | Outside the recorded feature scope |

Evidence items contain exactly `kind`, `source`, `observed`, `outcome`, and `captured_at`.
`kind` is `command`, `assertion`, `observation`, `artifact`, or `manual`. `source` identifies the
actual command, path, test, interaction, or observation surface. `observed` states what happened.
An exit code alone supports a scenario only when that command directly exercises the expected
behavior.

A worker summary without raw or directly inspected evidence, implementation existence, static code
shape, an unrelated green suite, or an inferred result cannot support `passed`.

## Semantic validation

JSON Schema closes field sets and enforces local result shape. Before any write or outcome claim,
also validate cross-record semantics:

1. all plan, criterion, and scenario IDs are unique and case-sensitive;
2. every criterion reference resolves and every criterion is covered;
3. each history begins with `planned`;
4. result timestamps are ordered and `updated_at` covers the latest append;
5. evidence outcome and result status agree exactly;
6. prior results are preserved in order;
7. the on-disk bytes still match the inspected precondition before update.

Any violation makes the plan **INCOMPLETE** and blocks mutation until the inconsistency is resolved
explicitly. Never silently normalize casing, discard unknown fields, regenerate an invalid plan, or
rewrite history to make it pass.

## Derived feature outcome

The plan does not persist an aggregate status. Derive it from each scenario's latest result:

- **VERIFIED:** every applicable latest result is `passed`, and every criterion has at least one
  latest `passed` scenario;
- **FAILED:** at least one latest result is `failed`;
- **INCOMPLETE:** any latest result is `planned` or `not-run`, any criterion lacks a latest passed
  scenario, or plan/evidence consistency is invalid;
- **NO APPLICABLE SCENARIOS:** all latest results are `not-applicable`.

Failure and incompleteness may coexist; report both. `not-applicable` never counts as passed
criterion coverage. A user may explicitly change scope and criteria, but that is a visible plan
edit, not an automatic status shortcut.

## Update protocol

1. Read and validate the complete current artifact.
2. State the scenario, current latest result, proposed appended result, evidence or reason, and
   derived-outcome effect.
3. Confirm that the current request and project plan gate authorize the write.
4. Recheck the file precondition and append; do not replace history.
5. Update `updated_at`, validate the full resulting artifact, and persist atomically where supported.
6. Re-read and summarize status counts, criterion coverage, derived outcome, and next action.

Do not run external, deployed, destructive, privileged, credentialed, purchased, published, Git, or
dependency-changing steps without separate explicit authority. A failed scenario does not authorize
an implementation fix.
