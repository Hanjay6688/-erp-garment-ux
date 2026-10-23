"""Private initial-analysis delta. A supplies transaction, envelope and release."""
from hashlib import sha256
from pathlib import Path
import json
import re
from cp7_production_stage import _row,_body
from cp7_ow04_restore_bundle import _catalog_rows
from . import patches

ROOT=Path(__file__).resolve().parent
SCHEMA='cp7_initial_analysis'
TABLE=SCHEMA+'.intents'
FUNCTIONS={SCHEMA+'.readiness(jsonb)':(False,'i'),SCHEMA+'.semantic_hash(jsonb,jsonb)':(False,'i'),
           SCHEMA+'.current(boolean)':(False,'v'),SCHEMA+'.tick()':(True,'v')}
MANIFEST=json.loads((ROOT/'MANIFEST.json').read_text())


def sources():
    return {p.name:sha256(p.read_bytes()).hexdigest()for p in ROOT.iterdir()if p.is_file()and p.suffix in('.py','.sql','.json')}


def _declared(group,key):
    if group=='schemas':return key==SCHEMA
    if group=='triggers'and key.startswith('cp7_analysis_stage.jobs:'+TABLE+':intents_job_id_fkey:'):
        return True
    return group in('relations','columns','constraints','indexes','triggers','functions','types','type_implementation','policies')and key.startswith(SCHEMA+'.')


def _new_catalog(catalog):
    return {group:{k:v for k,v in rows.items()if _declared(group,k)}for group,rows in catalog.items()}


def verify(cur,state):
    if sources()!=state['sources']or sha256((ROOT/'initial.sql').read_bytes()).hexdigest()!=MANIFEST['sql_sha256']:
        raise ValueError('OW13A_SOURCE_CHANGED')
    for sig in patches.SIGNATURES:
        row=_row(cur,sig)
        if row[0]!=state['definitions'][sig]or row[2:]!=state['originals'][sig][2:]:
            raise ValueError('OW13A_HOOK_OR_AUTHORITY_CHANGED: '+sig)
    definitions=dict(re.findall(r'create function (cp7_initial_analysis\.[a-z_]+)\([^;]*?\).*?as \$\$(.*?)\$\$;',
                                (ROOT/'initial.sql').read_text(),re.S))
    if set(definitions)!={sig.split('(')[0]for sig in FUNCTIONS}:
        raise ValueError('OW13A_PRIVATE_BODY_SET_CHANGED')
    for sig,(definer,volatility)in FUNCTIONS.items():
        row=_row(cur,sig)
        if row[1]!=definitions[sig.split('(')[0]]or row[2:6]!=['cp7_capture',definer,volatility,['search_path=""','TimeZone=UTC']]:
            raise ValueError('OW13A_PRIVATE_AUTHORITY_CHANGED: '+sig)
        for role in ('anon','authenticated','service_role','cp7_alert'):
            allowed=role=='cp7_alert'and sig==SCHEMA+'.tick()'
            if cur.execute("select has_function_privilege(%s,%s,'EXECUTE')",(role,sig)).fetchone()[0]!=allowed:
                raise ValueError('OW13A_PRIVATE_FUNCTION_EXPOSED: '+sig+':'+role)
    owner,rls=cur.execute('select pg_get_userbyid(relowner),relrowsecurity from pg_class where oid=%s::regclass',(TABLE,)).fetchone()
    if owner!='cp7_capture'or rls is not True:
        raise ValueError('OW13A_PRIVATE_TABLE_AUTHORITY_CHANGED')
    for role in ('anon','authenticated','service_role','cp7_alert'):
        if cur.execute("select has_table_privilege(%s,%s,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')",(role,TABLE)).fetchone()[0]:
            raise ValueError('OW13A_PRIVATE_TABLE_EXPOSED: '+role)
        if role!='cp7_alert'and cur.execute("select has_schema_privilege(%s,%s,'USAGE')",(role,SCHEMA)).fetchone()[0]:
            raise ValueError('OW13A_PRIVATE_SCHEMA_EXPOSED: '+role)
    catalog=_new_catalog(_catalog_rows(cur))
    if catalog!=state['new_catalog']or set(catalog['functions'])!=set(FUNCTIONS):
        raise ValueError('OW13A_PRIVATE_CATALOG_CHANGED')
    indexes={SCHEMA+'.'+name for name in('intents_pkey','intents_request_id_key','intents_job_id_key')}
    constraints={TABLE+':'+name for name in('intents_pkey','intents_request_id_key','intents_job_id_key',
                 'intents_job_id_fkey','intents_semantic_hash_check')}
    # PG18 records each NOT NULL as a pg_constraint row; PG17 records the
    # same six restrictions in pg_attribute. Admit the exact version's set.
    server_major=cur.execute("select current_setting('server_version_num')::integer/10000").fetchone()[0]
    if server_major>=18:
        constraints|={TABLE+':intents_'+column+'_not_null'for column in
                      ('actor','request_id','job_id','query','semantic_hash','recorded_at')}
    if set(catalog['relations'])!={TABLE}|indexes or set(catalog['indexes'])!=indexes or set(catalog['constraints'])!=constraints \
       or set(catalog['policies'])!={TABLE+':initial_no_access'}or len(catalog['types'])!=2:
        raise ValueError('OW13A_PRIVATE_OBJECT_SET_CHANGED: '+json.dumps({g:sorted(catalog[g])for g in('relations','indexes','constraints','policies','types')}))
    schema=catalog['schemas'].get(SCHEMA)
    if schema is None or schema[0]!='cp7_capture':raise ValueError('OW13A_SCHEMA_OWNER_CHANGED')
    for group,entries in (('schemas',{SCHEMA:schema}),('functions',catalog['functions']),('relations',catalog['relations'])):
        for key,row in entries.items():
            allowed={'cp7_capture','cp7_alert'}if(group=='schemas'or key==SCHEMA+'.tick()')else{'cp7_capture'}
            for grant in row[-1]:
                if grant[0]not in allowed or grant[1]!='cp7_capture'or grant[3]is not False:
                    raise ValueError('OW13A_UNDECLARED_PRIVATE_GRANT: '+group+':'+key)
                if grant[0]=='cp7_alert'and grant[2]!=('USAGE'if group=='schemas'else'EXECUTE'):
                    raise ValueError('OW13A_UNDECLARED_TICK_PRIVILEGE: '+group+':'+key)
    return dict(stage='cp7.initial-analysis.v1',initial_once_per_actor=True,new_public_rpcs=0,
                financial_capture='DEFERRED',full_A_chain_qualified=False,production_go=False)


