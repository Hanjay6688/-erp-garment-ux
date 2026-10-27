"""Closed A-only composition: one official check and one consistent report/book view.

Not registered with a default installer. An accepted diagnostic prerequisite
permits qualification, not adoption or an upgrade of existing captures.
"""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import importlib.util,json,os

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
CONTRACT='cp7.current-consistent-single-check-finance.v1'
USED_ERROR='COMBINED_FINANCE_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE'
CAPTURES='cp7_finance_capture.captures'
COLUMN=CAPTURES+':report_book_signature'
CONSTRAINT=CAPTURES+':captures_report_book_signature_check'
SCHEMA='cp7_finance_capture'


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def runtime():
    parent=load('combined_finance_actual_readonly_parent',ROOT/'scripts/current-finance-readonly-integration-qualification/composition.py')
    patch=load('combined_finance_exact_signature_patch',ROOT/'scripts/current-finance-consistent-capture-diagnostic/patch.py')
    single=load('combined_finance_exact_single_check',ROOT/'scripts/current-finance-single-check-diagnostic/single_check.py')
    predecessor,_,_,_=parent.runtime()
    return parent,patch,single,predecessor,predecessor.catalog


def qualification():
    evidence=load('combined_finance_accepted_evidence',HERE/'evidence.py')
    config=json.loads((HERE/'PREREQUISITES.json').read_bytes());binding=evidence.gate(config)
    pins=json.loads((HERE/'DERIVATION.json').read_bytes())
    for path,digest in pins['files'].items():
        assert sha256((ROOT/path).read_bytes()).hexdigest()==digest,'COMBINED_FINANCE_DERIVATION_CHANGED:'+path
    manifests=[]
    for path,key in (('scripts/current-finance-consistent-capture-diagnostic/SOURCE.json','expected_consistency_source_sha256'),
        ('scripts/current-finance-consistency-followup-qualification/SOURCE.json','expected_focused_source_sha256')):
        raw=(ROOT/path).read_bytes()
        assert sha256(raw).hexdigest()==pins[key]
        source=json.loads(raw)
        for name,digest in source['files'].items():
            assert sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
        manifests.append(source)
    assert manifests[1]['parent_source_sha256']==pins['expected_consistency_source_sha256']
    parent,_,_,_,_=runtime()
    directories=[Path(os.environ[config[key]])for key in ('original_directory_variable','focused_directory_variable')]
    proofs=[binding[key]for key in ('retained84','focused')]
    raw=[(directory/proof[name]).read_bytes()for directory,proof in zip(directories,proofs)
        for name in ('name','package_name')]
    retained_evidence=load('combined_retained84_evidence',ROOT/'scripts/current-finance-consistency-followup-qualification/evidence.py')
    return evidence.accepted_components(binding,*raw,*manifests,parent.sources(),retained_evidence)


def sources():
    _,accepted=qualification()
    parent,_,_,_,_=runtime()
    return dict(contract=CONTRACT,predecessor=parent.sources(),accepted_prerequisite=accepted,
        files={name:sha256((HERE/name).read_bytes()).hexdigest()for name in
            ('composition.py','evidence.py','PREREQUISITES.json','DERIVATION.json')},
        exact_derivation=json.loads((HERE/'DERIVATION.json').read_bytes()))


def identities(patch,single):
    replaced={patch.REPORT,patch.UNIT,patch.RESULT,single.reuse.PRIVATE}
    added={patch.HELPER,single.PRIVATE_BLOCKERS,single.PRIVATE_READINESS}
    return replaced,added


