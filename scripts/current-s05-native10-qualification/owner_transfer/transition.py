"""File-only bounded successor: original calculation/cases/UI stay frozen."""
from hashlib import sha256
from pathlib import Path
import ast
import json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
BASE='20092281416c5c9beffea53a10c02d72aeab7ae1'
ORIGINAL_MANIFEST='2f13ad4ddcd5a3213fe13d4059aa7ab1061b60416e7bbe58efe88164e8380058'
ORIGINAL_STAGE='14d50554184423b1898bc4560506bfda4c91c3c5983501cd74321ffe6e51a22f'
ORIGINAL_SQL='44e26f9144cff011bf2fb9935d1a448955f8179a9ffaa6884557d8391651c5ab'
STAGE='scripts/cp7_accessory_standard_report/stage.py'
SQL='scripts/cp7_accessory_standard_report/report.sql'
CHANGED={'install_delta','uninstall_delta'}
ADDED={'installer_identity','installer_function_grants'}


def stage_transition(original,current):
    old,new=ast.parse(original),ast.parse(current)
    old_functions={n.name:n for n in old.body if isinstance(n,ast.FunctionDef)}
    new_functions={n.name:n for n in new.body if isinstance(n,ast.FunctionDef)}
    if set(new_functions)!=set(old_functions)|ADDED:
        raise ValueError('S05_INSTALLER_FUNCTION_SCOPE_CHANGED')
    for name in set(old_functions)-CHANGED:
        if ast.dump(old_functions[name])!=ast.dump(new_functions[name]):
            raise ValueError('S05_FROZEN_READER_OR_ORACLE_CHANGED: '+name)
    def other(tree):
        return [ast.dump(n)for n in tree.body if not isinstance(n,ast.FunctionDef)]
    if other(old)!=other(new):raise ValueError('S05_INSTALLER_MODULE_SCOPE_CHANGED')
    for name in CHANGED:
        node=new_functions[name]
        atomic=[n for n in node.body if isinstance(n,ast.With)]
        if len(atomic)!=1 or len(atomic[0].items)!=1 or ast.unparse(atomic[0].items[0].context_expr)!='predecessor.atomic(cur)':
            raise ValueError('S05_COMPLETE_INHERITED_ATOMIC_REQUIRED')
        text=ast.unparse(node)
        if 'as_owner' in text or 'installer_identity(cur)' not in text:
            raise ValueError('S05_EXPLICIT_OUTER_SUPERUSER_BOUNDARY_REQUIRED')
    return dict(changed_functions=sorted(CHANGED),added_installer_checks=sorted(ADDED),
                original_verify_transition_source_read_bodies_unchanged=True,inherited_atomic=True)


def check(repo=ROOT,here=HERE):
    repo,here=Path(repo),Path(here)
    retained=here/'retained'
    original=(retained/'component_SOURCE.json').read_bytes()
    if sha256(original).hexdigest()!=ORIGINAL_MANIFEST:raise ValueError('S05_ORIGINAL_MANIFEST_CHANGED')
    old=json.loads(original)
    original_stage=(retained/'stage.py').read_bytes()
    original_sql=(retained/'report.sql').read_bytes()
    if sha256(original_stage).hexdigest()!=ORIGINAL_STAGE or sha256(original_sql).hexdigest()!=ORIGINAL_SQL:
        raise ValueError('S05_ORIGINAL_INSTALLER_BYTES_CHANGED')
    current=json.loads((repo/'scripts/cp7_accessory_standard_report/SOURCE.json').read_bytes())
    if set(current['files'])!=set(old['files']):raise ValueError('S05_COMPONENT_FILE_SCOPE_CHANGED')
    for path,digest in old['files'].items():
        raw=(repo/path).read_bytes()
        if sha256(raw).hexdigest()!=current['files'][path]:raise ValueError('S05_CURRENT_COMPONENT_PIN_CHANGED: '+path)
        if path!=STAGE and (sha256(raw).hexdigest()!=digest or current['files'][path]!=digest):
            raise ValueError('S05_FROZEN_CALCULATION_CASE_UI_OR_PARENT_CHANGED: '+path)
    if (repo/SQL).read_bytes()!=original_sql:raise ValueError('S05_REPORT_SQL_MUST_REMAIN_BYTE_IDENTICAL')
    details=stage_transition(original_stage,(repo/STAGE).read_bytes())
    transition=current['installer_transition']
    if transition['base_head']!=BASE or transition['original_manifest_sha256']!=ORIGINAL_MANIFEST:
        raise ValueError('S05_INSTALLER_TRANSITION_BASE_CHANGED')
    return dict(status='EXACT_BOUNDED_INSTALLER_SUCCESSOR_ONLY',base_head=BASE,
                original_manifest_sha256=ORIGINAL_MANIFEST,report_sql_sha256=ORIGINAL_SQL,
                unchanged_component_files=len(old['files'])-1,details=details,
                Native_executions=0,production_go=False,independent_acceptance=False)
