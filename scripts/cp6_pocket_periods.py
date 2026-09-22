"""Optional pocket-fabric period allocation, immutable sources and native HPP."""
import json
from pathlib import Path
PREDECESSOR=json.loads(Path('docs/evidence/cp6-pocket-period-predecessor.json').read_text())['functions']

SCHEMA=r"""
create table erp.pocket_periods(
 id uuid primary key default gen_random_uuid(),period_start date not null,period_end date not null,
 manifest jsonb not null,denominator bigint not null check(denominator>0),original_amount numeric(20,2) not null check(original_amount>0),
 reason text not null,created_by uuid not null references erp.app_users(id),created_at timestamptz not null default clock_timestamp(),
 check(period_end>=period_start and period_end-period_start<=366)
);
create table erp.pocket_period_sources(
 pool_id uuid not null references erp.pocket_periods(id),adjustment_id uuid not null references erp.pocket_fabric_usage(adjustment_id),
 original_amount numeric(20,2) not null check(original_amount>=0),primary key(pool_id,adjustment_id)
);
create index pocket_period_source_document on erp.pocket_period_sources(adjustment_id);
create table erp.pocket_period_destinations(
 pool_id uuid not null references erp.pocket_periods(id),event_id uuid not null references erp.sewing_terminal_events(id),
 po_id uuid not null references erp.production_orders(id),contractor_id uuid not null references erp.contractors(id),
 cutting_group_id uuid references erp.cutting_groups(id),sewing_qty bigint not null check(sewing_qty>0),
 preceding_qty bigint not null check(preceding_qty>=0),source_snapshot jsonb not null,primary key(pool_id,event_id)
);
create index pocket_period_destination_event on erp.pocket_period_destinations(event_id);
create index pocket_period_destination_po on erp.pocket_period_destinations(po_id);
create index pocket_period_destination_contractor on erp.pocket_period_destinations(contractor_id);
create index pocket_period_destination_group on erp.pocket_period_destinations(cutting_group_id);
create table erp.pocket_period_events(
 id uuid primary key,pool_id uuid not null references erp.pocket_periods(id),kind text not null check(kind in('POST','RECOST','CANCEL')),
 economic_date date not null,prior_ledger jsonb not null,target_ledger jsonb not null,ledger_delta jsonb not null,
 journal_entry_id uuid unique references erp.journal_entries(id),reason text not null,
 created_by uuid not null references erp.app_users(id),created_at timestamptz not null default clock_timestamp()
);
create index pocket_period_event_pool on erp.pocket_period_events(pool_id);
create unique index pocket_period_one_post on erp.pocket_period_events(pool_id) where kind='POST';
create unique index pocket_period_one_cancel on erp.pocket_period_events(pool_id) where kind='CANCEL';
alter table erp.pocket_periods enable row level security;
alter table erp.pocket_period_sources enable row level security;
alter table erp.pocket_period_destinations enable row level security;
alter table erp.pocket_period_events enable row level security;
revoke all on erp.pocket_periods,erp.pocket_period_sources,erp.pocket_period_destinations,erp.pocket_period_events from public,anon,authenticated,service_role;
"""

LOCK=r"""create or replace function erp.pocket_period_lock_v1() returns void
language plpgsql security definer set search_path='' as $function$
begin
 if not pg_try_advisory_xact_lock(hashtextextended('POCKET_HPP_PERIOD_V1',0)) then
  raise exception 'POCKET_PERIOD_BUSY: alokasi kain kantong sedang berubah. Coba kembali dengan data terbaru';end if;
end;$function$;"""

ACTIVE=r"""create or replace function erp.pocket_period_active_v1(p_pool uuid) returns boolean
language sql stable security definer set search_path='' as $function$
 select exists(select 1 from erp.pocket_periods p where p.id=p_pool)
 and not exists(select 1 from erp.pocket_period_events e where e.pool_id=p_pool and e.kind='CANCEL');
$function$;"""

TOTAL=r"""create or replace function erp.pocket_period_total_v1(p_pool uuid) returns numeric
language sql stable security definer set search_path='' as $function$
 select coalesce(sum(-((erp._cp6_material_adjustment_revaluation_state(s.adjustment_id)->>'current_value')::numeric)),0)::numeric(20,2)
 from erp.pocket_period_sources s where s.pool_id=p_pool;
$function$;"""

