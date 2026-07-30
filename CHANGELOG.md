# Changelog

All notable changes to UltraCode are documented here.

## [Unreleased]

## [0.7.0-rc.2] - 2026-07-31

This is a release candidate, not a stable release. The Conventional Commits command is packaged
and structurally validated, but its fresh runtime forward test is still pending and the PowerShell
release checker was unavailable in this environment.

### Added

- `ultracode-commit`, an eighth public skill and matching command for preparing and validating
  Conventional Commits 1.0.0 messages from the real Git diff.

### Safety

- Commit-message preparation remains read-only by default. Staging, committing, amending, rebasing,
  pushing, tagging, publishing, and pull-request actions still require separate explicit authority.

## [0.7.0-rc.1] - 2026-07-25

This is a release candidate, not a stable release. The Claude Code runtime support below is
installable and was exercised end to end, but the forward-test suite has not been re-run against it
— see the Note at the end of this entry.

### Added

- Claude Code as a supported runtime alongside Codex: `.claude-plugin/marketplace.json` at the
  repository root and `plugins/ultracode/.claude-plugin/plugin.json`, so the existing seven skills
  install with `/plugin marketplace add` and `/plugin install`.
- `references/claude-code-runtime.md`, the runtime adapter that maps role classes to Claude Code
  models, maps the effort ladder, names the delegation tool and its parameters, and lists what stays
  unobservable there.
- Seven Claude Code slash commands (`/ultracode:help`, `:ultra`, `:verify`, `:init`, `:edit`,
  `:flow`, `:status`) routing to the same skills.
- Four Claude Code role agents — `ultracode-explorer`, `ultracode-verifier`, `ultracode-reviewer`,
  and `ultracode-worker` — carrying the read-only, fail-closed, and exclusive-ownership contracts
  the lead delegates against.

### Changed

- Model routing selects a role class first and resolves it per runtime; emitting a `gpt-5.6-*`
  identifier into a Claude Code dispatch is now stated as a routing error, not a fallback.
- A scored `ultra` effort is clamped to `max` on Claude Code and reported as clamped.
- Delegation guidance names the concrete Claude Code mechanism: `Agent` tool parameters, fresh
  subagent context as the source of verifier independence, whole-wave dispatch in a single message,
  and `worktree` isolation for contending writers.
- Help and the command interface recognize `$ultracode-*` and `/ultracode:*` as the same invocation
  and emit the form belonging to the runtime the user is actually on.

### Note

- `references/evaluation-evidence.json` now carries the `0.7.0-rc.1` version prefix, but its
  `scenario_results` were produced on 2026-07-24 against the 0.6.0 skill text, before these changes.
  The file hashes were regenerated for local consistency only. The forward-test suite in
  `references/eval-prompts.md` must be re-run, on both runtimes, before a stable 0.7.0 is tagged.
  This is why 0.7.0-rc.1 ships as a pre-release.

## [0.6.0] - 2026-07-24

### Added

- `$ultracode-verify`, a seventh public skill for durable feature-level functional verification.
- A closed JSON verification-plan schema with append-only scenario histories and exactly
  `planned`, `passed`, `failed`, `not-run`, and `not-applicable` statuses.
- Main UltraCode, Help, Flow, and Status integration for verification-plan creation, coverage,
  evidence, derived outcomes, blockers, and drift.

### Safety

- Passed and failed results require direct status-consistent evidence; skipped and inapplicable
  results require reasons and cannot contain execution evidence.
- Incomplete, contradictory, stale, duplicated, or orphaned plan content fails closed instead of
  being normalized or overwritten.
- Verification-plan authority never implies Git, publishing, external requests, dependencies,
  destructive actions, production writes, or deployment.

## [0.5.3] - 2026-07-24

### Fixed

- The Python project doctor now canonicalizes a project root reached through an ancestor junction or
  symlink before comparing managed paths, preventing a false “outside the repository” failure in
  Windows temporary directories. The configurator corpus covers that route explicitly.

## [0.5.2] - 2026-07-23

### Changed

- Complete Help now renders as chat-friendly Markdown with a title, comparison tables, H3 command
  sections, short labeled fields, and examples embedded beside their commands.
- The repeated six-example footer has been removed so the full overview remains scannable.
- Python, PowerShell, and repository validators now fail closed when the required chat layout is
  flattened or its tables and blockquote examples are removed.
- An explicit `$ultracode-help` invocation now takes precedence over command names used as topics,
  so `$ultracode-help flow` explains Flow instead of reconstructing live task state.

## [0.5.1] - 2026-07-23

