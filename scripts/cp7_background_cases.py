"""D17-14 / OW-02: real requested jobs continue through the private K4 tick.

Uses the accepted Native workload/readers and compares complete sealed output;
no synthetic business facts, altered steps, real schedule installation or send.
The real-browser closed-tab cases are declared separately by K4.
"""
from concurrent.futures import ThreadPoolExecutor
import json
import time
import uuid

import cp7_p19_report_v2_cases as report
import cp7_p19_reminder_v2_cases as reminder
import cp7_p19_transport_cases as transport

IDS = ['K4R_REPORT_FINISHES_WITHOUT_PAGE', 'K4R_REMINDER_FINISHES_WITHOUT_PAGE',
       'K4R_SINGLE_ANALYSIS_FINISHES_WITHOUT_PAGE', 'K4R_FOUR_FAMILIES_GET_A_TURN',
       'K4R_OTHER_FAMILIES_REVOKED_ACTOR', 'K4R_BACKGROUND_PRIVATE_NO_NATIVE_GRANTS']
RACE_IDS = ['K4R_REPORT_PAGE_SERVER_ONE_UNIT', 'K4R_REMINDER_PAGE_SERVER_ONE_UNIT',
            'K4R_REPORT_REVOKED_DURING_SERVER_UNIT', 'K4R_REMINDER_REVOKED_DURING_SERVER_UNIT',
            'K4R_SINGLE_PAGE_LOCK_SKIPPED_BY_SERVER',
            'K4R_REPORT_SERVER_TIMEOUT_RESTORES_CALLER', 'K4R_REMINDER_SERVER_TIMEOUT_RESTORES_CALLER']


