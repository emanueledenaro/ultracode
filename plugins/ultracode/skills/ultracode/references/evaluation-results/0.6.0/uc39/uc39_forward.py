#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path


ARTIFACT_ROOT = Path(__file__).resolve().parent
SCHEMA_PATH = ARTIFACT_ROOT.parents[2] / "feature-verification-plan.schema.json"
SAMPLE_PROGRAM = ARTIFACT_ROOT / "sample_preference.py"

ROOT_FIELDS = {
    "schema_version",
    "plan_id",
    "feature",
    "objective",
    "scope",
    "acceptance_criteria",
    "scenarios",
    "created_at",
    "updated_at",
}
CRITERION_FIELDS = {"id", "statement"}
SCENARIO_FIELDS = {"id", "title", "criterion_ids", "procedure", "expected", "results"}
RESULT_FIELDS = {"status", "recorded_at", "reason", "evidence"}
EVIDENCE_FIELDS = {"kind", "source", "observed", "outcome", "captured_at"}
STATUSES = {"planned", "passed", "failed", "not-run", "not-applicable"}
EVIDENCE_KINDS = {"command", "assertion", "observation", "artifact", "manual"}
TIMESTAMP_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:Z|[+-][0-9]{2}:[0-9]{2})$"
)
PLAN_ID_RE = re.compile(r"^verify-[a-z0-9][a-z0-9-]*$")
AC_ID_RE = re.compile(r"^AC-[0-9]{3}$")
FV_ID_RE = re.compile(r"^FV-[0-9]{3}$")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_timestamp(value: object, where: str, errors: list[str]) -> datetime | None:
    if not isinstance(value, str) or not TIMESTAMP_RE.fullmatch(value):
        errors.append(f"{where}: expected RFC3339 whole-second timestamp with timezone")
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"{where}: timestamp is not a real calendar date/time")
        return None


def check_exact_fields(value: object, fields: set[str], where: str, errors: list[str]) -> bool:
    if not isinstance(value, dict):
        errors.append(f"{where}: expected object")
        return False
    missing = sorted(fields - set(value))
    extra = sorted(set(value) - fields)
    if missing:
        errors.append(f"{where}: missing fields {missing}")
    if extra:
        errors.append(f"{where}: unknown fields {extra}")
    return not missing and not extra


def nonempty_string(value: object, where: str, errors: list[str]) -> bool:
    if not isinstance(value, str) or len(value) < 1:
        errors.append(f"{where}: expected non-empty string")
        return False
    return True


def validate_result(result: object, where: str, errors: list[str]) -> datetime | None:
    if not check_exact_fields(result, RESULT_FIELDS, where, errors):
        return None
    assert isinstance(result, dict)
    status_value = result.get("status")
    if status_value not in STATUSES:
        errors.append(f"{where}.status: unknown status {status_value!r}")
        return parse_timestamp(result.get("recorded_at"), f"{where}.recorded_at", errors)

    timestamp = parse_timestamp(result.get("recorded_at"), f"{where}.recorded_at", errors)
    reason = result.get("reason")
    evidence = result.get("evidence")
    if not isinstance(evidence, list):
        errors.append(f"{where}.evidence: expected array")
        return timestamp

    if status_value == "planned":
        if reason is not None:
            errors.append(f"{where}.reason: planned requires null")
        if evidence:
            errors.append(f"{where}.evidence: planned requires empty evidence")
    elif status_value in {"not-run", "not-applicable"}:
        if not isinstance(reason, str) or not reason:
            errors.append(f"{where}.reason: {status_value} requires non-empty reason")
        if evidence:
            errors.append(f"{where}.evidence: {status_value} requires empty evidence")
    else:
        if reason is not None:
            errors.append(f"{where}.reason: {status_value} requires null")
        if not evidence:
            errors.append(f"{where}.evidence: {status_value} requires at least one item")

    expected_outcome = "supports" if status_value == "passed" else (
        "contradicts" if status_value == "failed" else None
    )
    for index, item in enumerate(evidence):
        evidence_where = f"{where}.evidence[{index}]"
        if not check_exact_fields(item, EVIDENCE_FIELDS, evidence_where, errors):
            continue
        assert isinstance(item, dict)
        if item.get("kind") not in EVIDENCE_KINDS:
            errors.append(f"{evidence_where}.kind: invalid evidence kind {item.get('kind')!r}")
        nonempty_string(item.get("source"), f"{evidence_where}.source", errors)
        nonempty_string(item.get("observed"), f"{evidence_where}.observed", errors)
        if item.get("outcome") not in {"supports", "contradicts"}:
            errors.append(f"{evidence_where}.outcome: invalid outcome {item.get('outcome')!r}")
        if expected_outcome is not None and item.get("outcome") != expected_outcome:
            errors.append(
                f"{evidence_where}.outcome: {status_value} requires {expected_outcome!r}, "
                f"got {item.get('outcome')!r}"
            )
        parse_timestamp(item.get("captured_at"), f"{evidence_where}.captured_at", errors)
    return timestamp


