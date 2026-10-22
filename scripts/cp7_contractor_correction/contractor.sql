-- OW05. A PO owns the Mandor identity. Posted wages/notes are never reassigned.
-- The operator first uses the named Native inverses in the workspace. This
-- command then replaces every current pickup, preserving its physical time,
-- quantities and old immutable allocations. Sewing is recorded again through
-- the existing writer with its explicit OLD/NEW rate choice (D16-2/3/4).
create schema cp7_contractor_correction authorization postgres;
revoke all on schema cp7_contractor_correction from public,anon,authenticated,service_role;

create table cp7_contractor_correction.requests_v1(
 actor uuid not null,request_id uuid not null,payload jsonb not null,response jsonb,
 primary key(actor,request_id)
);
create table cp7_contractor_correction.history_v1(
 actor uuid not null,request_id uuid not null,po_id uuid not null,
 old_contractor_id uuid not null,new_contractor_id uuid not null,
 source jsonb not null,result jsonb not null,reason text not null,
 recorded_at timestamptz not null default clock_timestamp(),
 generation_no bigint generated always as identity unique,primary key(actor,request_id)
);
-- No GUC, JWT claim, user-writable flag or durable row grants this capability.
create table cp7_contractor_correction.context_v1(
 backend_pid integer not null,transaction_id bigint not null,actor uuid not null,
 request_id uuid not null,po_id uuid not null,group_id uuid not null,
 primary key(backend_pid,transaction_id)
);
alter table cp7_contractor_correction.requests_v1 enable row level security;
alter table cp7_contractor_correction.history_v1 enable row level security;
alter table cp7_contractor_correction.context_v1 enable row level security;
create policy private_requests on cp7_contractor_correction.requests_v1 for all using(false)with check(false);
create policy private_history on cp7_contractor_correction.history_v1 for all using(false)with check(false);
create policy private_context on cp7_contractor_correction.context_v1 for all using(false)with check(false);
revoke all on all tables in schema cp7_contractor_correction from public,anon,authenticated,service_role,cp7_capture;
create trigger immutable_history before update or delete on cp7_contractor_correction.history_v1
 for each row execute function cp7_cutting_correction.immutable();
create trigger immutable_history_truncate before truncate on cp7_contractor_correction.history_v1
 for each statement execute function cp7_cutting_correction.immutable();

create function cp7_contractor_correction.access_now_v1()returns jsonb
language plpgsql volatile security definer set search_path=''as $$
declare v_pickup jsonb;v_sewing jsonb;
begin
 v_pickup:=cp7_cutting_correction.pickup_access_now();
 v_sewing:=cp7_cutting_correction.sewing_access_now(true);
 if erp.has_permission('production.distribution.create')is distinct from true then
  raise exception using errcode='42501',message='CP7_MANDOR_CORRECTION_DENIED';end if;
 if v_pickup is distinct from v_sewing then
  raise exception using errcode='42501',message='CP7_MANDOR_CORRECTION_ACCESS_CHANGED';end if;
 return v_pickup;
end $$;

-- All correction commands hold the same global envelope before allocating the
-- identity. Thus generation order is commit order (rolled-back gaps are fine),
-- unlike arbitrary sequence allocation by unrelated concurrent transactions.
-- A generation is an assignment, never a new physical date or a changed rate.
create function cp7_contractor_correction.generation_v1(p_po uuid)returns uuid
language plpgsql stable security definer set search_path=''as $$
declare v_history cp7_contractor_correction.history_v1;v_contractor uuid;
begin
 select *into v_history from cp7_contractor_correction.history_v1 hh where hh.po_id=p_po
  order by hh.generation_no desc limit 1;
 if not found then return null;end if;
 select po.contractor_id into v_contractor from erp.production_orders po where po.id=p_po;
 if v_history.new_contractor_id is distinct from v_contractor then
  raise exception 'CP7_MANDOR_CORRECTION_GENERATION_CHANGED';end if;
 return md5(v_history.actor::text||':'||v_history.request_id::text)::uuid;
end $$;

