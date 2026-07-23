# Repository adapter

Read this reference for `$ultracode-init`, `$ultracode-edit`, repository adoption, or project-control repair.

## Separate canonical content from projections

Use this ownership model:

```text
AGENTS.md                         common root contract
.ultracode/
  config.json                    machine-readable project and control policy
  managed.json                   ownership modes and last generated hashes
  status.md                      optional live snapshot
.agents/
  context/*.md                   canonical project documentation
  rules/*.md                     canonical path or workflow rules
  reviewers/*.md                 canonical reviewer criteria
  skills/<name>/SKILL.md         canonical project skills
.codex/
  agents/*.toml                  generated Codex projections when justified
  config.toml                    only verified Codex-specific settings
.claude/
  CLAUDE.md                      thin `@../AGENTS.md` import adapter
  rules/*.md                     path-frontmatter wrappers to canonical rules
  agents/*.md                    generated Claude projections
  skills/<name>/SKILL.md         thin adapters to canonical `.agents` skills
```

Do not create empty directories. Generate a role, rule, or skill only when a stable recurring need justifies it.

`AGENTS.md` and `.agents` are the shared source of truth. `.codex` and `.claude` contain tool-specific syntax or generated projections. Never maintain two independent semantic copies by hand.

## Minimum canonical guidance

Record verified stable facts under `.agents/context`:

- mission, supported target, and non-goals;
- source, tests, generated files, migrations, assets, and local-only data;
- entry points, boundaries, stable names, interfaces, and invariants;
- install, format, lint, typecheck, test, build, run, and health commands;
- checks that do not exist or remain unverified;
- protected files, dependency and migration rules, secrets, and external actions;
- completion evidence and the real execution path.

Keep the root `AGENTS.md` concise. Its exact `ultracode:project` block routes to `.ultracode/config.json`, every configured canonical artifact, and the highest-value constraints. References outside that block do not satisfy routing validation. Use nested `AGENTS.md` only for real subtree differences.

Every generated and registered canonical project skill uses deterministic frontmatter and a non-empty body:

```markdown
---
name: <directory-name>
description: "<JSON-escaped non-empty description>"
---

<canonical instructions>
```

The name must equal its `.agents/skills/<name>` directory. The Claude adapter copies that exact canonical description; it cannot substitute different discovery or activation semantics. User-owned skills not listed in `config.artifacts.skills` remain outside this managed contract.

## Managed markers

Use unique HTML comment markers in shared files:

```text
<!-- ultracode:project:start -->
...generated routing block...
<!-- ultracode:project:end -->
```

Use a distinct key for each block. Never edit text outside a managed block. Fail on missing, duplicated, nested, or reversed markers rather than guessing.

## Managed manifest

`.ultracode/managed.json` conforms to [managed-manifest.schema.json](managed-manifest.schema.json) and uses:

```json
{
  "schema_version": 1,
  "generated_by": "ultracode-init",
  "entries": [
    {
      "path": "AGENTS.md",
      "mode": "block",
      "start": "<!-- ultracode:project:start -->",
      "end": "<!-- ultracode:project:end -->",
      "sha256": "<lowercase hash of the LF-normalized complete block>"
    },
    {
      "path": ".claude/CLAUDE.md",
      "mode": "file",
      "sha256": "<lowercase hash of exact file bytes>"
    }
  ]
}
```

Rules:

1. Paths are repository-relative POSIX paths with no `..`, drive, home, or absolute prefix. Managed paths must not traverse symlinks, junctions, or other reparse points.
2. `file` means UltraCode created and owns the entire generated artifact, including canonical config or documentation and tool-specific projections.
3. `block` means UltraCode owns only the unique marked block.
4. Hash `file` entries from exact bytes.
5. Hash `block` entries from the complete start-to-end substring after CRLF/CR normalization to LF.
6. List `.ultracode/config.json` so direct manual edits are visible as drift; `$ultracode-edit` remains the safe modification path and preserves unknown forward-compatible keys.
7. Do not list `.ultracode/managed.json` itself or ephemeral status as generated content.
8. Unknown files remain user-owned.
9. `generated_by` is `ultracode-init` or `ultracode-edit`.
10. The manifest covers the config, the `AGENTS.md` managed block, every path in `config.artifacts`, all enabled Claude adapters, and every configured role projection. An empty or incomplete manifest is invalid.

