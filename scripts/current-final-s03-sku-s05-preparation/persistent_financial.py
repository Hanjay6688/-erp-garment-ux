"""Four original financial callbacks with the S05 reader kept installed.

Preparation only. An owning disposable package runner must first admit the
exact accepted joined37 Original, install the complete assembly, and own all
backup, roles, Auth, full restore and package gates. This module does not
connect, install, dispatch, change defaults or enable a runtime by import.
"""
from pathlib import Path
from hashlib import sha256
from types import ModuleType,SimpleNamespace
import ast,importlib.util,json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PARENT_HEAD='1edd7b7fb6f7f02528cf09bcc352b72ea0e4a2c3'
PARENT_TREE='7433f5bb0208584e656bbd30f90a7cac3cede1e8'
PARENT_RUN=41190706967
# Populate only from the terminal canonical root intake. Pending means closed.
PARENT_RECEIPT=None
LABEL='CP7_PERMANENT_S05_S03_FINANCIAL_NATIVE4'
ORIGINAL_IDS=(
 'S03_NATIVE_EXPENSE_APPROVAL_ONCE_PAID_E05_REOPEN',
 'S03_NATIVE_BOTH_CORRECTIONS_LINKED_INVERSES_NO_RECOGNITION',
 'S03_NATIVE_FINISHED_PO_FG_COGS_COST_AND_CANCEL_EXACT',
 'S03_NATIVE_OLD_ACCRUAL_LATER_BOOK_REOPEN_DATE_FLOOR',
)
IDS=tuple('PERMANENT_S05_'+key for key in ORIGINAL_IDS)


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def qualified_receipt(raw):
    if PARENT_RECEIPT is None:raise ValueError('PERMANENT_S05_EXACT_TERMINAL_JOIN37_INTAKE_PENDING')
    if len(raw)!=PARENT_RECEIPT['bytes']or sha256(raw).hexdigest()!=PARENT_RECEIPT['sha256']:
        raise ValueError('PERMANENT_S05_CANONICAL_PARENT_INTAKE_CHANGED')
    strict=load('permanent_S05_duplicate_and_nonfinite_JSON_guard',ROOT/'scripts/current-s03-sku-s05-composite-qualification/parents.py').strict
    receipt=strict(raw)
    required=dict(status='ROOT_VERIFIED_CURRENT_JOIN_NATIVE31_BROWSER6_ALL5',head=PARENT_HEAD,tree=PARENT_TREE,
        run_id=PARENT_RUN,complete37_qualified=True,package_all_five=True,prior_runs_aggregated=False,
        retained_SKU27_fresh_case_credit=0,production_go=False,independent_acceptance=False)
    for key,value in required.items():
        if type(receipt.get(key))is not type(value)or receipt[key]!=value:
            raise ValueError('PERMANENT_S05_ACTUAL_QUALIFIED_JOIN37_REQUIRED:'+key)
    return receipt


def code(name,text,**bindings):
    module=ModuleType(name);module.__file__=str(HERE/(name+'.py'));module.__dict__.update(bindings)
    exec(compile(text,module.__file__,'exec'),module.__dict__);return module


def prepared_sources():
    """Change only constructor verification, before unchanged callbacks exist."""
    source=load('permanent_S05_complete_financial_source_derivation',ROOT/'scripts/current-s03-sku-native14-binding/prepare.py')
    texts,proof=source.prepare()
    before='installed=composition.verify(cur,state)'
    after='installed=JOIN_COMPLETE_PRODUCT.verify(cur,JOIN_COMPLETE_STATE)'
    derived,route=source.substitute(texts['core'].encode(),((before,after),))
    if source.callbacks(derived)!=source.callbacks(texts['core']):
        raise ValueError('PERMANENT_S05_FINANCIAL_CALLBACK_AST_CHANGED')
    exact=source.literal(texts['core'],'IDS')
    if len(exact)!=11 or any(key not in exact for key in ORIGINAL_IDS)or len(set(IDS))!=4:
        raise ValueError('PERMANENT_S05_EXACT_FOUR_AUTHORED_CALLBACKS_REQUIRED')
    return dict(texts,core=derived),dict(original_preparation=proof,constructor_verifier_route=route,
        original_financial_callback_ASTs_unchanged=11,selected_original_ids=list(ORIGINAL_IDS),
        new_persistent_case_ids=list(IDS),all22_catalog_projection=False,Native_case_credit=0)


