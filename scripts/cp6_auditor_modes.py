"""Two-session and real-HTTP modes of the auditor runtime (scripts/cp6_auditor_scenario.py). Label AUDITOR_SCENARIO: not
release evidence, production_go=false.

The ordinary auditor cases run in one connection, inside a savepoint that is rolled back, so a second session cannot see
their fixtures, identity or the test-only schema grant (audit of 9add57e: two race runs refused while setting up). These
modes give the auditor committed state instead:

RACES   the scenario may define races(tools, today) -> [(race_id, zero_argument_callable), ...]. Before each callable the
        runtime makes a fresh copy (createdb -T) of the installed clone, commits the same setup the savepoint cases get
        (seed when empty, open period from 2026-08-31, and the test-only grant USAGE on schema erp to authenticated that
        the writer's private-schema fixtures need), and hands over tools: tools.admin (URL of the copy), tools.connect(),
        tools.two_sessions(first_op, second_op, commit) (the AW probe's schedule: the holder runs first_op and keeps its
        transaction open, a worker runs second_op in its own session, then the holder commits or aborts), tools.api
        (identity helpers: api.ordinary(cur), api.admin(cur)), tools.awp, tools.azp, tools.chain. A race commits
        whatever it needs; the copy is dropped afterwards.
HTTP    the scenario may define http_cases(http, today) -> [(case_id, zero_argument_callable), ...]. The runtime makes one
        committed copy (same setup, WITHOUT the schema grant: only public facades are reachable, as in production),
        serves it through its own PostgREST container (the stack's image and settings, database switched to the copy) and
        gives http.login(role_code, label) -> a user created in the stack's real Auth (admin API), bound to erp.app_users
        with that role in the copy, and signed in with its password; user.rpc(name, args) and http.anon_rpc(name, args)
        return dict(status, body) from the real PostgREST; http.connect() reads the copy as admin. No JWT is signed
        here: tokens come only from the Auth login. Cases run in order on the same copy. Every created Auth user, the
        container and the copy are removed; Auth row counts of the primary database must return to their start.
BROWSER (independent audit B4, GATE-04/08) the auditor supplies an ES module (workflow input browser_b64) exporting
        cases(ui, today) -> [[case_id, async () => ({status, ...})], ...]. The runtime makes one committed copy (same
        setup as HTTP, without the schema grant), serves it through its own PostgREST container, builds this branch's UI
        against a loopback proxy (Auth and public RPC only) and runs the module in Playwright
        (scripts/cp6_auditor_browser_host.mjs): ui.login(role) signs a new real Auth user in through the login form. Users,
        container, UI server and copy are removed; Auth row counts of the primary database must return to their start.
The stack's anon and service keys are masked in the job log (::add-mask::). The per-user password and access token are
never printed, not even as ::add-mask:: lines.
"""
from pathlib import Path
from collections import Counter
from datetime import date
from urllib.parse import urlsplit,urlunsplit
import json,secrets,subprocess,tempfile,time,traceback,urllib.error,urllib.request,uuid
import psycopg

AUDITOR=Path(__file__).resolve().parents[1]
BASE=AUDITOR.parent/'base'/'cp5-local'
RACE_DB='cp6_auditor_race'
HTTP_DB='cp6_auditor_http'
BROWSER_DB='cp6_auditor_browser'
REST='cp6_auditor_rest'
REST_URL='http://127.0.0.1:54329'
AUTH_URL='http://127.0.0.1:54321/auth/v1/'
LABEL='AUDITOR_SCENARIO'


def _probe():
    import cp6_aw_probe as awp
    import cp6_az_probe as azp
    return awp,azp


def copy_db(name):
    awp,_=_probe()
    awp.r1.docker('dropdb','-U','supabase_admin','--if-exists','--force','--maintenance-db=template1',name)
    awp.r1.docker('createdb','-U','supabase_admin','--maintenance-db=template1','-T','cp6_rollback',name)
    return awp.boundary.ADMIN.rsplit('/',1)[0]+'/'+name


def drop_db(name):
    awp,_=_probe()
    awp.r1.docker('dropdb','-U','supabase_admin','--if-exists','--force','--maintenance-db=template1',name)
    with psycopg.connect(awp.boundary.PRIMARY_ADMIN) as conn,conn.cursor() as cur:
        return cur.execute('select count(*) from pg_database where datname=%s',(name,)).fetchone()[0]


