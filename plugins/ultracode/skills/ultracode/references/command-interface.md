# Command interface

Use this contract whenever an UltraCode command explains work to the user.

## Use plain language

Write in the user's language. Prefer a concrete sentence over an internal label. Keep stable IDs for
tracking, but never show an ID without a descriptive title and explanation.

Define an unfamiliar term the first time it matters:

- an objective is the result the user asked for;
- a milestone is a meaningful stage toward that result;
- a ticket is the user-facing explanation of one bounded logical job;
- a responsible owner is the lead or delegated worker accountable for a ticket;
- a logical job is one unit in the complete work graph, while a live agent is a currently running instance;
- a wave is the group of jobs that fits into the current runtime capacity;
- a barrier is a checkpoint where results are reconciled before dependent work continues.

Do not expose chain-of-thought or raw agent transcripts. Explain decisions, evidence, errors, and
technical terms in ordinary language. Never invent progress percentages, agent counts, models,
results, ETAs, or completion claims.

## Start with what matters

Lead with the command's result or objective. Then show only information that helps the user
understand, decide, redirect, approve, pause, or stop.

Use this shared order when the information exists:

1. objective or requested change;
2. current phase and real milestone counts;
3. active tickets or proposed changes;
4. blockers, conflicts, or decisions required;
5. evidence and completed checks;
6. next concrete action.

Do not add a separate summary that repeats the ticket explanations. Do not repeat the same agent
data in both a ticket card and an agent table.

Use vertical ticket sections in conversation so narrow chat surfaces remain readable. Give the full
explanation when a ticket first appears or changes materially; routine progress updates show only
the changed fields. A persisted internal status document may keep its compact table.

## Map tickets to the real work graph

Reuse the logical job's stable ID for its ticket: `U-*`, `L-*`, `V-*`, or `S-*`. Keep
`F-*` for findings. Do not invent a second `T-*` ID for the same work. Show an agent ID only when
the runtime actually provides one; otherwise show its role or name without fabricating an ID.

## Explain every active ticket

Pair every ticket ID with a short action title. For an active or blocked ticket, explain:

- **State:** what is happening now in plain language;
- **Why it exists:** why this work is necessary for the objective;
- **Work:** what the assigned agent is doing;
- **Responsible:** lead, delegated worker, or role accountable for the ticket;
- **Live agent:** runtime-provided agent name or ID only while an instance exists;
- **Model:** requested model, effective model, and the reason for any fallback;
- **Reasoning:** requested effort, effective effort, and the objective evidence that selected it;
- **Completed:** concrete work or evidence already produced;
- **Remaining:** what is still missing;
- **Blocker:** what prevents progress, who can unblock it, and what they must do;
- **Completion criterion:** the observable fact that will prove the ticket is done;
- **Next:** the next concrete action;
- **Ownership:** files or modules exclusively owned by the writer when writes are active.

Omit a field only when it genuinely does not apply. Never leave a bare error code, model fallback,
status, or technical noun unexplained.

## Report models honestly

Distinguish the requested model from the effective model used by the runtime. If a queued ticket
has not started, say that no effective model has been selected yet. If the requested identifier is
unavailable, show the fallback and explain why. If a live agent exists but the runtime does not
expose its model, report that the effective model cannot be observed; never infer it from policy.

Apply the same rule to reasoning effort. A configured or requested effort is not proof of the
effective runtime effort. Explain why UltraCode selected it from the bounded objective, and state
when context inheritance, fallback, or runtime visibility prevents confirmation.

## Use stable states

Keep internal states canonical and translate their visible explanation into the user's language:

- `QUEUED`: defined but not started because it is waiting for a dependency or execution slot;
- `ACTIVE`: actively being worked;
- `BLOCKED`: cannot progress without a named condition changing;
- `DONE`: completion criterion proven;
- `FAILED`: work ran but did not satisfy its completion criterion;
- `CANCELLED`: intentionally stopped;

Use `UNKNOWN` for an unverified fact, model, result, or freshness condition, not as a job state.

For checks, use `PASSED`, `FAILED`, `BLOCKED`, `NOT AVAILABLE`, or `NOT RUN`, followed by
a plain explanation when the label alone is insufficient.

Use these separate evidence and configuration outcomes without pretending they are job states:

- `VERIFIED`: supported by an executed check or direct repository evidence;
- `INFERRED`: likely from repository evidence but not executed;
- `UNKNOWN`: not enough evidence to decide;
- `DRIFT`: managed content differs from its recorded canonical state.

Translate every visible label into the user's language and explain `INFERRED`, `UNKNOWN`, or
`DRIFT` the first time it appears.

## Keep command roles distinct

- `$ultracode` executes engineering work, routes uninitialized change work through the read-only
  `$ultracode-init` baseline preflight, and publishes compact updates at phase or barrier changes.
- `$ultracode-init` discovers a project and explains a reviewable configuration proposal before writing.
- `$ultracode-edit` explains the requested configuration delta, drift, preservation, and regeneration.
- `$ultracode-flow` gives a concise live control view with fully explained active tickets.
- `$ultracode-status` gives the detailed diagnostic view, including history, files, checks, and findings.
- `$ultracode-help` explains how UltraCode works, which command to choose, models, reasoning effort,
  examples, and safety boundaries without changing the project.

All six commands use the same vocabulary and truth sources. They differ in depth and purpose, not
in the meaning of states, tickets, agents, models, evidence, or blockers.