def cases(cur, today):
    import cp7_k4_runner_cases as k4
    staged, b, auth = k4.staged, k4.b, k4.auth

    def report_done():
        f, _ = k4.load.real_workload(cur, today)
        before = b.boundary.snapshot(cur)
        r = report.staged_run(cur, today)
        key = uuid.uuid4()
        p = report.payload(r, finance='INCLUDED')
        first = report.publish(cur, p, key)
        assert first['state'] == 'RUNNING' and first['units_done'] == 0
        for unit in range(first['unit_count']):
            out = k4.tick(cur)
            assert out['family'] == 'REPORT' and out['units_done'] == unit + 1, out
        done = report.publish(cur, p, key, lookup=True)
        assert done['state'] == 'DONE' and done['run_id'] == r['run'] and done['identity_hash'] == r['identity'], done
        d, bodies = report.document(cur, done['publication_id'])
        assert d['finance'] == 'INCLUDED' and len(bodies) == r['pages']
        assert report.step(cur, key) == done and k4.tick(cur)['outcome'] == 'IDLE'
        assert cur.execute('select count(*)from cp7_analysis_stage.report_publications where job_id=(select id from cp7_analysis_stage.report_jobs where request_id=%s)', (key,)).fetchone()[0] == 1
        assert b.boundary.snapshot(cur) == before
        k4.bridge.literal(cur, f, '175.00')
        return dict(status='PASS', page_steps=0, server_units=first['unit_count'], same_request_and_identity=True,
                    complete_report_hash_verified=d['report_hash'], finance_included=True, publication_count=1)

    def reminder_done():
        k4.load.real_workload(cur, today)
        before = b.boundary.snapshot(cur)
        r = report.staged_run(cur, today)
        # The request creates the set and its first unit. No later page step.
        first = reminder.status_checked(reminder.rpc(cur, 'erp_cp7_step_reminder_conditions_v2', (r['run'],)), r['run'])
        assert first['state'] == 'RUNNING' and first['units_done'] == 1 and first['page_count'] > 0, first
        b.api.admin(cur)
        cur.execute('savepoint ow02_same_reminder_input')
        expected, _ = reminder.step_all(cur, r['run'])
        expected_rows = reminder.conditions(cur, r['run'])
        cur.execute('rollback to savepoint ow02_same_reminder_input')
        cur.execute('release savepoint ow02_same_reminder_input')
        for unit in range(first['units_done'], first['unit_count']):
            out = k4.tick(cur)
            assert out['family'] == 'REMINDER' and out['units_done'] == unit + 1, out
        got = reminder.workspace(cur, r['run'])['conditions']
        assert got['state'] == 'DONE' and got['set_hash'] == expected['set_hash'] and got['totals'] == expected['totals'], (got, expected)
        assert reminder.conditions(cur, r['run']) == expected_rows
        assert reminder.rpc(cur, 'erp_cp7_step_reminder_conditions_v2', (r['run'],)) == got
        assert k4.tick(cur)['outcome'] == 'IDLE' and b.boundary.snapshot(cur) == before
        assert cur.execute('select count(*)from cp7_reminder_native.staged_claims').fetchone()[0] == 0
        return dict(status='PASS', page_steps_after_first=0, server_units=first['unit_count']-1,
                    same_identity=True, same_complete_conditions_and_hash_as_page=True, no_claim_or_send=True)

    def single_done():
        f, _ = k4.load.real_workload(cur, today)
        before = b.boundary.snapshot(cur)
        key = uuid.uuid4()
        transport.checked_job(transport.request(cur, today, key), key, 'WAITING')
        out = k4.tick(cur)
        assert out['family'] == 'ANALYSIS' and out['outcome'] == 'JOB_DONE', out
        done = transport.checked_job(transport.status(cur, key), key, 'DONE')
        assembled, manifest, parts = transport.fetch(cur, done['run_id'])
        assert assembled == transport.analysis.read(cur, done['run_id'])
        assert transport.request(cur, today, key) == done and transport.run(cur, key) == done
        b.api.admin(cur)
        assert transport.counts(cur, key) == (1, 1, 1) and k4.tick(cur)['outcome'] == 'IDLE'
        assert b.boundary.snapshot(cur) == before
        k4.bridge.literal(cur, f, '175.00')
        return dict(status='PASS', page_worker_calls=0, same_request_and_run=True, one_original_and_document=True,
                    complete_original_equals_serve=True, document_sha256=manifest['document']['sha256'], segments=len(parts))

    def prepare_three():
        k4.load.real_workload(cur, today)
        r = report.staged_run(cur, today)
        report_key, single_key = uuid.uuid4(), uuid.uuid4()
        report.publish(cur, report.payload(r), report_key)
        first = reminder.rpc(cur, 'erp_cp7_step_reminder_conditions_v2', (r['run'],))
        assert first['state'] == 'RUNNING', first
        transport.request_operational(cur, today, single_key)
        return r, report_key, single_key

    def fair():
        prepare_three()
        key = uuid.uuid4()
        staged.request(cur, today, key)
        seen = [k4.tick(cur).get('family', 'STAGED') for _ in range(4)]
        assert set(seen) == {'STAGED', 'REPORT', 'REMINDER', 'ANALYSIS'}, seen
        return dict(status='PASS', first_four_families=seen, no_wa_settings_required=True)

    def revoked():
        r, report_key, single_key = prepare_three()
        b.api.admin(cur)
        actor = auth.base.OPERATOR_AUTH
        cur.execute('update erp.app_users set is_active=false where auth_user_id=%s', (actor,))
        held = k4.claims(cur)
        outcomes = [k4.tick(cur) for _ in range(3)]
        assert {o['family'] for o in outcomes} == {'REPORT', 'REMINDER', 'ANALYSIS'} and all(o['outcome'] == 'JOB_FAILED' for o in outcomes), outcomes
        assert k4.claims(cur) == held and k4.tick(cur)['outcome'] == 'IDLE'
        assert cur.execute('select state,failure_code,units_done from cp7_analysis_stage.report_jobs where request_id=%s', (report_key,)).fetchone() == ('FAILED', 'CP7_REPORT_ACCESS_CHANGED', 0)
        assert cur.execute('select state,failure_code,units_done from cp7_reminder_native.staged_condition_sets where run_id=%s', (r['run'],)).fetchone() == ('FAILED', 'CP7_REMINDER_ACCESS_CHANGED', 1)
        assert cur.execute('select state,failure_code,run_id from cp7_analysis_jobs.jobs where request_id=%s', (single_key,)).fetchone() == ('FAILED', 'CP7_ANALYSIS_ACCESS_CHANGED', None)
        assert cur.execute('select count(*)from cp7_analysis_stage.report_publications').fetchone()[0] == 0
        assert cur.execute('select count(*)from cp7_reminder_native.staged_claims').fetchone()[0] == 0
        return dict(status='PASS', all_three_denied_without_output=True, caller_identity_restored=True, denied_jobs_not_retried_forever=True)

    def private():
        b.api.admin(cur)
        import cp7_reminder_v2_bundle as bundle
        bundle.verify_background(cur)
        for who in ('cp7_capture', 'cp7_reminder'):
            assert not cur.execute("select exists(select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp'and c.relkind in('r','p','v')and has_table_privilege(%s,c.oid,'INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER'))", (who,)).fetchone()[0]
        assert not cur.execute("select exists(select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='cp7_reminder_native'and has_table_privilege('cp7_capture',c.oid,'SELECT,INSERT,UPDATE,DELETE'))").fetchone()[0]
        assert cur.execute('select cp7_ops.schedules()').fetchone()[0] == k4.schedule.definitions(cur)
        return dict(status='PASS', private_function_allowlist_verified=True, no_native_writes=True, no_reminder_table_grants=True,
                    same_schedules=True, no_public_runner=True)

    return list(zip(IDS, (report_done, reminder_done, single_done, fair, revoked, private)))


