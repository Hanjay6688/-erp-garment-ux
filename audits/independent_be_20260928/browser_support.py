"""Transport/browser primitives reused from our own BD audit; no old business cases."""

from pathlib import Path

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from urllib.request import Request, urlopen

from urllib.error import HTTPError, URLError

from datetime import datetime

from zoneinfo import ZoneInfo

import concurrent.futures, errno, http.client, json, os, re, secrets, subprocess, threading, time, traceback, uuid

import psycopg, socket

ROOT=Path(__file__).resolve().parents[2]

OUT=ROOT/'audit-results'/'http-browser'

DSN='postgresql://postgres:postgres@127.0.0.1:54322/cp6_rollback'

RESULTS=[]

EVENTS=[]

HTTP_EVENTS=[]

FIX={}

KEYS={}

TOKENS={}

PROCESSES=[]

PRODUCT='e09b0207f08b7736fad79e82fd81f1bf5dc1a85d'

SECRET_VALUES=[]

def uid(): return str(uuid.uuid4())

def redact(value):
    s=str(value)
    for secret in SECRET_VALUES:
        if secret:s=s.replace(secret,'[REDACTED]')
    return re.sub(r'eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+','[JWT_REDACTED]',s)

def case(key,title,fn,origin='independent continuation'):
    row={'id':key,'title':title,'origin':origin};start=time.monotonic()
    try:row.update(status='PASS',observation=fn())
    except Exception as e:
        row.update(status='FAIL',error=redact(e),traceback=redact(traceback.format_exc()))
        try:
            who='mobile' if key.startswith('MOBILE.') else 'viewer' if 'VIEWER' in key else 'owner'
            snap('FAILED-'+key,who)
            (OUT/('FAILED-'+key+'-body.txt')).write_text(redact(text_body(who)))
        except Exception as capture:row['capture_error']=str(capture)
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
            if is_rest and path.endswith('/rpc/erp_save_product_conversion_action_v1') and FIX.get('drop_next_conversion') and json.loads(payload).get('p_action')=='POST':
                FIX['drop_next_conversion']=False
                HTTP_EVENTS.append({'method':self.command,'path':self.path,'http_status':response.status,'payload':json.loads(payload),'response':json.loads(body),'deliberately_lost_after_real_database_response':True})
                self.close_connection=True
                try:self.connection.shutdown(socket.SHUT_RDWR)
                except OSError:pass
                return
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
    p=ROOT/'audit-results'/'.be-http-env-private'
    p.write_text('\n'.join(k+'='+v for k,v in env.items())+'\n');p.chmod(0o600)
    try:run(['docker','run','--detach','--name','be-independent-rest','--network','host','--env-file',str(p),original['Config']['Image']])
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
        email='be-independent-'+who+'-'+uid()[:8]+'@example.test';password='Bd-Audit-'+secrets.token_hex(16)+'!'
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
    p=run(['agent-browser','--session','be-independent-'+who,*args],timeout=timeout,check=False)
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

def control_selector(code,who='owner'):
    ab('wait','--fn','(()=>{const e='+code+';return !!e&&!e.disabled;})()',who=who)
    selector=evaluate('(()=>{let e='+code+';const p=[];while(e&&e.nodeType===1){let n=1,s=e;while((s=s.previousElementSibling))if(s.tagName===e.tagName)n++;p.unshift(e.tagName.toLowerCase()+":nth-of-type("+n+")");e=e.parentElement;}return p.join(" > ");})()',who)
    return selector

def fill(label,value,who='owner'):
    code='(document.querySelector('+json.dumps('[aria-label='+json.dumps(label)+']')+')||Array.from(document.querySelectorAll("label")).find(l=>l.textContent.trim()==='+json.dumps(label)+')?.control)'
    selector=control_selector(code,who)
    ab('snapshot','-i',who=who)
    if evaluate(code+'.type',who) in ['date','datetime-local']:
        native_input(selector,value,who)
    else:ab('fill',selector,value,who=who)
    actual=evaluate('({value:'+code+'.value})',who)['value']
    assert actual==str(value),{'input_entry_prerequisite':label,'expected':str(value),'actual':actual}

def native_input(selector,value,who='owner'):
    raw=ab('get','cdp-url',who=who)
    endpoints=re.findall(r'ws://(?:127\.0\.0\.1|localhost):\d+/[^\s"\x27]+',raw)
    assert len(endpoints)==1,{'cdp_endpoints':len(endpoints)}
    worker=r'''
import {pathToFileURL} from 'node:url';
const {chromium}=await import(pathToFileURL(process.env.BE_PLAYWRIGHT_CORE+'/index.mjs').href);
const [endpoint, selector, value]=process.argv.slice(1);
const browser=await chromium.connectOverCDP(endpoint);
try {
 const pages=browser.contexts().flatMap(c=>c.pages()).filter(p=>p.url().startsWith('http://127.0.0.1:4176/'));
 if(pages.length!==1)throw new Error('Expected exactly one real app page: '+pages.length);
 const locator=pages[0].locator(selector);await locator.fill(value);await locator.press('Tab');
 console.log(JSON.stringify({input_value:await locator.inputValue(),adapter:'playwright-native-locator-fill'}));
} finally {await browser.close();}
'''
    r=run(['node','--input-type=module','-e',worker,endpoints[0],selector,value],timeout=45)
    out=json.loads(r.stdout);assert out['input_value']==value,out
    EVENTS.append({'native_input':out,'selector':selector,'session':who})

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

def cleanup():
    for who in ['owner','viewer','mobile','mobile_viewer']:
        try:ab('errors',who=who,check=False);ab('console',who=who,check=False);ab('close',who=who,check=False)
        except Exception:pass
    for p in PROCESSES:p.terminate()
    if FIX.get('proxy'):FIX['proxy'].shutdown()
    try:
        log=run(['docker','logs','be-independent-rest'],check=False).stdout
        (OUT/'postgrest.log').write_text(redact(log))
        run(['docker','rm','-f','be-independent-rest'],check=False)
    except Exception:pass
    save()
