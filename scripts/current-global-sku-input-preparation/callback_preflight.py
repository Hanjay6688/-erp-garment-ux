"""Review additional prepared Mandor/Afui callbacks, without a fake catalogue.

Retained actual metadata and the prior SKU/PO source analysis stay distinct.
New functions, tables, foreign keys and triggers come from parsed installation
SQL. This is a lower bound on final inputs, never an accepted input profile.
"""
from collections import defaultdict
from hashlib import sha256
from pathlib import Path
import argparse,ast,importlib.util,json,sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'scripts'))

PINS={
 'actual':(14755737,'80856b7ec2cebf08318a21617091b73c6744161b72bb3be98bcb9ecd2b8109eb'),
 'prior':(592423,'449631b4be097251072fc28f9760c26ebb8f095c1268292e678054ed007ed782'),
 'original_dispatch_inputs.py':(18374,'583a87ba25ed6ebf83b281c435a90336ec8b4031128e68707bdb07edf410846a'),
 'scan_saved_writer_census.py':(13782,'69adaed6494ea81cc93ed304718eda7a94131052a81ae3dbc2c8a6d54b4e045c'),
 'intake_common.py':(6518,'698216cfb4c31e8c93167e1b67f52f0b7532e5906ac8a09584b0a32c728b41e9'),
}


def require(value,message):
    if not value:raise ValueError(message)


def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())


def exact(path,key):
    raw=Path(path).read_bytes();require((len(raw),sha256(raw).hexdigest())==PINS[key],
        'COMPOSITE_CALLBACK_EXACT_INPUT:'+key);return raw


def source_sql(actual):
    from cp7_mandor_shop import native_payment_routes,native_sales_routes,command_guard_routes,native_dispatch,replay_routes
    from cp7_accessory_nonpayable import native_derivation
    product=ROOT/'scripts/cp7_mandor_shop';tree=ast.parse((product/'composition.py').read_text())
    order=[ast.literal_eval(n.value)for n in tree.body if isinstance(n,ast.Assign)
        and any(isinstance(t,ast.Name)and t.id=='ORDER'for t in n.targets)]
    require(len(order)==1 and len(order[0])==9,'COMPOSITE_CALLBACK_ORIGINAL_INSTALL_ORDER')
    facades,_=native_dispatch.derive(actual['functions'])
    changed,_=replay_routes.derive((product/'allocation.sql').read_bytes(),facades)
    texts={str((product/n).relative_to(ROOT)):changed.get(n,(product/n).read_text())for n in order[0]}
    texts['DERIVED_MANDOR_FACADES']=changed['composed_facades_with_native_dispatch.sql']
    for name in ('policy.sql','basis.sql','settings.sql'):
        path=ROOT/'scripts/cp7_accessory_nonpayable'/name;texts[str(path.relative_to(ROOT))]=path.read_text()
    payment,_=native_payment_routes.derive(actual['functions']);sales,_=native_sales_routes.derive(actual['functions'])
    guards,_=command_guard_routes.derive(actual['functions'],payment)
    afui,_=native_derivation.derive(native_derivation.originals())
    native=payment|sales|guards
    require(len(native)==13 and len(afui)==5 and not set(native)&set(afui),'COMPOSITE_CALLBACK_DISTINCT_NATIVE_ADAPTERS')
    return texts,native|afui


def current_source_expectations():
    """Use pinned source references only; do not represent these as live rows."""
    functions={};product=ROOT/'scripts/cp7_mandor_shop'
    for name in ('NATIVE_PAYMENT_OWNER_REFERENCE.json','NATIVE_SALES_COMMAND_REFERENCE.json','COMMAND_GUARD_NATIVE_REFERENCE.json'):
        for signature,row in json.loads((product/name).read_bytes())['functions'].items():
            require(signature not in functions or functions[signature]==row,'COMPOSITE_CALLBACK_REFERENCE_CONFLICT')
            functions[signature]=row
    return source_sql(dict(functions=functions))[0]


