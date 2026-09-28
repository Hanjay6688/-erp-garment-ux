"""Independently authored HTTP and real-browser BD continuation.

This creates only disposable fixtures. Product SQL/JS are never changed. Auth is
real local GoTrue password authentication, PostgREST uses authenticator against
the already-migrated cp6_rollback database, and agent-browser uses the actual
candidate UI. Peer-informed checks are labelled separately from blind checks.
"""
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from datetime import datetime
from zoneinfo import ZoneInfo
import concurrent.futures, errno, http.client, json, os, re, secrets, subprocess, threading, time, traceback, uuid
import psycopg

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'audit-results'/'http-browser';OUT.mkdir(parents=True,exist_ok=True)
DSN='postgresql://postgres:postgres@127.0.0.1:54322/cp6_rollback'
RESULTS=[];EVENTS=[];HTTP_EVENTS=[];FIX={};KEYS={};TOKENS={};PROCESSES=[]
PRODUCT='e96db5a270da5aa6d0f12c3812ac1c0542df938e'
SECRET_VALUES=[]

def uid(): return str(uuid.uuid4())
def redact(value):
    s=str(value)
    for secret in SECRET_VALUES:
        if secret:s=s.replace(secret,'[REDACTED]')
    return re.sub(r'eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+','[JWT_REDACTED]',s)
def save():
    data={'candidate':PRODUCT,'scope':'Real local GoTrue + PostgREST HTTP + actual candidate UI with agent-browser',
          'results':RESULTS,'production_go':False,
          'limits':['Disposable synthetic fixtures only; no production changes',
                    'Package extras and pagination probes are peer-informed, not blind discoveries',
                    'HTTP/browser smoke is not exhaustive UI, accessibility, or downstream accounting certification']}
    (OUT/'results.json').write_text(redact(json.dumps(data,indent=2,default=str))+'\n')
    (OUT/'events.json').write_text(redact(json.dumps(EVENTS,indent=2,default=str))+'\n')
    (OUT/'http-events.json').write_text(redact(json.dumps(HTTP_EVENTS,indent=2,default=str))+'\n')
def case(key,title,fn,origin='independent continuation'):
    row={'id':key,'title':title,'origin':origin};start=time.monotonic()
    try:row.update(status='PASS',observation=fn())
    except Exception as e:row.update(status='FAIL',error=redact(e),traceback=redact(traceback.format_exc()))
    row['seconds']=round(time.monotonic()-start,3);RESULTS.append(row);save()
    print(json.dumps({k:row.get(k) for k in ['id','title','status','error']},default=str),flush=True)
    return row['status']=='PASS'
def sql(q,args=(),one=False):
    with psycopg.connect(DSN) as c:
        r=c.execute(q,args)
        return r.fetchone()[0] if one else r.fetchall() if r.description else None
def run(args,*,timeout=120,env=None,log=None,check=True):
    p=subprocess.run(args,cwd=ROOT,capture_output=True,text=True,timeout=timeout,env=env)
    if log:(OUT/log).write_text(redact(p.stdout+'\n'+p.stderr))
    if check and p.returncode:raise RuntimeError({'command':redact(' '.join(args)),'exit':p.returncode,'output':redact((p.stdout+p.stderr)[-10000:])})
    return p

def request(url,payload=None,headers=None,method=None):
    data=None if payload is None else json.dumps(payload).encode()
    h={'Content-Type':'application/json',**(headers or {})}
    req=Request(url,data=data,headers=h,method=method or ('POST' if data is not None else 'GET'))
    try:
        with urlopen(req,timeout=60) as r:status,body=r.status,r.read()
    except HTTPError as e:status,body=e.code,e.read()
    try:body=json.loads(body)
    except (ValueError,UnicodeDecodeError):body=body.decode(errors='replace')
    return status,body

def rpc(name,payload,who='owner',expect_ok=True):
    status,body=request('http://127.0.0.1:54328/rest/v1/rpc/'+name,payload,
       {'apikey':KEYS['ANON_KEY'],'Authorization':'Bearer '+TOKENS[who]})
    EVENTS.append({'transport':'HTTP/PostgREST','rpc':name,'actor':who,'payload':payload,'http_status':status,'response':body})
    if expect_ok and status!=200:raise AssertionError({'rpc':name,'status':status,'body':body})
    return body if expect_ok else (status,body)
def cmd(action,payload,who='owner'):
    return rpc('erp_save_laundry_bd_action_v1',{'p_action':action,'p_payload':payload,'p_client_request_id':uid()},who)

class Proxy(BaseHTTPRequestHandler):
    protocol_version='HTTP/1.1'
    def log_message(self,*args):pass
    def do_OPTIONS(self):
        self.send_response(204);self.send_header('Access-Control-Allow-Origin',self.headers.get('Origin','*'))
        self.send_header('Access-Control-Allow-Headers','authorization,apikey,content-type,x-client-info,x-supabase-api-version,accept-profile,content-profile,prefer')
        self.send_header('Access-Control-Allow-Methods','GET,POST,PUT,PATCH,DELETE,OPTIONS');self.send_header('Content-Length','0');self.end_headers()
        HTTP_EVENTS.append({'method':'OPTIONS','path':self.path,'http_status':204,'requested_headers':self.headers.get('Access-Control-Request-Headers'),'origin':self.headers.get('Origin')})
    def proxy(self):
        is_rest=self.path.startswith('/rest/v1/')
        if is_rest:port,path=54329,self.path.removeprefix('/rest/v1')
        elif self.path.startswith('/auth/v1/'):port,path=54321,self.path
        else:
            self.send_response(404);self.send_header('Content-Length','0');self.end_headers();return
        payload=self.rfile.read(int(self.headers.get('Content-Length','0')))
        headers={k:v for k,v in self.headers.items() if k.lower() not in ('host','connection','content-length','accept-encoding')}
        conn=http.client.HTTPConnection('127.0.0.1',port,timeout=60)
        try:
            conn.request(self.command,path,payload,headers)
            response=conn.getresponse();body=response.read()
            self.send_response(response.status)
            for k,v in response.getheaders():
                if k.lower() not in ('transfer-encoding','content-length','connection','access-control-allow-origin'):self.send_header(k,v)
            self.send_header('Access-Control-Allow-Origin',self.headers.get('Origin','*'))
            self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
            event={'method':self.command,'path':self.path,'http_status':response.status,'transport_target':'cp6_rollback PostgREST' if is_rest else 'local GoTrue'}
            if is_rest:
                try:event['payload']=json.loads(payload) if payload else None
                except ValueError:event['payload']='non-json'
                try:event['response']=json.loads(body)
                except ValueError:event['response']='non-json'
            HTTP_EVENTS.append(event)
        finally:conn.close()
    do_GET=proxy;do_POST=proxy;do_PUT=proxy;do_PATCH=proxy;do_DELETE=proxy

def bind_gateway():
    # The frozen runtime pins this exact port. Reserve it before this script's
    # own outbound connections; the runner also excludes it from ephemeral use.
    deadline=time.monotonic()+65;attempt=0
    while True:
        attempt+=1
        try:
            server=ThreadingHTTPServer(('127.0.0.1',54328),Proxy)
            FIX['proxy']=server
            threading.Thread(target=server.serve_forever,daemon=True).start()
            EVENTS.append({'gateway_bind':{'port':54328,'attempt':attempt,'success':True}})
            return
        except OSError as error:
            if error.errno!=errno.EADDRINUSE:raise
            probe=run(['ss','-Htan','( sport = :54328 )'],check=False)
            states={line.split()[0] for line in probe.stdout.splitlines() if line.strip()}
            evidence={'port':54328,'attempt':attempt,'errno':error.errno,'ss_exit':probe.returncode,
                      'ss_output':probe.stdout,'ss_stderr':probe.stderr,'states':sorted(states)}
            EVENTS.append({'gateway_bind_collision':evidence});save()
            # Do not stop or replace an unknown listener. A measured TIME_WAIT
            # conflict is the only condition for this bounded retry.
            if probe.returncode or states!={'TIME-WAIT'} or time.monotonic()>=deadline:
                raise RuntimeError({'gateway_bind_failed':evidence,'time_wait_retry_budget_seconds':65}) from error
            time.sleep(1)