-- A known append-only Laundry WIP original needs its own exact Native inverse;
-- unrelated inflows, a net-zero sum, or a matching amount alone are insufficient.
create function cp7_contractor_correction.wip_closed_v1(p_po uuid)returns boolean
language sql stable security definer set search_path=''as $$
 select not exists(
  select 1 from erp.wip_stage_events w where w.po_id=p_po and not(
   (w.source_type in('LAUNDRY_DELIVERY_LINE','LAUNDRY_RECEIPT_LINE','CP6_LAUNDRY_BS_SIZE_LINE')
    and(select count(*)from erp.wip_stage_events rv where rv.source_id=w.id
     and rv.source_type=case w.source_type
      when'LAUNDRY_DELIVERY_LINE'then'CP6_LAUNDRY_DELIVERY_WIP_REVERSAL'
      when'LAUNDRY_RECEIPT_LINE'then'CP6_LAUNDRY_RECEIPT_WIP_REVERSAL'
      else'CP6_LAUNDRY_BS_WIP_REVERSAL'end
     and rv.po_id=w.po_id and rv.cutting_group_id is not distinct from w.cutting_group_id
     and rv.contractor_id is not distinct from w.contractor_id
     and rv.stage_from=w.stage_to and rv.stage_to=w.stage_from and rv.qty_pcs=w.qty_pcs)=1)
   or(w.source_type in('CP6_LAUNDRY_DELIVERY_WIP_REVERSAL','CP6_LAUNDRY_RECEIPT_WIP_REVERSAL','CP6_LAUNDRY_BS_WIP_REVERSAL')
    and exists(select 1 from erp.wip_stage_events orig where orig.id=w.source_id and orig.po_id=w.po_id
     and orig.cutting_group_id is not distinct from w.cutting_group_id
     and orig.contractor_id is not distinct from w.contractor_id
     and orig.stage_from=w.stage_to and orig.stage_to=w.stage_from and orig.qty_pcs=w.qty_pcs
     and w.source_type=case orig.source_type
      when'LAUNDRY_DELIVERY_LINE'then'CP6_LAUNDRY_DELIVERY_WIP_REVERSAL'
      when'LAUNDRY_RECEIPT_LINE'then'CP6_LAUNDRY_RECEIPT_WIP_REVERSAL'
      when'CP6_LAUNDRY_BS_SIZE_LINE'then'CP6_LAUNDRY_BS_WIP_REVERSAL'else''end))
  ))
$$;

