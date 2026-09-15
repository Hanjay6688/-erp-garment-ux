#!/usr/bin/env python3
"""Build AD from immutable canonical AC functions and the admitted Z capsule form.

The two business functions are changed by one exact anchor each. The CLI-created
migration stamp is fixed; rebuilding never creates another candidate generation.
"""
from pathlib import Path
import hashlib,json

STAMP='20260915113627'
NAME='erp_v2_6_20ad_cp6_opening_material_business_day'
MIGRATION=Path(f'supabase/migrations/{STAMP}_{NAME}.sql')
ROLLBACK=Path(f'supabase/rollbacks/{STAMP}_{NAME}.rollback.sql')
INPUT=Path('docs/evidence/cp6-ad-predecessor-functions.json')
PINS=Path('docs/evidence/cp6-ad-runtime-pins.json')
ZSTAMP='20260914085912'
ZNAME='erp_v2_6_20z_cp6_accounting_close_business_date'
ACL="array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]"
IDENTITIES=('erp.post_opening_balance(uuid)','erp.run_v268_financial_report_checks()')
OLD_HASHES=('d73391c79e725c14aab7370cf5f5dfc0bd2134a02480e5693c37dc9c25bf5829',
            '416b8c53665c4c2b814d4621935a9291797fdbf49067deb0a910d16dc90685fd')
OLD_CLOSE="'erp.close_accounting_through(date,text)'"
OLD_PRE='c9517690638ac40bb8914e0613b7d5bdf92256274e9c5551747060d09a79536b'
OLD_POST='7f20b0a381b049391fc3e33dce00b3b8c517b0b77ae8f2b2756cac5e0a021b42'
OLD_ACL="array['authenticated=X/postgres','postgres=X/postgres']::text[]"

# A date-only material opening means the start of that Jakarta business day.
# Check the whole source partition: each posted line has exactly one matching
# OPENING movement, with no movement on a different day or within-day cutoff.
DRIFT_QUERY="""select count(*)::bigint
    from erp.opening_balance_items i
    join erp.opening_balance_headers h on h.id=i.opening_id
    where h.status='POSTED' and i.balance_type='MATERIAL' and (
      (select count(*) from erp.material_stock_movements m
       where m.source_type='OPENING_BALANCE_ITEM' and m.source_id=i.id)<>1
      or not exists(select 1 from erp.material_stock_movements m
        where m.source_type='OPENING_BALANCE_ITEM' and m.source_id=i.id
          and m.movement_type='OPENING' and m.material_id=i.material_id
          and m.location_id=i.location_id and m.roll_id is not distinct from i.roll_id
          and m.physical_at=(h.opening_date::timestamp at time zone 'Asia/Jakarta'))
    )"""
CHECK_SQL="""
  return query
  select 'V2620AD_OPENING_MATERIAL_TIMELINE_MISMATCH'::text,'CRITICAL'::text,
    (%s),
    'Every posted material opening line must own one movement at the start of its Jakarta document date'::text;
""" % DRIFT_QUERY

def sha(s):return hashlib.sha256(s.encode() if isinstance(s,str) else s).hexdigest()
def exact_replace(s,old,new):
    assert s.count(old)==1,(old[:100],s.count(old))
    return s.replace(old,new,1)

