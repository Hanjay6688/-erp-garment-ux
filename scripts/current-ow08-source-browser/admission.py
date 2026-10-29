"""Successor declaration; historical money/browser manifests remain untouched."""
from pathlib import Path
from hashlib import sha256
import importlib.util,json,os,subprocess,tempfile
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from paint_binding import verify as verify_paint

def admitted(repo,here,product):
    cfg=json.loads((here/'CONFIG.json').read_bytes());source=json.loads((here/'SOURCE.json').read_bytes())
    for path,digest in source['files'].items():assert sha256((repo/path).read_bytes()).hexdigest()==digest,path
    def git(*args):return subprocess.check_output(['git','-C',str(repo),*args])
    changed=git('diff','--name-only',cfg['base_head'],'HEAD').decode().splitlines()
    assert set(changed)<=set(source['allowed_changes']),'UNDECLARED_OW08_SOURCE_BROWSER_CHANGE'
    assert not git('status','--porcelain','--untracked-files=no').strip()
    # The tested money source remains frozen. These new journeys add exactly
    # two scoped CSS suffixes, never a handler, formula or permission change.
    changed_product=git('diff','--name-only',cfg['base_head'],'HEAD','--','src','supabase','package.json','package-lock.json').decode().splitlines()
    paint_originals=verify_paint(cfg['scoped_paint_overlays'],changed_product,
        lambda path:git('show',cfg['base_head']+':'+path),lambda path:(repo/path).read_bytes())
    money=cfg['accepted_money_browser2']
    if money is None:raise ValueError('OW08_SOURCE_BROWSER_CLOSED_ACTUAL_MONEY_BROWSER2_REQUIRED')
    assert money['head']==cfg['base_head'],'OW08_OTHER_BROWSER_PRODUCT_SOURCE_REFUSED'
    v=cfg['frozen_intake_verifier'];raw=git('show',v['head']+':'+v['path'])
    assert sha256(raw).hexdigest()==v['sha256']
    current=product.sources();parent=sha256(json.dumps(current['predecessor'],sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
    assert parent==cfg['parent_backend_sha256']
    backend=cfg['accepted_backend11'];backroot=Path(os.environ['CP7_VENDOR_BACKEND11_ORIGINALS'])
    moneyroot=Path(os.environ['CP7_OW08_MONEY_BROWSER_ORIGINALS'])
    with tempfile.TemporaryDirectory(prefix='ow08-frozen-intake-')as directory:
        path=Path(directory)/'check.py';path.write_bytes(raw)
        spec=importlib.util.spec_from_file_location('ow08_frozen_intake',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        native=m.admit(backend,(backroot/backend['original']['name']).read_bytes(),(backroot/backend['package']['name']).read_bytes(),current['files'],parent)
        # Attribute retained money evidence to its exact pre-overlay client.
        # The new CSS is separately hashed and must pass the fresh source6 UI.
        clients=[dict(path=p,sha256=sha256(paint_originals[p]if p in paint_originals else(repo/p).read_bytes()).hexdigest())for p in cfg['client_files']]
        ui=m.admit_browser(money,(moneyroot/money['original']['name']).read_bytes(),(moneyroot/money['package']['name']).read_bytes(),backend['head'],clients,current['files'],cfg['current_installation_entrypoint'])
    assert source['browser_case_ids']==['OW08_KASBON_JOURNAL_SOURCE_DESKTOP','OW08_KASBON_JOURNAL_SOURCE_MOBILE',
        'OW08_UNKNOWN_WASH_SCREEN_PRICE_DESKTOP','OW08_UNKNOWN_WASH_SCREEN_PRICE_MOBILE',
        'OW08_FG_INVERSE_QC_BLOCKERS_DESKTOP','OW08_FG_INVERSE_QC_BLOCKERS_MOBILE']
    return dict(status='EXACT_BACKEND_AND_DECLARED_CSS_SUCCESSOR_ADMITTED_NEW_OW08_SOURCE6',qualification=source,
        prerequisite=native,retained_money_browser=ui,current_installation=current,
        current_installation_entrypoint=cfg['current_installation_entrypoint'],parent_backend_sha256=parent,
        scoped_paint_overlays=cfg['scoped_paint_overlays'],retained_money_client_scope='EXACT_BASE_BEFORE_DECLARED_CSS_APPENDS_NOT_NEW_MONEY_BROWSER_CREDIT',
        planned_browser_cases=6,retained_backend_cases_repeated=0,retained_money_browser_repeated=False,
        B_combined_browser_repeated=False,full_OW08_acceptance=False,production_go=False,independent_acceptance=False)