create function cp7_contractor_correction.blockers_v1(p_po uuid)returns jsonb
language sql stable security definer set search_path=''as $$
 select coalesce(jsonb_agg(d.item order by(d.item->>'order')::integer,d.item->>'id'),'[]')from(
  select jsonb_build_object('order',10,'kind','PO_STATE','id',po.id,'number',po.po_number,
   'status',po.status,'step','Buka kembali PO selesai atau selesaikan status tahan/batal melalui layar PO.')item
   from erp.production_orders po where po.id=p_po and po.status in('FINISHED','ON_HOLD','CANCELLED')
  union all select jsonb_build_object('order',10,'kind','PICKUP_SOURCE','id',po.id,
   'step','Koreksi ini memerlukan mandor PO dan pembagian yang sudah diposting dengan mandor yang sama. Periksa riwayat Bagi Potongan.')
   from erp.production_orders po where po.id=p_po and(po.contractor_id is null
    or not exists(select 1 from erp.cutting_pickups pk join erp.cutting_groups cg on cg.id=pk.cutting_group_id
     where cg.po_id=po.id and pk.status='POSTED')
    or exists(select 1 from erp.cutting_pickups pk join erp.cutting_groups cg on cg.id=pk.cutting_group_id
     where cg.po_id=po.id and pk.status='POSTED'and pk.contractor_id is distinct from po.contractor_id))
  union all select jsonb_build_object('order',20,'kind','PAYROLL','id',ps.id,'number',ps.payroll_number,'status',ps.status,
   'step',case when ps.status='PAID'then'Balik pembayaran dan nota melalui layar Nota/Gaji; uang keluar lama tidak dipindahkan ke mandor baru.'
    else'Batalkan nota/gaji yang belum dibayar melalui layar Nota/Gaji.'end)
   from erp.payroll_settlements ps where ps.status<>'REVERSED'and(
    exists(select 1 from erp.payroll_work_items wi where wi.payroll_id=ps.id and wi.po_id=p_po)
    or exists(select 1 from erp.payroll_reimbursements ri where ri.payroll_id=ps.id and ri.po_id=p_po))
  union all select jsonb_build_object('order',15,'kind','ATTENDANCE_POOL','id',ap.id,'number',ap.pool_number,
   'step','Batalkan pool HPP absen yang memakai hasil jahit ini melalui layar Pool HPP.')
   from erp.attendance_hpp_pools ap where ap.status='ACTIVE'and exists(
    select 1 from erp.attendance_hpp_pool_allocations aa where aa.pool_id=ap.id and aa.po_id=p_po)
  union all select distinct jsonb_build_object('order',15,'kind','POCKET_POOL','id',pd.pool_id,
   'step','Batalkan pembagian kain kantong yang memakai PO ini melalui layar Kain Kantong.')
   from erp.pocket_period_destinations pd where pd.po_id=p_po and erp.pocket_period_active_v1(pd.pool_id)
  union all select jsonb_build_object('order',40,'kind','QC','id',qh.id,'number',qh.inspection_number,'status',qh.status,
   'step','Balik QC dan pemakaian barang jadinya dari dokumen paling akhir; hapus draft QC yang belum diposting.')
   from erp.qc_inspections qh where qh.po_id=p_po and qh.status<>'REVERSED'
  union all select jsonb_build_object('order',40,'kind','FG_LOT','id',fl.id,'number',fl.lot_number,
   'step','Balik pemakaian barang jadi lalu QC asalnya; lot harus dibatalkan dan stoknya kembali nol.')
   from erp.fg_lots fl where fl.po_id=p_po and(fl.lot_origin<>'VOIDED_PRODUCTION'
    or exists(select 1 from erp.fg_stock_movements fm where fm.lot_id=fl.id group by fm.lot_id having sum(fm.qty_signed)<>0))
  union all select jsonb_build_object('order',50,'kind','LAUNDRY','id',ld.id,'number',ld.delivery_number,'status',ld.status,
   'step','Balik penerimaan/cuci dan kirim laundry dari dokumen paling akhir; hapus draft yang masih mengikat potongan.')
   from erp.laundry_deliveries ld where ld.po_id=p_po and ld.status<>'REVERSED'
  union all select jsonb_build_object('order',60,'kind','SEWING','id',st.id,'number',st.event_number,
   'step','Batalkan hasil Selesai Dijahit dari layar WIP & Jahit; upah/jurnal dibalik melalui penulis yang sama.')
   from erp.sewing_terminal_events st where st.po_id=p_po and st.event_kind='SELESAI_DIJAHIT'
    and not exists(select 1 from erp.sewing_terminal_events rv where rv.reversal_of_id=st.id)
  union all select jsonb_build_object('order',65,'kind','WORK','id',we.id,'number',we.completion_number,'status',we.status,
   'step','Balik hasil kerja/upah melalui layar WIP & Jahit; hapus draft hasil kerja. Riwayat lama tetap tersimpan.')
   from erp.work_completion_events we where we.po_id=p_po and we.status<>'REVERSED'
  union all select jsonb_build_object('order',66,'kind','WORK_JOURNAL','id',je.id,'number',je.journal_number,
   'step','Selesaikan pembalikan upah dari dokumen hasil kerja asalnya; jurnal tidak boleh dibalik terpisah.')
   from erp.journal_entries je join erp.work_completion_events we on we.id=je.source_id
   where we.po_id=p_po and je.source_type='WORK_COMPLETION'and je.status='POSTED'
  union all select jsonb_build_object('order',70,'kind','ACCESSORY_NOTE','id',ae.id,'status',ae.payroll_status,
   'step','Balik nota/pembayaran lalu dokumen aksesori atau QC asal hak tagih; hak mandor lama harus berstatus dibatalkan.')
   from erp.contractor_accessory_reimbursement_entitlements ae where ae.po_id=p_po and ae.payroll_status<>'CANCELLED'
  union all select jsonb_build_object('order',70,'kind','MATERIAL_ISSUE','id',mi.id,'number',mi.issue_number,'status',mi.status,
   'step','Balik pengeluaran bahan ke mandor atau hapus draftnya dari layar Bahan Mandor.')
   from erp.contractor_material_issues mi where mi.po_id=p_po and mi.status<>'REVERSED'
  union all select jsonb_build_object('order',70,'kind','REWORK','id',ro.id,'number',ro.rework_number,'status',ro.status,
   'step','Balik hasil/perjalanan rework lalu batalkan order rework yang terkait PO ini.')
   from erp.rework_orders ro join erp.bs_cases bc on bc.id=ro.bs_case_id where bc.po_id=p_po and ro.status<>'CANCELLED'
  union all select jsonb_build_object('order',70,'kind','BS','id',bc.id,'number',bc.bs_number,'status',bc.status,
   'step','Selesaikan pembalikan dokumen terkait dan batalkan kasus BS melalui layar BS.')
   from erp.bs_cases bc where bc.po_id=p_po and bc.status<>'CANCELLED'
  union all select jsonb_build_object('order',70,'kind','SCRAP','id',sb.id,'number',sb.scrap_number,'status',sb.status,
   'step','Balik atau batalkan dokumen scrap yang masih mengikat potongan PO ini.')
   from erp.scrap_batches sb join erp.cutting_groups cg on cg.id=sb.source_cutting_group_id
   where cg.po_id=p_po and sb.status<>'CANCELLED'
  union all select jsonb_build_object('order',80,'kind','PICKUP_DRAFT','id',pk.id,
   'step','Hapus draft Bagi Potongan terlebih dahulu; koreksi akan mengganti semua pembagian yang sudah diposting dalam PO.')
   from erp.cutting_pickups pk join erp.cutting_groups cg on cg.id=pk.cutting_group_id where cg.po_id=p_po and pk.status='DRAFT'
  union all select jsonb_build_object('order',80,'kind','GROUP_STATE','id',cg.id,'number',cg.group_number,'status',cg.status,
   'step','Selesaikan pembalikan proses lanjutan sampai potongan kembali ke status sudah diambil atau menunggu dibagi.')
   from erp.cutting_groups cg where cg.po_id=p_po and(cg.status not in('CUT','PICKED_UP')
    or(cg.status='PICKED_UP'and not exists(select 1 from erp.cutting_pickups pk where pk.cutting_group_id=cg.id and pk.status='POSTED')))
  union all select jsonb_build_object('order',90,'kind','WIP_HISTORY','id',p_po,
   'step','Riwayat perpindahan WIP belum memiliki pasangan pembalikan Native yang lengkap; balik dokumen sumbernya.')
   where not cp7_contractor_correction.wip_closed_v1(p_po)
 )d
