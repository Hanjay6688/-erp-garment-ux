"""Confirm a public macOS runner can operate the requested simulator, Safari and a second app."""
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

def shell(*args):
    return subprocess.check_output(args,text=True).strip()

def simulator(family):
    runtimes=json.loads(shell('xcrun','simctl','list','runtimes','-j'))['runtimes']
    available={r['identifier']:r['version'] for r in runtimes if r['isAvailable'] and r['name'].startswith('iOS ')}
    inventory=json.loads(shell('xcrun','simctl','list','devices','available','-j'))['devices']
    for runtime in sorted(available,key=lambda key:tuple(map(int,available[key].split('.'))),reverse=True):
        for d in inventory.get(runtime,[]):
            if d['name'].startswith(family) and d['isAvailable']:
                return d['udid'],d['name'],available[runtime]
    raise RuntimeError('No installed simulator for '+family)

def command(path,payload=None,method=None):
    data=None if payload is None else json.dumps(payload).encode()
    req=urllib.request.Request('http://127.0.0.1:4444'+path,data=data,method=method,headers={'Content-Type':'application/json'})
    try:
        return json.load(urllib.request.urlopen(req,timeout=75)).get('value')
    except urllib.error.HTTPError as exc:
        detail=json.loads(exc.read())
        raise RuntimeError(detail['value'].get('message',str(exc))) from exc

@contextmanager
def safari(family):
    device,name,version=simulator(family)
    print('ASTRA_SIMULATOR '+json.dumps({'family':family,'name':name,'version':version}),flush=True)
    subprocess.run(['xcrun','simctl','boot',device],check=False)
    shell('xcrun','simctl','bootstatus',device,'-b')
    shell('sudo','safaridriver','--enable')
    proc=subprocess.Popen(['/usr/bin/safaridriver','-p','4444','--diagnose'])
    session=None
    try:
        for _ in range(80):
            try:command('/status');break
            except (OSError,RuntimeError):time.sleep(.25)
        caps={'browserName':'Safari','platformName':'iOS','safari:useSimulator':True,'safari:deviceUDID':device}
        start=command('/session',{'capabilities':{'alwaysMatch':caps}})
        session='/session/'+start['sessionId']
        yield device,name,version,start['capabilities'],lambda path,data=None:command(session+path,data)
    finally:
        if session:
            try:command(session,method='DELETE')
            except (RuntimeError,OSError):pass
        proc.terminate()
        proc.wait(timeout=15)
        subprocess.run(['xcrun','simctl','shutdown',device],check=False)

def roundtrip(device):
    shell('xcrun','simctl','launch',device,'com.apple.Preferences')
    time.sleep(1.4)
    shell('xcrun','simctl','launch',device,'com.apple.mobilesafari')
    time.sleep(.6)

if __name__=='__main__':
    family=sys.argv[1]
    html=b'<meta name="viewport" content="width=device-width,initial-scale=1"><label>Note<input id="note"></label><script>window.visibilityLog=[];document.addEventListener("visibilitychange",()=>visibilityLog.push(document.visibilityState))</script>'
    class Page(BaseHTTPRequestHandler):
        def log_message(self,*_):pass
        def do_GET(self):
            self.send_response(200);self.send_header('Content-Type','text/html');self.end_headers();self.wfile.write(html)
    with ThreadingHTTPServer(('127.0.0.1',0),Page)as web,safari(family)as info:
        device,name,version,caps,call=info
        thread=Thread(target=web.serve_forever,daemon=True);thread.start()
        try:
            call('/url',{'url':'http://127.0.0.1:'+str(web.server_port)})
            element=call('/element',{'using':'css selector','value':'#note'})
            ident=element['element-6066-11e4-a52e-4f735466cecf']
            call('/element/'+ident+'/value',{'text':'Astra synthetic note'})
            before=call('/execute/sync',{'script':'return {touch:navigator.maxTouchPoints,ua:navigator.userAgent,value:document.querySelector("#note").value}','args':[]})
            roundtrip(device)
            after=call('/execute/sync',{'script':'return {events:window.visibilityLog,value:document.querySelector("#note").value}','args':[]})
            assert before['value']==after['value']=='Astra synthetic note' and before['touch']>0
            assert 'hidden' in after['events'] and 'visible' in after['events'],after
            print('ASTRA_PUBLIC_RUNTIME '+json.dumps({'surface':'Apple Simulator','model':name,'version':version,'initial':before,'returned':after,'safari':caps.get('browserVersion')}))
        finally:web.shutdown();thread.join()
