"""The original desktop and mobile cases on one disposable Auth/browser copy."""
import ast
from datetime import datetime, timedelta
import gzip
from hashlib import sha256
import importlib.util
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from zoneinfo import ZoneInfo

DRIVER = Path(__file__).resolve().parents[2]
AUDITOR = DRIVER.parent / 'auditor'
WRITER = DRIVER.parent / 'writer'
NS = Path('scripts/current-mandor-shop-native-qualification')
FOCUS = 'MANDOR_BROWSER_PAIR_FOCUSED'
LEGACY = 'a0e7d5616a0ac470876409d31c41388159f17692'
PATCH = 'a691e7d9a18e2cfb1f847a5306054ecd5750e602'
BRANCH = 'refs/heads/astra-a/mandor-shop-native9-on-unified-20261103'
CSS = 'src/payroll-connected.css'
CSS_SHA = '33c4385241120033c683d6230922fd104d460514001435ff66aec065fdac2fc2'
OUTPUT = AUDITOR / 'cp6-proof/t3'
WORK = 170 * 60
RECOVERY = 20 * 60
BUDGET = 200 * 60


def require(condition, message):
    if not condition:
        raise ValueError(message)


def git(root, *args):
    return subprocess.check_output(['git', '-C', root, *args], text=True).strip()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def replace_once(source, old, new):
    require(source.count(old) == 1 and old != new, 'FOCUSED_SOURCE_ROUTE_MISSING_OR_DUPLICATE:' + old)
    return source.replace(old, new, 1)


def remove_section(source, start, end):
    require(source.count(start) == source.count(end) == 1, 'FOCUSED_SOURCE_SECTION_MISSING')
    a = source.index(start)
    b = source.index(end, a + len(start))
    return source[:a] + source[b:]


def function(source, name):
    definitions = [x for x in ast.parse(source).body if isinstance(x, ast.FunctionDef) and x.name == name]
    require(len(definitions) == 1, 'FOCUSED_EXACT_FUNCTION:' + name)
    return ast.get_source_segment(source, definitions[0]) + '\n'


def exercise_source(source):
    source = remove_section(source, '    def factory(cursor,today):\n',
                            '    # A committed positive payment is necessary')
    source = replace_once(source, "report.update(status='PASS',actual_Native_cases=9,strict_case_ids=list(cases.IDS),",
                          "report.update(status='INCOMPLETE',actual_Native_cases=0,strict_case_ids=[],")
    source = replace_once(source, '    access_runtime.run(product,state,access_fixture,verify,report)\n', '')
    source = replace_once(source, '    access_runtime.run_http(product,state,access_fixture,verify,report)\n', '')
    source = replace_once(source, 'access_runtime.run_browser(product,state,access_fixture,verify,report)',
                          'focused_browser(product,state,access_fixture,verify,report)')
    return source


def browser_source(source):
    source = replace_once(source, 'modes.AUDITOR=ROOT', 'modes.AUDITOR=DRIVER')
    return replace_once(source, 'actual_browser_cases=2,actual_business_cases=17',
                        'actual_browser_cases=2,actual_business_cases=2')


def inner_source(source):
    for old, new in (
        ('actual_two_session_races\']=4', 'actual_two_session_races\']=0'),
        ('actual_Native_cases\']=9', 'actual_Native_cases\']=0'),
        ('actual_Auth_HTTP_cases\']=2', 'actual_Auth_HTTP_cases\']=0'),
        ('actual_business_cases\']=17', 'actual_business_cases\']=2'),
        ('real_Auth_HTTP_qualified\']=True', 'real_Auth_HTTP_qualified\']=False'),
        ('actual_Mandor_browser_acceptance_pending\']=False', 'actual_Mandor_browser_acceptance_pending\']=True'),
    ):
        source = replace_once(source, old, new)
    return replace_once(source, "report=dict(label=LABEL,status='INCOMPLETE',",
                        "report=dict(label=LABEL,status='INCOMPLETE',diagnostic_only=True,formal_case_credit=0,")


def build_function(source, name, scope):
    exec(compile(source, 'mandor_mobile_focus:' + name, 'exec'), scope)
    return scope[name]


def write(name, value):
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / (FOCUS + '_' + name + '.json')).write_text(json.dumps(value, indent=2, default=str) + '\n')


