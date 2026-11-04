"""Append current economic observations to the complete retained Native body.

The actual owning runtime must bind the original observer to the current
product first. No connection is opened and no fixture is created here.
"""

SESSION_SQL = """select jsonb_build_object(
 'advisory_locks',(select count(*) from pg_locks where locktype='advisory'
    and database=(select oid from pg_database where datname=current_database())),
 'advisory_lock_keys',(select coalesce(jsonb_agg(jsonb_build_array(pid,classid,objid,objsubid,mode,granted)
    order by pid,classid,objid,objsubid,mode),'[]'::jsonb) from pg_locks where locktype='advisory'
    and database=(select oid from pg_database where datname=current_database())),
 'other_sessions',(select coalesce(jsonb_agg(jsonb_build_array(pid::text,usename,state) order by pid),'[]'::jsonb)
    from pg_stat_activity where datname=current_database() and pid<>pg_backend_pid()
    and backend_type='client backend' and usename<>'authenticator'))"""


def observe(original, cur, fixture, label):
    value = original(cur, fixture, label)
    if set(value) & {'current_economic_pools', 'current_session_leaks'}:
        raise ValueError('CURRENT_SKU_ECONOMIC_OBSERVATION_MUST_NOT_REPLACE_ORIGINAL_FIELDS')
    pools = {product: cur.execute(
        "select cp7_sku_conversion.pool_quote_v2(%s,%s,'GRADE_A')",
        (product, fixture['location'])).fetchone()[0]
        for product in (fixture['source'], fixture['target'])}
    sessions = cur.execute(SESSION_SQL, ()).fetchone()[0]
    return dict(value, current_economic_pools=pools, current_session_leaks=sessions)
