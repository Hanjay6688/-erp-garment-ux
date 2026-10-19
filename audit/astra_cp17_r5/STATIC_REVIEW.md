# Astra r5 — independent source review

Candidate `17fa25075ba77f0853c3c16f504288ace03eec35`, tree `65f778479093d869a3354c0b9f19b4d9a541d98a`.
Evidence origin `INDEPENDENT_SOURCE_REVIEW`; all conclusions in this file are **STATIC_QUALIFIED**, not runtime acceptance.

## Identity and scope

`IDENTITY.json` records actual Git object identities. Compared with r4, src, release, migrations, dev, scripts/cp7-src, tests and package/lockfile are unchanged. scripts and workflow trigger differ. Candidate→writer head `2766a909` is nine documentation paths only. Pro Max bytes independently hash to `5752e96df751de5ebe4b86d3f572cffa1bbe94eb42bf8e283fa6e04f9f593639`. No AGENTS.md exists in the candidate tree. CLAUDE.md and owner decisions through D17-2 apply.

## R5-01 — payroll checker

The patch changes exactly one checked anchor in `run_v263a_payroll_integrity_checks`: adds a LEFT JOIN keyed by `source_type='FG_REPAIR'` plus wage primary ID, and adds that row's contractor to COALESCE. PRODUCTION and REWORK joins already restrict their own source_type, so an unrelated record sharing a UUID cannot win through another source branch. The added source resolves to the same contractor field as the accepted AX wage model. The wage primary key prevents multiplicity amplification. Missing wage/contractor stays NULL and `IS DISTINCT FROM` still detects it. The existing `status <> 'REVERSED'` predicate stays intact; all other checker text stays byte-identical. `STATIC_REWRITE_CHECKS.json` proves checked anchor count and inverse round trip on the predecessor source.

Path: AX repair source→FG wage/accrual→CP7 source card→SAVE/POST Nota→payroll work line→checker→readiness/report. The repair does not write a wage, payroll, stock, HPP or GL fact. It repairs the detector's source resolution. Runtime must still prove a valid source remains quiet, wrong/missing source is detected, and cancelled histories remain excluded. Own expected: 1+3 PCS ×2000 =8000, only one active allocation and no new physical/cost/cash effects from Nota.

## R5-02 — report readers

Eleven reader definitions contain 69 literal account lookups covering exactly17 core keys. All11 are STABLE and the account lookup itself is STABLE. The independent textual transform matches the writer transform exactly, and removes no filter, number, join, status, permission call or declaration. The changed operation is an uncorrelated scalar subquery around each literal lookup. Calls with row-dependent keys are unchanged.

The reader family covers owner financial position/performance, current and pre-scope v268 financial checks, v267 truth checks, PO/non-PO HPP books, sale lifecycle PO amount, opening credits, initial prepayments, pocket issues and pocket period books. Their higher-level users include period close readiness, owner finance/report, CP7 direct/staged analysis, Business Report, AI and reminder projections. `READER_IMPACT_INDEX.json` is a navigational index, not proof that every caller was dynamically tested.

The Native mapping guard denies deleting or renaming every core key, and validates a replacement account exists, is active and has the required account type. The R5 install separately requires all17 mappings present and non-NULL. Changing a mapping to another valid account remains possible. A missing mapping and a missing/unauthorized actor are different cases: `account_id()` also calls `require_internal()`. Lazy execution may alter an internal helper's empty-input refusal even when mappings exist. The own context case records any such difference without assuming public reachability or automatically calling it a security bypass. Public role boundaries must be judged on public facades/HTTP, not a database-owner diagnostic.

The review captures both Python and SQL enforcement: Python `wrap` checks volatility, listed keys, count, and already-wrapped state. SQL `block` checks count and already-wrapped state, while the complete F03 installer computes exact expected definitions and rejects undeclared changes before commit. Do not claim the SQL block alone checks every Python condition. Drift/missing-map refusal and all12 changed-function metadata restoration remain runtime gates.

## Composition and restoration

F03 executes the report optimization after the note report and kasbon overlays, so its expected definitions wrap the preceding overlay rather than resurrect Native originals. `note_report.capture` captures payroll and the nine additional report readers while preserving the owner report and v267 originals already present. `expected_definitions` combines those overlays in the same order. `note_correction_verify` now checks the wrapped note overlay and continues checking the separately retained original/overlay hash receipt. All F03 users share these capture/expected functions; the two explicitly updated probes additionally verify the new bundles. `cp7_restore_state` compares the complete operational/platform/Auth/schema boundary and all function definitions, owners and ACLs after replay/drop. These declarations support installation design, not an assertion that this run has restored successfully.

## Surrounding invariants

Dated cash guard, wage-after-payable guard, cutover floor, HPP policy, public-route guard, all economic SQL, and UI source are unchanged from r4. Regeneration composes the same bodies plus the two declared deltas. Their behavior is being exercised again by CP17; byte invariance alone does not close runtime claims. The numeric own public-report oracle uses 100.01/66.67/33.34 and 221.11/97.03/124.08 (revenue/HPP/profit), computed independently using decimal arithmetic. A concurrent mapping commit must leave all rows of one statement on one snapshot, then affect the next statement with an honest BLOCKED reconciliation.

## Limits

The SQL under `source/` is extracted from baseline bootstrap and explicit named CREATE definitions in the candidate's ordered migration/release sources. It is a review aid, **not an installation manifest or proof of the installed body**: dynamic alterations and later note/kasbon overlays are assessed separately and CI records the installed definitions. Imported fixture construction has writer provenance; the new expected values and comparisons have Astra provenance. The full unchanged app and every prior detector variant are not freshly reaudited by this focused r5 retest. Hosted Enteng, production, backup Drive, full original-engine CP2 restore, shadow real data, iPad and WA live remain outside this execution.

PostgreSQL17 STABLE snapshot semantics checked against the official [function volatility documentation](https://www.postgresql.org/docs/17/xfunc-volatility.html). Supabase changelog checked; no runtime/dependency version is upgraded in this audit.
