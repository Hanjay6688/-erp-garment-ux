"""Run the reviewed Global cases once on the private disposable CI job."""

from argparse import ArgumentParser
from contextlib import contextmanager
from datetime import datetime, timedelta
from hashlib import file_digest
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import traceback
from zoneinfo import ZoneInfo

from global_owning import installed_types_only, owning, p20_batch
from audit.codex import p20_resume
from p21 import installed as p21_installed, mode as p21_mode, preflight as p21_preflight
from global_owning.case_schedule import CASE, TRANSFER
from global_owning.foundation import WRITER_HEAD, WRITER_TREE
from global_owning.ordinary_case_scope import PHASES
from global_preseal import COMBINED, COMBINED_SRC, INPUTS, PLAN, ROOT_PIN
from sku_inputs import HEAD, TREE
from sku_parent import REPO, RUN, retained


HERE = Path(__file__).resolve().parent
SKU = 'scripts/current-sku-automatic-composite-preparation'
DONORS = {
    'window': (SKU + '/run_window.py', 'be4008173b1f6b8d8b970bdbb278de0a2d146cec5c660e28df036fdf681ca62f'),
    'receipt': (SKU + '/runtime_receipt.py', '2169088f8672f850d0ab4b0431d5ed0ea2da166436c9647ae1724f54bb4b88a8'),
    'supervisor': ('scripts/current-de-free-date-preparation/runtime_supervisor.py',
                   'af04570b8aecef5d7b0c9b1dfd5ab04942aec32fee8c2fdb908663108c97e149'),
}
PACKAGE_GATES = ('installed', 'primary_unchanged', 'backup_restore_drill', 'security_advisors', 'writer_runtime')
FULL_RESTORE = ('baseline_full22_all_rows_all_sequences_equal', 'baseline_full25_portable_catalogue_equal',
                'cp6_restored', 'baseline_advisors_equal', 'restore_raw_public_equal')
SCOPE_COUNTS = dict(actual_Native_cases=17, actual_two_session_races=1, actual_Auth_HTTP_cases=5,
                    actual_browser_cases=0, actual_business_cases=23)
FIXED_ORIGINALS = ('CP7_GLOBAL_FIRST_SNAPSHOTS.json', 'T3_PACKAGE_INSTALL.json', 'T3_BACKUP_RESTORE_DRILL.json',
                   'GLOBAL_OW06_TRANSFER_PAGE_25_TO_26_SETUP.json', 'GLOBAL_OW06_TRANSFER_PAGE_25_TO_26_ABORT.json',
                   'GLOBAL_OW06_TRANSFER_PAGE_25_TO_26_COMMIT.json',
                   'GLOBAL_AUTH_S05_COMMITTED_REPORT_FIXTURE.json', 'GLOBAL_AUTH_CREDIT_COMMITTED_FIXTURES.json',
                   'GLOBAL_AUTH_ADMIN_MAPPING_REMOVED.json', 'GLOBAL_AUTH_ADMIN_MAPPING_RESTORED.json',
                   'GLOBAL_FIRST_NATIVE_D1_E_SOURCE.json', 'GLOBAL_FIRST_NATIVE_D1_E_CURRENT_PERMISSION.json',
                   'GLOBAL_FIRST_NATIVE_LAWFUL_DIRTY.json', 'GLOBAL_FIRST_NATIVE_NOTA_WIB.json',
                   'GLOBAL_FIRST_NATIVE_NOTA_UTC.json', 'GLOBAL_COMMITTED_E_OBSERVATION.json',
                   'GLOBAL_USED_INVERSE_FULL_STATE.json', 'GLOBAL_STALE_D1.json', 'GLOBAL_STALE_E.json',
                   'GLOBAL_AUTH_S05_ORDINARY_ACCESS.json')
DOCKER = ('docker', '--host', 'unix:///var/run/docker.sock')
REST_OWNER = 'erp.cp7.global.auth-attempt'
DUMP = '/tmp/current_global_first_snapshots_pre.dump'
INHERITED_WRITER_RECEIPT = 'cp6-proof/au/SOURCE.json'
INHERITED_WRITER_RECEIPT_PIN = dict(bytes=3967, sha256='a3f3b8d2b4c1bf1501c38834c1967db43a1c71718b39b7a16e388b3f1ad20d31')


def require(value, code):
    owning.require(value, code)


def paths():
    workspace = Path(os.environ['GITHUB_WORKSPACE']).absolute()
    scratch = Path(os.environ['RUNNER_TEMP']).absolute() / 'cp7-live-parent'
    require(HERE == workspace / 'runner-source/qualification' and scratch.parent.is_dir()
            and not any(p.is_symlink() for p in (scratch, *scratch.parents)),
            'GLOBAL_ORDINARY_FIXED_RUNNER_PATHS_REQUIRED')
    scratch.mkdir(mode=0o700, exist_ok=True)
    return workspace, scratch, workspace / 'global-candidate/cp6-proof/t3'


def identity():
    runner = HERE.parent
    head = owning.git(runner, 'rev-parse', 'HEAD')
    result = owning.runner_ci_identity(runner, head)
    require(os.environ.get('GITHUB_REF') == owning.ordinary_ref()
            and os.environ.get('GITHUB_JOB') == 'ordinary' and result['run_attempt'] == 1,
            'GLOBAL_ORDINARY_EXACT_PRIVATE_JOB_REQUIRED')
    owning.tracked_source(runner, 'qualification/ordinary_run.py')
    return result


def donor(workspace, name):
    relative, digest = DONORS[name]
    path = workspace / 'auditor' / relative
    owning.exact(path, digest)
    return owning.load('global_ordinary_' + name, path)