$$;

-- A correction of assignment must have zero financial/stock/HPP effect of its
-- own. Native inverses and subsequent sewing own those effects, separately.
create function cp7_contractor_correction.financial_fingerprint_v1(p_po uuid)returns text
language sql stable security definer set search_path=''set TimeZone='UTC'as $$
 select md5(jsonb_build_object(
  'journal_lines',coalesce((select jsonb_agg(to_jsonb(jl)order by jl.id)from erp.journal_lines jl where jl.po_id=p_po),'[]'),
  'journals',coalesce((select jsonb_agg(to_jsonb(je)order by je.id)from erp.journal_entries je where exists(
   select 1 from erp.journal_lines jl where jl.journal_entry_id=je.id and jl.po_id=p_po)),'[]'),
  'fg_lots',coalesce((select jsonb_agg(to_jsonb(fl)order by fl.id)from erp.fg_lots fl where fl.po_id=p_po),'[]'),
  'fg_movements',coalesce((select jsonb_agg(to_jsonb(fm)order by fm.id)from erp.fg_stock_movements fm
   join erp.fg_lots fl on fl.id=fm.lot_id where fl.po_id=p_po),'[]'),
  'hpp_versions',coalesce((select jsonb_agg(to_jsonb(hv)order by hv.id)from erp.hpp_versions hv
   join erp.fg_lots fl on fl.id=hv.lot_id where fl.po_id=p_po),'[]'),
  'hpp_components',coalesce((select jsonb_agg(to_jsonb(hc)order by hc.id)from erp.hpp_version_components hc
   join erp.hpp_versions hv on hv.id=hc.hpp_version_id join erp.fg_lots fl on fl.id=hv.lot_id where fl.po_id=p_po),'[]'),
  'hpp_gl',coalesce((select jsonb_agg(to_jsonb(hg)order by hg.po_id)from erp.po_hpp_gl_state hg where hg.po_id=p_po),'[]'),
  'hpp_gl_events',coalesce((select jsonb_agg(to_jsonb(he)order by he.id)from erp.po_hpp_gl_events he where he.po_id=p_po),'[]'),
  'material_movements',coalesce((select jsonb_agg(to_jsonb(mm)order by mm.id)from erp.material_stock_movements mm where
   mm.roll_id in(select cr.roll_id from erp.cutting_group_rolls cr join erp.cutting_groups cg on cg.id=cr.cutting_group_id where cg.po_id=p_po)
   or mm.source_id in(select cg.id from erp.cutting_groups cg where cg.po_id=p_po)
   or mm.source_id in(select mi.id from erp.contractor_material_issues mi where mi.po_id=p_po)),'[]'),
  'entitlements',coalesce((select jsonb_agg(to_jsonb(ae)order by ae.id)from erp.contractor_accessory_reimbursement_entitlements ae where ae.po_id=p_po),'[]'),
  'payroll_work',coalesce((select jsonb_agg(to_jsonb(wi)order by wi.id)from erp.payroll_work_items wi where wi.po_id=p_po),'[]'),
  'payroll_reimbursements',coalesce((select jsonb_agg(to_jsonb(ri)order by ri.id)from erp.payroll_reimbursements ri where ri.po_id=p_po),'[]')
 )::text)