def setup_gateway():
    bind_gateway()
    # Only runtime configuration is reused; no writer tests or expected results.
    raw=run(['supabase','status','--workdir',str(ROOT.parent/'base'/'cp5-local'),'--output','json']).stdout
    KEYS.update(json.loads(raw));SECRET_VALUES.extend(str(v) for k,v in KEYS.items() if 'KEY' in k or 'SECRET' in k)
    assert KEYS.get('ANON_KEY') and KEYS.get('SERVICE_ROLE_KEY'),'Local legacy anon/service JWT keys required'
    original=json.loads(run(['docker','inspect','supabase_rest_cp5-local']).stdout)[0]
    env={k:v for item in original['Config']['Env'] for k,_,v in [item.partition('=')] if k.startswith('PGRST_')}
    SECRET_VALUES.extend(v for k,v in env.items() if 'SECRET' in k or 'KEY' in k)
    env.update(PGRST_DB_URI='postgresql://authenticator:postgres@127.0.0.1:54322/cp6_rollback',
               PGRST_SERVER_HOST='127.0.0.1',PGRST_SERVER_PORT='54329',PGRST_DB_SCHEMAS='public')
    p=ROOT/'audit-results'/'.bd-http-env-private'
    p.write_text('\n'.join(k+'='+v for k,v in env.items())+'\n');p.chmod(0o600)
    try:run(['docker','run','--detach','--name','bd-independent-rest','--network','host','--env-file',str(p),original['Config']['Image']])
    finally:p.unlink(missing_ok=True)
    for _ in range(80):
        try:
            status,_=request('http://127.0.0.1:54329/',headers={'Authorization':'Bearer '+KEYS['ANON_KEY']})
            if status<500:break
        except (URLError,ConnectionError):pass
        time.sleep(.25)
    else:raise RuntimeError('Independent PostgREST did not become ready')
    (OUT/'environment.json').write_text(json.dumps({'postgres_database':sql('select current_database()',one=True),
       'postgrest_image':original['Config']['Image'],'auth_gateway':'http://127.0.0.1:54321',
       'application_gateway':'http://127.0.0.1:54328','postgrest_database_role':'authenticator',
       'agent_browser':run(['agent-browser','--version']).stdout.strip()},indent=2)+'\n')

def setup_identities():
    for who,role in [('owner','OWNER'),('viewer','AUD_OPERATOR')]:
        email='bd-independent-'+who+'-'+uid()[:8]+'@example.test';password='Bd-Audit-'+secrets.token_hex(16)+'!'
        SECRET_VALUES.append(password)
        status,user=request('http://127.0.0.1:54321/auth/v1/admin/users',
          {'email':email,'password':password,'email_confirm':True},
          {'apikey':KEYS['SERVICE_ROLE_KEY'],'Authorization':'Bearer '+KEYS['SERVICE_ROLE_KEY']})
        assert status in (200,201),(status,user)
        authid=user['id'];FIX[who]={'auth_id':authid,'email':email,'password':password}
        rid=sql('select id from erp.app_roles where role_code=%s and is_active',(role,),one=True)
        assert rid,('Active ERP role absent',role)
        with psycopg.connect(DSN) as c:
            c.execute("select set_config('app.change_reason','Independent local browser fixture',true)")
            c.execute('insert into erp.app_users(auth_user_id,full_name,role,role_id) values(%s,%s,%s,%s)',
                      (authid,'AUD-BROWSER-'+who,'STAFF' if who=='viewer' else role,rid))
        status,session=request('http://127.0.0.1:54328/auth/v1/token?grant_type=password',{'email':email,'password':password},
          {'apikey':KEYS['ANON_KEY']})
        assert status==200,(status,session)
        TOKENS[who]=session['access_token'];SECRET_VALUES.extend([session['access_token'],session.get('refresh_token','')])
        access=rpc('erp_get_my_access_v1',{},who)
        assert access['allowed'] is True and access['profile']['auth_user_id']==authid,access
    return {'real_password_authentication':True,'owner_and_viewer_active':True}

def setup_master():
    FIX['vendor']=uid()
    sql('insert into erp.laundry_vendors(id,vendor_code,vendor_name) values(%s,%s,%s)',
        (FIX['vendor'],'AUD-BROWSER-V','Independent browser vendor'))
    cmd('SAVE_VENDOR_TERMS',{'vendor_id':FIX['vendor'],'pricing_mode':'COMPONENTS','pricing_unit':'PCS','minimum_charge':None,'expected_version':'0','reason':'Independent HTTP and browser fixture'})
    for key,code,status,amount in [('known','AUD-BROWSER-KNOWN','KNOWN','4321.09'),('unknown','AUD-BROWSER-UNKNOWN','UNKNOWN',None),('extra','AUD-BROWSER-EXTRA','KNOWN','678.91')]:
        FIX[key]=cmd('SAVE_COMPONENT',{'vendor_id':FIX['vendor'],'component_code':code,'component_name':code,'is_active':True,'reason':'Independent HTTP fixture'})['component_id']
        p={'component_id':FIX[key],'rate_status':status,'effective_from':'2026-09-01T08:00:00+07:00','reason':'Independent known and unknown fixture'}
        if amount is not None:p['rate_per_pcs']=amount
        cmd('SAVE_COMPONENT_RATE',p)
    FIX['package']=cmd('SAVE_PACKAGE',{'vendor_id':FIX['vendor'],'package_code':'AUD-BROWSER-PACK','package_name':'Independent browser package',
                    'component_ids':[FIX['known']],'is_active':True,'reason':'Independent package fixture'})['package_id']
    cmd('SAVE_PACKAGE_RATE',{'package_id':FIX['package'],'rate_per_pcs':'8712.35','effective_from':'2026-09-01T08:00:00+07:00','reason':'Independent package rate'})
    return {'vendor_id':FIX['vendor'],'known_component':FIX['known'],'unknown_component':FIX['unknown'],'package':FIX['package'],'outside_package_extra':FIX['extra']}

def owner_http():
    w=rpc('erp_get_laundry_bd_workspace_v1',{'p_filters':{'vendor_id':FIX['vendor']}})
    assert w['money_visible'] is True and w['can_manage_master'] is True,w
    rates={c['id']:c['current'] for c in w['components']}
    assert rates[FIX['known']]['rate']=='4321.09',rates
    assert rates[FIX['unknown']]['status']=='UNKNOWN' and rates[FIX['unknown']]['rate'] is None,rates
    return {'known':'4321.09','unknown':rates[FIX['unknown']],'money_visible':w['money_visible']}

def viewer_http():
    w=rpc('erp_get_laundry_bd_workspace_v1',{'p_filters':{'vendor_id':FIX['vendor']}},'viewer')
    assert w['money_visible'] is False and w['can_manage_master'] is False,w
    assert all(c['current'] is None or c['current']['rate'] is None for c in w['components']),w['components']
    assert w['invoices'] is None and w['payables'] is None,(w['invoices'],w['payables'])
    before=sql('select count(*) from erp.bd_laundry_components_v1',one=True)
    status,body=rpc('erp_save_laundry_bd_action_v1',{'p_action':'SAVE_COMPONENT','p_payload':{'vendor_id':FIX['vendor'],
       'component_code':'AUD-BROWSER-DENIED','component_name':'AUD-BROWSER-DENIED','is_active':True,'reason':'Denied role HTTP probe'},'p_client_request_id':uid()},'viewer',False)
    assert status in (400,401,403) and isinstance(body,dict) and body.get('code') in ('P0001','42501'),(status,body)
    assert sql('select count(*) from erp.bd_laundry_components_v1',one=True)==before,'Denied write changed master'
    return {'positive_read_control':True,'money_hidden':True,'forbidden_write_status':status,'response':body,'master_unchanged':True}

def build_ui():
    env=os.environ.copy();env.update(VITE_ERP_RUNTIME_MODE='DISPOSABLE_TEST',VITE_SUPABASE_URL='http://127.0.0.1:54328',
            VITE_SUPABASE_PUBLISHABLE_KEY='',VITE_SUPABASE_ANON_KEY=KEYS['ANON_KEY'])
    run(['npm','run','build:cp6-disposable'],timeout=360,env=env,log='build.log')
    log=(OUT/'static-server.log').open('w')
    p=subprocess.Popen(['python','-m','http.server','4176','--bind','127.0.0.1','--directory',str(ROOT/'cp6-ui-build')],stdout=log,stderr=log,cwd=ROOT)
    PROCESSES.append(p)
    for _ in range(80):
        try:
            if request('http://127.0.0.1:4176/')[0]==200:break
        except URLError:pass
        time.sleep(.25)
    else:raise RuntimeError('Built UI did not start')
    return {'build':'Actual frozen candidate UI','url':'http://127.0.0.1:4176'}

def ab(*args,who='owner',timeout=60,check=True):
    p=run(['agent-browser','--session','bd-independent-'+who,*args],timeout=timeout,check=False)
    EVENTS.append({'agent_browser':redact(' '.join(args)),'session':who,'exit':p.returncode,'stdout':redact(p.stdout),'stderr':redact(p.stderr)})
    if check and p.returncode:raise RuntimeError({'agent_browser':redact(' '.join(args)),'output':redact(p.stdout+p.stderr)})
    return p.stdout

