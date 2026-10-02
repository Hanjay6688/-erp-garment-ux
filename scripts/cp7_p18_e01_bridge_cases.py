"""Focused P18 E01 bridge; not full P18 or independent acceptance.

Every physical, cost, sale, cash and return effect uses the qualified E01
Native worksheet. Consumers then share its real current source and immutable
archives. No production result, money balance or HPP is seeded here.
"""
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from datetime import timedelta
import json
import uuid

import cp7_f03_e01_cases as worksheet
import cp7_obligation_report_cases as reports
import cp7_analysis_cases as analysis
import cp7_note_correction_cases as notes
import cp7_planning_history_cases as demand
import cp7_model_native_cases as models

b, auth = reports.b, reports.auth
rules = reports.previous.previous
DATABASE_NAMES = ('NATIVE_SOURCE_TO_ALL_CONSUMERS', 'CASH_INVERSE_IMMUTABLE_ARCHIVE', 'CURRENT_AUTHORITY',
                  'OWNING_NOTE_CORRECTION_ALL_CONSUMERS', 'CORRECTED_DEMAND_PROSPECTIVE_MODEL')
RACE_NAMES = ('CASH_INVERSE_DURING_SAVED_REPORT_WAIT',)
HTTP_NAMES = ('EXACT_AUTH_NATIVE_SOURCE_TO_REPORT',)
BROWSER_NAMES = ('DESKTOP', 'MOBILE')
REQUIRED = dict(native=len(DATABASE_NAMES), races=len(RACE_NAMES), http=len(HTTP_NAMES), browser=len(BROWSER_NAMES))
EXPECTED = sum(REQUIRED.values())


def prepare(cur, today):
    result = worksheet.journey(cur, today)
    ids = result['source_ids']
    tag, bank = cur.execute('select sale_number, (select cash_account_id::text from erp.sales_payments where id=%s) '
                           'from erp.sales_headers where id=%s',
                           (result['payment']['payment_id'], ids['sale'])).fetchone()
    f = dict(ids, tag=tag, bank=bank, payment_id=result['payment']['payment_id'])
    literal(cur, f, '175.00')
    return f, result


def literal(cur, f, remaining):
    detail = worksheet.source.read(cur, f)['detail']
    assert detail['financial']['net_total'] == '375.00'
    assert detail['financial']['open_balance'] == remaining
    assert worksheet.physical(cur, f) == 45
    assert cur.execute('select sum(m.qty_signed*h.hpp_per_pcs) from erp.fg_stock_movements m '
                       'join erp.fg_lots l on l.id=m.lot_id join erp.v_current_hpp h on h.lot_id=l.id '
                       'where l.po_id=%s', (f['po'],)).fetchone()[0] == Decimal('675')
    hpp = worksheet.native(cur, 'select to_jsonb(h) from erp.get_hpp_completeness(%s) h', (f['po'],))
    assert Decimal(str(hpp['current_hpp_total'])) == 900
    assert Decimal(str(hpp['hpp_per_pcs'])) == 15 and hpp['qty_basis_pcs'] == 60
    assert hpp['pending_reason_count'] == 0


