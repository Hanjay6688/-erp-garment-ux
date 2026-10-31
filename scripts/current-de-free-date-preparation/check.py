"""Prepared source/closed-parent controls only; never a Native date claim."""
from pathlib import Path
from hashlib import sha256
import argparse,ast,importlib.util,json,subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def controls():
    origin=json.loads((HERE/'ORIGIN.json').read_bytes())
    for name,pin in origin['files'].items():
        raw=subprocess.check_output(['/usr/bin/git','-C',str(ROOT),'show',origin['head']+':'+pin['source_path']])
        if len(raw)!=pin['bytes']or sha256(raw).hexdigest()!=pin['sha256']:
            raise ValueError('FREE_DATE_DE_EXACT_C43_SOURCE_REQUIRED:'+name)
        text=raw.decode()
        for change in pin['changes']:
            if text.count(change['before'])!=change['count']:raise ValueError('FREE_DATE_DE_EXACT_C43_ROUTE_ANCHOR_REQUIRED')
            text=text.replace(change['before'],change['after'],change['count'])
        if text.encode()!=(ROOT/name).read_bytes():raise ValueError('FREE_DATE_DE_UNDECLARED_C43_CHANGE:'+name)
        for change in reversed(pin['changes']):text=text.replace(change['after'],change['before'],change['count'])
        if text.encode()!=raw:raise ValueError('FREE_DATE_DE_C43_BYTES_NOT_RECOVERED')
    guard=origin['source_preflight_origin']
    raw=subprocess.check_output(['/usr/bin/git','-C',str(ROOT),'show',guard['head']+':'+guard['path']])
    if len(raw)!=guard['bytes']or sha256(raw).hexdigest()!=guard['sha256']:raise ValueError('FREE_DATE_DE_EXACT_SOURCE_GUARD_ORIGIN_REQUIRED')
    text=raw.decode()
    for change in guard['changes']:
        if text.count(change['before'])!=change['count']:raise ValueError('FREE_DATE_DE_EXACT_SOURCE_GUARD_ROUTE_REQUIRED')
        text=text.replace(change['before'],change['after'],change['count'])
    if text.encode()!=(HERE/'source.py').read_bytes():raise ValueError('FREE_DATE_DE_UNDECLARED_SOURCE_GUARD_CHANGE')
    stage=load('free_date_DE_exact_single_predicate_stage',ROOT/'scripts/cp7_special_free_date_on_de/composition.py')
    before,after,predicate=stage.prepared()
    if len(before.encode())!=749 or len(after.encode())!=822:raise ValueError('FREE_DATE_DE_EXACT_PREDICATE_BYTES_REQUIRED')
    signature=stage.SIGNATURE
    d1=load('free_date_DE_original_D1_deriver',ROOT/'scripts/cp7_credit_correction_de/native_delta.py')
    e=load('free_date_DE_original_E_deriver',ROOT/'scripts/cp7_credit_correction_de/e_native_delta.py')
    if signature in set(d1.CHANGED)|set(e.CHANGED):raise ValueError('FREE_DATE_DE_EXISTING_D1_E_SIGNATURE_OVERLAP')
    admission=load('free_date_DE_actual_root_receipt_gate',HERE/'admission.py')
    product=load('free_date_DE_current_whole_composition',ROOT/'scripts/cp7_current_de_free_date/composition.py')
    closed=[]
    operations=(('parent_receipt',admission.parent_receipt),('whole_source_admission',admission.admitted),
        ('stage_parent_before_ERP',stage.parent),('stage_install_before_ERP_or_SQL',lambda:stage.install_delta(None,{})),
        ('whole_parent_before_ERP',product.parent),('whole_sources_before_ERP',product.sources),
        ('whole_install_before_ERP_or_SQL',lambda:product.install(None)),
        ('delta_install_before_ERP_or_SQL',lambda:product.install_delta(None,{})),
        ('whole_verify_before_ERP_or_SQL',lambda:product.verify(None,{})),
        ('delta_inverse_before_ERP_or_SQL',lambda:product.rollback_delta_preuse(None,{})),
        ('full_inverse_before_ERP_or_SQL',lambda:product.rollback_preuse(None,{})))
    for name,operation in operations:
        try:operation()
        except ValueError as error:
            if str(error)!='FREE_DATE_DE_ACTUAL_NATIVE30_PARENT_INTAKE_PENDING':raise
            closed.append(name)
        else:raise ValueError('FREE_DATE_DE_PENDING_ENTRY_WAS_OPENED:'+name)
    return dict(status='FREE_DATE_ON_COMPLETE_DE_SOURCE_AND_PENDING_CONTROLS_PASS_NOT_NATIVE',
        original_c43_files=len(origin['files']),stage_only_parent_and_contract_routes=2,
        original_SQL_and_lifecycle_statements_unchanged=True,Native_predicate_before_bytes=749,
        Native_predicate_after_bytes=822,predicate_derivation=predicate,
        D1_E_changed_signature_overlap=False,closed_before_ERP_or_SQL=closed,
        reused_isolated_date_SQL_controls=39,actual_new_SQL_executed=0,actual_Native_cases=0,
        GOOD_eligibility_policy_decided=False,production_go=False,independent_acceptance=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',action='store_true',required=True);p.parse_args()
    source=load('free_date_DE_exact_closed_source',HERE/'source.py').preflight()
    fence=load('free_date_DE_three_entrypoint_no_DB_fence',
        ROOT/'scripts/current-sku-managed-recovery-native27-qualification/source_context.py')
    with fence.fenced_source_read()as guard:value=controls()
    print(json.dumps(dict(source=source,controls=value,source_DB_guard=guard),sort_keys=True))
