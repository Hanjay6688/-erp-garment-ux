"""Whole source closure; failed 9ac stays a negative, never a prerequisite.

The old425 checker remains physically exact. Five counted private changes only
admit this NEW namespace/WF through its Git/untracked fences and pass the exact
new workflow producer contract to both unchanged output validators. Every
historical hash, Original reader, runtime source and unknown-output refusal
remains active. No source projection or arbitrary SHA refresh is performed.
"""
from pathlib import Path
from hashlib import sha256
import importlib.util
import json
import subprocess
from types import ModuleType

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PARENT=ROOT/'scripts/current-attendance-choice-reader-native14-qualification'
NS='scripts/current-s03-lawful-fixture-successor-qualification'
WF='.github/workflows/cp7-s03-lawful-fixture-native14.yml'
BASE='9ac9c8bd1bfb7d64a1e735067083c68acbff02ef'
TREE='49591433899ef13c70e3cd94fc0c43894ea182df'


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def check(root=ROOT,here=HERE,require_bound=False):
    root,here=Path(root),Path(here)
    cfg=load('s03_lawful_closed_cfg',here/'gate.py').current()
    parent=root/'scripts/current-attendance-choice-reader-native14-qualification'
    old=json.loads((parent/'SOURCE.json').read_bytes())
    source=json.loads((here/'SOURCE.json').read_bytes())
    authority=load('s03_lawful_unchanged_source_path_rules',parent/'source_check.py')
    if (source.get('contract')!=cfg['qualification_contract'] or source.get('Native_executed')is not False
            or source.get('production_go')is not False or source.get('independent_acceptance')is not False):
        raise ValueError('S03_LAWFUL_SOURCE_ONLY_PREPARATION_REQUIRED')
    old_source_path=str((parent/'SOURCE.json').relative_to(root))
    if dict(bytes=(parent/'SOURCE.json').stat().st_size,sha256=sha256((parent/'SOURCE.json').read_bytes()).hexdigest())!=cfg['inherited_SOURCE']:
        raise ValueError('S03_LAWFUL_OLD425_SOURCE_CHANGED')
    # Name and refuse a leaf/ancestor link before directory enumeration can
    # report a less specific allocation-cardinality error. No guard is removed.
    for name,pin in source['files'].items():
        authority.pinned(root,name,pin)
    own={str(p.relative_to(root))for p in here.rglob('*')if p.is_file()and '__pycache__'not in p.parts and p.suffix!='.pyc'}
    allowed=own|{WF}
    if set(source['allowed_changes'])!=allowed:
        raise ValueError('S03_LAWFUL_ONLY_NEW_NAMESPACE_WORKFLOW_ALLOWED')
    expected=set(old['files'])|{old_source_path}|allowed-{str((here/'SOURCE.json').relative_to(root))}
    if set(source['files'])!=expected:
        raise ValueError('S03_LAWFUL_EVERY_INHERITED_AND_NEW_SOURCE_PIN_REQUIRED')
    for name,pin in old['files'].items():
        if source['files'][name]!=pin:
            raise ValueError('S03_LAWFUL_INHERITED425_PIN_CHANGED:'+name)
    api=cfg.get('fixture_API',{})
    if (api.get('path')!=NS+'/lawful_fixture.py'
            or {k:api.get(k)for k in('bytes','sha256')}!=source['files'].get(api.get('path'))):
        raise ValueError('S03_LAWFUL_FROZEN_EXPLICIT_FIXTURE_API_PIN_REQUIRED')
    git=lambda *args:subprocess.check_output(['git','-C',str(root),*args],text=True)
    if git('rev-parse',BASE+'^{tree}').strip()!=TREE:
        raise ValueError('S03_LAWFUL_EXACT_FAILED9AC_SOURCE_BASE_REQUIRED')
    changed=set(git('diff','--name-only',BASE,'HEAD').splitlines())
    if not changed<=allowed or git('status','--porcelain','--untracked-files=no').strip():
        raise ValueError('S03_LAWFUL_OTHER_TRACKED_CHANGE_OR_DIRTY_TREE')
    # Exact workflow/producer changes are a declaration, not a new validator.
    flow=load('s03_lawful_exact_workflow_derivation',here/'workflow.py')
    import yaml
    if yaml.safe_load((root/WF).read_bytes())!=flow.derive(yaml.safe_load((root/flow.OLD).read_bytes())):
        raise ValueError('S03_LAWFUL_WORKFLOW_OUTSIDE_BOUNDED_DERIVATION')
    for filename in ('GENERATED_RECEIPTS.json','LATER_GENERATED_RECEIPTS.json'):
        before=json.loads((parent/filename).read_bytes());after=json.loads((here/filename).read_bytes())
        declared=dict(before['producer_files']);declared.pop(flow.OLD)
        raw=(root/WF).read_bytes();declared[WF]=dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
        if after['producer_files']!=declared:
            raise ValueError('S03_LAWFUL_EXACT_PRODUCER_REBIND_REQUIRED')
        for key,value in before.items():
            if key not in ('producer_files','package_workflow_name','S03_contract_derivation')and after.get(key)!=value:
                raise ValueError('S03_LAWFUL_INHERITED_OUTPUT_CONTRACT_CHANGED:'+key)
        if filename=='LATER_GENERATED_RECEIPTS.json'and after['package_workflow_name']!=flow.NAME:
            raise ValueError('S03_LAWFUL_CURRENT_PACKAGE_WORKFLOW_CONTEXT_REQUIRED')
    helper=load('s03_lawful_closed_source_scope_bindings',here/'derive.py')
    def historical_intake(actual_root,actual_here):
        path=root/'scripts/current-attendance-period-choice-native11-qualification/source_check.py'
        # First retain the parent's four exact history/count metadata changes.
        parent_deriver=load('s03_lawful_frozen_history_metadata_deriver',parent/'derive.py')
        first,history=parent_deriver.source_checker(path.read_bytes())
        value,scope=helper.substitute(first.encode(),helper.INNER_SOURCE_PAIRS)
        inner=ModuleType('s03_lawful_full_old_intake_scope_explicit')
        inner.__file__=str(path);inner.CURRENT_ALLOWED=allowed;inner.CURRENT_RECEIPT_HERE=here
        exec(compile(value,str(path),'exec'),inner.__dict__)
        return inner.check(actual_root,actual_here),dict(parent_history_metadata=history,current_scope=scope)
    private,proof=helper.module('s03_lawful_full_old425_no_projection',parent/'source_check.py',
        helper.SOURCE_PAIRS,CURRENT_ALLOWED=allowed,CURRENT_RECEIPT_HERE=here,
        CURRENT_HISTORICAL_INTAKE=historical_intake)
    inherited=private.check(root,parent,require_bound=True)
    business=load('s03_lawful_exact_three_callback_source',here/'business.py')
    _,callbacks=business.derive((root/business.ORIGINAL).read_bytes())
    negative=load('s03_lawful_exact_first_actual_negative',here/'negative.py').check(root,here)
    return dict(status='EXACT_FROZEN_RUNTIME15_LAWFUL_FIXTURE_FRESH11_THEN_READER3_PREPARED',
        files=len(source['files']),source_base=BASE,source_base_is_runtime_prerequisite=False,
        inherited425_closure=inherited,inherited_private_scope_derivation=proof,
        private_callback_derivation=callbacks,retained_first_actual_failure=negative,
        whole_current_product_sources_required=True,unchanged_committed_ALLOCATE_witness_required=True,
        actual_Native_cases=0,Native_executed=False,production_go=False,independent_acceptance=False)
