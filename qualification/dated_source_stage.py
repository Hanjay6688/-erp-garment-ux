"""Install the dated source-custody repair over the qualified Vendor stage."""

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path


HERE = Path(__file__).resolve().parent
SCHEMA = 'cp7_vendor_receivable'
APPLY = 'erp.bd_apply_vendor_credit_v1(text,uuid,text,uuid,numeric,date,text,uuid)'
PROVE = SCHEMA + '.prove_v1(uuid)'
REFUND = SCHEMA + '.refund_v1(jsonb,uuid)'
HELPERS = (
    SCHEMA + '.source_journal_deltas_v1(uuid,uuid)',
    SCHEMA + '.assert_source_debit_v1(text,uuid,date,numeric)',
)
PREIMAGES = {
    APPLY: '490d632af17123df479fa02081595ff3965f613ccbc90d22f5877b43364273e0',
    PROVE: '69d81338432fc6bd56946c5fcc9466f350f84183e0675e2f7209080b453f0fe5',
    REFUND: 'c2516dfac1a9ef8e869e510c7f8fff7e021c74cf02b5d922022104f15e6d9919',
}
POSTIMAGES = {
    APPLY: '31e211a6eda49973145e8cb229fda290bee739621204902437b228eb507dd8bb',
    PROVE: 'f9b99323ecbe2c19a68aec63bc5a50244d01f3c77375b3a777ab8e21ca68edb7',
    REFUND: '42e9ebf747374348a031be9b72a22b4582160a32a874051def0b54c799ae1e48',
    HELPERS[0]: '4a1bb6cc47b9692914dcbf96899edf7172ee5ffddf00f076329870ebe035c544',
    HELPERS[1]: '255acea1c8bf2b14352d680fdcaf71ecab9f65f7a962e7009cdee82bffbdf0e6',
}
VENDOR_SOURCES = {
    'composition.py': 'b0bc106121932deb18a342299ec7ffb1a314abaca9d77879df29784261821df2',
    'native_delta.py': 'bd0f41be50fea0ab64b19c15d8a09fc7940782507c35482911dd86c36403a52b',
    'receivable.sql': '3b24728512e8be6af697f3234e591f7fe6b46331c68e3497ab71aedbcc9aa2ba',
}
SQL_SHA = '33b7ca6b0078a5f634b71b36e9d4ebf47fedc5ad34d8272b7b4bbd70a30c02e1'
OWNER_ACL = [['postgres', 'postgres', 'EXECUTE', False]]
PRIVATE_GRANTEES = 'public,anon,authenticated,service_role'


def require(value, reason):
    if not value:
        raise ValueError(reason)


def sql_source():
    raw = (HERE / 'dated_source.sql').read_bytes()
    require(sha256(raw).hexdigest() == SQL_SHA, 'S02_DATED_SOURCE_REVIEWED_SQL_CHANGED')
    return raw.decode()


def apply_body(definition):
    for indent, table in (('    ', 'vendor_payments'), ('  ', 'opening_subledger_settlements')):
        anchor = indent + f'insert into erp.{table}(id,'
        guard = indent + 'perform cp7_vendor_receivable.assert_source_debit_v1(p_kind,p_source,p_date,p_amount);\n'
        require(definition.count(anchor) == 1 and guard + anchor not in definition,
                'S02_DATED_SOURCE_APPLY_ANCHOR_CHANGED:' + table)
        definition = definition.replace(anchor, guard + anchor, 1)
    require(sha256(definition.encode()).hexdigest() == POSTIMAGES[APPLY], 'S02_DATED_SOURCE_APPLY_POSTIMAGE_CHANGED')
    return definition


def verify_transition(before, after):
    require(len(before) == 22 and before.keys() == after.keys(), 'S02_DATED_SOURCE_ALL22_REQUIRED')
    for group in before.keys() - {'functions'}:
        require(before[group] == after[group], 'S02_DATED_SOURCE_CATALOGUE_CHANGED:' + group)
    old, new = before['functions'], after['functions']
    require(set(new) == set(old) | set(HELPERS) and not set(HELPERS) & old.keys(),
            'S02_DATED_SOURCE_FUNCTION_SET_CHANGED')
    for signature, definition in old.items():
        actual = new[signature]
        if signature in PREIMAGES:
            require(actual[1:] == definition[1:], 'S02_DATED_SOURCE_AUTHORITY_CHANGED:' + signature)
        else:
            require(actual == definition, 'S02_DATED_SOURCE_UNDECLARED_FUNCTION_CHANGED:' + signature)
    for signature, expected in POSTIMAGES.items():
        actual = new[signature]
        require(sha256(actual[0].encode()).hexdigest() == expected and actual[-1] == OWNER_ACL,
                'S02_DATED_SOURCE_WRONG_BODY_OR_ACL:' + signature)
    for signature, language, volatility in zip(HELPERS, ('sql', 'plpgsql'), ('s', 'v'), strict=True):
        row = new[signature]
        require(row[1:5] == ['postgres', language, 'f', True]
                and row[8] == volatility and row[12] == ['search_path=""'],
                'S02_DATED_SOURCE_HELPER_AUTHORITY_CHANGED:' + signature)


