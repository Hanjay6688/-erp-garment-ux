"""Seven reversible authority substitutions; no Native or financial SQL edits."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import importlib.util
import json
import os

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('actual19_capture_recipe',HERE/'capture.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
NS='scripts/current-global-nonpo-actual19-profile-qualification/'
FIELDS=('owner','language','kind','security_definer','leakproof','strict','returns_set','volatility',
        'parallel','cost','rows','config','argument_names','argument_modes','arguments','result','support','expanded_acl')


def literal(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).replace("'","''")


def authority(captured):
    old=json.loads(c.frozen(c.PRODUCT+'AUTHORITY.json'));value=deepcopy(old);parser=c.source_module()
    if len(captured['functions'])!=19 or set(captured['functions'])!=set(old['known_functions']):
        raise ValueError('ACTUAL19_EXACT_KNOWN_FUNCTION_KEYS_REQUIRED')
    if captured['runtime_entry']is not None or captured['actual_Native_credit']!=0:
        raise ValueError('ACTUAL19_SOURCE_CAPTURE_CANNOT_OPEN_RUNTIME')
    changed=[]
    for name,row in captured['functions'].items():
        pin=old['known_functions'][name]
        observed=dict(owner=row[1],language=row[2],security_definer=row[4],returns_set=row[7],volatility=row[8],config=row[12])
        if any(observed[k]!=pin[k]for k in observed):raise ValueError('ACTUAL19_PRIOR_KNOWN_METADATA_CHANGED:'+name)
        body,definition=parser.function_text(row[0],name.split('(')[0]);digest=sha256(body.encode()).hexdigest()
        if digest!=pin['prosrc_sha256']:
            changed.append(name)
            source_body,definition=parser.function_text((HERE/'ACTUAL_NATIVE_AUTHORITY.sql').read_text(),name.split('(')[0])
            if source_body!=body:raise ValueError('ACTUAL19_CAPTURED_BODY_CHANGED_IN_STATEMENT_ENCODING')
            value['known_functions'][name]=dict(pin,source_kind='ACTUAL_MIDNIGHT_SOURCE_CAPTURE_NOT_FINAL_COMPOSITE_ACCEPTANCE',
                source=NS+'ACTUAL_NATIVE_AUTHORITY.sql',prosrc_sha256=digest,source_function_sha256=sha256(definition.encode()).hexdigest())
    if set(changed)!=set(c.CHANGED):raise ValueError('ACTUAL19_EXACT_TWO_EXPECTED_SOURCE_TRANSITIONS_REQUIRED')
    if sha256(captured['view_relation'][9].strip().encode()).hexdigest()!='9eb6fa12ee2b72085c6941fe00003f7da643b6fc98ebcd27ca12cc4220dee170':
        raise ValueError('ACTUAL19_KNOWN_VIEW_BODY_CHANGED')
    value['actual_source_profile']=dict(classification='FINITE_ACTUAL_CATALOG_PROFILE_NOT_RUNTIME_ACCEPTANCE',
        observed_head=captured['observed_head'],run_id=captured['run_id'],artifact_id=captured['artifact_id'],
        report=captured['report'],catalogue_observations=captured['catalogue_observations'],
        function_row_fields=['pg_get_functiondef',*FIELDS],functions=captured['functions'],view_relation=captured['view_relation'],
        raw_acl_observed=False,raw_NULL_vs_explicit_acl_inferred=False,
        final_composite_accepted=False,runtime_entry=None,writer_or_phantom_lock_closed=False,actual_Native_credit=0)
    return old,value


def acl(column,owner,kind):
    return "(select coalesce(jsonb_agg(jsonb_build_array(case when a.grantee=0 then 'PUBLIC'else pg_get_userbyid(a.grantee)end,pg_get_userbyid(a.grantor),a.privilege_type,a.is_grantable)order by a.grantee::regrole::text,a.grantor::regrole::text,a.privilege_type,a.is_grantable),'[]'::jsonb)from aclexplode(coalesce("+column+",acldefault('"+kind+"',"+owner+")))a)"


def function_row():
    return 'jsonb_build_array(pg_get_functiondef(p.oid),pg_get_userbyid(p.proowner),l.lanname,p.prokind,p.prosecdef,p.proleakproof,p.proisstrict,p.proretset,p.provolatile,p.proparallel,p.procost::text,p.prorows::text,p.proconfig,p.proargnames,p.proargmodes,pg_get_function_arguments(p.oid),pg_get_function_result(p.oid),p.prosupport::regprocedure::text,'+acl('p.proacl','p.proowner','f')+')'


def view_row():
    return "jsonb_build_array(pg_get_userbyid(c.relowner),c.relkind,c.relpersistence,c.relrowsecurity,c.relforcerowsecurity,c.relispartition,c.relreplident,c.reloptions,c.relispopulated,pg_get_viewdef(c.oid,false),pg_get_partkeydef(c.oid),pg_get_expr(c.relpartbound,c.oid),"+acl('c.relacl','c.relowner','r')+')'


def sql(old,current):
    original=c.frozen(c.PRODUCT+'authority.sql').decode();profile=current['actual_source_profile'];observed=function_row()
    replacements=[
        (literal(old['known_functions']),literal(current['known_functions'])),
        (' observed as(select e.signature,e.pin,p.oid,',
         " captured as(select key signature,value expected_row from jsonb_each('"+literal(profile['functions'])+"'::jsonb)),\n observed as(select e.signature,e.pin,p.oid,"),
        ('p.proacl::text raw_acl,p.proconfig,',
         'p.proacl::text raw_acl,p.proconfig,\n   '+observed+' actual_catalog_row,\n   '+observed+'=captured.expected_row exact_captured_profile,'),
        ('left join pg_roles r on r.oid=p.proowner),',
         'left join pg_roles r on r.oid=p.proowner\n  left join captured on captured.signature=e.signature),'),
        ('bool_and(exact_known_source)from observed','bool_and(exact_known_source and coalesce(exact_captured_profile,false))from observed'),
        ("pg_get_viewdef(c.oid,false) definition from pg_class c where c.oid=to_regclass('erp.v_current_hpp')",
         "pg_get_viewdef(c.oid,false) definition,"+view_row()+" actual_catalog_row from pg_class c where c.oid=to_regclass('erp.v_current_hpp')"),
        ("and owner='postgres'and'security_invoker=true'=any(reloptions))from v)",
         "and owner='postgres'and'security_invoker=true'=any(reloptions)and actual_catalog_row='"+literal(profile['view_relation'])+"'::jsonb)from v)"),
    ]
    text=original;steps=[]
    for before,after in replacements:
        if before==after or text.count(before)!=1:raise ValueError('ACTUAL19_EXACT_SQL_ANCHOR_REQUIRED:'+before[:90])
        text=text.replace(before,after,1);steps.append(dict(before=before,after=after,count=1))
    restored=text
    for step in reversed(steps):
        if restored.count(step['after'])!=1:raise ValueError('ACTUAL19_SQL_REVERSE_ANCHOR_NOT_UNIQUE')
        restored=restored.replace(step['after'],step['before'],1)
    if restored!=original:raise ValueError('ACTUAL19_SQL_REVERSE_NOT_BYTE_EXACT')
    return text.encode(),dict(original=c.pin(original.encode()),current=c.pin(text.encode()),
        counted_reversible_substitutions=7,steps=steps)


def source_proof():
    original=c.frozen(c.PRODUCT+'source.py').decode()
    before="native=(qualifier/'retained/Native_authority.sql').read_text()"
    after="native=(qualifier.parent/'current-global-nonpo-actual19-profile-qualification/ACTUAL_NATIVE_AUTHORITY.sql').read_text()"
    if original.count(before)!=1:raise ValueError('ACTUAL19_ONE_PRIVATE_SOURCE_PROOF_ROUTE_REQUIRED')
    value=original.replace(before,after,1)
    if value.replace(after,before,1)!=original:raise ValueError('ACTUAL19_SOURCE_PROOF_REVERSE_FAILED')
    return value,dict(original=c.pin(original.encode()),current=c.pin(value.encode()),count=1,
        before=before,after=after,product_source_file_unchanged=True,qualification_private_source_read_only=True)


def bundle():
    captured=json.loads((HERE/'CAPTURE.json').read_bytes());old,current=authority(captured)
    native,two=c.native_inputs(captured)
    if native!=(HERE/'ACTUAL_NATIVE_AUTHORITY.sql').read_bytes()or two!=(HERE/'ACTUAL_TWO_FUNCTIONS.sql').read_bytes():
        raise ValueError('ACTUAL19_CAPTURED_TWO_AND_RETAINED_NATIVE_SOURCE_NOT_EXACT')
    body,proof=sql(old,current);_,route=source_proof()
    return current,body,dict(base=c.BASE,authority_sql=proof,source_proof_route=route,
        changed_known_entries=list(c.CHANGED),other_known_entries_unchanged=17,Native_runtime_source_changes=0)


def write():
    if os.environ.get('CI')or os.environ.get('GITHUB_ACTIONS')=='true':raise ValueError('ACTUAL19_DERIVE_WRITER_FORBIDDEN_IN_CI')
    current,body,proof=bundle()
    (c.ROOT/c.PRODUCT/'AUTHORITY.json').write_text(json.dumps(current,indent=2,ensure_ascii=False)+'\n')
    (c.ROOT/c.PRODUCT/'authority.sql').write_bytes(body)
    (HERE/'DERIVATIONS.json').write_text(json.dumps(proof,indent=2,ensure_ascii=False)+'\n')
    return dict(status='EXACT_ACTUAL19_SOURCE_PROFILE_PREPARED_RUNTIME_CLOSED',known_functions=19,
        changed_expected_bodies=2,SQL_substitutions=7,actual_Native_credit=0)


if __name__=='__main__':print(json.dumps(write()))