def snap(label,who='owner'):
    s=ab('snapshot','-i',who=who);(OUT/(label+'.txt')).write_text(s)
    ab('screenshot',str(OUT/(label+'.png')),'--full',who=who)
    return s

def button(text,who='owner',exact=True):
    # Fresh snapshot for every semantic action; no stale ref reuse.
    s=ab('snapshot','-i',who=who)
    found=[]
    for line in s.splitlines():
        m=re.search(r'button "([^"]*)".*\[ref=(e\d+)\]',line)
        modern=re.search(r'@(e\d+)\s+\[button\]\s+"([^"]*)"',line)
        label,ref=(m.group(1),m.group(2)) if m else (modern.group(2),modern.group(1)) if modern else ('','')
        if ref and (label==text if exact else text in label):found.append(ref)
    if len(found)!=1:raise AssertionError({'button':text,'refs':found,'snapshot':s})
    ab('click','@'+found[0],who=who)

def fill(label,value,who='owner'):
    selector='[aria-label='+json.dumps(label)+']'
    # AuthGate uses a wrapping HTML label rather than aria-label. Match the
    # same accessible field as the native `find label` interaction below.
    control='(document.querySelector('+json.dumps(selector)+')||Array.from(document.querySelectorAll("label")).find(l=>l.textContent.trim()==='+json.dumps(label)+')?.control)'
    ab('wait','--fn',"(()=>{const e="+control+";return !!e&&!e.disabled;})()",who=who)
    ab('snapshot','-i',who=who);ab('find','label',label,'fill',value,who=who)
    # Preserve numeric-looking input text while unwrapping the CLI JSON output.
    actual=evaluate('({value:'+control+'.value})',who)['value']
    assert actual==str(value),{'input_entry_prerequisite':label,'expected':str(value),'actual':actual}

def select(label,value,who='owner'):
    selector='select[aria-label='+json.dumps(label)+']'
    # Native agent-browser select returned success against a disabled, empty
    # selector in run10. Wait for a user-operable control and the actual option.
    ready="(()=>{const e=document.querySelector("+json.dumps(selector)+");return !!e&&!e.disabled&&Array.from(e.options).some(o=>o.value==="+json.dumps(str(value))+");})()"
    ab('wait','--fn',ready,who=who)
    ab('snapshot','-i',who=who);ab('select',selector,value,who=who)
    # Choosing a vendor starts an asynchronous workspace read. A matching value
    # alone does not mean that the refreshed controls can be used yet (run12).
    settled="(()=>{const e=document.querySelector("+json.dumps(selector)+");return !!e&&!e.disabled&&e.value==="+json.dumps(str(value))+";})()"
    ab('wait','--fn',settled,who=who)

def text_body(who='owner'):return ab('get','text','body',who=who)
def wait_text(text,who='owner',timeout=30):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        body=text_body(who)
        if text in body:return body
        time.sleep(.25)
    raise AssertionError({'missing_text':text,'body':body})
def evaluate(code,who='owner'):
    out=ab('eval','JSON.stringify('+code+')',who=who).strip()
    for _ in range(3):
        try:out=json.loads(out)
        except (ValueError,TypeError):break
        if not isinstance(out,str):break
    return out

def browser_auth(who='owner'):
    ab('open','http://127.0.0.1:4176/',who=who)
    snap(who+'-initial-document',who)
    ab('wait','input[type="email"]',who=who)
    snap(who+'-login',who)
    fill('Email akun ERP',FIX[who]['email'],who);fill('Kata sandi',FIX[who]['password'],who)
    button('Masuk',who)
    try:ab('wait','aside.sidebar',who=who)
    except Exception:
        snap(who+'-login-failed',who)
        (OUT/(who+'-login-failed-body.txt')).write_text(redact(text_body(who)))
        EVENTS.append({'browser_login_failure_form':evaluate("Array.from(document.querySelectorAll('input')).map(e=>({type:e.type,valid:e.checkValidity(),validationMessage:e.validationMessage,length:e.value.length}))",who)})
        raise
    snap(who+'-authorized',who)
    return {'real_browser_password_login':True,'authorized_app_shell':True}

def open_bd_master(who='owner'):
    button('Produksi',who,False);button('• Laundry',who)
    wait_text('Harga & tagihan',who)
    button('Harga & tagihan',who)
    ab('wait','select[aria-label="Vendor harga laundry"]',who=who)
    select('Vendor harga laundry',FIX['vendor'],who)
    button('Harga vendor',who)
    wait_text('AUD-BROWSER-KNOWN',who)
    snap(who+'-master',who)
    return {'laundry_pricing_loaded':True,'fixture_vendor_selected':FIX['vendor']}

def owner_browser_known_unknown():
    body=wait_text('AUD-BROWSER-UNKNOWN')
    # Browser presentation oracle uses independent fixture values, no product formatter.
    normalized=body.replace('\u00a0',' ')
    assert '4.321,09' in normalized,normalized
    assert 'Belum diketahui sejak' in normalized,normalized
    return {'known_rendered_rupiah':'4.321,09','unknown_rendered':'Belum diketahui sejak','screenshot':'owner-master.png'}

def browser_master_create():
    before=sql("select count(*) from erp.bd_laundry_components_v1 where vendor_id=%s and component_code='AUD-UI-CREATED'",(FIX['vendor'],),one=True)
    assert before==0
    fill('Alasan','Independent browser creates one component')
    fill('Kode komponen','AUD-UI-CREATED');fill('Nama komponen','Independent actual UI component')
    button('Tambah komponen')
    wait_text('AUD-UI-CREATED');snap('owner-component-created')
    rows=sql("select component_code,component_name from erp.bd_laundry_components_v1 where vendor_id=%s and component_code='AUD-UI-CREATED'",(FIX['vendor'],))
    assert rows==[('AUD-UI-CREATED','Independent actual UI component')],rows
    events=[x for x in HTTP_EVENTS if x.get('path','').endswith('/rpc/erp_save_laundry_bd_action_v1') and x.get('payload',{}).get('p_payload',{}).get('component_code')=='AUD-UI-CREATED']
    assert len(events)==1 and events[0]['http_status']==200,events
    return {'row_count':1,'native_readback':rows,'browser_sent_rpc_count':len(events)}

def enter_date_with_keys(label,value,who='owner'):
    selector='input[aria-label='+json.dumps(label)+']'
    ab('wait','--fn',"(()=>{const e=document.querySelector("+json.dumps(selector)+");return !!e&&!e.disabled&&e.type==='date';})()",who=who)
    desired={'Year':int(value[:4]),'Month':int(value[5:7]),'Day':int(value[8:10])}
    changes=[]
    # Run11 native `fill` cleared the date's shadow spinbuttons to zero without
    # changing React state. Use actual keyboard arrows on the visible segments.
    for part in ('Year','Month','Day'):
        snapshot=ab('snapshot','-i','-s',selector,who=who)
        found=[]
        for line in snapshot.splitlines():
            m=re.search(r'spinbutton "'+part+r'(?: '+part+r')?".*ref=(e\d+).*:\s*(\d+)',line)
            if m:found.append((m.group(1),int(m.group(2))))
        if len(found)!=1:raise AssertionError({'date_entry_prerequisite':'One native date segment required','part':part,'snapshot':snapshot})
        ref,current=found[0];difference=desired[part]-current
        assert abs(difference)<=100,{'unexpected_date_segment':part,'current':current,'target':desired[part]}
        if difference:
            ab('click','@'+ref,who=who)
            for _ in range(abs(difference)):ab('press','ArrowUp' if difference>0 else 'ArrowDown',who=who)
            ab('press','Tab',who=who)
        changes.append({'part':part,'before':current,'target':desired[part],'keyboard_steps':abs(difference)})
    actual=evaluate('document.querySelector('+json.dumps(selector)+').value',who)
    assert actual==value,{'date_entry_prerequisite':True,'expected':value,'actual':actual,'changes':changes}
    EVENTS.append({'native_date_entry':label,'expected':value,'actual':actual,'changes':changes})
    return actual

