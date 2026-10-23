-- OW-08b (D17-13 2.20, owner LAU-DEC04): a failed wash ("cuci gagal") whose laundry vendor price is not known yet.
--
-- Owner LAU-DEC04 (docs/cp6-d11-kebijakan-dan-gbd03.md §4 no. 11): "Harga yang belum diketahui tidak boleh dianggap nol atau
-- membuat HPP terlihat final. Status belum final harus jelas, dan tutup buku yang terdampak tetap tertahan sampai harga serta
-- perhitungan biayanya selesai."
--
-- erp.save_laundry_qc_action_v1 POST_FAILED_WASH accepts price_status 'UNKNOWN' when no vendor/process rate is effective (more
-- than one stays refused). The attempt is stored with no rate, no cost and cost status PENDING (never zero) and registered in
-- prices_v1 with who, when and why. Owner/admin later sets the price once (KNOWN > 0, or FREE/WAIVED = 0 with a reason) through
-- the BD facade action SET_FAILED_WASH_PRICE (set_price_v1): the receipt line takes the rate, cost = attempts x rate, and the
-- accrual, HPP and GL resync at the attempt's own date exactly as a known-price POST_FAILED_WASH does. While the price is
-- unknown: close through a date on or after the attempt is blocked (LAUNDRY_FAILED_WASH_PRICE_UNKNOWN), the PO's HPP is not
-- final (rebuild_po_hpp and bd_lot_laundry_unknown_v1), selling its goods follows LAU-DEC04 (bd_assert_sale_laundry_known_v1,
-- unchanged) and the attempt cannot be billed. LAUNDRY_FAILED_WASH_PRICE_STATE_MISMATCH (CRITICAL) is the read-only detector.
-- Only postgres uses this schema (the patched Native functions are SECURITY DEFINER owned by postgres); no browser role does.
-- Every reference value of a close row is text, a date, a boolean or null (the client reads numbers only as strings).
create schema cp7_laundry_unknown_wash authorization postgres;
revoke all on schema cp7_laundry_unknown_wash from public;

-- One row per attempt recorded with an unknown price; the price is set once and the row is never deleted (history).
create table cp7_laundry_unknown_wash.prices_v1(
 attempt_id uuid primary key,
 receipt_line_id uuid not null unique,
 po_id uuid not null,
 recorded_by uuid not null,
 recorded_reason text not null check(length(btrim(recorded_reason))>=4),
 recorded_at timestamptz not null default statement_timestamp(),
 price_status text not null default 'UNKNOWN' check(price_status in('UNKNOWN','KNOWN','FREE','WAIVED')),
 rate_per_pcs numeric(18,2),
 price_reason text,
 priced_by uuid,
 priced_at timestamptz,
 price_request_id uuid unique,
 constraint prices_v1_state check(
  (price_status='UNKNOWN' and rate_per_pcs is null and price_reason is null and priced_by is null and priced_at is null and price_request_id is null)
  or(price_status='KNOWN' and rate_per_pcs>0 and length(btrim(price_reason))>=4 and priced_by is not null and priced_at is not null and price_request_id is not null)
  or(price_status in('FREE','WAIVED') and rate_per_pcs=0 and length(btrim(price_reason))>=4 and priced_by is not null and priced_at is not null
     and price_request_id is not null))
);
create index prices_v1_unknown_po on cp7_laundry_unknown_wash.prices_v1(po_id) where price_status='UNKNOWN';
alter table cp7_laundry_unknown_wash.prices_v1 owner to postgres;
alter table cp7_laundry_unknown_wash.prices_v1 enable row level security;
-- Default denial as an explicit policy (no API role has a grant either); the stage's own definer functions own the table.
create policy deny_prices on cp7_laundry_unknown_wash.prices_v1 for all using(false)with check(false);
revoke all on table cp7_laundry_unknown_wash.prices_v1 from public,anon,authenticated,service_role;

