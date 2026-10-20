"""OW01 proposed extra Native case: pause/resume preserves accessory episodes.

No product/source quantity is fabricated. prepared(), BOM successor and found FG
use the existing Native fixtures. SYNTHETIC_PROVIDER_ANSWER and
TEST_CLOCK_OVERRIDE affect only disposable WA rows inside each savepoint.
These cases prove queued pg_net requests if run; actual provider transport is a
separate retained race case. This proposal has not run against Native.
"""
from copy import deepcopy
from decimal import Decimal as D

import cp7_wa_accessory_cases as accessory

NATIVE_IDS = ['WAF_ACCESSORY_NEED_PAUSE_RESUME']


def _save(cur, wa, x, **changes):
    values = dict(accessory.WA_VALUES, enabled=True, quiet_enabled=False, digest_times=[])
    values.update(changes)
    return wa.save(cur, x['s']['owner'], **values)


def _episode(cur, wa, x):
    a = wa.alerts(cur, accessory.RULE)[x['key']]
    rows = wa.outbox(cur, a['id'])
    assert len(rows) == 1, rows
    o = rows[0]
    assert o['episode'] == str(a['episode']) and o['round'] == 0, (a, rows)
    assert o['state'] == 'PENDING' and o['attempts'] == 0 and o['dispatch'] is None, rows
    return dict(alert_id=a['id'], episode=a['episode'], outbox_id=o['id'])


def _same_open(cur, wa, x, identity):
    a = wa.alerts(cur, accessory.RULE)[x['key']]
    assert (a['id'], a['episode']) == (identity['alert_id'], identity['episode']), (a, identity)
    return a


def _same_waiting(cur, wa, x, identity, *, round_=0, reason=None, count=1):
    _same_open(cur, wa, x, identity)
    rows = wa.outbox(cur, identity['alert_id'])
    assert len(rows) == count, rows
    waiting = [o for o in rows if o['round'] == round_]
    assert len(waiting) == 1, rows
    o = waiting[0]
    expected_id = identity['outbox_id'] if round_ == 0 else identity['repeat_outbox_id']
    assert o['id'] == expected_id and o['episode'] == str(identity['episode']), (o, identity)
    assert o['state'] in ('PENDING', 'HELD_QUIET') and o['attempts'] == 0 and o['dispatch'] is None, o
    if reason is not None:
        assert o['reason'] == reason, o
    return o


def _no_queue(cur, wa, *, outcome=None):
    before = wa.last_request(cur)
    result = wa.tick(cur, 'send_tick')
    assert result['outcome'] not in ('SENT', 'DIGEST') and wa.queued(cur, before) == [], result
    if outcome is not None:
        assert result['outcome'] == outcome, result
    return result


def _accept(cur, wa, x, message, *, rounds):
    # SYNTHETIC_PROVIDER_ANSWER: the same labelled savepoint fixture already
    # used by the retained Native WA cases. The real worker is tested elsewhere.
    wa.answer(cur, message['id'], 200, 'Message queued')
    _no_queue(cur, wa)
    rows = wa.outbox(cur, wa.alert_item(cur, accessory.RULE, x['key']))
    assert [(o['round'], o['state'], o['attempts']) for o in rows] == [
        (number, 'ACCEPTED', 1) for number in rounds], rows
    assert wa.dispatch(cur, message['id'])['status'] == 'PROVIDER_ACCEPTED'
    return rows


def _first_sent(cur, wa, x, identity, *, gross='186'):
    before_detail = deepcopy(wa.alerts(cur, accessory.RULE)[x['key']]['detail'])
    message = accessory.sent(cur, wa, x, gross=gross)
    assert not message['body'].startswith('\U0001f501 Masih terbuka'), message['body']
    rows = wa.outbox(cur, identity['alert_id'])
    assert len(rows) == 1 and rows[0]['id'] == identity['outbox_id'], rows
    assert (rows[0]['round'], rows[0]['state'], rows[0]['attempts']) == (0, 'DISPATCHED', 1), rows
    assert rows[0]['dispatch'] == message['id'], (rows, message)
    current = accessory.assert_detail(_same_open(cur, wa, x, identity), x, gross=gross)
    assert current['checked_at'] >= before_detail['checked_at'], (before_detail, current)
    return message