def admit_delta(before,after,replaced,added):
    assert set(before)==set(after) and len(before)==22,'COMBINED_FINANCE_ALL22_REQUIRED'
    changed={(g,k)for g in before for k in set(before[g])|set(after[g])if before[g].get(k)!=after[g].get(k)}
    expected={('functions',k)for k in replaced|added}|{('columns',COLUMN),('constraints',CONSTRAINT),('schemas',SCHEMA)}
    assert changed==expected,('COMBINED_FINANCE_UNDECLARED_DELTA',sorted(changed^expected))
    for signature in replaced:
        assert before['functions'][signature][1:]==after['functions'][signature][1:]
    for signature in added:assert signature not in before['functions']
    column=deepcopy(before['columns'][CAPTURES+':book_signature'])
    column[0]='report_book_signature'
    column[1]=1+sum(k.startswith(CAPTURES+':')for k in before['columns'])
    assert after['columns'][COLUMN]==column,'COMBINED_FINANCE_COLUMN_METADATA_CHANGED'
    constraint=after['constraints'][CONSTRAINT]
    assert constraint[:10]==['c',False,False,True,True,0,False,None,None,CAPTURES]
    assert constraint[10]=="CHECK (((report_book_signature IS NULL) OR (report_book_signature ~ '^[0-9a-f]{64}$'::text)))"
    schema=deepcopy(before['schemas'][SCHEMA]);owner=schema[0]
    grant=['cp7_finance_read',owner,'USAGE',False]
    assert grant not in schema[1]
    schema[1]=sorted([*schema[1],grant],key=lambda r:tuple(r))
    assert after['schemas'][SCHEMA]==schema,'COMBINED_FINANCE_SCHEMA_GRANT_CHANGED'


def binding(catalog,prior,proof):
    return catalog.digest(dict(sources=prior['sources'],before=prior['before'],after=prior['after'],proof=proof))


def verify(cur,state):
    parent,patch,single,predecessor,catalog=runtime();catalog._authority(cur)
    replaced,added=identities(patch,single);prior=state['predecessor'];proof=state['predecessor_verified_before_delta']
    if (state['sources']!=sources() or prior['sources']!=parent.sources()
        or state['predecessor_binding_sha256']!=binding(catalog,prior,proof)
        or proof.get('status')!='EXACT_CURRENT_CHOICE_READONLY_FINANCE_ALL22'
        or proof.get('all22_transition_chain_verified')is not True
        or proof.get('substituted_catalog_or_definitions')is not False
        or state['before']!=prior['before']
        or state['preinstall_data_and_sequences']!=prior['preinstall_data_and_sequences']
        or state['preuse_data_and_sequences']!=prior['preuse_data_and_sequences']):
        raise ValueError('COMBINED_FINANCE_ACTUAL_PREDECESSOR_CHANGED')
    admit_delta(prior['after'],state['after'],replaced,added)
    assert catalog._catalog_rows(cur)==state['after'],'COMBINED_FINANCE_ACTUAL_ALL22_CHANGED'
    expected=patch.derived()['changed']|{single.reuse.PRIVATE:single.derived()['snapshot_body']}
    for signature,body in expected.items():
        actual=patch.row(cur,signature);old=state['original_rows'][signature]
        assert actual==state['rows'][signature] and actual[0]==body
        assert actual[1:5]==old[1:5],'COMBINED_FINANCE_EXISTING_AUTHORITY_CHANGED'
    new_bodies={patch.HELPER:(patch.HERE/'book_signature.sql').read_text().split('$book$')[1]}
    new_bodies.update({signature:definition.split('$function$')[1]
        for signature,definition in single.derived()['definitions'].items()})
    for signature in added:
        assert patch.row(cur,signature)==state['rows'][signature]
        owner='cp7_finance_read'if signature==patch.HELPER else'postgres'
        assert state['rows'][signature][0]==new_bodies[signature]
        assert state['rows'][signature][1:4]==('s',True,owner)
        config=['search_path=""','TimeZone=UTC','jit=off']if signature==patch.HELPER else['search_path=""']
        assert state['rows'][signature][4]==config
        assert state['after']['functions'][signature][-1]==[[owner,owner,'EXECUTE',False]]
        for role in ('anon','authenticated','service_role','cp7_capture'):
            assert not cur.execute("select has_function_privilege(%s,%s,'EXECUTE')",(role,signature)).fetchone()[0]
    return dict(contract=CONTRACT,status='EXACT_COMBINED_FINANCE_ALL22',
        actual_predecessor_verified=True,all22_transition_chain_verified=True,
        substituted_catalog_or_definitions=False,new_private_functions=3,
        changed_private_functions=4,new_private_columns=1,internal_schema_usage_grants=1,
        new_public_rpcs=0,Native_money_stock_HPP_definitions_unchanged=True,
        schedules_changed=False,timeout_changed=False,qualification_only=True,
        default_adopted=False,production_go=False)