AMOUNT=r"""create or replace function erp.pocket_period_amount_v1(p_pool uuid,p_before bigint,p_qty bigint) returns numeric
language sql stable security definer set search_path='' as $function$
 select case when erp.pocket_period_active_v1(p_pool) then
 round(erp.pocket_period_total_v1(p_pool)*(p_before+p_qty)/p.denominator,2)
 -round(erp.pocket_period_total_v1(p_pool)*p_before/p.denominator,2) else 0 end
 from erp.pocket_periods p where p.id=p_pool;
$function$;"""

MANIFEST=r"""create or replace function erp.pocket_period_manifest_v1(p_start date,p_end date) returns jsonb
language sql stable security definer set search_path='' set TimeZone='UTC' as $function$
 with sources as(
  select u.adjustment_id,h.row_version::text version,erp._cp3_business_date(h.physical_at) date,
   u.material_id,u.roll_id,u.issued_quantity::text quantity,
   (-((erp._cp6_material_adjustment_revaluation_state(h.id)->>'current_value')::numeric))::numeric(20,2)::text amount
  from erp.pocket_fabric_usage u join erp.material_adjustments h on h.id=u.adjustment_id
  where h.status='POSTED' and erp._cp3_business_date(h.physical_at) between p_start and p_end
 ), destinations as(
  select e.id event_id,e.po_id,e.contractor_id,e.cutting_group_id,e.qty_signed::bigint sewing_qty,
   coalesce(sum(e.qty_signed) over(order by e.physical_at,e.id rows between unbounded preceding and 1 preceding),0)::bigint preceding_qty,
   to_jsonb(e) source_snapshot
  from erp.sewing_terminal_events e join erp.work_completion_events w on w.id=e.source_work_completion_id
  where e.event_kind='SELESAI_DIJAHIT' and e.qty_signed>0 and w.status='POSTED'
   and erp._cp3_business_date(e.physical_at) between p_start and p_end
   and not exists(select 1 from erp.sewing_terminal_events rv where rv.reversal_of_id=e.id)
 ) select jsonb_build_object('period_start',p_start,'period_end',p_end,
  'sources',coalesce((select jsonb_agg(to_jsonb(s) order by adjustment_id) from sources s),'[]'::jsonb),
  'destinations',coalesce((select jsonb_agg(to_jsonb(d) order by preceding_qty,event_id) from destinations d),'[]'::jsonb),
  'amount',coalesce((select sum(amount::numeric) from sources),0)::numeric(20,2)::text,
  'quantity',coalesce((select sum(sewing_qty) from destinations),0)::bigint::text,
  'blocked_by',coalesce((select jsonb_agg(p.id order by p.id) from erp.pocket_periods p
   where erp.pocket_period_active_v1(p.id) and p.period_start<=p_end and p.period_end>=p_start),'[]'::jsonb));
$function$;"""

STATE=r"""create or replace function erp.pocket_period_state_v1(p_pool uuid) returns jsonb
language sql stable security definer set search_path='' set TimeZone='UTC' as $function$
 select jsonb_build_object('id',p.id,'period_start',p.period_start,'period_end',p.period_end,'reason',p.reason,
  'status',case when erp.pocket_period_active_v1(p.id) then 'ACTIVE' else 'CANCELLED' end,
  'quantity',p.denominator::text,'original_amount',p.original_amount::text,
  'current_amount',(case when erp.pocket_period_active_v1(p.id) then erp.pocket_period_total_v1(p.id) else 0 end)::numeric(20,2)::text,
  'per_piece',(case when erp.pocket_period_active_v1(p.id) then erp.pocket_period_total_v1(p.id)/p.denominator else 0 end)::numeric(24,6)::text,
  'revision',encode(extensions.digest(convert_to(jsonb_build_object('pool',to_jsonb(p),'events',
   (select jsonb_agg(to_jsonb(e) order by e.created_at,e.id) from erp.pocket_period_events e where e.pool_id=p.id),
   'value',erp.pocket_period_total_v1(p.id))::text,'UTF8'),'sha256'),'hex'))
 from erp.pocket_periods p where p.id=p_pool;
$function$;"""

