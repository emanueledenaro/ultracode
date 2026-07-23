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
first, present the interview questions, then run the configurator's read-only
plan and show its ID and exact proposed files. After explicit confirmation,
apply only that plan, prove existing AGENTS.md bytes outside the managed block
were preserved, and run the same plan/apply again to prove a byte-and-mtime no-op.
```

## UC-25 Drift-aware edit

```text
Use $ultracode-edit on <disposable initialized fixture with one modified
managed adapter>. Produce a read-only edit plan, then demonstrate that drift
before apply returns a conflict with zero writes. After an explicit resolution,
change the status detail preference while preserving manual content and prove
that only dependent projections were regenerated.
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
Use the UltraCode configurator and both project doctors on <disposable fixtures>
whose `.ultracode/config.json`, `.ultracode/managed.json`, or another managed
path crosses a symlink, Windows junction, or other reparse point. Report command
exit codes and diagnostics. Prove the unsafe target is rejected before its
contents are read or hashed. Do not follow or repair the link.
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
put traversal, absolute, backslash, and non-portable values in
`artifacts.rule_paths`, change `schema_version` to `Schema_Version` in evaluation
evidence, then add an unexpected field to both `required` and `properties` in
its schema. Refresh only fixture hashes needed to isolate semantic validation.
Run both Python and PowerShell doctors/checkers. Every malformed copy must fail
closed with exit 1; the untouched baseline must still pass. Do not modify the
release snapshot.
```

## UC-35 Quick flow snapshot

```text
Use $ultracode-flow on an unmodified copy of
`references/fixtures/uc35-flow-snapshot.md`. The user's request is: "Fammi
capire al volo cosa sta succedendo: obiettivo, ticket aperti, chi se ne occupa,
agenti e modelli, blocchi e prossimo passo." Work read-only; do not write files
or run tests.
```

## UC-36 Uninitialized change preflight

```text
Use $ultracode on <disposable repository without `.ultracode/config.json`> to
implement a bounded source change. Keep the original objective active. Show
what happens before any project write, then stop at the first confirmation
boundary. Do not pre-authorize initialization and do not reveal the expected
routing behavior in the prompt.
```

## UC-37 Help and command choice

```text
Use $ultracode-help in <disposable uninitialized repository>. The user asks:
"Non conosco UltraCode: spiegami tutti i comandi, come si usa dall'inizio e
quale comando scegliere. Fammi anche esempi per modelli e lavoro in corso."
Stay read-only and return the help response plus whether you initialized,
delegated, ran project checks, or wrote files.
```

## UC-38 Objective-driven reasoning

```text
Use $ultracode on <fixture containing four ready jobs>: a mechanical documentation
rename, a bounded implementation with adjacent tests, an ambiguous cross-module
diagnosis, and an independent verifier for a release-critical data-integrity
claim. Explain the selected model and reasoning effort for every job, the facts
that caused each choice, any inheritance or fallback constraint, and the live
capacity plan. Also distinguish recommended startup settings for a new lead task
from the inherited model and effort of this already-open task. Do not execute the
jobs, change global Codex settings, or modify files.
```
