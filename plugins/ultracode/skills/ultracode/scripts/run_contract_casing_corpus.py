#!/usr/bin/env python3
"""Adversarial release corpus for case-sensitive and exact schema validation."""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import OrderedDict
from pathlib import Path
from typing import Any, Callable


def find_powershell() -> str | None:
    candidates = [
        shutil.which("powershell.exe"),
        shutil.which("powershell"),
        shutil.which("pwsh.exe"),
        shutil.which("pwsh"),
    ]
    windir = os.environ.get("WINDIR")
    if windir:
        candidates.insert(
            0,
            str(Path(windir) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"),
        )
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
    return None


def run_case(case_id: str, command: list[str], expected_exit: int) -> dict[str, Any]:
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=environment,
            timeout=180,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "id": case_id,
            "expected_exit": expected_exit,
            "actual_exit": None,
            "outcome": "MISMATCH",
            "diagnostics": [f"checker timed out after {exc.timeout} seconds"],
        }
    except OSError as exc:
        return {
            "id": case_id,
            "expected_exit": expected_exit,
            "actual_exit": None,
            "outcome": "NOT_AVAILABLE",
            "diagnostics": [str(exc)],
        }
    output = [line for line in (process.stdout + process.stderr).splitlines() if line.strip()]
    return {
        "id": case_id,
        "expected_exit": expected_exit,
        "actual_exit": process.returncode,
        "outcome": "MATCH" if process.returncode == expected_exit else "MISMATCH",
        "diagnostics": output[-8:],
    }


def checker_commands(
    plugin_root: Path, *, skip_live_corpus: bool = False
) -> list[tuple[str, list[str]]]:
    script_root = plugin_root / "skills" / "ultracode" / "scripts"
    python_command = [
        sys.executable,
        "-B",
        str(script_root / "check_contract.py"),
        "--allow-pending",
    ]
    if skip_live_corpus:
        python_command.append("--skip-live-corpus")
    commands = [
        ("python", python_command)
    ]
    powershell = find_powershell()
    if powershell:
        powershell_command = [
            powershell,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script_root / "check_contract.ps1"),
            "-AllowPending",
        ]
        if skip_live_corpus:
            powershell_command.append("-SkipLiveCorpus")
        commands.append(("powershell", powershell_command))
    return commands


def run_group(
    prefix: str,
    plugin_root: Path,
    expected_exit: int,
    *,
    skip_live_corpus: bool = False,
) -> list[dict[str, Any]]:
    commands = checker_commands(plugin_root, skip_live_corpus=skip_live_corpus)
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(commands)) as executor:
        futures = [
            executor.submit(run_case, f"{prefix}-{runtime}", command, expected_exit)
            for runtime, command in commands
        ]
        results = [future.result() for future in futures]
    available = {item["id"].rsplit("-", 1)[-1] for item in results}
    if "powershell" not in available:
        results.append(
            {
                "id": f"{prefix}-powershell",
                "expected_exit": expected_exit,
                "actual_exit": None,
                "outcome": "NOT_AVAILABLE",
                "diagnostics": ["PowerShell executable not found"],
            }
        )
    return results