def setup_copy(url,verify,grant):
    awp,_=_probe()
    api=awp.api
    with psycopg.connect(url) as conn,conn.cursor() as cur:
        runtime=verify(cur);conn.rollback()
        api.admin(cur)
        if grant and not cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]:
            cur.execute('grant usage on schema erp to authenticated')
        if not cur.execute('select count(*) from erp.app_users').fetchone()[0]:api.seed(cur)
        awp.boundary.historical.prior.set_open_period(cur,date(2026,8,31))
        today=cur.execute("select (statement_timestamp() at time zone 'Asia/Jakarta')::date").fetchone()[0]
        conn.commit()
    return dict(runtime=runtime,today=today,test_only_usage_grant=grant)


class RaceTools:
    """What a race receives; the URL stays the same while the copy behind it is made fresh for every race."""

    def __init__(self,url,today):
        awp,azp=_probe()
        self.admin=url;self.today=today;self.api=awp.api;self.awp=awp;self.azp=azp;self.chain=awp.chain

    def connect(self,**kwargs):return psycopg.connect(self.admin,**kwargs)

    def two_sessions(self,first_op,second_op,commit):
        return self.awp.two_sessions(self.admin,first_op,second_op,commit)


VOCABULARY=('PASS','FAIL','COUNTEREXAMPLE','INCOMPLETE')


def copy_sessions(database,exclude_users=()):
    """Client sessions on a committed copy, read from the primary (the copy's own admin connection is closed by then)."""
    awp,_=_probe()
    with psycopg.connect(awp.boundary.PRIMARY_ADMIN) as conn,conn.cursor() as cur:
        cur.execute('select pg_stat_clear_snapshot()')
        return cur.execute("""select pid,usename,application_name,state from pg_stat_activity where datname=%s
            and backend_type='client backend' and not (usename=any(%s)) order by pid""",(database,list(exclude_users))).fetchall()


def session_leaks(database,exclude_users=()):
    """Sessions a case left open on its copy (independent audit round 9, W7: the race and HTTP modes check what the savepoint
    group checks). A closing backend can stay listed briefly, so the list is re-read for up to 2 s; leaks are terminated."""
    others=copy_sessions(database,exclude_users)
    for _ in range(20):
        if not others:break
        time.sleep(0.1);others=copy_sessions(database,exclude_users)
    if others:
        awp,_=_probe()
        with psycopg.connect(awp.boundary.PRIMARY_ADMIN) as conn,conn.cursor() as cur:
            for pid,*_ in others:cur.execute('select pg_terminate_backend(%s)',(pid,))
    return [list(map(str,o)) for o in others]


def strict_rows(group,planned,run_one,database,exclude_users=()):
    """The strict group of the savepoint mode (scripts/cp6_auditor_runner.py) for the modes that run on committed copies
    (round 9, W7): duplicate ids refuse the whole group before any operation; a result that is not a dict or whose
    status is outside PASS/FAIL/COUNTEREXAMPLE/INCOMPLETE is INCOMPLETE (the original value is kept); a session left
    open on the copy makes the case INCOMPLETE; planned, final and missing are printed. Returns (rows, refusal)."""
    import cp6_auditor_runner as runner
    ids=[k for k,_ in planned]
    duplicates=runner.duplicate_ids(ids)
    if duplicates:
        print(json.dumps(dict(group=group,refused='AUDITOR_DUPLICATE_CASE_IDS',duplicates=duplicates)),flush=True)
        return {},dict(error='AUDITOR_DUPLICATE_CASE_IDS',duplicate_case_ids=duplicates)
    rows={}
    for i,(key,operation) in enumerate(planned):
        try:
            row=run_one(i,key,operation)
            if not isinstance(row,dict):row=dict(status='INCOMPLETE',error='AUDITOR_CASE_RESULT_NOT_A_DICT',result=repr(row)[:500])
        except Exception as exc:row=dict(status='INCOMPLETE',error=str(exc)[:3000],traceback=traceback.format_exc()[-3000:])
        if row.get('status') not in VOCABULARY:
            row['status_outside_vocabulary']=row.get('status');row['status']='INCOMPLETE'
        row['session_leaks']=session_leaks(database,exclude_users)
        if row['session_leaks']:row['status']='INCOMPLETE'
        rows[key]=row
        print(json.dumps(dict(group=group,case=key,**row),default=str),flush=True)
    final={k:r['status'] for k,r in rows.items()}
    print(json.dumps(dict(group=group,planned=ids,final=final,missing=[k for k in ids if k not in rows])),flush=True)
    return rows,None


