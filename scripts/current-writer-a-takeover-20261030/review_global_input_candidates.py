"""Incremental proposed Global input candidates from saved actual DE30 metadata.

Reuse unchanged body syntax only; rebuild call targets and trigger identities.
This is not a runtime call graph, privilege, operator/RLS or phantom closure.
"""
from pathlib import Path
from hashlib import sha256
from collections import defaultdict,deque,Counter
import argparse,ast,importlib.util,json,re,sys,zipfile
from intake_common import exact,pin,require
import scan_saved_writer_census as syntax

CACHE=dict(bytes=6000014,sha256='3ca5e335ceb2198e2e069ff8ddedf249991e2326215a157c4f2c17dd1458cfbf')
CURRENT=dict(bytes=22185024,sha256='7607987b5a8a9100dddbfef5b39135b330eda329bf89b072b3839467cf7c7b86')
SCANNER=dict(bytes=13782,sha256='69adaed6494ea81cc93ed304718eda7a94131052a81ae3dbc2c8a6d54b4e045c')
FACTS=('relations','writes','statement_kinds','dynamic_PL_statements','query_errors','outer_error',
 'body_error','parsed_expressions','opaque_language')
NS='scripts/cp7_global_nonpo_envelope/'


def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


def type_name(node):
    names=[n['String']['sval']for n in node['names']]
    if names[0]=='pg_catalog':names=names[1:]
    aliases=dict(int8='bigint',int4='integer',int2='smallint',bool='boolean',float8='double precision')
    return '.'.join(aliases.get(n,n)for n in names)+('[]'*len(node.get('arrayBounds',[])))


def proposed_sources(repo,parser,actual):
    here=repo/NS;bridge=load_module('input_review_counted_catalog_bridge',here/'catalog_bridge.py')
    native=load_module('input_review_counted_native_owning',here/'native_hooks.py')
    native_originals=native.originals()
    for sig,row in native_originals.items():exact(actual['functions'][sig],row,'INPUT_REVIEW_ACTUAL_OWNING_ALL19:'+sig)
    definitions,proof=native.derive(native_originals);result={}
    for sig,text in definitions.items():result[sig]=dict(definition=text,language=actual['functions'][sig][2],kind='PROPOSED_NATIVE_OWNING_DERIVATION')
    texts={n:(here/n).read_text()for n in('schema.sql','work_scope.sql','review.sql','platform_catalog_fence.sql')}
    texts['derived_lock.sql']=bridge.derive()[0]
    texts.update({'graph_helpers/'+n:(here/'graph_helpers'/n).read_text()for n in('authority.sql','scope.sql','capture.sql','inspect.sql')})
    tables=set();triggers=[]
    for filename,text in texts.items():
        raw=text.encode();tree=json.loads(parser.parser.parse_sql_json(text))
        for item in tree['stmts']:
            stmt=item['stmt']
            if 'CreateStmt'in stmt:
                r=stmt['CreateStmt']['relation'];tables.add(r['schemaname']+'.'+r['relname'])
            if 'CreateTrigStmt'in stmt:
                t=stmt['CreateTrigStmt'];r=t['relation'];triggers.append(dict(firing_relation=r['schemaname']+'.'+r['relname'],function_name='.'.join(x['String']['sval']for x in t['funcname']),events=t['events'],source=filename))
            if 'CreateFunctionStmt'not in stmt:continue
            fn=stmt['CreateFunctionStmt'];stem='.'.join(x['String']['sval']for x in fn['funcname'])
            args=[x['FunctionParameter']for x in fn.get('parameters',[])];sig=stem+'('+','.join(type_name(x['argType'])for x in args if x.get('mode','FUNC_PARAM_IN')not in('FUNC_PARAM_OUT','FUNC_PARAM_TABLE'))+')'
            language=[x['DefElem']['arg']['String']['sval']for x in fn['options']if x['DefElem']['defname']=='language']
            exact(len(language),1,'INPUT_REVIEW_ONE_DECLARED_LANGUAGE')
            start=item.get('stmt_location',0);length=item.get('stmt_len',0);source=raw[start:start+length if length else None].decode()+';'
            require(sig not in result,'INPUT_REVIEW_UNIQUE_PROPOSED_IDENTITY:'+sig)
            result[sig]=dict(definition=source,language=language[0],kind='PROPOSED_NEW_PRIVATE_HELPER',file=filename)
    exact(len(definitions),8,'INPUT_REVIEW_EIGHT_COUNTED_OWNING_ADAPTERS');exact(len(result),21,'INPUT_REVIEW_EIGHT_DERIVED_AND_THIRTEEN_NEW_HELPERS')
    exact(len(tables),3,'INPUT_REVIEW_THREE_NEW_ENVELOPE_TABLES')
    return result,tables,triggers,proof


