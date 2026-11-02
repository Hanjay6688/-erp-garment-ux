"""Selected-current-source type/operator/cast/input review, never execution.

The earlier candidate set is reused as a conservative starting set. Only those
bodies and newly reached callbacks are parsed for the NEW dispatch projection;
the old all2970 census/parser controls and financial tests are not repeated.
Actual full25 metadata is mandatory. Unknown dispatch remains explicitly open.
"""
from collections import defaultdict,deque
from pathlib import Path
from hashlib import sha256
import argparse,csv,json,re,sys
from intake_common import exact,pin,require
from scan_saved_writer_census import Parser,walk,relation,WRITES

ALIASES=dict(int='integer',int8='bigint',int4='integer',int2='smallint',bool='boolean',float8='double precision',float4='real',
    timestamptz='timestamp with time zone',timestamp='timestamp without time zone',timetz='time with time zone',
    varchar='character varying',bpchar='character',decimal='numeric')
BUILTIN=set(('bigint smallint integer boolean real numeric money text name bytea date uuid xid8 xid oid tid regclass regprocedure regtype regrole regnamespace regcollation regoperator regconfig regdictionary json jsonb record void trigger event_trigger internal cstring unknown anyelement anyarray anynonarray anyenum anycompatible anycompatiblearray aclitem int2vector oidvector pg_node_tree char bit').split())|{'double precision','character varying','character','timestamp with time zone','timestamp without time zone','time with time zone','time without time zone','interval','bit varying'}


def normalize_type(name):
    name=re.sub(r'%rowtype$','',name,flags=re.I)
    name=re.sub(r'"([a-z_][a-z0-9_]*)"',r'\1',name)
    name=re.sub(r'\([^()]*\)','',name).strip().replace('pg_catalog.','')
    suffix=''
    while name.endswith('[]'):name=name[:-2];suffix+='[]'
    return ALIASES.get(name,name)+suffix


def typename(node):
    return normalize_type('.'.join(x['String']['sval']for x in node['names']))+('[]'*len(node.get('arrayBounds',[])))


class DispatchParser(Parser):
    def __init__(self):super().__init__();self.dispatch_cache={}

    def inspect_query(self,query,mode=0):
        cache_key=(mode,query)
        if cache_key in self.dispatch_cache:return self.dispatch_cache[cache_key]
        facts=super().sql(query,mode);require(facts['error']is None,'DISPATCH_EXISTING_QUERY_MUST_PARSE:'+str(facts['error']))
        if mode in(3,4,5):
            depth=0;assignment=None
            for token in self.pg.scan(query):
                if token.name in('ASCII_40','ASCII_91'):depth+=1
                elif token.name in('ASCII_41','ASCII_93'):depth-=1
                elif depth==0 and token.name in('COLON_EQUALS','ASCII_61'):assignment=token;break
            require(assignment is not None,'DISPATCH_ASSIGNMENT_BOUNDARY');query=query.encode()[assignment.end+1:].decode();mode=2
        if mode==2:query='SELECT '+query
        tree=json.loads(self.parser.parse_sql_json(query));types=set();operators=set();digests=[]
        for kind,value in walk(tree):
            if kind=='TypeName':types.add(typename(value))
            if kind=='A_Expr'and value.get('name'):
                operators.add('.'.join(x['String']['sval']for x in value['name']))
            if kind=='FuncCall':
                name='.'.join(x['String']['sval']for x in value['funcname'])
                if name.rsplit('.',1)[-1]=='digest':
                    args=value.get('args',[]);algorithm=None
                    if len(args)==2:algorithm=args[1].get('A_Const',{}).get('sval',{}).get('sval')
                    digests.append(dict(call=name,arguments=len(args),literal_algorithm=algorithm))
        result={k:sorted(v)for k,v in facts.items()if isinstance(v,set)}
        result.update(types=sorted(types),operators=sorted(operators),digest_calls=digests)
        self.dispatch_cache[cache_key]=result;return result

    def inspect_function(self,row):
        definition,language=row[0],row[2]
        create=json.loads(self.parser.parse_sql_json(definition))['stmts'][0]['stmt']['CreateFunctionStmt']
        types={typename(value)for kind,value in walk(create)if kind=='TypeName'}
        queries=[];dynamic=[];opaque=language not in('sql','plpgsql')
        if language=='plpgsql':
            for kind,value in walk(self.pg.parse_plpgsql(definition)):
                if kind=='PLpgSQL_expr':queries.append((value['query'],value['parseMode']))
                if kind=='PLpgSQL_type'and isinstance(value.get('typname'),str):types.add(normalize_type(value['typname']))
                if kind in('PLpgSQL_stmt_dynexecute','PLpgSQL_stmt_dynfors','PLpgSQL_stmt_call'):dynamic.append(kind)
                if kind=='PLpgSQL_stmt_open'and value.get('dynquery'):dynamic.append('PLpgSQL_stmt_open_dynamic')
        elif language=='sql':
            require(not create.get('sql_body'),'DISPATCH_NEW_SQL_ATOMIC_BODY_REQUIRES_REVIEW')
            bodies=[x['DefElem']['arg']['List']['items']for x in create['options']if x['DefElem']['defname']=='as']
            exact(len(bodies),1,'DISPATCH_ONE_SQL_BODY');exact(len(bodies[0]),1,'DISPATCH_ONE_SQL_BODY_STRING')
            queries.append((bodies[0][0]['String']['sval'],0))
        result=dict(types=types,operators=set(),calls=set(),relations=set(),writes=set(),digest_calls=[],dynamic=dynamic,opaque=opaque)
        for query,mode in queries:
            values=self.inspect_query(query,mode)
            for name in('types','operators','calls','relations'):result[name].update(values[name])
            result['writes'].update(tuple(x)for x in values['writes']);result['digest_calls'].extend(values['digest_calls'])
        return result