def finish(report,rows):
    report['counts']=dict(Counter(r.get('status') for r in rows.values()))
    bad=report['counts'].get('INCOMPLETE') or report.get('database_remaining') or report.get('cleanup_failures')
    report['status']='INCOMPLETE' if bad else 'RUN_COMPLETE'
    return report


def run_races(module,verify,phase):
    report=dict(status='INCOMPLETE',label=LABEL,database=RACE_DB,copy_per_race=True,test_only_usage_grant=True,races={},
                production_go=False,independent_acceptance=False,release_evidence=False)
    try:
        url=copy_db(RACE_DB);setup=setup_copy(url,verify,True)
        planned=list(module.races(RaceTools(url,setup['today']),setup['today']))
        report['planned_race_ids']=[k for k,_ in planned]
        state=dict(setup=setup)
        def run_one(i,key,operation):
            if i:copy_db(RACE_DB);state['setup']=setup_copy(url,verify,True)
            row=operation()
            if isinstance(row,dict):row['copy_runtime']=state['setup']['runtime']
            return row
        report['races'],refusal=strict_rows('AUDITOR_RACES_'+phase.upper(),planned,run_one,RACE_DB)
        if refusal:report.update(refusal)
    except Exception as exc:report.update(error=str(exc)[:3000],traceback=traceback.format_exc()[-3000:])
    finally:report['database_remaining']=drop_db(RACE_DB)
    if 'error' in report:report['status']='INCOMPLETE';return report
    return finish(report,report['races'])


def _status_env():
    values={}
    out=subprocess.check_output(['supabase','status','--workdir',str(BASE),'-o','env'],text=True,stderr=subprocess.DEVNULL)
    for line in out.splitlines():
        key,sep,value=line.partition('=')
        if sep:values[key]=value.strip('"')
    assert values.get('API_URL')=='http://127.0.0.1:54321',('AUDITOR_HTTP_UNEXPECTED_API',values.get('API_URL'))
    return values


def _call(url,body,headers,method='POST'):
    data=None if body is None else json.dumps(body,default=str).encode()
    request=urllib.request.Request(url,data=data,method=method,headers=dict(headers,**({'Content-Type':'application/json'} if data else {})))
    try:
        with urllib.request.urlopen(request,timeout=60) as response:
            raw=response.read();status=response.status
    except urllib.error.HTTPError as exc:
        raw=exc.read();status=exc.code
    try:parsed=json.loads(raw) if raw else None
    except ValueError:parsed=raw.decode(errors='replace')[:2000]
    return dict(status=status,body=parsed)


def _mask(value):print('::add-mask::'+value,flush=True)


class HttpUser:
    def __init__(self,http,token,auth_id,role):
        self._http=http;self._token=token;self.auth_user_id=auth_id;self.role=role

    def rpc(self,name,args=None):return self._http._rpc(self._token,name,args or {})