def browser_invoice_draft_reload():
    ctx=json.loads((ROOT/'audit-results'/'lifecycle-fixture.json').read_text())
    vendor=ctx['v1']
    w=rpc('erp_get_laundry_bd_workspace_v1',{'p_filters':{'vendor_id':vendor}})
    available=[u for u in w['opening_uninvoiced'] if not u['invoiced'] and u['estimate_status']=='KNOWN' and u['qty']-u['billed']>=1]
    assert available,'No own unbilled opening source is available for browser draft probe'
    source=available[0]['id'];name='AUD-UI-DRAFT-RELOAD';before=sql('select count(*) from erp.journal_entries',one=True)
    select('Vendor harga laundry',vendor);button('Invoice vendor');wait_text('Draf invoice baru')
    fill('Nomor invoice vendor',name);enter_date_with_keys('Tanggal invoice','2026-09-21');fill('Total invoice','1234.57')
    committed_date=evaluate("document.querySelector('input[aria-label=\"Tanggal invoice\"]').value")
    assert committed_date=='2026-09-21',{'date_after_other_field_changed':committed_date}
    button('Tambah baris');select('Sumber baris 1','o:'+source);select('Kategori baris 1','GOOD')
    fill('Qty baris 1','1');fill('Nominal baris 1','1234.57')
    committed_date=evaluate("document.querySelector('input[aria-label=\"Tanggal invoice\"]').value")
    assert committed_date=='2026-09-21',{'date_before_submit':committed_date}
    snap('owner-invoice-before-save');button('Simpan draf invoice')
    wait_text('Ubah draf '+name);snap('owner-invoice-draft')
    rows=sql("select id::text,status,header_total::text,journal_id,invoice_date::text from erp.bd_laundry_invoices_v1 where vendor_id=%s and invoice_number=%s",(vendor,name))
    assert len(rows)==1 and rows[0][1:] == ('DRAFT','1234.57',None,'2026-09-21'),rows
    sent=[e for e in HTTP_EVENTS if e.get('payload',{}).get('p_payload',{}).get('invoice_number')==name]
    assert len(sent)==1 and sent[0]['payload']['p_payload']['invoice_date']=='2026-09-21',sent
    assert sql('select count(*) from erp.journal_entries',one=True)==before,'Browser draft must not write a journal'
    # Actual page reload: React state is rebuilt and the draft must come from HTTP.
    ab('open','http://127.0.0.1:4176/');ab('wait','aside.sidebar')
    snap('owner-page-reopened');button('Produksi',exact=False);button('• Laundry')
    wait_text('Harga & tagihan');button('Harga & tagihan')
    ab('wait','select[aria-label="Vendor harga laundry"]');select('Vendor harga laundry',vendor)
    button('Invoice vendor');wait_text('Ubah draf '+name);snap('owner-draft-after-page-reload')
    body=text_body();assert '1.234,57' in body,body
    # The saved list row persists; edit selection itself is intentionally reopened.
    button('Ubah draf '+name)
    fields=evaluate("Object.fromEntries(['Nomor invoice vendor','Tanggal invoice','Total invoice','Sumber baris 1','Kategori baris 1','Qty baris 1','Nominal baris 1'].map(k=>[k,document.querySelector('[aria-label=\"'+k+'\"]')?.value]))")
    expected={'Nomor invoice vendor':name,'Tanggal invoice':'2026-09-21','Total invoice':'1234.57',
              'Sumber baris 1':'o:'+source,'Kategori baris 1':'GOOD','Qty baris 1':'1','Nominal baris 1':'1234.57'}
    assert fields==expected,{'expected_form':expected,'actual_form':fields}
    snap('owner-reopened-draft-fields')
    observation={'draft':rows[0],'source':source,'journal_count_unchanged':True,'actual_page_reload_preserved_draft':True,
                 'date_before_submit':committed_date,'date_in_http_payload':sent[0]['payload']['p_payload']['invoice_date'],
                 'date_in_database':rows[0][4],'reopened_form_fields':fields}
    EVENTS.append({'draft_round_trip':observation})
    # The following case owns its own navigation. Do not allow that navigation
    # to shadow the independently verified stored draft round trip (run12).
    return observation

def package_extras_browser():
    # Explicitly peer-informed. Same own vendor has a package + component outside it.
    select('Vendor harga laundry',FIX['vendor']);button('Harga vendor');wait_text('AUD-BROWSER-KNOWN')
    fill('Alasan','Switch synthetic vendor to package for UI capability probe')
    select('Cara harga vendor','PACKAGE');select('Satuan harga vendor','PCS');button('Simpan ketentuan')
    wait_text('Cara harga PACKAGE')
    button('Kirim dengan harga');wait_text('harga paket per PCS')
    select('Paket kirim berharga',FIX['package'])
    snap('peer-informed-package-extras')
    form=evaluate("(()=>{const s=document.querySelector('section[aria-label=\"Kirim laundry dengan harga BD\"]');return s?{text:s.innerText,controls:Array.from(s.querySelectorAll('input,select,button')).map(e=>({tag:e.tagName,aria:e.getAttribute('aria-label'),text:e.tagName==='SELECT'?e.innerText:e.textContent,type:e.getAttribute('type')}))}:null})()")
    assert isinstance(form,dict) and form.get('controls'),form
    FIX['extras_observation']=form
    extra=[c for c in form['controls'] if re.search(r'extra|tambahan|cakupan',str(c),re.I)]
    if not extra:raise AssertionError({'peer_finding_reproduced':True,'package_selector_present':any(c.get('aria')=='Paket kirim berharga' for c in form['controls']),
                                      'configured_outside_package_component':'AUD-BROWSER-EXTRA','extra_controls':extra,'rendered_form':form})
    return form

def viewer_browser():
    open_bd_master('viewer');body=text_body('viewer')
    assert 'Hak master mitra diperlukan' in body,body
    assert '4.321,09' not in body and '678,91' not in body,body
    button('Invoice vendor','viewer');wait_text('Hak melihat nominal diperlukan untuk invoice vendor.','viewer')
    snap('viewer-money-hidden','viewer')
    return {'money_hidden_in_master':True,'invoice_denial_visible':True}

def seed_pagination():
    # Public draft API; never post these documents. Existing own opening fixture is
    # merely a reference, and drafts reserve no quantity or ledger value.
    ctx=json.loads((ROOT/'audit-results'/'lifecycle-fixture.json').read_text())
    vendor=ctx['v1'];source=ctx['sources']['ATOMIC'];FIX['paging_vendor']=vendor
    made=[]
    before=sql('select count(*) from erp.journal_entries',one=True)
    for n in range(55):
        number='AUD-UI-PAGE-'+str(n).zfill(3)
        r=cmd('SAVE_INVOICE_DRAFT',{'vendor_id':vendor,'invoice_number':number,'invoice_date':'2026-09-21','header_total':'10.01',
          'lines':[{'line_kind':'BILL','opening_uninvoiced_id':source,'category':'GOOD','qty':1,'amount':'10.01','note':'Independent pagination draft'}]})
        made.append(r['invoice_id'])
    assert sql('select count(*) from erp.journal_entries',one=True)==before,'Draft paging setup changed journals'
    w=rpc('erp_get_laundry_bd_workspace_v1',{'p_filters':{'vendor_id':vendor}})
    returned={i['invoice_id'] for i in w['invoices']};FIX['paging_ids']=made
    return {'created_draft_ids':made,'public_returned_count':len(returned),'own_drafts_absent':sorted(set(made)-returned),'journal_count_unchanged':True}

def pagination_browser():
    select('Vendor harga laundry',FIX['paging_vendor']);button('Invoice vendor');wait_text('AUD-UI-PAGE-054')
    snap('peer-informed-invoice-pagination')
    dom=evaluate("(()=>{const s=document.querySelector('section[aria-label=\"Invoice vendor laundry\"]');return s?{text:s.innerText,buttons:Array.from(s.querySelectorAll('button')).map(e=>e.textContent),inputs:Array.from(s.querySelectorAll('input,select')).map(e=>({tag:e.tagName,aria:e.getAttribute('aria-label'),placeholder:e.getAttribute('placeholder'),type:e.getAttribute('type')})),rows:s.querySelector('tbody')?.rows.length}:null})()")
    assert isinstance(dom,dict) and dom.get('rows'),dom
    own_visible=set(re.findall(r'AUD-UI-PAGE-\d{3}',dom['text']));missing=['AUD-UI-PAGE-'+str(n).zfill(3) for n in range(55) if 'AUD-UI-PAGE-'+str(n).zfill(3) not in own_visible]
    navigation=[x for x in dom['buttons']+list(map(str,dom['inputs'])) if re.search(r'selanjut|sebelum|next|previous|halaman|cari|search|muat lebih',x,re.I)]
    if missing and not navigation:raise AssertionError({'peer_finding_reproduced':True,'own_drafts_created':55,'rendered_rows':dom['rows'],'own_visible':len(own_visible),'missing':missing,'paging_search_controls':navigation})
    return {'rendered_rows':dom['rows'],'missing':missing,'navigation':navigation}