def preflight():
    head = git(DRIVER, 'rev-parse', 'HEAD')
    require(head == os.environ['GITHUB_SHA'] and git(DRIVER, 'rev-parse', 'HEAD^') == PATCH, 'FOCUSED_EXACT_UI_SUCCESSOR')
    require(git(AUDITOR, 'rev-parse', 'HEAD') == LEGACY, 'FOCUSED_EXACT_OWNING_BASE')
    changed = set(git(DRIVER, 'diff', '--name-only', PATCH, 'HEAD').splitlines())
    require(changed == {'.github/workflows/cp7-mandor-shop-native17.yml',
                        str(NS / 'mobile_transaction_case.mjs'), str(NS / 'mobile_transaction_focus.py')},
            'FOCUSED_EXACT_DIAGNOSTIC_DELTA')
    require(os.environ.get('GITHUB_REF') == BRANCH and os.environ.get('GITHUB_RUN_ATTEMPT') == '1',
            'FOCUSED_DISPOSABLE_REF_AND_FIRST_ATTEMPT_REQUIRED')
    require(os.environ.get('MANDOR_NATIVE_CONFIRM') == 'cp6_rollback' and
            os.environ.get('AUDITOR_UI_MODE') == 'DISPOSABLE' and
            os.environ.get('PGURL') == 'postgresql://postgres:postgres@127.0.0.1:54322/postgres',
            'FOCUSED_FIXED_LOCAL_DISPOSABLE_ONLY')
    require(git(DRIVER, 'diff', '--name-only', LEGACY, 'HEAD', '--', 'src', 'index.html',
                'package.json', 'package-lock.json', 'tsconfig*.json', 'vite.config.ts', 'supabase') == CSS,
            'FOCUSED_ONLY_REVIEWED_CSS_IN_PRODUCT')
    require(sha256((DRIVER / CSS).read_bytes()).hexdigest() == CSS_SHA, 'FOCUSED_VERIFIED_CSS_BYTES_REQUIRED')
    require(git(DRIVER, 'diff', '--quiet', 'HEAD', '--') == '', 'FOCUSED_UI_WORKTREE_CHANGED')
    host = Path('scripts/current-s03-sku-s05-composite-qualification/host.mjs')
    require((DRIVER / host).read_bytes() == (AUDITOR / host).read_bytes(), 'FOCUSED_UNCHANGED_BROWSER_HOST_REQUIRED')
    require((DRIVER / NS / 'browser.mjs').read_bytes() == (AUDITOR / NS / 'browser.mjs').read_bytes(),
            'FOCUSED_UNCHANGED_BROWSER_CALLBACKS_REQUIRED')
    now = datetime.now(ZoneInfo('Asia/Jakarta'))
    midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    require((midnight - now).total_seconds() > BUDGET + 15 * 60, 'FOCUSED_WIB_WINDOW_WITH_SETUP_RESERVE')
    return dict(head=head, legacy_tool_head=LEGACY, css_sha256=CSS_SHA, run_id=os.environ['GITHUB_RUN_ID'],
                attempt=1, diagnostic_only=True, formal_case_credit=0, actual_sql_in_preflight=0)


def source_controls():
    inputs = (
        ('component.py', 'exercise', exercise_source),
        ('access_runtime.py', 'run_browser', browser_source),
    )
    for path, name, derive in inputs:
        raw = (AUDITOR / NS / path).read_text()
        compile(derive(function(raw, name)), 'focused:' + name, 'exec')
    package = load('focused_preflight_package_engine', AUDITOR / NS / 'package_engine.py')
    io = load('focused_preflight_report_io', AUDITOR / 'scripts/current-mandor-afui-preparation/report_io.py')
    engine, _ = package.derive((AUDITOR.parent / 'qualified-afui-parent' / package.ORIGINAL).read_bytes())
    engine, _ = io.derive_packet(engine, 'mandor17')
    compile(inner_source(function(io.derive_parent_install(engine), 'run_inner')), 'focused:run_inner', 'exec')
    return {'source_controlled_functions': [name for _, name, _ in inputs] + ['run_inner']}