def validate_plan(plan: object) -> list[str]:
    errors: list[str] = []
    if not check_exact_fields(plan, ROOT_FIELDS, "root", errors):
        return errors
    assert isinstance(plan, dict)

    if type(plan.get("schema_version")) is not int or plan.get("schema_version") != 1:
        errors.append("root.schema_version: expected integer constant 1")
    if not isinstance(plan.get("plan_id"), str) or not PLAN_ID_RE.fullmatch(plan["plan_id"]):
        errors.append("root.plan_id: expected pattern ^verify-[a-z0-9][a-z0-9-]*$")
    nonempty_string(plan.get("feature"), "root.feature", errors)
    nonempty_string(plan.get("objective"), "root.objective", errors)

    scope = plan.get("scope")
    if not isinstance(scope, list) or not scope:
        errors.append("root.scope: expected non-empty array")
    else:
        for index, value in enumerate(scope):
            nonempty_string(value, f"root.scope[{index}]", errors)
        if len({json.dumps(item, sort_keys=True) for item in scope}) != len(scope):
            errors.append("root.scope: duplicate items")

    criteria = plan.get("acceptance_criteria")
    criterion_ids: list[str] = []
    if not isinstance(criteria, list) or not criteria:
        errors.append("root.acceptance_criteria: expected non-empty array")
    else:
        for index, criterion in enumerate(criteria):
            where = f"root.acceptance_criteria[{index}]"
            if not check_exact_fields(criterion, CRITERION_FIELDS, where, errors):
                continue
            assert isinstance(criterion, dict)
            criterion_id = criterion.get("id")
            if not isinstance(criterion_id, str) or not AC_ID_RE.fullmatch(criterion_id):
                errors.append(f"{where}.id: expected pattern ^AC-[0-9]{{3}}$")
            else:
                criterion_ids.append(criterion_id)
            nonempty_string(criterion.get("statement"), f"{where}.statement", errors)
        duplicates = sorted({item for item in criterion_ids if criterion_ids.count(item) > 1})
        if duplicates:
            errors.append(f"root.acceptance_criteria: duplicate IDs {duplicates}")

    scenarios = plan.get("scenarios")
    scenario_ids: list[str] = []
    referenced_criteria: list[str] = []
    latest_result_time: datetime | None = None
    if not isinstance(scenarios, list) or not scenarios:
        errors.append("root.scenarios: expected non-empty array")
    else:
        for scenario_index, scenario in enumerate(scenarios):
            where = f"root.scenarios[{scenario_index}]"
            if not check_exact_fields(scenario, SCENARIO_FIELDS, where, errors):
                continue
            assert isinstance(scenario, dict)
            scenario_id = scenario.get("id")
            if not isinstance(scenario_id, str) or not FV_ID_RE.fullmatch(scenario_id):
                errors.append(f"{where}.id: expected pattern ^FV-[0-9]{{3}}$")
            else:
                scenario_ids.append(scenario_id)
            nonempty_string(scenario.get("title"), f"{where}.title", errors)
            nonempty_string(scenario.get("expected"), f"{where}.expected", errors)

            refs = scenario.get("criterion_ids")
            if not isinstance(refs, list) or not refs:
                errors.append(f"{where}.criterion_ids: expected non-empty array")
            else:
                for ref_index, ref in enumerate(refs):
                    if not isinstance(ref, str) or not AC_ID_RE.fullmatch(ref):
                        errors.append(
                            f"{where}.criterion_ids[{ref_index}]: expected pattern ^AC-[0-9]{{3}}$"
                        )
                    else:
                        referenced_criteria.append(ref)
                if len(set(refs)) != len(refs):
                    errors.append(f"{where}.criterion_ids: duplicate items")

            procedure = scenario.get("procedure")
            if not isinstance(procedure, list) or not procedure:
                errors.append(f"{where}.procedure: expected non-empty array")
            else:
                for procedure_index, step in enumerate(procedure):
                    nonempty_string(step, f"{where}.procedure[{procedure_index}]", errors)

            results = scenario.get("results")
            if not isinstance(results, list) or not results:
                errors.append(f"{where}.results: expected non-empty array")
                continue
            result_times: list[datetime] = []
            for result_index, result in enumerate(results):
                result_time = validate_result(
                    result, f"{where}.results[{result_index}]", errors
                )
                if result_time is not None:
                    result_times.append(result_time)
                    if latest_result_time is None or result_time > latest_result_time:
                        latest_result_time = result_time
            first = results[0]
            if isinstance(first, dict) and first.get("status") != "planned":
                errors.append(f"{where}.results: first result must be 'planned'")
            if any(later < earlier for earlier, later in zip(result_times, result_times[1:])):
                errors.append(f"{where}.results: timestamps are out of order")

        duplicate_scenarios = sorted(
            {item for item in scenario_ids if scenario_ids.count(item) > 1}
        )
        if duplicate_scenarios:
            errors.append(f"root.scenarios: duplicate IDs {duplicate_scenarios}")

    known_criteria = set(criterion_ids)
    unknown_refs = sorted(set(referenced_criteria) - known_criteria)
    if unknown_refs:
        errors.append(f"root.scenarios: orphan criterion references {unknown_refs}")
    uncovered = sorted(known_criteria - set(referenced_criteria))
    if uncovered:
        errors.append(f"root.acceptance_criteria: uncovered IDs {uncovered}")

    created_at = parse_timestamp(plan.get("created_at"), "root.created_at", errors)
    updated_at = parse_timestamp(plan.get("updated_at"), "root.updated_at", errors)
    if created_at is not None and updated_at is not None and updated_at < created_at:
        errors.append("root.updated_at: predates created_at")
    if updated_at is not None and latest_result_time is not None and updated_at < latest_result_time:
        errors.append("root.updated_at: predates latest recorded result")
    return errors


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
    ) as handle:
        temp_path = Path(handle.name)
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp_path, path)


