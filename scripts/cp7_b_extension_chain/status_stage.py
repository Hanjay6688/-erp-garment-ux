"""Counted OW16 installation/inverse; unchanged B SQL and verifier.

Admit only the new private objects, three facades and the eight explicitly
declared schema/function/column grants. No Native function body changes.
"""
from hashlib import sha256
from pathlib import Path
import cp7_ow16_status_install as owner
import cp7_ow04_restore_bundle as catalog

ROOT=Path(__file__).resolve().parents[2]
SCHEMA='cp7_cutting_status'
PINS={'scripts/cp7_ow16_status_install.py':'5cf9ea58750c37f1cf5e320926d8ec9a72a7b9407dfcf152e1dc8df65b804be9',
      'scripts/cp7-src/cutting-yield/automatic-status.sql':'45cf0b428fbe6b85d7e18367492ef188e7ac49d06f120e39156b66e9cf758d4f'}
SCHEMA_GRANTS=('cp7_wip','cp7_planning')
FUNCTION_GRANTS=('cp7_wip.fields(jsonb,text[])','cp7_planning.utc(timestamp with time zone)')
COLUMN_GRANTS=('erp.materials:id','erp.materials:material_name','erp.sizes:id','erp.sizes:sort_order')
FUNCTIONS=set(owner.PRIVATE)|set(owner.PUBLIC)


def sources():
    for path,digest in PINS.items():
        if sha256((ROOT/path).read_bytes()).hexdigest()!=digest:
            raise ValueError('OW15_OW16_SOURCE_CHANGED: '+path)
    return dict(owner=PINS,adapter=sha256(Path(__file__).read_bytes()).hexdigest())


def declared(group,key):
    if group=='schemas':return key==SCHEMA
    if group=='functions':return key in FUNCTIONS
    return group in('relations','columns','constraints','indexes','triggers','types','type_implementation','policies')and key.startswith(SCHEMA+'.')


def own_catalog(value):
    return {g:{k:v for k,v in rows.items()if declared(g,k)}for g,rows in value.items()}


def acl_delta(group,key,old,new,before):
    if old is None or new is None:return False
    if (group=='schemas'and key in SCHEMA_GRANTS)or(group=='functions'and key in FUNCTION_GRANTS):
        privilege='USAGE'if group=='schemas'else'EXECUTE'
        grantor=old[0 if group=='schemas'else 1]
        return old[:-1]==new[:-1]and {tuple(x)for x in new[-1]}=={tuple(x)for x in old[-1]}|{('cp7_policy',grantor,privilege,False)}
    if group=='columns'and key in COLUMN_GRANTS:
        grantor=before['relations'][key.split(':')[0]][0]
        return old[:12]==new[:12]and old[13:]==new[13:]and set(new[12]or[])==set(old[12]or[])|{'cp7_capture=r/'+grantor}
    return False


def admit_catalog(before,after,state):
    if set(before)!=set(after)or len(before)!=22:raise ValueError('OW15_OW16_CATALOG_GROUPS_CHANGED')
    for group in before:
        for key in set(before[group])|set(after[group]):
            old,new=before[group].get(key),after[group].get(key)
            if old==new:continue
            if old is None and new is not None and declared(group,key)and new==state['new_catalog'][group].get(key):continue
            if acl_delta(group,key,old,new,before):continue
            raise ValueError('OW15_OW16_UNDECLARED_DELTA: '+group+':'+key)


def verify(cur,state):
    if sources()!=state['sources']:raise ValueError('OW15_OW16_SOURCE_CHANGED')
    proof=owner.verify(cur)
    current=catalog._catalog_rows(cur)
    if own_catalog(current)!=state['new_catalog']:raise ValueError('OW15_OW16_PRIVATE_CATALOG_CHANGED')
    new=state['new_catalog']
    if set(new['schemas'])!={SCHEMA}or set(new['functions'])!=FUNCTIONS:
        raise ValueError('OW15_OW16_FUNCTION_SET_CHANGED')
    indexes={SCHEMA+'.'+name for name in('policies_pkey','policies_revision_key','policies_actor_request_id_key','requests_pkey')}
    if set(new['indexes'])!=indexes or set(new['relations'])!=indexes|{SCHEMA+'.policies',SCHEMA+'.requests'}:
        raise ValueError('OW15_OW16_RELATION_SET_CHANGED')
    if len(new['triggers'])!=4 or len(new['types'])!=4 or len(new['policies'])!=3:
        raise ValueError('OW15_OW16_PRIVATE_OBJECT_COUNT_CHANGED')
    for group,keys in(('schemas',SCHEMA_GRANTS),('functions',FUNCTION_GRANTS),('columns',COLUMN_GRANTS)):
        for key in keys:
            if current[group][key]!=state['after'][group][key]:raise ValueError('OW15_OW16_DECLARED_GRANT_CHANGED: '+key)
    return dict(owner=proof,all22_delta_admitted=True,existing_function_bodies_unchanged=True,production_go=False)


def install_delta(cur):
    pins=sources();before=catalog._catalog_rows(cur)
    if SCHEMA in before['schemas']or FUNCTIONS&set(before['functions']):raise ValueError('OW15_OW16_ALREADY_INSTALLED')
    cur.execute(owner.extension(),prepare=False)
    after=catalog._catalog_rows(cur)
    state=dict(sources=pins,before=before,after=after,new_catalog=own_catalog(after))
    admit_catalog(before,after,state);verify(cur,state)
    return state


def rollback_preuse(cur,state):
    verify(cur,state)
    if cur.execute('select exists(select 1 from cp7_cutting_status.policies)or exists(select 1 from cp7_cutting_status.requests)').fetchone()[0]:
        raise ValueError('OW15_OW16_AFTER_USE_REQUIRES_BACKUP_RESTORE')
    before=state['before']
    for signature in owner.PUBLIC:cur.execute('drop function '+signature)
    cur.execute('drop schema cp7_cutting_status cascade')
    # Only remove privileges this exact stage added. Existing grants survive.
    for group,keys,kind,privilege in(('schemas',SCHEMA_GRANTS,'schema','USAGE'),('functions',FUNCTION_GRANTS,'function','EXECUTE')):
        for key in keys:
            if before[group][key]==state['after'][group][key]:continue
            grantor=before[group][key][0 if group=='schemas'else 1]
            if ['cp7_policy',grantor,privilege,False]not in before[group][key][-1]:
                cur.execute('revoke '+privilege+' on '+kind+' '+key+' from cp7_policy')
    for key in COLUMN_GRANTS:
        if before['columns'][key]==state['after']['columns'][key]:continue
        table,column=key.split(':');grantor=before['relations'][table][0]
        if 'cp7_capture=r/'+grantor not in(before['columns'][key][12]or[]):
            cur.execute('revoke select('+column+') on '+table+' from cp7_capture')
    if catalog._catalog_rows(cur)!=before:raise ValueError('OW15_OW16_PREUSE_NOT_EXACT_ALL22')