def install_delta(cur):
    if cur.execute('select to_regnamespace(%s)is not null',(SCHEMA,)).fetchone()[0]:
        raise ValueError('OW13A_ALREADY_INSTALLED')
    if sha256((ROOT/'initial.sql').read_bytes()).hexdigest()!=MANIFEST['sql_sha256']:
        raise ValueError('OW13A_SOURCE_CHANGED')
    before=_catalog_rows(cur)
    originals={sig:_row(cur,sig)for sig in patches.SIGNATURES}
    for sig,row in originals.items():
        if sha256(row[1].encode()).hexdigest()not in MANIFEST['before_bodies'][sig]:
            raise ValueError('OW13A_PREDECESSOR_CHANGED: '+sig)
    definitions=patches.patched({sig:row[0]for sig,row in originals.items()})
    cur.execute((ROOT/'initial.sql').read_text(),prepare=False)
    for definition in definitions.values():cur.execute(definition,prepare=False)
    after=_catalog_rows(cur)
    state=dict(sources=sources(),originals=originals,
               definitions={sig:_row(cur,sig)[0]for sig in patches.SIGNATURES},new_catalog=_new_catalog(after))
    admit_catalog(before,after,state);verify(cur,state)
    return state


def admit_catalog(before,after,state):
    if set(before)!=set(after)or len(before)!=22:
        raise ValueError('OW13A_CATALOG_GROUPS_CHANGED')
    for group in before:
        for key in set(before[group])|set(after[group]):
            old,new=before[group].get(key),after[group].get(key)
            if old==new:continue
            if group=='functions'and key in patches.SIGNATURES and old is not None and new is not None:
                if old[0]==state['originals'][key][0]and new[0]==state['definitions'][key]and old[1:]==new[1:]:continue
            if old is None and new is not None and _declared(group,key)and new==state['new_catalog'][group].get(key):continue
            raise ValueError('OW13A_UNDECLARED_CATALOG_DELTA: '+group+':'+key)


def rollback_preuse(cur,state):
    verify(cur,state)
    if cur.execute('select exists(select 1 from cp7_initial_analysis.intents)').fetchone()[0]:
        raise ValueError('OW13A_AFTER_USE_REQUIRES_BACKUP_RESTORE')
    for sig in reversed(patches.SIGNATURES):cur.execute(state['originals'][sig][0],prepare=False)
    cur.execute('drop schema cp7_initial_analysis cascade',prepare=False)
    for sig,row in state['originals'].items():
        if _row(cur,sig)!=row:raise ValueError('OW13A_HOOK_NOT_RESTORED: '+sig)
