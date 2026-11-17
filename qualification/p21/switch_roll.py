"""Switch Roll qualification on the same P21 disposable application database."""
from hashlib import sha256
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch
from urllib.parse import urlsplit


BROWSER_CASE = 'P21_SWITCH_ROLL_UI_JOURNAL'
RPCS = ('erp_get_my_access_v1', 'erp_cp7_get_switch_roll_v1',
        'erp_cp7_preview_switch_roll_v1', 'erp_cp7_switch_roll_v1')
NATIVE_CASES = (
    ('all_sold', {'sold': 10}, 'native_case'),
    ('fg_and_sold', {'sold': 4}, 'native_case'),
    ('wip', {'sold': 0}, 'native_case'),
    ('closed', {'closed': True}, 'native_case'),
    ('downstream_average', {'later_use': True}, 'downstream_average'),
    ('cross_material', {'cross_material': True}, 'cross_material'),
)
EXPECTED_FLAGS = ('preuse_inverse', 'immutable_old_candidate', 'browser_authorized', 'browser_replay',
                  'real_ui_scope', 'all_native_passed', 'journal_cogs_delta_50000', 'used_inverse_refused',
                  'generated_public_types_match', 'browser_process_empty')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def product_checkout():
    base = Path(os.environ['GITHUB_WORKSPACE']) / 'switch-roll-product'
    head = os.environ['CP7_P21_SWITCH_ROLL_HEAD']
    tree = os.environ['CP7_P21_SWITCH_ROLL_TREE']
    identity = subprocess.check_output(('git','-C',str(base),'rev-parse','HEAD','HEAD^{tree}', 'HEAD^'), text=True).splitlines()
    from .preflight import PRODUCT
    require(identity == [head, tree, PRODUCT['head']], 'CP7_SWITCH_ROLL_SUCCESSOR_IDENTITY')
    require(not subprocess.check_output(('git','-C',str(base),'status','--porcelain','--untracked-files=no')),
            'CP7_SWITCH_ROLL_SUCCESSOR_SOURCE_DRIFT')
    return base


def auth_scope(original):
    return type(original)(connect=original.connect, transport=original.transport, retain=original.retain,
        attempt=original.attempt, head=original.head, allowed_actors=(('OWNER','p21-switch-roll'),), allowed_rpcs=RPCS)


def derive_browser_host(product):
    directory = product / 'scripts/current-s03-sku-s05-composite-qualification'
    raw = (directory / 'host.mjs').read_text(encoding='utf-8')
    original_login = '''    await page.getByRole('button', { name: 'Masuk', exact: true }).click()
    await expect(page.locator('.top-title strong')).toBeVisible()
    return { page, context: ctx, user: { id: user.id, role }, rpc: (name, args) => rpc(user.token, name, args) }'''
    actual_login = '''    const responseReady = page.waitForResponse(r => r.url().includes('/auth/v1/token?grant_type=password'))
    await page.getByRole('button', { name: 'Masuk', exact: true }).click()
    const response = await responseReady
    assert.equal(response.status(), 200, 'CP7_SWITCH_ROLL_REAL_GOTRUE_LOGIN')
    const session = await response.json()
    for (const key of [session.access_token, session.refresh_token]) redact(key)
    assert.ok(session.access_token && session.user.id === user.id, 'CP7_SWITCH_ROLL_REAL_GOTRUE_IDENTITY')
    await expect(page.locator('.top-title strong')).toBeVisible()
    return { page, context: ctx, user: { id: user.id, role }, rpc: (name, args) => rpc(session.access_token, name, args) }'''
    for before, after in (
        (r'/\/cp6_auditor_browser$/', r'/^postgresql:\/\/(?:postgres|supabase_admin)(?::[^@]*)?@(?:127\.0\.0\.1|localhost):54322\/cp6_rollback$/'),
        ('restPort = 54329', 'restPort = Number(process.env.CP7_P21_SWITCH_REST_PORT)'),
        ("const uiMode = (process.env.AUDITOR_UI_MODE || 'DISPOSABLE').toUpperCase()", '''const uiMode = 'DISPOSABLE'
const subject = JSON.parse(process.env.CP7_P21_SWITCH_BROWSER_SUBJECT)
delete process.env.CP7_P21_SWITCH_BROWSER_SUBJECT
assert.ok(Number.isInteger(restPort) && restPort >= 32768 && restPort <= 65535)
assert.match(subject.email, /^cp7-global-auth-[a-f0-9]{32}@example[.]invalid$/)'''),
        ('const secrets = [anon, service], users = []', 'const secrets = [anon, service, subject.email, subject.password], users = []'),
        ('    const user = await createUser(role, label)', "    const user = subject\n    assert.equal(role, 'OWNER', 'CP7_SWITCH_ROLL_BROWSER_OWNER_REQUIRED')"),
        (original_login, actual_login),
    ):
        require(raw.count(before)==1,'CP7_SWITCH_ROLL_EXACT_BROWSER_HOST_ANCHOR')
        raw=raw.replace(before,after,1)
    host = directory / '.p21-switch-roll-host.mjs'
    with host.open('x',encoding='utf-8') as stream:
        stream.write(raw)
    return host


