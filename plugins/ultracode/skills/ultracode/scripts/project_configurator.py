#!/usr/bin/env python3
"""Plan and apply deterministic UltraCode project configuration changes."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any


START = "<!-- ultracode:project:start -->"
END = "<!-- ultracode:project:end -->"
CLAUDE_START = "<!-- ultracode:claude-root:start -->"
CLAUDE_END = "<!-- ultracode:claude-root:end -->"
PORTABLE_PATH = re.compile(
    r"^(?!/)(?![A-Za-z]:)(?!~)(?!.*(?:^|/)\.{1,2}(?:/|$))[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*$"
)
RULE_SCOPE_PATH = re.compile(
    r"^(?!/)(?![A-Za-z]:)(?!~)(?!.*(?:^|/)\.{1,2}(?:/|$))"
    r"[A-Za-z0-9._*?-]+(?:/[A-Za-z0-9._*?-]+)*\Z"
)


class ConfiguratorError(ValueError):
    """Raised when a proposal cannot produce a safe deterministic plan."""


class ConfiguratorConflict(ConfiguratorError):
    """Raised when the project no longer matches the confirmed plan."""

    def __init__(self, message: str, conflicts: list[dict[str, Any]] | None = None) -> None:
        super().__init__(message)
        self.conflicts = conflicts or [{"kind": "plan-changed", "message": message}]


@dataclass(frozen=True)
class RenderedFile:
    path: str
    content: bytes
    mode: str = "file"
    start: str | None = None
    end: str | None = None


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ConfiguratorError(f"cannot load {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise ConfiguratorError(f"{label} must contain a JSON object")
    return value


def require_portable_path(raw: Any, label: str) -> str:
    if not isinstance(raw, str) or PORTABLE_PATH.fullmatch(raw) is None:
        raise ConfiguratorError(f"{label} is not a portable project-relative path")
    return raw


def is_reparse_point(path: Path) -> bool:
    try:
        metadata = os.lstat(path)
    except OSError:
        return False
    attributes = getattr(metadata, "st_file_attributes", 0)
    return stat.S_ISLNK(metadata.st_mode) or bool(attributes & 0x400)


def require_safe_project_root(raw: str) -> Path:
    root = Path(os.path.abspath(raw))
    if not root.is_dir():
        raise ConfiguratorError("project root must be an existing directory")
    if is_reparse_point(root):
        raise ConfiguratorError("project root must not be a symlink, junction, or reparse point")
    return root


def require_safe_target(root: Path, raw_path: str) -> Path:
    portable = require_portable_path(raw_path, "managed path")
    current = root
    parts = PurePosixPath(portable).parts
    for index, part in enumerate(parts):
        if not current.is_dir():
            raise ConfiguratorError(f"managed path parent is not a directory: {portable}")
        matches = [child.name for child in current.iterdir() if child.name.casefold() == part.casefold()]
        if matches and part not in matches:
            raise ConfiguratorError(f"managed path casing does not match the filesystem: {portable}")
        current = current / part
        if os.path.lexists(current):
            if is_reparse_point(current):
                raise ConfiguratorError(
                    f"managed path crosses a symlink, junction, or reparse point: {portable}"
                )
            if index < len(parts) - 1 and not current.is_dir():
                raise ConfiguratorError(f"managed path parent is not a directory: {portable}")
        else:
            break
    return root.joinpath(*PurePosixPath(portable).parts)


def require_safe_control_paths(root: Path) -> tuple[Path, Path]:
    resolved: dict[str, Path] = {}
    errors: list[str] = []
    for raw_path in (".ultracode/config.json", ".ultracode/managed.json"):
        try:
            resolved[raw_path] = require_safe_target(root, raw_path)
        except ConfiguratorError as exc:
            errors.append(str(exc))
    if errors:
        raise ConfiguratorError("; ".join(errors))
    return resolved[".ultracode/config.json"], resolved[".ultracode/managed.json"]


def configured_canonical_paths(config: dict[str, Any]) -> list[str]:
    artifacts = config.get("artifacts")
    roles = config.get("roles")
    if not isinstance(artifacts, dict) or not isinstance(roles, list):
        raise ConfiguratorError("config must contain artifacts and roles")
    paths: list[str] = []
    artifact_paths: dict[str, list[str]] = {}
    for key in ("context", "rules", "skills"):
        values = artifacts.get(key)
        if not isinstance(values, list):
            raise ConfiguratorError(f"config.artifacts.{key} must be an array")
        artifact_paths[key] = []
        for index, value in enumerate(values):
            portable = require_portable_path(value, f"config.artifacts.{key}[{index}]")
            artifact_paths[key].append(portable)
            paths.append(portable)
    rule_paths = artifacts.get("rule_paths")
    if not isinstance(rule_paths, dict) or set(rule_paths) != set(artifact_paths["rules"]):
        raise ConfiguratorError("config.artifacts.rule_paths keys must exactly match config.artifacts.rules")
    for rule, globs in rule_paths.items():
        if (
            not isinstance(globs, list)
            or not globs
            or any(
                not isinstance(item, str) or RULE_SCOPE_PATH.fullmatch(item) is None
                for item in globs
            )
            or len(globs) != len(set(globs))
        ):
            raise ConfiguratorError(
                f"config.artifacts.rule_paths[{rule!r}] must contain unique portable relative selectors"
            )
    for index, role in enumerate(roles):
        if not isinstance(role, dict) or not isinstance(role.get("id"), str):
            raise ConfiguratorError(f"config.roles[{index}] must contain an id")
        role_id = role["id"]
        if re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", role_id) is None:
            raise ConfiguratorError(f"config.roles[{index}].id must be kebab-case")
        paths.append(f".agents/reviewers/{role_id}.md")
    if len(paths) != len(set(paths)):
        raise ConfiguratorError("configured canonical paths contain duplicates")
    return paths


def render_agents_block(canonical_paths: list[str]) -> str:
    lines = [
        START,
        "Read and follow the canonical UltraCode project control:",
        "",
        "- `.ultracode/config.json`",
    ]
    lines.extend(f"- `{path}`" for path in canonical_paths)
    lines.extend(
        (
            "",
            "Preserve user-owned changes and require explicit authority for Git, external, destructive, dependency, and deployment actions.",
            END,
        )
    )
    return "\n".join(lines)


def merge_managed_block(existing: str | None, block: str) -> str:
    return merge_named_block(existing, block, START, END, "# Project instructions\n\n")


def merge_named_block(
    existing: str | None,
    block: str,
    start: str,
    end: str,
    absent_prefix: str = "",
) -> str:
    if existing is None:
        return f"{absent_prefix}{block}\n"
    start_count = existing.count(start)
    end_count = existing.count(end)
    if start_count == 0 and end_count == 0:
        if existing.endswith(("\r\n\r\n", "\n\n", "\r\r")):
            separator = ""
        elif existing.endswith(("\r\n", "\n", "\r")):
            separator = "\n"
        else:
            separator = "\n\n"
        return f"{existing}{separator}{block}\n"
    if start_count != 1 or end_count != 1:
        raise ConfiguratorError("AGENTS.md has invalid or duplicate UltraCode project markers")
    begin = existing.index(start)
    end_begin = existing.index(end)
    if end_begin <= begin:
        raise ConfiguratorError("AGENTS.md has reversed UltraCode project markers")
    finish = end_begin + len(end)
    return f"{existing[:begin]}{block}{existing[finish:]}"


def block_hash(block: str) -> str:
    return sha256_bytes(block.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8"))


def extract_managed_block(content: str, start: str, end: str) -> str | None:
    if content.count(start) != 1 or content.count(end) != 1:
        return None
    begin = content.index(start)
    end_begin = content.index(end)
    if end_begin <= begin:
        return None
    return content[begin : end_begin + len(end)]


def detect_managed_drift(root: Path) -> list[dict[str, Any]]:
    manifest_path = require_safe_target(root, ".ultracode/managed.json")
    if not manifest_path.is_file():
        return []
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return [
            {
                "path": ".ultracode/managed.json",
                "kind": "managed-drift",
                "message": f"Managed manifest is unreadable: {exc}",
                "expected_sha256": None,
                "actual_sha256": sha256_bytes(manifest_path.read_bytes()),
            }
        ]
    entries = manifest.get("entries") if isinstance(manifest, dict) else None
    if not isinstance(entries, list):
        return [
            {
                "path": ".ultracode/managed.json",
                "kind": "managed-drift",
                "message": "Managed manifest entries are invalid.",
                "expected_sha256": None,
                "actual_sha256": sha256_bytes(manifest_path.read_bytes()),
            }
        ]
    conflicts: list[dict[str, Any]] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ConfiguratorError(f"managed manifest entry {index} must be an object")
        path = require_portable_path(entry.get("path"), f"managed entry {index}.path")
        expected = entry.get("sha256")
        mode = entry.get("mode")
        target = require_safe_target(root, path)
        actual: str | None = None
        if target.is_file():
            if mode == "file":
                actual = sha256_bytes(target.read_bytes())
            elif mode == "block":
                start = entry.get("start")
                end = entry.get("end")
                if isinstance(start, str) and isinstance(end, str):
                    try:
                        block = extract_managed_block(target.read_text(encoding="utf-8"), start, end)
                    except (OSError, UnicodeError):
                        block = None
                    if block is not None:
                        actual = block_hash(block)
            else:
                raise ConfiguratorError(f"managed manifest entry {path!r} has invalid mode")
        if not isinstance(expected, str) or actual != expected:
            conflicts.append(
                {
                    "path": path,
                    "kind": "managed-drift",
                    "message": "Managed content no longer matches the manifest.",
                    "expected_sha256": expected if isinstance(expected, str) else None,
                    "actual_sha256": actual,
                }
            )
    return conflicts


def existing_manifest_entries(root: Path) -> dict[str, dict[str, Any]]:
    manifest_path = require_safe_target(root, ".ultracode/managed.json")
    if not manifest_path.is_file():
        return {}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = manifest.get("entries") if isinstance(manifest, dict) else None
    if not isinstance(entries, list):
        return {}
    return {
        entry["path"]: entry
        for entry in entries
        if isinstance(entry, dict) and isinstance(entry.get("path"), str)
    }


def parse_canonical_skill_description(content: bytes, skill_name: str) -> str:
    try:
        normalized = content.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
    except UnicodeError as exc:
        raise ConfiguratorError(f"canonical skill {skill_name} must be UTF-8") from exc
    if not normalized.startswith("---\n") or "\n---\n" not in normalized[4:]:
        raise ConfiguratorError(f"canonical skill {skill_name} must contain strict frontmatter")
    frontmatter, body = normalized[4:].split("\n---\n", 1)
    fields: dict[str, str] = {}
    for line in frontmatter.splitlines():
        if ":" not in line:
            raise ConfiguratorError(f"canonical skill {skill_name} frontmatter is invalid")
        key, value = line.split(":", 1)
        if key in fields:
            raise ConfiguratorError(f"canonical skill {skill_name} frontmatter has duplicate keys")
        fields[key] = value.strip()
    if set(fields) != {"name", "description"} or fields["name"] != skill_name or not body.strip():
        raise ConfiguratorError(f"canonical skill {skill_name} frontmatter or body is invalid")
    try:
        description = json.loads(fields["description"])
    except json.JSONDecodeError as exc:
        raise ConfiguratorError(f"canonical skill {skill_name} description must be JSON-quoted") from exc
    if not isinstance(description, str) or not description.strip():
        raise ConfiguratorError(f"canonical skill {skill_name} description must be non-empty")
    expected = f"name: {skill_name}\ndescription: {json.dumps(description, ensure_ascii=False)}"
    if frontmatter != expected:
        raise ConfiguratorError(f"canonical skill {skill_name} frontmatter is not deterministic")
    return description


def preserve_missing_config_keys(existing: Any, proposed: Any) -> Any:
    if not isinstance(existing, dict) or not isinstance(proposed, dict):
        return proposed
    merged = {
        key: preserve_missing_config_keys(existing.get(key), value)
        for key, value in proposed.items()
    }
    for key, value in existing.items():
        if key not in merged:
            merged[key] = value
    return merged


def render_codex_role(role: dict[str, Any], canonical_path: str, source_hash: str) -> bytes:
    role_id = role["id"]
    purpose = role.get("purpose")
    mode = role.get("mode")
    if not isinstance(purpose, str) or not purpose.strip() or mode not in {"read-only", "workspace-write"}:
        raise ConfiguratorError(f"role {role_id} purpose or mode is invalid")
    directive = f"Read and follow the canonical reviewer at `{canonical_path}` completely before starting work."
    lines = (
        f"# ultracode-canonical: {canonical_path}",
        f"# ultracode-source-sha256: {source_hash}",
        f'name = "{role_id}"',
        f"description = {json.dumps(purpose, ensure_ascii=False)}",
        f'sandbox_mode = "{mode}"',
        'developer_instructions = """',
        directive,
        "Return evidence and stay inside the assigned job boundary.",
        '"""',
    )
    return ("\n".join(lines) + "\n").encode("utf-8")


