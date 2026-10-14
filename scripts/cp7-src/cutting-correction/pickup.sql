-- SG-01 (Fable FABLE-009, Astra SG-01): reverse a POSTED cutting pickup (Bagi Potongan) before any sewing or other use.
-- The pickup becomes REVERSED (its batches and allocations stay as history), the group returns to CUT without a pickup
-- time, its executor name and the PO status, stage and Mandor return to the values the POST changed, read back from the
-- Native audit trail of that POST. No stock, journal, WIP or payroll fact exists for a pickup, so none is written; the
-- fabric stays posted and the group is back in the "waiting to be distributed" queue for the ordinary Native POST.
-- Two declared Native deltas (cp7_pickup_reversal_bundle.py) admit exactly these two writes, only inside this command:
-- erp.guard_cutting_pickup_lifecycle (POSTED->REVERSED) and erp.normalize_cutting_group_pickup (clear picked_up_at).
create table cp7_cutting_correction.pickup_requests(
 actor uuid not null,request_id uuid not null,payload jsonb not null,expected_version text not null,
 response jsonb,primary key(actor,request_id)
);
create table cp7_cutting_correction.pickup_history(
 actor uuid not null,request_id uuid not null,pickup_id uuid not null references erp.cutting_pickups,
 group_id uuid not null references erp.cutting_groups,original_source jsonb not null,restored jsonb not null,reason text not null,
 recorded_at timestamptz not null default clock_timestamp(),primary key(actor,request_id)
);
create table cp7_cutting_correction.pickup_context(
 backend_pid integer not null,transaction_id bigint not null,actor uuid not null,pickup_id uuid not null,group_id uuid not null,
 primary key(backend_pid,transaction_id)
);
alter table cp7_cutting_correction.pickup_requests owner to postgres;
alter table cp7_cutting_correction.pickup_history owner to postgres;
alter table cp7_cutting_correction.pickup_context owner to postgres;
alter table cp7_cutting_correction.pickup_requests enable row level security;
alter table cp7_cutting_correction.pickup_history enable row level security;
alter table cp7_cutting_correction.pickup_context enable row level security;
create policy private_pickup_requests on cp7_cutting_correction.pickup_requests for all using(false)with check(false);
create policy private_pickup_history on cp7_cutting_correction.pickup_history for all using(false)with check(false);
create policy private_pickup_context on cp7_cutting_correction.pickup_context for all using(false)with check(false);
revoke all on cp7_cutting_correction.pickup_requests,cp7_cutting_correction.pickup_history,cp7_cutting_correction.pickup_context
 from public,anon,authenticated,service_role,cp7_capture,cp7_cutting_read,cp7_cutting_write;
create trigger immutable_pickup_history before update or delete on cp7_cutting_correction.pickup_history
 for each row execute function cp7_cutting_correction.immutable();
create trigger immutable_pickup_history_truncate before truncate on cp7_cutting_correction.pickup_history
 for each statement execute function cp7_cutting_correction.immutable();

create function cp7_cutting_correction.pickup_access_now()returns jsonb
language plpgsql volatile security definer set search_path=''as $$
declare a jsonb;permission text;
begin
 if auth.uid()is null or auth.jwt()->>'role'is distinct from'authenticated'then
  raise exception using errcode='42501',message='CP7_PICKUP_REVERSAL_DENIED';end if;
 a:=erp.get_my_access_v1();
 if a->'allowed'is distinct from'true'::jsonb or coalesce(a->'profile'->>'role_code','')not in('OWNER','ADMIN')then
  raise exception using errcode='42501',message='CP7_PICKUP_REVERSAL_DENIED';end if;
 foreach permission in array array['production.distribution.view','production.distribution.edit_draft','production.distribution.post']loop
  if erp.has_permission(permission)is distinct from true then
   raise exception using errcode='42501',message='CP7_PICKUP_REVERSAL_DENIED';end if;
 end loop;
 return a;
end $$;

-- Read by the two declared Native deltas: true only inside this command's own transaction, for its own pickup/group.
create function cp7_cutting_correction.pickup_reversal_admitted(p_pickup uuid)returns boolean
language sql stable security definer set search_path=''as $$
 select exists(select 1 from cp7_cutting_correction.pickup_context c where c.backend_pid=pg_backend_pid()
  and c.transaction_id=txid_current()and c.pickup_id=p_pickup)$$;