def browser_subject(auth, fixture):
    role, label = next(iter(auth.allowed_actors))
    credentials = {}
    wire = auth.transport.auth

    def capture(path, body, admin=False, method='POST'):
        reply = wire(path, body, admin=admin, method=method)
        if path == 'token?grant_type=password' and reply['status'] == 200:
            require(not credentials, 'CP7_SWITCH_ROLL_SINGLE_BROWSER_SUBJECT')
            credentials.update(email=body['email'], password=body['password'])
        return reply

    try:
        with patch.object(auth.transport, 'auth', capture):
            actor = auth.login(role, label)
        profile = actor.rpc(RPCS[0], {})
        require(profile['status']==200 and profile['body']['allowed'] is True, 'CP7_SWITCH_ROLL_BROWSER_PROFILE')
        workspace = actor.rpc(RPCS[1], {'p_purchase':fixture['source_purchase']})
        require(workspace['status']==200 and any(row['issue_id']==fixture['payload']['issue_id']
                    for row in workspace['body']['issues']), 'CP7_SWITCH_ROLL_REST_SCHEMA_READY')
        subject = auth.subjects[(role,label)]
        require(credentials.get('email')==subject.email and subject.uid and credentials.get('password'),
                'CP7_SWITCH_ROLL_BROWSER_SUBJECT_REQUIRED')
        return dict(id=subject.uid, **credentials)
    finally:
        credentials.clear()


SUPERVISE_BROWSER = '''import json, runpy, sys
from pathlib import Path
source, host, receipt = sys.argv[1:]
supervise = runpy.run_path(source)['supervise']
result = supervise(('node', host), work_seconds=390, recovery_seconds=15)
Path(receipt).write_text(json.dumps(result), encoding='ascii')
sys.exit(0 if result['status'] == 'WORKER_COMPLETED_AND_REAPED' else 1)
'''


def browser(auth, product, day, output, fixture):
    user = browser_subject(auth, fixture)
    endpoint = urlsplit(auth.transport.url)
    require(endpoint.scheme=='http' and endpoint.hostname=='127.0.0.1' and endpoint.path=='',
            'CP7_SWITCH_ROLL_BROWSER_LOOPBACK_ONLY')
    host = derive_browser_host(product)
    raw = output/'CP7_SWITCH_ROLL_BROWSER_ORIGINAL.json'
    supervised = output/'CP7_SWITCH_ROLL_BROWSER_PROCESS.json'
    supervisor = host.with_name('runtime_supervisor.py')
    anon, service = auth._keys
    environment = dict(os.environ,AUDITOR_BROWSER_SCRIPT=str(product/'scripts/cp7_switch_roll_browser.mjs'),
        AUDITOR_BROWSER_DB_URL=auth.url,AUDITOR_BROWSER_OUT=str(raw),AUDITOR_BROWSER_TODAY=day.isoformat(),
        AUDITOR_BROWSER_CASE_TIMEOUT_MS='150000',SUPABASE_ANON_KEY=anon,SUPABASE_SERVICE_ROLE_KEY=service,
        CP7_P21_SWITCH_REST_PORT=str(endpoint.port), CP7_P21_SWITCH_BROWSER_SUBJECT=json.dumps(user),
        P21_SWITCH_ROLL_FIXTURE=json.dumps(fixture))
    user.clear()
    try:
        result = subprocess.run((sys.executable, '-B', '-c', SUPERVISE_BROWSER, str(supervisor), str(host), str(supervised)),
            cwd=product,env=environment,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=False)
    finally:
        host.unlink()
        environment.clear()
    require(raw.is_file(),'CP7_SWITCH_ROLL_BROWSER_RECEIPT_REQUIRED')
    require(supervised.is_file(), 'CP7_SWITCH_ROLL_BROWSER_PROCESS_RECEIPT_REQUIRED')
    process = json.loads(supervised.read_bytes())
    proof = json.loads(raw.read_bytes())
    case = proof.get('cases',{}).get(BROWSER_CASE,{})
    require(result.returncode==0 and proof['status']=='RUN_COMPLETE' and proof['planned']==[BROWSER_CASE]
            and proof['real_auth'] is True and proof['product_responses_mocked'] is False
            and proof['blocked_requests']==0 and not proof['auth_cleanup_failures']
            and process.get('process_group_empty') is True and process.get('process_tree_empty') is True
            and case.get('status')=='PASS' and case.get('real_auth') is True
            and case.get('real_ui_save') is True and case.get('lost_reply_recovered') is True
            and case.get('layout_320_390_1440') is True,'CP7_SWITCH_ROLL_BROWSER_CASE_INCOMPLETE')
    return dict(status='PASS',sha256=sha256(raw.read_bytes()).hexdigest(),
                lost_reply_recovered=True,layout_320_390_1440=True,process_tree_empty=True)


