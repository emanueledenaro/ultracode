---
name: ultracode-status
description: Detailed, read-only diagnosis of an UltraCode task. Use when the user explicitly invokes `$ultracode-status` or asks for complete job history, files, findings, model and reasoning effort, validation evidence, blockers, persisted-state freshness, or a full diagnostic account. Do not select this skill when the request explicitly invokes `$ultracode-help`; `status` is then only a Help topic. Prefer `$ultracode-flow` for a quick current-work snapshot. Never mutate the repository merely to refresh status.
---

# UltraCode Status

## Respect explicit Help precedence

If the request explicitly invokes `$ultracode-help` or `ultracode-help`, do not inspect live state.
Read `../ultracode-help/SKILL.md` and answer `status` as a read-only Help topic.

Explain the current state so the user can decide whether to continue, redirect, pause, or stop.

## Stay read-only

Do not write a status file, run a write-producing build or test, regenerate adapters, or change configuration. Reading collaboration state, plans, Git status, `.ultracode/config.json`, and `.ultracode/status.md` is allowed when available.

Read `../ultracode/references/command-interface.md` and
`../ultracode/references/control-and-status.md` completely. Read
`../ultracode/references/swarm-protocol.md` when delegated jobs or findings exist.

Status is the detailed diagnostic view; Flow is the concise live control view. When the user
explicitly invokes `$ultracode-status`, stay in the detailed view. For an unqualified request for
a fast active-work snapshot, prefer `$ultracode-flow`. Keep status for complete job history,
files, findings, validation, persistence, and staleness analysis.

## Reconcile sources

Use this precedence:

1. current live task and collaboration state;
2. current lead plan and known validation results;
3. persisted `.ultracode/status.md` snapshot;
4. repository history only when the user asks for historical status.

Show the snapshot timestamp and classify it internally as `STALE` when it conflicts with the live
task or predates relevant work. Present freshness in the user's language and explain exactly why
the data is or is not current. Never expose bare `LIVE`, `STALE`, `IDLE`, or `UNKNOWN` as the
reader-facing freshness statement; keep a canonical code only as secondary detail when it helps
diagnosis. If UltraCode is not initialized, say so and explain that
`$ultracode-init` creates persistent project control; do not initialize automatically.

## Report the control view

Lead with the objective and phase. Then show, at the requested detail level:

- completed, active, queued, and next milestones;
- logical jobs versus currently live agent instances;
- independent units, orthogonal lenses, findings, verifier outcomes, waves, and the single synthesis owner;
- files changed or currently owned by writers;
- validation states translated into the user's language, with `PASSED`, `FAILED`, `BLOCKED`,
  `NOT AVAILABLE`, or `NOT RUN` retained only as secondary diagnostic detail;
- blockers, authorization waits, unresolved `UNKNOWN` findings, and the next concrete action.

For every active or blocked ticket, explain why it exists, its assigned agent, requested and
effective model, requested and effective reasoning effort, the objective evidence that selected
them, current work, evidence produced, remaining work, blocker, completion criterion, and next
action. Define ticket, agent, logical job, wave, barrier, drift, fallback, and effort inheritance
when the reader would otherwise have to infer their meaning.

Never invent percentages, agent counts, test results, or ETAs. Do not dump raw agent transcripts. If no task is active, state that directly and show the last persisted outcome only when one exists.
