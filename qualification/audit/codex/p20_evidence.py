"""Evidence for the disposable P20 runner. Restore and audit remain separate gates."""

from argparse import ArgumentParser
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time


REPO = 'Hanjay6688/test'
PRODUCT = 'a752459a0a8baf1920d0e6d1c1fba6f4ef14af8d'
PRODUCT_TREE = '3440cb483c8f809987efb04c3e26072d14039ff2'
FIXTURE = '3f9e33ebc733d0bf7d49c00ce17899ec2ce6c6b8300661720767c6763eab412a'
AUDIT_REF = 'refs/heads/audit/codex-p20-a752459a'
SMOKE_REF = 'refs/heads/writer-a/p20-runner-evidence-20261117'
CONTRACT = 'cp7.audit.p20.checkpoint.v1'
ROOT = Path(__file__).resolve().parents[3]
FILES = {
    'manifest': 'qualification/audit/codex/p20_a752_manifest.json',
    'oracle': 'qualification/audit/codex/oracle.py',
    'planner': 'qualification/audit/codex/planner.py',
    'positive_close': 'qualification/audit/codex/positive_close.py',
    'auth_identity': 'qualification/audit/codex/auth_identity.py',
    'auth_binding': 'qualification/global_owning/dated_auth.py',
    'batch': 'qualification/global_owning/p20_batch.py',
    'supervisor': 'qualification/ordinary_run.py',
    'workflow': '.github/workflows/audit-codex-p20.yml',
    'legacy_native': 'qualification/global_owning/p20/legacy_native.py',
    'resume': 'qualification/audit/codex/p20_resume.py',
    'native': 'qualification/global_owning/p20/native.py',
}
FROZEN = {
    'manifest': '72e671ce9d803fd3faeb229bac23ff9a41384a50eb823f1e016cca594ae14a01',
    'oracle': '295387ab0ca0563783248b299f489d9ebc887448229eb3e188b861eda2192b41',
    'planner': 'c33ce21f2b1b92bfac228603c16289fafce0cb65d149d086d175849045a398c3',
    'positive_close': '6bcccf01e6e5d03dbcb97d1a0d6fc0f57965fa2ab0dab097632aab8e979dfbda',
    'auth_identity': '314d89060b434cf9db1d8095b042bc3e0bcd4dc5a3394090daebc49a7f333cc2',
    'auth_binding': '4e80f0d2f6913f4d489c7d0a982d84ad32bcb71015971fade5414b5764ead566',
}
TOOLS = (
    'qualification/audit/codex/p20_evidence.py',
    'qualification/audit/codex/p20_publish.py',
    'qualification/audit/codex/checkpoint_action/action.yml',
    'qualification/audit/codex/checkpoint_action/index.mjs',
    'qualification/audit/codex/checkpoint_action/upload.mjs',
    'qualification/audit/codex/checkpoint_action/package.json',
    'qualification/audit/codex/checkpoint_action/package-lock.json',
    '.github/workflows/p20-runner-evidence-smoke.yml',
    'qualification/audit/codex/test_p20_evidence.py',
    'qualification/audit/codex/test_p20_resume.py',
)
CASES = {
    'P20_OW07_POSITIVE_CLOSE': 'AUD-P20-OW07',
    'P20_OW07_REPORT_EXPENSE': 'AUD-P20-OW07',
    'P20_OW07_REPORT_CARRY': 'AUD-P20-OW07',
    'P19P_FG_INCREASE_NEED_CHANGED': 'P19P_FG_INCREASE_NEED_CHANGED',
    'P19P_WIP_INCREASE_NEED_CHANGED': 'P19P_WIP_INCREASE_NEED_CHANGED',
    'P19P_APPLY_AFTER_UNRELATED_CHANGE': 'P19P_APPLY_AFTER_UNRELATED_CHANGE',
    'P20_CASH_OW09_03': 'AUD-P20-CASH',
    'P20_CARRY_CASH_04': 'AUD-P20-CREDIT',
    'P20_CARRY_DATE_05': None,
    'P20_CARRY_CLOSED_06': None,
    'P20_AUTH_CASH_01_02': 'AUD-P20-CASH',
    'P20_SALE_SERIES_BROWSER': 'AUD-P20-SERIES',
    'P20_PLANNER_CURRENT_CUTTING_PERMISSION': 'P20_PLANNER_CURRENT_CUTTING_PERMISSION',
}
REMAINING_CASES = ('P20_PLANNER_CURRENT_CUTTING_PERMISSION',)
ROLES = {
    'P20_AUTH_CASH_01_02': ('OWNER', 'ADMIN'),
    'P20_PLANNER_CURRENT_CUTTING_PERMISSION': ('ADMIN',),
}
STATUSES = {'PASS', 'FAIL', 'INCOMPLETE'}
BOUNDARIES = {
    'ROLLBACK_BASELINE_VERIFIED', 'ROLLBACK_COMPLETED', 'COMMITTED_RECOVERY_PENDING',
    'BROWSER_INVERSE_COMPLETED_RECOVERY_PENDING', 'BOUNDARY_UNVERIFIED',
}
RESTORE_FLAGS = (
    'baseline_full22_all_rows_all_sequences_equal', 'baseline_full25_portable_catalogue_equal',
    'cp6_restored', 'baseline_advisors_equal', 'restore_raw_public_equal',
)
CODE = re.compile(r'(?:CP[67]_|P20_|AUDITOR_|GLOBAL_|T3_|E_)[A-Z0-9_]{4,100}|ORIGINAL_NOTE_BOOK_PAIR_ADAPTER_REQUIRED')
HEX = re.compile(r'[0-9a-f]{64}')
HEAD = re.compile(r'[0-9a-f]{40}')
UINT = re.compile(r'[1-9][0-9]{0,17}')
SAFE_VALUES = {'ACTIVE', 'SAVED', 'NATIVE_DRAFT_CREATED', 'CARRY', 'EXPENSE', 'CREATE', 'EDIT', 'POST', 'P0001',
               'ATTENDANCE_ZERO_CARRY_WAITING', 'ATTENDANCE_ZERO_PERIOD_EXPENSE'}