def json_read(path):
    if not path.exists():
        return {}
    value = json.loads(owning.read(path, 'GLOBAL_ORDINARY_REGULAR_REPORT_REQUIRED'))
    require(type(value) is dict, 'GLOBAL_ORDINARY_REPORT_OBJECT_REQUIRED')
    return value


def json_write(path, value):
    with path.open('x', encoding='ascii') as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def put_once(path, raw):
    if path.exists():
        require(owning.read(path, 'GLOBAL_ORDINARY_REGULAR_INPUT_REQUIRED') == raw,
                'GLOBAL_ORDINARY_EXISTING_INPUT_CHANGED')
        return
    with path.open('xb') as stream:
        stream.write(raw)


def phase(name, state):
    print(f'GLOBAL_ORDINARY_PHASE {name} {state}', flush=True)


def receipts(workspace, scratch, run):
    module = donor(workspace, 'receipt')
    record = dict(repo=REPO, run=str(run['run_id']), attempt=str(run['run_attempt']), job='ordinary', head=run['merge'])
    return module.RuntimeReceipt(scratch / 'ordinary-process', record)


def require_window(workspace):
    module = donor(workspace, 'window')
    plan = module.budget()
    now = time.monotonic()
    local = datetime.now(ZoneInfo('Asia/Jakarta'))
    midnight = (local + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    reserve = module.ARTIFACT_SECONDS + module.RECOVERY_SECONDS + module.TERMINATION_SECONDS
    require(os.environ.get('ORDINARY_JOB_BUDGET_SECONDS') == '10800',
            'GLOBAL_ORDINARY_EXACT_JOB_WINDOW_REQUIRED')
    job = float(os.environ[module.JOB_START]) + 10800 - reserve
    work = min(job - now, (midnight - local).total_seconds() - reserve,
               plan.get('work_seconds_remaining', math.inf))
    require(math.isfinite(work) and work > 0, 'GLOBAL_ORDINARY_WORK_AND_RESTORE_WINDOW_REQUIRED')
    return work, module.RECOVERY_SECONDS


@contextmanager
def bind_runtime(workspace, scratch):
    if p20_batch.enabled():
        p20_batch.retained_original(scratch)
        p20_resume.retained(scratch)
    elif p21_mode.enabled():
        p21_preflight.admitted(owning.tracked_source(HERE.parent, p21_preflight.EVIDENCE_PATH)[1])
    settings = json_read(scratch / 'sku-settings.json')
    require(settings and all(type(key) is str and type(value) is str and key.isidentifier()
                             and not key.startswith(('GITHUB_', 'RUNNER_', 'ORDINARY_', 'DOCKER_', 'SKU_CURRENT_AUTOMATIC_WIB_', 'P20_EVIDENCE_', 'CP7_P21_'))
                             and key not in ('GH_TOKEN', 'SKU_CURRENT_AUTOMATIC_JOB_START_MONOTONIC',
                                             installed_types_only.MODE_KEY, p20_batch.MODE)
                             for key, value in settings.items()), 'GLOBAL_ORDINARY_RETAINED_SETTINGS_SCOPE_REQUIRED')
    os.environ.update(settings)
    catalogue, _, proved_sources = retained(scratch / 'sku-original.zip')
    catalogue_path = scratch / 'ordinary-sku-catalogue.json'
    put_once(catalogue_path, catalogue)
    fixtures = owning.load('global_reviewed_ordinary_paths', owning.tracked_source(HERE.parent, owning.FIXTURE_ENTRY)[0])
    with owning.runtime(workspace / 'global-candidate', workspace / 'auditor',
                        parent_receipt=INPUTS / 'SKU_A625_VERIFIED_ROOT.json',
                        input_profile=HERE.parent / fixtures.PROFILE_PATH, sku_catalogue=catalogue_path,
                        reviewed_ordinary=True) as bound:
        require(bound.sku_source_proof['complete_combined_sources'] == proved_sources
                and not bound.source_fence['attempts'] and not bound.source_fence['network_nonGit_attempts'],
                'GLOBAL_ORDINARY_RETAINED_SKU_GRAPH_OR_FENCE_CHANGED')
        yield bound


def retain_inherited_writer_receipt(workspace, scratch):
    """Move the one source-only AU receipt emitted by the retained setup."""
    writer = workspace / 'writer'
    receipt = writer / INHERITED_WRITER_RECEIPT
    raw = owning.read(receipt, 'GLOBAL_ORDINARY_EXACT_INHERITED_WRITER_RECEIPT_REQUIRED')
    value = json.loads(raw)
    require(owning.pin(raw) == INHERITED_WRITER_RECEIPT_PIN
            and value.get('head') == WRITER_HEAD and value.get('tree') == WRITER_TREE
            and value.get('production_go') is value.get('independent_acceptance') is False,
            'GLOBAL_ORDINARY_INHERITED_WRITER_RECEIPT_IDENTITY_CHANGED')
    require(owning.git(writer, 'status', '--porcelain=v1', '-z', '--untracked-files=all')
            == '?? ' + INHERITED_WRITER_RECEIPT + '\0', 'GLOBAL_ORDINARY_UNEXPECTED_WRITER_WORKTREE_CHANGES')
    retained_path = scratch / 'ordinary-inherited-AU-source.json'
    put_once(retained_path, raw)
    receipt.unlink()
    owning.checked_writer(writer)
    return report_pin(retained_path)


def preflight(workspace, scratch, run):
    phase('SOURCE_PREFLIGHT', 'STARTED')
    try:
        require_window(workspace)
        if p21_mode.enabled():
            from p21 import g04_source, s06_source

            _, bundle = owning.tracked_source(HERE.parent, g04_source.BUNDLE)
            g04_source.prepare(workspace / 'g04-product', bundle)
            combined_product = workspace / 's06-product'
            owning.git(workspace, 'clone', '--quiet', '--shared', '--no-checkout',
                       str(workspace / 'g04-product'), str(combined_product))
            owning.git(combined_product, 'sparse-checkout', 'set', 'src', 'scripts', 'tests', 'contracts', 'public', 'supabase')
            owning.git(combined_product, 'checkout', '--quiet', '--detach', g04_source.PRODUCT)
            _, s06_bundle = owning.tracked_source(HERE.parent, s06_source.BUNDLE)
            s06_source.prepare(combined_product, s06_bundle)
            from close11.source import materialize
            materialize(workspace)
        inherited_receipt = retain_inherited_writer_receipt(workspace, scratch)
        with bind_runtime(workspace, scratch) as bound:
            require(bound.runner_source['github'] == run, 'GLOBAL_ORDINARY_SOURCE_IDENTITY_CHANGED')
    except Exception as error:
        json_write(scratch / 'ordinary-preflight-failure.json', source_failure(error))
        phase('SOURCE_PREFLIGHT', 'FAILED')
        raise
    receipts(workspace, scratch, run).prepare()
    json_write(scratch / 'ordinary-preflight.json',
               dict(identity=run, candidate_tree=COMBINED, passed=True, inherited_writer_receipt=inherited_receipt))
    phase('SOURCE_PREFLIGHT', 'COMPLETED')


def worker(workspace, scratch, run):
    process = receipts(workspace, scratch, run)
    require(process.read('decision.json')['phase'] == 'WORKER_CLAIMED',
            'GLOBAL_ORDINARY_SUPERVISED_WORKER_REQUIRED')
    phase('SOURCE_ADMISSION', 'STARTED')
    state = 'SOURCE_ADMISSION'
    try:
        with bind_runtime(workspace, scratch) as bound:
            require(bound.runner_source['github'] == run, 'GLOBAL_ORDINARY_RUNTIME_IDENTITY_CHANGED')
            phase(state, 'COMPLETED')
            state = ('OWNING_T3_AND_P20' if p20_batch.enabled() else
                     'OWNING_T3_AND_P21' if p21_mode.enabled() else
                     'OWNING_T3_AND_SCHEMA' if installed_types_only.enabled() else 'OWNING_T3_AND_CASES')
            phase(state, 'STARTED')
            bound.run()
    except BaseException as error:
        json_write(scratch / 'ordinary-worker-failure.json',
                   dict(phase=state, first_failure=bounded_failure(str(error)) or 'GLOBAL_ORDINARY_WORKER_INTERRUPTED'))
        phase(state, 'FAILED')
        raise
    phase(state, 'COMPLETED')


def supervise(workspace, scratch, run):
    require(verified_preflight(scratch, run), 'GLOBAL_ORDINARY_ACTUAL_PREFLIGHT_REQUIRED')
    work, recovery = require_window(workspace)
    process = receipts(workspace, scratch, run)
    supervisor = donor(workspace, 'supervisor')
    command = [sys.executable, '-u', '-B', str(Path(__file__).absolute()), 'worker']
    phase('SUPERVISION', 'STARTED')
    private_log = scratch / 'ordinary-worker.log'
    with private_log.open('xb') as log:
        process.claim_worker()
        # The retained supervisor owns creation, signals and reaping. Redirect
        # both descriptors before it starts the worker and its descendants.
        originals = (os.dup(1), os.dup(2))
        try:
            for fd in (1, 2):
                os.dup2(log.fileno(), fd)
            result = supervisor.supervise(command, work_seconds=work, recovery_seconds=recovery)
        finally:
            for fd, previous in enumerate(originals, 1):
                os.dup2(previous, fd)
                os.close(previous)
    result.update(github_run_id=str(run['run_id']), github_run_attempt=str(run['run_attempt']),
                  qualification_commit=run['merge'])
    output = scratch / 'ordinary-supervision.json'
    json_write(output, result)
    process.finish(output)
    completed = result['status'] == 'WORKER_COMPLETED_AND_REAPED'
    phase('SUPERVISION', 'COMPLETED' if completed else 'FAILED')
    return 0 if completed else 1


def docker(*args, check=True):
    return subprocess.run((*DOCKER, *args), check=check, capture_output=True, text=True, timeout=45)


def owned_rest(run):
    prefix = f"cp7-global-auth-{run['run_id']}-{run['run_attempt']}-"
    owned = []
    for line in docker('ps', '-a', '--no-trunc', '--filter', 'label=' + REST_OWNER,
                       '--format', '{{.ID}}\t{{.Names}}\t{{.Label "erp.cp7.global.auth-attempt"}}').stdout.splitlines():
        container, name, label = line.split('\t')
        if not (name.startswith(prefix) or label.startswith(prefix)):
            continue
        require(re.fullmatch(r'[a-f0-9]{64}', container) and name == label
                and re.fullmatch(re.escape(prefix) + '[a-f0-9]{12}', name),
                'GLOBAL_ORDINARY_REST_OWNER_MISMATCH')
        owned.append(container)
    return owned


def cleanup_transport(workspace, scratch, run):
    receipts(workspace, scratch, run).authorize_stop()
    json_write(scratch / 'ordinary-stack-stop-authorized.json', dict(identity=run, authorized=True))
    visible = owned_rest(run)
    for container in visible:
        docker('rm', '-f', container)
    require(not owned_rest(run), 'GLOBAL_ORDINARY_REST_CONTAINER_REMAINED')
    database = docker('ps', '--format', '{{.Names}}').stdout.splitlines()
    dump_present = False
    if 'supabase_db_cp5-local' in database:
        probe = docker('exec', 'supabase_db_cp5-local', 'test', '-f', DUMP, check=False)
        require(probe.returncode in (0, 1) and not probe.stderr, 'GLOBAL_ORDINARY_DUMP_CLEANUP_UNOBSERVED')
        dump_present = probe.returncode == 0
    json_write(scratch / 'ordinary-transport.json',
               dict(identity=run, abandoned_rest_removed=len(visible), baseline_dump_present_before_stack_stop=dump_present))
    require(not visible and not dump_present, 'GLOBAL_ORDINARY_NATURAL_CLEANUP_INCOMPLETE')


def report_pin(path):
    if not path.is_file():
        return None
    with owning.regular(path, 'GLOBAL_ORDINARY_REGULAR_ORIGINAL_REQUIRED').open('rb') as stream:
        return dict(bytes=os.fstat(stream.fileno()).st_size, sha256=file_digest(stream, 'sha256').hexdigest())


def verified_preflight(scratch, run):
    retained_pin = report_pin(scratch / 'ordinary-inherited-AU-source.json')
    return retained_pin == INHERITED_WRITER_RECEIPT_PIN and json_read(scratch / 'ordinary-preflight.json') == dict(
        identity=run, candidate_tree=COMBINED, passed=True, inherited_writer_receipt=retained_pin)


def bounded_failure(*messages):
    prefix = r'(?:AUDITOR_P20_|PRIVATE_GLOBAL_|GLOBAL_|CP7_|CP6_|SKU(?:27)?_|S02_|S05_|OW06_(?:TRANSFER_PAGE_|RACE_)|T3_|JOIN_|BASELINE_)'
    for message in messages:
        if type(message) is not str or not message:
            continue
        token = re.match(r'^(?:[A-Za-z]+(?:Error|Refusal): )?(' + prefix + r'[A-Z0-9_]{5,108})\b', message)
        if token:
            return token[1]
        assertion = re.match(r"^\('((?:S05_|OW06_(?:TRANSFER_PAGE_|RACE_))[A-Z0-9_]{5,108})',", message)
        if assertion:
            return assertion[1]
        return 'GLOBAL_ORDINARY_PRIVATE_ERROR_RETAINED_IN_RUNNER'
    return None


def source_failure(error):
    """Keep source locations for diagnosis without copying arguments or credentials."""
    frames = []
    for entry in traceback.extract_tb(error.__traceback__)[-10:]:
        name = Path(entry.filename).name
        if re.fullmatch(r'[A-Za-z0-9_.-]{1,96}\.py', name):
            frames.append(dict(file=name, line=entry.lineno, function=entry.name))
    result = dict(first_failure=bounded_failure(str(error)), exception_type=type(error).__name__, frames=frames)
    symbol = getattr(error, 'name', None)
    if isinstance(error, KeyError) and error.args:
        symbol = error.args[0]
    if isinstance(error, TypeError):
        unexpected = re.search(r"unexpected keyword argument '([A-Za-z_][A-Za-z0-9_]{0,63})'", str(error))
        symbol = unexpected[1] if unexpected else None
    if isinstance(symbol, str) and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,63}', symbol):
        result['symbol'] = symbol
    if isinstance(error, OSError) and type(error.errno) is int:
        result['errno'] = error.errno
    if isinstance(error, subprocess.CalledProcessError):
        result['returncode'] = error.returncode
    return result


