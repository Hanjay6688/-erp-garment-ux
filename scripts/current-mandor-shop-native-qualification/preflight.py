"""Check only NEW caller syntax, signatures and exact Native RPC arities.

No old source/model/financial scenario, ERP import, DB, HTTP or browser runs.
The earlier actual full25 original supplies existing RPC identities; new public
facades come from the exact Mandor installation plan. Actual parent adoption
remains closed until its successful original is independently accepted.
"""
from pathlib import Path
from hashlib import sha256
import argparse,ast,importlib.util,inspect,json,re,sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
ACTUAL25=dict(bytes=14755737,sha256='80856b7ec2cebf08318a21617091b73c6744161b72bb3be98bcb9ecd2b8109eb')


def require(value,message):
    if not value:raise ValueError(message)


def signature(node):
    args=node.args;pos=args.posonlyargs+args.args;offset=len(pos)-len(args.defaults);params=[]
    for index,arg in enumerate(pos):
        default=inspect.Parameter.empty if index<offset else None
        params.append(inspect.Parameter(arg.arg,inspect.Parameter.POSITIONAL_ONLY if index<len(args.posonlyargs)else inspect.Parameter.POSITIONAL_OR_KEYWORD,default=default))
    if args.vararg:params.append(inspect.Parameter(args.vararg.arg,inspect.Parameter.VAR_POSITIONAL))
    for arg,default in zip(args.kwonlyargs,args.kw_defaults):
        params.append(inspect.Parameter(arg.arg,inspect.Parameter.KEYWORD_ONLY,default=inspect.Parameter.empty if default is None else None))
    if args.kwarg:params.append(inspect.Parameter(args.kwarg.arg,inspect.Parameter.VAR_KEYWORD))
    return inspect.Signature(params)


