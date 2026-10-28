"""Source and fail-closed transition checks; never a database qualification."""
from pathlib import Path
from hashlib import sha256
from copy import deepcopy
from unittest.mock import patch
import argparse,json,sys

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--parent-admission',required=True);parser.add_argument('--out',required=True)
    args=parser.parse_args();sys.argv=sys.argv[:1]
    repo=Path(__file__).resolve().parents[2];sys.path.insert(0,str(repo/'scripts'))
    import psycopg
    def no_database(*a,**kw):raise AssertionError('PREFLIGHT_MUST_NOT_CONNECT_DATABASE')
    psycopg.connect=no_database
    from pglast import parse_sql
    from cp7_current_choice_preparation import installation as product
    from cp7_current_choice_preparation import hooks
    parent=Path(args.parent_admission).read_bytes();prior=json.loads(parent)
    sources=product.sources()
    assert prior['current_installation']==sources['predecessor']
    assert prior['qualification']['contract']=='cp7.d17-18.progress-native5-qualification.v1'
    assert prior['actual_parent_verified']['status']=='PASS'
    # Reconstruct each old hook by reversing only the newly introduced calls.
    definitions=hooks.definitions();originals=hooks.originals()
    for body in definitions.values():assert len(parse_sql(body))==1
    runner=definitions[hooks.RUNNER].replace('create or replace function ','create function ',1)
    runner=runner.replace("  union all select 'CHOICE_PREPARATION',min(updated_at)from cp7_frozen_choice_preparation.work where state='QUEUED'\n",'',1)
    runner=runner.replace("when 'CHOICE_PREPARATION'then cp7_frozen_choice_preparation.run_next()||jsonb_build_object('family','CHOICE_PREPARATION')",'',1)
    assert runner==originals[hooks.RUNNER]
    retention=definitions[hooks.RETENTION].replace('create or replace function ','create function ',1)
    retention=retention.replace("'choice_preparation_payloads',cp7_frozen_choice_preparation.purge_expired(200),",'',1)
    assert retention==originals[hooks.RETENTION]
    assert "limit_ms not between 1 and 8000"in runner and "'FINANCE',min(updated_at)"in runner
    assert 'cp7_analysis_stage.purge_expired(200)'in retention
    negative=[]
    for marker in ("  union all select 'FINANCE',min(updated_at)from cp7_finance_capture.captures where state='RUNNING'\n",
                   "when 'FINANCE'then cp7_finance_capture.run_next()else"):
        altered={**originals,hooks.RUNNER:originals[hooks.RUNNER].replace(marker,'REMOVED',1)}
        with patch.object(hooks,'originals',return_value=altered):
            try:hooks.definitions()
            except ValueError:negative.append('MISSING_FINANCE_ANCHOR_REFUSED')
            else:raise AssertionError('FINANCE_DISPATCH_REMOVAL_ACCEPTED')
    # A controlled catalog isolates the boundary guard, not SQL execution.
    before={g:{}for g in ['schemas','functions','relations']+[f'controlled_{n}'for n in range(19)]}
    before['functions']['erp.official()']=['official','owner','v']
    after=deepcopy(before);sig=next(iter(product.PUBLIC));after['functions'][sig]=['new','cp7_capture','v'];after['schemas'][product.readers.SCHEMA]=['cp7_capture']
    state=dict(catalog=product.readers.own(after),rows={sig:['new']})
    product.admit_delta(product.readers,before,after,state)
    for label,mutate in [
        ('OFFICIAL_FUNCTION_REPLACEMENT',lambda d:d['functions'].__setitem__('erp.official()',['modified','owner','v'])),
        ('UNDECLARED_PUBLIC_RPC',lambda d:d['functions'].__setitem__('public.undeclared()',['new','cp7_capture','v'])),
        ('UNDECLARED_BUSINESS_TABLE',lambda d:d['relations'].__setitem__('erp.money',['table'])),
        ('MISSING_DECLARED_FUNCTION',lambda d:d['functions'].pop(sig)),
    ]:
        changed=deepcopy(after);mutate(changed)
        try:product.admit_delta(product.readers,before,changed,state)
        except ValueError:negative.append(label+'_REFUSED')
        else:raise AssertionError('CATALOG_MUTATION_ACCEPTED:'+label)
    prior_data={'erp.balance':[1,'unchanged'],'sequence:erp.nota':[12,True]}
    product._data_transition('PREPARATION',prior_data,{**prior_data,**product.EMPTY_WORK})
    for label,changed in [
        ('CHANGED_BALANCE',{**prior_data,**product.EMPTY_WORK,'erp.balance':[0,'changed']}),
        ('CHANGED_SEQUENCE',{**prior_data,**product.EMPTY_WORK,'sequence:erp.nota':[13,True]}),
        ('PREPOPULATED_WORK',{**prior_data,product.preparation.SCHEMA+'.work':[1,'changed']}),
    ]:
        try:product._data_transition('PREPARATION',prior_data,changed)
        except ValueError:negative.append(label+'_REFUSED')
        else:raise AssertionError('INSTALLATION_DATA_MUTATION_ACCEPTED:'+label)
    result=dict(status='PASS_LOCAL_SOURCE_AND_GUARDS_ONLY',B_head=sources['B_source']['head'],B_files=len(sources['B_source']['files']),
        parent_admission_sha256=sha256(parent).hexdigest(),parent_sources_exact=True,public_registry=product.PUBLIC,
        hooks_reverse_to_exact_parents=True,finance_dispatch_retained=True,unit_limits_unchanged=True,
        controlled_negative_checks=negative,actual_database=False,Python_installer_runtime=False,
        actual_Auth_HTTP_credit=False,factory_qualified=False,full_final_acceptance=False,production_go=False)
    Path(args.out).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k]for k in ('status','B_files','actual_database','Python_installer_runtime','production_go')}|{'controlled_negative_checks':len(negative)}))

if __name__=='__main__':main()
