"""Offline PostgreSQL-17 syntax inventory of every saved function, not closure.

No function body is executed. Dynamic SQL, C functions, unresolved calls and
parse errors remain explicit review obligations. Exact runtime OIDs, raw ACLs,
operator/cast dispatch and concurrency are not inferred from syntax.
"""
from collections import Counter,defaultdict
from hashlib import sha256
from pathlib import Path
import argparse,json,sys

from intake_common import exact,pin,require

SOURCE_PIN=dict(bytes=14658977,sha256='39c88c4494b10e711b8e58116ea6013e00e1caae8f1d4f9b64fda9566e5c0789')
WRITES={'InsertStmt':'INSERT','UpdateStmt':'UPDATE','DeleteStmt':'DELETE','MergeStmt':'MERGE',
        'TruncateStmt':'TRUNCATE','CreateTableAsStmt':'CREATE_TABLE_AS','RefreshMatViewStmt':'REFRESH'}


def walk(value):
    if isinstance(value,dict):
        for name,item in value.items():
            yield name,item
            yield from walk(item)
    elif isinstance(value,list):
        for item in value:yield from walk(item)


def relation(value):
    if 'RangeVar'in value:value=value['RangeVar']
    if not isinstance(value,dict)or not value.get('relname'):return None
    return '.'.join(str(value[k])for k in('catalogname','schemaname','relname')if value.get(k))


class Parser:
    def __init__(self):
        import pglast
        from pglast import parser
        exact(pglast.__version__,'v7.20','WRITER_CENSUS_EXACT_ANALYSIS_PARSER_VERSION')
        exact(parser.get_postgresql_version(),(17,7),'WRITER_CENSUS_POSTGRESQL17_PARSER')
        self.pg=pglast;self.parser=parser;self.cache={}

    def sql(self,query,mode=0):
        key=(mode,query)
        if key in self.cache:return self.cache[key]
        result=dict(relations=set(),writes=set(),calls=set(),statement_kinds=set(),error=None)
        try:
            if mode in(3,4,5):
                depth=0;assignment=None
                for token in self.pg.scan(query):
                    if token.name in('ASCII_40','ASCII_91'):depth+=1
                    elif token.name in('ASCII_41','ASCII_93'):depth-=1
                    elif depth==0 and token.name in('COLON_EQUALS','ASCII_61'):
                        assignment=token;break
                require(assignment is not None,'WRITER_CENSUS_ASSIGNMENT_OPERATOR_UNRESOLVED')
                # Token offsets are byte offsets, including non-ASCII text.
                query=query.encode()[assignment.end+1:].decode();mode=2
            if mode==2:query='SELECT '+query
            require(mode in(0,2),'WRITER_CENSUS_UNSUPPORTED_PLPGSQL_PARSE_MODE')
            tree=json.loads(self.parser.parse_sql_json(query))
            for name,item in walk(tree):
                if name=='RangeVar':
                    target=relation(item)
                    if target:result['relations'].add(target)
                if name=='FuncCall':
                    result['calls'].add('.'.join(x['String']['sval']for x in item['funcname']))
                if name.endswith('Stmt'):result['statement_kinds'].add(name)
                if name in WRITES:
                    candidates=item.get('relations',[])if name=='TruncateStmt'else[item.get('relation',{})]
                    if name=='CreateTableAsStmt':candidates=[item.get('into',{}).get('rel',{})]
                    for candidate in candidates:
                        target=relation(candidate)
                        if target:result['writes'].add((WRITES[name],target))
                if name=='CopyStmt'and item.get('is_from'):
                    target=relation(item.get('relation',{}))
                    if target:result['writes'].add(('COPY_FROM',target))
        except Exception as error:result['error']=str(error)[:500]
        self.cache[key]=result
        return result

    def function(self,definition,language):
        result=dict(relations=set(),writes=set(),calls=set(),statement_kinds=set(),
            dynamic_PL_statements=Counter(),query_errors=[],outer_error=None,body_error=None,
            parsed_expressions=0,opaque_language=language not in('sql','plpgsql'))
        try:
            outer=json.loads(self.parser.parse_sql_json(definition))
            create=outer['stmts'][0]['stmt']['CreateFunctionStmt']
        except Exception as error:
            result['outer_error']=str(error)[:500];return result
        expressions=[]
        if language=='plpgsql':
            try:
                tree=self.pg.parse_plpgsql(definition)
                for name,item in walk(tree):
                    if name=='PLpgSQL_expr':expressions.append((item['query'],item['parseMode']))
                    if name in('PLpgSQL_stmt_dynexecute','PLpgSQL_stmt_dynfors','PLpgSQL_stmt_call'):
                        result['dynamic_PL_statements'][name]+=1
                    if name=='PLpgSQL_stmt_open'and item.get('dynquery'):
                        result['dynamic_PL_statements']['PLpgSQL_stmt_open_dynamic']+=1
            except Exception as error:result['body_error']=str(error)[:500]
        elif language=='sql':
            if create.get('sql_body'):
                result['body_error']='SQL_BEGIN_ATOMIC_BODY_REQUIRES_SEPARATE_AST_REVIEW'
            else:
                bodies=[x['DefElem']['arg']['List']['items']for x in create['options']if x['DefElem']['defname']=='as']
                if len(bodies)!=1 or len(bodies[0])!=1:
                    result['body_error']='SQL_FUNCTION_BODY_FORM_UNRESOLVED'
                else:expressions.append((bodies[0][0]['String']['sval'],0))
        for query,mode in expressions:
            row=self.sql(query,mode)
            result['parsed_expressions']+=1
            for key in('relations','writes','calls','statement_kinds'):result[key].update(row[key])
            if row['error']:result['query_errors'].append(dict(query=pin(query.encode()),mode=mode,error=row['error']))
        return result


