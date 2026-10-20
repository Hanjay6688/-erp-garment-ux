# OW01 per-kind delivery audit and accepted fixture map

Read-only source review at `ff587d89d110d871c084770629beb8f508503b55`.
This file records independent expectations before the proposed delivery module
is applied or run. No Native/database/browser execution was performed here.
The reported 86 PASS cases are existing evidence; they do not imply every kind
has a committed fake-provider receipt.

## Existing evidence by kind

`Q` means an asserted queued `net.http_request_queue` request/body in the
transaction; `P` means a committed request matched to a genuine fake-server log
and reconciled response. A source/collector assertion is weaker than Q.

| Kind | Strongest explicit existing delivery evidence | Exact source anchor |
| --- | --- | --- |
| MANUAL_REMINDER | P, real pg_cron-triggered owner reminder | `cp7_wa_forward_cases.py:races.pg_cron_ticks` |
| FABRIC_BELOW_MINIMUM | P, race and desktop/mobile owner journeys | `races.end_to_end`; `cp7_wa_forward_browser.mjs:ownerJourney` |
| ACCESSORY_NEED | P, committed concurrent sender plus desktop/mobile | `cp7_wa_accessory_transport_cases.py:two_ticks_one_receipt`; accessory browser |
| ACCESSORY_AT_REORDER_POINT | Q; browser edits minimum but never sends it | `cases.accessory_forwarded`; browser material journey |
| FG_AT_REORDER_POINT | Q; browser edits formula/manual point but never sends it | `cases.fg_forwarded`; browser FG journey |
| AR_DUE | Source/collector/current balance/episode; no explicit per-kind P | `cases.ar_ap_sources`, WA disabled in that fixture |
| AP_DUE | Source/collector/current balance/resolve; no explicit per-kind P | `cases.ar_ap_sources`, WA disabled in that fixture |
| PRODUCTION_GAP | Q with live reduced-need body | `cases.analysis_gap` |
| FABRIC_NEED | No explicit positive WA-delivery fixture | `analysis_gap` explicitly asserts no alert without a policy |
| OPENING_AR | Q; `fake_message` result flag is not P | `cp7_wa_obligation_cases.py:opening` and `sent` |
| OPENING_AP | Q; same shared queued request as opening AR | same |
| PAYROLL_AP | Q; later source mutations are still in the savepoint case | `payroll` and `sent` |
| ACCESSORY_AP | Q, allocation remains unknown; later payroll payment | `accessory` and `sent` |
| LAUNDRY_AP | Q after actual inverse | `laundry` and `sent` |
| LAUNDRY_RECEIPT | Q, not a second known payable | same |
| LAUNDRY_OPENING_UNINVOICED | Q, both opening receipts remain unknown | `laundry_opening` and `sent` |

There are 15 system kinds plus MANUAL_REMINDER. Thirteen system kinds lack an
explicit asserted P path. An incidental preexisting row possibly included in
another message is not a per-kind receipt oracle.

`obligation.sent()` calls `send_tick`, reads `dispatch`, and checks `wa.queued()`.
`wa.queued()` reads the request queue in that same transaction. The ordinary
Native runner rolls each case back to its savepoint; pg_net sends after commit.
The existing seven obligation cases do not call a provider worker, commit, wait
for its answer or inspect `fake_log()`. Their useful source/queue tests should
remain; their captions must describe that tier honestly.

The real provider plumbing already exists: `_provider_worker` selects the
disposable race database; `_committed` commits setup/send; `_wait_answer` waits
for the actual `net._http_response` row; `wa.fake_log()` reads docker log lines
beginning `FAKE_REQUEST`. The fake HTTP handler emits phone/text/key_ok/status,
never the key. Match those fields and the exact stored dispatch body.

## Thirteen isolated fixture builders

Use one predeclared committed race per kind so the accepted modes runner makes
a fresh race copy for each. Configure only the case's selected kind, no digest,
no quiet hours, no repeat and no automatic analysis. These are explicit test
choices. Create the settings owner before any owner-bound staged capture.

