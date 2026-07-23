# UltraCode project context

## Mission and targets

UltraCode is a Codex plugin for transparent, adaptive, evidence-driven multi-agent software engineering. It targets the Codex plugin marketplace, Codex desktop and CLI, shared Claude Code project adapters, and Windows-based validation.

UltraCode does not require accounts, API keys, MCP servers, background services, or telemetry. Project initialization must derive facts from the current repository and must not copy domain guidance or machine-local settings from another project.

## Repository map

- `.agents/plugins/marketplace.json` is the public Codex marketplace entry.
- `plugins/ultracode/.codex-plugin/plugin.json` is the installable plugin manifest.
- `plugins/ultracode/skills/` contains the six public skills and their agent metadata.
- `plugins/ultracode/skills/ultracode/references/` contains the canonical orchestration protocol, schemas, evaluation prompts, evidence, and traces.
- `plugins/ultracode/skills/ultracode/scripts/` contains mirrored Python and PowerShell doctors and contract validators.
- `scripts/validate_repository.py` validates the public repository structure and packaging.
- `.github/workflows/validate.yml` runs the strict repository and contract checks on Windows.
- `plugins/ultracode/assets/` contains packaged brand assets.

There are no dependency installation, formatter, linter, typecheck, build, runtime, health, migration, or database commands in the repository. Generated caches, local settings, credentials, permission allowlists, locks, PIDs, session artifacts, and absolute machine paths must remain outside tracked and managed content.

## Stable invariants

- The live conversation is the primary control surface and must remain observable and interruptible.
- Work graphs are derived from real independent units; agent count is never a quality target.
- Material findings receive adversarial verification when collaboration is available, followed by one synthesis owner.
- Read-only requests remain read-only; authority for Git, external, destructive, dependency, and deployment actions is explicit-only.
- `AGENTS.md` and canonical `.agents` content are the shared source of truth. Codex and Claude files are projections, not independent semantic copies.
- Managed files and blocks must preserve user-authored content, portable casing, exact schemas, and reparse-point boundaries.
- Python and PowerShell validators must remain behaviorally equivalent.
- Structural validation does not replace fresh behavioral evaluation for material protocol changes.

## Verified commands

Run from the repository root:

```powershell
python scripts/validate_repository.py
python plugins/ultracode/skills/ultracode/scripts/run_project_configurator_corpus.py
python plugins/ultracode/skills/ultracode/scripts/check_contract.py
powershell.exe -NoProfile -ExecutionPolicy Bypass -File plugins/ultracode/skills/ultracode/scripts/check_contract.ps1
```

These commands are declared by both the README and the Windows CI workflow. Completion requires successful final exit codes from all four, final diff inspection, and independent review for material changes.

## Protected boundaries

Never include credentials, private repository content, machine-local configuration, private evaluation data, or unrelated user changes. Publishing, staging, committing, pushing, releasing, dependency changes, and deployment require separate explicit authorization.
