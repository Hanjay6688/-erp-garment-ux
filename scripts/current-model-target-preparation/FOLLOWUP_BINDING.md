# Bind prepared followups after Native20 actually passes

`bind_followup_source.py` creates only SOURCE and a local environment JSON. It
does not run a database, commit, push or claim admission. Run it from the frozen
writer cwd against a clean dedicated worktree that contains the exact Native20
SOURCE from the successful candidate. Do not edit any file pinned by Native20.

Its JSON input has `repo`, `kind` (`browser`, `restore`, `transport`, `finance`,
`cron`, `factory`), `env_input`, `env_output`, and `originals`. Each originals
entry is an environment variable mapped to `{proof_path, report_path}`. The
complete raw Original and adjacent `T3_PACKAGE_INSTALL.json` must match the
verified intake proof. The environment input retains the parent Native20
environment, including all six prerequisite Originals and immutable source roots.
Keep environment files outside Git.

The binder refuses old Native15 evidence, changed Native20 source, incomplete
runtime/restore gates, missing parent Originals, mixed transport parts, or an
existing output. Target transport accepts full11 or both complete same-head
parts; repeated catalog has zero additional credit. Finance also preserves its
actual first INCOMPLETE Original; that artifact must retain its four passing
package gates and failed writer gate. Factory requires the current-chain Cron1
Original in addition to Native20.

After binding, commit SOURCE and invoke the selected probe's full `admitted()`
gate with the saved environment. Only after that succeeds publish the exact tree
on its dedicated workflow branch (branch at parent, then fast-forward update to
the new commit). Freeze that candidate while CI runs. Retain the actual first
result, all cleanup outcomes and raw artifact bytes, including failures.
