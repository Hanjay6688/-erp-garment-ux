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
import concurrent.futures, http.client, json, os, re, secrets, subprocess, threading, time, traceback, uuid
import psycopg

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'audit-results'/'http-browser';OUT.mkdir(parents=True,exist_ok=True)
DSN='postgresql://postgres:postgres@127.0.0.1:54322/cp6_rollback'
RESULTS=[];EVENTS=[];HTTP_EVENTS=[];FIX={};KEYS={};TOKENS={};PROCESSES=[]
PRODUCT='08065a3b4da71c51ffbbab77f0a6b1ac7e6638ec'
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

def setup_gateway():
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
    server=ThreadingHTTPServer(('127.0.0.1',54328),Proxy)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    FIX['proxy']=server
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
    except Exception as e:
        RESULTS.append({'id':'HTTP_BROWSER.SETUP','status':'BLOCKED','error':redact(e),'traceback':redact(traceback.format_exc())});save();raise
    finally:cleanup()
    return int(any(r['status']!='PASS' for r in RESULTS))
if __name__=='__main__':raise SystemExit(main())