def controls(parser):
    cte=parser.sql("WITH removed AS (DELETE FROM erp.sales RETURNING id) INSERT INTO erp.audit_logs(entity_id) SELECT id FROM removed")
    exact(cte['writes'],{('DELETE','erp.sales'),('INSERT','erp.audit_logs')},'WRITER_PARSER_DATA_MODIFYING_CTE_NOT_MISCLASSIFIED_READONLY')
    decoy=parser.sql("SELECT 'UPDATE erp.sales SET status=''POSTED''' AS label /* DELETE FROM erp.sales */")
    exact(decoy['writes'],set(),'WRITER_PARSER_COMMENTS_AND_STRING_LITERALS_ARE_NOT_EXECUTED_DML')
    dynamic=parser.function("CREATE FUNCTION private_control() RETURNS void LANGUAGE plpgsql AS $$ BEGIN EXECUTE 'DELETE FROM erp.sales'; END; $$",'plpgsql')
    exact(dict(dynamic['dynamic_PL_statements']),{'PLpgSQL_stmt_dynexecute':1},'WRITER_PARSER_DYNAMIC_SQL_MUST_REMAIN_OPEN')
    exact(dynamic['writes'],set(),'WRITER_PARSER_DYNAMIC_LITERAL_NOT_CLAIMED_AS_BOUND_TARGET')
    assignment=parser.sql("x := erp.current_app_user_id()",3)
    exact(assignment['calls'],{'erp.current_app_user_id'},'WRITER_PARSER_PL_ASSIGNMENT_CALL_RETAINED')
    require(all(row['error']is None for row in(cte,decoy,assignment))and not dynamic['body_error'],
        'WRITER_PARSER_CONTROLS_MUST_ACTUALLY_PARSE')
    return dict(modifying_CTE_detected=True,literal_and_comment_decoys_excluded=True,
        dynamic_SQL_explicitly_unresolved=True,assignment_function_call_preserved=True,
        SQL_executed=0,Native_cases=0)


