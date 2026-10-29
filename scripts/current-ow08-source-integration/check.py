"""Successor of the frozen vendor checker, admitting exactly two CSS appends."""
from pathlib import Path
from hashlib import sha256
import gzip, importlib.util, json, subprocess, sys
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE))
from admit import admit
from paint_binding import verify as verify_paint

def git(*args):
    return subprocess.check_output(['git','-C',str(ROOT),*args])

def check():
    cfg=json.loads((HERE/'CONFIG.json').read_bytes());pin=cfg['qualified_source6']
    if pin is None:raise ValueError('OW08_INTEGRATION_CLOSED_ACTUAL_SOURCE6_REQUIRED')
    assert pin['head']==cfg['component_head'] and pin['tree']==cfg['component_tree']
    assert not git('status','--porcelain','--untracked-files=no').strip()
    changed=git('diff','--name-only',cfg['base_head'],'HEAD','--','src','supabase','scripts','package.json','package-lock.json').decode().splitlines()
    assert all(p in {r['path']for r in cfg['scoped_paint_overlays']} or p.startswith('scripts/current-ow08-source-integration/')for p in changed),'UNDECLARED_OW08_INTEGRATION_CHANGE'
    product_changes=[p for p in changed if not p.startswith('scripts/current-ow08-source-integration/')]
    originals=verify_paint(cfg['scoped_paint_overlays'],product_changes,
        lambda p:git('show',cfg['base_head']+':'+p),lambda p:(ROOT/p).read_bytes())
    for p in originals:assert (ROOT/p).read_bytes()==git('show',pin['head']+':'+p),p
    spec=importlib.util.spec_from_file_location('retained_exact_vendor_intake',ROOT/'scripts/current-vendor-integration-source/check.py')
    vendor=importlib.util.module_from_spec(spec);spec.loader.exec_module(vendor)
    money_cfg,changed_B=vendor.verify_files(overrides=originals)
    runtime={p:sha256((ROOT/p).read_bytes()).hexdigest()for p in vendor.RUNTIME}
    def raw(p,k):return gzip.decompress((ROOT/p[k]['path']).read_bytes())
    native_pin=money_cfg['qualified_combined11'];money_pin=money_cfg['qualified_money_browser2']
    retained_backend=vendor.admit(native_pin,raw(native_pin,'original'),raw(native_pin,'package'),runtime,money_cfg['parent_backend_sha256'])
    retained_money=vendor.admit_browser(money_pin,raw(money_pin,'original'),raw(money_pin,'package'),native_pin['head'],money_cfg['imports'],runtime,money_cfg['current_installation_entrypoint'])
    declaration_raw=(HERE/'QUALIFIED_SOURCE_DECLARATION.json').read_bytes()
    assert declaration_raw==git('show',pin['head']+':scripts/current-ow08-source-browser/SOURCE.json')
    declaration=json.loads(declaration_raw)
    for path,digest in declaration['files'].items():
        assert sha256(git('show',pin['head']+':'+path)).hexdigest()==digest,path
    new=admit(pin,raw(pin,'original'),raw(pin,'package'),declaration,runtime,
        money_cfg['parent_backend_sha256'],native_pin['head'],money_pin['head'],cfg['scoped_paint_overlays'],money_cfg['current_installation_entrypoint'])
    return dict(status='PASS_QUALIFIED_OW08_SOURCE6_SELECTIVE_INTEGRATION',head=git('rev-parse','HEAD').decode().strip(),
        product_files=product_changes,retained_backend=retained_backend,retained_money_browser=retained_money,qualified_source6=new,
        original_B_graph_files=79,declared_changed_B_graph_files=changed_B,B_driver_unchanged=True,
        historical_manifests_rewritten=False,retained_money_scope=cfg['retained_money_client_scope'],formal='5/16',production_go=False,independent_acceptance=False)

if __name__=='__main__':
    assert not sys.argv[1:]
    print(json.dumps(check()))
