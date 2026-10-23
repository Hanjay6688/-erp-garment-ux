create or replace function cp7_stock_formula.workspace(p jsonb)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;q text;f text;off integer;n integer;total bigint;rows jsonb;checked timestamptz;result jsonb;
begin
 a:=cp7_stock_formula.access_now(false);
 if jsonb_typeof(p)is distinct from'object'or exists(select 1 from jsonb_object_keys(p)k where k not in('q','filter','offset','limit'))
  or(p?'q'and jsonb_typeof(p->'q')<>'string')or(p?'filter'and(jsonb_typeof(p->'filter')<>'string'
   or p->>'filter'not in('ALL','AT_OR_BELOW','MANUAL','NOT_ENOUGH_DATA')))
  or(p?'offset'and(jsonb_typeof(p->'offset')<>'number'or(p->>'offset')!~'^[0-9]{1,7}$'))
  or(p?'limit'and(jsonb_typeof(p->'limit')<>'number'or(p->>'limit')!~'^[0-9]{1,3}$'))then raise exception using errcode='22023',message='CP7_FORMULA_QUERY';end if;
 q:=lower(btrim(coalesce(p->>'q','')));f:=coalesce(p->>'filter','ALL');off:=coalesce((p->>'offset')::integer,0);n:=coalesce((p->>'limit')::integer,25);
 if length(q)>120 or n not between 1 and 100 then raise exception using errcode='22023',message='CP7_FORMULA_QUERY';end if;
 -- Count, rows and totals share this statement snapshot. Expose only the
 -- sanitized evaluation, never products/profiles/raw jobs or cache DTOs.
 with run as materialized(select r.computed_at,to_jsonb(r)-'id'body from cp7_stock_formula.runs r
  where exists(select 1 from cp7_reorder_caller.use_marks)),
 all_rows as materialized(select cp7_reorder_caller.wire_row(e.row,(select computed_at from run))r from cp7_reorder_caller.evaluations e),
 filtered as materialized(select r,case r->>'state'when'AT_OR_BELOW'then 0 when'ABOVE'then 1 else 2 end ord from all_rows
  where(q=''or strpos(lower(concat_ws(' ',r->>'sku',r->>'product_name',r->>'size_code')),q)>0)
   and(f='ALL'or(f='AT_OR_BELOW'and r->>'state'='AT_OR_BELOW')or(f='MANUAL'and r->>'basis'='MANUAL')
    or(f='NOT_ENOUGH_DATA'and r->>'basis'='NOT_ENOUGH_DATA'))),
 page as(select*from filtered order by ord,r->>'sku',r->>'target_key'limit n offset off)
 select jsonb_build_object('contract_version','cp7.fg-reorder.v2','read_at',statement_timestamp(),
  'settings',cp7_stock_formula.current_settings(),'run',(select body from run),
  'can_manage',coalesce(a->'profile'->>'role_code','')in('OWNER','ADMIN'),
  'counts',(select jsonb_build_object('items',count(*),'at_or_below',count(*)filter(where r->>'state'='AT_OR_BELOW'),
   'manual',count(*)filter(where r->>'basis'='MANUAL'),'formula',count(*)filter(where r->>'basis'='FORMULA'),
   'not_enough_data',count(*)filter(where r->>'basis'='NOT_ENOUGH_DATA'),'no_sales',0)from all_rows),
  'page',(select jsonb_build_object('rows',coalesce((select jsonb_agg(r order by ord,r->>'sku',r->>'target_key')from page),'[]'),
   'total',count(*)::text,'offset',off,'limit',n,'next_offset',case when off+(select count(*)from page)<count(*)then off+(select count(*)from page)end)from filtered))
 into result;
 if cp7_stock_formula.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_FORMULA_ACCESS_CHANGED';end if;
 return result;
end $$;
