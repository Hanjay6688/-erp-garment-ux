"""Source and read-only observer controls; no database or factory qualification claim."""
from pathlib import Path
from copy import deepcopy
import ast,importlib.util,json,shutil,subprocess,sys,tempfile,yaml
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1];sys.path.insert(0,str(REPO/'scripts'))
def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def run():
    load('factory_observe_graph',HERE/'probe.py')
    guard=load('factory_observe_guard',HERE/'source_guard.py');bound=guard.source_binding()
    rejected=[]
    def reject(name,operation):
        try:operation()
        except AssertionError:rejected.append(name)
        else:raise AssertionError('CONTROL_ACCEPTED:'+name)
    with tempfile.TemporaryDirectory(prefix='factory-observe-source-')as temp:
        target=Path(temp)
        for name in('CONFIG.json','runner.py','fixture.py','probe.py','diagnostics.py'):shutil.copyfile(HERE/name,target/name)
        saved=guard.HERE;guard.HERE=target
        try:
            for name,file,old,new in[
                ('relaxed_deadline','runner.py','started+300','started+3000'),
                ('relaxed_metrics','runner.py','len(wanted)==24','len(wanted)>=1'),
                ('relaxed_restore','probe.py','assert drill.data_hashes(database.SOURCE)==pre_data','assert True'),
                ('wrong_fixture','fixture.py','historical_sales_relabelled=False','historical_sales_relabelled=True'),
                ('writeable_observer','diagnostics.py','set local transaction read only','set local transaction read write'),
                ('missing_column_check','diagnostics.py',"assert set(captures[0])==set(columns['cp7_finance_capture.captures'])",'assert True'),
                ('observer_removed','runner.py',guard.CALL_ADDITION,'')]:
                original=(HERE/file).read_text();assert old in original,(name,old)
                (target/file).write_text(original.replace(old,new,1));reject(name,guard.source_binding);(target/file).write_text(original)
            assert guard.source_binding()==bound
        finally:guard.HERE=saved
    observer=load('factory_observe_readonly',HERE/'diagnostics.py')
    original_connect=observer.psycopg.connect;events=[]
    jobs=[dict(request_id=k,state='FAILED',failure_code='LOCAL_EXAMPLE',captured_at='2026-10-26T07:00:00.000001+07:00')for k in('request-A','request-B')]
    caps=[dict(id='capture-C',state='FAILED',failure_code='LOCAL_EXAMPLE',report=None)]
    settings=dict(readonly='on',missing_job=False,missing_column=False)
    class Cursor:
        def __enter__(self):return self
        def __exit__(self,*args):return False
        def execute(self,sql,params=None):
            events.append((sql,params));self.rows=[]
            assert sql.startswith(('select ','show ','set local ')),sql
            if sql.startswith('set local '):assert sql in('set local transaction read only',"set local statement_timeout='8s'")
            elif sql=='select current_database()':self.rows=[('cp6_rollback',)]
            elif sql=='show transaction_read_only':self.rows=[(settings['readonly'],)]
            elif sql.startswith('select to_jsonb(j)'):self.rows=[(deepcopy(row),)for row in(jobs[:1]if settings['missing_job']else jobs)]
            elif sql.startswith('select to_jsonb(c)'):self.rows=[(deepcopy(row),)for row in caps]
            elif sql.startswith('select a.attname'):
                keys=list(jobs[0]if params[1]=='jobs'else caps[0])
                if settings['missing_column']:keys.append('not_returned')
                self.rows=[(key,)for key in keys]
            else:raise AssertionError('UNEXPECTED_QUERY:'+sql)
            return self
        def fetchone(self):return self.rows[0]
        def fetchall(self):return self.rows
    class Connection:
        def __enter__(self):return self
        def __exit__(self,*args):return False
        def cursor(self):return Cursor()
    observer.psycopg.connect=lambda *args,**kwargs:Connection()
    try:
        url='postgresql://localhost:54322/cp6_rollback'
        out=observer.capture(url,['request-A','request-B'],'capture-C')
        assert out['job_rows']==jobs and out['finance_capture_rows']==caps and out['all_stored_columns_preserved']
        assert events[0][0]=='set local transaction read only'and events[1][0]=="set local statement_timeout='8s'"
        for name,url2,requests in [('foreign_host','postgresql://example.invalid:54322/cp6_rollback',['request-A','request-B']),('wrong_database','postgresql://localhost:54322/postgres',['request-A','request-B']),('duplicate_request',url,['request-A','request-A'])]:
            before=len(events);reject(name,lambda:observer.capture(url2,requests,'capture-C'));assert len(events)==before
        for name,key,value in [('readonly_off','readonly','off'),('missing_job','missing_job',True),('missing_column','missing_column',True)]:
            old=settings[key];settings[key]=value;reject(name,lambda:observer.capture(url,['request-A','request-B'],'capture-C'));settings[key]=old
        assert observer.capture(url,['request-A','request-B'],'capture-C')==out
    finally:observer.psycopg.connect=original_connect
    workflow=yaml.safe_load((REPO/'.github/workflows/cp7-current-frozen-finance-factory-observe.yml').read_bytes());steps=0
    for step in workflow['jobs']['p21']['steps']:
        if 'run'in step:
            p=subprocess.run(['bash','-n'],input=step['run'],text=True,capture_output=True);assert p.returncode==0,(step.get('name'),p.stderr);steps+=1
    assert workflow['on']['push']['branches']==['astra-a/d17-14-frozen-finance-factory-observe-20261026']
    for p in HERE.glob('*.py'):ast.parse(p.read_bytes())
    return dict(status='PASS_LOCAL_ONLY',retained_source=bound,negative_controls=rejected,
        observer_preserves_exact_rows=True,read_only_before_queries=True,all_hooks_restored=True,
        source_negative_controls=7,observer_negative_controls=6,bash_steps=steps,
        database_executed=False,runtime_qualified=False,production_go=False)
if __name__=='__main__':
    assert not sys.argv[1:]
    print(json.dumps(run(),indent=2))
