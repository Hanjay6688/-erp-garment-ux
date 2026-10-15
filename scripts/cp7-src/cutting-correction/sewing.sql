-- D14-14 gap G1: SELESAI DIJAHIT from the connected WIP & Sewing screen, like the UX demo ("SELESAI DIJAHIT __ / N pcs").
-- One command, one transaction, through the accepted Native writers only:
--  1. erp.ensure_po_work_component_snapshots_v2 commits the PO work BOM/rate snapshot at the sewing physical time (no-op
--     when it exists);
--  2. a DRAFT erp.work_completion_events row for the picked-up group and its Mandor with one line per base snapshot component
--     (qty completed = qty payable = the sewn pieces; the Native trigger sets the rate from the snapshot), posted by
--     erp.post_work_completion (WORK_COMPLETION journal: Dr WIP / Cr CONTRACTOR_PAYABLE, the piece-work wage that the
--     Nota/payroll path already reads);
--  3. erp.record_sewing_terminal_v1 (SELESAI_DIJAHIT) for that completion, which is what Laundry counts as ready to send.
-- Cancel (REVERSE) uses the Native inverses in their required order (erp.reverse_sewing_terminal_v1, then
-- erp.reverse_work_completion) and is refused while the pieces are already sent or drafted to Laundry, while the wage is
-- in an active payroll, or while an active attendance HPP pool uses the event. Native guards (pickup time, future time,
-- per-component and per-group caps, MANDOR role, attendance pool period lock) stay authoritative and unchanged.
create table cp7_cutting_correction.sewing_requests(
 actor uuid not null,request_id uuid not null,payload jsonb not null,expected_version text not null,
 response jsonb,primary key(actor,request_id)
);
create table cp7_cutting_correction.sewing_history(
 actor uuid not null,request_id uuid not null,action text not null check(action in('RECORD','REVERSE')),
 group_id uuid not null references erp.cutting_groups,work_completion_id uuid not null references erp.work_completion_events,
 sewing_event_id uuid not null references erp.sewing_terminal_events,qty_pcs integer not null check(qty_pcs>0),
 source jsonb not null,result jsonb not null,reason text not null,
 recorded_at timestamptz not null default clock_timestamp(),primary key(actor,request_id)
);
alter table cp7_cutting_correction.sewing_requests owner to postgres;
alter table cp7_cutting_correction.sewing_history owner to postgres;
alter table cp7_cutting_correction.sewing_requests enable row level security;
alter table cp7_cutting_correction.sewing_history enable row level security;
create policy private_sewing_requests on cp7_cutting_correction.sewing_requests for all using(false)with check(false);
create policy private_sewing_history on cp7_cutting_correction.sewing_history for all using(false)with check(false);
revoke all on cp7_cutting_correction.sewing_requests,cp7_cutting_correction.sewing_history
 from public,anon,authenticated,service_role,cp7_capture,cp7_cutting_read,cp7_cutting_write;
create trigger immutable_sewing_history before update or delete on cp7_cutting_correction.sewing_history
 for each row execute function cp7_cutting_correction.immutable();
create trigger immutable_sewing_history_truncate before truncate on cp7_cutting_correction.sewing_history
 for each statement execute function cp7_cutting_correction.immutable();

create function cp7_cutting_correction.sewing_access_now(p_reverse boolean)returns jsonb
language plpgsql volatile security definer set search_path=''as $$
declare a jsonb;permission text;
begin
 if auth.uid()is null or auth.jwt()->>'role'is distinct from'authenticated'then
  raise exception using errcode='42501',message='CP7_SEWING_DENIED';end if;
 a:=erp.get_my_access_v1();
 if a->'allowed'is distinct from'true'::jsonb or coalesce(a->'profile'->>'role_code','')not in('OWNER','ADMIN')then
  raise exception using errcode='42501',message='CP7_SEWING_DENIED';end if;
 foreach permission in array array['production.wip.view','production.wip.post']
  ||case when p_reverse then array['production.wip.reverse']else array[]::text[]end loop
  if erp.has_permission(permission)is distinct from true then
   raise exception using errcode='42501',message='CP7_SEWING_DENIED';end if;
 end loop;
 return a;
