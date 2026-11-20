"""Auditor entry point for a public job. The only remote input during restore is a wrapped key."""
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import time
from zipfile import ZipFile
from .audit_access import challenge
from .checkpoint import digest
from .source import PRODUCT,TREE,check

REPO='Hanjay6688/-erp-garment-ux'
FOLDER='qualification/astra-public/close11-key-grants'
BRANCH='audit/astra-cp7-public-ffda'

def api(path,timeout=90):
    return json.loads(subprocess.check_output(['gh','api',f'repos/{REPO}/'+path],stderr=subprocess.PIPE,timeout=timeout))
def fetch(a,path):
    with path.open('xb') as stream:subprocess.run(['gh','api',f"repos/{REPO}/actions/artifacts/{a['id']}/zip"],stdout=stream,stderr=subprocess.PIPE,check=True,timeout=600)
    check(a['digest']=='sha256:'+digest(path),'CLOSE11_ARTIFACT_SHA')

def install_build_inputs(app,inputs):
    """The source tree's regular frontend tests are typechecked by npm run build."""
    def object_id(kind,data):
        return hashlib.sha1(kind+b' '+str(len(data)).encode()+b'\0'+data).digest()
    fixtures=inputs/'fixtures'
    entries=[]
    for path in sorted(fixtures.iterdir(),key=lambda p:p.name.encode()):
        check(path.is_file() and not path.is_symlink(),'CLOSE11_UI_FIXTURE_KIND')
        entries.append(b'100644 '+path.name.encode()+b'\0'+object_id(b'blob',path.read_bytes()))
    check(object_id(b'tree',b''.join(entries)).hex()=='b50c67c3b2cd85a14a69b5e3abc1dde53ec2f868','CLOSE11_UI_FIXTURE_TREE')
    controls=inputs/'LOCAL_SETTINGS_CONTROLS.json'
    check(object_id(b'blob',controls.read_bytes()).hex()=='8711259fd44ee7305548fb061e4cc88ffc976433','CLOSE11_UI_CONTROLS_SOURCE')
    scanner=inputs/'scan-client-artifacts.mjs'
    check(object_id(b'blob',scanner.read_bytes()).hex()=='4e9ab66106ddc79dd150c373d5eae5764f6bbada','CLOSE11_UI_POSTBUILD_SOURCE')
    (app/'tests').mkdir(exist_ok=True)
    shutil.copytree(fixtures,app/'tests/fixtures',dirs_exist_ok=True)
    destination=app/'scripts/cp7_accessory_nonpayable'
    destination.mkdir(exist_ok=True)
    shutil.copyfile(controls,destination/controls.name)
    shutil.copyfile(scanner,app/'scripts'/scanner.name)

def plan(work):
    run=os.environ['ORIGIN_RUN'];head=os.environ['ORIGIN_RUNNER']
    check(run.isdecimal() and re.fullmatch(r'[0-9a-f]{40}',head),'CLOSE11_ORIGIN_ARGUMENTS')
    info=api('actions/runs/'+run);check(info['repository']['full_name']==REPO and info['head_sha']==head and info['conclusion']=='success','CLOSE11_ORIGIN_RUN_IDENTITY')
    arts={a['name']:a for a in api('actions/runs/'+run+'/artifacts?per_page=100')['artifacts']}
    wanted={'terminal':['terminal.json'],'catalogue':['installed.json'],'auditor-environment':['global-ffda.cp7'],'auditor-ui':['ffda-ui.tar.gz','ui.sha256']}
    for label,names in wanted.items():
        artifact=arts['writer-global-'+label+'-'+run];check(not artifact['expired'],'CLOSE11_ARTIFACT_EXPIRED')
        temp=work/(label+'.zip');fetch(artifact,temp)
        with ZipFile(temp) as z:
            check(z.testzip() is None,'CLOSE11_ARTIFACT_CRC')
            for name in names:
                matches=[i for i in z.infolist() if Path(i.filename).name==name]
                check(len(matches)==1,'CLOSE11_ARCHIVE_MEMBER '+name)
                with z.open(matches[0]) as source,(work/name).open('xb') as out:
                    import shutil
                    shutil.copyfileobj(source,out,length=1<<20)
        temp.unlink()
    terminal=json.loads((work/'terminal.json').read_bytes());rec=json.loads((work/'installed.json').read_bytes())
    check(terminal['status']=='INSTALLED_AND_PRESERVED' and rec['product']==PRODUCT and rec['tree']==TREE and rec['run']==run and rec['runner']==head and rec['catalogue_verified_after_scheduler'] is True,'CLOSE11_WRITER_TERMINAL')
    check(digest(work/'ffda-ui.tar.gz')==(work/'ui.sha256').read_text().split()[0],'CLOSE11_UI_DIGEST')
    with tarfile.open(work/'ffda-ui.tar.gz','r:gz') as t:t.extractall(path=work/'ui',filter='data')
    install_build_inputs(work/'ui/product',Path(__file__).parent/'build-inputs')
    challenge(work/'installed.json',work/'global-ffda.cp7',work/'request.json',work/'receiver.pem')
    print('Receiver ready for auditor run '+os.environ['GITHUB_RUN_ID']+' at '+os.environ['GITHUB_SHA'])
def restore(work):
    run=os.environ['GITHUB_RUN_ID'];deadline=time.monotonic()+1200;reply=work/'reply.json'
    while time.monotonic()<deadline:
        try:
            r=api('contents/'+FOLDER+'/'+run+'.json?ref='+BRANCH,timeout=25)
            data=base64.b64decode(r['content']);check(len(data)<2500,'CLOSE11_GRANT_SIZE')
            reply.write_bytes(data);break
        except subprocess.CalledProcessError as e:
            if b'404' not in (e.stderr or b''):raise
            time.sleep(15)
    else:raise TimeoutError('CLOSE11_AUDITOR_RECEIVER_EXPIRED')
    client=['--installed',str(work/'installed.json'),'--checkpoint',str(work/'global-ffda.cp7'),'--receiver-key',str(work/'receiver.pem'),'--request',str(work/'request.json'),'--reply',str(reply),'--network','internal','--container-file',str(work/'container.txt'),'--socket-dir',str(work/'socket')]
    try:subprocess.run([sys.executable,'-m','close11.resume',*client],check=True,timeout=900)
    finally:(work/'receiver.pem').unlink(missing_ok=True)
    container=(work/'container.txt').read_text().strip()
    check(re.fullmatch(r'cp7-ffda-audit-[0-9a-f]{10}',container),'CLOSE11_CONTAINER_NAME')
    with open(os.environ['GITHUB_OUTPUT'],'a') as out:
        print('container='+container,'socket='+str(work/'socket'),'application='+str(work/'ui/product'),file=out,sep='\n')

if __name__=='__main__':
    check(os.environ['GITHUB_REPOSITORY']==REPO and os.environ['GITHUB_REF'].startswith('refs/heads/audit/'),'CLOSE11_AUDITOR_REF_ONLY')
    workspace=Path(os.environ['RUNNER_TEMP'])/'cp7-global-auditor'
    if sys.argv[1:]==['prepare']:workspace.mkdir(mode=0o700);plan(workspace)
    elif sys.argv[1:]==['restore']:restore(workspace)
    else:raise SystemExit('prepare or restore')