# Gap completion requested after run15. The frozen original cases above stay
# unchanged; each following check states whether its origin is independent or
# a follow-up to a known concern.
def gap_replay_controls():
    who='revoked_owner';email='bd-gap-revoke-'+uid()[:8]+'@example.test';password='Bd-Audit-'+secrets.token_hex(16)+'!'
    SECRET_VALUES.append(password)
    status,user=request('http://127.0.0.1:54321/auth/v1/admin/users',{'email':email,'password':password,'email_confirm':True},
        {'apikey':KEYS['SERVICE_ROLE_KEY'],'Authorization':'Bearer '+KEYS['SERVICE_ROLE_KEY']})
    assert status in (200,201),(status,user)
    role_owner=sql("select id from erp.app_roles where role_code='OWNER' and is_active",one=True)
    role_viewer=sql("select id from erp.app_roles where role_code='AUD_OPERATOR' and is_active",one=True)
    with psycopg.connect(DSN) as c:
        c.execute("select set_config('app.change_reason','Independent HTTP revocation identity',true)")
        appid=c.execute("insert into erp.app_users(auth_user_id,full_name,role,role_id) values(%s,%s,'OWNER',%s) returning id",
                        (user['id'],'AUD-HTTP-REVOKED-OWNER',role_owner)).fetchone()[0]
    status,session=request('http://127.0.0.1:54328/auth/v1/token?grant_type=password',{'email':email,'password':password},{'apikey':KEYS['ANON_KEY']})
    assert status==200,(status,session)
    TOKENS[who]=session['access_token'];SECRET_VALUES.extend([session['access_token'],session.get('refresh_token','')])
    ctx=json.loads((ROOT/'audit-results'/'lifecycle-fixture.json').read_text());vendor=ctx['v1']
    before=rpc('erp_get_laundry_bd_workspace_v1',{'p_filters':{'vendor_id':vendor}},who)
    assert before['is_owner'] is True and before['money_visible'] is True,before
    policy=next(p for p in before['policies'] if p['key']=='LAU-DEC01')
    assert policy['status']=='SET' and isinstance(policy['value'],dict),policy
    policy_payload={'policy_key':'LAU-DEC01','operation':'SET','value':policy['value'],'expected_version':policy['version'],'reason':'HTTP replay: preserve existing owner policy value'}
    policy_request={'p_action':'SET_POLICY','p_payload':policy_payload,'p_client_request_id':uid()}
    accepted_policy=rpc('erp_save_laundry_bd_action_v1',policy_request,who)
    source=next(u['id'] for u in before['opening_uninvoiced'] if not u['invoiced'] and u['estimate_status']=='KNOWN' and u['qty']-u['billed']>=1)
    invoice_payload={'vendor_id':vendor,'invoice_number':'AUD-HTTP-REVOKE-CACHED','invoice_date':'2026-09-21','header_total':'4321.67',
                     'lines':[{'line_kind':'BILL','opening_uninvoiced_id':source,'category':'GOOD','qty':1,'amount':'4321.67'}]}
    invoice_request={'p_action':'SAVE_INVOICE_DRAFT','p_payload':invoice_payload,'p_client_request_id':uid()}
    accepted_invoice=rpc('erp_save_laundry_bd_action_v1',invoice_request,who)
    assert accepted_invoice['header_total']=='4321.67' and accepted_invoice['status']=='DRAFT',accepted_invoice
    def set_role(role_id,reason):
        version=sql('select row_version from erp.app_users where id=%s',(appid,),one=True)
        result=rpc('erp_save_app_user_v3',{'p_payload':{'id':str(appid),'full_name':'AUD-HTTP-REVOKED-OWNER',
                   'auth_user_id':user['id'],'role_id':str(role_id),'is_active':True,'change_reason':reason},
                   'p_expected_version':version,'p_client_request_id':uid()})
        assert result['role_id']==str(role_id),result
        return result
    observation={'actor_auth_id':user['id'],'real_password_auth':True,'revocation_transport':'public.erp_save_app_user_v3 over HTTP',
                 'policy_positive':accepted_policy,'invoice_positive':accepted_invoice,'jwt_unchanged':True}
    try:
        observation['role_revocation']=set_role(role_viewer,'Independent test: revoke OWNER rights from disposable actor')
        normal=rpc('erp_get_laundry_bd_workspace_v1',{'p_filters':{'vendor_id':vendor}},who)
        observation['normal_read_after_revocation']={'is_owner':normal['is_owner'],'money_visible':normal['money_visible'],
                                                    'can_manage_master':normal['can_manage_master'],'invoices':normal['invoices']}
        fresh_policy={**policy_payload,'expected_version':accepted_policy['version'],'reason':'Fresh policy request after owner revocation'}
        observation['fresh_policy']=rpc('erp_save_laundry_bd_action_v1',{'p_action':'SET_POLICY','p_payload':fresh_policy,'p_client_request_id':uid()},who,False)
        observation['fresh_invoice']=rpc('erp_save_laundry_bd_action_v1',{'p_action':'SAVE_INVOICE_DRAFT',
            'p_payload':{**invoice_payload,'invoice_number':'AUD-HTTP-REVOKE-FRESH'},'p_client_request_id':uid()},who,False)
        native_before=sql('select (select version from erp.bd_policy_settings_v1 where policy_key=\'LAU_DEC01\'),(select count(*) from erp.bd_laundry_invoices_v1)')[0]
        observation['cached_policy']=rpc('erp_save_laundry_bd_action_v1',policy_request,who,False)
        observation['cached_invoice']=rpc('erp_save_laundry_bd_action_v1',invoice_request,who,False)
        native_after=sql('select (select version from erp.bd_policy_settings_v1 where policy_key=\'LAU_DEC01\'),(select count(*) from erp.bd_laundry_invoices_v1)')[0]
        observation['cached_replay_did_not_repeat_writes']=native_before==native_after
    finally:
        observation['role_restored']=set_role(role_owner,'Independent test: restore original OWNER rights')
        restored=rpc('erp_get_laundry_bd_workspace_v1',{'p_filters':{'vendor_id':vendor}},who)
        observation['restored_owner_and_money']=restored['is_owner'] is True and restored['money_visible'] is True
        FIX['revocation_observation']=observation;EVENTS.append({'owner_revocation_http':observation});save()
    assert normal['is_owner'] is False and normal['money_visible'] is False and normal['invoices'] is None,observation
    assert all(not 200<=observation[k][0]<300 for k in ('fresh_policy','fresh_invoice')),observation
    assert observation['restored_owner_and_money'] and observation['cached_replay_did_not_repeat_writes'],observation
    return observation

def gap_replay_refusal(kind):
    o=FIX['revocation_observation'];status,body=o['cached_'+kind]
    result={'cached_http_status':status,'cached_response':body,'fresh_http_status':o['fresh_'+kind][0],
            'normal_read_money_hidden':o['normal_read_after_revocation']['money_visible'] is False,
            'no_repeated_write':o['cached_replay_did_not_repeat_writes'],'role_restored':o['restored_owner_and_money']}
    if kind=='invoice':result['financial_nominal_disclosed']=isinstance(body,dict) and body.get('header_total')=='4321.67'
    else:result['claim_scope']='Cached owner-only policy success; no claim that this policy response contains financial nominal'
    assert not 200<=status<300,result
    return result

def mobile_touch_context(who,app_url):
    # agent-browser 0.31.1 set device configures metrics/UA but omits touch.
    # Use Chromium's actual emulation API on the uniquely marked active page;
    # keep the CDP session alive through reloads. No product JS is injected.
    raw=ab('get','cdp-url',who=who)
    endpoints=re.findall(r'ws://(?:127\.0\.0\.1|localhost):\d+/[^\s"\x27]+',raw)
    assert len(endpoints)==1,{'local_cdp_endpoint_count':len(endpoints)}
    ready=OUT/(who+'-touch-ready.json');ready.unlink(missing_ok=True)
    worker=r'''
import {writeFileSync} from 'node:fs';
const [endpoint, readyPath, appUrl] = process.argv.slice(1);
const ws = new WebSocket(endpoint);
let nextId = 0;
const pending = new Map();
ws.addEventListener('message', event => {
  const msg = JSON.parse(event.data), entry = pending.get(msg.id);
  if (!entry) return;
  pending.delete(msg.id); clearTimeout(entry.timer);
  msg.error ? entry.reject(new Error(JSON.stringify(msg.error))) : entry.resolve(msg.result);
});
function send(method, params = {}, sessionId) {
  return new Promise((resolve, reject) => {
    const id = ++nextId;
    const timer = setTimeout(() => {pending.delete(id); reject(new Error('CDP timeout: '+method));}, 10000);
    pending.set(id, {resolve, reject, timer});
    ws.send(JSON.stringify({id, method, params, ...(sessionId ? {sessionId} : {})}));
  });
}
try {
  await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('CDP connection timeout')), 10000);
    ws.addEventListener('open', () => {clearTimeout(timer); resolve();}, {once:true});
    ws.addEventListener('error', () => {clearTimeout(timer); reject(new Error('CDP connection failed'));}, {once:true});
  });
  const {targetInfos} = await send('Target.getTargets');
  const pages = targetInfos.filter(t => t.type === 'page');
  const matches = pages.filter(t => t.url === appUrl);
  if (matches.length !== 1) throw new Error(JSON.stringify({expected_app_url:appUrl,matching_pages:matches.length,page_urls:pages.map(t=>t.url)}));
  const selected = matches[0];
  const {sessionId} = await send('Target.attachToTarget', {targetId:selected.targetId, flatten:true});
  await send('Emulation.setTouchEmulationEnabled', {enabled:true, maxTouchPoints:1}, sessionId);
  writeFileSync(readyPath, JSON.stringify({method:'Emulation.setTouchEmulationEnabled',enabled:true,maxTouchPoints:1,page_target_count:pages.length,matching_page_count:matches.length,selected_target_url:selected.url,selected_target_id:selected.targetId}));
  process.on('SIGTERM', () => {ws.close(); process.exit(0);});
  await new Promise(resolve => ws.addEventListener('close', resolve, {once:true}));
} catch (error) {
  writeFileSync(readyPath, JSON.stringify({error:String(error)}));
  ws.close(); process.exitCode = 1;
}
'''
    log=(OUT/(who+'-touch-worker.log')).open('w')
    p=subprocess.Popen(['node','--input-type=module','-e',worker,endpoints[0],str(ready),app_url],cwd=ROOT,stdout=log,stderr=log)
    log.close();PROCESSES.append(p);FIX[who+'_touch_worker']=p
    deadline=time.monotonic()+25
    while not ready.exists() and p.poll() is None and time.monotonic()<deadline:time.sleep(.1)
    assert ready.exists(),{'touch_worker_exit':p.poll(),'ready':False}
    result=json.loads(ready.read_text());assert 'error' not in result,result
    assert p.poll() is None,{'touch_worker_exit':p.returncode,'ready':result}
    EVENTS.append({'mobile_touch_emulation':result,'session':who})
    return result