end $$;

-- Everything the command reads, for the review token. Blockers name why nothing can be recorded; each event names why it
-- cannot be cancelled.
create function cp7_cutting_correction.sewing_snapshot(p_group uuid)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare g erp.cutting_groups;po erp.production_orders;p erp.cutting_pickups;c erp.contractors;
 effective bigint;sewn bigint;ready bigint;drafted bigint;comps jsonb;events jsonb;b jsonb:='[]';max_qty bigint;cap bigint;
 preview jsonb:='[]';
begin
 select *into g from erp.cutting_groups where id=p_group;
 if g.id is null then return null;end if;
 select *into po from erp.production_orders where id=g.po_id;
 select *into p from erp.cutting_pickups where cutting_group_id=g.id and status='POSTED';
 if p.id is not null then select *into c from erp.contractors where id=p.contractor_id;end if;
 select coalesce(max(v.total_pcs),0)into effective from erp.v_cutting_group_totals v where v.cutting_group_id=g.id;
 select coalesce(sum(e.qty_signed),0)into sewn from erp.sewing_terminal_events e where e.cutting_group_id=g.id;
 select coalesce(max(w.unsent_ready_qty_pcs),0),coalesce(max(w.laundry_draft_qty_pcs),0)into ready,drafted
  from erp.v_wip_control_status_v1 w where w.cutting_group_id=g.id;
 comps:=coalesce((select jsonb_agg(jsonb_build_object('snapshot_id',s.id,'work_component_id',s.work_component_id,
   'code',wc.component_code,'name',wc.component_name,'sequence_no',s.sequence_no,'rate',s.rate_per_pcs_snapshot,
   'posted_qty',coalesce((select sum(l.qty_completed)from erp.work_completion_lines l join erp.work_completion_events e on e.id=l.completion_id
     where e.cutting_group_id=g.id and e.status='POSTED'and l.work_component_id=s.work_component_id),0))order by s.sequence_no,s.id)
  from erp.po_work_component_snapshots s join erp.work_components wc on wc.id=s.work_component_id
  where s.po_id=g.po_id and s.bf_sku_version_id is null),'[]');
 events:=coalesce((select jsonb_agg(jsonb_build_object('id',e.id,'number',e.event_number,'qty_pcs',e.qty_signed,'physical_at',e.physical_at,
   'row_version',e.row_version,'reason',e.reason,'work_completion_id',e.source_work_completion_id,'work_status',w.status,
   'reversed',exists(select 1 from erp.sewing_terminal_events r where r.reversal_of_id=e.id),
   'wage_amount',(select coalesce(sum(l.amount_payable),0)from erp.work_completion_lines l where l.completion_id=e.source_work_completion_id),
   'in_payroll',exists(select 1 from erp.payroll_work_items pwi join erp.payroll_settlements ps on ps.id=pwi.payroll_id
     join erp.work_completion_lines wl on wl.id=pwi.source_id
     where wl.completion_id=e.source_work_completion_id and pwi.source_type='PRODUCTION'and ps.status<>'REVERSED'),
   'in_active_pool',exists(select 1 from erp.attendance_hpp_pool_allocations a join erp.attendance_hpp_pools ap on ap.id=a.pool_id
     where a.sewing_terminal_event_id=e.id and ap.status='ACTIVE'))order by e.physical_at,e.id)
  from erp.sewing_terminal_events e left join erp.work_completion_events w on w.id=e.source_work_completion_id
  where e.cutting_group_id=g.id and e.event_kind='SELESAI_DIJAHIT'),'[]');
 max_qty:=greatest(effective-sewn,0);
 select min(effective-(x->>'posted_qty')::bigint)into cap from jsonb_array_elements(comps)x;
 if cap is not null then max_qty:=greatest(least(max_qty,cap),0);end if;
 if p.id is null then
  b:=b||jsonb_build_array(jsonb_build_object('kind','NO_POSTED_PICKUP','id',g.id,'label',g.group_number));
 else
  if c.contractor_type is distinct from'MANDOR'then
   b:=b||jsonb_build_array(jsonb_build_object('kind','CONTRACTOR_NOT_MANDOR','id',c.id,'label',c.contractor_name));end if;
  if po.contractor_id is distinct from p.contractor_id then
   b:=b||jsonb_build_array(jsonb_build_object('kind','CONTRACTOR_MISMATCH','id',po.id,'label',po.po_number));end if;
 end if;
 if po.status in('ON_HOLD','FINISHED','CANCELLED')then
  b:=b||jsonb_build_array(jsonb_build_object('kind','PO_STATE','id',po.id,'label',po.po_number,'status',po.status));end if;
 if max_qty<=0 then
  b:=b||jsonb_build_array(jsonb_build_object('kind','NOTHING_TO_SEW','id',g.id,'label',g.group_number));end if;
 -- A Potongan bound to SKU waves (BF commercial ranges) is paid at SKU-scoped rates per size; this screen records one
 -- quantity for the whole Potongan, so it refuses instead of paying the base rate.
 if exists(select 1 from erp.bf_wave_skus_v1 w where w.cutting_group_id=g.id)then
  b:=b||jsonb_build_array(jsonb_build_object('kind','WAVE_SKU_RATES','id',g.id,'label',g.group_number));end if;
 -- Before the first record the PO has no rate snapshot yet: preview the rates the Native snapshot
 -- (erp.ensure_po_work_component_snapshots) would take now, read-only and with its rule (the model's active Work BOM version,
 -- per item the PO Mandor's rate for that model and component, else the BOM default rate). The command commits the
 -- snapshot at the sewing time, so the screen calls it an estimate and the outcome reports the wage actually posted.
 if jsonb_array_length(comps)=0 and po.contractor_id is not null then
  preview:=coalesce((select jsonb_agg(jsonb_build_object('code',wc.component_code,'name',wc.component_name,'sequence_no',i.sequence_no,
    'rate',coalesce((select cwr.rate_per_pcs from erp.contractor_work_rates cwr where cwr.contractor_id=po.contractor_id and cwr.model_id=po.model_id
      and cwr.work_component_id=i.work_component_id and cwr.effective_from<=clock_timestamp()and(cwr.effective_to is null or cwr.effective_to>clock_timestamp())
      order by cwr.effective_from desc,cwr.id desc limit 1),i.default_rate))order by i.sequence_no,i.id)
   from erp.work_bom_items i join erp.work_components wc on wc.id=i.work_component_id
   where i.bom_version_id=(select v.id from erp.work_bom_versions v where v.model_id=po.model_id and v.is_active
    and v.effective_from<=clock_timestamp()and(v.effective_to is null or v.effective_to>clock_timestamp())
    and exists(select 1 from erp.work_bom_items x where x.bom_version_id=v.id)
    order by v.effective_from desc,v.version_no desc,v.id desc limit 1)),'[]');
 end if;
 -- The wage needs the model's Work BOM with a rate for every component (Mandor rate or BOM default); otherwise the Native
 -- snapshot refuses.
 if jsonb_array_length(comps)=0 and(jsonb_array_length(preview)=0 or exists(select 1 from jsonb_array_elements(preview)x
   where x->'rate'='null'::jsonb or(x->>'rate')::numeric<0))then
  b:=b||jsonb_build_array(jsonb_build_object('kind','NO_WORK_RATE','id',po.model_id,'label',po.po_number));end if;
 return jsonb_build_object('group',jsonb_build_object('id',g.id,'number',g.group_number,'po_id',g.po_id,'status',g.status,
   'row_version',g.row_version,'picked_up_at',g.picked_up_at),
  'po',jsonb_build_object('id',po.id,'number',po.po_number,'status',po.status,'contractor_id',po.contractor_id),
  'pickup',case when p.id is null then null else jsonb_build_object('id',p.id,'contractor_id',p.contractor_id,'picked_up_at',p.picked_up_at,
   'row_version',p.row_version)end,
  'contractor',case when c.id is null then null else jsonb_build_object('id',c.id,'name',c.contractor_name,'type',c.contractor_type)end,
  'effective_pcs',effective,'sewn_pcs',sewn,'ready_unsent_pcs',ready,'laundry_draft_pcs',drafted,
  'reversible_pcs',greatest(ready-drafted,0),'max_qty',max_qty,'components',comps,'rate_preview',preview,'rates_committed',jsonb_array_length(comps)>0,
  'events',events,'blockers',b);
end $$;

create function cp7_cutting_correction.sewing_event_blocker(s jsonb,e jsonb)returns text
language sql immutable security definer set search_path=''as $$
 select case when(e->>'reversed')::boolean then'ALREADY_CANCELLED'
  when e->>'work_status'is distinct from'POSTED'then'WORK_NOT_POSTED'
  when(e->>'in_payroll')::boolean then'IN_PAYROLL'
  when(e->>'in_active_pool')::boolean then'IN_ATTENDANCE_POOL'
  when(e->>'qty_pcs')::bigint>(s->>'reversible_pcs')::bigint then'SENT_OR_DRAFTED_TO_LAUNDRY'
  end$$;

create function cp7_cutting_correction.sewing_workspace(p_group uuid)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;s jsonb;
begin
 a:=cp7_cutting_correction.sewing_access_now(false);s:=cp7_cutting_correction.sewing_snapshot(p_group);
 if s is null then raise exception 'CP7_SEWING_NOT_FOUND';end if;
 if cp7_cutting_correction.sewing_access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_SEWING_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.sewing-completion-workspace.v1','group_id',p_group,'group_version',s->'group'->>'row_version',
  'number',s->'group'->>'number','po_id',s->'po'->>'id','po_number',s->'po'->>'number','po_status',s->'po'->>'status',
  'contractor_id',s->'contractor'->>'id','contractor_name',s->'contractor'->>'name','picked_up_at',s->'pickup'->>'picked_up_at',
  'effective_pcs',(s->>'effective_pcs')::bigint,'sewn_pcs',(s->>'sewn_pcs')::bigint,'max_qty',(s->>'max_qty')::bigint,
  'ready_unsent_pcs',(s->>'ready_unsent_pcs')::bigint,'laundry_draft_pcs',(s->>'laundry_draft_pcs')::bigint,
  'rates_committed',(s->>'rates_committed')::boolean,
  'rate_preview',(select coalesce(jsonb_agg(jsonb_build_object('code',x->>'code','name',x->>'name','rate',(x->>'rate')::numeric)
    order by(x->>'sequence_no')::integer,x->>'code'),'[]')from jsonb_array_elements(s->'rate_preview')x where x->'rate'<>'null'::jsonb),
  'components',(select coalesce(jsonb_agg(jsonb_build_object('code',x->>'code','name',x->>'name','rate',(x->>'rate')::numeric,
    'posted_qty',(x->>'posted_qty')::bigint)order by(x->>'sequence_no')::integer,x->>'snapshot_id'),'[]')from jsonb_array_elements(s->'components')x),
  'events',(select coalesce(jsonb_agg(x||jsonb_build_object('cancel_blocker',cp7_cutting_correction.sewing_event_blocker(s,x))order by x->>'physical_at',x->>'id'),'[]')
    from jsonb_array_elements(s->'events')x),
  'can_cancel',erp.has_permission('production.wip.reverse')is true,
  'review_token',md5(s::text),'eligible',jsonb_array_length(s->'blockers')=0,'blockers',s->'blockers','business_DML',false);