def render_claude_role(role: dict[str, Any], canonical_path: str, source_hash: str) -> bytes:
    role_id = role["id"]
    purpose = role.get("purpose")
    mode = role.get("mode")
    skills = role.get("skills")
    if (
        not isinstance(purpose, str)
        or not purpose.strip()
        or mode not in {"read-only", "workspace-write"}
        or not isinstance(skills, list)
        or any(not isinstance(item, str) or not item for item in skills)
    ):
        raise ConfiguratorError(f"role {role_id} fields are invalid")
    permission = "plan" if mode == "read-only" else "default"
    frontmatter = [
        f"name: {role_id}",
        f"description: {json.dumps(purpose, ensure_ascii=False)}",
        f"permissionMode: {permission}",
    ]
    if skills:
        frontmatter.append("skills:")
        frontmatter.extend(f"  - {json.dumps(item, ensure_ascii=False)}" for item in skills)
    body = [
        "---",
        *frontmatter,
        "---",
        f"<!-- ultracode-canonical: {canonical_path} -->",
        f"<!-- ultracode-source-sha256: {source_hash} -->",
        "",
        f"Read and follow the canonical reviewer at `{canonical_path}` completely before starting work.",
        "Return evidence and stay inside the assigned job boundary.",
    ]
    return ("\n".join(body) + "\n").encode("utf-8")