def requirements():
    report=json.loads((HERE/'CALLBACK_SOURCE_REVIEW.json').read_bytes())
    require(report.get('status')=='PREPARED_COMPOSITE_CALLBACK_REVIEW_NOT_FINAL_INPUT_PROFILE'
        and report.get('complete_input_review')is False and report.get('actual_final_parent_adopted')is False
        and report.get('focused_callback_source_has_no_unresolved')is True,
        'COMPOSITE_CALLBACK_SOURCE_REVIEW_CANNOT_ADOPT_PARENT')
    require(report['installation_SQL']=={n:pin(t.encode())for n,t in current_source_expectations().items()},
        'COMPOSITE_CALLBACK_CURRENT_INSTALLATION_SQL_CHANGED')
    reviewed=json.loads((HERE/'INPUT_REVIEW_CONTROLS.json').read_bytes())
    require(report['prior_source_review']==dict(bytes=PINS['prior'][0],sha256=PINS['prior'][1])
        ==reviewed['full_source_review'],'COMPOSITE_CALLBACK_CURRENT_SKU_SOURCE_REVIEW_CHANGED')
    names=report['required_relation_lower_bound']
    require(type(names)is list and all(type(n)is str for n in names)and names==sorted(set(names))
        and len(names)==221 and len(report['new_physical_relation_candidates'])==12,
        'COMPOSITE_CALLBACK_EXACT_PREPARED_RELATION_LOWER_BOUND')
    require(set(names)==set(reviewed['physical_relation_candidates'])|set(report['new_physical_relation_candidates']),
        'COMPOSITE_CALLBACK_COMPLETE_CURRENT_SKU_AND_MANDOR_INPUTS_REQUIRED')
    require(len(report['additional_firing_triggers'])==4 and len(report['additional_parent_side_foreign_keys'])==2
        and len(report['new_callback_sources'])==6,'COMPOSITE_CALLBACK_COMPLETE_PREPARED_CALLBACK_SET')
    return report


def require_input_relations(profile):
    """Reject the known incomplete197 and209 profiles before any installer cursor use.

    Passing this lower bound does not certify metadata, privileges, concurrency,
    financial behavior, complete input coverage or the actual accepted parent.
    """
    report=requirements();names=profile.get('relations')if type(profile)is dict else None
    require(type(names)is list and all(type(n)is str for n in names)and names==sorted(set(names)),
        'GLOBAL_COMPOSITE_DISTINCT_SORTED_INPUT_RELATIONS_REQUIRED')
    missing=set(report['required_relation_lower_bound'])-set(names)
    require(not missing,'GLOBAL_COMPOSITE_CALLBACK_INPUT_RELATIONS_MISSING:'+','.join(sorted(missing)))
    return dict(required_relation_lower_bound=221,complete_input_review=False,actual_final_parent_adopted=False)


