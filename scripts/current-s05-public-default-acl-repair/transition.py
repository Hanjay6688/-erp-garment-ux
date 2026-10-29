"""File-only, exact b0-to-new-public-ACL transition. No runtime imports."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import ast
import json
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
COMPONENT = 'scripts/cp7_accessory_standard_report/'
BASE = 'b0e5ac05e2024d5673126b6fe7759591293b9b96'
BASE_TREE = '3820c7348167fc750cc3f3f36645f14f76286e44'
OLD = {
    'SOURCE.json': '1a2e3a0e72de364afb472b86a59907465d224a750889292f5095014619dd86dd',
    'stage.py': 'a30e254ddf5cba7f3f74524b2be98ce4a34c5008b4e775c25d79849f5eaa7d87',
    'report.sql': '44e26f9144cff011bf2fb9935d1a448955f8179a9ffaa6884557d8391651c5ab',
}
ANCHOR = ('revoke all on function public.erp_cp7_get_accessory_standard_report_v1'
          '(date,date,uuid,uuid,text,integer,integer)from public,anon,service_role,cp7_capture;')
REPLACEMENT = ANCHOR[:-1]+',postgres;'
CHECKER = 'installer_function_grants'


def sql_transition(original, current):
    anchor, replacement = ANCHOR.encode(), REPLACEMENT.encode()
    if original.count(anchor) != 1 or current != original.replace(anchor, replacement, 1):
        raise ValueError('S05_EXACT_ONE_NEW_PUBLIC_REVOKE_ONLY')
    bodies = lambda text: dict(re.findall(r'create function\s+([\w.]+)\([^$]*?as \$\$(.*?)\$\$;',
                                          text.decode(), re.I | re.S))
    old, new = bodies(original), bodies(current)
    if len(old) != 5 or old != new:
        raise ValueError('S05_FIVE_REPORT_FUNCTION_BODIES_CHANGED')
    return dict(SQL_substitutions=1, function_bodies_changed=0,
                function_body_sha256={name: sha256(body.encode()).hexdigest() for name, body in old.items()})


def stage_transition(original, current):
    old, new = ast.parse(original), ast.parse(current)
    old_functions = {n.name: n for n in old.body if isinstance(n, ast.FunctionDef)}
    new_functions = {n.name: n for n in new.body if isinstance(n, ast.FunctionDef)}
    if set(old_functions) != set(new_functions):
        raise ValueError('S05_STAGE_FUNCTION_SCOPE_CHANGED')
    for name in old_functions:
        if name != CHECKER and ast.dump(old_functions[name]) != ast.dump(new_functions[name]):
            raise ValueError('S05_FROZEN_STAGE_FUNCTION_CHANGED: '+name)
    outside = lambda tree: [ast.dump(n) for n in tree.body if not isinstance(n, ast.FunctionDef)]
    if outside(old) != outside(new):
        raise ValueError('S05_STAGE_MODULE_SCOPE_CHANGED')
    original_check = old_functions[CHECKER]
    successor_check = deepcopy(new_functions[CHECKER])
    old_refusals = [n for n in ast.walk(original_check) if isinstance(n, ast.If)
                    and ast.unparse(n.test) == 'len(rows) != len(expected) or set(rows) != expected']
    new_refusals = [n for n in ast.walk(successor_check) if isinstance(n, ast.If)
                    and ast.unparse(n.test) == 'len(rows) != len(expected) or set(rows) != expected']
    if len(old_refusals) != 1 or len(new_refusals) != 1:
        raise ValueError('S05_STRICT_FUNCTION_ACL_COMPARISON_CHANGED')
    body = new_refusals[0].body
    if not isinstance(body[-1], ast.Raise) or not isinstance(body[0], ast.Assign) or ast.unparse(body[0]) != 'limit = 16':
        raise ValueError('S05_BOUNDED_FAILURE_DIAGNOSTIC_REQUIRED')
    text = ast.unparse(ast.Module(body=body, type_ignores=[]))
    required = ('actual_acl_total', 'actual_acl_omitted', 'installer_function_default_acl_rows',
                'installer_function_default_acl_total', 'installer_function_default_acl_omitted',
                "d.defaclobjtype='f'", 'limit 17', 'count(*)over()')
    if any(token not in text for token in required):
        raise ValueError('S05_EXACT_FAILURE_DIAGNOSTIC_SCOPE_CHANGED')
    new_refusals[0].body = deepcopy(old_refusals[0].body)
    if ast.dump(original_check) != ast.dump(successor_check):
        raise ValueError('S05_CHECKER_CHANGED_OUTSIDE_FAILURE_DIAGNOSTIC')
    return dict(changed_functions=[CHECKER], original_strict_ACL_comparison_unchanged=True,
                original_verify_install_uninstall_sources_unchanged=True,
                diagnostic_rows_per_group=16, arbitrary_grants_normalized=False)


def check(repo=ROOT, here=HERE):
    repo, here = Path(repo), Path(here)
    retained = {}
    for name, digest in OLD.items():
        raw = (here/'retained'/name).read_bytes()
        if sha256(raw).hexdigest() != digest:
            raise ValueError('S05_B0_RETAINED_SOURCE_CHANGED: '+name)
        retained[name] = raw
    old = json.loads(retained['SOURCE.json'])
    current = json.loads((repo/(COMPONENT+'SOURCE.json')).read_bytes())
    if set(current['files']) != set(old['files']):
        raise ValueError('S05_COMPONENT_FILE_SCOPE_CHANGED')
    changed = {COMPONENT+'stage.py', COMPONENT+'report.sql'}
    for path, digest in old['files'].items():
        raw = (repo/path).read_bytes()
        if sha256(raw).hexdigest() != current['files'][path]:
            raise ValueError('S05_CURRENT_COMPONENT_PIN_CHANGED: '+path)
        if path not in changed and current['files'][path] != digest:
            raise ValueError('S05_FROZEN_CALCULATION_CALLBACK_UI_PARENT_CHANGED: '+path)
    old_shape = deepcopy(current)
    declaration = old_shape.pop('installer_transition')
    old_shape['installer_transition'] = old_shape.pop('historical_installer_transition')
    old_shape['files'] = old['files']
    if old_shape != old:
        raise ValueError('S05_COMPONENT_METADATA_OUTSIDE_TRANSITION_CHANGED')
    if (declaration['base_head'], declaration['base_tree'], declaration['original_manifest_sha256']) != (
            BASE, BASE_TREE, OLD['SOURCE.json']):
        raise ValueError('S05_PUBLIC_ACL_TRANSITION_BASE_CHANGED')
    if (declaration['SQL_edits'], declaration['function_bodies_changed'], declaration['Native_case_callbacks_changed'],
        declaration['verifier_changed'], declaration['default_privileges_changed'], declaration['schema_ACL_changed'],
        declaration['role_or_membership_changes'], declaration['Native_executions'],
        declaration['independent_acceptance'], declaration['production_go']) != (1, 0, 0, False, False, False, 0, 0, False, False):
        raise ValueError('S05_PUBLIC_ACL_TRANSITION_SCOPE_CHANGED')
    for name in ('stage.py', 'report.sql'):
        key = 'successor_stage_sha256' if name == 'stage.py' else 'successor_report_sql_sha256'
        if declaration[key] != current['files'][COMPONENT+name]:
            raise ValueError('S05_PUBLIC_ACL_TRANSITION_PIN_CHANGED')
    sql = sql_transition(retained['report.sql'], (repo/(COMPONENT+'report.sql')).read_bytes())
    stage = stage_transition(retained['stage.py'], (repo/(COMPONENT+'stage.py')).read_bytes())
    return dict(status='EXACT_B0_PUBLIC_ACL_AND_BOUNDED_DIAGNOSTIC_SUCCESSOR',
        failed_base=BASE, base_tree=BASE_TREE, original_manifest_sha256=OLD['SOURCE.json'],
        current_manifest_sha256=sha256((repo/(COMPONENT+'SOURCE.json')).read_bytes()).hexdigest(),
        unchanged_component_files=len(old['files'])-2, SQL=sql, installer=stage,
        Native_executions=0, database_calls=0, actual_CI_extra_tuple_identity_proven=False,
        independent_acceptance=False, production_go=False)


if __name__ == '__main__':
    print(json.dumps(check(), indent=2))
