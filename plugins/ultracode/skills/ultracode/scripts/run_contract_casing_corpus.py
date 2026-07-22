#!/usr/bin/env python3
"""Adversarial release corpus for case-sensitive and exact schema validation."""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections import OrderedDict
from pathlib import Path
from typing import Any


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


def checker_commands(plugin_root: Path) -> list[tuple[str, list[str]]]:
    script_root = plugin_root / "skills" / "ultracode" / "scripts"
    commands = [
        (
            "python",
            [sys.executable, "-B", str(script_root / "check_contract.py"), "--allow-pending"],
        )
    ]
    powershell = find_powershell()
    if powershell:
        commands.append(
            (
                "powershell",
                [
                    powershell,
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(script_root / "check_contract.ps1"),
                    "-AllowPending",
                ],
            )
        )
    return commands


def run_group(prefix: str, plugin_root: Path, expected_exit: int) -> list[dict[str, Any]]:
    commands = checker_commands(plugin_root)
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


def main() -> int:
    plugin_root = Path(__file__).resolve().parents[3]
    with tempfile.TemporaryDirectory(prefix="ultracode-contract-casing-") as temporary:
        temporary_root = Path(temporary)
        baseline_root = temporary_root / "baseline"
        malformed_evidence_root = temporary_root / "evidence-key-casing"
        malformed_schema_root = temporary_root / "schema-extra-required"
        shutil.copytree(plugin_root, baseline_root)
        shutil.copytree(plugin_root, malformed_evidence_root)
        shutil.copytree(plugin_root, malformed_schema_root)
        replace_evidence_key(malformed_evidence_root)
        add_unexpected_required_schema_field(malformed_schema_root)
        results = run_group("baseline", baseline_root, 0)
        results.extend(run_group("evidence-key-casing", malformed_evidence_root, 1))
        results.extend(run_group("schema-extra-required", malformed_schema_root, 1))

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
