"""Exact private catalog of the P19 staged (5,000-target) analysis layer (analysis-stages.sql)."""
# Every function of the schema with its volatility; nothing else may exist there
# (in particular no scenario stand-in: the product always runs the real units).
FUNCTIONS = {
    # scenario units (copies of history_build, the demand kernel, baseline, supply, schedule)
    'castable': 'i', 'events_clean': 'i', 'availability_clean': 'i', 'history_prep': 'i', 'event_facts': 'i', 'events_validate': 'i',
    'history_validate': 'i', 'history_rows': 'i', 'history_stock': 'i', 'baseline_rows': 'i', 'supply': 'i', 'schedule': 'i',
    # netting, allocation, analysis
    'netting_prep': 'i', 'netting_targets': 'i', 'netting_pairs': 'i', 'netting_plan': 'i', 'netting_rows': 'i',
    'alloc_prep': 'i', 'numerics': 'i', 'alloc_step': 'i', 'alloc_final': 'i',
    'analysis_targets': 'i', 'material_scope': 'i', 'analysis_skeleton': 'i', 'sentinel': 'i', 'fragment_fields': 'i',
    # bounds, status, plan, pages
    'bounds': 'i', 'status': 's', 'create_job': 'v', 'output': 's', 'tag': 'i', 'page_field': 'i', 'fragment_field': 'i',
    'page_layout': 's', 'page_cuts': 's', 'page_summary': 'i', 'run_scenario_unit': 'v', 'run_unit': 'v', 'step': 'v',
    # requests, readers, retention
    'job_of': 's', 'request': 'v', 'step_request': 'v', 'get': 'v', 'page_set': 's', 'page': 's', 'check_source': 's',
    'purge_intermediates': 'v'}
PUBLIC = ('public.erp_cp7_request_staged_analysis_v1(jsonb,uuid)', 'public.erp_cp7_step_staged_analysis_v1(uuid)',
          'public.erp_cp7_get_staged_analysis_v1(uuid)', 'public.erp_cp7_read_staged_analysis_pages_v1(uuid)',
          'public.erp_cp7_read_staged_analysis_page_v1(uuid,integer,text)', 'public.erp_cp7_check_staged_analysis_source_v1(uuid)')
TABLES = ('jobs', 'units', 'outputs', 'target_rows', 'pair_rows', 'pair_lists', 'fragments', 'headers', 'pages', 'page_sets')
# The job row's immutable columns (an UPDATE naming one of them is refused); every other table is insert-only.
JOB_FIXED = 'id, actor, request_id, query, reference, access_at_capture, captured_at, source_hash, run_id, created_at'
BOUNDS = {'targets_per_chunk': 250, 'pairs_per_chunk': 25000, 'visits_per_allocation_step': 100000, 'allocation_targets_per_step': 1000,
          'history_cells_per_unit': 12500, 'sales_per_events_unit': 2500, 'targets_per_stock_unit': 1000,
          'job_targets': 5000, 'job_history_cells': 500000, 'job_pairs': 1000000, 'job_matching_products': 10000,
          'page_utf8_bytes': 8000000, 'header_utf8_bytes': 8000000}


def verify(cur):
    ns = 'cp7_analysis_stage'
    assert cur.execute('select pg_get_userbyid(nspowner) from pg_namespace where nspname=%s', (ns,)).fetchone()[0] == 'cp7_capture'
    rows = cur.execute('select p.oid::regprocedure::text,p.proname,pg_get_userbyid(p.proowner),p.prosecdef,p.proconfig,p.provolatile::text '
                       'from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname=%s', (ns,)).fetchall()
    assert sorted(r[1] for r in rows) == sorted(FUNCTIONS), sorted(r[1] for r in rows)
    for sig, name, owner, definer, config, volatility in rows:
        assert (owner, definer, volatility) == ('cp7_capture', False, FUNCTIONS[name]), (sig, owner, definer, volatility)
        assert 'search_path=""' in (config or []) and 'TimeZone=UTC' in (config or []), (sig, config)
        for who in ('anon', 'authenticated', 'service_role'):
            assert not cur.execute("select has_function_privilege(%s,%s,'EXECUTE')", (who, sig)).fetchone()[0], (who, sig)
    assert cur.execute('select cp7_analysis_stage.bounds()').fetchone()[0] == BOUNDS
    for sig in PUBLIC:
        assert cur.execute('select pg_get_userbyid(proowner),prosecdef,proconfig,provolatile::text from pg_proc where oid=%s::regprocedure',
                           (sig,)).fetchone() == ('cp7_capture', True, ['search_path=""'], 'v'), sig
        assert cur.execute("select has_function_privilege('authenticated',%s,'EXECUTE')", (sig,)).fetchone()[0], sig
        for who in ('anon', 'service_role'):
            assert not cur.execute("select has_function_privilege(%s,%s,'EXECUTE')", (who, sig)).fetchone()[0], (who, sig)
    for who in ('anon', 'authenticated', 'service_role'):
        assert not cur.execute("select has_schema_privilege(%s,%s,'USAGE')", (who, ns)).fetchone()[0], who
    assert sorted(r[0] for r in cur.execute("select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname=%s and c.relkind='r'", (ns,)).fetchall()) == sorted(TABLES)
    for table in TABLES:
        name = ns + '.' + table
        assert cur.execute('select pg_get_userbyid(relowner),relrowsecurity from pg_class where oid=%s::regclass', (name,)).fetchone() == ('cp7_capture', True), name
        assert cur.execute("select count(*) from pg_policy where polrelid=%s::regclass and pg_get_expr(polqual,polrelid)='false' "
                           "and pg_get_expr(polwithcheck,polrelid)='false'", (name,)).fetchone()[0] == 1, name
        for who in ('anon', 'authenticated', 'service_role'):
            assert not cur.execute("select has_table_privilege(%s,%s,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER')", (who, name)).fetchone()[0], (who, name)
        triggers = cur.execute("select pg_get_triggerdef(t.oid) from pg_trigger t where t.tgrelid=%s::regclass and t.tgfoid='cp7_private.immutable_run()'::regprocedure "
                               "and not t.tgisinternal and t.tgenabled<>'D'", (name,)).fetchall()
        assert len(triggers) == 1, (name, triggers)
        expected = ('BEFORE DELETE OR UPDATE OF %s' % JOB_FIXED) if table == 'jobs' else 'BEFORE DELETE OR UPDATE'
        assert (' %s ON %s FOR EACH ROW EXECUTE FUNCTION cp7_private.immutable_run()' % (expected, name)) in triggers[0][0], triggers[0][0]
    # The staged job never writes the single path's run table: no function of
    # the schema inserts into cp7_analysis_native.runs or the job documents/segments.
    for pattern in ('insert into cp7_analysis_native.runs', 'insert into cp7_analysis_jobs.', 'scenario_stand_in'):
        assert cur.execute("select count(*) from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname=%s and p.prosrc like %s",
                           (ns, '%' + pattern + '%')).fetchone()[0] == 0, pattern
    return dict(staged_analysis=True, declared_targets=BOUNDS['job_targets'], page_utf8_bytes=BOUNDS['page_utf8_bytes'],
                statement_limit_raised=False, staged_runs_in_native_runs=False)