-- History is immutable: the only change is UNKNOWN -> priced, once; no delete.
create function cp7_laundry_unknown_wash.guard_v1()
returns trigger language plpgsql set search_path='' as $$
begin
 if tg_op='DELETE' then
  raise exception 'CP7_FAILED_WASH_PRICE_HISTORY_IMMUTABLE: catatan harga cuci gagal tidak dihapus';
 end if;
 if old.price_status<>'UNKNOWN' or new.price_status='UNKNOWN' or new.attempt_id is distinct from old.attempt_id
    or new.receipt_line_id is distinct from old.receipt_line_id or new.po_id is distinct from old.po_id
    or new.recorded_by is distinct from old.recorded_by or new.recorded_reason is distinct from old.recorded_reason
    or new.recorded_at is distinct from old.recorded_at then
  raise exception 'CP7_FAILED_WASH_PRICE_HISTORY_IMMUTABLE: harga cuci gagal hanya diisi sekali dan tidak diubah';
 end if;
 return new;
end $$;
create trigger prices_v1_guard before update or delete on cp7_laundry_unknown_wash.prices_v1
 for each row execute function cp7_laundry_unknown_wash.guard_v1();

-- The attempts whose price is still unknown: registered UNKNOWN and the attempt (its receipt) still POSTED.
create function cp7_laundry_unknown_wash.unknown_v1()
returns table(attempt_id uuid,receipt_id uuid,receipt_line_id uuid,receipt_number text,delivery_id uuid,delivery_number text,
 po_id uuid,po_number text,vendor_id uuid,custody_outcome text,qty integer,physical_at timestamptz,impact_date date)
language sql stable security definer set search_path='' as $$
 select a.id,a.receipt_id,a.receipt_line_id,r.receipt_number::text,d.id,d.delivery_number::text,d.po_id,po.po_number::text,d.vendor_id,
  a.custody_outcome::text,a.qty_attempted_pcs,r.physical_at,erp._cp3_business_date(r.physical_at)
 from cp7_laundry_unknown_wash.prices_v1 p
 join erp.laundry_failed_wash_attempts a on a.id=p.attempt_id
 join erp.laundry_receipts r on r.id=a.receipt_id and r.status='POSTED'
 join erp.laundry_deliveries d on d.id=a.delivery_id
 join erp.production_orders po on po.id=d.po_id
 where p.price_status='UNKNOWN'
$$;

-- One predicate for HPP (rebuild_po_hpp), goods (bd_lot_laundry_unknown_v1) and the sale guard that reads it.
create function cp7_laundry_unknown_wash.po_pending_v1(p_po uuid)
returns boolean language sql stable security definer set search_path='' as $$
 select exists(select 1 from cp7_laundry_unknown_wash.prices_v1 p
  join erp.laundry_failed_wash_attempts a on a.id=p.attempt_id
  join erp.laundry_receipts r on r.id=a.receipt_id and r.status='POSTED'
  where p.po_id=p_po and p.price_status='UNKNOWN')
$$;

