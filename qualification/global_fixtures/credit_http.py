"""Run the four ordinary D1/E cases through the caller's owned Auth attempt."""

from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import re
from types import FunctionType
from uuid import uuid4

import auth_case_plan as plan
import payload_routes


CASE_IDS = plan.HTTP_CASE_IDS[:4]
WIRE = 'scripts/cp6_auditor_modes.py'
WIRE_SHA = 'd927c7491c72fe1eecfd1b4b8b4faf7e1710d6943fda601ede6a599fbc99209f'
ERROR_SOURCE = 'scripts/current-mandor-shop-native-qualification/http_cases.py'
ERROR_SHA = '5c89a262a21d6e21d33b0287cb7861dd6ce707294ab510cad62ca471a9ccf414'
ACCESS_TABLE = 'erp.app_role_permissions'


@dataclass(frozen=True)
class Route:
    operation: str
    good: str
    denied: str
    command: str
    contract: str
    action: str
    changed_error: str
    denied_error: str
    changed_path: tuple[str, ...]
    changed_key: str
    changed_value: str


ROUTES = (
    Route('D1', CASE_IDS[0], CASE_IDS[2], plan.D1_COMMAND_RPC, 'cp7.sales-return-correction.v1', 'RETURN_CORRECT',
          'CP7_RETURN_CORRECTION_REQUEST_CHANGED', 'CP7_RETURN_CORRECTION_DENIED',
          ('replacement', 'items'), 'refund_amount', '250.01'),
    Route('E', CASE_IDS[1], CASE_IDS[3], plan.E_COMMAND_RPC, 'cp7.note-correction-outcome.v1', 'CORRECT',
          'CP7_NOTE_REQUEST_CHANGED', 'CP7_NOTE_ACCESS_DENIED',
          ('items',), 'unit_price_snapshot', '111.00'),
)


def require(value, reason):
    if not value:
        raise ValueError('GLOBAL_AUTH_CREDIT_HTTP_' + reason)


def fixed_source(root, relative, digest):
    path = Path(root).absolute() / relative
    require(path.is_file() and not any(part.is_symlink() for part in (path, *path.parents)), 'REGULAR_SOURCE_REQUIRED')
    raw = path.read_bytes()
    require(sha256(raw).hexdigest() == digest, 'EXACT_RETAINED_SOURCE_REQUIRED:' + relative)
    return path, raw


def is_uuid(value):
    return type(value) is str and re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', value) is not None


def matches_attempt(value, attempt):
    require(type(value) is dict and value.get('application_oid') == attempt.app[1]
            and value.get('cluster_system_id') == attempt.app[2], 'EXACT_OWNING_APPLICATION_REQUIRED')


def changed_intent(route, args):
    changed = deepcopy(args)
    items = changed['p_payload']
    for name in route.changed_path:
        items = items[name]
    require(type(items) is list and len(items) == 1 and route.changed_key in items[0]
            and items[0][route.changed_key] != route.changed_value, 'EXACT_RETAINED_CHANGED_INTENT_REQUIRED')
    items[0][route.changed_key] = route.changed_value
    return changed


def check_arguments(route, prepared_case, args, request):
    require(type(args) is dict and args.keys() == {'p_payload', 'p_request', 'p_expected'}
            and args['p_request'] == request and type(args['p_expected']) is str and bool(args['p_expected'])
            and type(args['p_payload']) is dict and args['p_payload'].get('sale_id') == prepared_case.sale_id,
            'EXACT_REVIEWED_COMMAND_REQUIRED')
    if route.operation == 'D1':
        require(args['p_payload'].get('return_id') == prepared_case.return_id, 'EXACT_REVIEWED_D1_RETURN_REQUIRED')


