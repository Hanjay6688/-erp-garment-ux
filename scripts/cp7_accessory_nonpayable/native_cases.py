"""Nine Native economic/date/inverse/sales cases, prepared and unexecuted.

No owning workflow or acceptance is supplied. Actual Auth, two-session
access/locking and normal-App settings browsers remain separate
required work. The caller must retain each real strict-group result and the
complete outer backup/restore, all rows/sequences, Auth and all package gates.
"""
from pathlib import Path
import json,sys

FIRST_IDS=(
    'NONPAYABLE_NATIVE_POSITIVE_HPP_ZERO_REIMBURSEMENT_FROZEN_HISTORY_AND_REPLAY',
    'NONPAYABLE_NATIVE_EXPLICIT_NORMAL_POLICY_REIMBURSEMENT_REGRESSION',
    'NONPAYABLE_NATIVE_NORMAL_PICKUP_SPECIAL_GOOD_PHYSICAL_DATE',
    'NONPAYABLE_NATIVE_SPECIAL_PICKUP_NORMAL_GOOD_PHYSICAL_DATE',
    'NONPAYABLE_NATIVE_MISSING_CATEGORY_EFFECTIVE_DATE_ATOMIC_GOOD_REFUSAL',
    'NONPAYABLE_NATIVE_NO_INITIAL_JOURNAL_CUMULATIVE_CENTS_AND_LAWFUL_INVOICE_INVERSES',
)
if __name__=='__main__':
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    from cp7_accessory_nonpayable.native_inverse_cases import IDS as INVERSE_IDS
    from cp7_accessory_nonpayable.native_sales_cases import IDS as SALES_IDS
else:
    from .native_inverse_cases import IDS as INVERSE_IDS
    from .native_sales_cases import IDS as SALES_IDS
IDS=FIRST_IDS+INVERSE_IDS+SALES_IDS

def fixture_module():
    # This package import has no ERP graph, connections or default bindings.
    from . import native_fixture
    return native_fixture

def source_controls():
    value=fixture_module().source_controls()
    from . import native_sales_cases
    sales=native_sales_cases.source_controls()
    if len(IDS)!=9 or len(set(IDS))!=9:raise ValueError('NONPAYABLE_EXACT_NINE_NATIVE_IDS_REQUIRED')
    return dict(status='PREPARED_NINE_NATIVE_CASES_NOT_EXECUTED',case_ids=list(IDS),
        fixture_sources=value,actual_Native_cases=0,actual_SQL_executed=0,production_go=False,
        inverse_source_prepared=True,sales_source_prepared=sales,inverse_Auth_two_session_browser_qualification_complete=False)

def finish(cur,modules,before_findings,**observations):
    modules.bc.api.admin(cur)
    after=modules.bc.findings(cur)
    new=modules.bc.new_findings(before_findings,after)
    if new:
        # The strict runner retains exception text before rolling the case
        # back. Preserve the actual detector deltas and completed economic
        # observations there so a failed case can be diagnosed from its first
        # immutable Original without rerunning an unchanged scenario.
        detail=dict(financial_findings_before=before_findings,financial_findings_after=after,
            new_financial_findings=new,completed_observations=observations)
        raise ValueError('NONPAYABLE_NATIVE_NEW_FINANCIAL_INTEGRITY_FINDINGS:'+json.dumps(
            detail,sort_keys=True,default=str,allow_nan=False))
    return dict(status='PASS',**observations,financial_findings_before=before_findings,
        financial_findings_after=after,new_financial_findings={},actual_Auth_HTTP_credit=0,
        actual_browser_credit=0,actual_two_session_credit=0,full_outer_restore_and_all5_required=True,
        production_go=False,independent_acceptance=False)