create function cp7_cutting_correction.pickup_group_admitted(p_group uuid)returns boolean
language sql stable security definer set search_path=''as $$
 select exists(select 1 from cp7_cutting_correction.pickup_context c where c.backend_pid=pg_backend_pid()
  and c.transaction_id=txid_current()and c.group_id=p_group)$$;

-- The POST of the pickup as the Native audit trail recorded it: one DRAFT->POSTED row of the pickup; in the same
-- statement the group row that set its pickup time, and the PO rows (net effect: first old, last new).
create function cp7_cutting_correction.pickup_post_audit(p_pickup uuid)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare p erp.cutting_pickups;g erp.cutting_groups;at timestamptz;n integer;grp jsonb;po jsonb;
begin
 select *into p from erp.cutting_pickups where id=p_pickup;
 if p.id is null then return null;end if;
 select *into g from erp.cutting_groups where id=p.cutting_group_id;
 select count(*),min(a.changed_at)into n,at from erp.audit_logs a where a.entity_type='cutting_pickups'and a.entity_id=p.id and a.action='UPDATE'
  and a.old_data->>'status'='DRAFT'and a.new_data->>'status'='POSTED';
 if n<>1 then return jsonb_build_object('found',false,'reason','PICKUP_POST_ROW','rows',n);end if;
 select count(*),min(jsonb_build_object('old',a.old_data,'new',a.new_data)::text)::jsonb into n,grp from erp.audit_logs a
  where a.entity_type='cutting_groups'and a.entity_id=g.id and a.action='UPDATE'and a.changed_at=at
   and a.old_data->'picked_up_at'='null'::jsonb and a.new_data->'picked_up_at'<>'null'::jsonb;
 if n<>1 then return jsonb_build_object('found',false,'reason','GROUP_POST_ROW','rows',n);end if;
 select jsonb_build_object('old',(array_agg(a.old_data order by a.id))[1],'new',(array_agg(a.new_data order by a.id desc))[1],'rows',count(*))
  into po from erp.audit_logs a where a.entity_type='production_orders'and a.entity_id=g.po_id and a.action='UPDATE'and a.changed_at=at;
 if coalesce((po->>'rows')::integer,0)<1 then return jsonb_build_object('found',false,'reason','PO_POST_ROW','rows',0);end if;
 return jsonb_build_object('found',true,'statement_at',at,'group',grp,'po',po);
end $$;

-- Everything the reversal reads, for the review token; blockers name each document that holds the pickup.
create function cp7_cutting_correction.pickup_snapshot(p_group uuid)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare g erp.cutting_groups;po erp.production_orders;p erp.cutting_pickups;audit jsonb;b jsonb:='[]';
 others boolean;bound jsonb:='[]';target_status text;target_stage text;clear_mandor boolean:=false;