def races(tools, today):
    import cp7_k4_runner_cases as k4
    b, auth = k4.b, k4.auth

    def ticking(timeout='8s'):
        with tools.connect() as conn, conn.cursor() as cur:
            b.api.admin(cur)
            # All three identity settings must survive success, revocation
            # and timeout in the SAME connection, before commit or cleanup.
            for name, value in [('request.jwt.claims', json.dumps({'sub': str(uuid.uuid4()), 'role': 'authenticated', 'probe': 'OW02_CALLER'})),
                                ('request.jwt.claim.sub', str(uuid.uuid4())),
                                ('request.jwt.claim', json.dumps({'sub': str(uuid.uuid4()), 'probe': 'OW02_SECONDARY'}))]:
                cur.execute('select set_config(%s,%s,true)', (name, value))
            identity = cur.execute("select current_setting('request.jwt.claims',true),current_setting('request.jwt.claim.sub',true),current_setting('request.jwt.claim',true)").fetchone()
            out = k4.tick(cur, timeout)
            assert cur.execute("select current_setting('request.jwt.claims',true),current_setting('request.jwt.claim.sub',true),current_setting('request.jwt.claim',true)").fetchone() == identity, 'OW02_CALLER_IDENTITY_NOT_RESTORED'
            conn.commit()
            return out

    def unit(family, revoke):
        with tools.connect() as conn, conn.cursor() as cur:
            k4.load.real_workload(cur, today)
            r = report.staged_run(cur, today)
            key = uuid.uuid4()
            if family == 'REPORT':
                first = report.publish(cur, report.payload(r), key)
                relation = 'cp7_analysis_stage.report_reads'
            else:
                first = reminder.rpc(cur, 'erp_cp7_step_reminder_conditions_v2', (r['run'],))
                relation = 'cp7_reminder_native.staged_conditions'
            assert first['state'] == 'RUNNING', first
            b.api.admin(cur)
            before = cur.execute('select count(*)from '+relation).fetchone()[0]
            conn.commit()
        holder = tools.connect()
        try:
            # Real table lock, not an altered step: the tick holds its job
            # row while its real unit waits to read/write its private output.
            holder.execute('lock table '+relation+' in access exclusive mode')
            with ThreadPoolExecutor(max_workers=1) as pool:
                running = pool.submit(ticking)
                deadline, waiting = time.monotonic()+6, False
                while time.monotonic() < deadline:
                    with tools.connect() as conn, conn.cursor() as cur:
                        waiting = cur.execute("select exists(select 1 from pg_locks where relation=%s::regclass and not granted)", (relation,)).fetchone()[0]
                    if waiting:
                        break
                    time.sleep(.05)
                assert waiting, ('OW02_SERVER_DID_NOT_REACH_UNIT', family)
                with tools.connect() as conn, conn.cursor() as cur:
                    if revoke:
                        cur.execute('update erp.app_users set is_active=false where auth_user_id=%s', (auth.base.OPERATOR_AUTH,))
                    else:
                        skipped = report.step(cur, key) if family == 'REPORT' else reminder.rpc(cur, 'erp_cp7_step_reminder_conditions_v2', (r['run'],))
                        assert skipped['worker_active'] is True and skipped['units_done'] == first['units_done'], skipped
                    conn.commit()
                holder.rollback()
                out = running.result(12)
        finally:
            holder.close()
        assert out['family'] == family, out
        if revoke:
            assert out['outcome'] == 'JOB_FAILED' and out['units_done'] == first['units_done'], out
            with tools.connect() as conn, conn.cursor() as cur:
                assert cur.execute('select count(*)from '+relation).fetchone()[0] == before
                assert k4.tick(cur)['outcome'] == 'IDLE'
                conn.commit()
            return dict(status='PASS', real_output_lock=True, family=family, revoked_during_unit=True,
                        output_rolled_back=True, job_failed_once=True)
        assert out['outcome'] in ('UNIT_STORED', 'JOB_DONE') and out['units_done'] == first['units_done']+1, out
        # Opposite order: a page holding the row is skipped, never waited on.
        holder = tools.connect()
        try:
            if family == 'REPORT':
                holder.execute('select 1 from cp7_analysis_stage.report_jobs where request_id=%s for update', (key,))
            else:
                holder.execute('select 1 from cp7_reminder_native.staged_condition_sets where run_id=%s for update', (r['run'],))
            assert ticking()['outcome'] == 'IDLE'
            holder.rollback()
        finally:
            holder.close()
        return dict(status='PASS', real_output_lock=True, family=family, one_unit_only=True,
                    page_while_server_skips=True, server_while_page_skips=True)

    def single_locked():
        key = uuid.uuid4()
        with tools.connect() as conn, conn.cursor() as cur:
            k4.load.real_workload(cur, today)
            transport.request_operational(cur, today, key)
            conn.commit()
        holder = tools.connect()
        try:
            holder.execute("select pg_advisory_xact_lock(hashtextextended('CP7:ANALYSIS-REQUEST:'||%s||':'||%s,0))",
                           (str(auth.base.OPERATOR_AUTH), str(key)))
            assert ticking()['outcome'] == 'IDLE'
            holder.rollback()
        finally:
            holder.close()
        assert ticking()['outcome'] == 'JOB_DONE'
        with tools.connect() as conn, conn.cursor() as cur:
            transport.checked_job(transport.status(cur, key), key, 'DONE')
            b.api.admin(cur)
            assert transport.counts(cur, key) == (1, 1, 1)
        return dict(status='PASS', page_advisory_lock_skipped=True, same_job_completed_after_release=True, one_original=True)

    def timed_out(family):
        with tools.connect() as conn, conn.cursor() as cur:
            k4.load.real_workload(cur, today)
            r = report.staged_run(cur, today)
            key = uuid.uuid4()
            if family == 'REPORT':
                first = report.publish(cur, report.payload(r), key)
                relation, table, where, value, code = ('cp7_analysis_stage.report_reads', 'cp7_analysis_stage.report_jobs',
                    'request_id', key, 'CP7_REPORT_V2_STAGE_STOPPED')
            else:
                first = reminder.rpc(cur, 'erp_cp7_step_reminder_conditions_v2', (r['run'],))
                relation, table, where, value, code = ('cp7_reminder_native.staged_conditions', 'cp7_reminder_native.staged_condition_sets',
                    'run_id', r['run'], 'CP7_REMINDER_V2_STAGE_STOPPED')
            assert first['state'] == 'RUNNING', first
            b.api.admin(cur)
            before = cur.execute('select count(*)from '+relation).fetchone()[0]
            conn.commit()
        holder = tools.connect()
        try:
            holder.execute('lock table '+relation+' in access exclusive mode')
            for attempt in range(1, 4):
                out = ticking('2s')
                assert out['family'] == family and out['units_done'] == first['units_done'], out
                assert out['outcome'] == ('UNIT_RETRY' if attempt < 3 else 'JOB_FAILED'), out
                with tools.connect() as conn, conn.cursor() as cur:
                    got = cur.execute('select state,unit_attempts,failure_sqlstate,failure_code from '+table+' where '+where+'=%s', (value,)).fetchone()
                    assert got == (('RUNNING', attempt, None, None) if attempt < 3 else ('FAILED', 3, '57014', code)), got
        finally:
            holder.rollback()
            holder.close()
        with tools.connect() as conn, conn.cursor() as cur:
            assert cur.execute('select count(*)from '+relation).fetchone()[0] == before
            assert k4.tick(cur)['outcome'] == 'IDLE'
            conn.commit()
        return dict(status='PASS', family=family, real_output_lock=True, statement_limit='2s',
                    unchanged_units_and_output=True, attempts=[1, 2, 3], final_sqlstate='57014',
                    final_code=code, all_three_caller_identity_settings_restored_in_same_connection=True)

    return list(zip(RACE_IDS, (lambda: unit('REPORT', False), lambda: unit('REMINDER', False),
                              lambda: unit('REPORT', True), lambda: unit('REMINDER', True), single_locked,
                              lambda: timed_out('REPORT'), lambda: timed_out('REMINDER'))))
