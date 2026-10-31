"""Exact source/recorded-capture checks only. No database or installer call."""
from pathlib import Path
from hashlib import sha256
import argparse,importlib.util,json,subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def controls():
    record=json.loads((HERE/'ORIGIN.json').read_bytes())
    for item in record['files']:
        raw=subprocess.check_output(['/usr/bin/git','-C',str(ROOT),'show',item['source_commit']+':'+item['path']])
        if len(raw)!=item['original_bytes']or sha256(raw).hexdigest()!=item['original_sha256']:
            raise ValueError('COMPLETE_DE_EXACT_ORIGINAL_PACKAGE_REQUIRED:'+item['path'])
        text=raw.decode()
        for change in item['changes']:
            if text.count(change['before'])!=change['count']:raise ValueError('COMPLETE_DE_EXACT_PARENT_ROUTE_REQUIRED')
            text=text.replace(change['before'],change['after'],change['count'])
        if text.encode()!=(ROOT/item['path']).read_bytes():raise ValueError('COMPLETE_DE_UNDECLARED_PACKAGE_CHANGE')
        for change in reversed(item['changes']):text=text.replace(change['after'],change['before'],change['count'])
        if text.encode()!=raw:raise ValueError('COMPLETE_DE_ORIGINAL_PACKAGE_BYTES_NOT_RECOVERED')
    package=ROOT/'scripts/cp7_credit_correction_de'
    d1=load('complete_de_original_D1_deriver',package/'native_delta.py')
    e=load('complete_de_original_E_deriver',package/'e_native_delta.py')
    capture=json.loads((ROOT/'scripts/cp7_complete_credit_de/RECORDED_NATIVE_CAPTURES.json').read_bytes())
    rows=capture['functions'];expected=set(d1.CAPTURES)|set(e.CAPTURES)
    if set(rows)!=expected or len(rows)!=32 or any(type(row)is not list or len(row)!=19 for row in rows.values()):
        raise ValueError('COMPLETE_DE_EXACT_RECORDED_32_FULL19_FUNCTIONS_REQUIRED')
    originals={sig:row[0]for sig,row in rows.items()}
    first=d1.derive({sig:originals[sig]for sig in d1.CAPTURES})
    after_d1=dict(originals,**first)
    second=e.derive({sig:after_d1[sig]for sig in e.CAPTURES})
    sku=load('complete_de_exact_SKU_derivation_set',ROOT/'scripts/cp7_sku_pair_conversion/native_delta.py')
    recovery=load('complete_de_exact_SKU_recovery_set',ROOT/'scripts/cp7_sku_pair_conversion/recovery_delta.py')
    s03=load('complete_de_exact_S03_derivation_set',ROOT/'scripts/cp7_s03_sku_composition/native_delta.py')
    overlap=(set(d1.CHANGED)|set(e.CHANGED))&(set(sku.SIGNATURES)|set(recovery.SIGNATURES)|set(s03.SIGNATURES))
    if overlap:raise ValueError('COMPLETE_DE_CHANGED_NATIVE_FUNCTION_OVERLAP:'+str(sorted(overlap)))
    admission=load('complete_de_pending_parent_source_control',HERE/'admission.py')
    pending=False
    try:admission.parent_receipt()
    except ValueError as error:
        if str(error)!='COMPLETE_DE_ACTUAL_PERMANENT_PARENT_INTAKE_PENDING':raise
        pending=True
    business=load('complete_de_exact_native30_source_control',HERE/'native_business.py')
    native_source=business.source_controls()
    native_pending=False
    if pending:
        try:business.bind({})
        except ValueError as error:
            if str(error)!='COMPLETE_DE_ACTUAL_PERMANENT_PARENT_INTAKE_PENDING':raise
            native_pending=True
        else:raise ValueError('COMPLETE_DE_PENDING_NATIVE30_ADMISSION_WAS_OPENED')
    return dict(status='COMPLETE_DE_PACKAGE_AND_CURRENT_NATIVE_SOURCE_CONTROLS_PASS_NOT_NATIVE',
        exact_package_files=len(record['files']),parent_import_changes=1,other_package_files_unchanged=18,
        actual_recorded_predecessor_functions=len(rows),D1_raw_definitions=len(first),E_raw_definitions=len(second),
        changed_function_overlap_with_S03_SKU=sorted(overlap),SQL_and_Native_derivers_unchanged=True,
        raw_source_chain_not_PostgreSQL_normalized_install=True,parent_qualification_pending=pending,
        native30_source=native_source,Native30_pending_before_ERP_or_SQL=native_pending,
        actual_SQL_executed=0,actual_Native_cases=0,production_go=False,independent_acceptance=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--source',action='store_true',required=True);parser.parse_args()
    source=load('complete_de_closed_source',HERE/'source.py').preflight()
    fence=load('complete_de_actual_three_entrypoint_fence',ROOT/'scripts/current-sku-managed-recovery-native27-qualification/source_context.py')
    with fence.fenced_source_read()as guard:value=controls()
    print(json.dumps(dict(source=source,controls=value,source_DB_guard=guard),sort_keys=True))