def cases(cur, today, wa):
    def pause_resume():
        checks = {}
        with accessory.isolated(cur, wa):
            x = accessory.prepared(cur, today, wa)
            identity = _episode(cur, wa, x)
            initial_detail = deepcopy(wa.alerts(cur, accessory.RULE)[x['key']]['detail'])
            _save(cur, wa, x, kinds=[])
            _no_queue(cur, wa)
            _same_waiting(cur, wa, x, identity, reason='KIND_OFF')
            _save(cur, wa, x, enabled=False)
            _no_queue(cur, wa, outcome='WA_OFF')
            _same_waiting(cur, wa, x, identity, reason='WA_OFF')
            _save(cur, wa, x)
            first = _first_sent(cur, wa, x, identity)
            current = wa.alerts(cur, accessory.RULE)[x['key']]['detail']
            assert current['checked_at'] > initial_detail['checked_at'], (initial_detail, current)
            _accept(cur, wa, x, first, rounds=(0,))
            _save(cur, wa, x, enabled=False)
            _no_queue(cur, wa, outcome='WA_OFF')
            _save(cur, wa, x)
            _no_queue(cur, wa)
            rows = wa.outbox(cur, identity['alert_id'])
            assert len(rows) == 1 and rows[0]['id'] == identity['outbox_id'], rows
            assert (rows[0]['state'], rows[0]['round'], rows[0]['attempts']) == ('ACCEPTED', 0, 1), rows
            assert accessory.original_unchanged(cur, x)
            assert wa.b.boundary.snapshot(cur) == x['boundary']
            checks['INITIAL_PAUSE_RESUME'] = 'same OPEN episode and round0, one first notice, no immediate repeat after acceptance'

        with accessory.isolated(cur, wa):
            x = accessory.prepared(cur, today, wa)
            identity = _episode(cur, wa, x)
            _save(cur, wa, x, enabled=False)
            new = accessory.successor(cur, x, qty='3')  # accepted Native BF writer
            boundary_after_source = wa.b.boundary.snapshot(cur)
            _no_queue(cur, wa, outcome='WA_OFF')
            _same_waiting(cur, wa, x, identity, reason='WA_OFF')
            _save(cur, wa, x)
            _no_queue(cur, wa)
            _same_waiting(cur, wa, x, identity, reason='RECHECK_ACCESSORY_SOURCE_CHANGED_AFTER_SNAPSHOT')
            assert accessory.original_unchanged(cur, x)
            assert wa.b.boundary.snapshot(cur) == boundary_after_source
            accessory.material.review_schedule(cur, today, accessory.analysis)
            fresh = accessory.stage_existing(cur, today, wa, x)
            fresh['f']['bom'] = new
            assert fresh['r']['run'] != x['r']['run']
            assert D(fresh['m']['gross']['value']) == D(93) * 3 == 279
            _same_waiting(cur, wa, fresh, identity)
            _first_sent(cur, wa, fresh, identity, gross='279')
            assert accessory.original_unchanged(cur, x) and D(x['m']['gross']['value']) == 186
            accessory.assert_unknown(x['m'])
            assert wa.b.boundary.snapshot(cur) == fresh['boundary']
            checks['SOURCE_CHANGE_WHILE_OFF'] = 'old snapshot held, same episode refreshed by new immutable analysis, one fresh round0 notice279'

        with accessory.isolated(cur, wa):
            x = accessory.prepared(cur, today, wa)
            identity = _episode(cur, wa, x)
            _save(cur, wa, x, enabled=False)
            wa.planv2.found_fg(cur, dict(root=x['f']['root']), 93)  # accepted Native found-stock writer
            boundary_after_source = wa.b.boundary.snapshot(cur)
            _no_queue(cur, wa, outcome='WA_OFF')
            _same_waiting(cur, wa, x, identity, reason='WA_OFF')
            _save(cur, wa, x)
            _no_queue(cur, wa)
            assert x['key'] not in wa.alerts(cur, accessory.RULE)
            rows = wa.outbox(cur, identity['alert_id'])
            assert len(rows) == 1 and rows[0]['id'] == identity['outbox_id'], rows
            assert (rows[0]['state'], rows[0]['round'], rows[0]['attempts'], rows[0]['dispatch']) == (
                'RESOLVED_BEFORE_SEND', 0, 0, None), rows
            assert accessory.original_unchanged(cur, x) and D(x['m']['gross']['value']) == 186
            accessory.assert_unknown(x['m'])
            assert wa.b.boundary.snapshot(cur) == boundary_after_source
            checks['SOURCE_RESOLVED_WHILE_OFF'] = 'complete Native coverage resolves same unattempted item before any queue request'

        with accessory.isolated(cur, wa):
            x = accessory.prepared(cur, today, wa)
            identity = _episode(cur, wa, x)
            _save(cur, wa, x, repeat_minutes=60)
            first = _first_sent(cur, wa, x, identity)
            _accept(cur, wa, x, first, rounds=(0,))
            # TEST_CLOCK_OVERRIDE: only this accepted WA item and its dispatch
            # move back61min. No Native source, capture date or policy is altered.
            wa.test_clock(cur, "update cp7_alert_native.outbox set settled_at=settled_at-interval'61 minutes' where id=%s and state='ACCEPTED'",
                (identity['outbox_id'],))
            wa.test_clock(cur, "update cp7_alert_native.dispatches set queued_at=queued_at-interval'61 minutes',"
                "answered_at=answered_at-interval'61 minutes' where id=%s", (first['id'],))
            q = accessory.quiet_window(cur, wa)
            _save(cur, wa, x, repeat_minutes=60, quiet_enabled=True, quiet_start=q['starts_at'], quiet_end=q['ends_at'])
            quiet = _no_queue(cur, wa, outcome='HELD_QUIET')
            assert quiet['repeats'] == 1, quiet
            rows = wa.outbox(cur, identity['alert_id'])
            assert [(o['round'], o['state'], o['attempts']) for o in rows] == [
                (0, 'ACCEPTED', 1), (1, 'HELD_QUIET', 0)], rows
            identity['repeat_outbox_id'] = rows[1]['id']
            _save(cur, wa, x, enabled=False, repeat_minutes=0)
            _no_queue(cur, wa, outcome='WA_OFF')
            _same_waiting(cur, wa, x, identity, round_=1, count=2, reason='WA_OFF')
            _save(cur, wa, x, repeat_minutes=0)
            _no_queue(cur, wa)
            _same_waiting(cur, wa, x, identity, round_=1, count=2, reason='REPEAT_OFF')
            _save(cur, wa, x, repeat_minutes=120)
            _no_queue(cur, wa)
            _same_waiting(cur, wa, x, identity, round_=1, count=2, reason='REPEAT_NOT_DUE')
            _save(cur, wa, x, repeat_minutes=60)
            again = accessory.sent(cur, wa, x)
            assert again['body'].startswith('\U0001f501 Masih terbuka'), again['body']
            rows = wa.outbox(cur, identity['alert_id'])
            assert len(rows) == 2 and rows[1]['id'] == identity['repeat_outbox_id'], rows
            assert (rows[1]['round'], rows[1]['state'], rows[1]['attempts'], rows[1]['dispatch']) == (
                1, 'DISPATCHED', 1, again['id']), rows
            _accept(cur, wa, x, again, rounds=(0, 1))
            _no_queue(cur, wa)
            assert len(wa.outbox(cur, identity['alert_id'])) == 2
            assert accessory.original_unchanged(cur, x)
            assert wa.b.boundary.snapshot(cur) == x['boundary']
            checks['QUEUED_REPEAT_CURRENT_POLICY'] = 'same queued round1 held by repeat0 and120, sent once when current60 is due'
        with accessory.isolated(cur, wa):
            x = accessory.prepared(cur, today, wa)
            identity = _episode(cur, wa, x)
            first = _first_sent(cur, wa, x, identity)
            # SYNTHETIC_PROVIDER_ANSWER: timeout leaves actual delivery unknown;
            # toggling settings cannot manufacture owner resolution or a retry.
            wa.answer(cur, first['id'], None, '', timed_out=True, error='Timeout was reached')
            _no_queue(cur, wa)
            assert wa.dispatch(cur, first['id'])['status'] == 'UNKNOWN'
            for settings in (dict(kinds=[]), dict(enabled=False), dict()):
                _save(cur, wa, x, **settings)
                _no_queue(cur, wa)
                _same_open(cur, wa, x, identity)
                rows = wa.outbox(cur, identity['alert_id'])
                assert len(rows) == 1 and rows[0]['id'] == identity['outbox_id'], rows
                assert (rows[0]['round'], rows[0]['state'], rows[0]['attempts'], rows[0]['dispatch']) == (
                    0, 'UNKNOWN', 1, first['id']), rows
                assert wa.dispatch(cur, first['id'])['status'] == 'UNKNOWN'
            assert accessory.original_unchanged(cur, x)
            assert wa.b.boundary.snapshot(cur) == x['boundary']
            checks['UNKNOWN_PROVIDER_PAUSE_RESUME'] = 'same UNKNOWN round0/attempt1; kindoff and WAoff/on never retry automatically'

        digest_checks = {}
        # Separate fresh fixtures prevent the unselected-kind slot from
        # consuming the selected-kind branch's due-slot uniqueness.
        for selected in (False, True):
            with accessory.isolated(cur, wa):
                x = accessory.prepared(cur, today, wa)
                identity = _episode(cur, wa, x)
                initial_detail = deepcopy(wa.alerts(cur, accessory.RULE)[x['key']]['detail'])
                # Existing actual-WIB clock helper; at most12sec near midnight.
                # All persisted date overrides below are WA-only and labelled.
                wa.past_midnight_if_close(cur, margin=10)
                slot = wa.one(cur, "select to_char(clock_timestamp() at time zone 'Asia/Jakarta','HH24:MI')")
                _save(cur, wa, x, repeat_minutes=0, digest_times=[slot], kinds=[accessory.RULE] if selected else [])
                rev = wa.revision(cur)
                # TEST_CLOCK_OVERRIDE: permit the current actual minute slot,
                # just as in the retained pacing/digest case; no Native date changes.
                wa.test_clock(cur, "update cp7_alert_native.settings set saved_at=saved_at-interval'5 minutes' where revision=%s", (rev,))
                before = wa.last_request(cur)
                result = wa.tick(cur, 'send_tick')
                requests = wa.queued(cur, before)
                _same_open(cur, wa, x, identity)
                if not selected:
                    assert requests == [], result
                    _same_waiting(cur, wa, x, identity, reason='KIND_OFF')
                    wa.b.api.admin(cur)
                    assert cur.execute('select count(*) from cp7_alert_native.dispatch_items where outbox_id=%s',
                        (identity['outbox_id'],)).fetchone()[0] == 0
                    assert accessory.original_unchanged(cur, x)
                    assert wa.b.boundary.snapshot(cur) == x['boundary']
                    digest_checks['CURRENT_KIND_OFF'] = 'due digest queues no accessory request and does not link pending round0'
                    continue
                assert result['outcome'] == 'DIGEST' and result['items'] == result['covered'] == 1, result
                message = wa.dispatch(cur, result['dispatch_id'])
                assert message['kind'] == 'DIGEST' and message['status'] == 'QUEUED', message
                assert len(requests) == 1 and requests[0]['base'] == wa.FAKE and requests[0]['phone'] == wa.PHONE, len(requests)
                assert requests[0]['text'] == message['body'] and 0 < len(message['body']) <= 1000
                assert message['body'].startswith('\U0001f4cb Ringkasan ERP Enteng · '), message['body']
                accessory.assert_notice_text(message['body'], x)
                rows = wa.outbox(cur, identity['alert_id'])
                assert len(rows) == 1 and rows[0]['id'] == identity['outbox_id'], rows
                assert (rows[0]['round'], rows[0]['state'], rows[0]['attempts'], rows[0]['dispatch']) == (
                    0, 'DISPATCHED', 1, message['id']), rows
                wa.b.api.admin(cur)
                links = cur.execute('select outbox_id from cp7_alert_native.dispatch_items where dispatch_id=%s order by outbox_id',
                    (message['id'],)).fetchall()
                assert links == [(identity['outbox_id'],)], links
                current = accessory.assert_detail(_same_open(cur, wa, x, identity), x)
                assert current['checked_at'] > initial_detail['checked_at'], (initial_detail, current)
                _accept(cur, wa, x, message, rounds=(0,))
                _no_queue(cur, wa)
                rows = wa.outbox(cur, identity['alert_id'])
                assert len(rows) == 1 and rows[0]['id'] == identity['outbox_id'], rows
                assert (rows[0]['round'], rows[0]['state'], rows[0]['attempts']) == (0, 'ACCEPTED', 1), rows
                wa.b.api.admin(cur)
                assert cur.execute("select count(*) from cp7_alert_native.dispatches where kind='DIGEST' and digest_slot=%s::timestamptz",
                    (result['slot'],)).fetchone()[0] == 1
                assert accessory.original_unchanged(cur, x)
                assert wa.b.boundary.snapshot(cur) == x['boundary']
                digest_checks['CURRENT_KIND_SELECTED'] = 'repeat0 independent; one fresh reviewed digest links pending round0 once, same-slot acceptance never duplicates'
        checks['SCHEDULED_DIGEST_PENDING_LINKAGE'] = digest_checks
        return dict(status='PASS', checks=checks, legacy_cases_retained_unchanged=True,
            source_fixture='accepted Native target100-WIP7=gap93; BOM2=>ASSUMED186; coverage remains UNKNOWN',
            test_labels=['SYNTHETIC_PROVIDER_ANSWER', 'TEST_CLOCK_OVERRIDE on own WA rows only'],
            transport_scope='queued pg_net request only; actual fake provider is a retained race case')
    return [(NATIVE_IDS[0], pause_resume)]