def exercise(conn, cur, state, report, *, lifecycle, candidate, auth, package):
    from global_owning import owning, p20_batch
    product = product_checkout()
    base = p20_batch.product_checkout(candidate)
    day = lifecycle.foundation.day
    output = Path(candidate)/'cp6-proof/t3'
    roots = [product/'scripts',*(base/'scripts/cp7_customer_credit'/s for s in
                               ('consumer','native','initial-settlement','reconciliation/native'))]
    with owning.import_paths(*roots):
        install = importlib.import_module('cp7_switch_roll_install')
        cases = importlib.import_module('cp7_switch_roll_cases')
        prepare = importlib.import_module('global_owning.p20.native').prepare
        prior = install.public_catalog(cur)
        installed = install.install(cur)
        install.remove_preuse(cur)
        require(install.public_catalog(cur)==prior and cur.execute("select to_regnamespace('cp7_switch_roll')").fetchone()==(None,),
                'CP7_SWITCH_ROLL_PREUSE_INVERSE_RESIDUE')
        conn.rollback()
        auth.begin(conn,cur,package.boundary.ADMIN,package.boundary.PRIMARY_ADMIN,
                   lambda observer: lifecycle.verify(observer,state),report)
        proof = install.install(cur)
        require(proof==installed,'CP7_SWITCH_ROLL_INSTALL_SOURCE_CHANGED')
        cur.execute("notify pgrst, 'reload schema'")
        conn.commit()
        from global_owning import installed_types
        generator = installed_types.load_exact(candidate, installed_types.GENERATOR, installed_types.GENERATOR_SHA)
        type_path = output/'database.switch-roll-disposable.generated.ts'
        type_receipt = generator.generate(package.boundary.PG,type_path)
        before_names = installed_types.public_erp_names((output/installed_types.TYPE_FILE).read_bytes())
        after_names = installed_types.public_erp_names(type_path.read_bytes())
        require(after_names==before_names|set(RPCS[1:]), 'CP7_SWITCH_ROLL_INSTALLED_TYPE_NAMES_CHANGED')
        native = {}
        for name,fixture_args,operation in NATIVE_CASES:
            try:
                prepare(cur)
                fixture = cases.seed(cur,day,**fixture_args)
                native[name] = getattr(cases,operation)(cur,fixture)
                require(native[name].get('status')=='PASS','CP7_SWITCH_ROLL_NATIVE_CASE_INCOMPLETE')
            except Exception:
                print('GLOBAL_ORDINARY_PHASE P21_SWITCH_ROLL_NATIVE_'+name.upper()+' FAILED',flush=True)
                raise
            finally:
                conn.rollback()
        prepare(cur)
        fixture = cases.seed(cur,day)
        before = cases.state(cur,fixture)
        conn.commit()
        ui = browser(auth,product,day,output,fixture)
        row = cur.execute('select result from cp7_switch_roll.corrections where issue_id=%s',
                          (fixture['payload']['issue_id'],)).fetchone()
        require(row is not None,'CP7_SWITCH_ROLL_BROWSER_COMMIT_DB_REQUIRED')
        cases.verify_saved(cur,fixture,before,row[0])
        conn.rollback()
        try:
            install.remove_preuse(cur)
        except ValueError as error:
            require(str(error)=='CP7_SWITCH_ROLL_AFTER_USE_FULL_RESTORE_REQUIRED',
                    'CP7_SWITCH_ROLL_USED_REFUSAL_CHANGED')
        else:
            raise ValueError('CP7_SWITCH_ROLL_USED_INVERSE_UNEXPECTEDLY_ALLOWED')
        finally:
            conn.rollback()
        return dict(status='PASS',preuse_inverse=True,immutable_old_candidate=True,browser_authorized=True,
            browser_replay=True,real_ui_scope=True,all_native_passed=True,journal_cogs_delta_50000=True,
            used_inverse_refused=True,generated_public_types_match=True,browser_process_empty=ui['process_tree_empty'],
            product=dict(head=os.environ['CP7_P21_SWITCH_ROLL_HEAD'],
            tree=os.environ['CP7_P21_SWITCH_ROLL_TREE']),installed=proof,native=native,ui=ui,generated_types=type_receipt)