def focused_work():
    identity = preflight()
    sys.path.insert(0, str(AUDITOR / NS))
    import qualification
    engine = qualification.runtime()
    # Capture the exact owning package, with its original data and restore authority.
    with engine.inherited_admission.parent_scope():
        import component, access_runtime, package_engine, package_identity
        import cp6_auditor_business_day as business_day
        io = load('focused_complete_report_io', AUDITOR / 'scripts/current-mandor-afui-preparation/report_io.py')
        source, _ = package_engine.derive(Path(engine.__file__).read_bytes())
        source, _ = io.derive_packet(source, 'mandor17')
        source = io.derive_parent_install(source)
        worker_scope = engine.__dict__
        build_function(inner_source(function(source, 'run_inner')), 'run_inner', worker_scope)
        browser_scope = dict(access_runtime.__dict__, DRIVER=DRIVER)
        focused_browser = build_function(browser_source(inspect.getsource(access_runtime.run_browser)), 'run_browser', browser_scope)
        exercise_scope = dict(component.__dict__, focused_browser=focused_browser)
        exercise = build_function(exercise_source(inspect.getsource(component.exercise)), 'exercise', exercise_scope)
        engine.runner.exercise = lambda conn, cur, database, url, report, state: exercise(
            engine.product, engine.trusted_installer_connection, conn, cur, database, url, report, state)
        engine.LABEL = FOCUS
        engine.OUT = OUTPUT / (FOCUS + '_OWNING.json')
        run_package = io.private_package_run(engine.package, OUTPUT, lambda browser_mode=False: engine.run())
        policy = load('focused_single_attempt_policy', AUDITOR / 'scripts/current-de-free-date-preparation/attempt_policy.py')
        write('IDENTITY', identity)
        with io.package_identity_scope(package_identity), policy.single_attempt(business_day):
            run_package('install')


def verify_browser_handoff(p, directory, actual, verified, ids):
    desktop_id, mobile_id = ids
    desktop, mobile = actual['cases'][desktop_id], actual['cases'][mobile_id]
    p.exact(desktop['source'], mobile['source'], 'BROWSER_PAIR_SAME_PAYROLL_AND_SALE')
    p.exact(desktop['business_day'], mobile['business_day'], 'BROWSER_PAIR_SAME_BUSINESS_DAY')
    desktop_after = desktop['complete_census_proofs'][-1]['original_after']
    mobile_before = mobile['complete_census_proofs'][0]['original_before']
    snapshots = []
    for reference in (desktop_after, mobile_before):
        name = reference['name']
        p.exact(reference, verified['original_observations'][name], 'BROWSER_PAIR_VERIFIED_HANDOFF_CENSUS')
        raw = gzip.decompress((directory / name).read_bytes())
        snapshots.append(p.pinned(raw, {key: reference[key] for key in ('bytes', 'sha256')},
                                  'BROWSER_PAIR_EXACT_HANDOFF_CENSUS'))
    left, right = snapshots
    for key in ('invoice', 'allocation_states', 'deductions', 'payroll'):
        p.exact(left[key], right[key], 'BROWSER_PAIR_SAME_BUSINESS_STATE:' + key)
    tables = ('cp7_mandor_shop.allocations', 'cp7_mandor_shop.allocation_events',
              'cp7_mandor_shop.requests', 'cp7_mandor_shop.deduction_links',
              'erp.payroll_deductions', 'erp.payroll_settlements')
    # Each case has its own real Auth user. The full-table census binds
    # requests across actors while the case-level request view is actor-specific.
    for table in tables:
        p.exact(left['full_data_and_sequences'][table], right['full_data_and_sequences'][table],
                'BROWSER_PAIR_SAME_HANDOFF_TABLE:' + table)
    allocation = desktop['actual_first_reply']['allocation_id']
    released = [row for row in right['allocation_states'] if row['allocation_id'] == allocation]
    require(len(released) == 1 and released[0]['state'] == 'RELEASED',
            'BROWSER_PAIR_DESKTOP_RELEASE_PRESENT_AT_MOBILE_ENTRY')
    return dict(desktop_case_id=desktop_id, mobile_case_id=mobile_id,
                desktop_after=desktop_after, mobile_before=mobile_before,
                released_allocation_id=allocation, unchanged_tables=list(tables))


