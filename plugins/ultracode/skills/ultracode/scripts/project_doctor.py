#!/usr/bin/env python3
"""Validate an initialized UltraCode repository without modifying it."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tomllib
from pathlib import Path, PurePosixPath
from typing import Any


REQUIRED_TOP_LEVEL = {
    "schema_version",
    "project",
    "control",
    "authority",
    "swarm",
    "adapters",
    "artifacts",
    "commands",
    "completion",
    "roles",
}
COMMAND_KEYS = ("install", "format", "lint", "typecheck", "test", "build", "run", "health")
EVIDENCE_STATES = {"VERIFIED", "INFERRED", "UNKNOWN"}
MODEL_POLICIES = {"strongest-available", "balanced-available", "inherit"}
HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")
KEBAB = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
STATUS_PATH = re.compile(r"^\.ultracode/[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*$")
CONTEXT_PATH = re.compile(r"^\.agents/context/[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*\.md$")
RULE_PATH = re.compile(r"^\.agents/rules/[a-z0-9]+(?:-[a-z0-9]+)*\.md$")
SKILL_PATH = re.compile(r"^\.agents/skills/[a-z0-9]+(?:-[a-z0-9]+)*/SKILL\.md$")
SOURCE_HASH = re.compile(r"ultracode-source-sha256:\s*([0-9a-f]{64})")
MANAGED_PATH = re.compile(r"^[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*$")
BLOCK_START = re.compile(r"^<!-- ultracode:([a-z0-9]+(?:-[a-z0-9]+)*):start -->$")
BLOCK_END = re.compile(r"^<!-- ultracode:([a-z0-9]+(?:-[a-z0-9]+)*):end -->$")
ANY_BLOCK_MARKER = re.compile(r"<!-- ultracode:[a-z0-9]+(?:-[a-z0-9]+)*:(?:start|end) -->")


def load_json(path: Path, errors: list[str]) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append(f"missing required file: {path}")
        return None
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        errors.append(f"cannot read JSON {path}: {exc}")
        return None
    if not isinstance(value, dict):
        errors.append(f"JSON root must be an object: {path}")
        return None
    return value


def read_utf8(path: Path, label: str, errors: list[str]) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        errors.append(f"cannot read {label}: {exc}")
        return None


def require_object(parent: dict[str, Any], key: str, errors: list[str]) -> dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        errors.append(f"{key} must be an object")
        return {}
    return value


def validate_string_list(
    value: Any,
    label: str,
    errors: list[str],
    *,
    minimum: int = 0,
    pattern: re.Pattern[str] | None = None,
) -> list[str]:
    if not isinstance(value, list):
        errors.append(f"{label} must be an array")
        return []
    if len(value) < minimum:
        errors.append(f"{label} must contain at least {minimum} item(s)")
    result: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item:
            errors.append(f"{label}[{index}] must be a non-empty string")
            continue
        if pattern is not None and not pattern.fullmatch(item):
            errors.append(f"{label}[{index}] has an invalid path: {item}")
        if item in seen:
            errors.append(f"{label} contains a duplicate: {item}")
        else:
            seen.add(item)
        result.append(item)
    return result


def is_reparse_or_link(path: Path) -> bool:
    try:
        info = os.lstat(path)
    except OSError:
        return False
    if stat.S_ISLNK(info.st_mode):
        return True
    attributes = getattr(info, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(attributes & reparse_flag)


def safe_project_path(root: Path, raw: Any, label: str, errors: list[str]) -> Path | None:
    if not isinstance(raw, str) or not raw:
        errors.append(f"{label} must be a non-empty relative POSIX path")
        return None
    if "\\" in raw:
        errors.append(f"{label} must use POSIX separators: {raw}")
        return None
    pure = PurePosixPath(raw)
    if (
        pure.is_absolute()
        or not pure.parts
        or raw != pure.as_posix()
        or any(part in {".", ".."} for part in pure.parts)
        or re.match(r"^[A-Za-z]:", raw)
        or raw.startswith("~")
    ):
        errors.append(f"{label} escapes the repository: {raw}")
        return None

    current = root
    for part in pure.parts:
        if current.is_dir():
            try:
                names = {child.name for child in current.iterdir()}
            except OSError as exc:
                errors.append(f"cannot inspect path casing for {label}: {exc}")
                return None
            lexical_child = current / part
            if os.path.lexists(lexical_child) and part not in names:
                errors.append(f"{label} uses non-portable path casing: {raw}")
                return None
        current = current / part
        if os.path.lexists(current) and is_reparse_or_link(current):
            errors.append(f"{label} traverses a symlink, junction, or reparse point: {raw}")
            return None

    candidate = current.resolve()
    try:
        common = os.path.commonpath((str(root), str(candidate)))
    except ValueError:
        errors.append(f"{label} resolves outside the repository: {raw}")
        return None
    if Path(common) != root:
        errors.append(f"{label} resolves outside the repository: {raw}")
        return None
    return candidate


def normalized_block(text: str, start: str, end: str, label: str, errors: list[str]) -> str | None:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    start_match = BLOCK_START.fullmatch(start)
    end_match = BLOCK_END.fullmatch(end)
    if start_match is None or end_match is None or start_match.group(1) != end_match.group(1):
        errors.append(f"{label} must use a matching UltraCode start/end marker pair")
        return None
    if normalized.count(start) != 1 or normalized.count(end) != 1:
        errors.append(f"{label} must contain exactly one start and end marker")
        return None
    begin = normalized.index(start)
    finish = normalized.index(end)
    if finish < begin:
        errors.append(f"{label} has reversed managed markers")
        return None
    block = normalized[begin : finish + len(end)]
    markers = ANY_BLOCK_MARKER.findall(block)
    if markers != [start, end]:
        errors.append(f"{label} contains nested or unexpected UltraCode block markers")
        return None
    return block


def require_file(root: Path, raw: str, label: str, errors: list[str]) -> Path | None:
    path = safe_project_path(root, raw, label, errors)
    if path is not None and not path.is_file():
        errors.append(f"missing required artifact: {raw}")
        return None
    return path


def verify_source_projection(path: Path, source_hash: str, label: str, errors: list[str]) -> str | None:
    text = read_utf8(path, label, errors)
    if text is None:
        return None
    matches = SOURCE_HASH.findall(text)
    if len(matches) != 1:
        errors.append(f"{label} must contain exactly one ultracode-source-sha256")
    elif matches[0] != source_hash:
        errors.append(f"{label} source hash does not match its canonical reviewer")
    return text


def split_strict_frontmatter(
    text: str,
    label: str,
    errors: list[str],
) -> tuple[str, str, dict[str, str]] | None:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    match = re.match(r"\A---[ \t]*\n(.*?)\n---[ \t]*\n", normalized, re.DOTALL)
    if match is None:
        errors.append(f"{label} lacks YAML frontmatter")
        return None
    frontmatter = match.group(1)
    keys: dict[str, str] = {}
    for line in frontmatter.splitlines():
        if not line or line[0].isspace():
            continue
        key_match = re.fullmatch(r"([A-Za-z][A-Za-z0-9_-]*):[ \t]*(.*)", line)
        if key_match is None:
            errors.append(f"{label} has unsupported YAML frontmatter syntax")
            return None
        key, value = key_match.groups()
        if key in keys:
            errors.append(f"{label} contains duplicate frontmatter key: {key}")
        else:
            keys[key] = value
    return frontmatter, normalized[match.end() :].strip(), keys


def parse_json_yaml_list(
    frontmatter: str,
    key: str,
    label: str,
    errors: list[str],
) -> list[str] | None:
    lines = frontmatter.splitlines()
    start = next((index for index, line in enumerate(lines) if line == f"{key}:"), None)
    if start is None:
        errors.append(f"{label}.{key} must use a block list")
        return None
    values: list[str] = []
    for line in lines[start + 1 :]:
        if line and not line[0].isspace():
            break
        if not line.strip():
            continue
        item = re.fullmatch(r"[ \t]+-[ \t]+(.+)", line)
        if item is None:
            errors.append(f"{label}.{key} contains unsupported list syntax")
            return None
        try:
            value = json.loads(item.group(1))
        except json.JSONDecodeError:
            errors.append(f"{label}.{key} entries must be JSON-quoted strings")
            return None
        if not isinstance(value, str) or not value:
            errors.append(f"{label}.{key} entries must be non-empty strings")
            return None
        values.append(value)
    if not values:
        errors.append(f"{label}.{key} must contain at least one item")
        return None
    return values


def parse_json_yaml_scalar(raw: str, label: str, errors: list[str]) -> str | None:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        errors.append(f"{label} must be a JSON-quoted YAML string")
        return None
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label} must be a non-empty string")
        return None
    return value


def verify_codex_role_projection(
    path: Path,
    label: str,
    source_hash: str,
    role_id: str,
    role_purpose: str,
    role_mode: str,
    canonical_raw: str,
    errors: list[str],
) -> None:
    text = verify_source_projection(path, source_hash, label, errors)
    if text is None:
        return
    marker = f"# ultracode-canonical: {canonical_raw}"
    source_marker = f"# ultracode-source-sha256: {source_hash}"
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    try:
        parsed = tomllib.loads(normalized)
    except tomllib.TOMLDecodeError as exc:
        errors.append(f"{label} is invalid TOML: {exc}")
        return
    expected_keys = {"name", "description", "sandbox_mode", "developer_instructions"}
    if set(parsed) != expected_keys:
        errors.append(f"{label} must contain exactly the deterministic Codex role fields")
    if parsed.get("name") != role_id:
        errors.append(f"{label} name must match role id {role_id}")
    if parsed.get("description") != role_purpose:
        errors.append(f"{label} description must exactly match the configured role purpose")
    if parsed.get("sandbox_mode") != role_mode:
        errors.append(f"{label} sandbox_mode must match role mode {role_mode}")
    directive = f"Read and follow the canonical reviewer at `{canonical_raw}` completely before starting work."
    expected_instructions = f"{directive}\nReturn evidence and stay inside the assigned job boundary."
    if not isinstance(parsed.get("developer_instructions"), str) or parsed.get(
        "developer_instructions", ""
    ).strip() != expected_instructions:
        errors.append(f"{label} developer_instructions differ from the deterministic role projection")
    encoded_purpose = json.dumps(role_purpose, ensure_ascii=False)
    expected = "\n".join(
        (
            marker,
            source_marker,
            f'name = "{role_id}"',
            f"description = {encoded_purpose}",
            f'sandbox_mode = "{role_mode}"',
            'developer_instructions = """',
            directive,
            "Return evidence and stay inside the assigned job boundary.",
            '"""',
        )
    )
    if normalized != expected:
        errors.append(f"{label} contains extra, duplicate, reordered, or ambiguous TOML content")


