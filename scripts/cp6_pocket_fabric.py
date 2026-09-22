"""Pocket fabric: warehouse roll outflow, period expense, no product allocation."""

SCHEMA = r"""
create table erp.pocket_fabric_materials(
 material_id uuid primary key references erp.materials(id),
 created_by uuid references erp.app_users(id),created_at timestamptz not null default clock_timestamp()
);
create table erp.pocket_fabric_usage(
 adjustment_id uuid primary key references erp.material_adjustments(id),
 material_id uuid not null references erp.pocket_fabric_materials(material_id),
 roll_id uuid not null references erp.material_rolls(id),location_id uuid not null references erp.locations(id),
 input_mode text not null check(input_mode in('USED','REMAINING')),
 input_quantity numeric(20,6) not null check(input_quantity>=0),
 stock_before numeric(20,6) not null check(stock_before>0),
 issued_quantity numeric(20,6) not null check(issued_quantity>0 and issued_quantity<=stock_before),
 stock_revision text not null,posted_header jsonb not null,posted_item jsonb not null,
 cost_policy text not null default 'PERIOD_EXPENSE' check(cost_policy='PERIOD_EXPENSE'),
 created_by uuid references erp.app_users(id),created_at timestamptz not null default clock_timestamp(),
 check(issued_quantity=case input_mode when 'USED' then input_quantity else stock_before-input_quantity end)
);
create index pocket_fabric_usage_roll on erp.pocket_fabric_usage(roll_id);
create index pocket_fabric_usage_material on erp.pocket_fabric_usage(material_id);
create index pocket_fabric_usage_location on erp.pocket_fabric_usage(location_id);
create table erp.pocket_fabric_execution_context(
 backend_pid integer not null,transaction_id bigint not null,actor_key text not null,
 adjustment_id uuid not null references erp.pocket_fabric_usage(adjustment_id),
 primary key(backend_pid,transaction_id,adjustment_id)
);
alter table erp.pocket_fabric_materials enable row level security;
alter table erp.pocket_fabric_usage enable row level security;
alter table erp.pocket_fabric_execution_context enable row level security;
revoke all on erp.pocket_fabric_materials,erp.pocket_fabric_usage,erp.pocket_fabric_execution_context from public,anon,authenticated,service_role;
"""

REVISION = r"""create or replace function erp.pocket_fabric_roll_revision_v1(p_roll uuid)
returns text language sql stable security definer set search_path='' set TimeZone='UTC' as $function$
 select encode(extensions.digest(convert_to(jsonb_build_object(
 'roll',(select to_jsonb(r) from erp.material_rolls r where id=p_roll),
 'movements',(select jsonb_agg(to_jsonb(m) order by m.id) from erp.material_stock_movements m where roll_id=p_roll)
 )::text,'UTF8'),'sha256'),'hex');
$function$;
"""

GUARD = r"""create or replace function erp.guard_pocket_fabric_v1()
returns trigger language plpgsql security definer set search_path='' as $function$
declare v_material uuid;v_adjustment uuid;
begin
 if tg_table_name in('pocket_fabric_materials','pocket_fabric_usage') then
  raise exception 'Riwayat kain kantong tetap; gunakan pembatalan tertaut';
 elsif tg_table_name='cutting_group_rolls' then
  select material_id into v_material from erp.material_rolls where id=new.roll_id;
  perform 1 from erp.materials where id=v_material for update;
  if exists(select 1 from erp.pocket_fabric_materials where material_id=v_material) then
   raise exception 'Kain kantong memakai pengurangan stok tanpa hasil ukuran atau HPP produk';end if;
 elsif tg_table_name='material_stock_movements' then
  if new.reversal_of_id is not null then
   select u.adjustment_id into v_adjustment from erp.pocket_fabric_usage u
    join erp.material_adjustment_items i on i.adjustment_id=u.adjustment_id
    join erp.material_stock_movements m on m.source_id=i.id and m.source_type='MATERIAL_ADJUSTMENT_ITEM'
    where m.id=new.reversal_of_id;
   if v_adjustment is not null and not exists(select 1 from erp.pocket_fabric_execution_context c
     where c.backend_pid=pg_backend_pid() and c.transaction_id=txid_current()
      and c.actor_key=erp._idempotency_actor_key() and c.adjustment_id=v_adjustment) then
    raise exception 'Batalkan pengurangan kain kantong melalui dokumen asal';end if;
  end if;
 end if;
 return new;
end;$function$;
"""