def review(cache_raw,current_raw,repo):
    exact(pin(cache_raw),CACHE,'INPUT_REVIEW_EXACT_SAVED_SYNTAX_FACTS');exact(pin(current_raw),CURRENT,'INPUT_REVIEW_EXACT_ACCEPTED_DE30_SOURCE')
    exact(pin(Path(syntax.__file__).read_bytes()),SCANNER,'INPUT_REVIEW_RETAINED_PARSER_SOURCE_UNCHANGED')
    cache=json.loads(cache_raw);actual=json.loads(current_raw)['before']['actual_all22'];exact(len(actual),22,'INPUT_REVIEW_ALL22_PRESENT')
    parser=syntax.Parser()  # Retained parser controls are deliberately not run.
    proposed,new_tables,proposed_triggers,owning=proposed_sources(repo,parser,actual)
    functions={n:dict(definition=r[0],language=r[2],kind='ACTUAL_ACCEPTED_DE30_NATIVE')for n,r in actual['functions'].items()}
    functions.update(proposed);facts={};reused=[];parsed=[]
    for sig,row in functions.items():
        previous=cache['functions'].get(sig)
        if previous and previous['definition']==pin(row['definition'].encode())and previous['language']==row['language']:
            facts[sig]={k:previous[k]for k in FACTS};facts[sig]['calls']=previous['static_call_names'];reused.append(sig)
        else:
            r=parser.function(row['definition'],row['language']);r={k:sorted(v)if isinstance(v,set)else dict(v)if isinstance(v,Counter)else v for k,v in r.items()};facts[sig]=r;parsed.append(sig)
    exact(len(reused),2970,'INPUT_REVIEW_REUSE2970_WITHOUT_REPARSING')
    exact(len(parsed),22,'INPUT_REVIEW_ONLY_CHANGED_CENSUS1_DERIVED8_NEW13_PARSED')
    by_name=defaultdict(set);simple=defaultdict(set)
    for sig in functions:stem=sig.split('(')[0];by_name[stem].add(sig);simple[stem.rsplit('.',1)[-1]].add(sig)
    def targets(name):return by_name.get(name,set())if'.'in name else simple.get(name,set())
    reference=json.loads((repo/NS/'graph_helpers/AUTHORITY.json').read_bytes())
    roots=set(reference['known_functions'])|set(proposed)
    queue=deque(roots);seen=set();read_relations=set();write_relations=set();unqualified=set();external_calls=set();trigger_bindings={};unknown_trigger_calls=set()
    actual_relations=set(actual['relations']);all_relations=actual_relations|new_tables
    simple_relations=defaultdict(set)
    for name in all_relations:simple_relations[name.rsplit('.',1)[-1]].add(name)
    def relation_targets(name):
        if name in all_relations:return{name}
        if'.'not in name:
            unqualified.add(name);return simple_relations.get(name,set())
        return set()
    firing=defaultdict(list)
    for key,row in actual['triggers'].items():
        exact(len(row),16,'INPUT_REVIEW_CURRENT_TRIGGER_FULL16')
        # tgrelid is the relation prefix in the original query key. row15 is
        # the constraint's child relation, and is NULL for regular triggers.
        relation=key.split(':',1)[0];require(relation in actual_relations,'INPUT_REVIEW_ACTUAL_FIRING_RELATION_FROM_QUERY_KEY')
        firing[relation].append((key,row))
    for t in proposed_triggers:firing[t['firing_relation']].append(('proposed:'+t['source']+':'+t['function_name'],t))
    processed_writes=set()
    while queue or write_relations-processed_writes:
        while queue:
            sig=queue.popleft()
            if sig in seen:continue
            seen.add(sig);r=facts[sig]
            for target in r['calls']:
                found=targets(target)
                if found:queue.extend(found)
                else:external_calls.add(target)
            for name in r['relations']:read_relations.update(relation_targets(name))
            for _,name in r['writes']:
                found=relation_targets(name);read_relations.update(found);write_relations.update(found)
        pending=sorted(write_relations-processed_writes);processed_writes.update(pending)
        for relation in pending:
            for key,row in firing[relation]:
                if isinstance(row,dict):
                    trigger_bindings[key]=row;queue.extend(targets(row['function_name']));continue
                trigger_bindings[key]=dict(firing_relation=relation,constraint_child=row[15],other_relation=row[13],function=row[8],internal=row[0],enabled=row[1])
                stem=row[8].split('(')[0].replace('"','');name=stem.rsplit('.',1)[-1]
                if row[0]and name.startswith('RI_FKey_'):
                    other=row[13]
                    if other:read_relations.update(relation_targets(other))
                    if other and re.fullmatch(r'RI_FKey_(?:cascade|setnull|setdefault)_(?:del|upd)',name):write_relations.update(relation_targets(other))
                elif targets(stem):queue.extend(targets(stem))
                else:unknown_trigger_calls.add(row[8])
    unresolved={n:{k:facts[n][k]for k in('dynamic_PL_statements','query_errors','outer_error','body_error','opaque_language')}for n in sorted(seen)if facts[n]['dynamic_PL_statements']or facts[n]['query_errors']or facts[n]['outer_error']or facts[n]['body_error']or facts[n]['opaque_language']}
    source_relations={n:dict(owner=actual['relations'][n][0],kind=actual['relations'][n][1])for n in sorted(read_relations&actual_relations)}
    ordinary=sum(not row[0]for row in actual['triggers'].values())
    return dict(status='PROPOSED_GLOBAL_INPUT_CANDIDATES_FROM_RETAINED_FACTS_NOT_RUNTIME_OR_BARRIER_CLOSURE',
        cache=CACHE,current_accepted_DE30=CURRENT,parser_source=SCANNER,parser=dict(pglast='7.20',PostgreSQL=[17,7]),
        retained_parser_and_old_census_controls_NOT_rerun=True,reused_native_body_facts=len(reused),new_or_changed_bodies_parsed=len(parsed),
        parsed_identities=parsed,parsed_source_facts={n:dict(source=pin(functions[n]['definition'].encode()),kind=functions[n]['kind'],**facts[n])for n in parsed},
        current_Native_all19_metadata_rebuilt_from_accepted_source=True,proposed_metadata_not_relabelled_as_actual=True,
        current_Native_function_count=len(actual['functions']),proposed_composite_function_count=len(functions),
        all_branch_reachable_function_candidates=sorted(seen),candidate_relations=source_relations,
        proposed_new_relations=sorted(new_tables),possible_write_relations=sorted(write_relations),
        unqualified_or_CTE_tokens_conservatively_matched_to_all_current_names=sorted(unqualified),
        external_or_builtin_calls_not_runtime_resolved=sorted(external_calls),unresolved_reachable_functions=unresolved,
        actual_trigger_firing_relation_rebuilt_from_original_query_key=True,
        constraint_child_row15_is_NOT_trigger_firing_relation=True,regular_actual_triggers=ordinary,
        relevant_actual_and_proposed_trigger_bindings=trigger_bindings,unresolved_trigger_callbacks=sorted(unknown_trigger_calls),
        remaining_before_closure=['Expand current view/rewrite/default/check/RLS expressions and operator/cast dispatch as needed',
            'Bound reachable dynamic/opaque cases and non-application inputs',
            'Choose exact lawful relation-lock authority and final raw identity/ACL profile',
            'Actual final parent adoption and Native dirty/stale/rights/phantom coexistence qualification'],
        actual_SQL_executed=0,actual_Native_cases=0,global_writer_or_permission_or_phantom_closure=False,
        production_go=False,independent_acceptance=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--cache',type=Path,required=True);p.add_argument('--de-archive',type=Path,required=True)
    p.add_argument('--global-source',type=Path,required=True);p.add_argument('--parser-runtime',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    require(not a.output.exists(),'INPUT_REVIEW_NEW_OUTPUT_REQUIRED');sys.path.insert(0,str(a.parser_runtime))
    with zipfile.ZipFile(a.de_archive)as z:raw=z.read('DE_GLOBAL_BEFORE_NATIVE30/CALLER_RAW_BOUNDARY_OBSERVATION.json')
    result=review(a.cache.read_bytes(),raw,a.global_source);a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status=result['status'],reused=result['reused_native_body_facts'],parsed=result['new_or_changed_bodies_parsed'],
        reachable_functions=len(result['all_branch_reachable_function_candidates']),relations=len(result['candidate_relations']),
        unresolved=len(result['unresolved_reachable_functions']),trigger_bindings=len(result['relevant_actual_and_proposed_trigger_bindings']),
        ordinary_trigger_identity_fix=result['actual_trigger_firing_relation_rebuilt_from_original_query_key'],actual_Native_cases=0)))
