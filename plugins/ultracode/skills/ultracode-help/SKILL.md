---
name: ultracode-help
description: Explain and help choose UltraCode commands without changing the task or repository. Use when the user invokes `$ultracode-help` or `ultracode-help`, asks how UltraCode works or which command fits, or asks about UltraCode initialization, control, tickets, agents, models, reasoning effort, safety, validation, or examples. Support focused command and model topics plus an explicitly brief or synthetic mode.
---

# UltraCode Help

Explain UltraCode in the user's language. Remain strictly read-only: do not initialize, plan project
changes, delegate, run tests or builds, refresh task state, or modify any file.

Read [the command guide](../ultracode/references/command-guide.md) completely before answering. Read
[the reasoning router](../ultracode/references/reasoning-routing.md) completely for `models` or any
question about model or effort selection.

## Select the response mode

First remove the invocation token `$ultracode-help` or `ultracode-help` from the request.
The invocation token is never itself the `help` topic. Only the remaining words can select a mode.
Normalize remaining topics with or without `$`: `ultracode`, `init`, `edit`, `flow`, `status`,
`help`, `models`, and `examples`. Accept complete command names such as `ultracode-status`.
An explicit Help invocation has precedence over every command name in the remaining words:
`$ultracode-help flow` explains Flow and must never execute `$ultracode-flow`.

- **No remaining topic:** render the complete overview. A bare `Use $ultracode-help` invocation and
  a broad request such as "come funziona?", "come inizio?", or "spiegami UltraCode" are not
  focused topics.
- **Explicit topic:** answer that topic first and include only the minimum comparison and example
  needed to place it correctly. Do not expand into the complete overview.
- **Explicit `breve` or `sintetico`:** use compact mode. Compress prose, never truth conditions or
  a requested topic. For a no-topic overview, retain every mandatory overview block.
- **Ambiguous choice:** recommend the least powerful command that satisfies the outcome. Explain
  the recommendation; do not invoke or simulate it.

## Render the complete overview

Render for the chat surface, not as a dense document. Translate headings naturally into the user's
language while preserving this Markdown hierarchy and semantic order:

1. **Scelta rapida:** an H2 section containing a two-column GitHub-flavored Markdown table that maps
   user intent to the right command.
2. **Sei comandi:** explain `$ultracode-help`, `$ultracode`, `$ultracode-init`,
   `$ultracode-edit`, `$ultracode-flow`, and `$ultracode-status` under one H2 section. Give each
   command its own H3 subsection, the four bold fields below, and one copyable example in a
   blockquote directly inside that subsection.
3. **Progetto non configurato:** explain that read-only use works without `.ultracode`; change work
   preserves the original objective, enters the read-only Init preflight, and requires confirmation
   before initialization writes.
4. **Modelli ed effort:** distinguish Sol `medium` as guidance only before opening a new lead task;
   the active lead inherits its chat; bounded workers normally request Terra `low`; material
   verifiers request Sol with at least `high`; critical work uses at least `xhigh`. Explain
   requested versus effective values and fallback, and never present an unexposed runtime value as
   observed.
5. **Ticket e agenti:** tickets are bounded logical jobs; an owner is accountable; a live agent is
   a runtime instance only when one actually exists.
6. **Autorizzazioni:** Git, deployment, external, dependency, destructive, and privileged actions
   require explicit authority and are not implied by implementation approval.

Use one H1 title at the top, H2 headings for the six content areas, and H3 headings only for the
commands. Use a compact Markdown table for model routing and another for ticket versus agent. Keep
paragraphs short. Do not collect examples into a repeated section at the end and do not put the six
examples in separate fenced code blocks.

For each command explanation, cover all four required fields even in compact mode:

- **Quando usarlo**
- **Cosa ottieni**
- **Può scrivere?**
- **Quando chiede conferma**

Put the command's example immediately after those fields as a Markdown blockquote with an inline
code prompt.

## Keep focused answers complete

For a command topic, use one H2 command heading, the same four bold fields, its closest comparison,
and one blockquote example. For `models`, use a compact table and cover new-task guidance,
active-task inheritance, worker/verifier/critical routes, requested and effective model plus
effort, fallback, and runtime visibility. For `examples`, give one safe blockquote prompt per
command. For `help`, explain Help itself unless the user asked for a general overview.

Do not claim current task state, project initialization, files, checks, tickets, agents, models,
effort, or fallback unless the user supplied it or the active runtime exposes it. Do not change a
global Codex model or effort default; describe startup guidance only.

## Check before sending

Internally verify the response without printing this checklist:

- correct mode selected;
- read-only boundary preserved;
- no-topic overview contains all six content areas in order;
- the overview uses one H1, H2 sections, a quick-choice table, H3 command sections, inline
  blockquote examples, a model table, and a ticket-versus-agent table;
- every described command includes when, result, write capability, and confirmation trigger;
- model and effort claims separate requested, effective, inheritance, and fallback;
- one example per command appears in the overview;
- no runtime or project fact was invented.

Do not finish the response until every semantic item required by the selected mode is covered.
