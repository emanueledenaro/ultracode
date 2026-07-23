---
name: ultracode-help
description: Explain and help choose UltraCode commands without changing the task or repository. Use when the user invokes `$ultracode-help` or `ultracode-help`, asks what UltraCode can do, which of `$ultracode`, `$ultracode-init`, `$ultracode-edit`, `$ultracode-flow`, `$ultracode-status`, or Help to use, or asks about UltraCode control, tickets, agents, models, effort, initialization, safety, or validation.
---

# UltraCode Help

Explain UltraCode's six commands in the user's language. This command is always read-only: do not initialize a project, delegate, run tests or builds, modify files, or create a plan merely to answer.

Read [the command guide](../ultracode/references/command-guide.md) completely before answering. It
is the canonical detailed guide. For the `models` topic or a question about effort selection, also
read [the reasoning router](../ultracode/references/reasoning-routing.md) completely.

## Answer the request

Accept `ultracode`, `init`, `edit`, `flow`, `status`, `models`, and `examples` as optional topics;
accept the same names with a leading `$` or the complete command name. Treat `help` as a request
for the default overview.

- With no topic, give the decision path and explain all six commands: purpose, when to use it, writes and confirmation boundary, result, comparison, and one copyable example each.
- With a command topic, explain that command first, then give the shortest useful comparison and a copyable example.
- With `models`, explain active-chat inheritance, objective-driven model and reasoning effort selection,
  requested versus effective values, fallback, and context constraints.
- With `examples`, offer one safe, concrete prompt for each command.
- If the request is ambiguous, recommend the least powerful command that meets it. Do not invoke or simulate the recommended command.

## Keep claims honest

Explain that UltraCode inherits the model of the chat in which it is opened. Normal subagents default to Terra with low effort and rise only when the objective justifies it; verifiers use Sol at least high, and critical work at least xhigh. Distinguish requested model and effort from effective runtime values and fallback. If the runtime does not expose an effective value, say it is not observable rather than inventing it.

Explain that read-only questions can work without `.ultracode`. Change work in an uninitialized project gets a read-only initialization proposal and one confirmation before setup writes. Git, deployment, external, destructive, and dependency actions always need explicit user authority. Tickets describe bounded jobs; agents are live workers only when the runtime actually has them.

Never claim current task state, files, checks, agents, models, effort, fallback, or initialization status unless the user supplied it or the active runtime exposes it.
