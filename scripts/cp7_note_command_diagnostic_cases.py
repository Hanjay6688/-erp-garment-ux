"""Measure the unchanged owning command and an isolated execution experiment.

Every attempt uses the actual Native E01 writers, current authenticated scope
and unchanged eight-second statement limit. The same UUID/payload is reused
only after an exact savepoint rollback. JIT changes are transaction-local,
experimental and give zero product qualification or factory scale credit.
"""
from decimal import Decimal
from time import monotonic
import json
import uuid

import psycopg
import cp7_note_correction_cases as cases


def prepare(cur, today):
    f = cases.e01.production(cur, today)
    cases.posted(cur, f, '20', '25')
    f['root_sale'] = f['sale']
    cases.returned.payments.pay(cur, f, '200')
    f['allocations'] = cases.returned.read(cur, f)['page']['rows']
    payload, version = cases.returned.payload(cur, f, qty='5', refund='125', destination=f['location'])
    cases.cmd.command(cur, 'RETURN', payload, version)
    return f


def measure(cur, f, disable_jit, key):
    cases.b.api.admin(cur)
    payload, version = cases.edit(cur, f, '16')
    payload['item_lineage'] = [i['id'] for i in cases.source.read(cur, f)['detail']['items']]
    before = cases.snapshot(cur)
    measurement = dict(experiment='TRANSACTION_LOCAL_JIT_DISABLED' if disable_jit else 'UNCHANGED_PRODUCT_DEFAULT',
                       diagnostic_only=True, product_qualification=False, statement_timeout='8s',
                       Native_HTTP_timeout_changed=False)
    cur.execute('savepoint note_command_measurement')
    started = None
    try:
        cur.execute("set local statement_timeout='8s'")
        if disable_jit:
            cur.execute('set local jit=off')
        measurement['jit'] = cur.execute('show jit').fetchone()[0]
        cases.auth.actor(cur)
        started = monotonic()
        result = cur.execute('select public.erp_cp7_correct_note_v1(%s,%s,%s)',
                             (json.dumps(payload), key, version)).fetchone()[0]
        measurement.update(status='MEASURED', elapsed_ms=round((monotonic()-started)*1000))
        cases.b.api.admin(cur)
        current = dict(f, sale=result['sale_id'])
        document = cases.source.read(cur, current)['detail']
        assert cases.e01.physical(cur, current) == 49
        assert Decimal(document['financial']['net_total']) == 275
        assert Decimal(document['financial']['paid_total']) == 200
        assert Decimal(document['financial']['open_balance']) == 75
        measurement['actual_Native_stock49_net275_paid200_AR75'] = True
    except psycopg.Error as error:
        measurement.update(status='SQL_ERROR', elapsed_ms=round((monotonic()-started)*1000) if started else None,
                           sqlstate=error.sqlstate, error=error.diag.message_primary,
                           SQL_context=error.diag.context)
    finally:
        cur.execute('rollback to savepoint note_command_measurement')
        cur.execute('release savepoint note_command_measurement')
        cases.b.api.admin(cur)
        assert cases.snapshot(cur) == before, 'DIAGNOSTIC_NOTE_NATIVE_OR_PRIVATE_ROLLBACK_MISMATCH'
        measurement['exact_Native_and_private_rollback'] = True
    return measurement


def cases_provider(cur, today):
    def emission():
        measurements = []
        f = None
        for checkpoint in (1, 4):
            for _ in range(checkpoint - (0 if f is None else 1)):
                f = prepare(cur, today)
            key = uuid.uuid4()
            for disable_jit in (False, True):
                row = dict(actual_E01_fixtures=checkpoint, **measure(cur, f, disable_jit, key))
                measurements.append(row)
                print('CP7_NOTE_COMMAND_MEASUREMENT ' + json.dumps(row), flush=True)
        return dict(status='PASS', diagnostic_emission_and_exact_rollback_only=True,
                    product_qualification=False, Native_exit_case_credit=0, measurements=measurements)
    return [('NOTE_COMMAND_TIMING_AND_EXACT_ROLLBACK', emission)]