$$;

-- Full relevant facts are bound to the review, including closed old documents.
create function cp7_contractor_correction.snapshot_v1(p_po uuid)returns jsonb
language sql stable security definer set search_path=''set TimeZone='UTC'as $$
 select jsonb_build_object('po',to_jsonb(po),'groups',
  coalesce((select jsonb_agg(to_jsonb(cg)order by cg.id)from erp.cutting_groups cg where cg.po_id=po.id),'[]'),
  'pickups',coalesce((select jsonb_agg(to_jsonb(pk)order by pk.id)from erp.cutting_pickups pk
   join erp.cutting_groups cg on cg.id=pk.cutting_group_id where cg.po_id=po.id),'[]'),
  'batches',coalesce((select jsonb_agg(to_jsonb(bt)order by bt.id)from erp.cutting_distribution_batches bt
   join erp.cutting_pickups pk on pk.id=bt.pickup_id join erp.cutting_groups cg on cg.id=pk.cutting_group_id where cg.po_id=po.id),'[]'),
  'allocations',coalesce((select jsonb_agg(to_jsonb(al)order by al.id)from erp.cutting_distribution_allocations al
   join erp.cutting_distribution_batches bt on bt.id=al.batch_id join erp.cutting_pickups pk on pk.id=bt.pickup_id
   join erp.cutting_groups cg on cg.id=pk.cutting_group_id where cg.po_id=po.id),'[]'),
  'work',coalesce((select jsonb_agg(to_jsonb(we)order by we.id)from erp.work_completion_events we where we.po_id=po.id),'[]'),
  'work_lines',coalesce((select jsonb_agg(to_jsonb(wl)order by wl.id)from erp.work_completion_lines wl
   join erp.work_completion_events we on we.id=wl.completion_id where we.po_id=po.id),'[]'),
  'work_snapshots',coalesce((select jsonb_agg(to_jsonb(ws)order by ws.id)from erp.po_work_component_snapshots ws where ws.po_id=po.id),'[]'),
  'financial_fingerprint',cp7_contractor_correction.financial_fingerprint_v1(po.id),
  'blockers',cp7_contractor_correction.blockers_v1(po.id),
  'contractors',coalesce((select jsonb_agg(to_jsonb(ct)order by ct.id)from erp.contractors ct
   where ct.contractor_type='MANDOR'and ct.is_active),'[]'),
  'closed_through',(select ac.closed_through from erp.accounting_period_control ac where ac.singleton_id=1))
 from erp.production_orders po where po.id=p_po
$$;

