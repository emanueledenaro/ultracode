---
name: ultracode-commit
description: Prepare and validate Conventional Commits 1.0.0 messages from the real Git diff. Use when the user asks for a commit message, asks to validate commit wording, or explicitly asks UltraCode to commit completed work. Keep inspection read-only until Git authority is explicit.
---

# UltraCode Commit

Prepare one truthful commit message from the real diff and validate it against
[Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/). Use this skill for
commit-message work instead of inventing a message from the user's request alone.

## Respect explicit Help precedence

If the request explicitly invokes `$ultracode-help`, `/ultracode:ultracode-help`, `/ultracode:help`,
or `ultracode-help`, stop before Git inspection and answer the remaining words as a read-only Help
topic. Read `../ultracode-help/SKILL.md` for that response. This is a read-only Help topic.

Read [the Conventional Commits reference](../ultracode/references/conventional-commits.md) before
deriving or validating a message.

Preparing or validating a message is read-only. Inspect `git status`, the relevant diff, and recent
history when available. Do not stage, commit, amend, rebase, push, tag, publish, or open a pull
request unless the user gives explicit authority for that exact Git action. A project plan or a
request to implement code does not grant Git authority.

## Apply the Conventional Commits shape

The subject MUST have this shape:

```text
<type>[optional scope][optional !]: <description>
```

Use these rules:

- `type` is a noun token. Use `feat` for a new feature and `fix` for a bug fix; other types such as
  `build`, `chore`, `ci`, `docs`, `perf`, `refactor`, `revert`, `style`, and `test` are allowed.
- `scope` is optional, describes a codebase section, and is wrapped in parentheses.
- `!` goes immediately before the colon when the change is breaking.
- A non-empty description follows the required colon and space. Prefer a consistent lower-case type
  and a concise imperative description, but do not claim these preferences are requirements of the
  specification.
- A body is optional and starts after one blank line. It explains context or implementation detail.
- Footers are optional and start after one blank line. Each footer uses a trailer token followed by
  `: ` or ` # ` and a value. Use `BREAKING CHANGE: ...` or `BREAKING-CHANGE: ...` for a breaking
  change when the prefix does not already contain `!`.
- The convention is case-insensitive except that the breaking footer token is uppercase. Keep local
  output consistently lower-case for predictable history.

Types are extensible: do not reject a project-specific noun merely because it is not in the
recommended list. `feat` and `fix` carry the usual SemVer meaning; only an actual breaking change
implies a major release.

## Derive and report the message

1. Confirm the repository root and current worktree state. Treat pre-existing changes as user-owned.
2. Inspect the exact diff and separate unrelated changes before choosing a type or scope.
3. Propose the subject first, then the optional body and footers. Explain which changed files support
   the type, scope, and any breaking-change marker. If the diff is ambiguous, report the ambiguity.
4. Validate the whole message against the shape above, including blank-line separation and footer
   tokens. Do not rewrite a breaking change as a normal fix or feature.
5. If the user explicitly authorizes a commit, show the final message, exact included paths, and
   checks before the commit boundary. Stage only the authorized paths and use the validated message;
   never include unrelated user changes.
6. After a commit, verify the resulting commit subject and repository state. Report commit, remote,
   push, and deployment status separately; a local commit is not a push or release.

When the diff contains multiple independently meaningful changes, recommend separate commits and
prepare one message per commit only after the user confirms the split. Do not stage or split files
silently.

## Keep runtime behavior honest

Use `$ultracode-commit` on Codex and `/ultracode:commit` on Claude Code. A plain request to “make a
commit” is enough to select this skill, but the Git action still needs explicit authority. If the
runtime does not expose Git output, say that validation is based on the supplied message or visible
repository evidence rather than claiming a commit occurred.