TARGET=r"""create or replace function erp.pocket_period_target_v1(p_pool uuid,p_cancel boolean default false) returns jsonb
language sql stable security definer set search_path='' as $function$
 with values_by_key as(
  select 'WIP|'||d.po_id::text key,sum(erp.pocket_period_amount_v1(d.pool_id,d.preceding_qty,d.sewing_qty)) amount
  from erp.pocket_period_destinations d where d.pool_id=p_pool group by d.po_id
  union all select 'OTHER_EXPENSE',-erp.pocket_period_total_v1(p_pool)
 ) select case when p_cancel or not erp.pocket_period_active_v1(p_pool) then '{}'::jsonb else
 coalesce((select jsonb_object_agg(key,amount) from values_by_key where amount<>0),'{}'::jsonb) end;
$function$;"""

BOOK=r"""create or replace function erp.pocket_period_book_v1(p_pool uuid) returns jsonb
language sql stable security definer set search_path='' as $function$
 with sums as(
  select case when l.account_id=erp.account_id('WIP') and l.po_id is not null then 'WIP|'||l.po_id::text
   when l.account_id=erp.account_id('OTHER_EXPENSE') and l.po_id is null then 'OTHER_EXPENSE'
   else 'INVALID|'||l.account_id::text||'|'||coalesce(l.po_id::text,'') end key,sum(l.debit-l.credit) amount
  from erp.pocket_period_events e join erp.journal_entries j on j.id=e.journal_entry_id
   join erp.journal_lines l on l.journal_entry_id=j.id where e.pool_id=p_pool group by 1
 ) select coalesce(jsonb_object_agg(key,amount) filter(where amount<>0),'{}'::jsonb) from sums;
$function$;"""

PREVIEW=r"""create or replace function erp.preview_pocket_period_v1(p_start date,p_end date) returns jsonb
language plpgsql stable security definer set search_path='' set TimeZone='UTC' as $function$
declare m jsonb;q numeric;v numeric;
begin
 perform erp.require_owner_admin();perform erp.require_permission('warehouse.stock.adjust');perform erp.require_permission('finance.hpp.manage');
 if p_start is null or p_end is null or p_end<p_start or p_end-p_start>366
  or p_end>erp._cp3_business_date(statement_timestamp()) then raise exception 'Pilih periode yang valid, maksimal 367 hari sampai hari ini';end if;
 m:=erp.pocket_period_manifest_v1(p_start,p_end);q:=(m->>'quantity')::numeric;v:=(m->>'amount')::numeric;
 return jsonb_build_object('period_start',p_start,'period_end',p_end,'amount',m->>'amount','quantity',m->>'quantity',
  'source_count',jsonb_array_length(m->'sources'),'per_piece',(case when q>0 then v/q else 0 end)::numeric(24,6)::text,
  'blocked',jsonb_array_length(m->'blocked_by')>0,'can_post',q>0 and v>0 and jsonb_array_length(m->'blocked_by')=0,
  'revision',encode(extensions.digest(convert_to(m::text,'UTF8'),'sha256'),'hex'));
end;$function$;"""

SYNC=r"""create or replace function erp.sync_pocket_period_v1(p_pool uuid,p_date date,p_kind text,p_reason text) returns void
language plpgsql security definer set search_path='' as $function$
declare target jsonb;book jsonb;delta jsonb;lines jsonb;ident uuid:=gen_random_uuid();journal uuid;v_po uuid;v_book_date date;
begin
 perform erp.require_internal();perform erp.pocket_period_lock_v1();
 if p_kind not in('POST','RECOST','CANCEL') or p_date is null or nullif(btrim(p_reason),'') is null then raise exception 'Invalid pocket allocation sync';end if;
 if not erp.pocket_period_active_v1(p_pool) then raise exception 'Alokasi periode sudah dibatalkan';end if;
 target:=erp.pocket_period_target_v1(p_pool,p_kind='CANCEL');book:=erp.pocket_period_book_v1(p_pool);
 select coalesce(jsonb_object_agg(k,amount),'{}'::jsonb) into delta from(
  select coalesce(t.key,b.key) k,coalesce(t.value::numeric,0)-coalesce(b.value::numeric,0) amount
  from jsonb_each_text(target) t full join jsonb_each_text(book) b using(key)) x where amount<>0;
 if delta='{}'::jsonb and p_kind='RECOST' then return;end if;
 if delta<>'{}'::jsonb then
  select jsonb_agg(jsonb_build_object('mapping_key',split_part(key,'|',1),
   'po_id',nullif(split_part(key,'|',2),''),'debit',greatest(value::numeric,0),'credit',greatest(-value::numeric,0)) order by key)
  into lines from jsonb_each_text(delta);
  journal:=erp.post_journal('POCKET_HPP_PERIOD',ident,p_date,p_reason,lines);
  select transaction_date into v_book_date from erp.journal_entries where id=journal;
 end if;
 insert into erp.pocket_period_events(id,pool_id,kind,economic_date,prior_ledger,target_ledger,ledger_delta,journal_entry_id,reason,created_by)
 values(ident,p_pool,p_kind,p_date,book,target,delta,journal,p_reason,erp.current_app_user_id());
 for v_po in select distinct po_id from erp.pocket_period_destinations where pool_id=p_pool order by po_id loop
  perform erp.rebuild_po_hpp(v_po,p_reason);perform erp.propagate_conversion_hpp_for_po(v_po);
  perform erp.sync_po_hpp_to_gl(v_po,p_date);
  if exists(select 1 from erp.production_orders where id=v_po and status='FINISHED') then
   perform erp.sync_finished_po_wip_residual(v_po,coalesce(v_book_date,p_date),p_reason);end if;
 end loop;
 if erp.pocket_period_book_v1(p_pool) is distinct from target then raise exception 'Pocket allocation ledger mismatch';end if;
end;$function$;"""

