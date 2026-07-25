# Claude Code runtime adapter

Read this reference before invoking, routing, delegating, or reporting anything while UltraCode runs
inside Claude Code. It maps the runtime-neutral rules in `reasoning-routing.md`,
`routing-and-delegation.md`, and `swarm-protocol.md` onto the mechanisms Claude Code actually
exposes. Codex remains the other supported runtime; nothing here replaces the Codex behaviour.

Detect the runtime before applying any mapping. Treat the runtime as Claude Code when the session
exposes an `Agent` (or `Task`) delegation tool, plugin skills addressed as `/ultracode:<name>`, or a
`CLAUDE.md` project memory file. When the runtime is ambiguous, say so and apply only the
runtime-neutral rules.

## Invocation

`$ultracode-<command>` is the Codex invocation token. Claude Code addresses the same skills through
the plugin namespace. Both forms select the same skill and the same behaviour.

| Codex | Claude Code | Selects |
| --- | --- | --- |
| `$ultracode-help` | `/ultracode:ultracode-help` | Help |
| `$ultracode` | `/ultracode:ultracode` | UltraCode |
| `$ultracode-verify` | `/ultracode:ultracode-verify` | Verify |
| `$ultracode-init` | `/ultracode:ultracode-init` | Init |
| `$ultracode-edit` | `/ultracode:ultracode-edit` | Edit |
| `$ultracode-flow` | `/ultracode:ultracode-flow` | Flow |
| `$ultracode-status` | `/ultracode:ultracode-status` | Status |

Short aliases `/ultracode:help`, `/ultracode:ultra`, `/ultracode:verify`, `/ultracode:init`,
`/ultracode:edit`, `/ultracode:flow`, and `/ultracode:status` are shipped as plugin commands and
route to the same skills.

Apply the Help precedence rule to every form. `/ultracode:ultracode-help flow`, `$ultracode-help
flow`, and `ultracode-help flow` are the same read-only Help request about Flow. The invocation
token is never itself the topic.

When a user is on Claude Code, show the `/ultracode:` form in copyable examples. Showing the `$`
form to a Claude Code user hands them a token their runtime does not resolve.

## Lead model and reasoning effort

The rule that UltraCode cannot replace the lead model mid-task holds on Claude Code. The session
model and session effort are chosen when the session starts or through the user's own `/model`
selection. UltraCode must not change them and must not infer them from a project preference or a
configuration file.

Report the lead as `inherit`. Report the effective lead model or effort only when the runtime
exposes it in this session; otherwise report it as unobservable. A model name printed in a plugin
manifest, a settings file, or an earlier session is not evidence about this session.

## Map role classes to Claude Code models

The configured role classes are runtime-neutral. Resolve them per runtime instead of emitting a
Codex model identifier into a Claude Code dispatch.

| Role class | Codex identifier | Claude Code alias |
| --- | --- | --- |
| Coordination, architecture, security, migration, data integrity, high-impact ambiguity | `gpt-5.6-sol` | `opus` |
| Material finding verification and critical integrated review | `gpt-5.6-sol` | `opus` |
| Bounded discovery, documentation, localized implementation, mechanical validation | `gpt-5.6-terra` | `sonnet` |
| Complex but bounded implementation | `gpt-5.6-terra` at the scored effort | `sonnet` at the scored effort |
| Trivial mechanical extraction with a directly checkable result | not routed | `haiku` |

Omitting the model is a valid and often better dispatch: an agent with no `model` inherits the
session model, which is the honest default when the user has already chosen their lead. Set a model
only when the role class genuinely requires a different tier, and report requested and effective
values separately either way.

Never emit `gpt-5.6-sol` or `gpt-5.6-terra` as a Claude Code model value. If the user explicitly
supplies an exact identifier this runtime does not expose, do not silently substitute it: state that
the identifier is unavailable here, apply `swarm.model_policy.fallback`, and report the effective
alias.

## Map the effort ladder

Claude Code exposes adaptive reasoning effort as `low`, `medium`, `high`, `xhigh`, and `max`. The
scoring table in `reasoning-routing.md` is unchanged; only the top of the ladder differs.

| Scored effort | Claude Code effort |
| --- | --- |
| `low` | `low` |
| `medium` | `medium` |
| `high` | `high` |
| `xhigh` | `xhigh` |
| `max` | `max` |
| `ultra` | `max`, reported as clamped |