def catalogue(raw):
    data=json.loads(raw);exact(len(data),25,'DISPATCH_ACTUAL_FULL25_REQUIRED');result={}
    for key,rows in data.items():
        result[key]=dict(rows);exact(len(result[key]),len(rows),'DISPATCH_DUPLICATE_ACTUAL_METADATA_KEY:'+key)
    return result


def review(raw,prior,c_contract,reuse=None):
    actual=catalogue(raw);parser=DispatchParser();functions=actual['functions'];by_name=defaultdict(set);simple=defaultdict(set)
    for signature in functions:
        name=signature.split('(')[0];by_name[name].add(signature);simple[name.rsplit('.',1)[-1]].add(signature)
    def targets(name):return by_name.get(name,set())if'.'in name else simple.get(name,set())
    candidates=set(prior['all_branch_reachable_function_candidates'])|{n for n in functions if n.startswith(('cp7_global_nonpo_envelope.','cp7_global_nonpo_native_graph.','cp7_global_catalog_fence.'))}
    require(candidates<=set(functions),'DISPATCH_ACTUAL_CURRENT_CANDIDATE_IDENTITY_MISSING')
    literals=prior['literal_dynamic_source_bounds'];platform={'cp7_global_catalog_fence.lock_v1()','cp7_global_catalog_fence.lock_relations_v1(text)'}
    c_expected=c_contract['full19_actual_C_metadata']
    for sig,row in c_expected.items():exact(functions.get(sig),row,'DISPATCH_EXACT_PLATFORM_OWNED_C_FULL19:'+sig)
    facts={};reused=[];seen_relations=set();writes=set();operators=set();types=set();paths={'pg_catalog'};opaque={};dynamic={};unknown_calls=set();unknown_relations=set();extra_callbacks=set();expression_proofs={};trigger_proofs={}
    def absorb(value):
        types.update(value['types']);operators.update(value['operators'])
        for name in value['relations']:
            if name in actual['relations']:seen_relations.add(name)
            elif'.'not in name:
                seen_relations.update(n for n in actual['relations']if n.rsplit('.',1)[-1]==name)
            elif not name.startswith(('pg_catalog.','information_schema.')):unknown_relations.add(name)
        for _,name in value['writes']:
            matches={name}if name in actual['relations']else{n for n in actual['relations']if n.rsplit('.',1)[-1]==name}
            writes.update(matches);seen_relations.update(matches)
            if not matches and'.'in name and not name.startswith(('pg_catalog.','information_schema.')):unknown_relations.add(name)
        for name in value['calls']:
            found=targets(name)
            if found:candidates.update(found)
            elif'.'in name and not name.startswith('pg_catalog.'):unknown_calls.add(name)
    completed_relations=set();completed_writes=set();dispatch_rows={};casts={};used_types={};domain_checks={}
    while True:
        before=(len(facts),len(seen_relations),len(writes),len(types),len(candidates))
        for sig in sorted(candidates-set(facts)):
            row=functions[sig];cached=(reuse or{}).get('facts',{}).get(sig)
            if cached and cached.get('definition')==pin(row[0].encode())and cached.get('language')==row[2]:
                value={k:v for k,v in cached.items()if k not in('definition','language')}
                value['types']={normalize_type(x)for x in value['types']}
                for key in('operators','calls','relations'):value[key]=set(value[key])
                value['writes']={tuple(x)for x in value['writes']};reused.append(sig)
            else:value=parser.inspect_function(row)
            facts[sig]=value;absorb(value)
            for setting in row[12]or[]:
                if setting.startswith('search_path='):
                    for name in next(csv.reader([setting.split('=',1)[1]],skipinitialspace=True)):
                        if name:paths.add(name)
            if value['opaque']and sig not in c_expected:opaque[sig]=dict(language=row[2],owner=row[1],full19=pin(json.dumps(row,separators=(',',':')).encode()))
            if value['dynamic']:
                if sig in literals:
                    exact(pin(row[0].encode()),literals[sig]['definition'],'DISPATCH_RETAINED_LITERAL_BODY_CHANGED:'+sig)
                    for statement in literals[sig]['statements']:absorb(parser.inspect_query(statement['query']))
                elif sig not in platform:dynamic[sig]=value['dynamic']
        for name in sorted(seen_relations-completed_relations):
            completed_relations.add(name);row=actual['relations'][name];expressions=[]
            if row[1]in('v','m')and row[9]:expressions.append(('VIEW:'+name,row[9],0))
            for key,row in actual['columns'].items():
                if key.split(':',1)[0]==name:
                    types.add(normalize_type(row[2]))
                    if row[13]:expressions.append(('DEFAULT:'+key,row[13],2))
            for key,row in actual['policies'].items():
                if key.split(':',1)[0]==name:
                    for i in(3,4):
                        if row[i]:expressions.append(('POLICY'+str(i)+':'+key,row[i],2))
            for key,row in actual['rules'].items():
                if key.split(':',1)[0]==name:expressions.append(('RULE:'+key,row[3],0))
            for key,row in actual['constraints'].items():
                if row[9]==name and row[0]=='c':expressions.append(('CHECK:'+key,re.sub(r'\s+(?:NO INHERIT|NOT VALID)\s*$','',row[10].removeprefix('CHECK ').strip()),2))
            for key,query,mode in expressions:
                value=parser.inspect_query(query,mode);absorb(value);expression_proofs[key]=dict(source=pin(query.encode()),mode=mode,types=value['types'],operators=value['operators'])
            for key,parent in actual['inheritance'].items():
                if parent==name:seen_relations.add(key.split(':',1)[0])
        for name in sorted(writes-completed_writes):
            completed_writes.add(name)
            for key,row in actual['triggers'].items():
                if key.split(':',1)[0]!=name:continue
                trigger_proofs[key]=dict(firing_relation=name,full16=pin(json.dumps(row,separators=(',',':')).encode()))
                stem=row[8].replace('"','').split('(')[0]
                if row[0]and stem.rsplit('.',1)[-1].startswith('RI_FKey_'):
                    if row[13]:seen_relations.add(row[13])
                    if row[13]and re.fullmatch(r'RI_FKey_(?:cascade|setnull|setdefault)_(?:del|upd)',stem.rsplit('.',1)[-1]):writes.add(row[13])
                elif targets(stem):candidates.update(targets(stem))
                else:unknown_calls.add(stem)
        # Domain coercion is implicit even without an explicit CAST node.
        for name,row in actual['types'].items():
            if normalize_type(name)not in types:continue
            used_types[name]=row
            if row[1]=='d'and row[6]:types.add(normalize_type(row[6]))
            for key,constraint in actual['constraints'].items():
                if key.split(':',1)[0]==name and constraint[0]=='c'and constraint[9]is None:
                    query=re.sub(r'\s+(?:NO INHERIT|NOT VALID)\s*$','',constraint[10].removeprefix('CHECK ').strip());value=parser.inspect_query(query,2);absorb(value);domain_checks[key]=dict(source=pin(query.encode()),calls=value['calls'],relations=value['relations'])
            implementation=actual['type_implementation'][name]
            for callback in implementation[9:]:
                if callback=='-':continue
                stem=callback.replace('"','').split('(')[0];found=targets(stem)
                if found:candidates.update(found);extra_callbacks.update(found)
                elif'.'in stem and not stem.startswith('pg_catalog.'):unknown_calls.add(stem)
        for key,row in actual['casts'].items():
            source,target=key.split('->',1);source=normalize_type(source);target=normalize_type(target)
            # Any implicit destination can become part of expression dispatch;
            # explicit/assignment targets must already occur in typed inputs.
            if source not in types or(target not in types and row[0]!='i'):continue
            if row[0]=='i':types.add(target)
            casts[key]=row
            if row[2]!='-':
                stem=row[2].replace('"','').split('(')[0];found=targets(stem)
                if found:candidates.update(found);extra_callbacks.update(found)
                elif'.'in stem and not stem.startswith('pg_catalog.'):unknown_calls.add(stem)
        for key,row in actual['operators'].items():
            stem=key.split('(')[0];namespace,op=stem.rsplit('.',1)
            if not(op in operators and namespace in paths or stem in operators):continue
            left,right=normalize_type(row[4]),normalize_type(row[5])
            if any(t not in types and t!='-'for t in(left,right)):continue
            dispatch_rows[key]=row
            for callback in(row[7],row[10],row[11]):
                if callback=='-':continue
                name=callback.replace('"','').split('(')[0];found=targets(name)
                if found:candidates.update(found);extra_callbacks.update(found)
                elif'.'in name and not name.startswith('pg_catalog.'):unknown_calls.add(name)
        after=(len(facts),len(seen_relations),len(writes),len(types),len(candidates))
        if after==before:break
    unknown_types=sorted(n for n in types if not n.startswith('pg_catalog.')and normalize_type(n).removesuffix('[]')not in BUILTIN and n not in actual['types'])
    physical=sorted(n for n in seen_relations if actual['relations'][n][1]in('r','p')and not n.startswith('pg_'))
    managed=sorted(n for n in physical if n.split('.',1)[0]in{'auth','storage','realtime','supabase_functions','supabase_migrations','graphql','graphql_public','vault','net','cron','pgsodium','pgsodium_masks'})
    return dict(status='ACTUAL_FULL25_SELECTED_SOURCE_DISPATCH_INPUT_REVIEW_NOT_RUNTIME_OR_FINANCIAL_ACCEPTANCE',
        original_full25=pin(raw),prior_candidate_functions=len(prior['all_branch_reachable_function_candidates']),
        selected_current_bodies_with_dispatch_projection=len(facts),saved_actual_DE_dispatch_projections_reused=len(reused),
        selected_bodies_parsed_for_NEW_dispatch_projection=len(facts)-len(reused),whole2970_census_and_parser_controls_NOT_rerun=True,
        selected_function_identities=sorted(facts),physical_relation_candidates=physical,
        possible_write_relations=sorted(writes),new_type_projection=sorted(types),unknown_type_names=unknown_types,
        search_path_namespace_union=sorted(paths),operator_tokens=sorted(operators),potential_operator_dispatch=dispatch_rows,
        potential_cast_dispatch=casts,used_custom_type_rows=used_types,domain_check_sources=domain_checks,
        callback_candidates_added=sorted(extra_callbacks),metadata_expression_sources=expression_proofs,
        actual_trigger_firing_identity_sources=trigger_proofs,bounded_literal_dynamic_statements=sum(v['dynamic_statements']for v in literals.values()),
        fixed_platform_dynamic_functions=sorted(platform),reviewed_C_source_contracts=sorted(c_expected),
        unresolved_opaque=opaque,unresolved_dynamic=dynamic,unresolved_qualified_calls=sorted(unknown_calls),
        unresolved_qualified_relations=sorted(unknown_relations),managed_platform_physical_relations=managed,
        digest_argument_sites={n:v['digest_calls']for n,v in facts.items()if v['digest_calls']},
        source_projection_has_no_unresolved=not(opaque or dynamic or unknown_calls or unknown_types or unknown_relations or managed),
        trusted_pinned_PostgreSQL_and_platform_extension_binary_integrity_is_assumed=True,
        actual_final_profile_or_runtime_adopted=False,actual_SQL_executed=0,actual_Native_cases=0,
        production_go=False,independent_acceptance=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--catalogue',type=Path,required=True);parser.add_argument('--prior',type=Path,required=True);parser.add_argument('--c-contract',type=Path,required=True);parser.add_argument('--parser-runtime',type=Path,required=True);parser.add_argument('--reuse-projection',type=Path);parser.add_argument('--out',type=Path,required=True);a=parser.parse_args()
    reuse=None
    if a.reuse_projection:
        raw=a.reuse_projection.read_bytes()
        exact(pin(raw),dict(bytes=217986,sha256='918e9ff70afd8fd5f6c5c80ed51dc3e6bb6bf8f4b5655dd3642f38dca050b89c'),'DISPATCH_EXACT_SAVED_DE_PROJECTION_CACHE')
        reuse=json.loads(raw)
    sys.path.insert(0,str(a.parser_runtime));value=review(a.catalogue.read_bytes(),json.loads(a.prior.read_bytes()),json.loads(a.c_contract.read_bytes()),reuse);a.out.write_text(json.dumps(value,indent=2)+'\n')
    print(json.dumps({k:value[k]for k in('status','selected_bodies_parsed_for_NEW_dispatch_projection','unknown_type_names','unresolved_opaque','unresolved_dynamic','unresolved_qualified_calls','source_projection_has_no_unresolved')}))
