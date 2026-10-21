"""Execute the actual probe __main__ admission without installing a database.

Only the package.run dispatcher is replaced in an isolated child process.
Connections refuse, and the supplied writer callback is never invoked. This
is a CLI regression control, not Native execution or a business PASS.
"""
from pathlib import Path
import hashlib,json,subprocess,sys

REPO=Path(__file__).resolve().parents[4]
PROBE=REPO/'scripts/cp7_ow04_probe.py'
CHILD=r'''
import json,runpy,sys
sys.path.insert(0,sys.argv[1]+'/scripts')
import psycopg
def no_connection(*args,**kwargs):raise AssertionError('CLI_ADMISSION_MUST_NOT_CONNECT')
psycopg.connect=no_connection
import cp7_f05_analysis_probe as predecessor
calls=[]
predecessor.package.run=lambda mode:calls.append(mode)
probe=sys.argv[1]+'/scripts/cp7_ow04_probe.py'
sys.argv=[probe]+json.loads(sys.argv[2])
try:
    result=runpy.run_path(probe,run_name='__main__')
except SystemExit as error:
    assert not calls,'REJECTED_CLI_MUST_NOT_DISPATCH'
    print(json.dumps(dict(accepted=False,message=str(error),dispatches=calls)))
else:
    assert calls==['install']
    assert callable(predecessor.package._writer_runtime)
    print(json.dumps(dict(accepted=True,case_count=result['EXPECTED_COUNT'],label=result['LABEL'],dispatches=calls)))
'''


def run():
    rows=[]
    for args,count in (([],32),(['--native-empty'],44),(['--fractional-hpp'],58),(['--signed-source'],63),
                       (['--unknown'],None),(['--signed-source','--fractional-hpp'],None),(['--signed-source','extra'],None)):
        answer=subprocess.run([sys.executable,'-c',CHILD,str(REPO),json.dumps(args)],check=True,capture_output=True,text=True)
        actual=json.loads(answer.stdout)
        assert actual['accepted']is(count is not None),(args,actual)
        if count is not None:assert actual['case_count']==count,(args,actual)
        rows.append(dict(arguments=args,expected_count=count,status='PASS',actual=actual))
    return dict(classification='ACTUAL_MAIN_CLI_DISPATCH_ONLY_NOT_NATIVE_EXECUTION',status='PASS',
        probe_sha256=hashlib.sha256(PROBE.read_bytes()).hexdigest(),control_count=len(rows),
        database_calls=0,writer_runtime_calls=0,native_executed=False,production_go=False,controls=rows)


if __name__=='__main__':print(json.dumps(run(),indent=2))