def replace_evidence_key(plugin_root: Path) -> None:
    evidence_path = (
        plugin_root
        / "skills"
        / "ultracode"
        / "references"
        / "evaluation-evidence.json"
    )
    with evidence_path.open("r", encoding="utf-8") as handle:
        evidence = json.load(handle, object_pairs_hook=OrderedDict)
    if "schema_version" not in evidence or "Schema_Version" in evidence:
        raise RuntimeError("evidence does not contain the exact schema_version key")
    mutated: OrderedDict[str, Any] = OrderedDict()
    for key, value in evidence.items():
        mutated["Schema_Version" if key == "schema_version" else key] = value
    with evidence_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(mutated, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def add_unexpected_required_schema_field(plugin_root: Path) -> None:
    reference_root = plugin_root / "skills" / "ultracode" / "references"
    schema_path = reference_root / "evaluation-evidence.schema.json"
    evidence_path = reference_root / "evaluation-evidence.json"
    with schema_path.open("r", encoding="utf-8") as handle:
        schema = json.load(handle, object_pairs_hook=OrderedDict)
    required = schema.get("required")
    properties = schema.get("properties")
    if not isinstance(required, list) or not isinstance(properties, dict):
        raise RuntimeError("evaluation evidence schema has invalid required/properties")
    required.append("unexpected_required")
    properties["unexpected_required"] = {"type": "string"}
    with schema_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(schema, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    refresh_payload_binding(plugin_root)


def refresh_payload_binding(plugin_root: Path) -> None:
    reference_root = plugin_root / "skills" / "ultracode" / "references"
    evidence_path = reference_root / "evaluation-evidence.json"
    checker = plugin_root / "skills" / "ultracode" / "scripts" / "check_contract.py"
    process = subprocess.run(
        [sys.executable, "-B", str(checker), "--print-payload-hash"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
    )
    payload_hash = process.stdout.strip()
    if process.returncode != 0 or len(payload_hash) != 64:
        raise RuntimeError("cannot recompute mutated plugin payload hash")
    with evidence_path.open("r", encoding="utf-8") as handle:
        evidence = json.load(handle, object_pairs_hook=OrderedDict)
    evidence["payload_sha256"] = payload_hash
    with evidence_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(evidence, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise RuntimeError(f"{path.name} does not contain exactly one mutation target: {old}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")


def remove_help_field(plugin_root: Path) -> None:
    guide = plugin_root / "skills" / "ultracode" / "references" / "command-guide.md"
    text = guide.read_text(encoding="utf-8")
    if text.count("**What you get:**") != 7:
        raise RuntimeError("command guide does not contain seven result fields")
    guide.write_text(
        text.replace("**What you get:**", "**Outcome:**", 1),
        encoding="utf-8",
        newline="\n",
    )


def remove_help_example(plugin_root: Path) -> None:
    guide = plugin_root / "skills" / "ultracode" / "references" / "command-guide.md"
    replace_once(
        guide,
        "Use $ultracode-status to explain why validation is blocked and show the available evidence.",
        "Explain why validation is blocked and show the available evidence.",
    )


def remove_help_quick_table(plugin_root: Path) -> None:
    guide = plugin_root / "skills" / "ultracode" / "references" / "command-guide.md"
    replace_once(guide, "| Need | Use |", "| Need / Use |")


def demote_help_guide_h1(plugin_root: Path) -> None:
    guide = plugin_root / "skills" / "ultracode" / "references" / "command-guide.md"
    replace_once(
        guide,
        "# UltraCode command guide",
        "## UltraCode command guide",
    )


def remove_help_model_table(plugin_root: Path) -> None:
    guide = plugin_root / "skills" / "ultracode" / "references" / "command-guide.md"
    replace_once(guide, "| Role | Default request |", "| Model routing |")


def remove_help_ticket_table(plugin_root: Path) -> None:
    guide = plugin_root / "skills" / "ultracode" / "references" / "command-guide.md"
    replace_once(guide, "| Concept | Meaning |", "| Concept / Meaning |")


def flatten_help_example(plugin_root: Path) -> None:
    guide = plugin_root / "skills" / "ultracode" / "references" / "command-guide.md"
    text = guide.read_text(encoding="utf-8")
    if text.count("> **Example:**") != 7:
        raise RuntimeError("command guide does not contain seven inline blockquote examples")
    guide.write_text(
        text.replace("> **Example:**", "**Example:**", 1),
        encoding="utf-8",
        newline="\n",
    )


def remove_flow_help_precedence(plugin_root: Path) -> None:
    flow_skill = plugin_root / "skills" / "ultracode-flow" / "SKILL.md"
    replace_once(
        flow_skill,
        "## Respect explicit Help precedence",
        "## Interpret command precedence",
    )


def remove_sol_medium_semantics(plugin_root: Path) -> None:
    guide = plugin_root / "skills" / "ultracode" / "references" / "command-guide.md"
    text = guide.read_text(encoding="utf-8")
    target = "Sol with `medium` effort"
    if text.count(target) < 2:
        raise RuntimeError("command guide does not contain the expected Sol medium semantics")
    guide.write_text(
        text.replace(target, "the selected lead model"),
        encoding="utf-8",
        newline="\n",
    )


def remove_terra_low_semantics(plugin_root: Path) -> None:
    guide = plugin_root / "skills" / "ultracode" / "references" / "command-guide.md"
    text = guide.read_text(encoding="utf-8")
    inline_target = "Terra with `low` effort"
    wrapped_target = "Terra\nwith `low` effort"
    if inline_target not in text or wrapped_target not in text:
        raise RuntimeError("command guide does not contain the expected Terra low semantics")
    guide.write_text(
        text.replace(inline_target, "a bounded worker route").replace(
            wrapped_target,
            "a bounded worker route",
        ),
        encoding="utf-8",
        newline="\n",
    )


def remove_requested_effective_semantics(plugin_root: Path) -> None:
    guide = plugin_root / "skills" / "ultracode" / "references" / "command-guide.md"
    replace_once(guide, "Requested model and effort", "Routing intent")


def remove_init_preflight_semantics(plugin_root: Path) -> None:
    guide = plugin_root / "skills" / "ultracode" / "references" / "command-guide.md"
    replace_once(guide, "`$ultracode-init` baseline preflight", "a setup review")


def weaken_help_metadata_prompt(plugin_root: Path) -> None:
    metadata = plugin_root / "skills" / "ultracode-help" / "agents" / "openai.yaml"
    text = metadata.read_text(encoding="utf-8")
    mutated, count = re.subn(
        r'(?m)^  default_prompt: ".*"$',
        '  default_prompt: "Use $ultracode-help."',
        text,
    )
    if count != 1:
        raise RuntimeError("cannot locate the Help metadata default_prompt")
    mutated += (
        "# With no explicit topic, request the complete ordered UltraCode overview. "
        "Use a chat-friendly Markdown layout with one H1 title, comparison tables, "
        "H3 command sections, and inline blockquote examples. "
        "If I provide a command, models, flow, verify, or examples, answer only that topic. "
        "Use compact wording only when I explicitly say breve or sintetico.\n"
    )
    metadata.write_text(mutated, encoding="utf-8", newline="\n")


def weaken_help_manifest_prompt(plugin_root: Path) -> None:
    manifest_path = plugin_root / ".codex-plugin" / "plugin.json"
    with manifest_path.open("r", encoding="utf-8") as handle:
        manifest = json.load(handle, object_pairs_hook=OrderedDict)
    prompts = manifest.get("interface", {}).get("defaultPrompt")
    if not isinstance(prompts, list):
        raise RuntimeError("manifest defaultPrompt is not an array")
    help_indexes = [
        index
        for index, prompt in enumerate(prompts)
        if isinstance(prompt, str) and "$ultracode-help" in prompt
    ]
    if help_indexes != [0]:
        raise RuntimeError("manifest does not expose one leading Help prompt")
    prompts[0] = "Use $ultracode-help."
    with manifest_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(manifest, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def mutate_feature_schema(
    plugin_root: Path,
    mutation: Callable[[dict[str, Any]], None],
) -> None:
    schema_path = (
        plugin_root
        / "skills"
        / "ultracode"
        / "references"
        / "feature-verification-plan.schema.json"
    )
    with schema_path.open("r", encoding="utf-8") as handle:
        schema = json.load(handle, object_pairs_hook=OrderedDict)
    mutation(schema)
    with schema_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(schema, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def replace_feature_status(plugin_root: Path) -> None:
    def mutation(schema: dict[str, Any]) -> None:
        schema["$defs"]["plannedResult"]["properties"]["status"]["const"] = "queued"

    mutate_feature_schema(plugin_root, mutation)


def weaken_passed_evidence(plugin_root: Path) -> None:
    def mutation(schema: dict[str, Any]) -> None:
        schema["$defs"]["passedResult"]["properties"]["evidence"]["minItems"] = 0

    mutate_feature_schema(plugin_root, mutation)


def allow_unknown_evidence_fields(plugin_root: Path) -> None:
    def mutation(schema: dict[str, Any]) -> None:
        schema["$defs"]["evidenceBase"]["additionalProperties"] = True

    mutate_feature_schema(plugin_root, mutation)


def add_result_union_variant(plugin_root: Path) -> None:
    def mutation(schema: dict[str, Any]) -> None:
        schema["$defs"]["result"]["oneOf"].append(
            {"$ref": "#/$defs/plannedResult"}
        )

    mutate_feature_schema(plugin_root, mutation)


def replace_result_union_variant_with_scalar(plugin_root: Path) -> None:
    def mutation(schema: dict[str, Any]) -> None:
        schema["$defs"]["result"]["oneOf"][0] = "#/$defs/plannedResult"

    mutate_feature_schema(plugin_root, mutation)


def omit_evidence_required_field(plugin_root: Path) -> None:
    def mutation(schema: dict[str, Any]) -> None:
        schema["$defs"]["evidenceBase"]["required"].remove("captured_at")

    mutate_feature_schema(plugin_root, mutation)


def weaken_supporting_outcome(plugin_root: Path) -> None:
    def mutation(schema: dict[str, Any]) -> None:
        schema["$defs"]["supportingEvidence"]["allOf"][1]["properties"]["outcome"][
            "const"
        ] = "contradicts"

    mutate_feature_schema(plugin_root, mutation)


def weaken_contradicting_outcome(plugin_root: Path) -> None:
    def mutation(schema: dict[str, Any]) -> None:
        schema["$defs"]["contradictingEvidence"]["allOf"][1]["properties"]["outcome"][
            "const"
        ] = "supports"

    mutate_feature_schema(plugin_root, mutation)


def main() -> int:
    plugin_root = Path(__file__).resolve().parents[3]
    with tempfile.TemporaryDirectory(prefix="ultracode-contract-casing-") as temporary:
        temporary_root = Path(temporary)
        baseline_root = temporary_root / "baseline"
        malformed_evidence_root = temporary_root / "evidence-key-casing"
        malformed_schema_root = temporary_root / "schema-extra-required"
        semantic_mutations = (
            ("help-field-missing", remove_help_field),
            ("help-example-missing", remove_help_example),
            ("help-h1-missing", demote_help_guide_h1),
            ("help-quick-table-missing", remove_help_quick_table),
            ("help-model-table-missing", remove_help_model_table),
            ("help-ticket-table-missing", remove_help_ticket_table),
            ("help-example-not-blockquote", flatten_help_example),
            ("help-flow-precedence-missing", remove_flow_help_precedence),
            ("help-sol-medium-missing", remove_sol_medium_semantics),
            ("help-terra-low-missing", remove_terra_low_semantics),
            ("help-requested-effective-missing", remove_requested_effective_semantics),
            ("help-init-preflight-missing", remove_init_preflight_semantics),
            ("help-metadata-prompt-weakened", weaken_help_metadata_prompt),
            ("help-manifest-prompt-weakened", weaken_help_manifest_prompt),
            ("verify-status-set-weakened", replace_feature_status),
            ("verify-passed-evidence-weakened", weaken_passed_evidence),
            ("verify-evidence-fields-open", allow_unknown_evidence_fields),
            ("verify-result-oneof-extra", add_result_union_variant),
            ("verify-result-oneof-scalar", replace_result_union_variant_with_scalar),
            ("verify-evidence-required-missing", omit_evidence_required_field),
            ("verify-supporting-outcome-weakened", weaken_supporting_outcome),
            ("verify-contradicting-outcome-weakened", weaken_contradicting_outcome),
        )
        shutil.copytree(plugin_root, baseline_root)
        shutil.copytree(plugin_root, malformed_evidence_root)
        shutil.copytree(plugin_root, malformed_schema_root)
        replace_evidence_key(malformed_evidence_root)
        add_unexpected_required_schema_field(malformed_schema_root)
        semantic_roots: list[tuple[str, Path]] = []
        for case_id, mutate in semantic_mutations:
            mutation_root = temporary_root / case_id
            shutil.copytree(plugin_root, mutation_root)
            mutate(mutation_root)
            refresh_payload_binding(mutation_root)
            semantic_roots.append((case_id, mutation_root))
        results = run_group("baseline", baseline_root, 0)
        results.extend(run_group("evidence-key-casing", malformed_evidence_root, 1))
        results.extend(run_group("schema-extra-required", malformed_schema_root, 1))
        for case_id, mutation_root in semantic_roots:
            results.extend(
                run_group(
                    case_id,
                    mutation_root,
                    1,
                    skip_live_corpus=True,
                )
            )

    mismatched = [item["id"] for item in results if item["outcome"] == "MISMATCH"]
    unavailable = [item["id"] for item in results if item["outcome"] == "NOT_AVAILABLE"]
    report = {
        "schema_version": 1,
        "manifest_sha256": hashlib.sha256(
            (plugin_root / ".codex-plugin" / "plugin.json").read_bytes()
        ).hexdigest(),
        "cases": results,
        "summary": {
            "total": len(results),
            "matched": len(results) - len(mismatched) - len(unavailable),
            "mismatched": len(mismatched),
            "not_available": len(unavailable),
        },
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 1 if mismatched else 0


if __name__ == "__main__":
    raise SystemExit(main())