def verify_claude_role_projection(
    path: Path,
    label: str,
    source_hash: str,
    role_id: str,
    role_purpose: str,
    role_mode: str,
    canonical_raw: str,
    role_skills: list[str],
    errors: list[str],
) -> None:
    text = verify_source_projection(path, source_hash, label, errors)
    if text is None:
        return
    split = split_strict_frontmatter(text, label, errors)
    if split is None:
        return
    frontmatter, body, keys = split
    expected_keys = {"name", "description", "permissionMode"}
    if role_skills:
        expected_keys.add("skills")
    if set(keys) != expected_keys:
        errors.append(f"{label} frontmatter must contain exactly {sorted(expected_keys)}")
    if keys.get("name") != role_id:
        errors.append(f"{label} name must match role id {role_id}")
    description = parse_json_yaml_scalar(keys.get("description", ""), f"{label}.description", errors)
    if description is not None and description != role_purpose:
        errors.append(f"{label}.description must exactly match the configured role purpose")
    permission_mode = "plan" if role_mode == "read-only" else "default"
    if keys.get("permissionMode") != permission_mode:
        errors.append(f"{label} permissionMode must be {permission_mode}")
    if role_skills:
        projected_skills = parse_json_yaml_list(frontmatter, "skills", label, errors)
        if projected_skills is not None and projected_skills != role_skills:
            errors.append(f"{label}.skills must exactly match configured role skills")
    expected_frontmatter_lines = [
        f"name: {role_id}",
        f"description: {json.dumps(role_purpose, ensure_ascii=False)}",
        f"permissionMode: {permission_mode}",
    ]
    if role_skills:
        expected_frontmatter_lines.append("skills:")
        expected_frontmatter_lines.extend(
            f"  - {json.dumps(skill, ensure_ascii=False)}" for skill in role_skills
        )
    if frontmatter != "\n".join(expected_frontmatter_lines):
        errors.append(f"{label} frontmatter differs from the deterministic role projection")
    marker = f"<!-- ultracode-canonical: {canonical_raw} -->"
    source_marker = f"<!-- ultracode-source-sha256: {source_hash} -->"
    directive = f"Read and follow the canonical reviewer at `{canonical_raw}` completely before starting work."
    expected_body = "\n".join(
        (
            marker,
            source_marker,
            "",
            directive,
            "Return evidence and stay inside the assigned job boundary.",
        )
    )
    if body != expected_body:
        errors.append(f"{label} body differs from the deterministic canonical reviewer adapter")


