# Data-driven swarm protocol

Read this reference for Deep or Critical work and whenever more than one delegated job is useful.

## Distinguish jobs from live agents

A **logical job** is one bounded unit in the work graph. A **live agent instance** is a currently running execution slot. One problem can require many logical jobs while the platform runs only a few instances concurrently.

Never report the live-slot limit as the coverage limit. Queue unstarted jobs and dispatch them in waves. Reuse an instance only for related non-adversarial jobs; use a fresh independent context for verification when available.

## Build the work graph from evidence

### 1. Inventory data units

Count real items found in the task or repository, such as:

- modules, files, endpoints, call sites, writers, migrations, assets, scenes, tests, requirements, traces, or evidence sources;
- user-visible flows that can be inspected or changed independently;
- components with exclusive write ownership.

Create one job per unit only when all are true:

1. the scope is concrete;
2. the deliverable is independently useful;
3. the result can be checked from evidence;
4. it does not require an unresolved upstream decision;
5. parallel execution will not overlap writes.

Do not split a tiny task into fragments that cost more to coordinate than to solve. Do not combine unrelated units merely to reduce the displayed count.

### 2. Add orthogonal lenses

Add a lens job only for a blind spot not covered by unit jobs. Typical lenses include:

- architecture and lifecycle;
- security and authority;
- compatibility and migration parity;
- performance or concurrency;
- user-visible behavior and accessibility;
- data integrity and rollback;
- evidence provenance in reverse engineering.

Two agents looking at the same surface are redundant unless one is explicitly adversarial.

### 3. Create stable IDs

Use IDs that remain stable in status and follow-ups:

- `U-001` for data-unit jobs;
- `L-001` for orthogonal lenses;
- `F-001` for deduplicated material findings;
- `V-001` for adversarial verification jobs;
- `S-001` for the single synthesis.

Record for every job: type, scope, responsible owner, live agent when one exists, parent,
dependencies, read/write mode, owned files, requested model, effective model when observable,
requested reasoning effort, effective effort when observable, the plain-language routing reason,
expected evidence, state, completion criterion, and result.

Allowed job states are `QUEUED`, `ACTIVE`, `DONE`, `FAILED`, `BLOCKED`, and `CANCELLED`.

## Dispatch in visible waves

1. Detect the currently available collaboration capacity; do not assume a fixed number.
2. Score each ready job with `reasoning-routing.md`, then start the highest-value dependency-free
   jobs that fit.
3. Keep the rest in a visible queue with counts and next IDs.
4. Continue useful lead work while a wave runs.
5. At the wave barrier, collect results, inspect any writes, release completed capacity, and dispatch the next wave.
6. Do not finish while an active job can change the conclusion or shared files.

Use a fresh or bounded context with a complete job brief when an explicit model or effort override
and context isolation matter. A full-history fork inherits the active chat model and effort; show
that inheritance instead of claiming that a requested override became effective.

Platform limits determine simultaneous execution and latency only. The problem graph determines total coverage.

## Normalize findings at the discovery barrier

A **material finding** is a factual claim whose falsity would change the implementation, risk assessment, validation plan, or final conclusion. Examples include a reachable call path, data writer, compatibility break, security boundary, asset identity, or missing required behavior.

Before creating verifiers:

1. merge duplicate claims that share the same failure mode and evidence;
2. split compound claims that can be independently true or false;
3. discard unsupported speculation or label it a question;
4. assign a stable `F-*` ID;
5. link source jobs and raw evidence.

Trivial file locations or observations that cannot affect a decision are not material findings.

## Verify adversarially

Create one `V-*` job per material finding. The verifier receives:

- the exact claim;
- acceptance or refutation criteria;
- raw files, paths, logs, captures, or commands needed to test it;
- a read-only boundary unless a dedicated disposable fixture is authorized.

Do not provide the discoverer's desired verdict or persuasive summary. Prefer a fresh agent that did not produce the finding. A verifier must return one of:

- `CONFIRMED`: independent evidence supports the claim;
- `REFUTED`: independent evidence contradicts it;
- `UNKNOWN`: evidence or capability is insufficient.

Link the outcome back to the `F-*` ID. Refuted findings must not enter implementation or synthesis as facts. Unknown findings remain visible and block only claims that depend on them.

## Synthesize once

Use one `S-001` owner after the required barriers. The lead normally owns synthesis; delegation is allowed only to one explicitly selected synthesizer.

Synthesis must:

1. use verified or clearly labeled evidence;
2. reconcile contradictions;
3. integrate worker changes and inspect ownership boundaries;
4. produce one coherent decision, implementation state, or report;
5. preserve `UNKNOWN` items instead of averaging them away.

Never vote across multiple final syntheses. Consensus does not replace evidence.

## Apply the safety circuit breaker

`hard_safety_cap` limits total logical jobs created for one task. It is not a target, default swarm size, or concurrency setting.

If the projected graph exceeds the cap:

1. stop before silently truncating coverage;
2. show the counts by data units, lenses, projected verifiers, and synthesis;
3. propose a scoped partition, staged continuation, or explicit cap change;
4. wait for authority when the choice changes coverage or cost materially.

Do not hide cap pressure by bundling independent material findings into one unverifiable job.

## Common mappings

| Task | Data units | Useful lenses | Verification |
| --- | --- | --- | --- |
| Reverse engineering | actors, call sites, writers, assets, scripts | interpreter, behavior table, provenance | one verifier per material decoded claim |
| Migration | files, modules, endpoints, schemas | compatibility, data integrity, rollout | parity verifier per material gap |
| Audit | components or attack surfaces | security, lifecycle, compatibility | verifier per evidence-backed finding |
| Implementation | independent components with exclusive ownership | architecture, regression, UX | reviewer or verifier per material change |
| Simple localized task | none beyond root scope | none | targeted local check; no artificial swarm |
