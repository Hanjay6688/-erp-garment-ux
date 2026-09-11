"""Verify N and historical capsules without weakening the maintenance executor.

The executor continues to demand the exact installed target. Business suites
may inspect historical capsules only through this separately pinned N chain.
"""
import hashlib
from pathlib import Path
from psycopg import sql
import cp6_preuse_rollback_maintenance as maintenance
import cp6_v2620o_runtime as o_runtime

MIGRATION = Path('supabase/migrations/20260911124328_erp_v2_6_20n_cp6_supplier_cent_lifecycle.sql')

def verified_successor(cur):
    cur.execute("""select exists(select 1 from erp.schema_migrations where version='v2.6.20n'),
      to_regclass('erp.cp6_v2620n_rollback_capsule') is not null""")
    marker, capsule = cur.fetchone()
    if not marker and not capsule:
        return {}
    if not marker or not capsule:
        raise AssertionError('N_MARKER_CAPSULE_MISMATCH')
    data = MIGRATION.read_bytes()
    cur.execute("""select version,encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),
      'UTF8'),'sha256'),'hex') from supabase_migrations.schema_migrations
      where name='erp_v2_6_20n_cp6_supplier_cent_lifecycle'""")
    rows = cur.fetchall()
    if len(rows) != 1 or rows[0][0] != '20260911124328' or rows[0][1] not in {
        hashlib.sha256(data).hexdigest(), hashlib.sha256(data[:-1]).hexdigest(),
    }:
        raise AssertionError('N_SOURCE_PLATFORM_MISMATCH')
    successor = o_runtime.verified_successor(cur)
    observations = o_runtime.predecessor_snapshot(cur, 'N', successor)
    o_runtime.extend_items(successor, observations)
    return {item['identity']: item for item in observations}

def effective_hash(successor, identity, predecessor):
    item = successor.get(identity)
    if item is None:
        return predecessor
    if predecessor != item['predecessor_sha256']:
        raise AssertionError('N_PREDECESSOR_CHAIN_MISMATCH')
    return item['installed_sha256']

def predecessor_snapshot(cur, generation, successor):
    """Read-only historical evidence; never called by rollback admission."""
    if not successor:
        return maintenance._capsule_snapshot(cur.connection, generation, maintenance.TARGETS[generation])
    capsule = sql.Identifier(*maintenance.TARGETS[generation]['capsule'].split('.'))
    cur.execute(sql.SQL("""select c.object_regidentity,c.definition_sha256,
      encode(extensions.digest(convert_to(c.object_definition,'UTF8'),'sha256'),'hex'),
      c.installed_definition_sha256,c.owner_snapshot,c.acl_snapshot,
      encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),
      pg_get_userbyid(p.proowner),case when p.proacl is null then null else
        array(select a::text from unnest(p.proacl) a order by a::text) end
      from {} c left join pg_proc p on p.oid=to_regprocedure(c.object_regidentity)
      order by c.object_regidentity""").format(capsule))
    columns = ('identity','predecessor_sha256','predecessor_definition_sha256','installed_sha256',
      'owner','acl','observed_installed_sha256','observed_installed_owner','observed_installed_acl')
    rows = [dict(zip(columns, row, strict=True)) for row in cur.fetchall()]
    wanted = {x['identity']: x for x in maintenance.TRUSTED_FUNCTIONS[generation]}
    if len(rows) != len(wanted) or {r['identity'] for r in rows} != set(wanted):
        raise AssertionError('N_HISTORICAL_CAPSULE_CARDINALITY_MISMATCH')
    for row in rows:
        expected = wanted[row['identity']]
        if (any(row[k] != expected[k] for k in ('predecessor_sha256','installed_sha256','owner','acl'))
          or row['predecessor_definition_sha256'] != expected['predecessor_sha256']
          or row['observed_installed_sha256'] != effective_hash(successor,row['identity'],expected['installed_sha256'])
          or row['observed_installed_owner'] != expected['owner'] or row['observed_installed_acl'] != expected['acl']):
            raise AssertionError('N_HISTORICAL_CAPSULE_SOURCE_PIN_MISMATCH')
    return rows

def extend_items(successor, items):
    for item in items:
        if item['identity'] in successor:
            old = item['installed_sha256']
            item['installed_sha256'] = effective_hash(successor,item['identity'],old)
            item['pre_n_installed_sha256'] = old
            if 'pre_o_installed_sha256' in successor[item['identity']]:
                item['pre_o_installed_sha256'] = successor[item['identity']]['pre_o_installed_sha256']
            item['expected_generation'] = 'N'

def extend_rows(successor, rows):
    return [tuple([r[0],r[1],effective_hash(successor,r[0],r[2]),*r[3:]]) for r in rows]

EXTRA_FUNCTIONS = [{'identity': 'erp._cp6_apply_supplier_cent_event(text,uuid,date,text,jsonb,boolean)',
  'sha256': '390fc3fae9bf59cf35fbc699f988521b3bde572e266937fdce99e0854c1756a3',
  'owner': 'postgres',
  'acl': ['postgres=X/postgres']},
 {'identity': 'erp._cp6_supplier_cent_ledger(uuid[])',
  'sha256': '43572de7870afb9050d5af24a05ff6f5b91063d9a46de2cf6616f1f1edb0e49c',
  'owner': 'postgres',
  'acl': ['postgres=X/postgres']},
 {'identity': 'erp._cp6_supplier_cent_state(uuid[])',
  'sha256': '19d43e3e32d94c6aaaf0acbb1f6e55946701fa10b9f53df7a990ea9375fad191',
  'owner': 'postgres',
  'acl': ['postgres=X/postgres']}]

INHERITED_FACT_GUARD = {'acl': ['postgres=X/postgres'],
 'identity': 'erp.guard_sales_payment_fact_append_only()',
 'owner': 'postgres',
 'sha256': '2011da553bc46c6106ba4c638c0f695da4bb2c1855bd1518b42df8215cf81cf5'}

def verify_extra_objects(cur):
    """Read-only object trust gate, also called by admission preflight."""
    maintenance._function_snapshot(cur.connection, EXTRA_FUNCTIONS)
    maintenance._function_snapshot(cur.connection, [INHERITED_FACT_GUARD])
    cur.execute("""select c.relrowsecurity,pg_get_userbyid(c.relowner),
      exists(select 1 from information_schema.role_table_grants g where g.table_schema='erp'
        and g.table_name='supplier_cent_posting_facts' and g.grantee in('PUBLIC','anon','authenticated','service_role')),
      (select count(*) from pg_trigger t where t.tgrelid=c.oid and not t.tgisinternal
        and t.tgenabled='O' and t.tgfoid='erp.guard_sales_payment_fact_append_only()'::regprocedure
        and t.tgname in('trg_supplier_cent_fact_append_only','trg_supplier_cent_fact_no_truncate'))
      from pg_class c where c.oid=to_regclass('erp.supplier_cent_posting_facts')""")
    if cur.fetchone() != (True, 'postgres', False, 2):
        raise AssertionError('N_CENT_FACT_SECURITY_MISMATCH')
    return len(EXTRA_FUNCTIONS)
