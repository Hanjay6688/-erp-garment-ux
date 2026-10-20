# Isolated OW01 capture dependency counter

Independent initial source assessment was sent before consulting peer conclusions:
the new `accessory_capture` calls private
`cp7_plan_native.after_snapshot(xid,timestamptz,timestamptz,pg_snapshot)` as
SECURITY INVOKER `cp7_capture`, but its accepted source had no EXECUTE grant to
that role. Schema USAGE and SELECT of `intents.xmin/recorded_at` do not imply it.

`EXPECTED.json` records literal expectations before execution. The exact helper
definition is extracted from `scripts/cp7-src/plan-native/staged.sql`; its actual
owner/revoke boundary is reproduced with isolated synthetic roles and an intents
table. `check_after_snapshot.mjs` creates no ERP schema or Native functions,
capture function, source data, authorization stub or installer. `RESULT.json`
records the first run passing all six observations:

| Observation | Actual isolated result |
| --- | --- |
| Capture schema/column rights | USAGE and needed SELECT true; helper EXECUTE false |
| New COUNT expression, empty intents | 42501: permission denied for function after_snapshot |
| Same expression, one synthetic intent | Same 42501 |
| Exact helper EXECUTE only, one intent | Count1 |
| Rights after narrow control | No table writes; no plan-writer membership |
| Exact helper EXECUTE only, empty intents | Count0 |

The expression initializes the function permission check even for an empty
table. Thus this missing capability can fail an unrelated old analysis run when
the alert runner starts processing its new ACCESSORY_NEED rule. This confirms a
source ACL defect; it does not prove the unseen Native CI SQLSTATE is this error.

Source anchors are under `/workspace/scratch/9442228ed2dc/erp-d1714/`:

| Dependency | Existing source boundary |
| --- | --- |
| New caller | `reminders/accessory-source.sql`87 in initial a106 read: direct after_snapshot call; function owner capture, SECURITY INVOKER |
| Private helper | `plan-native/staged.sql`113 definition;475 owner plan_writer;483–485 PUBLIC/client revoke, no capture grant in initial source |
| Existing counterpart | `reminders/staged-reminders.sql`224–236 performs the same xmin logic inline |
| Intents schema and columns | `plan-native/bootstrap.sql`7/40, `reminders/staged-reminders.sql`18 and reminder-v2 TABLE_GRANTS already cover schema/columns |
| Identity policy source | `identity/command.sql`101–102 explicitly grants workspace_data to capture |
| Profile source | `planning/profile.sql`134 explicitly grants source to capture |
| Schedule source | `planning/schedule.sql`230 owns source_at as capture |
| WIP source and normalization | `wip/ownership.sql` owns both exact helpers as capture |
| ERP products/commercial/FG/cutting/PO reads | `snapshot/bootstrap.sql`7–10 already grants capture SELECT |
| BOM/category reads | `planning/material-requirements.sql`5 already grants capture SELECT |
| Material and staged-run helpers/data | Existing capture-owned analysis modules |

All paths in that table are under `scripts/cp7-src/`. No second uncovered private
permission was found in this pass. Whole capture execution, current access,
RLS and actual Native source semantics remain the integrated CI's responsibility.

The root's subsequent working-tree fix was source-reviewed: it grants EXECUTE on
this one pure helper to capture, adds the same canonical signature to the bundle
GRANTS manifest and verifies that permission. Existing client revokes remain.
No role membership, general function grant, table expansion or ERP write is
required. The initial RESULT source hashes remain intact and are not rewritten
to pretend it exercised the later product candidate.

Run the isolated check with:

```sh
node /workspace/scratch/9442228ed2dc/ow01-proposals/capture/check_after_snapshot.mjs
```

It uses the existing PGlite dependency under `sql-dev/node_modules`; set
`OW01_PGLITE_MODULE` if needed. It neither starts Native DB nor installs or edits
the active product. This is source/isolated ACL evidence only, not a completion
claim for the two old analysis cases or OW01.
