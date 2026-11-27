"""Qualify the managed Global release above the exact Enteng Uji candidate."""

from hashlib import sha256
import json
import re

from cp7_enteng_global_lock_candidate import capture_catalogue,derive,only_once
from cp7_enteng_managed_credit_release import WORKFLOWS,render as render_staged_migration
from cp7_enteng_managed_wip_batch import alter_owned
from cp7_enteng_managed_ow04_migration import literal_json
from cp7_global_nonpo_envelope import composition as product
from cp7_ow04_restore_bundle import QUERIES


MIGRATION_NAME = 'enteng_uji_cp7_managed_global'
PARENT_CONTRACT = 'cp7.enteng-uji-managed-predecessor.v1'
PLATFORM_SCHEMA = 'cp7_global_catalog_fence'
CATALOGS_SQL = """select coalesce(jsonb_agg(jsonb_build_array(n.nspname,c.relname,c.relkind::text,
    c.relpersistence::text,pg_get_userbyid(c.relowner),c.relrowsecurity,c.relforcerowsecurity,
    case when c.relacl is null then null else to_jsonb(array(
        select a::text from unnest(c.relacl)a order by a::text collate "C"))end)
    order by n.nspname collate "C",c.relname collate "C"),'[]'::jsonb)
from pg_catalog.pg_class c join pg_catalog.pg_namespace n on n.oid=c.relnamespace
where n.nspname='pg_catalog' and c.relkind in('r','p')"""


def source_plan():
    manifest_raw = (product.HERE/'SOURCE.json').read_bytes()
    manifest = json.loads(manifest_raw)
    for name,wanted in manifest['files'].items():
        path = product.ROOT/name
        product.require(path.is_file() and not path.is_symlink() and product.pin(path.read_bytes())==wanted,
                        'Managed Global source differs: '+name)
    reviewed = json.loads((product.HERE/'INSTALL_PLAN.json').read_bytes())
    texts = product.sql_sources()
    product.require(reviewed['source_sql']=={k:product.pin(v.encode()) for k,v in texts.items()},
                    'Managed Global source plan changed')
    texts['derived_lock.sql'], lock_proof = derive()
    # Native PostgreSQL serializes OIDs as decimal JSON strings. Retain raw
    # values in the observation and validate just the paths removed by the hash.
    semantic = texts['semantic_authority.sql']
    for value,scalar in (("p_authority#>'{view,oid}'","p_authority#>>'{view,oid}'"),
                         ("element_.value->'oid'","element_.value->>'oid'")):
        semantic = only_once(semantic,f"jsonb_typeof({value})is distinct from'number'",
                             f"coalesce({scalar},'') !~ '^[1-9][0-9]{{0,9}}$'")
    texts['semantic_authority.sql'] = semantic
    functions = {signature:row for signature,row in reviewed['functions'].items()
                 if not signature.startswith(PLATFORM_SCHEMA+'.')}
    for name,key in (('derived_lock.sql','lock_v1(text)'),('semantic_authority.sql','semantic_authority_v1(jsonb)')):
        signature = 'cp7_global_nonpo_envelope.'+key
        functions[signature] = dict(functions[signature],body_sha256=sha256(texts[name].split('$$')[1].encode()).hexdigest())
    return dict(reviewed,functions=functions),texts,product.pin(manifest_raw),lock_proof


def verify_transition(cur,before,after,definitions,identity,plan):
    old,new = product.all22(before),product.all22(after)
    for group in product.catalogue_profile.EXTRA:
        product.require(after[group]==before[group],'Managed Global changed '+group)
    for group,rows in old.items():
        for key,row in rows.items():
            expected = [definitions[key],*row[1:]] if group=='functions' and key in definitions else row
            product.require(new[group].get(key)==expected,'Managed Global changed undeclared object: '+group+' '+key)
    declared = {
        'schemas':set(product.SCHEMAS[:2]), 'functions':set(plan['functions']),
        'relations':set(plan['tables']+plan['index_relations']), 'columns':set(plan['columns']),
        'indexes':set(plan['index_relations']), 'types':set(plan['types']), 'type_implementation':set(plan['types']),
    }
    for group,rows in new.items():
        added = set(rows)-old[group].keys()
        if group in ('triggers','constraints'):
            product.require(all(key.split(':',1)[0] in plan['tables'] for key in added),
                            'Managed Global added an undeclared '+group)
            product.require(len(added)==(plan['constraint_count'] if group=='constraints' else
                            len(plan['triggers'])+4*plan['foreign_key_count']), 'Managed Global trigger or constraint count differs')
        else:
            product.require(added==declared.get(group,set()),'Managed Global added unexpected objects in '+group)
    product.require(product.native_identity(cur,definitions)==identity,'Managed Global changed native identity or raw ACL')
    for signature,wanted in plan['functions'].items():
        row = cur.execute("""select encode(sha256(convert_to(p.prosrc,'UTF8')),'hex'),
            pg_get_userbyid(p.proowner),l.lanname,p.provolatile::text,p.prosecdef,p.proretset,p.proconfig
            from pg_proc p join pg_language l on l.oid=p.prolang where p.oid=%s::regprocedure""",(signature,)).fetchone()
        keys = ('body_sha256','owner','language','volatility','security_definer','returns_set','config')
        product.require(row and list(row)==[wanted[key] for key in keys] and
                        new['functions'][signature][18]==[['postgres','postgres','EXECUTE',False]],
                        'Managed Global private function authority differs: '+signature)
    for table in plan['tables']:
        row = new['relations'][table]
        product.require(row[0]=='postgres' and row[3] and all(x[:2]==['postgres','postgres'] for x in row[12]),
                        'Managed Global private table authority differs: '+table)
    for schema in product.SCHEMAS[:2]:
        row = new['schemas'][schema]
        product.require(row[0]=='postgres' and {tuple(x) for x in row[1]}==
                        {('postgres','postgres','USAGE',False),('postgres','postgres','CREATE',False)},
                        'Managed Global private schema authority differs: '+schema)