def consumers(cur, today, f, subject=None):
    before = b.boundary.snapshot(cur)
    original = analysis.capture(cur, today, subject=subject)
    analysis.checked(original)
    assert original['financial_source'] is not None
    financial = original['financial_source']['report']['snapshot']
    assert financial['data_confidence']['status'] == 'READY'
    current_owner = worksheet.finance.read(cur, today, subject=subject)
    # The original period can be longer than the one-day financial worksheet.
    # Current position uses the same authoritative as-of, not a new sum.
    for key in ('customer_ar', 'fg_inventory', 'cash'):
        assert financial['financial_position'][key] == current_owner['snapshot']['financial_position'][key]
    source = rules.source(cur, original, subject)
    ar = rules.row(source, 'AR_DUE:' + f['sale'])
    payroll = rules.row(source, reports.previous.key('PAYROLL_AP', f['payroll']))
    assert ar['financial_source']['remaining']['value'] == '175.00'
    assert Decimal(payroll['financial_source']['remaining']['value']) == 180
    assert ar['value']['state'] == payroll['value']['state'] == 'UNKNOWN'
    assert ar['financial_source']['recorded_due_date'] is None
    assert not ar['business_resolved'] and not payroll['business_resolved']
    assert source['analysis']['analysis'] == original['analysis']
    assert source['analysis']['financial_source'] == original['financial_source']
    base = reports.base(cur, original, subject)
    view = reports.preview(cur, base, subject)
    payload = reports.payload(view, title='E01 produksi sampai retur dan tagihan')
    request = uuid.uuid4()
    appendix = reports.checked(reports.command(cur, payload, request, subject), payload)
    assert appendix['base_report']['analysis']['analysis'] == original['analysis']
    assert appendix['base_report']['analysis']['financial_source'] == original['financial_source']
    assert '175.00 IDR' in appendix['body']
    assert appendix['base_report']['body'] == base['body']
    assert appendix['source']['analysis']['analysis'] == original['analysis']
    assert b.boundary.snapshot(cur) == before
    return dict(original=original, source=source, base=base, view=view, payload=payload,
                request=str(request), appendix=appendix)


def inverse(cur, f):
    # This is the current public CP7 payment inverse, including current review.
    return worksheet.payments.inverse(cur, f, f['payment_id'])


