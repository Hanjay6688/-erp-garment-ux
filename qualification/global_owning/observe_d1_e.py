"""Read Global completion and the original owning receipts before the inner rollback.

The owning Global caller must first admit its genuine parent/profile and verify
the installed state. Importing this adapter loads no product or DB client.
"""

from contextlib import contextmanager
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
import re
from types import FunctionType, SimpleNamespace
from uuid import UUID


SIGNED = 'scripts/cp7_customer_credit/reconciliation/native/cp7_ow04_signed_source_cases.py'
FACTORIES = {
    'scripts/cp7_credit_correction_de/cases.py': 'c530bb87f72ee6091e032d15efdb2b2e55cf9c9632b64c9e781665b70325bbdb',
    'scripts/cp7_credit_correction_de/e_cases.py': '058a9c29b991b30ca4da6467cfeb2629179d3ce8f25b8dba09d6ea45f419e2ad',
    SIGNED: '82831d767c85199ab182c21aa5a56fe46e7cba0c7e70ccba6c89477b755de640',
}
SIGNED_POSITIVES = {'OW04_SIGNED_RETURN_REVERSE_UNCONSUMED_CREDIT', 'OW04_SIGNED_PAYMENT_REVERSE_UNCONSUMED_CREDIT'}
OPERATIONS = {'D1', 'E', 'SOURCE'}
FIXTURE = 'scripts/cp7_customer_credit/native/cp7_ow04_native_source_fixture.py'
FIXTURE_SHA = '4984926b221df459e6e88c2f282da3e553d4810d177208ea489c9c3b1d264497'
POST_SEAL_DDL = {'D_ATOMIC_POST_FAILURE_RESTORE', 'E_NATIVE_POST_FAILURE_FULL_RESTORE'}

SNAPSHOT = """
select pg_backend_pid(), txid_current_if_assigned()::text,
       (select count(*) from cp7_global_nonpo_envelope.work_scopes_v1 w
        where w.backend_pid=pg_backend_pid() and w.transaction_id=txid_current_if_assigned())
"""
COMPLETIONS = """
select c.operation_id::text, to_jsonb(c)::text,
       case c.operation
         when 'D1' then to_jsonb(d)::text
         when 'E' then to_jsonb(e)::text
         when 'SOURCE' then jsonb_build_object('materialization',to_jsonb(s),'completion',to_jsonb(z))::text
       end,
       c.outside_before is not distinct from c.outside_after,
       case c.operation
         when 'D1' then (d.operation_id,d.actor,d.request_id,d.sale_id::text,d.payload,d.expected_version)
           = (c.operation_id,c.actor,c.request_id,c.native_binding->>'root_sale_id',
              c.native_binding->'payload',c.native_binding->>'expected_version')
         when 'E' then (e.operation_id,e.actor,e.request_id,e.source_sale_id::text,e.payload,e.expected_version)
           = (c.operation_id,c.actor,c.request_id,c.native_binding->>'root_sale_id',
              c.native_binding->'payload',c.native_binding->>'expected_version')
         when 'SOURCE' then z.operation_id=s.operation_id
           and (s.operation_id,s.actor,s.request_id,s.sale_id::text,s.payload,s.expected_version,
                s.backend_pid,s.transaction_id) = (c.operation_id,c.actor,c.request_id,c.native_binding->>'root_sale_id',
                c.native_binding->'payload',c.native_binding->>'expected_version',pg_backend_pid(),txid_current_if_assigned())
       end
from cp7_global_nonpo_envelope.scope_completions_v1 c
left join cp7_credit_correction_de.operations_v1 d on c.operation='D1' and d.operation_id=c.operation_id
left join cp7_credit_note_carry_de.operations_v1 e on c.operation='E' and e.operation_id=c.operation_id
left join cp7_credit.source_operation_materializations_v1 s on c.operation='SOURCE' and s.operation_id=c.operation_id
left join cp7_credit.source_operation_completions_v1 z on z.operation_id=s.operation_id
where c.proof->>'backend_pid'=pg_backend_pid()::text
  and c.proof->>'transaction_id'=txid_current_if_assigned()::text
order by c.operation_id
"""


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def capture(cur):
    connection = cur.connection
    require(connection.info.host in ('localhost', '127.0.0.1') and connection.info.port == 54322
            and connection.info.dbname == 'cp6_rollback' and not connection.autocommit,
            'GLOBAL_D1_E_OWNING_DISPOSABLE_TRANSACTION_REQUIRED')
    pid, xid, work = cur.execute(SNAPSHOT).fetchone()
    rows = [list(row) for row in cur.execute(COMPLETIONS).fetchall()]
    return dict(backend_pid=pid, transaction_id=xid, work_rows=work, rows=rows)


