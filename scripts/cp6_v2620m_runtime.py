"""Verify M and historical capsules without weakening the maintenance executor.

The executor continues to demand the exact installed target. Business suites
may inspect historical capsules only through this separately pinned M chain.
"""
import hashlib
from pathlib import Path
from psycopg import sql
import cp6_preuse_rollback_maintenance as maintenance
import cp6_v2620n_runtime as n_runtime
import cp6_v2620p_runtime as p_runtime
import cp6_v2620s_runtime as s_runtime

MIGRATION = Path('supabase/migrations/20260911092622_erp_v2_6_20m_cp6_subledger_exact_cent_closure.sql')

def verified_successor(cur):
    cur.execute("""select exists(select 1 from erp.schema_migrations where version='v2.6.20m'),
      to_regclass('erp.cp6_v2620m_rollback_capsule') is not null""")
    marker, capsule = cur.fetchone()
    if not marker and not capsule:
        return {}
    if not marker or not capsule:
        raise AssertionError('M_MARKER_CAPSULE_MISMATCH')
    data = MIGRATION.read_bytes()
    cur.execute("""select version,encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),
      'UTF8'),'sha256'),'hex') from supabase_migrations.schema_migrations
      where name='erp_v2_6_20m_cp6_subledger_exact_cent_closure'""")
    rows = cur.fetchall()
    if len(rows) != 1 or rows[0][0] != '20260911092622' or rows[0][1] not in {
        hashlib.sha256(data).hexdigest(), hashlib.sha256(data[:-1]).hexdigest(),
    }:
        raise AssertionError('M_SOURCE_PLATFORM_MISMATCH')
    successor = n_runtime.verified_successor(cur)
    # P also changes the M-owned report-scope function, an identity absent
    # from the intervening N/O capsules. Preserve exact cardinalities while
    # carrying that non-overlapping successor edge into historical evidence.
    p_successor = p_runtime.verified_successor(cur)
    scope_identity = 'erp._v268_financial_report_checks_pre_scope()'
    validation_successor = dict(successor)
    if scope_identity in p_successor:
        validation_successor[scope_identity] = p_successor[scope_identity]
    # S changes M-owned supplier payment outside the N/O/P/Q/R capsules.
    s_successor = s_runtime.verified_successor(cur)
    payment_identity = 'erp.post_supplier_payment(uuid)'
    if payment_identity in s_successor:
        validation_successor[payment_identity] = s_successor[payment_identity]
    observations = n_runtime.predecessor_snapshot(cur, 'M', validation_successor)
    n_runtime.extend_items(successor, observations)
    if scope_identity in p_successor:
        for item in observations:
            if item['identity'] == scope_identity:
                old = item['installed_sha256']
                item['installed_sha256'] = p_runtime.effective_hash(
                    p_successor, scope_identity, old
                )
                item['pre_p_installed_sha256'] = old
                if 'pre_q_installed_sha256' in p_successor[scope_identity]:
                    item['pre_q_installed_sha256'] = p_successor[scope_identity]['pre_q_installed_sha256']
                if 'pre_r_installed_sha256' in p_successor[scope_identity]:
                    item['pre_r_installed_sha256'] = p_successor[scope_identity]['pre_r_installed_sha256']
                if 'pre_s_installed_sha256' in p_successor[scope_identity]:
                    item['pre_s_installed_sha256'] = p_successor[scope_identity]['pre_s_installed_sha256']
                item['expected_generation'] = 'P'
                break
    if payment_identity in s_successor:
        for item in observations:
            if item['identity'] == payment_identity:
                old = item['installed_sha256']
                item['installed_sha256'] = s_runtime.effective_hash(s_successor, payment_identity, old)
                item['pre_s_installed_sha256'] = old
                item['expected_generation'] = 'S'
                break
    return {item['identity']: item for item in observations}

def effective_hash(successor, identity, predecessor):
    item = successor.get(identity)
    if item is None:
        return predecessor
    if predecessor != item['predecessor_sha256']:
        raise AssertionError('M_PREDECESSOR_CHAIN_MISMATCH')
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
        raise AssertionError('M_HISTORICAL_CAPSULE_CARDINALITY_MISMATCH')
    for row in rows:
        expected = wanted[row['identity']]
        if (any(row[k] != expected[k] for k in ('predecessor_sha256','installed_sha256','owner','acl'))
          or row['predecessor_definition_sha256'] != expected['predecessor_sha256']
          or row['observed_installed_sha256'] != effective_hash(successor,row['identity'],expected['installed_sha256'])
          or row['observed_installed_owner'] != expected['owner'] or row['observed_installed_acl'] != expected['acl']):
            raise AssertionError('M_HISTORICAL_CAPSULE_SOURCE_PIN_MISMATCH')
    return rows

def extend_items(successor, items):
    for item in items:
        if item['identity'] in successor:
            old = item['installed_sha256']
            item['installed_sha256'] = effective_hash(successor,item['identity'],old)
            item['pre_m_installed_sha256'] = old
            item['expected_generation'] = 'M'

def extend_rows(successor, rows):
    return [tuple([r[0],r[1],effective_hash(successor,r[0],r[2]),*r[3:]]) for r in rows]
