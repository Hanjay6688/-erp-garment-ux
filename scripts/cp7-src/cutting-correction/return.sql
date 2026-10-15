-- SG-02 (owner D14-4): leftover fabric of a posted cutting goes back to the warehouse.
-- "Ada langkah 'kain kembali ke gudang': roll yang sama masuk stok lagi beserta nilainya, biaya PO berkurang sebesar itu."
-- The accepted Native erp.post_cutting_material_returns posts the stock movement (CUTTING_RETURN, same roll, issue
-- unit cost), the journal Dr MATERIAL_INVENTORY / Cr WIP for the PO, the material cost recalculation and, when the PO
-- already has finished goods, its PO recost queue entry; all unchanged. No Native writer records the physical return
-- facts on a posted roll, so this command writes exactly those three columns of erp.cutting_group_rolls
-- (qty_physically_returned, return_destination='WAREHOUSE', returned_at) for the reviewed group and then runs the
-- Native posting inside the Native POST_CUTTING execution context, which the actor's own production.cutting.post
-- permission admits (the same admission the Native cutting post uses). Once per cutting group (Native).
create table cp7_cutting_correction.return_requests(
 actor uuid not null,request_id uuid not null,payload jsonb not null,expected_version text not null,
 response jsonb,primary key(actor,request_id)
);
create table cp7_cutting_correction.return_history(
 actor uuid not null,request_id uuid not null,group_id uuid not null references erp.cutting_groups,
 original_source jsonb not null,returned jsonb not null,reason text not null,
 recorded_at timestamptz not null default clock_timestamp(),primary key(actor,request_id)
);
alter table cp7_cutting_correction.return_requests owner to postgres;
alter table cp7_cutting_correction.return_history owner to postgres;
alter table cp7_cutting_correction.return_requests enable row level security;
alter table cp7_cutting_correction.return_history enable row level security;
create policy private_return_requests on cp7_cutting_correction.return_requests for all using(false)with check(false);
create policy private_return_history on cp7_cutting_correction.return_history for all using(false)with check(false);
revoke all on cp7_cutting_correction.return_requests,cp7_cutting_correction.return_history from public,anon,authenticated,service_role,cp7_capture,cp7_cutting_read,cp7_cutting_write;
create trigger immutable_return_history before update or delete on cp7_cutting_correction.return_history
 for each row execute function cp7_cutting_correction.immutable();
create trigger immutable_return_history_truncate before truncate on cp7_cutting_correction.return_history
 for each statement execute function cp7_cutting_correction.immutable();

create function cp7_cutting_correction.return_workspace(p_group uuid)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;s jsonb;g erp.cutting_groups;blockers jsonb:='[]';rolls jsonb;total numeric;warehouse jsonb;open_from date;
begin
 a:=cp7_cutting_correction.access_now();s:=cp7_cutting_correction.snapshot(p_group);
 if s is null then raise exception 'CP7_CUTTING_RETURN_NOT_FOUND';end if;
 select *into g from erp.cutting_groups where id=p_group;
 if not g.material_issue_posted then
  blockers:=blockers||jsonb_build_array(jsonb_build_object('kind','NOT_POSTED','id',g.id,'label',g.group_number));end if;
 if g.material_return_posted then
  blockers:=blockers||jsonb_build_array(jsonb_build_object('kind','ALREADY_RETURNED','id',g.id,'label',g.group_number));end if;
 if exists(select 1 from erp.cutting_group_rolls r where r.cutting_group_id=g.id
   and(r.qty_physically_returned<>0 or coalesce(r.return_destination,'NONE')<>'NONE'or r.returned_at is not null))then
  blockers:=blockers||jsonb_build_array(jsonb_build_object('kind','RETURN_FACTS_PRESENT','id',g.id,'label',g.group_number));end if;
 select jsonb_build_object('id',l.id,'code',l.location_code,'name',l.location_name)into warehouse
  from erp.locations l where l.id=g.source_location_id and l.is_active and l.location_type='RAW_MATERIAL_WAREHOUSE';
 if warehouse is null then
  blockers:=blockers||jsonb_build_array(jsonb_build_object('kind','WAREHOUSE','id',g.id,'label',g.group_number));end if;
 select coalesce(jsonb_agg(jsonb_build_object('cutting_group_roll_id',r.id,'roll_id',r.roll_id,'roll_number',mr.roll_number,
   'material_sku',m.material_sku,'material_name',m.material_name,'unit_code',m.unit_code,
   'qty_issued',r.qty_issued::text,'qty_consumed',r.qty_consumed::text,'qty_reported_remaining',r.qty_reported_remaining::text,
   'unit_cost',r.unit_cost_snapshot::text)order by mr.roll_number,r.id),'[]'),coalesce(sum(r.qty_reported_remaining),0)
  into rolls,total
  from erp.cutting_group_rolls r join erp.material_rolls mr on mr.id=r.roll_id join erp.materials m on m.id=mr.material_id
  where r.cutting_group_id=g.id;
 if total<=0 then
  blockers:=blockers||jsonb_build_array(jsonb_build_object('kind','NOTHING_LEFT','id',g.id,'label',g.group_number));end if;
 select p.closed_through+1 into open_from from erp.accounting_period_control p where p.singleton_id=1;
 if cp7_cutting_correction.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_CUTTING_CORRECTION_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.cutting-return-workspace.v1','group_id',g.id,'po_id',g.po_id,
  'number',g.group_number,'row_version',g.row_version::text,'review_token',md5(s::text),'cut_at',g.cut_at,
  'open_from',open_from,'warehouse',warehouse,'rolls',rolls,'eligible',jsonb_array_length(blockers)=0,'blockers',blockers,
  'business_DML',false);
