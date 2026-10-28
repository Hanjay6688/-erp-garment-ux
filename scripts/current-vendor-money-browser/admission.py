"""Exact backend11, money labels and scoped disabled-button readability."""
from pathlib import Path
from hashlib import sha256
import gzip,importlib.util,json,os,subprocess,tempfile


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


def client_style(before,after):
    addition='\n/* Vendor money actions remain legible while native disabled guards prevent submission. */\n.initial-import [aria-label="Pembayaran vendor laundry"] button:disabled { opacity: 1; border-style: dashed; }\n'
    if after!=before+addition:
        raise ValueError('VENDOR_BROWSER_ONLY_SCOPED_DISABLED_READABILITY_ALLOWED')


def admitted(repo,here,product):
    cfg=json.loads((here/'CONFIG.json').read_bytes());source=json.loads((here/'SOURCE.json').read_bytes())
    pin=cfg.get('accepted_backend11')
    if pin is None:raise ValueError('VENDOR_MONEY_BROWSER_CLOSED_COMPLETE_BACKEND11_REQUIRED')
    for path,digest in source['files'].items():assert sha256((repo/path).read_bytes()).hexdigest()==digest,path
    first=cfg['first_browser_failure']
    originals={k:gzip.decompress((here/first[k]['path']).read_bytes())for k in ('original','package')}
    for k,raw in originals.items():assert len(raw)==first[k]['bytes']and sha256(raw).hexdigest()==first[k]['sha256']
    failed=json.loads(originals['original']);failed_package=json.loads(originals['package'])
    assert failed['qualification_commit']==first['head']and failed['status']=='INCOMPLETE'
    assert failed['committed']['VENDOR_MONEY_BROWSER2']['browser']['counts']=={'INCOMPLETE':2}
    assert all('UNMEASURED_FINANCE_BACKGROUND_IMAGE'in v['error']for v in failed['committed']['VENDOR_MONEY_BROWSER2']['browser']['cases'].values())
    assert failed['baseline_full22_all_rows_all_sequences_equal']is True and failed['cp6_restored']is True
    assert failed_package['gate']==dict(installed=True,primary_unchanged=True,backup_restore_drill=True,security_advisors=True,writer_runtime=False)
    layer_first=cfg['layer_list_first_failure']
    layer_raw={k:gzip.decompress((here/layer_first[k]['path']).read_bytes())for k in ('original','package')}
    for k,raw in layer_raw.items():assert len(raw)==layer_first[k]['bytes']and sha256(raw).hexdigest()==layer_first[k]['sha256']
    layer_failed=json.loads(layer_raw['original']);layer_package=json.loads(layer_raw['package'])
    assert layer_failed['qualification_commit']==layer_first['head']and layer_failed['status']=='INCOMPLETE'
    layer_browser=layer_failed['committed']['VENDOR_MONEY_BROWSER2']['browser']
    assert layer_browser['counts']=={'INCOMPLETE':2}
    assert all('UNMEASURED_FINANCE_TEXT_SURFACE'in v['error']and 'normal, normal'in v['error']for v in layer_browser['cases'].values())
    assert layer_failed['baseline_full22_all_rows_all_sequences_equal']is True and layer_failed['cp6_restored']is True
    assert layer_package['gate']==dict(installed=True,primary_unchanged=True,backup_restore_drill=True,security_advisors=True,writer_runtime=False)
    changed=subprocess.check_output(['git','-C',str(repo),'diff','--name-only',cfg['base_head'],'HEAD'],text=True).splitlines()
    assert set(changed)<=set(source['allowed_changes']),'UNDECLARED_VENDOR_BROWSER_CHANGE'
    assert not subprocess.check_output(['git','-C',str(repo),'status','--porcelain','--untracked-files=no']).strip()
    verifier=cfg['frozen_intake_verifier']
    raw_verifier=subprocess.check_output(['git','-C',str(repo),'show',verifier['head']+':'+verifier['path']])
    assert sha256(raw_verifier).hexdigest()==verifier['sha256']
    root=Path(os.environ['CP7_VENDOR_BACKEND11_ORIGINALS'])
    raw=(root/pin['original']['name']).read_bytes();package=(root/pin['package']['name']).read_bytes()
    current=product.sources()
    entry=cfg['current_installation_entrypoint']
    assert entry==dict(module='cp7_vendor_receivable.composition',path='scripts/cp7_vendor_receivable/composition.py',
        install='install',verify='verify',rollback_preuse='rollback_preuse')
    assert all(callable(getattr(product,name,None))for name in ('install','verify','rollback_preuse'))
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
        if path=='src/initial-import.css':
            assert sha256(old).hexdigest()==cfg['style_successor']['before_sha256']
            client_style(old.decode(),(repo/path).read_text())
            continue
        assert sha256(old).hexdigest()==client_sources[path],path
        if path==label_path:client_label(old.decode(),(repo/path).read_text())
        else:assert(repo/path).read_bytes()==old,path
    return dict(status='EXACT_BACKEND11_LABELS_AND_SCOPED_READABILITY_ADMITTED',prerequisite=prerequisite,
        qualification=source,client_sources={p:sha256((repo/p).read_bytes()).hexdigest()for p in cfg['client_files']},
        current_installation=current,current_installation_entrypoint=entry,parent_backend_sha256=parent_digest,
        actual_backend_cases_repeated=0,planned_browser_cases=2,B_combined_browser_repeated=False,
        production_go=False,independent_acceptance=False)