def mobile_button(text,who,exact=True):
    # Fresh refs and native Input.dispatchTouchEvent through agent-browser tap.
    s=ab('snapshot','-i',who=who);found=[]
    for line in s.splitlines():
        m=re.search(r'button "([^"]*)".*\[ref=(e\d+)\]',line)
        modern=re.search(r'@(e\d+)\s+\[button\]\s+"([^"]*)"',line)
        label,ref=(m.group(1),m.group(2)) if m else (modern.group(2),modern.group(1)) if modern else ('','')
        if ref and (label==text if exact else text in label):found.append(ref)
    assert len(found)==1,{'mobile_button':text,'refs':found,'snapshot':s}
    ab('tap','@'+found[0],who=who)

def mobile_snap(label,who):
    # Chromium beyond-viewport capture can reset native maxTouchPoints.
    # Keep real viewport captures and verify emulation on both sides.
    probe='({touch_points:navigator.maxTouchPoints,coarse:matchMedia("(pointer:coarse)").matches})'
    before=evaluate(probe,who)
    s=ab('snapshot','-i',who=who);(OUT/(label+'.txt')).write_text(s)
    ab('screenshot',str(OUT/(label+'.png')),who=who)
    after=evaluate(probe,who)
    observation={'mobile_viewport_capture':label,'session':who,'before':before,'after':after,'full_page':False}
    EVENTS.append(observation)
    assert all(x['touch_points']>0 and x['coarse'] is True for x in (before,after)),observation
    return s

def mobile_open_pricing(who,vendor):
    mobile_button('Buka menu',who)
    ab('wait','--fn',"document.querySelector('aside.sidebar')?.getBoundingClientRect().left===0",who=who)
    mobile_button('Produksi',who,False);mobile_button('• Laundry',who)
    ab('wait','--fn',"document.querySelector('aside.sidebar')?.getBoundingClientRect().right<=0",who=who)
    wait_text('Harga & tagihan',who);mobile_button('Harga & tagihan',who)
    ab('wait','select[aria-label="Vendor harga laundry"]',who=who);select('Vendor harga laundry',vendor,who)

def mobile_auth(who,actor):
    FIX[who]=FIX[actor]
    ab('set','device','iPhone 14',who=who)
    app_url='http://127.0.0.1:4176/?audit_mobile='+uid()
    ab('open',app_url,who=who);ab('wait','input[type="email"]',who=who)
    active_url=ab('get','url',who=who).strip()
    assert active_url==app_url,{'expected_active_url':app_url,'actual_active_url':active_url}
    emulation=mobile_touch_context(who,active_url)
    mobile_snap(who+'-login',who)
    fill('Email akun ERP',FIX[who]['email'],who);fill('Kata sandi',FIX[who]['password'],who)
    mobile_button('Masuk',who);ab('wait','aside.sidebar',who=who);mobile_snap(who+'-authorized',who)
    result={'real_browser_password_login':True,'authorized_app_shell':True,'touch_configuration':emulation,'button_input':'native touch tap'}
    env=evaluate('({width:innerWidth,height:innerHeight,pixel_ratio:devicePixelRatio,user_agent:navigator.userAgent,touch_points:navigator.maxTouchPoints,coarse:matchMedia("(pointer:coarse)").matches})',who)
    assert env['width']<=430 and env['touch_points']>0 and env['coarse'] is True and re.search('iPhone|Mobile',env['user_agent']),env
    FIX[who+'_environment']=env
    return {**result,'emulation':env,'physical_device':False}

def mobile_master():
    who='mobile_owner';mobile_open_pricing(who,FIX['vendor']);mobile_button('Harga vendor',who)
    body=wait_text('AUD-BROWSER-UNKNOWN',who).replace('\u00a0',' ')
    assert '4.321,09' in body and 'Belum diketahui sejak' in body,body
    fill('Alasan','Independent mobile emulation master creation',who)
    fill('Kode komponen','AUD-MOBILE-CREATED',who);fill('Nama komponen','Mobile emulation master',who);mobile_button('Tambah komponen',who)
    wait_text('AUD-MOBILE-CREATED',who);mobile_snap('mobile-owner-master',who)
    rows=sql("select component_code,component_name from erp.bd_laundry_components_v1 where vendor_id=%s and component_code='AUD-MOBILE-CREATED'",(FIX['vendor'],))
    assert rows==[('AUD-MOBILE-CREATED','Mobile emulation master')],rows
    sent=[x for x in HTTP_EVENTS if (x.get('payload') or {}).get('p_payload',{}).get('component_code')=='AUD-MOBILE-CREATED']
    assert len(sent)==1 and sent[0]['http_status']==200,sent
    layout=evaluate('({viewport:innerWidth,page_scroll_width:document.documentElement.scrollWidth})',who)
    return {'row':rows,'http_mutations':len(sent),'known_unknown_visible':True,'layout_observation':layout,'physical_device':False}

def mobile_draft():
    who='mobile_owner';ctx=json.loads((ROOT/'audit-results'/'lifecycle-fixture.json').read_text());vendor=ctx['v1']
    w=rpc('erp_get_laundry_bd_workspace_v1',{'p_filters':{'vendor_id':vendor}})
    source=next(u['id'] for u in w['opening_uninvoiced'] if not u['invoiced'] and u['estimate_status']=='KNOWN' and u['qty']-u['billed']>=1)
    day=datetime.now(ZoneInfo('Asia/Jakarta')).date().isoformat();name='AUD-MOBILE-DRAFT-RELOAD';before=sql('select count(*) from erp.journal_entries',one=True)
    # Independent entry point: a master-form failure must not suppress this flow.
    ab('open','http://127.0.0.1:4176/',who=who);ab('wait','aside.sidebar',who=who)
    mobile_open_pricing(who,vendor);mobile_button('Invoice vendor',who);wait_text('Draf invoice baru',who)
    fill('Nomor invoice vendor',name,who);fill('Total invoice','5678.43',who)
    date=evaluate("({value:document.querySelector('input[aria-label=\"Tanggal invoice\"]').value})",who)['value']
    assert date==day,{'expected_business_day':day,'rendered_date':date}
    mobile_button('Tambah baris',who);select('Sumber baris 1','o:'+source,who);select('Kategori baris 1','GOOD',who)
    fill('Qty baris 1','1',who);fill('Nominal baris 1','5678.43',who);mobile_snap('mobile-invoice-before-save',who)
    mobile_button('Simpan draf invoice',who);wait_text('Ubah draf '+name,who)
    row=sql("select id::text,status,header_total::text,invoice_date::text,journal_id from erp.bd_laundry_invoices_v1 where vendor_id=%s and invoice_number=%s",(vendor,name))
    assert len(row)==1 and row[0][1:]==('DRAFT','5678.43',day,None),row
    sent=[x for x in HTTP_EVENTS if (x.get('payload') or {}).get('p_payload',{}).get('invoice_number')==name]
    assert len(sent)==1 and sent[0]['http_status']==200 and sent[0]['payload']['p_payload']['invoice_date']==day,sent
    ab('open','http://127.0.0.1:4176/',who=who);ab('wait','aside.sidebar',who=who)
    mobile_open_pricing(who,vendor);mobile_button('Invoice vendor',who);wait_text('Ubah draf '+name,who);mobile_button('Ubah draf '+name,who)
    fields=evaluate("Object.fromEntries(['Nomor invoice vendor','Tanggal invoice','Total invoice','Sumber baris 1','Kategori baris 1','Qty baris 1','Nominal baris 1'].map(k=>[k,document.querySelector('[aria-label=\"'+k+'\"]')?.value]))",who)
    expected={'Nomor invoice vendor':name,'Tanggal invoice':day,'Total invoice':'5678.43','Sumber baris 1':'o:'+source,'Kategori baris 1':'GOOD','Qty baris 1':'1','Nominal baris 1':'5678.43'}
    assert fields==expected,{'expected':expected,'actual':fields}
    assert sql('select count(*) from erp.journal_entries',one=True)==before,'Mobile draft changed journals'
    mobile_snap('mobile-draft-after-reload',who)
    return {'invoice':row[0],'http_payload_date':sent[0]['payload']['p_payload']['invoice_date'],'reopened_fields':fields,'journals_unchanged':True,
            'date_scope':'Default business date persisted; mobile date-picker editing is not covered','physical_device':False}

