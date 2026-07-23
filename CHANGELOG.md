# Changelog

All notable changes to UltraCode are documented here.

## [Unreleased]

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