def write_validated_plan(path: Path, plan: dict) -> None:
    errors = validate_plan(plan)
    if errors:
        raise RuntimeError("refusing initial write: " + "; ".join(errors))
    atomic_write(path, canonical_bytes(plan))


def append_result(
    path: Path,
    scenario_id: str,
    result: dict,
    expected_sha256: str,
) -> dict:
    before = path.read_bytes()
    before_hash = sha256_bytes(before)
    if before_hash != expected_sha256:
        return {
            "accepted": False,
            "wrote": False,
            "phase": "precondition",
            "errors": [
                f"stale precondition: expected {expected_sha256}, observed {before_hash}"
            ],
            "before_sha256": before_hash,
            "after_sha256": sha256_bytes(path.read_bytes()),
        }

    try:
        current = json.loads(before)
    except json.JSONDecodeError as exc:
        return {
            "accepted": False,
            "wrote": False,
            "phase": "current-parse",
            "errors": [str(exc)],
            "before_sha256": before_hash,
            "after_sha256": sha256_bytes(path.read_bytes()),
        }

    current_errors = validate_plan(current)
    if current_errors:
        return {
            "accepted": False,
            "wrote": False,
            "phase": "current-validation",
            "errors": current_errors,
            "before_sha256": before_hash,
            "after_sha256": sha256_bytes(path.read_bytes()),
        }

    candidate = copy.deepcopy(current)
    matching = [scenario for scenario in candidate["scenarios"] if scenario["id"] == scenario_id]
    if len(matching) != 1:
        return {
            "accepted": False,
            "wrote": False,
            "phase": "scenario-resolution",
            "errors": [f"scenario {scenario_id!r} resolved {len(matching)} times"],
            "before_sha256": before_hash,
            "after_sha256": sha256_bytes(path.read_bytes()),
        }
    prior_results = copy.deepcopy(matching[0]["results"])
    matching[0]["results"].append(copy.deepcopy(result))
    candidate["updated_at"] = result["recorded_at"]
    candidate_errors = validate_plan(candidate)
    if matching[0]["results"][:-1] != prior_results:
        candidate_errors.append("append-only violation: prior result history changed")
    if candidate_errors:
        return {
            "accepted": False,
            "wrote": False,
            "phase": "candidate-validation",
            "errors": candidate_errors,
            "before_sha256": before_hash,
            "after_sha256": sha256_bytes(path.read_bytes()),
        }

    atomic_write(path, canonical_bytes(candidate))
    after = path.read_bytes()
    reread_errors = validate_plan(json.loads(after))
    return {
        "accepted": not reread_errors,
        "wrote": True,
        "phase": "atomic-write-and-reread",
        "errors": reread_errors,
        "before_sha256": before_hash,
        "after_sha256": sha256_bytes(after),
    }