def ordinary_case(cur,today,state,*,initial_special=True,transition=None,history=False):
    fixture=fixture_module();modules=fixture.admitted_modules(cur,state)
    before=modules.bc.findings(cur)
    f=fixture.prepare(cur,today,modules,special=initial_special,transition=transition)
    fixture.post_good(cur,modules,f)
    nonpayable=initial_special if transition is None else transition
    first=fixture.observe(cur,modules,f);fixture.require_economics(first,f,nonpayable=nonpayable,hpp='20')
    # Native accrual replay is exercised on this same lot; no new GOOD or note.
    modules.bc.api.admin(cur);cur.execute('select erp.post_accessory_reimbursement_accrual(%s)',(f['lot'],))
    replay=fixture.observe(cur,modules,f)
    if replay!=first:raise ValueError('NONPAYABLE_NATIVE_ACCRUAL_REPLAY_CREATED_A_SECOND_EFFECT')
    history_proof=None
    if history:
        # The later CLEAR starts tomorrow, strictly after today's GOOD date.
        # Existing basis, entitlement absence and original accrual stay frozen.
        current=next(p for p in modules.bc.ws(cur)['policies']if p['key']=='ERP-DEC02')
        modules.bc.svc(cur,'SET_POLICY',dict(policy_key='ERP_DEC02',operation='CLEAR',
            expected_version=current['version'],reason='Native later clear must preserve historical GOOD'))
        from datetime import timedelta
        confirmation=fixture.confirm_date(cur,modules,today+timedelta(days=1))
        modules.bc.api.admin(cur);cur.execute('select erp.post_accessory_reimbursement_accrual(%s)',(f['lot'],))
        after=fixture.observe(cur,modules,f)
        if after!=first:raise ValueError('NONPAYABLE_LATER_POLICY_CHANGED_POSTED_GOOD_HISTORY')
        history_proof=dict(later_clear=confirmation,after=after,exact_history_unchanged=True)
    return finish(cur,modules,before,fixture=f,actual_initial=first,actual_replay=replay,
        later_policy_history=history_proof,physical_GOOD_date_basis=True,
        expected_accessory_HPP='20',expected_reimbursement='0'if nonpayable else'20',
        expected_new_entitlements=0 if nonpayable else 1,
        explicit_fresh_mandor_and_dated_policy=True,Native_fixture_constructor_code_unchanged=True)

def boundary(cur,modules,state):
    from .report_io import share_strings
    modules.bc.api.admin(cur)
    with modules.control.product_catalog(cur):
        modules.product.verify(cur,state)
        catalog=modules.product.runtime()[-1]
        return dict(actual_all22=share_strings(catalog._catalog_rows(cur),state['after']),
            full_data_and_sequences=catalog._data(cur))

def missing_date_case(cur,today,state):
    fixture=fixture_module();modules=fixture.admitted_modules(cur,state)
    before_findings=modules.bc.findings(cur)
    f=fixture.prepare(cur,today,modules,register_date=False)
    before=boundary(cur,modules,state)
    import psycopg
    cur.execute('savepoint nonpayable_actual_missing_date')
    error=None
    try:
        try:fixture.post_good(cur,modules,f)
        except psycopg.Error as caught:error=dict(sqlstate=caught.sqlstate,message=caught.diag.message_primary)
    finally:
        cur.execute('rollback to savepoint nonpayable_actual_missing_date')
        cur.execute('release savepoint nonpayable_actual_missing_date')
    if error!={'sqlstate':'P0001','message':'NONPAYABLE_CURRENT_POLICY_EFFECTIVE_DATE_REQUIRED: tetapkan tanggal berlaku ERP-DEC02'}:
        raise ValueError('NONPAYABLE_EXACT_NATIVE_MISSING_DATE_REFUSAL_REQUIRED:'+str(error))
    after=boundary(cur,modules,state)
    if before['actual_all22']!=after['actual_all22']:raise ValueError('NONPAYABLE_REFUSAL_CHANGED_CATALOG')
    a=before['full_data_and_sequences'];b=after['full_data_and_sequences']
    if set(a)!=set(b)or any(a[k]!=b[k]for k in a if not k.startswith('sequence:')):
        raise ValueError('NONPAYABLE_REFUSAL_LEFT_PARTIAL_BUSINESS_OR_JOURNAL_ROWS')
    allocations={k:dict(before=a[k],after=b[k])for k in a if k.startswith('sequence:')and a[k]!=b[k]}
    # PostgreSQL sequence allocations survive a failed posting. Preserve them
    # explicitly; only the owning full DB restore proves complete restoration.
    for key,pair in allocations.items():
        if (len(pair['before'])!=2 or len(pair['after'])!=2 or int(pair['after'][0])<int(pair['before'][0])
            or type(pair['before'][1])is not bool or type(pair['after'][1])is not bool):
            raise ValueError('NONPAYABLE_UNEXPLAINED_NATIVE_REFUSAL_SEQUENCE_CHANGE:'+key)
    return finish(cur,modules,before_findings,fixture=f,actual_error=error,before=before,after=after,
        every_business_row_and_catalog_restored=True,actual_sequence_allocations=allocations,
        sequence_reseed_performed=False,complete_sequence_restore_requires='OWNING_FULL_DATABASE_RESTORE',
        no_partial_GOOD_stock_or_journal=True)

