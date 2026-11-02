"""Read the first successful actual Native DDL original, without ERP imports.

This reader performs no database operation, scenario rerun, runtime admission or
financial acceptance. It reconstructs the complete catalogue delta and inverse
from the original compressed observations and immutable public Git blobs.
"""
from pathlib import Path
from hashlib import sha256
import argparse,gzip,io,json,re,zipfile
from intake_common import GitBytes,exact,fields,json_bytes,pin,require

HEAD='0f93f50a70e45f0dbc6e71fd27ca0815ba598b2d'
TREE='b75edbfb5d4f9bf8c4e65947af30ca259f213869'
RUN=41476731067
JOB=125384144685
ARCHIVE=dict(bytes=9040006,sha256='8975546df0f9863372e2ed7679bffa6ddf73408633a564b32f42e8ab3ea447d0')
REPORT=dict(bytes=127617,sha256='1a4e1df61281408a952113c55404ead674e3e729765b416850981a4704c618f5')
PLAN=dict(bytes=16095,sha256='96ce9eee5c4e12f2669cb1e9636080632a5f84c043e1d01b6c14c1c72a288a40')
MODULE='scripts/cp7_global_nonpo_envelope/'
CHECKS=[
 'ACTUAL_ACCEPTED_FREE_SCHEMA_FULL25_AND_ALL19_REFERENCES_EIGHT_OWNERS_AND73_WORK_COLUMNS',
 'ALL16_FUNCTIONS_THREE_TABLES_SEVEN_TRIGGERS_EIGHT_NATIVE_ADAPTERS_COMPILE_ON_ACTUAL_PARENT_WITH_EXACT_ACLS',
 'GLOBAL_SAVEPOINT_RESTORES_FULL25_AND_ORIGINAL_EIGHT_RAW_IDENTITIES_PARENT_DDL_TRANSACTION_RESTORES_BASELINE25',
]
SCHEMAS={'cp7_global_catalog_fence','cp7_global_nonpo_envelope','cp7_global_nonpo_native_graph'}


def catalogue(value):
    require(type(value)is dict and len(value)==25,'NATIVE_INSTALL_COMPLETE_25_GROUPS')
    result={}
    for group,rows in value.items():
        require(type(rows)is list and all(type(r)is list and len(r)==2 and type(r[0])is str for r in rows),'NATIVE_INSTALL_KEY_VALUE_ROWS:'+group)
        require(rows==sorted(rows,key=lambda r:(r[0],json.dumps(r[1],sort_keys=True,separators=(',',':')))),'NATIVE_INSTALL_SORTED_ROWS:'+group)
        keys=[r[0]for r in rows]
        require(len(set(keys))==len(keys),'NATIVE_INSTALL_NO_DISCARDED_DUPLICATE_KEYS:'+group)
        result[group]=dict(rows)
    return result


def body(definition):
    m=re.search(r'\bAS (\$[a-zA-Z0-9_]*\$)',definition)
    require(m is not None,'NATIVE_INSTALL_FUNCTION_BODY_DELIMITER')
    start=m.end();end=definition.find(m.group(1),start)
    require(end>=start,'NATIVE_INSTALL_FUNCTION_BODY_END')
    return definition[start:end]


