"""Bind the unmodified first counterexample, then admit the closed repair."""
from hashlib import sha256
from pathlib import Path
import importlib.util,json,os,subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PARENT=ROOT/'scripts/current-finance-followups-qualification'
VISIBILITY='FINANCE_PREEXISTING_CHILD_TRANSACTION_COMMITS_AFTER_JOURNAL_SCAN'
SINGLE='FINANCE_CURRENT_TWO_CHECK_TO_SINGLE_CHECK_SMALL_PRICE_FACTORY_DIAGNOSTIC'


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def check_gate(config,prepared):
    if (config.get('allow_database_execution')is not True
        or prepared.get('allow_database_execution')is not True
        or not config.get('first_diagnostic')):
        raise ValueError('CONSISTENT_CAPTURE_FIRST_ACTUAL_DIAGNOSTIC_REQUIRED')


def first_counterexample(binding,raw,package_raw,expected_source):
    for value,size,digest in ((raw,binding['bytes'],binding['sha256']),
        (package_raw,binding['package_bytes'],binding['package_sha256'])):
        if len(value)!=size or sha256(value).hexdigest()!=digest:
            raise ValueError('CONSISTENT_CAPTURE_FIRST_ORIGINAL_CHANGED')
    actual=json.loads(raw);package=json.loads(package_raw)
    assert actual['qualification_commit']==binding['head']
    assert actual['source_declaration']==expected_source,'CONSISTENT_CAPTURE_FIRST_SOURCE_CHANGED'
    assert actual['status']=='INCOMPLETE' and actual['error']=='FOLLOWUP_FIRST_FAILURES_RETAINED'
    assert actual['production_go']is actual['independent_acceptance']is False
    assert package['gate']==dict(installed=True,primary_unchanged=True,
        backup_restore_drill=True,security_advisors=True,writer_runtime=False)
    for key in ('cp6_restored','advisor_gate','baseline_full22_all_rows_all_sequences_equal','baseline_advisors_equal'):
        assert actual.get(key)is True,'CONSISTENT_CAPTURE_FIRST_RESTORATION_MISSING:'+key
    assert len(actual['committed'])==1
    first=next(iter(actual['committed'].values()))['cases']
    assert set(first)=={VISIBILITY,SINGLE}
    case=first[VISIBILITY]
    assert case['status']=='INCOMPLETE'
    assert case['error']=='PREEXISTING_CHILD_TRANSACTION_MUST_NOT_SEAL_MIXED_BOOK'
    assert case['unsafe_ready_observed']is case['mixed_signature_confirmed']is True
    assert case['source_commit_after_journal_and_line_chunks']is True
    assert first[SINGLE]['status']in ('PASS','INCOMPLETE')
    for child in first.values():
        restored=child['installed_baseline_restoration']
        assert restored['all22_all_rows_all_sequences_roles_exact']is True
        assert restored['complete_database_dump_restored']is True
        assert restored['used_guard_refused_before_DDL']is True
        assert not child.get('restore_error')
    return dict(head=binding['head'],original_sha256=binding['sha256'],
        retained_actual_status='INCOMPLETE',escaped_mixed_book_proven=True,
        all_child_and_outer_baselines_restored=True,single_check_status=first[SINGLE]['status'],
        failed_writer_runtime_not_relabelled=True)


def admitted(repo,here,ids,product,native):
    config=json.loads((here/'CONFIG.json').read_bytes())
    prepared=json.loads((here/'PREPARED.json').read_bytes());check_gate(config,prepared)
    source=json.loads((here/'SOURCE.json').read_bytes())
    assert source['case_ids']==list(ids)
    assert source['production_go']is source['independent_acceptance']is False
    for path,digest in source['files'].items():
        assert sha256((repo/path).read_bytes()).hexdigest()==digest,path
    assert sha256((PARENT/'SOURCE.json').read_bytes()).hexdigest()==source['parent_source_sha256']
    parent=load('unchanged_first_followups_admission',PARENT/'admission.py')
    parent_ids=json.loads((PARENT/'SOURCE.json').read_bytes())['case_ids']
    accepted=parent.admitted(repo,PARENT,parent_ids,product,native)
    binding=config['first_diagnostic'];directory=Path(os.environ[config['original_directory_variable']])
    first=first_counterexample(binding,(directory/binding['name']).read_bytes(),
        (directory/binding['package_name']).read_bytes(),accepted)
    guard=load('consistent_capture_probe_guard',here/'source_guard.py').check(repo,here)
    assert not subprocess.check_output(['git','-C',str(repo),'status','--porcelain','--untracked-files=no'],text=True).strip()
    return dict(qualification=source,current_installation=accepted['current_installation'],
        accepted_readonly_native13_cron1=accepted['accepted_readonly_native13_cron1'],
        exact_first_followups=first,source_guard=guard,production_go=False,independent_acceptance=False)


if __name__=='__main__':
    probe=load('consistent_capture_probe_admission',HERE/'probe.py')
    result=probe.admitted()
    print(json.dumps(dict(status='SOURCE_ADMITTED',pins=len(result['qualification']['files']),
        prepared_diagnostics=5,actual_cases_executed=False)))