def declared(parser,texts,typename):
    """Preserve exact statement bytes; parse FKs at both column and table level."""
    functions={};tables={};triggers=[];foreign=[]
    def relation(row):
        require(bool(row.get('schemaname')),'COMPOSITE_CALLBACK_QUALIFIED_DDL_REQUIRED')
        return row['schemaname']+'.'+row['relname']
    def strings(values):return [x['String']['sval']for x in values]
    for filename,text in texts.items():
        raw=text.encode();parsed=json.loads(parser.parser.parse_sql_json(text))
        for item in parsed['stmts']:
            node=item['stmt'];start=item.get('stmt_location',0);length=item.get('stmt_len',0)
            statement=raw[start:start+length if length else None].decode()+';'
            if 'CreateFunctionStmt'in node:
                fn=node['CreateFunctionStmt'];name='.'.join(strings(fn['funcname']))
                args=[x['FunctionParameter']for x in fn.get('parameters',[])]
                signature=name+'('+','.join(typename(a['argType'])for a in args
                    if a.get('mode','FUNC_PARAM_IN')not in('FUNC_PARAM_OUT','FUNC_PARAM_TABLE'))+')'
                options=[x['DefElem']for x in fn['options']]
                language=[x['arg']['String']['sval']for x in options if x['defname']=='language']
                require(signature not in functions and len(language)==1,'COMPOSITE_CALLBACK_UNIQUE_DECLARED_FUNCTION')
                functions[signature]=dict(definition=statement,language=language[0],source=filename)
            if 'CreateStmt'in node:
                table=node['CreateStmt'];name=relation(table['relation']);require(name not in tables,'COMPOSITE_CALLBACK_UNIQUE_TABLE')
                tables[name]=dict(source=filename,statement=pin(statement.encode()))
                for entry in table.get('tableElts',[]):
                    if 'ColumnDef'in entry:
                        column=entry['ColumnDef'];constraints=[(x['Constraint'],[column['colname']])for x in column.get('constraints',[])]
                    elif 'Constraint'in entry:
                        constraint=entry['Constraint'];constraints=[(constraint,strings(constraint.get('fk_attrs',[])))]
                    else:raise ValueError('COMPOSITE_CALLBACK_UNREVIEWED_TABLE_ELEMENT')
                    for constraint,columns in constraints:
                        if constraint['contype']!='CONSTR_FOREIGN':continue
                        foreign.append(dict(child=name,columns=columns,parent=relation(constraint['pktable']),
                            referenced_columns=strings(constraint.get('pk_attrs',[])),
                            update_action=constraint['fk_upd_action'],delete_action=constraint['fk_del_action'],
                            deferrable=constraint.get('deferrable',False),initially_deferred=constraint.get('initdeferred',False),source=filename))
            if 'CreateTrigStmt'in node:
                t=node['CreateTrigStmt'];triggers.append(dict(name=t['trigname'],relation=relation(t['relation']),
                    function='.'.join(strings(t['funcname'])),events=t['events'],timing=t.get('timing',0),
                    deferrable=t.get('deferrable',False),initially_deferred=t.get('initdeferred',False),source=filename))
    return functions,tables,triggers,foreign


