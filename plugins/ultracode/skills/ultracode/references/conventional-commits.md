# Conventional Commits 1.0.0

UltraCode uses Conventional Commits as its default commit-message convention. The canonical
specification is [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/).

## Message shape

```text
<type>[optional scope][optional !]: <description>

[optional body]

[optional footer(s)]
```

The required prefix is a type, optional scope, optional breaking marker, colon, and space. The
description is required. A body starts after one blank line, and footers start after one blank line
after the body or description. Footer tokens use `-` instead of spaces, except `BREAKING CHANGE`,
which may also be written as `BREAKING-CHANGE`.

## Default UltraCode policy

- `feat` means a new feature and `fix` means a bug fix.
- Other noun types are valid. The recommended project vocabulary is `build`, `chore`, `ci`, `docs`,
  `perf`, `refactor`, `revert`, `style`, and `test`, but the specification does not require a fixed
  type allowlist.
- A scope is optional and should name a real codebase section, not a ticket or invented subsystem.
- Use `!` immediately before `:` or a `BREAKING CHANGE:` footer only when the diff changes a public
  contract or compatibility expectation. Breaking changes may use any type.
- Prefer lower-case types and concise descriptions for a consistent history. This is a local style
  choice; the specification treats the units as case-insensitive except for the uppercase breaking
  footer token.
- Footers follow Git-trailer style: `Token: value` or `Token # value`. `BREAKING CHANGE: value` is
  the explicit breaking-change footer form.

## UltraCode control boundary

The default is message preparation and validation, not a Git mutation. UltraCode may inspect the
worktree and diff without Git authority. It must not stage, commit, amend, rebase, push, tag, publish,
or open a pull request until the user explicitly authorizes that exact action. Implementation approval
does not grant Git authority, and a local commit does not prove push, release, or deployment.

When a commit is authorized, UltraCode must:

1. preserve unrelated user changes;
2. identify the exact paths included in the commit;
3. show the final message before the commit boundary;
4. use the actual diff to justify type, scope, description, and breaking status; and
5. verify the resulting local commit independently from remote or deployment state.

If unrelated changes cannot be separated safely, stop at the proposal and ask the user whether to
split, narrow, or leave the work uncommitted.