def checked_delta(before, after, profile_id, outside_conversion_id):
    require(before['backend_pid'] == after['backend_pid'] and before['work_rows'] == after['work_rows'] == 0
            and before['transaction_id'] in (None, after['transaction_id']),
            'GLOBAL_D1_E_SAME_TRANSACTION_AND_NO_WORK_LEAK_REQUIRED')
    old, new = ({row[0]: row for row in value['rows']} for value in (before, after))
    require(len(old) == len(before['rows']) and len(new) == len(after['rows'])
            and all(new.get(key) == row for key, row in old.items()),
            'GLOBAL_D1_E_EXISTING_COMPLETIONS_CHANGED')
    operations = []
    for key, (_, raw, native_raw, exact_outside, exact_owner) in new.items():
        if key in old:
            continue
        require(after['transaction_id'] is not None and type(native_raw) is str
                and exact_outside is True and exact_owner is True,
                'GLOBAL_D1_E_EXACT_OUTSIDE_AND_OWNING_RECEIPT_REQUIRED')
        row = json.loads(raw, parse_float=Decimal)
        binding = row['native_binding']
        proof = row['proof']
        outside = row['outside_before']
        require(row['operation'] in OPERATIONS and row['operation_id'] == key and row['profile_id'] == profile_id
                and all(binding[field] == row[field] for field in ('operation_id', 'operation', 'actor', 'request_id'))
                and proof['backend_pid'] == after['backend_pid'] and proof['transaction_id'] == after['transaction_id']
                and proof['same_actual_Native_owner_and_request'] is True
                and proof['outside_full_identity_and_facts_equal'] is True
                and proof['lock']['profile'] == profile_id and proof['lock']['all_acquisition_NOWAIT'] is True,
                'GLOBAL_D1_E_EXACT_OPERATION_PROFILE_AND_LOCK_REQUIRED')
        require(outside['classification'] == 'NEW_ACTUAL_OUTSIDE_GLOBAL_FACTS_NOT_NATIVE_SALE_SNAPSHOT'
                and outside['facts']['BE_context_rows'] == []
                and outside_conversion_id in outside['identity_domain']['conversion_ids']
                and [fact['status'] for fact in outside['facts']['conversions']
                     if fact['id'] == outside_conversion_id] == ['POSTED'],
                'GLOBAL_D1_E_COMMITTED_OUTSIDE_SKU_IDENTITY_REQUIRED')
        operations.append(row['operation'])
    return operations


def exact_function(function, path, expected_sha, name):
    require(path.is_file() and not path.is_symlink(), 'GLOBAL_D1_E_EXACT_SOURCE_FILE_REQUIRED:' + name)
    raw = path.read_bytes()
    require(sha256(raw).hexdigest() == expected_sha and Path(function.__code__.co_filename).resolve() == path,
            'GLOBAL_D1_E_EXACT_SOURCE_PIN_REQUIRED:' + name)
    code = [value for value in compile(raw, function.__code__.co_filename, 'exec', dont_inherit=True).co_consts
            if isinstance(value, type(function.__code__)) and value.co_name == name]
    require(code == [function.__code__], 'GLOBAL_D1_E_EXACT_ORIGINAL_CALLABLE_REQUIRED:' + name)


