# Explicit lawful qualification fixture API v1

Load `lawful_fixture.py` by its pinned path with `importlib.util`; do not assign
over an inherited module's `earned`, `source` or financial oracle functions.
The helper is a qualification dependency, never an ERP/public RPC.

```python
payroll_id = lawful.earned(cur, source, output_day, Decimal('20.02'),
    core=frozen_original_cases_module, evidence=report, approve=True)
```

`source` is the unchanged dictionary from `core.f.source`: `day` date,
`contractor`/`payroll`/`owner` canonical PostgreSQL UUID strings, `capture` original
Native manifest. The source amount for these cases is exactly1000.03 and its
original approved payroll is authoritative. `output_day > source['day']` and
positive exact daily cents are required. This API returns a new P2 payroll UUID.
The exact original P1 worker is looked up from posted payroll attendance items;
the actual current eligible worker set must equal that one ID. Additional or
missing workers explicitly refuse. No employee is retired or assigned synthetic
ABSENT/OFF/zero. After rate wait, eligibility is reread. The installed
`erp.set_worker_daily_rate_v1(uuid,numeric,date,text,uuid,bigint)` uses the fresh
worker version, P2 effective date, reason and newUUID. Attendance is explicit
PRESENT, posted through the existing writer; Native PREPARE/APPROVE follow.
Only the new DRAFT payroll header is an administrative fixture. No posted
attendance/payroll/journal/stock is inserted as a fabricated fixture.

For the finished browser fixture, scope the retained production contractor only
around retained `finish_fixture` exactly as before, obtain P1 `source` before
the actual output, and call the API above using that same source/contractor.
The API does not change accounting-control dates. Its evidence includes exact
worker IDs, Native rate receipt, P2 actual items and full unchanged P1 facts.

`reopen_source(cur,source,*,core,evidence=None)` is specific to the prepared
correction case after current-day allocation cancellation. It first requires the
closed-source REVERSE no-effect negative, then the existing real OWNER period
workspace→REOPEN to P1-1 with fresh token/reason/newUUID. Original filings and
source facts remain exact. It must not be used as an administrative backdate
bypass or replace a different case's intended closed-period refusal.

`finished_facts(cur,fixture,*,core)` returns direct raw `FG`, `current_HPP`,
`HPP_history`, `HPP_components`, `journal_headers`, `journal_lines`, and numeric `GL` facts.
`assert_valuation(before,after,own_cost,*,lot,baseline_cost,before_gl,after_gl)`
requires the retained one PRODUCTION lot/ten-piece fixture and only the exact
Native receiving cache change. Unknown columns/rows or changed whole SALE
facts refuse. `observe_valuation(...)` captures and retains the raw after state.
`assert_cancelled(cur,fixture,before,*,after_allocation,core,evidence,made,cancelled,oracle)`
requires full FG exact baseline, current HPP quantity/value and GL exact,
unchanged baseline facts, and the actual linked Native journal inverse including
all dimensions/signs/amounts and economic/book dates. Raw append-only history is
retained; it is never projected as if new inverse IDs did not exist.

`after_allocation` is REQUIRED, with no fallback. Keep the full direct snapshot
returned by `observe_valuation` before cancellation. Every allocation-era posted
header, full journal line, intermediate HPP version and HPP component must still
exist unchanged afterwards. Only the bound owning pool header may change from
POSTED to REVERSED, and Native HPP `is_current` pointers may retire to false.
Inverse signs/dimensions/amounts compare to frozen pre-cancel lines. Comparing
two rows first reread after cancel could wrongly accept a symmetric rewrite;
that old oracle gap has two preserved RED controls and a fixed successor.

The helper's final bytes/SHA are pinned by CONFIG.fixture_API and SOURCE.
This API does not claim qualification. A future browser successor must explicitly
bind it and still require fresh full Native14/used/outer/all5 actual proof.
