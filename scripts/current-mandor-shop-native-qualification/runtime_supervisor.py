"""Exact retained process supervision, routed to this closed Mandor caller.

The ten earlier process controls and 360/330/20/10 minute budgets retain
their validity. This preparation runs none of those controls or ERP cases.
"""
from hashlib import sha256
from pathlib import Path
from types import ModuleType
import subprocess,sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
ORIGINAL='scripts/current-de-free-date-preparation/runtime_supervisor.py'
ORIGINAL_BASE='0da4d79a4f7201ef053d6de1eb155d990b4bfa4d'
PIN=(8914,'af04570b8aecef5d7b0c9b1dfd5ab04942aec32fee8c2fdb908663108c97e149')
CHANGES=(('FREE_DATE_RUNTIME_SUPERVISION.json','MANDOR_RUNTIME_SUPERVISION.json'),
    ("os.environ.get('FREE_DATE_CONFIRM')","os.environ.get('MANDOR_NATIVE_CONFIRM')"),
    ("os.environ['FREE_DATE_JOB_START_MONOTONIC']","os.environ['MANDOR_NATIVE_JOB_START_MONOTONIC']"),
    ("str(HERE/'probe.py')","str(HERE/'qualification.py')"))


def derive(raw):
    if(len(raw),sha256(raw).hexdigest())!=PIN:raise ValueError('MANDOR_SUPERVISOR_EXACT_ORIGINAL_BYTES')
    if raw!=subprocess.check_output(['git','-C',str(ROOT),'show',ORIGINAL_BASE+':'+ORIGINAL]):
        raise ValueError('MANDOR_SUPERVISOR_EXACT_ORIGINAL_PUBLIC_BLOB')
    text=raw.decode()
    for before,after in CHANGES:
        if text.count(before)!=1 or after in text:raise ValueError('MANDOR_SUPERVISOR_ONE_EXACT_ROUTE_REQUIRED')
        text=text.replace(before,after,1)
    restored=text
    for before,after in reversed(CHANGES):
        if restored.count(after)!=1:raise ValueError('MANDOR_SUPERVISOR_EXACT_INVERSE_SITE_REQUIRED')
        restored=restored.replace(after,before,1)
    if restored.encode()!=raw:raise ValueError('MANDOR_SUPERVISOR_COMPLETE_ORIGINAL_NOT_RECOVERED')
    compile(text,'mandor_exact_original_process_supervisor','exec')
    return text,dict(original_bytes=PIN[0],original_sha256=PIN[1],derived_sha256=sha256(text.encode()).hexdigest(),
        exact_reversible_routes=4,original_bytes_recovered=True,prior_ten_process_controls_reused=True,
        original_360_330_20_10_minute_budgets_unchanged=True,actual_ERP_cases=0,production_go=False,independent_acceptance=False)


def main():
    if sys.argv[1:]not in([],['--allow-database-stop']):raise ValueError('MANDOR_FIXED_SUPERVISED_RUNTIME_ONLY')
    if not sys.argv[1:]:
        import qualification
        qualification.actual_parent()  # Before worker construction or subreaper.
    text,_=derive((ROOT/ORIGINAL).read_bytes())
    module=ModuleType('mandor_exact_original_process_supervision');module.__file__=str(HERE/'runtime_supervisor.py')
    exec(compile(text,module.__file__,'exec'),module.__dict__)
    return module.main()


if __name__=='__main__':sys.exit(main())
