"""Source-owned payment-correction stage over a verified fresh predecessor.

Administrative API only. The caller supplies one transaction. The full current
consumer owner must have just installed and verified its complete source and
22 catalog groups; this module never adopts an arbitrary live definition.
"""
from hashlib import sha256
from pathlib import Path
import re

from cp7_customer_credit.consumer import composition as consumer
from cp7_customer_credit.payment_correction import transform

HERE = Path(__file__).resolve().parent
TABLES = ('payment_source_context_v1', 'payment_source_legs_v1')
CONSTRAINTS = {f'cp7_credit.{name}:{name}_action_check' for name in
    ('source_operation_work_v1', 'source_operation_materializations_v1')}
OLD_CHECK = "CHECK ((action = ANY (ARRAY['RETURN_REVERSE'::text, 'PAYMENT_REVERSE'::text])))"
NEW_CHECK = "CHECK ((action = ANY (ARRAY['RETURN_REVERSE'::text, 'PAYMENT_REVERSE'::text, 'PAYMENT_CORRECT'::text])))"


def sources():
    names = (*transform.SQL_FILES, 'transform.py', 'composition.py')
    return {name:sha256((HERE/name).read_bytes()).hexdigest() for name in names}


def fragments():
    barrier = r"do \$not_an_installer\$begin raise exception 'OW04_PAYMENT_SOURCE_REQUIRES_COMPLETE_OWNING_COMPOSITION';end \$not_an_installer\$;"
    result = []
    for name in transform.SQL_FILES:
        text, count = re.subn(barrier, '', (HERE/name).read_text())
        if count != 1:
            raise ValueError('OW04_PAYMENT_SOURCE_COMPOSITION_BARRIER_CHANGED: '+name)
        result.append((name, text))
    return result


def new_function_names():
    text = '\n'.join(s for _, s in fragments())
    names = re.findall(r'\bcreate function (cp7_credit\.[a-z0-9_]+)\(', text)
    names += ['cp7_credit.payment_source_preflight_v1', 'cp7_credit.payment_source_ambient_guard_v1']
    if len(names) != len(set(names)):
        raise ValueError('OW04_PAYMENT_SOURCE_NEW_FUNCTION_DECLARATION_DUPLICATE')
    return set(names)


def _changed_catalog(before, after):
    return {group: {key:(before[group].get(key), after[group].get(key))
        for key in set(before[group]) | set(after[group])
        if before[group].get(key) != after[group].get(key)}
        for group in before if before[group] != after[group]}


def _admit_catalog(before, after, new_signatures):
    if set(before) != set(after) or len(after) != 22:
        raise ValueError('OW04_PAYMENT_SOURCE_COMPLETE_CATALOG_GROUP_SET_CHANGED')
    for group, rows in _changed_catalog(before, after).items():
        for key, (old, new) in rows.items():
            if new is None:
                raise ValueError('OW04_PAYMENT_SOURCE_UNDECLARED_REMOVAL: '+group+':'+key)
            if old is not None:
                if group == 'functions' and key in transform.CHANGED and old[1:] == new[1:]:
                    continue
                if group == 'constraints' and key in CONSTRAINTS and old[:-1] == new[:-1] \
                        and old[-1] == OLD_CHECK and new[-1] == NEW_CHECK:
                    continue
                raise ValueError('OW04_PAYMENT_SOURCE_UNDECLARED_EXISTING_CATALOG_DELTA: '+group+':'+key)
            if group == 'functions' and key in new_signatures:
                continue
            # Exactly two source-declared private relations and their Native
            # automatic type/index/constraint/policy/trigger objects, no FK to
            # or new trigger on any existing relation or ERP parent.
            if group in ('relations','columns','constraints','indexes','triggers','policies','types') and any(
                key == 'cp7_credit.'+table or key == 'cp7_credit.'+table+'[]'
                or key.startswith('cp7_credit.'+table+':') or
                group in ('relations','indexes') and key.startswith('cp7_credit.'+table+'_') for table in TABLES):
                continue
            raise ValueError('OW04_PAYMENT_SOURCE_UNDECLARED_NEW_CATALOG_OBJECT: '+group+':'+key)


