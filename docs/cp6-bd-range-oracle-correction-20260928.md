# Range base-rate oracle correction — writer, CP6 HOLD

Product source remains `2f6ac0d`. This changes test interpretation, not the application, public API, SQL, or gate machinery. Auditor/owner acceptance is still required.

The intended owner check is that mixed31/32/33, only32, and singleton27 shipments use the applicable service tariff without a surcharge caused by the number of shipped sizes. It does not prove a commercial SKU tariff resolver; that master gap stays open.

Two prior runs are retained as INCOMPLETE:

- `36349471819` / `108705193247`: the helper read `version_id` from the public pricing receipt, which does not expose it.
- `36350528938` / `108708212366`: reading `bd_laundry_charge_lines_v1.version_id` then demanding a non-null base-rate FK was also an incorrect writer assumption. The first attempted fix had not traced the RATE branch sufficiently.

Source contract inspected before this correction:

- `bd_process_rate_at_v1` in `scripts/cp6_bd_objects_master.sql` returns the nominal from exactly one `laundry_vendor_rate_versions` row applicable to vendor/process/time. It does not return an ID.
- The RATE branch in `scripts/cp6_bd_objects_pricing.sql` stores that nominal, covered quantity and amount. Its `version_id` expression uses the scoped-rate ID, so ordinary base RATE has null there. Component/package branches have their own explicit version IDs. A direct base RATE version FK is therefore **not proven or introduced** by this follow-up.
- `bd_assert_version_start_v1` rejects a new tariff starting at/before a posted delivery. Original nominal snapshots remain the accounting basis.

The replacement case is explicitly named `RANGE:SAME_EFFECTIVE_BASE_RATE_MIXED_SINGLE_32_SINGLETON_27`. For every persisted charge, it requires exactly one effective master row at the persisted delivery vendor/process/time, the exact ID created by the fixture, the expected nominal1731.29, `amount = covered_qty × rate`, and the original physical quantities. All three shipments must resolve the same effective master version; singleton27 must total5193.87. Evidence includes both the observed charge version field and the temporally resolved rate ID so they cannot be confused. This is temporal attribution plus a nominal snapshot, not a claim of a stored version FK.

The renamed oracle narrows the unsupported storage assertion explicitly; it does not silently turn either previous failure into PASS. A business requirement for an explicit RATE version FK would remain a separate source change and require its own package/regression qualification.

Both prior runs passed the other7 native,18 race,6 HTTP and19 browser cases at the same product source. The next dispatch targets only this corrected native case and retains the configured19-browser suite. Prior results keep their original run IDs/statuses; the next run is not represented as a new51-case execution. Full grouped-SKU master and membership changes remain unimplemented and unqualified.