def observed_cases(scopes, selected):
    states = dict(scopes.get('business_cases', {}))
    states.update(scopes.get('HTTP_case_results', {}))
    for section in ('original_Native_D1_E_SOURCE', 'positive_originals', 'permission_originals', 'lawful_dirty_original'):
        states.update(scopes.get(section, {}).get('cases', {}))
    for timezone, suffix in (('Asia/Jakarta', '_WIB'), ('UTC', '_UTC')):
        notes = scopes.get('nota_originals', {}).get(timezone, {}).get('cases', {})
        states.update((case + suffix, state) for case, state in notes.items())
    return [case for case in selected if states.get(case, {}).get('status') == 'PASS']


def scoped_writes(observation):
    return (observation.get('mode') == 'transaction' and type(observation.get('write_attempts')) is dict
            and all(observation.get(key) == empty for key, empty in (
                ('outside_write_attempts', {}), ('relation_identity_changes', []),
                ('unexpected_temporary_relations', []))))


def transfer_terminals(output):
    result = {}
    for label, count, cash in (('ABORT', 25, '1000.00'), ('COMMIT', 26, '0.00')):
        original = json_read(output / ('GLOBAL_OW06_TRANSFER_PAGE_25_TO_26_' + label + '.json'))
        if not original:
            continue
        old, active, staged, following = (original.get(key, {}).get('transfers', {})
                                          for key in ('old', 'active', 'staged', 'following'))
        native = original.get('following_native', {})
        ids = (original.get('reader_pid'), original.get('writer_pid'))
        if (original.get('terminal') == label and original.get('actual_case_credit') == 0
                and old.get('total') == active.get('total') == '25' and staged.get('total') == '26'
                and following.get('total') == str(count) and native.get('cash') == cash
                and len(native.get('transfers', ())) == count
                and all(type(pid) is int and pid > 0 for pid in ids) and ids[0] != ids[1]):
            result[label] = dict(active_read=25, staged=26, after_terminal=count, cash=cash,
                                 native_ap_journal_stock_hpp_verified=True, separate_reader_writer=True)
    return result


