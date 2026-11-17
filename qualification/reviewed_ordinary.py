"""Admit the reviewed ordinary case inputs to the private disposable runner."""

from hashlib import sha256
import json
from pathlib import Path


FIXTURE_PATH = 'qualification/reviewed_ordinary.py'
PROFILE_PATH = 'qualification/global_fixtures/GLOBAL_ORDINARY_INPUT_PROFILE.json'
MANIFEST_PATH = 'qualification/global_fixtures/GLOBAL_ORDINARY_FIXTURE_MANIFEST.json'
ROOT_PATH = 'qualification/global-preseal/SKU_A625_VERIFIED_ROOT.json'
RELATIONS_PATH = 'qualification/global-preseal/GLOBAL_DATED_S05_RELATION_LOWER_BOUND.json'
PLAN_PATH = 'scripts/current-global-first-snapshot-preparation/INSTALL_PLAN.json'
SKU_ENTRY = 'scripts/current-sku-automatic-composite-preparation/qualification.py'

PROFILE_PIN = dict(bytes=31142, sha256='2478af40612a86198e86a4990ce48ebf64793022c9e27529e04f7c0260f983f1')
MANIFEST_PIN = dict(bytes=15945, sha256='fae12bffb6b8b1c771ed2319c3394c0bc92ef9393560f823556ebfab459c795f')
ROOT_PIN = dict(bytes=23897, sha256='ef5bbb964536502c25d4cf99774447006f4f015833818fae5c14e3cf8be5932a')
PLAN_PIN = dict(bytes=15667, sha256='71f15d39d45696c40d683f1cd27a03ac4c53a8da960a060839b24bd81996a319')
SKU_ENTRY_PIN = dict(bytes=15058, sha256='fb1dd131c0853b4feb80506d914b0984bac1a8babf53fdf5350eec0f84327a15')
RELATIONS_PIN = dict(bytes=14882, sha256='4ddd740d20841ad90bdc18101375cb0743645d53c43e6adc2d1840db532e3f74')

GATES = dict(
    PARENT_HEAD='a62504d71a6ca1cdbaa59b6fe0fd5739693f100a',
    PARENT_TREE='df64669b64e82f4b5027ccad837cc3d014dbcafa',
    PARENT_ROOT_RECEIPT=ROOT_PIN,
    PARENT_RUN=43347020525,
    PARENT_JOB=131628716944,
    PARENT_ROOT_CONTRACT=dict(
        status='ROOT_VERIFIED_CURRENT_SKU_NATIVE25_BROWSER2_ALL5',
        attempt=1,
        artifact_id=14011544457,
        actual_Native_cases=25,
        actual_Auth_HTTP_cases=0,
        actual_two_session_races=0,
        actual_browser_cases=2,
        actual_business_cases=27,
        actual_outer_restore=True,
        prior_runs_aggregated=False,
        complete_global_input_review=False,
    ),
    INPUT_PROFILE_PIN=PROFILE_PIN,
    RUNTIME_ENTRY='qualification/global_owning/owning.py',
)

NATIVE_CASE_IDS = (
    'D_AFTER_ACTIVE_APPLY', 'D_REPLAY_EXACT_UUID', 'E_SAME_UUID_AND_CHANGED_INTENT',
    'E_UNDO_ORIGINAL_80_AND_OLD_RECEIPT', 'OW04_SIGNED_RETURN_REVERSE_UNCONSUMED_CREDIT',
    'OW04_SIGNED_PAYMENT_REVERSE_UNCONSUMED_CREDIT', 'D_ACCESS_REVOKED_NO_EFFECT',
    'E_CURRENT_ACCESS_REVOKED_REFUSES', 'GLOBAL_DIRTY_D1_REVIEW_REFUSED', 'GLOBAL_DIRTY_E_REVIEW_REFUSED',
    'GLOBAL_DIRTY_SOURCE_RETURN_REVERSE_REFUSED', 'NOTE_PREPAYMENT_REPLAY_WIB', 'NOTE_PREPAYMENT_OVERPAYMENT_ATOMIC_WIB',
    'NOTE_OLD_ADVANCE_CASH_REPORT_WIB', 'NOTE_PREPAYMENT_REPLAY_UTC', 'NOTE_PREPAYMENT_OVERPAYMENT_ATOMIC_UTC',
    'NOTE_OLD_ADVANCE_CASH_REPORT_UTC',
)
HTTP_CASE_IDS = (
    'GLOBAL_AUTH_D1_FRESH_REPLAY', 'GLOBAL_AUTH_E_FRESH_REPLAY', 'GLOBAL_AUTH_D1_ADMIN_PERMISSION_REVOKED',
    'GLOBAL_AUTH_E_ADMIN_PERMISSION_REVOKED', 'GLOBAL_AUTH_S05_ORDINARY_ACCESS',
)
TRANSFER_CASE_ID = 'OW06_TRANSFER_PAGE_25_TO_26'
RPC_ALLOWLIST = (
    'erp_get_my_access_v1', 'erp_cp7_get_sales_return_correction_v1', 'erp_cp7_correct_sales_return_v1',
    'erp_cp7_get_note_correction_v2', 'erp_cp7_correct_note_v1', 'erp_cp7_get_accessory_standard_report_v1',
)