def render_claude_rule(canonical_path: str, paths: list[str]) -> bytes:
    lines = ["---", "paths:"]
    lines.extend(f"  - {json.dumps(item, ensure_ascii=False)}" for item in paths)
    lines.extend(
        (
            "---",
            f"<!-- ultracode-canonical: {canonical_path} -->",
            "",
            f"Read and follow the canonical rule at `{canonical_path}` completely before applying this adapter.",
        )
    )
    return ("\n".join(lines) + "\n").encode("utf-8")


def render_claude_skill(canonical_path: str, name: str, description: str) -> bytes:
    lines = (
        "---",
        f"name: {name}",
        f"description: {json.dumps(description, ensure_ascii=False)}",
        "---",
        f"<!-- ultracode-canonical: {canonical_path} -->",
        "",
        f"Read and follow the canonical skill at `{canonical_path}` completely before executing this skill.",
    )
    return ("\n".join(lines) + "\n").encode("utf-8")


def validate_rendered_project(rendered: list[RenderedFile]) -> None:
    doctor = Path(__file__).with_name("project_doctor.py")
    if not doctor.is_file():
        raise ConfiguratorError("project doctor is unavailable for preflight validation")
    with tempfile.TemporaryDirectory(prefix="ultracode-configurator-preflight-") as temporary:
        staging = Path(temporary)
        for item in rendered:
            target = staging.joinpath(*PurePosixPath(item.path).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(item.content)
        completed = subprocess.run(
            [sys.executable, str(doctor), str(staging), "--json"],
            capture_output=True,
            text=True,
            check=False,
        )
        try:
            report = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise ConfiguratorError("project doctor returned invalid JSON during preflight") from exc
        if completed.returncode != 0 or report.get("status") != "PASSED":
            diagnostics = [
                *report.get("errors", []),
                *report.get("drift", []),
            ]
            detail = "; ".join(item for item in diagnostics if isinstance(item, str))
            raise ConfiguratorError(
                f"desired project fails doctor preflight{': ' + detail if detail else ''}"
            )


def render_plan(root: Path, proposal: dict[str, Any]) -> tuple[str, list[RenderedFile], dict[str, Any]]:
    config_path, _ = require_safe_control_paths(root)
    drift = detect_managed_drift(root)
    if drift:
        raise ConfiguratorConflict("managed project content has drifted", drift)
    if proposal.get("schema_version") != 1:
        raise ConfiguratorError("proposal.schema_version must be 1")
    proposed_config = proposal.get("config")
    canonical_files = proposal.get("canonical_files")
    if not isinstance(proposed_config, dict) or not isinstance(canonical_files, dict):
        raise ConfiguratorError("proposal must contain config and canonical_files objects")
    existing_config = load_object(config_path, "existing config") if config_path.is_file() else {}
    config = preserve_missing_config_keys(existing_config, proposed_config)
    canonical_paths = configured_canonical_paths(config)
    supplied_paths = {require_portable_path(path, "canonical_files key") for path in canonical_files}
    if supplied_paths != set(canonical_paths):
        missing = sorted(set(canonical_paths) - supplied_paths)
        extras = sorted(supplied_paths - set(canonical_paths))
        raise ConfiguratorError(f"canonical_files mismatch; missing={missing}, extras={extras}")
    for path in [
        ".ultracode/config.json",
        ".ultracode/managed.json",
        "AGENTS.md",
        *canonical_paths,
    ]:
        require_safe_target(root, path)
    mode = "edit" if config_path.is_file() else "init"
    owned_entries = existing_manifest_entries(root)
    rendered: list[RenderedFile] = []
    config_content = json_bytes(config)
    rendered.append(RenderedFile(".ultracode/config.json", config_content))
    agents_path = root / "AGENTS.md"
    existing_agents = agents_path.read_bytes().decode("utf-8") if agents_path.is_file() else None
    if (
        existing_agents is not None
        and existing_agents.count(START) == 1
        and existing_agents.count(END) == 1
        and "AGENTS.md" not in owned_entries
    ):
        raise ConfiguratorConflict(
            "pre-existing UltraCode markers require explicit adoption or replacement",
            [
                {
                    "path": "AGENTS.md",
                    "kind": "ownership-conflict",
                    "message": "A valid-looking managed block exists without compatible manifest ownership.",
                    "expected_sha256": None,
                    "actual_sha256": sha256_bytes(agents_path.read_bytes()),
                }
            ],
        )
    agents_block = render_agents_block(canonical_paths)
    agents_content = merge_managed_block(existing_agents, agents_block).encode("utf-8")
    rendered.append(RenderedFile("AGENTS.md", agents_content, "block", START, END))
    for path in canonical_paths:
        content = canonical_files.get(path)
        if not isinstance(content, str) or not content:
            raise ConfiguratorError(f"canonical_files[{path!r}] must be a non-empty string")
        rendered.append(RenderedFile(path, content.encode("utf-8")))
    rendered_by_path = {item.path: item for item in rendered}
    adapters = config.get("adapters")
    artifacts = config["artifacts"]
    roles = config["roles"]
    if not isinstance(adapters, dict):
        raise ConfiguratorError("config.adapters must be an object")
    if adapters.get("codex") is True:
        for role in roles:
            canonical = f".agents/reviewers/{role['id']}.md"
            source_hash = sha256_bytes(rendered_by_path[canonical].content)
            rendered.append(
                RenderedFile(
                    f".codex/agents/{role['id']}.toml",
                    render_codex_role(role, canonical, source_hash),
                )
            )
    if adapters.get("claude") is True:
        nested_raw = ".claude/CLAUDE.md"
        top_raw = "CLAUDE.md"
        nested_path = require_safe_target(root, nested_raw)
        top_path = require_safe_target(root, top_raw)
        root_raw = nested_raw if nested_path.is_file() or not top_path.is_file() else top_raw
        root_path = nested_path if root_raw == nested_raw else top_path
        import_line = "@../AGENTS.md" if root_raw == nested_raw else "@AGENTS.md"
        ownership = owned_entries.get(root_raw, {})
        existing_bytes = root_path.read_bytes() if root_path.is_file() else None
        existing_root = existing_bytes.decode("utf-8") if existing_bytes is not None else None
        if (
            existing_root is not None
            and existing_root.count(CLAUDE_START) == 1
            and existing_root.count(CLAUDE_END) == 1
            and root_raw not in owned_entries
        ):
            raise ConfiguratorConflict(
                "pre-existing Claude markers require explicit adoption or replacement",
                [
                    {
                        "path": root_raw,
                        "kind": "ownership-conflict",
                        "message": "A valid-looking managed block exists without compatible manifest ownership.",
                        "expected_sha256": None,
                        "actual_sha256": sha256_bytes(existing_bytes),
                    }
                ],
            )
        if existing_root is None or ownership.get("mode") == "file":
            rendered.append(RenderedFile(root_raw, f"{import_line}\n".encode("utf-8")))
        else:
            block = f"{CLAUDE_START}\n{import_line}\n{CLAUDE_END}"
            merged = merge_named_block(existing_root, block, CLAUDE_START, CLAUDE_END)
            rendered.append(RenderedFile(root_raw, merged.encode("utf-8"), "block", CLAUDE_START, CLAUDE_END))
        for rule in artifacts["rules"]:
            rendered.append(
                RenderedFile(
                    f".claude/rules/{PurePosixPath(rule).name}",
                    render_claude_rule(rule, artifacts["rule_paths"][rule]),
                )
            )
        for skill in artifacts["skills"]:
            skill_name = PurePosixPath(skill).parent.name
            description = parse_canonical_skill_description(rendered_by_path[skill].content, skill_name)
            rendered.append(
                RenderedFile(
                    f".claude/skills/{skill_name}/SKILL.md",
                    render_claude_skill(skill, skill_name, description),
                )
            )
        for role in roles:
            canonical = f".agents/reviewers/{role['id']}.md"
            source_hash = sha256_bytes(rendered_by_path[canonical].content)
            rendered.append(
                RenderedFile(
                    f".claude/agents/{role['id']}.md",
                    render_claude_role(role, canonical, source_hash),
                )
            )
    projection_paths = [item.path for item in rendered]
    if len(projection_paths) != len(set(projection_paths)):
        raise ConfiguratorError("configured artifacts produce duplicate managed projections")
    for item in rendered:
        target = require_safe_target(root, item.path)
        if os.path.lexists(target) and not target.is_file():
            raise ConfiguratorError(f"managed file path is occupied by a non-file: {item.path}")
    ownership_conflicts: list[dict[str, Any]] = []
    for item in rendered:
        target = root / PurePosixPath(item.path)
        if target.is_file() and item.path not in owned_entries and item.mode == "file":
            ownership_conflicts.append(
                {
                    "path": item.path,
                    "kind": "ownership-conflict",
                    "message": "Existing file is not owned by the UltraCode managed manifest.",
                    "expected_sha256": None,
                    "actual_sha256": sha256_bytes(target.read_bytes()),
                }
            )
    if ownership_conflicts:
        raise ConfiguratorConflict("existing user-owned files require an explicit resolution", ownership_conflicts)
    entries: list[dict[str, Any]] = []
    for item in rendered:
        entry: dict[str, Any] = {"path": item.path, "mode": item.mode}
        if item.mode == "block":
            if item.start is None or item.end is None:
                raise ConfiguratorError(f"managed block markers are missing for {item.path}")
            decoded = item.content.decode("utf-8")
            managed_block = extract_managed_block(decoded, item.start, item.end)
            if managed_block is None:
                raise ConfiguratorError(f"managed block is invalid for {item.path}")
            entry.update(
                {
                    "start": item.start,
                    "end": item.end,
                    "sha256": block_hash(managed_block),
                }
            )
        else:
            entry["sha256"] = sha256_bytes(item.content)
        entries.append(entry)
    manifest = {
        "schema_version": 1,
        "generated_by": "ultracode-edit" if mode == "edit" else "ultracode-init",
        "entries": entries,
    }
    manifest_content = json_bytes(manifest)
    existing_manifest_path = root / ".ultracode" / "managed.json"
    non_manifest_unchanged = all(
        (root / PurePosixPath(item.path)).is_file()
        and (root / PurePosixPath(item.path)).read_bytes() == item.content
        for item in rendered
    )
    if mode == "edit" and non_manifest_unchanged and existing_manifest_path.is_file():
        try:
            existing_manifest = json.loads(existing_manifest_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            existing_manifest = None
        if (
            isinstance(existing_manifest, dict)
            and existing_manifest.get("schema_version") == 1
            and existing_manifest.get("generated_by") in {"ultracode-init", "ultracode-edit"}
            and existing_manifest.get("entries") == entries
        ):
            manifest_content = existing_manifest_path.read_bytes()
    rendered.append(RenderedFile(".ultracode/managed.json", manifest_content))
    validate_rendered_project(rendered)
    state = {
        item.path: sha256_bytes((root / PurePosixPath(item.path)).read_bytes())
        if (root / PurePosixPath(item.path)).is_file()
        else None
        for item in rendered
    }
    plan_material = {
        "mode": mode,
        "proposal": proposal,
        "state": state,
        "desired": {item.path: sha256_bytes(item.content) for item in rendered},
    }
    return mode, rendered, plan_material


def plan_command(root: Path, proposal: dict[str, Any]) -> dict[str, Any]:
    mode, rendered, material = render_plan(root, proposal)
    changes: list[dict[str, str]] = []
    rendered_by_path = {item.path: item for item in rendered}
    for item in rendered:
        path = root / PurePosixPath(item.path)
        if not path.is_file():
            changes.append({"path": item.path, "action": "create"})
        elif path.read_bytes() != item.content:
            changes.append({"path": item.path, "action": "update"})
    ordered_changes = sorted(changes, key=lambda item: item["path"])
    writes: list[dict[str, Any]] = []
    for change in ordered_changes:
        item = rendered_by_path[change["path"]]
        write: dict[str, Any] = {
            "path": item.path,
            "mode": item.mode,
            "sha256": sha256_bytes(item.content),
            "content": item.content.decode("utf-8"),
        }
        if item.mode == "block":
            write.update({"start": item.start, "end": item.end})
        writes.append(write)
    return {
        "schema_version": 1,
        "status": "PLANNED" if changes else "NO_CHANGES",
        "mode": mode,
        "plan_id": sha256_bytes(json.dumps(material, sort_keys=True, ensure_ascii=False).encode("utf-8")),
        "changes": ordered_changes,
        "writes": writes,
        "conflicts": [],
    }


def atomic_write(root: Path, raw_path: str, content: bytes) -> None:
    path = require_safe_target(root, raw_path)
    current = root
    for part in PurePosixPath(raw_path).parent.parts:
        candidate = current / part
        if os.path.lexists(candidate):
            if is_reparse_point(candidate) or not candidate.is_dir():
                raise ConfiguratorError(f"unsafe managed path parent: {raw_path}")
        else:
            candidate.mkdir()
        current = candidate
    path = require_safe_target(root, raw_path)
    temporary_path = path.parent / f".{path.name}.{uuid.uuid4().hex}.tmp"
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    descriptor = os.open(temporary_path, flags, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def apply_command(root: Path, proposal: dict[str, Any], confirmed_plan_id: str) -> dict[str, Any]:
    plan = plan_command(root, proposal)
    if confirmed_plan_id != plan["plan_id"]:
        raise ConfiguratorConflict("project or proposal changed after the confirmed plan")
    if plan["status"] == "NO_CHANGES":
        return {**plan, "status": "NO_CHANGES", "applied": []}
    _, rendered, _ = render_plan(root, proposal)
    for item in rendered:
        require_safe_target(root, item.path)
    rendered_by_path = {item.path: item for item in rendered}
    ordered_paths = [
        item["path"] for item in plan["changes"] if item["path"] != ".ultracode/managed.json"
    ]
    if ".ultracode/managed.json" in rendered_by_path:
        ordered_paths.append(".ultracode/managed.json")
    backups: dict[str, tuple[bytes, os.stat_result] | None] = {}
    missing_directories: set[Path] = set()
    for raw_path in ordered_paths:
        target = require_safe_target(root, raw_path)
        backups[raw_path] = (target.read_bytes(), target.stat()) if target.is_file() else None
        current = root
        for part in PurePosixPath(raw_path).parent.parts:
            current = current / part
            if not os.path.lexists(current):
                missing_directories.add(current)
    applied: list[str] = []
    try:
        for raw_path in ordered_paths:
            atomic_write(root, raw_path, rendered_by_path[raw_path].content)
            applied.append(raw_path)
    except (OSError, ConfiguratorError) as exc:
        rollback_errors: list[str] = []
        for raw_path in reversed(applied):
            target = root.joinpath(*PurePosixPath(raw_path).parts)
            backup = backups[raw_path]
            try:
                require_safe_target(root, raw_path)
                if backup is None:
                    if target.is_file():
                        target.chmod(stat.S_IREAD | stat.S_IWRITE)
                        target.unlink()
                else:
                    content, metadata = backup
                    if target.is_file():
                        target.chmod(stat.S_IREAD | stat.S_IWRITE)
                    atomic_write(root, raw_path, content)
                    os.chmod(target, stat.S_IMODE(metadata.st_mode))
                    os.utime(target, ns=(metadata.st_atime_ns, metadata.st_mtime_ns))
            except (OSError, ConfiguratorError) as rollback_exc:
                rollback_errors.append(f"{raw_path}: {rollback_exc}")
        for directory in sorted(missing_directories, key=lambda item: len(item.parts), reverse=True):
            try:
                if directory.is_dir() and not is_reparse_point(directory):
                    directory.rmdir()
            except OSError:
                pass
        if rollback_errors:
            raise ConfiguratorError(
                "apply failed and rollback was incomplete: " + "; ".join(rollback_errors)
            ) from exc
        raise ConfiguratorError(f"apply failed and all applied paths were rolled back: {exc}") from exc
    return {**plan, "status": "APPLIED", "applied": applied}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    plan = subparsers.add_parser("plan", help="Render a deterministic read-only project plan")
    plan.add_argument("--project-root", required=True)
    plan.add_argument("--proposal", required=True)
    apply = subparsers.add_parser("apply", help="Apply an unchanged confirmed project plan")
    apply.add_argument("--project-root", required=True)
    apply.add_argument("--proposal", required=True)
    apply.add_argument("--plan-id", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        root = require_safe_project_root(args.project_root)
        proposal = load_object(Path(args.proposal), "proposal")
        result = (
            plan_command(root, proposal)
            if args.command == "plan"
            else apply_command(root, proposal, args.plan_id)
        )
    except ConfiguratorConflict as exc:
        print(
            json.dumps(
                {"schema_version": 1, "status": "CONFLICT", "conflicts": exc.conflicts},
                ensure_ascii=False,
            )
        )
        return 2
    except (OSError, UnicodeError, ConfiguratorError) as exc:
        print(json.dumps({"schema_version": 1, "status": "FAILED", "errors": [str(exc)]}, ensure_ascii=False))
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