def install_delta(cur,prior):
    pins=sources();actual,_=qualification()
    parent,patch,single,predecessor,catalog=runtime();parent.disposable(cur)
    replaced,added=identities(patch,single)
    with predecessor.atomic(cur):
        predecessor.predecessor.predecessor._locks(cur)
        proof=parent.verify(cur,prior)
        if catalog._data(cur)!=prior['preuse_data_and_sequences']:
            raise ValueError('COMBINED_FINANCE_UNUSED_PREDECESSOR_REQUIRED')
        old={signature:patch.row(cur,signature)for signature in replaced}
        patch.RUNTIME_BASELINE=next(iter(actual['committed'].values()))['baseline_null_snapshot_counterexample']
        consistency=patch.install_for_rollback(cur,catalog)
        one_check=single.install_for_rollback(cur,catalog)
        assert catalog._data(cur)==prior['preuse_data_and_sequences'],'COMBINED_FINANCE_INSTALL_CHANGED_DATA'
        state=dict(sources=pins,predecessor=prior,predecessor_verified_before_delta=proof,
            predecessor_binding_sha256=binding(catalog,prior,proof),before=prior['before'],
            preinstall_data_and_sequences=prior['preinstall_data_and_sequences'],
            preuse_data_and_sequences=prior['preuse_data_and_sequences'],original_rows=old,
            rows={signature:patch.row(cur,signature)for signature in replaced|added},
            after=catalog._catalog_rows(cur),
            exact_consistency_installation={k:v for k,v in consistency.items()if k not in ('original_catalog','original_data')},
            exact_single_check_installation=one_check)
        verify(cur,state);return state


def install(cur):
    sources();parent,_,_,predecessor,_=runtime();parent.disposable(cur)
    with predecessor.atomic(cur):
        predecessor.predecessor.predecessor._locks(cur)
        return install_delta(cur,parent.install(cur))


def rollback_delta_preuse(cur,state):
    parent,patch,single,predecessor,catalog=runtime()
    _,added=identities(patch,single)
    with predecessor.atomic(cur):
        predecessor.predecessor.predecessor._locks(cur);verify(cur,state);catalog._lock_tables(cur)
        if catalog._data(cur)!=state['preuse_data_and_sequences']:raise ValueError(USED_ERROR)
        for row in state['original_rows'].values():cur.execute(row[5],prepare=False)
        for signature in sorted(added):cur.execute('drop function '+signature+' restrict')
        cur.execute('alter table cp7_finance_capture.captures drop column report_book_signature restrict')
        cur.execute('revoke usage on schema cp7_finance_capture from cp7_finance_read')
        parent.verify(cur,state['predecessor'])
        assert catalog._catalog_rows(cur)==state['predecessor']['after']
        assert catalog._data(cur)==state['preuse_data_and_sequences']
        return dict(status='EXACT_COMBINED_FINANCE_DELTA_PREUSE_INVERSE',all22_installed_parent_equal=True,
            all_rows_and_sequences_equal=True,global_used_guard_before_DDL=True,full_parent_inverse_repeated=False)


def rollback_preuse(cur,state):
    parent,_,_,predecessor,catalog=runtime()
    with predecessor.atomic(cur):
        predecessor.predecessor.predecessor._locks(cur)
        delta=rollback_delta_preuse(cur,state);removed=parent.rollback_preuse(cur,state['predecessor'])
        assert catalog._catalog_rows(cur)==state['before'] and catalog._data(cur)==state['preinstall_data_and_sequences']
        return dict(status='EXACT_COMBINED_FINANCE_PREUSE_INVERSE',delta=delta,predecessor=removed,
            all22_preinstall_equal=True,all_rows_and_sequences_equal=True,global_used_guard_before_DDL=True)
