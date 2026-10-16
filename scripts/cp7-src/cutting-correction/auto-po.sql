-- Owner D15-6 (SOL-R1-002): "Pilih A — PO otomatis dari Buat Potongan, seperti alur demo. Pengguna cukup mengisi pekerjaan
-- potong; sistem membuat PO terkait dan menampilkan nomornya untuk pelacakan. Saat disahkan, pembuatan PO dan posting
-- potongan harus atomik. Pengiriman ulang memakai UUID yang sama harus mendapatkan hasil yang sama, tanpa PO atau stok
-- ganda. Draf tetap belum memengaruhi stok maupun keuangan."
-- There is no Native writer that creates an operational Production Order (the only insert is the opening import,
-- erp.apply_migration_open_pos). This facade creates one in the state the Native guard erp.guard_initial_lifecycle_insert_v263e
-- requires of every non-import insert (DRAFT at CUTTING), posts the cutting through the accepted Native writer
-- public.erp_save_cutting_group_before_sewing_v2 (action POST: rolls locked, size slots checked against the PO model, the
-- material issue, stock and journal), and then sets the PO to CUTTING, the state the Native lifecycle derives for a PO whose
-- cutting is posted and not yet picked up (erp.reverse_* of the v2.6.20ac surface). All in one transaction: when any step
-- refuses, nothing stays (no PO, no number used, no movement). Same request, same answer (actor, request); a changed
-- payload under the same request is refused.
-- Drafts (SAVE_DRAFT/DELETE) are kept in this schema only: no ERP row, no stock, no journal, no PO.
-- PO number: PO-<cut date WIB YYMMDD>-<NNN>, the next free number of that day under one lock per day.
create table cp7_cutting_correction.auto_po_requests(
 actor uuid not null,request_id uuid not null,payload jsonb not null,response jsonb,primary key(actor,request_id)
);
create table cp7_cutting_correction.auto_po_drafts(
 id uuid primary key default gen_random_uuid(),model_id uuid not null references erp.product_models,cutting jsonb not null,
 row_version integer not null default 1 check(row_version>0),status text not null default'DRAFT'check(status in('DRAFT','POSTED','DELETED')),
 created_by uuid not null,updated_by uuid not null,created_at timestamptz not null default clock_timestamp(),
 updated_at timestamptz not null default clock_timestamp(),posted_po_id uuid references erp.production_orders,
 posted_group_id uuid references erp.cutting_groups,
 check((status='POSTED')=(posted_po_id is not null and posted_group_id is not null))
);
create table cp7_cutting_correction.auto_po_history(
 actor uuid not null,request_id uuid not null,action text not null check(action in('SAVE_DRAFT','DELETE','POST')),
 draft_id uuid,po_id uuid references erp.production_orders,group_id uuid references erp.cutting_groups,
 payload jsonb not null,result jsonb not null,recorded_at timestamptz not null default clock_timestamp(),primary key(actor,request_id)
);
alter table cp7_cutting_correction.auto_po_requests owner to postgres;
alter table cp7_cutting_correction.auto_po_drafts owner to postgres;
alter table cp7_cutting_correction.auto_po_history owner to postgres;
alter table cp7_cutting_correction.auto_po_requests enable row level security;
alter table cp7_cutting_correction.auto_po_drafts enable row level security;
alter table cp7_cutting_correction.auto_po_history enable row level security;
create policy private_auto_po_requests on cp7_cutting_correction.auto_po_requests for all using(false)with check(false);
create policy private_auto_po_drafts on cp7_cutting_correction.auto_po_drafts for all using(false)with check(false);
create policy private_auto_po_history on cp7_cutting_correction.auto_po_history for all using(false)with check(false);
revoke all on cp7_cutting_correction.auto_po_requests,cp7_cutting_correction.auto_po_drafts,cp7_cutting_correction.auto_po_history
 from public,anon,authenticated,service_role,cp7_capture,cp7_cutting_read,cp7_cutting_write;
create trigger immutable_auto_po_history before update or delete on cp7_cutting_correction.auto_po_history
 for each row execute function cp7_cutting_correction.immutable();
