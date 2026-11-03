"""Exact original 360/330/20/10 process supervision for the new owning entry."""
from hashlib import sha256
from pathlib import Path
from types import ModuleType
import importlib.util,sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
CHANGES=(
    ('MANDOR_RUNTIME_SUPERVISION.json','SKU_CURRENT_PARENT_RUNTIME_SUPERVISION.json'),
    ("os.environ.get('MANDOR_NATIVE_CONFIRM')","os.environ.get('SKU_CURRENT_PARENT_CONFIRM')"),
    ("os.environ['MANDOR_NATIVE_JOB_START_MONOTONIC']","os.environ['SKU_CURRENT_PARENT_JOB_START_MONOTONIC']"),
    ("str(HERE/'qualification.py')","str(HERE/'sku_current_parent_runtime.py')"),
)


def derive():
    path=ROOT/'scripts/current-mandor-shop-native-qualification/runtime_supervisor.py'
    spec=importlib.util.spec_from_file_location('sku_original_Mandor_supervisor_routes',path)
    original=importlib.util.module_from_spec(spec);spec.loader.exec_module(original)
    text,parent=original.derive((ROOT/original.ORIGINAL).read_bytes());before=text
    for old,new in CHANGES:
        if text.count(old)!=1 or new in text:raise ValueError('SKU_COMPOSITE_EXACT_SUPERVISOR_ROUTE')
        text=text.replace(old,new,1)
    recovered=text
    for old,new in reversed(CHANGES):recovered=recovered.replace(new,old,1)
    if recovered!=before:raise ValueError('SKU_COMPOSITE_COMPLETE_SUPERVISOR_NOT_RECOVERED')
    compile(text,'sku_current_parent_original_supervision','exec')
    return text,dict(parent_derivation=parent,original_sha256=sha256(before.encode()).hexdigest(),
        derived_sha256=sha256(text.encode()).hexdigest(),exact_routes=4,complete_original_recovered=True,
        real_360_330_20_10_budgets_unchanged=True,actual_composite_cases=0,production_go=False)


def main():
    if sys.argv[1:]not in([],['--allow-database-stop']):raise ValueError('SKU_COMPOSITE_FIXED_SUPERVISED_RUNTIME_ONLY')
    if not sys.argv[1:]:
        import sku_current_parent_runtime as runtime
        runtime.actual_inputs()
    text,_=derive();module=ModuleType('sku_current_parent_exact_process_supervision')
    module.__file__=str(HERE/'sku_current_parent_supervisor.py')
    exec(compile(text,module.__file__,'exec'),module.__dict__);return module.main()


if __name__=='__main__':sys.exit(main())