def census(raw,blueprint):
    exact(pin(raw),SOURCE_PIN,'WRITER_CENSUS_EXACT_ACCEPTED15A_RAW_CENSUS_ORIGINAL')
    data=json.loads(raw);catalog=data['catalog_rows'];functions=catalog['functions']
    exact(len(catalog),22,'WRITER_CENSUS_ALL_TWENTYTWO_GROUPS')
    exact(len(functions),2894,'WRITER_CENSUS_ALL_ACTUAL_FUNCTIONS_NOT_LITERAL78')
    parser=Parser();proof=controls(parser);records={};by_name=defaultdict(set)
    for signature in functions:by_name[signature.split('(')[0]].add(signature)
    simple=defaultdict(set)
    for name,signatures in by_name.items():simple[name.rsplit('.',1)[-1]].update(signatures)
    global_relations=set(blueprint['relations']);exact(len(global_relations),38,'WRITER_CENSUS_REVIEWED_GLOBAL_RELATIONS38')
    for signature,metadata in functions.items():
        exact(len(metadata),19,'WRITER_CENSUS_FULL19_FUNCTION_METADATA:'+signature)
        result=parser.function(metadata[0],metadata[2]);calls=result.pop('calls')
        candidates=set();unresolved=[];ambiguous=[]
        for name in sorted(calls):
            targets=by_name.get(name,set())if'.'in name else simple.get(name,set())
            if not targets:unresolved.append(name)
            else:
                candidates.update(targets)
                if len(targets)>1 or'.'not in name:ambiguous.append(dict(name=name,candidate_count=len(targets)))
        result={k:sorted(v)if isinstance(v,set)else dict(v)if isinstance(v,Counter)else v for k,v in result.items()}
        records[signature]=dict(definition=pin(metadata[0].encode()),full19_row=pin(json.dumps(metadata,separators=(',',':'),ensure_ascii=False).encode()),
            owner=metadata[1],language=metadata[2],kind=metadata[3],security_definer=metadata[4],
            configuration=metadata[12],expanded_execute_ACL=metadata[18],**result,
            static_call_names=sorted(calls),candidate_callees=sorted(candidates),unresolved_external_or_builtin_calls=unresolved,
            overload_or_search_path_ambiguities=ambiguous,direct_global_writes=sorted({target for _,target in result['writes']}&global_relations))
    direct={name for name,row in records.items()if row['direct_global_writes']};closure=set(direct)
    while True:
        following=closure|{name for name,row in records.items()if set(row['candidate_callees'])&closure}
        if following==closure:break
        closure=following
    trigger_rows={name:dict(relation=row[15],function=row[8],internal=row[0],enabled=row[1],
        referenced_relation=row[13],constraint=row[12],full16_row=pin(json.dumps(row,separators=(',',':')).encode()))
        for name,row in catalog['triggers'].items()if row[15]in global_relations or row[13]in global_relations}
    # Match the actual RI check identities, including incoming references
    # from outside tables. Constraint text can omit the schema or contain
    # another relation's name as a substring and is not an identity oracle.
    fk_keys=set()
    for row in catalog['triggers'].values():
        function=row[8].replace('"','').split('(')[0].rsplit('.',1)[-1]
        if row[0]is True and function in('RI_FKey_check_ins','RI_FKey_check_upd')and(
                row[15]in global_relations or row[13]in global_relations):
            fk_keys.add(row[15]+':'+row[12])
    for key in fk_keys:
        require(key in catalog['constraints']and catalog['constraints'][key][0]=='f',
            'WRITER_CENSUS_RI_CHECK_MUST_BIND_ACTUAL_FOREIGN_KEY:'+key)
    foreign_keys={name:dict(relation=catalog['constraints'][name][9],
        definition=catalog['constraints'][name][10],
        full_row=pin(json.dumps(catalog['constraints'][name],separators=(',',':')).encode()))
        for name in sorted(fk_keys)}
    unresolved_functions=[name for name,row in records.items()if row['outer_error']or row['body_error']or row['query_errors']or row['dynamic_PL_statements']or row['opaque_language']]
    return dict(status='SAVED_ACTUAL2894_FUNCTION_SYNTAX_WRITER_CENSUS_NOT_RUNTIME_CLOSURE',
        accepted_source=SOURCE_PIN,parser=dict(pglast='7.20',PostgreSQL=[17,7],grammar_not_execution=True),
        parser_controls=proof,catalog_groups={k:len(v)for k,v in catalog.items()},
        functions_scanned=len(records),languages=dict(Counter(row['language']for row in records.values())),
        parsed_expressions=sum(row['parsed_expressions']for row in records.values()),
        unique_query_parse_cache_entries=len(parser.cache),functions_with_explicit_unresolved_syntax_or_dynamic_or_opaque=unresolved_functions,
        direct_global_writer_candidates=sorted(direct),transitive_static_known_call_candidates=sorted(closure),
        exact_runtime_call_graph_claim=False,all_external_builtin_calls_resolved=False,
        operator_cast_RLS_trigger_and_FK_dispatch_closure=False,raw_NULL_ACL_or_OID_inferred=False,
        relevant_triggers_and_RI=trigger_rows,relevant_foreign_keys=foreign_keys,
        foreign_keys_selected_by_exact_RI_identities_not_SQL_text=True,
        actual_event_triggers=catalog['event_triggers'],role_count=len(catalog['roles']),membership_count=len(catalog['memberships']),
        global_relations=sorted(global_relations),functions=records,
        ERP_imports=0,SQL_executed=0,Native_cases=0,global_writer_or_current_rights_or_phantom_closure=False,
        production_go=False,independent_acceptance=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--census',type=Path,required=True);p.add_argument('--blueprint',type=Path,required=True);p.add_argument('--parser-runtime',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    sys.path.insert(0,str(a.parser_runtime));value=census(a.census.read_bytes(),json.loads(a.blueprint.read_bytes()))
    a.output.write_text(json.dumps(value,indent=2)+'\n')
    print(json.dumps({k:v for k,v in value.items()if k not in('functions','relevant_triggers_and_RI','relevant_foreign_keys','actual_event_triggers','functions_with_explicit_unresolved_syntax_or_dynamic_or_opaque','direct_global_writer_candidates','transitive_static_known_call_candidates')}))
    print(json.dumps({'direct_writer_candidates':len(value['direct_global_writer_candidates']),
        'transitive_candidates':len(value['transitive_static_known_call_candidates']),
        'unresolved_function_count':len(value['functions_with_explicit_unresolved_syntax_or_dynamic_or_opaque']),
        'relevant_trigger_count':len(value['relevant_triggers_and_RI']),'relevant_FK_count':len(value['relevant_foreign_keys'])}))
