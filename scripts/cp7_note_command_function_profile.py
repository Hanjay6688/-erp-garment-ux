"""Validate actual transaction-local PostgreSQL function counters.

This module neither queries nor changes a database. Its caller retains both
unaltered counter arrays. Inclusive function times must never be added together:
parent times already include children. These are elapsed times, not CPU samples,
and a diagnostic profile grants no Native product or performance exit credit.
"""
from decimal import Decimal, InvalidOperation
import re

MAX_FUNCTIONS = 1000
FIELDS = frozenset(('function_oid', 'schema_name', 'function_name',
                    'identity_arguments', 'calls', 'total_time_ms', 'self_time_ms'))
INTEGER = re.compile(r'(?:0|[1-9][0-9]*)\Z')


def instrument_admission(control, target):
    """Admit only the existing local maintenance identity on the HTTP copy.

    Conninfo is parsed by psycopg in the actual caller. Neither connection map
    nor any password is returned or attached to a failure. Server identity and
    existing superuser authority still require a separate actual SQL check.
    """
    if not isinstance(control, dict) or not isinstance(target, dict):
        raise ValueError('PROFILE_INSTALL_CLOSED_CONNINFO_REQUIRED')
    if control.get('user') != 'cp6_maintenance_admission' or control.get('dbname') != 'template1':
        raise ValueError('PROFILE_INSTALL_EXISTING_MAINTENANCE_ONLY')
    if target.get('dbname') != 'cp6_auditor_http':
        raise ValueError('PROFILE_INSTALL_DISPOSABLE_HTTP_ONLY')
    if control.get('host') not in ('localhost', '127.0.0.1') or target.get('host') != control['host']:
        raise ValueError('PROFILE_INSTALL_SAME_LOCAL_HOST_ONLY')
    port = control.get('port')
    if not isinstance(port, str) or INTEGER.fullmatch(port) is None or not 1 <= int(port) <= 65535 or \
            target.get('port') != port:
        raise ValueError('PROFILE_INSTALL_SAME_EXPLICIT_PORT_ONLY')
    return dict(database='cp6_auditor_http', installer_role='cp6_maintenance_admission',
                host=control['host'], port=port, existing_authority_only=True,
                connection_strings_or_passwords_emitted=False)


def _integer(value, label, positive=False):
    if not isinstance(value, str) or INTEGER.fullmatch(value) is None:
        raise ValueError('PROFILE_INVALID_' + label)
    number = int(value)
    if positive and number == 0:
        raise ValueError('PROFILE_INVALID_' + label)
    return number


def _time(value):
    if not isinstance(value, str):
        raise ValueError('PROFILE_INVALID_TIME')
    try:
        number = Decimal(value)
    except InvalidOperation as error:
        raise ValueError('PROFILE_INVALID_TIME') from error
    if not number.is_finite() or number < 0:
        raise ValueError('PROFILE_INVALID_TIME')
    return number


def _rows(raw):
    if not isinstance(raw, list) or len(raw) > MAX_FUNCTIONS:
        raise ValueError('PROFILE_INVALID_OR_OVER_CAP_ROWS')
    indexed = {}
    for row in raw:
        if not isinstance(row, dict) or frozenset(row) != FIELDS:
            raise ValueError('PROFILE_INVALID_FIELDS')
        oid = _integer(row['function_oid'], 'OID', positive=True)
        if oid in indexed:
            raise ValueError('PROFILE_DUPLICATE_OID')
        schema, name, arguments = (row[k] for k in
                                   ('schema_name', 'function_name', 'identity_arguments'))
        if not all(isinstance(v, str) for v in (schema, name, arguments)) or not name:
            raise ValueError('PROFILE_INVALID_IDENTITY')
        if not (schema == 'erp' or schema.startswith('cp7_') or
                (schema == 'public' and name == 'erp_cp7_correct_note_v1')):
            raise ValueError('PROFILE_OUT_OF_SCOPE_FUNCTION')
        calls = _integer(row['calls'], 'CALLS')
        total, own = _time(row['total_time_ms']), _time(row['self_time_ms'])
        if own > total:
            raise ValueError('PROFILE_SELF_EXCEEDS_TOTAL')
        indexed[oid] = (schema, name, arguments, calls, total, own)
    return indexed


def summarize(before, after, root_oid, *, command_completed):
    """Return validated deltas; incomplete command counters stay explicitly partial."""
    if not isinstance(command_completed, bool):
        raise ValueError('PROFILE_COMMAND_COMPLETION_REQUIRED')
    root = _integer(root_oid, 'ROOT_OID', positive=True)
    old, new = _rows(before), _rows(after)
    if old.keys() - new.keys():
        raise ValueError('PROFILE_COUNTER_DISAPPEARED')
    deltas = []
    for oid, values in new.items():
        previous = old.get(oid, (*values[:3], 0, Decimal(0), Decimal(0)))
        if values[:3] != previous[:3]:
            raise ValueError('PROFILE_IDENTITY_CHANGED')
        calls, total, own = (values[i] - previous[i] for i in (3, 4, 5))
        if calls < 0 or total < 0 or own < 0:
            raise ValueError('PROFILE_COUNTER_RESET_OR_NEGATIVE_DELTA')
        if own > total:
            raise ValueError('PROFILE_SELF_DELTA_EXCEEDS_TOTAL')
        deltas.append(dict(function_oid=str(oid), schema_name=values[0],
                           function_name=values[1], identity_arguments=values[2],
                           delta_calls=str(calls), delta_total_time_ms=str(total),
                           delta_self_time_ms=str(own)))
    root_rows = [row for row in deltas if row['function_oid'] == str(root)]
    if root_rows and (root_rows[0]['schema_name'], root_rows[0]['function_name']) != (
            'public', 'erp_cp7_correct_note_v1'):
        raise ValueError('PROFILE_ROOT_IDENTITY_MISMATCH')
    if command_completed and (len(root_rows) != 1 or root_rows[0]['delta_calls'] != '1'):
        raise ValueError('PROFILE_COMPLETED_ROOT_NOT_EXACTLY_ONCE')
    deltas.sort(key=lambda row: (-Decimal(row['delta_self_time_ms']),
                                int(row['function_oid'])))
    return dict(status='COMPLETED_COMMAND_FUNCTION_COUNTERS' if command_completed else
                'PARTIAL_COUNTERS_COMMAND_NOT_COMPLETED',
                scope='CURRENT_TRANSACTION_COMPLETED_TRACKED_NONINLINED_FUNCTION_CALLS',
                counter_source='pg_catalog.pg_stat_xact_user_functions',
                command_completed=command_completed, function_count=len(deltas),
                root_function_oid=str(root), root_function_delta=root_rows[0] if root_rows else None,
                functions_by_self_elapsed_ms=deltas, inclusive_times_not_summed=True,
                timings_are_elapsed_not_CPU=True, one_profile_does_not_establish_cause=True,
                diagnostic_only=True, product_qualification=False, Native_exit_case_credit=0)
