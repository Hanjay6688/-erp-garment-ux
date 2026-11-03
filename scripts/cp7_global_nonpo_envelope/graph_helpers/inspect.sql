-- Pure inspection. Even an observed quiescent graph confers NO command admission.
create function cp7_global_nonpo_native_graph.inspect_v1(p_root_sales uuid[]) returns jsonb
language plpgsql stable security definer set search_path='' set timezone='UTC' as $$
declare authority jsonb;scope jsonb;global_source jsonb;outside_source jsonb;issues jsonb:='[]';
 edges jsonb;transfers jsonb;invalid_graph boolean;missing_hpp boolean;outside_alignment jsonb;
 outside_input jsonb;book_error text;relevant_bad boolean;
begin
 authority:=cp7_global_nonpo_native_graph.authority_v1();
 if authority->'known_functions_exact' is distinct from 'true'::jsonb
  or authority#>'{view,exact_known_source}' is distinct from 'true'::jsonb
  or authority->'new_private_acl_closed' is distinct from 'true'::jsonb then
  return jsonb_build_object('status','REFUSE_KNOWN_SOURCE_AUTHORITY','authority',authority,
   'runtime_entry',null,'qualified_for_runtime',false,'actual_Native_credit',0);
 end if;
 -- There is no application EXECUTE/USAGE grant or runtime caller yet. Do not
 -- execute Native's VOLATILE role/context dispatcher from this STABLE reader.
 -- Future owning command authority remains the unchanged outer D1/E contract.
 scope:=cp7_global_nonpo_native_graph.scope_v1(p_root_sales);
 global_source:=cp7_global_nonpo_native_graph.capture_v1(scope,false);
 outside_source:=cp7_global_nonpo_native_graph.capture_v1(scope,true);
 if exists(select 1 from erp.be_execution_context_v1)then
  issues:=issues||'"AMBIENT_BE_CONTEXT_OR_LEAK_UNQUALIFIED"'::jsonb;end if;
 select exists(select 1 from erp.fg_lots l where l.id in(select value::uuid from jsonb_array_elements_text(scope#>'{relevant,lot_ids}'))
  and(l.po_id is not null or l.lot_origin='CONVERSION'
   or(select count(*)from erp.hpp_versions h where h.lot_id=l.id)<>1
   or(select count(*)from erp.hpp_versions h where h.lot_id=l.id and h.is_current)<>1))
  or exists(select 1 from erp.opening_lot_hpp_gl_state s where s.lot_id in(select value::uuid from jsonb_array_elements_text(scope#>'{relevant,lot_ids}')))
  or exists(select 1 from erp.opening_hpp_corrections c where c.lot_id in(select value::uuid from jsonb_array_elements_text(scope#>'{relevant,lot_ids}')))
  or exists(select 1 from erp.product_conversions c where c.id in(select value::uuid from jsonb_array_elements_text(scope#>'{relevant,conversion_ids}')))
 into relevant_bad;
 if relevant_bad then issues:=issues||'"RELEVANT_EXISTING_CLASS_OR_IDENTITY_ADAPTER_REQUIRED"'::jsonb;end if;
 if exists(select 1 from erp.fg_lots l where l.po_id is null and l.lot_origin<>'VOIDED_PRODUCTION'and(
   (select count(*)from erp.hpp_versions h where h.lot_id=l.id and h.is_current)<>1
   or exists(select 1 from erp.hpp_versions h where h.lot_id=l.id and h.is_current
    and(h.total_cost is null or h.hpp_per_pcs is null or h.total_cost::text in('NaN','Infinity','-Infinity')
     or h.hpp_per_pcs::text in('NaN','Infinity','-Infinity')))))then
  issues:=issues||'"GLOBAL_NONVOIDED_CURRENT_HPP_UNKNOWN_OR_NONFINITE"'::jsonb;end if;

 with recursive rooted(lot_id,depth,path)as(
  select l.id,0,array[l.id]from erp.fg_lots l where l.po_id is null and l.lot_origin not in('CONVERSION','VOIDED_PRODUCTION')
  union all select a.destination_lot_id,r.depth+1,r.path||a.destination_lot_id from rooted r
   join erp.product_conversion_allocations a on a.source_lot_id=r.lot_id
   join erp.product_conversions c on c.id=a.conversion_id and c.status='POSTED'
   where a.destination_lot_id is not null and not a.destination_lot_id=any(r.path)and r.depth<128
 ),visits as(select a.*,r.depth source_depth from rooted r join erp.product_conversion_allocations a on a.source_lot_id=r.lot_id
  join erp.product_conversions c on c.id=a.conversion_id and c.status='POSTED'where a.destination_lot_id is not null),
 values_now as(select a.id,a.conversion_id,a.source_lot_id,a.destination_lot_id,a.source_depth,a.qty_pcs,
   s.hpp_per_pcs::numeric(18,6) source_hpp,d.hpp_per_pcs::numeric(18,6) destination_hpp,
   (s.hpp_per_pcs::numeric(18,6)+erp.be_allocation_extra_v1(a.id)/nullif(a.qty_pcs,0))::numeric(18,6) desired_hpp,
   (select count(*)from erp.hpp_versions h where h.lot_id=a.source_lot_id and h.is_current)source_current_count,
   (select count(*)from erp.hpp_versions h where h.lot_id=a.destination_lot_id and h.is_current)destination_current_count
  from visits a left join erp.v_current_hpp s on s.lot_id=a.source_lot_id left join erp.v_current_hpp d on d.lot_id=a.destination_lot_id)
 select coalesce(jsonb_agg(to_jsonb(v)||jsonb_build_object('would_write_HPP',
   destination_hpp is null or abs(destination_hpp-desired_hpp)>0.000001)order by source_depth,id),'[]'),
  coalesce(bool_or(source_hpp is null or destination_hpp is null or desired_hpp is null or qty_pcs<=0 or source_current_count<>1 or destination_current_count<>1
   or source_hpp::text in('NaN','Infinity','-Infinity')or destination_hpp::text in('NaN','Infinity','-Infinity')
   or desired_hpp::text in('NaN','Infinity','-Infinity')or desired_hpp<0),false)
 into edges,missing_hpp from values_now v;
 with recursive reachable(lot_id,path,depth)as(
  select l.id,array[l.id],0 from erp.fg_lots l where l.po_id is null and l.lot_origin not in('CONVERSION','VOIDED_PRODUCTION')
  union all select a.destination_lot_id,r.path||a.destination_lot_id,r.depth+1 from reachable r
   join erp.product_conversion_allocations a on a.source_lot_id=r.lot_id
   join erp.product_conversions c on c.id=a.conversion_id and c.status='POSTED'
   where a.destination_lot_id is not null and not a.destination_lot_id=any(r.path)and r.depth<128)
 select exists(select 1 from erp.product_conversion_allocations a
  join erp.product_conversions c on c.id=a.conversion_id and c.status='POSTED'
  join erp.fg_lots s on s.id=a.source_lot_id and s.po_id is null
  left join erp.fg_lots d on d.id=a.destination_lot_id
  where d.id is null or not exists(select 1 from reachable r where r.lot_id=a.destination_lot_id)
   or not erp.be_nonpo_admitted_v1(c.id)or d.po_id is distinct from s.po_id
   or d.lot_origin<>'CONVERSION'or d.source_lot_id is distinct from s.id or a.qty_pcs<=0)
 into invalid_graph;
 if invalid_graph then issues:=issues||'"GLOBAL_NATIVE_LINEAGE_ORPHAN_CYCLE_DEPTH_OR_SOURCE_INVALID"'::jsonb;end if;
 if missing_hpp then issues:=issues||'"GLOBAL_NATIVE_HPP_SOURCE_MISSING_NONFINITE_OR_AMBIGUOUS"'::jsonb;end if;
 if exists(select 1 from jsonb_array_elements(edges)e where(e->>'would_write_HPP')::boolean)then
  issues:=issues||'"GLOBAL_PROPAGATION_REQUIRES_HPP_WRITE"'::jsonb;end if;

 with basis as(select a.id allocation_id,a.conversion_id,a.qty_pcs,a.original_hpp_per_pcs,h.hpp_per_pcs,
   round(a.qty_pcs*a.original_hpp_per_pcs,2)+coalesce((select sum(e.target_value-e.previous_value)
    from erp.be_nonpo_transfer_events_v1 e where e.conversion_id=c.id),0) previous_value,
   round(a.qty_pcs*h.hpp_per_pcs,2) target_value
  from erp.product_conversions c join erp.product_conversion_allocations a on a.conversion_id=c.id
  join erp.fg_lots l on l.id=a.source_lot_id and l.po_id is null
  left join erp.v_current_hpp h on h.lot_id=l.id where c.status='POSTED')
 select coalesce(jsonb_agg(to_jsonb(b)||jsonb_build_object('delta',target_value-previous_value,
  'would_write_transfer',target_value is null or previous_value is null or target_value-previous_value<>0)order by conversion_id,allocation_id),'[]')
 into transfers from basis b;
 if exists(select 1 from jsonb_array_elements(transfers)t where(t->>'would_write_transfer')::boolean
  or t->>'previous_value'in('NaN','Infinity','-Infinity')or t->>'target_value'in('NaN','Infinity','-Infinity'))then
  issues:=issues||'"GLOBAL_TRANSFER_REQUIRES_EVENT_OR_SOURCE_INVALID"'::jsonb;end if;

 -- This is a NEW actual outside-global input, not a relabelled source_native_snapshot.
 select jsonb_build_object('fg_lots',coalesce(jsonb_agg(to_jsonb(l)order by l.id),'[]'),
  'hpp_accounts',global_source#>'{facts,hpp_accounts}')into outside_input from erp.fg_lots l
  where l.po_id is null and l.product_id in(select value::uuid from jsonb_array_elements_text(scope#>'{outside,product_ids}'));
 begin
  outside_alignment:=cp7_credit.source_first_nonpo_hpp_alignment_v1(outside_input);
 exception when raise_exception or no_data_found then
  get stacked diagnostics book_error=MESSAGE_TEXT;
  issues:=issues||'"OUTSIDE_NATIVE_TARGET_BOOK_NOT_EXACT"'::jsonb;
 end;
 return jsonb_build_object('contract','cp7.global-nonpo-native-graph.readonly-inspector.v1',
  'status',case when issues='[]'::jsonb then'OBSERVED_QUIESCENT_SOURCE_ONLY'else'OBSERVED_REFUSAL_SOURCE_ONLY'end,
  'issues',issues,'authority',authority,'scope',scope,'global_source',global_source,'outside_source',outside_source,
  'propagation_visits',edges,'transfer_rows',transfers,'outside_alignment_input',outside_input,
  'outside_alignment',outside_alignment,'outside_alignment_error',book_error,
  'basis_sha256',cp7_credit.pg_jsonb_sha256(jsonb_build_object('scope',scope,'global',global_source,'outside',outside_source,
    'edges',edges,'transfers',transfers,'outside_alignment',outside_alignment)),
  'read_only',true,'writer_or_phantom_lock_closed',false,'required_final_composition_parent',null,
  'runtime_entry',null,'qualified_for_runtime',false,'actual_Native_credit',0,'production_go',false,'independent_acceptance',false);
end $$;
alter function cp7_global_nonpo_native_graph.inspect_v1(uuid[]) owner to postgres;
revoke all on function cp7_global_nonpo_native_graph.inspect_v1(uuid[]) from public,anon,authenticated,service_role;
