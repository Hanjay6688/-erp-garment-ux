-- Owner D15-3: Mandor work rates per model x work component, with the date they apply from (FABLE-017: a new Mandor or
-- a new model needs a rate before "Catat selesai jahit" can pay him). The rate the wage uses is the one the Native
-- snapshot (erp.ensure_po_work_component_snapshots) takes at the sewing time: the model's Work BOM version valid then, and
-- per component the Mandor's rate valid then, else the BOM default rate. A PO keeps the rates of its first wage
-- (po_work_component_snapshots), so a later rate change never alters a wage already recorded.
-- Versions are never edited once a wage used them (Native erp.guard_used_contractor_work_rate): a change is a new version
-- from a later date, which closes the previous one at that date; a version nobody used yet can be corrected in place.
-- The model's work components (its Work BOM) are kept here too: the first version is written by this facade (there is no
-- Native writer for it), every later change goes through the Native erp.save_work_bom_edit (in place before first use,
-- otherwise a successor version from the given date).
create function cp7_master.rate_versions(p_contractor uuid,p_model uuid,p_component uuid)returns jsonb
language sql stable security definer set search_path=''set TimeZone='UTC'as $$
 select coalesce(jsonb_agg(jsonb_build_object('id',r.id,'rate',r.rate_per_pcs::text,'effective_from',r.effective_from,'effective_to',r.effective_to,
   'notes',r.notes,'last_use',(select max(s.committed_at)from erp.po_work_component_snapshots s where s.source_contractor_rate_id=r.id),
   'rework_uses',(select count(*)from erp.rework_component_lines l where l.source_contractor_rate_id=r.id))order by r.effective_from,r.id),'[]'::jsonb)
 from erp.contractor_work_rates r where r.contractor_id=p_contractor and r.model_id=p_model and r.work_component_id=p_component$$;

create function cp7_master.bom(p_model uuid)returns jsonb
language sql stable security definer set search_path=''set TimeZone='UTC'as $$
 select coalesce(jsonb_agg(jsonb_build_object('id',v.id,'version_no',v.version_no,'effective_from',v.effective_from,'effective_to',v.effective_to,
   'is_active',v.is_active,'notes',v.notes,'last_use',(select max(s.committed_at)from erp.po_work_component_snapshots s where s.source_bom_version_id=v.id),
   'items',(select coalesce(jsonb_agg(jsonb_build_object('component_id',i.work_component_id,'code',c.component_code,'name',c.component_name,
     'sequence_no',i.sequence_no,'default_rate',i.default_rate::text)order by i.sequence_no,i.id),'[]'::jsonb)
    from erp.work_bom_items i join erp.work_components c on c.id=i.work_component_id where i.bom_version_id=v.id))
   order by v.effective_from,v.version_no,v.id),'[]'::jsonb)
 from erp.work_bom_versions v where v.model_id=p_model$$;

-- The Work BOM version the sewing screen and the Native snapshot use at a moment: active, valid then, with items.
create function cp7_master.bom_at(p_model uuid,p_at timestamptz)returns uuid
language sql stable security definer set search_path=''as $$
 select v.id from erp.work_bom_versions v where v.model_id=p_model and v.is_active and v.effective_from<=p_at
  and(v.effective_to is null or v.effective_to>p_at)and exists(select 1 from erp.work_bom_items x where x.bom_version_id=v.id)
 order by v.effective_from desc,v.version_no desc,v.id desc limit 1$$;

create function cp7_master.rate_workspace(p_query jsonb)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;q jsonb:=coalesce(p_query,'{}'::jsonb);c erp.contractors;m erp.product_models;v_offset integer;v_bom uuid;comps jsonb;
 models jsonb;can_write boolean;can_price boolean;v_today date;
 uuid_re constant text:='^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';