def check(raw,parser_path):
    require(dict(bytes=len(raw),sha256=sha256(raw).hexdigest())==ACTUAL25,'MANDOR_PREFLIGHT_EXACT_ACTUAL_NATIVE_ORIGINAL')
    actual=json.loads(raw);require(len(actual)==25,'MANDOR_PREFLIGHT_COMPLETE_25_GROUPS')
    functions=dict(actual['functions'])
    plan=json.loads((ROOT/'scripts/cp7_mandor_shop/INSTALL_PLAN.json').read_bytes())
    allowed={}
    for sig in list(functions)+plan['public_functions']:
        name,arguments=sig.split('(',1)
        if name.startswith('public.'):allowed.setdefault(name,set()).add(0 if arguments==')'else len(arguments[:-1].split(',')))
    trees={name:ast.parse((HERE/name).read_bytes())for name in ['admission.py','native_fixture.py','oracle.py','cases.py','preflight.py',
        'assembly.py','component.py','package_engine.py','qualification.py','runtime_supervisor.py','final_gate.py']}
    klass=next(n for n in trees['native_fixture.py'].body if isinstance(n,ast.ClassDef)and n.name=='Native')
    methods={n.name:signature(n)for n in klass.body if isinstance(n,ast.FunctionDef)}
    assembly=next(n for n in trees['assembly.py'].body if isinstance(n,ast.ClassDef)and n.name=='Assembly')
    assembly_methods={n.name:signature(n)for n in assembly.body if isinstance(n,ast.FunctionDef)}
    mandor_methods={n.name:signature(n)for n in ast.parse((ROOT/'scripts/cp7_mandor_shop/composition.py').read_bytes()).body if isinstance(n,ast.FunctionDef)}
    oracles={n.name:signature(n)for n in trees['oracle.py'].body if isinstance(n,ast.FunctionDef)}
    method_calls=[];oracle_calls=[];rpcs=[];sql=[]
    for filename,tree in trees.items():
        if filename=='preflight.py':continue
        for node in ast.walk(tree):
            if not isinstance(node,ast.Call):continue
            func=node.func
            if isinstance(func,ast.Name)and func.id=='Native':
                methods['__init__'].bind(None,*[None for _ in node.args],**{k.arg:None for k in node.keywords})
                method_calls.append(dict(file=filename,line=node.lineno,name='Native.__init__'))
            if isinstance(func,ast.Attribute)and isinstance(func.value,ast.Name):
                prefix=func.value.id
                selected=assembly_methods if prefix=='product'or prefix=='self'and filename=='assembly.py'else methods
                if prefix in('self','n','native','committed','product')and func.attr in selected:
                    require(not any(isinstance(x,ast.Starred)for x in node.args)and all(k.arg for k in node.keywords),'MANDOR_PREFLIGHT_EXPLICIT_NEW_METHOD_CALL')
                    selected[func.attr].bind(None,*[None for _ in node.args],**{k.arg:None for k in node.keywords})
                    method_calls.append(dict(file=filename,line=node.lineno,name=func.attr))
                    if func.attr=='public':
                        require(len(node.args)==4 and isinstance(node.args[1],ast.Constant)and type(node.args[1].value)is str,'MANDOR_PREFLIGHT_LITERAL_PUBLIC_RPC_QUERY')
                        query=node.args[1].value
                        match=re.fullmatch(r'select (public\.[a-z0-9_]+)\(([^;]*)\)',query)
                        require(match is not None,'MANDOR_PREFLIGHT_SINGLE_PUBLIC_RPC_QUERY')
                        count=len(match[2].split(','))if match[2]else 0
                        require(count in allowed.get(match[1],set()),'MANDOR_PREFLIGHT_ACTUAL_RPC_ARITY:'+match[1])
                        require(isinstance(node.args[2],ast.Tuple)and query.count('%s')==len(node.args[2].elts),'MANDOR_PREFLIGHT_SQL_PARAMETER_TUPLE')
                        rpcs.append(dict(file=filename,line=node.lineno,name=match[1],arity=count,parameters=query.count('%s')))
                elif prefix=='oracle'and func.attr in oracles:
                    oracles[func.attr].bind(*[None for _ in node.args],**{k.arg:None for k in node.keywords})
                    oracle_calls.append(dict(file=filename,line=node.lineno,name=func.attr))
                elif prefix=='mandor'and func.attr in mandor_methods:
                    mandor_methods[func.attr].bind(*[None for _ in node.args],**{k.arg:None for k in node.keywords})
                    method_calls.append(dict(file=filename,line=node.lineno,name='mandor.'+func.attr))
                elif prefix=='assembly'and func.attr=='Assembly':
                    assembly_methods['__init__'].bind(None,*[None for _ in node.args],**{k.arg:None for k in node.keywords})
                    method_calls.append(dict(file=filename,line=node.lineno,name='Assembly.__init__'))
            if isinstance(func,ast.Attribute)and func.attr=='execute'and node.args and isinstance(node.args[0],ast.Constant)and type(node.args[0].value)is str:
                sql.append(node.args[0].value)
    sys.path.insert(0,str(parser_path));import pglast
    for query in sql+[n.args[1].value for tree in trees.values()for n in ast.walk(tree)if isinstance(n,ast.Call)and isinstance(n.func,ast.Attribute)and n.func.attr=='public'and len(n.args)==4 and isinstance(n.args[1],ast.Constant)]:
        position=iter(range(1,query.count('%s')+1));normalized=re.sub('%s',lambda _: '$'+str(next(position)),query)
        pglast.parse_sql(normalized)
    ids=next(ast.literal_eval(n.value)for n in trees['cases.py'].body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='IDS'for t in n.targets))
    require(len(ids)==6 and len(set(ids))==6,'MANDOR_PREFLIGHT_EXACT_SIX_NEW_CASES')
    admission={t.id:ast.literal_eval(n.value)for n in trees['admission.py'].body if isinstance(n,ast.Assign)and isinstance(n.value,ast.Constant)for t in n.targets if isinstance(t,ast.Name)}
    require(admission['PARENT_ROOT_PIN']is None and admission['RUNTIME_ENTRY']is None,'MANDOR_PREFLIGHT_MUST_KEEP_UNACCEPTED_PARENT_CLOSED')
    return dict(status='NEW_MANDOR_NATIVE6_CALLER_SOURCE_PREFLIGHT_PASS_NOT_RUNTIME_OR_BUSINESS',
        new_source_files={name:dict(bytes=len((HERE/name).read_bytes()),sha256=sha256((HERE/name).read_bytes()).hexdigest())for name in trees},
        base_source_head='2135bdde920ea632f98671896cc5f0f8410845e9',actual_original25=ACTUAL25,
        new_method_calls=method_calls,new_oracle_calls=oracle_calls,exact_public_RPC_calls=rpcs,
        fixed_observer_SQL_statements_parsed=len(sql),new_case_ids=list(ids),parser=pglast.__version__,
        accepted_Afui15_parent_root_pin=None,runtime_entry=None,actual_SQL_executed=0,actual_Native_cases=0,
        old_source84_or_model_or_financial_tests_rerun=False,production_go=False,independent_acceptance=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--catalogue',type=Path,required=True);p.add_argument('--parser-runtime',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    value=check(a.catalogue.read_bytes(),a.parser_runtime);a.out.write_text(json.dumps(value,indent=2)+'\n')
    print(json.dumps(dict(status=value['status'],new_method_calls=len(value['new_method_calls']),new_oracle_calls=len(value['new_oracle_calls']),new_RPC_calls=len(value['exact_public_RPC_calls']),actual_SQL_executed=0)))