On edit, hash before writing. A mismatch is drift, not permission to overwrite.

## Configuration contract

Create `.ultracode/config.json` from [project-config.schema.json](project-config.schema.json). Use POSIX relative paths. Preserve unknown keys during edits for forward compatibility. Its `artifacts` registry lists every canonical context, rule, and skill owned by initialization; the doctor derives required adapters from this registry.

Treat JSON property names and schema-constrained identifiers as ordinal and case-sensitive in every runtime. `plan_gate` and `Plan_Gate`, lower-case role IDs and upper-case variants, and portable artifact paths with different casing are different values; doctors and release checkers must fail closed rather than normalizing them.

Core invariants:

- `swarm.decomposition` is `data-driven`;
- `swarm.verification` is `one-per-material-finding`;
- `swarm.synthesis_agents` is `1`;
- `swarm.concurrency` is `auto` unless the user sets a proven technical limit;
- `swarm.hard_safety_cap` is a positive circuit breaker, default `1000`;
- `swarm.model_policy.lead` defaults to `inherit`, bounded agents prefer `gpt-5.6-terra`,
  verifiers prefer `gpt-5.6-sol`, and unavailable identifiers use the visible fallback;
- `swarm.reasoning_policy.mode` is `objective-driven`; bounded work normally starts at `low`,
  material verification is at least `high`, critical work is at least `xhigh`, and `max` or
  `ultra` require qualifying critical evidence under `reasoning-routing.md`;
- no normal `max_total_agents` setting exists;
- Git, external, destructive, dependency, and deployment actions remain explicit-only by default;
- status visibility does not grant unrelated write authority.

## Codex projection

Codex reads `AGENTS.md` and discovers project skills under `.agents/skills`. Keep `.codex/config.toml` untouched unless a verified Codex-specific setting is necessary. Generate `.codex/agents/<role>.toml` only for a stable role needing specialized read-only instructions, tools, sandboxing, or reasoning.

Each Codex custom-agent file must use exactly this deterministic projection. Introduce another supported setting only through a documented plugin/schema migration that updates the generator, doctor, fixtures, and manifest together:

```toml
# ultracode-canonical: .agents/reviewers/<role>.md
# ultracode-source-sha256: <lowercase hash>
name = "<role>"
description = "<escaped purpose>"
sandbox_mode = "read-only"
developer_instructions = """
Read and follow the canonical reviewer at `.agents/reviewers/<role>.md` completely before starting work.
Return evidence and stay inside the assigned job boundary.
"""
```

Map `role.mode` to Codex `sandbox_mode` as `read-only` or `workspace-write`. The doctor rejects a missing required field, mismatched name or mode, missing canonical directive, duplicate marker, or source hash that no longer matches its canonical reviewer. `roles[].skills` are lead-routing requirements; name them in each delegated job and let Codex load them through its supported skill mechanism rather than inventing unverified TOML.

Do not create one agent file per folder, framework, or swarm job. Runtime jobs are derived dynamically; stored agents define reusable roles.

## Claude Code projection

Prefer `.claude/CLAUDE.md` containing:

```markdown
@../AGENTS.md
```

If UltraCode creates the file, manage the whole file and emit exactly that import. If it already exists, manage only this exact block:

```markdown
<!-- ultracode:claude-root:start -->
@../AGENTS.md
<!-- ultracode:claude-root:end -->
```

For a root-level `CLAUDE.md`, use the same exact forms with `@AGENTS.md`. Content outside a managed block stays user-owned. Generated rule and skill adapters are also deterministic: no additional keys, duplicate keys, reordered fields, or extra/contradictory body text are allowed. Serialize every YAML string using JSON-compatible double quoting.

A rule adapter uses this exact shape, with one or more unique project-derived paths:

```markdown
---
paths:
  - "src/**"
---
<!-- ultracode-canonical: .agents/rules/<name>.md -->

Read and follow the canonical rule at `.agents/rules/<name>.md` completely before applying this adapter.
```

A skill adapter uses this exact shape, copying the canonical description byte-for-value after decoding:

