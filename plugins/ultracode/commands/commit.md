---
description: Prepare or validate a Conventional Commits message from the real Git diff
argument-hint: "[message or commit scope]"
---

Use the `ultracode-commit` skill from the ultracode plugin.

Request: $ARGUMENTS

Inspect the real diff before proposing a message. Keep preparation read-only. Git staging, commit,
amend, rebase, push, tag, publish, and pull-request actions require explicit authority for the exact
action and paths.