end $$;

create function cp7_cutting_correction.sewing_command(p jsonb,p_request uuid,p_expected text)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;old cp7_cutting_correction.sewing_requests;g erp.cutting_groups;po erp.production_orders;pk erp.cutting_pickups;
 s jsonb;s2 jsonb;r jsonb;answer jsonb;v_actor uuid;v_action text;v_reason text;v_qty integer;v_at timestamptz;v_seed text;
 v_completion uuid;v_lines integer;v_amount numeric;v_journal numeric;ev erp.sewing_terminal_events;x jsonb;v_block text;
 uuid_re constant text:='^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 if jsonb_typeof(p)is distinct from'object'or jsonb_typeof(p->'action')is distinct from'string'then raise exception 'CP7_SEWING_FIELDS';end if;
 v_action:=p->>'action';
 if v_action not in('RECORD','REVERSE')then raise exception 'CP7_SEWING_FIELDS';end if;
 a:=cp7_cutting_correction.sewing_access_now(v_action='REVERSE');
 if p_request is null or p_expected is null or p_expected!~'^[1-9][0-9]{0,18}$'
  or jsonb_typeof(p->'group_id')is distinct from'string'or coalesce(p->>'group_id','')!~uuid_re
  or jsonb_typeof(p->'review_token')is distinct from'string'or coalesce(p->>'review_token','')!~'^[a-f0-9]{32}$'
  or jsonb_typeof(p->'change_reason')is distinct from'string'or length(btrim(p->>'change_reason'))not between 5 and 1000 then
  raise exception 'CP7_SEWING_FIELDS';end if;
 if v_action='RECORD'then
  if not(p?&array['action','group_id','qty_pcs','physical_at','review_token','change_reason'])or(select count(*)from jsonb_object_keys(p))<>6
   or jsonb_typeof(p->'qty_pcs')is distinct from'string'or coalesce(p->>'qty_pcs','')!~'^[1-9][0-9]{0,6}$'
   or jsonb_typeof(p->'physical_at')is distinct from'string'
   or coalesce(p->>'physical_at','')!~'^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}(:[0-9]{2}(\.[0-9]{1,6})?)?(Z|[+-][0-9]{2}:[0-9]{2})$'then
   raise exception 'CP7_SEWING_FIELDS';end if;
 elsif not(p?&array['action','group_id','event_id','review_token','change_reason'])or(select count(*)from jsonb_object_keys(p))<>5
  or jsonb_typeof(p->'event_id')is distinct from'string'or coalesce(p->>'event_id','')!~uuid_re then
  raise exception 'CP7_SEWING_FIELDS';end if;
 v_reason:=btrim(p->>'change_reason');
 insert into cp7_cutting_correction.sewing_requests values(auth.uid(),p_request,p,p_expected,null)on conflict do nothing;
 select *into strict old from cp7_cutting_correction.sewing_requests where actor=auth.uid()and request_id=p_request for update;
 if old.payload is distinct from p or old.expected_version is distinct from p_expected then raise exception 'CP7_SEWING_REQUEST_CHANGED';end if;
 if cp7_cutting_correction.sewing_access_now(v_action='REVERSE')is distinct from a then raise exception using errcode='42501',message='CP7_SEWING_ACCESS_CHANGED';end if;
 if old.response is not null then return old.response;end if;
 -- Same lock order as the Native pickup writer and the pickup reversal: cutting flow lock, group, PO, pickup.
 perform pg_advisory_xact_lock(hashtextextended('CP6FLOW:'||(p->>'group_id'),0));
 select *into g from erp.cutting_groups where id=(p->>'group_id')::uuid for update;
 if g.id is null then raise exception 'CP7_SEWING_NOT_FOUND';end if;
 select *into po from erp.production_orders where id=g.po_id for update;
 select *into pk from erp.cutting_pickups where cutting_group_id=g.id and status='POSTED'for update;
 if cp7_cutting_correction.sewing_access_now(v_action='REVERSE')is distinct from a then raise exception using errcode='42501',message='CP7_SEWING_ACCESS_CHANGED';end if;
 s:=cp7_cutting_correction.sewing_snapshot(g.id);
 if g.row_version::text is distinct from p_expected or md5(s::text)is distinct from p->>'review_token'then raise exception 'CP7_SEWING_STALE_REVIEW';end if;
 v_actor:=erp.current_app_user_id();
 if v_actor is null then raise exception using errcode='42501',message='CP7_SEWING_DENIED';end if;
 perform set_config('app.change_reason',v_reason,true);
 v_seed:=auth.uid()::text||':'||p_request::text;
 if v_action='RECORD'then
  if jsonb_array_length(s->'blockers')<>0 then raise exception 'CP7_SEWING_BLOCKED: %',s->'blockers';end if;
  v_qty:=(p->>'qty_pcs')::integer;
  if v_qty>(s->>'max_qty')::bigint then raise exception 'CP7_SEWING_QTY_ABOVE_REMAINING: % > %',v_qty,s->>'max_qty';end if;
  v_at:=(p->>'physical_at')::timestamptz;
  if v_at<pk.picked_up_at then raise exception 'CP7_SEWING_BEFORE_PICKUP';end if;
  if v_at>clock_timestamp()+interval '5 minutes'then raise exception 'CP7_SEWING_FUTURE';end if;
  perform erp.ensure_po_work_component_snapshots_v2(po.id,v_at,md5(v_seed||':ensure')::uuid);
  if not exists(select 1 from erp.po_work_component_snapshots where po_id=po.id and bf_sku_version_id is null)then raise exception 'CP7_SEWING_NO_WORK_RATE';end if;
  v_completion:=gen_random_uuid();
  insert into erp.work_completion_events(id,completion_number,po_id,contractor_id,cutting_group_id,physical_at,status,notes,created_by)
   values(v_completion,'CP7-SEW-'||to_char(v_at at time zone 'Asia/Jakarta','YYYYMMDD')||'-'||substr(replace(v_completion::text,'-',''),1,10),
    po.id,pk.contractor_id,g.id,v_at,'DRAFT',v_reason,v_actor);
  insert into erp.work_completion_lines(completion_id,po_component_snapshot_id,work_component_id,qty_completed,qty_payable,rate_snapshot)
   select v_completion,sn.id,sn.work_component_id,v_qty,v_qty,sn.rate_per_pcs_snapshot
   from erp.po_work_component_snapshots sn where sn.po_id=po.id and sn.bf_sku_version_id is null order by sn.sequence_no,sn.id;
  get diagnostics v_lines=row_count;
  perform erp.post_work_completion(v_completion);
  perform erp.record_sewing_terminal_v1(jsonb_build_object('work_completion_id',v_completion,'qty_pcs',v_qty,'reason',v_reason),
   md5(v_seed||':sewing')::uuid);
  select *into ev from erp.sewing_terminal_events where source_work_completion_id=v_completion and event_kind='SELESAI_DIJAHIT';
  select coalesce(sum(amount_payable),0)into v_amount from erp.work_completion_lines where completion_id=v_completion;
  select coalesce(sum(jl.debit),0)into v_journal from erp.journal_entries je join erp.journal_lines jl on jl.journal_entry_id=je.id
   where je.source_type='WORK_COMPLETION'and je.source_id=v_completion and je.status='POSTED';
  s2:=cp7_cutting_correction.sewing_snapshot(g.id);
  -- Post-conditions: one POSTED completion with every snapshot component, its wage journal, one SELESAI_DIJAHIT of exactly
  -- the requested pieces, and the sewn total moved by exactly that many.
  if ev.id is null or ev.qty_signed<>v_qty or ev.cutting_group_id is distinct from g.id
   or not exists(select 1 from erp.work_completion_events w where w.id=v_completion and w.status='POSTED')
   or v_lines<>jsonb_array_length(s2->'components')or v_lines=0
   or v_journal<>round(v_amount,2)
   or(s2->>'sewn_pcs')::bigint<>(s->>'sewn_pcs')::bigint+v_qty then
   raise exception 'CP7_SEWING_INCOMPLETE';end if;
  r:=jsonb_build_object('work_completion_id',v_completion,'sewing_event_id',ev.id,'qty_pcs',v_qty,'wage_amount',round(v_amount,2),
   'components',v_lines,'sewn_pcs',(s2->>'sewn_pcs')::bigint,'ready_unsent_pcs',(s2->>'ready_unsent_pcs')::bigint,
   'max_qty',(s2->>'max_qty')::bigint);
 else
  select e into x from jsonb_array_elements(s->'events')e where e->>'id'=p->>'event_id';
  if x is null then raise exception 'CP7_SEWING_NOT_FOUND';end if;
  v_block:=cp7_cutting_correction.sewing_event_blocker(s,x);
  if v_block is not null then raise exception 'CP7_SEWING_CANCEL_BLOCKED: %',v_block;end if;
  select *into ev from erp.sewing_terminal_events where id=(x->>'id')::uuid for update;
  v_completion:=ev.source_work_completion_id;v_qty:=ev.qty_signed;
  perform 1 from erp.work_completion_events where id=v_completion for update;
  perform erp.reverse_sewing_terminal_v1(ev.id,v_reason,md5(v_seed||':reverse')::uuid,ev.row_version);
  perform erp.reverse_work_completion(v_completion,v_reason);
  s2:=cp7_cutting_correction.sewing_snapshot(g.id);
  if not exists(select 1 from erp.sewing_terminal_events rv where rv.reversal_of_id=ev.id and rv.qty_signed=-v_qty)
   or not exists(select 1 from erp.work_completion_events w where w.id=v_completion and w.status='REVERSED')
   or exists(select 1 from erp.journal_entries je where je.source_type='WORK_COMPLETION'and je.source_id=v_completion and je.status='POSTED')
   or(s2->>'sewn_pcs')::bigint<>(s->>'sewn_pcs')::bigint-v_qty then
   raise exception 'CP7_SEWING_INCOMPLETE';end if;
  r:=jsonb_build_object('work_completion_id',v_completion,'sewing_event_id',ev.id,'qty_pcs',v_qty,'status','CANCELLED',
   'sewn_pcs',(s2->>'sewn_pcs')::bigint,'ready_unsent_pcs',(s2->>'ready_unsent_pcs')::bigint,'max_qty',(s2->>'max_qty')::bigint);
 end if;
 if cp7_cutting_correction.sewing_access_now(v_action='REVERSE')is distinct from a then raise exception using errcode='42501',message='CP7_SEWING_ACCESS_CHANGED';end if;
 insert into cp7_cutting_correction.sewing_history values(auth.uid(),p_request,v_action,g.id,v_completion,ev.id,v_qty,s,r,v_reason,clock_timestamp());
 answer:=jsonb_build_object('contract_version','cp7.sewing-completion-outcome.v1','kind','COMMITTED_OUTCOME','action',v_action,
  'request_id',p_request,'group_id',g.id,'po_id',po.id,'number',g.group_number,'result',r);
 update cp7_cutting_correction.sewing_requests set response=answer where actor=auth.uid()and request_id=p_request;
 return answer;