READER = r"""create or replace function erp.get_pocket_fabric_workspace_v1(p_query text default '')
returns jsonb language plpgsql security definer set search_path='' set TimeZone='UTC' as $function$
declare v_query text:=lower(btrim(coalesce(p_query,'')));v_result jsonb;
begin
 perform erp.require_owner_admin();perform erp.require_permission('warehouse.stock.adjust');
 if length(v_query)>120 then raise exception 'Pencarian terlalu panjang';end if;
 with balances as (
  select m.roll_id,m.location_id,sum(m.qty_signed)::numeric(20,6) qty
  from erp.material_stock_movements m join erp.pocket_fabric_materials p on p.material_id=m.material_id
  where m.roll_id is not null group by m.roll_id,m.location_id having sum(m.qty_signed)>0
 ), choices as (
  select r.id,r.material_id,r.roll_number,m.material_name,m.unit_code,b.location_id,l.location_name,b.qty::text qty,
   erp.pocket_fabric_roll_revision_v1(r.id) revision
  from balances b join erp.material_rolls r on r.id=b.roll_id join erp.materials m on m.id=r.material_id
  join erp.locations l on l.id=b.location_id
  where m.is_active and l.is_active and l.location_type='RAW_MATERIAL_WAREHOUSE'
   and (v_query='' or strpos(lower(concat_ws(' ',r.roll_number,m.material_sku,m.material_name,l.location_name)),v_query)>0)
 ), recent as (
  select h.id,h.adjustment_number number,h.status,h.row_version::text row_version,
   erp._cp3_business_date(h.physical_at) date,h.notes reason,u.roll_id,r.roll_number,m.material_name,m.unit_code,
   u.input_mode,u.input_quantity::text input_quantity,u.stock_before::text stock_before,u.issued_quantity::text issued_quantity,
   u.cost_policy,(-((erp._cp6_material_adjustment_revaluation_state(h.id)->>'current_value')::numeric))::numeric(20,2)::text current_cost
  from erp.pocket_fabric_usage u join erp.material_adjustments h on h.id=u.adjustment_id
  join erp.material_rolls r on r.id=u.roll_id join erp.materials m on m.id=u.material_id
  where v_query='' or strpos(lower(concat_ws(' ',h.adjustment_number,r.roll_number,m.material_sku,m.material_name)),v_query)>0
  order by h.created_at desc,h.id limit 50
 ) select jsonb_build_object(
  'rolls',coalesce((select jsonb_agg(to_jsonb(x) order by x.roll_number,x.id,x.location_id) from (select * from choices order by roll_number,id,location_id limit 100) x),'[]'::jsonb),
  'roll_count',(select count(*) from choices),
  'materials',coalesce((select jsonb_agg(to_jsonb(x) order by x.name,x.id) from (
    select m.id,m.material_sku sku,m.material_name name from erp.materials m
    where m.is_active and m.material_type='FABRIC' and not exists(select 1 from erp.pocket_fabric_materials where material_id=m.id)
     and (v_query='' or strpos(lower(concat_ws(' ',m.material_sku,m.material_name)),v_query)>0)
     and not exists(select 1 from erp.cutting_group_rolls c join erp.material_rolls r on r.id=c.roll_id where r.material_id=m.id)
    order by m.material_name,m.id limit 50) x),'[]'::jsonb),
  'history',coalesce((select jsonb_agg(to_jsonb(x) order by x.date desc,x.id) from recent x),'[]'::jsonb)
 ) into v_result;
 return v_result;
end;$function$;
"""

