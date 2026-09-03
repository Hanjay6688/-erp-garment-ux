# CP4.5 truth boundary

CP4.5 is a pre-CP5 candidate for ERP Enteng UAT. It does not authorize a production deploy, production invite, or production data mutation. `production_go` remains `false`.

## Connected source of truth

- Dynamic role, permission, user-role assignment, Master Pola, authoritative WIP status, WIP flags, and the Final SKU permission boundary use guarded RPCs in connected UAT mode.
- Master Pola may start empty. Search is server-side and paginated; status filtering supports active, inactive, and all records.
- Both the Master Pola page and quick-create from Buat Potongan call `erp_save_pattern_v1`. There is no second table, shadow list, or free-text transaction identity.
- Pattern identity is `(pattern_id, code snapshot, name snapshot, revision snapshot)`. Database triggers populate immutable transaction snapshots from an active master row. The v2.6.17a forward-only correction makes this an initial-only binding: the Potongan must still be a pristine `CUT` draft with no downstream fact, and a bound identity cannot be reassigned, unassigned, or edited in place.
- Grandfathered history may remain without `pattern_id`, so deployment does not require importing old Pola. Any new or changed Potongan through a JWT application request is rejected unless it carries `pattern_id`.
- A used pattern can only be deactivated. Inactive patterns are excluded from normal choices and remain readable in historical WIP.
- Bagi Potongan and WIP display the immutable parent-Potongan pattern snapshot. Pickup and child-batch controls do not offer a second pattern selector, so splitting or moving quantities cannot silently change identity.
- Code/revision uniqueness, client-request idempotency, permission checks, optimistic version checks, and database uniqueness handle duplicate and concurrent creation.
- Assignment and downstream child creation serialize on the Potongan row. A later correction of a bound Pola is intentionally unavailable through the assignment RPC; it requires a separately reviewed append-only lifecycle/version rather than overwriting history.
- Final SKU binds every posted Good piece to an active product. Once its QC document leaves draft, item identity is immutable; corrections must use the owning reversal or reclassification lifecycle.

## Deliberate UI boundary

The current Buat Potongan screen is still a simulation for the final cutting transaction save. Its connected pattern picker and quick-create are real UAT RPC boundaries, but the page does not claim that the simulated “save cutting” button posts a production transaction. When that writer is connected later, it must submit `pattern_id`; the database assignment path owns all snapshots. This avoids presenting demo state as persisted truth.

The non-UAT Bagi Potongan and WIP screens use explicit simulation fixtures. Those fixtures now carry and render one locked pattern snapshot at the Batch Produksi parent, including search and Potongan detail. This proves UX continuity only; it does not claim the simulated cutting save persisted anything. In UAT Auth mode, authoritative WIP continues to read the real backend snapshot.

## Safety and hygiene

- Independent audit defect `P2-CP45-001` remains a closure stop until v2.6.17a has exact-head CI, hosted-UAT verification, cleanup, and a fresh read-only re-gate. The base v2.6.17 evidence is retained but does not by itself close this correction.
- Frozen CP3 and CP4 runtime/proof bytes remain byte-bound by the V2 ownership gate.
- Legacy ERP Garment is read-only and outside the CP4.5 mutation target.
- Branch protection/status enforcement is absent and recorded as non-blocking P3 hygiene.
- Cloudflare dry-run names environment `uat-auth` explicitly. No deploy command is part of CP4.5 closure.
- Build UX runs a disposable Chromium smoke in 1440×900 and 412×915 projects. It gates console/page errors, verifies pattern snapshot visibility through Bagi Potongan and WIP, and retains non-secret screenshots plus JSON/HTML results; it never points at UAT or production.