end $$;

create function public.erp_cp7_get_sewing_completion_v1(p_group uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_cutting_correction.sewing_workspace(p_group)$$;
create function public.erp_cp7_save_sewing_completion_v1(p_payload jsonb,p_request uuid,p_expected text)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_cutting_correction.sewing_command(p_payload,p_request,p_expected)$$;
alter function cp7_cutting_correction.sewing_access_now(boolean)owner to postgres;
alter function cp7_cutting_correction.sewing_snapshot(uuid)owner to postgres;
alter function cp7_cutting_correction.sewing_event_blocker(jsonb,jsonb)owner to postgres;
alter function cp7_cutting_correction.sewing_workspace(uuid)owner to postgres;
alter function cp7_cutting_correction.sewing_command(jsonb,uuid,text)owner to postgres;
grant create on schema public to cp7_cutting_read,cp7_cutting_write;
alter function public.erp_cp7_get_sewing_completion_v1(uuid)owner to cp7_cutting_read;
alter function public.erp_cp7_save_sewing_completion_v1(jsonb,uuid,text)owner to cp7_cutting_write;
revoke create on schema public from cp7_cutting_read,cp7_cutting_write;
revoke all on function cp7_cutting_correction.sewing_access_now(boolean),cp7_cutting_correction.sewing_snapshot(uuid),
 cp7_cutting_correction.sewing_event_blocker(jsonb,jsonb),cp7_cutting_correction.sewing_workspace(uuid),
 cp7_cutting_correction.sewing_command(jsonb,uuid,text)
 from public,anon,authenticated,service_role,cp7_capture,cp7_cutting_read,cp7_cutting_write;
grant execute on function cp7_cutting_correction.sewing_workspace(uuid)to cp7_cutting_read;
grant execute on function cp7_cutting_correction.sewing_command(jsonb,uuid,text)to cp7_cutting_write;
revoke all on function public.erp_cp7_get_sewing_completion_v1(uuid),public.erp_cp7_save_sewing_completion_v1(jsonb,uuid,text)from public,anon,authenticated,service_role,cp7_capture;
grant execute on function public.erp_cp7_get_sewing_completion_v1(uuid),public.erp_cp7_save_sewing_completion_v1(jsonb,uuid,text)to authenticated;