def cases(cur, today):
    def complete():
        f, trace = prepare(cur, today)
        c = consumers(cur, today, f)
        before = b.boundary.snapshot(cur)
        observed = rules.observe(cur, c['original'])
        for key in ('AR_DUE:' + f['sale'], reports.previous.key('PAYROLL_AP', f['payroll'])):
            episode = rules.observation(observed, key)['episode']
            assert episode['state'] == 'ACTIVE' and episode['freshness'] == 'UNKNOWN'
        assert b.boundary.snapshot(cur) == before
        literal(cur, f, '175.00')
        return dict(status='PASS', actual_Native_E01_60_to_sale20_cash200_return5=True,
                    physical45_value675_HPP15_AR175_payroll180=True,
                    same_Original_in_analysis_base_report_appendix_rule_source=True,
                    missing_due_UNKNOWN_not_zero_or_false_healing=True,
                    all_consumers_leave_ERP_business_unchanged=True, checkpoints=trace['checkpoints'])

    def archive():
        f, _ = prepare(cur, today)
        c = consumers(cur, today, f)
        body, source = c['appendix']['body'], c['appendix']['source']
        inverse(cur, f)
        literal(cur, f, '375.00')
        archived = reports.read(cur, c['appendix']['id'])
        assert archived['source_state'] == 'ARCHIVED_STALE'
        assert archived['body'] == body and archived['source'] == source
        original = analysis.read(cur, c['original']['run_id'])
        assert original['analysis'] == c['original']['analysis']
        assert original['financial_source'] == c['original']['financial_source']
        fresh = analysis.capture(cur, today)
        analysis.checked(fresh)
        new_base = reports.base(cur, fresh)
        view = reports.preview(cur, new_base)
        payload = reports.payload(view, c['appendix'], title='E01 setelah inverse pembayaran')
        successor = reports.checked(reports.command(cur, payload), payload)
        ar = rules.row(successor['source'], 'AR_DUE:' + f['sale'])
        assert ar['financial_source']['remaining']['value'] == '375.00'
        assert successor['series_id'] == c['appendix']['series_id'] and successor['revision'] == '2'
        assert successor['base_report']['period_query'] == c['appendix']['base_report']['period_query']
        assert reports.read(cur, c['appendix']['id'])['body'] == body
        assert reports.command(cur, c['payload'], c['request'], lookup=True)['document']['body'] == body
        return dict(status='PASS', actual_public_cash_inverse_AR175_to375_stock45_HPP15_unchanged=True,
                    earlier_Original_finance_body_and_source_byte_identical=True,
                    explicit_current_revision_same_period_no_historical_relabel=True,
                    old_UUID_recovery_returns_original_immutable_body=True)

    def current():
        f, _ = prepare(cur, today)
        subject, role = reports.previous.actor(cur)
        c = consumers(cur, today, f, subject)
        other, _ = reports.previous.actor(cur)
        auth.refused(cur, lambda: reports.read(cur, c['appendix']['id'], other), 'CP7_OBLIGATION_REPORT_UNAVAILABLE')
        reports.previous.revoke(cur, role, 'finance.payroll.view')
        for operation in (
            lambda: reports.read(cur, c['appendix']['id'], subject),
            lambda: reports.command(cur, c['payload'], c['request'], subject, True),
            lambda: reports.command(cur, c['payload'], c['request'], subject),
        ):
            auth.refused(cur, operation, 'CP7_OBLIGATION_REPORT_DOMAIN_DENIED')
        assert reports.listing(cur, c['original'], subject)['rows'] == []
        source = rules.source(cur, c['original'], subject)
        assert source['coverage']['payroll_ap'] == 'EXCLUDED_BY_CURRENT_RIGHTS'
        assert not any(r['domain'] == 'PAYROLL_AP' for r in source['rows'])
        assert rules.row(source, 'AR_DUE:' + f['sale'])['financial_source']['remaining']['value'] == '175.00'
        return dict(status='PASS', real_E01_current_payroll_right_before_old_body_UUID_replay_and_count=True,
                    own_AR175_and_ops_remain_authorized_without_payroll_leak=True,
                    foreign_actor_saved_report_unavailable=True)

    def corrected_consumers():
        f, _ = prepare(cur, today)
        old_sale = f['sale']
        c = consumers(cur, today, f)
        old_body, old_source = c['appendix']['body'], c['appendix']['source']
        old_facts = notes.unchanged_facts(cur, old_sale)
        p, v = notes.edit(cur, f, '16')
        result = notes.correct(cur, p, v)
        f['sale'] = result['sale_id']
        detail = worksheet.source.read(cur, f)['detail']
        assert detail['financial']['net_total'] == '275.00' and detail['financial']['paid_total'] == '200.00'
        assert detail['financial']['open_balance'] == '75.00' and worksheet.physical(cur, f) == 49
        assert notes.unchanged_facts(cur, old_sale) == old_facts
        notes.inverse_date_truth(cur)
        old_report = reports.read(cur, c['appendix']['id'])
        assert old_report['source_state'] == 'ARCHIVED_STALE'
        assert old_report['body'] == old_body and old_report['source'] == old_source
        saved = analysis.read(cur, c['original']['run_id'])
        assert saved['analysis'] == c['original']['analysis'] and saved['financial_source'] == c['original']['financial_source']
        fresh = analysis.capture(cur, today)
        analysis.checked(fresh)
        financial = fresh['financial_source']['report']['snapshot']
        assert financial['data_confidence']['status'] == 'READY'
        assert Decimal(financial['financial_position']['customer_ar']) - Decimal(c['original']['financial_source']['report']['snapshot']['financial_position']['customer_ar']) == -100
        current_source = rules.source(cur, fresh)
        assert rules.row(current_source, 'AR_DUE:' + f['sale'])['financial_source']['remaining']['value'] == '75.00'
        assert not any(r['key'] == 'AR_DUE:' + old_sale and not r['business_resolved'] for r in current_source['rows'])
        new_base = reports.base(cur, fresh)
        payload = reports.payload(reports.preview(cur, new_base), c['appendix'], title='E01 nota dibetulkan, kas dan retur tetap')
        successor = reports.checked(reports.command(cur, payload), payload)
        assert successor['series_id'] == c['appendix']['series_id'] and successor['revision'] == '2'
        assert rules.row(successor['source'], 'AR_DUE:' + f['sale'])['financial_source']['remaining']['value'] == '75.00'
        assert reports.read(cur, c['appendix']['id'])['body'] == old_body
        assert notes.history(cur, old_sale)['current_sale_id'] == f['sale']
        return dict(status='PASS', owning_note20_to16_cash200_return5_retained=True,
                    current_Native_AR75_FG49_HPP15_and_financial_READY=True,
                    superseded_note_not_an_active_AR_obligation=True,
                    new_Original_analysis_report_rules_appendix_share_corrected_current_source=True,
                    prior_Original175_body_financial_and_source_immutable=True, explicit_report_revision2=True)

    def corrected_learning():
        f = notes.posted(cur, notes.stock(cur, today, 10, notes.source.fg.ax.r1.now(cur) - timedelta(days=2)))
        original_sale = f['sale']
        q = demand.query(today, 3)
        first = demand.capture(cur, today, q=q)
        assert demand.history(first, f)['gross_observed_pcs'] == '4'
        first_model = models.capture(cur, models.query(first, f))
        frozen = models.stored(cur, first_model['run_id'])
        old_history = cur.execute('select facts,result from cp7_planning.history_runs where id=%s', (first['run_id'],)).fetchone()
        p, v = notes.edit(cur, f, '3')
        result = notes.correct(cur, p, v)
        f['sale'] = result['sale_id']
        corrected = demand.capture(cur, today, q=q)
        assert demand.history(corrected, f)['gross_observed_pcs'] == '3'
        demand.stock_assert(cur, corrected, f, 7, 0, 7)
        assert demand.read(cur, first['run_id'])['source_state'] == 'ARCHIVED_STALE'
        assert cur.execute('select facts,result from cp7_planning.history_runs where id=%s', (first['run_id'],)).fetchone() == old_history
        assert models.read(cur, first_model['run_id'])['source_state'] == 'ARCHIVED_STALE'
        assert models.stored(cur, first_model['run_id']) == frozen
        current_model = models.capture(cur, models.query(corrected, f))
        current_input, _ = models.stored(cur, current_model['run_id'])
        assert current_input['known_as_of'] == corrected['captured_at']
        assert all(x['known_at'] <= corrected['captured_at'] for x in current_input['series'])
        assert current_input['no_retrospective_availability_backfill']
        assert all(x['state'] != 'OBSERVED' and x['value'] is None for x in current_input['series'])
        assert current_model['automatic_activation'] is False and current_model['apply_allowed'] is False
        assert notes.history(cur, original_sale)['current_sale_id'] == f['sale']
        return dict(status='PASS', actual_Native_corrected_demand4_to3_once_current_stock7=True,
                    original_history_and_model_input_result_immutable=True,
                    correction_known_at_actual_new_capture_not_old_physical_time=True,
                    historical_availability_UNKNOWN_not_fabricated_zero_or_OBSERVED=True,
                    no_automatic_model_promotion_or_material_business_write=True)

    return [('P18_E01_' + name, operation) for name, operation in zip(DATABASE_NAMES, (complete, archive, current, corrected_consumers, corrected_learning))]


