# UC-37 Help Flow — Context B

## Raw request

```text
Use $ultracode-help flow
```

## Raw response

```markdown
## `$ultracode-flow`

**When to use it:** Use Flow for a quick view of current work: objective, phase, active or blocked tickets, owners, observable agents and models, completion criteria, blockers, and next action.

**What you get:** A compact, read-only snapshot that clearly labels freshness and unknown information.

**Can it write?:** No. Flow does not initialize, delegate, resume work, run checks, change settings, or write status files.

**When confirmation is required:** Never. Flow has no write path.

**Closest comparison:** Use `$ultracode-status` when you need a more detailed diagnosis covering files, checks, evidence, drift, history, and blockers.

> **Example:** `Use $ultracode-flow to show active tickets, blockers, and the next action.`
```

## Verdict

**PASS**

The explicit `$ultracode-help` invocation took precedence over the remaining `flow` topic. The
response explained Flow using the required focused Help structure and did not execute Flow or
reconstruct live task state.

## Side effects

- Initialized project control: **No**
- Delegated work: **No**
- Ran project checks, tests, or builds: **No**
- Changed global model, effort, or other settings: **No**
- Wrote files: **No**

The evaluation used only read-only repository inspection. The later creation of this evidence file
is an explicitly authorized persistence action and is not a side effect of the evaluated raw
request.

## Source references

- `plugins/ultracode/skills/ultracode-help/SKILL.md`: strict read-only boundary, invocation-token
  parsing, explicit Help precedence, and focused-answer structure.
- `plugins/ultracode/skills/ultracode-flow/SKILL.md`: explicit Help precedence and prohibition on
  reconstructing live Flow state for a Help invocation.
- `plugins/ultracode/skills/ultracode/references/command-guide.md`: canonical focused Flow content,
  closest command distinction, and read-only behavior.
- `plugins/ultracode/skills/ultracode/references/behavioral-contract.md`: UC-37 behavioral
  acceptance contract.
- `plugins/ultracode/skills/ultracode/references/eval-prompts.md`: UC-37 context-B raw request and
  required side-effect report.
