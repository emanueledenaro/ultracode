---
description: Run UltraCode engineering work end to end with visible progress
argument-hint: "<what to build, fix, migrate, audit, or diagnose>"
---

Use the `ultracode` skill from the ultracode plugin to execute this work end to end.

Objective: $ARGUMENTS

Before writing anything, explain the objective, the jobs you derived from the real project, who owns
each one, and how completion will be verified. Read the plugin's Claude Code runtime adapter before
routing any model, effort level, or delegated job, and delegate through the `Agent` tool using the
plugin's `ultracode-explorer`, `ultracode-worker`, `ultracode-verifier`, and `ultracode-reviewer`
agent types.
