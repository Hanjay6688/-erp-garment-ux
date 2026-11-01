"""Compare Native32 preparation with saved actual metadata, without ERP work.

This is an early compatibility check on 17 procedure attributes. It does not
replace actual full19 installation checks, qualify a failed run, or establish
current permissions, writer closure, or concurrency safety.
"""
from copy import deepcopy
from decimal import Decimal
from hashlib import file_digest,sha256
from pathlib import Path
import argparse,json,re,zipfile

from intake_common import GitBytes,exact,pin,require,safe_path
from intake_sku27 import strict
import intake_complete_de30 as de

MAIN='CP7_PERMANENT_S05_S03_SKU_NATIVE4_BROWSER2.json'
COMPONENT='PERMANENT_S05_S03_SKU_NATIVE4_BROWSER2'


def typed(expected,actual,label):
    require(type(expected)is type(actual),'SAVED_NATIVE_METADATA_TYPE:'+label)
    exact(actual,expected,'SAVED_NATIVE_METADATA_VALUE:'+label)


def indexed(rows,key):
    result={}
    for row in rows:
        identity=row[key]
        require(type(identity)is str and identity not in result,'SAVED_NATIVE_METADATA_DUPLICATE_IDENTITY:'+key)
        result[identity]=row
    return result


def definition_body(definition,signature):
    require(type(definition)is str and definition.startswith(
        'CREATE OR REPLACE FUNCTION '+signature.split('(',1)[0]+'('),'SAVED_NATIVE_EXPECTED_FUNCTION_DEFINITION')
    token='AS $function$'
    exact(definition.count(token),1,'SAVED_NATIVE_EXACT_FUNCTION_BODY_DELIMITER')
    start=definition.index(token)+len(token);end=definition.rindex('$function$')
    require(end>start and definition[end+len('$function$'):]== '\n','SAVED_NATIVE_EXACT_FUNCTION_BODY_END')
    return definition[start:end].encode()


def config_digest(values):
    if values is None:return sha256(b'<SQL-NULL>').hexdigest()
    require(type(values)is list and all(type(v)is str for v in values),'SAVED_NATIVE_CONFIG_TEXT_ARRAY_REQUIRED')
    # Pinned qualification runtime's text-array serializer; no connection.
    from psycopg.types.array import ListDumper
    return sha256(bytes(ListDumper(list).dump(values))).hexdigest()


def acl_rows(acl,owner):
    if acl is None:return sorted([['PUBLIC',owner,'EXECUTE',False],[owner,owner,'EXECUTE',False]])
    require(type(acl)is list,'SAVED_NATIVE_EXACT_EXECUTE_ACL_ARRAY')
    result=[]
    for item in acl:
        require(type(item)is str,'SAVED_NATIVE_EXECUTE_ACL_TEXT_REQUIRED')
        match=re.fullmatch(r'([a-zA-Z_][a-zA-Z_0-9]*|)=(X\*?)/([a-zA-Z_][a-zA-Z_0-9]*)',item)
        require(match is not None,'SAVED_NATIVE_UNSUPPORTED_EXECUTE_ACL_REFUSED')
        grantee,right,grantor=match.groups()
        result.append([grantee or'PUBLIC',grantor,'EXECUTE',right.endswith('*')])
    return sorted(result)


def numeric(value):
    require(type(value)in(str,int,float),'SAVED_NATIVE_FINITE_NUMERIC_ATTRIBUTE_REQUIRED')
    result=Decimal(str(value));require(result.is_finite(),'SAVED_NATIVE_NONFINITE_ATTRIBUTE_REFUSED')
    return result


def validate(expected,snapshot):
    typed('ACTUAL_READ_ONLY_ALL_NAMESPACE_SYSTEM_CRON_METADATA_NOT_WRITER_CLOSURE',snapshot['classification'],'classification')
    typed('cp6_rollback',snapshot['database'],'database');typed(0,snapshot['Native_cases'],'Native_cases')
    groups=snapshot['groups']
    for key in('roles','languages','routines'):typed('CAPTURED',groups[key]['status'],key+':status')
    roles={k:v['rolname']for k,v in indexed(groups['roles']['rows'],'oid').items()}
    languages={k:v['lanname']for k,v in indexed(groups['languages']['rows'],'oid').items()}
    actual=indexed(groups['routines']['rows'],'signature');typed(32,len(expected),'expected32')
    require(set(expected)<=set(actual),'SAVED_NATIVE_EVERY_EXPECTED_PROCEDURE_REQUIRED')
    receipts={}
    for name,want in expected.items():
        require(type(want)is list and len(want)==19,'SAVED_NATIVE_ORIGINAL_FULL19_CAPTURE_REQUIRED')
        row=actual[name];body_sha=sha256(definition_body(want[0],name)).hexdigest()
        require(row['proowner']in roles and row['prolang']in languages,'SAVED_NATIVE_OWNER_AND_LANGUAGE_OID_REQUIRED')
        fields=dict(source_body=(body_sha,row['source_sha256']),owner=(want[1],roles[row['proowner']]),
            language=(want[2],languages[row['prolang']]),kind=(want[3],row['prokind']),
            security_definer=(want[4],row['prosecdef']),strict=(want[5],row['proisstrict']),
            leakproof=(want[6],row['proleakproof']),returns_set=(want[7],row['proretset']),
            volatility=(want[8],row['provolatile']),parallel=(want[9],row['proparallel']),
            cost=(numeric(want[10]),numeric(row['procost'])),rows=(numeric(want[11]),numeric(row['prorows'])),
            configuration=(config_digest(want[12]),row['config_sha256']),
            argument_names=(want[13],row['proargnames']),argument_modes=(want[14],row['proargmodes']),
            support=(want[17],row['prosupport']),execute_ACL=(sorted(want[18]),acl_rows(row['proacl'],want[1])))
        typed(17,len(fields),'matched_attribute_count')
        for key,(before,after)in fields.items():typed(before,after,name+':'+key)
        receipts[name]=dict(actual_oid=row['oid'],source_body_sha256=body_sha,matched_fields=list(fields),
            actual_argument_defaults=row['pronargdefaults'],full19_not_claimed=True)
    return dict(status='SAVED_ACTUAL_METADATA_NATIVE32_ATTRIBUTE_PREFLIGHT_PASS',routines=receipts,
        functions=32,attributes_per_function=17,actual_ERP_cases=0,full19_and_installation_still_required=True,
        global_writer_or_permission_or_lock_closure=False,production_go=False,independent_acceptance=False)


