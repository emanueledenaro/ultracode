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
COMMAND_INTERFACE_PATH = (
    PLUGIN_ROOT / "skills" / "ultracode" / "references" / "command-interface.md"
)
COMMAND_GUIDE_PATH = (
    PLUGIN_ROOT / "skills" / "ultracode" / "references" / "command-guide.md"
)
HELP_METADATA_PATH = PLUGIN_ROOT / "skills" / "ultracode-help" / "agents" / "openai.yaml"
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
    "ultracode-help",
    "ultracode-init",
    "ultracode-edit",
    "ultracode-flow",
    "ultracode-status",
)
ASSET_FIELDS = ("composerIcon", "logo", "logoDark")
FLOW_REQUIRED_TEXT = (
    "Stay read-only",
    "A ticket is a bounded unit of work",
    "requested model",
    "effective model",
    "Why it exists",
    "Completion criterion",
    "$ultracode-flow full",
    "$ultracode-flow agents",
)
HELP_REQUIRED_ORDER = (
    "1. **Scelta rapida:**",
    "2. **Sei comandi:**",
    "3. **Progetto non configurato:**",
    "4. **Modelli ed effort:**",
    "5. **Ticket e agenti:**",
    "6. **Autorizzazioni:**",
)
HELP_GUIDE_SECTIONS = (
    "## Response contract",
    "## Quick choice",
    "## The six commands",
    "## Unconfigured projects",
    "## Models and reasoning effort",
    "## Tickets and agents",
    "## Authority boundaries",
)
HELP_COMMANDS = (
    ("ultracode-help", "Help"),
    ("ultracode", "UltraCode"),
    ("ultracode-init", "Init"),
    ("ultracode-edit", "Edit"),
    ("ultracode-flow", "Flow"),
    ("ultracode-status", "Status"),
)
HELP_FIELD_MARKERS = (
    "**When to use it:**",
    "**What you get:**",
    "**Can it write?:**",
    "**When confirmation is required:**",
)
HELP_GUIDE_SEMANTICS = (
    "Strip the `$ultracode-help` or `ultracode-help` invocation token",
    "An explicit Help invocation has precedence",
    "With no remaining explicit topic",
    "`breve` and `sintetico` request compact wording",
    "`$ultracode-init` baseline preflight",
    "Sol with `medium` effort",
    "Terra with `low` effort",
    "Requested model and effort",
    "Effective model and effort",
    "A ticket is the user-facing form",
    "A live agent is only",
    "requires explicit user authority",
)
HELP_PRECEDENCE_REQUIRED = (
    "## Respect explicit Help precedence",
    "../ultracode-help/SKILL.md",
    "read-only Help topic",
)
HELP_METADATA_PROMPT_REQUIREMENTS = (
    "$ultracode-help",
    "With no explicit topic",
    "complete ordered UltraCode overview",
    "chat-friendly Markdown layout",
    "one H1 title",
    "comparison tables",
    "H3 command sections",
    "inline blockquote examples",
    "If I provide a command, models, flow, or examples, answer only that topic",
    "compact wording only when I explicitly say breve or sintetico",
)
HELP_MANIFEST_PROMPT_REQUIREMENTS = (
    "$ultracode-help",
    "With no explicit topic",
    "complete ordered overview",
    "chat-friendly Markdown layout",
    "one H1 title",
    "comparison tables",
    "H3 command sections",
    "inline blockquote examples",
    "focus on one command, models, flow, or examples only when named",
    "compact wording only for an explicit breve or sintetico request",
)
COMMAND_REQUIRED_TEXT = {
    "ultracode": (
        "references/command-interface.md",
        "Explain each active ticket",
        "Handle an uninitialized project",
    ),
    "ultracode-help": (
        "../ultracode/references/command-guide.md",
        "../ultracode/references/reasoning-routing.md",
        "The invocation token is never itself the `help` topic.",
        "An explicit Help invocation has precedence over every command name",
        "`$ultracode-help flow` explains Flow",
        "**No remaining topic:**",
        "A bare `Use $ultracode-help` invocation",
        "**Explicit topic:**",
        "**Explicit `breve` or `sintetico`:**",
        "read-only Init preflight",
        "Sol `medium`",
        "Terra `low`",
        "requested versus effective",
        "Render for the chat surface, not as a dense document.",
        "Use one H1 title at the top",
        "For each command explanation, cover all four required fields even in compact mode:",
        "Put the command's example immediately after those fields as a Markdown blockquote",
        "Do not collect examples into a repeated section at the end",
        "Do not finish the response until every semantic item required by the selected mode is covered.",
    ),
    "ultracode-init": (
        "../ultracode/references/command-interface.md",
        "Explain the proposal in plain language",
        "baseline preflight mode",
        "load_workspace_dependencies",
    ),
    "ultracode-edit": (
        "../ultracode/references/command-interface.md",
        "Explain the delta in plain language",
        "load_workspace_dependencies",
    ),
    "ultracode-flow": (
        "../ultracode/references/command-interface.md",
        "A ticket is a bounded unit of work",
    ),
    "ultracode-status": (
        "../ultracode/references/command-interface.md",
        "Status is the detailed diagnostic view",
    ),
}


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