def verify_claude_rule_projection(
    path: Path,
    label: str,
    canonical_raw: str,
    errors: list[str],
) -> None:
    text = read_utf8(path, label, errors)
    if text is None:
        return
    split = split_strict_frontmatter(text, label, errors)
    if split is None:
        return
    frontmatter, body, keys = split
    if set(keys) != {"paths"}:
        errors.append(f"{label} frontmatter must contain exactly the paths key")
    paths = parse_json_yaml_list(frontmatter, "paths", label, errors)
    if paths is not None:
        if len(paths) != len(set(paths)):
            errors.append(f"{label}.paths contains duplicates")
        expected_frontmatter = "paths:\n" + "\n".join(
            f"  - {json.dumps(item, ensure_ascii=False)}" for item in paths
        )
        if frontmatter != expected_frontmatter:
            errors.append(f"{label} frontmatter differs from the deterministic rule adapter")
    marker = f"<!-- ultracode-canonical: {canonical_raw} -->"
    directive = f"Read and follow the canonical rule at `{canonical_raw}` completely before applying this adapter."
    expected_body = f"{marker}\n\n{directive}"
    if body != expected_body:
        errors.append(f"{label} body differs from the deterministic canonical rule adapter")


def verify_claude_skill_projection(
    path: Path,
    label: str,
    canonical_raw: str,
    skill_name: str,
    canonical_description: str | None,
    errors: list[str],
) -> None:
    text = read_utf8(path, label, errors)
    if text is None:
        return
    split = split_strict_frontmatter(text, label, errors)
    if split is None:
        return
    frontmatter, body, keys = split
    if set(keys) != {"name", "description"}:
        errors.append(f"{label} frontmatter must contain exactly name and description")
    if keys.get("name") != skill_name:
        errors.append(f"{label} name must match canonical skill name {skill_name}")
    description = parse_json_yaml_scalar(keys.get("description", ""), f"{label}.description", errors)
    if (
        description is not None
        and canonical_description is not None
        and description != canonical_description
    ):
        errors.append(f"{label}.description must exactly match its canonical skill description")
    expected_description = canonical_description if canonical_description is not None else description
    if expected_description is not None:
        expected_frontmatter = "\n".join(
            (
                f"name: {skill_name}",
                f"description: {json.dumps(expected_description, ensure_ascii=False)}",
            )
        )
        if frontmatter != expected_frontmatter:
            errors.append(f"{label} frontmatter differs from the deterministic skill adapter")
    marker = f"<!-- ultracode-canonical: {canonical_raw} -->"
    directive = f"Read and follow the canonical skill at `{canonical_raw}` completely before executing this skill."
    expected_body = f"{marker}\n\n{directive}"
    if body != expected_body:
        errors.append(f"{label} body differs from the deterministic canonical skill adapter")