def safe_result(scratch, output, run):
    writer = json_read(output / FIXED_ORIGINALS[0])
    package = json_read(output / FIXED_ORIGINALS[1])
    drill = json_read(output / FIXED_ORIGINALS[2])
    supervision = json_read(scratch / 'ordinary-supervision.json')
    owner = writer.get('source_declaration', {}).get('global_owning_source', {})
    outer = package.get('run_identity', {})
    scopes = writer.get('committed', {}).get(CASE, {})
    live = scopes.get('live_candidate_scope_observation', {})
    foundation = writer.get('preseal_foundation', {})
    phase_scope = scopes.get('case_relation_scope', {})
    cleanup = writer.get('global_auth_cleanup', {})
    application_oid = writer.get('global_auth_application', {}).get('oid')
    s05_setup = json_read(output / 'GLOBAL_AUTH_S05_COMMITTED_REPORT_FIXTURE.json')
    foundation_writes = foundation.get('relation_scope', {})
    changed_session_fields = foundation.get('preseed_session_changed_fields', [])
    session_fields = {'pid', 'database', 'temporary_namespace', 'current_user', 'session_user', 'role',
                      'session_authorization', 'TimeZone', 'search_path', 'request.jwt.claims',
                      'request.jwt.claim.sub', 'app.change_reason', 'app.worker_rate_write',
                      'app.worker_employment_write', 'app.attendance_period_lifecycle',
                      'cp7.sku_nonpo_sync_expanding', 'cp7.sku_po_sync_expanding'}
    require(type(changed_session_fields) is list and set(changed_session_fields) <= session_fields,
            'GLOBAL_ORDINARY_SESSION_DIAGNOSTIC_FIELDS_CHANGED')
    s05_writes = s05_setup.get('write_scope', {})
    transport = json_read(scratch / 'ordinary-transport.json')
    fixtures = owning.load('global_ordinary_receipt_fixtures', owning.tracked_source(HERE.parent, owning.FIXTURE_ENTRY)[0])
    case_state = scopes.get('business_cases', {})
    transfer = transfer_terminals(output)
    selected = (*fixtures.NATIVE_CASE_IDS, TRANSFER, *fixtures.HTTP_CASE_IDS)
    cases = observed_cases(scopes, selected)
    originals = dict()
    auth_originals = tuple('GLOBAL_AUTH_' + f"{run['run_id']}-{run['run_attempt']}_" + phase_name + '.json'
                           for phase_name in ('BASELINE', 'REST_BOUND', 'RESTORED_APPLICATION', 'FINAL_CLEANUP'))
    failures = ('GLOBAL_AUTH_ORDINARY_SCHEDULE_FIRST_FAILURE.json',
                'GLOBAL_OW06_TRANSFER_PAGE_25_TO_26_SETUP_FIRST_FAILURE.json',
                'GLOBAL_OW06_TRANSFER_PAGE_25_TO_26_ABORT_FIRST_FAILURE.json',
                'GLOBAL_OW06_TRANSFER_PAGE_25_TO_26_COMMIT_FIRST_FAILURE.json')
    native_observations = tuple(case + '_GLOBAL_OBSERVATION.json' for case in fixtures.NATIVE_CASE_IDS[:8])
    for name in (*FIXED_ORIGINALS, *auth_originals, *native_observations, *failures):
        pinned = report_pin(output / name)
        if pinned is not None:
            originals[name] = pinned
    credit_originals = True
    for case in fixtures.HTTP_CASE_IDS[:-1]:
        case_report = case_state.get(case, {})
        pins = case_report.get('originals', {})
        denials = case_report.get('denials', {})
        valid = type(pins) is type(denials) is dict and bool(pins)
        if valid:
            for pin in (*pins.values(), *(item['original'] for item in denials.values())):
                name = pin.get('name', '')
                if not re.fullmatch(r'GLOBAL_AUTH_CREDIT_HTTP_[A-Z0-9_]+\.json', name):
                    valid = False
                    continue
                local = report_pin(output / name)
                if local is None or pin != dict(name=name, **local):
                    valid = False
                    continue
                originals[name] = local
        credit_originals = credit_originals and valid
    first_http = json_read(output / failures[0])
    transfer_failure = next((json_read(output / name) for name in failures[1:] if name in originals), {})
    failing_group = next((item for section in ('positive_originals', 'permission_originals', 'lawful_dirty_original')
                          for item in scopes.get(section, {}).get('cases', {}).values()
                          if item.get('status') != 'PASS' and item.get('error')), {})
    preflight_failure = json_read(scratch / 'ordinary-preflight-failure.json')
    worker_failure = json_read(scratch / 'ordinary-worker-failure.json')
    first_stage = next((stage for stage in package.get('stages', ()) if stage.get('status') != 'PASS'), {})
    failure = bounded_failure(preflight_failure.get('first_failure'), first_http.get('error_code'),
                              transfer_failure.get('error'), failing_group.get('error'), writer.get('error'),
                              writer.get('restore_error'), writer.get('global_auth_cleanup_error'),
                              first_stage.get('error'), package.get('error'), worker_failure.get('first_failure'))
    evidence = transfer_failure.get('evidence')
    sqlstate = transfer_failure.get('sqlstate') or (evidence.get('sqlstate') if type(evidence) is dict else None)
    if type(sqlstate) is not str or not re.fullmatch('[0-9A-Z]{5}', sqlstate):
        sqlstate = None
    workflow = {key.lower(): os.environ.get('ORDINARY_' + key, '') for key in
                ('PREFLIGHT', 'STACK', 'RUNTIME', 'CLEANUP', 'TRANSPORT')}
    allowed = ('success', 'failure', 'cancelled', 'skipped')
    workflow = {key: value if value in allowed else 'unobserved' for key, value in workflow.items()}
    checks = dict(
        preflight=verified_preflight(scratch, run),
        candidate=writer.get('qualification_commit') == HEAD and owner.get('candidate_head') == HEAD
                  and owner.get('candidate_tree') == COMBINED and owner.get('candidate_src') == COMBINED_SRC
                  and owner.get('sku_root') == ROOT_PIN and owner.get('runner', {}).get('github') == run
                  and owner.get('input_profile') == fixtures.GATES['INPUT_PROFILE_PIN']
                  and owner.get('fixture_entry') == report_pin(HERE.parent / owning.FIXTURE_ENTRY)
                  and owner.get('fixture_manifest') == fixtures.MANIFEST_PIN,
        package_identity=outer.get('tool_head') == HEAD and outer.get('github_sha') == run['merge']
                         and outer.get('run_id') == str(run['run_id']) and outer.get('run_attempt') == str(run['run_attempt']),
        supervisor=supervision.get('status') == 'WORKER_COMPLETED_AND_REAPED'
                   and supervision.get('process_group_empty') is True and supervision.get('process_tree_empty') is True
                   and supervision.get('worker_exit') == 0 and supervision.get('signals') == [],
        actual_scope=live.get('status') == 'OBSERVED_EXACT_SEALED_SCOPE' and live.get('relation_count') == 461,
        foundation_scope=foundation.get('status') == 'VERIFIED_ON_EXISTING_INSTALLER_AFTER_COMMIT'
                         and scoped_writes(foundation_writes)
                         and foundation_writes.get('changed_tables_outside_scope') == []
                         and type(foundation.get('seed_invoked')) is bool
                         and bool(foundation_writes['write_attempts']) == foundation['seed_invoked'],
        s05_setup_scope=scoped_writes(s05_writes) and bool(s05_writes['write_attempts'])
                        and s05_setup.get('temporary', {}).get('recost_table_removed') is True
                        and s05_setup.get('temporary', {}).get('original_backend_observed') is True,
        case_relation_scope=set(phase_scope) == set(PHASES)
                            and type(application_oid) is int and application_oid > 0
                            and all(phase_scope[name].get('status') == 'OBSERVED_SCOPED_CHANGES'
                                    and phase_scope[name].get('database_oid') == application_oid
                                    and phase_scope[name].get('origin_relation_count') == 461 for name in PHASES),
        full_restore=all(writer.get(key) is True for key in FULL_RESTORE)
                     and writer.get('baseline_restore', {}).get('only_pg_cron_errors') is True,
        application_issuer_cleanup=cleanup.get('status') == 'PASS' and cleanup.get('verified_actors') == 3
                                    and writer.get('global_auth_before_restore', {}).get('verified') is True
                                    and cleanup.get('restored_application_mappings_absent') is True
                                    and cleanup.get('primary_application_mappings_absent') is True,
        transport=transport == dict(identity=run, abandoned_rest_removed=0, baseline_dump_present_before_stack_stop=False),
        all_package_gates=(set(package.get('gate', {})) == set(PACKAGE_GATES)
                           and all(package['gate'][key] is True for key in PACKAGE_GATES)),
        backup_drill=drill.get('status') in ('RESTORED_IDENTICAL', 'RESTORED_SAME_MEANING')
                     and len(drill.get('checks', {})) == 5 and all(value is True for value in drill['checks'].values())
                     and drill.get('data', {}).get('differ') == {},
        all_cases=set(case_state) == set(selected) and all(state.get('status') == 'PASS' for state in case_state.values())
                  and writer.get('status') == scopes.get('status') == 'PASS'
                  and all(type(writer.get(key)) is int and writer[key] == count for key, count in SCOPE_COUNTS.items()),
        transfer_terminals=set(transfer) == {'ABORT', 'COMMIT'},
        originals=credit_originals and all(name in originals for name in (*FIXED_ORIGINALS, *auth_originals,
                                                                        *native_observations)),
    )
    passed = all(checks.values()) and all(value == 'success' for value in workflow.values())
    return dict(contract='cp7.global.ordinary.run.v1', status='PASS' if passed else 'INCOMPLETE', runner=run,
                candidate=dict(head=HEAD, tree=COMBINED, app_tree=COMBINED_SRC, sku_tree=TREE),
                retained_SKU_run=RUN, input_profile=fixtures.GATES['INPUT_PROFILE_PIN'], installation_plan=PLAN,
                workflow=workflow, checks=checks, passed_case_ids_observed=cases,
                observed_relation_phases=[name for name in PHASES
                                          if phase_scope.get(name, {}).get('status') == 'OBSERVED_SCOPED_CHANGES'],
                original_pins=originals, transfer_observations=transfer, first_failure=failure, first_sqlstate=sqlstate,
                foundation_session=dict(changed=changed_session_fields,
                                        local_self_role_reset=foundation.get('preseed_local_self_role_reset') is True),
                first_failed_phase=next((stage['phase'] for stage in writer.get('stage_timings', ())
                                         if stage.get('state') == 'FAILED'
                                         and type(stage.get('phase')) is str
                                         and re.fullmatch('[A-Z0-9_]{4,100}', stage['phase'])),
                                        'SOURCE_PREFLIGHT' if preflight_failure else worker_failure.get('phase')),
                **(SCOPE_COUNTS if passed else dict.fromkeys(SCOPE_COUNTS, 0)),
                actual_Global_cases=SCOPE_COUNTS['actual_business_cases'] if passed else 0,
                production_go=False, independent_acceptance=False)


