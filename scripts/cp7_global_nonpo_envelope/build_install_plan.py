"""Offline parser-only plan generator; no database import or execution.

Developer use requires pinned pglast7.20/PostgreSQL17.7 grammar. Runtime uses
the sealed JSON plan and needs no parser. Actual compiled authority still has
to pass Supabase17 capability and the Native final-parent qualification.
"""
from pathlib import Path
from hashlib import sha256
import argparse,json
from . import composition,native_hooks

HERE=Path(__file__).resolve().parent


def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())


def typename(value):
    names=[n['String']['sval']for n in value['names']]
    if names[0]=='pg_catalog':names=names[1:]
    aliases=dict(int8='bigint',int4='integer',int2='smallint',bool='boolean',float8='double precision')
    return '.'.join(aliases.get(n,n)for n in names)+('[]'*len(value.get('arrayBounds',[])))


def build():
    import pglast
    if pglast.__version__!='v7.20':raise ValueError('GLOBAL_INSTALL_PLAN_PINNED_PGLAST720_REQUIRED')
    sources=composition.sql_sources();functions={};tables={};triggers=[];indexes=[];constraints=0;fks=0
    for filename,text in sources.items():
        parsed=json.loads(pglast.parser.parse_sql_json(text))
        if parsed['version']!=170007:raise ValueError('GLOBAL_INSTALL_PLAN_POSTGRES177_GRAMMAR_REQUIRED')
        for item in parsed['stmts']:
            node=item['stmt']
            if'CreateFunctionStmt'in node:
                value=node['CreateFunctionStmt'];name='.'.join(x['String']['sval']for x in value['funcname'])
                args=[x['FunctionParameter']for x in value.get('parameters',[])]
                signature=name+'('+','.join(typename(x['argType'])for x in args if x.get('mode','FUNC_PARAM_IN')not in('FUNC_PARAM_OUT','FUNC_PARAM_TABLE'))+')'
                options=[x['DefElem']for x in value['options']];ordinary={x['defname']:x['arg']for x in options if x['defname']!='set'}
                config=[]
                for option in options:
                    if option['defname']!='set':continue
                    setting=option['arg']['VariableSetStmt'];key=setting['name'];vals=setting['args']
                    if len(vals)!=1 or'sval'not in vals[0]['A_Const']:raise ValueError('GLOBAL_INSTALL_PLAN_EXPLICIT_SINGLE_STRING_GUC_REQUIRED')
                    setting_value=vals[0]['A_Const']['sval']['sval']
                    if key.lower()=='timezone':key='TimeZone'
                    if key=='search_path'and setting_value=='':setting_value='""'
                    config.append(key+'='+setting_value)
                if signature in functions:raise ValueError('GLOBAL_INSTALL_PLAN_DUPLICATE_FUNCTION')
                body=ordinary['as']['List']['items'];assert len(body)==1
                functions[signature]=dict(file=filename,body_sha256=sha256(body[0]['String']['sval'].encode()).hexdigest(),
                    owner='supabase_admin'if name.startswith('cp7_global_catalog_fence.')else'postgres',
                    language=ordinary['language']['String']['sval'],volatility=ordinary['volatility']['String']['sval'][0],
                    security_definer=ordinary.get('security',{'Boolean':{'boolval':False}})['Boolean']['boolval'],
                    returns_set=value['returnType'].get('setof',False),config=config or None)
            if'CreateStmt'in node:
                value=node['CreateStmt'];r=value['relation'];name=r['schemaname']+'.'+r['relname'];cols=[];cons=[]
                for entry in value.get('tableElts',[]):
                    if'ColumnDef'in entry:
                        column=entry['ColumnDef'];cols.append(column['colname'])
                        cons.extend((x['Constraint'],[column['colname']])for x in column.get('constraints',[]))
                    elif'Constraint'in entry:
                        constraint=entry['Constraint'];keys=[x['String']['sval']for x in constraint.get('keys',[])]
                        cons.append((constraint,keys))
                tables[name]=[name+':'+c for c in cols]
                for constraint,keys in cons:
                    kind=constraint['contype']
                    if kind not in('CONSTR_PRIMARY','CONSTR_UNIQUE','CONSTR_FOREIGN','CONSTR_CHECK'):continue
                    constraints+=1
                    if kind=='CONSTR_FOREIGN':fks+=1
                    if kind in('CONSTR_PRIMARY','CONSTR_UNIQUE'):
                        if constraint.get('conname'):index=constraint['conname']
                        elif kind=='CONSTR_PRIMARY':index=r['relname']+'_pkey'
                        else:index=r['relname']+'_'+'_'.join(keys)+'_key'
                        indexes.append(r['schemaname']+'.'+index)
            if'CreateTrigStmt'in node:
                value=node['CreateTrigStmt'];r=value['relation']
                triggers.append(dict(name=value['trigname'],relation=r['schemaname']+'.'+r['relname'],
                    events=value['events'],timing=value.get('timing',0),row=value.get('row',False),
                    function='.'.join(x['String']['sval']for x in value['funcname'])))
    definitions,proof=native_hooks.derive(native_hooks.originals())
    assert len(functions)==16 and len(tables)==3 and len(triggers)==3 and len(indexes)==4 and fks==1
    return dict(contract=composition.CONTRACT,actual_parent_adoption=False,source_sql={n:pin(t.encode())for n,t in sources.items()},
        functions=functions,tables=sorted(tables),columns=sorted(c for cs in tables.values()for c in cs),
        types=sorted(x for n in tables for x in(n,n+'[]')),triggers=triggers,index_relations=sorted(indexes),
        index_count=len(indexes),constraint_count=constraints,foreign_key_count=fks,
        native_adapter_sources={n:pin(t.encode())for n,t in definitions.items()},
        native_adapter_routes=proof['source_routes'],Native_adapters=8,
        parser=dict(pglast=pglast.__version__,PostgreSQL_grammar=170007),actual_SQL_executed=0,
        actual_Native_cases=0,production_go=False,independent_acceptance=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--write',action='store_true');args=parser.parse_args()
    raw=(json.dumps(build(),indent=2)+'\n').encode()
    if args.write:(HERE/'INSTALL_PLAN.json').write_bytes(raw)
    else:
        if raw!=(HERE/'INSTALL_PLAN.json').read_bytes():raise ValueError('GLOBAL_INSTALL_PLAN_SOURCE_CHANGED')
        print(json.dumps(dict(status='EXACT_SOURCE_PLAN_NOT_ACTUAL_INSTALLATION',plan=pin(raw))))
