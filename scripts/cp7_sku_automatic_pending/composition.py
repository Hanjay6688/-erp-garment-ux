"""Owning incremental installer; no workflow or acceptance is activated here."""
from hashlib import sha256
from pathlib import Path
from psycopg import sql
from cp7_laundry_unknown_wash.composition import as_owner
from cp7_sku_cost_components import composition as money_parent, prepared_product as money_product
from . import catalog_additions, installation_product

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CONTRACT = 'cp7.sku-automatic-pending.v5'
USED_ERROR = 'SKU_AUTOMATIC_PENDING_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE'


def parent():
    return money_parent


def runtime():
    return parent().runtime()


def sources():
    files = sorted(p for p in HERE.iterdir() if p.is_file() and p.suffix in ('.py', '.sql', '.json', '.md', '.mjs', '.inc'))
    accounting = HERE.parent / 'cp7_sku_pending_accounting/derivation.py'
    return dict(contract=CONTRACT, predecessor=parent().sources(),
                files={str(p.relative_to(ROOT)): sha256(p.read_bytes()).hexdigest() for p in [*files, accounting]},
                actual_ERP_cases=0, production_go=False, independent_acceptance=False)


def binding(catalog, prior, proof):
    return catalog.digest(dict(sources=prior['sources'], before=prior['before'], after=prior['after'],
                               parent_binding=prior['parent_binding'], definitions=prior['definitions'],
                               originals=prior['originals'], preinstall=prior['preinstall_data_and_sequences'],
                               preuse=prior['preuse_data_and_sequences'], proof=proof))


def prepared(before, prior):
    required = money_product.parent_original_signatures()
    originals = prior['predecessor']['originals']
    if not set(required) <= set(originals):
        raise ValueError('AUTOMATIC_FROZEN_PARENT_ORIGINALS_MISSING')
    product = installation_product.derive(before, prior['before'], {sig: originals[sig] for sig in required})
    profile, tables = catalog_additions.expected(product)
    return product, profile, tables


def verify(cur, state):
    _, _, _, _, catalog = runtime()
    catalog._authority(cur)
    if state['sources'] != sources():
        raise ValueError('AUTOMATIC_SOURCE_CHANGED')
    prior = state['predecessor']
    if prior['sources'] != parent().sources() or state['parent_binding'] != binding(catalog, prior, state['parent_proof']):
        raise ValueError('AUTOMATIC_PARENT_CHANGED')
    if state['before'] != prior['after']:
        raise ValueError('AUTOMATIC_PARENT_ALL22_CHANGED')
    product, profile, tables = prepared(state['before'], prior)
    if state['definitions'] != {sig: row[0] for sig, row in profile['replacement_functions'].items()}:
        raise ValueError('AUTOMATIC_NORMALIZED_DEFINITIONS_CHANGED')
    if state['originals'] != {sig: state['before']['functions'][sig][0] for sig in product['definitions']}:
        raise ValueError('AUTOMATIC_ORIGINAL_DEFINITIONS_CHANGED')
    actual = catalog._catalog_rows(cur)
    if actual != state['after']:
        raise ValueError('AUTOMATIC_ACTUAL_ALL22_CHANGED')
    catalog_additions.transition(state['before'], actual, profile)
    roles = [row[0] for row in cur.execute("select rolname from pg_roles where rolname in('anon','authenticated','service_role')or rolname like 'cp7_%'")]
    for role in roles:
        for table in tables:
            if cur.execute("select has_table_privilege(%s,%s,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')", (role, table)).fetchone()[0]:
                raise ValueError('AUTOMATIC_PRIVATE_TABLE_EXPOSED:' + role + ':' + table)
        for sig in profile['groups']['functions']:
            if cur.execute("select has_function_privilege(%s,%s,'EXECUTE')", (role, sig)).fetchone()[0]:
                raise ValueError('AUTOMATIC_PRIVATE_FUNCTION_EXPOSED:' + role + ':' + sig)
    return dict(status='SKU_AUTOMATIC_PENDING_EXACT_SOURCE_ALL22', new_tables=len(tables),
                new_private_functions=len(profile['groups']['functions']), replacement_functions=len(product['definitions']),
                actual_ERP_cases=0, production_go=False, independent_acceptance=False)


def install_delta(cur, prior):
    _, _, _, predecessor, catalog = runtime()
    with predecessor.atomic(cur):
        predecessor.predecessor.predecessor._locks(cur)
        proof = parent().verify(cur, prior)
        before, data = catalog._catalog_rows(cur), catalog._data(cur)
        product, profile, _ = prepared(before, prior)
        for sig, row in profile['replacement_before'].items():
            if before['functions'].get(sig) != row:
                raise ValueError('AUTOMATIC_FROZEN_PARENT_FUNCTION_CHANGED:' + sig)
        originals = {sig: before['functions'][sig][0] for sig in product['definitions']}
        with as_owner(cur, 'postgres'):
            cur.execute(product['ddl'], prepare=False)
            for definition in product['definitions'].values():
                cur.execute(definition, prepare=False)
        after = catalog._catalog_rows(cur)
        catalog_additions.transition(before, after, profile)
        state = dict(sources=sources(), predecessor=prior, parent_proof=proof,
                     parent_binding=binding(catalog, prior, proof), before=before, before_data=data,
                     originals=originals, definitions={sig: row[0] for sig, row in profile['replacement_functions'].items()},
                     after=after, preuse_data_and_sequences=catalog._data(cur),
                     preinstall_data_and_sequences=prior['preinstall_data_and_sequences'])
        verify(cur, state)
        return state


def install(cur):
    _, _, _, predecessor, _ = runtime()
    with predecessor.atomic(cur):
        return install_delta(cur, parent().install(cur))


def rollback_delta_preuse(cur, state):
    _, _, _, predecessor, catalog = runtime()
    with predecessor.atomic(cur):
        predecessor.predecessor.predecessor._locks(cur)
        verify(cur, state)
        catalog._lock_tables(cur)
        if catalog._data(cur) != state['preuse_data_and_sequences']:
            raise ValueError(USED_ERROR)
        _, profile, tables = prepared(state['before'], state['predecessor'])
        with as_owner(cur, 'postgres'):
            for original in state['originals'].values():
                cur.execute(original, prepare=False)
            for sig in reversed(tuple(profile['groups']['functions'])):
                cur.execute(sql.SQL('drop function ' + sig))
            for table in reversed(tables):
                cur.execute(sql.SQL('drop table {}').format(sql.Identifier(*table.split('.'))))
        if catalog._catalog_rows(cur) != state['before'] or catalog._data(cur) != state['before_data']:
            raise ValueError('AUTOMATIC_EXACT_PARENT_NOT_RESTORED')
        return dict(status='SKU_AUTOMATIC_PENDING_EXACT_PREUSE_DELTA_RESTORE',
                    used_guard_before_DDL=True, parent_verified=parent().verify(cur, state['predecessor']))


def rollback_preuse(cur, state):
    _, _, _, predecessor, _ = runtime()
    with predecessor.atomic(cur):
        delta = rollback_delta_preuse(cur, state)
        return dict(status='SKU_AUTOMATIC_PENDING_FULL_PREUSE_RESTORE', delta=delta,
                    parent=parent().rollback_preuse(cur, state['predecessor']))
