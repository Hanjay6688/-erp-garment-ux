# S03 — closed legacy HPP reader metadata

Only two existing private reader returns are decorated. Existing public HPP
RPCs, current Owner/Admin+finance.hpp.view authority and all financial/access
guards stay unchanged. Unaffected ordinary JSON is returned exactly as before.
Existing S03 wire7e91 is unchanged; this is additional legacy HPP reader wire.

Owned pool objects add exactly one optional object, never null:

```json
{
  "attendance_choice": {
    "domain": "ATTENDANCE_PERIOD_CHOICE",
    "decision_id": "canonical PostgreSQL UUID",
    "allocation_id": "canonical PostgreSQL UUID",
    "source_period_start": "YYYY-MM-DD",
    "source_period_end": "YYYY-MM-DD",
    "output_period_start": "YYYY-MM-DD",
    "output_period_end": "YYYY-MM-DD",
    "output_period_closed": false
  }
}
```

The eight keys are closed. Source dates equal the Native header P1; output is
strictly later P2. `period_closed` remains the original P1 flag; the output flag
uses output end<=the same workspace closed_through. Owned ACTIVE/CANCELLED pools
have `actions:[]` permanently, including after owning cancel, decision correction
or reversal. Ownership derives from immutable allocation.pool_id, not ACTIVE or
current-choice filters. No owned DRAFT/VOIDED marker or dual marker is emitted.
A cached/mismatched Native composite or inconsistent allocation/inverse snapshot
raises `CP7_S03_HPP_READ_CHANGED`; reload rather than fall back to ordinary actions.

Ordinary historical CANCELLED/VOIDED pool rows in an exactly held source period,
and held period previews, add exactly this optional four-key object:

```json
{
  "period_hold": {
    "domain": "ATTENDANCE_PERIOD_CHOICE",
    "decision_id": "canonical PostgreSQL UUID",
    "source_period_start": "YYYY-MM-DD",
    "source_period_end": "YYYY-MM-DD"
  }
}
```

This is a live exact-source CARRY/EXPENSE hold, not pool ownership. Affected
ordinary rows have actions[]. Ordinary ACTIVE/DRAFT+current hold is inconsistent
and raises READ_CHANGED. Matching uses exact current_v1(start,end), never overlap
or the carried output period. Unrelated normal P2 payroll/pools remain ordinary.

A held preview retains its source period/closed flag/history references and
uses the existing BLOCKED contract: `can_create:false`, `pos:[]`, and null
numerator_amount, denominator_qty, unit_cost_per_sewn_pcs, source_count,
destination_count, po_count, manifest_sha256 and review_token. Its existing
`blocker:{code,message}` has exact code **CP7_S03_PERIOD_HELD** and a plain Owner
choice explanation. There is no fake existing_pool, invented zero, usable token
or READY-parser exception. Unheld previews retain their exact original JSON.

The UI must accept exactly the original keys or original+one closed object,
reject both markers/unknown/null metadata, keep canonical PG UUIDs (all version
and variant bits), and validate source/header/date/cutoff relationships. Suppress
legacy cancel/replace/create and the misleading P1-closed cancellation warning
for S03-owned rows. Show sourceP1 and outputP2 and open the Owner's S03 workspace
using only source dates; fetch a new64-character S03 preview. Never carry over a
legacy32-character token, pool action/UUID or assume a historical decision is
still current. Admin sees explanation and gains no S03 action. Retire stale forms
and translate period/owning-context/access refusals without changing PG codes or
uncertainty recovery. All browser/real-Auth acceptance remains unqualified here.