-- Close rows (erp.period_blockers_v1): one POLICY row per unknown attempt dated on or before the date, and the CRITICAL
-- detector (every date) when the price record and the attempt's cost line disagree.
create function cp7_laundry_unknown_wash.blockers_v1(p_through date)
returns table(family text,code text,severity text,scope text,impact_date date,reference jsonb,reason text)
language sql stable security definer set search_path='' as $$
 select 'LAUNDRY'::text,'LAUNDRY_FAILED_WASH_PRICE_UNKNOWN'::text,'POLICY'::text,'AS_OF'::text,u.impact_date,
  jsonb_build_object('failed_wash_attempt_id',u.attempt_id,'receipt_id',u.receipt_id,'receipt_number',u.receipt_number,
   'delivery_id',u.delivery_id,'delivery_number',u.delivery_number,'po_id',u.po_id,'po_number',u.po_number,
   'qty_attempted_pcs',u.qty::text,'custody_outcome',u.custody_outcome),
  format('Harga cuci gagal %s (kiriman %s, PO %s, %s pcs, tanggal %s) belum diketahui: biayanya belum dihitung dan HPP PO itu belum final. Isi harganya di Produksi › Laundry › Harga & tagihan › Harga belum diketahui.',
   u.receipt_number,u.delivery_number,u.po_number,u.qty,u.impact_date)
 from cp7_laundry_unknown_wash.unknown_v1() u
 where u.impact_date<=p_through
 union all
 select 'INTEGRITY'::text,'LAUNDRY_FAILED_WASH_PRICE_STATE_MISMATCH'::text,'CRITICAL'::text,'CURRENT_STATE'::text,null::date,
  jsonb_build_object('attempt_count',count(*)::text,
   'attempt_ids',coalesce(jsonb_agg(m.attempt_id order by m.attempt_id) filter(where m.n<=50),'[]'::jsonb)),
  format('%s cuci gagal punya status harga yang tidak cocok antara catatan harga dan baris biayanya; periksa di Produksi › Laundry › Harga & tagihan sebelum tutup buku.',count(*))
 from(
  select a.id attempt_id,row_number()over(order by a.id) n
  from erp.laundry_failed_wash_attempts a
  join erp.laundry_receipts r on r.id=a.receipt_id and r.status='POSTED'
  join erp.laundry_receipt_lines rl on rl.id=a.receipt_line_id
  left join cp7_laundry_unknown_wash.prices_v1 p on p.attempt_id=a.id
  where(p.attempt_id is null and(rl.actual_rate_snapshot is null or rl.actual_cost_status='PENDING'))
   or(p.attempt_id is not null and p.receipt_line_id is distinct from a.receipt_line_id)
   or(p.price_status='UNKNOWN' and(rl.actual_rate_snapshot is not null or rl.actual_cost is not null or rl.actual_cost_status<>'PENDING'))
   or(p.price_status<>'UNKNOWN' and rl.actual_cost_status='PENDING')
   or(p.price_status<>'UNKNOWN' and rl.actual_cost_status='ESTIMATED'
    and(rl.actual_rate_snapshot is distinct from p.rate_per_pcs or rl.actual_cost is distinct from round(a.qty_attempted_pcs*p.rate_per_pcs,2)))
 ) m
 having count(*)>0
$$;

-- The Laundry > Harga & tagihan list (erp.get_laundry_bd_workspace_v1 'failed_wash_prices'): attempts still waiting for their
-- price first, then the latest priced or cancelled ones. Amounts only for money readers (null otherwise: hidden, never zero).
create function cp7_laundry_unknown_wash.workspace_v1(p_vendor uuid,p_money boolean)
returns jsonb language sql stable security definer set search_path='' as $$
 select coalesce(jsonb_agg(x.j order by x.n),'[]'::jsonb) from(
  select row_number()over(order by(r.status='POSTED' and p.price_status='UNKNOWN') desc,coalesce(p.priced_at,p.recorded_at) desc,p.attempt_id) n,
   jsonb_build_object('attempt_id',p.attempt_id,'receipt_id',r.id,'receipt_number',r.receipt_number,'attempt_status',r.status,
    'delivery_number',d.delivery_number,'po_number',po.po_number,'vendor_id',d.vendor_id,'vendor_code',v.vendor_code,
    'process_name',w.process_name,'custody_outcome',a.custody_outcome,'qty',a.qty_attempted_pcs,
    'physical_local',to_char(r.physical_at at time zone 'Asia/Jakarta','YYYY-MM-DD"T"HH24:MI:SS'),
    'recorded_reason',p.recorded_reason,'recorded_by',ru.full_name,
    'recorded_local',to_char(p.recorded_at at time zone 'Asia/Jakarta','YYYY-MM-DD"T"HH24:MI:SS'),
    'price_status',p.price_status,
    'rate',case when p_money then p.rate_per_pcs::numeric(18,2)::text end,
    'amount',case when p_money then round(a.qty_attempted_pcs*p.rate_per_pcs,2)::numeric(18,2)::text end,
    'price_reason',p.price_reason,'priced_by',pu.full_name,
    'priced_local',to_char(p.priced_at at time zone 'Asia/Jakarta','YYYY-MM-DD"T"HH24:MI:SS')) j
  from cp7_laundry_unknown_wash.prices_v1 p
  join erp.laundry_failed_wash_attempts a on a.id=p.attempt_id
  join erp.laundry_receipts r on r.id=a.receipt_id
  join erp.laundry_receipt_lines rl on rl.id=a.receipt_line_id
  join erp.laundry_deliveries d on d.id=a.delivery_id
  join erp.production_orders po on po.id=d.po_id
  join erp.laundry_vendors v on v.id=d.vendor_id
  left join erp.wash_processes w on w.id=rl.actual_wash_process_id
  left join erp.app_users ru on ru.id=p.recorded_by
  left join erp.app_users pu on pu.id=p.priced_by
  where p_vendor is null or d.vendor_id=p_vendor
  order by 1 limit 100) x