def intake(archive,repository,api):
    exact(pin(archive),ARCHIVE,'NATIVE_INSTALL_EXACT_CANONICAL_ARCHIVE')
    run=api['run'];jobs=api['jobs']['jobs'];artifacts=api['artifacts']['artifacts']
    fields(run,dict(id=RUN,head_sha=HEAD,status='completed',conclusion='success'),'NATIVE_INSTALL_TERMINAL_RUN')
    exact(len(jobs),1,'NATIVE_INSTALL_SINGLE_JOB');fields(jobs[0],dict(id=JOB,run_id=RUN,status='completed',conclusion='success'),'NATIVE_INSTALL_TERMINAL_JOB')
    require(all(x['status']=='completed'and x['conclusion']=='success'for x in jobs[0]['steps']),'NATIVE_INSTALL_ALL_JOB_STEPS_SUCCEEDED')
    exact(len(artifacts),1,'NATIVE_INSTALL_SINGLE_CANONICAL_ARTIFACT')
    fields(artifacts[0],dict(id=13159939766,size_in_bytes=ARCHIVE['bytes'],digest='sha256:'+ARCHIVE['sha256'],expired=False),'NATIVE_INSTALL_API_ARTIFACT')
    observations={}
    with zipfile.ZipFile(io.BytesIO(archive))as z,GitBytes(repository,HEAD,TREE)as git:
        require(z.testzip()is None and len(z.namelist())==len(set(z.namelist())),'NATIVE_INSTALL_ARCHIVE_CRC_AND_UNIQUE_MEMBERS')
        def member(name):
            names=[n for n in z.namelist()if Path(n).name==name]
            exact(len(names),1,'NATIVE_INSTALL_SINGLE_ORIGINAL_MEMBER:'+name)
            return z.read(names[0])
        raw=member('GLOBAL_NATIVE_INSTALL_CAPABILITY3.json');exact(pin(raw),REPORT,'NATIVE_INSTALL_ORIGINAL_REPORT_BYTES');v=json_bytes(raw)
        fields(v['source'],dict(head=HEAD,tree=TREE,source_pins=48,unchanged_parent_blobs=14410,actual_business_cases=0,old_financial_cases_NOT_dispatched=True),'NATIVE_INSTALL_ORIGINAL_SOURCE_IDENTITY')
        exact(v['status'],'ACTUAL_SUPABASE17_GLOBAL_FULL_STAGE_DDL_ON_ACCEPTED_NATIVE_PARENT3_PASS_NOT_RUNTIME_OR_FINANCE','NATIVE_INSTALL_ORIGINAL_STATUS')
        exact(v['checks'],[dict(id=x,status='PASS')for x in CHECKS],'NATIVE_INSTALL_THREE_EXACT_CHECKS')
        fields(v,dict(no_Native_table_or_callback_models=True,real_Global_runtime_gate_NEVER_opened=True,profile_rows_seeded=0,
            old_DE30_FREE3_permanent_and_capability_scenarios_NOT_dispatched=True,actual_Native_business_cases=0,
            actual_Auth_HTTP_cases=0,actual_two_session_cases=0,actual_browser_cases=0,
            runtime_profile_and_explicit_unused_inverse_and_financial_qualification_pending=True,
            global_writer_or_permission_or_phantom_closure=False,production_go=False,independent_acceptance=False),'NATIVE_INSTALL_SCOPE_NOT_INFLATED')
        fields(v['accepted_predecessor'],dict(head='91a7b46ed13c4ad6094114871a4a39fa6765d140',tree='01c4807d932af1d534477c4c182715b1378bd39b',run_id=41399754004,job_id=125128803743,retained_cases_rerun=False),'NATIVE_INSTALL_ACCEPTED_FREE_PARENT')
        fields(v['committed_release_DDL_bootstrap'],dict(status='ALL_FILES_INSTALLED',files=30,old_business_scenarios_dispatched=0),'NATIVE_INSTALL_COMPLETE_EXISTING_RELEASE_DDL')
        source=json_bytes(git.read('scripts/current-global-native-install-capability/SOURCE.json'))
        exact(source['parent_head'],'b8c572d28f944ad9a5947ffc164e134558ed6641','NATIVE_INSTALL_COMPLETE_SOURCE_PARENT')
        exact(git.git('rev-parse',source['parent_head']+'^{tree}').decode().strip(),source['parent_tree'],'NATIVE_INSTALL_PARENT_TREE')
        base=git.entries(source['parent_head']);require(all(git.tree.get(n)==row for n,row in base.items()),'NATIVE_INSTALL_EVERY_PARENT_BLOB_AND_MODE_PRESERVED')
        exact(len(base),14410,'NATIVE_INSTALL_PARENT_BLOB_COUNT')
        exact(len(source['files']),48,'NATIVE_INSTALL_EXACT_SOURCE_PIN_COUNT')
        for name,expected in source['files'].items():git.verify_pin(name,expected)
        plan_raw=git.read(MODULE+'INSTALL_PLAN.json');exact(pin(plan_raw),PLAN,'NATIVE_INSTALL_INDEPENDENT_EXACT_PLAN');plan=json_bytes(plan_raw)
        # These two are derived SQL strings, not repository files. Their actual
        # compiled bodies are independently checked against the pinned plan
        # below; every derivation input is covered by the 48 immutable pins.
        derived={'derived_review.sql','derived_lock.sql'}
        exact({n for n in plan['source_sql']if n.startswith('derived_')},derived,'NATIVE_INSTALL_ONLY_TWO_DERIVED_SQL_INPUTS')
        for name,expected in plan['source_sql'].items():
            if name not in derived:git.verify_pin(MODULE+name,expected)
        for name in ['actual_accepted_parent25','compiled_global25','restored_accepted_parent25','before_parent25','after_parent25']:
            expected=v['raw'][name];packed=member(expected['name']);exact(pin(packed),expected['compressed'],'NATIVE_INSTALL_COMPRESSED_ORIGINAL:'+name)
            raw=gzip.decompress(packed);exact(pin(raw),expected['raw'],'NATIVE_INSTALL_UNCOMPRESSED_ORIGINAL:'+name)
            observations[name]=json_bytes(raw)
        before=catalogue(observations['actual_accepted_parent25']);after=catalogue(observations['compiled_global25'])
        exact(observations['restored_accepted_parent25'],observations['actual_accepted_parent25'],'NATIVE_INSTALL_EXACT_FULL25_GLOBAL_ROLLBACK')
        exact(observations['after_parent25'],observations['before_parent25'],'NATIVE_INSTALL_EXACT_FULL25_PARENT_ROLLBACK')
        catalogue(observations['before_parent25'])
        reference=json_bytes(git.read(MODULE+'graph_helpers/AUTHORITY.json'))['actual_source_profile']
        exact(len(reference['functions']),19,'NATIVE_INSTALL_NINETEEN_ACTUAL_REFERENCES')
        for name,row in reference['functions'].items():exact(before['functions'][name],row,'NATIVE_INSTALL_ORIGINAL_FULL19_NATIVE_AUTHORITY:'+name)
        exact(before['relations']['erp.v_current_hpp'],reference['view_relation'],'NATIVE_INSTALL_ORIGINAL_CURRENT_HPP_VIEW')
        work=json_bytes(git.read(MODULE+'NATIVE_SCOPE_WORK_REFERENCE.json'))['columns'];count=0
        for rows in work.values():
            for name,row in rows.items():exact(before['columns'][name],row,'NATIVE_INSTALL_ACTUAL_WORK_COLUMN:'+name);count+=1
        exact(count,73,'NATIVE_INSTALL_ALL73_NATIVE_WORK_COLUMNS')
        routes=v['raw']['eight_counted_routes'];exact(routes['source_routes'],18,'NATIVE_INSTALL_EIGHTEEN_COUNTED_ROUTES')
        exact(set(routes['functions']),set(plan['native_adapter_sources']),'NATIVE_INSTALL_EXACT_EIGHT_ADAPTER_SET')
        for name,route in routes['functions'].items():
            old=before['functions'][name];new=after['functions'][name];text=old[0]
            exact(pin(text.encode()),route['before'],'NATIVE_INSTALL_ORIGINAL_NATIVE_BODY:'+name)
            for change in route['routes']:
                exact(text.count(change['before']),change['count'],'NATIVE_INSTALL_LITERAL_ROUTE_COUNT:'+name)
                text=text.replace(change['before'],change['after'])
            exact(text,new[0],'NATIVE_INSTALL_DERIVED_NATIVE_BODY:'+name)
            exact(pin(text.encode()),plan['native_adapter_sources'][name],'NATIVE_INSTALL_PREPARED_NATIVE_BODY_PIN:'+name)
            exact(new[1:],old[1:],'NATIVE_INSTALL_NATIVE_COMPLETE_OTHER18_ATTRIBUTES:'+name)
        exact(v['raw']['after_eight_native_raw_authorities'],v['raw']['original_eight_native_raw_authorities'],'NATIVE_INSTALL_ACTUAL_RAW_NATIVE_OID_ACL_AND_SCHEMA_AUTHORITY')
        exact(len(v['raw']['original_eight_native_raw_authorities']),8,'NATIVE_INSTALL_ALL_EIGHT_RAW_IDENTITIES')
        changes={}
        for group in before:
            old,new=before[group],after[group]
            require(set(old)<=set(new),'NATIVE_INSTALL_NO_PREEXISTING_OBJECT_REMOVED:'+group)
            changed={n for n in old if old[n]!=new[n]};added=set(new)-set(old)
            exact(changed,set(plan['native_adapter_sources'])if group=='functions'else set(),'NATIVE_INSTALL_ONLY_DECLARED_NATIVE_BODIES_CHANGED:'+group)
            allowed=set()
            if group=='functions':allowed=set(plan['functions'])
            elif group=='relations':allowed=set(plan['tables']+plan['index_relations'])
            elif group=='columns':allowed=set(plan['columns'])
            elif group=='indexes':allowed=set(plan['index_relations'])
            elif group in('types','type_implementation'):allowed=set(plan['types'])
            elif group=='schemas':allowed=SCHEMAS
            elif group in('constraints','triggers'):
                require(all(n.split(':',1)[0]in plan['tables']for n in added),'NATIVE_INSTALL_ONLY_NEW_TABLE_CONSTRAINTS_OR_TRIGGERS')
                exact(len(added),15 if group=='constraints'else 7,'NATIVE_INSTALL_DECLARED_RELATION_OBJECT_COUNT:'+group);allowed=added
            exact(added,allowed,'NATIVE_INSTALL_COMPLETE_EXACT_CATALOGUE_ADDITIONS:'+group)
            if changed or added:changes[group]=dict(added=len(added),changed=len(changed))
        for name,expected in plan['functions'].items():
            row=after['functions'][name];exact(len(row),19,'NATIVE_INSTALL_NEW_FULL19_FUNCTION:'+name)
            exact(sha256(body(row[0]).encode()).hexdigest(),expected['body_sha256'],'NATIVE_INSTALL_NEW_EXACT_FUNCTION_BODY:'+name)
            exact([row[i]for i in [1,2,8,4,7,12]],[expected[k]for k in ['owner','language','volatility','security_definer','returns_set','config']],'NATIVE_INSTALL_NEW_FUNCTION_ATTRIBUTES:'+name)
            acl=[[expected['owner'],expected['owner'],'EXECUTE',False]]
            if expected['owner']=='supabase_admin':acl.append(['postgres','supabase_admin','EXECUTE',False])
            exact(sorted(row[18]),sorted(acl),'NATIVE_INSTALL_NEW_EXACT_PRIVATE_ACL:'+name)
        triggers={n:r for n,r in after['triggers'].items()if n not in before['triggers']}
        custom={n:r for n,r in triggers.items()if r[0]is False}
        exact(set(custom),{t['relation']+':'+t['name']for t in plan['triggers']},'NATIVE_INSTALL_EXACT_CUSTOM_TRIGGER_SET')
        for t in plan['triggers']:
            r=custom[t['relation']+':'+t['name']]
            exact([r[1],r[2],r[6],r[7],r[8]],['O',t['events']|t['timing']|(1 if t['row']else 0),False,False,t['function']+'()'],'NATIVE_INSTALL_ACTUAL_CUSTOM_TRIGGER_AUTHORITY')
        internal=[r for r in triggers.values()if r[0]is True]
        require(len(internal)==4 and all(r[15]in plan['tables']and r[8].split('(')[0].rsplit('.',1)[-1].strip('"').startswith('RI_FKey_')for r in internal),'NATIVE_INSTALL_ONLY_FOUR_DECLARED_INTERNAL_FK_TRIGGERS')
        for name in SCHEMAS:
            owner='supabase_admin'if name=='cp7_global_catalog_fence'else'postgres'
            acl=[[owner,owner,'USAGE',False],[owner,owner,'CREATE',False]]
            if owner=='supabase_admin':acl.append(['postgres',owner,'USAGE',False])
            exact(after['schemas'][name],[owner,sorted(acl)],'NATIVE_INSTALL_NEW_EXACT_SCHEMA_ACL:'+name)
        for name in plan['tables']:
            row=after['relations'][name]
            require(row[0]=='postgres'and row[1]=='r'and row[3]is True and all(x[0:2]==['postgres','postgres']for x in row[12]),'NATIVE_INSTALL_PRIVATE_TABLE_OWNER_RLS_AND_ACL:'+name)
    return dict(status='ROOT_VERIFIED_ACTUAL_NATIVE_GLOBAL_INSTALL3_DDL_ONLY_NOT_RUNTIME_OR_BUSINESS',head=HEAD,tree=TREE,run_id=RUN,job_id=JOB,
        archive=ARCHIVE,original_report=REPORT,install_plan=PLAN,source_pins=48,unchanged_source_parent_blobs=14410,
        actual_Native_parent_schema_used=True,modeled_Native_tables_or_callbacks=False,DDL_controls=3,catalogue_delta=changes,
        exact_full25_stage_and_parent_rollbacks=True,existing_raw_eight_native_authorities_preserved=True,
        actual_business_cases=0,actual_Auth_HTTP_cases=0,actual_two_session_cases=0,actual_browser_cases=0,
        runtime_gate_opened=False,input_profile_seeded=False,explicit_unused_installer_inverse_qualified=False,
        global_dispatch_closure=False,financial_restore_or_full_CP7_credit=False,old_tests_rerun=False,production_go=False,independent_acceptance=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True);p.add_argument('--repository',type=Path,required=True);p.add_argument('--api',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    result=intake(a.archive.read_bytes(),a.repository,json_bytes(a.api.read_bytes()))
    a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