def profile_sql(parent,manifest,relations,expected_authority):
    # The full catalogue is specific to the current hosted database. Seal it
    # only in the same guarded transaction that verified the release package.
    root_pin = product.pin(json.dumps(parent,sort_keys=True,separators=(',',':')).encode())
    root = dict(contract='cp7.global-parent-and-catalogue-profile.v1',accepted_parent=dict(parent,root_receipt_pin=root_pin),
                module_manifest=manifest,managed_enteng_uji=True,production_go=False)
    product.require(re.fullmatch('[a-f0-9]{64}',expected_authority), 'Managed Global native authority SHA is required')
    return f"""do $enteng_global_profile$
declare catalogue jsonb;native jsonb;native_sha text;catalogs jsonb;root jsonb;relations jsonb;profile_id text;
begin
    perform cp7_global_release_guard.enter_release();
    if exists(select from pg_locks where locktype='transactionid' and mode='ExclusiveLock'
              and granted and pid is distinct from pg_backend_pid()) then
        raise exception using errcode='55P03',message='CP7_GLOBAL_PREEXISTING_TRANSACTION_REVIEW_AGAIN';
    end if;
    catalogue := cp7_global_nonpo_envelope.catalogue_fingerprint_v1();
    native := cp7_global_nonpo_envelope.semantic_authority_v1(cp7_global_nonpo_native_graph.authority_v1());
    native_sha := encode(sha256(convert_to(native::text,'UTF8')),'hex');
    if native->'known_functions_exact' is distinct from 'true'::jsonb
       or native->'new_private_acl_closed' is distinct from 'true'::jsonb
       or native#>'{{view,exact_known_source}}' is distinct from 'true'::jsonb
       or native_sha is distinct from '{expected_authority}' then
        raise exception 'CP7_GLOBAL_MANAGED_REVIEWED_AUTHORITY_DIFFERS';
    end if;
    catalogs := ({CATALOGS_SQL});
    relations := {literal_json(relations)};
    root := {literal_json(root)} || jsonb_build_object('catalogue_fingerprint',catalogue);
    profile_id := encode(sha256(convert_to(jsonb_build_array(root,native_sha,relations,catalogs)::text,'UTF8')),'hex');
    insert into cp7_global_nonpo_envelope.profiles
        (id,parent_head,parent_tree,actual_parent_root_receipt,expected_catalogs,expected_relations,native_authority_sha256)
        values(profile_id,'{parent['head']}','{parent['tree']}',root,catalogs,relations,native_sha);
    perform cp7_global_nonpo_envelope.lock_v1(profile_id);
end $enteng_global_profile$"""


