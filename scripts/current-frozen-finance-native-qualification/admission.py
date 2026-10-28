"""Require the unchanged full Native40 source gate and its actual PASS Original."""
from hashlib import sha256
from pathlib import Path
import importlib.util
import json
import os
import subprocess

CONTRACT='cp7.current-frozen-finance-native45-qualification.v1'
VARIABLE='CURRENT_FROZEN_UNITS_NATIVE_ORIGINAL_REPORT'
PARENT_HEAD='8de2ae694c6eda60a6724415eb60772c4f7a20b2'


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result


def admitted(repo,here,ids,product,business):
    pins=json.loads((here/'SOURCE.json').read_bytes())
    assert pins['contract']==CONTRACT and pins['case_ids']==list(ids)
    assert len(ids)==len(set(ids))==45
    assert set(pins['actual_qualification_originals'])=={VARIABLE}
    prior_probe=repo/'scripts/current-frozen-units-native-qualification/probe.py'
    prior=load('unchanged_full_frozen_units_admission',prior_probe)
    old=prior.admitted()
    assert old['current_installation']==product.predecessor.sources()
    assert pins['retained_declaration_sha256']==sha256(prior_probe.with_name('SOURCE.json').read_bytes()).hexdigest()
    for path,digest in old['qualification']['files'].items():
        assert sha256((repo/path).read_bytes()).hexdigest()==digest,path
    for path,digest in pins['files'].items():
        assert sha256((repo/path).read_bytes()).hexdigest()==digest,path
    assert not subprocess.check_output(['git','-C',str(repo),'status','--porcelain','--untracked-files=no'],text=True).strip()
    proof=pins['actual_qualification_originals'][VARIABLE]
    raw=Path(os.environ[VARIABLE]).read_bytes()
    assert len(raw)==proof['bytes']and sha256(raw).hexdigest()==proof['sha256']
    actual=json.loads(raw)
    assert proof['head']==actual['qualification_commit']==PARENT_HEAD
    assert actual['label']=='CP7_CURRENT_FROZEN_UNITS_NATIVE40'
    assert actual['status']==proof['status']=='PASS'
    assert actual['production_go']is actual['independent_acceptance']is False
    assert actual['source_declaration']['qualification']==old['qualification']
    assert actual['source_declaration']['current_installation']==product.predecessor.sources()
    for key in('cp6_restored','advisor_gate','baseline_full22_all_rows_all_sequences_equal',
               'baseline_advisors_equal','restore_raw_public_equal','required_case_ids_pass'):
        assert actual[key]is True,key
    assert actual['complete_preuse_removal']['all22_preinstall_equal']
    assert actual['complete_preuse_removal']['all_rows_and_sequences_equal']
    assert actual['complete_preuse_removal']['global_used_guard_before_any_DDL']
    assert actual['observed_case_count']==actual['expected_case_count']==40
    assert actual['required_case_ids']==old['qualification']['case_ids']
    assert actual['native']['counts']=={'PASS':40}
    assert set(actual['native']['cases'])==set(actual['required_case_ids'])
    for name,row in actual['native']['cases'].items():
        assert row['status']=='PASS'and row['full_boundary_restored']and row['public_schema_unchanged'],name
        assert all(v in(0,[],{})for v in row.get('session_leaks',{}).values()),name
    removed={'CURRENT_FROZEN_UNITS_PRIVATE_CATALOG_DEPENDENT_VIEW_ATOMIC'}
    assert set(business.RETAINED_IDS)|set(business.private.IDS[1:])==set(actual['required_case_ids'])-removed
    assert set(ids)==(set(actual['required_case_ids'])-removed)|set(business.finance.IDS)|{business.private.IDS[0]}
    assert business.private.IDS[0]=='CURRENT_FROZEN_FINANCE_FULL22_DEPENDENCY_GUARD'
    return dict(qualified_current_frozen_units=old,current_installation=product.sources(),qualification=pins,
        actual_originals_verified={VARIABLE:dict(proof,observed_status='PASS')},
        retained_business_cases=business.source_binding(),private_official_finance_test_scope=True,
        actual_Auth_HTTP_credit=False,public_or_default_adopted=False,
        full_factory3600_finance_qualified=False,production_go=False,independent_acceptance=False)
