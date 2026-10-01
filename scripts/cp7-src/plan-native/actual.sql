-- Read one immutable plan's linked Native origin. Reuse the existing conserved
-- physical graph; estimates, other groups and current FG stock are not input.
create function cp7_plan_native.actual_source(p_run uuid,p_group uuid,p_target text)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;r cp7_analysis_native.runs%rowtype;e jsonb;product jsonb;
 captured jsonb;normalized jsonb;native_group jsonb;identities jsonb;positions jsonb:='[]';
 at timestamptz;state text;reason text;hash text;ref jsonb;facts jsonb:='{}';
 total jsonb;pos jsonb;identity jsonb;k text;qty numeric;matched numeric:=0;other_fg numeric:=0;
 fg_known boolean:=true;values_by_key jsonb;
begin
 a:=cp7_private.access_now();
 if not erp.has_permission('production.cutting.view')then raise exception using errcode='42501',message='CP7_PLAN_ACCESS_DENIED';end if;
 select *into r from cp7_analysis_native.runs where id=p_run and actor=(a->>'actor')::uuid;
 if r.id is null then raise exception using errcode='42501',message='CP7_PLAN_ORIGINAL_UNAVAILABLE';end if;
 e:=cp7_analysis_native.serve(p_run); -- Current protected finance/preflight authority, including stale Originals.
 select value into product from jsonb_array_elements(r.facts->'facts'->'products')
  where value->>'root_id'||':'||(value->>'size_id')=p_target;
 if product is null then raise exception 'CP7_PLAN_TARGET';end if;
 -- Header, raw facts, normalization and FG identity all use this one outer
 -- statement's MVCC snapshot. Capture time is explicit, never a future fact.
 with clock as materialized(select clock_timestamp() captured_at),
 header as materialized(select jsonb_build_object('id',cg.id,'number',cg.group_number,
  'po_id',cg.po_id,'model_id',po.model_id,'revision',cg.row_version::text,
  'cut_at',cg.cut_at,'material_issue_posted',cg.material_issue_posted,'status',cg.status) g
  from erp.cutting_groups cg join erp.production_orders po on po.id=cg.po_id where cg.id=p_group),
 cap as materialized(select cp7_wip.capture_cutting_sources(
  case when p_group is null then array[]::uuid[]else array[p_group]end,clock.captured_at)c,clock.captured_at from clock),
 norm as materialized(select cap.c,cap.captured_at,cp7_wip.normalize_cutting(cap.c)n from cap),
 ids as materialized(
  select 'FGQC:'||(q.value->>'id') position_key,q.value->>'product_root' root_id,q.value->>'size_id' size_id
   from cap cross join lateral jsonb_array_elements(cap.c#>'{facts,qc}')q(value)
  union all
  select 'FGREWORK:'||(rw.value->>'id'),coalesce(p.identity_root_id,p.id)::text,p.size_id::text
   from cap cross join lateral jsonb_array_elements(cap.c#>'{facts,reworks}')rw(value)
   join erp.fg_lots lot on lot.id=(rw.value->>'good_fg_lot_id')::uuid join erp.products p on p.id=lot.product_id
  union all
  select 'FGDISPOSITION:'||(bs.value->>'bs_resolution_id'),coalesce(p.identity_root_id,p.id)::text,p.size_id::text
   from cap cross join lateral jsonb_array_elements(cap.c#>'{facts,bs_fg}')bs(value)
   join erp.fg_lots lot on lot.id=(bs.value->>'lot_id')::uuid join erp.products p on p.id=lot.product_id)
 select norm.c,norm.n,norm.captured_at,(select header.g from header),
  coalesce((select jsonb_agg(jsonb_build_object('position_key',ids.position_key,'root_id',ids.root_id,'size_id',ids.size_id)order by ids.position_key)from ids),'[]'::jsonb)
 into captured,normalized,at,native_group,identities from norm;
 ref:=case when native_group is null then '[]'::jsonb else jsonb_build_array(
  cp7_wip.ref('erp.cutting_groups',p_group::text,native_group->>'revision'))end;
 if p_group is null then state:='NOT_STARTED';reason:='NO_LINKED_NATIVE_INTENT';
 elsif native_group is null then state:='UNKNOWN';reason:='LINKED_NATIVE_GROUP_MISSING';
 elsif native_group->>'model_id'<>product->>'model_id'then state:='UNKNOWN';reason:='LINKED_NATIVE_MODEL_CHANGED';
 elsif (native_group->>'cut_at')::timestamptz>at then state:='UNKNOWN';reason:='LINKED_NATIVE_CUT_OUTSIDE_CAPTURE_CLOCK';
 elsif native_group->'material_issue_posted'<>'true'::jsonb then state:='NOT_STARTED';reason:='NATIVE_DRAFT_NOT_PHYSICAL_PRODUCTION';
 elsif normalized->>'status'<>'COMPLETE'then state:=case when normalized->>'status'='CONFLICT'then'CONFLICT'else'UNKNOWN'end;reason:=normalized->>'reason';
 else
  select value into total from jsonb_array_elements(normalized->'totals')where value->>'pool_key'='CUT:'||p_group::text||':'||(product->>'size_id');
  if total is null then state:='UNKNOWN';reason:='LINKED_NATIVE_EXACT_SIZE_UNPROVEN';
  else
   state:='COMPLETE';reason:='CONSERVED_LINKED_NATIVE_EXACT_SIZE';
   for pos in select value from jsonb_array_elements(normalized->'positions')
    where value->>'pool_key'=total->>'pool_key'order by value->>'key'loop
    identity:=null;qty:=(pos->>'remaining_pcs')::numeric;
    if pos->>'stage'='FG'and qty>0 then
     select value into identity from jsonb_array_elements(identities)where value->>'position_key'=pos->>'key';
     if identity is null or identity->>'size_id'<>product->>'size_id'then fg_known:=false;identity:=null;
     elsif identity->>'root_id'=product->>'root_id'then matched:=matched+qty;
     else other_fg:=other_fg+qty;end if;
    end if;
    positions:=positions||jsonb_build_array(pos||jsonb_build_object('fg_identity',identity));
   end loop;
  end if;
 end if;
 values_by_key:=case when state='COMPLETE'then jsonb_build_object(
  'input_pcs',total->'input_pcs','wip_pcs',total->'wip_pcs','group_fg_pcs',total->'fg_pcs',
  'bs_pcs',total->'bs_pcs','withheld_pcs',total->'withheld_pcs','exited_pcs',total->'exited_pcs',
  'matched_fg_pcs',matched::text,'other_root_fg_pcs',other_fg::text)
 else jsonb_build_object('input_pcs','0','wip_pcs','0','group_fg_pcs','0','bs_pcs','0',
  'withheld_pcs','0','exited_pcs','0','matched_fg_pcs','0','other_root_fg_pcs','0')end;
 foreach k in array array['input_pcs','wip_pcs','group_fg_pcs','bs_pcs','withheld_pcs','exited_pcs','matched_fg_pcs','other_root_fg_pcs']loop
  if state in('UNKNOWN','CONFLICT')or(state='COMPLETE'and not fg_known and k in('matched_fg_pcs','other_root_fg_pcs'))then
   facts:=facts||jsonb_build_object(k,jsonb_build_object('state','UNKNOWN','unit','PCS','reason',
    case when state='COMPLETE'then'FG_PHYSICAL_ROOT_UNPROVEN'else reason end,'refs',ref));
  else facts:=facts||jsonb_build_object(k,jsonb_build_object('state','KNOWN','unit','PCS','value',values_by_key->k,'refs',ref));end if;
 end loop;
 hash:=encode(extensions.digest(convert_to(jsonb_build_object('native_group',native_group,
  'cutting_facts',captured->'facts','capture_status',captured->'status','fg_identities',identities)::text,'UTF8'),'sha256'),'hex');
 -- A concurrent authority loss cannot return the preceding protected result.
 perform cp7_analysis_native.serve(p_run);
 if cp7_private.access_now()is distinct from a or not erp.has_permission('production.cutting.view')then
  raise exception using errcode='42501',message='CP7_PLAN_ACCESS_CHANGED';end if;
 return jsonb_build_object('captured_at',at,'source_hash',hash,'state',state,'reason',reason,
  'original_source_state',e->'source_state','native_group',native_group,'size_id',product->'size_id',
  'physical_root_id',product->'root_id','facts',facts,'positions',positions,
  'scope','ONE_LINKED_NATIVE_GROUP_EXACT_SIZE','fg_basis','PRODUCTION_DISPOSITION_NOT_CURRENT_ON_HAND');
end $$;

create function cp7_plan_native.actual(p_draft uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;r cp7_plan_native.drafts%rowtype;i cp7_plan_native.intents%rowtype;
 actual jsonb;planned numeric;remaining jsonb;outcome jsonb;
begin
 a:=cp7_plan_native.access_now('READ');
 select *into r from cp7_plan_native.drafts where id=p_draft and actor=(a->>'actor')::uuid;
 if r.id is null then raise exception using errcode='42501',message='CP7_PLAN_DRAFT_UNAVAILABLE';end if;
 select *into i from cp7_plan_native.intents where draft_id=r.id and actor=r.actor;
 select coalesce(sum((yield.value->>'qty_pcs')::numeric),0)into planned
  from jsonb_array_elements(r.payload#>'{cutting,rolls}')roll(value)
  cross join lateral jsonb_array_elements(roll.value->'yields')yield(value);
 actual:=cp7_plan_native.actual_source(r.run_id,i.cutting_group_id,r.target_key);
 if actual#>>'{facts,matched_fg_pcs,state}'='KNOWN'then
  remaining:=jsonb_build_object('state','KNOWN','unit','PCS','value',greatest(planned-(actual#>>'{facts,matched_fg_pcs,value}')::numeric,0)::text,'refs',actual#>'{facts,matched_fg_pcs,refs}');
 else remaining:=jsonb_build_object('state','UNKNOWN','unit','PCS','reason','MATCHED_NATIVE_FG_UNPROVEN','refs',actual#>'{facts,matched_fg_pcs,refs}');end if;
 outcome:=jsonb_build_object('contract_version','cp7.plan-actual.v1','actor_scope_id',r.actor,
  'draft_id',r.id,'plan_id',r.plan_id,'revision',r.revision::text,'run_id',r.run_id,'target_key',r.target_key,
  'original_source_hash',r.source_hash,'composition_hash',r.composition_hash,'planned_pcs',planned::text,
  'planned_basis','IMMUTABLE_OPERATOR_DRAFT_ESTIMATE','native_intent_id',i.id,'actual',actual,
  'remaining_to_plan_pcs',remaining,'comparison_scope','LINKED_DRAFT_ONLY_NOT_ALL_PO_OR_WAREHOUSE',
  'reservation_created',false,'production_go',false);
 if cp7_plan_native.access_now('READ')is distinct from a then raise exception using errcode='42501',message='CP7_PLAN_ACCESS_CHANGED';end if;
 return outcome;
end $$;