def apply(cur,parent):
    """Build and seal a locally qualified candidate with no change to the original admission."""
    product.require(parent.get('contract')==PARENT_CONTRACT and parent.get('production_go') is False
                    and parent.get('independent_acceptance') is False and parent.get('environment')=='Enteng Uji',
                    'Managed Global requires an Enteng Uji Writer A predecessor receipt')
    product.require(all(re.fullmatch(r'[0-9a-f]{40}',parent.get(key,'')) for key in ('head','tree')),
                    'Managed Global requires exact code identities')
    product.require(cur.execute("select current_user,session_user,current_setting('is_superuser')").fetchone()
                    ==('postgres','postgres','off'),'Managed Global requires the normal project role')
    prior = cur.execute("""select count(*), (array_agg(name order by version desc))[1],
         (select encode(sha256(convert_to(statements[1],'UTF8')),'hex')
            from supabase_migrations.schema_migrations where name=%s and cardinality(statements)=1)
        from supabase_migrations.schema_migrations""",(WORKFLOWS,)).fetchone()
    product.require(prior==(152,WORKFLOWS,parent.get('previous_migration_sha256')), 'Managed Global predecessor receipt differs')
    plan,texts,manifest,lock_proof = source_plan()
    with product.metadata_context(cur):
        cur.execute('select cp7_global_release_guard.enter_release(),cp7_credit.assert_source_native_trigger_census_v1()')
        before = capture_catalogue(cur)
        current = product.all22(before)
        product.require(not any(name in current['schemas'] for name in product.SCHEMAS),
                        'Managed Global refuses an existing Global installation')
        product.readonly_graph.compare_current(current)
        definitions,route_proof = product.native_hooks.derive({name:current['functions'].get(name)
            for name in product.native_hooks.originals()})
        product.require(plan['native_adapter_sources']=={k:product.pin(v.encode()) for k,v in definitions.items()},
                        'Managed Global owning source differs')
        expected_columns = {key:row for columns in json.loads(
            (product.HERE/'NATIVE_SCOPE_WORK_REFERENCE.json').read_bytes())['columns'].values() for key,row in columns.items()}
        # Match the reviewed source while ignoring only PostgreSQL's internal
        # pg_attver counter. The runtime full25 fingerprint still retains it.
        portable_columns = dict(cur.execute('select k,v from ('+QUERIES['columns']+') q(k,v) where k=any(%s)',
                                            (list(expected_columns),)).fetchall())
        product.require(portable_columns==expected_columns,'Managed Global native column differs')
        identity = product.native_identity(cur,definitions)
        cur.execute('create schema cp7_global_nonpo_native_graph authorization postgres')
        for name in product.CORE_ORDER:
            cur.execute(texts[name],prepare=False)
        product.normalize_private(cur,plan)
        for signature,statement in definitions.items():
            row = identity[signature]
            if row[6]:
                cur.execute(statement,prepare=False)
            else:
                alter_owned(cur,signature,(row[2],row[4]),statement)
        after = capture_catalogue(cur)
        verify_transition(cur,before,after,definitions,identity,plan)
        fingerprint = product.fingerprint(cur,after)
        product.require(cur.execute('select cp7_global_nonpo_envelope.catalogue_fingerprint_v1()').fetchone()[0]==fingerprint,
                        'Managed Global independent all25 fingerprint differs')
        needed = json.loads((product.HERE/'SYNTAX_AND_SOURCE_CONTROLS.json').read_bytes())['required_actual_accepted15a_relation_keys']
        relations = product.relation_metadata(cur,sorted(set(needed)|set(plan['tables'])))
        auth,preimage = cur.execute("""select a,a::text from (select cp7_global_nonpo_envelope.semantic_authority_v1(
             cp7_global_nonpo_native_graph.authority_v1()) a) inp""").fetchone()
        product.require(auth['known_functions_exact'] and auth['known_function_count']==19 and
                        auth['new_private_acl_closed'] and auth['view']['exact_known_source'],
                        'Managed Global financial authority differs')
        authority_sha = sha256(preimage.encode()).hexdigest()
        cur.execute(profile_sql(parent,manifest,relations,authority_sha),prepare=False)
        profile_id = cur.execute('select cp7_global_nonpo_envelope.selected_profile_v1()').fetchone()[0]
        lock = cur.execute('select cp7_global_nonpo_envelope.lock_v1(%s)',(profile_id,)).fetchone()[0]
        cur.execute('select cp7_credit.assert_source_native_trigger_census_v1(),cp7_global_release_guard.assert_ddl_fence()')
        return dict(profile_id=profile_id,financial_routines_verified=19,catalogue=fingerprint,lock=lock,
                    native_adapters=len(definitions),native_routes=route_proof['source_routes'],reviewed_lock=lock_proof,
                    private_routines=len(plan['functions']),production_go=False,independent_acceptance=False)


def render(previous_sha,scope_before,scope_after,catalogue_before,statements):
    product.require(catalogue_before.get('contract')=='cp7.global-catalogue-fingerprint.v1' and
                    catalogue_before.get('groups')==25 and len(catalogue_before.get('counts',{}))==25,
                    'Managed Global release requires a full target catalogue receipt')
    query = (product.HERE/'catalogue_fingerprint.sql').read_text().split('$catalogue$')[1]
    admission = f"""do $enteng_full25_before$
declare fingerprint jsonb;prior_path text:=current_setting('search_path');prior_zone text:=current_setting('TimeZone');
begin
    perform set_config('search_path','',true);
    perform set_config('TimeZone','UTC',true);
    select q.f into strict fingerprint from ({query}) q(f);
    if fingerprint is distinct from {literal_json(catalogue_before)} then
        raise exception 'CP7_GLOBAL_MANAGED_TARGET_CATALOGUE_CHANGED';
    end if;
    perform set_config('search_path',prior_path,true);
    perform set_config('TimeZone',prior_zone,true);
end $enteng_full25_before$;
"""
    return render_staged_migration(WORKFLOWS,previous_sha,152,scope_before,scope_after,admission+statements)