begin
 a:=cp7_master.access_now('WORK_RATE','READ');
 if jsonb_typeof(q)<>'object'or exists(select 1 from jsonb_object_keys(q)k where k not in('contractor_id','model_id','q','offset'))
  or(q?'q'and(jsonb_typeof(q->'q')<>'string'or length(q->>'q')>80))
  or(q?'offset'and(jsonb_typeof(q->'offset')<>'number'or(q->>'offset')!~'^[0-9]{1,6}$'))
  or(q?'contractor_id'and q->'contractor_id'<>'null'::jsonb and(jsonb_typeof(q->'contractor_id')<>'string'or(q->>'contractor_id')!~uuid_re))
  or(q?'model_id'and q->'model_id'<>'null'::jsonb and(jsonb_typeof(q->'model_id')<>'string'or(q->>'model_id')!~uuid_re))then
  raise exception 'CP7_WORK_RATE_QUERY';end if;
 v_offset:=coalesce((q->>'offset')::integer,0);v_today:=(clock_timestamp()at time zone'Asia/Jakarta')::date;
 can_write:=coalesce(a->'profile'->>'role_code','')in('OWNER','ADMIN')and erp.has_permission('master.workforce.manage')is true;
 can_price:=can_write and erp.has_permission('master.price.edit_draft')is true;
 if q->>'contractor_id'is not null then
  select*into c from erp.contractors where id=(q->>'contractor_id')::uuid and contractor_type='MANDOR';
  if c.id is null then raise exception 'CP7_WORK_RATE_NOT_FOUND';end if;
 end if;
 models:=(with hit as(select x.id,x.model_code::text code,x.model_name::text name,x.is_active from erp.product_models x
   where coalesce(q->>'q','')=''or position(lower(q->>'q')in lower(x.model_code||' '||x.model_name))>0)
  select jsonb_build_object('total',(select count(*)from hit),'offset',v_offset,'query',coalesce(q->>'q',''),
   'rows',coalesce((select jsonb_agg(jsonb_build_object('id',z.id,'code',z.code,'name',z.name,'active',z.is_active,
     'components',(select count(*)from erp.work_bom_items i where i.bom_version_id=cp7_master.bom_at(z.id,clock_timestamp())))order by z.code,z.id)
    from(select*from hit order by code,id offset v_offset limit 20)z),'[]'::jsonb)));
 if q->>'model_id'is not null then
  select*into m from erp.product_models where id=(q->>'model_id')::uuid;
  if m.id is null then raise exception 'CP7_WORK_RATE_NOT_FOUND';end if;
  v_bom:=cp7_master.bom_at(m.id,clock_timestamp());
  -- Components of the version valid now, and of a later version already scheduled.
  select coalesce(jsonb_agg(jsonb_build_object('component_id',k.id,'code',k.component_code,'name',k.component_name,
    'default_rate',(select i.default_rate::text from erp.work_bom_items i where i.bom_version_id=v_bom and i.work_component_id=k.id),
    'in_current_bom',exists(select 1 from erp.work_bom_items i where i.bom_version_id=v_bom and i.work_component_id=k.id),
    'versions',case when c.id is null then'[]'::jsonb else cp7_master.rate_versions(c.id,m.id,k.id)end,
    'current',case when c.id is null then null else(select jsonb_build_object('id',r.id,'rate',r.rate_per_pcs::text,'effective_from',r.effective_from)
      from erp.contractor_work_rates r where r.contractor_id=c.id and r.model_id=m.id and r.work_component_id=k.id
       and r.effective_from<=clock_timestamp()and(r.effective_to is null or r.effective_to>clock_timestamp())order by r.effective_from desc,r.id desc limit 1)end,
    'review_token',md5(case when c.id is null then'[]'::jsonb else cp7_master.rate_versions(c.id,m.id,k.id)end::text))
    order by(select min(i.sequence_no)from erp.work_bom_items i join erp.work_bom_versions v on v.id=i.bom_version_id where v.model_id=m.id and i.work_component_id=k.id),k.component_code,k.id),'[]'::jsonb)
   into comps from erp.work_components k
   where exists(select 1 from erp.work_bom_items i join erp.work_bom_versions v on v.id=i.bom_version_id
    where v.model_id=m.id and v.is_active and i.work_component_id=k.id and(v.effective_to is null or v.effective_to>clock_timestamp()));
 end if;
 if cp7_master.access_now('WORK_RATE','READ')is distinct from a then raise exception using errcode='42501',message='CP7_MASTER_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.work-rate-workspace.v1','can_write',can_write,'can_price',can_price,'today',v_today,
  'contractor',case when c.id is null then null else jsonb_build_object('id',c.id,'code',c.contractor_code,'name',c.contractor_name,'active',c.is_active,
   'attendance_required',c.attendance_required,'is_special',coalesce((cp7_master.policy_at(c.id,v_today)).is_special,false))end,
  'models',models,
  'model',case when m.id is null then null else jsonb_build_object('id',m.id,'code',m.model_code,'name',m.model_name,'active',m.is_active,
   'current_bom_id',v_bom,'bom',cp7_master.bom(m.id),'bom_review_token',md5(cp7_master.bom(m.id)::text),'components',comps)end,
  'component_catalog',(select coalesce(jsonb_agg(jsonb_build_object('id',k.id,'code',k.component_code,'name',k.component_name,
    'category',k.component_category,'sequence_default',k.sequence_default)order by k.sequence_default,k.component_code,k.id),'[]'::jsonb)
   from(select*from erp.work_components where is_active order by sequence_default,component_code,id limit 300)k));
