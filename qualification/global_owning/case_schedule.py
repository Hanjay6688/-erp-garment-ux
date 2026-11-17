"""Compose the existing case callbacks for one installed and restored Global database."""

from inspect import signature
from pathlib import Path
import re
from types import SimpleNamespace

from .lifecycle import CASE_COUNTS
from .package_routes import require


TRANSFER = 'OW06_TRANSFER_PAGE_25_TO_26'
TRANSFER_RESULT = TRANSFER + '_OBSERVED_PENDING_OWNING_RESTORE_AND_GATES'
CASE = 'GLOBAL_ORDINARY_NATIVE_TRANSFER_AND_HTTP'


def bind_transfer(page, *, lifecycle, state, verify, trusted_connection, require_quiet, retain):
    require(page.CASE == TRANSFER, 'GLOBAL_FIXTURE_EXACT_ORDINARY_TRANSFER_PAGE_REQUIRED')
    return page.exercise(provider=lifecycle.provider, parent_raw=lifecycle.parent_raw,
                         profile_raw=lifecycle.profile_raw, state=state, verify=verify,
                         trusted_connection=trusted_connection, require_quiet=require_quiet, retain=retain)


def case_original(value, label):
    require(type(value) is dict and value.keys() == {'name', 'bytes', 'sha256'}
            and value.get('name') == label + '.json'
            and type(value.get('bytes')) is int and value['bytes'] > 0
            and type(value.get('sha256')) is str and re.fullmatch('[a-f0-9]{64}', value['sha256']),
            'GLOBAL_FIXTURE_EXACT_PRIVATE_ORIGINAL_REQUIRED:' + label)


def transfer_observation(value):
    require(type(value) is dict and value.get('status') == TRANSFER_RESULT
            and type(value.get('actual_case_credit')) is int and value['actual_case_credit'] == 0
            and value.get('production_go') is False, 'GLOBAL_FIXTURE_TRANSFER_PENDING_OUTER_RESTORE_REQUIRED')
    prefix = 'GLOBAL_' + TRANSFER + '_'
    case_original(value.get('setup'), prefix + 'SETUP')
    terminals = value.get('terminals')
    require(type(terminals) is dict and tuple(terminals) == ('ABORT', 'COMMIT'),
            'GLOBAL_FIXTURE_BOTH_ORDERED_TRANSFER_TERMINALS_REQUIRED')
    backends = []
    for terminal, case in terminals.items():
        require(type(case) is dict, 'GLOBAL_FIXTURE_EXACT_TRANSFER_TERMINAL_REQUIRED:' + terminal)
        case_original(case.get('original'), prefix + terminal)
        for key in ('reader_pid', 'writer_pid'):
            pid = case.get(key)
            require(type(pid) is int and pid > 0, 'GLOBAL_FIXTURE_EXACT_TRANSFER_BACKEND_REQUIRED')
            backends.append(pid)
    require(len(set(backends)) == 4, 'GLOBAL_FIXTURE_DISTINCT_TRANSFER_TERMINAL_BACKENDS_REQUIRED')
    return dict(value, status='PASS', observation_status=TRANSFER_RESULT)


def checked_cases(cases, ids, group):
    require(type(cases) is dict and tuple(cases) == ids
            and all(type(case) is dict and case.get('status') == 'PASS' for case in cases.values()),
            'GLOBAL_FIXTURE_EXACT_PASSED_CASES_REQUIRED:' + group)
    return cases