def require(condition, name):
    if not condition:
        raise ValueError('GLOBAL_ORDINARY_REVIEW_' + name)


def pin(raw):
    return dict(bytes=len(raw), sha256=sha256(raw).hexdigest())


def read(root, name, expected):
    relative = Path(name)
    path = root / relative
    require(not relative.is_absolute() and '..' not in relative.parts and path.is_file()
            and path.resolve() == path, 'EXACT_REGULAR_INPUT_REQUIRED:' + name)
    raw = path.read_bytes()
    require(pin(raw) == expected, 'INPUT_PIN_CHANGED:' + name)
    return raw


def admit(candidate, sku_checkout, parent_raw, profile_raw):
    """Check bytes and planned case boundaries before the owner opens a cursor."""
    runner = Path(__file__).absolute().parents[1]
    candidate = Path(candidate).absolute()
    sku_checkout = Path(sku_checkout).absolute()
    require(len({runner, candidate, sku_checkout}) == 3, 'SEPARATE_EXACT_CHECKOUTS_REQUIRED')
    require(type(parent_raw) is bytes and parent_raw == read(runner, ROOT_PATH, ROOT_PIN), 'EXACT_SKU_ORIGINAL_REQUIRED')
    require(type(profile_raw) is bytes and profile_raw == read(runner, PROFILE_PATH, PROFILE_PIN), 'EXACT_PROFILE_REQUIRED')
    profile = json.loads(profile_raw)
    manifest = json.loads(read(runner, MANIFEST_PATH, MANIFEST_PIN))
    require(manifest['contract'] == 'cp7.global-dated-ordinary-private-fixtures.v1'
            and manifest['profile'] == dict(path=PROFILE_PATH, **PROFILE_PIN)
            and profile['complete_input_review'] is True and profile['review_scope'] == manifest['scope'],
            'EXACT_SCOPED_FIXTURE_MANIFEST_REQUIRED')
    scope = manifest['scope']
    require(scope['repository'] == 'Hanjay6688/test' and scope['fixture_manifest'] == MANIFEST_PATH
            and scope['private_pull_request'] is scope['disposable'] is scope['single_attempt'] is True
            and scope['independent_acceptance'] is scope['production_go'] is False,
            'PRIVATE_DISPOSABLE_ATTEMPT_ONLY')
    expected_cases = dict(native=list(NATIVE_CASE_IDS), races=[TRANSFER_CASE_ID], http=list(HTTP_CASE_IDS), browser=[])
    require(manifest['case_ids'] == expected_cases and manifest['rpc_allowlist'] == list(RPC_ALLOWLIST)
            and manifest['actor_roles'] == ['OWNER', 'ADMIN', 'KEUANGAN']
            and manifest['application_database'] == 'cp6_rollback' and manifest['issuer_database'] == 'postgres',
            'EXACT_ORDINARY_CASE_AND_TRANSPORT_SCOPE_REQUIRED')
    immutable = manifest['immutable_runner_inputs']
    for name, expected in immutable.items():
        read(runner, name, expected)

    review = json.loads(read(runner, RELATIONS_PATH, manifest['relations']['source']))
    names = profile['relations']
    relation_bytes = json.dumps(names, separators=(',', ':')).encode()
    require(names == review['proposed_relations'] == sorted(set(names))
            and manifest['relations']['count'] == len(names) == 461
            and pin(relation_bytes) == manifest['relations']['list'] == review['proposed_relations_pin'] == RELATIONS_PIN,
            'EXACT_461_RELATIONS_REQUIRED')
    require(profile['installation_plan'] == manifest['installation_plan'] == PLAN_PIN,
            'EXACT_INSTALLATION_PLAN_REQUIRED')
    read(candidate, PLAN_PATH, PLAN_PIN)
    read(sku_checkout, SKU_ENTRY, SKU_ENTRY_PIN)
    return manifest
