"""Exact source-only CLI successor from public b874/local2834, same tree."""
from hashlib import sha256
from pathlib import Path
import ast
import json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
NS='scripts/current-s05-native10-qualification'
LOCAL_BASE='2834c9ada13a1f70f79bf67c62f5c7d3554e2cb5'
PUBLIC_BASE='b874783f57be809a867ce4d0806553a17c03243e'
BASE_TREE='7f78cf2488afeca9d90a0d281a873c556dee082e'
OLD_SOURCE_SHA='5327ae751656ed0f3836313fa6f633c9881c817ecf154373962180ac20b0d1b8'
BRANCH='astra-a/s05-native10-import-argv-20261029'
OLD_BRANCH='astra-a/s05-native10-qualification-20261029'
WORKFLOW='.github/workflows/cp7-current-s05-native10.yml'
ALLOWED_OLD={NS+'/'+name for name in ('probe.py','admission.py','workflow_source.py','CONFIG.json','README.md','LOCAL_CONTROLS.json')}|{WORKFLOW}


def checked(repo=ROOT,here=HERE):
    repo,here=Path(repo),Path(here)
    raw=(here/'retained/SOURCE.json').read_bytes()
    if sha256(raw).hexdigest()!=OLD_SOURCE_SHA:raise ValueError('S05_CLI_EXACT_FROZEN_PARENT_REQUIRED')
    old=json.loads(raw)
    for path,digest in old['files'].items():
        if path not in ALLOWED_OLD and sha256((repo/path).read_bytes()).hexdigest()!=digest:
            raise ValueError('S05_CLI_FROZEN_PRODUCT_ENGINE_OR_ORACLE_CHANGED: '+path)
    old_probe=ast.parse((here/'retained/probe.py').read_bytes())
    new_probe=ast.parse((repo/NS/'probe.py').read_bytes())
    def other(tree):
        return [ast.dump(n)for n in tree.body if not(isinstance(n,ast.FunctionDef)and n.name=='check')]
    if other(old_probe)!=other(new_probe):raise ValueError('S05_CLI_ONLY_PROBE_CHECK_BOUNDARY_ALLOWED')
    old_admission=ast.parse((here/'retained/admission.py').read_bytes())
    new_admission=ast.parse((repo/NS/'admission.py').read_bytes())
    def admission_other(tree):
        return [ast.dump(n)for n in tree.body if not(isinstance(n,ast.FunctionDef)and n.name=='offline')]
    if admission_other(old_admission)!=admission_other(new_admission):raise ValueError('S05_CLI_RUNTIME_ADMISSION_ORACLE_CHANGED')
    before=(here/'retained/workflow_source.py').read_text()
    after=(repo/NS/'workflow_source.py').read_text()
    if before.count(OLD_BRANCH)!=1 or after!=before.replace(OLD_BRANCH,BRANCH,1):
        raise ValueError('S05_CLI_ONLY_EXECUTION_BRANCH_WORKFLOW_CHANGE_ALLOWED')
    first=json.loads((here/'FIRST_FAILURE.json').read_bytes())
    if(first['failed_public_head'],first['tree'],first['Native_executions'],first['database_started'])!=(PUBLIC_BASE,BASE_TREE,0,False):
        raise ValueError('S05_CLI_FIRST_FAILURE_NOT_EXACT_ZERO_DATABASE')
    return dict(status='EXACT_SCOPED_IMPORT_ARGV_SUCCESSOR_ONLY',local_base=LOCAL_BASE,public_base=PUBLIC_BASE,
        base_tree=BASE_TREE,unchanged_frozen_pins=len(old['files'])-len(ALLOWED_OLD),
        report_stage_ten_cases_UI_engine_oracles_unchanged=True,execution_branch=BRANCH,
        actual_Native_cases=0,actual_inherited_runtime_import='NOT_RUN_BY_HELPER',
        production_go=False,independent_acceptance=False)
