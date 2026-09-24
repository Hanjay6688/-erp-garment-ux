# Verification: CP6-01 / F1-14 / GPT F01

## Claim
Three active connected frontend pages serialize an operator-entered wall-clock
`datetime-local` value with the *device* timezone instead of the ERP business
timezone WIB (Asia/Jakarta):
- `src/ConnectedCuttingPage.tsx:272` `cut_at: new Date(cutAt).toISOString()`
- `src/ConnectedPickupPage.tsx:200` `picked_up_at: new Date(pickedUpAt).toISOString()`
- `src/ConnectedBsResolutionPage.tsx:40` `toIso = (v) => new Date(v).toISOString()`
  (default seed `nowInput`, lines 36-39, has the same defect)

while `src/cp6BusinessTime.ts:16-25` (`cp6WibPhysicalTimeToIso`, explicit
`+07:00`) is the correct helper and is used only by
`ConnectedLaundryPage.tsx` and `ConnectedQcFinalPage.tsx`.

## Refutation attempts

### (A) CODE reachability, wrappers, server-side normalization

**1. Are the three pages reachable / is CONNECTED the only path?**
`src/App.tsx:607-666` gates each page on a runtime mode flag:
```
607: {page === 'cutting-roll' && runtime.cuttingMode === 'CONNECTED' && ... ConnectedCuttingPage}
609: {page === 'mandor-wip' && runtime.distributionMode === 'CONNECTED' && ... ConnectedPickupPage}
665: {page === 'bs-rework' && runtime.bsResolutionMode === 'CONNECTED' && ... ConnectedBsResolutionPage}
```
`src/config/runtime.ts` shows `cuttingMode`, `distributionMode`,
`bsResolutionMode`, **and** `laundryMode`/`qcFinalMode` (the two pages that
use the correct WIB helper) are set identically: `'SIMULATION'` under
`DEMO_SIMULATION` (the default when `VITE_ERP_RUNTIME_MODE` is unset), and
all six flipped to `'CONNECTED'` together under `UAT_AUTH_SIMULATION` /
`DISPOSABLE_TEST` (`isConnectedRuntime`, runtime.ts:262). So whenever the
laundry/QC pages (which the auditors trust to use the WIB helper) are live,
the three defective pages are equally live, on the same connected runtime.
**Reachability attempt fails to refute** — the bug is live exactly when the
correct-helper pages are live, not gated off.

**2. Is there a wrapper/global Date shim/server-side normalization?**
- `src/useProductionMutation.ts` (shared by all three pages via
  `useProductionMutation`) is a generic idempotency/lock/retry wrapper. It
  only stamps `createdAt: new Date().toISOString()` on the *envelope*
  metadata (useProductionMutation.ts, inside `execute`) — it never touches
  `cut_at`/`picked_up_at`/`physical_at` inside the caller-supplied payload.
  No timezone normalization present.