def check_outcome(route, prepared_case, body, request):
    require(body.get('kind') == 'COMMITTED_OUTCOME' and body.get('action') == route.action
            and body.get('contract_version') == route.contract and body.get('request_id') == request,
            'EXACT_COMMITTED_OUTCOME_REQUIRED')
    if route.operation == 'D1':
        require(body.get('sale_id') == prepared_case.sale_id
                and body.get('original_return_id') == prepared_case.return_id and body.get('original_return_status') == 'REVERSED'
                and body.get('return_status') == 'POSTED'
                and is_uuid(body.get('return_id')) and body['return_id'] != prepared_case.return_id,
                'EXACT_D1_REPLACEMENT_REQUIRED')
    else:
        require(body.get('previous_sale_id') == prepared_case.sale_id and is_uuid(body.get('sale_id'))
                and body['sale_id'] != prepared_case.sale_id and is_uuid(body.get('revision_id')),
                'EXACT_E_REPLACEMENT_REQUIRED')


def check_completion(route, before, after, oracle, request, actor_uid, profile_id, response):
    previous, current = before['completions'], after['completions']
    name = route.operation + '_operations'
    other = 'E_operations' if route.operation == 'D1' else 'D1_operations'
    operation_id = oracle.get('operation_id')
    require(is_uuid(operation_id) and type(oracle.get('native_profile')) is dict
            and after['fixtures'] == before['fixtures'] and current['pending_Global_work'] == 0
            and current[other] == previous[other], 'EXACT_ONE_COMMITTED_CREDIT_EFFECT_REQUIRED')
    added = {}
    for group in ('scope_completions', name):
        original = {item['operation_id']: item for item in previous[group]}
        terminal = {item['operation_id']: item for item in current[group]}
        require(operation_id not in original and terminal.keys() == original.keys() | {operation_id}
                and all(terminal[key] == row for key, row in original.items()), 'EXACT_IMMUTABLE_COMPLETION_APPEND_REQUIRED')
        added[group] = terminal[operation_id]
        require(added[group]['actor'] == actor_uid and added[group]['request_id'] == request,
                'EXACT_COMMITTED_ACTOR_AND_REQUEST_REQUIRED')
    require(added['scope_completions']['profile_id'] == profile_id
            and added['scope_completions']['operation'] == route.operation and added[name]['response'] == response,
            'EXACT_COMMITTED_PROFILE_AND_RESPONSE_REQUIRED')


def retained_reply_checkers(candidate):
    fixed_source(candidate, WIRE, WIRE_SHA)
    location, raw = fixed_source(candidate, ERROR_SOURCE, ERROR_SHA)

    def quiet_require(value, _untrusted_message):
        require(value, 'RETAINED_REPLY_ORACLE_REFUSED')

    safe_builtins = dict(type=type, dict=dict, int=int, str=str)
    private = dict(__builtins__=safe_builtins, require=quiet_require)
    ok = FunctionType(payload_routes.original_function(raw, location, 'ok',
                      {'require', 'get', 'type', 'dict', 'str'}), private)
    denied = FunctionType(payload_routes.original_function(raw, location, 'denied',
                          {'require', 'type', 'get', 'int', 'dict', 'str'}), private)
    return ok, denied


@contextmanager
def authorized_window(permission_window, access):
    """Make the caller restore its window on errors and propagate the first failure."""
    original = None
    try:
        with permission_window(deepcopy(access)):
            try:
                yield
            except BaseException as error:
                original = error
                raise
    except BaseException as recovery:
        if original is not None and recovery is not original:
            raise original from recovery
        raise
    if original is not None:
        raise original


