create or replace function cp7_alert_native.fabric_kind_source()returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare m jsonb:=cp7_alert_native.fabric_source();f jsonb:=cp7_stock_formula.material_source('FABRIC');
begin
 return jsonb_build_object('rows',(m->'rows')||(f->'rows'),
  'states',coalesce((select jsonb_object_agg(e.key,e.value)from jsonb_each(f->'states')e where e.value<>'"MANUAL_MINIMUM_IN_FORCE"'::jsonb),'{}')||(m->'states'));
end $$;