class EvidenceError(RuntimeError):
    """A stable, non-business diagnostic for an evidence failure."""


def need(ok, code):
    if not ok:
        raise EvidenceError(code)


def encode(value):
    return (json.dumps(value, sort_keys=True, allow_nan=False, separators=(',', ':')) + '\n').encode('ascii')


def stamp():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds')


def write_once(path, value):
    """Publish a synced complete JSON file or leave its predecessor untouched."""
    fd, tmp = tempfile.mkstemp(prefix='.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(encode(value))
            stream.flush()
            os.fsync(stream.fileno())
        os.link(tmp, path)
        sync = os.open(path.parent, os.O_DIRECTORY)
        try:
            os.fsync(sync)
        finally:
            os.close(sync)
    finally:
        os.unlink(tmp)


def read(path):
    need(not path.is_symlink() and path.is_file(), 'P20_EVIDENCE_REGULAR_FILE_REQUIRED')
    return json.loads(path.read_bytes())


def preflight(mode, destination):
    env = os.environ
    expected_scope = {'audit': ('workflow_dispatch', AUDIT_REF, 'ordinary'),
                      'smoke': ('push', SMOKE_REF, 'smoke')}
    event_name, ref, job = expected_scope[mode]
    event = read(Path(env['GITHUB_EVENT_PATH']))
    need(env.get('GITHUB_ACTIONS') == 'true' and env.get('GITHUB_REPOSITORY') == REPO
         and env.get('GITHUB_EVENT_NAME') == event_name and env.get('GITHUB_REF') == ref
         and env.get('GITHUB_JOB') == job and event['repository']['full_name'] == REPO
         and event['repository']['private'] is True and env.get('GITHUB_RUN_ATTEMPT') == '1',
         'P20_EVIDENCE_PRIVATE_RUN_REQUIRED')
    run = env.get('GITHUB_RUN_ID', '')
    need(UINT.fullmatch(run), 'P20_EVIDENCE_RUN_ID_INVALID')

    def git(*args, **kwargs):
        return subprocess.check_output(('git', '-C', ROOT, *args), **kwargs).decode().rstrip('\n')

    head, tree = git('rev-parse', 'HEAD', 'HEAD^{tree}').splitlines()
    need(HEAD.fullmatch(head) and HEAD.fullmatch(tree) and head == env.get('GITHUB_SHA'),
         'P20_EVIDENCE_RUNNER_SHA_CHANGED')
    if mode == 'audit':
        need(event.get('inputs') == {'candidate_sha': PRODUCT, 'audit_head': head},
             'P20_EVIDENCE_AUDIT_INPUT_CHANGED')
    pins = {}
    for label, name in (*FILES.items(), *((name, name) for name in TOOLS)):
        path = ROOT / name
        raw = path.read_bytes()
        blob = git('hash-object', '--stdin', input=raw)
        need(not path.is_symlink() and git('ls-tree', head, '--', name) == f'100644 blob {blob}\t{name}',
             'P20_EVIDENCE_TRACKED_SOURCE_CHANGED')
        pins[label] = sha256(raw).hexdigest()
    need(all(pins[label] == digest for label, digest in FROZEN.items()), 'P20_EVIDENCE_ORACLE_OR_FIXTURE_CHANGED')
    manifest = read(ROOT / FILES['manifest'])
    need(manifest['candidate_sha'] == PRODUCT and manifest['candidate_tree'] == PRODUCT_TREE
         and manifest['planner_handoff']['product_fixture_sha256'] == FIXTURE,
         'P20_EVIDENCE_PRODUCT_PIN_CHANGED')
    write_once(destination, dict(mode=mode, repository=REPO, run_id=int(run), attempt=1,
                product=PRODUCT, product_tree=PRODUCT_TREE, runner=head, runner_tree=tree,
                fixture_sha256=FIXTURE, oracle_sha256=pins['oracle'], source_pins=pins,
                planned_case_ids=list(REMAINING_CASES) if mode == 'audit' else []))


def scalar(value):
    if type(value) is bool or value is None:
        return value
    if type(value) is int and abs(value) <= 10**9:
        return value
    if type(value) is str and (value in SAFE_VALUES or CODE.fullmatch(value)
           or re.fullmatch(r'-?[0-9]{1,11}(\.[0-9]{1,4})?', value)
           or re.fullmatch(r'\d{4}-\d\d-\d\d(?:T\d\d:\d\d:\d\d[+-]\d\d:\d\d)?', value)):
        return value
    raise EvidenceError('P20_EVIDENCE_OBSERVED_VALUE_REJECTED')


NUMBER_MAP = 'fg wip need capacity selected needed_pcs capacity_pcs available_fg_pcs production_state'.split()
LISTS = frozenset('series_counts full_lifecycle matched_pages cash_pages old_report'.split())
NESTED = {
    'baseline': NUMBER_MAP,
    'observed': NUMBER_MAP,
    'amounts': ('liabilities', 'wip_inventory', 'operating_and_other_expense'),
    'journal': ('AR_CUSTOMER', 'SALES_REVENUE', 'COGS', 'FG_INVENTORY'),
    'real_auth_replacement_money': ('net_total', 'paid_total', 'open_balance'),
    'stale_refusal': ('sqlstate', 'message'),
    'actual_refusal': ('sqlstate', 'message'),
}
OBSERVED = frozenset('''
    choice source_choice source_day amount initial_ready pending_choice_blocked ready_after_choice
    filing_delta same_uuid_replay_no_extra_filing post_close_correction_refused
    gl_and_stock_unchanged_by_close rollback_boundary_verified official_report_matches_close
    pending_choice_blocks_report_and_close observed_choice_info unrelated_blockers_retained
    stock_cogs_and_cash_unchanged choice_replay native_draft_delta intent_delta apply_ready
    money_stock_HPP_unchanged sqlstate code state material_issue_posted exact_uuid_replay
    changed_request_code repeat_new_uuid_code fixture_opening_delta receipts outflow closing_delta
    draft_99_excluded inactive_alias_not_double_counted transfer_debit_and_credit
    post_transfer_closing_delta generated_native_labels before_AR after_AR replacement_net
    carried_credit cash_delta complete_cash_report_unchanged exact_carry_assignment
    physical_and_HPP_unchanged immutable_original_and_credit_journal real_auth_owner_profile
    real_auth_cash_matches_pretransfer credit_carried_each replacement_each_AR
    native_journal_dates_match_public_cash_report open_period closed_original_book_pair_preserved
    old_cash fresh_report fresh_cash stale_data_retired exact_grant_restored separate_issuer_sessions
    sale_hpp replay inverse draft_state_when_denied native_draft_delta_denied intent_delta_denied
    native_draft_delta_after_restore intent_delta_after_restore revocation_committed real_auth_http
'''.split())


def project(raw, fields):
    return {key: scalar(raw[key]) for key in fields if key in raw}


def short_list(raw):
    need(type(raw) is list and len(raw) <= 12, 'P20_EVIDENCE_OBSERVED_LIST_REJECTED')
    return [scalar(item) for item in raw]


def safe_observed(raw):
    out = project(raw, OBSERVED)
    out.update({key: short_list(raw[key]) for key in LISTS if key in raw})
    out.update({key: project(raw[key], fields) for key, fields in NESTED.items() if key in raw})
    if 'actual_refusal' in raw:
        detail = raw['actual_refusal'].get('detail', '')
        if type(detail) is str and len(detail) <= 8192:
            try:
                issues = json.loads(detail).get('issues', [])
            except (ValueError, AttributeError):
                issues = []
            closed_issue = 'ORIGINAL_NOTE_BOOK_PAIR_ADAPTER_REQUIRED'
            if type(issues) is list and closed_issue in issues:
                out['actual_refusal']['issues'] = [closed_issue]
    if 'stock' in raw:
        stock = raw['stock']
        out['stock'] = {key: [short_list(row) for row in stock[key]] for key in ('created', 'edited', 'posted')
                        if key in stock and type(stock[key]) is list and len(stock[key]) <= 8}
    if 'midnight_sides' in raw:
        need(type(raw['midnight_sides']) is list and len(raw['midnight_sides']) <= 2,
             'P20_EVIDENCE_OBSERVED_DATES_REJECTED')
        fields = ('physical_WIB', 'physical_UTC', 'economic_date', 'book_date', 'cash_receipt_debit',
                  'review_token_and_carry_hash_equal_across_zones')
        out['midnight_sides'] = [project(row, fields) for row in raw['midnight_sides']]
    return out


def safe_failure(raw):
    if type(raw) is str:
        raw = {'code': raw}
    raw = raw or {}
    code = raw.get('code')
    out = {'code': code if type(code) is str and CODE.fullmatch(code) else 'P20_EVIDENCE_CASE_RESULT_INCOMPLETE'}
    state = raw.get('sqlstate')
    if type(state) is str and re.fullmatch(r'[0-9A-Z]{5}', state):
        out['sqlstate'] = state
    locations = raw.get('locations', [])
    out['locations'] = [loc for loc in locations[:6] if type(loc) is str and
                        re.fullmatch(r'(?:p20_batch|native|attendance|positive_close|planner|cp7_[a-z0-9_]+)\.py:[1-9]\d{0,4}', loc)]
    if code == 'AUDITOR_P20_CLOSE_INITIAL_NOT_READY' and type(raw.get('blocker_codes')) is list:
        out['blocker_codes'] = [code for code in raw['blocker_codes'][:30]
                                if type(code) is str and re.fullmatch(r'[A-Z][A-Z0-9_]{1,71}', code)]
    if type(raw.get('observed')) is dict:
        # Unexpected server values must not prevent the first failure being recorded.
        out['observed'] = {}
        for key in NUMBER_MAP:
            if key in raw['observed']:
                try:
                    out['observed'][key] = scalar(raw['observed'][key])
                except EvidenceError:
                    pass
    return out


def receipt_valid(value, name, raw):
    return (type(value) is dict and value.get('status') == 'UPLOADED'
            and value.get('artifact_name') == name and value.get('document_sha256') == sha256(raw).hexdigest()
            and type(value.get('artifact_id')) is int and value['artifact_id'] > 0
            and type(value.get('archive_sha256')) is str
            and HEX.fullmatch(value['archive_sha256']) is not None)


class Journal:
    def __init__(self, spool, *, wait_seconds=65):
        self.spool = Path(spool)
        self.identity = read(self.spool / 'identity.json')
        self.wait_seconds = wait_seconds
        manifest_path = ROOT / FILES['manifest']
        need(sha256(manifest_path.read_bytes()).hexdigest() == self.identity['source_pins']['manifest'],
             'P20_EVIDENCE_MANIFEST_DRIFT')
        self.expected = {entry['id']: entry['expected'] for entry in read(manifest_path)['cases']}

    def envelope(self, kind, payload):
        return dict(contract=CONTRACT, identity=self.identity, kind=kind, captured_at_utc=stamp(),
                    independent_acceptance=False, installed_P21_acceptance=False,
                    actual_case_credit=0, production_go=False, **payload)

    def record(self, stem, kind, payload):
        target = self.spool / 'outbound' / f'{stem}.json'
        write_once(target, self.envelope(kind, payload))
        raw = target.read_bytes()
        ack = self.spool / 'receipts' / target.name
        deadline = time.monotonic() + self.wait_seconds
        while time.monotonic() < deadline:
            if ack.exists():
                value = read(ack)
                if value.get('status') == 'UPLOAD_FAILED':
                    raise EvidenceError('P20_EVIDENCE_UPLOAD_FAILED')
                need(receipt_valid(value, artifact_name(self.identity, stem), raw),
                     'P20_EVIDENCE_UPLOAD_RECEIPT_MISMATCH')
                if (self.spool / 'publisher-failure.json').exists():
                    raise EvidenceError('P20_EVIDENCE_PUBLISHER_FAILED')
                return value
            if (self.spool / 'publisher-failure.json').exists():
                raise EvidenceError('P20_EVIDENCE_PUBLISHER_FAILED')
            time.sleep(0.15)
        raise EvidenceError('P20_EVIDENCE_UPLOAD_ACK_TIMEOUT')

    def case(self, case_id, raw, boundary, started, *, boundary_failure=None):
        need(case_id in CASES and boundary in BOUNDARIES, 'P20_EVIDENCE_CASE_OR_BOUNDARY_INVALID')
        group = CASES[case_id]
        expected = self.expected[group] if group else (
            dict(credit_carried_each='80.00', replacement_each_AR='470.00',
                 cash_receipt_debit=['1.25', '2.75'], open_period=True,
                 same_book_and_economic_day=True) if case_id == 'P20_CARRY_DATE_05' else
            dict(sqlstate='P0001', message='CP7_CREDIT_NOTE_CARRY_REVIEW_REFUSED',
                 issue='ORIGINAL_NOTE_BOOK_PAIR_ADAPTER_REQUIRED'))
        status = raw.get('status')
        need(status in STATUSES, 'P20_EVIDENCE_CASE_STATUS_INVALID')
        payload = dict(case_id=case_id, roles=ROLES.get(case_id, ('OWNER',)), raw_status=status,
                       status=status if not boundary_failure else 'INCOMPLETE', boundary=boundary,
                       started_at_utc=started, provisional=True, restore_verified=False,
                       expected_origin=group or 'PINNED_NATIVE_CASE', expected=expected)
        if status == 'PASS':
            try:
                payload['observed'] = safe_observed(raw)
            except EvidenceError as error:
                payload.update(status='INCOMPLETE', first_failure=safe_failure(str(error)))
                self.record(f'case-{case_id}', 'case', payload)
                raise
        else:
            payload['first_failure'] = safe_failure(raw.get('first_failure'))
        if boundary_failure is not None:
            payload['boundary_failure'] = safe_failure(boundary_failure)
            payload.setdefault('first_failure', payload['boundary_failure'])
        return self.record(f'case-{case_id}', 'case', payload)

    def oracle(self, raw):
        return self.record('oracle', 'oracle', dict(status=raw.get('status'),
            cases=sorted(CASES) if raw.get('status') == 'PASS' else [],
            planned_case_ids=list(REMAINING_CASES),
            retained_case_ids=[case_id for case_id in CASES if case_id not in REMAINING_CASES],
            first_failure=None if raw.get('status') == 'PASS' else safe_failure(raw.get('first_failure')),
            provisional=True, restore_verified=False))


def artifact_name(identity, stem):
    need(re.fullmatch(r'(?:case-[A-Z0-9_]{1,64}|oracle|worker-exit|heartbeat-[0-9]{3}|smoke-[a-z0-9-]+)', stem),
         'P20_EVIDENCE_ARTIFACT_NAME_INVALID')
    return f"p20-evidence-{identity['run_id']}-{identity['attempt']}-{stem}"


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('audit', 'smoke'))
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    preflight(args.mode, args.destination)


if __name__ == '__main__':
    main()