def normalize_whitespace(text: str) -> str:
    return " ".join(text.split())


def validate_help_guide(text: str) -> None:
    section_positions = [text.find(heading) for heading in HELP_GUIDE_SECTIONS]
    if any(position < 0 for position in section_positions):
        missing = [
            heading
            for heading, position in zip(HELP_GUIDE_SECTIONS, section_positions)
            if position < 0
        ]
        fail(f"command guide is missing ordered Help sections: {missing}")
    if section_positions != sorted(section_positions):
        fail("command guide Help sections are out of order")

    h1_headings = re.findall(r"(?m)^# [^#\r\n].*$", text)
    if h1_headings != ["# UltraCode command guide"]:
        fail("command guide must contain exactly one canonical H1 title")

    if "## Copyable examples" in text or "```text" in text:
        fail("command guide must keep inline examples with commands, not in a repeated footer")

    quick_start = text.index("## Quick choice")
    quick_end = text.index("## The six commands", quick_start)
    quick_section = text[quick_start:quick_end]
    if "| Need | Use |" not in quick_section or "| --- | --- |" not in quick_section:
        fail("command guide Quick choice must use a two-column Markdown table")
    for command, _ in HELP_COMMANDS:
        if f"`${command}`" not in quick_section:
            fail(f"command guide Quick choice table is missing ${command}")

    commands_start = text.index("## The six commands")
    commands_end = text.index("## Unconfigured projects", commands_start)
    command_headings = [f"### `${command}`" for command, _ in HELP_COMMANDS]
    command_positions = [
        text.find(heading, commands_start, commands_end) for heading in command_headings
    ]
    if any(position < 0 for position in command_positions):
        fail("command guide must contain all six command sections")
    if command_positions != sorted(command_positions):
        fail("command guide command sections are out of order")
    for index, (command, _) in enumerate(HELP_COMMANDS):
        start = command_positions[index]
        end = command_positions[index + 1] if index + 1 < len(command_positions) else commands_end
        section = text[start:end]
        marker_positions: list[int] = []
        for marker in HELP_FIELD_MARKERS:
            if section.count(marker) != 1:
                fail(f"command guide {command} must contain exactly one {marker}")
            marker_positions.append(section.index(marker))
        if marker_positions != sorted(marker_positions):
            fail(f"command guide {command} fields are out of order")
        if section.count("> **Example:**") != 1:
            fail(f"command guide {command} must contain exactly one inline blockquote example")
        example_position = section.index("> **Example:**")
        if example_position <= marker_positions[-1]:
            fail(f"command guide {command} example must follow all four fields")
        for field_index, marker in enumerate(HELP_FIELD_MARKERS):
            content_start = marker_positions[field_index] + len(marker)
            content_end = (
                marker_positions[field_index + 1]
                if field_index + 1 < len(marker_positions)
                else example_position
            )
            if len(normalize_whitespace(section[content_start:content_end])) < 20:
                fail(f"command guide {command} has empty or trivial content after {marker}")
        example = section[example_position:]
        if f"${command}" not in example or "`" not in example:
            fail(f"command guide {command} blockquote must contain one inline copyable prompt")

    models_start = text.index("## Models and reasoning effort")
    models_end = text.index("## Tickets and agents", models_start)
    models_section = text[models_start:models_end]
    if "| Role | Default request |" not in models_section or "| --- | --- |" not in models_section:
        fail("command guide Models must use a compact Markdown table")

    tickets_start = text.index("## Tickets and agents")
    tickets_end = text.index("## Authority boundaries", tickets_start)
    tickets_section = text[tickets_start:tickets_end]
    if "| Concept | Meaning |" not in tickets_section or "| --- | --- |" not in tickets_section:
        fail("command guide Tickets and agents must use a comparison table")

    normalized = normalize_whitespace(text)
    for required in HELP_GUIDE_SEMANTICS:
        if required not in normalized:
            fail(f"command guide is missing Help semantics: {required}")