def latest_statuses(plan: dict) -> dict[str, str]:
    return {
        scenario["id"]: scenario["results"][-1]["status"]
        for scenario in plan["scenarios"]
    }


def derive_outcome(plan: dict) -> dict:
    errors = validate_plan(plan)
    if errors:
        return {
            "outcome": "INCOMPLETE",
            "failure_present": False,
            "incomplete_present": True,
            "errors": errors,
        }
    latest = {
        scenario["id"]: scenario["results"][-1]["status"]
        for scenario in plan["scenarios"]
    }
    criteria_with_pass = {
        criterion_id
        for scenario in plan["scenarios"]
        if scenario["results"][-1]["status"] == "passed"
        for criterion_id in scenario["criterion_ids"]
    }
    all_criteria = {criterion["id"] for criterion in plan["acceptance_criteria"]}
    failure = "failed" in latest.values()
    incomplete = (
        any(status in {"planned", "not-run"} for status in latest.values())
        or criteria_with_pass != all_criteria
    )
    if failure:
        outcome = "FAILED"
    elif all(status == "not-applicable" for status in latest.values()):
        outcome = "NO APPLICABLE SCENARIOS"
    elif incomplete:
        outcome = "INCOMPLETE"
    else:
        outcome = "VERIFIED"
    return {
        "outcome": outcome,
        "failure_present": failure,
        "incomplete_present": incomplete,
        "latest_statuses": latest,
        "criteria_with_latest_pass": sorted(criteria_with_pass),
        "criteria_without_latest_pass": sorted(all_criteria - criteria_with_pass),
    }


def exact_file_state(path: Path) -> dict[str, object]:
    if not path.exists():
        return {
            "exists": False,
            "bytes_utf8": None,
            "bytes_hex": None,
            "sha256": None,
        }
    payload = path.read_bytes()
    return {
        "exists": True,
        "bytes_utf8": payload.decode("utf-8"),
        "bytes_hex": payload.hex(),
        "sha256": sha256_bytes(payload),
    }


def run_sample(work_root: Path, *arguments: str) -> dict[str, object]:
    state_path = work_root / "preference.json"
    before = exact_file_state(state_path)
    command = [sys.executable, "sample_preference.py", "--state", "preference.json", *arguments]
    completed = subprocess.run(
        command,
        cwd=work_root,
        check=False,
        capture_output=True,
        text=True,
    )
    after = exact_file_state(state_path)
    return {
        "command": "${PYTHON} sample_preference.py --state preference.json "
        + " ".join(arguments),
        "cwd": "${DISPOSABLE_ROOT}",
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "state_before": before,
        "state_after": after,
    }


def command_evidence(
    timestamp: str,
    outcome: str,
    execution: dict[str, object],
    interpretation: str,
) -> dict:
    return evidence(
        timestamp,
        outcome,
        str(execution["command"]),
        json.dumps(
            {
                "cwd": execution["cwd"],
                "exit_code": execution["exit_code"],
                "stdout": execution["stdout"],
                "stderr": execution["stderr"],
                "state_before": execution["state_before"],
                "state_after": execution["state_after"],
                "interpretation": interpretation,
            },
            sort_keys=True,
            separators=(",", ":"),
        ),
    )


def planned(timestamp: str) -> dict:
    return {
        "status": "planned",
        "recorded_at": timestamp,
        "reason": None,
        "evidence": [],
    }