def mobile_viewer():
    who='mobile_viewer';mobile_open_pricing(who,FIX['vendor']);mobile_button('Harga vendor',who)
    body=wait_text('AUD-BROWSER-KNOWN',who)
    assert 'Hak master mitra diperlukan' in body and '4.321,09' not in body and '678,91' not in body,body
    mobile_snap('mobile-viewer-master',who);mobile_button('Invoice vendor',who)
    wait_text('Hak melihat nominal diperlukan untuk invoice vendor.',who);mobile_snap('mobile-viewer-invoice-denied',who)
    return {'master_money_hidden':True,'invoice_denial_visible':True,'physical_device':False}

def gap_receipt_fixture():
    p=ROOT/'audit-results'/'remaining-fixture.json'
    assert p.exists(),{'missing_fixture':str(p),'required':'Native public priced dispatch and receipt fixture, no direct inserted receipt eligibility'}
    f=json.loads(p.read_text())['browser_receipts'];ids=f['receipt_line_ids'];expected=f['expected_count']
    assert expected>=201 and len(ids)==len(set(ids))==expected,f
    rows=sql("select rl.id::text,r.status,rl.actual_cost_status,rl.actual_cost::text,rl.qty_good_received,rl.qty_bs_laundry,d.vendor_id::text from erp.laundry_receipt_lines rl join erp.laundry_receipts r on r.id=rl.receipt_id join erp.laundry_delivery_lines dl on dl.id=rl.delivery_line_id join erp.laundry_deliveries d on d.id=dl.delivery_id where rl.id=any(%s::uuid[])",(ids,))
    assert len(rows)==expected and all(r[1]=='POSTED' and r[2]=='ESTIMATED' and r[3] is not None and r[4]==1 and r[5]==0 and r[6]==f['vendor_id'] for r in rows),rows
    billed=sql("select count(*) from erp.bd_laundry_invoice_lines_v1 l join erp.bd_laundry_invoices_v1 i on i.id=l.invoice_id where l.receipt_line_id=any(%s::uuid[]) and i.status='POSTED'",(ids,),one=True)
    assert billed==0,billed
    w=rpc('erp_get_laundry_bd_workspace_v1',{'p_filters':{'vendor_id':f['vendor_id']}})
    returned={x['receipt_line_id'] for x in w['billable_receipts']};missing=sorted(set(ids)-returned)
    assert returned.issubset(set(ids)),{'unrelated_sources':sorted(returned-set(ids))}
    probes=[];before=sql('select count(*) from erp.journal_entries',one=True)
    # A public draft of every omitted receipt is an additional positive control
    # that the absent identifier is a real usable source, not a fabricated row.
    for n,source in enumerate(missing):
        result=cmd('SAVE_INVOICE_DRAFT',{'vendor_id':f['vendor_id'],'invoice_number':'AUD-SOURCE-OMITTED-'+str(n),'invoice_date':'2026-09-21','header_total':'17.31',
            'lines':[{'line_kind':'BILL','receipt_line_id':source,'category':'GOOD','qty':1,'amount':'17.31'}]})
        assert result['status']=='DRAFT' and result['lines'][0]['receipt_line_id']==source,result
        probes.append({'source':source,'invoice_id':result['invoice_id'],'status':result['status']})
    assert sql('select count(*) from erp.journal_entries',one=True)==before,'Source eligibility drafts changed journals'
    FIX['receipt_gap']={**f,'returned_ids':sorted(returned),'missing_ids':missing,'positive_omitted_drafts':probes}
    return {'expected_public_lifecycle_receipts':expected,'native_verified_rows':len(rows),'posted_bills':billed,'public_returned_count':len(returned),
            'missing_ids':missing,'positive_omitted_drafts':probes,'provenance':f.get('provenance'),'journals_unchanged':True}

def gap_receipt_api_reachability():
    f=FIX['receipt_gap'];o={'expected':f['expected_count'],'public_returned':len(f['returned_ids']),'missing':f['missing_ids'],'omitted_sources_accepted_by_public_draft':f['positive_omitted_drafts']}
    assert not f['missing_ids'],o
    return o

def gap_open_desktop_invoices(vendor):
    ab('open','http://127.0.0.1:4176/');ab('wait','aside.sidebar');button('Produksi',exact=False);button('• Laundry')
    wait_text('Harga & tagihan');button('Harga & tagihan');ab('wait','select[aria-label="Vendor harga laundry"]')
    select('Vendor harga laundry',vendor);button('Invoice vendor');wait_text('Draf invoice baru')

def gap_receipt_browser_reachability():
    f=FIX['receipt_gap'];gap_open_desktop_invoices(f['vendor_id']);button('Tambah baris')
    selector='select[aria-label="Sumber baris 1"]';ab('wait',selector)
    dom=evaluate("(()=>{const s=document.querySelector('section[aria-label=\"Invoice vendor laundry\"]');return {options:Array.from(s.querySelector('select[aria-label=\"Sumber baris 1\"]').options).map(o=>({value:o.value,label:o.text})),controls:Array.from(s.querySelectorAll('button,input,select')).map(e=>({tag:e.tagName,label:e.getAttribute('aria-label'),text:e.tagName==='BUTTON'?e.textContent:null,type:e.getAttribute('type')}))};})()")
    ids={x['value'][2:] for x in dom['options'] if x['value'].startswith('r:')}
    assert ids==set(f['returned_ids']),{'browser_ids':sorted(ids),'http_ids':f['returned_ids']}
    select('Sumber baris 1','r:'+sorted(ids)[0]);snap('receipt-source-limit-201')
    navigation=[c for c in dom['controls'] if re.search(r'cari|search|selanjut|sebelum|next|previous|halaman|muat lebih',str(c),re.I)]
    missing=sorted(set(f['receipt_line_ids'])-ids)
    observation={'native_eligible_count':f['expected_count'],'http_count':len(f['returned_ids']),'browser_receipt_options':len(ids),
                 'missing_ids':missing,'paging_search_controls':navigation,'existing_source_selected':sorted(ids)[0]}
    EVENTS.append({'receipt_source_browser_gap':observation})
    assert not missing or navigation,observation
    return observation

def gap_bounded_reads():
    f=FIX['receipt_gap'];samples=[];expected_ids=set(f['returned_ids'])
    before=sql('select count(*) from erp.laundry_receipt_lines where id=any(%s::uuid[])',(f['receipt_line_ids'],),one=True)
    for _ in range(5):
        t=time.perf_counter();w=rpc('erp_get_laundry_bd_workspace_v1',{'p_filters':{'vendor_id':f['vendor_id']}});seconds=time.perf_counter()-t
        got={x['receipt_line_id'] for x in w['billable_receipts']}
        samples.append({'seconds':round(seconds,6),'http_receipts':len(got),'json_bytes':len(json.dumps(w).encode()),'same_returned_identifiers':got==expected_ids})
        assert got==expected_ids and seconds<10,{'audit_local_budget_seconds':10,'sample':samples[-1]}
    after=sql('select count(*) from erp.laundry_receipt_lines where id=any(%s::uuid[])',(f['receipt_line_ids'],),one=True)
    assert before==after==f['expected_count'],{'before':before,'after':after,'expected':f['expected_count']}
    return {'dataset_receipts':before,'sequential_reads':5,'samples':samples,'read_only_count_unchanged':True,
            'audit_local_budget_seconds':10,'completeness_assessed_separately':'HTTP.RECEIPT_SOURCE_CAP and BROWSER.RECEIPT_SOURCE_CAP',
            'limits':'Single local CI instance, five sequential reads; not concurrent or unlimited load certification'}