COMMAND=r"""create or replace function erp.save_pocket_period_action_v1(p_action text,p_payload jsonb,p_request uuid) returns jsonb
language plpgsql security definer set search_path='' set TimeZone='UTC' set DateStyle='ISO, YMD' as $function$
declare cached jsonb;m jsonb;v jsonb;r jsonb;ident uuid;start_day date;end_day date;reason text;
begin
 perform erp.require_owner_admin();perform erp.require_permission('warehouse.stock.adjust');perform erp.require_permission('finance.hpp.manage');
 if p_action not in('POST_PERIOD','CANCEL_PERIOD') or jsonb_typeof(p_payload) is distinct from 'object'
  or octet_length(p_payload::text)>10000 then raise exception 'Data alokasi periode tidak valid';end if;
 reason:=nullif(btrim(p_payload->>'reason'),'');if reason is null or length(reason)>1000 then raise exception 'Alasan wajib diisi, maksimal 1000 karakter';end if;
 cached:=erp._idempotency_begin('save_pocket_fabric_action_v1',p_request,erp._request_hash(jsonb_build_object('action',p_action,'payload',p_payload)));
 if cached is not null then return cached;end if;
 perform erp.pocket_period_lock_v1();perform set_config('app.change_reason',reason,true);
 if p_action='POST_PERIOD' then
  if coalesce(p_payload->>'period_start','') !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
   or coalesce(p_payload->>'period_end','') !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' then raise exception 'Tanggal periode wajib YYYY-MM-DD';end if;
  start_day:=(p_payload->>'period_start')::date;end_day:=(p_payload->>'period_end')::date;
  v:=erp.preview_pocket_period_v1(start_day,end_day);
  if not (v->>'can_post')::boolean then raise exception 'Periode memerlukan biaya dan hasil jahit positif serta tidak boleh tumpang tindih';end if;
  if v->>'revision' is distinct from p_payload->>'expected_revision' then raise exception 'STALE_VERSION: sumber biaya atau hasil jahit berubah; lihat pembagian terbaru';end if;
  perform erp._cp3_lock_business_period(start_day,end_day);
  m:=erp.pocket_period_manifest_v1(start_day,end_day);ident:=gen_random_uuid();
  insert into erp.pocket_periods(id,period_start,period_end,manifest,denominator,original_amount,reason,created_by)
  values(ident,start_day,end_day,m,(m->>'quantity')::bigint,(m->>'amount')::numeric,reason,erp.current_app_user_id());
  insert into erp.pocket_period_sources(pool_id,adjustment_id,original_amount)
  select ident,(x->>'adjustment_id')::uuid,(x->>'amount')::numeric from jsonb_array_elements(m->'sources') x;
  insert into erp.pocket_period_destinations(pool_id,event_id,po_id,contractor_id,cutting_group_id,sewing_qty,preceding_qty,source_snapshot)
  select ident,(x->>'event_id')::uuid,(x->>'po_id')::uuid,(x->>'contractor_id')::uuid,(x->>'cutting_group_id')::uuid,
   (x->>'sewing_qty')::bigint,(x->>'preceding_qty')::bigint,x->'source_snapshot' from jsonb_array_elements(m->'destinations') x;
  perform erp.sync_pocket_period_v1(ident,end_day,'POST',reason);
 else
  ident:=(p_payload->>'id')::uuid;v:=erp.pocket_period_state_v1(ident);
  if v is null or v->>'status'<>'ACTIVE' then raise exception 'Pilih alokasi periode yang aktif';end if;
  if v->>'revision' is distinct from p_payload->>'expected_revision' then raise exception 'STALE_VERSION: alokasi periode berubah';end if;
  perform erp.sync_pocket_period_v1(ident,erp._cp3_business_date(statement_timestamp()),'CANCEL',reason);
 end if;
 insert into erp.audit_logs(entity_type,entity_id,action,changed_by,change_reason)
 values('pocket_periods',ident,case when p_action='POST_PERIOD' then 'POST' else 'REVERSE' end,erp.current_app_user_id(),reason);
 r:=jsonb_build_object('request_id',p_request,'action',p_action,'id',ident,'status',case when p_action='POST_PERIOD' then 'ACTIVE' else 'CANCELLED' end);
 return erp._idempotency_complete('save_pocket_fabric_action_v1',p_request,r);
end;$function$;"""