def install(cur, predecessor_verified, catalog_reader):
    if predecessor_verified.get('catalog_groups') != 22 or predecessor_verified.get('legacy_definitions_projected') is not False:
        raise ValueError('OW04_PAYMENT_SOURCE_COMPLETE_FRESH_PREDECESSOR_PROOF_REQUIRED')
    before = catalog_reader(cur)
    if any(cur.execute('select to_regclass(%s)is not null', ('cp7_credit.'+name,)).fetchone()[0] for name in TABLES):
        raise ValueError('OW04_PAYMENT_SOURCE_ALREADY_INSTALLED')
    captures = {sig:consumer.capture(cur, sig) for sig in transform.CHANGED}
    catalog_before = consumer.function_catalog(cur)
    definitions = transform.derive(captures)
    source_manifest = sources()
    inventory = consumer.load('ow04_payment_source_context_inventory', HERE.parent/'integration/typed_context_inventory.py')
    with consumer.as_owner(cur, 'postgres'):
        cur.execute(transform.ambient_definition(inventory))
        cur.execute(transform.preflight_definition())
        for _, text in fragments():
            cur.execute(text)
        for definition in definitions.values():
            cur.execute(definition)
        existing_oids = set(catalog_before)
        new_rows = cur.execute("select p.oid::text,p.oid::regprocedure::text,n.nspname||'.'||p.proname from pg_proc p join pg_namespace n on n.oid=p.pronamespace where p.oid<>all(%s::oid[])",
            (list(existing_oids),)).fetchall()
        if {row[2] for row in new_rows} != new_function_names() or len(new_rows) != len(new_function_names()):
            raise ValueError('OW04_PAYMENT_SOURCE_NEW_FUNCTION_SET_CHANGED')
        for _, sig, _ in new_rows:
            cur.execute('alter function '+sig+' owner to postgres')
            cur.execute('revoke all on function '+sig+' from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write,cp7_credit_write')
    after = catalog_reader(cur)
    _admit_catalog(before, after, {row[1] for row in new_rows})
    state = dict(sources=source_manifest, captures=captures, definitions=definitions,
        before_catalog=before, after_catalog=after, catalog_before=catalog_before,
        catalog_after=consumer.function_catalog(cur), new_signatures=[row[1] for row in new_rows],
        new_functions={row[1]:consumer.capture(cur,row[1]) for row in new_rows},
        installed={sig:consumer.capture(cur,sig) for sig in transform.CHANGED},
        classification='ISOLATED_UNQUALIFIED_ACTUAL_OWNING_PAYMENT_CORRECTION_STAGE', production_go=False)
    verify(cur, state, catalog_reader)
    return state


def verify(cur, state, catalog_reader):
    if sources() != state['sources'] or consumer.function_catalog(cur) != state['catalog_after'] \
            or catalog_reader(cur) != state['after_catalog']:
        raise ValueError('OW04_PAYMENT_SOURCE_INSTALLED_SOURCE_OR_COMPLETE_CATALOG_CHANGED')
    for sig, row in {**state['new_functions'], **state['installed']}.items():
        if consumer.capture(cur,sig) != row:
            raise ValueError('OW04_PAYMENT_SOURCE_FUNCTION_SOURCE_OR_METADATA_CHANGED: '+sig)
    for sig, row in state['new_functions'].items():
        fingerprint = row['fingerprint']
        if fingerprint['owner'] != 'postgres' or fingerprint['privileges'] != [['postgres','postgres','EXECUTE',False]]:
            raise ValueError('OW04_PAYMENT_SOURCE_PRIVATE_FUNCTION_PRIVILEGES_CHANGED: '+sig)
    for table in TABLES:
        relation = 'cp7_credit.'+table
        if cur.execute("select pg_get_userbyid(relowner),relrowsecurity,relforcerowsecurity from pg_class where oid=%s::regclass", (relation,)).fetchone() != ('postgres',True,False):
            raise ValueError('OW04_PAYMENT_SOURCE_PRIVATE_TABLE_OWNER_OR_RLS_CHANGED')
        for role in ('anon','authenticated','service_role','cp7_capture','cp7_sales_read','cp7_sales_write','cp7_credit_write'):
            if cur.execute("select has_table_privilege(%s,%s,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')", (role,relation)).fetchone()[0]:
                raise ValueError('OW04_PAYMENT_SOURCE_PRIVATE_TABLE_DML_EXPOSED')
    cur.execute('select cp7_credit.assert_source_native_trigger_census_v1()')
    consumer.guard.verify(cur)
    return dict(status='EXACT_DECLARED_PAYMENT_SOURCE_STAGE_VERIFIED', complete_catalog_groups=22,
        changed_functions=len(transform.CHANGED), new_functions=len(state['new_functions']),
        new_Native_foreign_keys=0, Native_existing_triggers_changed=0, production_go=False)


def uninstall_preuse(cur, state, catalog_reader):
    verify(cur,state,catalog_reader)
    for table in TABLES:
        if cur.execute('select count(*)from cp7_credit.'+table).fetchone()[0]:
            raise ValueError('CP7_FULL_ROLLBACK_AFTER_USE_REQUIRES_BACKUP_RESTORE')
    with consumer.as_owner(cur,'postgres'):
        for table in TABLES:
            cur.execute('drop table cp7_credit.'+table)
        for sig, original in state['captures'].items():
            cur.execute(original['definition'])
        for sig in reversed(state['new_signatures']):
            cur.execute('drop function '+sig)
        for key in sorted(CONSTRAINTS):
            relation, name = key.split(':')
            cur.execute('alter table '+relation+' drop constraint '+name)
            cur.execute('alter table '+relation+' add constraint '+name+' '+OLD_CHECK)
    if catalog_reader(cur) != state['before_catalog'] or consumer.function_catalog(cur) != state['catalog_before']:
        raise ValueError('OW04_PAYMENT_SOURCE_PREDECESSOR_NOT_EXACTLY_RESTORED')
    return dict(status='PAYMENT_SOURCE_UNUSED_STAGE_EXACTLY_REMOVED', financial_facts_deleted=False)