def validate_help_prompt(prompt: str, requirements: tuple[str, ...], label: str) -> None:
    normalized = normalize_whitespace(prompt)
    for required in requirements:
        if required not in normalized:
            fail(f"{label} is missing Help mode semantics: {required}")


def parse_help_metadata_prompt(text: str) -> str:
    matches = re.findall(
        r'(?m)^  default_prompt:\s*"([^"\r\n]*)"\s*$',
        text,
    )
    if len(matches) != 1:
        fail("ultracode-help agents/openai.yaml must declare one quoted default_prompt")
    return matches[0]


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
    default_prompts = interface.get("defaultPrompt")
    if not isinstance(default_prompts, list) or not all(
        isinstance(item, str) for item in default_prompts
    ):
        fail("plugin defaultPrompt must be an array of strings")
    for skill_name in REQUIRED_SKILLS:
        if not any(f"${skill_name}" in item for item in default_prompts):
            fail(f"plugin defaultPrompt does not expose ${skill_name}")
    help_manifest_prompts = [
        item for item in default_prompts if "$ultracode-help" in item
    ]
    if len(help_manifest_prompts) != 1:
        fail("plugin defaultPrompt must contain exactly one UltraCode Help prompt")
    validate_help_prompt(
        help_manifest_prompts[0],
        HELP_MANIFEST_PROMPT_REQUIREMENTS,
        "plugin defaultPrompt Help entry",
    )
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
        skill_text = skill_path.read_text(encoding="utf-8")
        for required in COMMAND_REQUIRED_TEXT[skill_name]:
            if required not in skill_text:
                fail(f"{skill_name} is missing shared command behavior: {required}")
        if skill_name != "ultracode-help":
            for required in HELP_PRECEDENCE_REQUIRED:
                if required not in skill_text:
                    fail(f"{skill_name} is missing explicit Help precedence: {required}")
        if skill_name == "ultracode-help":
            positions = [skill_text.index(required) for required in HELP_REQUIRED_ORDER]
            if positions != sorted(positions):
                fail("ultracode-help mandatory overview blocks are out of order")

    if not COMMAND_GUIDE_PATH.is_file() or COMMAND_GUIDE_PATH.is_symlink():
        fail("missing regular command-guide.md")
    validate_help_guide(COMMAND_GUIDE_PATH.read_text(encoding="utf-8"))
    if not HELP_METADATA_PATH.is_file() or HELP_METADATA_PATH.is_symlink():
        fail("missing regular ultracode-help agents/openai.yaml")
    validate_help_prompt(
        parse_help_metadata_prompt(HELP_METADATA_PATH.read_text(encoding="utf-8")),
        HELP_METADATA_PROMPT_REQUIREMENTS,
        "ultracode-help agents/openai.yaml default_prompt",
    )

    if not COMMAND_INTERFACE_PATH.is_file() or COMMAND_INTERFACE_PATH.is_symlink():
        fail("missing shared command-interface.md contract")
    flow_text = (
        PLUGIN_ROOT / "skills" / "ultracode-flow" / "SKILL.md"
    ).read_text(encoding="utf-8")
    for required in FLOW_REQUIRED_TEXT:
        if required not in flow_text:
            fail(f"ultracode-flow is missing its public behavior: {required}")
    if "SITUAZIONE NUDA E CRUDA" in flow_text.upper():
        fail("ultracode-flow must not add the rejected situation summary")

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