GUARD=r"""create or replace function erp.guard_pocket_period_v1() returns trigger
language plpgsql security definer set search_path='' as $function$
declare v_pool uuid;v_date date;v_po uuid;v_prior uuid;
begin
 if tg_table_name in('pocket_periods','pocket_period_sources','pocket_period_destinations','pocket_period_events') then
  raise exception 'Riwayat alokasi periode tetap; gunakan pembatalan tertaut';end if;
 if tg_table_name='material_stock_movements' then
 if new.reversal_of_id is null or not exists(
  select 1 from erp.material_stock_movements m join erp.material_adjustment_items i on i.id=m.source_id and m.source_type='MATERIAL_ADJUSTMENT_ITEM'
  join erp.pocket_fabric_usage u on u.adjustment_id=i.adjustment_id where m.id=new.reversal_of_id) then return new;end if;
 elsif tg_table_name='material_adjustment_revaluation_facts' then
  if not exists(select 1 from erp.pocket_fabric_usage where adjustment_id=new.adjustment_id) then return new;end if;
 elsif tg_table_name='work_completion_events' then
  if old.status<>'POSTED' or new.status='POSTED' then return new;end if;
 end if;
 perform erp.pocket_period_lock_v1();
 if tg_table_name='material_adjustment_revaluation_facts' then
  for v_pool in select s.pool_id from erp.pocket_period_sources s where s.adjustment_id=new.adjustment_id and erp.pocket_period_active_v1(s.pool_id) order by s.pool_id loop
   perform erp.sync_pocket_period_v1(v_pool,new.effective_date,'RECOST','Koreksi harga kain kantong');end loop;
 elsif tg_table_name='pocket_fabric_usage' then
  select erp._cp3_business_date(physical_at) into v_date from erp.material_adjustments where id=new.adjustment_id;
  if exists(select 1 from erp.pocket_periods p where erp.pocket_period_active_v1(p.id) and v_date between p.period_start and p.period_end) then
   raise exception 'Batalkan alokasi periode sebelum menambah pengeluaran di periode itu';end if;
 elsif tg_table_name='material_stock_movements' then
  if new.reversal_of_id is not null and exists(select 1 from erp.material_stock_movements m
   join erp.material_adjustment_items i on i.id=m.source_id and m.source_type='MATERIAL_ADJUSTMENT_ITEM'
   join erp.pocket_period_sources s on s.adjustment_id=i.adjustment_id
   where m.id=new.reversal_of_id and erp.pocket_period_active_v1(s.pool_id)) then
   raise exception 'Batalkan alokasi periode sebelum membatalkan pengeluaran kain kantong';end if;
 elsif tg_table_name in('sewing_terminal_events','work_completion_events') then
  if tg_table_name='work_completion_events' then
   if old.status<>'POSTED' or new.status='POSTED' then return new;end if;
   v_date:=erp._cp3_business_date(old.physical_at);v_po:=old.po_id;
  else
   v_date:=erp._cp3_business_date(new.physical_at);v_po:=new.po_id;v_prior:=new.reversal_of_id;
   if v_prior is not null then select erp._cp3_business_date(physical_at) into v_date from erp.sewing_terminal_events where id=v_prior;end if;
  end if;
  if exists(select 1 from erp.pocket_periods p where erp.pocket_period_active_v1(p.id) and
   (v_date between p.period_start and p.period_end or exists(select 1 from erp.pocket_period_destinations d
    join erp.sewing_terminal_events e on e.id=d.event_id where d.pool_id=p.id and d.po_id=v_po and erp._cp3_business_date(e.physical_at)>=v_date))) then
   raise exception 'Batalkan alokasi kain kantong terkait sebelum mengoreksi hasil jahit';end if;
 end if;
 return new;
end;$function$;"""