class Http:
    """Real Auth plus a PostgREST container on the copy; see the module docstring."""

    def __init__(self,url):
        self.url=url;self.users=[];self.cleanup_failures=[]
        values=_status_env()
        self._anon,self._service=values['ANON_KEY'],values['SERVICE_ROLE_KEY']
        _mask(self._anon);_mask(self._service)
        names=subprocess.check_output(['docker','ps','--format','{{.Names}}'],text=True).split()
        original=next(n for n in names if n.startswith('supabase_rest_'))
        inspected=json.loads(subprocess.check_output(['docker','inspect',original],text=True))[0]
        config=dict(x.split('=',1) for x in inspected['Config']['Env'])
        uri=urlsplit(config['PGRST_DB_URI'])
        # The container serves the copy this mode made (HTTP or browser copy); run 36089919668 pointed the browser mode's
        # container at the dropped HTTP copy, so PostgREST never became ready.
        database=urlsplit(url).path.lstrip('/')
        assert database in (HTTP_DB,BROWSER_DB),('AUDITOR_HTTP_UNEXPECTED_DATABASE',database)
        config['PGRST_DB_URI']=urlunsplit((uri.scheme,uri.netloc,'/'+database,uri.query,uri.fragment))
        config.update(PGRST_DB_SCHEMAS='public',PGRST_SERVER_PORT='3000')
        network=next(iter(inspected['NetworkSettings']['Networks']))
        subprocess.run(['docker','rm','-f',REST],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=False)
        with tempfile.NamedTemporaryFile(mode='w',prefix='cp6-auditor-rest-',delete=True) as envfile:
            envfile.write(''.join(f'{k}={v}\n' for k,v in sorted(config.items())));envfile.flush()
            subprocess.run(['docker','run','-d','--name',REST,'--network',network,'--env-file',envfile.name,'-p','127.0.0.1:54329:3000',
                            inspected['Config']['Image']],check=True,stdout=subprocess.DEVNULL)
        deadline=time.monotonic()+60
        while True:
            try:
                with urllib.request.urlopen(REST_URL+'/',timeout=5) as response:
                    if response.status==200:break
            except Exception:
                pass
            assert time.monotonic()<deadline,'AUDITOR_HTTP_REST_NOT_READY'
            time.sleep(1)

    def _auth(self,path,body,admin=False,method='POST'):
        key=self._service if admin else self._anon
        return _call(AUTH_URL+path,body,{'apikey':key,'Authorization':'Bearer '+key},method)

    def _rpc(self,token,name,args):
        return _call(REST_URL+'/rpc/'+name,args,{'apikey':self._anon,'Authorization':'Bearer '+(token or self._anon)})

    def login(self,role_code,label='auditor'):
        email='cp6-auditor-%s-%s@example.invalid'%(label.lower(),uuid.uuid4());password='Au!'+secrets.token_hex(24)
        created=self._auth('admin/users',dict(email=email,password=password,email_confirm=True),admin=True)
        assert created['status'] in (200,201) and created['body'].get('id'),('AUDITOR_HTTP_AUTH_CREATE',created['status'])
        auth_id=created['body']['id'];self.users.append(auth_id)
        with psycopg.connect(self.url) as conn,conn.cursor() as cur:
            cur.execute("insert into erp.app_users(id,auth_user_id,full_name,role,role_id,is_active) "
                        "select gen_random_uuid(),%s,%s,role_code,id,true from erp.app_roles where role_code=%s and is_active",
                        (auth_id,'Auditor HTTP '+label,role_code))
            assert cur.rowcount==1,('AUDITOR_HTTP_UNKNOWN_OR_INACTIVE_ROLE',role_code)
            conn.commit()
        session=self._auth('token?grant_type=password',dict(email=email,password=password))
        assert session['status']==200 and session['body'].get('access_token'),('AUDITOR_HTTP_LOGIN',session['status'])
        token=session['body']['access_token']
        return HttpUser(self,token,auth_id,role_code)

    def anon_rpc(self,name,args=None):return self._rpc(None,name,args or {})

    def connect(self,**kwargs):return psycopg.connect(self.url,**kwargs)

    def close(self):
        for auth_id in self.users:
            try:
                r=self._auth('admin/users/'+auth_id,None,admin=True,method='DELETE')
                if r['status'] not in (200,204):self.cleanup_failures.append(auth_id)
            except Exception:self.cleanup_failures.append(auth_id)
        subprocess.run(['docker','rm','-f',REST],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=False)
        remaining=subprocess.check_output(['docker','ps','-aq','--filter','name=^/'+REST+'$'],text=True).strip()
        return dict(users_created=len(self.users),cleanup_failures=self.cleanup_failures,rest_remaining=bool(remaining))


AUTH_COUNTS="select (select count(*) from auth.users),(select count(*) from auth.identities),(select count(*) from auth.sessions),(select count(*) from auth.refresh_tokens)"


def run_http(module,verify,phase):
    awp,_=_probe()
    report=dict(status='INCOMPLETE',label=LABEL,database=HTTP_DB,real_auth=True,jwt_signed_by_runtime=False,
                test_only_usage_grant=False,cases={},production_go=False,independent_acceptance=False,release_evidence=False)
    http=None
    with psycopg.connect(awp.boundary.PRIMARY_ADMIN) as conn,conn.cursor() as cur:auth_before=list(cur.execute(AUTH_COUNTS).fetchone())
    try:
        url=copy_db(HTTP_DB);setup=setup_copy(url,verify,False);report['copy_runtime']=setup['runtime']
        http=Http(url)
        planned=list(module.http_cases(http,setup['today']))
        report['planned_case_ids']=[k for k,_ in planned]
        # PostgREST keeps its pool on the copy as `authenticator`; every other session left open is a leak.
        report['cases'],refusal=strict_rows('AUDITOR_HTTP_'+phase.upper(),planned,lambda i,key,operation:operation(),HTTP_DB,('authenticator',))
        if refusal:report.update(refusal)
    except Exception as exc:report.update(error=str(exc)[:3000],traceback=traceback.format_exc()[-3000:])
    finally:
        if http is not None:
            cleanup=http.close();report['cleanup']=cleanup;report['cleanup_failures']=cleanup['cleanup_failures'] or cleanup['rest_remaining']
        else:
            # The container may have started before the setup failed.
            subprocess.run(['docker','rm','-f',REST],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=False)
        report['database_remaining']=drop_db(HTTP_DB)
        with psycopg.connect(awp.boundary.PRIMARY_ADMIN) as conn,conn.cursor() as cur:auth_after=list(cur.execute(AUTH_COUNTS).fetchone())
        report['auth_counts']=dict(before=auth_before,after=auth_after,restored=auth_before==auth_after)
        if not report['auth_counts']['restored']:report['cleanup_failures']=True
    if 'error' in report:report['status']='INCOMPLETE';return report
    return finish(report,report['cases'])