`ultra` has no Claude Code equivalent. Clamp it to `max` and record the clamp in the dispatch
ledger; never report a clamped dispatch as if the requested level took effect. Some model versions
do not expose `xhigh`; when a requested level is rejected, fall back one level, keep the requested
value in the ledger, and report the effective value separately.

Effort floors and caps in the configured policy still apply after the mapping, not before it.

## Delegate through the Agent tool

Claude Code delegates through the `Agent` tool (`Task` is an accepted alias). One call creates one
subagent. The parameters that carry UltraCode's routing decisions are:

| Decision | Parameter |
| --- | --- |
| Which role class runs the job | `subagent_type` |
| The complete job brief | `prompt` |
| Model override for the role class | `model` |
| Scored reasoning effort | `effort` |
| Exclusive workspace for a writing worker | `isolation: "worktree"` |

The subagent's final message is the return value. It reaches the lead, not the user. Say so in every
brief, and require the status payload the lead ledger needs rather than a human-facing summary.

### A subagent starts from a fresh context

A Claude Code subagent does not inherit the lead's conversation. It loads project context —
`CLAUDE.md`, skills, MCP servers — and nothing else.

This satisfies the independence requirement for adversarial verification directly: a verifier
spawned this way is structurally fresh, so a `CONFIRMED` verdict from it is independent evidence.

It also means a brief that references "the finding above", "the file we discussed", or "the same
scope as the previous job" transfers nothing. Every job template in `routing-and-delegation.md` must
be sent complete, with the raw evidence inlined or referenced by exact path.

### Run a wave concurrently

Issue every dispatch of one wave as multiple `Agent` calls in a single assistant message; that is
what makes them run concurrently. Calls sent in separate messages serialize.

Claude Code does not document a fixed concurrency limit, and the effective limit varies by version
and account. Do not assume a number and do not print one as fact. Dispatch the wave, observe what
actually starts, keep every remainder visible as `QUEUED`, and apply the existing rule: a platform
slot limit is not a total-agent limit.

Long-running subagents may complete in a later turn rather than blocking. Treat a pending result as
a live job under the integration protocol: do not synthesize, and do not finish, while a dispatched
job can still change the conclusion or the files.

### Prevent overlapping writes

The delegation gate that forbids two concurrent writes to the same files is unchanged. Claude Code
adds one mechanism for satisfying it: `isolation: "worktree"` gives a writing worker its own git
worktree.

Use it only when concurrent workers would otherwise contend for the same paths — it costs setup time
and disk per agent. Exclusive path ownership stated in the brief remains the cheaper and preferred
control. Never use a worktree as a substitute for inspecting the resulting writes.

## Shipped role agents

The plugin ships four read-mostly role agents under the plugin namespace:

| Agent | Role class | Write access |
| --- | --- | --- |
| `ultracode-explorer` | bounded discovery answering one specific question | read-only |
| `ultracode-verifier` | adversarial verification of one material finding | read-only |
| `ultracode-reviewer` | independent review of an integrated diff | read-only |
| `ultracode-worker` | implementation of one component under exclusive ownership | workspace write |

Pass them as `subagent_type` and address them in chat as `@ultracode:<name>`. They carry the role
contract; they do not carry the job. Send the full job template from `routing-and-delegation.md` as
the `prompt` regardless of which agent type runs it.

When a shipped agent is unavailable, `general-purpose` with the same brief is an acceptable
substitute, and `Explore` is an acceptable read-only substitute for `ultracode-explorer`. Record the
substitution. Reusing the lead context instead of a fresh agent is not a substitution: disclose it
and do not promote the result to independent confirmation.

## Project memory

Claude Code loads `CLAUDE.md` from the project root and `.claude/`, walking up to the repository
root, plus the user-scope file. The `@path` import syntax works inside those files, resolves
relative to the importing file, and nests up to four hops.

This is what makes the `CLAUDE.md` projection in `project-adapter.md` sufficient: a managed
`@AGENTS.md` import gives Claude Code the same canonical guidance that Codex reads directly. Keep
`AGENTS.md` canonical and the projection thin. Do not duplicate rule text into `CLAUDE.md`, and do
not write outside the managed markers.

## What stays unobservable here

Report these as unobservable rather than inferring them:

- the lead model and effort of an already-open session, unless the runtime states them;
- whether a requested subagent `model` or `effort` was actually applied, unless the runtime reports
  the effective value back;
- the real concurrency ceiling before a wave is dispatched;
- anything about a queued job's effective runtime values, which do not exist yet.

Flow and Status must show requested values for queued work and never invent effective ones.
