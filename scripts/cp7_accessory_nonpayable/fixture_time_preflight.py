"""New fixture/API/read-only-advisor source checks; never ERP execution."""
from hashlib import sha256
from pathlib import Path
import argparse,ast,inspect,json,re,sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
ACTUAL25=(14755737,'80856b7ec2cebf08318a21617091b73c6744161b72bb3be98bcb9ecd2b8109eb')


def require(value,message):
    if not value:raise ValueError(message)


def signature(node):
    args=node.args;pos=args.posonlyargs+args.args;offset=len(pos)-len(args.defaults);params=[]
    for i,arg in enumerate(pos):
        params.append(inspect.Parameter(arg.arg,inspect.Parameter.POSITIONAL_ONLY if i<len(args.posonlyargs)
            else inspect.Parameter.POSITIONAL_OR_KEYWORD,default=inspect.Parameter.empty if i<offset else None))
    if args.vararg:params.append(inspect.Parameter(args.vararg.arg,inspect.Parameter.VAR_POSITIONAL))
    for arg,default in zip(args.kwonlyargs,args.kw_defaults):
        params.append(inspect.Parameter(arg.arg,inspect.Parameter.KEYWORD_ONLY,
            default=inspect.Parameter.empty if default is None else None))
    if args.kwarg:params.append(inspect.Parameter(args.kwarg.arg,inspect.Parameter.VAR_KEYWORD))
    return inspect.Signature(params)


def dotted(node):
    if isinstance(node,ast.Name):return node.id
    if isinstance(node,ast.Attribute):return dotted(node.value)+'.'+node.attr
    return ''


def check(raw,parser_runtime):
    require((len(raw),sha256(raw).hexdigest())==ACTUAL25,'AFUI_TIME_PREFLIGHT_EXACT_ACTUAL_NATIVE25_REQUIRED')
    metadata=json.loads(raw);functions=dict(metadata['functions'])
    guard=next(row[0]for name,row in functions.items()if name.startswith('erp.bf_save_groups_v1('))
    require("at_time<statement_timestamp()-interval '5 minutes'"in guard,'AFUI_TIME_PREFLIGHT_ACTUAL_BF_HISTORY_GUARD')
    names=('native_fixture.py','native_cases.py','native_inverse_cases.py','native_sales_cases.py',
        'advisor_review.py','qualification.py','qualification_component.py','final_gate.py','fixture_time_preflight.py')
    trees={name:ast.parse((HERE/name).read_bytes())for name in names}
    for name,tree in trees.items():compile(tree,str(HERE/name),'exec')
    fixture=trees['native_fixture.py'];methods={n.name:signature(n)for n in fixture.body if isinstance(n,ast.FunctionDef)}
    master_tree=ast.parse((ROOT/'scripts/cp6_bf_probe.py').read_bytes())
    master={n.name:signature(n)for n in master_tree.body if isinstance(n,ast.FunctionDef)and n.name in('group','save')}
    calls=[];queries=[]
    for name,tree in trees.items():
        for node in ast.walk(tree):
            if not isinstance(node,ast.Call):continue
            function=dotted(node.func);target=None
            if function.startswith(('fixture.','native_fixture.'))and function.split('.')[-1]in methods:
                target=methods[function.split('.')[-1]]
            elif name=='native_fixture.py'and function in('actual_time','master_recipe'):target=methods[function]
            elif function.startswith('modules.bom.master.')and function.split('.')[-1]in master:
                target=master[function.split('.')[-1]]
            if target is not None:
                require(not any(k.arg is None for k in node.keywords),'AFUI_TIME_PREFLIGHT_EXPLICIT_CALL_SIGNATURE')
                target.bind(*[None for _ in node.args],**{k.arg:None for k in node.keywords})
                calls.append(dict(file=name,line=node.lineno,function=function))
            if isinstance(node.func,ast.Attribute)and node.func.attr=='execute'and node.args and isinstance(node.args[0],ast.Constant)and isinstance(node.args[0].value,str):
                if(name=='advisor_review.py'or any(x in node.args[0].value for x in('statement_timestamp()','bf_sku_members_v1'))
                    or name=='qualification_component.py'and node.args[0].value in('set constraints all immediate','set constraints all deferred')):
                    queries.append(dict(file=name,line=node.lineno,sql=node.args[0].value))
    current=next(n for n in fixture.body if isinstance(n,ast.FunctionDef)and n.name=='actual_time')
    current_source=ast.get_source_segment((HERE/'native_fixture.py').read_text(),current)
    require('statement_timestamp()'in current_source and "Asia/Jakarta"in current_source and 'day!=expected_day'in current_source,
        'AFUI_TIME_PREFLIGHT_REAL_DATABASE_CLOCK_AND_WIB_GUARD_REQUIRED')
    for tree in trees.values():
        require(not any(isinstance(n,ast.Call)and dotted(n.func)=='modules.bom.recipe'for n in ast.walk(tree)),
            'AFUI_TIME_PREFLIGHT_NO_HISTORICAL_MIDNIGHT_RECIPE_ROUTE')
    sys.path.insert(0,str(parser_runtime));import pglast
    for row in queries:
        positions=iter(range(1,row['sql'].count('%s')+1))
        pglast.parse_sql(re.sub('%s',lambda _: '$'+str(next(positions)),row['sql']))
    require(len(master)==2 and any(r['function']=='modules.bom.master.save'for r in calls),
        'AFUI_TIME_PREFLIGHT_REAL_SHARED_MASTER_API_REQUIRED')
    return dict(status='NEW_AFUI_GENUINE_TIME_FIXTURE_AND_EXACT_PRIVATE_ADVISOR_SOURCE_PREFLIGHT_PASS_NOT_BUSINESS',
        actual_native_original=dict(bytes=ACTUAL25[0],sha256=ACTUAL25[1]),actual_BF_history_definition_sha256=sha256(guard.encode()).hexdigest(),
        changed_source_files={n:dict(bytes=len((HERE/n).read_bytes()),sha256=sha256((HERE/n).read_bytes()).hexdigest())for n in names},
        actual_helper_signatures_checked=calls,new_SQL_statements_parsed=queries,parser=pglast.__version__,
        Native_BF_HISTORY_guard_unchanged=True,genuine_SQL_clock_source_required=True,
        Native_case_ids_and_oracles_unchanged=True,remaining_cases_blocked_after_first_failure_not_marked_PASS=True,
        private_advisor_scope=['cp7_accessory_nonpayable.'+n for n in('category_versions_v1','date_requests_v1','good_bases_v1')],
        actual_SQL_executed=0,actual_Native_cases=0,actual_Auth_HTTP_cases=0,actual_browser_cases=0,
        old_Native_or_model_or_financial_suites_rerun=False,production_go=False,independent_acceptance=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--actual25',type=Path,required=True)
    parser.add_argument('--parser-runtime',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    value=check(args.actual25.read_bytes(),args.parser_runtime)
    args.out.write_text(json.dumps(value,indent=2)+'\n')
    print(json.dumps(dict(status=value['status'],helper_calls=len(value['actual_helper_signatures_checked']),
        SQL_parsed=len(value['new_SQL_statements_parsed']),actual_SQL_executed=0)))