create trigger immutable_auto_po_history_truncate before truncate on cp7_cutting_correction.auto_po_history
 for each statement execute function cp7_cutting_correction.immutable();

-- The Native cutting permissions: view to read, create to keep a draft, create and post to post.
create function cp7_cutting_correction.auto_po_access_now(p_level text)returns jsonb
language plpgsql volatile security definer set search_path=''as $$
declare a jsonb;permission text;
begin
 if auth.uid()is null or auth.jwt()->>'role'is distinct from'authenticated'then
  raise exception using errcode='42501',message='CP7_AUTO_PO_DENIED';end if;
 a:=erp.get_my_access_v1();
 if a->'allowed'is distinct from'true'::jsonb then raise exception using errcode='42501',message='CP7_AUTO_PO_DENIED';end if;
 foreach permission in array array['production.cutting.view']
  ||case p_level when'DRAFT'then array['production.cutting.create']when'POST'then array['production.cutting.create','production.cutting.post']
   else array[]::text[]end loop
  if erp.has_permission(permission)is distinct from true then raise exception using errcode='42501',message='CP7_AUTO_PO_DENIED';end if;
 end loop;
 return a;
end $$;

-- The cutting part of a request, closed: the Native cutting payload without po_id/id/action/change_reason. Shapes only; the
-- Native writer checks rolls, stock, sizes and yields when it posts.
create function cp7_cutting_correction.auto_po_cutting(p jsonb)returns jsonb
language plpgsql stable security definer set search_path=''as $$
declare uuid_re constant text:='^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';x jsonb;y jsonb;
begin
 if jsonb_typeof(p)is distinct from'object'or not(p?&array['pattern_id','source_location_id','cut_at','notes','size_slots','rolls'])
  or(select count(*)from jsonb_object_keys(p))<>6
  or jsonb_typeof(p->'pattern_id')is distinct from'string'or(p->>'pattern_id')!~uuid_re
  or jsonb_typeof(p->'source_location_id')is distinct from'string'or(p->>'source_location_id')!~uuid_re
  or jsonb_typeof(p->'cut_at')is distinct from'string'or length(p->>'cut_at')>40
  or(p->'notes'<>'null'::jsonb and(jsonb_typeof(p->'notes')<>'string'or length(p->>'notes')>1000))
  or jsonb_typeof(p->'size_slots')is distinct from'array'or jsonb_array_length(p->'size_slots')not between 1 and 40
  or jsonb_typeof(p->'rolls')is distinct from'array'or jsonb_array_length(p->'rolls')not between 1 and 200 then
  raise exception 'CP7_AUTO_PO_FIELDS';end if;
 for x in select value from jsonb_array_elements(p->'size_slots')loop
  if jsonb_typeof(x)is distinct from'object'or(select count(*)from jsonb_object_keys(x))<>3 or not(x?&array['slot_no','size_id','drawing_no'])
   or jsonb_typeof(x->'size_id')<>'string'or(x->>'size_id')!~uuid_re or jsonb_typeof(x->'slot_no')<>'number'or jsonb_typeof(x->'drawing_no')<>'number'then
   raise exception 'CP7_AUTO_PO_FIELDS: size_slots';end if;
 end loop;
 for x in select value from jsonb_array_elements(p->'rolls')loop
  if jsonb_typeof(x)is distinct from'object'or(select count(*)from jsonb_object_keys(x))<>5
   or not(x?&array['roll_id','qty_issued','qty_consumed','qty_reported_remaining','yields'])
   or jsonb_typeof(x->'roll_id')<>'string'or(x->>'roll_id')!~uuid_re or jsonb_typeof(x->'yields')<>'array'
   or jsonb_typeof(x->'qty_issued')<>'number'or jsonb_typeof(x->'qty_consumed')<>'number'or jsonb_typeof(x->'qty_reported_remaining')<>'number'then
   raise exception 'CP7_AUTO_PO_FIELDS: rolls';end if;
  for y in select value from jsonb_array_elements(x->'yields')loop
   if jsonb_typeof(y)is distinct from'object'or(select count(*)from jsonb_object_keys(y))<>2 or not(y?&array['slot_no','qty_pcs'])
    or jsonb_typeof(y->'slot_no')<>'number'or jsonb_typeof(y->'qty_pcs')<>'number'or(y->>'qty_pcs')!~'^[0-9]{1,7}$'then
    raise exception 'CP7_AUTO_PO_FIELDS: yields';end if;
  end loop;
 end loop;
 begin perform(p->>'cut_at')::timestamptz;exception when others then raise exception 'CP7_AUTO_PO_FIELDS: cut_at';end;
 return p;
