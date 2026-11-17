"""One installed P21 E14/E22 qualification with the retained owning lifecycle."""
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch
from urllib.parse import urlsplit
from uuid import uuid4

from . import mode, switch_roll
from .state_probe import write
from .retained import verify_retained


HERE = Path(__file__).resolve().parent
E22 = 'P21_E22_ISOLATION'
CHECKS = (E22,)
BROWSER_CASES = ('P21_E22_ANALYSIS_ISOLATION',)
ACTORS = (('OWNER','owner'), ('ADMIN','analyst'))
RPCS = (*switch_roll.RPCS, 'erp_cp7_get_analysis_attention_v1',
        'erp_cp7_capture_operational_analysis_v1')
ANALYST_GRANTS = ('dashboard.view','master.product.view','production.wip.view','warehouse.stock.view','sales.invoice.view')


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def auth_scope(original):
    return type(original)(connect=original.connect, transport=original.transport, retain=original.retain,
        attempt=original.attempt, head=original.head, allowed_actors=ACTORS, allowed_rpcs=RPCS)


def store_role(cur, code, permissions):
    role, = cur.execute('insert into erp.app_roles(role_code,role_name) values(%s,%s) returning id',
                        (code, code)).fetchone()
    for name in permissions:
        cur.execute('insert into erp.app_role_permissions(role_id,permission_key) values(%s,%s)', (role, name))
    return role


def provision(conn, cur, auth):
    role = store_role(cur,'P21_ANALYSIS_ONLY',ANALYST_GRANTS)
    conn.commit()
    credentials, users = {}, {}
    wire = auth.transport.auth

    def capture(path, body, admin=False, method='POST'):
        reply = wire(path, body, admin=admin, method=method)
        if path == 'token?grant_type=password' and reply['status'] == 200:
            require(not credentials, 'P21_FOLLOWUP_SINGLE_ACTOR_CREDENTIAL_CAPTURE')
            credentials.update(email=body['email'], password=body['password'])
        return reply

    for role, label in ACTORS:
        try:
            with patch.object(auth.transport, 'auth', capture):
                actor = auth.login(role, label)
            profile = actor.rpc(switch_roll.RPCS[0], {})
            require(profile['status']==200 and profile['body']['allowed'] is True, 'P21_FOLLOWUP_POSITIVE_PROFILE')
            subject = auth.subjects[(role,label)]
            require(credentials.get('email')==subject.email and subject.uid and credentials.get('password'),
                    'P21_FOLLOWUP_PREPARED_BROWSER_SUBJECT_REQUIRED')
            users[label] = dict(uid=subject.uid, role=role, **credentials)
        finally:
            credentials.clear()
    require(auth.verified_actors == len(ACTORS), 'P21_FOLLOWUP_ACTOR_COUNT')
    require(cur.execute('update erp.app_users set role_id=%s where auth_user_id=%s',
                        (role, users['analyst']['uid'])).rowcount==1,'P21_E22_ANALYSIS_ROLE_FIXTURE')
    conn.commit()
    return users


def populate(cur, day, cases, analysis, rule):
    fixture = cases.seed(cur, day)
    rule.due_fixture(cur, day)
    query = analysis.previous.baseline.history.query(day)
    return dict(switch_roll=fixture, analysis_query=query,
                finance_fields={'Periode laporan dari': fixture['source_date'],
                    'Periode laporan sampai': str(day), 'Posisi laporan pada': str(day)})


