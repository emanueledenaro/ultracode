# UltraCode plugin contract maintenance

Apply this rule to changes affecting the plugin payload, repository validator, marketplace metadata, documentation, or CI.

Before changing behavior, read `plugins/ultracode/skills/ultracode/references/behavioral-contract.md` and the relevant scenarios in `plugins/ultracode/skills/ultracode/references/eval-prompts.md` completely.

For every material behavior change:

- identify the affected contract scenario and add or update evaluation coverage;
- keep the Python and PowerShell validators and doctor corpora behaviorally equivalent;
- preserve authority, visibility, evidence, drift-protection, exact-casing, and reparse-point gates;
- update `CHANGELOG.md` when behavior visible to users changes;
- recompute release evidence and payload hashes through the documented validation workflow rather than editing attestations speculatively;
- run the repository validator and both strict contract checkers, then inspect their final exit codes and the final diff.

Do not weaken a contract gate merely to make a fixture pass. Do not add credentials, machine-local settings, generated caches, private evaluation data, or unrelated cleanup.