### Changed

- A bare `$ultracode-help` invocation now requires a complete ordered overview instead of allowing
  the model to compress away command, startup, routing, ticket, or authority details.
- Explicit command topics use focused mode, while only `breve` or `sintetico` enables compact mode.
- Help now uses a semantic completion checklist: wording remains natural, but required facts cannot
  be omitted.

## [0.5.0] - 2026-07-23

### Added

- `$ultracode-help`, an always read-only command guide that recommends the right UltraCode command and supports detailed help for `ultracode`, `init`, `edit`, `flow`, `status`, `models`, and `examples`.
- Canonical command documentation with a decision path, confirmation boundaries, comparisons, copyable prompts, and honest requested-versus-effective model and effort reporting.
- Objective-driven reasoning policy with Terra `low` as the bounded default, Sol verification floors,
  explicit critical floors, and guarded `max` or `ultra` escalation.

### Changed

- README command documentation now covers all six commands and explains the Terra/Sol effort policy without claiming runtime values that are not observable.
- New-task guidance recommends Sol `medium` for the lead while keeping the active task inherited and
  global Codex settings untouched unless the user separately requests a change.
- Flow and Status now report requested and effective reasoning effort plus the evidence that selected
  it, including fallback or context inheritance.
- The deterministic configurator now surfaces denied temporary-file creation immediately instead of
  retrying until a long timeout.
- Claude root candidates are now checked for symlink, junction, and reparse traversal before file
  selection, decoding, or hashing, with regressions for nested and top-level adapter paths.

## [0.4.0] - 2026-07-23

### Added

- `$ultracode-flow`, a quick read-only control view for the current objective, phase, active or blocked tickets, responsible and live agents, requested and effective models, completion criteria, and immediate next action.
- A shared plain-language command interface that explains every active or blocked ticket by reusing its real UltraCode job ID.

### Changed

- `$ultracode` now explains the work graph, ticket purpose, ownership, and completion criteria before execution, then reports only material changes during routine updates.
- `$ultracode` now detects uninitialized projects before change work, runs the read-only `$ultracode-init` preflight automatically, asks before initialization writes, and resumes the original task after a verified apply.
- `$ultracode-init` now explains the proposed setup, evidence level, practical effect, and confirmation boundary before writing.
- `$ultracode-edit` now explains configuration changes as a before-and-after delta, including drift conflicts and affected projections.
- `$ultracode-status` is now the detailed diagnostic view, distinct from the shorter `$ultracode-flow` snapshot.
- Agent and model reporting now distinguishes responsible ownership from the live runtime agent, and the requested model from the effective model or fallback.

### Safety

- Configurator and project doctors now reject reparse boundaries on the canonical `.ultracode` control files before reading their targets.
- Rule-path selectors now use the same portable relative-path grammar as managed artifacts, rejecting traversal, absolute, backslash, and machine-local paths.

## [0.3.0] - 2026-07-22

### Added

- Deterministic project configurator with read-only plan IDs and confirmed apply for `$ultracode-init` and `$ultracode-edit`.
- Explicit model-ID policy support, including `gpt-5.6-sol` and user-supplied exact model IDs, with reported fallback when unavailable.
- Persisted rule-to-path mappings so Claude rule adapters are reproducible from canonical config.

### Safety

- Atomic per-file replacement, whole-plan rollback on later write failure, and managed manifest written last.
- Doctor-valid desired-state preflight plus drift, stale-plan, unmanaged-file, casing, traversal, symlink, junction, and reparse rejection before project writes.
- Idempotent repeated apply, byte-exact preservation outside managed blocks, ownership conflicts for unmanifested pre-existing markers, and no automatic adapter deletion.

## [0.2.0] - 2026-07-22

### Added

- Adaptive work-graph derivation from real independent units and orthogonal lenses.
- Adversarial verification for deduplicated material findings and a single synthesis owner.
- Guided `$ultracode-init` setup for shared Codex and Claude Code project control.
- Drift-safe `$ultracode-edit` regeneration that preserves manual work.
- Read-only `$ultracode-status` reporting for milestones, agents, files, checks, and blockers.
- Python and PowerShell project doctors with mirrored adversarial corpora.
- Deterministic release-evidence and plugin-payload attestation.
- Minimal UltraCode brand icon and public Codex marketplace packaging.

### Safety

- Read-only command gate for answer, review, audit, and diagnosis requests.
- Explicit external-action and destructive-action authority boundaries.
- Reparse-point rejection, exact schema casing, managed-content drift detection, and canonical adapter semantics.
