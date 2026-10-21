"""Pure source/metadata regression: no database, native or Auth execution."""
from copy import deepcopy
import gzip
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import types

HERE = Path(__file__).resolve().parent
REPO = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else HERE.parents[5]
GUARD = REPO / 'scripts/cp7_customer_credit/integration/source_triggers/trigger_guard.py'
spec = importlib.util.spec_from_file_location('ri_owner_current_guard', GUARD)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)
manifest = json.loads((GUARD.parent / 'SOURCE_PINS.json').read_text())
snapshot = json.loads(gzip.decompress((HERE / 'SYNTHETIC_PREDECESSOR.json.gz').read_bytes()))['snapshot']
ordinary = {f['identity']: f for f in manifest['phases']['VERIFIED_PREDECESSOR']['functions']}
for fn in snapshot['functions']:
    if fn['identity'] in ordinary:
        # Same explicit installment ACL correction proved in the previous
        # controls. This is a synthetic model, never an accepted live capture.
        fn['acl'] = deepcopy(ordinary[fn['identity']]['acl'])
    else:
        assert fn['identity'].startswith('pg_catalog.RI_FKey_')
        fn['owner'] = 'supabase_admin'
        assert fn['owner_oid'] == 10

before = types.ModuleType('ri_owner_before_guard')
before.__file__ = str(GUARD)
old = subprocess.check_output(['git', 'show', '052d5b49:' + str(GUARD.relative_to(REPO))], cwd=REPO, text=True)
exec(compile(old, str(GUARD), 'exec'), before.__dict__)
cases = []

def refuses(module, name, value, reason):
    try:
        module.validate_source(value, manifest, 'VERIFIED_PREDECESSOR')
    except ValueError as error:
        assert str(error).startswith('OW04_BOUNDED_TRIGGER_GUARD_' + reason), str(error)
        cases.append(dict(case=name, status='PASS', expected='REFUSED', refusal=str(error)))
    else:
        raise AssertionError('BAD_METADATA_ACCEPTED: ' + name)

refuses(before, 'BEFORE_valid_supabase_bootstrap_owner_rejected', snapshot, 'UNKNOWN_INTERNAL_FUNCTION')
guard.validate_source(snapshot, manifest, 'VERIFIED_PREDECESSOR')
cases.append(dict(case='AFTER_exact_supabase_bootstrap_model', status='PASS', expected='ACCEPTED'))
text_oid = deepcopy(snapshot)
for fn in text_oid['functions']:
    if fn['identity'].startswith('pg_catalog.RI_FKey_'):
        fn['owner_oid'] = '10'
prior = types.ModuleType('ri_owner_first_fix_guard')
prior.__file__ = str(GUARD)
previous = subprocess.check_output(['git','show','1c9a4373:' + str(GUARD.relative_to(REPO))],cwd=REPO,text=True)
exec(compile(previous,str(GUARD),'exec'),prior.__dict__)
refuses(prior,'BEFORE_actual_json_oid_text_rejected',text_oid,'UNKNOWN_INTERNAL_FUNCTION')
guard.validate_source(text_oid,manifest,'VERIFIED_PREDECESSOR')
cases.append(dict(case='AFTER_actual_json_oid_text_accepted',status='PASS',expected='ACCEPTED'))
for name, field, value, reason in (
    ('ordinary_postgres_is_not_system_owner', 'owner', 'postgres', 'UNKNOWN_INTERNAL_FUNCTION'),
    ('browser_is_not_system_owner', 'owner', 'authenticated', 'UNKNOWN_INTERNAL_FUNCTION'),
    ('lookalike_role_different_oid', 'owner_oid', 10010, 'UNKNOWN_INTERNAL_FUNCTION'),
    ('float_oid_not_canonical', 'owner_oid', 10.0, 'UNKNOWN_INTERNAL_FUNCTION'),
    ('boolean_oid_refused', 'owner_oid', True, 'UNKNOWN_INTERNAL_FUNCTION'),
    ('noncanonical_oid_text_refused', 'owner_oid', '010', 'UNKNOWN_INTERNAL_FUNCTION'),
    ('plpgsql_is_not_internal', 'language', 'plpgsql', 'UNKNOWN_INTERNAL_FUNCTION'),
    ('security_definer_changed', 'security_definer', True, 'UNKNOWN_INTERNAL_FUNCTION'),
    ('function_configuration_changed', 'config', ['search_path=public'], 'UNKNOWN_INTERNAL_FUNCTION'),
    ('function_arguments_changed', 'input_arguments', 'p_id uuid', 'UNKNOWN_INTERNAL_FUNCTION'),
    ('function_result_changed', 'result', 'boolean', 'UNKNOWN_INTERNAL_FUNCTION'),
    ('builtin_entry_point_changed', 'body', 'not_the_builtin_entry', 'RI_INTERNAL_ENTRY_POINT'),
):
    changed = deepcopy(snapshot)
    fn = next(f for f in changed['functions'] if f['identity'].startswith('pg_catalog.RI_FKey_'))
    fn[field] = value
    refuses(guard, name, changed, reason)

for name, field, value in (
    ('disabled_RI_refused', 'enabled', 'D'),
    ('extra_RI_argument_refused', 'argument_count', 1),
    ('condition_on_RI_refused', 'condition', 'true'),
):
    changed = deepcopy(snapshot)
    next(t for t in changed['triggers'] if t['internal'])[field] = value
    refuses(guard, name, changed, 'INTERNAL_TRIGGER_SHAPE')
changed = deepcopy(snapshot)
changed['foreign_keys'].pop()
refuses(guard, 'missing_FK_still_refused', changed, 'FOREIGN_KEY_SOURCE_CENSUS')
changed = deepcopy(snapshot)
changed['triggers'].pop(next(i for i, t in enumerate(changed['triggers']) if t['internal']))
refuses(guard, 'missing_RI_still_refused', changed, 'INTERNAL_ATTACHMENT_SOURCE_CENSUS')
changed = deepcopy(snapshot)
next(f for f in changed['functions'] if f['identity'] in ordinary)['owner'] = 'supabase_admin'
refuses(guard, 'ordinary_ERP_owner_stays_source_owned', changed, 'FUNCTION_OWNER')

assert len(cases) == 22
print(json.dumps(dict(classification='PURE_SOURCE_METADATA_NOT_NATIVE', status='PASS', count=len(cases),
    database_calls=0, guard_sha256=sha256(GUARD.read_bytes()).hexdigest(), cases=cases), indent=2))