def installation_result(scratch, output, run):
    base = safe_result(scratch, output, run)
    writer = json_read(output / FIXED_ORIGINALS[0])
    package = json_read(output / FIXED_ORIGINALS[1])
    schema = json_read(output / 'CP7_INSTALLED_TYPES.json')
    shared = ('preflight', 'candidate', 'package_identity', 'supervisor', 'foundation_scope',
              'full_restore', 'transport', 'all_package_gates', 'backup_drill')
    checks = {name: base['checks'][name] for name in shared}
    checks.update(
        installed_schema_and_unused_inverse=writer.get('status') == 'PASS'
            and writer.get('qualification_scope') == installed_types_only.SCOPE
            and installed_types_only.complete(writer) and writer.get('installed_public_types') == schema,
        no_ordinary_replay=all(type(writer.get(name)) is int and writer[name] == 0 for name in SCOPE_COUNTS)
            and package.get('auth_users_before') == package.get('auth_users_after') == 0
            and writer.get('observed_case_count') == 0 and not owned_rest(run),
        schema_export=report_pin(output / installed_types_only.installed_types.TYPE_FILE) == dict(
            bytes=schema.get('generated', {}).get('raw_bytes'),
            sha256=schema.get('generated', {}).get('raw_sha256')),
    )
    passed = all(checks.values()) and all(step == 'success' for step in base['workflow'].values())
    return dict(contract='cp7.global.installed-observation.v1', scope=installed_types_only.SCOPE,
                status='PASS' if passed else 'INCOMPLETE', runner=run, candidate=base['candidate'],
                checks=checks, workflow=base['workflow'], actual_Global_cases=0,
                first_failure=base['first_failure'], first_failed_phase=base['first_failed_phase'],
                retained_ordinary=dict(run=43586847411, artifact=14113320822, cases=23,
                                       repeated=False),
                schema_receipt=report_pin(output / 'CP7_INSTALLED_TYPES.json'),
                production_go=False, independent_acceptance=False)