def evidence(timestamp: str, outcome: str, source: str, observed: str) -> dict:
    return {
        "kind": "command",
        "source": source,
        "observed": observed,
        "outcome": outcome,
        "captured_at": timestamp,
    }


def result(status: str, timestamp: str, reason: str | None, evidence_items: list[dict]) -> dict:
    return {
        "status": status,
        "recorded_at": timestamp,
        "reason": reason,
        "evidence": evidence_items,
    }


def make_initial_plan() -> dict:
    timestamp = "2026-07-24T12:00:00Z"
    return {
        "schema_version": 1,
        "plan_id": "verify-local-preference",
        "feature": "Disposable local preference storage",
        "objective": (
            "Verify that a valid display preference can be saved and read, invalid input is "
            "rejected without overwriting prior state, and persistence behavior is explicitly tracked."
        ),
        "scope": [
            "disposable local JSON state under the UC-39 fixture",
            "display preference values light and dark",
            "local read, validation, and persistence observations only",
        ],
        "acceptance_criteria": [
            {
                "id": "AC-001",
                "statement": "A valid display preference can be saved and read back unchanged.",
            },
            {
                "id": "AC-002",
                "statement": (
                    "An invalid display preference is rejected with exit code 1 and does not replace "
                    "the last valid value."
                ),
            },
            {
                "id": "AC-003",
                "statement": (
                    "The last valid display preference remains available to a later local reader."
                ),
            },
        ],
        "scenarios": [
            {
                "id": "FV-001",
                "title": "Valid preference succeeds",
                "criterion_ids": ["AC-001"],
                "procedure": [
                    "Run the sample feature in a disposable directory to set dark.",
                    "Run a separate sample-feature process to read the value back.",
                    "Capture both command results and the exact persisted bytes.",
                ],
                "expected": "The read value is dark.",
                "results": [planned(timestamp)],
            },
            {
                "id": "FV-002",
                "title": "Invalid preference is rejected",
                "criterion_ids": ["AC-002"],
                "procedure": [
                    "Start with the persisted valid value dark.",
                    "Run the sample feature with the invalid value ultraviolet.",
                    "Capture the exit code, streams, and state hashes before and after.",
                ],
                "expected": (
                    "The invalid value exits 1, emits an invalid-preference diagnostic, and leaves "
                    "the stored value dark."
                ),
                "results": [planned(timestamp)],
            },
            {
                "id": "FV-003",
                "title": "Preference persists for a later reader",
                "criterion_ids": ["AC-003"],
                "procedure": [
                    "Stop the fixture and retain its state file.",
                    "Restart the fixture in a later execution and read the saved preference.",
                ],
                "expected": "The restarted fixture loads the last valid value.",
                "results": [planned(timestamp)],
            },
            {
                "id": "FV-004",
                "title": "Platform keychain persistence",
                "criterion_ids": ["AC-003"],
                "procedure": [
                    "Attempt to load the preference through an operating-system keychain.",
                ],
                "expected": "The keychain exposes the last valid preference.",
                "results": [planned(timestamp)],
            },
        ],
        "created_at": timestamp,
        "updated_at": timestamp,
    }


def record_invalid_case(
    report: dict,
    name: str,
    path: Path,
    plan: dict,
    proposed_result: dict,
    scenario_id: str = "FV-001",
) -> None:
    atomic_write(path, canonical_bytes(plan))
    before = path.read_bytes()
    attempt = append_result(path, scenario_id, proposed_result, sha256_bytes(before))
    after = path.read_bytes()
    report["invalid_cases"][name] = {
        "manual_validation_errors_before_update": validate_plan(plan),
        "update_attempt": attempt,
        "zero_write_on_rejection": before == after and attempt["wrote"] is False,
    }


