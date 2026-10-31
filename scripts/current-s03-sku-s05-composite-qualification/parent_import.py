"""Admit real parent imports despite inherited sys.path side effects."""
from pathlib import Path
import importlib,importlib.util,json,sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]

def parent_modules(backend_root):
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
            source_DB_guard=guard,whole_product_sources_evaluated=False,actual_Native_cases=0)))
    finally:sys.path[:]=previous_path;sys.argv=previous_argv