def races(tools, today):
    def payment_wait():
        with tools.connect() as conn, conn.cursor() as cur:
            f, _ = prepare(cur, today)
            c = consumers(cur, today, f)
            conn.commit()
        def lookup():
            with tools.connect() as conn, conn.cursor() as cur:
                result = reports.command(cur, c['payload'], c['request'], lookup=True)
                conn.commit()
                return result['document']
        with tools.connect() as holder, holder.cursor() as held:
            held.execute("select pg_advisory_xact_lock(hashtextextended('CP7:OBLIGATION_REPORT_REQUEST:'||%s||':'||%s,0))",
                         (c['appendix']['actor_scope_id'], c['request']))
            with ThreadPoolExecutor(max_workers=1) as pool:
                job = pool.submit(lookup)
                try:
                    rules.wait_for(tools, 'erp_cp7_get_obligation_report_request_v1')
                    with tools.connect() as conn, conn.cursor() as cur:
                        inverse(cur, f)
                        conn.commit()
                finally:
                    holder.rollback()
                archived = job.result(90)
        assert archived['source_state'] == 'ARCHIVED_STALE'
        assert archived['body'] == c['appendix']['body'] and archived['source'] == c['appendix']['source']
        with tools.connect() as conn, conn.cursor() as cur:
            literal(cur, f, '375.00')
            assert cur.execute('select count(*) from cp7_reminder_native.obligation_reports where request_id=%s',
                               (c['request'],)).fetchone()[0] == 1
        return dict(status='PASS', actual_E01_cash_inverse_during_observed_cached_request_wait=True,
                    post_wait_fresh_stale_state_original175_snapshot_body_retained=True,
                    Native_current_AR375_stock45_HPP15_one_appendix=True)
    return [('P18_E01_' + RACE_NAMES[0], payment_wait)]