TRIGGERS='\n'.join(f'create trigger pocket_period_immutable before update or delete on erp.{t} for each row execute function erp.guard_pocket_period_v1();' for t in ['pocket_periods','pocket_period_sources','pocket_period_destinations','pocket_period_events'])+r"""
create trigger pocket_period_recost after insert on erp.material_adjustment_revaluation_facts for each row execute function erp.guard_pocket_period_v1();
create trigger pocket_period_new_source before insert on erp.pocket_fabric_usage for each row execute function erp.guard_pocket_period_v1();
create trigger pocket_period_stock_inverse before insert on erp.material_stock_movements for each row execute function erp.guard_pocket_period_v1();
create trigger pocket_period_sewing before insert on erp.sewing_terminal_events for each row execute function erp.guard_pocket_period_v1();
create trigger pocket_period_work_inverse before update of status on erp.work_completion_events for each row execute function erp.guard_pocket_period_v1();
"""

CHECKS=r"""create or replace function erp.pocket_period_checks_v1()
returns table(check_name text,severity text,issue_count bigint,details text)
language sql stable security definer set search_path='' as $function$
 select 'AP_PERIOD_POCKET_LEDGER'::text,'CRITICAL'::text,count(*),'Period funding matches current source value and cancellation'::text
 from erp.pocket_periods p where erp.pocket_period_book_v1(p.id) is distinct from erp.pocket_period_target_v1(p.id,false)
 union all select 'AP_PERIOD_POCKET_SOURCES','CRITICAL',count(*),'Source membership and original snapshots remain conserved'
 from erp.pocket_periods p where (select sum(s.original_amount) from erp.pocket_period_sources s where s.pool_id=p.id) is distinct from p.original_amount
  or (select count(*) from erp.pocket_period_sources where pool_id=p.id)<>jsonb_array_length(p.manifest->'sources')
  or (select sum(d.sewing_qty) from erp.pocket_period_destinations d where d.pool_id=p.id) is distinct from p.denominator
  or (select count(*) from erp.pocket_period_destinations where pool_id=p.id)<>jsonb_array_length(p.manifest->'destinations')
  or exists(select 1 from erp.pocket_period_destinations d join erp.sewing_terminal_events e on e.id=d.event_id
    where d.pool_id=p.id and (to_jsonb(e)<>d.source_snapshot or (erp.pocket_period_active_v1(p.id) and
     exists(select 1 from erp.sewing_terminal_events rv where rv.reversal_of_id=e.id))))
 union all select 'AP_PERIOD_POCKET_OVERLAP','CRITICAL',count(*),'Active allocation periods never overlap'
 from erp.pocket_periods p join erp.pocket_periods q on p.id<q.id and p.period_start<=q.period_end and p.period_end>=q.period_start
 where erp.pocket_period_active_v1(p.id) and erp.pocket_period_active_v1(q.id)
 union all select 'AP_PERIOD_POCKET_HPP','CRITICAL',count(*),'Current lot HPP includes the exact period source share'
 from erp.fg_lots l join erp.hpp_versions h on h.lot_id=l.id and h.is_current
 where l.lot_origin='PRODUCTION' and exists(select 1 from erp.pocket_period_destinations d where d.po_id=l.po_id)
 and abs(erp.pocket_lot_cost_v1(l.id)-coalesce((select sum(c.total_cost) from erp.hpp_version_components c
  where c.hpp_version_id=h.id and c.source_type='POCKET_PERIOD_ALLOCATION'),0))>0.000001;
$function$;"""