def validate_canonical_skill(
    path: Path,
    label: str,
    skill_name: str,
    errors: list[str],
) -> str | None:
    text = read_utf8(path, label, errors)
    if text is None:
        return None
    split = split_strict_frontmatter(text, label, errors)
    if split is None:
        return None
    frontmatter, body, keys = split
    if set(keys) != {"name", "description"}:
        errors.append(f"{label} frontmatter must contain exactly name and description")
    if keys.get("name") != skill_name:
        errors.append(f"{label} name must match its folder name {skill_name}")
    description = parse_json_yaml_scalar(keys.get("description", ""), f"{label}.description", errors)
    if description is not None:
        expected_frontmatter = "\n".join(
            (
                f"name: {skill_name}",
                f"description: {json.dumps(description, ensure_ascii=False)}",
            )
        )
        if frontmatter != expected_frontmatter:
            errors.append(f"{label} frontmatter differs from the deterministic canonical skill format")
    if not body:
        errors.append(f"{label} body must be non-empty")
    return description


def verify_local_status_git(root: Path, status_path: str, errors: list[str], warnings: list[str]) -> None:
    git = shutil.which("git")
    if git is None:
        warnings.append("Git is unavailable; local status ignore state was not checked")
        return
    probe = subprocess.run(
        [git, "-C", str(root), "rev-parse", "--show-toplevel"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if probe.returncode != 0:
        if "not a git repository" in probe.stderr.lower():
            warnings.append("project is not a Git repository; local status needs no Git ignore rule")
        else:
            errors.append(f"cannot verify Git state for local status: {probe.stderr.strip()}")
        return
    tracked = subprocess.run(
        [git, "-C", str(root), "ls-files", "--error-unmatch", "--", status_path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if tracked.returncode == 0:
        errors.append(f"local status path is tracked by Git: {status_path}")
    ignored = subprocess.run(
        [git, "-C", str(root), "check-ignore", "--quiet", "--", status_path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if ignored.returncode != 0:
        errors.append(f"local status path is not ignored by Git: {status_path}")


def validate_config(
    config: dict[str, Any],
    root: Path,
    errors: list[str],
    warnings: list[str],
) -> tuple[set[str], str | None]:
    expected_managed = {".ultracode/config.json", "AGENTS.md"}
    missing = REQUIRED_TOP_LEVEL - set(config)
    if missing:
        errors.append(f"config missing keys: {sorted(missing)}")
    schema_version = config.get("schema_version")
    if (
        not isinstance(schema_version, int)
        or isinstance(schema_version, bool)
        or schema_version != 1
    ):
        errors.append("config.schema_version must be 1")

    project = require_object(config, "project", errors)
    for key in ("name", "mission"):
        if not isinstance(project.get(key), str) or not project.get(key, "").strip():
            errors.append(f"project.{key} must be a non-empty string")
    if project.get("root") != ".":
        errors.append("project.root must be '.'")
    for key in ("stack", "targets", "non_goals"):
        validate_string_list(project.get(key), f"project.{key}", errors)

    control = require_object(config, "control", errors)
    if control.get("plan_gate") not in {"follow-repository", "confirm-before-write", "autonomous-within-authority"}:
        errors.append("control.plan_gate is invalid")
    if control.get("updates") not in {"phase-and-barrier", "phase-only", "detailed"}:
        errors.append("control.updates is invalid")
    if control.get("detail") not in {"compact", "standard", "detailed"}:
        errors.append("control.detail is invalid")
    for key in ("show_agent_jobs", "show_files", "show_validation"):
        if not isinstance(control.get(key), bool):
            errors.append(f"control.{key} must be boolean")
    persistence = control.get("persistent_status")
    if persistence not in {"conversation-only", "local", "tracked"}:
        errors.append("control.persistent_status is invalid")
    raw_status_path = control.get("status_path")
    status_path = safe_project_path(root, raw_status_path, "control.status_path", errors)
    if not isinstance(raw_status_path, str) or not STATUS_PATH.fullmatch(raw_status_path):
        errors.append("control.status_path must be a portable path under .ultracode/")
    if persistence == "local" and status_path is not None and isinstance(raw_status_path, str):
        verify_local_status_git(root, raw_status_path, errors, warnings)

    authority = require_object(config, "authority", errors)
    for key in ("git", "external", "destructive", "dependencies", "deployment"):
        if authority.get(key) != "explicit-only":
            errors.append(f"authority.{key} must be explicit-only")
    if authority.get("status_writes") not in {"change-tasks-only", "explicit-per-task"}:
        errors.append("authority.status_writes is invalid")

    swarm = require_object(config, "swarm", errors)
    expected_swarm = {
        "decomposition": "data-driven",
        "orthogonal_lenses": "as-needed",
        "verification": "one-per-material-finding",
    }
    for key, value in expected_swarm.items():
        if swarm.get(key) != value:
            errors.append(f"swarm.{key} must be {value!r}")
    synthesis_agents = swarm.get("synthesis_agents")
    if (
        not isinstance(synthesis_agents, int)
        or isinstance(synthesis_agents, bool)
        or synthesis_agents != 1
    ):
        errors.append("swarm.synthesis_agents must be integer 1")
    if "max_total_agents" in swarm:
        errors.append("swarm.max_total_agents is forbidden; use hard_safety_cap only")
    concurrency = swarm.get("concurrency")
    if concurrency != "auto" and (not isinstance(concurrency, int) or isinstance(concurrency, bool) or concurrency < 1):
        errors.append("swarm.concurrency must be 'auto' or a positive integer")
    cap = swarm.get("hard_safety_cap")
    if not isinstance(cap, int) or isinstance(cap, bool) or cap < 1:
        errors.append("swarm.hard_safety_cap must be a positive integer")
    model_policy = swarm.get("model_policy")
    if not isinstance(model_policy, dict):
        errors.append("swarm.model_policy must be an object")
    else:
        for key in ("lead", "bounded_agents", "verifiers"):
            if model_policy.get(key) not in MODEL_POLICIES:
                errors.append(f"swarm.model_policy.{key} is invalid")
        if model_policy.get("fallback") != "inherit":
            errors.append("swarm.model_policy.fallback must be inherit")

    adapters = require_object(config, "adapters", errors)
    for key in ("codex", "claude"):
        if not isinstance(adapters.get(key), bool):
            errors.append(f"adapters.{key} must be boolean")
    if adapters.get("codex") is False and adapters.get("claude") is False:
        errors.append("at least one adapter must be enabled")

    agents_path = require_file(root, "AGENTS.md", "AGENTS.md", errors)
    agents_text = read_utf8(agents_path, "AGENTS.md", errors) if agents_path is not None else None
    agents_block = (
        normalized_block(agents_text, "<!-- ultracode:project:start -->", "<!-- ultracode:project:end -->", "AGENTS.md", errors)
        if agents_text is not None
        else None
    )
    if agents_block is not None and ".ultracode/config.json" not in agents_block:
        errors.append("AGENTS.md managed project block must route to .ultracode/config.json")

    artifacts = require_object(config, "artifacts", errors)
    contexts = validate_string_list(
        artifacts.get("context"), "artifacts.context", errors, minimum=1, pattern=CONTEXT_PATH
    )
    rules = validate_string_list(artifacts.get("rules"), "artifacts.rules", errors, pattern=RULE_PATH)
    skills = validate_string_list(artifacts.get("skills"), "artifacts.skills", errors, pattern=SKILL_PATH)
    canonical_artifacts = contexts + rules + skills
    canonical_skill_descriptions: dict[str, str] = {}
    for index, raw in enumerate(canonical_artifacts):
        artifact_path = require_file(root, raw, f"artifacts[{index}]", errors)
        expected_managed.add(raw)
        if agents_block is not None and raw not in agents_block:
            errors.append(f"AGENTS.md does not route to canonical artifact: {raw}")
        if artifact_path is not None and raw in skills:
            skill_name = PurePosixPath(raw).parent.name
            description = validate_canonical_skill(
                artifact_path,
                f"canonical skill {skill_name}",
                skill_name,
                errors,
            )
            if description is not None:
                canonical_skill_descriptions[raw] = description

    if adapters.get("claude") is True:
        nested_raw = ".claude/CLAUDE.md"
        top_raw = "CLAUDE.md"
        nested = safe_project_path(root, nested_raw, "Claude adapter", errors)
        top = safe_project_path(root, top_raw, "Claude adapter", errors)
        adapter_raw = nested_raw if nested is not None and nested.is_file() else top_raw if top is not None and top.is_file() else None
        if adapter_raw is None:
            errors.append("Claude adapter is enabled but no CLAUDE.md exists")
        else:
            expected_managed.add(adapter_raw)
            adapter_path = require_file(root, adapter_raw, "Claude adapter", errors)
            adapter_text = read_utf8(adapter_path, adapter_raw, errors) if adapter_path is not None else None
            expected_import = "@../AGENTS.md" if adapter_raw == nested_raw else "@AGENTS.md"
            if adapter_text is not None and not any(line.strip() == expected_import for line in adapter_text.splitlines()):
                errors.append(f"Claude adapter must contain standalone import {expected_import}")

        for raw in rules:
            adapter_raw = f".claude/rules/{PurePosixPath(raw).name}"
            expected_managed.add(adapter_raw)
            adapter_path = require_file(root, adapter_raw, f"Claude rule adapter for {raw}", errors)
            if adapter_path is not None:
                verify_claude_rule_projection(adapter_path, adapter_raw, raw, errors)

        for raw in skills:
            skill_name = PurePosixPath(raw).parent.name
            adapter_raw = f".claude/skills/{skill_name}/SKILL.md"
            expected_managed.add(adapter_raw)
            adapter_path = require_file(root, adapter_raw, f"Claude skill adapter for {raw}", errors)
            if adapter_path is not None:
                verify_claude_skill_projection(
                    adapter_path,
                    adapter_raw,
                    raw,
                    skill_name,
                    canonical_skill_descriptions.get(raw),
                    errors,
                )

    commands = require_object(config, "commands", errors)
    for key in COMMAND_KEYS:
        entries = commands.get(key)
        if not isinstance(entries, list):
            errors.append(f"commands.{key} must be an array")
            continue
        seen_entries: set[str] = set()
        for index, entry in enumerate(entries):
            marker = json.dumps(entry, sort_keys=True, ensure_ascii=False) if isinstance(entry, dict) else repr(entry)
            if marker in seen_entries:
                errors.append(f"commands.{key} contains a duplicate entry")
            seen_entries.add(marker)
            if not isinstance(entry, dict) or not isinstance(entry.get("command"), str) or not entry.get("command"):
                errors.append(f"commands.{key}[{index}] must contain a command string")
            elif entry.get("evidence") not in EVIDENCE_STATES:
                errors.append(f"commands.{key}[{index}].evidence is invalid")
            elif entry.get("evidence") != "VERIFIED":
                warnings.append(f"commands.{key}[{index}] remains {entry.get('evidence')}")

    completion = require_object(config, "completion", errors)
    validate_string_list(completion.get("required_checks"), "completion.required_checks", errors)
    if not isinstance(completion.get("real_path"), str):
        errors.append("completion.real_path must be a string")
    if completion.get("review") not in {
        "independent-for-material-change",
        "independent-for-critical-only",
        "repository-policy",
    }:
        errors.append("completion.review is invalid")

    roles = config.get("roles")
    if not isinstance(roles, list):
        errors.append("roles must be an array")
    else:
        role_ids: set[str] = set()
        for index, role in enumerate(roles):
            if not isinstance(role, dict):
                errors.append(f"roles[{index}] must be an object")
                continue
            role_id = role.get("id")
            if not isinstance(role_id, str) or not KEBAB.fullmatch(role_id):
                errors.append(f"roles[{index}].id must be kebab-case")
                continue
            if role_id in role_ids:
                errors.append(f"duplicate role id: {role_id}")
            role_ids.add(role_id)
            role_purpose = role.get("purpose") if isinstance(role.get("purpose"), str) else ""
            if not role_purpose.strip():
                errors.append(f"roles[{index}].purpose must be a non-empty string")
            if role.get("mode") not in {"read-only", "workspace-write"}:
                errors.append(f"roles[{index}].mode is invalid")
            role_skills = validate_string_list(role.get("skills"), f"roles[{index}].skills", errors)

            canonical_raw = f".agents/reviewers/{role_id}.md"
            expected_managed.add(canonical_raw)
            canonical_path = require_file(root, canonical_raw, f"canonical reviewer {role_id}", errors)
            if canonical_path is None:
                continue
            source_hash = hashlib.sha256(canonical_path.read_bytes()).hexdigest()
            role_mode = role.get("mode") if isinstance(role.get("mode"), str) else ""
            if adapters.get("codex") is True:
                codex_raw = f".codex/agents/{role_id}.toml"
                expected_managed.add(codex_raw)
                codex_path = require_file(root, codex_raw, f"Codex role projection {role_id}", errors)
                if codex_path is not None:
                    verify_codex_role_projection(
                        codex_path,
                        codex_raw,
                        source_hash,
                        role_id,
                        role_purpose,
                        role_mode,
                        canonical_raw,
                        errors,
                    )
            if adapters.get("claude") is True:
                claude_raw = f".claude/agents/{role_id}.md"
                expected_managed.add(claude_raw)
                claude_path = require_file(root, claude_raw, f"Claude role projection {role_id}", errors)
                if claude_path is not None:
                    verify_claude_role_projection(
                        claude_path,
                        claude_raw,
                        source_hash,
                        role_id,
                        role_purpose,
                        role_mode,
                        canonical_raw,
                        role_skills,
                        errors,
                    )

    return expected_managed, raw_status_path if isinstance(raw_status_path, str) else None


def validate_manifest(
    manifest: dict[str, Any],
    root: Path,
    status_path: str | None,
    expected_managed: set[str],
    errors: list[str],
    drift: list[str],
    warnings: list[str],
) -> None:
    schema_version = manifest.get("schema_version")
    if (
        not isinstance(schema_version, int)
        or isinstance(schema_version, bool)
        or schema_version != 1
    ):
        errors.append("managed.schema_version must be 1")
    if manifest.get("generated_by") not in {"ultracode-init", "ultracode-edit"}:
        errors.append("managed.generated_by must be ultracode-init or ultracode-edit")
    entries = manifest.get("entries")
    if not isinstance(entries, list):
        errors.append("managed.entries must be an array")
        return
    if len(entries) < 3:
        errors.append("managed.entries is incomplete; at least config, AGENTS.md, and canonical context are required")

    seen: dict[str, dict[str, Any]] = {}
    for index, entry in enumerate(entries):
        label = f"managed.entries[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{label} must be an object")
            continue
        raw_path = entry.get("path")
        if not isinstance(raw_path, str):
            errors.append(f"{label}.path must be a string")
            continue
        if raw_path in seen:
            errors.append(f"duplicate managed path: {raw_path}")
            continue
        seen[raw_path] = entry
        if MANAGED_PATH.fullmatch(raw_path) is None:
            errors.append(f"{label}.path does not match the portable managed-path grammar: {raw_path}")
        if raw_path in {".ultracode/managed.json", status_path}:
            errors.append(f"ephemeral or self-owned path cannot be managed: {raw_path}")
        path = safe_project_path(root, raw_path, f"{label}.path", errors)
        if path is None:
            continue
        if not path.is_file():
            errors.append(f"managed file is missing: {raw_path}")
            continue
        expected_hash = entry.get("sha256")
        if not isinstance(expected_hash, str) or not HEX_SHA256.fullmatch(expected_hash):
            errors.append(f"{label}.sha256 must be a lowercase SHA-256")
            continue
        mode = entry.get("mode")
        try:
            raw_bytes = path.read_bytes()
        except OSError as exc:
            errors.append(f"cannot read managed file {raw_path}: {exc}")
            continue
        if mode == "file":
            if "start" in entry or "end" in entry:
                errors.append(f"{label} file mode must not define block markers")
            if raw_path in {".claude/CLAUDE.md", "CLAUDE.md"}:
                try:
                    claude_text = raw_bytes.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n").strip()
                except UnicodeError as exc:
                    errors.append(f"Claude root adapter is not UTF-8 {raw_path}: {exc}")
                    continue
                expected_import = "@../AGENTS.md" if raw_path == ".claude/CLAUDE.md" else "@AGENTS.md"
                if claude_text != expected_import:
                    errors.append(f"{raw_path} file projection must contain exactly {expected_import}")
            actual_hash = hashlib.sha256(raw_bytes).hexdigest()
        elif mode == "block":
            start = entry.get("start")
            end = entry.get("end")
            if not isinstance(start, str) or not start or not isinstance(end, str) or not end:
                errors.append(f"{label} block mode requires start and end markers")
                continue
            try:
                text = raw_bytes.decode("utf-8")
            except UnicodeError as exc:
                errors.append(f"managed block file is not UTF-8 {raw_path}: {exc}")
                continue
            block = normalized_block(text, start, end, raw_path, errors)
            if block is None:
                continue
            if raw_path in {".claude/CLAUDE.md", "CLAUDE.md"}:
                expected_import = "@../AGENTS.md" if raw_path == ".claude/CLAUDE.md" else "@AGENTS.md"
                expected_start = "<!-- ultracode:claude-root:start -->"
                expected_end = "<!-- ultracode:claude-root:end -->"
                expected_block = f"{expected_start}\n{expected_import}\n{expected_end}"
                if start != expected_start or end != expected_end or block != expected_block:
                    errors.append(
                        f"{raw_path} block projection must be the exact ultracode:claude-root import block"
                    )
            actual_hash = hashlib.sha256(block.encode("utf-8")).hexdigest()
        else:
            errors.append(f"{label}.mode must be file or block")
            continue
        if actual_hash != expected_hash:
            drift.append(f"managed content changed: {raw_path}")

    missing = expected_managed - set(seen)
    if missing:
        errors.append(f"managed manifest omits configured artifacts: {sorted(missing)}")
    extras = set(seen) - expected_managed
    if extras:
        warnings.append(f"managed manifest contains disabled or unregistered artifacts: {sorted(extras)}")
    config_entry = seen.get(".ultracode/config.json")
    if config_entry is not None and config_entry.get("mode") != "file":
        errors.append(".ultracode/config.json must use managed mode file")
    agents_entry = seen.get("AGENTS.md")
    if agents_entry is not None and agents_entry.get("mode") != "block":
        errors.append("AGENTS.md must use a managed block")
    elif agents_entry is not None and (
        agents_entry.get("start") != "<!-- ultracode:project:start -->"
        or agents_entry.get("end") != "<!-- ultracode:project:end -->"
    ):
        errors.append("AGENTS.md must use the exact ultracode:project marker pair")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_root", nargs="?", default=".")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    root = Path(args.project_root).resolve()
    errors: list[str] = []
    drift: list[str] = []
    warnings: list[str] = []
    if not root.is_dir():
        errors.append(f"project root is not a directory: {root}")
    else:
        config = load_json(root / ".ultracode" / "config.json", errors)
        manifest = load_json(root / ".ultracode" / "managed.json", errors)
        expected_managed: set[str] = set()
        status_path: str | None = None
        if config is not None:
            expected_managed, status_path = validate_config(config, root, errors, warnings)
        if manifest is not None:
            validate_manifest(manifest, root, status_path, expected_managed, errors, drift, warnings)

    status = "FAILED" if errors else "DRIFT" if drift else "PASSED"
    result = {
        "status": status,
        "project_root": str(root),
        "errors": errors,
        "drift": drift,
        "warnings": warnings,
    }
    if args.as_json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"UltraCode project doctor: {status}")
        for label, items in (("ERROR", errors), ("DRIFT", drift), ("WARNING", warnings)):
            for item in items:
                print(f"{label}: {item}")
    return 1 if errors else 2 if drift else 0


if __name__ == "__main__":
    sys.exit(main())
