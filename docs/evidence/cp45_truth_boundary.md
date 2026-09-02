# CP4.5 truth boundary

CP4.5 is a pre-CP5 candidate for ERP Enteng UAT. It does not authorize a production deploy, production invite, or production data mutation. `production_go` remains `false`.

## Connected source of truth

- Dynamic role, permission, user-role assignment, Master Pola, authoritative WIP status, WIP flags, and the Final SKU permission boundary use guarded RPCs in connected UAT mode.
- Master Pola may start empty. Search is server-side and paginated; status filtering supports active, inactive, and all records.
- Both the Master Pola page and quick-create from Buat Potongan call `erp_save_pattern_v1`. There is no second table, shadow list, or free-text transaction identity.
- Pattern identity is `(pattern_id, code snapshot, name snapshot, revision snapshot)`. Database triggers populate immutable transaction snapshots from an active master row.
- Grandfathered history may remain without `pattern_id`, so deployment does not require importing old Pola. Any new or changed Potongan through a JWT application request is rejected unless it carries `pattern_id`.
- A used pattern can only be deactivated. Inactive patterns are excluded from normal choices and remain readable in historical WIP.
- Code/revision uniqueness, client-request idempotency, permission checks, optimistic version checks, and database uniqueness handle duplicate and concurrent creation.

## Deliberate UI boundary

The current Buat Potongan screen is still a simulation for the final cutting transaction save. Its connected pattern picker and quick-create are real UAT RPC boundaries, but the page does not claim that the simulated “save cutting” button posts a production transaction. When that writer is connected later, it must submit `pattern_id`; the database assignment path owns all snapshots. This avoids presenting demo state as persisted truth.

## Safety and hygiene

- Frozen CP3 and CP4 runtime/proof bytes remain byte-bound by the V2 ownership gate.
- Legacy ERP Garment is read-only and outside the CP4.5 mutation target.
- Branch protection/status enforcement is absent and recorded as non-blocking P3 hygiene.
- Cloudflare dry-run names environment `uat-auth` explicitly. No deploy command is part of CP4.5 closure.
- Build UX runs a disposable Chromium smoke in 1440×900 and 412×915 projects. It gates console/page errors and retains non-secret screenshots plus JSON/HTML results; it never points at UAT or production.