- Server RPCs (`supabase/migrations/20260903022604_..._cutting_persistence_pickup_wip.sql`):
  - line 656: `v_cut_at timestamptz:=nullif(p_payload->>'cut_at','')::timestamptz;`
  - line 1009: `v_picked_up_at timestamptz:=nullif(p_payload->>'picked_up_at','')::timestamptz;`
  Both are a plain `::timestamptz` cast — Postgres parses whatever offset the
  client sent (`Z` from `.toISOString()`) as the literal instant; there is
  **no re-derivation from a WIB-formatted string** and no rejection of a
  non-`+07:00` string. Only bounds checks exist: `cut_at` not in the future
  (line 728-729) and `picked_up_at` between `cut_at` and now (line 1089-1091).
  A wrongly-shifted instant (e.g. an hour off due to device TZ=Asia/Makassar)
  still satisfies both bounds checks in the overwhelming majority of cases,
  so it is **not** caught server-side.
  - BS resolution (`supabase/migrations/20260903070932_..._cp5_bs_resolution_recovery.sql:875`):
    `v_physical_at timestamptz:=nullif(p_payload->>'physical_at','')::timestamptz;`
    same pattern, same absence of WIB-format enforcement (only a
    not-in-future bound for `HOLD_BS`, line ~977).
  - **Contrast (important, and it cuts against a "code doesn't actually
    matter" refutation, i.e. it supports the finding):** a *sibling*
    endpoint, `erp.save_accessory_issue_action_v1` in
    `supabase/migrations/20260922135615_erp_v2_6_20ap_cp6_connected_import_materials.sql:502-503`,
    **does** defend against exactly this bug class:
    ```
    if jsonb_typeof(p_payload->'physical_at') is distinct from 'string'
       or (p_payload->>'physical_at')!~'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+07:00$'
    then raise exception 'Waktu pengambilan wajib memakai tanggal dan jam WIB';end if;
    v_at:=(p_payload->>'physical_at')::timestamptz;
    if (to_char(v_at at time zone 'Asia/Jakarta','YYYY-MM-DD"T"HH24:MI:SS')||'+07:00')
       <>(p_payload->>'physical_at') ...
    ```
    This proves the team knows how to fail-closed against a non-WIB-offset
    payload, and did apply it elsewhere (accessory issue / import
    materials), but did **not** apply the same guard to cutting, pickup, or
    BS-resolution. That is evidence of an inconsistently-applied fix, not
    evidence the defect is harmless.
  - Searched all `supabase/migrations/*.sql` (incl. the `..._20ac_...
    temporal_surface_closure.sql` mega-migration and `supabase/dev/*`,
    `supabase/release/cp6-t3*`) for any later re-interpretation of
    `cut_at`/`picked_up_at` tied to these RPCs — none found beyond the
    bounds checks above. The `POT-` group_number generation even uses UTC
    explicitly (`to_char(v_cut_at at time zone 'UTC','YYMMDD')`, line 755),
    confirming the backend does not enforce WIB on this value at all.

**3. Does the UI restrict device timezone (Intl check) so the defect is
unreachable?**
`grep -rn "resolvedOptions\|Intl.DateTimeFormat" src/` shows `Intl.DateTimeFormat`
is used only for *display formatting* (with explicit `timeZone: 'Asia/Jakarta'`
in a couple of places, e.g. `ConnectedInitialImportPage.tsx:279`), never as a
guard/validation gate on login or before a mutation. No code anywhere checks
`Intl.DateTimeFormat().resolvedOptions().timeZone` and blocks or corrects a
non-WIB device. The defect is fully reachable for any operator whose device
clock/timezone is not exactly `Asia/Jakarta`.

**4. Round-trip self-consistency (would this cancel out?).**
`datetimeLocal()` (ConnectedCuttingPage.tsx:28-32) and the pickup page's
identical helper convert a stored ISO instant back to `datetime-local` using
`date.getTimezoneOffset()` — device-local, symmetric with the device-local
save. This makes single-session edits look self-consistent in the browser,
but the **absolute instant persisted in the DB** (used for WIB-business-day
bucketing, ordering vs. `cut_at`) is still off by the device UTC-offset
delta. Does not refute the claim; explains why it's easy to miss in manual
QA on one consistently-misconfigured device.

### (B) CONTRACT scope

- Contract line ~3820 (`ERP_V3_2_Master_Pulih_20260923.md`, section "3.
  Invariant proyek yang tidak berubah" — i.e. an unconditional, non-checkpoint
  -scoped invariant):
  > "**Tanggal terpisah:** `physical_at`, tanggal dokumen/ekonomi,
  > `system_created_at`, ... **Jam perangkat tidak menggantikan waktu bisnis
  > WIB.**"
  This is stated as a project-wide invariant, not scoped to a single
  checkpoint, so it applies to Cutting/Pickup/BS-resolution regardless of
  which checkpoint originally shipped them.
- Explicit CP6-scope tagging for exactly these three pages, in the audit
  register (section R1.3/R1.4):
  - line 1708: `AUD-A01 | ... | CP6 recovery BS/rework; ...`
  - line 1710: `AUD-A03 | ... | CP6 cutting/pickup; ...`
  - line 3451: "... attendance/payroll, **cutting/pickup**, laundry/QC/FG,
    **BS/rework**, sales reserve/return, ... tetap memakai kontrak yang benar."
  - line 4380 (`CROSS-T01`): "... → **cutting/pickup** → laundry pending →
    partial QC/FG → invoice laundry"
  These confirm Cutting, Pickup and BS/rework are explicitly inside CP6
  audit/closure scope (migration filenames' "cp5_..." labels are historical
  checkpoint-of-origin naming, not evidence they're out of CP6's register —
  AUD-A01/A03 place them under "CP6 recovery" / "CP6 cutting/pickup").
- Line 1691 area is a reminder-family scoping note (manual/evaluator/
  scheduler distinctions for CP7 reminders); it does not carve WIB-time
  input out of CP6 — the operative scoping text for these three pages is
  AUD-A01/A03 above.
- **P1 justification:** operators are explicitly Indonesia-based (Jakarta
  business timezone WIB, but Indonesia spans WIB/WITA/WIT — Asia/Makassar,
  Asia/Jayapura). The probe (below) shows Asia/Makassar (WITA, UTC+8) alone
  produces a 1-hour shift versus WIB, which can move a record across a WIB
  business-day boundary for any cut/pickup/physical event near midnight —
  directly contradicting the invariant at line 3820 and potentially
  corrupting downstream business-date bucketing
  (`erp._cp3_business_date`, WIP status day boundaries, reporting). This is
  consistent with a P1 (data-correctness / financial-report-adjacent)
  severity, not merely cosmetic.

## Independent probe
Ran `tzprobe.mjs` (reproduces the exact expressions at the cited line
numbers) under multiple `TZ` values:

```
TZ=UTC:               legacy=2026-09-20T00:30:00.000Z  wib=2026-09-19T17:30:00.000Z  equal=false
TZ=Pacific/Kiritimati: legacy=2026-09-19T10:30:00.000Z  wib=2026-09-19T17:30:00.000Z  equal=false
TZ=Asia/Makassar:      legacy=2026-09-19T16:30:00.000Z  wib=2026-09-19T17:30:00.000Z  equal=false
TZ=Asia/Jakarta:       legacy=2026-09-19T17:30:00.000Z  wib=2026-09-19T17:30:00.000Z  equal=true
TZ=America/Los_Angeles:legacy=2026-09-20T07:30:00.000Z  wib=2026-09-19T17:30:00.000Z  equal=false
```
Confirms: the `new Date(x).toISOString()` expression used by all three pages
only matches the correct WIB conversion when the executing device's TZ is
already `Asia/Jakarta`. Any other device timezone (including the
domestic Asia/Makassar/WITA case, off by exactly 1 hour) produces a
different, wrong instant.

## Residual
- No live browser + Supabase round trip executed (no network/DB available);
  confirmation is static-code + isolated Node probe, same method as the
  original finding.
- Operators could be operationally required to keep device clocks on WIB;
  this would reduce real-world likelihood without changing the code defect.
  No such enforcement exists in code (A.3), and the contract explicitly
  disclaims relying on device clock ("Jam perangkat tidak menggantikan
  waktu bisnis WIB"), rejecting that exact mitigation as sufficient.
- The accessory-issue endpoint's `+07:00`-format guard is corroborating
  evidence of the finding's pattern (some flows fixed, these three not),
  not a mitigating factor for the three named pages.

## Verdict: CONFIRMED

Justification: All three citations are accurate (line numbers, code
content) and reachable through the CONNECTED runtime, which is exactly the
runtime that also carries the two "correct" pages (Laundry/QC) — so there is
no reachability gate distinguishing them. No wrapper (`useProductionMutation`)
or server RPC (`erp.save_cutting_group_before_sewing_v2`,
`erp.save_cutting_pickup_v1`, `erp.save_bs_resolution_action_v1`) normalizes
or validates the timezone offset of `cut_at`/`picked_up_at`/`physical_at`;
a sibling endpoint (`save_accessory_issue_action_v1`) shows the team can and
does add exactly such a guard, but it is absent here. The Node probe
independently reproduces the device-offset-dependent instant shift. The
contract's line-3820 invariant ("Jam perangkat tidak menggantikan waktu
bisnis WIB") is a project-wide, unscoped rule, and the audit register
explicitly places Cutting/Pickup (AUD-A03) and BS/rework (AUD-A01) inside
CP6 scope, so this is not an out-of-scope CP5 legacy issue.

Recommended priority: **P1** (confirmed as filed). Justification: silent,
device-dependent corruption of a business-critical timestamp used for
WIB-day bucketing and downstream sequencing (`picked_up_at` vs `cut_at`
ordering, WIP status transitions, potential report/business-date
misclassification near day boundaries), affecting three high-traffic
production-floor entry points, with no server-side or UI-side WIB
enforcement, in a codebase that demonstrably treats this exact class of bug
as fail-closed-worthy elsewhere (accessory issue endpoint).
