# Runtime snapshot

Captured at: 2026-07-23T10:15:00+02:00
Current time: 2026-07-23T10:17:00+02:00

Objective: publish UltraCode 0.5.0 with command Help and objective-driven model and effort routing.
Phase: release validation
Next action: finish the contract evidence, then reinstall the local plugin in Codex.

## Jobs

### U-101

- Title: Implement the shared command interface
- State: DONE
- Responsible owner: lead
- Live agent: none
- Requested model: inherit
- Effective model: gpt-5.6-sol
- Requested effort: inherit
- Effective effort: high
- Routing reason: lead work keeps the active chat model and effort; both effective values were observable here.
- Why it exists: give all public commands the same understandable language.
- Completed: the shared interface and all six skill contracts were updated.
- Remaining: none.
- Completion criterion: all six skills reference and follow the shared interface.

### U-102

- Title: Align the PowerShell release checker
- State: ACTIVE
- Responsible owner: validator worker
- Live agent: Hubble, agent id agent-42
- Requested model: gpt-5.6-terra
- Effective model: gpt-5.6-terra
- Requested effort: low
- Effective effort: low
- Selection reason: Terra is the configured bounded-agent model for this operational validation job.
- Why it exists: Python and PowerShell must enforce the same release contract.
- Completed: the sixth skill and UC-37/38 checks were added.
- Remaining: rerun after release evidence is refreshed.
- Completion criterion: the PowerShell checker reaches exit code 0 on the frozen release payload.

### U-103

- Title: Run the final independent audit
- State: QUEUED
- Responsible owner: contract-reviewer
- Live agent: none
- Requested model: gpt-5.6-sol
- Effective model: not selected yet
- Requested effort: xhigh
- Effective effort: not selected yet
- Routing reason: release integrity requires an independent critical review.
- Why it exists: the release cannot ship with an open high-severity finding.
- Completed: no final audit has run on the new frozen payload.
- Remaining: start after all payload files and evidence are stable.
- Completion criterion: an independent reviewer reports zero open HIGH findings.

### U-104

- Title: Reinstall the plugin in Codex
- State: BLOCKED
- Responsible owner: lead
- Live agent: none
- Requested model: inherit
- Effective model: cannot be observed because no worker is running.
- Requested effort: inherit
- Effective effort: cannot be observed because no worker is running.
- Routing reason: this external action remains owned by the active chat and therefore inherits its model and effort.
- Why it exists: Codex is still loading the previous installed release.
- Completed: the local plugin manifest has been prepared for 0.5.0.
- Remaining: refresh the configured local marketplace and install the new cache-busted version.
- Blocker: installation must wait until the payload and its version are frozen.
- Completion criterion: `codex plugin list` reports an enabled UltraCode 0.5.x installation.

## Checks

- Repository validator: PASSED at 2026-07-23T10:12:00+02:00
- Python contract checker: BLOCKED because UC-35 evidence is not populated yet.
- PowerShell contract checker: BLOCKED because the sixth skill hash is not populated yet.

## Files

- Modified: six public skill contracts, shared command interface, model/effort routing, validators, release docs.
- No Git staging, commit, push, deployment, or destructive operation was performed.
