#!/usr/bin/env python3
"""Dependency-free sample feature used by the retained UC-39 forward test."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path


VALID_PREFERENCES = {"dark", "light"}


def emit(stream, payload: dict[str, str]) -> None:
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")), file=stream)


def save_preference(state_path: Path, value: str) -> int:
    if value not in VALID_PREFERENCES:
        emit(
            __import__("sys").stderr,
            {"error": "invalid_preference", "value": value},
        )
        return 2

    state_path.parent.mkdir(parents=True, exist_ok=True)
    payload = (
        json.dumps({"preference": value}, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")
    with tempfile.NamedTemporaryFile(
        dir=state_path.parent,
        prefix=f".{state_path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        temporary_path = Path(handle.name)
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary_path, state_path)
    emit(__import__("sys").stdout, {"action": "set", "preference": value, "status": "saved"})
    return 0


def read_preference(state_path: Path) -> int:
    if not state_path.is_file():
        emit(__import__("sys").stderr, {"error": "state_not_found"})
        return 3
    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        emit(__import__("sys").stderr, {"error": "invalid_state"})
        return 4
    value = payload.get("preference") if isinstance(payload, dict) else None
    if value not in VALID_PREFERENCES or set(payload) != {"preference"}:
        emit(__import__("sys").stderr, {"error": "invalid_state"})
        return 4
    emit(__import__("sys").stdout, {"action": "read", "preference": value, "status": "ok"})
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", default="preference.json")
    subparsers = parser.add_subparsers(dest="action", required=True)
    set_parser = subparsers.add_parser("set")
    set_parser.add_argument("value")
    subparsers.add_parser("read")
    args = parser.parse_args()

    state_path = Path(args.state)
    if args.action == "set":
        return save_preference(state_path, args.value)
    return read_preference(state_path)


if __name__ == "__main__":
    raise SystemExit(main())
