"""One unchanged child/header race with exact Native nine-piece payroll linkage."""
from datetime import timedelta
from pathlib import Path
from hashlib import sha256
from urllib.parse import urlparse
import ast,importlib.util,json,sys,traceback
import cp7_retained_cp6_fixture as fixture
import cp6_v2620af_concurrency as sessions

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
CURRENT=False
AI=('HEADER_CHILD_ABORT',)
LEGACY_IDS=AI
IDS=('CURRENT_WORK_PAYROLL_CHILD9_HEADER_CHILD_ABORT',)


def load(name,path):
    assert name not in sys.modules,('DUPLICATE_QUALIFIER_MODULE',name)
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec);sys.modules[name]=mod;spec.loader.exec_module(mod)
    return mod


prerequisites=load('current_work_payroll_child9_prerequisites',HERE/'prerequisites.py')
ai=load('current_work_payroll_child9_ai',HERE/'ai_oracle.py')


def verify_transforms():
    rows=json.loads((HERE/'TRANSFORMS.json').read_bytes())['functions'];verified=[]
    for row in rows:
        source=(REPO/row['original']).read_text();lines=source.splitlines(keepends=True)
        node=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef)and n.name==row['function'])
        old=''.join(lines[node.lineno-1:node.end_lineno]);new=old
        assert sha256(old.encode()).hexdigest()==row['original_function_sha256']
        for left,right in row['replacements']:
            assert new.count(left)==1;new=new.replace(left,right)
        assert sha256(new.encode()).hexdigest()==row['successor_function_sha256']
        expected='import current_work_payroll_child9_prerequisites as prerequisites\n'+''.join(lines[:node.lineno-1])+new+''.join(lines[node.end_lineno:])
        assert(REPO/row['successor']).read_text()==expected,'UNDECLARED_ORACLE_CHANGE'
        verified.append(dict(function=row['function'],original_sha256=row['original_function_sha256'],
            successor_sha256=row['successor_function_sha256'],exact_declared_transform=True))
    assert len(IDS)==len(set(IDS))==1 and len(verified)==1
    return verified


def races(tools,today):
    url=urlparse(tools.admin)
    assert url.hostname in('127.0.0.1','localhost')and url.path=='/cp6_auditor_race'
    plans=[(n,lambda m=n:ai.run_case(m),'PASS')for n in AI]
    result=[]
    for name,(legacy,operation,expected)in zip(IDS,plans):
        def run(n=name,old=legacy,fn=operation,want=expected):
            preparation={};previous=sessions.CLONE;sessions.CLONE=tools.admin
            try:
                with tools.connect()as conn,conn.cursor()as cur:
                    sessions.actors.admin(cur)
                    day=sessions.base.one(cur,"select(statement_timestamp()at time zone'Asia/Jakarta')::date")-timedelta(days=3)
                    assert day==today-timedelta(days=3),'RETAINED_RACE_BUSINESS_DAY_CHANGED'
                    fixture.prepare(cur,today,current=CURRENT,closed_through=day-timedelta(days=5),evidence=preparation)
                raw=fn();assert raw['status']==want and raw['payroll_linkage']['known_positive_source_rate_preserved'],raw
                return dict(status='PASS',case_id=n,represented_legacy_id=old,original_result=raw,
                    exact_original_race_lock_and_work_oracles=True,explicit_new_Native_payroll_before_final_READY=True,
                    seed_prerequisite_preparation=preparation,legacy_result_relabelled=False)
            except Exception as error:
                return dict(status='INCOMPLETE',case_id=n,represented_legacy_id=old,error=str(error),
                    traceback=traceback.format_exc(),seed_prerequisite_preparation=preparation)
            finally:sessions.CLONE=previous
        result.append((name,run))
    assert tuple(n for n,_ in result)==IDS
    return result