def main() -> None:
    report: dict[str, object] = {
        "schema_validation": {
            "mechanism": "explicit-manual-checker",
            "draft_2020_12_library_available": False,
            "limitation": (
                "No installed jsonschema, AJV, json_schemer, or json-schema runtime was available; "
                "the fixture explicitly checks the bundled schema's closed fields, types, constants, "
                "patterns, enums, cardinality, uniqueItems, timestamp shape, result variants, and "
                "all documented cross-record semantics."
            ),
            "schema_source": (
                "plugins/ultracode/skills/ultracode/references/"
                "feature-verification-plan.schema.json"
            ),
        },
        "sample_feature": {
            "source": "evaluation-results/0.6.0/uc39/sample_preference.py",
            "dependency_free": True,
            "interface": {
                "set_valid": (
                    "${PYTHON} sample_preference.py --state preference.json set dark"
                ),
                "set_invalid": (
                    "${PYTHON} sample_preference.py --state preference.json set ultraviolet"
                ),
                "read": "${PYTHON} sample_preference.py --state preference.json read",
            },
        },
        "sample_feature_execution": {},
        "valid_appends": {},
        "invalid_cases": {},
    }
    schema_document = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    report["schema_validation"]["schema_declared_draft"] = schema_document.get("$schema")

    initial_plan = make_initial_plan()
    initial_errors = validate_plan(initial_plan)
    report["initial_plan_manual_validation_errors"] = initial_errors
    preview = json.dumps(initial_plan, indent=2, ensure_ascii=False)
    print("EXACT_INITIAL_PLAN_PREVIEW_BEFORE_WRITE")
    print(preview)
    print("END_EXACT_INITIAL_PLAN_PREVIEW_BEFORE_WRITE")
    atomic_write(ARTIFACT_ROOT / "initial-plan-preview.json", canonical_bytes(initial_plan))

    with tempfile.TemporaryDirectory(prefix="uc39-forward-") as disposable:
        work_root = Path(disposable)
        shutil.copyfile(SAMPLE_PROGRAM, work_root / "sample_preference.py")
        plan_path = work_root / ".ultracode" / "verification" / "local-preference.json"
        write_validated_plan(plan_path, initial_plan)

        set_valid = run_sample(work_root, "set", "dark")
        read_back = run_sample(work_root, "read")
        set_invalid = run_sample(work_root, "set", "ultraviolet")
        report["sample_feature_execution"] = {
            "set_valid": set_valid,
            "read_back_separate_process": read_back,
            "set_invalid": set_invalid,
            "persisted_bytes_after_invalid": exact_file_state(
                work_root / "preference.json"
            ),
        }

        direct_results = [
            (
                "passed",
                "FV-001",
                result(
                    "passed",
                    "2026-07-24T12:00:10Z",
                    None,
                    [
                        command_evidence(
                            "2026-07-24T12:00:10Z",
                            "supports",
                            set_valid,
                            (
                                "The command exited 0, reported saved dark, and persisted the exact "
                                "UTF-8 bytes shown in state_after."
                            ),
                        ),
                        command_evidence(
                            "2026-07-24T12:00:10Z",
                            "supports",
                            read_back,
                            (
                                "A separate subprocess exited 0 and read dark from the persisted "
                                "state bytes without changing them."
                            ),
                        ),
                    ],
                ),
            ),
            (
                "failed",
                "FV-002",
                result(
                    "failed",
                    "2026-07-24T12:00:20Z",
                    None,
                    [
                        command_evidence(
                            "2026-07-24T12:00:20Z",
                            "contradicts",
                            set_invalid,
                            (
                                "The invalid value was rejected and the before/after state hashes "
                                "match, but the observed exit code was 2 while the criterion "
                                "requires exit code 1."
                            ),
                        )
                    ],
                ),
            ),
            (
                "not-run",
                "FV-003",
                result(
                    "not-run",
                    "2026-07-24T12:00:30Z",
                    (
                        "A stop-and-later-restart lifecycle was intentionally not executed; the "
                        "separate immediate readback is already retained under FV-001."
                    ),
                    [],
                ),
            ),
            (
                "not-applicable",
                "FV-004",
                result(
                    "not-applicable",
                    "2026-07-24T12:00:40Z",
                    (
                        "Operating-system keychain integration is outside the dependency-free "
                        "disposable JSON sample feature."
                    ),
                    [],
                ),
            ),
        ]
        for label, scenario_id, appended in direct_results:
            before = plan_path.read_bytes()
            outcome = append_result(plan_path, scenario_id, appended, sha256_bytes(before))
            after_plan = json.loads(plan_path.read_text(encoding="utf-8"))
            scenario = next(
                item for item in after_plan["scenarios"] if item["id"] == scenario_id
            )
            report["valid_appends"][label] = {
                "scenario_id": scenario_id,
                "proposed_result": appended,
                "attempt": outcome,
                "history_statuses": [item["status"] for item in scenario["results"]],
                "prior_history_preserved": scenario["results"][0]["status"] == "planned",
            }

        final_plan = json.loads(plan_path.read_text(encoding="utf-8"))
        report["final_plan_validation_errors"] = validate_plan(final_plan)
        report["final_latest_statuses"] = latest_statuses(final_plan)
        report["derived_feature_outcome"] = derive_outcome(final_plan)
        atomic_write(ARTIFACT_ROOT / "final-plan.json", canonical_bytes(final_plan))

    invalid_root = ARTIFACT_ROOT / "invalid"
    invalid_root.mkdir(parents=True, exist_ok=True)
    benign_not_run = result(
        "not-run",
        "2026-07-24T12:00:50Z",
        "Blocked by the deliberately malformed retained plan.",
        [],
    )

    prospective_cases = [
        ("unknown_status", result("success", "2026-07-24T12:00:50Z", None, [])),
        (
            "passed_without_evidence",
            result("passed", "2026-07-24T12:00:50Z", None, []),
        ),
        (
            "not_run_with_evidence",
            result(
                "not-run",
                "2026-07-24T12:00:50Z",
                "Deliberately malformed.",
                [
                    evidence(
                        "2026-07-24T12:00:50Z",
                        "supports",
                        "${PYTHON} invalid-case",
                        "Execution evidence must not accompany not-run.",
                    )
                ],
            ),
        ),
        (
            "contradictory_outcome",
            result(
                "passed",
                "2026-07-24T12:00:50Z",
                None,
                [
                    evidence(
                        "2026-07-24T12:00:50Z",
                        "contradicts",
                        "${PYTHON} invalid-case",
                        "A passed result cannot contain contradicting evidence.",
                    )
                ],
            ),
        ),
    ]
    for name, invalid_result in prospective_cases:
        candidate_path = invalid_root / f"{name}.json"
        write_validated_plan(candidate_path, initial_plan)
        before = candidate_path.read_bytes()
        attempt = append_result(
            candidate_path,
            "FV-001",
            invalid_result,
            sha256_bytes(before),
        )
        after = candidate_path.read_bytes()
        report["invalid_cases"][name] = {
            "proposed_result": invalid_result,
            "update_attempt": attempt,
            "retained_fixture_sha256": sha256_bytes(after),
            "zero_write_on_rejection": before == after and attempt["wrote"] is False,
        }

    duplicate_orphan = copy.deepcopy(initial_plan)
    duplicate_orphan["acceptance_criteria"].append(
        copy.deepcopy(duplicate_orphan["acceptance_criteria"][0])
    )
    duplicate_orphan["scenarios"].append(copy.deepcopy(duplicate_orphan["scenarios"][0]))
    duplicate_orphan["scenarios"][0]["criterion_ids"].append("AC-999")
    record_invalid_case(
        report,
        "duplicate_and_orphan_ids",
        invalid_root / "duplicate-and-orphan-ids.json",
        duplicate_orphan,
        benign_not_run,
    )

    missing_reference = copy.deepcopy(initial_plan)
    missing_reference["scenarios"][0]["criterion_ids"] = ["AC-999"]
    record_invalid_case(
        report,
        "missing_criterion_reference",
        invalid_root / "missing-criterion-reference.json",
        missing_reference,
        benign_not_run,
    )

    missing_field = copy.deepcopy(initial_plan)
    del missing_field["objective"]
    record_invalid_case(
        report,
        "missing_required_field",
        invalid_root / "missing-required-field.json",
        missing_field,
        benign_not_run,
    )

    wrong_initial = copy.deepcopy(initial_plan)
    wrong_initial["scenarios"][0]["results"] = [
        result(
            "passed",
            "2026-07-24T12:00:00Z",
            None,
            [
                evidence(
                    "2026-07-24T12:00:00Z",
                    "supports",
                    "${PYTHON} invalid-case",
                    "History deliberately begins with passed.",
                )
            ],
        )
    ]
    record_invalid_case(
        report,
        "wrong_initial_state",
        invalid_root / "wrong-initial-state.json",
        wrong_initial,
        benign_not_run,
    )

    out_of_order = copy.deepcopy(initial_plan)
    out_of_order["scenarios"][0]["results"].extend(
        [
            result(
                "passed",
                "2026-07-24T12:00:20Z",
                None,
                [
                    evidence(
                        "2026-07-24T12:00:20Z",
                        "supports",
                        "${PYTHON} invalid-case",
                        "First append at 12:00:20.",
                    )
                ],
            ),
            result(
                "failed",
                "2026-07-24T12:00:10Z",
                None,
                [
                    evidence(
                        "2026-07-24T12:00:10Z",
                        "contradicts",
                        "${PYTHON} invalid-case",
                        "Second append has an earlier timestamp.",
                    )
                ],
            ),
        ]
    )
    out_of_order["updated_at"] = "2026-07-24T12:00:20Z"
    record_invalid_case(
        report,
        "out_of_order_history",
        invalid_root / "out-of-order-history.json",
        out_of_order,
        benign_not_run,
    )

    malformed_path = invalid_root / "malformed-json.json"
    malformed_bytes = b'{"schema_version":1,"plan_id":'
    atomic_write(malformed_path, malformed_bytes)
    malformed_before = malformed_path.read_bytes()
    malformed_attempt = append_result(
        malformed_path,
        "FV-001",
        benign_not_run,
        sha256_bytes(malformed_before),
    )
    malformed_after = malformed_path.read_bytes()
    report["invalid_cases"]["malformed_json"] = {
        "update_attempt": malformed_attempt,
        "retained_fixture_sha256": sha256_bytes(malformed_after),
        "zero_write_on_rejection": (
            malformed_before == malformed_after and malformed_attempt["wrote"] is False
        ),
    }

    stale_path = invalid_root / "stale-concurrent-update.json"
    write_validated_plan(stale_path, initial_plan)
    inspected_hash = sha256_bytes(stale_path.read_bytes())
    concurrent_plan = copy.deepcopy(initial_plan)
    concurrent_plan["objective"] += " Concurrent editor marker."
    atomic_write(stale_path, canonical_bytes(concurrent_plan))
    immediately_before_attempt = stale_path.read_bytes()
    stale_attempt = append_result(
        stale_path,
        "FV-001",
        benign_not_run,
        inspected_hash,
    )
    immediately_after_attempt = stale_path.read_bytes()
    report["invalid_cases"]["stale_concurrent_update_precondition"] = {
        "inspected_sha256": inspected_hash,
        "concurrent_sha256": sha256_bytes(immediately_before_attempt),
        "update_attempt": stale_attempt,
        "retained_fixture_sha256": sha256_bytes(immediately_after_attempt),
        "zero_write_on_conflict": (
            immediately_before_attempt == immediately_after_attempt
            and stale_attempt["wrote"] is False
        ),
    }

    for item in report["invalid_cases"].values():
        if "retained_fixture_sha256" not in item:
            attempt = item["update_attempt"]
            item["retained_fixture_sha256"] = attempt["after_sha256"]
    report["all_valid_appends_accepted"] = all(
        item["attempt"]["accepted"] and item["attempt"]["wrote"]
        for item in report["valid_appends"].values()
    )
    report["all_invalid_cases_zero_write"] = all(
        item.get("zero_write_on_rejection", item.get("zero_write_on_conflict", False))
        for item in report["invalid_cases"].values()
    )
    report["overall_verdict"] = (
        "CONFIRMED"
        if (
            not report["initial_plan_manual_validation_errors"]
            and not report["final_plan_validation_errors"]
            and report["all_valid_appends_accepted"]
            and report["all_invalid_cases_zero_write"]
            and report["sample_feature_execution"]["set_valid"]["exit_code"] == 0
            and report["sample_feature_execution"]["read_back_separate_process"]["exit_code"]
            == 0
            and report["sample_feature_execution"]["set_invalid"]["exit_code"] == 2
            and (
                report["sample_feature_execution"]["set_invalid"]["state_before"]["sha256"]
                == report["sample_feature_execution"]["set_invalid"]["state_after"]["sha256"]
            )
        )
        else "REFUTED"
    )
    atomic_write(ARTIFACT_ROOT / "run-report.json", canonical_bytes(report))
    print("RAW_RUN_SUMMARY")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
