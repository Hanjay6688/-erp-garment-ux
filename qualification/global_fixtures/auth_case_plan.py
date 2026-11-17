"""Ordinary HTTP case inputs for the existing Global owning Auth attempt."""

import re
from uuid import UUID


CANDIDATE_HEAD = 'a62504d71a6ca1cdbaa59b6fe0fd5739693f100a'
CANDIDATE_TREE = '3a338b69cc13d44f7c881c62ecf77f5a762a7df7'
APP_TREE = 'ada4544ebf22d9352461beb4b234f9a2f3e0ee29'
RUNNER_REPOSITORY = 'Hanjay6688/test'

ACTOR_PLAN = (
    ('OWNER', 'global-owner'),
    ('ADMIN', 'global-admin'),
    ('KEUANGAN', 'global-keuangan'),
)
ACCESS_RPC = 'erp_get_my_access_v1'
D1_REVIEW_RPC = 'erp_cp7_get_sales_return_correction_v1'
D1_COMMAND_RPC = 'erp_cp7_correct_sales_return_v1'
E_REVIEW_RPC = 'erp_cp7_get_note_correction_v2'
E_COMMAND_RPC = 'erp_cp7_correct_note_v1'
S05_REVIEW_RPC = 'erp_cp7_get_accessory_standard_report_v1'
RPC_PLAN = (ACCESS_RPC, D1_REVIEW_RPC, D1_COMMAND_RPC, E_REVIEW_RPC, E_COMMAND_RPC, S05_REVIEW_RPC)

HTTP_CASE_IDS = (
    'GLOBAL_AUTH_D1_FRESH_REPLAY',
    'GLOBAL_AUTH_E_FRESH_REPLAY',
    'GLOBAL_AUTH_D1_ADMIN_PERMISSION_REVOKED',
    'GLOBAL_AUTH_E_ADMIN_PERMISSION_REVOKED',
    'GLOBAL_AUTH_S05_ORDINARY_ACCESS',
)

REVOKED_PERMISSION = 'finance.hpp.view'
D1_PERMISSIONS = frozenset((
    'sales.invoice.view', 'sales.return.create', 'sales.return.post', 'sales.return.view',
    'sales.return.reverse', 'finance.ar.view', REVOKED_PERMISSION,
))
E_PERMISSIONS = frozenset((
    'sales.invoice.view', 'sales.invoice.create', 'sales.invoice.edit_draft',
    'sales.invoice.post', 'sales.invoice.reverse', 'finance.ar.view', REVOKED_PERMISSION,
))
S05_PERMISSIONS = frozenset(('finance.contractor_accessory.view', REVOKED_PERMISSION))


def require(value, reason):
    if not value:
        raise ValueError('GLOBAL_AUTH_CASE_PLAN_' + reason)


def attempt_kwargs(source_identity):
    """Read the already verified owning declaration, without reading CI env."""
    require(type(source_identity) is dict
            and source_identity.get('candidate_head') == CANDIDATE_HEAD
            and source_identity.get('candidate_tree') == CANDIDATE_TREE
            and source_identity.get('candidate_src') == APP_TREE, 'EXACT_CANDIDATE_REQUIRED')
    runner = source_identity.get('runner')
    require(type(runner) is dict and type(runner.get('github')) is dict, 'VERIFIED_RUNNER_REQUIRED')
    github = runner['github']
    require(github.get('repository') == RUNNER_REPOSITORY
            and runner.get('head') == github.get('merge')
            and runner['head'] != source_identity['candidate_head']
            and type(runner.get('tree')) is str and re.fullmatch('[a-f0-9]{40}', runner['tree'])
            and all(type(github.get(key)) is str and re.fullmatch('[a-f0-9]{40}', github[key])
                    for key in ('base', 'head', 'merge'))
            and type(github.get('pr')) is int and github['pr'] > 0
            and len({github['base'], github['head'], github['merge']}) == 3,
            'DISTINCT_PRIVATE_PR_CHECKOUT_REQUIRED')
    run, ordinal = github.get('run_id'), github.get('run_attempt')
    require(type(run) is int and 1 <= run < 10**18 and type(ordinal) is int and 1 <= ordinal < 10**4,
            'EXACT_RUN_AND_ATTEMPT_REQUIRED')
    return dict(head=source_identity['candidate_head'], attempt=f'{run}-{ordinal}',
                allowed_actors=ACTOR_PLAN, allowed_rpcs=RPC_PLAN)


