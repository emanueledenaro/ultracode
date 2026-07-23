#!/usr/bin/env python3
"""Integration corpus for the deterministic UltraCode project configurator."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


CONFIGURATOR = Path(__file__).with_name("project_configurator.py")
DOCTOR = Path(__file__).with_name("project_doctor.py")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def snapshot(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def snapshot_with_mtime(root: Path) -> dict[str, tuple[str, int]]:
    return {
        path.relative_to(root).as_posix(): (
            hashlib.sha256(path.read_bytes()).hexdigest(),
            path.stat().st_mtime_ns,
        )
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def base_config() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "project": {
            "name": "configurator-corpus",
            "mission": "Exercise deterministic project configuration.",
            "root": ".",
            "stack": ["fixture"],
            "targets": ["project configurator"],
            "non_goals": ["production"],
        },
        "control": {
            "plan_gate": "confirm-before-write",
            "updates": "phase-and-barrier",
            "detail": "compact",
            "show_agent_jobs": True,
            "show_files": True,
            "show_validation": True,
            "persistent_status": "conversation-only",
            "status_path": ".ultracode/status.md",
        },
        "authority": {
            "git": "explicit-only",
            "external": "explicit-only",
            "destructive": "explicit-only",
            "dependencies": "explicit-only",
            "deployment": "explicit-only",
            "status_writes": "change-tasks-only",
        },
        "swarm": {
            "decomposition": "data-driven",
            "orthogonal_lenses": "as-needed",
            "verification": "one-per-material-finding",
            "synthesis_agents": 1,
            "concurrency": "auto",
            "hard_safety_cap": 1000,
            "model_policy": {
                "lead": "gpt-5.6-sol",
                "bounded_agents": "gpt-5.6-terra",
                "verifiers": "gpt-5.6-sol",
                "fallback": "inherit",
            },
            "reasoning_policy": {
                "mode": "objective-driven",
                "bounded_default": "low",
                "material_verifier_minimum": "high",
                "critical_minimum": "xhigh",
                "maximum": "ultra",
            },
        },
        "adapters": {"codex": True, "claude": False},
        "artifacts": {
            "context": [".agents/context/project.md"],
            "rules": [],
            "rule_paths": {},
            "skills": [],
        },
        "commands": {
            key: []
            for key in ("install", "format", "lint", "typecheck", "test", "build", "run", "health")
        },
        "completion": {
            "required_checks": ["project doctor"],
            "real_path": "Run the project doctor.",
            "review": "independent-for-material-change",
        },
        "roles": [],
    }


def base_proposal() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "config": base_config(),
        "canonical_files": {
            ".agents/context/project.md": "# Project\n\nCanonical fixture context.\n"
        },
    }


def run_configurator(*args: str) -> tuple[int, dict[str, Any], str]:
    command = subprocess.run(
        [sys.executable, str(CONFIGURATOR), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        payload = json.loads(command.stdout)
    except json.JSONDecodeError:
        payload = {}
    return command.returncode, payload, command.stderr.strip()


def case_plan_is_read_only(base: Path) -> None:
    root = base / "project"
    root.mkdir(parents=True)
    (root / "AGENTS.md").write_text("# Existing guidance\n", encoding="utf-8")
    proposal_path = base / "proposal.json"
    write_json(proposal_path, base_proposal())
    before = snapshot_with_mtime(root)
    exit_code, payload, stderr = run_configurator(
        "plan",
        "--project-root",
        str(root),
        "--proposal",
        str(proposal_path),
    )
    after = snapshot_with_mtime(root)
    if exit_code != 0:
        raise AssertionError(f"plan exited {exit_code}: {stderr or payload}")
    if payload.get("status") != "PLANNED" or payload.get("mode") != "init":
        raise AssertionError(f"unexpected plan result: {payload}")
    if not isinstance(payload.get("plan_id"), str) or len(payload["plan_id"]) != 64:
        raise AssertionError("plan did not return a SHA-256 plan_id")
    if before != after:
        raise AssertionError("plan modified the project")
    planned_paths = {item.get("path") for item in payload.get("changes", []) if isinstance(item, dict)}
    expected = {
        ".agents/context/project.md",
        ".ultracode/config.json",
        ".ultracode/managed.json",
        "AGENTS.md",
    }
    if planned_paths != expected:
        raise AssertionError(f"unexpected planned paths: {sorted(planned_paths)}")
    writes = payload.get("writes")
    if not isinstance(writes, list) or {item.get("path") for item in writes} != expected:
        raise AssertionError("plan did not expose every exact planned write")
    if any(
        not isinstance(item.get("content"), str)
        or not isinstance(item.get("sha256"), str)
        or len(item["sha256"]) != 64
        for item in writes
    ):
        raise AssertionError("plan writes do not expose deterministic content and SHA-256")
    deterministic_runs = [
        subprocess.run(
            [
                sys.executable,
                str(CONFIGURATOR),
                "plan",
                "--project-root",
                str(root),
                "--proposal",
                str(proposal_path),
            ],
            capture_output=True,
            check=False,
        )
        for _ in range(2)
    ]
    if any(run.returncode != 0 or run.stderr for run in deterministic_runs):
        raise AssertionError("repeated deterministic plan did not exit cleanly")
    if deterministic_runs[0].stdout != deterministic_runs[1].stdout:
        raise AssertionError("repeated plans did not produce byte-identical stdout")


def case_apply_creates_doctor_valid_init(base: Path) -> None:
    root = base / "project"
    root.mkdir(parents=True)
    proposal_path = base / "proposal.json"
    write_json(proposal_path, base_proposal())
    plan_exit, plan, stderr = run_configurator(
        "plan",
        "--project-root",
        str(root),
        "--proposal",
        str(proposal_path),
    )
    if plan_exit != 0:
        raise AssertionError(f"plan exited {plan_exit}: {stderr or plan}")
    apply_exit, applied, stderr = run_configurator(
        "apply",
        "--project-root",
        str(root),
        "--proposal",
        str(proposal_path),
        "--plan-id",
        plan["plan_id"],
    )
    if apply_exit != 0 or applied.get("status") != "APPLIED":
        raise AssertionError(f"apply failed: exit={apply_exit}, stderr={stderr!r}, payload={applied}")
    expected = {
        ".agents/context/project.md",
        ".ultracode/config.json",
        ".ultracode/managed.json",
        "AGENTS.md",
    }
    actual = set(snapshot(root))
    if actual != expected:
        raise AssertionError(f"apply wrote unexpected paths: {sorted(actual)}")
    doctor = subprocess.run(
        [sys.executable, str(DOCTOR), str(root), "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        doctor_payload = json.loads(doctor.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"doctor returned invalid JSON: {doctor.stdout!r}") from exc
    if doctor.returncode != 0 or doctor_payload.get("status") != "PASSED":
        raise AssertionError(f"doctor rejected applied project: {doctor_payload}")


def case_second_apply_is_noop(base: Path) -> None:
    root = base / "project"
    root.mkdir(parents=True)
    proposal_path = base / "proposal.json"
    write_json(proposal_path, base_proposal())
    first_exit, first_plan, stderr = run_configurator(
        "plan", "--project-root", str(root), "--proposal", str(proposal_path)
    )
    if first_exit != 0:
        raise AssertionError(f"first plan failed: {stderr or first_plan}")
    first_apply_exit, first_apply, stderr = run_configurator(
        "apply",
        "--project-root",
        str(root),
        "--proposal",
        str(proposal_path),
        "--plan-id",
        first_plan["plan_id"],
    )
    if first_apply_exit != 0 or first_apply.get("status") != "APPLIED":
        raise AssertionError(f"first apply failed: {stderr or first_apply}")
    before = snapshot_with_mtime(root)
    second_exit, second_plan, stderr = run_configurator(
        "plan", "--project-root", str(root), "--proposal", str(proposal_path)
    )
    if second_exit != 0 or second_plan.get("status") != "NO_CHANGES":
        raise AssertionError(f"second plan was not a no-op: {stderr or second_plan}")
    second_apply_exit, second_apply, stderr = run_configurator(
        "apply",
        "--project-root",
        str(root),
        "--proposal",
        str(proposal_path),
        "--plan-id",
        second_plan["plan_id"],
    )
    if second_apply_exit != 0 or second_apply.get("status") != "NO_CHANGES":
        raise AssertionError(f"second apply was not a no-op: {stderr or second_apply}")
    if before != snapshot_with_mtime(root):
        raise AssertionError("no-op apply changed project bytes or mtimes")


def case_existing_agents_content_is_preserved(base: Path) -> None:
    root = base / "project"
    root.mkdir(parents=True)
    original = b"# Existing guidance\r\n\r\nManual content stays byte exact.\r\n"
    (root / "AGENTS.md").write_bytes(original)
    proposal_path = base / "proposal.json"
    write_json(proposal_path, base_proposal())
    plan_exit, plan, stderr = run_configurator(
        "plan", "--project-root", str(root), "--proposal", str(proposal_path)
    )
    if plan_exit != 0:
        raise AssertionError(f"plan failed: {stderr or plan}")
    apply_exit, applied, stderr = run_configurator(
        "apply",
        "--project-root",
        str(root),
        "--proposal",
        str(proposal_path),
        "--plan-id",
        plan["plan_id"],
    )
    if apply_exit != 0 or applied.get("status") != "APPLIED":
        raise AssertionError(f"apply failed: {stderr or applied}")
    agents_path = root / "AGENTS.md"
    if not agents_path.read_bytes().startswith(original):
        raise AssertionError("apply changed pre-existing AGENTS.md bytes outside the managed block")
    with agents_path.open("ab") as stream:
        stream.write(b"\nUser-owned suffix.\r\n")
    before = agents_path.read_bytes()
    second_exit, second_plan, stderr = run_configurator(
        "plan", "--project-root", str(root), "--proposal", str(proposal_path)
    )
    if second_exit != 0 or second_plan.get("status") != "NO_CHANGES":
        raise AssertionError(f"outside-block edit caused managed drift: {stderr or second_plan}")
    if agents_path.read_bytes() != before:
        raise AssertionError("plan modified user-owned AGENTS.md content")

    marked_root = base / "unowned-marked-project"
    marked_root.mkdir()
    marked_agents = marked_root / "AGENTS.md"
    marked_agents.write_text(
        "# Existing\n\n"
        "<!-- ultracode:project:start -->\n"
        "USER-OWNED POLICY\n"
        "<!-- ultracode:project:end -->\n",
        encoding="utf-8",
    )
    marked_proposal = base / "unowned-marked-proposal.json"
    write_json(marked_proposal, base_proposal())
    marked_before = snapshot_with_mtime(marked_root)
    marked_exit, marked, stderr = run_configurator(
        "plan", "--project-root", str(marked_root), "--proposal", str(marked_proposal)
    )
    if marked_exit != 2 or marked.get("status") != "CONFLICT":
        raise AssertionError(
            f"unowned pre-existing managed markers were overwritten without resolution: {marked_exit}, {stderr or marked}"
        )
    if marked_before != snapshot_with_mtime(marked_root):
        raise AssertionError("unowned marker conflict modified AGENTS.md")


def case_managed_drift_conflicts_without_writes(base: Path) -> None:
    root = base / "project"
    root.mkdir(parents=True)
    proposal_path = base / "proposal.json"
    write_json(proposal_path, base_proposal())
    plan_exit, plan, stderr = run_configurator(
        "plan", "--project-root", str(root), "--proposal", str(proposal_path)
    )
    if plan_exit != 0:
        raise AssertionError(f"initial plan failed: {stderr or plan}")
    apply_exit, applied, stderr = run_configurator(
        "apply",
        "--project-root",
        str(root),
        "--proposal",
        str(proposal_path),
        "--plan-id",
        plan["plan_id"],
    )
    if apply_exit != 0 or applied.get("status") != "APPLIED":
        raise AssertionError(f"initial apply failed: {stderr or applied}")
    context_path = root / ".agents" / "context" / "project.md"
    context_path.write_text("# User edit\n", encoding="utf-8")
    before = snapshot_with_mtime(root)
    drift_exit, drift, stderr = run_configurator(
        "plan", "--project-root", str(root), "--proposal", str(proposal_path)
    )
    if drift_exit != 2 or drift.get("status") != "CONFLICT":
        raise AssertionError(f"managed drift was not rejected: exit={drift_exit}, {stderr or drift}")
    conflicts = drift.get("conflicts")
    if not isinstance(conflicts, list) or not any(
        isinstance(item, dict)
        and item.get("path") == ".agents/context/project.md"
        and item.get("kind") == "managed-drift"
        for item in conflicts
    ):
        raise AssertionError(f"managed drift conflict was not structured: {drift}")
    if before != snapshot_with_mtime(root):
        raise AssertionError("drift detection modified project bytes or mtimes")

    concurrent_root = base / "concurrent-project"
    concurrent_root.mkdir(parents=True)
    concurrent_proposal = base / "concurrent-proposal.json"
    write_json(concurrent_proposal, base_proposal())
    init_exit, init_plan, stderr = run_configurator(
        "plan", "--project-root", str(concurrent_root), "--proposal", str(concurrent_proposal)
    )
    if init_exit != 0:
        raise AssertionError(f"concurrent fixture plan failed: {stderr or init_plan}")
    init_apply_exit, init_applied, stderr = run_configurator(
        "apply",
        "--project-root",
        str(concurrent_root),
        "--proposal",
        str(concurrent_proposal),
        "--plan-id",
        init_plan["plan_id"],
    )
    if init_apply_exit != 0 or init_applied.get("status") != "APPLIED":
        raise AssertionError(f"concurrent fixture apply failed: {stderr or init_applied}")
    edit_exit, edit_plan, stderr = run_configurator(
        "plan", "--project-root", str(concurrent_root), "--proposal", str(concurrent_proposal)
    )
    if edit_exit != 0:
        raise AssertionError(f"edit plan failed: {stderr or edit_plan}")
    concurrent_context = concurrent_root / ".agents" / "context" / "project.md"
    concurrent_context.write_text("# Concurrent change\n", encoding="utf-8")
    concurrent_before = snapshot_with_mtime(concurrent_root)
    conflict_exit, conflict, stderr = run_configurator(
        "apply",
        "--project-root",
        str(concurrent_root),
        "--proposal",
        str(concurrent_proposal),
        "--plan-id",
        edit_plan["plan_id"],
    )
    if conflict_exit != 2 or conflict.get("status") != "CONFLICT":
        raise AssertionError(f"post-plan drift was not rejected: exit={conflict_exit}, {stderr or conflict}")
    if concurrent_before != snapshot_with_mtime(concurrent_root):
        raise AssertionError("post-plan drift conflict modified project bytes or mtimes")

    unmanaged_root = base / "unmanaged-project"
    unmanaged_context = unmanaged_root / ".agents" / "context" / "project.md"
    unmanaged_context.parent.mkdir(parents=True)
    unmanaged_context.write_bytes(b"user-owned canonical-looking file\n")
    unmanaged_proposal = base / "unmanaged-proposal.json"
    write_json(unmanaged_proposal, base_proposal())
    unmanaged_before = snapshot_with_mtime(unmanaged_root)
    unmanaged_exit, unmanaged, stderr = run_configurator(
        "plan", "--project-root", str(unmanaged_root), "--proposal", str(unmanaged_proposal)
    )
    if unmanaged_exit != 2 or unmanaged.get("status") != "CONFLICT":
        raise AssertionError(
            f"unmanaged whole-file collision was not rejected: exit={unmanaged_exit}, {stderr or unmanaged}"
        )
    if unmanaged_before != snapshot_with_mtime(unmanaged_root):
        raise AssertionError("unmanaged collision handling modified project bytes or mtimes")


def create_directory_link(link: Path, target: Path) -> None:
    try:
        link.symlink_to(target, target_is_directory=True)
        return
    except OSError as symlink_error:
        if os.name != "nt":
            raise AssertionError(f"directory symlink is unavailable: {symlink_error}") from symlink_error
    command = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(link), str(target)],
        capture_output=True,
        text=True,
        check=False,
    )
    if command.returncode != 0:
        raise AssertionError(
            f"directory symlink/junction is unavailable: {command.stderr or command.stdout}"
        )


def case_project_root_under_linked_ancestor_is_accepted(base: Path) -> None:
    canonical_base = base / "canonical-base"
    root = canonical_base / "project"
    root.mkdir(parents=True)
    alias = base / "base-alias"
    create_directory_link(alias, canonical_base)
    proposal_path = base / "linked-ancestor-proposal.json"
    write_json(proposal_path, base_proposal())

    exit_code, result, stderr = run_configurator(
        "plan", "--project-root", str(alias / "project"), "--proposal", str(proposal_path)
    )
    if exit_code != 0 or result.get("status") != "PLANNED":
        raise AssertionError(
            "project root under a linked ancestor was rejected: " f"{stderr or result}"
        )
    apply_exit, applied, stderr = run_configurator(
        "apply",
        "--project-root",
        str(alias / "project"),
        "--proposal",
        str(proposal_path),
        "--plan-id",
        result["plan_id"],
    )
    if apply_exit != 0 or applied.get("status") != "APPLIED":
        raise AssertionError(
            "linked-ancestor project could not be initialized: " f"{stderr or applied}"
        )
    doctor = subprocess.run(
        [sys.executable, str(DOCTOR), str(alias / "project"), "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        report = json.loads(doctor.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(
            f"doctor returned invalid JSON through a linked ancestor: {doctor.stdout!r}"
        ) from exc
    if doctor.returncode != 0 or report.get("status") != "PASSED":
        raise AssertionError(
            "doctor rejected a project under a linked ancestor: " f"{stderr or report}"
        )
    if os.name == "nt":
        powershell_doctor = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(DOCTOR.with_suffix(".ps1")),
                "-ProjectRoot",
                str(alias / "project"),
                "-Json",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        try:
            powershell_report = json.loads(powershell_doctor.stdout)
        except json.JSONDecodeError as exc:
            raise AssertionError(
                "PowerShell doctor returned invalid JSON through a linked ancestor: "
                f"{powershell_doctor.stdout!r}"
            ) from exc
        if powershell_doctor.returncode != 0 or powershell_report.get("status") != "PASSED":
            raise AssertionError(
                "PowerShell doctor rejected a project under a linked ancestor: "
                f"{powershell_doctor.stderr or powershell_report}"
            )


def case_unsafe_paths_and_reparse_are_rejected(base: Path) -> None:
    unsafe_root = base / "unsafe-project"
    unsafe_root.mkdir(parents=True)
    unsafe_proposal = base_proposal()
    unsafe_proposal["config"]["artifacts"]["context"] = ["../escape.md"]
    unsafe_proposal["canonical_files"] = {"../escape.md": "escape\n"}
    unsafe_proposal_path = base / "unsafe-proposal.json"
    write_json(unsafe_proposal_path, unsafe_proposal)
    before = snapshot_with_mtime(base)
    unsafe_exit, unsafe, stderr = run_configurator(
        "plan", "--project-root", str(unsafe_root), "--proposal", str(unsafe_proposal_path)
    )
    if unsafe_exit != 1 or unsafe.get("status") != "FAILED":
        raise AssertionError(f"unsafe path was not rejected: exit={unsafe_exit}, {stderr or unsafe}")
    if before != snapshot_with_mtime(base):
        raise AssertionError("unsafe path validation modified the fixture")

    invalid_root = base / "invalid-config-project"
    invalid_root.mkdir()
    invalid_proposal = base_proposal()
    invalid_proposal["config"]["control"]["plan_gate"] = "invalid-policy"
    invalid_proposal["config"]["swarm"]["reasoning_policy"]["maximum"] = "medium"
    invalid_proposal_path = base / "invalid-config-proposal.json"
    write_json(invalid_proposal_path, invalid_proposal)
    invalid_before = snapshot_with_mtime(invalid_root)
    invalid_exit, invalid, stderr = run_configurator(
        "plan", "--project-root", str(invalid_root), "--proposal", str(invalid_proposal_path)
    )
    if invalid_exit != 1 or invalid.get("status") != "FAILED":
        raise AssertionError(
            f"doctor-invalid desired config was not rejected before planning: {invalid_exit}, {stderr or invalid}"
        )
    if invalid_before != snapshot_with_mtime(invalid_root):
        raise AssertionError("invalid desired config modified the project")

    directory_root = base / "directory-collision-project"
    directory_target = directory_root / ".agents" / "context" / "project.md"
    directory_target.mkdir(parents=True)
    directory_proposal = base / "directory-collision-proposal.json"
    write_json(directory_proposal, base_proposal())
    directory_before = snapshot_with_mtime(directory_root)
    directory_exit, directory_result, stderr = run_configurator(
        "plan", "--project-root", str(directory_root), "--proposal", str(directory_proposal)
    )
    if directory_exit != 1 or directory_result.get("status") != "FAILED":
        raise AssertionError(
            f"existing directory at a managed file path was not rejected in plan: {directory_exit}, {stderr or directory_result}"
        )
    if directory_before != snapshot_with_mtime(directory_root):
        raise AssertionError("managed path directory collision modified the project")

    root = base / "reparse-project"
    root.mkdir(parents=True)
    proposal_path = base / "reparse-proposal.json"
    write_json(proposal_path, base_proposal())
    plan_exit, plan, stderr = run_configurator(
        "plan", "--project-root", str(root), "--proposal", str(proposal_path)
    )
    if plan_exit != 0:
        raise AssertionError(f"reparse fixture plan failed: {stderr or plan}")
    outside = base / "outside"
    outside.mkdir()
    sentinel = outside / "sentinel.txt"
    sentinel.write_bytes(b"outside stays unchanged\n")
    (root / ".agents").mkdir()
    create_directory_link(root / ".agents" / "context", outside)
    outside_before = snapshot_with_mtime(outside)
    apply_exit, applied, stderr = run_configurator(
        "apply",
        "--project-root",
        str(root),
        "--proposal",
        str(proposal_path),
        "--plan-id",
        plan["plan_id"],
    )
    if apply_exit != 1 or applied.get("status") != "FAILED":
        raise AssertionError(f"reparse traversal was not rejected: exit={apply_exit}, {stderr or applied}")
    if outside_before != snapshot_with_mtime(outside):
        raise AssertionError("reparse traversal wrote outside the project root")

    invalid_rule_paths = (
        "/srv/app/**",
        "../src/**",
        r"src\**",
        "src files/**",
        "C:/src/**",
        "~/src/**",
    )
    for index, invalid_rule_path in enumerate(invalid_rule_paths):
        rule_root = base / f"rule-path-{index}"
        rule_root.mkdir()
        rule_proposal = base_proposal()
        rule = ".agents/rules/no-deploy.md"
        rule_proposal["config"]["artifacts"]["rules"] = [rule]
        rule_proposal["config"]["artifacts"]["rule_paths"] = {rule: [invalid_rule_path]}
        rule_proposal["canonical_files"][rule] = "# No deploy\n\nNever deploy without authority.\n"
        rule_proposal_path = base / f"rule-path-{index}.json"
        write_json(rule_proposal_path, rule_proposal)
        rule_before = snapshot_with_mtime(rule_root)
        rule_exit, rule_result, stderr = run_configurator(
            "plan", "--project-root", str(rule_root), "--proposal", str(rule_proposal_path)
        )
        if rule_exit != 1 or rule_result.get("status") != "FAILED":
            raise AssertionError(
                f"non-portable rule path was not rejected: {invalid_rule_path!r}, "
                f"exit={rule_exit}, {stderr or rule_result}"
            )
        if rule_before != snapshot_with_mtime(rule_root):
            raise AssertionError(f"rule path validation modified the fixture: {invalid_rule_path!r}")

    control_root = base / "control-reparse-project"
    control_root.mkdir()
    control_proposal_path = base / "control-reparse-proposal.json"
    write_json(control_proposal_path, base_proposal())
    control_plan_exit, control_plan, stderr = run_configurator(
        "plan", "--project-root", str(control_root), "--proposal", str(control_proposal_path)
    )
    if control_plan_exit != 0:
        raise AssertionError(f"control reparse fixture plan failed: {stderr or control_plan}")
    external_control = base / "external-control"
    external_control.mkdir()
    (external_control / "config.json").write_text("{ malformed config\n", encoding="utf-8")
    (external_control / "managed.json").write_text("{ malformed manifest\n", encoding="utf-8")
    create_directory_link(control_root / ".ultracode", external_control)
    external_before = snapshot_with_mtime(external_control)
    for action in ("plan", "apply"):
        arguments = [
            action,
            "--project-root",
            str(control_root),
            "--proposal",
            str(control_proposal_path),
        ]
        if action == "apply":
            arguments.extend(["--plan-id", control_plan["plan_id"]])
        control_exit, control_result, stderr = run_configurator(*arguments)
        diagnostics = control_result.get("errors", [])
        detail = " ".join(item for item in diagnostics if isinstance(item, str))
        if (
            control_exit != 1
            or control_result.get("status") != "FAILED"
            or ".ultracode/config.json" not in detail
            or ".ultracode/managed.json" not in detail
            or "symlink, junction, or reparse point" not in detail
        ):
            raise AssertionError(
                f"{action} did not reject both reparse control files before reading: "
                f"exit={control_exit}, {stderr or control_result}"
            )
        if "cannot load" in detail or "unreadable" in detail:
            raise AssertionError(f"{action} read a reparse control-file target before rejection")
    if external_before != snapshot_with_mtime(external_control):
        raise AssertionError("control-file reparse rejection modified the external target")

    nested_claude_root = base / "nested-claude-reparse-project"
    nested_claude_root.mkdir()
    nested_claude_proposal = base_proposal()
    nested_claude_proposal["config"]["adapters"]["claude"] = True
    nested_claude_proposal_path = base / "nested-claude-reparse-proposal.json"
    write_json(nested_claude_proposal_path, nested_claude_proposal)
    external_claude = base / "external-claude"
    external_claude.mkdir()
    (external_claude / "CLAUDE.md").write_bytes(b"\xffoutside must not be decoded\n")
    create_directory_link(nested_claude_root / ".claude", external_claude)
    nested_before = snapshot_with_mtime(nested_claude_root)
    external_claude_before = snapshot_with_mtime(external_claude)
    nested_exit, nested_result, stderr = run_configurator(
        "plan",
        "--project-root",
        str(nested_claude_root),
        "--proposal",
        str(nested_claude_proposal_path),
    )
    nested_detail = " ".join(
        item for item in nested_result.get("errors", []) if isinstance(item, str)
    )
    if (
        nested_exit != 1
        or nested_result.get("status") != "FAILED"
        or ".claude/CLAUDE.md" not in nested_detail
        or "symlink, junction, or reparse point" not in nested_detail
    ):
        raise AssertionError(
            "nested Claude reparse was not rejected before decoding: "
            f"exit={nested_exit}, {stderr or nested_result}"
        )
    if nested_before != snapshot_with_mtime(nested_claude_root):
        raise AssertionError("nested Claude reparse rejection modified the project")
    if external_claude_before != snapshot_with_mtime(external_claude):
        raise AssertionError("nested Claude reparse rejection modified the external target")

    top_claude_root = base / "top-claude-reparse-project"
    top_claude_root.mkdir()
    top_claude_proposal = base_proposal()
    top_claude_proposal["config"]["adapters"]["claude"] = True
    top_claude_proposal_path = base / "top-claude-reparse-proposal.json"
    write_json(top_claude_proposal_path, top_claude_proposal)
    external_top_claude = base / "external-top-claude"
    external_top_claude.mkdir()
    create_directory_link(top_claude_root / "CLAUDE.md", external_top_claude)
    top_before = snapshot_with_mtime(top_claude_root)
    external_top_before = snapshot_with_mtime(external_top_claude)
    top_exit, top_result, stderr = run_configurator(
        "plan",
        "--project-root",
        str(top_claude_root),
        "--proposal",
        str(top_claude_proposal_path),
    )
    top_detail = " ".join(
        item for item in top_result.get("errors", []) if isinstance(item, str)
    )
    if (
        top_exit != 1
        or top_result.get("status") != "FAILED"
        or "CLAUDE.md" not in top_detail
        or "symlink, junction, or reparse point" not in top_detail
    ):
        raise AssertionError(
            "top-level Claude reparse was not rejected before selection: "
            f"exit={top_exit}, {stderr or top_result}"
        )
    if top_before != snapshot_with_mtime(top_claude_root):
        raise AssertionError("top-level Claude reparse rejection modified the project")
    if external_top_before != snapshot_with_mtime(external_top_claude):
        raise AssertionError("top-level Claude reparse rejection modified the external target")


def rich_proposal() -> dict[str, Any]:
    proposal = base_proposal()
    config = proposal["config"]
    config["adapters"]["claude"] = True
    rule = ".agents/rules/no-deploy.md"
    skill = ".agents/skills/verify-state/SKILL.md"
    config["artifacts"]["rules"] = [rule]
    config["artifacts"]["rule_paths"] = {rule: ["src/**", "scripts/*.py"]}
    config["artifacts"]["skills"] = [skill]
    config["roles"] = [
        {
            "id": "auditor",
            "purpose": 'Review "quoted" evidence without writes.',
            "mode": "read-only",
            "skills": ["verify-state"],
        },
        {
            "id": "implementer",
            "purpose": "Apply a bounded workspace change.",
            "mode": "workspace-write",
            "skills": [],
        },
    ]
    proposal["canonical_files"].update(
        {
            rule: "# No deploy\n\nNever deploy without explicit authority.\n",
            skill: (
                "---\nname: verify-state\n"
                'description: "Verify \\"quoted\\" state read-only."\n---\n'
                "# Verify state\n\nInspect evidence and report it.\n"
            ),
            ".agents/reviewers/auditor.md": "# Auditor\n\nReview evidence only.\n",
            ".agents/reviewers/implementer.md": "# Implementer\n\nApply bounded changes.\n",
        }
    )
    return proposal


def case_rich_adapters_are_generated_deterministically(base: Path) -> None:
    root = base / "project"
    root.mkdir(parents=True)
    claude_root = root / ".claude" / "CLAUDE.md"
    claude_root.parent.mkdir(parents=True)
    existing_claude = b"# Existing Claude guidance\r\n"
    claude_root.write_bytes(existing_claude)
    proposal = rich_proposal()
    proposal_path = base / "proposal.json"
    write_json(proposal_path, proposal)
    plan_exit, plan, stderr = run_configurator(
        "plan", "--project-root", str(root), "--proposal", str(proposal_path)
    )
    if plan_exit != 0:
        raise AssertionError(f"rich plan failed: {stderr or plan}")
    apply_exit, applied, stderr = run_configurator(
        "apply",
        "--project-root",
        str(root),
        "--proposal",
        str(proposal_path),
        "--plan-id",
        plan["plan_id"],
    )
    if apply_exit != 0 or applied.get("status") != "APPLIED":
        raise AssertionError(f"rich apply failed: {stderr or applied}")
    expected_projection_paths = {
        ".claude/CLAUDE.md",
        ".claude/rules/no-deploy.md",
        ".claude/skills/verify-state/SKILL.md",
        ".codex/agents/auditor.toml",
        ".codex/agents/implementer.toml",
        ".claude/agents/auditor.md",
        ".claude/agents/implementer.md",
    }
    actual = set(snapshot(root))
    missing = expected_projection_paths - actual
    if missing:
        raise AssertionError(f"rich apply omitted projections: {sorted(missing)}")
    if not claude_root.read_bytes().startswith(existing_claude):
        raise AssertionError("rich apply changed user-owned Claude root content")
    rule_adapter = (root / ".claude" / "rules" / "no-deploy.md").read_text(encoding="utf-8")
    if '  - "src/**"\n  - "scripts/*.py"' not in rule_adapter:
        raise AssertionError("rule adapter did not preserve configured path order")
    doctor = subprocess.run(
        [sys.executable, str(DOCTOR), str(root), "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        doctor_payload = json.loads(doctor.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"doctor returned invalid JSON for rich fixture: {doctor.stdout!r}") from exc
    if doctor.returncode != 0 or doctor_payload.get("status") != "PASSED":
        raise AssertionError(f"doctor rejected rich generated project: {doctor_payload}")


def case_localized_edit_only_updates_dependents(base: Path) -> None:
    root = base / "project"
    root.mkdir(parents=True)
    proposal = rich_proposal()
    proposal["config"]["future_extension"] = {"opaque": True}
    proposal["config"]["control"]["future_toggle"] = "preserve-me"
    proposal_path = base / "proposal.json"
    write_json(proposal_path, proposal)
    init_exit, init_plan, stderr = run_configurator(
        "plan", "--project-root", str(root), "--proposal", str(proposal_path)
    )
    if init_exit != 0:
        raise AssertionError(f"localized fixture plan failed: {stderr or init_plan}")
    apply_exit, applied, stderr = run_configurator(
        "apply",
        "--project-root",
        str(root),
        "--proposal",
        str(proposal_path),
        "--plan-id",
        init_plan["plan_id"],
    )
    if apply_exit != 0 or applied.get("status") != "APPLIED":
        raise AssertionError(f"localized fixture apply failed: {stderr or applied}")
    before = snapshot_with_mtime(root)
    proposal["config"]["roles"][0]["purpose"] = "Review updated evidence without writes."
    proposal["config"].pop("future_extension")
    proposal["config"]["control"].pop("future_toggle")
    proposal["canonical_files"][".agents/reviewers/auditor.md"] = (
        "# Auditor\n\nReview updated evidence only.\n"
    )
    write_json(proposal_path, proposal)
    edit_exit, edit_plan, stderr = run_configurator(
        "plan", "--project-root", str(root), "--proposal", str(proposal_path)
    )
    if edit_exit != 0 or edit_plan.get("status") != "PLANNED":
        raise AssertionError(f"localized edit plan failed: {stderr or edit_plan}")
    edit_apply_exit, edit_applied, stderr = run_configurator(
        "apply",
        "--project-root",
        str(root),
        "--proposal",
        str(proposal_path),
        "--plan-id",
        edit_plan["plan_id"],
    )
    if edit_apply_exit != 0 or edit_applied.get("status") != "APPLIED":
        raise AssertionError(f"localized edit apply failed: {stderr or edit_applied}")
    after = snapshot_with_mtime(root)
    changed = {path for path in before if before[path] != after[path]}
    expected_changed = {
        ".ultracode/config.json",
        ".ultracode/managed.json",
        ".agents/reviewers/auditor.md",
        ".codex/agents/auditor.toml",
        ".claude/agents/auditor.md",
    }
    if changed != expected_changed:
        raise AssertionError(f"localized edit changed unexpected paths: {sorted(changed)}")
    final_config = json.loads((root / ".ultracode" / "config.json").read_text(encoding="utf-8"))
    if final_config.get("future_extension") != {"opaque": True}:
        raise AssertionError("localized edit discarded an unknown top-level config key")
    if final_config.get("control", {}).get("future_toggle") != "preserve-me":
        raise AssertionError("localized edit discarded an unknown nested config key")
    doctor = subprocess.run(
        [sys.executable, str(DOCTOR), str(root), "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    doctor_payload = json.loads(doctor.stdout)
    if doctor.returncode != 0 or doctor_payload.get("status") != "PASSED":
        raise AssertionError(f"doctor rejected localized edit: {doctor_payload}")

    if os.name == "nt":
        rollback_proposal = proposal
        rollback_proposal["config"]["project"]["mission"] = "Force a mid-apply rollback."
        rollback_proposal["canonical_files"][".agents/context/project.md"] = (
            "# Project\n\nContent that must be rolled back.\n"
        )
        write_json(proposal_path, rollback_proposal)
        rollback_plan_exit, rollback_plan, stderr = run_configurator(
            "plan", "--project-root", str(root), "--proposal", str(proposal_path)
        )
        if rollback_plan_exit != 0 or rollback_plan.get("status") != "PLANNED":
            raise AssertionError(f"rollback fixture plan failed: {stderr or rollback_plan}")
        before_failure = snapshot(root)
        config_path = root / ".ultracode" / "config.json"
        config_path.chmod(stat.S_IREAD)
        try:
            failure_exit, failure, stderr = run_configurator(
                "apply",
                "--project-root",
                str(root),
                "--proposal",
                str(proposal_path),
                "--plan-id",
                rollback_plan["plan_id"],
            )
        finally:
            config_path.chmod(stat.S_IREAD | stat.S_IWRITE)
        if failure_exit != 1 or failure.get("status") != "FAILED":
            raise AssertionError(f"mid-apply failure was not surfaced: {failure_exit}, {stderr or failure}")
        if before_failure != snapshot(root):
            raise AssertionError("mid-apply failure left a partially applied project")
        rollback_doctor = subprocess.run(
            [sys.executable, str(DOCTOR), str(root), "--json"],
            capture_output=True,
            text=True,
            check=False,
        )
        rollback_report = json.loads(rollback_doctor.stdout)
        if rollback_doctor.returncode != 0 or rollback_report.get("status") != "PASSED":
            raise AssertionError(f"doctor rejected rolled-back project: {rollback_report}")


def main() -> int:
    try:
        with tempfile.TemporaryDirectory(prefix="ultracode-configurator-corpus-") as temporary:
            base = Path(temporary)
            case_plan_is_read_only(base / "plan-no-write")
            case_apply_creates_doctor_valid_init(base / "apply-valid-init")
            case_second_apply_is_noop(base / "idempotent-apply")
            case_existing_agents_content_is_preserved(base / "existing-agents")
            case_managed_drift_conflicts_without_writes(base / "managed-drift")
            case_project_root_under_linked_ancestor_is_accepted(base / "linked-ancestor")
            case_unsafe_paths_and_reparse_are_rejected(base / "unsafe-paths")
            case_rich_adapters_are_generated_deterministically(base / "rich-adapters")
            case_localized_edit_only_updates_dependents(base / "localized-edit")
    except (OSError, AssertionError, ValueError) as exc:
        print(f"Project configurator corpus failed: {exc}", file=sys.stderr)
        return 1
    print("Project configurator corpus passed: 9/9")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
