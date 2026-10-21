"""Pure source/metadata controls. Does not import a DB driver or execute SQL."""
from collections import Counter
from copy import deepcopy
from hashlib import sha256
import ast
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
REPO = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
    '/workspace/scratch/9442228ed2dc/ow04-reconciliation-writer')
MODEL = Path('/workspace/scratch/9442228ed2dc/ow04-next-scope-proposal/'
             'native-inverse-proof/trigger-guard/'
             'SYNTHETIC_CATALOG_MODEL_VERIFIED_PREDECESSOR.json')


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


base = REPO / 'scripts/cp7_customer_credit/integration/source_triggers'
builder = load('counter_source_acl', base / 'build_source_pins.py')
guard = load('counter_metadata_guard', base / 'trigger_guard.py')
derivation = json.loads((HERE / 'INITIAL_SOURCE_DERIVATION.json').read_text())
cases = []
for fn in derivation['expected']:
    source = (REPO / fn['source']).read_text()
    got = builder.fresh_trigger_acl(source, fn['identity'], fn['owner'])
    assert sorted(got, key=builder.canonical) == sorted(fn['acl'], key=builder.canonical)
    cases.append(dict(case=fn['identity'], status='PASS', acl=got))

source = (REPO / 'scripts/cp7-src/payroll/installments.sql').read_text()
clause = 'grant execute on all functions in schema cp7_installment to postgres;'
for name, changed in (
    ('missing', source.replace(clause, '')),
    ('comment_only', source.replace(clause, '--' + clause)),
    ('different_role', source.replace(clause, clause.replace('postgres', 'authenticated'))),
    ('grant_option', source.replace(clause, clause[:-1] + ' with grant option;')),
    ('duplicate', source + '\n' + clause),
):
    try:
        builder.fresh_trigger_acl(changed, 'cp7_installment.guard_journal()', 'cp7_installment_read')
    except ValueError as error:
        assert str(error) == 'SOURCE_INSTALLMENT_POSTGRES_EXECUTE_GRANT_CHANGED'
        cases.append(dict(case='grant_' + name, status='PASS', refusal=str(error)))
    else:
        raise AssertionError('SOURCE_GRANT_MUTATION_ACCEPTED: ' + name)

manifest = json.loads((HERE / 'REVIEWED_PRE_CORRECTION_SOURCE_PINS.json').read_text())
snapshot = json.loads(MODEL.read_text())['snapshot']
for phase in manifest['phases'].values():
    for fn in phase['functions']:
        found = next((f for f in derivation['expected'] if f['identity'] == fn['identity']), None)
        if found:
            fn['acl'] = deepcopy(found['acl'])
for fn in snapshot['functions']:
    found = next((f for f in derivation['expected'] if f['identity'] == fn['identity']), None)
    if found:
        fn['acl'] = deepcopy(found['acl'])
phase = 'VERIFIED_PREDECESSOR'
guard.validate_source(snapshot, manifest, phase)
cases.append(dict(case='source_corrected_synthetic_catalogue', status='PASS'))


def refuse(name, changed, code):
    try:
        guard.validate_source(changed, manifest, phase)
    except ValueError as error:
        message = str(error)
        assert message.startswith('OW04_BOUNDED_TRIGGER_GUARD_' + code + ': '), message
        detail = ast.literal_eval(message.split(': ', 1)[1])
        cases.append(dict(case=name, status='PASS', refusal=message, detail=detail))
        return detail
    raise AssertionError('CATALOGUE_MUTATION_ACCEPTED: ' + name)


for name, mutate in (
    ('unknown_authenticated', lambda f: f['acl'].append(dict(grantee='authenticated', privilege='EXECUTE', grantable=False))),
    ('unexpected_grant_option', lambda f: f['acl'].__setitem__(1, dict(grantee='postgres', privilege='EXECUTE', grantable=True))),
    ('missing_postgres', lambda f: f['acl'].pop()),
    ('duplicate_acl', lambda f: f['acl'].append(deepcopy(f['acl'][0]))),
):
    changed = deepcopy(snapshot)
    fn = next(f for f in changed['functions'] if f['identity'] == 'cp7_installment.guard_journal()')
    mutate(fn)
    detail = refuse(name, changed, 'FUNCTION_ACL')
    assert detail['function'] == fn['identity'] and detail['actual'] == fn['acl']
    assert detail['expected'] != detail['actual']

changed = deepcopy(snapshot)
removed = changed['foreign_keys'].pop()
detail = refuse('missing_FK_exact_delta', changed, 'FOREIGN_KEY_SOURCE_CENSUS')
assert detail == dict(missing=[dict(identity=guard.fk_key(removed['semantic']), count=1)], unknown=[])

changed = deepcopy(snapshot)
changed['foreign_keys'].append(deepcopy(changed['foreign_keys'][0]))
detail = refuse('duplicate_FK_exact_delta', changed, 'FOREIGN_KEY_SOURCE_CENSUS')
assert detail == dict(missing=[], unknown=[dict(identity=guard.fk_key(changed['foreign_keys'][0]['semantic']), count=1)])

changed = deepcopy(snapshot)
index = next(i for i, row in enumerate(changed['triggers']) if row['internal'])
removed = changed['triggers'].pop(index)
detail = refuse('missing_RI_exact_delta', changed, 'INTERNAL_ATTACHMENT_SOURCE_CENSUS')
key = (removed['relation'], guard.fk_key(removed['constraint']['semantic']), removed['function'],
       removed['trigger_type'], removed['deferrable'], removed['initially_deferred'], removed['referenced_relation'])
assert detail == dict(missing=[dict(identity=key, count=1)], unknown=[])

print(json.dumps(dict(classification='PURE_SOURCE_METADATA_NOT_PG_OR_NATIVE_EXECUTION',
    database_calls=0, status='PASS', count=len(cases), cases=cases,
    builder_sha256=sha256((base / 'build_source_pins.py').read_bytes()).hexdigest(),
    guard_sha256=sha256((base / 'trigger_guard.py').read_bytes()).hexdigest()), indent=2))