def check_attempt(attempt, source_identity):
    """Verify the owned Attempt registry before its existing writer hooks run."""
    expected = attempt_kwargs(source_identity)
    require(attempt.head == expected['head'] and attempt.attempt == expected['attempt'],
            'EXACT_ATTEMPT_IDENTITY_REQUIRED')
    check_registry(attempt)


def check_registry(attempt):
    require(attempt.head == CANDIDATE_HEAD
            and attempt.allowed_actors == frozenset(ACTOR_PLAN)
            and attempt.allowed_rpcs == frozenset(RPC_PLAN), 'EXACT_ORDINARY_RPC_AND_ACTOR_SCOPE_REQUIRED')


def login_actor(attempt, role):
    """Use one of the already reviewed active roles in the owned attempt."""
    check_registry(attempt)
    labels = dict(ACTOR_PLAN)
    require(attempt.phase == 'ACTIVE' and role in labels, 'ACTIVE_REVIEWED_ACTOR_REQUIRED')
    return attempt.login(role, labels[role])


def observe_access(attempt, actor):
    """Capture effective ERP permission keys from the existing actor's session."""
    check_registry(attempt)
    labels = dict(ACTOR_PLAN)
    require(attempt.phase == 'ACTIVE' and any(actor is item for item in attempt._actors)
            and actor.role in labels, 'OWNED_ACTIVE_ACTOR_REQUIRED')
    subject = attempt.subjects.get((actor.role, labels[actor.role]))
    require(subject is not None and subject.uid_recorded is True and subject.uid == actor.auth_user_id,
            'EXACT_RECORDED_SUBJECT_REQUIRED')
    result = actor.rpc(ACCESS_RPC, {})
    body = result.get('body')
    require(result.get('status') == 200 and type(body) is dict and body.get('allowed') is True,
            'CURRENT_EFFECTIVE_ACCESS_REQUIRED')
    profile, permissions = body.get('profile'), body.get('permissions')
    require(type(profile) is dict and type(permissions) is list and all(
        type(key) is str and re.fullmatch(r'[a-z0-9_]+(?:\.[a-z0-9_]+)+', key) for key in permissions
    ) and len(permissions) == len(set(permissions)), 'EXACT_ACCESS_PROFILE_AND_PERMISSION_KEYS_REQUIRED')
    role_id = profile.get('role_id')
    try:
        canonical_role_id = type(role_id) is str and str(UUID(role_id)) == role_id
    except ValueError:
        canonical_role_id = False
    require(canonical_role_id and profile.get('id') == subject.app_id and profile.get('auth_user_id') == subject.uid
            and profile.get('role_code') == subject.role == actor.role and profile.get('is_active') is True
            and all(type(profile.get(key)) is int and profile[key] >= 0 for key in ('row_version', 'role_row_version')),
            'REST_PROFILE_DOES_NOT_MATCH_ATTEMPT_ACTOR')
    return dict(qualification_commit=attempt.head, attempt=attempt.attempt, application_oid=attempt.app[1],
                issuer_oid=attempt.issuer[1], cluster_system_id=attempt.app[2],
                app_user_id=subject.app_id, auth_uid=subject.uid, label=subject.label, role=subject.role,
                role_id=role_id, row_version=profile['row_version'], role_row_version=profile['role_row_version'],
                allowed=True, permission_keys=sorted(permissions))


def compare_access(before, after, *, lost=()):
    """Prove the actor and all unrelated effective permissions stayed equal."""
    require({key: value for key, value in before.items() if key != 'permission_keys'}
            == {key: value for key, value in after.items() if key != 'permission_keys'}, 'ACTOR_OR_SESSION_SCOPE_DRIFT')
    initial, observed, expected_lost = (set(keys) for keys in (before['permission_keys'], after['permission_keys'], lost))
    require(initial - observed == expected_lost and not observed - initial, 'EFFECTIVE_PERMISSION_DELTA_CHANGED')
    return dict(lost=sorted(expected_lost), added=[])


def require_permissions(access, expected):
    require(access['allowed'] is True and set(expected) <= set(access['permission_keys']),
            'EXPECTED_EXISTING_ERP_PERMISSIONS_REQUIRED')
