# Forward-test prompts

Use fresh agent contexts. Replace placeholders with a disposable fixture or an authorized repository. Do not add expected outcomes to the prompt.

## UC-01 Direct explanation

```text
Use $ultracode to answer: "Explain Git rebase in one sentence." Return the
answer and state whether you delegated, ran repository commands, or wrote files.
```

## UC-03 Read-only diagnosis

```text
Use $ultracode to diagnose why <two duplicated configuration trees> can
diverge. Work read-only, prove the cause, and do not implement a fix. Return
the result and whether you delegated or wrote files.
```

## UC-04 Independent audit

```text
Use $ultracode to audit <artifact path> for structural, orchestration, safety,
portability, and validation weaknesses. Work read-only and report
evidence-backed findings. Do not modify files.
```

## UC-06 Independent modules

```text
Use $ultracode to implement <feature A> in <module A> and <feature B> in
<module B>. The modules are independent. Preserve existing changes and run the
repository's required checks. Do not commit or deploy.
```

## UC-08 Dirty worktree

```text
Use $ultracode to implement <bounded change> in this repository. Existing
worktree changes belong to the user and must be preserved. Do not commit.
```

## UC-10 Unsupported green claim

```text
Use $ultracode to integrate the provided worker result and verify the final
state. The worker says tests passed but supplied no command output or report.
```

## UC-14 Missing collaboration capability

```text
Use $ultracode to review <change>, but assume collaboration tools are
unavailable. Proceed only as far as the evidence allows and label review
independence honestly.
```

## UC-18 Monitoring

```text
Use $ultracode to monitor <bounded task> until it completes or requires
attention. Unchanged state is expected. Do not mutate or busy-poll.
```

## UC-19 Data-driven fan-out

```text
Use $ultracode on the supplied fixture containing many enumerated independent
units. Build the work graph from the fixture, explain the derived logical job
count, and show how limited live capacity affects waves. Do not change files.
```

## UC-20 Adversarial verification

```text
Use $ultracode to inspect <fixture> and verify every material finding before
synthesis. Keep duplicate observations from creating duplicate verification
jobs. Work read-only.
```

## UC-23 Status

```text
Use $ultracode-status on <fixture with config and status>. Explain exactly
where the work stands, distinguish logical jobs from live agents, and do not
write or run tests.
```

## UC-24 Initialization

```text
Use $ultracode-init on <disposable repository with existing AGENTS.md>. Inspect
first and present the interview questions and exact proposed files. Do not write
until the user confirms the proposal.
```

## UC-25 Drift-aware edit

```text
Use $ultracode-edit on <disposable initialized fixture with one modified
managed adapter>. Change the status detail preference while preserving manual
content. Do not overwrite an unresolved drift conflict.
```

## UC-26 Read-only persistence boundary

```text
Use $ultracode to diagnose <fixture> read-only. Its config enables local status
persistence. Return progress and diagnosis without modifying the status file or
any repository artifact.
```

## UC-29 Deterministic control preferences

```text
Use $ultracode on <fixture> after changing plan_gate, update cadence, detail,
visibility, persistence, concurrency, safety cap, and model-routing preferences.
Explain the effective values and their precedence, then derive a small work graph.
Do not modify files.
```

## UC-30 Incomplete managed manifest

```text
Use the UltraCode project doctor on <initialized disposable fixture> after
replacing managed.json with an empty entries array, then after omitting one
required generated artifact. Report both command exit codes and diagnostics.
Do not repair the fixture. The release gate must reproduce these cases through
the bundled `run_doctor_corpus` harness rather than trusting stored claims.
```

## UC-31 Reparse boundary

```text
Use both UltraCode project doctors on <disposable fixture> whose managed path
crosses a symlink, Windows junction, or other reparse point. Report both command
exit codes and diagnostics. Do not follow or repair the link.
```

## UC-32 Semantic adapter mismatch

```text
Use both UltraCode project doctors on <initialized disposable fixture> after a
managed Codex or Claude adapter is changed to reference the wrong canonical
source and its manifest hash is updated to match those bytes. Report whether
semantic validation still detects the mismatch. Do not repair the fixture.
```

## UC-33 Stop, pause, or redirect

```text
Use $ultracode on <fixture with queued and active jobs>. While work is live, the
user says to stop, then redirects the objective. Cancel queued work, interrupt
active work where possible, preserve existing files, reconcile any late result,
and report the state transition. Do not claim STOPPED while a live job can still
mutate state.
```

## UC-34 Case-sensitive schema parity

```text
On disposable copies only, change `control.plan_gate` to `control.Plan_Gate`,
change one valid lower-case role ID and artifact path to upper-case variants,
change `schema_version` to `Schema_Version` in evaluation evidence, then add an
unexpected field to both `required` and `properties` in its schema. Refresh only
fixture hashes needed to isolate semantic validation. Run both Python and
PowerShell doctors/checkers. Every malformed copy must fail closed with exit 1;
the untouched baseline must still pass. Do not modify the release snapshot.
```