end $$;

create function cp7_cutting_correction.auto_po_workspace(p_query jsonb)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;q jsonb:=coalesce(p_query,'{}'::jsonb);v_offset integer;models jsonb;drafts jsonb;sel jsonb;d cp7_cutting_correction.auto_po_drafts;
 uuid_re constant text:='^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';
begin
 a:=cp7_cutting_correction.auto_po_access_now('READ');
 if jsonb_typeof(q)<>'object'or exists(select 1 from jsonb_object_keys(q)k where k not in('q','offset','draft_id'))
  or(q?'q'and(jsonb_typeof(q->'q')<>'string'or length(q->>'q')>80))
  or(q?'offset'and(jsonb_typeof(q->'offset')<>'number'or(q->>'offset')!~'^[0-9]{1,6}$'))
  or(q?'draft_id'and q->'draft_id'<>'null'::jsonb and(jsonb_typeof(q->'draft_id')<>'string'or(q->>'draft_id')!~uuid_re))then
  raise exception 'CP7_AUTO_PO_QUERY';end if;
 v_offset:=coalesce((q->>'offset')::integer,0);
 -- Active models with their sizes (the size slots a cutting of that model may use, as the Native writer checks them).
 models:=(with hit as(select m.id,m.model_code::text code,m.model_name::text name from erp.product_models m where m.is_active
   and(coalesce(q->>'q','')=''or position(lower(q->>'q')in lower(m.model_code||' '||m.model_name))>0))
  select jsonb_build_object('total',(select count(*)from hit),'offset',v_offset,'query',coalesce(q->>'q',''),
   'rows',coalesce((select jsonb_agg(jsonb_build_object('id',z.id,'code',z.code,'name',z.name,
     'sizes',coalesce((select jsonb_agg(jsonb_build_object('id',s.id,'code',s.size_code)order by pms.sort_order,s.sort_order,s.size_code)
       from erp.product_model_sizes pms join erp.sizes s on s.id=pms.size_id where pms.model_id=z.id and s.is_active),'[]'::jsonb))order by z.code,z.id)
    from(select*from hit order by code,id offset v_offset limit 50)z),'[]'::jsonb)));
 drafts:=coalesce((select jsonb_agg(jsonb_build_object('id',x.id,'model_id',x.model_id,'model_code',m.model_code,'model_name',m.model_name,
   'cut_at',x.cutting->>'cut_at','pieces',(select coalesce(sum((y->>'qty_pcs')::bigint),0)from jsonb_array_elements(x.cutting->'rolls')r,jsonb_array_elements(r->'yields')y),
   'row_version',x.row_version,'updated_at',x.updated_at)order by x.updated_at desc,x.id)
  from(select*from cp7_cutting_correction.auto_po_drafts where status='DRAFT'order by updated_at desc,id limit 50)x
  join erp.product_models m on m.id=x.model_id),'[]'::jsonb);
 if q->>'draft_id'is not null then
  select*into d from cp7_cutting_correction.auto_po_drafts where id=(q->>'draft_id')::uuid and status='DRAFT';
  if d.id is not null then
   sel:=jsonb_build_object('id',d.id,'model_id',d.model_id,'row_version',d.row_version,'cutting',d.cutting,
    'pattern',(select jsonb_build_object('id',pp.id,'code',pp.pattern_code,'revision',pp.revision,'name',pp.pattern_name)
      from erp.production_patterns pp where pp.id=(d.cutting->>'pattern_id')::uuid),
    'model',(select jsonb_build_object('id',m.id,'code',m.model_code,'name',m.model_name,
      'sizes',coalesce((select jsonb_agg(jsonb_build_object('id',s.id,'code',s.size_code)order by pms.sort_order,s.sort_order,s.size_code)
        from erp.product_model_sizes pms join erp.sizes s on s.id=pms.size_id where pms.model_id=m.id and s.is_active),'[]'::jsonb))
      from erp.product_models m where m.id=d.model_id),
    'rolls',coalesce((select jsonb_agg(jsonb_build_object('roll_id',mr.id,'roll_number',mr.roll_number,'material_id',mt.id,
      'material_sku',mt.material_sku,'material_name',mt.material_name,'unit_code',mt.unit_code,'supplier_name',su.supplier_name,
      'original_qty',mr.original_qty,'available_qty',(select coalesce(sum(msm.qty_signed),0)from erp.material_stock_movements msm
        where msm.roll_id=mr.id and msm.location_id=(d.cutting->>'source_location_id')::uuid))order by mr.roll_number,mr.id)
     from erp.material_rolls mr join erp.materials mt on mt.id=mr.material_id left join erp.suppliers su on su.id=mr.supplier_id
     where mr.id in(select(r->>'roll_id')::uuid from jsonb_array_elements(d.cutting->'rolls')r)),'[]'::jsonb));
  end if;
 end if;
 if cp7_cutting_correction.auto_po_access_now('READ')is distinct from a then raise exception using errcode='42501',message='CP7_AUTO_PO_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.cutting-auto-po-workspace.v1','today',(clock_timestamp()at time zone'Asia/Jakarta')::date,
  'can_draft',erp.has_permission('production.cutting.create')is true,
  'can_post',erp.has_permission('production.cutting.create')is true and erp.has_permission('production.cutting.post')is true,
  'models',models,'drafts',drafts,'selected_draft',sel,'business_DML',false);
