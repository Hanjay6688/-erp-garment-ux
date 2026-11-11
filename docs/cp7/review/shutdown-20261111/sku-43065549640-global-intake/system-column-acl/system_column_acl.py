"""Observe explicit ACLs on system columns in the CP7 catalogue domain."""

QUERY = """
select schema_name, relation_name, column_name, attribute_number,
       grantor, grantee, privilege_type, is_grantable
from (
    select n.nspname::text as schema_name, c.relname::text as relation_name,
           a.attname::text as column_name, a.attnum as attribute_number,
           pg_get_userbyid(p.grantor)::text as grantor,
           case when p.grantee = 0 then 'PUBLIC' else pg_get_userbyid(p.grantee)::text end as grantee,
           p.privilege_type, p.is_grantable
    from pg_catalog.pg_attribute a
    join pg_catalog.pg_class c on c.oid = a.attrelid
    join pg_catalog.pg_namespace n on n.oid = c.relnamespace
    cross join lateral pg_catalog.aclexplode(a.attacl) p
    where a.attnum < 0 and not a.attisdropped
      and n.nspname <> all(array['pg_catalog', 'information_schema', 'cron'])
      and n.nspname !~ '^pg_'
) acl
order by schema_name collate "C", relation_name collate "C", column_name collate "C",
         attribute_number, grantor collate "C", grantee collate "C", privilege_type collate "C", is_grantable
"""

FIELDS = ('schema', 'relation', 'column', 'attribute_number', 'grantor',
          'grantee', 'privilege', 'grantable')
SNAPSHOT_RELATIONS = ('audit_logs', 'bb_purchase_commitments_v1', 'locations', 'material_stock_movements')


def observe(cursor):
    return [dict(zip(FIELDS, row, strict=True)) for row in cursor.execute(QUERY).fetchall()]


def require_same(cursor, expected):
    current = observe(cursor)
    if current != expected:
        raise ValueError('CP7_SYSTEM_COLUMN_ACL_CHANGED')
    return current


def require_snapshot_xmin(cursor, rows):
    exact = {row['relation'] for row in rows if row['schema'] == 'erp' and row['column'] == 'xmin'
             and row['grantee'] == 'cp7_capture' and row['privilege'] == 'SELECT' and row['grantable'] is False}
    missing = set(SNAPSHOT_RELATIONS) - exact
    if missing:
        raise ValueError('CP7_SNAPSHOT_XMIN_EXPLICIT_GRANT_MISSING:' + ','.join(sorted(missing)))
    effective = cursor.execute("""
        select target, pg_catalog.has_column_privilege('cp7_capture', target, 'xmin', 'SELECT')
        from unnest(%s::text[]) as scope(target)
    """, (['erp.' + name for name in SNAPSHOT_RELATIONS],)).fetchall()
    unavailable = [target for target, granted in effective if granted is not True]
    if unavailable:
        raise ValueError('CP7_SNAPSHOT_XMIN_NOT_EFFECTIVE:' + ','.join(sorted(unavailable)))
    return effective