begin
 select *into g from erp.cutting_groups where id=p_group;
 if g.id is null then return null;end if;
 select *into po from erp.production_orders where id=g.po_id;
 select *into p from erp.cutting_pickups where cutting_group_id=g.id and status='POSTED';
 if p.id is null then
  b:=b||jsonb_build_array(jsonb_build_object('kind','NO_POSTED_PICKUP','id',g.id,'label',g.group_number));
 else
  audit:=cp7_cutting_correction.pickup_post_audit(p.id);
 end if;
 if g.status is distinct from'PICKED_UP'or g.picked_up_at is null or(p.id is not null and g.picked_up_at is distinct from p.picked_up_at)then
  b:=b||jsonb_build_array(jsonb_build_object('kind','GROUP_STATE','id',g.id,'label',g.group_number,'status',g.status));end if;
 if erp.cutting_group_has_downstream_after_pickup(g.id)then
  b:=b||jsonb_build_array(jsonb_build_object('kind','DOWNSTREAM','id',g.id,'label',g.group_number));end if;
 -- Every document that can point at the group or the pickup's batches, in any status (drafts included).
 b:=b||coalesce((select jsonb_agg(x order by x->>'kind',x->>'id')from(
   select jsonb_build_object('kind','WIP_EVENT','id',w.id)x from erp.wip_stage_events w where w.cutting_group_id=g.id
   union all select jsonb_build_object('kind','WORK_COMPLETION','id',w.id,'status',w.status)from erp.work_completion_events w where w.cutting_group_id=g.id
   union all select jsonb_build_object('kind','QC','id',q.inspection_id)from erp.qc_inspection_items q where q.cutting_group_id=g.id
   union all select jsonb_build_object('kind','LAUNDRY','id',l.delivery_id)from erp.laundry_delivery_lines l where l.cutting_group_id=g.id
   union all select jsonb_build_object('kind','LAUNDRY_BATCH','id',s.id)from erp.laundry_delivery_batch_size_lines s
    join erp.cutting_distribution_batches d on d.id=s.distribution_batch_id where d.pickup_id=p.id
   union all select jsonb_build_object('kind','FG_LOT','id',f.id)from erp.fg_lots f where f.cutting_group_id=g.id
   union all select jsonb_build_object('kind','BS_CASE','id',c.id,'status',c.status)from erp.bs_cases c where c.cutting_group_id=g.id
   union all select jsonb_build_object('kind','SCRAP','id',s.id)from erp.scrap_batches s where s.source_cutting_group_id=g.id
   union all select jsonb_build_object('kind','QTY_CORRECTION','id',c.id)from erp.cutting_qty_correction_lines c where c.cutting_group_id=g.id
   union all select jsonb_build_object('kind','SEWING_TERMINAL','id',t.id)from erp.sewing_terminal_events t where t.cutting_group_id=g.id
   union all select jsonb_build_object('kind','ATTENDANCE_POOL','id',a.id)from erp.attendance_hpp_pool_allocations a where a.cutting_group_id=g.id
   union all select jsonb_build_object('kind','WIP_FLAG','id',f.id)from erp.wip_control_flags f where f.cutting_group_id=g.id
   union all select jsonb_build_object('kind','POCKET','id',d.pool_id)from erp.pocket_period_destinations d where d.cutting_group_id=g.id)z),'[]');
 if po.status in('ON_HOLD','FINISHED','CANCELLED')then
  b:=b||jsonb_build_array(jsonb_build_object('kind','PO_STATE','id',po.id,'label',po.po_number,'status',po.status));end if;
 if p.id is not null and coalesce(audit->>'found','false')<>'true'then
  b:=b||jsonb_build_array(jsonb_build_object('kind','NO_POST_AUDIT','id',p.id,'reason',audit->>'reason'));end if;
 if audit->>'found'='true'then
  -- Group: unchanged since the POST (same pickup time and executor), restored to the executor before it.
  if g.executor_name is distinct from audit->'group'->'new'->>'executor_name'
   or g.picked_up_at is distinct from(audit->'group'->'new'->>'picked_up_at')::timestamptz then
   b:=b||jsonb_build_array(jsonb_build_object('kind','GROUP_CHANGED_SINCE_PICKUP','id',g.id,'label',g.group_number));end if;
  -- PO: stays at its stage while another group of it is still picked up; otherwise back to its values before the
  -- POST, only if nothing changed them since.
  select exists(select 1 from erp.cutting_groups x where x.po_id=po.id and x.id<>g.id and x.picked_up_at is not null)into others;
  if others then target_status:=po.status;target_stage:=po.current_stage;
  else
   if po.status is distinct from audit->'po'->'new'->>'status'or po.current_stage is distinct from audit->'po'->'new'->>'current_stage'then
    b:=b||jsonb_build_array(jsonb_build_object('kind','PO_CHANGED_SINCE_PICKUP','id',po.id,'label',po.po_number));end if;
   target_status:=audit->'po'->'old'->>'status';target_stage:=audit->'po'->'old'->>'current_stage';
   if target_status not in('DRAFT','CUTTING')or target_stage is distinct from'CUTTING'then
    b:=b||jsonb_build_array(jsonb_build_object('kind','PO_STAGE_BEFORE_PICKUP','id',po.id,'label',po.po_number,'status',target_status));end if;
  end if;
  -- Mandor: cleared only when this POST set it and nothing else binds that Mandor to the PO.
  if audit->'po'->'old'->'contractor_id'='null'::jsonb and po.contractor_id::text=audit->'po'->'new'->>'contractor_id'
   and po.contractor_id=p.contractor_id then
   bound:=coalesce((select jsonb_agg(x order by x->>'kind',x->>'id')from(
     select jsonb_build_object('kind','OTHER_PICKUP','id',o.id)x from erp.cutting_pickups o join erp.cutting_groups og on og.id=o.cutting_group_id
      where og.po_id=po.id and o.id<>p.id and o.status in('DRAFT','POSTED')
     union all select jsonb_build_object('kind','MATERIAL_ISSUE','id',i.id)from erp.contractor_material_issues i where i.po_id=po.id and i.status<>'DRAFT'
     union all select jsonb_build_object('kind','WORK_COMPLETION','id',w.id)from erp.work_completion_events w where w.po_id=po.id and w.status<>'DRAFT'
     union all select jsonb_build_object('kind','PAYROLL_WORK','id',w.id)from erp.payroll_work_items w where w.po_id=po.id
      and exists(select 1 from erp.payroll_settlements s where s.id=w.payroll_id and s.status<>'REVERSED')
     union all select jsonb_build_object('kind','WORK_SNAPSHOT','id',s.id)from erp.po_work_component_snapshots s where s.po_id=po.id
     union all select jsonb_build_object('kind','ACCESSORY_ENTITLEMENT','id',e.id)from erp.contractor_accessory_reimbursement_entitlements e
      where e.po_id=po.id and e.payroll_status<>'CANCELLED'
     union all select jsonb_build_object('kind','REWORK','id',r.id)from erp.rework_orders r join erp.bs_cases c on c.id=r.bs_case_id
      where c.po_id=po.id and r.status<>'CANCELLED')z),'[]');
   clear_mandor:=jsonb_array_length(bound)=0;
  end if;
 end if;
 return jsonb_build_object('group',to_jsonb(g),'po',to_jsonb(po),'pickup',to_jsonb(p),
  'batches',(select coalesce(jsonb_agg(jsonb_build_object('batch',to_jsonb(d),'allocations',(select coalesce(jsonb_agg(to_jsonb(a)order by a.id),'[]')
    from erp.cutting_distribution_allocations a where a.batch_id=d.id))order by d.batch_no),'[]')from erp.cutting_distribution_batches d where d.pickup_id=p.id),
  'audit',audit,'blockers',b,'restore',jsonb_build_object('executor_name',audit->'group'->'old'->'executor_name','po_status',target_status,
   'po_stage',target_stage,'clear_mandor',clear_mandor,'mandor_bound_by',bound,'other_groups_picked_up',coalesce(others,false)));
