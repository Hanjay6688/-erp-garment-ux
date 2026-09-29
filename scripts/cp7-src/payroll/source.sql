-- P10/P12 candidate source module; not installed by the FG bundle.
-- Native component entitlements, never QC GOOD or browser tariff calculations.
create role cp7_payroll_read nologin noinherit nosuperuser nocreatedb nocreaterole noreplication bypassrls;
create schema cp7_payroll authorization cp7_payroll_read;
revoke all on schema cp7_payroll from public,anon,authenticated,service_role;
grant usage on schema auth,erp to cp7_payroll_read;
grant execute on function auth.uid(),auth.jwt(),erp.get_my_access_v1(),erp.has_permission(text) to cp7_payroll_read;
-- Both accepted eligibility views use security_invoker: grant their complete,
-- explicit dependency closure, not schema-wide SELECT or elevated view ownership.
grant select on erp.v_payroll_eligible_work_lines,erp.v_payroll_production_work_eligibility,
 erp.laundry_delivery_lines,erp.laundry_deliveries,erp.laundry_receipt_lines,erp.laundry_receipts,
 erp.payroll_work_items,erp.payroll_settlements,erp.bs_case_components,erp.bs_cases,
 erp.contractors,erp.work_components,erp.work_completion_lines,erp.work_completion_events,
 erp.rework_component_lines,erp.rework_orders,erp.fg_unsourced_repair_wages_v1,erp.fg_unsourced_receipts_v1,
 erp.production_orders,erp.cutting_groups to cp7_payroll_read;

create function cp7_payroll.access_now(p_purpose text) returns jsonb
language plpgsql stable security invoker set search_path='' as $$
declare a jsonb;k text;
begin
 k:=case p_purpose when 'NOTA' then 'production.fg_handoff.view' when 'PAYROLL' then 'finance.payroll.view' end;
 if k is null or auth.uid() is null or coalesce(auth.jwt()->>'role','')<>'authenticated' then raise exception using errcode='42501',message='CP7_PAYROLL_ACCESS_DENIED';end if;
 a:=erp.get_my_access_v1();
 if a->'allowed' is distinct from 'true'::jsonb or not erp.has_permission(k) then raise exception using errcode='42501',message='CP7_PAYROLL_ACCESS_DENIED';end if;
 return jsonb_build_object('actor',auth.uid(),'profile',a->'profile','permissions',a->'permissions',
  'financial',erp.has_permission('finance.payroll.view'),'can_post_nota',erp.has_permission('production.fg_handoff.post'));
end $$;

create function cp7_payroll.source_lines() returns table(
 source_type text,source_id uuid,origin_id uuid,origin_number text,contractor_id uuid,contractor_name text,contractor_active boolean,
 po_id uuid,po_number text,cutting_group_id uuid,group_number text,bs_case_id uuid,work_component_id uuid,component_code text,component_name text,component_order integer,
 eligible_at timestamptz,source_qty integer,eligible_qty integer,allocated_qty integer,remaining_qty integer,held_qty integer,rate_snapshot numeric,remaining_amount numeric,eligibility_reason text,source_revision text
) language sql stable security invoker set search_path='' as $$
 select e.source_type,e.source_id,coalesce(w.id,ro.id,receipt.id),coalesce(w.completion_number,ro.rework_number,receipt.id::text)::text,
  e.contractor_id,c.contractor_name::text,c.is_active,e.po_id,po.po_number::text,e.cutting_group_id,cg.group_number::text,e.bs_case_id,
  e.work_component_id,wc.component_code::text,wc.component_name::text,wc.sequence_default,e.eligible_at,e.source_qty,e.eligible_qty,e.allocated_qty,e.remaining_qty,e.held_qty,e.rate_snapshot,e.remaining_amount,e.eligibility_reason,concat_ws(':',wl.xmin::text,w.xmin::text,rl.xmin::text,ro.xmin::text,repair.xmin::text,receipt.xmin::text)
 from erp.v_payroll_eligible_work_lines e join erp.contractors c on c.id=e.contractor_id join erp.work_components wc on wc.id=e.work_component_id
 left join erp.production_orders po on po.id=e.po_id left join erp.cutting_groups cg on cg.id=e.cutting_group_id
 left join erp.work_completion_lines wl on e.source_type='PRODUCTION' and wl.id=e.source_id left join erp.work_completion_events w on w.id=wl.completion_id
 left join erp.rework_component_lines rl on e.source_type='REWORK' and rl.id=e.source_id left join erp.rework_orders ro on ro.id=rl.rework_order_id
 left join erp.fg_unsourced_repair_wages_v1 repair on e.source_type='FG_REPAIR' and repair.id=e.source_id left join erp.fg_unsourced_receipts_v1 receipt on receipt.id=repair.receipt_id
$$;