$$;

-- SET_FAILED_WASH_PRICE (erp.save_laundry_bd_action_v1, which keeps the request id and replays it): owner/admin with
-- finance.hpp.manage sets the price of one unknown attempt, once. The same flow lock as the laundry writers of its cutting
-- group, then the price record, then the attempt's receipt; the receipt line trigger computes cost = attempts x rate. The
-- accrual, HPP and GL resync at the attempt's own date, as erp.save_laundry_qc_action_v1 does for a known-price attempt.
create function cp7_laundry_unknown_wash.set_price_v1(p_payload jsonb,p_request uuid)
returns jsonb language plpgsql security definer set search_path='' as $$
declare
 v_attempt uuid;v_status text:=coalesce(p_payload->>'rate_status','KNOWN');v_rate numeric;
 v_reason text:=nullif(btrim(p_payload->>'reason'),'');v_date date;v_cost numeric;
 v_price cp7_laundry_unknown_wash.prices_v1%rowtype;v_row erp.laundry_failed_wash_attempts%rowtype;
 v_receipt erp.laundry_receipts%rowtype;v_delivery erp.laundry_deliveries%rowtype;
begin
 perform erp.require_owner_admin();perform erp.require_permission('finance.hpp.manage');
 perform erp._cp3_assert_closed_json_object(p_payload,array['failed_wash_attempt_id','rate_per_pcs','reason'],
  array['failed_wash_attempt_id','rate_status','rate_per_pcs','reason'],'harga cuci gagal');
 if v_reason is null or length(v_reason)<4 or length(v_reason)>1000 then
  raise exception 'BD_REASON_REQUIRED: alasan wajib diisi, 4 sampai 1000 karakter';end if;
 if v_status not in('KNOWN','FREE','WAIVED') then
  raise exception 'BD_RATE_STATUS: penyelesaian harga harus KNOWN, FREE atau WAIVED';end if;
 v_attempt:=erp.bd_uuid_v1(p_payload,'failed_wash_attempt_id',true);
 v_rate:=erp.bd_amount_v1(p_payload->'rate_per_pcs','rate_per_pcs',v_status='KNOWN');
 if v_status in('FREE','WAIVED') and v_rate<>0 then raise exception 'BD_FREE_REQUIRES_ZERO: FREE/WAIVED wajib nominal 0.00';end if;
 perform pg_advisory_xact_lock(hashtextextended('CP6FLOW:'||dl.cutting_group_id::text,0))
 from erp.laundry_failed_wash_attempts x join erp.laundry_delivery_lines dl on dl.delivery_id=x.delivery_id where x.id=v_attempt;
 select * into v_price from cp7_laundry_unknown_wash.prices_v1 where attempt_id=v_attempt for update;
 if v_price.attempt_id is null then
  raise exception 'CP7_FAILED_WASH_PRICE_NOT_PENDING: cuci gagal ini tidak dicatat dengan harga belum diketahui';end if;
 if v_price.price_status<>'UNKNOWN' then
  raise exception 'CP7_FAILED_WASH_PRICE_ALREADY_SET: harga cuci gagal ini sudah diisi (%); tidak ditimpa',v_price.price_status;end if;
 select * into v_row from erp.laundry_failed_wash_attempts where id=v_attempt;
 select * into v_receipt from erp.laundry_receipts where id=v_row.receipt_id for update;
 if v_receipt.status is distinct from 'POSTED' then
  raise exception 'CP7_FAILED_WASH_ATTEMPT_REVERSED: cuci gagal ini sudah dibatalkan; tidak ada harga yang diisi';end if;
 select * into v_delivery from erp.laundry_deliveries where id=v_row.delivery_id for update;
 perform set_config('app.change_reason',v_reason,true);
 update cp7_laundry_unknown_wash.prices_v1 set price_status=v_status,rate_per_pcs=v_rate,price_reason=v_reason,
  priced_by=erp.current_app_user_id(),priced_at=statement_timestamp(),price_request_id=p_request
 where attempt_id=v_attempt;
 update erp.laundry_receipt_lines set actual_rate_snapshot=v_rate,actual_cost_status='ESTIMATED' where id=v_row.receipt_line_id;
 select actual_cost into v_cost from erp.laundry_receipt_lines where id=v_row.receipt_line_id;
 if v_cost is distinct from round(v_row.qty_attempted_pcs*v_rate,2) then
  raise exception 'CP7_FAILED_WASH_PRICE_COST_MISMATCH: biaya cuci gagal tidak sama dengan jumlah attempt x harga';end if;
 v_date:=(v_receipt.physical_at at time zone 'Asia/Jakarta')::date;
 perform erp.sync_laundry_accrual(v_delivery.po_id,v_date);
 if exists(select 1 from erp.fg_lots f where f.po_id=v_delivery.po_id) then
  perform erp.rebuild_po_hpp(v_delivery.po_id,'Paid failed-wash service attempt '||v_row.id::text);
  perform erp.propagate_conversion_hpp_for_po(v_delivery.po_id);
  perform erp.sync_po_hpp_to_gl(v_delivery.po_id,v_date);
 end if;
 -- A FINISHED PO settles its residual WIP as the other late cost paths do (erp.set_laundry_rate_owner_estimate_v1).
 if (select po.status from erp.production_orders po where po.id=v_delivery.po_id)='FINISHED' then
  perform erp.sync_finished_po_wip_residual(v_delivery.po_id,v_date,'Failed-wash price set: '||v_reason);
 end if;
 insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)
 values('laundry_failed_wash_attempts',v_row.id,'SET_PRICE',jsonb_build_object('receipt_id',v_receipt.id,'rate_status',v_status,
  'rate_per_pcs',v_rate,'actual_cost',v_cost,'qty_attempted_pcs',v_row.qty_attempted_pcs,'economic_date',v_date,
  'history_deleted',false),erp.current_app_user_id(),v_reason);
 return jsonb_build_object('failed_wash_attempt_id',v_row.id,'receipt_id',v_receipt.id,'receipt_number',v_receipt.receipt_number,
  'delivery_id',v_delivery.id,'po_id',v_delivery.po_id,'rate_status',v_status,'rate_per_pcs',v_rate::numeric(18,2)::text,
  'actual_cost',v_cost::numeric(18,2)::text,'economic_date',v_date,'cost_status','ESTIMATED_UNBILLED');
end $$;

alter function cp7_laundry_unknown_wash.guard_v1() owner to postgres;
alter function cp7_laundry_unknown_wash.unknown_v1() owner to postgres;
alter function cp7_laundry_unknown_wash.po_pending_v1(uuid) owner to postgres;
alter function cp7_laundry_unknown_wash.blockers_v1(date) owner to postgres;
alter function cp7_laundry_unknown_wash.workspace_v1(uuid,boolean) owner to postgres;
alter function cp7_laundry_unknown_wash.set_price_v1(jsonb,uuid) owner to postgres;
revoke all on all functions in schema cp7_laundry_unknown_wash from public,anon,authenticated,service_role;
