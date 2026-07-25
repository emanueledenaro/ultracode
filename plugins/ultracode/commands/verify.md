---
description: Create, inspect, execute, or update a durable feature verification plan
argument-hint: "<feature or scenario to prove>"
---

Use the `ultracode-verify` skill from the ultracode plugin.

Feature: $ARGUMENTS

Keep the plan append-only, use only the statuses planned, passed, failed, not-run, and
not-applicable, and fail closed on incomplete or inconsistent evidence. Do not fix product code to
make a scenario pass. Delegate each independent check to the plugin's `ultracode-verifier` agent
type with the claim and raw evidence inlined in the brief.