```markdown
---
name: <name>
description: "<escaped description>"
---
<!-- ultracode-canonical: .agents/skills/<name>/SKILL.md -->

Read and follow the canonical skill at `.agents/skills/<name>/SKILL.md` completely before executing this skill.
```

Use only the marker appropriate to that adapter. The doctor rejects absent, duplicated, mismatched, ambiguous, or contradictory projections.

Generated Claude agents use required `name` and `description` frontmatter, an explicit permission mode, the canonical directive, and both provenance markers:

```markdown
---
name: <role>
description: "<escaped purpose>"
permissionMode: plan
---
<!-- ultracode-canonical: .agents/reviewers/<role>.md -->
<!-- ultracode-source-sha256: <lowercase hash> -->

Read and follow the canonical reviewer at `.agents/reviewers/<role>.md` completely before starting work.
Return evidence and stay inside the assigned job boundary.
```

Map a read-only role to `permissionMode: plan` and a workspace-write role to `permissionMode: default`. When `roles[].skills` is non-empty, project it as a JSON-quoted YAML block list in the configured order. Record the generated file hash in the managed manifest. The doctor validates the exact deterministic frontmatter and body, permission mode, canonical directive, projection hash, and canonical source hash.

Serialize project-derived strings with a real JSON, TOML, or YAML-safe encoder for the target file. Never interpolate raw interview text into quotes or frontmatter; reject control characters and invalid role IDs before generation.

Never generate `.claude/settings.local.json`, `CLAUDE.local.md`, scheduled-task locks, session IDs, permission allowlists, secrets, or absolute machine paths.

## Idempotent initialization and editing

`scripts/project_configurator.py` is the canonical writer for `$ultracode-init` and `$ultracode-edit`. Its `plan` command is read-only, renders the complete desired state in a disposable preflight, requires the project doctor to return `PASSED`, and then returns a deterministic `plan_id`, exact writes, ordered changes, and structured conflicts. Its `apply` command accepts only the unchanged proposal plus that confirmed `plan_id`, repeats the doctor preflight, rechecks manifest drift and path preconditions before writing, rejects symlinks, junctions, reparse traversal, unsafe casing, non-file collisions, unmanaged whole-file collisions, and unmanifested pre-existing managed markers. Each changed file uses a sibling temporary plus atomic replace; the manifest is last. If a later write fails, restore every earlier file byte-for-byte and remove files or empty directories created by the failed plan before returning `FAILED`; report any incomplete rollback explicitly.

Resolve the configurator's Python interpreter from a verified project command or the host runtime.
In Codex Desktop, use `codex_app.load_workspace_dependencies` when Python is not on `PATH`; use the returned
executable only for the current command and never write that machine-local absolute path into
managed files. If no interpreter exists, planning and apply are `NOT AVAILABLE`; no manual
substitute may write the managed projection.

Repeated plan/apply with the same desired state is a byte-and-mtime no-op. Existing bytes outside managed blocks remain user-owned. Adapter disablement never authorizes deletion; exact removals require separate explicit scope. The writer must not broaden the ownership recorded in `.ultracode/managed.json` merely because a canonical-looking file exists.

Initialization:

1. inspect before asking;
2. propose detected values;
3. preview exact files and conflicts;
4. create missing artifacts or add unique managed blocks;
5. record hashes;
6. run the project doctor;
7. inspect the final diff.

Editing:

1. run the doctor before changes;
2. compare manifest hashes;
3. preserve outside-block edits automatically;
4. require a choice for inside-block or generated-file drift;
5. update canonical content first;
6. regenerate only affected projections;
7. recompute hashes and rerun the doctor.

Disabling an adapter does not authorize file deletion. Leave managed projections in place unless the user explicitly approves the exact removal scope.

## Adoption checks

Before handoff, verify:

- every documented command is evidenced or marked unverified;
- no copied domain fact came from another project;
- canonical and projection paths resolve with portable casing;
- no managed path traverses a symlink, junction, or reparse point;
- all managed hashes match;
- every configured artifact and role has the required managed entry and adapter;
- local/session files remain outside the tracked surface;
- a `local` status path is untracked and ignored when the repository uses Git;
- Codex and Claude adapters point to the same canonical meaning;
- the configured status mode respects the current authority boundary.
