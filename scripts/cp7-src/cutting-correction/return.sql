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

create function cp7_cutting_correction.return_command(p jsonb,p_request uuid,p_expected text)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;old cp7_cutting_correction.return_requests;g erp.cutting_groups;s jsonb;w jsonb;x jsonb;
 r erp.cutting_group_rolls;v_at timestamptz;v_qty numeric;seen uuid[]:='{}';returned jsonb:='[]';
 closed date;value numeric:=0;posted numeric;answer jsonb;
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
 for x in select e from jsonb_array_elements(p->'rolls')e loop
  select *into r from erp.cutting_group_rolls where id=(x->>'cutting_group_roll_id')::uuid and cutting_group_id=g.id for update;
  if r.id is null or r.id=any(seen)then raise exception 'CP7_CUTTING_RETURN_FIELDS';end if;
  seen:=seen||r.id;v_qty:=(x->>'qty_returned')::numeric;
  if v_qty<=0 then raise exception 'CP7_CUTTING_RETURN_FIELDS';end if;
  if v_qty>r.qty_reported_remaining then
   raise exception 'CP7_CUTTING_RETURN_OVER_REMAINING: kain kembali % melebihi sisa yang dicatat saat potong (%). Koreksi potongan dulu bila sisanya memang lebih banyak.',v_qty,r.qty_reported_remaining;end if;
  update erp.cutting_group_rolls set qty_physically_returned=v_qty,return_destination='WAREHOUSE',returned_at=v_at where id=r.id;
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
 if cp7_cutting_correction.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_CUTTING_CORRECTION_ACCESS_CHANGED';end if;
 select coalesce(sum(l.debit),0)into posted from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id
  where j.source_type='CUTTING_MATERIAL_RETURN_LINE'and j.source_id=any(seen)and j.status='POSTED'and l.account_id=erp.account_id('MATERIAL_INVENTORY');
 if not exists(select 1 from erp.cutting_groups x where x.id=g.id and x.material_return_posted)
  or(select count(*)from erp.material_stock_movements m where m.source_type='CUTTING_GROUP_RETURN'and m.source_id=g.id and m.movement_type='CUTTING_RETURN')
   <>cardinality(seen)or posted<>value then
  raise exception 'CP7_CUTTING_RETURN_INCOMPLETE';end if;
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
grant create on schema public to cp7_cutting_read,cp7_cutting_write;
alter function public.erp_cp7_get_cutting_return_v1(uuid)owner to cp7_cutting_read;
alter function public.erp_cp7_return_cutting_fabric_v1(jsonb,uuid,text)owner to cp7_cutting_write;
revoke create on schema public from cp7_cutting_read,cp7_cutting_write;
revoke all on function cp7_cutting_correction.return_workspace(uuid),cp7_cutting_correction.return_command(jsonb,uuid,text)
 from public,anon,authenticated,service_role,cp7_capture,cp7_cutting_read,cp7_cutting_write;
grant execute on function cp7_cutting_correction.return_workspace(uuid)to cp7_cutting_read;
grant execute on function cp7_cutting_correction.return_command(jsonb,uuid,text)to cp7_cutting_write;
revoke all on function public.erp_cp7_get_cutting_return_v1(uuid),public.erp_cp7_return_cutting_fabric_v1(jsonb,uuid,text)from public,anon,authenticated,service_role,cp7_capture;
grant execute on function public.erp_cp7_get_cutting_return_v1(uuid),public.erp_cp7_return_cutting_fabric_v1(jsonb,uuid,text)to authenticated;