end $$;

create function cp7_cutting_correction.auto_po_command(p jsonb,p_request uuid)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;old cp7_cutting_correction.auto_po_requests;v_action text;v_level text;keys text[];c jsonb;m erp.product_models;
 d cp7_cutting_correction.auto_po_drafts;v_actor uuid;v_reason text;v_prefix text;v_n integer;v_number text;v_po uuid;r jsonb;
 v_pieces bigint;v_group erp.cutting_groups;answer jsonb;result jsonb;
 uuid_re constant text:='^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 if p_request is null or jsonb_typeof(p)is distinct from'object'or jsonb_typeof(p->'action')is distinct from'string'then raise exception 'CP7_AUTO_PO_FIELDS';end if;
 v_action:=p->>'action';
 v_level:=case v_action when'POST'then'POST'else'DRAFT'end;
 a:=cp7_cutting_correction.auto_po_access_now(v_level);
 keys:=case v_action when'SAVE_DRAFT'then array['action','draft_id','expected_version','model_id','cutting']
  when'DELETE'then array['action','draft_id','expected_version']
  when'POST'then array['action','draft_id','expected_version','model_id','cutting','change_reason']end;
 if keys is null or not(p?&keys)or(select count(*)from jsonb_object_keys(p))<>cardinality(keys)
  or(p->'draft_id'<>'null'::jsonb and(jsonb_typeof(p->'draft_id')<>'string'or(p->>'draft_id')!~uuid_re))
  or(p->'expected_version'<>'null'::jsonb and(jsonb_typeof(p->'expected_version')<>'number'or(p->>'expected_version')!~'^[1-9][0-9]{0,8}$'))
  or((p->'draft_id'='null'::jsonb)<>(p->'expected_version'='null'::jsonb))
  or(v_action='DELETE'and p->'draft_id'='null'::jsonb)
  or(p?'model_id'and(jsonb_typeof(p->'model_id')<>'string'or(p->>'model_id')!~uuid_re))
  or(p?'change_reason'and(jsonb_typeof(p->'change_reason')<>'string'or length(btrim(p->>'change_reason'))not between 5 and 1000))then
  raise exception 'CP7_AUTO_PO_FIELDS';end if;
 if p?'cutting'then c:=cp7_cutting_correction.auto_po_cutting(p->'cutting');end if;
 insert into cp7_cutting_correction.auto_po_requests values(auth.uid(),p_request,p,null)on conflict do nothing;
 select*into strict old from cp7_cutting_correction.auto_po_requests where actor=auth.uid()and request_id=p_request for update;
 if old.payload is distinct from p then raise exception 'CP7_AUTO_PO_REQUEST_CHANGED';end if;
 if cp7_cutting_correction.auto_po_access_now(v_level)is distinct from a then raise exception using errcode='42501',message='CP7_AUTO_PO_ACCESS_CHANGED';end if;
 if old.response is not null then return old.response;end if;
 v_actor:=erp.current_app_user_id();
 if v_actor is null then raise exception using errcode='42501',message='CP7_AUTO_PO_DENIED';end if;

 if p->'draft_id'<>'null'::jsonb then
  select*into d from cp7_cutting_correction.auto_po_drafts where id=(p->>'draft_id')::uuid for update;
  if d.id is null or d.status<>'DRAFT'then raise exception 'CP7_AUTO_PO_DRAFT_NOT_FOUND';end if;
  if d.row_version<>(p->>'expected_version')::integer then raise exception 'CP7_AUTO_PO_STALE_DRAFT';end if;
 end if;
 if p?'model_id'then
  select*into m from erp.product_models where id=(p->>'model_id')::uuid;
  if m.id is null or not m.is_active then raise exception 'CP7_AUTO_PO_MODEL_INACTIVE';end if;
  -- Every size slot is a size of this model (the Native writer checks it against the PO model at POST; a draft is checked now).
  if exists(select 1 from jsonb_array_elements(c->'size_slots')x where not exists(select 1 from erp.product_model_sizes pms join erp.sizes s on s.id=pms.size_id
    where pms.model_id=m.id and s.id=(x->>'size_id')::uuid and s.is_active))then raise exception 'CP7_AUTO_PO_SIZE';end if;
 end if;

 if v_action='SAVE_DRAFT'then
  if d.id is null then
   insert into cp7_cutting_correction.auto_po_drafts(model_id,cutting,created_by,updated_by)values(m.id,c,auth.uid(),auth.uid())returning*into d;
  else
   update cp7_cutting_correction.auto_po_drafts set model_id=m.id,cutting=c,row_version=row_version+1,updated_by=auth.uid(),updated_at=clock_timestamp()
    where id=d.id returning*into d;
  end if;
  result:=jsonb_build_object('draft_id',d.id,'row_version',d.row_version);
 elsif v_action='DELETE'then
  update cp7_cutting_correction.auto_po_drafts set status='DELETED',row_version=row_version+1,updated_by=auth.uid(),updated_at=clock_timestamp()
   where id=d.id returning*into d;
  result:=jsonb_build_object('draft_id',d.id,'row_version',d.row_version);
 else
  v_reason:=btrim(p->>'change_reason');
  perform set_config('app.change_reason',v_reason,true);
  select coalesce(sum((y->>'qty_pcs')::bigint),0)into v_pieces from jsonb_array_elements(c->'rolls')x,jsonb_array_elements(x->'yields')y;
  if v_pieces<=0 or v_pieces>2147483647 then raise exception 'CP7_AUTO_PO_FIELDS: pieces';end if;
  -- The day's next free number, one lock per day (two tabs wait for each other; a refused post releases its number).
  v_prefix:='PO-'||to_char((c->>'cut_at')::timestamptz at time zone'Asia/Jakarta','YYMMDD')||'-';
  perform pg_advisory_xact_lock(hashtextextended('CP7AUTOPO:'||v_prefix,0));
  select count(*)+1 into v_n from erp.production_orders where po_number like v_prefix||'%';
  while exists(select 1 from erp.production_orders where po_number=v_prefix||lpad(v_n::text,3,'0'))loop v_n:=v_n+1;end loop;
  v_number:=v_prefix||lpad(v_n::text,3,'0');
  insert into erp.production_orders(po_number,model_id,target_qty_pcs,status,current_stage,physical_start_at,notes,created_by)
  values(v_number,m.id,v_pieces::integer,'DRAFT','CUTTING',(c->>'cut_at')::timestamptz,'Dibuat otomatis dari Buat Potongan',v_actor)returning id into v_po;
  -- The accepted Native writer posts the cutting on the new PO (one Native request per facade request and actor).
  r:=public.erp_save_cutting_group_before_sewing_v2(c||jsonb_build_object('action','POST','po_id',v_po,'change_reason',v_reason),
   md5(auth.uid()::text||':'||p_request::text||':cp7-auto-po')::uuid,null::bigint);
  select*into v_group from erp.cutting_groups where id=(r->>'cutting_group_id')::uuid;
  if v_group.id is null or v_group.po_id is distinct from v_po or v_group.material_issue_posted is not true
   or(r->>'total_pieces')::bigint<>v_pieces then raise exception 'CP7_AUTO_PO_INCOMPLETE';end if;
  update erp.production_orders set status='CUTTING',current_stage='CUTTING',updated_at=clock_timestamp()where id=v_po and status='DRAFT';
  if(select count(*)from erp.production_orders where id=v_po and status='CUTTING')<>1 then raise exception 'CP7_AUTO_PO_INCOMPLETE';end if;
  if d.id is not null then
   update cp7_cutting_correction.auto_po_drafts set status='POSTED',posted_po_id=v_po,posted_group_id=v_group.id,row_version=row_version+1,
    updated_by=auth.uid(),updated_at=clock_timestamp()where id=d.id;
  end if;
  result:=jsonb_build_object('draft_id',d.id,'po_id',v_po,'po_number',v_number,'cutting_group_id',v_group.id,'group_number',v_group.group_number,
   'total_pieces',v_pieces,'material_issue_posted',true);
 end if;
 if cp7_cutting_correction.auto_po_access_now(v_level)is distinct from a then raise exception using errcode='42501',message='CP7_AUTO_PO_ACCESS_CHANGED';end if;
 insert into cp7_cutting_correction.auto_po_history values(auth.uid(),p_request,v_action,coalesce(d.id,(result->>'draft_id')::uuid),v_po,v_group.id,p,result,clock_timestamp());
 answer:=jsonb_build_object('contract_version','cp7.cutting-auto-po-outcome.v1','kind','COMMITTED_OUTCOME','action',v_action,'request_id',p_request)||result;
 update cp7_cutting_correction.auto_po_requests set response=answer where actor=auth.uid()and request_id=p_request;
 return answer;
