"""XA12-F4 (Fable, round 12): independent reproduction of the writer's finding F4 (commit 5e1ae83): an opening payable settled
from an imported advance (no cash account, no credit row) is sent by the BB import workspace with 'reversible' = NULL
(BB SQL: `A and B and cash_account_id is not null or (POSTED and credit_kind in (...))` = false or NULL = NULL), and the import page
(`src/initialImportBB.ts:98`: `typeof s.reversible !== 'boolean'` -> throw) refuses the whole batch. BC wraps the flag in
coalesce(..., false). Phases: pre_bc = product with BB but without BC (expect COUNTEREXAMPLE), after = with BC (expect PASS).
Setup reuses the writer's helper modules (REUSED fixture code); the read, the oracle and the page predicate are the auditor's.
Oracle: the workspace contract of ALL (M cutover states) gives every settlement a yes/no reversibility; a settlement paid from an
advance is not reversible there (it is reversed through the advance). A flag that is not a boolean hides the batch = harm.
"""
import json,traceback,uuid
from datetime import timedelta
from decimal import Decimal
import cp6_bb_probe as bbp
import cp6_initial_import_prepayment_trial as prepayment_trial
api=bbp.api;D=Decimal
def one(cur,sql,*args):
    api.admin(cur);return cur.execute(sql,args).fetchone()[0]
def bc_installed(cur):return bool(one(cur,"select exists(select 1 from erp.schema_migrations where version='v2.6.20bc')"))
def settlements(cur,batch):
    return [(b['number'] if 'number' in b else b.get('document_number'),s) for b in bbp.ws(cur,batch)['opening_balances'] for s in b['settlements']]
def page_refuses(flags):
    """The import page's own predicate (src/initialImportBB.ts:98): any settlement whose flag is not a boolean throws."""
    return any(not isinstance(f,bool) for f in flags)

def f4_advance(cur,today):
    f=prepayment_trial.fixture(api,cur,today,'SUPPLIER')
    target=prepayment_trial.state(api,cur,f)['targets'][0]['id']
    prepayment_trial.manage(api,cur,f,'APPLY',today,target_id=target,amount='12.75')
    rows=settlements(cur,f['batch'])
    adv=[s['reversible'] for _,s in rows if s['method']=='ADVANCE']
    all_flags=[s['reversible'] for _,s in rows]
    bc=bc_installed(cur);refuses=page_refuses(all_flags)
    if not bc:
        status='COUNTEREXAMPLE' if (adv and None in adv and refuses) else 'INCOMPLETE'
        why='BB workspace sends reversible=NULL for the advance settlement; page predicate refuses the batch (writer F4 CONFIRMED pre-existing)' if status=='COUNTEREXAMPLE' else 'no advance settlement with NULL flag reproduced'
    else:
        ok=adv==[False] and not refuses
        status='PASS' if ok else 'FAIL';why='advance settlement flag is boolean false and the page accepts the batch' if ok else 'BC still sends a non-boolean or a wrong flag'
    return dict(status=status,classification=why,bc_installed=bc,advance_flags=adv,all_flags=all_flags,page_would_refuse=refuses,
                settlements=[dict(number=n,method=s['method'],status=s['status'],amount=s['amount'],reversible=s['reversible']) for n,s in rows])

def f4_cash_control(cur,today):
    """Control: a cash settlement of an opening supplier payable keeps reversible = True in both phases (the BC coalesce must not flip it)."""
    fx=bbp.financial_fixture(cur,today,documents=[('SUPPLIER_PAYABLE','INV-F4C','100.00','35.00')])
    bbp.act(cur,'OPENING_SETTLEMENT',fx['batch'],operation='SETTLE',balance_id=fx['balances']['INV-F4C'],amount='20.00',
            effective_date=str(fx['cutover']+timedelta(days=1)),cash_account_id=fx['cash'],reason='XA12 F4 control settlement')
    rows=settlements(cur,fx['batch']);flags=[s['reversible'] for _,s in rows if s['method']=='CASH']
    ok=flags==[True] and not page_refuses([s['reversible'] for _,s in rows])
    return dict(status='PASS' if ok else 'COUNTEREXAMPLE',bc_installed=bc_installed(cur),cash_flags=flags,
                settlements=[dict(number=n,method=s['method'],status=s['status'],reversible=s['reversible']) for n,s in rows])

def cases(cur,today):
    def wrap(fn):
        def run():
            try:return fn()
            except Exception as exc:return dict(status='INCOMPLETE',error=str(exc)[:600],trace=traceback.format_exc()[-1500:])
        return run
    return [('XA12:F4_BC_STATE',wrap(lambda:dict(status='PASS',bc_installed=bc_installed(cur)))),
            ('XA12:F4_ADVANCE_SETTLEMENT_FLAG',wrap(lambda:f4_advance(cur,today))),
            ('XA12:F4_CASH_SETTLEMENT_CONTROL',wrap(lambda:f4_cash_control(cur,today)))]