def derived_host(product):
    directory = product / 'scripts/current-s03-sku-s05-composite-qualification'
    text = (directory/'host.mjs').read_text(encoding='utf-8')
    old = """    await page.getByRole('button', { name: 'Masuk', exact: true }).click()
    await expect(page.locator('.top-title strong')).toBeVisible()
    return { page, context: ctx, user: { id: user.id, role }, rpc: (name, args) => rpc(user.token, name, args) }"""
    new = """    const replyReady = page.waitForResponse(r => r.url().includes('/auth/v1/token?grant_type=password'))
    await page.getByRole('button', { name: 'Masuk', exact: true }).click()
    const response = await replyReady
    assert.equal(response.status(), 200, 'P21_FOLLOWUP_REAL_GOTRUE_LOGIN')
    const session = await response.json()
    for (const key of [session.access_token, session.refresh_token]) redact(key)
    assert.ok(session.access_token && session.user.id === user.uid, 'P21_FOLLOWUP_REAL_GOTRUE_IDENTITY')
    if (blocked) await expect(page.getByRole('heading', { name:'Akun belum lolos guardrail' })).toBeVisible()
    else await expect(page.locator('.top-title strong')).toBeVisible()
    return { page, context: ctx, loginStatus: response.status(), user: { id: user.uid, role },
      rpc: (name,args) => rpc(session.access_token,name,args) }"""
    changes = (
        (r'/\/cp6_auditor_browser$/', r'/^postgresql:\/\/(?:postgres|supabase_admin)(?::[^@]*)?@(?:127\.0\.0\.1|localhost):54322\/cp6_rollback$/'),
        ('restPort = 54329', 'restPort = Number(process.env.CP7_P21_FOLLOWUP_REST_PORT)'),
        ("const uiMode = (process.env.AUDITOR_UI_MODE || 'DISPOSABLE').toUpperCase()", """const uiMode = 'DISPOSABLE'
const subjects = JSON.parse(process.env.CP7_P21_FOLLOWUP_SUBJECTS)
delete process.env.CP7_P21_FOLLOWUP_SUBJECTS
assert.ok(Number.isInteger(restPort) && restPort >= 32768 && restPort <= 65535)
for (const user of Object.values(subjects)) assert.match(user.email, /^cp7-global-auth-[a-f0-9]{32}@example[.]invalid$/)"""),
        ('const secrets = [anon, service], users = []',
         'const secrets = [anon, service, ...Object.values(subjects).flatMap(u => [u.email,u.password])], users = []'),
        ("label: 'AUDITOR_SCENARIO'", "label: 'WRITER_P21_FOLLOWUP'"),
        ("async login(role, { label = 'auditor', ...opts } = {}) {\n    const user = await createUser(role, label)",
         """async login(role, { label, blocked = false, ...opts } = {}) {
    const user = subjects[label]
    assert.equal(user?.role, role, 'P21_FOLLOWUP_ACTOR_SCOPE')"""),
        (old, new),
    )
    for before, after in changes:
        require(text.count(before)==1,'P21_FOLLOWUP_BROWSER_HOST_EXACT_ANCHOR')
        text = text.replace(before, after, 1)
    host = directory / '.p21-followup-host.mjs'
    host.write_text(text, encoding='utf8')
    return host


def run_browser(auth, product, day, output, fixture, users):
    endpoint = urlsplit(auth.transport.url)
    require(endpoint.scheme=='http' and endpoint.hostname=='127.0.0.1' and not endpoint.path,
            'P21_FOLLOWUP_BROWSER_LOOPBACK_ONLY')
    host = derived_host(product)
    receipt, proc = output/'browser-original.json', output/'browser-process.json'
    supervisor = host.with_name('runtime_supervisor.py')
    anon, service = auth._keys
    environment = dict(os.environ,
        AUDITOR_BROWSER_SCRIPT=str(HERE/'followup_browser.mjs'),
        AUDITOR_BROWSER_DB_URL=auth.url,
        AUDITOR_BROWSER_OUT=str(receipt), AUDITOR_BROWSER_TODAY=day.isoformat(),
        AUDITOR_BROWSER_CASE_TIMEOUT_MS='195000', SUPABASE_ANON_KEY=anon, SUPABASE_SERVICE_ROLE_KEY=service,
        CP7_P21_FOLLOWUP_REST_PORT=str(endpoint.port), CP7_P21_FOLLOWUP_SUBJECTS=json.dumps(users),
        CP7_P21_FOLLOWUP_FIXTURE=json.dumps(fixture,default=str), CP7_P21_FOLLOWUP_RAW=str(output),
        CP7_P21_STATE_SCRIPT=str(HERE/'state_probe.py'))
    users.clear()
    code = switch_roll.SUPERVISE_BROWSER.replace('work_seconds=390','work_seconds=710')
    try:
        child = subprocess.run((sys.executable,'-B','-c',code,str(supervisor),str(host),str(proc)),
            cwd=product,env=environment,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=False)
    finally:
        host.unlink()
        environment.clear()
    require(receipt.is_file() and proc.is_file(), 'P21_FOLLOWUP_BROWSER_RECEIPTS_REQUIRED')
    report = json.loads(receipt.read_bytes())
    process = json.loads(proc.read_bytes())
    require(child.returncode==0 and process['process_group_empty'] and process['process_tree_empty'],
            'P21_FOLLOWUP_BROWSER_PROCESS_NOT_REAPED')
    require(report['status']=='RUN_COMPLETE' and report['planned']==list(BROWSER_CASES)
            and report['real_auth'] is True and report['product_responses_mocked'] is False
            and report['blocked_requests']==0 and not report['console_errors'] and not report['auth_cleanup_failures'],
            'P21_FOLLOWUP_REAL_BROWSER_INCOMPLETE')
    return report