def business(state,raw_receipt):
    receipt=qualified_receipt(raw_receipt)  # Before importing the ERP graph.
    from cp7_current_s03_sku_s05 import composition as complete
    if state['sources']!=complete.sources():raise ValueError('PERMANENT_S05_CURRENT_COMPLETE_SOURCE_REQUIRED')
    texts,proof=prepared_sources()
    fixture=code('permanent_s05_financial_fixture',texts['fixture'])
    lawful=code('permanent_s05_lawful_fixture',texts['lawful_fixture'])
    def admitted(actual):
        if actual!=state['financial_parent']['sources']['predecessor']:
            raise ValueError('PERMANENT_S05_ACTUAL_QUALIFIED_SKU_SOURCE_CHANGED')
        return dict(status='ACTUAL_JOIN37_PARENT_INTAKE_ADMITTED_FOR_PERMANENT_S05',
            head=receipt['head'],run_id=receipt['run_id'],parent_case_credit=0,production_go=False)
    core=ModuleType('permanent_s05_financial_core');core.__file__=str(HERE/'permanent_s05_financial_core.py')
    core.__dict__.update(JOIN_FIXTURE=fixture,JOIN_PARENT_ADMISSION=SimpleNamespace(admit=admitted),
        JOIN_COMPLETE_PRODUCT=complete,JOIN_COMPLETE_STATE=state,LAWFUL=lawful,CORE=core)
    exec(compile(texts['core'],core.__file__,'exec'),core.__dict__)
    return core,complete,proof


def read_kept_reader(cursor,today,core,complete,state):
    from cp7_p21_current_chain_rehearsal_probe import helper
    _,_,_,_,catalog=complete.runtime()
    core.f.admin(cursor)
    with helper.control.product_catalog(cursor):
        complete.verify(cursor,state)
        before_catalog,before_data=catalog._catalog_rows(cursor),catalog._data(cursor)
    owner=core.f.hp.owner(cursor)
    core.f.hp.auth.actor(cursor,owner)
    try:
        response=cursor.execute('select public.erp_cp7_get_accessory_standard_report_v1(%s,%s,null,null,%s,0,10)',
            (today,today,'')).fetchone()[0]
    finally:
        if cursor.connection.info.transaction_status.name!='INERROR':core.f.admin(cursor)
    if response.get('contract_version')!='cp7.accessory-standard-report.v1'or response.get('business_DML')is not False:
        raise ValueError('PERMANENT_S05_ACTUAL_NORMAL_OWNER_READER_REQUIRED')
    with helper.control.product_catalog(cursor):
        complete.verify(cursor,state)
        after_catalog,after_data=catalog._catalog_rows(cursor),catalog._data(cursor)
    if before_catalog!=after_catalog or before_data!=after_data or len(after_catalog)!=22:
        raise ValueError('PERMANENT_S05_READ_CHANGED_ALL22_ROWS_OR_ANY_SEQUENCE')
    return dict(status='PASS',actual_public_response=response,reader_remained_installed=True,
        before=dict(actual_all22=before_catalog,full_data_and_sequences=before_data),
        after=dict(actual_all22=after_catalog,full_data_and_sequences=after_data),
        all_fields_retained=True,business_DML=False)