end $$;

create function cp7_cutting_correction.pickup_workspace(p_group uuid)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;s jsonb;
begin
 a:=cp7_cutting_correction.pickup_access_now();s:=cp7_cutting_correction.pickup_snapshot(p_group);
 if s is null then raise exception 'CP7_PICKUP_REVERSAL_NOT_FOUND';end if;
 if cp7_cutting_correction.pickup_access_now()is distinct from a then raise exception using errcode='42501',message='CP7_PICKUP_REVERSAL_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.pickup-reversal-workspace.v1','group_id',p_group,'po_id',s->'group'->>'po_id',
  'number',s->'group'->>'group_number','po_number',s->'po'->>'po_number','pickup_id',s->'pickup'->>'id',
  'pickup_version',s->'pickup'->>'row_version','picked_up_at',s->'pickup'->>'picked_up_at','contractor_id',s->'pickup'->>'contractor_id',
  'contractor_name',(select c.contractor_name from erp.contractors c where c.id=(s->'pickup'->>'contractor_id')::uuid),
  'batch_count',jsonb_array_length(s->'batches'),
  'pieces',(select coalesce(sum((x->>'qty_pcs')::bigint),0)from jsonb_array_elements(s->'batches')bt,jsonb_array_elements(bt->'allocations')x),
  'restore',s->'restore','review_token',md5(s::text),'eligible',jsonb_array_length(s->'blockers')=0,'blockers',s->'blockers',
  'business_DML',false);
end $$;

