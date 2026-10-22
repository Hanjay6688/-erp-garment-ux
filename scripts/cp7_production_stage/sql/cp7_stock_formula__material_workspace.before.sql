create or replace function cp7_stock_formula.material_workspace(p jsonb)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;typ text;q text;f text;off integer;n integer;total bigint;rows jsonb;
begin
 if jsonb_typeof(p)is distinct from'object'or exists(select 1 from jsonb_object_keys(p)k where k not in('material_type','q','filter','offset','limit'))
  or jsonb_typeof(p->'material_type')is distinct from'string'
  or(p?'q'and jsonb_typeof(p->'q')<>'string')or(p?'filter'and(jsonb_typeof(p->'filter')<>'string'
   or p->>'filter'not in('ALL','AT_OR_BELOW','MANUAL','ESTIMATE','NOT_ENOUGH_DATA','NOT_SET')))
  or(p?'offset'and(jsonb_typeof(p->'offset')<>'number'or(p->>'offset')!~'^[0-9]{1,7}$'))
  or(p?'limit'and(jsonb_typeof(p->'limit')<>'number'or(p->>'limit')!~'^[0-9]{1,3}$'))then raise exception using errcode='22023',message='CP7_FORMULA_QUERY';end if;
 typ:=p->>'material_type';a:=cp7_stock_formula.material_access_now(typ,false);
 q:=lower(btrim(coalesce(p->>'q','')));f:=coalesce(p->>'filter','ALL');off:=coalesce((p->>'offset')::integer,0);n:=coalesce((p->>'limit')::integer,25);
 if length(q)>120 or n not between 1 and 100 then raise exception using errcode='22023',message='CP7_FORMULA_QUERY';end if;
 select count(*)into total from cp7_stock_formula.material_evaluations e where e.material_type=typ
  and(q=''or strpos(lower(concat_ws(' ',e.sku,e.name)),q)>0)
  and(f='ALL'or(f='AT_OR_BELOW'and e.state='AT_OR_BELOW')or(f='MANUAL'and e.basis='MANUAL')or(f='NOT_ENOUGH_DATA'and e.basis='NOT_ENOUGH_DATA')
   or(f='NOT_SET'and e.basis='NOT_SET')or(f='ESTIMATE'and e.basis='ESTIMATE'));
 select coalesce(jsonb_agg(to_jsonb(x)-'ord'order by x.ord,x.sku,x.material_id),'[]')into rows from(
  select e.*,case e.state when'AT_OR_BELOW'then 0 when'ABOVE'then 1 else 2 end ord from cp7_stock_formula.material_evaluations e
  where e.material_type=typ and(q=''or strpos(lower(concat_ws(' ',e.sku,e.name)),q)>0)
   and(f='ALL'or(f='AT_OR_BELOW'and e.state='AT_OR_BELOW')or(f='MANUAL'and e.basis='MANUAL')or(f='NOT_ENOUGH_DATA'and e.basis='NOT_ENOUGH_DATA')
    or(f='NOT_SET'and e.basis='NOT_SET')or(f='ESTIMATE'and e.basis='ESTIMATE'))
  order by ord,e.sku,e.material_id limit n offset off)x;
 return jsonb_build_object('contract_version','cp7.material-reorder.v1','material_type',typ,'read_at',statement_timestamp(),
  'settings',cp7_stock_formula.current_settings(),'run',(select to_jsonb(r)-'id'from cp7_stock_formula.runs r),
  'can_manage',coalesce(a->'profile'->>'role_code','')in('OWNER','ADMIN'),
  'counts',(select jsonb_build_object('items',count(*),'at_or_below',count(*)filter(where e.state='AT_OR_BELOW'),'manual',count(*)filter(where e.basis='MANUAL'),
    'formula',count(*)filter(where e.basis='FORMULA'),'not_enough_data',count(*)filter(where e.basis='NOT_ENOUGH_DATA'),'no_usage',count(*)filter(where e.basis='NO_USAGE'),
    'not_set',count(*)filter(where e.basis='NOT_SET'),'estimate',count(*)filter(where e.basis='ESTIMATE'))
   from cp7_stock_formula.material_evaluations e where e.material_type=typ),
  'page',jsonb_build_object('rows',rows,'total',total::text,'offset',off,'limit',n,'next_offset',case when off+jsonb_array_length(rows)<total then off+jsonb_array_length(rows)end));
end $$;