COMMAND = r"""create or replace function erp.save_pocket_fabric_action_v1(p_action text,p_payload jsonb,p_client_request_id uuid)
returns jsonb language plpgsql security definer set search_path='' set TimeZone='UTC' set DateStyle='ISO, YMD' as $function$
declare v_action text:=upper(btrim(p_action));v_cached jsonb;v_result jsonb;v_reason text;v_mode text;
 v_material uuid;v_roll uuid;v_location uuid;v_id uuid;v_stock numeric;v_input numeric;v_qty numeric;v_date date;
 v_revision text;v_native jsonb;h erp.material_adjustments%rowtype;u erp.pocket_fabric_usage%rowtype;
begin
 perform erp.require_owner_admin();perform erp.require_permission('warehouse.stock.adjust');
 if v_action is null or v_action not in('REGISTER','POST','REVERSE') then raise exception 'Aksi kain kantong tidak dikenal';end if;
 if jsonb_typeof(p_payload) is distinct from 'object' or octet_length(p_payload::text)>10000 then raise exception 'Data kain kantong tidak valid';end if;
 v_reason:=nullif(btrim(p_payload->>'reason'),'');
 if v_reason is null or length(v_reason)>1000 then raise exception 'Alasan wajib diisi, maksimal 1000 karakter';end if;
 v_cached:=erp._idempotency_begin('save_pocket_fabric_action_v1',p_client_request_id,
  erp._request_hash(jsonb_build_object('action',v_action,'payload',p_payload)));
 if v_cached is not null then return v_cached;end if;
 perform set_config('app.change_reason',v_reason,true);
 if v_action='REGISTER' then
  v_material:=(p_payload->>'material_id')::uuid;
  perform 1 from erp.materials where id=v_material and is_active and material_type='FABRIC' for update;
  if not found then raise exception 'Pilih bahan kain yang aktif';end if;
  if exists(select 1 from erp.cutting_group_rolls c join erp.material_rolls r on r.id=c.roll_id where r.material_id=v_material) then
   raise exception 'Bahan sudah dipakai pada potongan; gunakan master kain kantong tersendiri';end if;
  insert into erp.pocket_fabric_materials(material_id,created_by) values(v_material,erp.current_app_user_id());
  v_id:=v_material;
 elsif v_action='POST' then
  v_roll:=(p_payload->>'roll_id')::uuid;v_location:=(p_payload->>'location_id')::uuid;
  select material_id into v_material from erp.material_rolls where id=v_roll;
  perform 1 from erp.materials where id=v_material and is_active for update;
  if not found or not exists(select 1 from erp.pocket_fabric_materials where material_id=v_material) then raise exception 'Roll belum ditetapkan sebagai kain kantong';end if;
  perform 1 from erp.material_rolls where id=v_roll for update;
  v_revision:=erp.pocket_fabric_roll_revision_v1(v_roll);
  if nullif(p_payload->>'expected_revision','') is null or p_payload->>'expected_revision'<>v_revision then
   raise exception 'STALE_VERSION: stok roll berubah. Muat ulang dan periksa angkanya';end if;
  if coalesce(p_payload->>'date','') !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' then raise exception 'Tanggal wajib YYYY-MM-DD';end if;
  v_date:=(p_payload->>'date')::date;
  if v_date::text<>p_payload->>'date' or v_date>erp._cp3_business_date(statement_timestamp()) then raise exception 'Tanggal pengurangan tidak valid';end if;
  v_mode:=p_payload->>'mode';
  if v_mode is null or v_mode not in('USED','REMAINING') or jsonb_typeof(p_payload->'quantity') is distinct from 'string'
   or coalesce(p_payload->>'quantity','') !~ '^[0-9]{1,14}([.,][0-9]{1,6})?$' then raise exception 'Jumlah harus angka teks, maksimal enam desimal';end if;
  v_input:=replace(p_payload->>'quantity',',','.')::numeric;
  select coalesce(sum(qty_signed),0) into v_stock from erp.material_stock_movements where roll_id=v_roll and location_id=v_location;
  v_qty:=case v_mode when 'USED' then v_input else v_stock-v_input end;
  if v_qty<=0 or v_qty>v_stock then raise exception 'Pengurangan harus positif dan tidak melebihi stok roll di gudang';end if;
  if v_mode='REMAINING' and exists(select 1 from erp.material_stock_movements where roll_id=v_roll and erp._cp3_business_date(physical_at)>v_date) then
   raise exception 'Hitung sisa tidak boleh mendahului pergerakan stok berikutnya; gunakan jumlah keluar bila mencatat mundur';end if;
  v_native:=erp.save_material_adjustment_draft_v2(jsonb_build_object(
   'adjustment_number','KKT-'||p_client_request_id::text,'reason_code','INTERNAL_FACTORY_USE',
   'physical_at',v_date::text||'T12:00:00+07:00','location_id',v_location,'change_reason',v_reason,
   'notes',v_reason,'items',jsonb_build_array(jsonb_build_object('material_id',v_material,'roll_id',v_roll,'qty_signed',(-v_qty)::text))
  ),gen_random_uuid(),null);
  v_id:=(v_native->>'material_adjustment_id')::uuid;
  perform erp.post_material_adjustment_v2(v_id,gen_random_uuid(),(v_native->>'row_version')::bigint,v_reason);
  insert into erp.pocket_fabric_usage(adjustment_id,material_id,roll_id,location_id,input_mode,input_quantity,
   stock_before,issued_quantity,stock_revision,posted_header,posted_item,created_by)
  select v_id,v_material,v_roll,v_location,v_mode,v_input,v_stock,v_qty,v_revision,
   to_jsonb(a)-'status'-'row_version'-'updated_at',to_jsonb(i),erp.current_app_user_id()
  from erp.material_adjustments a join erp.material_adjustment_items i on i.adjustment_id=a.id where a.id=v_id;
 else
  v_id:=(p_payload->>'id')::uuid;
  select * into h from erp.material_adjustments where id=v_id for update;
  select * into u from erp.pocket_fabric_usage where adjustment_id=v_id;
  if u.adjustment_id is null or h.status<>'POSTED' then raise exception 'Pilih pengurangan kain kantong yang masih disahkan';end if;
  if jsonb_typeof(p_payload->'expected_version') is distinct from 'string' or h.row_version::text is distinct from p_payload->>'expected_version' then
   raise exception 'STALE_VERSION: dokumen berubah';end if;
  perform 1 from erp.materials where id=u.material_id for update;
  perform 1 from erp.material_rolls where id=u.roll_id for update;
  insert into erp.pocket_fabric_execution_context values(pg_backend_pid(),txid_current(),erp._idempotency_actor_key(),v_id);
  perform erp.reverse_material_adjustment_v2(v_id,v_reason,gen_random_uuid(),h.row_version);
  delete from erp.pocket_fabric_execution_context where backend_pid=pg_backend_pid() and transaction_id=txid_current() and adjustment_id=v_id;
 end if;
 insert into erp.audit_logs(entity_type,entity_id,action,changed_by,change_reason)
 values(case when v_action='REGISTER' then 'pocket_fabric_materials' else 'pocket_fabric_usage' end,v_id,
  case when v_action='REGISTER' then 'CREATE' when v_action='POST' then 'POST' else 'REVERSE' end,erp.current_app_user_id(),v_reason);
 v_result:=jsonb_build_object('request_id',p_client_request_id,'action',v_action,'id',v_id,
  'status',case when v_action='REGISTER' then 'REGISTERED' else (select status from erp.material_adjustments where id=v_id) end);
 return erp._idempotency_complete('save_pocket_fabric_action_v1',p_client_request_id,v_result);
end;$function$;
"""

