# Recovery / unknown browser — independent oracle freeze

Candidate product a095a9d804d29643721e18635c2c3e26adcd56ea, tool9dd7bc2b9309d008e8a2e50d81876d831f3e5ea7. Existing findings CP6-05 and CP6-06; do not create duplicate IDs. Four cases, all BELUM until native execution. Source manifest: `audit/scenarios/recovery_round8/MANIFEST.json`.

## Incremental source notes

- `src/PatternPage.tsx:82–102` read: each save uses a fresh UUID, even when the prior reply was ambiguous. On error the same editor remains. Pola has stable code/revision, so uniqueness may prevent a second row; never infer duplicated financial effects merely from a changed UUID.
- `src/AccessControlPage.tsx:186–209` read: duplicate-role save creates both a new CUSTOM code and a new UUID on every attempt. On error the duplicate editor remains. Use GUDANG template with every permission unchecked, no user assigned, disposable only; measure actual one/two rows rather than assume a duplicate.
- `supabase/migrations/20260902104937_erp_v2_6_17_access_pattern_wip_control.sql:751–818,954–978,1141–1195` read: real idempotency cache precedes writes; role storage is app_roles(role_code,role_name), pattern storage production_patterns(pattern_code,pattern_name). Pattern identity/name uniqueness may refuse a retry. Server behavior does not justify replacing an ambiguous client envelope.
- `src/useLaundryQcWorkspace.ts:28–50,115–130` read: initial workspace stays null after failed RPC; error and writer lock retained. Successful later read installs real workspace.
- `src/ConnectedLaundryPage.tsx:412–418,434–438` read: unavailable workspace renders0 in KPIs. `src/ConnectedQcFinalPage.tsx:314–335` read: queue/KPI fallbacks likewise0. Error banner/locked write are mitigating facts, not hidden.
- Browser host `scripts/cp6_auditor_browser_host.mjs:112–153` read: ui.login uses actual login form/Auth; page routing can inject transport failure; returned case results and page errors are recorded. Loopback-only contexts and disposable database remain enforced.
- Existing fixture helper `scripts/cp6_au_r1_probe.py:102–128` read: production creates10physical pieces sent to laundry; receipt makes10GOOD ready for QC. We use these actual business commands to establish nonzero truth, restore schema grants, and read the real Auth RPC before fault injection. Fixture has no direct quantity patch.

## Frozen cases and oracle

1. `G8UI:RECOVERY:PATTERN_COMMIT_REPLY_LOST`: fill actual Pola form, forward POST to product and receive true response in transport layer, discard reply before browser receives it. Confirm one committed row by SQL. Press unchanged Save again. **M:1679,3819** requires exact UUID/payload/expected-version retention and exact replay, one effect. A new UUID or non-replayed result is COUNTEREXAMPLE; first commit absent or setup failure is INCOMPLETE. Preserve database rows, both payloads and real server replies.
2. `G8UI:RECOVERY:ROLE_DUPLICATE_COMMIT_REPLY_LOST`: duplicate an existing role through UI with zero permissions/no assigned user. Same real commit/reply loss and retry. Oracle identical; count role definitions after each click. Report duplicate role only if database shows it. No privilege-escalation or financial-loss claim.
3. `G8UI:UNKNOWN:LAUNDRY_INITIAL_READ`: ordinary native fixture has10pcs outside factory. Real Auth workspace read must show >=10. Abort browser initial read; record error, all KPI values and write-lock indication. **M:3825** requires unknown rather than authoritative0. Remove only the transport fault and press Reload; HTTP200 and KPI matching real server value are positive control.
4. `G8UI:UNKNOWN:QC_INITIAL_READ`: same, with10GOOD ready for QC. Error banners and locked actions are explicitly preserved in evidence. No claim of posting bypass or false financial report finality from a dashboard KPI alone.

The fault changes network delivery, not product replies, data, guards or permissions. Empty native factory contributes no case coverage. A transport/setup error is INCOMPLETE. Expected network failures are captured as case evidence; do not confuse them with unhandled page exceptions. All result statuses must come from per-case JSON, not workflow color.

Next: commit hashes and workflow phase together; capture run/job; collect four results and cleanup; update CP6-05/06 only to the level actually demonstrated.
