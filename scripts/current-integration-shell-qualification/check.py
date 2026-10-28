"""Admit only the new qualification harness on the exact integrated application."""
from pathlib import Path
from hashlib import sha256
import importlib.util,json,subprocess
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args],text=True).strip()
def check():
    cfg=json.loads((HERE/'CONFIG.json').read_bytes())
    assert git('rev-parse',cfg['base_head']+'^{tree}')==cfg['base_tree']
    assert not git('status','--porcelain','--untracked-files=no')
    changed=git('diff','--name-only',cfg['base_head'],'HEAD').splitlines()
    assert set(changed)==set(cfg['allowed_new_paths']),changed
    for p in changed:assert git('diff','--diff-filter=A','--name-only',cfg['base_head'],'HEAD','--',p)==p,p
    old=cfg['accepted_source_suite'];assert old['head']=='b7d6b75add6883b7cfc5b162c05531a8d0ac2f23'
    assert old['status']=='PASS_SOURCE_AND_COMPLETE_CLIENT_AND_KERNEL_SUITE_ONLY'
    assert old['client_counts']['numPassedTests']==old['client_counts']['numTotalTests']==3253
    assert old['client_counts']['numFailedTests']==old['client_counts']['numPendingTests']==old['client_counts']['numTodoTests']==0
    assert old['Node_tests_passed']==10
    spec=importlib.util.spec_from_file_location('unchanged_source_closure',ROOT/'scripts/current-source-closure-preparation/check.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);source=m.check()
    return dict(status='PASS_EXACT_INTEGRATED_SOURCE_ONLY',head=git('rev-parse','HEAD'),base_head=cfg['base_head'],base_tree=cfg['base_tree'],only_new_paths=changed,retained_suite_head=old['head'],source=source,source_admission_database_connections=0,actual_browser_cases=0,production_go=False,independent_acceptance=False)
if __name__=='__main__':
    value=check();out=ROOT/'cp6-proof/current-integration-shell/SOURCE_BOUNDARY.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(value,indent=2)+'\n');print(json.dumps(value))