end $$;

-- One return posting of the reviewed rolls (the return command and a correction share it). Writes the three physical
-- return columns of erp.cutting_group_rolls, then runs the accepted Native erp.post_cutting_material_returns inside the
-- Native POST_CUTTING execution context (the actor's own production.cutting.post admits it), and checks its effect:
-- one active CUTTING_RETURN movement per roll and the posted journal value. Callers hold the group lock.
create function cp7_cutting_correction.post_return_rolls(p_group uuid,p_at timestamptz,p_rolls jsonb)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare g erp.cutting_groups;x jsonb;r erp.cutting_group_rolls;v_qty numeric;seen uuid[]:='{}';returned jsonb:='[]';value numeric:=0;posted numeric;
begin
 select *into strict g from erp.cutting_groups where id=p_group;
 if jsonb_typeof(p_rolls)is distinct from'array'or jsonb_array_length(p_rolls)not between 1 and 200 then raise exception 'CP7_CUTTING_RETURN_FIELDS';end if;
 for x in select e from jsonb_array_elements(p_rolls)e loop
  if jsonb_typeof(x)is distinct from'object'or(select count(*)from jsonb_object_keys(x))<>2 or not(x?&array['cutting_group_roll_id','qty_returned'])
   or jsonb_typeof(x->'cutting_group_roll_id')is distinct from'string'
   or coalesce(x->>'cutting_group_roll_id','')!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
   or jsonb_typeof(x->'qty_returned')is distinct from'string'or coalesce(x->>'qty_returned','')!~'^(0|[1-9][0-9]{0,11})(\.[0-9]{1,6})?$'then
   raise exception 'CP7_CUTTING_RETURN_FIELDS';end if;
  select *into r from erp.cutting_group_rolls where id=(x->>'cutting_group_roll_id')::uuid and cutting_group_id=g.id for update;
  if r.id is null or r.id=any(seen)then raise exception 'CP7_CUTTING_RETURN_FIELDS';end if;
  seen:=seen||r.id;v_qty:=(x->>'qty_returned')::numeric;
  if v_qty<=0 then raise exception 'CP7_CUTTING_RETURN_FIELDS';end if;
  if v_qty>r.qty_reported_remaining then
   raise exception 'CP7_CUTTING_RETURN_OVER_REMAINING: kain kembali % melebihi sisa yang dicatat saat potong (%). Koreksi potongan dulu bila sisanya memang lebih banyak.',v_qty,r.qty_reported_remaining;end if;
  update erp.cutting_group_rolls set qty_physically_returned=v_qty,return_destination='WAREHOUSE',returned_at=p_at where id=r.id;
  -- Native journals a line only when its unrounded value exceeds half a cent.
  if abs(v_qty*coalesce(r.unit_cost_snapshot,0))>0.005 then value:=value+round(v_qty*coalesce(r.unit_cost_snapshot,0),2);end if;
  returned:=returned||jsonb_build_array(jsonb_build_object('cutting_group_roll_id',r.id,'roll_id',r.roll_id,'qty_returned',v_qty::text,
   'unit_cost',r.unit_cost_snapshot::text,'value',round(v_qty*coalesce(r.unit_cost_snapshot,0),2)::text));
 end loop;
 -- The accepted Native posting; its stock, cost, journal, period and pocket guards run unchanged.
 insert into erp.cutting_bridge_execution_context(backend_pid,transaction_id,actor_key,action,permission_key)
  values(pg_backend_pid(),txid_current(),erp._idempotency_actor_key(),'POST_CUTTING','production.cutting.post');
 perform erp.post_cutting_material_returns(g.id,g.source_location_id);
 delete from erp.cutting_bridge_execution_context where backend_pid=pg_backend_pid()and transaction_id=txid_current()
  and actor_key=erp._idempotency_actor_key();
 if not found then raise exception 'CP7_CUTTING_RETURN_CONTEXT_LOST';end if;
 select coalesce(sum(l.debit),0)into posted from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id
  where j.source_type='CUTTING_MATERIAL_RETURN_LINE'and j.source_id=any(seen)and j.status='POSTED'and l.account_id=erp.account_id('MATERIAL_INVENTORY');
 -- A movement already reversed by a cancelled earlier return (D14-10) is history, not an active return.
 if not exists(select 1 from erp.cutting_groups x where x.id=g.id and x.material_return_posted)
  or(select count(*)from erp.material_stock_movements m where m.source_type='CUTTING_GROUP_RETURN'and m.source_id=g.id and m.movement_type='CUTTING_RETURN'
     and not exists(select 1 from erp.material_stock_movements v where v.reversal_of_id=m.id))<>cardinality(seen)or posted<>value then
  raise exception 'CP7_CUTTING_RETURN_INCOMPLETE';end if;
 return jsonb_build_object('rolls',returned,'value',value::text);
end $$;

create function cp7_cutting_correction.return_command(p jsonb,p_request uuid,p_expected text)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;old cp7_cutting_correction.return_requests;g erp.cutting_groups;s jsonb;w jsonb;x jsonb;
 v_at timestamptz;returned jsonb;closed date;value numeric;posted jsonb;answer jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_cutting_correction.access_now();
 if p_request is null or p_expected is null or p_expected!~'^[1-9][0-9]{0,18}$'
  or jsonb_typeof(p)is distinct from'object'or not(p?&array['group_id','po_id','review_token','returned_at','change_reason','rolls'])
  or(select count(*)from jsonb_object_keys(p))<>6
  or jsonb_typeof(p->'group_id')is distinct from'string'or coalesce(p->>'group_id','')!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  or jsonb_typeof(p->'po_id')is distinct from'string'or coalesce(p->>'po_id','')!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  or jsonb_typeof(p->'review_token')is distinct from'string'or coalesce(p->>'review_token','')!~'^[a-f0-9]{32}$'
  or jsonb_typeof(p->'returned_at')is distinct from'string'
  or coalesce(p->>'returned_at','')!~'^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}(:[0-9]{2}(\.[0-9]{1,6})?)?(Z|[+-][0-9]{2}:[0-9]{2})$'
  or jsonb_typeof(p->'change_reason')is distinct from'string'or length(btrim(p->>'change_reason'))not between 5 and 1000
  or jsonb_typeof(p->'rolls')is distinct from'array'or jsonb_array_length(p->'rolls')not between 1 and 200
  or exists(select 1 from jsonb_array_elements(p->'rolls')e where jsonb_typeof(e)is distinct from'object'
   or(select count(*)from jsonb_object_keys(e))<>2 or not(e?&array['cutting_group_roll_id','qty_returned'])
   or jsonb_typeof(e->'cutting_group_roll_id')is distinct from'string'
   or coalesce(e->>'cutting_group_roll_id','')!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
   or jsonb_typeof(e->'qty_returned')is distinct from'string'or coalesce(e->>'qty_returned','')!~'^(0|[1-9][0-9]{0,11})(\.[0-9]{1,6})?$')then
  raise exception 'CP7_CUTTING_RETURN_FIELDS';end if;
 begin v_at:=(p->>'returned_at')::timestamptz;exception when others then raise exception 'CP7_CUTTING_RETURN_FIELDS';end;
 insert into cp7_cutting_correction.return_requests values(auth.uid(),p_request,p,p_expected,null)on conflict do nothing;
 select *into strict old from cp7_cutting_correction.return_requests where actor=auth.uid()and request_id=p_request for update;
 if old.payload is distinct from p or old.expected_version is distinct from p_expected then raise exception 'CP7_CUTTING_RETURN_REQUEST_CHANGED';end if;
 if cp7_cutting_correction.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_CUTTING_CORRECTION_ACCESS_CHANGED';end if;
 if old.response is not null then return old.response;end if;
 perform pg_advisory_xact_lock(hashtextextended('CP6FLOW:'||(p->>'group_id'),0));
 select *into g from erp.cutting_groups where id=(p->>'group_id')::uuid for update;
 if g.id is null then raise exception 'CP7_CUTTING_RETURN_NOT_FOUND';end if;
 if cp7_cutting_correction.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_CUTTING_CORRECTION_ACCESS_CHANGED';end if;
 s:=cp7_cutting_correction.snapshot(g.id);w:=cp7_cutting_correction.return_workspace(g.id);
 if g.row_version::text is distinct from p_expected or g.po_id::text is distinct from p->>'po_id'
  or md5(s::text)is distinct from p->>'review_token'then raise exception 'CP7_CUTTING_RETURN_STALE_REVIEW';end if;
 if w->'eligible'is distinct from'true'::jsonb then raise exception 'CP7_CUTTING_RETURN_DEPENDENCIES';end if;
 if v_at<g.cut_at then
  raise exception 'CP7_CUTTING_RETURN_BEFORE_CUT: kain tidak bisa kembali ke gudang sebelum dipotong. Isi tanggal/jam kembali pada atau sesudah waktu potong.';end if;
 if v_at>clock_timestamp()+interval '5 minutes'then
  raise exception 'CP7_CUTTING_RETURN_IN_FUTURE: tanggal/jam kain kembali ada di masa depan.';end if;
 select p.closed_through into closed from erp.accounting_period_control p where p.singleton_id=1;
 if(v_at at time zone 'Asia/Jakarta')::date<=closed then
  raise exception 'CP7_CUTTING_RETURN_PERIOD_CLOSED: tanggal kain kembali ada di periode yang sudah ditutup. Pilih tanggal sesudah %.',closed;end if;
 posted:=cp7_cutting_correction.post_return_rolls(g.id,v_at,p->'rolls');returned:=posted->'rolls';value:=(posted->>'value')::numeric;
 if cp7_cutting_correction.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_CUTTING_CORRECTION_ACCESS_CHANGED';end if;
 insert into cp7_cutting_correction.return_history values(auth.uid(),p_request,g.id,s,returned,btrim(p->>'change_reason'),clock_timestamp());
 answer:=jsonb_build_object('contract_version','cp7.cutting-return-outcome.v1','kind','COMMITTED_OUTCOME','action','RETURN_FABRIC',
  'request_id',p_request,'group_id',g.id,'po_id',g.po_id,'number',g.group_number,
  'row_version',(select x.row_version::text from erp.cutting_groups x where x.id=g.id),
  'returned_at',v_at,'rolls',returned,'value',value::text,
  'recost_queued',exists(select 1 from erp.cost_recalc_queue q where q.entity_type='PO'and q.entity_id=g.po_id and q.status in('PENDING','RUNNING')));
 update cp7_cutting_correction.return_requests set response=answer where actor=auth.uid()and request_id=p_request;
 return answer;
end $$;

create function public.erp_cp7_get_cutting_return_v1(p_group uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_cutting_correction.return_workspace(p_group)$$;
create function public.erp_cp7_return_cutting_fabric_v1(p_payload jsonb,p_request uuid,p_expected text)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_cutting_correction.return_command(p_payload,p_request,p_expected)$$;
alter function cp7_cutting_correction.return_workspace(uuid)owner to postgres;
alter function cp7_cutting_correction.return_command(jsonb,uuid,text)owner to postgres;
alter function cp7_cutting_correction.post_return_rolls(uuid,timestamptz,jsonb)owner to postgres;
grant create on schema public to cp7_cutting_read,cp7_cutting_write;
alter function public.erp_cp7_get_cutting_return_v1(uuid)owner to cp7_cutting_read;
alter function public.erp_cp7_return_cutting_fabric_v1(jsonb,uuid,text)owner to cp7_cutting_write;
revoke create on schema public from cp7_cutting_read,cp7_cutting_write;
revoke all on function cp7_cutting_correction.return_workspace(uuid),cp7_cutting_correction.return_command(jsonb,uuid,text),cp7_cutting_correction.post_return_rolls(uuid,timestamptz,jsonb)
 from public,anon,authenticated,service_role,cp7_capture,cp7_cutting_read,cp7_cutting_write;
grant execute on function cp7_cutting_correction.return_workspace(uuid)to cp7_cutting_read;
grant execute on function cp7_cutting_correction.return_command(jsonb,uuid,text)to cp7_cutting_write;
revoke all on function public.erp_cp7_get_cutting_return_v1(uuid),public.erp_cp7_return_cutting_fabric_v1(jsonb,uuid,text)from public,anon,authenticated,service_role,cp7_capture;
grant execute on function public.erp_cp7_get_cutting_return_v1(uuid),public.erp_cp7_return_cutting_fabric_v1(jsonb,uuid,text)to authenticated;

-- SG-02 cancel or correct a fabric return (owner D14-10, 15 Oct 2026): "Ya, buat tombol batal/koreksi retur kain.
-- Pembalikan stok, hutang/kredit, jurnal, dan HPP yang terdampak harus selesai dalam satu transaksi, dengan riwayat asli
-- tetap tersimpan. Kalau ada transaksi lanjutan yang menghalangi, tampilkan bagian mana yang harus dibetulkan terlebih
-- dahulu." The inverse is the return part of the accepted Native erp.reverse_cutting_material_flow_before_sewing_v2,
-- applied alone and in the same order: the unchanged Native erp.reverse_journal for each posted
-- CUTTING_MATERIAL_RETURN_LINE journal, one REVERSAL movement per active CUTTING_RETURN movement (reversal_of_id, the
-- Native single-reversal index, chronology and negative-stock guards apply), erp.recalculate_material_cost (which queues
-- the PO recost when the PO already has finished goods, exactly as the return did), then the three return columns and
-- erp.cutting_groups.material_return_posted go back to their state before the return. A fabric return touches no
-- supplier payable or credit. Everything is dated at the cancel instant, as the Native inverse is; the original return,
-- its journal and movement stay in the books (REVERSED / reversed) and in return_history. A correction posts the
-- corrected quantities in the same transaction, at the same instant. When later movements already used the returned
-- fabric, the workspace names them and the command refuses.
create table cp7_cutting_correction.return_reversal_requests(
 actor uuid not null,request_id uuid not null,payload jsonb not null,expected_version text not null,
 response jsonb,primary key(actor,request_id)
);
create table cp7_cutting_correction.return_reversal_history(
 actor uuid not null,request_id uuid not null,group_id uuid not null references erp.cutting_groups,
 original_source jsonb not null,reversed jsonb not null,replacement jsonb,reason text not null,
 recorded_at timestamptz not null default clock_timestamp(),primary key(actor,request_id)
);
alter table cp7_cutting_correction.return_reversal_requests owner to postgres;
alter table cp7_cutting_correction.return_reversal_history owner to postgres;
alter table cp7_cutting_correction.return_reversal_requests enable row level security;
alter table cp7_cutting_correction.return_reversal_history enable row level security;
create policy private_return_reversal_requests on cp7_cutting_correction.return_reversal_requests for all using(false)with check(false);
create policy private_return_reversal_history on cp7_cutting_correction.return_reversal_history for all using(false)with check(false);
revoke all on cp7_cutting_correction.return_reversal_requests,cp7_cutting_correction.return_reversal_history from public,anon,authenticated,service_role,cp7_capture,cp7_cutting_read,cp7_cutting_write;
create trigger immutable_return_reversal_history before update or delete on cp7_cutting_correction.return_reversal_history
 for each row execute function cp7_cutting_correction.immutable();
create trigger immutable_return_reversal_history_truncate before truncate on cp7_cutting_correction.return_reversal_history
 for each statement execute function cp7_cutting_correction.immutable();

create function cp7_cutting_correction.return_reversal_workspace(p_group uuid)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;s jsonb;g erp.cutting_groups;blockers jsonb:='[]';returned jsonb;later jsonb;closed date;today date;
begin
 a:=cp7_cutting_correction.access_now();s:=cp7_cutting_correction.snapshot(p_group);
 if s is null then raise exception 'CP7_CUTTING_RETURN_NOT_FOUND';end if;
 select *into g from erp.cutting_groups where id=p_group;
 -- Active returns: CUTTING_RETURN movements of this group that no movement reverses yet.
 select coalesce(jsonb_agg(jsonb_build_object('movement_id',m.id,'cutting_group_roll_id',r.id,'roll_id',m.roll_id,'roll_number',mr.roll_number,
   'material_sku',mt.material_sku,'material_name',mt.material_name,'unit_code',mt.unit_code,'qty_returned',m.qty_signed::text,
   'returned_at',m.physical_at,'unit_cost',m.unit_cost_snapshot::text,'qty_reported_remaining',r.qty_reported_remaining::text,
   'available_now',(select coalesce(sum(x.qty_signed),0)from erp.material_stock_movements x where x.material_id=m.material_id and x.roll_id is not distinct from m.roll_id and x.location_id=m.location_id)::text,
   'later_uses',(select coalesce(jsonb_agg(jsonb_build_object('movement_id',x.id,'movement_type',x.movement_type,'qty',x.qty_signed::text,'physical_at',x.physical_at,
      'source_type',x.source_type,'source_id',x.source_id,
      'label',coalesce((select c.group_number from erp.cutting_groups c where x.source_type in('CUTTING_GROUP','CUTTING_GROUP_RETURN','CUTTING_GROUP_RETURN_REVERSAL')and c.id=x.source_id),x.source_type))
      order by x.physical_at,x.system_created_at,x.id),'[]')
    from erp.material_stock_movements x where x.material_id=m.material_id and x.roll_id is not distinct from m.roll_id and x.location_id=m.location_id
     and x.qty_signed<0 and(x.physical_at,x.system_created_at,x.id)>(m.physical_at,m.system_created_at,m.id)))
   order by mr.roll_number,m.id),'[]')
  into returned
  from erp.material_stock_movements m join erp.cutting_group_rolls r on r.cutting_group_id=g.id and r.roll_id=m.roll_id
  join erp.material_rolls mr on mr.id=m.roll_id join erp.materials mt on mt.id=m.material_id
  where m.source_type='CUTTING_GROUP_RETURN'and m.source_id=g.id and m.movement_type='CUTTING_RETURN'
   and not exists(select 1 from erp.material_stock_movements v where v.reversal_of_id=m.id);
 if not g.material_return_posted or jsonb_array_length(returned)=0 then
  blockers:=blockers||jsonb_build_array(jsonb_build_object('kind','NOT_RETURNED','id',g.id,'label',g.group_number));end if;
 -- The returned fabric must still be in that roll at that warehouse; otherwise the later uses must be corrected first.
 select coalesce(jsonb_agg(jsonb_build_object('kind','LATER_USE','id',e->>'cutting_group_roll_id','label',e->>'roll_number',
   'qty_returned',e->>'qty_returned','available_now',e->>'available_now','uses',e->'later_uses')),'[]')
  into later from jsonb_array_elements(returned)e where(e->>'available_now')::numeric<(e->>'qty_returned')::numeric;
 blockers:=blockers||later;
 select p.closed_through into closed from erp.accounting_period_control p where p.singleton_id=1;today:=(clock_timestamp()at time zone 'Asia/Jakarta')::date;
 if today<=closed then
  blockers:=blockers||jsonb_build_array(jsonb_build_object('kind','PERIOD_CLOSED','id',g.id,'label',g.group_number,'closed_through',closed));end if;
 if cp7_cutting_correction.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_CUTTING_CORRECTION_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.cutting-return-reversal-workspace.v1','group_id',g.id,'po_id',g.po_id,
  'number',g.group_number,'row_version',g.row_version::text,'review_token',md5(s::text),'cut_at',g.cut_at,
  'returned',returned,'eligible',jsonb_array_length(blockers)=0,'blockers',blockers,'business_DML',false);
end $$;

create function cp7_cutting_correction.return_reversal_command(p jsonb,p_request uuid,p_expected text)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;old cp7_cutting_correction.return_reversal_requests;g erp.cutting_groups;s jsonb;w jsonb;r record;
 v_now timestamptz;reason text;journals jsonb:='[]';movements jsonb:='[]';rev uuid;replacement jsonb;answer jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_cutting_correction.access_now();
 if p_request is null or p_expected is null or p_expected!~'^[1-9][0-9]{0,18}$'
  or jsonb_typeof(p)is distinct from'object'or not(p?&array['group_id','po_id','review_token','change_reason','replacement_rolls'])
  or(select count(*)from jsonb_object_keys(p))<>5
  or jsonb_typeof(p->'group_id')is distinct from'string'or coalesce(p->>'group_id','')!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  or jsonb_typeof(p->'po_id')is distinct from'string'or coalesce(p->>'po_id','')!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  or jsonb_typeof(p->'review_token')is distinct from'string'or coalesce(p->>'review_token','')!~'^[a-f0-9]{32}$'
  or jsonb_typeof(p->'change_reason')is distinct from'string'or length(btrim(p->>'change_reason'))not between 5 and 1000
  or jsonb_typeof(p->'replacement_rolls')is distinct from'array'or jsonb_array_length(p->'replacement_rolls')>200 then
  raise exception 'CP7_CUTTING_RETURN_REVERSAL_FIELDS';end if;
 reason:=btrim(p->>'change_reason');
 insert into cp7_cutting_correction.return_reversal_requests values(auth.uid(),p_request,p,p_expected,null)on conflict do nothing;
 select *into strict old from cp7_cutting_correction.return_reversal_requests where actor=auth.uid()and request_id=p_request for update;
 if old.payload is distinct from p or old.expected_version is distinct from p_expected then raise exception 'CP7_CUTTING_RETURN_REVERSAL_REQUEST_CHANGED';end if;
 if cp7_cutting_correction.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_CUTTING_CORRECTION_ACCESS_CHANGED';end if;
 if old.response is not null then return old.response;end if;
 perform pg_advisory_xact_lock(hashtextextended('CP6FLOW:'||(p->>'group_id'),0));
 select *into g from erp.cutting_groups where id=(p->>'group_id')::uuid for update;
 if g.id is null then raise exception 'CP7_CUTTING_RETURN_NOT_FOUND';end if;
 if cp7_cutting_correction.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_CUTTING_CORRECTION_ACCESS_CHANGED';end if;
 s:=cp7_cutting_correction.snapshot(g.id);w:=cp7_cutting_correction.return_reversal_workspace(g.id);
 if g.row_version::text is distinct from p_expected or g.po_id::text is distinct from p->>'po_id'
  or md5(s::text)is distinct from p->>'review_token'then raise exception 'CP7_CUTTING_RETURN_REVERSAL_STALE_REVIEW';end if;
 if w->'eligible'is distinct from'true'::jsonb then
  raise exception 'CP7_CUTTING_RETURN_REVERSAL_DEPENDENCIES: %',coalesce((select string_agg(case b->>'kind'
    when 'LATER_USE'then 'kain kembali di roll '||(b->>'label')||' sudah dipakai lagi ('||coalesce((select string_agg(u->>'label',', ')from jsonb_array_elements(b->'uses')u),'')||'); betulkan pemakaian itu dulu'
    when 'NOT_RETURNED'then 'belum ada kain kembali yang bisa dibatalkan'
    when 'PERIOD_CLOSED'then 'periode hari ini sudah ditutup'else b->>'kind'end,'; ')from jsonb_array_elements(w->'blockers')b),'');end if;
 v_now:=clock_timestamp();
 insert into erp.cutting_bridge_execution_context(backend_pid,transaction_id,actor_key,action,permission_key)
  values(pg_backend_pid(),txid_current(),erp._idempotency_actor_key(),'POST_CUTTING','production.cutting.post');
 -- 1. The posted return journals, through the unchanged Native reversal (status REVERSED + linked JOURNAL_REVERSAL).
 for r in select je.id from erp.journal_entries je join erp.cutting_group_rolls cgr on cgr.id=je.source_id
   where cgr.cutting_group_id=g.id and je.source_type='CUTTING_MATERIAL_RETURN_LINE'and je.status='POSTED'
   order by je.posting_at desc,je.id desc loop
  rev:=erp.reverse_journal(r.id,'Batal kain kembali ke gudang: '||reason);
  journals:=journals||jsonb_build_array(jsonb_build_object('journal_id',r.id,'reversal_journal_id',rev));
 end loop;
 -- 2. One REVERSAL movement per active return movement, as the Native pre-sewing inverse writes it.
 for r in select m.* from erp.material_stock_movements m
   where m.source_type='CUTTING_GROUP_RETURN'and m.source_id=g.id and m.movement_type='CUTTING_RETURN'
    and not exists(select 1 from erp.material_stock_movements v where v.reversal_of_id=m.id)
   order by m.system_created_at,m.id loop
  insert into erp.material_stock_movements(material_id,roll_id,location_id,movement_type,qty_signed,input_unit_cost,source_type,source_id,
   physical_at,created_by,reversal_of_id,note)
  values(r.material_id,r.roll_id,r.location_id,'REVERSAL',-r.qty_signed,r.unit_cost_snapshot,'CUTTING_GROUP_RETURN_REVERSAL',g.id,
   greatest(v_now,r.physical_at),erp.current_app_user_id(),r.id,'Batal kain kembali ke gudang: '||reason)returning id into rev;
  movements:=movements||jsonb_build_array(jsonb_build_object('movement_id',r.id,'reversal_movement_id',rev,'roll_id',r.roll_id,'qty',r.qty_signed::text));
 end loop;
 if jsonb_array_length(movements)=0 then raise exception 'CP7_CUTTING_RETURN_REVERSAL_DEPENDENCIES: belum ada kain kembali yang bisa dibatalkan';end if;
 -- 3. Material moving average (and its PO recost queue when the PO has finished goods), as after the return.
 for r in select distinct m.material_id from erp.material_stock_movements m where m.source_type='CUTTING_GROUP_RETURN'and m.source_id=g.id loop
  perform erp.recalculate_material_cost(r.material_id);
 end loop;
 -- 4. The return facts and the once-per-cutting flag go back to their state before the return.
 update erp.cutting_group_rolls set qty_physically_returned=0,return_destination=null,returned_at=null
  where cutting_group_id=g.id and(qty_physically_returned<>0 or return_destination is not null or returned_at is not null);
 update erp.cutting_groups set material_return_posted=false where id=g.id;
 delete from erp.cutting_bridge_execution_context where backend_pid=pg_backend_pid()and transaction_id=txid_current()
  and actor_key=erp._idempotency_actor_key();
 if not found then raise exception 'CP7_CUTTING_RETURN_CONTEXT_LOST';end if;
 -- 5. A correction: the corrected quantities, at the same instant, through the same posting as a first return.
 if jsonb_array_length(p->'replacement_rolls')>0 then
  replacement:=cp7_cutting_correction.post_return_rolls(g.id,v_now,p->'replacement_rolls');
 end if;
 if cp7_cutting_correction.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_CUTTING_CORRECTION_ACCESS_CHANGED';end if;
 if exists(select 1 from jsonb_array_elements(journals)j join erp.journal_entries x on x.id=(j->>'journal_id')::uuid where x.status<>'REVERSED')
  or(select count(*)from erp.material_stock_movements m where m.source_type='CUTTING_GROUP_RETURN'and m.source_id=g.id
     and not exists(select 1 from erp.material_stock_movements v where v.reversal_of_id=m.id))
   <>coalesce(jsonb_array_length(replacement->'rolls'),0)
  or(select material_return_posted from erp.cutting_groups where id=g.id)is distinct from(replacement is not null)then
  raise exception 'CP7_CUTTING_RETURN_REVERSAL_INCOMPLETE';end if;
 insert into cp7_cutting_correction.return_reversal_history values(auth.uid(),p_request,g.id,s,
  jsonb_build_object('journals',journals,'movements',movements,'at',v_now),replacement,reason,clock_timestamp());
 answer:=jsonb_build_object('contract_version','cp7.cutting-return-reversal-outcome.v1','kind','COMMITTED_OUTCOME',
  'action',case when replacement is null then 'CANCEL_RETURN'else 'CORRECT_RETURN'end,
  'request_id',p_request,'group_id',g.id,'po_id',g.po_id,'number',g.group_number,
  'row_version',(select x.row_version::text from erp.cutting_groups x where x.id=g.id),'at',v_now,
  'reversed_movements',jsonb_array_length(movements),'reversed_journals',jsonb_array_length(journals),
  'replacement',replacement,
  'recost_queued',exists(select 1 from erp.cost_recalc_queue q where q.entity_type='PO'and q.entity_id=g.po_id and q.status in('PENDING','RUNNING')));
 update cp7_cutting_correction.return_reversal_requests set response=answer where actor=auth.uid()and request_id=p_request;
 return answer;
end $$;

create function public.erp_cp7_get_cutting_return_reversal_v1(p_group uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_cutting_correction.return_reversal_workspace(p_group)$$;
create function public.erp_cp7_reverse_cutting_return_v1(p_payload jsonb,p_request uuid,p_expected text)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_cutting_correction.return_reversal_command(p_payload,p_request,p_expected)$$;
alter function cp7_cutting_correction.return_reversal_workspace(uuid)owner to postgres;
alter function cp7_cutting_correction.return_reversal_command(jsonb,uuid,text)owner to postgres;
grant create on schema public to cp7_cutting_read,cp7_cutting_write;
alter function public.erp_cp7_get_cutting_return_reversal_v1(uuid)owner to cp7_cutting_read;
alter function public.erp_cp7_reverse_cutting_return_v1(jsonb,uuid,text)owner to cp7_cutting_write;
revoke create on schema public from cp7_cutting_read,cp7_cutting_write;
revoke all on function cp7_cutting_correction.return_reversal_workspace(uuid),cp7_cutting_correction.return_reversal_command(jsonb,uuid,text)
 from public,anon,authenticated,service_role,cp7_capture,cp7_cutting_read,cp7_cutting_write;
grant execute on function cp7_cutting_correction.return_reversal_workspace(uuid)to cp7_cutting_read;
grant execute on function cp7_cutting_correction.return_reversal_command(jsonb,uuid,text)to cp7_cutting_write;
revoke all on function public.erp_cp7_get_cutting_return_reversal_v1(uuid),public.erp_cp7_reverse_cutting_return_v1(jsonb,uuid,text)from public,anon,authenticated,service_role,cp7_capture;
grant execute on function public.erp_cp7_get_cutting_return_reversal_v1(uuid),public.erp_cp7_reverse_cutting_return_v1(jsonb,uuid,text)to authenticated;