def bind(candidate):
    """Resolve the exact source once. The returned lane consumes only owner-bound objects."""
    payloads = payload_routes.bind(candidate)
    ok, denied = retained_reply_checkers(candidate)
    started = False

    def exercise(attempt, *, admin, source_identity, conn, cur, prepared, native, verify, profile_id, outside_id,
                 capture_scope, permission_window, report, require_quiet, retain, during_revocation=None):
        nonlocal started
        plan.check_attempt(attempt, source_identity)
        require(not started and attempt.phase == 'ACTIVE' and attempt.rest_verified is True
                and admin.role == 'ADMIN' and any(admin is item for item in attempt._actors),
                'ACTIVE_OWNED_ADMIN_AND_SINGLE_LANE_REQUIRED')
        require(type(profile_id) is str and re.fullmatch('[a-f0-9]{64}', profile_id)
                and is_uuid(outside_id) and type(report) is dict and not set(CASE_IDS) & report.keys()
                and callable(permission_window) and (during_revocation is None or callable(during_revocation)),
                'EXACT_OWNING_LANE_INPUT_REQUIRED')
        matches_attempt(prepared.report, attempt)
        require(prepared.report.get('status') == 'COMMITTED_FIXTURES', 'EXACT_COMMITTED_FIXTURE_BATCH_REQUIRED')
        require(set(prepared.cases) == set(CASE_IDS), 'EXACT_FOUR_PREPARED_CREDIT_PAIRS_REQUIRED')
        cases = prepared.cases
        for key in CASE_IDS:
            case = cases[key]
            operation = 'D1' if key.startswith('GLOBAL_AUTH_D1_') else 'E'
            require(case.case_id == key and case.operation == operation
                    and is_uuid(case.sale_id) and case.sale_id != outside_id and is_uuid(case.apply_event_id)
                    and is_uuid(case.apply_operation_id)
                    and is_uuid(case.return_id),
                    'EXACT_PREPARED_CREDIT_IDENTITIES_REQUIRED')
        for field in ('sale_id', 'return_id', 'apply_event_id', 'apply_operation_id'):
            require(len({getattr(cases[key], field) for key in CASE_IDS}) == len(CASE_IDS), 'PREPARED_CREDIT_PAIR_REUSED')

        require_quiet()
        started = True
        app, issuer = attempt.app, attempt.issuer
        phase = 'ADMIN_BEFORE'
        originals = {}

        def step(name, **data):
            original = 'GLOBAL_AUTH_CREDIT_HTTP_' + name
            originals[name] = retain(original, dict(attempt=attempt.attempt, qualification_commit=attempt.head,
                                                    application_oid=app[1], cluster_system_id=app[2], **deepcopy(data)))
            return originals[name]

        def access():
            require_quiet()
            require(attempt.app == app and attempt.issuer == issuer, 'OWNED_AUTH_DATABASE_CHANGED')
            result = plan.observe_access(attempt, admin)
            require_quiet()
            return result

        def observe():
            require_quiet()
            current = native.observe(conn, cur, attempt=attempt, verify=verify, prepared=prepared, capture_scope=capture_scope)
            require_quiet()
            matches_attempt(current, attempt)
            scope = current.get('scope')
            require(type(scope) is dict and {ACCESS_TABLE, 'erp.sales_headers', 'sequence:erp.audit_logs_id_seq',
                    'sequence:erp.fg_stock_book_order_seq'} <= scope.keys(),
                    'EXACT_FULL_ROWS_AND_SEQUENCES_REQUIRED')
            completions = current.get('completions')
            require(type(completions) is dict and completions.get('pending_Global_work') == 0
                    and all(type(completions.get(key)) is list for key in ('scope_completions', 'D1_operations', 'E_operations')),
                    'EXACT_QUIESCENT_COMPLETION_CENSUS_REQUIRED')
            return deepcopy(current)

        def rpc(stage, name, arguments):
            require(name in (plan.D1_REVIEW_RPC, plan.D1_COMMAND_RPC, plan.E_REVIEW_RPC, plan.E_COMMAND_RPC)
                    and attempt.phase == 'ACTIVE' and attempt.app == app and attempt.issuer == issuer,
                    'EXACT_D1_E_RPC_NAMESPACE_REQUIRED')
            require_quiet()
            reply = admin.rpc(name, deepcopy(arguments))
            require_quiet()
            original = step(stage, rpc=name, args=arguments, reply=reply)
            require(type(reply) is dict and type(reply.get('status')) is int and type(reply.get('body')) is dict,
                    'EXACT_RETAINED_REPLY_SHAPE_REQUIRED')
            return reply, original

        def review(route, case):
            request = str(uuid4())
            index = 0

            def read(name, arguments):
                nonlocal index
                index += 1
                reply, _ = rpc(phase + '_RPC_' + str(index), name, arguments)
                return reply

            if route.operation == 'D1':
                args, proof = payloads.d1(read, sale_id=case.sale_id, return_id=case.return_id, request_id=request)
            else:
                args, proof = payloads.e(read, sale_id=case.sale_id, request_id=request)
            check_arguments(route, case, args, request)
            return args, proof

        def expect_denial(reply, *, status, message, code):
            denied(reply, message, code)
            require(reply['status'] == status, 'EXACT_HTTP_DENIAL_STATUS_REQUIRED')
            return dict(http_status=status, sqlstate=reply['body']['code'], message=reply['body']['message'])

        def unchanged(expected):
            require(observe() == expected, 'COMPLETE_NATIVE_STATE_CHANGED')

        accepted = {}
        rejected_intents = {}
        pending_denials = {}
        try:
            initial_access = access()
            plan.require_permissions(initial_access, plan.D1_PERMISSIONS | plan.E_PERMISSIONS)
            access_before_original = step('ADMIN_BEFORE', access=initial_access)
            for route in ROUTES:
                case = cases[route.good]
                phase = route.operation + '_FRESH_REVIEW'
                before = observe()
                args, proof = review(route, case)
                request = args['p_request']
                unchanged(before)
                review_original = step(phase, command_args=args, review=proof, observation=before)

                phase = route.operation + '_FRESH_COMMIT'
                first, fresh_original = rpc(phase, route.command, args)
                body = ok(first)
                check_outcome(route, case, body, request)
                held = observe()
                require(held != before and held['completions'] != before['completions'], 'COMMITTED_EFFECT_NOT_OBSERVED')
                matches_attempt(held, attempt)
                oracle = native.verify_success(conn, cur, attempt=attempt, verify=verify, prepared_case=case,
                    response=deepcopy(body), request_id=request, actor_uid=initial_access['auth_uid'],
                    profile_id=profile_id, outside_id=outside_id)
                require_quiet()
                matches_attempt(oracle, attempt)
                require(all(oracle.get(key) is True for key in ('exact_native_and_global_completion', 'outside_unchanged',
                            'original_apply_unchanged')), 'EXACT_NATIVE_AND_GLOBAL_COMPLETION_REQUIRED')
                check_completion(route, before, held, oracle, request, initial_access['auth_uid'], profile_id, body)
                oracle_original = step(route.operation + '_FRESH_ORACLE', oracle=oracle, observation=held)

                phase = route.operation + '_EXACT_REPLAY'
                replay, replay_original = rpc(phase, route.command, args)
                require(ok(replay) == body and replay['status'] == first['status'], 'CACHED_REPLY_CHANGED')
                unchanged(held)

                phase = route.operation + '_CHANGED_INTENT'
                changed_args = changed_intent(route, args)
                changed, changed_original = rpc(phase, route.command, changed_args)
                changed_proof = expect_denial(changed, status=400, message=route.changed_error, code='P0001')
                unchanged(held)
                require(plan.compare_access(initial_access, access()) == {'lost': [], 'added': []}, 'ADMIN_ACCESS_DRIFT')
                report[route.good] = dict(status='PASS', request_id=request, originals={
                    'access': access_before_original, 'review': review_original, 'fresh': fresh_original,
                    'committed_oracle': oracle_original, 'replay': replay_original, 'changed_intent': changed_original},
                    changed_intent_denial=changed_proof, exact_replay_no_effect=True, changed_intent_no_effect=True)
                accepted[route.operation] = args

            phase = 'BEFORE_PERMISSION_WINDOW'
            pre_window = observe()
            for route in ROUTES:
                phase = route.operation + '_DENIAL_REVIEW'
                args, proof = review(route, cases[route.denied])
                require(args['p_request'] != accepted[route.operation]['p_request'], 'DENIAL_MUST_USE_UNSEEN_UUID')
                step(phase, command_args=args, review=proof)
                rejected_intents[route.operation] = args
            requests = [replacement['p_request'] for replacement in (*accepted.values(), *rejected_intents.values())]
            require(len(set(requests)) == len(CASE_IDS), 'SAME_CASE_UUID_REUSED')
            unchanged(pre_window)
            phase = 'ENTER_PERMISSION_WINDOW'
            with authorized_window(permission_window, initial_access):
                revoked_access = access()
                effective = plan.compare_access(initial_access, revoked_access, lost=(plan.REVOKED_PERMISSION,))
                revoked = observe()
                scope_before, scope_after = pre_window['scope'], revoked['scope']
                require(scope_before.keys() == scope_after.keys()
                        and {key for key, value in scope_before.items() if value != scope_after[key]} == {ACCESS_TABLE}
                        and {key: value for key, value in pre_window.items() if key != 'scope'}
                        == {key: value for key, value in revoked.items() if key != 'scope'},
                        'EXACT_ADMIN_PERMISSION_MAPPING_ONLY_REQUIRED')
                window_original = step('PERMISSION_REVOKED', access=revoked_access, effective=effective, observation=revoked)
                for route in ROUTES:
                    proofs = {}
                    for label, args in (('FRESH', rejected_intents[route.operation]), ('CACHED', accepted[route.operation])):
                        phase = route.operation + '_REVOKED_' + label
                        reply, original = rpc(phase, route.command, args)
                        proof = expect_denial(reply, status=403, message=route.denied_error, code='42501')
                        unchanged(revoked)
                        proofs[label.lower()] = dict(request_id=args['p_request'], denial=proof, original=original)
                    if route.operation == 'E':
                        phase = 'E_REVOKED_REVIEW'
                        reply, original = rpc(phase, plan.E_REVIEW_RPC, {'p_sale': cases[route.denied].sale_id})
                        proof = expect_denial(reply, status=403, message=route.denied_error, code='42501')
                        unchanged(revoked)
                        proofs['workspace'] = dict(denial=proof, original=original)
                    pending_denials[route.denied] = proofs
                if during_revocation is not None:
                    phase = 'ADDITIONAL_ORDINARY_ACCESS_DURING_REVOCATION'
                    require_quiet()
                    during_revocation(admin, deepcopy(revoked_access))
                    require_quiet()
                    unchanged(revoked)
                plan.compare_access(revoked_access, access())
                phase = 'EXIT_PERMISSION_WINDOW'

            phase = 'ADMIN_RESTORED'
            restored_access = access()
            plan.compare_access(initial_access, restored_access)
            unchanged(pre_window)
            restored_original = step(phase, access=restored_access, observation=pre_window)
            for case_id in CASE_IDS[2:]:
                report[case_id] = dict(status='PASS', exact_admin_permission_loss_and_restore=True,
                    same_registered_actor=True, complete_no_effect=True, denials=pending_denials[case_id],
                    originals=dict(initial=access_before_original, revoked=window_original, restored=restored_original))
            return report
        except Exception as error:
            # Exact requests/responses already have their own stage receipts. Keep a bounded first-error summary.
            failure = dict(status='INCOMPLETE', stage=phase, error_type=type(error).__name__,
                           completed_case_ids=[key for key in CASE_IDS if key in report], originals=originals)
            message = str(error)
            if re.fullmatch(r'GLOBAL_AUTH_(?:CREDIT_HTTP_|CASE_PLAN_)[A-Z0-9_]+', message):
                failure['error_code'] = message
            try:
                step('FIRST_FAILURE', failure=failure)
            except Exception as evidence_error:
                error.add_note('GLOBAL_AUTH_CREDIT_HTTP_FIRST_FAILURE_ORIGINAL_NOT_RETAINED:' + type(evidence_error).__name__)
            raise

    return exercise
