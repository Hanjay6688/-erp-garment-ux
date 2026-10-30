"""Read-only cancelled-pool oracle against the first Native-validated ACTIVE rows.

Current allocation eligibility is deliberately not a historical verdict. This
oracle never reconstructs a historical manifest from a current carry preview.
The separate phase-specific Native HPP/FG cancellation oracles remain required.
"""
from collections import Counter
from copy import deepcopy
from decimal import Decimal
import json

IMMUTABLE = ('sources', 'allocations', 'links', 'choice_allocation', 'lines')
CANCEL_FIELDS = {'status', 'cancellation_journal_entry_id', 'cancellation_reason',
                 'cancelled_by', 'cancelled_at', 'row_version'}


def require(ok, message):
    if not ok:
        raise ValueError('S03_HISTORY_' + message)


def require_observed(history, pools):
    ids = [pool['id'] for pool in pools]
    require(len(ids) == len(set(ids)) and set(history) <= set(ids),
            'EVERY_PRIOR_POOL_PRESENT_EXACTLY_ONCE_REQUIRED')


def snapshot(cur, f, pool):
    result = {'pool': pool}
    for key, table in (('sources', 'erp.attendance_hpp_pool_sources'),
                       ('allocations', 'erp.attendance_hpp_pool_allocations'),
                       ('links', 'erp.attendance_hpp_journal_line_links'),
                       ('choice_allocation', 'cp7_attendance_choice.allocations_v1')):
        result[key] = f.one(cur, "select coalesce(jsonb_agg(to_jsonb(r)order by r.id),'[]'::jsonb)from "
                           + table + ' r where r.pool_id=%s', (pool['id'],))
    result['journal'] = f.one(cur, 'select to_jsonb(j)from erp.journal_entries j where id=%s',
                              (pool['post_journal_entry_id'],))
    result['lines'] = f.one(cur, "select coalesce(jsonb_agg(to_jsonb(l)order by l.id),'[]'::jsonb)from erp.journal_lines l where journal_entry_id=%s",
                            (pool['post_journal_entry_id'],))
    return result


def line_signature(row, flip=False):
    rest = {k: v for k, v in row.items() if k not in {'id', 'journal_entry_id', 'debit', 'credit', 'description'}}
    debit, credit = Decimal(str(row['debit'])), Decimal(str(row['credit']))
    require(debit.is_finite() and credit.is_finite(), 'NONFINITE_JOURNAL_AMOUNT')
    return (json.dumps(rest, sort_keys=True, separators=(',', ':')),
            credit if flip else debit, debit if flip else credit,
            'Reversal: ' + (row['description'] or '') if flip else row['description'])


def checked_cancelled(active, current, cancellation):
    require(type(active) is dict and active.get('pool', {}).get('status') == 'ACTIVE', 'NATIVE_ACTIVE_AUTHORITY_REQUIRED')
    old, now = active['pool'], current['pool']
    require(now['status'] == 'CANCELLED' and now['id'] == old['id'], 'CANCELLED_POOL_ID_REQUIRED')
    require({k: v for k, v in now.items() if k not in CANCEL_FIELDS}
            == {k: v for k, v in old.items() if k not in CANCEL_FIELDS}, 'IMMUTABLE_POOL_CHANGED')
    require(now['row_version'] == old['row_version'] + 1, 'NATIVE_CANCEL_VERSION_REQUIRED')
    require(all(now.get(k) for k in ('cancellation_journal_entry_id', 'cancellation_reason', 'cancelled_by', 'cancelled_at')),
            'NATIVE_CANCEL_METADATA_REQUIRED')
    for key in IMMUTABLE:
        require(current[key] == active[key], 'IMMUTABLE_' + key.upper() + '_CHANGED')
    require(active['sources'] and active['allocations'] and active['links'] and active['lines'], 'COMPLETE_ACTIVE_ROWS_REQUIRED')
    require(active['journal']['status'] == 'POSTED'
            and current['journal'] == dict(active['journal'], status='REVERSED'), 'ORIGINAL_JOURNAL_CHANGED')
    require((active['journal']['source_type'], active['journal']['source_id']) == ('ATTENDANCE_HPP_POOL', old['id']),
            'ORIGINAL_POOL_JOURNAL_LINEAGE_REQUIRED')
    inverses = cancellation['journals']
    require(len(inverses) == 1, 'EXACTLY_ONE_LINKED_INVERSE_REQUIRED')
    inverse = inverses[0]
    require((inverse['id'], inverse['source_type'], inverse['source_id'], inverse['reversal_of_id'], inverse['status'])
            == (now['cancellation_journal_entry_id'], 'JOURNAL_REVERSAL', active['journal']['id'], active['journal']['id'], 'POSTED'),
            'INVERSE_LINEAGE_REQUIRED')
    require(inverse['economic_date'] == cancellation['expected_economic_date']
            and inverse['transaction_date'] == cancellation['expected_book_date'], 'INVERSE_DATES_REQUIRED')
    lines = cancellation['lines']
    require(lines and len(lines) == len(active['lines'])
            and all(r['journal_entry_id'] == inverse['id'] for r in lines)
            and len({r['id'] for r in lines}) == len(lines)
            and not ({r['id'] for r in lines} & {r['id'] for r in active['lines']})
            and Counter(line_signature(r, True) for r in active['lines']) == Counter(line_signature(r) for r in lines),
            'EXACT_INVERSE_LINES_REQUIRED')
    allocations = active['choice_allocation']
    if allocations:
        require(len(allocations) == 1 and len(cancellation['choice_reversals']) == 1, 'OWNING_ALLOCATION_REVERSAL_REQUIRED')
        reversal = cancellation['choice_reversals'][0]
        require((reversal['allocation_id'], reversal['journal_id'], reversal['app_user'], reversal['reason'])
                == (allocations[0]['id'], inverse['id'], now['cancelled_by'], now['cancellation_reason']),
                'OWNING_REVERSAL_LINEAGE_REQUIRED')
    else:
        require(cancellation['choice_reversals'] == [], 'ORDINARY_POOL_CANNOT_HAVE_CHOICE_REVERSAL')
    return dict(status='CANCELLED_HISTORY_EXACT_ACTIVE_AUTHORITY_AND_LINKED_INVERSE',
                pool_id=now['id'], current_allocation_eligibility_claim=False)