def negative_controls(expected,snapshot):
    name=next(iter(expected));negative=[]
    for mode in('body','boolean_type','execute_ACL','configuration','missing_procedure','duplicate_procedure'):
        changed=deepcopy(snapshot);rows=changed['groups']['routines']['rows']
        row=next(r for r in rows if r['signature']==name)
        if mode=='body':row['source_sha256']='0'*64
        elif mode=='boolean_type':row['prosecdef']=int(row['prosecdef'])
        elif mode=='execute_ACL':row['proacl']=['=X/'+expected[name][1]]
        elif mode=='configuration':row['config_sha256']='0'*64
        elif mode=='missing_procedure':rows.remove(row)
        else:rows.append(deepcopy(row))
        try:validate(expected,changed)
        except ValueError as error:negative.append(dict(mode=mode,refused=str(error)))
        else:raise AssertionError('SAVED_NATIVE_CORRUPT_OBSERVATION_ACCEPTED:'+mode)
    return dict(positive=1,negative=negative,DB_connections=0,actual_ERP_cases=0)


def archive_snapshot(path,metadata):
    run=metadata['run'];artifact=metadata['artifact'];jobs=metadata['jobs']
    typed('completed',run['status'],'terminal_run');typed(1,run['run_attempt'],'run_attempt')
    require(run['conclusion']in('success','failure'),'SAVED_NATIVE_TERMINAL_RUN_CONCLUSION')
    typed(False,artifact['expired'],'unexpired_canonical');typed(1,len(jobs),'one_actual_job')
    typed(run['id'],jobs[0]['run_id'],'job_run');typed('completed',jobs[0]['status'],'terminal_job')
    typed(run['conclusion'],jobs[0]['conclusion'],'job_conclusion')
    typed(run['id'],artifact['workflow_run']['id'],'artifact_run')
    typed(run['head_sha'],artifact['workflow_run']['head_sha'],'artifact_head')
    path=Path(path);typed(artifact['size_in_bytes'],path.stat().st_size,'canonical_size')
    with path.open('rb')as stream:typed(artifact['digest'],'sha256:'+file_digest(stream,'sha256').hexdigest(),'canonical_digest')
    with zipfile.ZipFile(path)as archive:
        names=archive.namelist();typed(len(names),len(set(names)),'unique_canonical_paths')
        for name in names:safe_path(name)
        require(archive.testzip()is None,'SAVED_NATIVE_FULL_CANONICAL_CRC')
        main=strict(archive.read(MAIN));typed(run['head_sha'],main['qualification_commit'],'actual_report_head')
        observation=main['committed'][COMPONENT]['read_only_system_metadata_before_native']
        typed(27,observation['source']['query_count'],'original_readonly_queries')
        typed(dict(bytes=1726,sha256='7a1d1b6d930abc96918df8fb35f96ac2a4dd3905c7e230d848c5d4f528b80c47'),
            observation['source']['manifest'],'original_readonly_source_manifest')
        return observation['snapshots']['candidate'],dict(head=run['head_sha'],run_id=run['id'],
            job_id=jobs[0]['id'],conclusion=run['conclusion'],artifact_id=artifact['id'],
            archive=dict(bytes=artifact['size_in_bytes'],digest=artifact['digest'],members=len(names)),
            failed_run_not_relabelled_PASS=True,business_case_credit=0)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--de-source',type=Path,required=True)
    parser.add_argument('--de-head',required=True);parser.add_argument('--de-tree',required=True)
    parser.add_argument('--archive',type=Path,required=True);parser.add_argument('--api-metadata',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--negative-controls',action='store_true')
    args=parser.parse_args();metadata=strict(args.api_metadata.read_bytes())
    with GitBytes(args.de_source,args.de_head,args.de_tree)as git:
        source=de.source(git);raw=git.read(de.PRODUCT+'RECORDED_NATIVE_CAPTURES.json')
        expected=strict(raw)['functions']
    snapshot,identity=archive_snapshot(args.archive,metadata);result=validate(expected,snapshot)
    result.update(actual_metadata_original=identity,expected_prepared_source=dict(head=args.de_head,tree=args.de_tree,
        manifest=source['source_manifest'],recorded_capture=pin(raw)),actual_snapshot=snapshot['snapshot'])
    if args.negative_controls:result['explicit_corruption_controls']=negative_controls(expected,snapshot)
    with args.output.open('x')as output:output.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps({key:result[key]for key in('status','functions','attributes_per_function','actual_ERP_cases')}))


if __name__=='__main__':main()