create function cp7_cutting_correction.pickup_command(p jsonb,p_request uuid,p_expected text)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;old cp7_cutting_correction.pickup_requests;g erp.cutting_groups;pk erp.cutting_pickups;po erp.production_orders;
 s jsonb;r jsonb;answer jsonb;v_actor uuid;after_po erp.production_orders;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_cutting_correction.pickup_access_now();
 if p_request is null or p_expected is null or p_expected!~'^[1-9][0-9]{0,18}$'
  or jsonb_typeof(p)is distinct from'object'or not(p?&array['group_id','pickup_id','review_token','change_reason'])
  or(select count(*)from jsonb_object_keys(p))<>4
  or jsonb_typeof(p->'group_id')is distinct from'string'or coalesce(p->>'group_id','')!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  or jsonb_typeof(p->'pickup_id')is distinct from'string'or coalesce(p->>'pickup_id','')!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  or jsonb_typeof(p->'review_token')is distinct from'string'or coalesce(p->>'review_token','')!~'^[a-f0-9]{32}$'
  or jsonb_typeof(p->'change_reason')is distinct from'string'or length(btrim(p->>'change_reason'))not between 5 and 1000 then
  raise exception 'CP7_PICKUP_REVERSAL_FIELDS';end if;
 insert into cp7_cutting_correction.pickup_requests values(auth.uid(),p_request,p,p_expected,null)on conflict do nothing;
 select *into strict old from cp7_cutting_correction.pickup_requests where actor=auth.uid()and request_id=p_request for update;
 if old.payload is distinct from p or old.expected_version is distinct from p_expected then raise exception 'CP7_PICKUP_REVERSAL_REQUEST_CHANGED';end if;
 if cp7_cutting_correction.pickup_access_now()is distinct from a then raise exception using errcode='42501',message='CP7_PICKUP_REVERSAL_ACCESS_CHANGED';end if;
 if old.response is not null then return old.response;end if;
 -- Same lock order as the Native pickup writer: cutting flow lock, group, PO, pickup.
 perform pg_advisory_xact_lock(hashtextextended('CP6FLOW:'||(p->>'group_id'),0));
 select *into g from erp.cutting_groups where id=(p->>'group_id')::uuid for update;
 if g.id is null then raise exception 'CP7_PICKUP_REVERSAL_NOT_FOUND';end if;
 select *into po from erp.production_orders where id=g.po_id for update;
 select *into pk from erp.cutting_pickups where id=(p->>'pickup_id')::uuid for update;
 if pk.id is null or pk.cutting_group_id is distinct from g.id then raise exception 'CP7_PICKUP_REVERSAL_NOT_FOUND';end if;
 if cp7_cutting_correction.pickup_access_now()is distinct from a then raise exception using errcode='42501',message='CP7_PICKUP_REVERSAL_ACCESS_CHANGED';end if;
 s:=cp7_cutting_correction.pickup_snapshot(g.id);
 if pk.row_version::text is distinct from p_expected or s->'pickup'->>'id'is distinct from pk.id::text
  or md5(s::text)is distinct from p->>'review_token'then raise exception 'CP7_PICKUP_REVERSAL_STALE_REVIEW';end if;
 if jsonb_array_length(s->'blockers')<>0 then raise exception 'CP7_PICKUP_REVERSAL_DEPENDENCIES: %',s->'blockers';end if;
 v_actor:=erp.current_app_user_id();
 if v_actor is null then raise exception using errcode='42501',message='CP7_PICKUP_REVERSAL_DENIED';end if;
 perform set_config('app.change_reason',btrim(p->>'change_reason'),true);
 insert into cp7_cutting_correction.pickup_context values(pg_backend_pid(),txid_current(),auth.uid(),pk.id,g.id);
 update erp.cutting_pickups set status='REVERSED',reversed_by=v_actor,reversed_at=clock_timestamp(),
  reversal_reason=btrim(p->>'change_reason'),updated_at=clock_timestamp()where id=pk.id;
 update erp.cutting_groups set picked_up_at=null,status='CUT',executor_name=s->'restore'->>'executor_name',updated_at=clock_timestamp()
  where id=g.id;
 update erp.production_orders set status=s->'restore'->>'po_status',current_stage=s->'restore'->>'po_stage',
  contractor_id=case when(s->'restore'->>'clear_mandor')::boolean then null else contractor_id end,updated_at=clock_timestamp()
  where id=po.id and(status is distinct from s->'restore'->>'po_status'or current_stage is distinct from s->'restore'->>'po_stage'
   or((s->'restore'->>'clear_mandor')::boolean and contractor_id is not null));
 delete from cp7_cutting_correction.pickup_context where backend_pid=pg_backend_pid()and transaction_id=txid_current();
 if cp7_cutting_correction.pickup_access_now()is distinct from a then raise exception using errcode='42501',message='CP7_PICKUP_REVERSAL_ACCESS_CHANGED';end if;
 -- Post-conditions: the pickup is REVERSED, the group waits again with its fabric still posted, and nothing downstream appeared.
 select *into after_po from erp.production_orders where id=po.id;
 if not exists(select 1 from erp.cutting_pickups x where x.id=pk.id and x.status='REVERSED'and x.reversed_by=v_actor)
  or not exists(select 1 from erp.cutting_groups x where x.id=g.id and x.status='CUT'and x.picked_up_at is null and x.material_issue_posted
   and not x.material_return_posted and x.executor_name is not distinct from s->'restore'->>'executor_name')
  or exists(select 1 from erp.cutting_pickups x where x.cutting_group_id=g.id and x.status in('DRAFT','POSTED'))
  or erp.cutting_group_has_downstream_after_pickup(g.id)
  or after_po.status is distinct from s->'restore'->>'po_status'or after_po.current_stage is distinct from s->'restore'->>'po_stage'
  or((s->'restore'->>'clear_mandor')::boolean and after_po.contractor_id is not null)then
  raise exception 'CP7_PICKUP_REVERSAL_INCOMPLETE';end if;
 r:=jsonb_build_object('pickup_status','REVERSED','group_status','CUT','po_status',after_po.status,'po_stage',after_po.current_stage,
  'mandor_cleared',(s->'restore'->>'clear_mandor')::boolean,'mandor_bound_by',s->'restore'->'mandor_bound_by');
 insert into cp7_cutting_correction.pickup_history values(auth.uid(),p_request,pk.id,g.id,s,r,btrim(p->>'change_reason'),clock_timestamp());
 answer:=jsonb_build_object('contract_version','cp7.pickup-reversal-outcome.v1','kind','COMMITTED_OUTCOME','action','REVERSE_PICKUP',
  'request_id',p_request,'group_id',g.id,'pickup_id',pk.id,'po_id',po.id,'number',g.group_number,'result',r);
 update cp7_cutting_correction.pickup_requests set response=answer where actor=auth.uid()and request_id=p_request;
 return answer;