create function cp7_contractor_correction.admitted_group_v1(p_group uuid)returns boolean
language sql stable security definer set search_path=''as $$
 select exists(select 1 from cp7_contractor_correction.context_v1 cx
  join erp.cutting_groups cg on cg.id=cx.group_id and cg.po_id=cx.po_id
  where cx.backend_pid=pg_backend_pid()and cx.transaction_id=txid_current()and cx.actor=auth.uid()
   and cx.group_id=p_group
   and exists(select 1 from cp7_contractor_correction.requests_v1 rq
    where rq.actor=cx.actor and rq.request_id=cx.request_id and rq.response is null))
$$;

create function cp7_contractor_correction.workspace_v1(p_po uuid)returns jsonb
language plpgsql volatile security definer set search_path=''as $$
declare v_access jsonb;v_source jsonb;
begin
 v_access:=cp7_contractor_correction.access_now_v1();
 v_source:=cp7_contractor_correction.snapshot_v1(p_po);
 if v_source is null then raise exception 'CP7_MANDOR_CORRECTION_NOT_FOUND';end if;
 if cp7_contractor_correction.access_now_v1()is distinct from v_access then
  raise exception using errcode='42501',message='CP7_MANDOR_CORRECTION_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.mandor-correction-workspace.v1','po_id',p_po,
  'po_number',v_source->'po'->>'po_number','contractor_id',v_source->'po'->>'contractor_id',
  'contractors',(select coalesce(jsonb_agg(jsonb_build_object('id',ct->>'id','name',ct->>'contractor_name')order by ct->>'contractor_name',ct->>'id'),'[]')
    from jsonb_array_elements(v_source->'contractors')ct),
  'group_count',jsonb_array_length(v_source->'groups'),
  'pickup_count',(select count(*)from jsonb_array_elements(v_source->'pickups')pk where pk->>'status'='POSTED'),
  'blockers',v_source->'blockers','eligible',jsonb_array_length(v_source->'blockers')=0,
  'review_token',md5(v_source::text),'closed_through',v_source->'closed_through',
  'after_step','Catat ulang hasil jahit untuk mandor yang benar dari WIP & Jahit. Periksa pilihan tarif PO lama atau tarif mandor baru pada waktu jahit asli; buat ulang nota hanya sesudah hasilnya benar.',
  'business_DML',false);
end $$;