def cumulative_cents_case(cur,today,state):
    fixture=fixture_module();modules=fixture.admitted_modules(cur,state);bc=modules.bc
    before_findings=bc.findings(cur)
    f=fixture.prepare(cur,today,modules,unit_cost='0.004',qty_per_good='0.1')
    fixture.post_good(cur,modules,f)
    initial=fixture.observe(cur,modules,f);fixture.require_economics(initial,f,nonpayable=True,hpp='0.004')
    if initial['original_accrual']:raise ValueError('NONPAYABLE_SUBCENT_START_MUST_HAVE_NO_INITIAL_JOURNAL')
    af=f['accessory'];invoice_fixture=dict(af,receipt=dict(purchase_id=af['purchase']),tag=af['code'],day=today)
    phases=[]
    for index,price in enumerate(('0.006','0.014','0.016')):
        payload=modules.invoice.payload(invoice_fixture,'1000',price)
        payload.update(invoice_date=str(today),received_at=bc.local_at(today,8),due_date=str(today))
        made=modules.invoice.finalize(cur,invoice_fixture,p=payload)
        bc.internal(cur,'process_cost_recalc_queue',100)
        current=fixture.observe(cur,modules,f);fixture.require_economics(current,f,nonpayable=True,hpp=price)
        if (current['original_accrual']!=initial['original_accrual']
            or current['physical_material_movements']!=initial['physical_material_movements']):
            raise ValueError('NONPAYABLE_RECOST_CHANGED_ORIGINAL_ACCRUAL_OR_PHYSICAL_STOCK_FACTS')
        phase=dict(invoice=made,unit_cost=price,actual=current)
        if index<2:
            # Never overwrite a posted invoice: use its existing legal inverse
            # before the next supplier document, keeping every original ID.
            inverse=modules.invoice.reverse(cur,invoice_fixture,made['invoice_id'])
            bc.internal(cur,'process_cost_recalc_queue',100)
            restored=fixture.observe(cur,modules,f);fixture.require_economics(restored,f,nonpayable=True,hpp='0.004')
            if restored['original_accrual']!=initial['original_accrual']:
                raise ValueError('NONPAYABLE_INVOICE_INVERSE_CHANGED_ORIGINAL_ACCRUAL')
            phase.update(invoice_inverse=inverse,after_inverse=restored)
        phases.append(phase)
    return finish(cur,modules,before_findings,fixture=f,actual_initial=initial,phases=phases,
        no_initial_accrual_journal=True,positive_HPP_zero_reimbursement=True,
        expected_cumulative_WIP_cents=['0.01','0.01','0.02'],
        expected_WIP_after_each_legal_invoice_inverse='0.00',
        posted_invoice_overwrites=0,original_basis_and_reimbursement_frozen=True,
        physical_stock_quantity_and_source_ids_unchanged=True)

def cases(cur,today,state):
    fixture_module().admitted_modules(cur,state)  # Parent gate before closures.
    source_controls()
    from . import native_inverse_cases,native_sales_cases
    return [
        (IDS[0],lambda:ordinary_case(cur,today,state,history=True)),
        (IDS[1],lambda:ordinary_case(cur,today,state,initial_special=False)),
        (IDS[2],lambda:ordinary_case(cur,today,state,initial_special=False,transition=True)),
        (IDS[3],lambda:ordinary_case(cur,today,state,initial_special=True,transition=False)),
        (IDS[4],lambda:missing_date_case(cur,today,state)),
        (IDS[5],lambda:cumulative_cents_case(cur,today,state)),
    ]+native_inverse_cases.cases(cur,today,state)+native_sales_cases.cases(cur,today,state)

if __name__=='__main__':
    if sys.argv[1:]!=['--prepare']:raise SystemExit('READ_ONLY_PREPARATION_ONLY')
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    from cp7_accessory_nonpayable.native_cases import source_controls as checked
    print(json.dumps(checked(),sort_keys=True))
