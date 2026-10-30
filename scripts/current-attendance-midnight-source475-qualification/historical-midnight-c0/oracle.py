"""Independent fixed-instant/fact oracles; no DB or Native calculations."""
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

WIB = ZoneInfo('Asia/Jakarta')
UTC = timezone.utc
CENTS = 100003


def epoch_us(value):
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError('S03_MIDNIGHT_AWARE_INSTANT_REQUIRED')
    delta = value.astimezone(UTC) - datetime(1970, 1, 1, tzinfo=UTC)
    return (delta.days * 86400 + delta.seconds) * 1000000 + delta.microseconds


def fixed_plan(today):
    if type(today) is not date:
        raise ValueError('S03_MIDNIGHT_NATIVE_BUSINESS_TODAY_DATE_REQUIRED')
    left = today - timedelta(days=3)
    right = today - timedelta(days=2)
    after = datetime.combine(right, time.min, WIB).astimezone(UTC)
    before = after - timedelta(microseconds=1)
    assert before.date() == after.date() == left
    assert before.astimezone(WIB).date() == left
    assert after.astimezone(WIB).date() == right
    return dict(left=left, right=right, before=before, after=after,
                before_us=epoch_us(before), after_us=epoch_us(after))


def assert_events(events, plan, source):
    assert len(events) == 2, ('S03_MIDNIGHT_EXACT_TWO_EVENTS', events)
    by_epoch = {row['event_epoch_us']: row for row in events}
    assert set(by_epoch) == {plan['before_us'], plan['after_us']}, by_epoch
    before, after = (by_epoch[plan[key]] for key in ('before_us', 'after_us'))
    assert after['event_epoch_us'] - before['event_epoch_us'] == 1
    assert before['event_id'] != after['event_id']
    assert before['work_id'] != after['work_id']
    assert before['po_id'] == after['po_id']
    assert before['group_id'] == after['group_id']
    for row, day in ((before, plan['left']), (after, plan['right'])):
        assert type(row['qty']) is int and row['qty'] == 5, row
        assert row['kind'] == 'SELESAI_DIJAHIT' and row['work_status'] == 'POSTED', row
        assert row['contractor_id'] == row['work_contractor_id'] == source['contractor'], row
        assert row['event_epoch_us'] == row['work_epoch_us'], row
        assert row['wib_day'] == str(day) and row['utc_day'] == str(plan['left']), row
    return before, after


def assert_manifest(native, carried, public, source, decision, start, end, events):
    """Exact membership and original source ownership, not response-derived money."""
    expected = {row['event_id']: row for row in events}
    quantity = len(events) * 5
    assert native['period_start'] == str(start) and native['period_end'] == str(end)
    assert type(native['denominator_qty']) is int and native['denominator_qty'] == quantity
    assert type(native['numerator_cents']) is int and native['numerator_cents'] == 0 and native['sources'] == []
    destinations = native['destinations']
    assert len(destinations) == len(expected)
    assert {row['sewing_terminal_event_id'] for row in destinations} == set(expected)
    policy = source['capture']['native_manifest']['sources'][0]['policy_version_id']
    for row in destinations:
        fact = expected[row['sewing_terminal_event_id']]
        assert (row['contractor_id'], row['source_work_completion_id'], row['po_id'], row['cutting_group_id']) == (
            source['contractor'], fact['work_id'], fact['po_id'], fact['group_id'])
        assert row['physical_at_epoch_us'] == fact['event_epoch_us'] and row['sewing_qty'] == 5
        assert row['policy_version_id'] == policy
        assert row['contractor_role_snapshot'] == 'MANDOR'
        assert row['attendance_required_snapshot'] is True and row['is_special_snapshot'] is False
    assert carried['status'] == 'READY'
    manifest = carried['manifest']
    assert manifest['period_start'] == manifest['period_end'] == str(source['day'])
    assert manifest['output_start'] == str(start) and manifest['output_end'] == str(end)
    assert manifest['decision_id'] == decision['decision_id']
    assert manifest['source_binding'] == source['capture']['source_binding']
    assert manifest['numerator_cents'] == CENTS and manifest['denominator_qty'] == quantity
    assert manifest['sources'] == source['capture']['native_manifest']['sources']
    assert manifest['source_native_manifest'] == source['capture']['native_manifest']
    assert manifest['destinations'] == destinations
    assert manifest['output_destination_facts']['destinations'] == destinations
    assert manifest['output_destination_facts']['denominator_qty'] == quantity
    # Public wire deliberately strips private context and destination details.
    assert 'context' not in public
    assert public['action'] == 'ALLOCATE' and public['decision_id'] == decision['decision_id']
    assert public['payload']['period_start'] == public['payload']['period_end'] == str(source['day'])
    assert (public['payload']['output_start'], public['payload']['output_end']) == (str(start), str(end))
    assert public['amount_cents'] == str(CENTS) and public['amount'] == '1000.03'
    assert public['source_count'] == '1' and public['denominator_qty'] == str(quantity)
    assert public['source_binding'] == source['capture']['source_binding']
    assert public['economic_date'] == str(end) and public['can_apply'] is True
    assert public['business_DML'] is False
    return dict(source_cents=CENTS, denominator=quantity,
                destination_ids=sorted(expected), physical_epoch_us=[row['event_epoch_us'] for row in events])