def p20_result(scratch, output, run):
    base = installation_result(scratch, output, run)
    writer = json_read(output / FIXED_ORIGINALS[0])
    package = json_read(output / FIXED_ORIGINALS[1])
    schema = json_read(output / 'CP7_INSTALLED_TYPES.json')
    p20 = writer.get('p20_installed', {})
    cleanup = writer.get('global_auth_cleanup', {})
    cases = p20.get('cases', {})
    passed_cases = [name for name in p20_batch.IDS if cases.get(name, {}).get('status') == 'PASS']
    checks = base['checks']
    checks.pop('no_ordinary_replay')
    checks['tested_successor_and_auth_cleanup'] = p20_batch.complete(writer)
    earlier = p20_batch.retained_original(scratch) if checks['preflight'] else None
    checks['installed_schema_and_unused_inverse'] = (
        writer.get('status') == 'PASS' and writer.get('installed_public_types') == schema
        and all(writer.get('focused_preuse_removal', {}).get(key) is value
                for key, value in installed_types_only.INVERSE_FLAGS.items()))
    checks['issuer_baseline'] = (package.get('auth_users_before') == package.get('auth_users_after') == 0
                                and cleanup.get('primary_application_mappings_absent') is True)
    evidence = json_read(scratch.parent / 'p20-evidence-spool/summary.json')
    evidence_identity = evidence.get('identity', {})
    evidence_archived = (evidence.get('all_archived') is True
                         and evidence_identity.get('run_id') == run['run_id']
                         and evidence_identity.get('attempt') == run['run_attempt']
                         and evidence_identity.get('runner') == run['head']
                         and evidence_identity.get('product') == p20_batch.HEAD
                         and evidence_identity.get('planned_case_ids') == list(p20_batch.IDS))
    passed = (evidence_archived and all(checks.values())
              and all(step == 'success' for step in base['workflow'].values()))
    base.update(contract='cp7.audit.p20.codex.a752.v3', scope='P20_INDEPENDENT_GLOBAL_PLANNER_PERMISSION',
                successor=dict(head=p20_batch.HEAD, tree=p20_batch.TREE),
                status='PASS' if passed else 'INCOMPLETE', p20_cases=cases,
                actual_Global_cases=len(passed_cases), passed_case_ids=passed_cases,
                executed_case_ids=[name for name in p20_batch.IDS if name in cases],
                planned_case_ids=list(p20_batch.IDS),
                retained_audited_P20=p20.get('retained_audit',
                    p20_resume.provenance() if checks['preflight'] else None),
                verified_real_auth_actors=cleanup.get('verified_actors', 0),
                auditor_oracle=p20.get('auditor_oracle'),
                auditor_sources={name: report_pin(HERE.parent / path) for name, path in {
                    'manifest': 'qualification/audit/codex/p20_a752_manifest.json',
                    'oracle': 'qualification/audit/codex/oracle.py',
                    'positive_close': 'qualification/audit/codex/positive_close.py',
                    'planner': 'qualification/audit/codex/planner.py',
                    'auth_identity': 'qualification/audit/codex/auth_identity.py',
                    'auth_binding': 'qualification/global_owning/dated_auth.py',
                    'batch': 'qualification/global_owning/p20_batch.py',
                    'resume': 'qualification/audit/codex/p20_resume.py',
                    'workflow': '.github/workflows/audit-codex-p20.yml',
                }.items()},
                p20_checkpoint_archive=dict(verified=evidence_archived, summary=report_pin(
                    scratch.parent / 'p20-evidence-spool/summary.json'),
                    receipts=evidence.get('receipts', {})),
                retained_installed_P20=earlier,
                installed_P21_acceptance=False)
    return base


