---
name: ultracode-status
description: Read-only explanation of where an UltraCode task currently stands. Use when the user explicitly invokes `$ultracode-status` or asks where the AI is, what has finished, what agents are active or queued, which files changed, what checks passed, what is blocked, or what happens next. Never mutate the repository merely to refresh status.
---

# UltraCode Status

Explain the current state so the user can decide whether to continue, redirect, pause, or stop.

## Stay read-only

Do not write a status file, run a write-producing build or test, regenerate adapters, or change configuration. Reading collaboration state, plans, Git status, `.ultracode/config.json`, and `.ultracode/status.md` is allowed when available.

Read `../ultracode/references/control-and-status.md` completely. Read `../ultracode/references/swarm-protocol.md` when delegated jobs or findings exist.

## Reconcile sources

Use this precedence:

1. current live task and collaboration state;
2. current lead plan and known validation results;
3. persisted `.ultracode/status.md` snapshot;
4. repository history only when the user asks for historical status.

Show the snapshot timestamp and label it `STALE` when it conflicts with the live task or predates relevant work. If UltraCode is not initialized, say so and explain that `$ultracode-init` creates persistent project control; do not initialize automatically.

## Report the control view

Lead with the objective and phase. Then show, at the requested detail level:

- completed, active, queued, and next milestones;
- logical jobs versus currently live agent instances;
- independent units, orthogonal lenses, findings, verifier outcomes, waves, and the single synthesis owner;
- files changed or currently owned by writers;
- validation states using `PASSED`, `FAILED`, `BLOCKED`, `NOT AVAILABLE`, or `NOT RUN`;
- blockers, authorization waits, unresolved `UNKNOWN` findings, and the next concrete action.

Never invent percentages, agent counts, test results, or ETAs. Do not dump raw agent transcripts. If no task is active, state that directly and show the last persisted outcome only when one exists.
