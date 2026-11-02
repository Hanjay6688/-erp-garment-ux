"""Extend saved syntax facts to the actual installed DE prefix, without SQL.

The failed overall run is never promoted to Native acceptance. Source-equivalent
function bodies reuse already recorded parsing; ALL call targets and current
metadata are rebuilt. Dynamic/runtime/dispatch/authorization closure stays open.
"""
from pathlib import Path
from collections import Counter,defaultdict
import argparse,json,sys
from intake_common import exact,pin,require
import scan_saved_writer_census as retained

OLD_REPORT=dict(bytes=5694338,sha256='56ce1474d6ece1e7c35a7b250ade71fd0838153d4f5efcfd614b7a30c1b40060')
CURRENT_RAW=dict(bytes=22185024,sha256='e6fe54f13a3e2f563dcadeee8570256b095dc412cd692a9794027b8b2765627f')
SCANNER=dict(bytes=13782,sha256='69adaed6494ea81cc93ed304718eda7a94131052a81ae3dbc2c8a6d54b4e045c')
FACTS=('relations','writes','statement_kinds','dynamic_PL_statements','query_errors',
       'outer_error','body_error','parsed_expressions','opaque_language')
RIGHTS={'erp.app_permissions','erp.app_role_permissions','erp.app_roles','erp.app_users'}


def full19(row):
    return pin(json.dumps(row,separators=(',',':'),ensure_ascii=False).encode())


def validate_retained(catalog,prior):
    exact(set(prior['functions']),set(catalog['functions']),'CURRENT_CENSUS_ALL_RETAINED_IDENTITIES')
    for name,row in catalog['functions'].items():
        record=prior['functions'][name]
        exact(record['definition'],pin(row[0].encode()),'CURRENT_CENSUS_RETAINED_EXACT_BODY:'+name)
        exact(record['full19_row'],full19(row),'CURRENT_CENSUS_RETAINED_EXACT_FULL19:'+name)
        exact(record['language'],row[2],'CURRENT_CENSUS_RETAINED_LANGUAGE:'+name)


def reusable(metadata,previous):
    return(previous is not None and previous['definition']==pin(metadata[0].encode())
        and previous['language']==metadata[2])