CHECKS = r"""create or replace function erp.pocket_fabric_checks_v1()
returns table(check_name text,issue_count bigint) language sql stable security definer set search_path='' set TimeZone='UTC' as $function$
 with docs as (
  select u.*,h.status,h.physical_at,h.reason_code,to_jsonb(h)-'status'-'row_version'-'updated_at' header,
   (erp._cp6_material_adjustment_revaluation_state(h.id)->>'current_value')::numeric signed_value
  from erp.pocket_fabric_usage u join erp.material_adjustments h on h.id=u.adjustment_id
 ), original_journals as (
  select u.adjustment_id,j.id from docs u join erp.journal_entries j on j.source_type='MATERIAL_ADJUSTMENT' and j.source_id=u.adjustment_id
  union select u.adjustment_id,f.journal_entry_id from docs u join erp.material_adjustment_revaluation_facts f on f.adjustment_id=u.adjustment_id
 ), all_journals as (
  select * from original_journals union select o.adjustment_id,j.id from original_journals o join erp.journal_entries j on j.reversal_of_id=o.id
 )
 select 'AP_POCKET_SOURCE'::text,count(*) from docs u where u.header<>u.posted_header or u.reason_code<>'INTERNAL_FACTORY_USE'
  or u.status not in('POSTED','REVERSED') or (select count(*) from erp.material_adjustment_items where adjustment_id=u.adjustment_id)<>1
  or not exists(select 1 from erp.material_adjustment_items i where i.adjustment_id=u.adjustment_id and to_jsonb(i)=u.posted_item
    and i.material_id=u.material_id and i.roll_id=u.roll_id and i.qty_signed=-u.issued_quantity)
 union all select 'AP_POCKET_EXPENSE_LEDGER',count(*) from docs u where
  erp._cp6_supplier_cent_ledger((select array_agg(j.id) from all_journals j where j.adjustment_id=u.adjustment_id))
  is distinct from case when u.signed_value=0 then '{}'::jsonb else jsonb_build_object(
   erp.account_id('MATERIAL_INVENTORY')::text,u.signed_value,erp.account_id('OTHER_EXPENSE')::text,-u.signed_value) end
 union all select 'AP_POCKET_NO_PRODUCT_ALLOCATION',count(*) from erp.cutting_group_rolls c join erp.material_rolls r on r.id=c.roll_id
  join erp.pocket_fabric_materials p on p.material_id=r.material_id;
$function$;
"""