def native_identity(cur, signatures):
    rows = cur.execute('''select name,p.oid,p.proacl::text,pg_get_userbyid(p.proowner),n.nspname,n.nspacl::text
        from unnest(%s::text[]) as names(name) join pg_proc p on p.oid=to_regprocedure(name)
        join pg_namespace n on n.oid=p.pronamespace''', (list(signatures),)).fetchall()
    require({row[0] for row in rows} == set(signatures) and all(row[3] == 'postgres' for row in rows),
            'S02_DATED_SOURCE_EXACT_POSTGRES_FUNCTIONS_REQUIRED')
    return {name: identity for name, *identity in rows}


@dataclass(frozen=True)
class Installed:
    parent: dict
    before: dict
    after: dict
    data: dict
    identity_before: dict
    identity_after: dict


def verify_parent_source(parent, state):
    manifest = parent.sources()
    pins = {'scripts/cp7_vendor_receivable/' + file: pin for file, pin in VENDOR_SOURCES.items()}
    require(state['sources'] == manifest and manifest['files'] == pins
            and manifest['contract'] == 'cp7.vendor-receivable.v1', 'S02_DATED_SOURCE_EXACT_VENDOR_41C_REQUIRED')


def verify(cur, parent, state):
    verify_parent_source(parent, state.parent)
    _, _, _, _, catalog = parent.runtime()
    catalog._authority(cur)
    require(state.parent['after'] == state.before, 'S02_DATED_SOURCE_VENDOR_CATALOGUE_BINDING_CHANGED')
    require(catalog._catalog_rows(cur) == state.after, 'S02_DATED_SOURCE_LIVE_ALL22_CHANGED')
    verify_transition(state.before, state.after)
    require(native_identity(cur, POSTIMAGES) == state.identity_after
            and all(state.identity_before[signature] == state.identity_after[signature] for signature in PREIMAGES),
            'S02_DATED_SOURCE_OID_OR_RAW_ACL_CHANGED')
    return dict(status='S02_DATED_SOURCE_EXACT_ALL22', existing_replacements=len(PREIMAGES),
                new_private_functions=len(HELPERS), new_public_rpcs=0, production_go=False)


def install_delta(cur, parent, prior):
    verify_parent_source(parent, prior)
    _, _, _, base, catalog = parent.runtime()
    with base.atomic(cur):
        base.predecessor.predecessor._locks(cur)
        proof = parent.verify(cur, prior)
        require(proof['status'] == 'VENDOR_RECEIVABLE_EXACT_SOURCE_AND_ALL22', 'S02_DATED_SOURCE_VENDOR_VERIFY_REQUIRED')
        before = prior['after']
        originals = {signature: before['functions'][signature][0] for signature in PREIMAGES}
        require(all(sha256(definition.encode()).hexdigest() == PREIMAGES[signature]
                    for signature, definition in originals.items()), 'S02_DATED_SOURCE_VENDOR_BODIES_CHANGED')
        require(not set(HELPERS) & before['functions'].keys(), 'S02_DATED_SOURCE_ALREADY_INSTALLED')
        data = catalog._data(cur)
        identity = native_identity(cur, PREIMAGES)
        with parent.as_owner(cur, 'postgres'):
            cur.execute(sql_source(), prepare=False)
            cur.execute('revoke all on function ' + ','.join(HELPERS) + ' from ' + PRIVATE_GRANTEES)
            cur.execute(apply_body(originals[APPLY]), prepare=False)
        after = catalog._catalog_rows(cur)
        actual_identity = native_identity(cur, POSTIMAGES)
        require(catalog._data(cur) == data, 'S02_DATED_SOURCE_INSTALL_CHANGED_DATA_OR_SEQUENCE')
        state = Installed(prior, before, after, data, identity, actual_identity)
        verify(cur, parent, state)
        return state


def rollback_delta_preuse(cur, parent, state):
    _, _, _, base, catalog = parent.runtime()
    with base.atomic(cur):
        base.predecessor.predecessor._locks(cur)
        verify(cur, parent, state)
        catalog._lock_tables(cur)
        require(catalog._data(cur) == state.data, 'S02_DATED_SOURCE_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE')
        with parent.as_owner(cur, 'postgres'):
            for signature in PREIMAGES:
                cur.execute(state.before['functions'][signature][0], prepare=False)
            for signature in reversed(HELPERS):
                cur.execute('drop function ' + signature + ' restrict')
        require(native_identity(cur, PREIMAGES) == state.identity_before and catalog._data(cur) == state.data,
                'S02_DATED_SOURCE_PREUSE_RESTORE_CHANGED_DATA_OR_RAW_AUTHORITY')
        proof = parent.verify(cur, state.parent)
        require(proof['status'] == 'VENDOR_RECEIVABLE_EXACT_SOURCE_AND_ALL22', 'S02_DATED_SOURCE_VENDOR_NOT_RESTORED')
        return dict(status='S02_DATED_SOURCE_PREUSE_RESTORED', parent_verified=proof, used_guard_before_DDL=True)