def gap_redye_boundary():
    schema=sql("select to_regclass('erp.be_redye_services_v1')::text,to_regprocedure('erp.be_set_redye_price_v1(jsonb,uuid)')::text")[0]
    w=rpc('erp_get_laundry_bd_workspace_v1',{'p_filters':{'vendor_id':FIX['vendor']}})
    # No valid BE service exists in the BD-only installed schema. This well-typed
    # envelope measures routing only; its identifier is explicitly a sentinel.
    sentinel=uid();status,body=rpc('erp_save_laundry_bd_action_v1',{'p_action':'SET_REDYE_PRICE',
        'p_payload':{'service_id':sentinel,'rate':'987.65','reason':'Independent latent UI route boundary'},'p_client_request_id':uid()},expect_ok=False)
    o={'be_service_table':schema[0],'be_price_function':schema[1],'reader_has_redye_services':'redye_services' in w,
       'public_route_status':status,'public_route_response':body,'sentinel_service_id':sentinel,'valid_be_service_fixture':False,
       'scope':'BD-only latent integration; no BE product schema installed; valid BE service mutation is not testable here'}
    FIX['redye_boundary']=o
    assert schema==(None,None) and 'redye_services' not in w and not 200<=status<300,o
    return o

def gap_redye_browser_boundary():
    gap_open_desktop_invoices(FIX['vendor'])
    dom=evaluate("({redye_sections:document.querySelectorAll('section[aria-label=\"Jasa celup ulang\"]').length,redye_buttons:Array.from(document.querySelectorAll('button')).filter(b=>b.textContent.includes('Isi tarif celup')).map(b=>b.textContent)})")
    snap('redye-latent-bd-boundary')
    assert dom['redye_sections']==0 and not dom['redye_buttons'],dom
    return {'actual_ui':dom,'reader_and_route':FIX.get('redye_boundary'),'scope':'Latent UI only: no visible current redye button was clicked'}

def run_gap_continuation():
    own='independent gap completion';peer='peer-informed HTTP/browser continuation'
    if case('HTTP.OWNER_REVOCATION_CONTROLS','Real Auth owner revocation/restoration, ordinary read and fresh UUID controls',gap_replay_controls,peer):
        case('HTTP.OWNER_POLICY_REPLAY','Owner-only policy replay must refuse revoked actor',lambda:gap_replay_refusal('policy'),peer)
        case('HTTP.OWNER_INVOICE_REPLAY','Invoice replay must not disclose cached money after revocation',lambda:gap_replay_refusal('invoice'),peer)
    else:
        RESULTS.append({'id':'HTTP.OWNER_REPLAY_DEPENDENT','status':'BLOCKED','origin':peer,'reason':'Revocation/restore control prerequisites failed; no refusal oracle established'});save()
    try:
        if case('MOBILE.AUTH_OWNER','Real owner login with iPhone14 browser emulation',lambda:mobile_auth('mobile_owner','owner'),own):
            case('MOBILE.MASTER','Emulated mobile known/unknown and master creation with HTTP/DB proof',mobile_master,own)
            case('MOBILE.DRAFT_RELOAD','Emulated mobile invoice draft and exact stored values after reload',mobile_draft,own)
        else:
            RESULTS.append({'id':'MOBILE.OWNER_DEPENDENT','status':'BLOCKED','origin':own,'reason':'Real mobile-emulated owner authentication prerequisite failed'});save()
        if case('MOBILE.AUTH_VIEWER','Real viewer login with iPhone14 browser emulation',lambda:mobile_auth('mobile_viewer','viewer'),own):
            case('MOBILE.VIEWER','Emulated mobile role visibility and invoice denial',mobile_viewer,own)
        else:
            RESULTS.append({'id':'MOBILE.VIEWER','status':'BLOCKED','origin':own,'reason':'Real mobile-emulated viewer authentication prerequisite failed'});save()
    finally:
        for who in ('mobile_owner','mobile_viewer'):
            for operation in ('errors','console','close'):
                try:ab(operation,who=who,check=False)
                except Exception:pass
            if FIX.get(who+'_touch_worker'):FIX[who+'_touch_worker'].terminate()
    if case('HTTP.RECEIPT_SOURCE_FIXTURE','201 legitimate public-lifecycle receipt sources and omitted-source positive control',gap_receipt_fixture,peer):
        case('HTTP.RECEIPT_SOURCE_CAP','Every eligible receipt remains reachable from public reader',gap_receipt_api_reachability,peer)
        case('BROWSER.RECEIPT_SOURCE_CAP','Every eligible receipt remains selectable or searchable in new invoice',gap_receipt_browser_reachability,peer)
        case('HTTP.BOUNDED_LARGER_READS','Five bounded larger-data reads preserve exact native counts',gap_bounded_reads,own)
    else:
        RESULTS.append({'id':'RECEIPT_SOURCE_DEPENDENT','status':'BLOCKED','origin':peer,'reason':'Public-lifecycle 201-receipt fixture prerequisite failed; no fabricated eligibility used'});save()
    case('HTTP.REDYE_BOUNDARY','Measure missing BE reader/schema and actual BD HTTP route',gap_redye_boundary,'cross-check from prior static redye observation')
    case('BROWSER.REDYE_BOUNDARY','Observe latent redye controls against actual BD reader',gap_redye_browser_boundary,'cross-check from prior static redye observation')

def cleanup():
    for who in ['owner','viewer']:
        try:ab('errors',who=who,check=False);ab('console',who=who,check=False);ab('close',who=who,check=False)
        except Exception:pass
    for p in PROCESSES:p.terminate()
    if FIX.get('proxy'):FIX['proxy'].shutdown()
    try:
        log=run(['docker','logs','bd-independent-rest'],check=False).stdout
        (OUT/'postgrest.log').write_text(redact(log))
        run(['docker','rm','-f','bd-independent-rest'],check=False)
    except Exception:pass
    save()

def main():
    try:
        setup_gateway()
        if not case('HTTP.AUTH','Real local Auth accounts and ERP access',setup_identities):
            RESULTS.append({'id':'HTTP_BROWSER.AUTH_DEPENDENT','status':'BLOCKED','reason':'Real Auth/ERP identity prerequisite failed; no browser behavior established'})
            save();return 1
        if not case('HTTP.FIXTURE','Own master fixtures through real public HTTP',setup_master):
            RESULTS.append({'id':'HTTP_BROWSER.FIXTURE_DEPENDENT','status':'BLOCKED','reason':'Own master fixture prerequisite failed; downstream assertions not executed'})
            save();return 1
        case('HTTP.KNOWN_UNKNOWN','Known value and unknown null over HTTP',owner_http)
        case('HTTP.VIEWER','Active viewer reads quantities, cannot see money or create master',viewer_http)
        if not case('BROWSER.BUILD','Actual candidate UI build and local server',build_ui):
            RESULTS.append({'id':'BROWSER.DEPENDENT','status':'BLOCKED','reason':'Actual UI build/server prerequisite failed; HTTP results remain separate'})
            save();return 1
        owner_auth=case('BROWSER.AUTH_OWNER','Real browser owner password login',browser_auth)
        if owner_auth and case('BROWSER.LOGIN','Real owner BD workspace and fixture vendor selection',open_bd_master):
            case('BROWSER.KNOWN_UNKNOWN','Known price versus unknown UI presentation',owner_browser_known_unknown)
            case('BROWSER.MASTER','Create master through UI and verify committed row',browser_master_create)
            case('BROWSER.INVOICE_DRAFT_RELOAD','Create invoice draft through UI, reload, verify no journal',browser_invoice_draft_reload)
            case('BROWSER.PACKAGE_EXTRAS','Package shipment offers outside-package extras',package_extras_browser,'peer-informed reproduction')
            if case('HTTP.PAGINATION_FIXTURE','55 public invoice drafts without ledger effects',seed_pagination,'peer-informed reproduction'):
                case('BROWSER.INVOICE_PAGINATION','Invoices beyond 50 remain reachable with search or paging',pagination_browser,'peer-informed reproduction')
        else:
            RESULTS.append({'id':'BROWSER.OWNER_DEPENDENT','status':'BLOCKED','reason':'Real owner browser login/BD workspace prerequisite failed'})
            save()
        if case('BROWSER.AUTH_VIEWER','Real browser viewer password login',lambda:browser_auth('viewer')):
            case('BROWSER.VIEWER','Actual viewer UI hides nominal values and invoices',viewer_browser)
        run_gap_continuation()
    except Exception as e:
        RESULTS.append({'id':'HTTP_BROWSER.SETUP','status':'BLOCKED','error':redact(e),'traceback':redact(traceback.format_exc())});save();raise
    finally:cleanup()
    return int(any(r['status']!='PASS' for r in RESULTS))
if __name__=='__main__':raise SystemExit(main())
