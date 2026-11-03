"""Generate a fixed read-only fingerprint of complete current catalogue inputs.

The original all22 queries are immutable inputs, not imported ERP callbacks.
Three extra fixed catalogue groups cover operator/cast/language dispatch that
the retained all22 restoration projection does not represent separately. No
profile is seeded, installer admitted, SQL executed or old control repeated.
"""
from pathlib import Path
from hashlib import sha256
import ast,json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
ORIGINAL=dict(bytes=19828,sha256='a1605193347cf5b3321a7bdbf8ff6c634df4f4c0a5113eb295e8c3ce44428e00')
EXTRA={
 'operators':"""select n.nspname||'.'||o.oprname||'('||o.oprleft::regtype::text||','||o.oprright::regtype::text||')',
 jsonb_build_array(pg_get_userbyid(o.oprowner),o.oprkind::text,o.oprcanmerge,o.oprcanhash,
 o.oprleft::regtype::text,o.oprright::regtype::text,o.oprresult::regtype::text,
 o.oprcode::regprocedure::text,o.oprcom::regoperator::text,o.oprnegate::regoperator::text,
 o.oprrest::regprocedure::text,o.oprjoin::regprocedure::text)
 from pg_operator o join pg_namespace n on n.oid=o.oprnamespace""",
 'casts':"""select c.castsource::regtype::text||'->'||c.casttarget::regtype::text,
 jsonb_build_array(c.castcontext::text,c.castmethod::text,c.castfunc::regprocedure::text)
 from pg_cast c""",
 'languages':"""select l.lanname,jsonb_build_array(pg_get_userbyid(l.lanowner),l.lanispl,l.lanpltrusted,
 l.lanplcallfoid::regprocedure::text,l.laninline::regprocedure::text,l.lanvalidator::regprocedure::text,
 case when l.lanacl is null then null else to_jsonb(array(select a::text from unnest(l.lanacl)a order by a::text collate "C"))end)
 from pg_language l""",
}


def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())


def queries():
    p=ROOT/'scripts/cp7_ow04_restore_bundle.py';raw=p.read_bytes()
    if pin(raw)!=ORIGINAL:raise ValueError('GLOBAL_CATALOGUE_EXACT_ORIGINAL_ALL22_SOURCE_REQUIRED')
    nodes=[]
    for n in ast.parse(raw).body:
        if isinstance(n,ast.FunctionDef)and n.name=='_acl':nodes.append(n)
        if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id in('NAMESPACE','QUERIES')for t in n.targets):nodes.append(n)
    env={};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(p)+':inert-original-query-strings','exec'),env)
    result=env['QUERIES']
    if len(result)!=22 or set(result)&set(EXTRA):raise ValueError('GLOBAL_CATALOGUE_EXACT22_PLUS_THREE_DISPATCH_GROUPS')
    return result|EXTRA


def derive():
    groups=queries();pieces=[]
    for name,query in sorted(groups.items()):
        # Sorted key/value arrays retain every row, even duplicate observation
        # keys; jsonb_object_agg inside an individual group could erase one.
        pieces.append("select '"+name+"'::text name,coalesce(jsonb_agg(jsonb_build_array(k,v)"
            'order by k collate "C",v::text collate "C"),\'[]\'::jsonb)value from ('+query+')q(k,v)')
    body=""" with observations as(
"""+'\n union all\n'.join(pieces)+"""
 ),combined as(select jsonb_object_agg(name,value)catalogues from observations)
 select jsonb_build_object('contract','cp7.global-catalogue-fingerprint.v1',
  'groups',25,'sha256',encode(sha256(convert_to(catalogues::text,'UTF8')),'hex'),
  'counts',(select jsonb_object_agg(name,jsonb_array_length(value))from observations))from combined
"""
    sql="""-- New private read-only authority fingerprint; no installer/profile seed.
-- Call after the complete catalogue fence and permanent-XID drain, before
-- trusting any source graph. Data rows and sequence positions are excluded.
create function cp7_global_nonpo_envelope.catalogue_fingerprint_v1()returns jsonb
language sql stable security definer set search_path=''set TimeZone='UTC'as $catalogue$
"""+body+"""$catalogue$;
alter function cp7_global_nonpo_envelope.catalogue_fingerprint_v1()owner to postgres;
revoke all on function cp7_global_nonpo_envelope.catalogue_fingerprint_v1()from public,anon,authenticated,service_role;
"""
    proof=dict(status='FIXED_READONLY_ALL22_PLUS_OPERATOR_CAST_LANGUAGE_FINGERPRINT_SOURCE_NOT_RUNTIME',
        original_all22_source=ORIGINAL,original_all22_groups=22,new_dispatch_groups=sorted(EXTRA),
        total_groups=25,query_pins={k:pin(v.encode())for k,v in sorted(groups.items())},
        generated_source=pin(sql.encode()),no_SQL_executor_or_installer=True,profile_seed_statements=0,
        actual_SQL_executed=0,actual_Native_cases=0,production_go=False,independent_acceptance=False)
    return sql,proof


if __name__=='__main__':
    _,proof=derive();print(json.dumps(proof,indent=2))
