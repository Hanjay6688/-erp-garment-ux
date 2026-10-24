"""Exact retained failed-wash chronology oracle after Native payroll linkage."""
from cp6_v2620h_adversarial_regression import *
from prerequisites import complete_known_work

def case_r02(cur: psycopg.Cursor) -> dict[str, Any]:
    fixture = base.fresh(cur, 'a')
    delivery = base.post_delivery(
        cur, fixture, base.BASE_PROCESS, '2026-09-01T11:00:00Z'
    )
    delivery_id = str(delivery['delivery_id'])
    failed = base.action(
        cur,
        'POST_FAILED_WASH',
        {
            'delivery_id': delivery_id,
            'wash_process_id': base.BASE_PROCESS,
            'custody_outcome': 'RETURN_UNPROCESSED',
            'physical_at': '2026-09-02T11:00:00Z',
            'reason': 'H native authoritative full physical return',
            'lines': [{
                'delivery_batch_size_line_id': base.delivery_size_line(cur, delivery_id),
                'qty_attempted_pcs': 10,
            }],
        },
        base.delivery_version(cur, delivery_id),
    )
    inverse = str(base.one(
        cur,
        """select return_wip_event_id from erp.laundry_failed_wash_attempts
           where receipt_id=%s""",
        (failed['receipt_id'],),
    ))
    complete_known_work(cur)
    baseline = owner(cur)['data_confidence']['status']
    if baseline != 'READY' or targeted_issues(cur) != 0:
        raise AssertionError('R02 lawful baseline is not READY')
    cur.execute('savepoint h_r02_fault')
    cur.execute(
        "update erp.wip_stage_events set physical_at='2026-09-01T12:00:00Z' where id=%s",
        (inverse,),
    )
    blocked_issue = issue_count(cur, 'V2620H_FAILED_WASH_RETURN_TIME_MISMATCH')
    blocked_status = owner(cur)['data_confidence']['status']
    if blocked_issue != 1 or blocked_status != 'BLOCKED':
        raise AssertionError(
            f'R02 fault escaped: issue={blocked_issue}, status={blocked_status}'
        )
    cur.execute('rollback to savepoint h_r02_fault')
    cur.execute('release savepoint h_r02_fault')
    restored = owner(cur)['data_confidence']['status']
    if restored != 'READY' or targeted_issues(cur) != 0:
        raise AssertionError('R02 rollback did not restore READY baseline')
    return {
        'status': 'PASS',
        'dispatch_physical_at': '2026-09-01T11:00:00Z',
        'authoritative_return_physical_at': '2026-09-02T11:00:00Z',
        'fault_inverse_physical_at': '2026-09-01T12:00:00Z',
        'fault_issue_count': blocked_issue,
        'fault_report_status': blocked_status,
        'restored_report_status': restored,
    }
