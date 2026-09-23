# AT independent review of frozen AS

Audited product/source: `8a170ce9931523f6fabe02ac5c24154d3333236b`, tree
`6c03015ca641e5fd81058f294f0dcb3cac3803ee`. AS writer is QUIESCED.

This round adds only an audit workflow, independent probes and this record.
It changes no product, migration, rollback, historical oracle or scope guard.
The workflow checks out AS at the exact frozen commit, replays its original
500 cases, 34 additions, 12 separate calendar policy checks and two populated
recovery cycles. It then uses another disposable clone for paired AR/AS probes.

The new cases investigate valid nonoverlapping product versions at cutover
and WIP output dates. The live immutable identity guards remain installed.
Fixtures use admin; business actions use ordinary authenticated public RPCs.
Refusals must restore all data; accepted output must identify the intended
product, replay without effects and reverse to the original WIP quantity.
Case snapshots include ERP, platform/auth, history and schema ACL. Full
catalog pins are checked before/after; the primary AN database stays unchanged
and the disposable clone is removed in finally.

The additional gate fails on either a product counterexample or an incomplete
test. Raw results distinguish those outcomes. No result is claimed before the
native evidence exists. CP6 HOLD; CP7 unopened; production_go false. Browser
acceptance remains separate from native database evidence.