def check_browser_case(value):
    return bool(value.get('status')=='PASS' and value.get('business_day',{}).get('before')
                == value.get('business_day',{}).get('after') == value.get('business_day',{}).get('planned'))


def exercise(conn,cur,state,report,*,lifecycle,candidate,make_lanes,checkpoint,auth,package):
    del make_lanes
    from global_owning import owning, p20_batch
    from .installed import verify_loopback
    import importlib

    require(mode.enabled(), 'P21_FOLLOWUP_EXACT_MODE')
    verify_loopback(conn,cur)
    product = switch_roll.product_checkout()
    base = p20_batch.product_checkout(candidate)
    day = lifecycle.foundation.day
    output = Path(candidate)/'cp6-proof/t3/P21_FOLLOWUP_ORIGINALS'
    output.mkdir(mode=0o700, exist_ok=False)
    reused = verify_retained()
    report['p21_followup_retained'] = reused
    write(output/'retained-originals.json', reused)
    results = report['p21_installed_checks'] = {}
    try:
        p20_batch.progress('P21_FOLLOWUP_FIXTURES','STARTED')
        roots = [product/'scripts',*(base/'scripts/cp7_customer_credit'/part for part in
                                     ('consumer','native','initial-settlement','reconciliation/native'))]
        with owning.import_paths(*roots):
            install = importlib.import_module('cp7_switch_roll_install')
            cases = importlib.import_module('cp7_switch_roll_cases')
            analysis = importlib.import_module('cp7_analysis_cases')
            rule = importlib.import_module('cp7_rule_source_cases')
            prepare = importlib.import_module('global_owning.p20.native').prepare
            # Bind the owning Auth lifecycle to the exact Global installation,
            # before installing the additive, source-bound Switch Roll functions.
            auth.begin(conn,cur,package.boundary.ADMIN,package.boundary.PRIMARY_ADMIN,
                       lambda observer: lifecycle.verify(observer,state),report)
            installed = install.install(cur)
            require(installed['source_sha256'] == 'dac3f026f2b2b7d891fc0106fd1960f55c39959aa6756611f45c8179df8e1422'
                    and installed['public_rpc_count']==3 and installed['predecessor_public_functions_preserved'],
                    'P21_FOLLOWUP_SWITCH_ROLL_INSTALL_SOURCE')
            conn.commit()
            write(output/'switch-roll-install-original.json',installed)
            users = provision(conn, cur, auth)
            prepare(cur)
            fixture = populate(cur,day,cases,analysis,rule)
            cur.execute('reset session authorization')
            cur.execute("notify pgrst, 'reload schema'")
            conn.commit()
        write(output/'fixture-identity.json',dict(product=reused['product'], business_day=str(day), fixture=fixture))
        p20_batch.progress('P21_FOLLOWUP_FIXTURES','COMPLETED')
        p20_batch.progress('P21_FOLLOWUP_REAL_GOTRUE_BROWSER','STARTED')
        # Verify the installed clone routes through the retained transport
        # before any browser login. Retain the same worker-owned cleanup.
        actor = auth._actors[ACTORS.index(('OWNER','owner'))]
        readiness = actor.rpc(switch_roll.RPCS[1], {'p_purchase':fixture['switch_roll']['source_purchase']})
        require(readiness['status']==200 and readiness['body']['issues'],'P21_FOLLOWUP_REST_SCHEMA_READY')
        browser = run_browser(auth,product,day,output,fixture,users)
        p20_batch.progress('P21_FOLLOWUP_REAL_GOTRUE_BROWSER','COMPLETED')
        analysis = browser['cases'][BROWSER_CASES[0]]
        e22 = check_browser_case(analysis)
        native_role = reused['prior_e14_and_compute_role']['cp7_capture_writer_denied']
        results[E22] = dict(status='PASS' if e22 and native_role else 'INCOMPLETE', real_browser=e22,
                           compute_role_denied=native_role, analysis=analysis)
    except Exception as error:
        report['p21_followup_exception'] = p20_batch.bounded_failure(error)
        write(output/'first-failure.json', report['p21_followup_exception'])
    finally:
        conn.rollback()
        for name in CHECKS:
            if name not in results:
                results[name] = dict(status='INCOMPLETE', first_failure=report.get('p21_followup_exception',
                                     dict(code='P21_FOLLOWUP_PROBE_NOT_OBSERVED')))
            elif results[name]['status'] != 'PASS':
                results[name]['first_failure'] = dict(code=name+'_BROWSER_INCOMPLETE')
            checkpoint(name, results[name])
    return results


def proven(results):
    return bool(set(results)==set(CHECKS) and results[E22]['status']=='PASS'
                and results[E22]['real_browser'] is True and results[E22]['compute_role_denied'] is True)
