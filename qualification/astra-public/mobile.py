"""Serve the candidate and a published synthetic contract fixture on loopback to an Apple simulator."""
import json
import os
import plistlib
import shutil
import subprocess
import sys
import time
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from threading import Event,Thread
from urllib.parse import urlsplit
from runtime import simulator,shell

here=Path(__file__).resolve().parent
surface=sys.argv[1]
assets=Path(sys.argv[2]).resolve()
sample=json.loads((assets/'sample.json').read_bytes())
receipt=json.loads((assets/'receipt.json').read_bytes())
state={'events':{},'calls':[],'deny':False,'request':None}
resume=Event()

class App(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def reply(self,body,kind='application/json',code=200):
        if not isinstance(body,bytes):body=json.dumps(body).encode()
        self.send_response(code);self.send_header('Content-Type',kind);self.send_header('Cache-Control','no-store')
        self.send_header('Permissions-Policy','clipboard-write=(), clipboard-read=()');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    def do_GET(self):
        p=urlsplit(self.path).path
        if p=='/':
            head='<meta name="viewport" content="width=device-width,initial-scale=1"><meta charset="utf-8">'
            flags='<script>window.developmentControl='+json.dumps(surface=='local')+'</script>'
            return self.reply((head+flags+'<iframe id="analysis" sandbox="allow-scripts allow-same-origin" src="/app"></iframe><iframe id="reminders" sandbox="allow-scripts allow-same-origin" src="/app?reminders"></iframe><style>iframe{display:block;width:98vw;height:44vh;border:0}</style><script>addEventListener("load",()=>{const s=document.createElement("script");s.src="/case.js";document.body.append(s)})</script>').encode(),'text/html')
        if p=='/app':return self.reply(b'<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/ui.css"><div id="erp"></div><script src="/ui.js"></script>','text/html')
        if p=='/case.js':return self.reply((here/'mobile-case.js').read_bytes(),'text/javascript')
        if p in ('/ui.js','/ui.css'):return self.reply((assets/p[1:]).read_bytes(),'text/css' if p.endswith('css')else 'text/javascript')
        if p=='/release':return self.reply({'released':resume.wait(60)})
        return self.reply({},code=404)
    def do_POST(self):
        value=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        if self.path=='/event':
            label=value['label'];state['events'][label]=value
            print('ASTRA_MOBILE_STEP '+json.dumps({'label':label,'step':value.get('step'),'error':value.get('error'),'checks':list(value['checks'])}),flush=True)
            return self.reply({'ok':True})
        if self.path=='/fault':state['deny']=True;return self.reply({'armed':True})
        if not self.path.startswith('/rest/v1/rpc/'):return self.reply({},code=404)
        name=self.path.rsplit('/',1)[-1];state['calls'].append(name)
        if name in ('erp_cp7_capture_operational_analysis_v1','erp_cp7_capture_analysis_v1'):
            assert value['p_query']==sample['query'];state['request']=value['p_request']
            return self.reply(dict(sample,request_id=state['request']))
        if name=='erp_cp7_read_analysis_v1':
            assert value['p_run']==sample['run_id'] and state['request']
            if state['deny']:state['deny']=False;return self.reply({'message':'Incomplete synthetic test response'},code=503)
            return self.reply(dict(sample,request_id=state['request']))
        if name=='erp_cp7_get_reminders_v1':
            q=value['p_query']
            return self.reply(dict(contract_version='cp7.reminders-workspace.v1',filter=q['filter'],
                page=dict(limit=q['limit'],offset=q['offset'],total=0,shown=0,window=0,window_limit=200,next_offset=None,beyond_window=0),
                items=[],counts=dict(open=0,done=0,cancelled=0),due=dict(overdue=0,today=0,tomorrow=0,complete=True),
                today='2026-10-17',read_at='2026-10-17T03:00:00+00:00',can_manage=True,business_DML=False))
        return self.reply({'message':'Unrecognized fixture route'},code=400)

def wait_phase(name,seconds):
    until=time.monotonic()+seconds
    while time.monotonic()<until:
        if 'failed'in state['events']:raise RuntimeError(json.dumps(state['events']['failed']))
        if name in state['events']:return
        time.sleep(.25)
    raise TimeoutError(name+'; observed '+str(list(state['events']))+'; calls '+str(state['calls']))

def install_host(device):
    app=assets/'AstraSimulator.app';app.mkdir(exist_ok=True)
    sdk=shell('xcrun','--sdk','iphonesimulator','--show-sdk-path')
    arch=shell('uname','-m')
    shell('xcrun','--sdk','iphonesimulator','swiftc','-parse-as-library','-target',arch+'-apple-ios17.0-simulator','-sdk',sdk,
          '-framework','UIKit','-framework','WebKit',str(here/'SimulatorHost.swift'),'-o',str(app/'AstraSimulator'))
    info=dict(CFBundleIdentifier='org.astra.audit.simulator',CFBundleExecutable='AstraSimulator',CFBundlePackageType='APPL',
              CFBundleName='Astra Simulator',CFBundleShortVersionString='1.0',CFBundleVersion='1',MinimumOSVersion='17.0',
              UIDeviceFamily=[1,2],LSRequiresIPhoneOS=True,UILaunchScreen={},NSAppTransportSecurity={'NSAllowsLocalNetworking':True})
    with (app/'Info.plist').open('wb')as out:plistlib.dump(info,out)
    shell('codesign','--force','--sign','-',str(app));shell('xcrun','simctl','install',device,str(app))

with ThreadingHTTPServer(('127.0.0.1',0),App)as server:
    thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    url='http://127.0.0.1:'+str(server.server_port)
    if surface=='local':
        chrome=os.environ['WRITER_CHROME']
        proc=subprocess.Popen([chrome,'--headless','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--user-data-dir='+str(assets/'chrome-home'),url],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            wait_phase('switch',45);resume.set();wait_phase('complete',40)
            print('ASTRA_LOCAL_CONTROL '+json.dumps(state['events']['complete']['checks']))
        finally:resume.set();proc.terminate();proc.wait(timeout=10);server.shutdown()
    else:
        device,model,version=simulator(surface)
        print('ASTRA_SIMULATOR '+json.dumps({'model':model,'version':version}),flush=True)
        subprocess.run(['xcrun','simctl','boot',device],check=False);shell('xcrun','simctl','bootstatus',device,'-b')
        flavor='Mobile Safari';bundle='com.apple.mobilesafari'
        try:
            shell('xcrun','simctl','openurl',device,url)
            try:wait_phase('switch',50)
            except TimeoutError:
                if state['calls'] or state['events']:raise
                flavor='WKWebView';bundle='org.astra.audit.simulator'
                install_host(device);shell('xcrun','simctl','launch',device,bundle,url)
                wait_phase('switch',40)
            shell('xcrun','simctl','launch',device,'com.apple.Preferences');time.sleep(2.5)
            shell('xcrun','simctl','launch',device,bundle);time.sleep(.8);resume.set()
            wait_phase('complete',45)
            assert state['events']['complete']['touch']>0
        finally:
            resume.set()
            evidence={'build':receipt,'hardware':False,'family':surface,'model':model,'simulator_version':version,'engine':flavor,
                      'transport':'published synthetic contract fixture over loopback HTTP','events':state['events'],'calls':state['calls']}
            print('ASTRA_MOBILE_RECEIPT '+json.dumps(evidence,separators=(',',':')),flush=True)
            server.shutdown();subprocess.run(['xcrun','simctl','shutdown',device],check=False)
