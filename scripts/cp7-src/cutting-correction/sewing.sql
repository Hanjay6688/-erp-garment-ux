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
-- Sol R2-10: a wave Potongan (BF commercial ranges) records one work completion and one SELESAI_DIJAHIT per SKU in a single
-- request; one immutable row per SKU line.
create table cp7_cutting_correction.sewing_wave_history(
 actor uuid not null,request_id uuid not null,line_no integer not null check(line_no>0),
 group_id uuid not null references erp.cutting_groups,sku_id uuid not null references erp.bf_skus_v1,
 work_completion_id uuid not null references erp.work_completion_events,sewing_event_id uuid not null references erp.sewing_terminal_events,
 qty_pcs integer not null check(qty_pcs>0),wage_amount numeric not null check(wage_amount>=0),
 source jsonb not null,result jsonb not null,reason text not null,
 recorded_at timestamptz not null default clock_timestamp(),primary key(actor,request_id,line_no)
);
alter table cp7_cutting_correction.sewing_wave_history owner to postgres;
alter table cp7_cutting_correction.sewing_wave_history enable row level security;
create policy private_sewing_wave_history on cp7_cutting_correction.sewing_wave_history for all using(false)with check(false);
revoke all on cp7_cutting_correction.sewing_wave_history from public,anon,authenticated,service_role,cp7_capture,cp7_cutting_read,cp7_cutting_write;
create trigger immutable_sewing_wave_history before update or delete on cp7_cutting_correction.sewing_wave_history
 for each row execute function cp7_cutting_correction.immutable();
create trigger immutable_sewing_wave_history_truncate before truncate on cp7_cutting_correction.sewing_wave_history
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

-- Sol R2-10: the per-SKU rates the Native snapshot (erp.ensure_po_work_component_snapshots, which ends with
-- erp.bf_ensure_work_v1) gives the SKUs of a wave Potongan for a sewing at p_at, read-only and by the same rule:
--  base components from the PO base snapshot once committed, else from the model's Work BOM at p_at (the Mandor rate for the
--  model and component, else the BOM default);
--  per SKU the version already pinned for the PO (its snapshot rates), else the version in force at p_at with, per base
--  component, erp.bf_work_rate_v1 (contractor-specific first, special only under a special HPP policy that WIB day), else the
--  base rate.
-- complete is false exactly where the Native snapshot refuses: no Mandor on the PO, no base component, a base rate missing or
-- negative, or any wave SKU of the PO (also of its other Potongan) without a version at p_at or bound to a size that version
-- no longer covers (BF_WORK_VERSION_MISSING, BF_WAVE_REFERENCE_STALE).
create function cp7_cutting_correction.sewing_wave_at(p_group uuid,p_at timestamptz)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare po erp.production_orders;base jsonb;ok boolean;s record;vid uuid;pinned boolean;rates jsonb;skus jsonb:='[]';
begin
 select o.*into po from erp.production_orders o join erp.cutting_groups g on g.po_id=o.id where g.id=p_group;
 if exists(select 1 from erp.po_work_component_snapshots x where x.po_id=po.id and x.bf_sku_version_id is null)then
  select jsonb_agg(jsonb_build_object('work_component_id',x.work_component_id,'code',wc.component_code,'name',wc.component_name,
    'sequence_no',x.sequence_no,'rate',x.rate_per_pcs_snapshot)order by x.sequence_no,x.id)into base
  from erp.po_work_component_snapshots x join erp.work_components wc on wc.id=x.work_component_id where x.po_id=po.id and x.bf_sku_version_id is null;
 else
  select jsonb_agg(jsonb_build_object('work_component_id',i.work_component_id,'code',wc.component_code,'name',wc.component_name,'sequence_no',i.sequence_no,
    'rate',coalesce((select cwr.rate_per_pcs from erp.contractor_work_rates cwr where cwr.contractor_id=po.contractor_id and cwr.model_id=po.model_id
      and cwr.work_component_id=i.work_component_id and cwr.effective_from<=p_at and(cwr.effective_to is null or cwr.effective_to>p_at)
      order by cwr.effective_from desc,cwr.id desc limit 1),i.default_rate))order by i.sequence_no,i.id)into base
  from erp.work_bom_items i join erp.work_components wc on wc.id=i.work_component_id
  where i.bom_version_id=(select v.id from erp.work_bom_versions v where v.model_id=po.model_id and v.is_active
   and v.effective_from<=p_at and(v.effective_to is null or v.effective_to>p_at)
   and exists(select 1 from erp.work_bom_items x where x.bom_version_id=v.id)
   order by v.effective_from desc,v.version_no desc,v.id desc limit 1);
 end if;
 base:=coalesce(base,'[]');
 ok:=po.contractor_id is not null and jsonb_array_length(base)>0
  and not exists(select 1 from jsonb_array_elements(base)c where c->'rate'='null'::jsonb or(c->>'rate')::numeric<0);
 for s in select distinct w.sku_id from erp.bf_wave_skus_v1 w join erp.cutting_groups g on g.id=w.cutting_group_id where g.po_id=po.id order by w.sku_id loop
  select x.bf_sku_version_id into vid from erp.po_work_component_snapshots x join erp.bf_sku_versions_v1 v on v.id=x.bf_sku_version_id
   where x.po_id=po.id and v.sku_id=s.sku_id order by x.committed_at,x.id limit 1;
  pinned:=vid is not null;rates:=null;
  if pinned then
   select jsonb_agg(jsonb_build_object('code',wc.component_code,'name',wc.component_name,'sequence_no',x.sequence_no,'rate',x.rate_per_pcs_snapshot)
     order by x.sequence_no,x.id)into rates
   from erp.po_work_component_snapshots x join erp.work_components wc on wc.id=x.work_component_id where x.po_id=po.id and x.bf_sku_version_id=vid;
  else
   select v.id into vid from erp.bf_sku_versions_v1 v where v.sku_id=s.sku_id and v.effective_from<=p_at and(v.effective_to is null or v.effective_to>p_at);
   if vid is null or exists(select 1 from erp.bf_wave_skus_v1 w join erp.cutting_groups g on g.id=w.cutting_group_id
     where g.po_id=po.id and w.sku_id=s.sku_id and not exists(select 1 from erp.bf_sku_members_v1 m join erp.products p on p.id=m.product_root
      where m.version_id=vid and p.size_id=w.size_id))then
    ok:=false;
   else
    select jsonb_agg(jsonb_build_object('code',c->>'code','name',c->>'name','sequence_no',(c->>'sequence_no')::integer,
      'rate',coalesce(erp.bf_work_rate_v1(vid,po.contractor_id,(c->>'work_component_id')::uuid,p_at),(c->>'rate')::numeric))order by n)into rates
    from jsonb_array_elements(base)with ordinality e(c,n);
   end if;
  end if;
  if exists(select 1 from erp.bf_wave_skus_v1 w where w.cutting_group_id=p_group and w.sku_id=s.sku_id)then
   skus:=skus||jsonb_build_array(jsonb_build_object('sku_id',s.sku_id,'pinned',pinned,'rates',coalesce(rates,'[]')));end if;
 end loop;
 return jsonb_build_object('complete',ok,'skus',skus);