def build():
    assert sha(INPUT.read_bytes())=='0a0edbcfd0c4cd26212a161a84f3b7414ecc15fe5642409c868f1f17a0694446'
    incoming=json.loads(INPUT.read_text());rows={r[0]:r for r in incoming['functions']}
    assert set(rows)==set(IDENTITIES)
    functions=[]
    for identity,old_hash in zip(IDENTITIES,OLD_HASHES,strict=True):
        _,definition,acl,owner=rows[identity]
        assert sha(definition)==old_hash and owner=='postgres'
        assert sorted(acl.strip('{}').split(','))==['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']
        if identity==IDENTITIES[0]:
            patched=exact_replace(definition,'h.opening_date::timestamptz',"(h.opening_date::timestamp at time zone 'Asia/Jakarta')")
        else:
            patched=exact_replace(definition,'\nend\n$function$',CHECK_SQL+'\nend\n$function$')
        functions.append({'identity':identity,'predecessor_sha256':old_hash,'installed_sha256':sha(patched),'owner':owner,'acl':sorted(acl.strip('{}').split(','))})
    values=',\n    '.join(f"('{f['identity']}','{f['predecessor_sha256']}','{f['installed_sha256']}',{ACL})" for f in functions)
    predecessor_values=',\n    '.join(f"('{f['identity']}','{f['predecessor_sha256']}',{ACL})" for f in functions)
    restore_values=',\n    '.join(f"('{f['identity']}','{f['predecessor_sha256']}')" for f in functions)

    migration=Path(f'supabase/migrations/{ZSTAMP}_{ZNAME}.sql').read_text()
    rollback=Path(f'supabase/rollbacks/{ZSTAMP}_{ZNAME}.rollback.sql').read_text()
    assert sha(migration)=='4811f4ea21b35aac10da02da96bdec34505c619d3daa0b53f64fe22205a2f4a3'
    assert sha(rollback)=='c00029564f0092ebfb8afa9daeb566961af7fe2b6fe8eb800550d1b045896f2f'
    start=migration.index('do $predecessor_v2620z$')
    end=migration.index('$predecessor_v2620z$;',start)+len('$predecessor_v2620z$;')
    guard=f"""do $predecessor_v2620z$
declare r record;v_actual text;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.20ac')
     or exists(select 1 from erp.schema_migrations where version='v2.6.20z')
     or to_regclass('erp.cp6_v2620z_rollback_capsule') is not null
     or to_regclass('erp.cp6_v2620ac_rollback_capsule') is null
     or to_regclass('erp.cp6_v2620ac_relation_rollback_capsule') is null then
    raise exception 'Z_REQUIRES_EXACT_AC_WITHOUT_Z_RESIDUE';
  end if;
  if (select count(*) from supabase_migrations.schema_migrations where name='erp_v2_6_20ac_cp6_temporal_surface_closure')<>1
     or not exists(select 1 from supabase_migrations.schema_migrations
       where version='20260915031500' and name='erp_v2_6_20ac_cp6_temporal_surface_closure'
         and encode(extensions.digest(convert_to(array_to_string(statements,E'\\n'),'UTF8'),'sha256'),'hex')
             ='7b5690a2eddf618833d352dc75eb95aa1ef4dbcfb25d39b30374b733d33dadbc')
     or exists(select 1 from supabase_migrations.schema_migrations where version>'20260915031500')
     or (select count(*) from erp.cp6_v2620ac_rollback_capsule)<>115
     or (select count(*) from erp.cp6_v2620ac_relation_rollback_capsule)<>157 then
    raise exception 'Z_REQUIRES_EXACT_AC_PLATFORM_CAPSULES';
  end if;
  for r in select * from(values
    {predecessor_values}
  ) expected(identity,sha256,acl) loop
    select encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex')
    into v_actual from pg_proc p where p.oid=to_regprocedure(r.identity)
      and pg_get_userbyid(p.proowner)='postgres'
      and array(select a::text from unnest(p.proacl) a order by a::text)=r.acl;
    if v_actual is distinct from r.sha256 then
      raise exception 'Z_PREDECESSOR_FUNCTION_OWNER_ACL_MISMATCH: %',r.identity;
    end if;
  end loop;
  if ({DRIFT_QUERY})<>0 then
    raise exception 'Z_PREEXISTING_OPENING_TIMELINE_REVIEW_REQUIRED';
  end if;
end
$predecessor_v2620z$;"""
    migration=migration[:start]+guard+migration[end:]
    migration=exact_replace(migration,"where p.oid='erp.close_accounting_through(date,text)'::regprocedure;",
        "where p.oid in('erp.post_opening_balance(uuid)'::regprocedure,'erp.run_v268_financial_report_checks()'::regprocedure);")
    start=migration.index('do $canonical_close_v2620z$');end=migration.index('$canonical_close_v2620z$;',start)+len('$canonical_close_v2620z$;')
    patch="""do $canonical_opening_v2620z$
declare d text;anchor text:='h.opening_date::timestamptz';
begin
  select pg_get_functiondef('erp.post_opening_balance(uuid)'::regprocedure) into d;
  if (length(d)-length(replace(d,anchor,'')))/length(anchor)<>1 then raise exception 'Z_OPENING_ANCHOR';end if;
  execute replace(d,anchor,'(h.opening_date::timestamp at time zone ''Asia/Jakarta'')');
  select pg_get_functiondef('erp.run_v268_financial_report_checks()'::regprocedure) into d;
  anchor:=E'\\nend\\n$function$';
  if (length(d)-length(replace(d,anchor,'')))/length(anchor)<>1 then raise exception 'Z_REPORT_ANCHOR';end if;
  execute replace(d,anchor,$replacement$"""+CHECK_SQL+"\nend\n$function$"+"""$replacement$);
end
$canonical_opening_v2620z$;"""
    migration=migration[:start]+patch+migration[end:]
    old_values=f'({OLD_CLOSE},\'{OLD_PRE}\',\'{OLD_POST}\',{OLD_ACL})'
    migration=exact_replace(migration,old_values,values)
    migration=migration.replace("like erp.cp6_v2620y_rollback_capsule", "like erp.cp6_v2620ab_rollback_capsule")
    migration=exact_replace(migration,"(select count(*) from erp.cp6_v2620z_rollback_capsule)<>1","(select count(*) from erp.cp6_v2620z_rollback_capsule)<>2")
    migration=migration[migration.index('begin;'):]
    migration='-- CP6 AD: one canonical material-opening clock and its owner-report detector.\n-- Qualified AC native counterexamples: run 34963873816; no posted history rewrite.\n'+migration
    migration=migration.replace('211','216').replace('v2620z','v2620ad').replace('v2.6.20z','v2.6.20ad').replace('Z_','AD_')
    migration=exact_replace(migration,'Canonical Jakarta accounting-close day; authorization, reason, reopen, checkpoints and audit history preserved',
        'Canonical Jakarta material opening for direct and imported stock; report detects source timeline drift; posted history remains immutable')
    MIGRATION.write_text(migration)

    rollback=exact_replace(rollback,old_values,values)
    rollback=exact_replace(rollback,f'({OLD_CLOSE},\'{OLD_PRE}\')',restore_values)
    rollback=exact_replace(rollback,f'({OLD_CLOSE},\'{OLD_PRE}\',{OLD_ACL})',predecessor_values)
    rollback=rollback.replace("(select count(*) from erp.cp6_v2620z_rollback_capsule)<>1","(select count(*) from erp.cp6_v2620z_rollback_capsule)<>2")
    rollback=rollback.replace('211','216').replace('v2620z','v2620ad').replace('v2.6.20z','v2.6.20ad').replace('Z_','AD_').replace("'v2.6.20y'","'v2.6.20ac'")
    rollback=rollback.replace(ZSTAMP,STAMP).replace(ZNAME,NAME)
    rollback=rollback.replace('4811f4ea21b35aac10da02da96bdec34505c619d3daa0b53f64fe22205a2f4a3',sha(migration)).replace('0b7f3ee8d450d4aacbba2893c7026e1a1b74ed8404138ad199ab075c980db5a5',sha(migration.removesuffix('\n')))
    rollback=rollback.replace('-> exact Y.','-> exact AC.')
    ROLLBACK.write_text(rollback)
    pins={'format':'CP6_AD_RUNTIME_PINS_V1','stamp':STAMP,'name':NAME,'version':'v2.6.20ad','predecessor_head':incoming['source_head'],
        'predecessor_tree':incoming['source_tree'],'functions':functions,'boundary_count':216,'predecessor_function_count':533,'predecessor_table_count':218,
        'source_pins':{str(p):{'sha256':sha(p.read_bytes()),'bytes':p.stat().st_size} for p in (INPUT,MIGRATION,ROLLBACK)},'production_go':False}
    PINS.write_text(json.dumps(pins,indent=2)+'\n')
    print(json.dumps(pins,indent=2))

if __name__=='__main__':build()
