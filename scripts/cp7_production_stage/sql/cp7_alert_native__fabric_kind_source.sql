create or replace function cp7_alert_native.fabric_kind_source()returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare f jsonb:=cp7_stock_formula.material_source('FABRIC');m jsonb:=cp7_alert_native.fabric_source();
begin
 -- The current evaluation owns the explicit choice. The Native legacy rule
 -- only fills subjects it still delegates, including during a busy recheck;
 -- it cannot resurrect a reference minimum after FORMULA was selected.
 return jsonb_build_object('rows',(f->'rows')||coalesce((select jsonb_agg(x)from jsonb_array_elements(m->'rows')x
   where(f->'states'->>(x->>'subject_key')is null or f->'states'->>(x->>'subject_key')='MANUAL_MINIMUM_IN_FORCE')
    and not exists(select 1 from jsonb_array_elements(f->'rows')y where y->>'subject_key'=x->>'subject_key')),'[]'::jsonb),
  'states',coalesce((select jsonb_object_agg(e.key,e.value)from jsonb_each(f->'states')e where e.value<>'"MANUAL_MINIMUM_IN_FORCE"'::jsonb),'{}')||
   coalesce((select jsonb_object_agg(e.key,e.value)from jsonb_each(m->'states')e
    where(f->'states'->>e.key is null or f->'states'->>e.key='MANUAL_MINIMUM_IN_FORCE')
     and not exists(select 1 from jsonb_array_elements(f->'rows')y where y->>'subject_key'=e.key)),'{}'));
end $$;