def bind(installer, parent_raw, profile_raw, state, root, factory, expected_operations, outside_conversion_id, *, retain):
    """Supply a strict-group factory through the actual Global admission first."""
    parent, profile = installer.admission.runtime_admission(parent_raw, profile_raw)
    profile_id = state['profile_id']
    require(state['contract'] == installer.CONTRACT and state['parent'] == parent and state['inputs'] == profile
            and re.fullmatch('[0-9a-f]{64}', profile_id), 'GLOBAL_D1_E_EXACT_INSTALLED_STATE_REQUIRED')
    require(type(outside_conversion_id) is str and str(UUID(outside_conversion_id)) == outside_conversion_id,
            'GLOBAL_D1_E_EXACT_PERSISTED_CONVERSION_ID_REQUIRED')
    root = Path(root).resolve()
    path = Path(factory.__globals__['__file__']).resolve()
    require(path.is_relative_to(root) and path.relative_to(root).as_posix() in FACTORIES,
            'GLOBAL_D1_E_OWNING_FACTORY_SOURCE_REQUIRED')
    relative = path.relative_to(root).as_posix()
    exact_function(factory, path, FACTORIES[relative], 'cases')
    ids = factory.__globals__['IDS']
    native = factory.__globals__['native']
    fixture_path = Path(native.__file__).resolve()
    require(fixture_path.as_posix().endswith('/' + FIXTURE), 'GLOBAL_D1_E_EXACT_IMPORTED_FIXTURE_ROUTE_REQUIRED')
    exact_function(native.isolated.__wrapped__, fixture_path, FIXTURE_SHA, 'isolated')
    expected = dict(expected_operations)
    allowed = SIGNED_POSITIVES if relative == SIGNED else set(ids) - POST_SEAL_DDL
    require(expected and set(expected) <= allowed
            and all(isinstance(operations, tuple) and set(operations) <= OPERATIONS for operations in expected.values()),
            'GLOBAL_D1_E_REVIEWED_CASES_WITHOUT_POST_SEAL_DDL_REQUIRED')
    signed_positive = None
    if relative == SIGNED:
        signed_positive = factory.__globals__['_positive']
        exact_function(signed_positive, path, FACTORIES[relative], '_positive')
    require(callable(retain), 'GLOBAL_D1_E_EXACT_OWNING_ORIGINAL_WRITER_REQUIRED')

    def cases(cur, today):
        observations = []

        @contextmanager
        def observed_isolation(cursor):
            with native.isolated(cursor):
                before = capture(cursor)
                yield
                observations.append(dict(before=before, after=capture(cursor)))

        private_native = SimpleNamespace(**(vars(native) | {'isolated': observed_isolation}))
        namespace = dict(factory.__globals__, native=private_native)
        if signed_positive is not None:
            namespace['_positive'] = FunctionType(signed_positive.__code__, namespace)
        original = FunctionType(factory.__code__, namespace)
        registered = original(cur, today)
        require(tuple(name for name, _ in registered) == ids,
                'GLOBAL_D1_E_EXACT_REGISTERED_NATIVE_CASES_REQUIRED')

        def observed(name, operation):
            def run():
                try:
                    result = operation()
                except Exception as error:
                    if observations:
                        try:
                            retain(name, dict(case_id=name, observations=observations))
                        except Exception as write_error:
                            error.add_note('Global observation sidecar: ' + str(write_error))
                    raise
                finally:
                    spans = list(observations)
                    observations.clear()
                if not isinstance(result, dict) or result.get('status') != 'PASS':
                    return result
                original = retain(name, dict(case_id=name, observations=spans))
                try:
                    require(type(original) is dict and type(original.get('bytes')) is int
                            and original['bytes'] > 0 and isinstance(original.get('name'), str)
                            and re.fullmatch('[0-9a-f]{64}', original.get('sha256', '')),
                            'GLOBAL_D1_E_EXACT_ORIGINAL_SIDECAR_PIN_REQUIRED')
                    require(spans, 'GLOBAL_D1_E_INNER_SAVEPOINT_OBSERVATION_REQUIRED')
                    actual = [operation for span in spans
                              for operation in checked_delta(span['before'], span['after'], profile_id,
                                                             outside_conversion_id)]
                    require(sorted(actual) == sorted(expected[name]), 'GLOBAL_D1_E_EXACT_COMPLETION_COUNT_REQUIRED')
                except (ValueError, KeyError, TypeError) as error:
                    return dict(result, status='INCOMPLETE', native_case_status='PASS',
                                first_global_observation_error=str(error), Global_completion_original=original)
                return dict(result, Global_completion_original=original, Global_completion_operations=actual)
            return run

        return [(name, observed(name, operation)) for name, operation in registered if name in expected]

    return cases
