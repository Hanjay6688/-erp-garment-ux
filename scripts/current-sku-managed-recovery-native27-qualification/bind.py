"""Explicit writer freeze only; current pins are never regenerated in CI."""
from hashlib import sha256
from pathlib import Path
import importlib.util
import json
import os
import sys
import yaml

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]

def load(name,file):
    spec=importlib.util.spec_from_file_location(name,HERE/file);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def bind():
    assert not os.environ.get('CI'),'SKU27_CI_MUST_NOT_REGENERATE_SOURCE'
    t=load('sku27_writer_transition','transition.py');workflow=load('sku27_writer_workflow','workflow.py')
    expected=workflow.derive(yaml.safe_load((ROOT/workflow.OLD).read_bytes()))
    assert yaml.safe_load((ROOT/workflow.NEW).read_bytes())==expected
    derived=load('sku27_writer_derivations','derive.py')
    for name in('browser','cases'):(HERE/(name+'.mjs')).write_text(derived.derive(name)[0])
    browser_delta=load('sku27_writer_browser_delta','browser_delta.py')
    for name in browser_delta.STAGED:(HERE/name).write_text(browser_delta.staged(name)[0])
    wf=(ROOT/t.WORKFLOW).read_bytes();wf_pin=dict(bytes=len(wf),sha256=sha256(wf).hexdigest())
    for name in('GENERATED_RECEIPTS.json','LATER_GENERATED_RECEIPTS.json','SKU_GENERATED_RECEIPTS.json'):
        path=HERE/name;value=json.loads(path.read_bytes());value['producer_files'][t.WORKFLOW]=wf_pin
        if name=='LATER_GENERATED_RECEIPTS.json':assert value['package_workflow_name']==workflow.NAME
        path.write_text(json.dumps(value,indent=2)+'\n')
    parent=json.loads((HERE/'PARENT_SOURCE.json').read_bytes());assert parent['head']==t.BASE and parent['tree']==t.TREE and len(parent['files'])==13759
    owned=sorted(str(p.relative_to(ROOT))for p in HERE.rglob('*')if p.is_file()and p!=HERE/'SOURCE.json'and'__pycache__'not in p.parts and p.suffix!='.pyc')
    names=owned+[t.WORKFLOW];files={}
    for name in names:
        path=ROOT/name;assert not path.is_symlink();raw=path.read_bytes();files[name]=dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
    value=dict(status='PREPARED_FULL_NATIVE27_NOT_EXECUTED',base_head=t.BASE,base_tree=t.TREE,
      base_file_count=13759,files=files,allowed_changes=sorted(names+[t.NS+'/SOURCE.json']),
      product_alias=dict(public_head=t.PRODUCT_HEAD,tree=t.PRODUCT_TREE,historical_preflight_source_pin_count=43,
        prepared_material_transition_source_pin_count=20,actual_runtime_leaves=10,
        transition_manifest='scripts/current-sku-recovery-material-lock/SOURCE.json',
        transition_manifest_sha256=sha256((ROOT/'scripts/current-sku-recovery-material-lock/SOURCE.json').read_bytes()).hexdigest()),
      private_derivations=derived.inventory(),complete_vendor_engine_changes=6,
      frozen_original23_callbacks_edited=0,original_23_ids_retained=True,
      planned=dict(base_Native=7,cost_Native=5,conversion_races=3,Native_permission_waits=7,Native_nonblocking_busy=1,real_Auth_browser=4,total=27),
      new_case_ids=[*load('sku27_writer_positive_ids','recovery_cases.py').IDS],
      new_session_ids=['SKU30_RECOVERY_CACHE_REPLAY_PERMISSION_WITHDRAWN_DURING_REAL_REQUEST_WAIT','SKU30_RECOVERY_FG_TRY_LOCK_BUSY_BEFORE_ANY_EFFECT'],
      busy_case_subattempts=['FG','MATERIAL_NONE'],busy_case_declared_IDs=1,
      sequence_producer=dict(path=t.NS+'/sequence_prefix.py',all_current_sequences=15,per_case_complete_before_after=True,successful_prefix_is_not_savepoint_restore=True),
      cost_census_producer=dict(path='scripts/current-sku-group-cost-qualification/native_fixture.py',all22=True,all_current_tables=True,all_sequences=True,original_code_unchanged=True),
      Node_source_reader=dict(path=t.NS+'/browser_source.py',actual_current_product_sources=True,authentic_Original21_reader=True,projected_sources=False),
      explicit_a18_browser_successor=browser_delta.verify(),
      execution_attempt_policy=dict(path=t.NS+'/attempt_policy.py',automatic_group_retry=False,
        pre_database_and_runtime_WIB_window_seconds=12600,unchanged_business_day_guard=True,
        first_attempt_failures_preserved=True,unchanged_copy_count=11),
      actual_successor_cases=0,actual_Auth_HTTP_cases=0,actual_real_browser_cases=0,
      group_recovery_supported=False,production_go=False,independent_acceptance=False,default_adoption=False)
    (HERE/'SOURCE.json').write_text(json.dumps(value,indent=2)+'\n')
    return dict(status=value['status'],files=len(files),parent_files=13759,actual_successor_cases=0)

if __name__=='__main__':
    assert sys.argv[1:]==['--writer-freeze'],'SKU27_WRITER_FREEZE_ONLY'
    print(json.dumps(bind(),sort_keys=True))