end $$;

create function cp7_master.save_rate(p_action text,p jsonb,p_request uuid)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;old cp7_master.requests;keys text[];v_level text;v_reason text;v_at timestamptz;v_rate numeric;v_versions jsonb;v_after jsonb;
 c erp.contractors;m erp.product_models;k erp.work_components;cur erp.contractor_work_rates;prev erp.contractor_work_rates;
 v_last timestamptz;v_rework bigint;v_entity uuid;v_id uuid;answer jsonb;v_bom jsonb;b erp.work_bom_versions;v_items jsonb;item jsonb;v_seen uuid[]:='{}';
 uuid_re constant text:='^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 v_level:=case when p_action='CREATE_COMPONENT'then'WRITE'else'PRICE'end;
 a:=cp7_master.access_now('WORK_RATE',v_level);
 keys:=case p_action when'SET_RATE'then array['contractor_id','model_id','work_component_id','rate','effective_date','review_token','reason']
  when'STOP_RATE'then array['contractor_id','model_id','work_component_id','effective_date','review_token','reason']
  when'SAVE_BOM'then array['model_id','items','effective_date','review_token','reason']
  when'CREATE_COMPONENT'then array['code','name','category','reason']end;
 if p_request is null or keys is null or jsonb_typeof(p)is distinct from'object'or not(p?&keys)or(select count(*)from jsonb_object_keys(p))<>cardinality(keys)
  or jsonb_typeof(p->'reason')is distinct from'string'or length(btrim(p->>'reason'))not between 5 and 1000
  or exists(select 1 from unnest(array['contractor_id','model_id','work_component_id'])x where p?x and(jsonb_typeof(p->x)<>'string'or(p->>x)!~uuid_re))
  or(p?'rate'and(jsonb_typeof(p->'rate')<>'string'or(p->>'rate')!~'^[0-9]{1,12}([.][0-9]{1,2})?$'))
  or(p?'effective_date'and(jsonb_typeof(p->'effective_date')<>'string'or(p->>'effective_date')!~'^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
   or to_char(to_date(p->>'effective_date','YYYY-MM-DD'),'YYYY-MM-DD')<>p->>'effective_date'))
  or(p?'review_token'and(jsonb_typeof(p->'review_token')<>'string'or(p->>'review_token')!~'^[a-f0-9]{32}$'))
  or(p?'code'and(jsonb_typeof(p->'code')<>'string'or upper(btrim(p->>'code'))!~'^[A-Z0-9][A-Z0-9._/-]{0,39}$'))
  or(p?'name'and(jsonb_typeof(p->'name')<>'string'or length(btrim(p->>'name'))not between 1 and 120))
  or(p?'category'and(jsonb_typeof(p->'category')<>'string'or(p->>'category')not in('LABOR','COMMISSION','FINISHING','OTHER')))
  or(p?'items'and(jsonb_typeof(p->'items')<>'array'or jsonb_array_length(p->'items')not between 1 and 30))then
  raise exception 'CP7_WORK_RATE_FIELDS';end if;
 v_reason:=btrim(p->>'reason');
 if p?'effective_date'then v_at:=((p->>'effective_date')::date)::timestamp at time zone'Asia/Jakarta';end if;
 insert into cp7_master.requests values(auth.uid(),p_request,'WORK_RATE',jsonb_build_object('action',p_action,'payload',p),null)on conflict do nothing;
 select*into strict old from cp7_master.requests where actor=auth.uid()and request_id=p_request for update;
 if old.kind is distinct from'WORK_RATE'or old.payload is distinct from jsonb_build_object('action',p_action,'payload',p)then
  raise exception 'CP7_MASTER_REQUEST_CHANGED';end if;
 if cp7_master.access_now('WORK_RATE',v_level)is distinct from a then raise exception using errcode='42501',message='CP7_MASTER_ACCESS_CHANGED';end if;
 if old.response is not null then return old.response;end if;
 if erp.current_app_user_id()is null then raise exception using errcode='42501',message='CP7_MASTER_DENIED';end if;
 perform set_config('app.change_reason',v_reason,true);

 if p_action='CREATE_COMPONENT'then
  perform pg_advisory_xact_lock(hashtextextended('CP7MASTER:WORK_COMPONENT:'||lower(btrim(p->>'code')),0));
  if exists(select 1 from erp.work_components where lower(component_code)=lower(btrim(p->>'code')))then raise exception 'CP7_MASTER_DUPLICATE_CODE';end if;
  insert into erp.work_components(component_code,component_name,component_category,sequence_default,is_active)
  values(upper(btrim(p->>'code')),btrim(p->>'name'),p->>'category',
   coalesce((select max(sequence_default)+10 from erp.work_components),10),true)returning id into v_entity;
  v_versions:=null;
  v_after:=(select to_jsonb(x)from erp.work_components x where x.id=v_entity);

 elsif p_action='SAVE_BOM'then
  select*into m from erp.product_models where id=(p->>'model_id')::uuid for share;
  if m.id is null then raise exception 'CP7_WORK_RATE_NOT_FOUND';end if;
  if m.is_active is distinct from true then raise exception 'CP7_WORK_RATE_MODEL_INACTIVE';end if;
  for item in select value from jsonb_array_elements(p->'items')loop
   if jsonb_typeof(item)<>'object'or not(item?&array['work_component_id','sequence_no','default_rate'])or(select count(*)from jsonb_object_keys(item))<>3
    or jsonb_typeof(item->'work_component_id')<>'string'or(item->>'work_component_id')!~uuid_re
    or jsonb_typeof(item->'sequence_no')<>'number'or(item->>'sequence_no')!~'^[0-9]{1,3}$'
    or jsonb_typeof(item->'default_rate')<>'string'or(item->>'default_rate')!~'^[0-9]{1,12}([.][0-9]{1,2})?$'
    or(item->>'work_component_id')::uuid=any(v_seen)then raise exception 'CP7_WORK_RATE_FIELDS';end if;
   if not exists(select 1 from erp.work_components where id=(item->>'work_component_id')::uuid and is_active)then raise exception 'CP7_WORK_RATE_COMPONENT';end if;
   v_seen:=v_seen||(item->>'work_component_id')::uuid;
  end loop;
  -- Same lock as the Native overlap guard, then the reviewed state of every version of the model.
  perform pg_advisory_xact_lock(hashtextextended('WBOM:'||m.id::text,0));
  v_bom:=cp7_master.bom(m.id);
  if md5(v_bom::text)is distinct from p->>'review_token'then raise exception 'CP7_WORK_RATE_REVIEW_CHANGED';end if;
  v_versions:=v_bom;
  select*into b from erp.work_bom_versions where model_id=m.id and is_active order by effective_from desc,version_no desc,id desc limit 1 for update;
  if b.id is null then
   if exists(select 1 from erp.work_bom_versions where model_id=m.id)then raise exception 'CP7_WORK_RATE_BOM_INACTIVE';end if;
   insert into erp.work_bom_versions(model_id,version_no,effective_from,effective_to,is_active,notes)
   values(m.id,1,v_at,null,true,v_reason)returning id into v_entity;
   insert into erp.work_bom_items(bom_version_id,work_component_id,sequence_no,default_rate)
   select v_entity,(i->>'work_component_id')::uuid,(i->>'sequence_no')::integer,(i->>'default_rate')::numeric from jsonb_array_elements(p->'items')i;
  else
   select max(committed_at)into v_last from erp.po_work_component_snapshots where source_bom_version_id=b.id;
   -- Native rule for a used version: the successor starts after its last use and after its start, before its end.
   if v_last is not null and(v_at<=v_last or v_at<=b.effective_from or(b.effective_to is not null and v_at>=b.effective_to))then
    raise exception 'CP7_WORK_RATE_BOM_DATE: %',(coalesce(greatest(v_last,b.effective_from),b.effective_from)at time zone'Asia/Jakarta')::date;end if;
   v_items:=(select jsonb_agg(jsonb_build_object('work_component_id',i->>'work_component_id','sequence_no',i->>'sequence_no','default_rate',i->>'default_rate'))
    from jsonb_array_elements(p->'items')i);
   v_entity:=erp.save_work_bom_edit(b.id,v_items,v_at,v_reason);
  end if;
  v_after:=cp7_master.bom(m.id);

 else
  -- SET_RATE / STOP_RATE
  select*into c from erp.contractors where id=(p->>'contractor_id')::uuid and contractor_type='MANDOR'for share;
  if c.id is null then raise exception 'CP7_WORK_RATE_NOT_FOUND';end if;
  if p_action='SET_RATE'and c.is_active is distinct from true then raise exception 'CP7_WORK_RATE_MANDOR_INACTIVE';end if;
  select*into m from erp.product_models where id=(p->>'model_id')::uuid;
  select*into k from erp.work_components where id=(p->>'work_component_id')::uuid;
  if m.id is null or k.id is null then raise exception 'CP7_WORK_RATE_NOT_FOUND';end if;
  if p_action='SET_RATE'and(m.is_active is distinct from true or k.is_active is distinct from true)then raise exception 'CP7_WORK_RATE_MODEL_INACTIVE';end if;
  -- The component must be on the model's Work BOM (a rate outside it is never read by the wage snapshot).
  if not exists(select 1 from erp.work_bom_items i join erp.work_bom_versions v on v.id=i.bom_version_id
    where v.model_id=m.id and v.is_active and i.work_component_id=k.id)then raise exception 'CP7_WORK_RATE_COMPONENT';end if;
  -- The Native overlap guard's lock, so this check and its insert serialize with any other writer of the same key.
  perform pg_advisory_xact_lock(hashtextextended('WRATE:'||c.id::text||':'||m.id::text||':'||k.id::text,0));
  v_versions:=cp7_master.rate_versions(c.id,m.id,k.id);
  if md5(v_versions::text)is distinct from p->>'review_token'then raise exception 'CP7_WORK_RATE_REVIEW_CHANGED';end if;
  if exists(select 1 from erp.contractor_work_rates where contractor_id=c.id and model_id=m.id and work_component_id=k.id and effective_from>v_at)then
   raise exception 'CP7_WORK_RATE_LATER_VERSION';end if;
  if p_action='SET_RATE'then
   v_rate:=(p->>'rate')::numeric;
   select*into cur from erp.contractor_work_rates where contractor_id=c.id and model_id=m.id and work_component_id=k.id and effective_from=v_at for update;
   if cur.id is not null then
    -- A version starting that day: corrected in place only while no wage (and no rework line) used it.
    select max(committed_at)into v_last from erp.po_work_component_snapshots where source_contractor_rate_id=cur.id;
    select count(*)into v_rework from erp.rework_component_lines where source_contractor_rate_id=cur.id;
    if v_last is not null or v_rework>0 then raise exception 'CP7_WORK_RATE_USED';end if;
    if cur.rate_per_pcs=v_rate then raise exception 'CP7_MASTER_NO_CHANGE';end if;
    update erp.contractor_work_rates set rate_per_pcs=v_rate,notes=v_reason where id=cur.id;
    v_entity:=cur.id;
   else
    select*into prev from erp.contractor_work_rates where contractor_id=c.id and model_id=m.id and work_component_id=k.id and effective_from<v_at
     order by effective_from desc,id desc limit 1 for update;
    if prev.id is not null and(prev.effective_to is null or prev.effective_to>v_at)then
     if prev.rate_per_pcs=v_rate and prev.effective_to is null then raise exception 'CP7_MASTER_NO_CHANGE';end if;
     select max(committed_at)into v_last from erp.po_work_component_snapshots where source_contractor_rate_id=prev.id;
     if v_last is not null and v_at<=v_last then raise exception 'CP7_WORK_RATE_USED_UNTIL: %',(v_last at time zone'Asia/Jakarta')::date;end if;
     update erp.contractor_work_rates set effective_to=v_at where id=prev.id;
    end if;
    insert into erp.contractor_work_rates(contractor_id,model_id,work_component_id,rate_per_pcs,effective_from,effective_to,notes)
    values(c.id,m.id,k.id,v_rate,v_at,null,v_reason)returning id into v_entity;
   end if;
  else
   select*into cur from erp.contractor_work_rates where contractor_id=c.id and model_id=m.id and work_component_id=k.id and effective_from<v_at
    and(effective_to is null or effective_to>v_at)order by effective_from desc,id desc limit 1 for update;
   if cur.id is null then raise exception 'CP7_WORK_RATE_NOTHING_TO_STOP';end if;
   select max(committed_at)into v_last from erp.po_work_component_snapshots where source_contractor_rate_id=cur.id;
   if v_last is not null and v_at<=v_last then raise exception 'CP7_WORK_RATE_USED_UNTIL: %',(v_last at time zone'Asia/Jakarta')::date;end if;
   update erp.contractor_work_rates set effective_to=v_at where id=cur.id;
   v_entity:=cur.id;
  end if;
  v_after:=cp7_master.rate_versions(c.id,m.id,k.id);
 end if;

 insert into cp7_master.history(kind,entity_id,action,before,after,reason,actor,request_id)
 values('WORK_RATE',v_entity,p_action,v_versions,v_after,v_reason,auth.uid(),p_request);
 if cp7_master.access_now('WORK_RATE',v_level)is distinct from a then raise exception using errcode='42501',message='CP7_MASTER_ACCESS_CHANGED';end if;
 answer:=jsonb_build_object('contract_version','cp7.work-rate-outcome.v1','kind','COMMITTED_OUTCOME','action',p_action,'request_id',p_request,
  'id',v_entity,'contractor_id',c.id,'model_id',m.id,'work_component_id',k.id,'effective_date',p->>'effective_date','after',v_after,
  'review_token',case when v_after is null then null else md5(v_after::text)end);
 update cp7_master.requests set response=answer where actor=auth.uid()and request_id=p_request;
 return answer;