create function cp7_payroll.source_cards(p_financial boolean) returns table(card_key text,contractor_id uuid,eligible_at timestamptz,search_text text,card jsonb)
language sql stable security invoker set search_path='' as $$
 with grouped as(
  select e.source_type,e.origin_id,e.origin_number,e.contractor_id,e.contractor_name,e.contractor_active,e.po_id,e.po_number,e.cutting_group_id,e.group_number,e.bs_case_id,
   min(e.eligible_at) eligible_at,count(*) line_count,
   md5(jsonb_agg(jsonb_build_array(e.source_id,e.work_component_id,e.source_qty,e.eligible_qty,e.allocated_qty,e.remaining_qty,e.held_qty,e.source_revision,e.eligible_at) order by e.source_id,e.work_component_id)::text) source_token,
   sum(e.remaining_amount) remaining_amount,
   jsonb_agg(jsonb_build_object('source_type',e.source_type,'source_id',e.source_id,'component_id',e.work_component_id,'component_code',e.component_code,'component_name',e.component_name,
    'source_qty',e.source_qty::text,'eligible_qty',e.eligible_qty::text,'allocated_qty',e.allocated_qty::text,'remaining_qty',e.remaining_qty::text,'held_qty',e.held_qty::text,
    'eligible_at',e.eligible_at,'eligibility_reason',e.eligibility_reason)
    ||case when p_financial then jsonb_build_object('rate',e.rate_snapshot::text,'amount',e.remaining_amount::text) else '{}'::jsonb end order by e.component_order,e.source_id) lines
  from cp7_payroll.source_lines() e
  group by e.source_type,e.origin_id,e.origin_number,e.contractor_id,e.contractor_name,e.contractor_active,e.po_id,e.po_number,e.cutting_group_id,e.group_number,e.bs_case_id
 )
 select source_type||':'||origin_id||':'||contractor_id,contractor_id,eligible_at,lower(concat_ws(' ',origin_number,contractor_name,po_number,group_number)),
  jsonb_build_object('card_key',source_type||':'||origin_id||':'||contractor_id,'source_type',source_type,'origin_id',origin_id,'origin_number',origin_number,'contractor_id',contractor_id,'contractor_name',contractor_name,
   'contractor_active',contractor_active,'po_id',po_id,'po_number',po_number,'cutting_group_id',cutting_group_id,'group_number',group_number,'bs_case_id',bs_case_id,'eligible_at',eligible_at,
   'line_count',line_count::text,'source_token',source_token,'lines',lines,'basis','NATIVE_REMAINING_COMPONENT_ENTITLEMENT')
   ||case when p_financial then jsonb_build_object('remaining_amount',remaining_amount::text) else '{}'::jsonb end
 from grouped
$$;

create function cp7_payroll.source_workspace(p_query jsonb) returns jsonb
language plpgsql stable security invoker set search_path='' as $$
declare a jsonb;q text;n integer;off integer;contractor uuid;rows jsonb;total bigint;
begin
 a:=cp7_payroll.access_now('NOTA');
 if jsonb_typeof(p_query) is distinct from 'object' or exists(select 1 from jsonb_object_keys(p_query) k where k not in('q','contractor_id','limit','offset'))
  or exists(select 1 from jsonb_each(p_query) e where e.key in('q','contractor_id') and jsonb_typeof(e.value) not in('string','null'))
  or(p_query?'limit' and (jsonb_typeof(p_query->'limit')<>'number' or(p_query->>'limit')!~'^[0-9]{1,3}$'))
  or(p_query?'offset' and (jsonb_typeof(p_query->'offset')<>'number' or(p_query->>'offset')!~'^[0-9]{1,7}$')) then raise exception 'CP7_PAYROLL_SOURCE_QUERY';end if;
 q:=btrim(coalesce(p_query->>'q',''));contractor:=(p_query->>'contractor_id')::uuid;n:=coalesce((p_query->>'limit')::integer,25);off:=coalesce((p_query->>'offset')::integer,0);
 if length(q)>120 or n not between 1 and 100 or off not between 0 and 1000000 then raise exception 'CP7_PAYROLL_SOURCE_QUERY';end if;
 with filtered as materialized(select * from cp7_payroll.source_cards((a->>'financial')::boolean) c where(contractor is null or c.contractor_id=contractor) and(q='' or strpos(c.search_text,lower(q))>0)),
 page as(select * from filtered order by eligible_at,card_key limit n offset off)
 select(select count(*) from filtered),coalesce(jsonb_agg(card order by eligible_at,card_key),'[]') into total,rows from page;
 return jsonb_build_object('contract_version','cp7.nota-sources.v1','read_at',statement_timestamp(),'financial_captured',a->'financial','can_post',a->'can_post_nota',
  'page',jsonb_build_object('rows',rows,'total',total::text,'offset',off,'limit',n,'next_offset',case when off+jsonb_array_length(rows)<total then off+jsonb_array_length(rows) else null end));
end $$;
