-- One captured explanation for direct/staged and reorder consumers.
-- This projects actual kernel inputs; it never calculates another forecast.
create function cp7_product_analog_consumer.provenance(c jsonb,q jsonb,h jsonb,estimate jsonb,resolution jsonb,kernel jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare choice jsonb;evidence jsonb;analog jsonb;total numeric;days numeric;key text:=h->>'target_key';inputs jsonb:=kernel->'inputs';
begin
 perform cp7_wip.key(to_jsonb(key));perform cp7_wip.key(h->'size_id');
 if split_part(key,':',2)is distinct from h->>'size_id'then raise exception 'CP7_ANALOG_PROVENANCE_TARGET';end if;
 select coalesce(sum(cp7_wip.pcs(x->'gross_observed_pcs')),0),count(*)into total,days
  from jsonb_array_elements(h->'days')x where x->>'state'='AVAILABLE';
 if days is distinct from(h->>'available_days')::numeric then raise exception 'CP7_ANALOG_PROVENANCE_OWN_DAYS';end if;
 if resolution is not null and resolution<>'null'::jsonb then
  select x into strict choice from jsonb_array_elements(c->'product_analog_choices')x where x->>'target_key'=key;
  if resolution->'choice_id'is distinct from choice->'choice_id'
   or resolution->'choice_revision'is distinct from choice->'revision'then raise exception 'CP7_ANALOG_PROVENANCE_CHOICE';end if;
  evidence:=choice->'evidence';
  analog:=jsonb_build_object('state',resolution->'state','reason',resolution->'reason',
   'choice_id',choice->'choice_id','choice_revision',choice->'revision','recorded_at',choice->'recorded_at',
   'source_key',evidence->'source_key','source_sku',evidence->'source_product'->'sku',
   'source_name',evidence->'source_product'->'product_name','scale_factor',evidence->'scale_factor',
   'review_reason',choice->'reason','source_total_pcs',resolution->'analog'->'available_total_pcs',
   'available_days',resolution->'available_days','scaled_total_pcs',resolution->'scaled_total_pcs',
   'scaled_daily_sd',resolution->'scaled_daily_sd');
 end if;
 if(estimate->>'basis'='REVIEWED_ANALOG_SAME_PHYSICAL_SIZE_ASSUMPTION')is true
  and(analog->>'state'is distinct from'READY'or inputs->'daily_total_pcs'is distinct from analog->'scaled_total_pcs'
   or inputs->'counted_days'is distinct from analog->'available_days')then raise exception 'CP7_ANALOG_PROVENANCE_INPUTS';end if;
 return jsonb_build_object('contract_version','cp7.target-demand-provenance.v1','target_key',key,'size_id',h->'size_id',
  'captured_at',c->'captured_at','query',q,'basis',coalesce(estimate->>'basis','UNKNOWN'),
  'own_total_pcs',total::text,'own_available_days',days::text,
  'daily_total_pcs',inputs->'daily_total_pcs','counted_days',inputs->'counted_days','daily_sd',inputs->'daily_sd',
  'target_pcs',kernel->'target_pcs','reorder_point_pcs',kernel->'reorder_point_pcs','analog',analog);
end $$;
alter function cp7_product_analog_consumer.provenance(jsonb,jsonb,jsonb,jsonb,jsonb,jsonb)owner to cp7_capture;
revoke all on function cp7_product_analog_consumer.provenance(jsonb,jsonb,jsonb,jsonb,jsonb,jsonb)from public,anon,authenticated,service_role,cp7_alert;
