#!/usr/bin/env python3
"""Dependency-free structural validation for the public UltraCode repository."""

from __future__ import annotations

import json
import re
import struct
import sys
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
MARKETPLACE_PATH = ROOT / ".agents" / "plugins" / "marketplace.json"
PLUGIN_ROOT = ROOT / "plugins" / "ultracode"
MANIFEST_PATH = PLUGIN_ROOT / ".codex-plugin" / "plugin.json"
EXPECTED_REPOSITORY = "https://github.com/emanueledenaro/ultracode"
REQUIRED_DOCS = (
    "README.md",
    "LICENSE",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "CODE_OF_CONDUCT.md",
)
REQUIRED_SKILLS = (
    "ultracode",
    "ultracode-init",
    "ultracode-edit",
    "ultracode-status",
)
ASSET_FIELDS = ("composerIcon", "logo", "logoDark")


def fail(message: str) -> None:
    raise ValueError(message)


def load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        fail(f"cannot load {path.relative_to(ROOT)}: {exc}")
    if not isinstance(value, dict):
        fail(f"{path.relative_to(ROOT)} must contain a JSON object")
    return value


def validate_relative_asset(raw_path: Any, field: str) -> Path:
    if not isinstance(raw_path, str) or not raw_path.startswith("./assets/"):
        fail(f"interface.{field} must use a ./assets/ relative path")
    relative = PurePosixPath(raw_path[2:])
    if relative.is_absolute() or ".." in relative.parts:
        fail(f"interface.{field} escapes the plugin root")
    target = PLUGIN_ROOT.joinpath(*relative.parts)
    if not target.is_file() or target.is_symlink():
        fail(f"interface.{field} does not reference a regular packaged file")
    return target


def validate_png(path: Path) -> None:
    data = path.read_bytes()[:24]
    if len(data) != 24 or data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        fail(f"{path.relative_to(ROOT)} is not a valid PNG header")
    width, height = struct.unpack(">II", data[16:24])
    if width != height or width < 256:
        fail(f"{path.relative_to(ROOT)} must be square and at least 256px")


def parse_skill_name(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\s*\n(?P<frontmatter>.*?)\n---\s*\n", text, re.DOTALL)
    if match is None:
        fail(f"{path.relative_to(ROOT)} has no YAML frontmatter")
    name_match = re.search(r"(?m)^name:\s*[\"']?([^\"'\r\n]+)[\"']?\s*$", match.group("frontmatter"))
    description_match = re.search(r"(?m)^description:\s*.+$", match.group("frontmatter"))
    if name_match is None or description_match is None:
        fail(f"{path.relative_to(ROOT)} must declare name and description")
    return name_match.group(1).strip()


def validate_repository() -> None:
    for relative in REQUIRED_DOCS:
        if not (ROOT / relative).is_file():
            fail(f"missing required repository file: {relative}")

    marketplace = load_object(MARKETPLACE_PATH)
    if marketplace.get("name") != "ultracode":
        fail("marketplace name must be ultracode")
    plugins = marketplace.get("plugins")
    if not isinstance(plugins, list) or len(plugins) != 1:
        fail("marketplace must contain exactly one plugin entry")
    entry = plugins[0]
    if not isinstance(entry, dict) or entry.get("name") != "ultracode":
        fail("marketplace plugin entry must be ultracode")
    source = entry.get("source")
    if source != {"source": "local", "path": "./plugins/ultracode"}:
        fail("marketplace source must point to ./plugins/ultracode")

    manifest = load_object(MANIFEST_PATH)
    if manifest.get("name") != "ultracode":
        fail("plugin manifest name must be ultracode")
    version = manifest.get("version")
    version_pattern = r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?\+codex\.\d{14}"
    if not isinstance(version, str) or re.fullmatch(version_pattern, version) is None:
        fail("plugin manifest version must use semantic versioning with a Codex cachebuster")
    if manifest.get("repository") != EXPECTED_REPOSITORY or manifest.get("homepage") != EXPECTED_REPOSITORY:
        fail("plugin repository and homepage must use the canonical GitHub URL")
    if manifest.get("license") != "MIT":
        fail("plugin manifest license must be MIT")

    interface = manifest.get("interface")
    if not isinstance(interface, dict):
        fail("plugin manifest interface must be an object")
    if interface.get("displayName") != "UltraCode" or interface.get("brandColor") != "#2FB9D1":
        fail("plugin interface identity is inconsistent")
    icon_paths = {validate_relative_asset(interface.get(field), field) for field in ASSET_FIELDS}
    if len(icon_paths) != 1:
        fail("all icon surfaces must use the canonical UltraCode asset")
    validate_png(icon_paths.pop())

    for skill_name in REQUIRED_SKILLS:
        skill_path = PLUGIN_ROOT / "skills" / skill_name / "SKILL.md"
        if not skill_path.is_file() or skill_path.is_symlink():
            fail(f"missing regular SKILL.md for {skill_name}")
        if parse_skill_name(skill_path) != skill_name:
            fail(f"SKILL.md name mismatch for {skill_name}")

    forbidden_names = {".DS_Store", "Thumbs.db"}
    for path in ROOT.rglob("*"):
        if path.is_symlink():
            fail(f"repository contains a symlink: {path.relative_to(ROOT)}")
        if path.name in forbidden_names or path.suffix in {".pyc", ".pyo"} or path.name == "__pycache__":
            fail(f"repository contains a generated artifact: {path.relative_to(ROOT)}")


def main() -> int:
    try:
        validate_repository()
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        print(f"Repository validation failed: {exc}", file=sys.stderr)
        return 1
    print("UltraCode repository validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