end $$;

create function public.erp_cp7_get_pickup_reversal_v1(p_group uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_cutting_correction.pickup_workspace(p_group)$$;
create function public.erp_cp7_reverse_pickup_v1(p_payload jsonb,p_request uuid,p_expected text)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_cutting_correction.pickup_command(p_payload,p_request,p_expected)$$;
alter function cp7_cutting_correction.pickup_access_now()owner to postgres;
alter function cp7_cutting_correction.pickup_reversal_admitted(uuid)owner to postgres;
alter function cp7_cutting_correction.pickup_group_admitted(uuid)owner to postgres;
alter function cp7_cutting_correction.pickup_post_audit(uuid)owner to postgres;
alter function cp7_cutting_correction.pickup_snapshot(uuid)owner to postgres;
alter function cp7_cutting_correction.pickup_workspace(uuid)owner to postgres;
alter function cp7_cutting_correction.pickup_command(jsonb,uuid,text)owner to postgres;
grant create on schema public to cp7_cutting_read,cp7_cutting_write;
alter function public.erp_cp7_get_pickup_reversal_v1(uuid)owner to cp7_cutting_read;
alter function public.erp_cp7_reverse_pickup_v1(jsonb,uuid,text)owner to cp7_cutting_write;
revoke create on schema public from cp7_cutting_read,cp7_cutting_write;
revoke all on function cp7_cutting_correction.pickup_access_now(),cp7_cutting_correction.pickup_reversal_admitted(uuid),
 cp7_cutting_correction.pickup_group_admitted(uuid),cp7_cutting_correction.pickup_post_audit(uuid),cp7_cutting_correction.pickup_snapshot(uuid),
 cp7_cutting_correction.pickup_workspace(uuid),cp7_cutting_correction.pickup_command(jsonb,uuid,text)
 from public,anon,authenticated,service_role,cp7_capture,cp7_cutting_read,cp7_cutting_write;
grant execute on function cp7_cutting_correction.pickup_workspace(uuid)to cp7_cutting_read;
grant execute on function cp7_cutting_correction.pickup_command(jsonb,uuid,text)to cp7_cutting_write;
revoke all on function public.erp_cp7_get_pickup_reversal_v1(uuid),public.erp_cp7_reverse_pickup_v1(jsonb,uuid,text)from public,anon,authenticated,service_role,cp7_capture;
grant execute on function public.erp_cp7_get_pickup_reversal_v1(uuid),public.erp_cp7_reverse_pickup_v1(jsonb,uuid,text)to authenticated;