def http_cases(http, today):
    def flow():
        owner = http.login('OWNER', 'p18-e01-report-owner')
        with http.connect() as conn, conn.cursor() as cur:
            had = cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
            acl = cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
            if not had:
                cur.execute('grant usage on schema erp to authenticated')
            f, _ = prepare(cur, today)
            if not had:
                cur.execute('revoke usage on schema erp from authenticated')
            assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0] == acl
            conn.commit()
        def send(name, args):
            r = owner.rpc(name, args)
            assert r['status'] == 200, (name, r)
            return r['body']
        original = send('erp_cp7_capture_analysis_v1', dict(
            p_query=analysis.previous.baseline.history.query(today), p_request=str(uuid.uuid4())))
        analysis.checked(original)
        base = send('erp_cp7_publish_report_v1', dict(
            p_payload=reports.original_reports.payload(original), p_request=str(uuid.uuid4())))['document']
        view = send('erp_cp7_get_obligation_report_preview_v1', dict(p_publication=base['id']))
        payload = reports.payload(view, title='E01 Native Auth laporan dan tagihan')
        args = dict(p_payload=payload, p_request=str(uuid.uuid4()))
        saved = reports.checked(send('erp_cp7_publish_obligation_report_v1', args), payload)
        assert rules.row(saved['source'], 'AR_DUE:' + f['sale'])['financial_source']['remaining']['value'] == '175.00'
        assert send('erp_cp7_get_obligation_report_request_v1', args)['document'] == saved
        assert saved['base_report']['analysis']['analysis'] == original['analysis']
        assert http.anon_rpc('erp_cp7_read_obligation_report_v1', dict(p_id=saved['id']))['status'] in (401, 403)
        with http.connect() as conn, conn.cursor() as cur:
            literal(cur, f, '175.00')
            cur.execute('update erp.app_users set is_active=false where auth_user_id=%s', (owner.auth_user_id,))
            conn.commit()
        for name, query in (
            ('erp_cp7_read_obligation_report_v1', dict(p_id=saved['id'])),
            ('erp_cp7_get_obligation_report_request_v1', args),
            ('erp_cp7_read_analysis_v1', dict(p_run=original['run_id'])),
            ('erp_cp7_get_rule_conditions_v1', dict(p_run=original['run_id'])),
        ):
            assert owner.rpc(name, query)['status'] == 403
        return dict(status='PASS', actual_Auth_HTTP_E01_Native_source_Original_report_appendix_AR175=True,
                    same_UUID_one_archive_anonymous_denied_current403_before_cached_all_facts=True,
                    source_stock45_value675_HPP15_unchanged=True)
    return [('P18_E01_' + HTTP_NAMES[0], flow)]
