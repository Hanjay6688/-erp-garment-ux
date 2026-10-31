"""Pure P0 selector controls; no database, network, or ERP runtime."""
from copy import deepcopy
from pathlib import Path
import argparse,importlib.util,json

HERE=Path(__file__).resolve().parent


def check():
    spec=importlib.util.spec_from_file_location('DE_P0_dependency_target',HERE/'p0_dependencies.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    declaration=json.loads((HERE/'P0_DEPENDENCIES.json').read_bytes())
    functions=[]
    for index,(signature,item)in enumerate(declaration['functions'].items(),1):
        functions.append(dict(oid=index,proowner=100,signature=signature,schema=item['schema'],
            prokind='f',prosecdef=item['security_definer'],provolatile=item['volatility'],proacl=None,
            source_sha256=str(index)*64))
    relations=[]
    for index,(name,item)in enumerate(declaration['relations'].items(),20):
        relations.append(dict(oid=index,relowner=100,schema=item['schema'],relname=item['name'],
            relkind=item['kind'],relpersistence=item['persistence'],relacl=None))
    base=dict(classification='ACTUAL_READ_ONLY_ALL_NAMESPACE_SYSTEM_CRON_METADATA_NOT_WRITER_CLOSURE',
        database='cp6_rollback',primary_scheduler_database=False,groups={
        'routines':{'rows':functions},'relations':{'rows':relations},
        'roles':{'rows':[dict(oid=100,rolname='postgres',rolsuper=True,rolinherit=True)]}})
    selected=module.select(base,declaration);negative=[]
    def refusal(label,change):
        changed=deepcopy(base);change(changed)
        try:module.select(changed,declaration)
        except (ValueError,KeyError,TypeError):negative.append(label)
        else:raise AssertionError('P0_INVALID_MODEL_ACCEPTED:'+label)
    refusal('missing-function',lambda x:x['groups']['routines']['rows'].pop())
    refusal('duplicate-function',lambda x:x['groups']['routines']['rows'].append(deepcopy(x['groups']['routines']['rows'][0])))
    refusal('wrong-function-schema',lambda x:x['groups']['routines']['rows'][0].update(schema='public'))
    refusal('wrong-function-kind',lambda x:x['groups']['routines']['rows'][0].update(prokind='p'))
    refusal('wrong-security-mode',lambda x:x['groups']['routines']['rows'][0].update(prosecdef=False))
    refusal('wrong-volatility',lambda x:x['groups']['routines']['rows'][0].update(provolatile='v'))
    refusal('boolean-function-oid',lambda x:x['groups']['routines']['rows'][0].update(oid=True))
    refusal('missing-relation',lambda x:x['groups']['relations']['rows'].pop())
    refusal('duplicate-relation',lambda x:x['groups']['relations']['rows'].append(deepcopy(x['groups']['relations']['rows'][0])))
    refusal('wrong-relation-kind',lambda x:x['groups']['relations']['rows'][0].update(relkind='v'))
    refusal('temporary-relation',lambda x:x['groups']['relations']['rows'][0].update(relpersistence='t'))
    refusal('missing-owner',lambda x:x['groups']['roles']['rows'].clear())
    refusal('empty-owner-name',lambda x:x['groups']['roles']['rows'][0].update(rolname=''))
    captured=module.capture(base)
    assert captured['selected']==selected and captured['identity_is_not_authority']is True
    return dict(status='PASS_P0_IDENTITY_SELECTION_NOT_AUTHORITY_OR_LOCK_CLOSURE',
        positive_controls=1,negative_controls=negative,functions=len(selected['functions']),
        relations=len(selected['relations']),owner_roles=len(selected['owner_roles']),
        full_rows_retained=True,actual_SQL_executed=0,actual_ERP_calls=0,
        actual_Native_case_credit=0,production_go=False,independent_acceptance=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    result=check();a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status=result['status'],positive=1,negative=len(result['negative_controls']),
        actual_ERP_calls=0)))