def extend_period_contract(functions):
    for ident,definition,_,_ in PREDECESSOR:
        assert ident not in functions
        functions[ident]=definition
    identity='erp.rebuild_po_hpp(uuid,text)'
    s=functions[identity]
    def replace(old,new,count=1):
        nonlocal s
        assert s.count(old)==count,(identity,old,s.count(old))
        s=s.replace(old,new)
    replace('  v_other numeric(24,6):=0;', '  v_other numeric(24,6):=0;\n  v_pocket numeric(24,6):=0;v_pocket_allocated numeric(24,6):=0;v_lot_pocket numeric(24,6):=0;')
    replace('  perform erp.require_internal();','  perform erp.require_internal();\n  perform erp.pocket_period_lock_v1();\n  select coalesce(sum(erp.pocket_period_amount_v1(d.pool_id,d.preceding_qty,d.sewing_qty)),0) into v_pocket from erp.pocket_period_destinations d where d.po_id=p_po_id;')
    replace('    v_lot_attendance_hpp:=erp.cp6_lot_attendance_cost_v2620c(r.id);','    v_lot_attendance_hpp:=erp.cp6_lot_attendance_cost_v2620c(r.id);\n    v_lot_pocket:=erp.pocket_lot_cost_v1(r.id);v_pocket_allocated:=v_pocket_allocated+v_lot_pocket;')
    replace('+v_lot_attendance_hpp+v_lot_other+v_lot_accessory;','+v_lot_attendance_hpp+v_lot_other+v_lot_accessory+v_lot_pocket;')
    replace("      (v_new_id,'OTHER','Other/adjustment allocation'", "      (v_new_id,'OTHER','Kain kantong: pembagian periode selesai dijahit',v_lot_pocket,'POCKET_PERIOD_ALLOCATION',p_po_id),\n      (v_new_id,'OTHER','Other/adjustment allocation'")
    replace('  if v_labor_allocated < -0.005', "  if v_pocket_allocated < -0.005 or v_pocket_allocated>v_pocket+0.005 then raise exception 'Pocket HPP cost conservation failed';end if;\n  if v_labor_allocated < -0.005")
    replace("    'accessory',v_accessory", "    'pocket_fabric',v_pocket,'pocket_allocated_to_fg',v_pocket_allocated,'pocket_remaining_in_wip',v_pocket-v_pocket_allocated,\n    'accessory',v_accessory")
    functions[identity]=s
    for ident,old,new in [
      ('erp.save_pocket_fabric_action_v1(text,jsonb,uuid)'," if v_action is null", " if v_action in('POST_PERIOD','CANCEL_PERIOD') then return erp.save_pocket_period_action_v1(v_action,p_payload,p_client_request_id);end if;\n perform erp.pocket_period_lock_v1();\n if v_action is null"),
      ('erp.get_pocket_fabric_workspace_v1(text)',"  'history',coalesce", "  'periods',coalesce((select jsonb_agg(erp.pocket_period_state_v1(p.id) order by p.created_at desc,p.id) from (select * from erp.pocket_periods order by created_at desc,id limit 50) p),'[]'::jsonb),\n  'history',coalesce"),
      ('erp.reverse_journal(uuid,text)',"  if v_source_type='MATERIAL_ADJUSTMENT'", "  if v_source_type='POCKET_HPP_PERIOD' then raise exception 'Batalkan alokasi kain kantong melalui periode asal';end if;\n  if v_source_type='MATERIAL_ADJUSTMENT'"),
      ('erp.run_v267_financial_truth_checks()', 'UNION ALL SELECT * FROM erp.pocket_fabric_checks_v1()', 'UNION ALL SELECT * FROM erp.pocket_period_checks_v1()\n UNION ALL SELECT * FROM erp.pocket_fabric_checks_v1()')]:
        assert functions[ident].count(old)==1,(ident,old)
        functions[ident]=functions[ident].replace(old,new)
    added={
      'erp.pocket_period_lock_v1()':LOCK,'erp.pocket_period_active_v1(uuid)':ACTIVE,'erp.pocket_period_total_v1(uuid)':TOTAL,
      'erp.pocket_period_amount_v1(uuid,bigint,bigint)':AMOUNT,'erp.pocket_period_manifest_v1(date,date)':MANIFEST,
      'erp.pocket_period_state_v1(uuid)':STATE,'erp.pocket_period_target_v1(uuid,boolean)':TARGET,'erp.pocket_period_book_v1(uuid)':BOOK,
      'erp.pocket_lot_cost_v1(uuid)':LOT_COST,'erp.preview_pocket_period_v1(date,date)':PREVIEW,
      'erp.sync_pocket_period_v1(uuid,date,text,text)':SYNC,'erp.save_pocket_period_action_v1(text,jsonb,uuid)':COMMAND,
      'erp.guard_pocket_period_v1()':GUARD,'erp.pocket_period_checks_v1()':CHECKS,
      'public.erp_preview_pocket_fabric_period_v1(date,date)':"create or replace function public.erp_preview_pocket_fabric_period_v1(p_period_start date,p_period_end date) returns jsonb language sql stable security definer set search_path='' as $function$ select erp.preview_pocket_period_v1(p_period_start,p_period_end);$function$;",
    }
    old=dict(functions);functions.clear();functions.update(added);functions.update(old)