def observe(cur, f, pool, history):
    require(type(history) is dict, 'AUTHORITY_MAP_REQUIRED')
    if pool['status'] == 'ACTIVE':
        require(f.native(cur, "select erp.validate_attendance_hpp_pool_v1(%s)->>'validation'", (pool['id'],)) == 'PASS',
                'ACTUAL_NATIVE_ACTIVE_VALIDATOR_REQUIRED')
        current = snapshot(cur, f, pool)
        if pool['id'] in history:
            require(history[pool['id']]['active'] == current and history[pool['id']]['cancelled'] is None,
                    'NATIVE_VALIDATED_ACTIVE_AUTHORITY_CHANGED')
        else:
            history[pool['id']] = dict(active=deepcopy(current), cancelled=None)
        return dict(status='ACTUAL_NATIVE_ACTIVE_VALIDATION_PASS', pool_id=pool['id'])
    require(pool['status'] == 'CANCELLED', 'ACTIVE_OR_CANCELLED_REQUIRED')
    require(pool['id'] in history, 'CANCELLED_WITHOUT_PRE_CANCEL_ACTIVE_AUTHORITY')
    current = snapshot(cur, f, pool)
    cancellation = dict(
        journals=f.one(cur, "select coalesce(jsonb_agg(to_jsonb(j)order by j.id),'[]'::jsonb)from erp.journal_entries j where reversal_of_id=%s", (pool['post_journal_entry_id'],)),
        lines=f.one(cur, "select coalesce(jsonb_agg(to_jsonb(l)order by l.id),'[]'::jsonb)from erp.journal_lines l where journal_entry_id=%s", (pool['cancellation_journal_entry_id'],)),
        choice_reversals=f.one(cur, "select coalesce(jsonb_agg(to_jsonb(r)order by r.id),'[]'::jsonb)from cp7_attendance_choice.allocation_reversals_v1 r join cp7_attendance_choice.allocations_v1 a on a.id=r.allocation_id where a.pool_id=%s", (pool['id'],)))
    prior = history[pool['id']]['cancelled']
    if prior is None:
        day = f.one(cur, "select (%s::timestamptz at time zone 'Asia/Jakarta')::date::text", (pool['cancelled_at'],))
        book = str(f.one(cur, 'select erp.resolve_accounting_transaction_date(%s::date)', (day,)))
    else:
        day, book = prior['cancellation']['expected_economic_date'], prior['cancellation']['expected_book_date']
    cancellation.update(expected_economic_date=day, expected_book_date=book)
    proof = checked_cancelled(history[pool['id']]['active'], current, cancellation)
    frozen = dict(current=current, cancellation=cancellation)
    if prior is None:
        history[pool['id']]['cancelled'] = deepcopy(frozen)
    else:
        require(prior == frozen, 'CANCELLED_HISTORY_CHANGED_AFTER_FIRST_VALIDATION')
    return proof