end $$;

create function public.erp_cp7_get_cutting_auto_po_v1(p_query jsonb)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_cutting_correction.auto_po_workspace(p_query)$$;
create function public.erp_cp7_save_cutting_auto_po_v1(p_payload jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_cutting_correction.auto_po_command(p_payload,p_request)$$;
alter function cp7_cutting_correction.auto_po_access_now(text)owner to postgres;
alter function cp7_cutting_correction.auto_po_cutting(jsonb)owner to postgres;
alter function cp7_cutting_correction.auto_po_workspace(jsonb)owner to postgres;
alter function cp7_cutting_correction.auto_po_command(jsonb,uuid)owner to postgres;
grant create on schema public to cp7_cutting_read,cp7_cutting_write;
alter function public.erp_cp7_get_cutting_auto_po_v1(jsonb)owner to cp7_cutting_read;
alter function public.erp_cp7_save_cutting_auto_po_v1(jsonb,uuid)owner to cp7_cutting_write;
revoke create on schema public from cp7_cutting_read,cp7_cutting_write;
revoke all on function cp7_cutting_correction.auto_po_access_now(text),cp7_cutting_correction.auto_po_cutting(jsonb),
 cp7_cutting_correction.auto_po_workspace(jsonb),cp7_cutting_correction.auto_po_command(jsonb,uuid)
 from public,anon,authenticated,service_role,cp7_capture,cp7_cutting_read,cp7_cutting_write;
grant execute on function cp7_cutting_correction.auto_po_workspace(jsonb)to cp7_cutting_read;
grant execute on function cp7_cutting_correction.auto_po_command(jsonb,uuid)to cp7_cutting_write;
revoke all on function public.erp_cp7_get_cutting_auto_po_v1(jsonb),public.erp_cp7_save_cutting_auto_po_v1(jsonb,uuid)from public,anon,authenticated,service_role,cp7_capture;
grant execute on function public.erp_cp7_get_cutting_auto_po_v1(jsonb),public.erp_cp7_save_cutting_auto_po_v1(jsonb,uuid)to authenticated;
