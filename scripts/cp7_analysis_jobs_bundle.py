"""Exact private catalog of the P19 analysis job and segment transport layer."""
FUNCTIONS = {
    'compute_key': 'i', 'worker_active': 's', 'status': 's', 'original': 'i', 'store': 'v',
    'request': 'v', 'run': 'v', 'get': 'v', 'manifest': 'v', 'segment': 's'}
PUBLIC = ('public.erp_cp7_request_analysis_job_v1(jsonb,uuid)', 'public.erp_cp7_run_analysis_job_v1(uuid)',
          'public.erp_cp7_get_analysis_job_v1(uuid)', 'public.erp_cp7_read_analysis_manifest_v1(uuid)',
          'public.erp_cp7_read_analysis_segment_v1(uuid,integer,text)')
TABLES = ('jobs', 'documents', 'segments')


def verify(cur):
    ns = 'cp7_analysis_jobs'
    assert cur.execute('select pg_get_userbyid(nspowner) from pg_namespace where nspname=%s', (ns,)).fetchone()[0] == 'cp7_capture'
    rows = cur.execute('select p.oid::regprocedure::text,p.proname,pg_get_userbyid(p.proowner),p.prosecdef,p.proconfig,p.provolatile::text '
                       'from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname=%s', (ns,)).fetchall()
    assert sorted(r[1] for r in rows) == sorted(FUNCTIONS), rows
    for sig, name, owner, definer, config, volatility in rows:
        assert (owner, definer, volatility) == ('cp7_capture', False, FUNCTIONS[name]), (sig, owner, definer, volatility)
        assert 'search_path=""' in (config or []) and 'TimeZone=UTC' in (config or []), (sig, config)
        for who in ('anon', 'authenticated', 'service_role'):
            assert not cur.execute("select has_function_privilege(%s,%s,'EXECUTE')", (who, sig)).fetchone()[0], (who, sig)
    for sig in PUBLIC:
        assert cur.execute('select pg_get_userbyid(proowner),prosecdef,proconfig,provolatile::text from pg_proc where oid=%s::regprocedure',
                           (sig,)).fetchone() == ('cp7_capture', True, ['search_path=""'], 'v'), sig
        assert cur.execute("select has_function_privilege('authenticated',%s,'EXECUTE')", (sig,)).fetchone()[0], sig
        for who in ('anon', 'service_role'):
            assert not cur.execute("select has_function_privilege(%s,%s,'EXECUTE')", (who, sig)).fetchone()[0], (who, sig)
    for who in ('anon', 'authenticated', 'service_role'):
        assert not cur.execute("select has_schema_privilege(%s,%s,'USAGE')", (who, ns)).fetchone()[0], who
    for table in TABLES:
        name = ns + '.' + table
        assert cur.execute('select pg_get_userbyid(relowner),relrowsecurity from pg_class where oid=%s::regclass', (name,)).fetchone() == ('cp7_capture', True), name
        assert cur.execute("select count(*) from pg_policy where polrelid=%s::regclass and pg_get_expr(polqual,polrelid)='false' "
                           "and pg_get_expr(polwithcheck,polrelid)='false'", (name,)).fetchone()[0] == 1, name
        for who in ('anon', 'authenticated', 'service_role'):
            assert not cur.execute("select has_table_privilege(%s,%s,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER')", (who, name)).fetchone()[0], (who, name)
    for table in ('documents', 'segments'):
        assert cur.execute("select count(*) from pg_trigger where tgrelid=%s::regclass and tgfoid='cp7_private.immutable_run()'::regprocedure "
                           "and not tgisinternal", (ns + '.' + table,)).fetchone()[0] == 1, table
    return dict(analysis_job_transport=True, segment_characters=2000000, statement_limit_raised=False)
