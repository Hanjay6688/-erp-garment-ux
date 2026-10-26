"""Three real Auth/PostgREST cases on one disposable complete-product copy."""
# Injected by cases.py; avoids ambiguous globally named `common` imports.
C = None


def http_cases(http, today):
    def prepare(label, extra=False):
        user = http.login('OWNER', label)
        other = http.login('OWNER', label + '-other') if extra else None
        observed = {}
        with http.connect() as conn, conn.cursor() as cur:
            f = C.fixture(cur, today, user.auth_user_id, observed)
            before = C.snapshot(cur)
            conn.commit()
        return user, other, f, before, observed

    def ready(user, f, observed):
        first = C.status(C.http_call(user, C.PREP['request'], C.prep_args(f), observed), f, 'QUEUED')
        answer = C.status(C.http_call(user, C.PREP['step'], C.prep_args(f), observed), f, 'READY')
        assert answer['created_at'] == first['created_at'] and answer['unit_attempts'] == 0
        with http.connect() as conn, conn.cursor() as cur:
            assert C.one_work(cur, f)['payload']['inputs'] == f['expected']
        return answer

    def lifecycle():
        user, _, f, before, observed = prepare('choice-preparation-flow')
        args = C.save_args(f)
        C.refused(C.http_call(user, C.PREP['get'], C.prep_args(f), observed), 'P0001', 'CP7_CHOICE_PREPARATION_NOT_STARTED')
        for method, payload in ((C.READ, C.read_args(f)), (C.SAVE, args)):
            C.refused(C.http_call(user, method, payload, observed), 'P0001', 'CP7_CHOICE_PREPARATION_REQUIRED')
        with http.connect() as conn, conn.cursor() as cur:
            C.unchanged(cur, before)
        # Commit occurs through real HTTP. Deliberately ignore the first body
        # as a client-state-loss simulation; this is NOT a broken-network claim.
        sent = C.http_call(user, C.PREP['request'], C.prep_args(f), observed)
        assert sent['status'] == 200
        del sent
        reopened = C.status(C.http_call(user, C.PREP['get'], C.prep_args(f), observed), f, 'QUEUED')
        repeated = C.status(C.http_call(user, C.PREP['request'], C.prep_args(f), observed), f, 'QUEUED')
        assert reopened == repeated
        finished = C.status(C.http_call(user, C.PREP['step'], C.prep_args(f), observed), f, 'READY')
        assert finished['created_at'] == reopened['created_at'] and finished['unit_attempts'] == 0
        for verb in ('get', 'step', 'request'):
            assert C.status(C.http_call(user, C.PREP[verb], C.prep_args(f), observed), f, 'READY') == finished
        with http.connect() as conn, conn.cursor() as cur:
            C.unchanged(cur, before)
            work = C.one_work(cur, f)
            assert work['payload']['inputs'] == f['expected']
            expected = C.candidate(cur, f)
        read = C.http_call(user, C.READ, C.read_args(f), observed)
        assert read == dict(status=200, body=expected), read
        first = C.http_call(user, C.SAVE, args, observed)
        assert first['status'] == 200 and first['body']['revision'] == '1', first
        assert first['body']['state'] == 'CONFIRMED_ASSUMPTION' and first['body']['forecast_applied'] is False
        assert C.http_call(user, C.SAVE, args, observed) == first
        with http.connect() as conn, conn.cursor() as cur:
            after = C.snapshot(cur)
            assert after['money'] == before['money'] and C.one_work(cur, f) == work
            assert after['counts'] == tuple(n + 1 for n in before['counts'])
        changed = dict(args, p_payload=dict(args['p_payload'], reason='changed same HTTP request'))
        C.refused(C.http_call(user, C.SAVE, changed, observed), 'P0001', 'CP7_ANALOG_CHOICE_REQUEST_CHANGED')
        with http.connect() as conn, conn.cursor() as cur:
            C.unchanged(cur, after)
        return dict(status='PASS', actual_Auth_PostgREST=True, same_work_after_client_state_loss=True,
            actual_network_reply_loss=False, cold_GET_read_SAVE_refused=True,
            READY_does_not_save=True, full_compiler_candidate_equal=True,
            exact_SAVE_UUID_payload_replay=True, changed_payload_refused=True,
            no_money_stock_HPP_change=True, observations=C.observations(observed))

    def stale_source():
        user, _, f, before, observed = prepare('choice-preparation-source')
        finished = ready(user, f, observed)
        historical = C.http_call(user, C.READ, C.read_args(f), observed)
        assert historical['status'] == 200
        with http.connect() as conn, conn.cursor() as cur:
            C.unchanged(cur, before)
            C.plan.found_fg(cur, f['x'], '1')
            after_post = C.snapshot(cur)
            work = C.one_work(cur, f)
            conn.commit()
        C.refused(C.http_call(user, C.SAVE, C.save_args(f), observed), '40001', 'CP7_ANALOG_CHOICE_SOURCE_CHANGED')
        assert C.http_call(user, C.READ, C.read_args(f), observed) == historical
        assert C.status(C.http_call(user, C.PREP['get'], C.prep_args(f), observed), f, 'READY') == finished
        with http.connect() as conn, conn.cursor() as cur:
            C.unchanged(cur, after_post)
            assert C.one_work(cur, f) == work
        return dict(status='PASS', actual_Native_post_changes_source=True,
            actual_Auth_SAVE_refuses_old_source=True, historical_result_remains_exact=True,
            no_effect_beyond_explicit_Native_post=True, observations=C.observations(observed))

    def access():
        user, other, f, before, observed = prepare('choice-preparation-access', extra=True)
        ready(user, f, observed)
        with http.connect() as conn, conn.cursor() as cur:
            epoch = C.reader.reader.epoch(cur, other.auth_user_id)
        for name, args in C.calls(f, epoch=epoch):
            result = C.http_call(other, name, args, observed)
            assert result['status'] == 403, result
            C.refused(result, '42501', 'CP7_PRODUCT_ANALOG_RUN_UNAVAILABLE')
        for name, args in C.calls(f, epoch='0' * 64):
            C.refused(C.http_call(user, name, args, observed), '42501', 'CP7_ANALYSIS_ACCESS_CHANGED')
        for name, args in C.calls(f):
            reply = http.anon_rpc(name, args)
            assert reply['status'] in (401, 403), reply
        with http.connect() as conn, conn.cursor() as cur:
            C.unchanged(cur, before)
        args = C.save_args(f)
        accepted = C.http_call(user, C.SAVE, args, observed)
        assert accepted['status'] == 200
        with http.connect() as conn, conn.cursor() as cur:
            C.plan.b.api.admin(cur)
            cur.execute('update erp.app_users set is_active=false where auth_user_id=%s', (user.auth_user_id,))
            after = C.snapshot(cur)
            assert after['money'] == before['money']
            conn.commit()
        for name, payload in C.calls(f, save=args):
            reply = C.http_call(user, name, payload, observed)
            assert reply['status'] == 403, reply
            C.refused(reply, '42501')
        with http.connect() as conn, conn.cursor() as cur:
            C.unchanged(cur, after)
        return dict(status='PASS', actual_second_OWNER_own_epoch_denied=True,
            wrong_epoch_and_anonymous_all_five_RPCs_denied=True,
            actual_old_token_after_revocation_denied=True, committed_SAVE_replay_denied=True,
            no_money_stock_HPP_change=True, observations=C.observations(observed))

    return list(zip(C.IDS['http'], (lifecycle, stale_source, access)))