LOT_COST = "CREATE OR REPLACE FUNCTION erp.pocket_lot_cost_v1(p_lot_id uuid)\n RETURNS numeric\n LANGUAGE sql\n STABLE SECURITY DEFINER\n SET search_path TO ''\nAS $function$\nwith target as(\n  select fl.id,fl.po_id,coalesce(fl.cutting_group_id,qi.cutting_group_id) group_id,\n    fl.initial_qty_pcs::numeric lot_qty,fl.produced_at\n  from erp.fg_lots fl\n  left join erp.qc_inspection_items qi on qi.id=fl.qc_item_id\n  where fl.id=p_lot_id and fl.lot_origin='PRODUCTION'\n), position as(\n  select t.*,\n    coalesce((select sum(x.initial_qty_pcs)::numeric from erp.fg_lots x\n      left join erp.qc_inspection_items xqi on xqi.id=x.qc_item_id\n      where x.po_id=t.po_id and x.lot_origin='PRODUCTION'\n        and coalesce(x.cutting_group_id,xqi.cutting_group_id)=t.group_id\n        and (x.produced_at,x.id)<(t.produced_at,t.id)),0) group_start,\n    coalesce((select sum(x.initial_qty_pcs)::numeric from erp.fg_lots x\n      where x.po_id=t.po_id and x.lot_origin='PRODUCTION'\n        and (x.produced_at,x.id)<(t.produced_at,t.id)),0) po_start\n  from target t\n), terminal as(\n  select e.id,e.po_id,e.cutting_group_id,e.qty_signed::numeric event_qty,\n    coalesce(sum(e.qty_signed) over(\n      partition by e.po_id,e.cutting_group_id\n      order by e.physical_at,e.id rows between unbounded preceding and 1 preceding\n    ),0)::numeric group_start,\n    coalesce(sum(e.qty_signed) over(\n      partition by e.po_id\n      order by e.physical_at,e.id rows between unbounded preceding and 1 preceding\n    ),0)::numeric po_start\n  from erp.sewing_terminal_events e join position p on p.po_id=e.po_id\n  where e.event_kind='SELESAI_DIJAHIT' and e.qty_signed>0\n    and not exists(select 1 from erp.sewing_terminal_events rv where rv.reversal_of_id=e.id)\n), alloc as(\n  select a.cutting_group_id,a.sewing_qty::numeric source_qty,erp.pocket_period_amount_v1(a.pool_id,a.preceding_qty,a.sewing_qty)::numeric source_cost,\n    case when a.cutting_group_id is null then t.po_start else t.group_start end source_start\n  from position p\n  join erp.pocket_period_destinations a on a.po_id=p.po_id\n    and (a.cutting_group_id=p.group_id or a.cutting_group_id is null)\n  join erp.pocket_periods hp on hp.id=a.pool_id and erp.pocket_period_active_v1(hp.id)\n  join terminal t on t.id=a.event_id\n)\nselect coalesce(sum(\n  greatest(least(\n    case when a.cutting_group_id is null then p.po_start+p.lot_qty else p.group_start+p.lot_qty end,\n    a.source_start+a.source_qty\n  )-greatest(\n    case when a.cutting_group_id is null then p.po_start else p.group_start end,\n    a.source_start\n  ),0)*a.source_cost/nullif(a.source_qty,0)\n),0)::numeric\nfrom position p left join alloc a on true\n$function$\n"
