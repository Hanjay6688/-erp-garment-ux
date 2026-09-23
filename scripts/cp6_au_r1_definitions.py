"""AU-R1 candidate definitions, written in exact pg_get_functiondef form.

The successor cutoff reads one source of NEW_STOCK physical instants. fg_lots
stays whole, exactly as AU checked it (never loosened). bs_cases counts only
rows whose immutable producer lineage passed
assert_product_identity_time(...,'NEW_STOCK'): QC items and laundry BS
allocations. Manual LEGACY/OUT_OF_NOWHERE and opening BS never pass that assert
and keep AU behaviour; whether they bound a successor is an open owner contract
(STATUS_DAN_TODO P0 "AU physical timestamp cutoff"), held rather than guessed.
"""
import cp6_au_definitions as au

EDIT='erp.edit_product_identity_effective(uuid,text,uuid,uuid,text,uuid,text,timestamp with time zone,text)'
HELPER='erp.latest_new_stock_physical_at_v1(uuid)'
COVERAGE='erp.assert_new_stock_cutoff_coverage_v1()'
PRIVATE_ACL=['postgres=X/postgres']
COVERED=('bs_cases','fg_lots')
# Product-referencing tables written by NEW_STOCK producers that carry no
# physical instant of their own (running balance cache keyed by lot/location).
DERIVED=('fg_inventory_balances',)

OLD={EDIT:au.FUNCTIONS[EDIT]}

DECLARE_OLD="v_used boolean; v_eff timestamptz:=coalesce(p_effective_from,clock_timestamp());\n"
DECLARE_NEW="v_used boolean; v_eff timestamptz:=coalesce(p_effective_from,clock_timestamp()); v_last timestamptz;\n"
CUTOFF_OLD="""  if exists(select 1 from erp.fg_lots l where l.product_id=p.id and l.produced_at>=v_eff) then
    raise exception 'Tanggal efektif SKU akan memotong histori produksi yang sudah tercatat';
  end if;
"""
CUTOFF_NEW="""  v_last:=erp.latest_new_stock_physical_at_v1(p.id);
  if v_last>=v_eff then
    raise exception 'Tanggal efektif SKU akan memotong histori produksi yang sudah tercatat (fakta fisik stok baru terakhir %). Pilih tanggal efektif sesudahnya.',v_last;
  end if;
"""


def replace_once(text,old,new):
    assert text.count(old)==1,('AU_R1_SOURCE_ANCHOR',old[:60])
    return text.replace(old,new)


FUNCTIONS={EDIT:replace_once(replace_once(OLD[EDIT],DECLARE_OLD,DECLARE_NEW),CUTOFF_OLD,CUTOFF_NEW)}

NEW_FUNCTIONS={
HELPER:"""CREATE OR REPLACE FUNCTION erp.latest_new_stock_physical_at_v1(p_product_id uuid)
 RETURNS timestamp with time zone
 LANGUAGE sql
 STABLE
 SET search_path TO ''
AS $function$
select max(f.physical_at) from (
  select l.produced_at as physical_at from erp.fg_lots l where l.product_id=p_product_id
  union all
  select b.physical_at from erp.bs_cases b
  where b.product_id=p_product_id
    and (b.qc_item_id is not null or b.source_laundry_bs_allocation_id is not null)
) f
$function$
""",
COVERAGE:"""CREATE OR REPLACE FUNCTION erp.assert_new_stock_cutoff_coverage_v1()
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
 SET search_path TO ''
AS $function$
declare
  v_covered text[]:=array['bs_cases','fg_lots'];
  v_derived text[]:=array['fg_inventory_balances'];
  v_helper text[];
  v_missing text[];
  v_producers jsonb;
begin
  select array_agg(distinct m[1] order by m[1]) into v_helper
  from pg_proc p cross join lateral regexp_matches(p.prosrc,'erp\\.([a-z0-9_]+)','g') m
  where p.oid='erp.latest_new_stock_physical_at_v1(uuid)'::regprocedure;
  if v_helper is distinct from v_covered then
    raise exception 'NEW_STOCK_CUTOFF_HELPER_SCOPE_DRIFT: %',v_helper;
  end if;
  if (select p.prosrc from pg_proc p where p.oid='erp.edit_product_identity_effective(uuid,text,uuid,uuid,text,uuid,text,timestamp with time zone,text)'::regprocedure)
     !~ 'erp\\.latest_new_stock_physical_at_v1\\s*\\(' then
    raise exception 'NEW_STOCK_CUTOFF_CONSUMER_DRIFT';
  end if;
  with producers as (
    select p.oid::regprocedure::text fn,p.prosrc
    from pg_proc p join pg_namespace n on n.oid=p.pronamespace
    where n.nspname in('erp','public') and p.prokind in('f','p')
      and p.oid<>'erp.assert_product_identity_time(uuid,timestamp with time zone,text)'::regprocedure
      and exists(select 1 from regexp_matches(p.prosrc,'assert_product_identity_time\\s*\\(([^;]*)\\)\\s*;','g') c
                 where c[1] !~ '''EXISTING_STOCK''\\s*$')
  ), targets as (
    select distinct pr.fn,lower(m[1]) relname
    from producers pr cross join lateral regexp_matches(pr.prosrc,'insert\\s+into\\s+erp\\.([a-z0-9_]+)','gi') m
  )
  select coalesce(jsonb_object_agg(x.fn,x.tables),'{}'::jsonb),
         array_agg(x.missing) filter(where x.missing is not null)
    into v_producers,v_missing
  from (
    select t.fn,jsonb_agg(t.relname order by t.relname) tables,
           string_agg(case when t.relname<>all(v_covered) and t.relname<>all(v_derived)
             and exists(select 1 from pg_constraint fk join pg_class c on c.oid=fk.conrelid
                        join pg_namespace cn on cn.oid=c.relnamespace
                        where fk.contype='f' and fk.confrelid='erp.products'::regclass
                          and cn.nspname='erp' and c.relname=t.relname)
             then t.fn||' -> erp.'||t.relname end,'; ' order by t.relname) missing
    from targets t group by t.fn
  ) x;
  if v_missing is not null then
    raise exception 'NEW_STOCK_CUTOFF_COVERAGE_MISSING: %',array_to_string(v_missing,'; ');
  end if;
  return jsonb_build_object('covered',v_covered,'derived_without_physical_instant',v_derived,'new_stock_producers',v_producers);
end;
$function$
""",
}
