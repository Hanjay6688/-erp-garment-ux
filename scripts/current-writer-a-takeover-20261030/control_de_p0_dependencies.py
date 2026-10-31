"""Root P0 dependency intake controls using immutable prepared source only."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import argparse,json
import intake_complete_de30 as target
from intake_common import GitBytes,exact,pin


def check(root):
    with GitBytes(root,target.PREPARED_HEAD,target.PREPARED_TREE)as g:
        source=target.source(g);declaration,_=target.p0_dependency_sources(g)
        functions=[]
        for index,(signature,item)in enumerate(declaration['functions'].items(),1):
            functions.append(dict(oid=index,proowner=100,signature=signature,schema=item['schema'],
                prokind='f',prosecdef=item['security_definer'],provolatile=item['volatility'],
                proacl=None,source_sha256=str(index)*64))
        relations=[]
        for index,(name,item)in enumerate(declaration['relations'].items(),20):
            relations.append(dict(oid=index,relowner=100,schema=item['schema'],relname=item['name'],
                relkind=item['kind'],relpersistence=item['persistence'],relacl=None))
        row=dict(classification='ACTUAL_READ_ONLY_ALL_NAMESPACE_SYSTEM_CRON_METADATA_NOT_WRITER_CLOSURE',
            database='cp6_rollback',primary_scheduler_database=False,
            groups={'routines':{'rows':functions},'relations':{'rows':relations},
                'roles':{'rows':[dict(oid=100,rolname='postgres',rolsuper=True)]}})
        selected=target.p0_dependency_sources(g)[1](row,declaration)
        value=dict(classification=declaration['classification'],selected=selected,
            declaration_sha256=sha256(g.read(target.NS+'P0_DEPENDENCIES.json')).hexdigest(),
            same_original_readonly_snapshot=True,original_27_groups_rewritten=False,
            unresolved=declaration['unresolved'],identity_is_not_authority=True,
            identity_is_not_reachability=True,identity_is_not_lock_closure=True,
            writer_closure=False,permission_closure=False,lockset_approved=False,
            actual_Native_case_credit=0,production_go=False,independent_acceptance=False)
        row['P0_dependency_supplement']=value
        accepted=target.p0_dependency_observation(g,row);negative=[]
        primary=dict(database='postgres',primary_scheduler_database=True)
        exact(target.p0_dependency_observation(g,primary),
            dict(status='NOT_APPLICABLE_PRIMARY_SCHEDULER_DATABASE',actual_Native_case_credit=0),
            'PRIMARY_DOES_NOT_REQUIRE_INSTALLED_ERP_FUNCTIONS')
        for label,bad in [('primary-claiming-candidate-P0',dict(primary,P0_dependency_supplement=value)),
                          ('primary-marker-wrong-database',dict(primary,database='cp6_rollback'))]:
            try:target.p0_dependency_observation(g,bad)
            except ValueError:negative.append(label)
            else:raise AssertionError('ROOT_ACCEPTED_WRONG_DATABASE_SCOPE:'+label)
        changes=[
            ('missing-supplement',lambda r:r.pop('P0_dependency_supplement')),
            ('missing-function-row',lambda r:r['groups']['routines']['rows'].pop()),
            ('duplicate-function-row',lambda r:r['groups']['routines']['rows'].append(deepcopy(r['groups']['routines']['rows'][0]))),
            ('changed-function-contract',lambda r:r['groups']['routines']['rows'][0].update(provolatile='v')),
            ('missing-relation-row',lambda r:r['groups']['relations']['rows'].pop()),
            ('temporary-relation',lambda r:r['groups']['relations']['rows'][0].update(relpersistence='t')),
            ('missing-owner-row',lambda r:r['groups']['roles']['rows'].clear()),
            ('forged-selected-row',lambda r:r['P0_dependency_supplement']['selected']['functions'].pop(next(iter(r['P0_dependency_supplement']['selected']['functions'])))),
            ('changed-declaration',lambda r:r['P0_dependency_supplement'].update(declaration_sha256='0'*64)),
            ('invented-authority',lambda r:r['P0_dependency_supplement'].update(identity_is_not_authority=False)),
            ('invented-lock-closure',lambda r:r['P0_dependency_supplement'].update(lockset_approved=True)),
            ('hidden-unresolved',lambda r:r['P0_dependency_supplement'].update(unresolved=[])),
        ]
        for label,change in changes:
            changed=deepcopy(row);change(changed)
            try:target.p0_dependency_observation(g,changed)
            except (ValueError,KeyError,TypeError):negative.append(label)
            else:raise AssertionError('ROOT_ACCEPTED_INVALID_P0_DEPENDENCY:'+label)
    exact([target.HEAD,target.TREE,target.RUN,target.JOB,target.PARENT_HEAD,target.PARENT_TREE],[None]*6,
        'DE30_ACTUAL_IDS_STILL_UNARMED')
    try:target.intake('/does-not-exist','/does-not-exist',{})
    except ValueError as error:
        exact(str(error),'DE30_ACTUAL_QUALIFIED_PARENT_AND_OWNING_RUN_NOT_YET_PINNED','UNARMED_BEFORE_IO')
    else:raise AssertionError('UNARMED_DE30_INTAKE_OPENED')
    return dict(status='ROOT_P0_DEPENDENCY_IDENTITY_CONTROLS_PASS',head=target.PREPARED_HEAD,
        tree=target.PREPARED_TREE,source=source,positive=1,negative_controls=negative,
        accepted=accepted,primary_scope_control=True,full_rows_retained=True,unarmed_before_archive_or_Git=True,
        actual_SQL_executed=0,actual_ERP_calls=0,actual_Native_case_credit=0,
        production_go=False,independent_acceptance=False,
        root_intake_source=pin(Path(target.__file__).read_bytes()))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args();result=check(a.source)
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status=result['status'],own_paths=result['source']['own_paths'],
        positive=1,negative=len(result['negative_controls']),actual_ERP_calls=0)))