def p21_result(scratch, output, run):
    from p21.checkpoints import archived
    from p21.followup import verify_retained
    from p21.s06_followup import S06
    from p21.g04_source import PRODUCT as G04_PRODUCT, TREE as G04_TREE
    from p21.s06_source import PRODUCT as S06_PRODUCT, TREE as S06_TREE

    result = installation_result(scratch, output, run)
    intake = json_read(scratch / 'P21_P20_INTAKE.json')
    evidence = p21_preflight.admitted(
        owning.tracked_source(HERE.parent, p21_preflight.EVIDENCE_PATH)[1])
    writer = json_read(output / FIXED_ORIGINALS[0])
    probes = writer.get('p21_installed_checks', {})
    checkpoints = archived(scratch / 'p21-checkpoints', run)
    retained = verify_retained()
    retained_intake = json_read(scratch / 'P21_RETAINED_INTAKE.json')
    auth = writer.get('global_auth_cleanup',{})
    result['checks'].update(p20_evidence_reused=intake == evidence,
                            p21_originals_reused=retained_intake==retained==writer.get('p21_followup_retained'),
                            s06_setup_auth_cleanup=installed_types_only.p21_auth_complete(writer),
                            installed_P21_probes=p21_installed.proven(probes),
                            checkpoints_archived=bool(checkpoints))
    if result['status'] != 'PASS' or not all(result['checks'].values()):
        result['status'] = 'INCOMPLETE'
        case_failure = probes.get(S06, {}).get('first_failure') or {}
        if case_failure.get('code'):
            result['first_failure'] = case_failure['code']
            result['first_failed_phase'] = case_failure.get('phase') or result['first_failed_phase']
        elif not result['first_failure']:
            result['first_failure'] = 'CP7_P21_INSTALLATION_GATE_INCOMPLETE'
    schema = json_read(output / 'CP7_INSTALLED_TYPES.json')
    result.update(contract='cp7.writer.p21.disposable-install.v1', scope=p21_mode.SCOPE,
                  target=p21_mode.TARGET, product=retained['product'], retained=retained,
                  g04_product=dict(head=G04_PRODUCT, tree=G04_TREE),
                  combined_product=dict(head=S06_PRODUCT, tree=S06_TREE),
                  actual_G04_cases_rerun=0,
                  auth_cleanup=dict(status=auth.get('status'), verified_actors=auth.get('verified_actors'),
                                    removed_actors=len(auth.get('deletions',{})),
                                    primary_mappings_absent=auth.get('primary_application_mappings_absent'),
                                    residual_subject_rows=auth.get('residual_subject_rows'), failures=auth.get('failures')),
                  p20_product=p21_preflight.PRODUCT, p20_prior=evidence,
                  actual_P20_cases_rerun=0, installed_checks=probes, checkpoint_receipts=checkpoints,
                  observed_P21_probes=[name for name in p21_installed.CHECKS
                                        if probes.get(name, {}).get('status') == 'OBSERVED'],
                  schema_inventory=dict(public_erp_names=schema.get('public_erp_names'),
                                        catalogue_groups=schema.get('catalogue_groups')),
                  actual_switch_roll_successful_saves_rerun=0, actual_E14_cases_rerun=0,
                  pending_independent_gates=['Independent review of S06 on the combined candidate'],
                  installed_P21_acceptance=False, independent_acceptance=False, production_go=False)
    return result