end $$;

create function public.erp_cp7_get_work_rates_v1(p_query jsonb)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_master.rate_workspace(p_query)$$;
create function public.erp_cp7_save_work_rate_v1(p_action text,p_payload jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_master.save_rate(p_action,p_payload,p_request)$$;

-- Ownership and access: every private function belongs to postgres and only the two private roles may call the four
-- entry points; the public wrappers belong to those roles and only `authenticated` may call them.
do $own$
declare f regprocedure;
begin
 for f in select p.oid::regprocedure from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_master'loop
  execute format('alter function %s owner to postgres',f);
  execute format('revoke all on function %s from public,anon,authenticated,service_role,cp7_capture,cp7_master_read,cp7_master_write',f);
 end loop;
end $own$;
grant execute on function cp7_master.workspace(text,jsonb),cp7_master.rate_workspace(jsonb)to cp7_master_read;
grant execute on function cp7_master.save(text,jsonb,uuid),cp7_master.save_rate(text,jsonb,uuid)to cp7_master_write;
grant create on schema public to cp7_master_read,cp7_master_write;
alter function public.erp_cp7_get_master_v1(text,jsonb)owner to cp7_master_read;
alter function public.erp_cp7_get_work_rates_v1(jsonb)owner to cp7_master_read;
alter function public.erp_cp7_save_master_v1(text,jsonb,uuid)owner to cp7_master_write;
alter function public.erp_cp7_save_work_rate_v1(text,jsonb,uuid)owner to cp7_master_write;
revoke create on schema public from cp7_master_read,cp7_master_write;
revoke all on function public.erp_cp7_get_master_v1(text,jsonb),public.erp_cp7_get_work_rates_v1(jsonb),
 public.erp_cp7_save_master_v1(text,jsonb,uuid),public.erp_cp7_save_work_rate_v1(text,jsonb,uuid)from public,anon,authenticated,service_role,cp7_capture;
grant execute on function public.erp_cp7_get_master_v1(text,jsonb),public.erp_cp7_get_work_rates_v1(jsonb),
 public.erp_cp7_save_master_v1(text,jsonb,uuid),public.erp_cp7_save_work_rate_v1(text,jsonb,uuid)to authenticated;