def retain(native,report):
    target=ROOT/'cp6-proof/t3';target.mkdir(parents=True,exist_ok=True);files=[]
    for name in (LABEL+'.json',LABEL+'_BUSINESS_DAY_FIRST_ATTEMPT.json'):
        path=native.r1.OUT/name
        if not path.is_file():continue
        raw=path.read_bytes();out=target/name
        if out.exists()and out.read_bytes()!=raw:raise ValueError('PERMANENT_S05_FIRST_NATIVE_ORIGINAL_OVERWRITE_REFUSED')
        if not out.exists():
            with out.open('xb')as stream:stream.write(raw)
        files.append(dict(name=name,bytes=len(raw),sha256=sha256(raw).hexdigest()))
    report['strict_group_originals']=files


def exercise(conn,cur,database,url,report,state,*,raw_parent_receipt):
    core,complete,proof=business(state,raw_parent_receipt)
    from cp7_p21_current_chain_rehearsal_probe import helper
    from cp7_catalog_state import exact_public_catalog
    native=helper.control.native
    if conn.info.host not in('127.0.0.1','localhost')or conn.info.port!=54322:
        raise ValueError('PERMANENT_S05_LOCAL_DISPOSABLE_ONLY')
    if cur.execute('select current_database()').fetchone()!=('cp6_rollback',):
        raise ValueError('PERMANENT_S05_CP6_ROLLBACK_ONLY')
    with helper.control.product_catalog(cur):complete.verify(cur,state)
    report.update(status='INCOMPLETE',source_derivation=proof,actual_Native_cases=0,
        retained_join37_fresh_case_credit=0,reader_remains_installed=True,production_go=False,independent_acceptance=False)
    conn.rollback();cur.close();conn.close()
    def verify(cursor):
        with helper.control.product_catalog(cursor):return complete.verify(cursor,state)
    def cases(cursor,today):
        with helper.control.product_catalog(cursor):
            selected=dict(core.cases(cursor,today,state=state['financial_parent'],evidence=report))
        def wrapped(original,operation):
            def run():
                verify(cursor)
                actual=operation()
                actual['permanent_S05_read']=read_kept_reader(cursor,today,core,complete,state)
                actual['unchanged_original_financial_case']=original
                return actual
            return run
        return [(key,wrapped(original,selected[original]))for key,original in zip(IDS,ORIGINAL_IDS)]
    try:
        with exact_public_catalog(native,retain_raw=True)as public:
            actual=native.strict_group(LABEL,cases,verify)
    finally:retain(native,report)
    report.update(native=actual,public_catalog_observation=public)
    if(actual.get('status')!='PASS'or actual.get('counts')!={'PASS':4}or actual.get('planned_case_ids')!=list(IDS)
       or set(actual.get('cases',{}))!=set(IDS)or actual.get('complete_boundary_restored')is not True):
        raise ValueError('PERMANENT_S05_COMPLETE_FINANCIAL4_REQUIRED')
    for key,row in actual['cases'].items():
        if(row.get('status')!='PASS'or row.get('full_boundary_restored')is not True
           or row.get('public_schema_unchanged')is not True or row.get('permanent_S05_read',{}).get('status')!='PASS'):
            raise ValueError('PERMANENT_S05_FULL_STRICT_CASE_AND_PERSISTENT_READER_REQUIRED:'+key)
    report.update(status='PASS',actual_Native_cases=4,financial_callbacks_unchanged=True,
        permanent_reader_present_before_and_after_every_financial_callback=True,
        full_outer_backup_roles_sequences_restore_and_all5_still_required=True)


if __name__=='__main__':
    # Source-only evidence, no ERP imports, connection or Native claim.
    print(json.dumps(dict(status='PERMANENT_S05_FINANCIAL4_SOURCE_PREPARED_NOT_EXECUTED',
        source=prepared_sources()[1],accepted_parent_receipt_pinned=PARENT_RECEIPT is not None,
        actual_Native_cases=0,production_go=False,independent_acceptance=False)))
