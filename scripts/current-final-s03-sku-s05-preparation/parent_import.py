"""Admit real parent imports despite inherited sys.path side effects."""
from pathlib import Path
import importlib,importlib.util,json,sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]

def owning_harness():
    # Select the actual current caller before selecting the frozen financial
    # parent. Its package reports and run identity belong to this checkout.
    sys.path.insert(0,str(ROOT/'scripts'))
    origins={}
    # These are the owning package's entry, report, identity and restore
    # modules. Additional frozen CP6 financial helpers belong to the actual
    # qualified parent and are checked by its complete sources() admission.
    names=('cp6_t3_package_run','cp6_run_identity','cp6_aw_probe','cp6_ax_probe',
        'cp6_g01_fingerprint','cp6_t3_backup_restore_drill','cp6_t3_release_package',
        'cp6_t3_browser','cp6_t3_aligned_install')
    for name in names:
        sys.path.insert(0,str(ROOT/'scripts'))
        module=importlib.import_module(name)
        actual=Path(module.__file__).resolve()
        if actual!=ROOT/'scripts'/(name+'.py'):
            raise ValueError('JOIN_OWNING_CP6_HARNESS_ORIGIN_CHANGED:'+name+':'+str(actual))
        origins[name]=str(actual)
    package=sys.modules['cp6_t3_package_run'];identity=sys.modules['cp6_run_identity']
    if package.AUDITOR!=ROOT or package.OUT!=ROOT/'cp6-proof/t3'or identity.ROOT!=ROOT:
        raise ValueError('JOIN_OWNING_CP6_OUTPUT_AND_IDENTITY_REQUIRED')
    return origins

def parent_modules(backend_root):
    owning_harness()
    backend_root=Path(backend_root);modules=[]
    for name in ('cp7_vendor_receivable','cp7_sku_pair_conversion'):
        # Vendor imports retained readers which prepend their own paths. The
        # qualified parent must be selected again before EACH package import.
        sys.path.insert(0,str(backend_root/'scripts'))
        module=importlib.import_module(name+'.composition')
        expected=backend_root/'scripts'/name/'composition.py';actual=Path(module.__file__).resolve()
        if actual!=expected:
            raise ValueError('JOIN_QUALIFIED_BACKEND_MODULE_ORIGIN_CHANGED:'+name+':'+str(actual)+':EXPECTED:'+str(expected))
        modules.append(module)
    return tuple(modules)

if __name__=='__main__':
    def load(name,path):
        spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
    backend=load('joined_import_control_actual_checkout',HERE/'frozen_parent.py').admitted()
    fence=load('joined_import_control_DB_network_fence',ROOT/'scripts/current-sku-managed-recovery-native27-qualification/source_context.py')
    previous_path=list(sys.path);previous_argv=sys.argv
    try:
        sys.argv=sys.argv[:1]
        with fence.fenced_source_read()as guard:
            modules=parent_modules(Path(backend['path']))
        print(json.dumps(dict(status='ACTUAL_QUALIFIED_PARENT_MODULE_ORIGINS_PASS',
            actual_modules=[str(Path(module.__file__).resolve())for module in modules],
            owning_CP6_harness_origins=owning_harness(),
            source_DB_guard=guard,whole_product_sources_evaluated=False,actual_Native_cases=0)))
    finally:sys.path[:]=previous_path;sys.argv=previous_argv
