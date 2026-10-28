"""Exact complete backend11 plus explicit money-label-only client successor."""
from pathlib import Path
from hashlib import sha256
import importlib.util,json,os,subprocess,tempfile


def client_label(before,after):
    old="      <div><dt>Pencocokan</dt><dd role=\"status\">{l.matches ? 'Cocok: saldo utang = sisa tagihan − kredit belum dipakai' : 'Tidak cocok: periksa pelunasan dan klaim vendor ini'}</dd></div>"
    new="""      <div><dt>Pencocokan</dt><dd role="status">{l.matches ? l.receivable_balance === undefined
        ? 'Cocok: saldo utang = sisa tagihan − kredit belum dipakai'
        : 'Cocok: saldo utang = sisa tagihan − kredit belum dipakai + piutang ke vendor'
        : 'Tidak cocok: periksa pelunasan dan klaim vendor ini'}</dd></div>"""
    anchor='    </dl>\n    <table aria-label="Tagihan vendor">'
    replacement='    </dl>\n    {l.receivable_balance !== undefined && <p>Piutang ke vendor sudah termasuk dalam kredit belum dipakai. Angka itu bukan kredit tambahan.</p>}\n    <table aria-label="Tagihan vendor">'
    if before.count(old)!=1 or before.count(anchor)!=1 or after!=before.replace(old,new,1).replace(anchor,replacement,1):
        raise ValueError('VENDOR_BROWSER_ONLY_DECLARED_CLIENT_LABEL_SUCCESSOR_ALLOWED')


def admitted(repo,here,product):
    cfg=json.loads((here/'CONFIG.json').read_bytes());source=json.loads((here/'SOURCE.json').read_bytes())
    pin=cfg.get('accepted_backend11')
    if pin is None:raise ValueError('VENDOR_MONEY_BROWSER_CLOSED_COMPLETE_BACKEND11_REQUIRED')
    for path,digest in source['files'].items():assert sha256((repo/path).read_bytes()).hexdigest()==digest,path
    changed=subprocess.check_output(['git','-C',str(repo),'diff','--name-only',cfg['base_head'],'HEAD'],text=True).splitlines()
    assert set(changed)<=set(source['allowed_changes']),'UNDECLARED_VENDOR_BROWSER_CHANGE'
    assert not subprocess.check_output(['git','-C',str(repo),'status','--porcelain','--untracked-files=no']).strip()
    verifier=cfg['frozen_intake_verifier']
    raw_verifier=subprocess.check_output(['git','-C',str(repo),'show',verifier['head']+':'+verifier['path']])
    assert sha256(raw_verifier).hexdigest()==verifier['sha256']
    root=Path(os.environ['CP7_VENDOR_BACKEND11_ORIGINALS'])
    raw=(root/pin['original']['name']).read_bytes();package=(root/pin['package']['name']).read_bytes()
    current=product.sources()
    parent_digest=sha256(json.dumps(current['predecessor'],sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
    assert parent_digest==cfg['parent_backend_sha256']
    with tempfile.TemporaryDirectory(prefix='vendor-intake-verifier-')as directory:
        path=Path(directory)/'scripts/intake/check.py';path.parent.mkdir(parents=True);path.write_bytes(raw_verifier)
        spec=importlib.util.spec_from_file_location('frozen_vendor_backend11_verifier',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        prerequisite=module.admit(pin,raw,package,current['files'],parent_digest)
    backend=json.loads(raw);client_sources=backend['source_declaration']['qualification']['files']
    label_path='src/LaundryBdPanel.tsx'
    for path in cfg['client_files']:
        old=subprocess.check_output(['git','-C',str(repo),'show',pin['head']+':'+path])
        assert sha256(old).hexdigest()==client_sources[path],path
        if path==label_path:client_label(old.decode(),(repo/path).read_text())
        else:assert(repo/path).read_bytes()==old,path
    return dict(status='EXACT_COMPLETE_BACKEND11_AND_LABEL_SUCCESSOR_ADMITTED',prerequisite=prerequisite,
        qualification=source,current_installation=current,parent_backend_sha256=parent_digest,
        actual_backend_cases_repeated=0,planned_browser_cases=2,B_combined_browser_repeated=False,
        production_go=False,independent_acceptance=False)
