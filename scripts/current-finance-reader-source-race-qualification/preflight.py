"""Local preparation only: exact instrumentation and negative input controls."""
from pathlib import Path
from hashlib import sha256
import ast,json,subprocess,sys,tempfile
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
import clone_patch

def main():
    assert not(HERE/'SOURCE.json').exists(),'PREPARED_PREFLIGHT_ONLY'
    for p in HERE.glob('*.py'):ast.parse(p.read_text())
    raw=(ROOT/'scripts/cp7_finance_capture/finance_capture.sql').read_text()
    a=raw.index('create function cp7_finance_capture.report_unit(')
    b=raw.index('end $$;',a)+len('end $$;')
    original=raw[a:b].replace('create function','CREATE OR REPLACE FUNCTION',1)
    key='CP7:FINANCE_READER_RACE:local-control'
    result=clone_patch.held_report_definition(original,key)
    added=" perform pg_advisory_xact_lock(hashtextextended('"+key+"',0));\n"
    assert result.replace(added,'',1)==original
    for changed in(original.replace('begin\n select','begin\n  select',1),original+original):
        try:clone_patch.held_report_definition(changed,key)
        except AssertionError:pass
        else:raise AssertionError('HOLD_ACCEPTED_CHANGED_SOURCE')
    try:clone_patch.held_report_definition(original,"CP7:FINANCE_READER_RACE:bad'key")
    except AssertionError:pass
    else:raise AssertionError('HOLD_ACCEPTED_UNSAFE_KEY')
    with tempfile.TemporaryDirectory(prefix='finance_source_race_preflight_')as folder:
        path=Path(folder)/'instrumented.sql';path.write_text(result)
        check=subprocess.run([sys.executable,str(ROOT/'scripts/cp7_plpgsql_clash_check.py'),str(path)],capture_output=True,text=True,check=True)
    assert check.stdout.strip()=='functions 1',check.stdout
    receipt=dict(status='PREPARED_ONLY',source_transform_round_trip=True,negative_drift_and_key_guards=3,
        PLpgsql_alias_check=check.stdout.strip(),instrumented_SQL_sha256=sha256(result.encode()).hexdigest(),
        database_compilation='NOT_AVAILABLE_LOCALLY',runtime_qualified=False,production_go=False)
    (HERE/'LOCAL_PREFLIGHT.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt))

if __name__=='__main__':main()