All amounts below are fixed existing fixture oracles, not new financial
calculations. Build every source/payment/allocation before the frozen boundary
and first send. Do not invoke an entire old `cases()` closure: several old
closures intentionally pay/reverse documents after queueing.

| Kind | Existing accepted helper calls | Expected target/source fact before send |
| --- | --- | --- |
| AR_DUE | `wa.ar_overdue(cur,today)` | `f['key']`; Native original500, paid200, remaining300; actual due yesterday |
| AP_DUE | `wa.ap_overdue(cur,today)` | `f['key']`; final material payable500; actual due yesterday |
| FG_AT_REORDER_POINT | `wa.formula.item(...,140)`, `sell_days(...,PATTERN)`, `profile(...,lead_days=7)` | `f['target']`; exact accepted oracle point, raw current free `140-sum(PATTERN)`, WIP complete0 |
| ACCESSORY_AT_REORDER_POINT | `formula.accessory(...,280)`, `accessory_days(...,SPARSE)`, `save_material(admin,...,lead=20,estimate={moq:'5000',usage_month_qty:'300',buffer_days:'5'})` | accessory material ID; Native free180, minimum250, basis ESTIMATE; source unit copied |
| PRODUCTION_GAP | `wa.remv2.plan_target(cur,today,subject=owner)` then explicit public `policy(...,'PRODUCTION_GAP','PCS',subject=owner)` | `r['target']`; exactly one ACTIVE snapshot condition, raw source value/state retained; own live recheck STILL_OPEN |
| FABRIC_NEED | Exact positive recipe/staged sequence below | exact target/material condition; source additional_external ASSUMED176, not UNKNOWN0 or a fabricated physical purchase quantity |
| OPENING_AR | `other.opening.bb.financial_fixture(...,documents=[('CUSTOMER_RECEIVABLE','WAF-AR','100.00','30.00')])` | `other.key(kind,f['balances']['WAF-AR'])`; Native remaining70, due missing => DATA_REVIEW |
| OPENING_AP | same helper with `('SUPPLIER_PAYABLE','WAF-AP','100.00','35.00')` | Native remaining65, due missing => DATA_REVIEW |
| PAYROLL_AP | `other.installments.fixture(cur,today)` then `other.installments.act(cur,f)` | `other.key(kind,f['payroll'])`; actual approved1000/payment600/remaining400 before freeze |
| ACCESSORY_AP | `other.accessory_fixture(cur,today)` then `other.allocate_accessory(cur,f)` | `other.key(kind,f['credit']['event_id'])`; actual credit12, allocation is not settlement; remaining UNKNOWN/reason ALLOCATION_NOT_SETTLEMENT |
| LAUNDRY_AP | `other.laundry_fixture(cur,today,invoice=True)` | `other.key(kind,f['invoice'])`; final Native payable17312.90, ACTIVE; do not pay it after queue |
| LAUNDRY_RECEIPT | `other.laundry_fixture(cur,today,invoice=False)` | `other.key(kind,f['line'])`; actual estimated receipt, VALUE_PENDING/remaining UNKNOWN; estimate is not final AP |
| LAUNDRY_OPENING_UNINVOICED | `other.laundry_opening_fixture(cur,today)` | both actual opening receipt IDs; remaining UNKNOWN for both, including the estimated70000 receipt |

The `other` helpers are from `scripts/cp7_other_obligation_cases.py`; `wa` helpers
are from `scripts/cp7_wa_forward_cases.py`. Existing fixtures may also create
comparison documents. Select target IDs explicitly and require the chosen
kind's entire dispatched set to match accepted current source rows; do not
assume the fixture creates only one row in the whole database.

## Positive FABRIC_NEED sequence