TRIGGERS = r"""
create trigger pocket_fabric_material_immutable before update or delete on erp.pocket_fabric_materials for each row execute function erp.guard_pocket_fabric_v1();
create trigger pocket_fabric_usage_immutable before update or delete on erp.pocket_fabric_usage for each row execute function erp.guard_pocket_fabric_v1();
create trigger pocket_fabric_cutting_guard before insert or update of roll_id on erp.cutting_group_rolls for each row execute function erp.guard_pocket_fabric_v1();
create trigger pocket_fabric_stock_inverse before insert on erp.material_stock_movements for each row execute function erp.guard_pocket_fabric_v1();
"""

def extend_pocket_contract(functions):
    added={
      'erp.pocket_fabric_roll_revision_v1(uuid)':REVISION,
      'erp.guard_pocket_fabric_v1()':GUARD,
      'erp.get_pocket_fabric_workspace_v1(text)':READER,
      'erp.save_pocket_fabric_action_v1(text,jsonb,uuid)':COMMAND,
      'erp.pocket_fabric_checks_v1()':CHECKS,
    }
    for name,args,call in [
      ('get_pocket_fabric_workspace_v1','p_query text default \'\'','p_query'),
      ('save_pocket_fabric_action_v1','p_action text,p_payload jsonb,p_client_request_id uuid','p_action,p_payload,p_client_request_id')]:
        identity='public.erp_'+name+('('+'text' if name.startswith('get_') else '(text,jsonb,uuid')+')'
        added[identity]=f"create or replace function public.erp_{name}({args}) returns jsonb language sql security definer set search_path='' as $function$ select erp.{name}({call});$function$;"
    old=dict(functions);functions.clear();functions.update(added);functions.update(old)
    identity='erp.reverse_journal(uuid,text)'
    needle="  if v_source_type in('OPENING_PREPAYMENT','PREPAYMENT_EVENT')"
    assert functions[identity].count(needle)==1
    guard="""  if v_source_type='MATERIAL_ADJUSTMENT' and exists(select 1 from erp.pocket_fabric_usage u join erp.journal_entries j on j.source_id=u.adjustment_id where j.id=p_journal_entry_id)
    and not exists(select 1 from erp.pocket_fabric_execution_context c join erp.journal_entries j on j.source_id=c.adjustment_id
      where c.backend_pid=pg_backend_pid() and c.transaction_id=txid_current()
      and c.actor_key=erp._idempotency_actor_key() and j.id=p_journal_entry_id) then
    raise exception 'Batalkan pengurangan kain kantong melalui dokumen asal';end if;
"""
    functions[identity]=functions[identity].replace(needle,guard+needle)
    identity='erp.run_v267_financial_truth_checks()'
    needle='select * from erp.initial_prepayment_checks_v1()'
    assert functions[identity].count(needle)==1
    functions[identity]=functions[identity].replace(needle,needle+'\nUNION ALL SELECT * FROM erp.pocket_fabric_checks_v1()')
