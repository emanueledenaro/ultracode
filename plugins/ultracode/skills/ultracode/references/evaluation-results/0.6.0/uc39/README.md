# UC-39 durable feature verification forward test

## Raw request

> Fresh UC-39 forward test. Work in `${REPOSITORY_ROOT}` without editing files outside the retained
> evaluation artifact set. In a disposable directory, create a feature-verification plan for a
> dependency-free sample feature; execute real success, failure, persistence, invalid, and stale
> cases; capture direct command evidence; and prove rejected updates make zero writes. Use local
> tools only. Do not commit, push, install dependencies, make external requests, or deploy.

## Verdict

`CONFIRMED`

`uc39_forward.py` copied `sample_preference.py` into `${DISPOSABLE_ROOT}` and executed it through
three subprocesses. The retained report records each exact portable command, exit code, stdout,
stderr, pre/post state hash, exact UTF-8 state bytes, hex bytes, and separate-process readback.

- Valid `dark` save: exit `0`, exact persisted bytes `{"preference":"dark"}\n`.
- Separate readback: exit `0`, returned `dark`, state bytes unchanged.
- Invalid `ultraviolet`: exit `2`, deterministic diagnostic on stderr, state hash unchanged.
- The plan deliberately required exit `1` for the invalid case, so the direct exit-`2` observation
  correctly produced a `failed` result with contradicting evidence.
- `not-run` and `not-applicable` retained reasons and no execution evidence.
- All eleven malformed or stale updates were rejected with identical before/after hashes.
- Derived feature outcome: `FAILED`, with incomplete coverage also present.

The runner uses the explicit schema-equivalent semantic checker because no Draft 2020-12 library is
assumed. It covers closed fields, types, constants, patterns, statuses, evidence variants, unique
IDs, criterion coverage, ordered append-only histories, and stale-byte preconditions.

## Artifact inventory

`README.md` is intentionally excluded from its self-referential table.

| Artifact | SHA-256 |
| --- | --- |
| `sample_preference.py` | `fa5270be413dfdf69b3cdffaa9d7fd2b8bfda59ad2dbcd6e57cd7417417aa53d` |
| `uc39_forward.py` | `921587e620e89986501ba2c896b63b5114026ea973c649f74261e6bdfbdda301` |
| `initial-plan-preview.json` | `6d83c8da8a012a8821949acadea30229de4eef396eef953f9ea4796a9a98e43f` |
| `final-plan.json` | `9e2dd34afb5830a77617011c5c6cb6a27d06404a55756de1dd92cc70066e3dfb` |
| `run-report.json` | `5ea0d59fe0f91cd4eec6e84b37afda4e15b33f79eb546252f6d65596b7f380be` |
| `invalid/unknown_status.json` | `6d83c8da8a012a8821949acadea30229de4eef396eef953f9ea4796a9a98e43f` |
| `invalid/passed_without_evidence.json` | `6d83c8da8a012a8821949acadea30229de4eef396eef953f9ea4796a9a98e43f` |
| `invalid/not_run_with_evidence.json` | `6d83c8da8a012a8821949acadea30229de4eef396eef953f9ea4796a9a98e43f` |
| `invalid/contradictory_outcome.json` | `6d83c8da8a012a8821949acadea30229de4eef396eef953f9ea4796a9a98e43f` |
| `invalid/duplicate-and-orphan-ids.json` | `7a51401e7e012877514099c5457c10e3ceb1df30de496fdb127fae6fac843157` |
| `invalid/missing-criterion-reference.json` | `d4c3c7ad3d5ea5caa0c51471f9aafe9fddb91c7f2241811276a94fb0c3ab5da8` |
| `invalid/missing-required-field.json` | `f4f9df16c412d81239e1347ff294cb956b8cac16373f4c7f4262bf5ed487f440` |
| `invalid/wrong-initial-state.json` | `02a2e249b44997a0f13e31aa37b9440d7843be971c70bc3ea97b6c9a2ac25410` |
| `invalid/out-of-order-history.json` | `3f72e9c876fd7b6e93ca1436b7e77b522364f93a735a923281432262cfc4cf5f` |
| `invalid/malformed-json.json` | `15c1e2529bdbe0b5657e9e73898a4ac728d2b7be33d3ec08d4c796614c02eb35` |
| `invalid/stale-concurrent-update.json` | `3e8de7caee92647e81416c2301d491a08c3e1a699da749e4bf80e85da5b645a7` |
