"""Install the Enteng credit correction candidate with a managed project role.

The caller must verify the managed OW04 predecessor and supply an open,
quiescent maintenance transaction. This module neither connects nor commits.
Final composition, hosted installation and go-live admission are separate.
"""

from contextlib import contextmanager
from hashlib import sha256
import json
from pathlib import Path

from psycopg import sql
from psycopg.pq import TransactionStatus

import cp7_ow04_restore_bundle as catalog
from cp7_customer_credit.consumer import composition as consumer
from cp7_customer_credit.payment_correction import composition as payment
from cp7_enteng_managed_credit import installer_memberships
import cp7_enteng_managed_identity as identity
from cp7_credit_followups import composition as followups
from cp7_credit_remaining import composition as remaining
from cp7_credit_multi import composition as multi
from cp7_credit_incoming import composition as incoming
from cp7_credit_correction_de import composition as return_correction
from cp7_credit_correction_de import e_composition as note_carry


REPO = Path(__file__).resolve().parents[1]
NATIVE_REFERENCE = REPO / 'scripts/cp7_complete_credit_de/RECORDED_NATIVE_CAPTURES.json'
NATIVE_REFERENCE_SHA256 = 'c5c18ca3d68e373ecaef8ec992e168564e21f37d9a0ee190414322e1688de214'
NOTE_CARRY_UTC = {
    'note_carry/03_readers.sql': ('940200b5320189bd424a99ccef9cc92846dd576a6c6d4bd2e8f1e25afd3325d8', {
        'effective_target_v1(p_event uuid)returns uuid': 'plpgsql stable',
        'raw_document_v1(p_sale uuid)returns jsonb': 'sql stable',
    }),
    'note_carry/06_owning.sql': ('0c00bb08274827e6295ada3ed4e4b8e7d917ed1bc1a996aaa0685d0fd1772c94', {
        'assert_work_v1()returns void': 'plpgsql volatile',
    }),
    'note_carry/07_profile_closure.sql': ('8e82c257ca20a4dcac5cf0dad2f1e487c2e202caea7fa466503019003d3f75ac', {
        'assert_historical_v1(p_root uuid)returns void': 'plpgsql stable',
        'assert_closed_v1(p_operation uuid)returns void': 'plpgsql stable',
    }),
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


@contextmanager
def temporary_roles(cur, roles):
    """Open SET only. Any exception returns through the enclosing savepoint."""
    before = installer_memberships(cur)
    added = {(name, 'postgres', False, False, True) for name in roles}
    for name in roles:
        identity.validate_role(cur.connection, name)
        rights = cur.execute("select pg_has_role('postgres',%s,'SET'),pg_has_role('postgres',%s,'USAGE')", (name, name)).fetchone()
        require(rights == (False, False) and any(edge[0] == name and edge[2:] == (True, False, False) for edge in before),
                'Unexpected managed role authority: ' + name)
    names = sql.SQL(',').join(map(sql.Identifier, roles))
    cur.execute(sql.SQL('grant {} to postgres with inherit false, set true granted by postgres').format(names))
    require(installer_memberships(cur) == before | added, 'Unexpected managed role grants during installation')
    yield
    cur.execute(sql.SQL('revoke {} from postgres granted by postgres restrict').format(names))
    require(installer_memberships(cur) == before, 'Temporary managed role grants remain after installation')


@contextmanager
def payment_ddl(cur):
    raw_acl = cur.execute("select nspowner::regrole::text,nspacl::text from pg_namespace where nspname='cp7_payment_correction'").fetchone()
    require(raw_acl and raw_acl[0] == 'cp7_sales_read' and raw_acl[1], 'Unexpected payment correction schema authority')
    require(cur.execute("select has_schema_privilege('postgres','cp7_payment_correction','CREATE')").fetchone() == (False,),
            'Payment correction requires the expected closed CREATE privilege')
    with temporary_roles(cur, ('cp7_sales_read',)):
        cur.execute('set local role cp7_sales_read')
        cur.execute('grant create on schema cp7_payment_correction to postgres')
        cur.execute('reset role')
        yield
        cur.execute('set local role cp7_sales_read')
        cur.execute('revoke create on schema cp7_payment_correction from postgres')
        cur.execute('reset role')
    require(cur.execute("select nspowner::regrole::text,nspacl::text from pg_namespace where nspname='cp7_payment_correction'").fetchone() == raw_acl,
            'Payment correction schema ACL was not restored exactly')


def verify_only_payment_ddl(before, after):
    delta = payment._changed_catalog(before, after)
    require(set(delta) == {'memberships', 'schemas'}
            and delta['memberships'] == {'cp7_sales_read:postgres:postgres': (None, [False, False, True])}
            and set(delta['schemas']) == {'cp7_payment_correction'}, 'Unexpected payment DDL catalogue delta')
    original, opened = delta['schemas']['cp7_payment_correction']
    added = ['postgres', 'cp7_sales_read', 'CREATE', False]
    require(original[0] == opened[0] == 'cp7_sales_read'
            and [grant for grant in opened[1] if grant != added] == original[1]
            and len(opened[1]) == len(original[1]) + 1, 'Unexpected payment DDL schema ACL change')


def reader_stage(cur, stage, filename, predecessor):
    before = catalog._catalog_rows(cur)
    require(stage.SCHEMA not in before['schemas'], 'Credit schema already installed: ' + stage.SCHEMA)
    signatures = stage.native_delta.SIGNATURES
    require(all(before['functions'].get(sig, [None, None])[1] == 'postgres' for sig in signatures),
            'Unexpected credit reader input authority: ' + stage.SCHEMA)
    original = {sig: before['functions'][sig][0] for sig in signatures}
    definitions = stage.native_delta.patched(original)
    cur.execute((stage.ROOT / filename).read_text(), prepare=False)
    for ddl in definitions.values():
        cur.execute(ddl, prepare=False)
    after = catalog._catalog_rows(cur)
    stage.admit_catalog(before, after, definitions)
    require(set(after['functions']) - set(before['functions']) == set(stage.READERS),
            'Unexpected credit reader additions: ' + stage.SCHEMA)
    state = dict(predecessor=predecessor, sources=stage.sources(), definitions=definitions)
    return state, stage.verify_objects(cur, state)


HOOKS = {
    'cp7_credit_correction_de': ('quote_v1', 'prepare_v1', 'finish_v1'),
    'cp7_credit_note_carry_de': ('basis_v1', 'prepare_v1', 'finish_v1'),
}


def qualify_raw_sources(cur):
    raw = NATIVE_REFERENCE.read_bytes()
    require(sha256(raw).hexdigest() == NATIVE_REFERENCE_SHA256, 'Reviewed D1/E1 predecessor record changed')
    reference = json.loads(raw)
    expected = reference['functions']
    before = catalog._catalog_rows(cur)['functions']
    qualified = []
    narrowed = []
    owners = return_correction.PUBLIC_OWNERS | note_carry.PUBLIC_OWNERS
    for sig, row in expected.items():
        actual = before.get(sig)
        if actual == row:
            qualified.append(sig)
            continue
        # Stock PG gave postgres explicit EXECUTE on these four owner facades.
        # Managed keeps the original operator/owner grants and a narrower ACL.
        if sig not in owners or actual is None or actual[:-1] != row[:-1]:
            raise ValueError('Credit source or authority differs from the exact admitted predecessor: ' + sig)
        extra = ['postgres', owners[sig], 'EXECUTE', False]
        if extra not in row[-1] or actual[-1] != [entry for entry in row[-1] if entry != extra]:
            raise ValueError('Unsupported managed facade ACL: ' + sig)
        narrowed.append(sig)
    return {'reference_head': reference['head'], 'reference_sha256': NATIVE_REFERENCE_SHA256,
            'exact': len(qualified), 'narrower_postgres_acl': narrowed}


def function_identity(cur, signatures):
    return cur.execute("""
        select name,p.oid,p.proowner,p.proacl::text from unnest(%s::text[]) name
        join pg_proc p on p.oid=to_regprocedure(name) order by name collate "C"
    """, (sorted(signatures),)).fetchall()


def verify_correction_access(cur, stage):
    schema = stage.SCHEMA
    if stage is return_correction:
        allowed = {f'{schema}.workspace_v1(jsonb)': 'cp7_sales_read',
                   f'{schema}.dispatch_v1(jsonb,uuid,text)': 'cp7_sales_write'}
    else:
        allowed = {f'{schema}.workspace_v1(uuid)': 'cp7_sales_write',
                   f'{schema}.dispatch_v1(jsonb,uuid,text)': 'cp7_sales_write'}
    roles = [row[0] for row in cur.execute("select rolname from pg_roles where rolname in ('anon','authenticated','service_role') or rolname like 'cp7_%'")]
    declared = stage.sql_functions()
    for signature in stage.functions():
        owner, definer, volatility, config = cur.execute('select proowner::regrole::text,prosecdef,provolatile,proconfig from pg_proc where oid=to_regprocedure(%s)', (signature,)).fetchone()
        if owner != 'postgres':
            raise ValueError('Unexpected correction owner: ' + signature)
        expected = declared.get(signature)
        if expected and ((definer, volatility) != expected or 'search_path=""' not in (config or ())):
            raise ValueError('Unexpected correction security attributes: ' + signature)
        rights = {row[0] for row in cur.execute("select r from unnest(%s::text[]) r where has_function_privilege(r,%s,'EXECUTE')", (roles, signature))}
        if rights != ({allowed[signature]} if signature in allowed else set()):
            raise ValueError('Unexpected correction execution grant: ' + signature)
    schema_rights = {r[0] for r in cur.execute("select r from unnest(%s::text[]) r where has_schema_privilege(r,%s,'USAGE')", (roles, schema))}
    require(schema_rights == set(allowed.values()), 'Unexpected correction schema privilege: ' + schema)
    for table in stage.TABLES:
        authority = cur.execute('select relowner::regrole::text,relrowsecurity from pg_class where oid=to_regclass(%s)', (table,)).fetchone()
        rights = cur.execute("select r from unnest(%s::text[]) r where has_table_privilege(r,%s,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')", (roles, table)).fetchall()
        require(authority == ('postgres', True) and not rights, 'Unexpected correction table authority: ' + table)


def correction_stage(cur, stage):
    schema = stage.SCHEMA
    before = catalog._catalog_rows(cur)
    require(schema not in before['schemas'], 'Credit correction schema already installed: ' + schema)
    captured = {sig: before['functions'][sig][0] for sig in stage.native_delta.CAPTURES}
    definitions = stage.native_delta.derive(captured)
    original_identity = function_identity(cur, captured)
    for name in stage.SQL:
        ddl = (stage.HERE / name).read_text()
        if stage is note_carry and name in NOTE_CARRY_UTC:
            source_hash, declarations = NOTE_CARRY_UTC[name]
            require(sha256(ddl.encode()).hexdigest() == source_hash, 'Reviewed note carry SQL changed: ' + name)
            # Persist and compare period, event and receipt timestamps in the
            # same representation, including deferred checks after the RPC.
            for declaration, language in declarations.items():
                previous = (f"create function {schema}.{declaration}\n"
                            f"language {language} security definer set search_path=''as $$")
                require(ddl.count(previous) == 1, 'Note carry declaration changed: ' + declaration)
                ddl = ddl.replace(previous, previous.replace("as $$", "set TimeZone='UTC'as $$"), 1)
            if name == 'note_carry/07_profile_closure.sql':
                # Preserve the original receipt text and verify its instant.
                # Native note responses keep the session's display time zone.
                old = "  'effective_at',(select sale_date from erp.sales_headers where id=o.source_sale_id));"
                new = """  'effective_at',o.response->'effective_at');
 if (o.response->>'effective_at')::timestamptz is distinct from
    (select sale_date from erp.sales_headers where id=o.source_sale_id) then
  raise exception 'CP7_CREDIT_NOTE_CARRY_HISTORICAL_RECEIPT_CHANGED';end if;"""
                require(ddl.count(old) == 1, 'Note carry receipt timestamp declaration changed')
                ddl = ddl.replace(old, new, 1)
        cur.execute(ddl, prepare=False)
    for sig, ddl in definitions.items():
        if sig not in stage.PUBLIC_OWNERS:
            cur.execute(ddl, prepare=False)
    cur.execute('revoke all on all functions in schema ' + schema + ' from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write,cp7_credit_write')
    if stage is return_correction:
        cur.execute('grant usage on schema ' + schema + ' to cp7_sales_read,cp7_sales_write')
        cur.execute('grant execute on function ' + schema + '.workspace_v1(jsonb) to cp7_sales_read')
    else:
        cur.execute('grant usage on schema ' + schema + ' to cp7_sales_write')
        cur.execute('grant execute on function ' + schema + '.workspace_v1(uuid) to cp7_sales_write')
    cur.execute('grant execute on function ' + schema + '.dispatch_v1(jsonb,uuid,text) to cp7_sales_write')
    with temporary_roles(cur, tuple(sorted(set(stage.PUBLIC_OWNERS.values())))):
        for sig in stage.PUBLIC_OWNERS:
            with stage.public_function_ddl(cur, sig, before):
                cur.execute(definitions[sig], prepare=False)
    require(function_identity(cur, captured) == original_identity, 'Existing correction owner, OID or ACL changed: ' + schema)
    after = catalog._catalog_rows(cur)
    stage.transition(before, after, {sig: after['functions'][sig][0] for sig in definitions})
    verify_correction_access(cur, stage)
    result = dict(private_functions=len(stage.functions()), catalog_groups=len(after),
                  exact_old_oids_owners_and_acl=len(original_identity))
    if stage is note_carry:
        require('TimeZone=UTC' in after['functions'][f'{schema}.assert_closed_v1(uuid)'][12],
                'Note carry receipt proof timezone must be UTC')
        result['receipt_and_history_timezone'] = 'UTC'
    result['hooks'] = [sig for sig in after['functions'] if sig.split('(')[0] in {schema + '.' + name for name in HOOKS[schema]}]
    if len(result['hooks']) != 3:
        raise ValueError('Incomplete credit correction hook set: ' + schema)
    return result


def bind_transaction_source(cur):
    owner = 'cp7_transaction_source_read'
    pins = {
        'cp7_transaction_source.authority()': '3345a341dbd670d7bc75212a2218fdd311385d3c66a368bcb2132f1f4ef42621',
        'cp7_transaction_source.resolve(jsonb)': 'ed2fdeaa081c1d79a18570c38b4e172801d82fd51293569bd2d52c522ada6faa',
    }
    identity.validate_context(cur.connection)
    identity.validate_role(cur.connection, owner)
    prior = function_identity(cur, pins)
    with temporary_roles(cur, (owner,)):
        for signature, digest in pins.items():
            app_owner, definer, body, ddl = cur.execute("""
                select proowner::regrole::text,prosecdef,prosrc,pg_get_functiondef(oid)
                  from pg_proc where oid=to_regprocedure(%s)
            """, (signature,)).fetchone()
            if app_owner != owner or definer or identity.digest(body) != digest or ddl.count(body) != 1:
                raise ValueError('Unexpected transaction-source reader definition: ' + signature)
            for role in identity.CALLER_ROLES:
                direct_call_denied = cur.execute("""select not (has_function_privilege(%s,%s,'EXECUTE') and
                    has_schema_privilege(%s,'cp7_transaction_source','USAGE'))
                """, (role, signature, role)).fetchone() == (True,)
                require(direct_call_denied, 'Unexpected direct transaction-source reader: ' + role)
            changed = identity.IDENTITY_CALL.sub(lambda m: 'cp7_request_context.' + m[1].lower() + '()', body)
            cur.execute('set local role cp7_transaction_source_read')
            cur.execute(ddl.replace(body, changed, 1))
            cur.execute('reset role')
        cur.execute('grant usage on schema cp7_request_context to cp7_transaction_source_read')
        cur.execute('grant execute on function cp7_request_context.uid(),cp7_request_context.jwt() to cp7_transaction_source_read')
    identity.validate_context(cur.connection)
    require(function_identity(cur, pins) == prior, 'Transaction-source reader owner, OID or ACL changed')
    return len(pins)


def install(cur, consumer_state, consumer_catalog):
    """Compose the credit stages over an immediately verified managed consumer install."""
    require(cur.connection.info.transaction_status == TransactionStatus.INTRANS,
            'Open a maintenance transaction before installing credit corrections')
    with cur.connection.transaction(), catalog._catalog(cur):
        authority = cur.execute("select session_user,current_user,rolsuper from pg_roles where rolname=current_user").fetchone()
        require(authority == ('postgres', 'postgres', False), 'Managed postgres installer identity required')
        require(consumer_state.get('managed_identity') is True, 'Verified managed consumer installation required')
        proof = consumer.verify(cur, consumer_state)
        installed = catalog._catalog_rows(cur)
        require(len(installed) == 22 and consumer_catalog == installed,
                'Complete managed consumer catalog does not match the verified install')
        initial = catalog._data(cur)
        with payment_ddl(cur):
            verify_only_payment_ddl(installed, catalog._catalog_rows(cur))
            payment_state = payment.install(cur, dict(proof, catalog_groups=len(installed),
                legacy_definitions_projected=False), catalog._catalog_rows)
        closed = catalog._catalog_rows(cur)
        verify_only_payment_ddl(closed, payment_state['after_catalog'])
        payment_state['after_catalog'] = closed
        report = {'payment': payment.verify(cur, payment_state, catalog._catalog_rows)}

        previous = None
        for stage, filename in ((followups, 'followups.sql'), (remaining, 'remaining.sql'),
                                (multi, 'multi.sql'), (incoming, 'incoming.sql')):
            previous, report[stage.SCHEMA] = reader_stage(cur, stage, filename, previous)
        report['reference_match'] = qualify_raw_sources(cur)
        for stage in (return_correction, note_carry):
            report[stage.SCHEMA] = correction_stage(cur, stage)
        report['transaction_source_identity_bindings'] = bind_transaction_source(cur)

        end = catalog._data(cur)
        require(all(end.get(key) == value for key, value in initial.items()),
                'Existing business table content or sequence changed during installation')
        report['preserved_existing_data_and_sequences'] = len(initial)
        report['catalog_sha256'] = catalog.digest(catalog._catalog_rows(cur))
        report['production_go'] = False
        return report