def finalize(scratch, output, run):
    focused = installed_types_only.enabled()
    p21 = p21_mode.enabled()
    receipt_name = ('P21_INSTALLATION_FINAL.json' if p21 else
                    'CP7_GLOBAL_INSTALLED_FINAL.json' if focused else 'GLOBAL_ORDINARY_FINAL.json')
    try:
        if p20_batch.enabled():
            result = p20_result(scratch, output, run)
        elif p21:
            result = p21_result(scratch, output, run)
        else:
            result = installation_result(scratch, output, run) if focused else safe_result(scratch, output, run)
    except Exception as error:
        contract = ('cp7.writer.p21.disposable-install.v1' if p21 else
                    'cp7.global.installed-observation.v1' if focused else 'cp7.global.ordinary.run.v1')
        result = dict(contract=contract, status='INCOMPLETE', runner=run,
                      first_failure=bounded_failure(str(error)), actual_Global_cases=0,
                      production_go=False, independent_acceptance=False)
        if p21:
            result.update(product=p21_preflight.PRODUCT, installed_P21_acceptance=False,
                          actual_P20_cases_rerun=0)
    json_write(scratch / receipt_name, result)
    return 0 if result['status'] == 'PASS' else 1


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('preflight', 'supervise', 'worker', 'cleanup-transport', 'finalize'))
    args = parser.parse_args()
    os.umask(0o077)
    work, scratch, output = paths()
    run = identity()
    operations = {
        'preflight': lambda: preflight(work, scratch, run),
        'supervise': lambda: supervise(work, scratch, run),
        'worker': lambda: worker(work, scratch, run),
        'cleanup-transport': lambda: cleanup_transport(work, scratch, run),
        'finalize': lambda: finalize(scratch, output, run),
    }
    return operations[args.action]()


if __name__ == '__main__':
    raise SystemExit(main())

