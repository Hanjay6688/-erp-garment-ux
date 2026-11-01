"""Four exact routes in the previously controlled process supervisor."""
from hashlib import sha256
from pathlib import Path
from types import ModuleType
import subprocess,sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
ORIGINAL='scripts/current-de-free-date-preparation/runtime_supervisor.py'
ORIGINAL_BASE='0da4d79a4f7201ef053d6de1eb155d990b4bfa4d'
PIN=(8914, 'af04570b8aecef5d7b0c9b1dfd5ab04942aec32fee8c2fdb908663108c97e149')
CHANGES=(('FREE_DATE_RUNTIME_SUPERVISION.json','AFUI_RUNTIME_SUPERVISION.json'),
    ("os.environ.get('FREE_DATE_CONFIRM')","os.environ.get('AFUI_CONFIRM')"),
    ("os.environ['FREE_DATE_JOB_START_MONOTONIC']","os.environ['AFUI_JOB_START_MONOTONIC']"),
    ("str(HERE/'probe.py')","str(HERE/'qualification.py')"))

def derive(raw):
    if PIN is None or (len(raw),sha256(raw).hexdigest())!=PIN:
        raise ValueError('NONPAYABLE_EXACT_ORIGINAL_PROCESS_SUPERVISOR_REQUIRED')
    if raw!=subprocess.check_output(['/usr/bin/git','-C',str(ROOT),'show',ORIGINAL_BASE+':'+ORIGINAL]):
        raise ValueError('NONPAYABLE_SUPERVISOR_ORIGINAL_PUBLIC_BYTES_REQUIRED')
    text=raw.decode()
    for before,after in CHANGES:
        if text.count(before)!=1 or after in text:raise ValueError('NONPAYABLE_ONE_EXACT_SUPERVISOR_ROUTE_REQUIRED')
        text=text.replace(before,after,1)
    restored=text
    for before,after in reversed(CHANGES):restored=restored.replace(after,before,1)
    if restored.encode()!=raw:raise ValueError('NONPAYABLE_ORIGINAL_SUPERVISION_NOT_RECOVERED')
    compile(text,'afui_exact_process_supervision','exec')
    return text,dict(original_bytes=PIN[0],original_sha256=PIN[1],derived_sha256=sha256(text.encode()).hexdigest(),
        exact_reversible_routes=4,process_engine_and_original_360_330_20_10_budgets_unchanged=True,
        original_bytes_recovered=True,prior_10_process_controls_reused=True,actual_ERP_cases=0,
        production_go=False,independent_acceptance=False)

def main():
    if sys.argv[1:]not in([],['--allow-database-stop']):raise ValueError('NONPAYABLE_FIXED_SUPERVISED_RUNTIME_ONLY')
    if not sys.argv[1:]:
        from cp7_accessory_nonpayable import admission
        admission.parent_receipt()  # No worker or subreaper before acceptance.
    text,_=derive((ROOT/ORIGINAL).read_bytes())
    module=ModuleType('afui_exact_original_supervisor');module.__file__=str(HERE/'runtime_supervisor.py')
    exec(compile(text,module.__file__,'exec'),module.__dict__)
    return module.main()

if __name__=='__main__':
    sys.path.insert(0,str(ROOT/'scripts'));sys.exit(main())