def extend(prior_raw,old_raw,current_raw):
    exact(pin(prior_raw),OLD_REPORT,'CURRENT_CENSUS_EXACT_DURABLE_RETAINED_REPORT')
    exact(pin(old_raw),retained.SOURCE_PIN,'CURRENT_CENSUS_EXACT_RETAINED_ACCEPTED15A')
    exact(pin(current_raw),CURRENT_RAW,'CURRENT_CENSUS_EXACT_OBSERVED_DE_PREFIX')
    exact(pin(Path(retained.__file__).read_bytes()),SCANNER,'CURRENT_CENSUS_ORIGINAL_ANALYSIS_PARSER_UNCHANGED')
    prior=json.loads(prior_raw);old=json.loads(old_raw)['catalog_rows'];observed=json.loads(current_raw)
    exact(observed['classification'],'READONLY_CURRENT_DE_RAW_DEPENDENCIES_NOT_WRITER_CLOSURE','CURRENT_CENSUS_RECORDED_SCOPE')
    exact(observed['status'],'RAW_READONLY_METADATA_UNAVAILABLE','CURRENT_CENSUS_NO_FALSE_RAW_PAIR_CAPTURE')
    require(observed['actual_Native_cases']==0 and observed['global_writer_or_permission_or_lock_closure']is False,
        'CURRENT_CENSUS_NOT_AN_ACCEPTED_FINANCIAL_OR_GLOBAL_RUN')
    catalog=observed['before']['actual_all22'];functions=catalog['functions']
    exact(len(catalog),22,'CURRENT_CENSUS_FULL22');exact(len(functions),2979,'CURRENT_CENSUS_ALL_ACTUAL2979')
    validate_retained(old,prior)
    # New controls concern cache admission, not another execution of unchanged
    # parser controls or any original Native case.
    name=next(iter(old['functions']));metadata=old['functions'][name];record=prior['functions'][name]
    require(reusable(metadata,record),'CURRENT_CENSUS_EXACT_SOURCE_REUSABLE')
    changed=list(metadata);changed[0]+='\n-- changed source'
    require(not reusable(changed,record),'CURRENT_CENSUS_CHANGED_BODY_NOT_REUSED')
    changed=list(metadata);changed[2]='different-language'
    require(not reusable(changed,record),'CURRENT_CENSUS_CHANGED_LANGUAGE_NOT_REUSED')
    forged=json.loads(prior_raw);forged['functions'][name]['full19_row']['sha256']='0'*64
    try:validate_retained(old,forged)
    except ValueError:pass
    else:raise ValueError('CURRENT_CENSUS_FORGED_RETAINED_ROW_WAS_ACCEPTED')
    del forged
    parser=retained.Parser();records={};by_name=defaultdict(set);simple=defaultdict(set)
    for signature in functions:
        stem=signature.split('(')[0];by_name[stem].add(signature);simple[stem.rsplit('.',1)[-1]].add(signature)
    global_relations=set(prior['global_relations'])|RIGHTS
    exact(len(global_relations),42,'CURRENT_CENSUS_EXPLICIT38_PLUS4_RIGHTS_RELATIONS')
    require(global_relations<=set(catalog['relations']),'CURRENT_CENSUS_EVERY_RELATION_ACTUALLY_EXISTS')
    reused=[];parsed=[]
    for signature,metadata in functions.items():
        exact(len(metadata),19,'CURRENT_CENSUS_COMPLETE_CURRENT_METADATA:'+signature)
        previous=prior['functions'].get(signature)
        if reusable(metadata,previous):
            result={k:previous[k]for k in FACTS};calls=previous['static_call_names'];reused.append(signature)
        else:
            result=parser.function(metadata[0],metadata[2]);calls=sorted(result.pop('calls'));parsed.append(signature)
            result={k:sorted(v)if isinstance(v,set)else dict(v)if isinstance(v,Counter)else v for k,v in result.items()}
        candidates=set();unresolved=[];ambiguous=[]
        for target in calls:
            targets=by_name.get(target,set())if'.'in target else simple.get(target,set())
            if not targets:unresolved.append(target)
            else:
                candidates.update(targets)
                if len(targets)>1 or'.'not in target:ambiguous.append(dict(name=target,candidate_count=len(targets)))
        records[signature]=dict(definition=pin(metadata[0].encode()),full19_row=full19(metadata),
            owner=metadata[1],language=metadata[2],kind=metadata[3],security_definer=metadata[4],
            configuration=metadata[12],expanded_execute_ACL=metadata[18],**result,
            static_call_names=calls,candidate_callees=sorted(candidates),
            unresolved_external_or_builtin_calls=unresolved,overload_or_search_path_ambiguities=ambiguous,
            direct_global_writes=sorted({target for _,target in result['writes']}&global_relations))
    direct={name for name,row in records.items()if row['direct_global_writes']};closure=set(direct)
    while True:
        following=closure|{name for name,row in records.items()if set(row['candidate_callees'])&closure}
        if following==closure:break
        closure=following
    fk_keys=set()
    for row in catalog['triggers'].values():
        function=row[8].replace('"','').split('(')[0].rsplit('.',1)[-1]
        if row[0]is True and function in('RI_FKey_check_ins','RI_FKey_check_upd')and(
                row[15]in global_relations or row[13]in global_relations):fk_keys.add(row[15]+':'+row[12])
    for key in fk_keys:
        require(key in catalog['constraints']and catalog['constraints'][key][0]=='f','CURRENT_CENSUS_ACTUAL_RI_CONSTRAINT:'+key)
    triggers={name:dict(relation=row[15],function=row[8],internal=row[0],enabled=row[1],
        referenced_relation=row[13],constraint=row[12],full16_row=pin(json.dumps(row,separators=(',',':')).encode()))
        for name,row in catalog['triggers'].items()if row[15]in global_relations or row[13]in global_relations}
    unresolved=[name for name,row in records.items()if row['outer_error']or row['body_error']
        or row['query_errors']or row['dynamic_PL_statements']or row['opaque_language']]
    return dict(status='ACTUAL_OBSERVED_DE2979_INCREMENTAL_SYNTAX_CENSUS_NOT_NATIVE_OR_GLOBAL_ACCEPTANCE',
        retained_accepted15A_source=retained.SOURCE_PIN,retained_syntax_report=OLD_REPORT,
        observed_failed_A861_prefix_source=CURRENT_RAW,overall_failed_run=41361511976,
        observed_prefix_is_NOT_an_accepted_DE30_parent=True,
        original_raw_pair_capture_unavailable=True,
        parser=dict(pglast='7.20',PostgreSQL=[17,7],source=SCANNER,grammar_not_execution=True),
        retained_parser_controls_NOT_rerun=prior['parser_controls'],
        new_reuse_admission_controls=dict(exact_body_reused=True,changed_body_refused=True,
            changed_language_refused=True,forged_full19_row_refused=True),
        functions_scanned=len(records),reused_unchanged_body_facts=len(reused),new_or_changed_bodies_parsed=len(parsed),
        parsed_body_identities=parsed,removed_function_identities=sorted(set(old['functions'])-set(functions)),
        ALL_current_metadata_and_candidate_call_targets_rebuilt=True,
        parsed_expressions_in_new_or_changed_bodies=sum(records[k]['parsed_expressions']for k in parsed),
        unique_new_query_parse_cache_entries=len(parser.cache),
        direct_global_writer_candidates=sorted(direct),transitive_static_known_call_candidates=sorted(closure),
        functions_with_explicit_unresolved_syntax_or_dynamic_or_opaque=unresolved,
        relevant_triggers_and_RI=triggers,relevant_foreign_keys={name:catalog['constraints'][name]for name in sorted(fk_keys)},
        foreign_keys_selected_by_exact_RI_identities_not_SQL_text=True,actual_event_triggers=catalog['event_triggers'],
        global_relations=sorted(global_relations),rights_tables_added=sorted(RIGHTS),
        functions=records,catalog_groups={k:len(v)for k,v in catalog.items()},
        exact_runtime_call_graph_claim=False,operator_cast_RLS_trigger_FK_and_runtime_dispatch_closure=False,
        raw_NULL_ACL_or_OID_inferred=False,permission_and_phantom_barrier_installed=False,
        ERP_imports=0,SQL_executed=0,Native_cases=0,global_writer_or_current_rights_or_phantom_closure=False,
        production_go=False,independent_acceptance=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--prior-report',type=Path,required=True)
    p.add_argument('--old-catalog',type=Path,required=True);p.add_argument('--observed-de',type=Path,required=True)
    p.add_argument('--parser-runtime',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    require(not a.output.exists(),'CURRENT_CENSUS_NEW_OUTPUT_REQUIRED');sys.path.insert(0,str(a.parser_runtime))
    value=extend(a.prior_report.read_bytes(),a.old_catalog.read_bytes(),a.observed_de.read_bytes())
    with a.output.open('x')as stream:json.dump(value,stream,indent=2);stream.write('\n')
    print(json.dumps({k:value[k]for k in('status','functions_scanned','reused_unchanged_body_facts',
        'new_or_changed_bodies_parsed','parsed_expressions_in_new_or_changed_bodies',
        'unique_new_query_parse_cache_entries','removed_function_identities')}))
    print(json.dumps(dict(direct_writer_candidates=len(value['direct_global_writer_candidates']),
        transitive_candidates=len(value['transitive_static_known_call_candidates']),
        explicit_unresolved_functions=len(value['functions_with_explicit_unresolved_syntax_or_dynamic_or_opaque']),
        relevant_triggers=len(value['relevant_triggers_and_RI']),actual_RI_foreign_keys=len(value['relevant_foreign_keys']))))