def terminal_gate():
    identity = preflight()
    sys.path.insert(0, str(AUDITOR / NS))
    import browser_gate, browser_preflight, final_gate, qualification
    qualification.actual_parent()
    p = final_gate.packet_reader()
    main = p.strict((OUTPUT / (FOCUS + '_OWNING.json')).read_bytes())
    p.fields(main, dict(status='PASS', diagnostic_only=True, formal_case_credit=0,
        actual_business_cases=2, actual_browser_cases=2, actual_Native_cases=0, actual_Auth_HTTP_cases=0,
        actual_two_session_races=0, cp6_restored=True, restore_raw_public_equal=True,
        baseline_full22_all_rows_all_sequences_equal=True, baseline_advisors_equal=True, advisor_gate=True,
        used_guard_refused_before_DDL=True), 'FOCUSED_EXACT_BROWSER_PAIR_AND_RESTORE')
    package = p.strict((OUTPUT / 'T3_PACKAGE_INSTALL.json').read_bytes())
    p.exact(package['gate'], p.GATES, 'FOCUSED_ALL_FIVE_ACTUAL_PACKAGE_GATES')
    p.fields(package['run_identity'], dict(tool_head=LEGACY, github_sha=identity['head'],
        run_id=identity['run_id'], run_attempt='1', job=os.environ['GITHUB_JOB']), 'FOCUSED_PACKAGE_RUN_IDENTITY')
    backup = p.strict((OUTPUT / 'T3_BACKUP_RESTORE_DRILL.json').read_bytes())
    p.fields(backup, dict(status='RESTORED_IDENTICAL'), 'FOCUSED_COMPLETE_BACKUP_DRILL')
    require(backup['checks'] and all(check is True for check in backup['checks'].values()),
            'FOCUSED_EVERY_TYPED_BACKUP_CHECK_REQUIRED')
    p.exact(backup['data']['differ'], {}, 'FOCUSED_BACKUP_NO_ROW_DIFFERENCE')
    owned = p.strict((OUTPUT / (FOCUS + '_WORKER.json')).read_bytes())
    p.fields(owned, dict(status='WORKER_COMPLETED_AND_REAPED', worker_exit=0, process_group_empty=True,
                        process_tree_empty=True, head=identity['head'], run_id=identity['run_id']), 'FOCUSED_WORKER_REAPED')
    p.exact(set(main['committed']), {final_gate.CASE}, 'FOCUSED_ONE_COMPONENT')
    part = main['committed'][final_gate.CASE]
    for prefix in ('DESKTOP', 'MOBILE390'):
        for path in (DRIVER / 'cp6-proof/t3').glob(f'MANDOR_{prefix}_*.png'):
            require(path.is_file() and not path.is_symlink(), 'FOCUSED_SCREENSHOT_FILE_REQUIRED')
            with (OUTPUT / path.name).open('xb') as target:
                target.write(path.read_bytes())
    browser = browser_gate.gate(p, OUTPUT, part, qualification.FROZEN)
    actual = p.strict((OUTPUT / 'MANDOR_BROWSER2_ORIGINAL.json').read_bytes())
    handoff = verify_browser_handoff(p, OUTPUT, actual, browser, browser_preflight.IDS)
    write('GATE', {**identity, **browser, 'status': 'BROWSER_PAIR_PASS', 'full_restoration': True,
                   'browser_handoff': handoff,
                   'five_package_gates': True, 'production_go': False, 'independent_acceptance': False})
    print(json.dumps(dict(status='BROWSER_PAIR_PASS', formal_case_credit=0, full_restoration=True)), flush=True)


def main():
    require(Path.cwd() == WRITER, 'FOCUSED_EXACT_WRITER_CWD')
    mode = sys.argv[1:]
    if mode == ['--cleanup-check']:
        path = OUTPUT / (FOCUS + '_WORKER.json')
        if path.exists():
            require(json.loads(path.read_text()).get('process_tree_empty') is True, 'FOCUSED_WORKER_STILL_ALIVE')
    elif mode == ['--check']:
        print(json.dumps({**preflight(), **source_controls()}), flush=True)
    elif mode == ['--work']:
        focused_work()
    elif mode == ['--verify']:
        terminal_gate()
    elif mode == ['--run']:
        identity = preflight()
        start = float(os.environ['MANDOR_NATIVE_JOB_START_MONOTONIC'])
        now = time.monotonic()
        require(0 < start <= now < start + WORK, 'FOCUSED_WORK_BUDGET_REQUIRED')
        write('WORKER', {**identity, 'status': 'STARTING', 'process_tree_empty': False})
        supervisor = load('focused_original_child_supervisor', AUDITOR / 'scripts/current-de-free-date-preparation/runtime_supervisor.py')
        result = supervisor.supervise([sys.executable, '-u', '-B', __file__, '--work'],
                                      work_seconds=start + WORK - now, recovery_seconds=RECOVERY)
        write('WORKER', {**identity, **result})
        print(json.dumps(result), flush=True)
        require(result['status'] == 'WORKER_COMPLETED_AND_REAPED', 'FOCUSED_SUPERVISED_RUNTIME_INCOMPLETE')
    else:
        raise ValueError('FOCUSED_FIXED_COMMAND_REQUIRED')


if __name__ == '__main__':
    main()