def review(actual_path,prior_path,parser_sources,parser_runtime):
    raw=exact(actual_path,'actual');prior_raw=exact(prior_path,'prior')
    for name in ('original_dispatch_inputs.py','scan_saved_writer_census.py','intake_common.py'):exact(Path(parser_sources)/name,name)
    sys.path.insert(0,str(parser_runtime));sys.path.insert(0,str(parser_sources))
    import original_dispatch_inputs as original
    require(Path(original.__file__).resolve()==Path(parser_sources).resolve()/'original_dispatch_inputs.py',
        'COMPOSITE_CALLBACK_EXACT_ORIGINAL_PARSER_PATH')
    parser=original.DispatchParser();actual=original.catalogue(raw);prior=json.loads(prior_raw)
    require(prior['source_projection_has_no_unresolved']is True and prior['actual_final_profile_or_runtime_adopted']is False,
        'COMPOSITE_CALLBACK_RETAINED_SOURCE_ANALYSIS_NOT_RUNTIME')
    texts,native=source_sql(actual);functions,tables,triggers,foreign=declared(parser,texts,original.typename)
    prior_functions=set(prior['selected_function_identities']);writes=set(prior['possible_write_relations'])
    require(not set(native)&prior_functions,'COMPOSITE_CALLBACK_CHANGED_PRIOR_BODY_REQUIRES_NEW_DISPATCH_REVIEW')
    relevant_triggers=[t for t in triggers if t['relation']in writes]
    relevant_foreign=[f for f in foreign if f['parent']in writes]
    known=set(actual['functions'])|set(functions)|prior_functions;by_name=defaultdict(set);simple=defaultdict(set)
    for sig in known:
        stem=sig.split('(')[0];by_name[stem].add(sig);simple[stem.rsplit('.',1)[-1]].add(sig)
    targets=lambda name:by_name.get(name,set())if'.'in name else simple.get(name,set())
    pending=set();records={};old_reused=set();unknown_calls=set();unknown_relations=set();dynamic={};opaque={}
    new_relations={f['child']for f in relevant_foreign};new_writes=set()
    for trigger in relevant_triggers:
        found=targets(trigger['function']);require(bool(found),'COMPOSITE_CALLBACK_MISSING_TRIGGER_FUNCTION');pending.update(found)
    while pending:
        signature=min(pending);pending.remove(signature)
        if signature in records or signature in old_reused:continue
        if signature in prior_functions:old_reused.add(signature);continue
        if signature in functions:source=functions[signature]
        else:
            row=actual['functions'][signature]
            source=dict(definition=native.get(signature,row[0]),language=row[2],source='EXPECTED_NATIVE_ADAPTER'if signature in native else'RETAINED_ACTUAL_FUNCTION')
        # The original parser reads only definition and language. No owner,
        # ACL, actual full19 row or installed catalogue is fabricated here.
        facts=parser.inspect_function([source['definition'],None,source['language']])
        records[signature]=dict(source=source['source'],definition=pin(source['definition'].encode()),language=source['language'],
            **{k:sorted(v)if isinstance(v,set)else v for k,v in facts.items()})
        if facts['dynamic']:dynamic[signature]=facts['dynamic']
        if facts['opaque']:opaque[signature]=source['language']
        for name in facts['calls']:
            found=targets(name)
            if found:pending.update(found-set(records)-old_reused)
            elif'.'in name and not name.startswith('pg_catalog.'):unknown_calls.add(name)
        for name in facts['relations']:
            if name in tables or name in actual['relations']:new_relations.add(name)
            elif'.'not in name:new_relations.update(n for n in set(tables)|set(actual['relations'])if n.rsplit('.',1)[-1]==name)
            elif not name.startswith(('pg_catalog.','information_schema.')):unknown_relations.add(name)
        for _,name in facts['writes']:new_writes.add(name)
    # Writes reached through a new callback need the full actual trigger/FK
    # fixed point. This focused read-only callback review must not claim it.
    added_writes=new_writes-writes
    physical={n for n in new_relations if n in tables or actual['relations'][n][1]in('r','p')}
    added_relations=physical-set(prior['physical_relation_candidates'])
    required=set(prior['physical_relation_candidates'])|physical
    unresolved=bool(dynamic or opaque or unknown_calls or unknown_relations or added_writes)
    return dict(status='PREPARED_COMPOSITE_CALLBACK_REVIEW_NOT_FINAL_INPUT_PROFILE',
        retained_actual25=pin(raw),prior_source_review=pin(prior_raw),installation_SQL={n:pin(t.encode())for n,t in texts.items()},
        declared_functions=len(functions),declared_tables=len(tables),declared_triggers=len(triggers),declared_foreign_keys=len(foreign),
        direct_Native_function_overlap_with_prior_review=[],additional_firing_triggers=relevant_triggers,
        additional_parent_side_foreign_keys=relevant_foreign,new_callback_sources=records,
        exact_prior_source_facts_reused=sorted(old_reused),new_physical_relation_candidates=sorted(added_relations),
        required_relation_lower_bound=sorted(required),unresolved_dynamic=dynamic,unresolved_opaque=opaque,
        unresolved_qualified_calls=sorted(unknown_calls),unresolved_qualified_relations=sorted(unknown_relations),
        new_write_targets_requiring_full_actual_callback_review=sorted(added_writes),
        focused_callback_source_has_no_unresolved=not unresolved,
        metadata_dispatch_RLS_owner_ACL_and_actual_parent_still_require_final_review=True,
        complete_input_review=False,actual_final_parent_adopted=False,actual_SQL_executed=0,actual_Native_cases=0,
        production_go=False,independent_acceptance=False)


if __name__=='__main__':
    args=argparse.ArgumentParser()
    for name in ('actual','prior','parser-sources','parser-runtime','report'):args.add_argument('--'+name,required=True,type=Path)
    a=args.parse_args();result=review(a.actual,a.prior,a.parser_sources,a.parser_runtime)
    with a.report.open('x')as output:json.dump(result,output,indent=2);output.write('\n')
    print(json.dumps({k:result[k]for k in ('status','new_physical_relation_candidates','focused_callback_source_has_no_unresolved')}))