def bind(ordinary, transfer, *, lifecycle, attempt, http_ids, http, db_scheduler, trusted_connection,
         output, originals, observe_scope=None):
    """Keep Native, one allowed race and the reviewed HTTP callbacks in one setup."""
    native_ids = tuple(ordinary.proof['native_case_ids'])
    plan = dict(native=native_ids, races=(TRANSFER,), http=http_ids, browser=())
    keys = (*native_ids, TRANSFER, *http_ids)
    require(plan.keys() == CASE_COUNTS.keys() and len(native_ids) == 17
            and type(http_ids) is tuple and bool(http_ids)
            and all(type(key) is str and re.fullmatch('[A-Z0-9_]+', key) for key in keys)
            and len(keys) == len(set(keys)), 'GLOBAL_FIXTURE_EXACT_SCOPED_CASE_IDS_REQUIRED')
    signature(http.prepare).bind(attempt, verify=object(), require_quiet=object(), retain=object())
    signature(http.exercise).bind(attempt, conn=object(), cur=object(), state=object(), verify=object(),
                                  report=object(), require_quiet=object(), outside_id=object(), retain=object())
    require(transfer.CASE == TRANSFER, 'GLOBAL_FIXTURE_EXACT_ORDINARY_TRANSFER_PAGE_REQUIRED')
    signature(transfer.exercise).bind(provider=object(), parent_raw=b'', profile_raw=b'', state=object(),
                                      verify=object(), trusted_connection=object(), require_quiet=object(),
                                      retain=object())
    output = Path(output)

    def retain(name, value):
        require(type(name) is str and re.fullmatch(r'GLOBAL_[A-Z0-9_]+', name),
                'GLOBAL_FIXTURE_PRIVATE_CASE_ORIGINAL_NAME_REQUIRED')
        output.mkdir(parents=True, exist_ok=True)
        return originals.save_sorted(output / (name + '.json'), value, 'GLOBAL_FIXTURE_PRIVATE_ORIGINAL_CONFLICT')

    started = False

    def exercise(conn, cur, database, url, report, state, verify, observe_native, require_quiet):
        nonlocal started
        require(not started, 'GLOBAL_FIXTURE_ONE_CASE_SCHEDULE_ATTEMPT_REQUIRED')
        require_quiet()
        require(attempt.phase == 'ACTIVE' and not attempt.verified_actors and not attempt.application_rpc_responses,
                'GLOBAL_FIXTURE_FRESH_OWNING_AUTH_ATTEMPT_REQUIRED')
        require(db_scheduler(url) is True, 'GLOBAL_FIXTURE_QUIET_DATED_DATABASE_REQUIRED')
        require_quiet()
        started = True
        report.update(status='INCOMPLETE', business_cases={})
        cases = report['business_cases']
        lanes = ordinary.make_lanes(lifecycle, state, verify=verify, trusted_connection=trusted_connection,
                                    output=output, originals=originals)

        def record_scope(label):
            if observe_scope is not None:
                observe_scope(label, conn, cur, report, require_quiet)

        # The historical S05 period must still be open before the retained committed E fixture.
        record_scope('START')
        report['pre_Native_http_fixture'] = dict(status='INCOMPLETE')
        report['pre_Native_http_fixture'] = http.prepare(attempt, verify=verify, require_quiet=require_quiet,
                                                        retain=retain)
        record_scope('S05_SETUP')
        dispatched = False

        def consumers(outside_id):
            nonlocal dispatched
            require(not dispatched, 'GLOBAL_FIXTURE_ONE_OUTSIDE_CONSUMER_ATTEMPT_REQUIRED')
            dispatched = True
            require_quiet()
            record_scope('NATIVE_AND_COMMITTED_E')
            # Complete independent Native/race sessions before login starts the REST pool.
            report['transfer_page'] = dict(status='INCOMPLETE')
            observation = bind_transfer(transfer, lifecycle=lifecycle, state=state, verify=verify,
                                        trusted_connection=trusted_connection, require_quiet=require_quiet,
                                        retain=retain)
            report['transfer_page'] = observation
            cases[TRANSFER] = transfer_observation(observation)
            record_scope('OW06_TRANSFER')
            require_quiet()
            responses = report['HTTP_case_results'] = {}
            http.exercise(attempt, conn=conn, cur=cur, state=state, verify=verify, report=responses,
                          require_quiet=require_quiet, outside_id=outside_id, retain=retain)
            require(attempt.phase == 'ACTIVE' and attempt.rest_verified
                    and attempt.verified_actors == len(attempt.allowed_actors)
                    and attempt.application_rpc_responses >= len(http_ids),
                    'GLOBAL_FIXTURE_REAL_HTTP_OBSERVATIONS_REQUIRED')
            cases.update(checked_cases(responses, http_ids, 'http'))
            record_scope('AUTH_ORDINARY')
            require_quiet()

        native = ordinary.run_native(lanes, conn, cur, report, observe_native=observe_native,
                                     require_quiet=require_quiet, before_outside_inverse=consumers)
        record_scope('OUTSIDE_REVERSE_AND_STALE')
        require(dispatched and native.get('used_guard_refused_before_DDL') is True,
                'GLOBAL_FIXTURE_NATIVE_USED_REFUSAL_AND_CONSUMERS_REQUIRED')
        native_cases = checked_cases(native.get('business_cases'), native_ids, 'native')
        require(tuple(cases) == (TRANSFER, *http_ids), 'GLOBAL_FIXTURE_ALL_PLANNED_LANES_REQUIRED')
        report.update(status='PASS', used_guard_refused_before_DDL=True, business_cases=native_cases | cases)
        return report

    return SimpleNamespace(CASE=CASE, CASE_IDS=plan, exercise=exercise, capture_advisors=ordinary.advisors.capture,
                           review_advisors=ordinary.advisors.review)
