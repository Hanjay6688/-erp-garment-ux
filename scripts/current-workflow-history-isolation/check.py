"""Prove unchanged frozen bytes and complete source after isolated materialization."""
from pathlib import Path
from hashlib import sha256
import importlib.util,json,subprocess
from materialize import materialize
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def git(*a):return subprocess.check_output(['git','-C',str(ROOT),*a],text=True).strip()
def check():
    cfg=json.loads((HERE/'ARCHIVE.json').read_bytes());assert git('rev-parse',cfg['base_head']+'^{tree}')==cfg['base_tree']
    assert not git('status','--porcelain','--untracked-files=no')
    changes=git('diff','--name-status','--no-renames',cfg['base_head'],'HEAD').splitlines()
    deleted={line.split('\t',1)[1]for line in changes if line.startswith('D\t')};assert deleted=={x['path']for x in cfg['files']}
    for line in changes:
        status,path=line.split('\t',1)
        assert(status=='D'and path in deleted)or(status=='A'and(path.startswith('scripts/current-workflow-history-isolation/')or path=='.github/workflows/cp7-d17-18-workflow-history-isolation.yml')),line
    copied=materialize()
    spec=importlib.util.spec_from_file_location('unchanged_full_source',ROOT/'scripts/current-source-closure-preparation/check.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);source=m.check()
    return dict(status='PASS_UNCHANGED_SOURCE_WITH_HISTORICAL_WORKFLOWS_RETIRED',head=git('rev-parse','HEAD'),base_head=cfg['base_head'],materialization=copied,source=source,original_manifests_rewritten=0,old_B_and_all_product_bodies_changed=False,CodeQL_finding_dismissal=False,actual_DB_Auth_browser_cases=0,production_go=False,independent_acceptance=False)
if __name__=='__main__':
    value=check();out=ROOT/'cp6-proof/workflow-history-isolation/SOURCE.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(value,indent=2)+'\n');print(json.dumps(value))