create function cp7_contractor_correction.command_v1(p jsonb,p_request uuid)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare v_access jsonb;v_old cp7_contractor_correction.requests_v1;v_po erp.production_orders;
 v_source jsonb;v_actor uuid;v_target uuid;v_group erp.cutting_groups;v_pickup erp.cutting_pickups;
 v_batches jsonb;v_result jsonb;v_replacements jsonb:='[]';v_response jsonb;v_check jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 v_access:=cp7_contractor_correction.access_now_v1();
 if p_request is null or jsonb_typeof(p)is distinct from'object'or not(p?&array['po_id','contractor_id','review_token','change_reason'])
  or(select count(*)from jsonb_object_keys(p))<>4
  or jsonb_typeof(p->'po_id')is distinct from'string'or coalesce(p->>'po_id','')!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  or jsonb_typeof(p->'contractor_id')is distinct from'string'or coalesce(p->>'contractor_id','')!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  or jsonb_typeof(p->'review_token')is distinct from'string'or coalesce(p->>'review_token','')!~'^[0-9a-f]{32}$'
  or jsonb_typeof(p->'change_reason')is distinct from'string'or length(btrim(p->>'change_reason'))not between 5 and 1000 then
  raise exception 'CP7_MANDOR_CORRECTION_FIELDS';end if;
 -- All source writers share this financial envelope; refresh rights after waits.
 perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 if cp7_contractor_correction.access_now_v1()is distinct from v_access then
  raise exception using errcode='42501',message='CP7_MANDOR_CORRECTION_ACCESS_CHANGED';end if;
 insert into cp7_contractor_correction.requests_v1 values(auth.uid(),p_request,p,null)on conflict do nothing;
 select *into strict v_old from cp7_contractor_correction.requests_v1 rq where rq.actor=auth.uid()and rq.request_id=p_request for update;
 if v_old.payload is distinct from p then raise exception 'CP7_MANDOR_CORRECTION_REQUEST_CHANGED';end if;
 if v_old.response is not null then return v_old.response;end if;
 -- Legacy sewing takes flow/rows before its Native financial writer. Never
 -- wait for those while holding the global envelope: refuse atomically so
 -- that writer can finish and the operator can obtain a fresh review.
 for v_group in select *from erp.cutting_groups cg where cg.po_id=(p->>'po_id')::uuid order by cg.id loop
  if not pg_try_advisory_xact_lock(hashtextextended('CP6FLOW:'||v_group.id::text,0))then
   raise exception using errcode='55P03',message='CP7_MANDOR_CORRECTION_BUSY';end if;end loop;
 perform 1 from erp.cutting_groups cg where cg.po_id=(p->>'po_id')::uuid order by cg.id for update nowait;
 select *into v_po from erp.production_orders po where po.id=(p->>'po_id')::uuid for update nowait;
 if v_po.id is null then raise exception 'CP7_MANDOR_CORRECTION_NOT_FOUND';end if;
 perform 1 from erp.cutting_pickups pk join erp.cutting_groups cg on cg.id=pk.cutting_group_id
  where cg.po_id=v_po.id order by pk.id for update of pk nowait;
 if cp7_contractor_correction.access_now_v1()is distinct from v_access then
  raise exception using errcode='42501',message='CP7_MANDOR_CORRECTION_ACCESS_CHANGED';end if;
 v_source:=cp7_contractor_correction.snapshot_v1(v_po.id);
 if md5(v_source::text)is distinct from p->>'review_token'then raise exception 'CP7_MANDOR_CORRECTION_STALE_REVIEW';end if;
 if jsonb_array_length(v_source->'blockers')<>0 then raise exception 'CP7_MANDOR_CORRECTION_DEPENDENCIES: %',v_source->'blockers';end if;
 v_target:=(p->>'contractor_id')::uuid;
 if v_po.contractor_id is null or v_po.contractor_id=v_target or not exists(select 1 from erp.contractors ct
  where ct.id=v_target and ct.is_active and ct.contractor_type='MANDOR')then raise exception 'CP7_MANDOR_CORRECTION_TARGET';end if;
 if not exists(select 1 from erp.cutting_groups cg join erp.cutting_pickups pk on pk.cutting_group_id=cg.id
  where cg.po_id=v_po.id and pk.status='POSTED')or exists(select 1 from erp.cutting_groups cg
  join erp.cutting_pickups pk on pk.cutting_group_id=cg.id where cg.po_id=v_po.id and pk.status='POSTED'and pk.contractor_id<>v_po.contractor_id)then
  raise exception 'CP7_MANDOR_CORRECTION_PICKUP_SOURCE';end if;
 v_actor:=erp.current_app_user_id();if v_actor is null then raise exception using errcode='42501',message='CP7_MANDOR_CORRECTION_DENIED';end if;
 perform set_config('app.change_reason',btrim(p->>'change_reason'),true);
 perform erp._cp3_lock_business_date((statement_timestamp()at time zone'Asia/Jakarta')::date);
 update erp.production_orders set contractor_id=v_target,updated_at=clock_timestamp()where id=v_po.id;
 for v_pickup in select pk.*from erp.cutting_pickups pk join erp.cutting_groups cg on cg.id=pk.cutting_group_id
  where cg.po_id=v_po.id and pk.status='POSTED'order by pk.cutting_group_id loop
  select *into strict v_group from erp.cutting_groups cg where cg.id=v_pickup.cutting_group_id;
  select jsonb_agg(jsonb_build_object('batch_no',bt.batch_no,'notes',bt.notes,'allocations',
   (select jsonb_agg(jsonb_build_object('cutting_roll_yield_id',al.cutting_roll_yield_id,'qty_pcs',al.qty_pcs)order by al.id)
    from erp.cutting_distribution_allocations al where al.batch_id=bt.id))order by bt.batch_no,bt.id)
   into v_batches from erp.cutting_distribution_batches bt where bt.pickup_id=v_pickup.id;
  insert into cp7_contractor_correction.context_v1 values(pg_backend_pid(),txid_current(),auth.uid(),p_request,v_po.id,v_group.id);
  insert into cp7_cutting_correction.pickup_context values(pg_backend_pid(),txid_current(),auth.uid(),v_pickup.id,v_group.id);
  update erp.cutting_pickups set status='REVERSED',reversed_by=v_actor,reversed_at=clock_timestamp(),
   reversal_reason=btrim(p->>'change_reason'),updated_at=clock_timestamp()where id=v_pickup.id;
  update erp.cutting_groups set picked_up_at=null,status='CUT',updated_at=clock_timestamp()where id=v_group.id;
  select *into strict v_group from erp.cutting_groups cg where cg.id=v_group.id;
  v_result:=erp.save_cutting_pickup_v1(jsonb_build_object('cutting_group_id',v_group.id,'contractor_id',v_target,
   'picked_up_at',v_pickup.picked_up_at,'allocation_mode',v_pickup.allocation_mode,'action','POST',
   'change_reason',btrim(p->>'change_reason'),'expected_group_version',v_group.row_version,
   'notes',v_pickup.notes,'batches',v_batches),md5('OW05:'||auth.uid()::text||':'||p_request::text||':'||v_group.id::text)::uuid,null);
  v_replacements:=v_replacements||jsonb_build_array(jsonb_build_object('group_id',v_group.id,'old_pickup_id',v_pickup.id,
   'new_pickup_id',v_result->>'pickup_id','picked_up_at',v_pickup.picked_up_at,'allocated_pieces',v_result->'allocated_pieces'));
  delete from cp7_cutting_correction.pickup_context pc where pc.backend_pid=pg_backend_pid()and pc.transaction_id=txid_current();
  delete from cp7_contractor_correction.context_v1 cx where cx.backend_pid=pg_backend_pid()and cx.transaction_id=txid_current();
 end loop;
 v_check:=cp7_contractor_correction.snapshot_v1(v_po.id);
 if v_check->'work'is distinct from v_source->'work'or v_check->'work_lines'is distinct from v_source->'work_lines'
  or v_check->'work_snapshots'is distinct from v_source->'work_snapshots'
  or v_check->>'financial_fingerprint'is distinct from v_source->>'financial_fingerprint'
  or v_check->'po'->>'contractor_id'is distinct from v_target::text or jsonb_array_length(v_check->'blockers')<>0 then
  raise exception 'CP7_MANDOR_CORRECTION_INCOMPLETE';end if;
 if cp7_contractor_correction.access_now_v1()is distinct from v_access then
  raise exception using errcode='42501',message='CP7_MANDOR_CORRECTION_ACCESS_CHANGED';end if;
 v_response:=jsonb_build_object('contract_version','cp7.mandor-correction-result.v1','po_id',v_po.id,'po_number',v_po.po_number,
  'old_contractor_id',v_po.contractor_id,'contractor_id',v_target,'request_id',p_request,'status','PICKUPS_REPLACED',
  'replacements',v_replacements,'sewing_repost_required',true,'wage_history_reassigned',false);
 insert into cp7_contractor_correction.history_v1(actor,request_id,po_id,old_contractor_id,new_contractor_id,source,result,reason,recorded_at)
 values(auth.uid(),p_request,v_po.id,v_po.contractor_id,v_target,
  v_source,v_response,btrim(p->>'change_reason'),clock_timestamp());
 update cp7_contractor_correction.requests_v1 rq set response=v_response where rq.actor=auth.uid()and rq.request_id=p_request;
 return v_response;
end $$;

create function public.erp_cp7_get_mandor_correction_v1(p_po uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_contractor_correction.workspace_v1(p_po)$$;
create function public.erp_cp7_correct_mandor_v1(p_payload jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_contractor_correction.command_v1(p_payload,p_request)$$;
revoke all on all functions in schema cp7_contractor_correction from public,anon,authenticated,service_role,cp7_capture;
revoke all on function public.erp_cp7_get_mandor_correction_v1(uuid),public.erp_cp7_correct_mandor_v1(jsonb,uuid)
 from public,anon,authenticated,service_role,cp7_capture;
grant execute on function public.erp_cp7_get_mandor_correction_v1(uuid),public.erp_cp7_correct_mandor_v1(jsonb,uuid)to authenticated;
