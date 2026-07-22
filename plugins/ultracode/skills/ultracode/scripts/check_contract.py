#!/usr/bin/env python3
"""Deterministic structural and release-evidence checks for UltraCode."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any


SKILL_NAMES = ("ultracode", "ultracode-init", "ultracode-edit", "ultracode-status")
CORE_REFERENCES = {
    "routing-and-delegation.md",
    "validation-and-review.md",
    "project-adapter.md",
    "swarm-protocol.md",
    "control-and-status.md",
    "behavioral-contract.md",
    "eval-prompts.md",
}
CORE_RESOURCES = {
    "references/project-config.schema.json",
    "references/managed-manifest.schema.json",
    "references/evaluation-evidence.schema.json",
    "references/evaluation-traces.json",
    "references/evaluation-evidence.json",
    "scripts/project_doctor.py",
    "scripts/project_doctor.ps1",
    "scripts/run_doctor_corpus.py",
    "scripts/run_doctor_corpus.ps1",
    "scripts/run_contract_casing_corpus.py",
}
REQUIRED_CORE_TEXT = {
    "read-only command gate": "Do not run build, test, formatter, generator, package, or editor commands",
    "non-independent fallback": "Label self-review as non-independent",
    "data-driven count": "The problem structure determines the logical job count",
    "adversarial verification": "one adversarial verifier to each material finding",
    "single synthesis": "exactly one synthesis owner",
    "wave queue": "queue the remainder in visible waves",
    "safety circuit breaker": "hard_safety_cap` is a circuit breaker, not a target",
    "status write boundary": "a read-only task remains read-only",
    "bounded repair": "Limit the automatic fix-review loop to two iterations",
    "authority boundary": "Treat staging, committing, pushing, deploying, publishing",
}
REQUIRED_SCENARIOS = {f"UC-{index:02d}" for index in range(1, 35)}
REQUIRED_EVAL_PROMPTS = {
    "UC-01", "UC-03", "UC-04", "UC-06", "UC-08", "UC-10", "UC-14",
    "UC-18", "UC-19", "UC-20", "UC-23", "UC-24", "UC-25", "UC-26",
    "UC-29", "UC-30", "UC-31", "UC-32", "UC-33", "UC-34",
}
REQUIRED_EVIDENCE_SCENARIOS = {
    "UC-01", "UC-03", "UC-04", "UC-19", "UC-23", "UC-24", "UC-25",
    "UC-29", "UC-30", "UC-31", "UC-32", "UC-34",
}
EXPECTED_FIXTURES = {
    "valid project fixture Python": ("PASSED", 0),
    "valid project fixture PowerShell": ("PASSED", 0),
    "managed drift fixture Python": ("DRIFT", 2),
    "managed drift fixture PowerShell": ("DRIFT", 2),
    "incomplete managed manifest fixture Python": ("FAILED", 1),
    "incomplete managed manifest fixture PowerShell": ("FAILED", 1),
    "reparse boundary fixture Python": ("FAILED", 1),
    "reparse boundary fixture PowerShell": ("FAILED", 1),
    "semantic adapter mismatch fixture Python": ("FAILED", 1),
    "semantic adapter mismatch fixture PowerShell": ("FAILED", 1),
}
EXPECTED_FIXTURE_COMMANDS = {
    "valid project fixture Python": "${PYTHON} ${PLUGIN_ROOT}/skills/ultracode/scripts/project_doctor.py ${VALID_FIXTURE}",
    "valid project fixture PowerShell": "powershell -File ${PLUGIN_ROOT}/skills/ultracode/scripts/project_doctor.ps1 -ProjectRoot ${VALID_FIXTURE}",
    "managed drift fixture Python": "${PYTHON} ${PLUGIN_ROOT}/skills/ultracode/scripts/project_doctor.py ${DRIFT_FIXTURE}",
    "managed drift fixture PowerShell": "powershell -File ${PLUGIN_ROOT}/skills/ultracode/scripts/project_doctor.ps1 -ProjectRoot ${DRIFT_FIXTURE}",
    "incomplete managed manifest fixture Python": "${PYTHON} ${PLUGIN_ROOT}/skills/ultracode/scripts/project_doctor.py ${INCOMPLETE_MANIFEST_FIXTURE}",
    "incomplete managed manifest fixture PowerShell": "powershell -File ${PLUGIN_ROOT}/skills/ultracode/scripts/project_doctor.ps1 -ProjectRoot ${INCOMPLETE_MANIFEST_FIXTURE}",
    "reparse boundary fixture Python": "${PYTHON} ${PLUGIN_ROOT}/skills/ultracode/scripts/project_doctor.py ${REPARSE_FIXTURE}",
    "reparse boundary fixture PowerShell": "powershell -File ${PLUGIN_ROOT}/skills/ultracode/scripts/project_doctor.ps1 -ProjectRoot ${REPARSE_FIXTURE}",
    "semantic adapter mismatch fixture Python": "${PYTHON} ${PLUGIN_ROOT}/skills/ultracode/scripts/project_doctor.py ${SEMANTIC_ADAPTER_FIXTURE}",
    "semantic adapter mismatch fixture PowerShell": "powershell -File ${PLUGIN_ROOT}/skills/ultracode/scripts/project_doctor.ps1 -ProjectRoot ${SEMANTIC_ADAPTER_FIXTURE}",
}
REQUIRED_VALIDATIONS = {
    "quick_validate ultracode",
    "quick_validate ultracode-init",
    "quick_validate ultracode-edit",
    "quick_validate ultracode-status",
    "validate_plugin",
    "contract checker Python bootstrap",
    "contract checker PowerShell bootstrap",
    "contract casing corpus",
}
EXPECTED_VALIDATION_COMMANDS = {
    "quick_validate ultracode": "uv run --offline --with pyyaml -- python ${SKILL_CREATOR}/scripts/quick_validate.py ${PLUGIN_ROOT}/skills/ultracode",
    "quick_validate ultracode-init": "uv run --offline --with pyyaml -- python ${SKILL_CREATOR}/scripts/quick_validate.py ${PLUGIN_ROOT}/skills/ultracode-init",
    "quick_validate ultracode-edit": "uv run --offline --with pyyaml -- python ${SKILL_CREATOR}/scripts/quick_validate.py ${PLUGIN_ROOT}/skills/ultracode-edit",
    "quick_validate ultracode-status": "uv run --offline --with pyyaml -- python ${SKILL_CREATOR}/scripts/quick_validate.py ${PLUGIN_ROOT}/skills/ultracode-status",
    "validate_plugin": "uv run --offline --with pyyaml -- python ${PLUGIN_CREATOR}/scripts/validate_plugin.py ${PLUGIN_ROOT}",
    "contract checker Python bootstrap": "${PYTHON} ${PLUGIN_ROOT}/skills/ultracode/scripts/check_contract.py --allow-pending",
    "contract checker PowerShell bootstrap": "powershell -File ${PLUGIN_ROOT}/skills/ultracode/scripts/check_contract.ps1 -AllowPending",
    "contract casing corpus": "${PYTHON} ${PLUGIN_ROOT}/skills/ultracode/scripts/run_contract_casing_corpus.py",
}
EVIDENCE_KEYS = {
    "schema_version", "attestation_scope", "plugin_version_prefix", "evaluated_on",
    "skill_sha256", "payload_sha256", "trace_artifact", "trace_sha256",
    "scenario_results", "fixture_results", "validation_results", "audit_results",
}
PAYLOAD_EXCLUSIONS = {
    "skills/ultracode/references/evaluation-evidence.json",
    "skills/ultracode/references/evaluation-traces.json",
}
VALID_STATUSES = {"PASSED", "FAILED", "DRIFT", "PENDING", "NOT_AVAILABLE"}
HASH_RE = re.compile(r"^[0-9a-f]{64}$")
TRACE_ID_RE = re.compile(r"^trace-[a-z0-9][a-z0-9-]*$")
LIVE_CORPUS_CASES = {
    "valid": ("PASSED", 0),
    "drift": ("DRIFT", 2),
    "empty-manifest": ("FAILED", 1),
    "omitted-config": ("FAILED", 1),
    "broken-claude-root-import": ("FAILED", 1),
    "claude-root-extra-body": ("FAILED", 1),
    "casing": ("FAILED", 1),
    "config-key-casing": ("FAILED", 1),
    "artifact-id-casing": ("FAILED", 1),
    "role-id-casing": ("FAILED", 1),
    "semantic-rule-adapter": ("FAILED", 1),
    "semantic-skill-adapter": ("FAILED", 1),
    "semantic-skill-adapter-contrary": ("FAILED", 1),
    "invalid-managed-block": ("FAILED", 1),
    "invalid-managed-block-key": ("FAILED", 1),
    "invalid-managed-path-char": ("FAILED", 1),
    "rich-valid": ("PASSED", 0),
    "role-valid": ("PASSED", 0),
    "duplicate-claude-role-key": ("FAILED", 1),
    "extra-claude-role-key": ("FAILED", 1),
    "reparse": ("FAILED", 1),
    "missing-config-route": ("FAILED", 1),
    "boolean-control-plan": ("FAILED", 1),
    "boolean-authority": ("FAILED", 1),
    "boolean-decomposition": ("FAILED", 1),
    "boolean-concurrency": ("FAILED", 1),
    "boolean-model-policy": ("FAILED", 1),
    "boolean-command-evidence": ("FAILED", 1),
    "boolean-completion-review": ("FAILED", 1),
    "boolean-generated-by": ("FAILED", 1),
    "boolean-manifest-mode": ("FAILED", 1),
    "boolean-config-schema": ("FAILED", 1),
    "boolean-manifest-schema": ("FAILED", 1),
    "boolean-synthesis": ("FAILED", 1),
    "canonical-skill-missing-frontmatter": ("FAILED", 1),
    "skill-description-mismatch": ("FAILED", 1),
}


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    raise SystemExit(1)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        fail(f"cannot read {path}: {exc}")
    raise AssertionError("unreachable")


def load_json(path: Path, label: str) -> Any:
    try:
        return json.loads(read_text(path))
    except json.JSONDecodeError as exc:
        fail(f"invalid {label} JSON: {exc}")
    raise AssertionError("unreachable")


def require_exact_keys(value: dict[str, Any], expected: set[str], label: str) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        fail(f"{label} keys differ; missing={missing}, extra={extra}")


def require_nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        fail(f"{label} must be a non-empty string")
    return value


def is_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def integer_equals(value: Any, expected: int) -> bool:
    return is_integer(value) and value == expected


def require_unique_objects(items: Any, key: str, label: str) -> dict[str, dict[str, Any]]:
    if not isinstance(items, list) or not items:
        fail(f"{label} must be a non-empty array")
    result: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            fail(f"{label}[{index}] must be an object")
        identity = require_nonempty_string(item.get(key), f"{label}[{index}].{key}")
        if identity in result:
            fail(f"{label} contains duplicate {key}: {identity}")
        result[identity] = item
    return result


def compute_payload_sha256(plugin_root: Path) -> str:
    files: list[tuple[str, Path]] = []
    reparse_flag = 0x400

    def is_reparse(stat_result: os.stat_result) -> bool:
        return bool(getattr(stat_result, "st_file_attributes", 0) & reparse_flag)

    def visit(directory: Path, prefix: str) -> None:
        try:
            with os.scandir(directory) as iterator:
                entries = list(iterator)
        except OSError as exc:
            fail(f"cannot enumerate plugin payload directory {directory}: {exc}")
        for entry in entries:
            try:
                stat_result = entry.stat(follow_symlinks=False)
            except OSError as exc:
                fail(f"cannot inspect plugin payload entry {entry.path}: {exc}")
            if entry.is_symlink() or is_reparse(stat_result):
                fail(f"plugin payload contains a symlink or reparse entry: {entry.path}")
            relative = f"{prefix}/{entry.name}" if prefix else entry.name
            path = Path(entry.path)
            if entry.is_dir(follow_symlinks=False):
                visit(path, relative)
            elif entry.is_file(follow_symlinks=False) and relative not in PAYLOAD_EXCLUSIONS:
                files.append((relative, path))

    try:
        root_stat = os.lstat(plugin_root)
    except OSError as exc:
        fail(f"cannot inspect plugin payload root: {exc}")
    if plugin_root.is_symlink() or is_reparse(root_stat):
        fail("plugin payload root cannot be a symlink or reparse point")
    visit(plugin_root, "")
    digest = hashlib.sha256()
    for relative, path in sorted(files, key=lambda item: item[0]):
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        try:
            digest.update(path.read_bytes())
        except OSError as exc:
            fail(f"cannot hash plugin payload file {relative}: {exc}")
        digest.update(b"\0")
    return digest.hexdigest()


def validate_live_corpus_report(
    report: Any,
    runtime: str,
    doctor_path: Path,
    process_exit: int,
) -> None:
    if not isinstance(report, dict):
        fail(f"{runtime} live corpus report root must be an object")
    require_exact_keys(
        report,
        {"schema_version", "runtime", "doctor_sha256", "cases", "summary"},
        f"{runtime} live corpus report",
    )
    if not integer_equals(report.get("schema_version"), 1) or report.get("runtime") != runtime:
        fail(f"{runtime} live corpus report identity is invalid")
    doctor_hash = hashlib.sha256(doctor_path.read_bytes()).hexdigest()
    if report.get("doctor_sha256") != doctor_hash:
        fail(f"{runtime} live corpus report does not bind the current doctor")
    cases = require_unique_objects(report.get("cases"), "id", f"{runtime} live corpus cases")
    if set(cases) != set(LIVE_CORPUS_CASES):
        fail(f"{runtime} live corpus case set is incomplete or unexpected")
    mismatches: list[str] = []
    unavailable: list[str] = []
    for case_id, item in cases.items():
        require_exact_keys(
            item,
            {
                "id", "expected_status", "expected_exit", "actual_status",
                "actual_exit", "outcome", "diagnostics",
            },
            f"{runtime} live corpus case {case_id}",
        )
        expected_status, expected_exit = LIVE_CORPUS_CASES[case_id]
        if (
            item.get("expected_status") != expected_status
            or not integer_equals(item.get("expected_exit"), expected_exit)
        ):
            fail(f"{runtime} live corpus case {case_id} changed its expected result")
        diagnostics = item.get("diagnostics")
        if not isinstance(diagnostics, list) or any(not isinstance(value, str) for value in diagnostics):
            fail(f"{runtime} live corpus case {case_id} diagnostics must be strings")
        if item.get("outcome") == "NOT_AVAILABLE":
            unavailable.append(case_id)
            if item.get("actual_status") != "NOT_AVAILABLE" or item.get("actual_exit") is not None:
                fail(f"{runtime} live corpus case {case_id} has malformed NOT_AVAILABLE state")
        elif item.get("outcome") == "MATCH":
            if (
                item.get("actual_status") != expected_status
                or not integer_equals(item.get("actual_exit"), expected_exit)
            ):
                fail(f"{runtime} live corpus case {case_id} claims a false match")
        else:
            mismatches.append(case_id)
    summary = report.get("summary")
    if not isinstance(summary, dict):
        fail(f"{runtime} live corpus summary must be an object")
    require_exact_keys(summary, {"total", "matched", "mismatched", "not_available"}, f"{runtime} live corpus summary")
    expected_summary = {
        "total": len(LIVE_CORPUS_CASES),
        "matched": len(LIVE_CORPUS_CASES) - len(mismatches) - len(unavailable),
        "mismatched": len(mismatches),
        "not_available": len(unavailable),
    }
    if any(
        not integer_equals(summary.get(key), expected)
        for key, expected in expected_summary.items()
    ):
        fail(f"{runtime} live corpus summary does not match its case records")
    if unavailable:
        platform_note = " on Windows" if os.name == "nt" else ""
        fail(f"{runtime} live corpus cases are NOT_AVAILABLE{platform_note}: {sorted(unavailable)}")
    if mismatches or process_exit != 0:
        fail(
            f"{runtime} live corpus failed; process_exit={process_exit}, mismatches={sorted(mismatches)}"
        )


def run_live_python_corpus(core_root: Path) -> None:
    harness = core_root / "scripts" / "run_doctor_corpus.py"
    doctor = core_root / "scripts" / "project_doctor.py"
    try:
        process = subprocess.run(
            [sys.executable, str(harness)],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        fail(f"cannot execute Python live doctor corpus: {exc}")
    try:
        report = json.loads(process.stdout)
    except json.JSONDecodeError as exc:
        detail = process.stderr.strip() or process.stdout.strip()
        fail(f"invalid Python live corpus JSON: {exc}; output={detail!r}")
    validate_live_corpus_report(report, "python", doctor, process.returncode)


def validate_schema_document(schema: Any) -> None:
    if not isinstance(schema, dict):
        fail("evaluation evidence schema root must be an object")
    required = schema.get("required")
    properties = schema.get("properties")
    if schema.get("type") != "object" or schema.get("additionalProperties") is not False:
        fail("evaluation evidence schema must close the root object")
    if (
        not isinstance(required, list)
        or len(required) != len(EVIDENCE_KEYS)
        or set(required) != EVIDENCE_KEYS
    ):
        fail("evaluation evidence schema must require exactly the release fields")
    if not isinstance(properties, dict) or set(properties) != EVIDENCE_KEYS:
        fail("evaluation evidence schema must define exactly the release fields")
    if not integer_equals(properties.get("schema_version", {}).get("const"), 2):
        fail("evaluation evidence schema version must be const 2")
    if properties.get("attestation_scope", {}).get("const") != "local-consistency-only":
        fail("evaluation evidence schema must pin local-consistency-only attestation scope")
    if properties.get("trace_artifact", {}).get("const") != "evaluation-traces.json":
        fail("evaluation evidence schema must pin the trace artifact name")
    expected_counts = {
        "scenario_results": 12,
        "fixture_results": 10,
        "validation_results": 8,
        "audit_results": 1,
    }
    for field, count in expected_counts.items():
        definition = properties.get(field, {})
        if (
            not integer_equals(definition.get("minItems"), count)
            or not integer_equals(definition.get("maxItems"), count)
            or definition.get("uniqueItems") is not True
        ):
            fail(f"evaluation evidence schema must pin {field} to {count} unique results")
    hashes = properties.get("skill_sha256", {})
    if hashes.get("additionalProperties") is not False:
        fail("evaluation evidence schema must close skill_sha256")
    if set(hashes.get("required", [])) != set(SKILL_NAMES):
        fail("evaluation evidence schema must require exactly four skill hashes")
    defs = schema.get("$defs", {})
    status_enum = set(defs.get("status", {}).get("enum", []))
    if status_enum != VALID_STATUSES:
        fail("evaluation evidence schema status enum is incomplete")


def validate_result_shape(item: dict[str, Any], kind: str, label: str) -> None:
    if kind == "scenario":
        require_exact_keys(item, {"id", "status", "trace_id", "evidence"}, label)
    elif kind in {"fixture", "validation"}:
        require_exact_keys(
            item,
            {"check", "status", "command", "exit_code", "trace_id", "evidence"},
            label,
        )
        require_nonempty_string(item.get("command"), f"{label}.command")
    elif kind == "audit":
        require_exact_keys(item, {"check", "severity", "status", "trace_id", "evidence"}, label)
        if item.get("severity") not in {"HIGH", "MEDIUM", "LOW"}:
            fail(f"{label}.severity is invalid")
    else:
        fail(f"internal error: unknown result kind {kind}")
    if item.get("status") not in VALID_STATUSES:
        fail(f"{label}.status is invalid")
    trace_id = require_nonempty_string(item.get("trace_id"), f"{label}.trace_id")
    if not TRACE_ID_RE.fullmatch(trace_id):
        fail(f"{label}.trace_id is invalid")
    require_nonempty_string(item.get("evidence"), f"{label}.evidence")


def validate_executable_result(item: dict[str, Any], label: str) -> None:
    status = item["status"]
    exit_code = item["exit_code"]
    if status in {"PENDING", "NOT_AVAILABLE"}:
        if exit_code is not None:
            fail(f"{label} must use null exit_code while {status}")
        return
    if isinstance(exit_code, bool) or not isinstance(exit_code, int):
        fail(f"{label} must record an integer exit_code after execution")
    expected_exit = {"PASSED": 0, "FAILED": 1, "DRIFT": 2}.get(status)
    if exit_code != expected_exit:
        fail(f"{label} status {status} must use exit_code {expected_exit}")


def validate_trace_records(
    traces: Any,
    plugin_version_prefix: str,
    evaluated_on: str,
) -> dict[str, dict[str, Any]]:
    if not isinstance(traces, dict):
        fail("evaluation traces root must be an object")
    require_exact_keys(
        traces,
        {"schema_version", "attestation_scope", "plugin_version_prefix", "generated_on", "records"},
        "evaluation traces",
    )
    if not integer_equals(traces.get("schema_version"), 1):
        fail("evaluation traces schema_version must be 1")
    if traces.get("plugin_version_prefix") != plugin_version_prefix:
        fail("evaluation traces plugin version does not match evidence")
    if traces.get("attestation_scope") != "local-consistency-only":
        fail("evaluation traces must declare local-consistency-only attestation scope")
    if traces.get("generated_on") != evaluated_on:
        fail("evaluation traces date does not match evidence")
    records = require_unique_objects(traces.get("records"), "trace_id", "trace records")
    expected_keys = {
        "trace_id", "category", "subject", "status", "source_type",
        "command", "exit_code", "facts",
    }
    for trace_id, record in records.items():
        require_exact_keys(record, expected_keys, f"trace record {trace_id}")
        if not TRACE_ID_RE.fullmatch(trace_id):
            fail(f"trace record ID is invalid: {trace_id}")
        if record.get("category") not in {"scenario", "fixture", "validation", "audit"}:
            fail(f"trace record {trace_id} has invalid category")
        require_nonempty_string(record.get("subject"), f"trace record {trace_id}.subject")
        status = record.get("status")
        if status not in VALID_STATUSES:
            fail(f"trace record {trace_id} has invalid status")
        source_type = require_nonempty_string(
            record.get("source_type"), f"trace record {trace_id}.source_type"
        )
        if source_type not in {
            "fresh-agent-result", "command-result", "independent-audit-result",
            "planned", "planned-command",
        }:
            fail(f"trace record {trace_id} has invalid source_type")
        command = record.get("command")
        if command is not None and (not isinstance(command, str) or not command.strip()):
            fail(f"trace record {trace_id}.command must be null or non-empty")
        exit_code = record.get("exit_code")
        if exit_code is not None and (isinstance(exit_code, bool) or not isinstance(exit_code, int)):
            fail(f"trace record {trace_id}.exit_code must be null or integer")
        facts = record.get("facts")
        if not isinstance(facts, list) or not facts or any(
            not isinstance(fact, str) or not fact.strip() for fact in facts
        ):
            fail(f"trace record {trace_id}.facts must contain non-empty strings")
        if status == "PENDING":
            expected_source = (
                "planned-command"
                if record["category"] in {"fixture", "validation"}
                else "planned"
            )
            if source_type != expected_source or exit_code is not None:
                fail(f"pending trace {trace_id} must be explicitly planned and unexecuted")
        else:
            expected_sources = {
                "scenario": {"fresh-agent-result", "command-result"},
                "fixture": {"command-result"},
                "validation": {"command-result"},
                "audit": {"independent-audit-result"},
            }[record["category"]]
            if source_type not in expected_sources:
                fail(
                    f"executed trace {trace_id} must use one of {sorted(expected_sources)}"
                )
    return records


def bind_result_to_trace(
    item: dict[str, Any],
    category: str,
    subject_key: str,
    records: dict[str, dict[str, Any]],
) -> str:
    trace_id = item["trace_id"]
    record = records.get(trace_id)
    if record is None:
        fail(f"result references missing trace: {trace_id}")
    if record["category"] != category:
        fail(f"trace {trace_id} category does not match {category}")
    if record["subject"] != item[subject_key] or record["status"] != item["status"]:
        fail(f"trace {trace_id} subject or status does not match its result")
    if category in {"fixture", "validation"}:
        if record["command"] != item["command"] or record["exit_code"] != item["exit_code"]:
            fail(f"trace {trace_id} command or exit_code does not match its result")
    return trace_id


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--allow-pending",
        action="store_true",
        help="validate bootstrap structure while allowing unexecuted release results",
    )
    parser.add_argument(
        "--print-payload-hash",
        action="store_true",
        help="print the deterministic current plugin payload hash and exit",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    script_path = Path(__file__).resolve()
    core_root = script_path.parent.parent
    skills_root = core_root.parent
    plugin_root = skills_root.parent
    reference_root = core_root / "references"
    manifest_path = plugin_root / ".codex-plugin" / "plugin.json"

    if args.print_payload_hash:
        print(compute_payload_sha256(plugin_root))
        return

    for path in (skills_root, core_root / "SKILL.md", reference_root, manifest_path):
        if not path.exists():
            fail(f"missing required path: {path}")

    skill_hashes: dict[str, str] = {}
    for skill_name in SKILL_NAMES:
        skill_root = skills_root / skill_name
        skill_path = skill_root / "SKILL.md"
        metadata_path = skill_root / "agents" / "openai.yaml"
        if not skill_path.is_file() or not metadata_path.is_file():
            fail(f"missing skill or metadata for {skill_name}")
        skill_text = read_text(skill_path)
        if "TODO" in skill_text:
            fail(f"{skill_name}/SKILL.md contains TODO text")
        if len(skill_text.splitlines()) >= 500:
            fail(f"{skill_name}/SKILL.md must remain under 500 lines")
        frontmatter = re.match(r"\A---\s*\n(.*?)\n---\s*\n", skill_text, re.DOTALL)
        if not frontmatter or not re.search(
            rf"^name:\s*{re.escape(skill_name)}\s*$", frontmatter.group(1), re.MULTILINE
        ):
            fail(f"{skill_name}/SKILL.md frontmatter name is missing or invalid")
        metadata_text = read_text(metadata_path)
        if f"${skill_name}" not in metadata_text:
            fail(f"{skill_name}/agents/openai.yaml default prompt must mention ${skill_name}")
        skill_hashes[skill_name] = hashlib.sha256(skill_path.read_bytes()).hexdigest()

    core_text = read_text(core_root / "SKILL.md")
    for label, required in REQUIRED_CORE_TEXT.items():
        if required not in core_text:
            fail(f"missing core contract clause: {label}")

    actual_references = {path.name for path in reference_root.glob("*.md")}
    missing_references = CORE_REFERENCES - actual_references
    if missing_references:
        fail(f"missing references: {sorted(missing_references)}")
    for reference in CORE_REFERENCES:
        if f"references/{reference}" not in core_text:
            fail(f"core SKILL.md does not route to {reference}")
    for relative in CORE_RESOURCES:
        if not (core_root / relative).is_file():
            fail(f"missing core resource: {relative}")

    run_live_python_corpus(core_root)

    for schema_name in (
        "project-config.schema.json",
        "managed-manifest.schema.json",
        "evaluation-evidence.schema.json",
    ):
        load_json(reference_root / schema_name, schema_name)

    init_text = read_text(skills_root / "ultracode-init" / "SKILL.md")
    edit_text = read_text(skills_root / "ultracode-edit" / "SKILL.md")
    status_text = read_text(skills_root / "ultracode-status" / "SKILL.md")
    for required in (
        "project-config.schema.json", "Do not ask how many swarm agents",
        ".ultracode/managed.json", ".git/info/exclude",
    ):
        if required not in init_text:
            fail(f"ultracode-init is missing: {required}")
    for required in (
        "project_doctor", "managed.json", "Never ask for an agent count",
        "Do not delete automatically",
    ):
        if required not in edit_text:
            fail(f"ultracode-edit is missing: {required}")
    for required in (
        "Stay read-only", "logical jobs versus currently live agent instances",
        "Never invent percentages",
    ):
        if required not in status_text:
            fail(f"ultracode-status is missing: {required}")

    contract_text = read_text(reference_root / "behavioral-contract.md")
    missing_scenarios = REQUIRED_SCENARIOS - set(re.findall(r"UC-\d{2}", contract_text))
    if missing_scenarios:
        fail(f"missing behavioral scenarios: {sorted(missing_scenarios)}")

    eval_prompts = read_text(reference_root / "eval-prompts.md")
    missing_eval_prompts = REQUIRED_EVAL_PROMPTS - set(re.findall(r"UC-\d{2}", eval_prompts))
    if missing_eval_prompts:
        fail(f"missing forward-test prompts: {sorted(missing_eval_prompts)}")

    manifest = load_json(manifest_path, "plugin manifest")
    if not isinstance(manifest, dict):
        fail("plugin manifest root must be an object")
    if manifest.get("name") != "ultracode" or manifest.get("skills") != "./skills/":
        fail("plugin manifest identity or skill path is invalid")
    if "hooks" in manifest:
        fail("unsupported hooks field must not be present")
    prompts = manifest.get("interface", {}).get("defaultPrompt", [])
    if not isinstance(prompts, list) or not all(isinstance(item, str) for item in prompts):
        fail("plugin default prompts must be an array of strings")
    if not any("$ultracode-init" in item for item in prompts):
        fail("plugin default prompts must expose $ultracode-init")
    if not any("$ultracode-status" in item for item in prompts):
        fail("plugin default prompts must expose $ultracode-status")

    schema = load_json(reference_root / "evaluation-evidence.schema.json", "evaluation evidence schema")
    validate_schema_document(schema)
    evidence_path = reference_root / "evaluation-evidence.json"
    evidence = load_json(evidence_path, "evaluation evidence")
    if not isinstance(evidence, dict):
        fail("evaluation evidence root must be an object")
    require_exact_keys(evidence, EVIDENCE_KEYS, "evaluation evidence")
    if not integer_equals(evidence.get("schema_version"), 2):
        fail("evaluation evidence schema_version must be 2")
    if evidence.get("attestation_scope") != "local-consistency-only":
        fail("evaluation evidence must declare local-consistency-only attestation scope")
    expected_prefix = require_nonempty_string(
        manifest.get("version"), "plugin manifest.version"
    ).split("+", 1)[0]
    if evidence.get("plugin_version_prefix") != expected_prefix:
        fail("evaluation evidence version prefix does not match the plugin manifest")
    evaluated_on = require_nonempty_string(evidence.get("evaluated_on"), "evaluated_on")
    try:
        date.fromisoformat(evaluated_on)
    except ValueError:
        fail("evaluated_on must be an ISO date")
    hashes = evidence.get("skill_sha256")
    if not isinstance(hashes, dict) or set(hashes) != set(SKILL_NAMES):
        fail("evaluation evidence must contain exactly four named skill hashes")
    for skill_name, actual_hash in skill_hashes.items():
        recorded_hash = hashes.get(skill_name)
        if not isinstance(recorded_hash, str) or not HASH_RE.fullmatch(recorded_hash):
            fail(f"evaluation evidence hash is invalid for {skill_name}")
        if recorded_hash != actual_hash:
            fail(f"evaluation evidence hash mismatch for {skill_name}")

    payload_hash = evidence.get("payload_sha256")
    if not isinstance(payload_hash, str) or not HASH_RE.fullmatch(payload_hash):
        fail("evaluation evidence payload_sha256 is invalid")
    actual_payload_hash = compute_payload_sha256(plugin_root)
    if payload_hash != actual_payload_hash:
        fail("evaluation evidence payload_sha256 does not match the current plugin tree")

    if evidence.get("trace_artifact") != "evaluation-traces.json":
        fail("evaluation evidence must use evaluation-traces.json")
    trace_path = reference_root / "evaluation-traces.json"
    trace_hash = hashlib.sha256(trace_path.read_bytes()).hexdigest()
    if evidence.get("trace_sha256") != trace_hash:
        fail("evaluation trace hash does not match evaluation-traces.json")
    records = validate_trace_records(
        load_json(trace_path, "evaluation traces"), expected_prefix, evaluated_on
    )

    pending_results: list[str] = []
    referenced_trace_ids: set[str] = set()

    scenarios = require_unique_objects(evidence.get("scenario_results"), "id", "scenario_results")
    if set(scenarios) != REQUIRED_EVIDENCE_SCENARIOS:
        fail(
            "scenario_results must contain exactly the required release scenarios: "
            f"{sorted(REQUIRED_EVIDENCE_SCENARIOS)}"
        )
    for scenario_id, item in scenarios.items():
        validate_result_shape(item, "scenario", f"scenario {scenario_id}")
        referenced_trace_ids.add(bind_result_to_trace(item, "scenario", "id", records))
        if item["status"] == "PENDING":
            pending_results.append(f"scenario:{scenario_id}")
        elif item["status"] != "PASSED":
            fail(f"release scenario {scenario_id} must pass")

    fixtures = require_unique_objects(evidence.get("fixture_results"), "check", "fixture_results")
    if set(fixtures) != set(EXPECTED_FIXTURES):
        fail("fixture_results do not match the required two-runtime parity corpus")
    for check, item in fixtures.items():
        validate_result_shape(item, "fixture", f"fixture {check}")
        validate_executable_result(item, f"fixture {check}")
        referenced_trace_ids.add(bind_result_to_trace(item, "fixture", "check", records))
        if item["command"] != EXPECTED_FIXTURE_COMMANDS[check]:
            fail(f"fixture {check} command does not match the required command")
        if item["status"] == "PENDING":
            pending_results.append(f"fixture:{check}")
        else:
            expected_status, expected_exit = EXPECTED_FIXTURES[check]
            if item["status"] != expected_status or item["exit_code"] != expected_exit:
                fail(
                    f"fixture {check} must record {expected_status} with exit code {expected_exit}"
                )

    validations = require_unique_objects(
        evidence.get("validation_results"), "check", "validation_results"
    )
    if set(validations) != REQUIRED_VALIDATIONS:
        fail("validation_results do not contain exactly the required validators")
    for check, item in validations.items():
        validate_result_shape(item, "validation", f"validation {check}")
        validate_executable_result(item, f"validation {check}")
        referenced_trace_ids.add(bind_result_to_trace(item, "validation", "check", records))
        expected_command = EXPECTED_VALIDATION_COMMANDS[check]
        if item["command"] != expected_command:
            fail(f"validation {check} command does not match the required command")
        if item["status"] == "PENDING":
            pending_results.append(f"validation:{check}")
        elif item["status"] != "PASSED" or item["exit_code"] != 0:
            fail(f"release validation {check} must pass with exit code 0")

    audits = require_unique_objects(evidence.get("audit_results"), "check", "audit_results")
    if set(audits) != {"final independent high-severity audit"}:
        fail("audit_results must contain the final independent high-severity audit")
    for check, item in audits.items():
        validate_result_shape(item, "audit", f"audit {check}")
        referenced_trace_ids.add(bind_result_to_trace(item, "audit", "check", records))
        if item["severity"] != "HIGH":
            fail("final independent audit must cover high-severity findings")
        if item["status"] == "PENDING":
            pending_results.append(f"audit:{check}")
        elif item["status"] != "PASSED":
            fail("final independent high-severity audit must pass")

    if referenced_trace_ids != set(records):
        missing = sorted(set(records) - referenced_trace_ids)
        fail(f"evaluation traces contain unreferenced records: {missing}")

    if pending_results:
        summary = ", ".join(sorted(pending_results))
        if not args.allow_pending:
            print(f"PENDING: release evidence is incomplete: {summary}")
            raise SystemExit(2)
        print(f"UltraCode contract structure passed with pending release evidence: {summary}")
        return

    print("UltraCode contract and release evidence checks passed")


if __name__ == "__main__":
    main()
