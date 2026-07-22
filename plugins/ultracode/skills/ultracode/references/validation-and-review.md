# Validation and independent review

Read this reference for Deep or Critical execution and whenever a completion claim carries material risk.

## Build the verification ladder

Choose checks from repository evidence, in this order:

1. Commands required by applicable `AGENTS.md` files.
2. Existing CI jobs and scripts.
3. Package, build, and test manifests.
4. Tests adjacent to changed code.
5. Runtime or health checks that exercise the real path.

Start with the fastest discriminating check. Expand only after it passes or when a broader failure is needed to locate the problem.

For a read-only request, first classify the side effects of every check. A check that creates a cache, build directory, generated report, import, lockfile change, or workspace artifact is not read-only. Use a non-writing alternative, obtain explicit authorization, or report it as `BLOCKED`/`NOT RUN`.

## Interpret results literally

Use these states:

- **PASSED:** the relevant command completed successfully and its report supports the claim.
- **FAILED:** the command ran and reported a relevant failure.
- **BLOCKED:** the check could not run because of a concrete environmental or authority boundary.
- **NOT AVAILABLE:** the repository does not provide that check.
- **NOT RUN:** the check existed but was intentionally skipped; state why.

Starting a server, compiler, scan, or test runner is not a pass. Inspect final status, exit code, and produced report. A green build does not prove runtime behavior, security, data correctness, or a clean worktree.

## Validate the real path

For user-visible or operational work, prefer an end-to-end path that proves the outcome:

- HTTP status and response boundary for services;
- process, port, and health endpoint for local servers;
- real compilation plus error logs for editors or game engines;
- generated artifact plus parser/open check for documents or packages;
- migration status and representative queries for data changes;
- UI interaction and state transition for frontend behavior.

Do not perform production writes, deployments, purchases, messages, or destructive actions unless the user's scope authorizes them.

## Keep review independent

The reviewer receives:

- acceptance criteria;
- applicable repository instructions;
- raw diff or changed paths;
- relevant test output.

The reviewer should not receive the lead's conclusion, expected “no issues” result, or a prewritten finding list. Independence is strongest when the reviewer reconstructs the risk surface from raw artifacts.

## Prioritize findings

Order findings by material impact:

1. data loss, security, permissions, or destructive behavior;
2. incorrect behavior, regressions, broken compatibility, or race conditions;
3. missing error handling, lifecycle problems, and unverified integration paths;
4. maintainability problems likely to create concrete defects;
5. style only when contractually enforced.

Every finding needs a failure mode, evidence, and the smallest safe correction. Questions without evidence remain questions, not defects.

## Convergence rule

After a confirmed finding:

1. apply the smallest in-scope fix;
2. rerun the narrow failing check;
3. rerun any broader check invalidated by the fix;
4. obtain one follow-up review of the affected area.

Stop after two automatic fix-review iterations. Report a repeated blocker or design conflict rather than masking it with more retries. Every iteration must produce new evidence or reduce a measurable failure set; repeating the same command with the same result is not progress.

## Handoff evidence

The final handoff should contain only what helps the user decide:

- outcome achieved;
- important changed files;
- checks that passed;
- checks blocked, unavailable, or not run;
- unresolved material risks or assumptions.

Avoid dumping subagent transcripts, routine command history, or unsupported confidence language.
