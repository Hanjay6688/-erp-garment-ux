"""New copy-race source prerequisites, using the retained exact actual catalog.

No database connection, ERP import, old model suite or financial case runs.
"""
from hashlib import sha256
from pathlib import Path
import argparse,ast,importlib.util,inspect,json,re,sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
ORIGINAL=dict(bytes=14755737,sha256='80856b7ec2cebf08318a21617091b73c6744161b72bb3be98bcb9ecd2b8109eb')


def require(value,message):
    if not value:raise ValueError(message)


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module);return module


def check(raw,parser_path):
    require(dict(bytes=len(raw),sha256=sha256(raw).hexdigest())==ORIGINAL,'MANDOR_ACCESS_EXACT_NATIVE_CATALOGUE')
    catalog=json.loads(raw);functions=dict(catalog['functions'])
    plan=json.loads((ROOT/'scripts/cp7_mandor_shop/INSTALL_PLAN.json').read_bytes())
    require(len(plan['replay_guard_preparation']['routes'])==2,'MANDOR_ACCESS_BOTH_CACHED_PERMISSION_GUARDS_REQUIRED')
    source=HERE/'access_cases.py';tree=ast.parse(source.read_bytes())
    native=load('mandor_access_inert_native_fixture',HERE/'native_fixture.py')
    access=load('mandor_access_inert_cases',source)
    require(len(access.RACE_IDS)==len(set(access.RACE_IDS))==4,'MANDOR_ACCESS_FOUR_DISTINCT_NEW_RACES')
    prepared=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='prepare')
    require(not any(isinstance(n,ast.Call)and isinstance(n.func,ast.Attribute)and n.func.attr=='physical'
        for n in ast.walk(prepared)),'MANDOR_ACCESS_MUST_REUSE_GOOD_WITHOUT_DUPLICATE_GLOBAL_DATE')
    policy=(ROOT/'scripts/cp7_accessory_nonpayable/policy.sql').read_bytes()
    require(b'effective_from date not null unique'in policy and b'NONPAYABLE_EFFECTIVE_DATE_ALREADY_RECORDED'in policy,
        'MANDOR_ACCESS_BIND_ACTUAL_UNIQUE_IMMUTABLE_AFUI_DATE_CONTRACT')
    signatures={}
    for signature in list(functions)+plan['public_functions']:
        name,args=signature.split('(',1)
        if name.startswith('public.'):
            signatures.setdefault(name,set()).add(0 if args==')'else len(args[:-1].split(',')))
    sys.path.insert(0,str(parser_path));import pglast
    from pglast.visitors import Visitor
    calls=[];sql=[];rpcs=[]
    class PublicCalls(Visitor):
        def visit_FuncCall(self,ancestors,node):
            name='.'.join(x.sval for x in node.funcname)
            if name.startswith('public.'):
                count=len(node.args or())
                require(count in signatures.get(name,set()),'MANDOR_ACCESS_EXACT_PUBLIC_RPC_ARITY:'+name)
                rpcs.append(dict(name=name,arity=count))
    for node in ast.walk(tree):
        if not isinstance(node,ast.Call):continue
        func=node.func
        if isinstance(func,ast.Attribute)and isinstance(func.value,ast.Name):
            klass=native.Native if func.value.id=='native'else access.Context if func.value.id in('ctx','self')else None
            if klass is not None and hasattr(klass,func.attr):
                inspect.signature(getattr(klass,func.attr)).bind(None,*[None for _ in node.args],
                    **{k.arg:None for k in node.keywords})
                calls.append(dict(line=node.lineno,owner=klass.__name__,name=func.attr))
        if isinstance(func,ast.Attribute)and func.attr=='execute':
            require(node.args and isinstance(node.args[0],ast.Constant)and type(node.args[0].value)is str,
                'MANDOR_ACCESS_FIXED_SQL_ONLY')
            query=node.args[0].value;count=query.count('%s')
            if count:require(len(node.args)==2 and isinstance(node.args[1],ast.Tuple)and len(node.args[1].elts)==count,
                'MANDOR_ACCESS_EXACT_SQL_PLACEHOLDER_TUPLE')
            positions=iter(range(1,count+1));parsed=pglast.parse_sql(re.sub('%s',lambda _:'$'+str(next(positions)),query))
            PublicCalls()(parsed);sql.append(dict(line=node.lineno,parameters=count))
    # Use the real Native status and audit behavior, not a guessed postcondition.
    recalculate=functions['erp.recalculate_payroll(uuid)'][0]
    require("status='CALCULATED'"in recalculate,'MANDOR_ACCESS_NATIVE_RESERVATION_RECALCULATION_STATUS')
    triggers=dict(catalog['triggers']);audit=functions['erp.audit_row_change()'][0]
    require(triggers['erp.app_users:trg_audit_v262_app_users'][8]=='erp.audit_row_change()'
        and 'insert into erp.audit_logs('in audit,'MANDOR_ACCESS_NATIVE_REVOCATION_AUDIT_REQUIRED')
    require('erp.audit_logs'in access.ALLOCATION_TABLES and'sequence:erp.audit_logs_id_seq'in access.ALLOCATION_TABLES,
        'MANDOR_ACCESS_NATIVE_AUDIT_SEQUENCE_DECLARED')
    # A hostile/wrong target must refuse before the first fixture mutation.
    from types import SimpleNamespace
    ctx=access.Context.__new__(access.Context);ctx.mode='RACE';queries=[]
    class Cursor:
        def __init__(self,host,database,isolation):
            self.connection=SimpleNamespace(info=SimpleNamespace(host=host,port=54322))
            self.database=database;self.isolation=isolation
        def execute(self,query):
            queries.append(query)
            if query=='select current_database()':return SimpleNamespace(fetchone=lambda:(self.database,))
            if query=="select current_setting('transaction_isolation')":return SimpleNamespace(fetchone=lambda:(self.isolation,))
            raise AssertionError('Unreviewed local prerequisite query')
    refused=0
    for host,database,isolation in(('remote.invalid','cp6_auditor_race','read committed'),
            ('127.0.0.1','postgres','read committed'),('127.0.0.1','cp6_auditor_race','repeatable read')):
        try:ctx.local(Cursor(host,database,isolation))
        except ValueError:refused+=1
        else:raise ValueError('MANDOR_ACCESS_UNSAFE_COPY_PREREQUISITE_ADMITTED')
    ctx.local(Cursor('127.0.0.1','cp6_auditor_race','read committed'))
    # Check the owning routes now, rather than discovering them after Native9.
    runtime=load('mandor_access_inert_runtime',HERE/'access_runtime.py')
    package=load('mandor_access_inert_package_engine',HERE/'package_engine.py')
    _,copy_proof=runtime.derive((ROOT/runtime.ORIGINAL).read_bytes())
    _,package_proof=package.derive((ROOT/package.ORIGINAL).read_bytes())
    sources=['access_cases.py','access_runtime.py','access_gate.py','access_preflight.py','http_cases.py','http_gate.py',
        'browser.mjs','browser_observer.py','browser_preflight.py','browser_gate.py']
    for name in sources:
        if name.endswith('.py'):compile((HERE/name).read_bytes(),str(HERE/name),'exec')
    component=ast.parse((HERE/'component.py').read_bytes())
    names=[]
    for node in ast.walk(component):
        if isinstance(node,ast.Call)and isinstance(node.func,ast.Attribute)and isinstance(node.func.value,ast.Name):
            owner=node.func.value.id
            if owner in('access_cases','access_runtime'):
                target=access if owner=='access_cases'else runtime
                inspect.signature(getattr(target,node.func.attr)).bind(*[None for _ in node.args],
                    **{k.arg:None for k in node.keywords})
                names.append((node.lineno,owner+'.'+node.func.attr))
    require([name for _,name in sorted(names)]==['access_cases.prepare','access_runtime.run','access_runtime.run_http','access_runtime.run_browser'],
        'MANDOR_ACCESS_EXACT_COMMITTED_PREPARATION_THEN_OWNING_RUN')
    http=load('mandor_access_inert_HTTP_cases',HERE/'http_cases.py')
    require(len(http.HTTP_IDS)==len(set(http.HTTP_IDS))==2,'MANDOR_HTTP_TWO_UNIQUE_REAL_AUTH_CASES')
    http_tree=ast.parse((HERE/'http_cases.py').read_bytes());http_calls=[]
    # Named PostgREST arguments must match the current source facade itself.
    definitions=pglast.parse_sql((ROOT/'scripts/cp7_mandor_shop/facade.sql').read_text())
    arguments={}
    for statement in definitions:
        node=statement.stmt
        if type(node).__name__=='CreateFunctionStmt':
            name='.'.join(x.sval for x in node.funcname)
            arguments[name.split('.')[-1]]={p.name for p in node.parameters or()}
    for node in ast.walk(http_tree):
        if not isinstance(node,ast.Call)or not isinstance(node.func,ast.Attribute):continue
        if node.func.attr in('rpc','anon_rpc'):
            require(len(node.args)==2 and isinstance(node.args[0],ast.Name)
                and node.args[0].id in('READ','WRITE'),'MANDOR_HTTP_FIXED_CURRENT_RPC_ONLY')
            name=getattr(http,node.args[0].id);body=node.args[1]
            require(isinstance(body,ast.Call)and isinstance(body.func,ast.Name)and body.func.id=='dict'
                and not body.args and {k.arg for k in body.keywords}==arguments[name],
                'MANDOR_HTTP_NAMED_POSTGREST_ARGUMENTS_MATCH_ACTUAL_FACADE')
            http_calls.append(dict(line=node.lineno,name=name,arguments=sorted(arguments[name])))
        elif node.func.attr=='execute':
            require(len(node.args)==2 and isinstance(node.args[0],ast.Constant)
                and isinstance(node.args[1],ast.Tuple),'MANDOR_HTTP_FIXED_FIXTURE_SQL')
            query=node.args[0].value;require(query.count('%s')==len(node.args[1].elts),'MANDOR_HTTP_EXACT_SQL_PARAMETER_TUPLE')
            positions=iter(range(1,query.count('%s')+1))
            pglast.parse_sql(re.sub('%s',lambda _:'$'+str(next(positions)),query))
    final=ast.parse((HERE/'final_gate.py').read_bytes())
    require(sum(isinstance(n,ast.Call)and isinstance(n.func,ast.Attribute)
        and isinstance(n.func.value,ast.Name)and n.func.value.id=='access_gate'and n.func.attr=='gate'
        for n in ast.walk(final))==1,'MANDOR_ACCESS_OWNING_ORIGINAL_GATE_REQUIRED')
    import browser_preflight
    browser=browser_preflight.check()
    return dict(status='MANDOR_ACCESS_FOUR_RACES_SOURCE_PREPARED_NOT_EXECUTED',
        source=dict(bytes=len(source.read_bytes()),sha256=sha256(source.read_bytes()).hexdigest()),
        source_files={name:dict(bytes=len((HERE/name).read_bytes()),sha256=sha256((HERE/name).read_bytes()).hexdigest())for name in sources},
        exact_catalogue=ORIGINAL,case_ids=list(access.RACE_IDS),method_calls=calls,fixed_SQL=sql,public_RPC_calls=rpcs,
        actual_Native_status_source=sha256(recalculate.encode()).hexdigest(),
        actual_Native_audit_source=sha256(audit.encode()).hexdigest(),unsafe_copy_refusals=refused,
        same_GOOD_reuse_without_second_global_date=True,actual_Afui_unique_date_source=sha256(policy).hexdigest(),
        actual_two_session_races=0,actual_Auth_HTTP_cases=0,actual_Native_cases=0,actual_browser_cases=0,
        owning_copy_source_integration_prepared=True,actual_copy_qualification_pending=True,
        HTTP_case_ids=list(http.HTTP_IDS),named_HTTP_RPC_calls=http_calls,actual_HTTP_qualification_pending=True,
        browser_source_prerequisites=browser,
        copy_authority_derivation=copy_proof,whole_package_derivation=package_proof,
        production_go=False,independent_acceptance=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--catalogue',type=Path,required=True)
    parser.add_argument('--parser-runtime',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();result=check(args.catalogue.read_bytes(),args.parser_runtime)
    args.out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status=result['status'],methods=len(result['method_calls']),SQL=len(result['fixed_SQL']),
        RPCs=len(result['public_RPC_calls']),unsafe_copy_refusals=result['unsafe_copy_refusals'],actual_races=0)))