This uses the accepted **beginning** of
`cp7_p19_reminder_v2_cases.py:cases.fabric_held` and the source proof in
`cp7_p18_fabric_rule_cases.py:cases.active`. It does not run the later source
change or the local preview claim.

```python
# Settings/key/owner first; these explicit fixture choices are not defaults.
s = wa.setup(cur, kinds=['FABRIC_NEED'], detail='DETAILED', max_items=20,
             repeat_minutes=0, digest_times=[], quiet_enabled=False,
             analysis_every_minutes=0)
owner = s['owner']
f = wa.remv2.physical.bound(cur, today, subject=owner)
_, _, done, _ = wa.remv2.staged.staged_done(cur, today, subject=owner)
r = dict(run=done['run_id'], identity=wa.remv2.identity(cur, done['run_id']))
wa.remv2.ready_set(cur, r['run'], owner)
rows = [c for c in wa.remv2.conditions(cur, r['run'], 'FABRIC_NEED', subject=owner)
        if c['target_key'] == f['target']]
assert len(rows) == 1
c = rows[0]
assert c['state'] == 'ACTIVE' and c['value']['state'] == 'ASSUMED'
assert Decimal(c['value']['value']) == Decimal('176')
# Exact unit from the recorded source, never an invented M/YD conversion.
rev = cur.execute("select coalesce(max(revision),0) from cp7_reminder_native.rule_policies "
                  "where rule_id='FABRIC_NEED' and scope_kind='GLOBAL' and scope_key='*'").fetchone()[0]
wa.remv2.policy(cur, r, 'FABRIC_NEED', c['value']['unit'], revision=str(rev), subject=owner)
assert wa.drain(cur)[-1] == 'ANALYSIS_CHECKED'
v = wa.remv2.recheck(cur, r['run'], c['key'], owner)
assert v['verdict'] == 'STILL_OPEN'
assert v['reason'] == 'FABRIC_NEED_UNCHANGED_SINCE_SNAPSHOT'
assert Decimal(v['numbers']['snapshot_value']) == Decimal('176')
```

`physical.bound()` creates an actual ten-unit receipt and an explicitly reviewed
source recipe of two per good piece; exact bound WIP yields gap93, gross186 and
external176 **ASSUMED**. That quality must remain exactly the stored source
quality. Fetch the staged Original and assert condition `value` equals that
Original's exact `additional_external` object, including its raw decimal scale,
unit, refs and assumptions. Never convert the fixture assumption into proof of
physical installation/consumption. Do not call `select_profiles(...,True)` or a
new recipe mutation after the staged source; it changes the captured source.

`analysis_every_minutes=0` is safe here: actual `analysis_unit` processes the
owner's already finished run before its automatic-analysis switch. No local
binding/claim/finish RPC is necessary; require zero local-preview claim and
recorded recheck rows for the new run throughout delivery.

## Common committed delivery expectation

Freeze after Native fixture writes and policy setup: original business
documents and balances, raw stock/HPP/journal facts, and the existing Native
boundary. For analysis, also freeze the staged Original/page identity. Avoid
comparing live read timestamps as business data.

Run collector/analysis checks, assert exact public Reminder row IDs/kind/detail,
and same-episode round0 PENDING outbox with no prior attempt. Inside the existing
provider-worker context, commit one `send_tick`; do not write source data while
waiting. Match exactly one new `FAKE_REQUEST` to that dispatch body, fake number,
key_ok=true and status200. Wait for its real response and reconcile normally.
Require PROVIDER_ACCEPTED/200, exact dispatch_items links, target round0
ACCEPTED/attempts1, and no new request/dispatch on the next tick. Check the
frozen source, balances and Original immediately after send commit while the
provider is still independent, and again after reconciliation. Leave old source
transition and queue-only cases intact.

No synthetic `_http_response` row, direct outbox/alert insertion, rewritten
source amount/date, or provider-key logging can count as this proof. The
expected-first module/manifest and its integration are owned by the transport
reviewer in this proposal folder; runtime results remain pending.