end $$;

-- Everything the command reads, for the review token. Blockers name why nothing can be recorded; each event names why it
-- cannot be cancelled.
create function cp7_cutting_correction.sewing_snapshot(p_group uuid)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare g erp.cutting_groups;po erp.production_orders;p erp.cutting_pickups;c erp.contractors;
 effective bigint;sewn bigint;ready bigint;drafted bigint;comps jsonb;events jsonb;b jsonb:='[]';max_qty bigint;cap bigint;
 preview jsonb:='[]';timeline jsonb:='[]';wave jsonb;k jsonb;skus jsonb:='[]';sku_max bigint;sum_max bigint:=0;base_committed boolean;
 wave_committed boolean;wave_timeline jsonb:='[]';
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
     where a.sewing_terminal_event_id=e.id and ap.status='ACTIVE'),
   'sku',(select string_agg(distinct ks.sku,', ')from erp.work_completion_lines l join erp.po_work_component_snapshots x on x.id=l.po_component_snapshot_id
     join erp.bf_sku_versions_v1 v on v.id=x.bf_sku_version_id join erp.bf_skus_v1 ks on ks.id=v.sku_id where l.completion_id=e.source_work_completion_id))
   order by e.physical_at,e.id)
  from erp.sewing_terminal_events e left join erp.work_completion_events w on w.id=e.source_work_completion_id
  where e.cutting_group_id=g.id and e.event_kind='SELESAI_DIJAHIT'),'[]');
 max_qty:=greatest(effective-sewn,0);
 select min(effective-(x->>'posted_qty')::bigint)into cap from jsonb_array_elements(comps)x;
 if cap is not null then max_qty:=greatest(least(max_qty,cap),0);end if;
 -- Sol R2-10: a Potongan bound to SKU waves (BF commercial ranges) is paid per SKU at the SKU's work rates. Per SKU: its sizes,
 -- the pieces cut in them (the sum erp.bf_work_capacity_v1 takes), and per work component what is already completed and
 -- payable on that SKU for this Potongan (the Native per-SKU guard checks both against the pieces cut); once the SKU is pinned
 -- for the PO, its snapshot rates. The Potongan can take at most the sum of what each SKU can still take.
 if exists(select 1 from erp.bf_wave_skus_v1 w where w.cutting_group_id=g.id)then
  for k in select jsonb_build_object('sku_id',s.id,'sku',s.sku,'color',s.color_name,
     'sizes',(select jsonb_agg(z.size_code order by z.sort_order,z.size_code,z.id)from erp.bf_wave_skus_v1 w join erp.sizes z on z.id=w.size_id
       where w.cutting_group_id=g.id and w.sku_id=s.id),
     'capacity',(select coalesce(sum(y.qty_pcs),0)from erp.cutting_roll_yields y join erp.cutting_group_rolls r on r.id=y.cutting_group_roll_id
       join erp.cutting_group_size_slots slot on slot.id=y.size_slot_id
       join erp.bf_wave_skus_v1 w on w.cutting_group_id=r.cutting_group_id and w.size_id=slot.size_id where r.cutting_group_id=g.id and w.sku_id=s.id),
     'components',coalesce((select jsonb_agg(jsonb_build_object('snapshot_id',x.id,'work_component_id',x.work_component_id,'code',wc.component_code,
        'name',wc.component_name,'sequence_no',x.sequence_no,'rate',x.rate_per_pcs_snapshot,
        'posted_completed',(select coalesce(sum(l.qty_completed),0)from erp.work_completion_lines l join erp.work_completion_events e on e.id=l.completion_id
          join erp.po_work_component_snapshots ls on ls.id=l.po_component_snapshot_id join erp.bf_sku_versions_v1 lv on lv.id=ls.bf_sku_version_id
          where e.cutting_group_id=g.id and e.status='POSTED'and l.work_component_id=x.work_component_id and lv.sku_id=s.id),
        'posted_payable',(select coalesce(sum(l.qty_payable),0)from erp.work_completion_lines l join erp.work_completion_events e on e.id=l.completion_id
          join erp.po_work_component_snapshots ls on ls.id=l.po_component_snapshot_id join erp.bf_sku_versions_v1 lv on lv.id=ls.bf_sku_version_id
          where e.cutting_group_id=g.id and e.status='POSTED'and l.work_component_id=x.work_component_id and lv.sku_id=s.id))order by x.sequence_no,x.id)
      from erp.po_work_component_snapshots x join erp.work_components wc on wc.id=x.work_component_id
      where x.po_id=g.po_id and x.bf_sku_version_id=(select x2.bf_sku_version_id from erp.po_work_component_snapshots x2
        join erp.bf_sku_versions_v1 v2 on v2.id=x2.bf_sku_version_id where x2.po_id=g.po_id and v2.sku_id=s.id order by x2.committed_at,x2.id limit 1)),'[]'))
   from erp.bf_skus_v1 s where exists(select 1 from erp.bf_wave_skus_v1 w where w.cutting_group_id=g.id and w.sku_id=s.id)order by s.sku,s.id loop
   sku_max:=(k->>'capacity')::bigint;
   select least(sku_max,min((k->>'capacity')::bigint-greatest((x->>'posted_completed')::bigint,(x->>'posted_payable')::bigint)))into sku_max
    from jsonb_array_elements(k->'components')x;
   sku_max:=greatest(sku_max,0);sum_max:=sum_max+sku_max;
   skus:=skus||jsonb_build_array(k||jsonb_build_object('max_qty',sku_max));
  end loop;
  max_qty:=least(max_qty,sum_max);
  -- Rates are fixed once the PO has its base snapshot and every wave SKU of the PO is pinned. Before that, between two
  -- consecutive instants where the Native answer can change (Work BOM versions and this Mandor's rates while the base is not
  -- committed, versions of the PO's wave SKUs, this Mandor's HPP policy days in WIB) each segment [from, to) carries
  -- sewing_wave_at at its start, from the pickup up to now.
  base_committed:=jsonb_array_length(comps)>0;
  wave_committed:=base_committed and not exists(select 1 from erp.bf_wave_skus_v1 w join erp.cutting_groups cg on cg.id=w.cutting_group_id
   where cg.po_id=g.po_id and not exists(select 1 from erp.po_work_component_snapshots x join erp.bf_sku_versions_v1 v on v.id=x.bf_sku_version_id
    where x.po_id=g.po_id and v.sku_id=w.sku_id));
  if not wave_committed then
   wave_timeline:=coalesce((with po_skus as(select w.sku_id from erp.bf_wave_skus_v1 w join erp.cutting_groups cg on cg.id=w.cutting_group_id where cg.po_id=g.po_id),
     t as(
      select v.effective_from x from erp.work_bom_versions v where not base_committed and v.model_id=po.model_id
      union select v.effective_to from erp.work_bom_versions v where not base_committed and v.model_id=po.model_id and v.effective_to is not null
      union select r.effective_from from erp.contractor_work_rates r where not base_committed and r.contractor_id=po.contractor_id and r.model_id=po.model_id
      union select r.effective_to from erp.contractor_work_rates r where not base_committed and r.contractor_id=po.contractor_id and r.model_id=po.model_id
       and r.effective_to is not null
      union select v.effective_from from erp.bf_sku_versions_v1 v where v.sku_id in(select sku_id from po_skus)
      union select v.effective_to from erp.bf_sku_versions_v1 v where v.sku_id in(select sku_id from po_skus)and v.effective_to is not null
      union select h.effective_from::timestamp at time zone 'Asia/Jakarta' from erp.contractor_hpp_policy_versions h where h.contractor_id=po.contractor_id
      union select(h.effective_to+1)::timestamp at time zone 'Asia/Jakarta' from erp.contractor_hpp_policy_versions h
       where h.contractor_id=po.contractor_id and h.effective_to is not null),
     seg as(select x f,lead(x)over(order by x)u from t)
    select jsonb_agg(jsonb_build_object('from',seg.f,'to',seg.u)||cp7_cutting_correction.sewing_wave_at(g.id,seg.f)order by seg.f)
    from seg where(seg.u is null or seg.u>coalesce(p.picked_up_at,'-infinity'::timestamptz))and seg.f<=clock_timestamp()),'[]');
  end if;
  wave:=jsonb_build_object('committed',wave_committed,'skus',skus,'timeline',wave_timeline);
 end if;
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
 -- Before the first record the PO has no rate snapshot yet: preview the rates the Native snapshot
 -- (erp.ensure_po_work_component_snapshots) would take now, read-only and with its rule (the model's active Work BOM version,
 -- per item the PO Mandor's rate for that model and component, else the BOM default rate). The command commits the
 -- snapshot at the sewing time, so the screen calls it an estimate and the outcome reports the wage actually posted.
 if wave is null and jsonb_array_length(comps)=0 and po.contractor_id is not null then
  preview:=coalesce((select jsonb_agg(jsonb_build_object('code',wc.component_code,'name',wc.component_name,'sequence_no',i.sequence_no,
    'rate',coalesce((select cwr.rate_per_pcs from erp.contractor_work_rates cwr where cwr.contractor_id=po.contractor_id and cwr.model_id=po.model_id
      and cwr.work_component_id=i.work_component_id and cwr.effective_from<=clock_timestamp()and(cwr.effective_to is null or cwr.effective_to>clock_timestamp())
      order by cwr.effective_from desc,cwr.id desc limit 1),i.default_rate))order by i.sequence_no,i.id)
   from erp.work_bom_items i join erp.work_components wc on wc.id=i.work_component_id
   where i.bom_version_id=(select v.id from erp.work_bom_versions v where v.model_id=po.model_id and v.is_active
    and v.effective_from<=clock_timestamp()and(v.effective_to is null or v.effective_to>clock_timestamp())
    and exists(select 1 from erp.work_bom_items x where x.bom_version_id=v.id)
    order by v.effective_from desc,v.version_no desc,v.id desc limit 1)),'[]');
  -- Owner D15-3: rates are dated, and the snapshot is taken at the sewing time the user enters, not now. Between two
  -- consecutive start/end instants of the model's Work BOM versions and of this Mandor's rates for the model the Native rule
  -- has one answer; each segment [from, to) carries it, from the pickup up to now, so the screen shows the rates of the
  -- time it will send (the review token covers them, so a rate saved meanwhile refuses the record instead of changing it).
  timeline:=coalesce((with t as(
     select v.effective_from x from erp.work_bom_versions v where v.model_id=po.model_id
     union select v.effective_to from erp.work_bom_versions v where v.model_id=po.model_id and v.effective_to is not null
     union select r.effective_from from erp.contractor_work_rates r where r.contractor_id=po.contractor_id and r.model_id=po.model_id
     union select r.effective_to from erp.contractor_work_rates r where r.contractor_id=po.contractor_id and r.model_id=po.model_id and r.effective_to is not null),
    seg as(select x f,lead(x)over(order by x)u from t)
   select jsonb_agg(jsonb_build_object('from',seg.f,'to',seg.u,'rates',coalesce((select jsonb_agg(jsonb_build_object('code',wc.component_code,
       'name',wc.component_name,'sequence_no',i.sequence_no,
       'rate',coalesce((select cwr.rate_per_pcs from erp.contractor_work_rates cwr where cwr.contractor_id=po.contractor_id and cwr.model_id=po.model_id
         and cwr.work_component_id=i.work_component_id and cwr.effective_from<=seg.f and(cwr.effective_to is null or cwr.effective_to>seg.f)
         order by cwr.effective_from desc,cwr.id desc limit 1),i.default_rate))order by i.sequence_no,i.id)
      from erp.work_bom_items i join erp.work_components wc on wc.id=i.work_component_id
      where i.bom_version_id=(select v.id from erp.work_bom_versions v where v.model_id=po.model_id and v.is_active
       and v.effective_from<=seg.f and(v.effective_to is null or v.effective_to>seg.f)
       and exists(select 1 from erp.work_bom_items x where x.bom_version_id=v.id)
       order by v.effective_from desc,v.version_no desc,v.id desc limit 1)),'[]'))order by seg.f)
   from seg where(seg.u is null or seg.u>coalesce(p.picked_up_at,'-infinity'::timestamptz))and seg.f<=clock_timestamp()),'[]');
 end if;
 -- The wage needs the model's Work BOM with a rate for every component (Mandor rate or BOM default) at the sewing time;
 -- otherwise the Native snapshot refuses. Blocked when no moment between the pickup and now has a complete set.
 if wave is null and jsonb_array_length(comps)=0 and not exists(select 1 from jsonb_array_elements(timeline)x where jsonb_array_length(x->'rates')>0
   and not exists(select 1 from jsonb_array_elements(x->'rates')y where y->'rate'='null'::jsonb or(y->>'rate')::numeric<0))then
  b:=b||jsonb_build_array(jsonb_build_object('kind','NO_WORK_RATE','id',po.model_id,'label',po.po_number));end if;
 -- A wave Potongan: blocked when no moment between the pickup and now has a complete set for every SKU of its PO (Work BOM
 -- and Mandor rates, and a version of each SKU covering its bound sizes).
 if wave is not null and not wave_committed and not exists(select 1 from jsonb_array_elements(wave_timeline)x where(x->>'complete')::boolean)then
  b:=b||jsonb_build_array(jsonb_build_object('kind','NO_WAVE_RATE','id',po.model_id,'label',po.po_number));end if;
 return jsonb_build_object('group',jsonb_build_object('id',g.id,'number',g.group_number,'po_id',g.po_id,'status',g.status,
   'row_version',g.row_version,'picked_up_at',g.picked_up_at),
  'po',jsonb_build_object('id',po.id,'number',po.po_number,'status',po.status,'contractor_id',po.contractor_id),
  'pickup',case when p.id is null then null else jsonb_build_object('id',p.id,'contractor_id',p.contractor_id,'picked_up_at',p.picked_up_at,
   'row_version',p.row_version)end,
  'contractor',case when c.id is null then null else jsonb_build_object('id',c.id,'name',c.contractor_name,'type',c.contractor_type)end,
  'effective_pcs',effective,'sewn_pcs',sewn,'ready_unsent_pcs',ready,'laundry_draft_pcs',drafted,
  'reversible_pcs',greatest(ready-drafted,0),'max_qty',max_qty,'components',comps,'rate_preview',preview,'rate_timeline',timeline,
  'rates_committed',jsonb_array_length(comps)>0,'wave',wave,
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
declare a jsonb;s jsonb;wave boolean;
begin
 a:=cp7_cutting_correction.sewing_access_now(false);s:=cp7_cutting_correction.sewing_snapshot(p_group);
 if s is null then raise exception 'CP7_SEWING_NOT_FOUND';end if;
 wave:=jsonb_typeof(s->'wave')='object';
 if cp7_cutting_correction.sewing_access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_SEWING_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.sewing-completion-workspace.v1','group_id',p_group,'group_version',s->'group'->>'row_version',
  'number',s->'group'->>'number','po_id',s->'po'->>'id','po_number',s->'po'->>'number','po_status',s->'po'->>'status',
  'contractor_id',s->'contractor'->>'id','contractor_name',s->'contractor'->>'name','picked_up_at',s->'pickup'->>'picked_up_at',
  'effective_pcs',(s->>'effective_pcs')::bigint,'sewn_pcs',(s->>'sewn_pcs')::bigint,'max_qty',(s->>'max_qty')::bigint,
  'ready_unsent_pcs',(s->>'ready_unsent_pcs')::bigint,'laundry_draft_pcs',(s->>'laundry_draft_pcs')::bigint,
  'rates_committed',case when wave then(s->'wave'->>'committed')::boolean else(s->>'rates_committed')::boolean end,
  'rate_preview',(select coalesce(jsonb_agg(jsonb_build_object('code',x->>'code','name',x->>'name','rate',(x->>'rate')::numeric)
    order by(x->>'sequence_no')::integer,x->>'code'),'[]')from jsonb_array_elements(s->'rate_preview')x where x->'rate'<>'null'::jsonb),
  'rate_timeline',(select coalesce(jsonb_agg(jsonb_build_object('from',x->'from','to',x->'to',
    'complete',jsonb_array_length(x->'rates')>0 and not exists(select 1 from jsonb_array_elements(x->'rates')y where y->'rate'='null'::jsonb or(y->>'rate')::numeric<0),
    'rates',(select coalesce(jsonb_agg(jsonb_build_object('code',y->>'code','name',y->>'name','rate',(y->>'rate')::numeric)
      order by(y->>'sequence_no')::integer,y->>'code'),'[]')from jsonb_array_elements(x->'rates')y where y->'rate'<>'null'::jsonb))
    order by(x->>'from')::timestamptz),'[]')from jsonb_array_elements(s->'rate_timeline')x),
  'components',(select coalesce(jsonb_agg(jsonb_build_object('code',x->>'code','name',x->>'name','rate',(x->>'rate')::numeric,
    'posted_qty',(x->>'posted_qty')::bigint)order by(x->>'sequence_no')::integer,x->>'snapshot_id'),'[]')from jsonb_array_elements(s->'components')x where not wave),
  -- Sol R2-10: a wave Potongan is recorded per SKU at the SKU rates (the base components above are not its wage).
  'wave',case when wave then jsonb_build_object('rates_committed',(s->'wave'->>'committed')::boolean,
   'skus',(select jsonb_agg(jsonb_build_object('sku_id',k->>'sku_id','sku',k->>'sku','color',k->>'color','sizes',k->'sizes',
     'capacity',(k->>'capacity')::bigint,'max_qty',(k->>'max_qty')::bigint,
     'posted_qty',coalesce((select max(greatest((x->>'posted_completed')::bigint,(x->>'posted_payable')::bigint))from jsonb_array_elements(k->'components')x),0),
     'rates',(select coalesce(jsonb_agg(jsonb_build_object('code',x->>'code','name',x->>'name','rate',(x->>'rate')::numeric)
       order by(x->>'sequence_no')::integer,x->>'snapshot_id'),'[]')from jsonb_array_elements(k->'components')x))order by n)
     from jsonb_array_elements(s->'wave'->'skus')with ordinality e(k,n)),
   'timeline',(select coalesce(jsonb_agg(jsonb_build_object('from',x->'from','to',x->'to','complete',(x->>'complete')::boolean,
     'skus',(select coalesce(jsonb_agg(jsonb_build_object('sku_id',y->>'sku_id','rates',(select coalesce(jsonb_agg(jsonb_build_object('code',z->>'code',
       'name',z->>'name','rate',(z->>'rate')::numeric)order by(z->>'sequence_no')::integer,z->>'code'),'[]')from jsonb_array_elements(y->'rates')z
       where z->'rate'<>'null'::jsonb))order by y->>'sku_id'),'[]')from jsonb_array_elements(x->'skus')y))
     order by(x->>'from')::timestamptz),'[]')from jsonb_array_elements(s->'wave'->'timeline')x))end,
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
 y jsonb;v_n bigint;v_sku uuid;v_line_qty integer;v_base integer;v_sku_snaps integer;v_out jsonb:='[]';v_total numeric:=0;
 uuid_re constant text:='^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 if jsonb_typeof(p)is distinct from'object'or jsonb_typeof(p->'action')is distinct from'string'then raise exception 'CP7_SEWING_FIELDS';end if;
 v_action:=p->>'action';
 if v_action not in('RECORD','RECORD_WAVE','REVERSE')then raise exception 'CP7_SEWING_FIELDS';end if;
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
 elsif v_action='RECORD_WAVE'then
  -- Sol R2-10: pieces per SKU of a wave Potongan: 1 to 50 lines, each a distinct SKU with its own pieces.
  if not(p?&array['action','group_id','lines','physical_at','review_token','change_reason'])or(select count(*)from jsonb_object_keys(p))<>6
   or jsonb_typeof(p->'lines')is distinct from'array'or jsonb_typeof(p->'physical_at')is distinct from'string'
   or coalesce(p->>'physical_at','')!~'^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}(:[0-9]{2}(\.[0-9]{1,6})?)?(Z|[+-][0-9]{2}:[0-9]{2})$'then
   raise exception 'CP7_SEWING_FIELDS';end if;
  if jsonb_array_length(p->'lines')not between 1 and 50
   or exists(select 1 from jsonb_array_elements(p->'lines')l where jsonb_typeof(l)is distinct from'object')then
   raise exception 'CP7_SEWING_FIELDS';end if;
  if exists(select 1 from jsonb_array_elements(p->'lines')l where not(l?&array['sku_id','qty_pcs'])or(select count(*)from jsonb_object_keys(l))<>2
    or jsonb_typeof(l->'sku_id')is distinct from'string'or coalesce(l->>'sku_id','')!~uuid_re
    or jsonb_typeof(l->'qty_pcs')is distinct from'string'or coalesce(l->>'qty_pcs','')!~'^[1-9][0-9]{0,6}$')
   or(select count(distinct l->>'sku_id')from jsonb_array_elements(p->'lines')l)<>jsonb_array_length(p->'lines')then
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
  -- A wave Potongan is paid per SKU; the single-quantity path at base rates is not a way around that.
  if jsonb_typeof(s->'wave')='object'then raise exception 'CP7_SEWING_WAVE_PER_SKU';end if;
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
 elsif v_action='RECORD_WAVE'then
  if jsonb_typeof(s->'wave')is distinct from'object'then raise exception 'CP7_SEWING_NOT_WAVE';end if;
  if jsonb_array_length(s->'blockers')<>0 then raise exception 'CP7_SEWING_BLOCKED: %',s->'blockers';end if;
  for x in select value from jsonb_array_elements(p->'lines')loop
   y:=null;select k into y from jsonb_array_elements(s->'wave'->'skus')k where k->>'sku_id'=x->>'sku_id';
   if y is null then raise exception 'CP7_SEWING_WAVE_SKU: %',x->>'sku_id';end if;
   if(x->>'qty_pcs')::bigint>(y->>'max_qty')::bigint then
    raise exception 'CP7_SEWING_QTY_ABOVE_REMAINING: SKU % % > %',y->>'sku',x->>'qty_pcs',y->>'max_qty';end if;
  end loop;
  select sum((l->>'qty_pcs')::integer)into v_qty from jsonb_array_elements(p->'lines')l;
  if v_qty>(s->>'max_qty')::bigint then raise exception 'CP7_SEWING_QTY_ABOVE_REMAINING: % > %',v_qty,s->>'max_qty';end if;
  v_at:=(p->>'physical_at')::timestamptz;
  if v_at<pk.picked_up_at then raise exception 'CP7_SEWING_BEFORE_PICKUP';end if;
  if v_at>clock_timestamp()+interval '5 minutes'then raise exception 'CP7_SEWING_FUTURE';end if;
  -- The Native snapshot pins the base rates and every wave SKU of the PO at the sewing time (no-op when pinned).
  perform erp.ensure_po_work_component_snapshots_v2(po.id,v_at,md5(v_seed||':ensure')::uuid);
  select count(*)into v_base from erp.po_work_component_snapshots where po_id=po.id and bf_sku_version_id is null;
  -- One work completion per SKU with one line per SKU snapshot component (the Native trigger takes the rate from the snapshot
  -- and checks the SKU belongs to the wave; the posting checks each component against the pieces cut in that SKU's sizes),
  -- then its SELESAI_DIJAHIT. Any refusal on any line rolls the whole request back.
  for x,v_n in select value,ordinality from jsonb_array_elements(p->'lines')with ordinality loop
   v_sku:=(x->>'sku_id')::uuid;v_line_qty:=(x->>'qty_pcs')::integer;
   select count(*)into v_sku_snaps from erp.po_work_component_snapshots sn join erp.bf_sku_versions_v1 v on v.id=sn.bf_sku_version_id
    where sn.po_id=po.id and v.sku_id=v_sku;
   if v_base=0 or v_sku_snaps<>v_base then raise exception 'CP7_SEWING_NO_WORK_RATE';end if;
   v_completion:=gen_random_uuid();
   insert into erp.work_completion_events(id,completion_number,po_id,contractor_id,cutting_group_id,physical_at,status,notes,created_by)
    values(v_completion,'CP7-SEW-'||to_char(v_at at time zone 'Asia/Jakarta','YYYYMMDD')||'-'||substr(replace(v_completion::text,'-',''),1,10),
     po.id,pk.contractor_id,g.id,v_at,'DRAFT',v_reason,v_actor);
   insert into erp.work_completion_lines(completion_id,po_component_snapshot_id,work_component_id,qty_completed,qty_payable,rate_snapshot)
    select v_completion,sn.id,sn.work_component_id,v_line_qty,v_line_qty,sn.rate_per_pcs_snapshot
    from erp.po_work_component_snapshots sn join erp.bf_sku_versions_v1 v on v.id=sn.bf_sku_version_id
    where sn.po_id=po.id and v.sku_id=v_sku order by sn.sequence_no,sn.id;
   get diagnostics v_lines=row_count;
   perform erp.post_work_completion(v_completion);
   perform erp.record_sewing_terminal_v1(jsonb_build_object('work_completion_id',v_completion,'qty_pcs',v_line_qty,'reason',v_reason),
    md5(v_seed||':sewing:'||v_n)::uuid);
   select *into ev from erp.sewing_terminal_events where source_work_completion_id=v_completion and event_kind='SELESAI_DIJAHIT';
   select coalesce(sum(amount_payable),0)into v_amount from erp.work_completion_lines where completion_id=v_completion;
   select coalesce(sum(jl.debit),0)into v_journal from erp.journal_entries je join erp.journal_lines jl on jl.journal_entry_id=je.id
    where je.source_type='WORK_COMPLETION'and je.source_id=v_completion and je.status='POSTED';
   if ev.id is null or ev.qty_signed<>v_line_qty or ev.cutting_group_id is distinct from g.id
    or not exists(select 1 from erp.work_completion_events w where w.id=v_completion and w.status='POSTED')
    or v_lines<>v_base or v_journal<>round(v_amount,2)
    or exists(select 1 from erp.work_completion_lines l join erp.po_work_component_snapshots sn on sn.id=l.po_component_snapshot_id
     left join erp.bf_sku_versions_v1 v on v.id=sn.bf_sku_version_id where l.completion_id=v_completion and v.sku_id is distinct from v_sku)then
    raise exception 'CP7_SEWING_INCOMPLETE';end if;
   v_total:=v_total+round(v_amount,2);
   v_out:=v_out||jsonb_build_array(jsonb_build_object('sku_id',v_sku,'sku',(select k.sku from erp.bf_skus_v1 k where k.id=v_sku),
    'work_completion_id',v_completion,'sewing_event_id',ev.id,'qty_pcs',v_line_qty,'wage_amount',round(v_amount,2),'components',v_lines));
  end loop;
  s2:=cp7_cutting_correction.sewing_snapshot(g.id);
  -- Post-conditions: the sewn total moved by exactly the pieces sent, and on each SKU sent every component's completed
  -- pieces moved by exactly that SKU's pieces.
  if(s2->>'sewn_pcs')::bigint<>(s->>'sewn_pcs')::bigint+v_qty
   or exists(select 1 from jsonb_array_elements(p->'lines')l
    left join lateral(select k from jsonb_array_elements(s2->'wave'->'skus')k where k->>'sku_id'=l->>'sku_id')after_sku on true
    where after_sku.k is null or jsonb_array_length(after_sku.k->'components')<>v_base
     or exists(select 1 from jsonb_array_elements(after_sku.k->'components')c
      where(c->>'posted_completed')::bigint<>(l->>'qty_pcs')::bigint+coalesce((select(c0->>'posted_completed')::bigint
       from jsonb_array_elements(s->'wave'->'skus')k0 cross join lateral jsonb_array_elements(k0->'components')c0
       where k0->>'sku_id'=l->>'sku_id'and c0->>'work_component_id'=c->>'work_component_id'),0)))then
   raise exception 'CP7_SEWING_INCOMPLETE';end if;
  r:=jsonb_build_object('lines',v_out,'qty_pcs',v_qty,'wage_amount',v_total,'sewn_pcs',(s2->>'sewn_pcs')::bigint,
   'ready_unsent_pcs',(s2->>'ready_unsent_pcs')::bigint,'max_qty',(s2->>'max_qty')::bigint);
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
 if v_action='RECORD_WAVE'then
  insert into cp7_cutting_correction.sewing_wave_history(actor,request_id,line_no,group_id,sku_id,work_completion_id,sewing_event_id,qty_pcs,wage_amount,
    source,result,reason,recorded_at)
   select auth.uid(),p_request,n,g.id,(l->>'sku_id')::uuid,(l->>'work_completion_id')::uuid,(l->>'sewing_event_id')::uuid,(l->>'qty_pcs')::integer,
    (l->>'wage_amount')::numeric,s,r,v_reason,clock_timestamp()
   from jsonb_array_elements(r->'lines')with ordinality e(l,n);
 else
  insert into cp7_cutting_correction.sewing_history values(auth.uid(),p_request,v_action,g.id,v_completion,ev.id,v_qty,s,r,v_reason,clock_timestamp());
 end if;
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
alter function cp7_cutting_correction.sewing_wave_at(uuid,timestamptz)owner to postgres;
alter function cp7_cutting_correction.sewing_snapshot(uuid)owner to postgres;
alter function cp7_cutting_correction.sewing_event_blocker(jsonb,jsonb)owner to postgres;
alter function cp7_cutting_correction.sewing_workspace(uuid)owner to postgres;
alter function cp7_cutting_correction.sewing_command(jsonb,uuid,text)owner to postgres;
grant create on schema public to cp7_cutting_read,cp7_cutting_write;
alter function public.erp_cp7_get_sewing_completion_v1(uuid)owner to cp7_cutting_read;
alter function public.erp_cp7_save_sewing_completion_v1(jsonb,uuid,text)owner to cp7_cutting_write;
revoke create on schema public from cp7_cutting_read,cp7_cutting_write;
revoke all on function cp7_cutting_correction.sewing_access_now(boolean),cp7_cutting_correction.sewing_wave_at(uuid,timestamptz),cp7_cutting_correction.sewing_snapshot(uuid),
 cp7_cutting_correction.sewing_event_blocker(jsonb,jsonb),cp7_cutting_correction.sewing_workspace(uuid),
 cp7_cutting_correction.sewing_command(jsonb,uuid,text)
 from public,anon,authenticated,service_role,cp7_capture,cp7_cutting_read,cp7_cutting_write;
grant execute on function cp7_cutting_correction.sewing_workspace(uuid)to cp7_cutting_read;
grant execute on function cp7_cutting_correction.sewing_command(jsonb,uuid,text)to cp7_cutting_write;
revoke all on function public.erp_cp7_get_sewing_completion_v1(uuid),public.erp_cp7_save_sewing_completion_v1(jsonb,uuid,text)from public,anon,authenticated,service_role,cp7_capture;
grant execute on function public.erp_cp7_get_sewing_completion_v1(uuid),public.erp_cp7_save_sewing_completion_v1(jsonb,uuid,text)to authenticated;