def run_browser(script,verify,phase):
    """The auditor's Playwright module against the candidate UI, real Auth and PostgREST on a committed copy."""
    import hashlib,os
    awp,_=_probe()
    text=Path(script).read_bytes()
    report=dict(status='INCOMPLETE',label=LABEL,database=BROWSER_DB,real_auth=True,jwt_signed_by_runtime=False,test_only_usage_grant=False,
                frontend='candidate branch checkout (auditor)',script_sha256=hashlib.sha256(text).hexdigest(),cases={},
                production_go=False,independent_acceptance=False,release_evidence=False)
    print(json.dumps(dict(auditor_browser_script_sha256=report['script_sha256'],bytes=len(text))),flush=True)
    http=None
    with psycopg.connect(awp.boundary.PRIMARY_ADMIN) as conn,conn.cursor() as cur:auth_before=list(cur.execute(AUTH_COUNTS).fetchone())
    try:
        url=copy_db(BROWSER_DB);setup=setup_copy(url,verify,False);report['copy_runtime']=setup['runtime']
        http=Http(url)
        out=Path(tempfile.mkdtemp(prefix='cp6-auditor-browser-'))/'BROWSER.json'
        env=dict(os.environ,AUDITOR_BROWSER_SCRIPT=str(Path(script).resolve()),AUDITOR_BROWSER_DB_URL=url,AUDITOR_BROWSER_OUT=str(out),
                 AUDITOR_BROWSER_PHASE=phase,AUDITOR_BROWSER_TODAY=str(setup['today']),SUPABASE_ANON_KEY=http._anon,
                 SUPABASE_SERVICE_ROLE_KEY=http._service)
        result=subprocess.run(['node','scripts/cp6_auditor_browser_host.mjs'],cwd=AUDITOR,env=env,check=False)
        host=json.loads(out.read_text()) if out.exists() else {}
        report.update(host_exit=result.returncode,host_status=host.get('status'),planned_case_ids=host.get('planned',[]),
                      cases=host.get('cases',{}),console_errors=len(host.get('console_errors',[])),users_created=host.get('users_created'),
                      auth_cleanup_failures=host.get('auth_cleanup_failures'),host_error=host.get('error'))
        if host.get('status')!='RUN_COMPLETE':report['error']=host.get('error') or 'AUDITOR_BROWSER_HOST_%s'%host.get('status')
        report['session_leaks']=session_leaks(BROWSER_DB,('authenticator',))
        if report['session_leaks'] and 'error' not in report:report['error']='AUDITOR_BROWSER_SESSION_LEFT_OPEN'
    except Exception as exc:report.update(error=str(exc)[:3000],traceback=traceback.format_exc()[-3000:])
    finally:
        if http is not None:
            cleanup=http.close();report['cleanup']=cleanup;report['cleanup_failures']=cleanup['cleanup_failures'] or cleanup['rest_remaining']
        else:
            subprocess.run(['docker','rm','-f',REST],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=False)
        report['database_remaining']=drop_db(BROWSER_DB)
        with psycopg.connect(awp.boundary.PRIMARY_ADMIN) as conn,conn.cursor() as cur:auth_after=list(cur.execute(AUTH_COUNTS).fetchone())
        report['auth_counts']=dict(before=auth_before,after=auth_after,restored=auth_before==auth_after)
        if not report['auth_counts']['restored'] or report.get('auth_cleanup_failures'):report['cleanup_failures']=True
    if 'error' in report:report['status']='INCOMPLETE';return report
    return finish(report,report['cases'])
