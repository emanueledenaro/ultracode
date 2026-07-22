# Contributing

Contributions should preserve UltraCode's central property: the user can always understand, interrupt, and verify the work.

## Before changing behavior

1. Open an issue describing the concrete failure or missing capability.
2. Identify the affected behavioral contract and evaluation scenario.
3. Keep Codex and Claude Code project adapters derived from the same canonical source.
4. Do not weaken authority, visibility, evidence, or drift-protection gates to simplify an implementation.

## Pull requests

- Keep changes scoped and explain the behavioral impact.
- Update `CHANGELOG.md` for user-visible changes.
- Add or update an evaluation scenario when protocol behavior changes.
- Keep Python and PowerShell validators behaviorally equivalent.
- Run all commands from the README validation section.
- Do not commit credentials, machine-local configuration, generated caches, or private evaluation data.

Pull requests should state what changed, why it changed, the risks, and the exact validation performed.
