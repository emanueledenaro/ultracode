---
name: ultracode-flow
description: Concise, read-only live control view for an UltraCode task. Use when the user explicitly invokes `$ultracode-flow` or asks for a quick but fully explained view of the objective, phase, active tickets, assigned agents, requested and effective models and reasoning effort, blockers, completion criteria, and next actions. Use `full` for all known tickets or `agents` for an agent-focused view.
---

# UltraCode Flow

Show what is happening now in a form the user can understand in one pass and act on immediately.

## Stay read-only

Do not write status files, edit configuration, run write-producing checks, regenerate adapters, or
change the task merely to refresh the view.

Read these resources completely:

- `../ultracode/references/command-interface.md`
- `../ultracode/references/control-and-status.md`

Read `../ultracode/references/swarm-protocol.md` when delegated jobs, findings, or waves exist.

## Reconstruct current truth

Use sources in this order:

1. current live task, plan, and collaboration state;
2. results and evidence already observed by the lead;
3. persisted `.ultracode/status.md`, when present;
4. repository history only when the user requests historical context.

Classify freshness internally as `LIVE`, `STALE`, or `IDLE`, but present it in the user's
language with a reason. For example, explain that data is not current because the last snapshot
predates live work. Show the snapshot timestamp when relying on persisted state. Never treat a
stale file as live truth.

## Keep tickets and agents distinct

A ticket is a bounded unit of work in the user-facing view; it maps one-to-one to a logical job and
reuses that job's `U-*`, `L-*`, `V-*`, or `S-*` ID. A responsible owner is accountable for
the ticket; a live agent is a currently running instance.
Never invent parallel `T-*` or `A-*` IDs when the work graph or runtime does not provide them.
Never use an agent ID, ticket ID, role, phase, or status as if it explained the work by itself.

For each active or blocked ticket, show:

1. ticket ID and action title;
2. state, explained in the user's language;
3. **Why it exists** and what part of the objective it supports;
4. what the agent is doing now;
5. responsible owner and understandable role;
6. live agent name or ID only when the runtime provides one;
7. requested model and effective model;
8. requested reasoning effort, effective effort, and why the objective selected it;
9. whether no runtime value is selected yet, a fallback occurred, context forced inheritance, or
   the runtime hides the effective model or effort;
10. completed work and concrete evidence;
11. remaining work and any blocker;
12. **Completion criterion** that can be verified;
13. next action;
14. active file ownership when the ticket can write.

Do not duplicate the same agent details in a second table.

## Render the default view

Start with:

- `ULTRACODE FLOW` plus a plain-language freshness explanation;
- objective;
- current phase;
- total, completed, active, queued, and blocked ticket counts;
- live-agent capacity and current wave only when delegation exists.

Then render every active or blocked ticket using the shared command interface. Summarize recently
completed tickets in one line each. End with decisions required, if any, and the next overall
action.

Do not add a generic summary section that repeats the ticket cards. Do not invent percentages or
ETAs. Do not dump transcripts.

## Support focused views

- `$ultracode-flow`: fully explain active and blocked tickets; summarize completed and queued work.
- `$ultracode-flow full`: include every known ticket, dependencies, findings, files, and validation evidence.
- `$ultracode-flow agents`: focus on every live agent, its ticket, role, requested model, effective
  model, requested and effective reasoning effort, routing reason, current action, latest result,
  wait reason, and file ownership.

Never hide blockers, authorization requests, failed checks, ownership conflicts, model fallbacks,
or material unknowns in a focused view.

## Handle quiet states

If no task is active, say so directly in the user's language. Show the last completed outcome only
when a verified snapshot exists and label its timestamp. If UltraCode is not initialized, explain
that live conversation state can still be shown while `$ultracode-init` adds persistent project
control.
