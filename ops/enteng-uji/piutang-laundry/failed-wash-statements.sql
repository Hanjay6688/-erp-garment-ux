do $wash_pin$ begin if exists (select from (values ('erp.bd_lot_laundry_unknown_v1(uuid)','58e2d100f3392ced5efb2f9c99ffac9145dc22b8853394a2f202f43e15682d8a'),('erp.bd_pending_cost_json_v1(uuid,boolean)','f2f3ac90695933af35ec0457514ad051d7c8abd25cee2afe38e9b2f1da6d2257'),('erp.bd_save_invoice_draft_v1(jsonb,uuid)','ca7dfc9d1266e9d33023e408bff857760d21e006e02dac8b442d66f173e5af2b'),('erp.get_laundry_bd_workspace_v1(jsonb)','1014d385389bdc4104582dded00a2c8ebcc2cf923df48e367d2adf0b089adf59'),('erp.guard_cp6_laundry_receipt_lineage_on_post_v2620()','06efb9cab8a16f6dce00bbb931989ca246116fc6547e59afc026298afcffdefd'),('erp.period_blockers_v1(date,date)','ef32011630cea8b98954eeba03d38ade0b71fb4fed221909282493a05469878b'),('erp.rebuild_po_hpp(uuid,text)','4879a59677caead622302499957c39a80651d153f55ba0c609c58817d2acee64'),('erp.save_laundry_bd_action_v1(text,jsonb,uuid)','b39f17ad726e2059cbebfd9ed321a6840bf39dc9821aa83df852acdb4469bdd6'),('erp.save_laundry_qc_action_v1(text,jsonb,uuid,bigint)','f3aa593a01e62a5ffeea518305f23622ae5ae12ddc8d12c59414581ce0f28056'),('erp.validate_laundry_receipt_line()','0b72c14b4513ef577f8b044e5feb8829cfe341da10d5fa321221b18cc76cd30d')) wanted(sig,sha) left join pg_proc p
         on p.oid=to_regprocedure(sig) where p.oid is null or p.proowner<>'postgres'::regrole or encode(sha256(convert_to(pg_get_functiondef(p.oid),'UTF8')),'hex')<>wanted.sha)
         then raise exception 'Deferred wash financial routine differs from its qualified source';end if;end $wash_pin$;
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
 -- erp.audit_logs admits only its fixed actions (audit_logs_action_check): an UPDATE of the attempt's cost, named in the data.
 insert into erp.audit_logs(entity_type,entity_id,action,old_data,new_data,changed_by,change_reason)
 values('laundry_failed_wash_attempts',v_row.id,'UPDATE',jsonb_build_object('rate_status','UNKNOWN','rate_per_pcs',null,'actual_cost',null,
  'actual_cost_status','PENDING'),jsonb_build_object('operation','SET_FAILED_WASH_PRICE','receipt_id',v_receipt.id,'rate_status',v_status,
  'rate_per_pcs',v_rate,'actual_cost',v_cost,'actual_cost_status','ESTIMATED','qty_attempted_pcs',v_row.qty_attempted_pcs,'economic_date',v_date,
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

CREATE OR REPLACE FUNCTION erp.save_laundry_qc_action_v1(p_action text, p_payload jsonb, p_client_request_id uuid, p_expected_version bigint DEFAULT NULL::bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare
  v_action text:=upper(nullif(btrim(p_action),''));
  v_reason text:=nullif(btrim(p_payload->>'reason'),'');
  v_custody_outcome text:=upper(nullif(btrim(p_payload->>'custody_outcome'),''));
  v_hash text;
  v_cached jsonb;
  v_response jsonb;
  v_actor uuid:=erp.current_app_user_id();
  v_physical_raw text:=nullif(btrim(p_payload->>'physical_at'),'');
  v_physical_at timestamptz;
  v_batch_id uuid:=nullif(p_payload->>'distribution_batch_id','')::uuid;
  v_group_id uuid:=nullif(p_payload->>'cutting_group_id','')::uuid;
  v_delivery_id uuid:=nullif(p_payload->>'delivery_id','')::uuid;
  v_receipt_id uuid;
  v_failed_wash_attempt_id uuid;
  v_return_wip_event_id uuid;
  v_qc_id uuid:=nullif(p_payload->>'qc_inspection_id','')::uuid;
  v_vendor_id uuid:=nullif(p_payload->>'vendor_id','')::uuid;
  v_process_id uuid:=nullif(p_payload->>'wash_process_id','')::uuid;
  v_location_id uuid:=nullif(p_payload->>'destination_location_id','')::uuid;
  v_target_color text:=nullif(btrim(p_payload->>'target_dyeing_color'),'');
  v_lines jsonb:=p_payload->'lines';
  v_line jsonb;
  v_rate numeric(18,2);
  v_rate_count integer;
  v_deferred_delivery boolean;
  v_group_count integer;
  v_total bigint;
  v_good bigint;
  v_bs bigint;
  v_available bigint;
  v_available_at_physical_time bigint;
  v_ready_after_qc bigint;
  v_delivery_line_id uuid;
  v_receipt_line_id uuid;
  v_number text;
  v_nested jsonb;
  v_group erp.cutting_groups%rowtype;
  v_po erp.production_orders%rowtype;
  v_delivery erp.laundry_deliveries%rowtype;
  v_receipt erp.laundry_receipts%rowtype;
  v_qc erp.qc_inspections%rowtype;
begin
  if p_client_request_id is null then raise exception 'client_request_id UUID is required'; end if;
  if v_actor is null then raise exception 'Active ERP app user is required'; end if;
  if v_action not in(
    'POST_DELIVERY','POST_RECEIPT','POST_FAILED_WASH','REVERSE_DELIVERY',
    'REVERSE_RECEIPT','POST_FINAL_SKU','REVERSE_FINAL_SKU'
  ) then raise exception 'Unsupported CP6 Laundry/QC action %',coalesce(v_action,'NULL'); end if;

  -- Physical time is operator intent. Validate it before the generic closed-payload
  -- gate so missing, timezone-less, and calendar-invalid values all fail with one
  -- actionable domain message instead of a helper or native cast error.
  if v_action in('POST_DELIVERY','POST_RECEIPT','POST_FAILED_WASH','POST_FINAL_SKU') then
    if jsonb_typeof(p_payload->'physical_at') is distinct from 'string'
       or v_physical_raw is null
       or v_physical_raw !~ '^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}(:\d{2})?)$' then
      raise exception 'An explicit timezone-qualified physical_at is required; server time is never a transactional default';
    end if;
    begin
      v_physical_at:=v_physical_raw::timestamptz;
    exception
      when data_exception then
        raise exception 'An explicit timezone-qualified physical_at is required; server time is never a transactional default';
    end;
  end if;

  -- Do not let JSON coercion reinterpret a physical count or silently ignore
  -- a misspelled field.  Every connected writer uses one closed, canonical
  -- payload shape before idempotency or business mutation begins.
  if v_action='POST_DELIVERY' then
    perform erp._cp3_assert_closed_json_object(
      p_payload,
      array['distribution_batch_id','vendor_id','physical_at','reason','lines'],
      array['distribution_batch_id','vendor_id','wash_process_id','target_dyeing_color',
        'colour_process','sku_reference_id','dyeing_type_id','physical_at','reason','notes','lines'],
      'CP6 POST_DELIVERY payload'
    );
    if jsonb_typeof(p_payload->'distribution_batch_id')<>'string'
       or jsonb_typeof(p_payload->'vendor_id')<>'string'
       or (p_payload ? 'wash_process_id' and jsonb_typeof(p_payload->'wash_process_id') not in('string','null'))
       or (p_payload ? 'target_dyeing_color' and jsonb_typeof(p_payload->'target_dyeing_color') not in('string','null'))
       or (p_payload ? 'colour_process' and jsonb_typeof(p_payload->'colour_process') not in('string','null'))
       or (p_payload ? 'sku_reference_id' and jsonb_typeof(p_payload->'sku_reference_id') not in('string','null'))
       or (p_payload ? 'dyeing_type_id' and jsonb_typeof(p_payload->'dyeing_type_id') not in('string','null'))
       or jsonb_typeof(p_payload->'physical_at')<>'string'
       or jsonb_typeof(p_payload->'reason')<>'string'
       or jsonb_typeof(p_payload->'lines')<>'array'
       or(p_payload ? 'notes' and jsonb_typeof(p_payload->'notes') not in('string','null')) then
      raise exception 'CP6 POST_DELIVERY payload has invalid field types';
    end if;
    for v_line in select value from jsonb_array_elements(v_lines) loop
      perform erp._cp3_assert_closed_json_object(
        v_line,array['size_id','qty_sent_pcs'],array['size_id','qty_sent_pcs'],
        'CP6 POST_DELIVERY line'
      );
      if jsonb_typeof(v_line->'size_id')<>'string'
         or jsonb_typeof(v_line->'qty_sent_pcs')<>'number'
         or(v_line->>'qty_sent_pcs')!~'^(0|[1-9][0-9]*)$' then
        raise exception 'CP6 POST_DELIVERY line has invalid field types';
      end if;
    end loop;
  elsif v_action='POST_RECEIPT' then
    perform erp._cp3_assert_closed_json_object(
      p_payload,array['delivery_id','physical_at','reason','lines'],
      array['delivery_id','wash_process_id','physical_at','reason','lines'],
      'CP6 POST_RECEIPT payload'
    );
    if jsonb_typeof(p_payload->'delivery_id')<>'string'
       or (p_payload ? 'wash_process_id' and jsonb_typeof(p_payload->'wash_process_id') not in('string','null'))
       or jsonb_typeof(p_payload->'physical_at')<>'string'
       or jsonb_typeof(p_payload->'reason')<>'string'
       or jsonb_typeof(p_payload->'lines')<>'array' then
      raise exception 'CP6 POST_RECEIPT payload has invalid field types';
    end if;
    for v_line in select value from jsonb_array_elements(v_lines) loop
      perform erp._cp3_assert_closed_json_object(
        v_line,
        array['delivery_batch_size_line_id','qty_good_received','qty_bs_laundry'],
        array['delivery_batch_size_line_id','qty_good_received','qty_bs_laundry','bs_product_id'],
        'CP6 POST_RECEIPT line'
      );
      if not(v_line ? 'bs_product_id')
         or jsonb_typeof(v_line->'delivery_batch_size_line_id')<>'string'
         or jsonb_typeof(v_line->'qty_good_received')<>'number'
         or(v_line->>'qty_good_received')!~'^(0|[1-9][0-9]*)$'
         or jsonb_typeof(v_line->'qty_bs_laundry')<>'number'
         or(v_line->>'qty_bs_laundry')!~'^(0|[1-9][0-9]*)$'
         or jsonb_typeof(v_line->'bs_product_id') not in('string','null') then
        raise exception 'CP6 POST_RECEIPT line has invalid field types';
      end if;
    end loop;
  elsif v_action='POST_FAILED_WASH' then
    perform erp._cp3_assert_closed_json_object(
      p_payload,
      array['delivery_id','wash_process_id','custody_outcome','physical_at','reason','lines'],
      array['delivery_id','wash_process_id','custody_outcome','physical_at','reason','lines','price_status'],
      'CP6 POST_FAILED_WASH payload'
    );
    if jsonb_typeof(p_payload->'delivery_id')<>'string'
       or jsonb_typeof(p_payload->'wash_process_id')<>'string'
       or jsonb_typeof(p_payload->'custody_outcome')<>'string'
       or v_custody_outcome not in('RETRY_AT_VENDOR','RETURN_UNPROCESSED')
       or jsonb_typeof(p_payload->'physical_at')<>'string'
       or jsonb_typeof(p_payload->'reason')<>'string'
       or jsonb_typeof(p_payload->'lines')<>'array' then
      raise exception 'CP6 POST_FAILED_WASH payload has invalid field types';
    end if;
    -- OW-08b (LAU-DEC04): optional price_status; its only value says the vendor rate is not known yet.
    if p_payload ? 'price_status' and(jsonb_typeof(p_payload->'price_status') is distinct from 'string'
       or p_payload->>'price_status'<>'UNKNOWN') then
      raise exception 'CP7_FAILED_WASH_PRICE_STATUS: price_status hanya boleh UNKNOWN (tarif vendor belum diketahui)';
    end if;
    for v_line in select value from jsonb_array_elements(v_lines) loop
      perform erp._cp3_assert_closed_json_object(
        v_line,array['delivery_batch_size_line_id','qty_attempted_pcs'],
        array['delivery_batch_size_line_id','qty_attempted_pcs'],
        'CP6 POST_FAILED_WASH line'
      );
      if jsonb_typeof(v_line->'delivery_batch_size_line_id')<>'string'
         or jsonb_typeof(v_line->'qty_attempted_pcs')<>'number'
         or(v_line->>'qty_attempted_pcs')!~'^[1-9][0-9]*$' then
        raise exception 'CP6 POST_FAILED_WASH line has invalid field types';
      end if;
    end loop;
  elsif v_action='POST_FINAL_SKU' then
    perform erp._cp3_assert_closed_json_object(
      p_payload,
      array['cutting_group_id','destination_location_id','physical_at','reason',
        'good_qty_pcs','completion_mode','lines'],
      array['cutting_group_id','destination_location_id','physical_at','reason',
        'good_qty_pcs','completion_mode','lines'],
      'CP6 POST_FINAL_SKU payload'
    );
    if jsonb_typeof(p_payload->'cutting_group_id')<>'string'
       or jsonb_typeof(p_payload->'destination_location_id')<>'string'
       or jsonb_typeof(p_payload->'physical_at')<>'string'
       or jsonb_typeof(p_payload->'reason')<>'string'
       or jsonb_typeof(p_payload->'good_qty_pcs')<>'number'
       or(p_payload->>'good_qty_pcs')!~'^(0|[1-9][0-9]*)$'
       or jsonb_typeof(p_payload->'completion_mode')<>'string'
       or(p_payload->>'completion_mode') not in('ALL_READY','PARTIAL_SELECTION')
       or jsonb_typeof(p_payload->'lines')<>'array' then
      raise exception 'CP6 POST_FINAL_SKU payload has invalid field types';
    end if;
    for v_line in select value from jsonb_array_elements(v_lines) loop
      perform erp._cp3_assert_closed_json_object(
        v_line,
        array['final_product_id','qty_good_pcs','qty_bs_pcs',
          'source_laundry_receipt_line_id','source_laundry_receipt_batch_size_line_id'],
        array['final_product_id','qty_good_pcs','qty_bs_pcs',
          'source_laundry_receipt_line_id','source_laundry_receipt_batch_size_line_id','notes'],
        'CP6 POST_FINAL_SKU line'
      );
      if jsonb_typeof(v_line->'final_product_id')<>'string'
         or jsonb_typeof(v_line->'qty_good_pcs')<>'number'
         or(v_line->>'qty_good_pcs')!~'^(0|[1-9][0-9]*)$'
         or jsonb_typeof(v_line->'qty_bs_pcs')<>'number'
         or(v_line->>'qty_bs_pcs')!~'^(0|[1-9][0-9]*)$'
         or jsonb_typeof(v_line->'source_laundry_receipt_line_id')<>'string'
         or jsonb_typeof(v_line->'source_laundry_receipt_batch_size_line_id')<>'string'
         or(v_line ? 'notes' and jsonb_typeof(v_line->'notes') not in('string','null')) then
        raise exception 'CP6 POST_FINAL_SKU line has invalid field types';
      end if;
    end loop;
  elsif v_action='REVERSE_DELIVERY' then
    perform erp._cp3_assert_closed_json_object(
      p_payload,array['delivery_id','reason'],array['delivery_id','reason'],
      'CP6 REVERSE_DELIVERY payload'
    );
    if jsonb_typeof(p_payload->'delivery_id')<>'string'
       or jsonb_typeof(p_payload->'reason')<>'string' then
      raise exception 'CP6 REVERSE_DELIVERY payload has invalid field types';
    end if;
  elsif v_action='REVERSE_RECEIPT' then
    perform erp._cp3_assert_closed_json_object(
      p_payload,array['receipt_id','reason'],array['receipt_id','reason'],
      'CP6 REVERSE_RECEIPT payload'
    );
    if jsonb_typeof(p_payload->'receipt_id')<>'string'
       or jsonb_typeof(p_payload->'reason')<>'string' then
      raise exception 'CP6 REVERSE_RECEIPT payload has invalid field types';
    end if;
  else
    perform erp._cp3_assert_closed_json_object(
      p_payload,array['qc_inspection_id','reason'],array['qc_inspection_id','reason'],
      'CP6 REVERSE_FINAL_SKU payload'
    );
    if jsonb_typeof(p_payload->'qc_inspection_id')<>'string'
       or jsonb_typeof(p_payload->'reason')<>'string' then
      raise exception 'CP6 REVERSE_FINAL_SKU payload has invalid field types';
    end if;
  end if;
  if v_reason is null or length(v_reason)<4 then raise exception 'A clear reason of at least 4 characters is required'; end if;
  if v_physical_at>clock_timestamp()+interval '5 minutes' then
    raise exception 'Physical time cannot be more than five minutes in the future';
  end if;

  if v_action in('POST_DELIVERY','POST_RECEIPT','POST_FAILED_WASH') then
    perform erp.require_permission('production.laundry.post');
    if v_action='POST_DELIVERY' then perform erp.require_permission('production.laundry.create'); end if;
  elsif v_action in('REVERSE_DELIVERY','REVERSE_RECEIPT') then
    perform erp.require_permission('production.laundry.reverse');
  elsif v_action='POST_FINAL_SKU' then
    perform erp.require_permission('production.final_sku.post');
  else
    perform erp.require_permission('production.final_sku.reverse');
  end if;

  v_hash:=erp._request_hash(jsonb_build_object(
    'action',v_action,'payload',p_payload,'expected_version',p_expected_version
  ));
  v_cached:=erp._idempotency_begin(
    'cp6_laundry_qc_action_v1:'||lower(v_action),p_client_request_id,v_hash
  );
  if v_cached is not null then return v_cached; end if;
  perform set_config('app.change_reason',v_reason,true);

  if v_action in('REVERSE_DELIVERY','REVERSE_RECEIPT','REVERSE_FINAL_SKU') then
    insert into erp.cp6_laundry_qc_execution_context(
      backend_pid,transaction_id,actor_key,action,permission_key,client_request_id,payload
    ) values(
      pg_backend_pid(),txid_current(),erp._idempotency_actor_key(),v_action,
      case when v_action in('REVERSE_DELIVERY','REVERSE_RECEIPT')
        then 'production.laundry.reverse' else 'production.final_sku.reverse' end,
      p_client_request_id,p_payload
    );
  end if;

  if v_action='POST_DELIVERY' then
    if p_expected_version is null then raise exception 'Potongan expected_version is required'; end if;
    if v_batch_id is null or v_vendor_id is null then
      raise exception 'Distribution batch and vendor are required';
    end if;
    if jsonb_typeof(v_lines)<>'array' or jsonb_array_length(v_lines)=0 then
      raise exception 'Laundry delivery requires positive size lines';
    end if;
    if exists(
      select 1 from jsonb_to_recordset(v_lines) x(size_id uuid,qty_sent_pcs integer)
      where x.size_id is null or coalesce(x.qty_sent_pcs,0)<=0
    ) or exists(
      select 1 from jsonb_to_recordset(v_lines) x(size_id uuid,qty_sent_pcs integer)
      group by x.size_id having count(*)>1
    ) then raise exception 'Laundry delivery size lines must be unique and positive'; end if;

    -- Resolve the immutable Potongan key without retaining a row lock, then
    -- take the shared CP6 fence before every business row.  The locked re-read
    -- below rejects a source that changed while this transaction waited; it
    -- must never continue under a fence for the wrong Potongan.
    select p.cutting_group_id into v_group_id
    from erp.cutting_distribution_batches b
    join erp.cutting_pickups p on p.id=b.pickup_id and p.status='POSTED'
    where b.id=v_batch_id;
    if v_group_id is null then raise exception 'Authoritative POSTED distribution batch was not found'; end if;
    -- Every CP6 mutation that can change Laundry/QC progress shares this
    -- transaction fence.  Cross-document actions on one Potongan therefore
    -- have one serial order even when their individual row locks do not meet.
    perform pg_advisory_xact_lock(hashtextextended('CP6FLOW:'||v_group_id::text,0));
    perform 1
    from erp.cutting_distribution_batches b
    join erp.cutting_pickups p on p.id=b.pickup_id
    where b.id=v_batch_id and p.status='POSTED'
      and p.cutting_group_id=v_group_id
    for update of b,p;
    if not found then
      raise exception 'Authoritative POSTED distribution batch changed while waiting for the Potongan fence; refetch before retrying';
    end if;
    if not erp.cp8_wip_batch_active_v1(v_batch_id,clock_timestamp())
       or not erp.cp8_wip_batch_active_v1(v_batch_id,v_physical_at) then
      raise exception 'WIP_BATCH_NOT_AVAILABLE_FOR_LAUNDRY';
    end if;
    select * into v_group from erp.cutting_groups where id=v_group_id for update;
    if v_group.row_version<>p_expected_version then
      raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_group.row_version;
    end if;
    select * into v_po from erp.production_orders where id=v_group.po_id for update;
    if v_po.status in('FINISHED','CANCELLED') then
      raise exception 'PO status % cannot receive a new Laundry delivery',v_po.status;
    end if;
    if v_physical_at<v_group.picked_up_at then
      raise exception 'Laundry send time cannot be earlier than the physical contractor pickup';
    end if;
    perform 1 from erp.laundry_vendors v
    where v.id=v_vendor_id and v.is_active for share;
    if not found then
      raise exception 'An active authoritative Laundry vendor is required';
    end if;
    if v_process_id is not null then
      perform 1 from erp.wash_processes w where w.id=v_process_id and w.is_active for share;
      if not found then raise exception 'An active authoritative wash process is required'; end if;
      perform pg_advisory_xact_lock(hashtextextended('LRATE:'||v_vendor_id::text||':'||v_process_id::text,0));
    end if;
    if coalesce((erp.bd_context_v1()).action,'')='POST_PRICED_DELIVERY' then
      -- BD (LAU-05b): the BD facade priced this delivery; the line keeps the exact average rate when every price is known and
      -- NULL while a component price is unknown (the charge lines are attached below).
      v_rate:=((erp.bd_context_v1()).pricing->>'avg_rate')::numeric;v_rate_count:=1;
    elsif v_process_id is null then
      v_rate:=null;
    elsif erp.bd_vendor_needs_pricing_v1(v_vendor_id,v_process_id) then
      raise exception 'BD_PRICING_REQUIRED: vendor ini memakai harga paket/komponen/borongan/minimum/tarif khusus; kirim lewat tab Harga & tagihan di halaman Laundry (Kirim dengan harga)';
    else
      select count(*)::integer,min(r.rate_per_pcs) into v_rate_count,v_rate
      from erp.laundry_vendor_rate_versions r
      where r.vendor_id=v_vendor_id and r.wash_process_id=v_process_id
        and r.effective_from<=v_physical_at
        and(r.effective_to is null or r.effective_to>v_physical_at);
      if v_rate_count>1 then
        raise exception 'Exactly one authoritative Laundry rate must be effective for this vendor/process/time; found %',v_rate_count;
      end if;
    end if;
    perform 1 from erp.laundry_vendor_rate_versions r
    where r.vendor_id=v_vendor_id and r.wash_process_id=v_process_id
      and r.effective_from<=v_physical_at
      and(r.effective_to is null or r.effective_to>v_physical_at)
    order by r.id for share;

    if exists(
      select 1
      from jsonb_to_recordset(v_lines) x(size_id uuid,qty_sent_pcs integer)
      left join lateral(
        select coalesce(sum(a.qty_pcs),0)::bigint qty
        from erp.cutting_distribution_allocations a
        join erp.cutting_roll_yields y on y.id=a.cutting_roll_yield_id
        join erp.cutting_group_size_slots s on s.id=y.size_slot_id
        where a.batch_id=v_batch_id and s.size_id=x.size_id
      ) cap on true
      left join lateral(
        select coalesce(sum(sx.qty_sent_pcs),0)::bigint qty
        from erp.laundry_delivery_batch_size_lines sx
        join erp.laundry_delivery_lines dl on dl.id=sx.delivery_line_id
        join erp.laundry_deliveries d on d.id=dl.delivery_id
        where sx.distribution_batch_id=v_batch_id and sx.size_id=x.size_id
          and d.status not in('DRAFT','REVERSED')
      ) used on true
      where x.qty_sent_pcs>cap.qty-used.qty
    ) then raise exception 'Requested Laundry size quantity exceeds its remaining distribution-batch capacity'; end if;

    if exists(
      select 1
      from jsonb_to_recordset(v_lines) x(size_id uuid,qty_sent_pcs integer)
      left join lateral(
        select coalesce(sum(a.qty_pcs),0)::bigint qty
        from erp.cutting_distribution_allocations a
        join erp.cutting_roll_yields y on y.id=a.cutting_roll_yield_id
        join erp.cutting_group_size_slots s on s.id=y.size_slot_id
        where a.batch_id=v_batch_id and s.size_id=x.size_id
      ) cap on true
      left join lateral(
        select coalesce(sum(sx.qty_sent_pcs),0)::bigint qty
        from erp.laundry_delivery_batch_size_lines sx
        join erp.laundry_delivery_lines dl on dl.id=sx.delivery_line_id
        join erp.laundry_deliveries d on d.id=dl.delivery_id
        where sx.distribution_batch_id=v_batch_id and sx.size_id=x.size_id
          and d.status<>'DRAFT' and d.physical_at<=v_physical_at
      ) dispatched_at_prefix on true
      left join lateral(
        select coalesce(sum(sx.qty_sent_pcs),0)::bigint qty
        from erp.laundry_delivery_batch_size_lines sx
        join erp.laundry_delivery_lines dl on dl.id=sx.delivery_line_id
        join erp.wip_stage_events src
          on src.source_type='LAUNDRY_DELIVERY_LINE' and src.source_id=dl.id
        join erp.wip_stage_events rv
          on rv.source_type='CP6_LAUNDRY_DELIVERY_WIP_REVERSAL'
         and rv.source_id=src.id and rv.physical_at<=v_physical_at
        where sx.distribution_batch_id=v_batch_id and sx.size_id=x.size_id
      ) returned_at_prefix on true
      where x.qty_sent_pcs>cap.qty-dispatched_at_prefix.qty+returned_at_prefix.qty
    ) then
      raise exception 'Laundry redispatch time precedes sufficient linked physical return for this distribution batch/size';
    end if;

    select sum(x.qty_sent_pcs)::bigint into v_total
    from jsonb_to_recordset(v_lines) x(size_id uuid,qty_sent_pcs integer);
    select coalesce(w.unsent_ready_qty_pcs,0)::bigint into v_available
    from erp.v_wip_control_status_v1 w where w.cutting_group_id=v_group.id;
    if v_total>coalesce(v_available,0) then
      raise exception 'Laundry send exceeds sewn-and-unsent capacity. Ready %, requested %',coalesce(v_available,0),v_total;
    end if;
    select greatest(
      coalesce((
        select sum(e.qty_signed) from erp.sewing_terminal_events e
        where e.cutting_group_id=v_group.id and e.physical_at<=v_physical_at
      ),0)
      -coalesce((
        select sum(dl.qty_sent_pcs)
        from erp.laundry_delivery_lines dl
        join erp.laundry_deliveries d on d.id=dl.delivery_id
        where dl.cutting_group_id=v_group.id
          and d.status<>'DRAFT' and d.physical_at<=v_physical_at
      ),0)
      +coalesce((
        select sum(rv.qty_pcs)
        from erp.wip_stage_events rv
        join erp.wip_stage_events src
          on src.id=rv.source_id and src.source_type='LAUNDRY_DELIVERY_LINE'
        where rv.cutting_group_id=v_group.id
          and rv.source_type='CP6_LAUNDRY_DELIVERY_WIP_REVERSAL'
          and rv.physical_at<=v_physical_at
      ),0)
      -coalesce((
        select sum(i.qty_good_pcs+i.qty_bs_pcs)
        from erp.qc_inspection_items i
        join erp.qc_inspections q on q.id=i.inspection_id
        where i.cutting_group_id=v_group.id
          and i.source_laundry_receipt_line_id is null
          and q.status='POSTED' and q.physical_at<=v_physical_at
      ),0),0
    )::bigint into v_available_at_physical_time;
    if v_total>v_available_at_physical_time then
      raise exception 'Laundry send time predates sufficient authoritative sewing output. Ready at physical time %, requested %',
        v_available_at_physical_time,v_total;
    end if;

    perform erp.assert_cp6_dispatch_timeline_v2620b(
      v_batch_id,v_group.id,v_physical_at,v_lines
    );
    v_delivery_id:=gen_random_uuid();
    v_delivery_line_id:=gen_random_uuid();
    -- The UUID is already the immutable document identity. Keep all 128 bits
    -- in the unique human key so two valid postings can never be rejected by
    -- the former 40-bit display prefix collision surface.
    v_number:='LDR-'||to_char((v_physical_at AT TIME ZONE 'Asia/Jakarta'),'YYMMDD')||'-'
      ||upper(replace(v_delivery_id::text,'-',''));
    insert into erp.laundry_deliveries(
      id,delivery_number,po_id,vendor_id,target_dyeing_color,target_wash_process_id,
      special_instruction,physical_at,status,created_by,colour_process,sku_reference_id,dyeing_type_id
    ) values(
      v_delivery_id,v_number,v_group.po_id,v_vendor_id,v_target_color,v_process_id,
      nullif(btrim(p_payload->>'notes'),''),v_physical_at,'DRAFT',v_actor,
      coalesce(erp.cp8_laundry_dyeing_label_v1(v_vendor_id,nullif(p_payload->>'dyeing_type_id','')::uuid),
        nullif(btrim(p_payload->>'colour_process'),'')),
      nullif(p_payload->>'sku_reference_id','')::uuid,nullif(p_payload->>'dyeing_type_id','')::uuid
    );
    insert into erp.laundry_delivery_lines(
      id,delivery_id,cutting_group_id,qty_sent_pcs,estimated_rate_snapshot,
      estimated_cost_status,notes
    ) values(
      v_delivery_line_id,v_delivery_id,v_group.id,v_total,v_rate,case when v_rate is null then 'PENDING' else 'ESTIMATED' end,
      'CP6 immutable distribution batch/size handoff: '||v_reason
    );
    insert into erp.laundry_delivery_batch_size_lines(
      delivery_line_id,distribution_batch_id,size_id,qty_sent_pcs,created_by
    ) select v_delivery_line_id,v_batch_id,x.size_id,x.qty_sent_pcs,v_actor
      from jsonb_to_recordset(v_lines) x(size_id uuid,qty_sent_pcs integer);
    -- BD: the priced charge lines and per-size estimates of this delivery (only inside the BD facade's context).
    -- Use the same BF pending evidence and invoice allocation as a priced delivery.
    if v_rate is null and coalesce((erp.bd_context_v1()).action,'')<>'POST_PRICED_DELIVERY' then
      insert into erp.bd_execution_context_v1(backend_pid,transaction_id,action,request_id,pricing)
      values(pg_backend_pid(),txid_current(),'POST_PRICED_DELIVERY',p_client_request_id,
        erp.bd_compute_pricing_v1(p_payload,jsonb_build_object('deferred',true)));
      perform erp.bd_attach_delivery_pricing_v1(v_delivery_line_id);
      delete from erp.bd_execution_context_v1
      where backend_pid=pg_backend_pid() and transaction_id=txid_current();
    else
      perform erp.bd_attach_delivery_pricing_v1(v_delivery_line_id);
    end if;
    insert into erp.cp6_laundry_qc_execution_context(
      backend_pid,transaction_id,actor_key,action,permission_key,client_request_id,payload
    ) values(
      pg_backend_pid(),txid_current(),erp._idempotency_actor_key(),v_action,
      'production.laundry.post',p_client_request_id,p_payload
    );
    if exists(
      select 1 from erp.schema_migrations where version='v2.6.20d'
    ) then
      if to_regprocedure('erp.allocate_laundry_redispatch_participants_v2620e(uuid)') is null then
        raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: v2.6.20d redispatch allocator is missing';
      end if;
      perform erp.allocate_laundry_redispatch_participants_v2620e(v_delivery_line_id);
    end if;
    perform erp.post_laundry_delivery(v_delivery_id);
    delete from erp.cp6_laundry_qc_execution_context
    where backend_pid=pg_backend_pid() and transaction_id=txid_current();
    if not found then raise exception 'CP6 execution context cleanup failed'; end if;
    select * into v_delivery from erp.laundry_deliveries where id=v_delivery_id;
    select * into v_group from erp.cutting_groups where id=v_group.id;
    v_response:=jsonb_build_object(
      'action',v_action,'delivery_id',v_delivery.id,'delivery_number',v_delivery.delivery_number,
      'status',v_delivery.status,'row_version',v_delivery.row_version,
      'cutting_group_id',v_group.id,'cutting_group_row_version',v_group.row_version,
      'qty_sent_pcs',v_total,'rate_per_pcs',v_rate,
      'estimated_cost',round(v_total*v_rate,2),
      'stock_effect','SEWING_TO_LAUNDRY','hpp_effect','LAUNDRY_ACCRUAL_REBUILT'
    );

  elsif v_action='POST_RECEIPT' then
    if p_expected_version is null or v_delivery_id is null then
      raise exception 'Delivery and expected_version are required';
    end if;
    if jsonb_typeof(v_lines)<>'array' or jsonb_array_length(v_lines)=0 then
      raise exception 'Laundry receipt requires positive batch/size return lines';
    end if;
    if exists(
      select 1 from jsonb_to_recordset(v_lines) x(
        delivery_batch_size_line_id uuid,qty_good_received integer,
        qty_bs_laundry integer,bs_product_id uuid
      ) where x.delivery_batch_size_line_id is null
        or coalesce(x.qty_good_received,0)<0 or coalesce(x.qty_bs_laundry,0)<0
        or coalesce(x.qty_good_received,0)+coalesce(x.qty_bs_laundry,0)<=0
        or(coalesce(x.qty_bs_laundry,0)>0 and x.bs_product_id is null)
        or(coalesce(x.qty_bs_laundry,0)=0 and x.bs_product_id is not null)
    ) or exists(
      select 1 from jsonb_to_recordset(v_lines) x(
        delivery_batch_size_line_id uuid,qty_good_received integer,
        qty_bs_laundry integer,bs_product_id uuid
      ) group by x.delivery_batch_size_line_id having count(*)>1
    ) then raise exception 'Receipt size lines must be unique, positive, and bind every Laundry BS to a product'; end if;

    select min(dl.cutting_group_id::text)::uuid,count(*)::integer
      into v_group_id,v_group_count
    from erp.laundry_delivery_lines dl where dl.delivery_id=v_delivery_id;
    if v_group_count<>1 or v_group_id is null then
      raise exception 'Connected CP6 receipt requires one authoritative delivery line';
    end if;
    perform pg_advisory_xact_lock(hashtextextended('CP6FLOW:'||v_group_id::text,0));
    select * into v_delivery from erp.laundry_deliveries where id=v_delivery_id for update;
    if v_delivery.id is null or v_delivery.status not in('SENT','PARTIAL_RETURN') then
      raise exception 'Laundry receipt requires an active SENT/PARTIAL_RETURN delivery';
    end if;
    if v_delivery.row_version<>p_expected_version then
      raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_delivery.row_version;
    end if;
    if v_physical_at<v_delivery.physical_at then
      raise exception 'Laundry return time cannot be earlier than the send time';
    end if;
    if exists(select 1 from erp.laundry_claims c where c.delivery_id=v_delivery.id
      and c.claim_type in('STUCK','MISSING') and c.status<>'REJECTED') then
      raise exception 'Reverse/reject the active STUCK/MISSING claim before posting a late physical return';
    end if;
    if v_process_id is not null then
      perform 1 from erp.wash_processes w where w.id=v_process_id and w.is_active for share;
      if not found then raise exception 'An active authoritative actual wash process is required'; end if;
      perform pg_advisory_xact_lock(hashtextextended('LRATE:'||v_delivery.vendor_id::text||':'||v_process_id::text,0));
    end if;
    -- BA (round 9, W1 source inventory; M:4474 LAU-DEC03 / LAU-T14): the receipt prices the actual process at the rate that
    -- was effective when the goods were sent (the agreement snapshot), not at the return time; a rate version that starts
    -- between send and return does not reprice the delivery.
    v_deferred_delivery:=exists(select 1 from erp.bd_laundry_priced_lines_v1 bp
      join erp.bf_laundry_delivery_sources_v1 bf using(delivery_line_id)
      where bp.delivery_id=v_delivery.id and bf.details_pending);
    if v_deferred_delivery then
      v_rate:=null;
    elsif v_process_id is null then
      -- An agreed estimate may remain on the return without claiming the actual process is known.
      select dl.estimated_rate_snapshot into v_rate from erp.laundry_delivery_lines dl where dl.delivery_id=v_delivery.id;
    elsif exists(select 1 from erp.bd_laundry_priced_lines_v1 bp where bp.delivery_id=v_delivery.id) then
      -- BD (LAU-05b): a priced delivery is received at its own exact estimate (erp.bd_allocate_receipt_v1 below), with the
      -- process it was priced for; its rate snapshot is the priced average (NULL while a component price is unknown).
      if v_delivery.target_wash_process_id is not null and v_process_id<>v_delivery.target_wash_process_id then
        raise exception 'BD_PROCESS_CHANGED: kiriman dengan harga paket/komponen/borongan hanya diterima dengan proses yang dihargai saat kirim';
      end if;
      select dl.estimated_rate_snapshot into v_rate from erp.laundry_delivery_lines dl where dl.delivery_id=v_delivery.id;
      v_rate_count:=1;
    else
      select count(*)::integer,min(r.rate_per_pcs) into v_rate_count,v_rate
      from erp.laundry_vendor_rate_versions r
      where r.vendor_id=v_delivery.vendor_id and r.wash_process_id=v_process_id
        and r.effective_from<=v_delivery.physical_at
        and(r.effective_to is null or r.effective_to>v_delivery.physical_at);
      if v_rate_count<>1 then
        raise exception 'Exactly one authoritative actual Laundry rate must be effective for this vendor/process/time; found % (rate of the send time)',v_rate_count;
      end if;
    end if;
    perform 1 from erp.laundry_vendor_rate_versions r
    where r.vendor_id=v_delivery.vendor_id and r.wash_process_id=v_process_id
      and r.effective_from<=v_delivery.physical_at
      and(r.effective_to is null or r.effective_to>v_delivery.physical_at)
    order by r.id for share;
    select min(dl.id::text)::uuid into v_delivery_line_id
    from erp.laundry_delivery_lines dl
    where dl.delivery_id=v_delivery.id and dl.cutting_group_id=v_group_id;
    if v_delivery_line_id is null or(
      select count(*) from erp.laundry_delivery_lines dl where dl.delivery_id=v_delivery.id
    )<>1 then raise exception 'Connected CP6 receipt requires one authoritative delivery line'; end if;
    perform 1
    from erp.laundry_delivery_batch_size_lines sx
    join jsonb_to_recordset(v_lines) x(
      delivery_batch_size_line_id uuid,qty_good_received integer,
      qty_bs_laundry integer,bs_product_id uuid
    ) on x.delivery_batch_size_line_id=sx.id
    order by sx.id for update of sx;
    if(
      select count(*) from erp.laundry_delivery_batch_size_lines sx
      join jsonb_to_recordset(v_lines) x(
        delivery_batch_size_line_id uuid,qty_good_received integer,
        qty_bs_laundry integer,bs_product_id uuid
      ) on x.delivery_batch_size_line_id=sx.id
      where sx.delivery_line_id=v_delivery_line_id
    )<>jsonb_array_length(v_lines) then
      raise exception 'A receipt source does not belong to this CP6 delivery';
    end if;
    if exists(
      select 1
      from jsonb_to_recordset(v_lines) x(
        delivery_batch_size_line_id uuid,qty_good_received integer,
        qty_bs_laundry integer,bs_product_id uuid
      )
      join erp.laundry_delivery_batch_size_lines sx on sx.id=x.delivery_batch_size_line_id
      where coalesce(x.qty_good_received,0)+coalesce(x.qty_bs_laundry,0)>
        sx.qty_sent_pcs-coalesce((
          select sum(rx.qty_good_received+rx.qty_bs_laundry)
          from erp.laundry_receipt_batch_size_lines rx
          join erp.laundry_receipt_lines rl on rl.id=rx.receipt_line_id
          join erp.laundry_receipts rh on rh.id=rl.receipt_id
          where rx.delivery_batch_size_line_id=sx.id and rh.status='POSTED'
        ),0)
    ) then raise exception 'Laundry receipt exceeds remaining quantity for an exact batch/size source'; end if;

    select sum(coalesce(x.qty_good_received,0))::bigint,
           sum(coalesce(x.qty_bs_laundry,0))::bigint
      into v_good,v_bs
    from jsonb_to_recordset(v_lines) x(
      delivery_batch_size_line_id uuid,qty_good_received integer,
      qty_bs_laundry integer,bs_product_id uuid
    );
    v_total:=v_good+v_bs;
    v_receipt_id:=gen_random_uuid();
    v_receipt_line_id:=gen_random_uuid();
    v_number:='LRC-'||to_char((v_physical_at AT TIME ZONE 'Asia/Jakarta'),'YYMMDD')||'-'
      ||upper(replace(v_receipt_id::text,'-',''));
    insert into erp.laundry_receipts(
      id,receipt_number,delivery_id,physical_at,status,created_by
    ) values(v_receipt_id,v_number,v_delivery.id,v_physical_at,'DRAFT',v_actor);
    insert into erp.laundry_receipt_lines(
      id,receipt_id,delivery_line_id,actual_wash_process_id,
      qty_good_received,qty_bs_laundry,qty_stuck,qty_missing,
      actual_rate_snapshot,actual_cost_status,actual_cost,notes
    ) values(
      v_receipt_line_id,v_receipt_id,v_delivery_line_id,v_process_id,
      -- A physical receipt proves the process/rate snapshot, not the vendor
      -- invoice.  Keep the amount ESTIMATED so the delivery accrual remains a
      -- liability until post_vendor_invoice atomically replaces it with AP.
      -- Marking this FINAL here would release accrual early and leave negative
      -- WIP after the same cost moves into FG/HPP.
      v_good,v_bs,0,0,v_rate,'ESTIMATED',round(v_total*v_rate,2),
      'CP6 immutable physical batch/size return: '||v_reason
    );
    insert into erp.laundry_receipt_batch_size_lines(
      receipt_line_id,delivery_batch_size_line_id,size_id,
      qty_good_received,qty_bs_laundry,bs_product_id,created_by
    ) select v_receipt_line_id,x.delivery_batch_size_line_id,sx.size_id,
        coalesce(x.qty_good_received,0),coalesce(x.qty_bs_laundry,0),x.bs_product_id,v_actor
      from jsonb_to_recordset(v_lines) x(
        delivery_batch_size_line_id uuid,qty_good_received integer,
        qty_bs_laundry integer,bs_product_id uuid
      ) join erp.laundry_delivery_batch_size_lines sx on sx.id=x.delivery_batch_size_line_id;
    -- BD: each size of a priced delivery takes its exact share of the estimate; the receipt line's cost is their sum.
    perform erp.bd_allocate_receipt_v1(v_receipt_line_id);
    insert into erp.laundry_receipt_bs_product_allocations(
      receipt_line_id,product_id,qty_bs,notes,created_by
    ) select v_receipt_line_id,x.bs_product_id,sum(x.qty_bs_laundry)::integer,
        'CP6 immutable Laundry-BS product/size declaration',v_actor
      from jsonb_to_recordset(v_lines) x(
        delivery_batch_size_line_id uuid,qty_good_received integer,
        qty_bs_laundry integer,bs_product_id uuid
      ) where x.qty_bs_laundry>0 group by x.bs_product_id;
    insert into erp.cp6_laundry_qc_execution_context(
      backend_pid,transaction_id,actor_key,action,permission_key,client_request_id,payload
    ) values(
      pg_backend_pid(),txid_current(),erp._idempotency_actor_key(),v_action,
      'production.laundry.post',p_client_request_id,p_payload
    );
    perform erp.post_laundry_receipt(v_receipt_id);
    -- The predecessor function records every physical return as LAUNDRY → QC.
    -- Laundry BS is terminal at this boundary, so append the balancing
    -- QC → ON_HOLD event instead of rewriting/deleting the predecessor event.
    insert into erp.wip_stage_events(
      po_id,cutting_group_id,stage_from,stage_to,qty_pcs,
      source_type,source_id,physical_at,created_by,notes
    )
    select v_delivery.po_id,dl.cutting_group_id,'QC','ON_HOLD',x.qty_bs_laundry,
      'CP6_LAUNDRY_BS_SIZE_LINE',x.id,v_physical_at,v_actor,
      'Laundry BS is terminal and must never become QC-ready'
    from erp.laundry_receipt_batch_size_lines x
    join erp.laundry_receipt_lines rl on rl.id=x.receipt_line_id
    join erp.laundry_delivery_lines dl on dl.id=rl.delivery_line_id
    where x.receipt_line_id=v_receipt_line_id and x.qty_bs_laundry>0;
    delete from erp.cp6_laundry_qc_execution_context
    where backend_pid=pg_backend_pid() and transaction_id=txid_current();
    if not found then raise exception 'CP6 execution context cleanup failed'; end if;
    select * into v_receipt from erp.laundry_receipts where id=v_receipt_id;
    select * into v_delivery from erp.laundry_deliveries where id=v_delivery.id;
    v_response:=jsonb_build_object(
      'action',v_action,'receipt_id',v_receipt.id,'receipt_number',v_receipt.receipt_number,
      'receipt_status',v_receipt.status,'receipt_row_version',v_receipt.row_version,
      'delivery_id',v_delivery.id,'delivery_status',v_delivery.status,
      'delivery_row_version',v_delivery.row_version,'good_qty_pcs',v_good,'bs_qty_pcs',v_bs,
      'rate_per_pcs',v_rate,'actual_cost',(select rl.actual_cost from erp.laundry_receipt_lines rl where rl.id=v_receipt_line_id),
      'cost_status',case when (select rl.actual_cost_status from erp.laundry_receipt_lines rl where rl.id=v_receipt_line_id)='PENDING'
        then 'PRICE_UNKNOWN' else 'ESTIMATED_UNBILLED' end,
      'accrual_effect','PRESERVED_UNTIL_VENDOR_INVOICE',
      'stock_effect','LAUNDRY_GOOD_TO_QC_AND_BS_TO_ON_HOLD',
      'hpp_effect','ACTUAL_LAUNDRY_COST_REBUILT'
    );

  elsif v_action='POST_FAILED_WASH' then
    if p_expected_version is null or v_delivery_id is null or v_process_id is null then
      raise exception 'Delivery, failed process, and expected_version are required';
    end if;
    if jsonb_typeof(v_lines)<>'array' or jsonb_array_length(v_lines)=0 then
      raise exception 'Paid failed wash requires positive attempted batch/size lines';
    end if;
    if exists(
      select 1 from jsonb_to_recordset(v_lines) x(
        delivery_batch_size_line_id uuid,qty_attempted_pcs integer
      ) where x.delivery_batch_size_line_id is null or coalesce(x.qty_attempted_pcs,0)<=0
    ) or exists(
      select 1 from jsonb_to_recordset(v_lines) x(
        delivery_batch_size_line_id uuid,qty_attempted_pcs integer
      ) group by x.delivery_batch_size_line_id having count(*)>1
    ) then
      raise exception 'Failed-wash size lines must be unique positive integer pieces';
    end if;

    select min(dl.cutting_group_id::text)::uuid,count(*)::integer
      into v_group_id,v_group_count
    from erp.laundry_delivery_lines dl where dl.delivery_id=v_delivery_id;
    if v_group_count<>1 or v_group_id is null then
      raise exception 'Connected failed-wash action requires one authoritative delivery line';
    end if;
    perform pg_advisory_xact_lock(hashtextextended('CP6FLOW:'||v_group_id::text,0));
    select * into v_delivery from erp.laundry_deliveries
    where id=v_delivery_id for update;
    if v_delivery.id is null or v_delivery.status not in('SENT','PARTIAL_RETURN') then
      raise exception 'Paid failed wash requires an active SENT/PARTIAL_RETURN delivery';
    end if;
    if v_delivery.row_version<>p_expected_version then
      raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_delivery.row_version;
    end if;
    if v_physical_at<v_delivery.physical_at
       or exists(select 1 from erp.laundry_receipts r
         where r.delivery_id=v_delivery.id and r.status='POSTED'
           and r.physical_at>v_physical_at) then
      raise exception 'Failed-wash physical time cannot precede the send or later posted Laundry history';
    end if;
    if exists(select 1 from erp.laundry_claims c
      where c.delivery_id=v_delivery.id and c.status<>'REJECTED') then
      raise exception 'Resolve/reject active Laundry claims before recording a failed-wash service attempt';
    end if;
    perform 1 from erp.wash_processes w
    where w.id=v_process_id and w.is_active for share;
    if not found then raise exception 'An active authoritative failed wash process is required'; end if;
    perform pg_advisory_xact_lock(hashtextextended(
      'LRATE:'||v_delivery.vendor_id::text||':'||v_process_id::text,0
    ));
    select count(*)::integer,min(r.rate_per_pcs) into v_rate_count,v_rate
    from erp.laundry_vendor_rate_versions r
    where r.vendor_id=v_delivery.vendor_id and r.wash_process_id=v_process_id
      and r.effective_from<=v_physical_at
      and(r.effective_to is null or r.effective_to>v_physical_at);
    -- OW-08b (LAU-DEC04): no effective rate is recorded as an unknown price only when the request says so (never zero);
    -- a known rate is never recorded as unknown, and more than one effective rate stays refused (ambiguity is not unknown).
    if v_rate_count=0 and p_payload->>'price_status'='UNKNOWN' then
      v_rate:=null;
    elsif v_rate_count=1 and p_payload->>'price_status'='UNKNOWN' then
      raise exception 'CP7_FAILED_WASH_RATE_KNOWN: tarif vendor untuk proses dan waktu ini sudah ada; catat cuci gagal dengan tarif itu, bukan sebagai harga belum diketahui';
    elsif v_rate_count<>1 then
      raise exception 'Exactly one authoritative failed-wash rate must be effective for this vendor/process/time; found %',v_rate_count;
    end if;
    perform 1 from erp.laundry_vendor_rate_versions r
    where r.vendor_id=v_delivery.vendor_id and r.wash_process_id=v_process_id
      and r.effective_from<=v_physical_at
      and(r.effective_to is null or r.effective_to>v_physical_at)
    order by r.id for share;
    select min(dl.id::text)::uuid into v_delivery_line_id
    from erp.laundry_delivery_lines dl where dl.delivery_id=v_delivery.id;
    perform 1
    from erp.laundry_delivery_batch_size_lines s
    join jsonb_to_recordset(v_lines) x(
      delivery_batch_size_line_id uuid,qty_attempted_pcs integer
    ) on x.delivery_batch_size_line_id=s.id
    order by s.id for update of s;
    if (select count(*)
        from erp.laundry_delivery_batch_size_lines s
        join jsonb_to_recordset(v_lines) x(
          delivery_batch_size_line_id uuid,qty_attempted_pcs integer
        ) on x.delivery_batch_size_line_id=s.id
        where s.delivery_line_id=v_delivery_line_id)<>jsonb_array_length(v_lines)
       or exists(
         select 1
         from jsonb_to_recordset(v_lines) x(
           delivery_batch_size_line_id uuid,qty_attempted_pcs integer
         )
         join erp.laundry_delivery_batch_size_lines s
           on s.id=x.delivery_batch_size_line_id
         where x.qty_attempted_pcs>s.qty_sent_pcs-coalesce((
           select sum(rx.qty_good_received+rx.qty_bs_laundry)
           from erp.laundry_receipt_batch_size_lines rx
           join erp.laundry_receipt_lines rl on rl.id=rx.receipt_line_id
           join erp.laundry_receipts rh on rh.id=rl.receipt_id
           where rx.delivery_batch_size_line_id=s.id and rh.status='POSTED'
         ),0)
       ) then
      raise exception 'Failed-wash attempted quantity exceeds the exact pieces still in Laundry custody';
    end if;
    select sum(x.qty_attempted_pcs)::bigint into v_total
    from jsonb_to_recordset(v_lines) x(
      delivery_batch_size_line_id uuid,qty_attempted_pcs integer
    );
    if v_custody_outcome='RETURN_UNPROCESSED' and(
      v_delivery.status<>'SENT'
      or exists(
        select 1 from erp.laundry_receipt_lines rl
        join erp.laundry_receipts rh on rh.id=rl.receipt_id
        left join erp.laundry_failed_wash_attempts a on a.receipt_line_id=rl.id
        where rh.delivery_id=v_delivery.id and rh.status='POSTED'
          and a.id is null and rl.qty_good_received+rl.qty_bs_laundry>0
      )
      or jsonb_array_length(v_lines)<>(
        select count(*) from erp.laundry_delivery_batch_size_lines s
        where s.delivery_line_id=v_delivery_line_id
      )
      or exists(
        select 1 from erp.laundry_delivery_batch_size_lines s
        left join jsonb_to_recordset(v_lines) x(
          delivery_batch_size_line_id uuid,qty_attempted_pcs integer
        ) on x.delivery_batch_size_line_id=s.id
        where s.delivery_line_id=v_delivery_line_id
          and x.qty_attempted_pcs is distinct from s.qty_sent_pcs
      )
    ) then
      raise exception 'Return-unprocessed is deliberately all-or-nothing: every exact sent size must return before redispatch';
    end if;

    v_receipt_id:=gen_random_uuid();
    v_receipt_line_id:=gen_random_uuid();
    v_failed_wash_attempt_id:=gen_random_uuid();
    v_number:='LFW-'||to_char((v_physical_at AT TIME ZONE 'Asia/Jakarta'),'YYMMDD')||'-'
      ||upper(replace(v_receipt_id::text,'-',''));
    insert into erp.cp6_laundry_qc_execution_context(
      backend_pid,transaction_id,actor_key,action,permission_key,client_request_id,payload
    ) values(
      pg_backend_pid(),txid_current(),erp._idempotency_actor_key(),v_action,
      'production.laundry.post',p_client_request_id,p_payload
    );
    insert into erp.laundry_receipts(
      id,receipt_number,delivery_id,physical_at,status,created_by
    ) values(v_receipt_id,v_number,v_delivery.id,v_physical_at,'DRAFT',v_actor);
    insert into erp.laundry_receipt_lines(
      id,receipt_id,delivery_line_id,actual_wash_process_id,
      qty_good_received,qty_bs_laundry,qty_stuck,qty_missing,
      actual_rate_snapshot,actual_cost_status,actual_cost,notes
    ) values(
      v_receipt_line_id,v_receipt_id,v_delivery_line_id,v_process_id,
      0,0,0,0,v_rate,case when p_payload->>'price_status'='UNKNOWN' then 'PENDING' else 'ESTIMATED' end,round(v_total*v_rate,2),
      'CP6 paid failed-wash service only; no physical Good/BS receipt: '||v_reason
    );
    insert into erp.laundry_failed_wash_attempts(
      id,receipt_id,receipt_line_id,delivery_id,custody_outcome,
      qty_attempted_pcs,reason,created_by
    ) values(
      v_failed_wash_attempt_id,v_receipt_id,v_receipt_line_id,v_delivery.id,
      v_custody_outcome,v_total,v_reason,v_actor
    );
    -- OW-08b: the unknown price is registered with the attempt (who, when, why); owner/admin sets it later, once.
    if p_payload->>'price_status'='UNKNOWN' then
      insert into cp7_laundry_unknown_wash.prices_v1(attempt_id,receipt_line_id,po_id,recorded_by,recorded_reason)
      values(v_failed_wash_attempt_id,v_receipt_line_id,v_delivery.po_id,v_actor,v_reason);
    end if;
    insert into erp.laundry_failed_wash_batch_size_lines(
      attempt_id,delivery_batch_size_line_id,size_id,qty_attempted_pcs,created_by
    ) select v_failed_wash_attempt_id,x.delivery_batch_size_line_id,s.size_id,
        x.qty_attempted_pcs,v_actor
      from jsonb_to_recordset(v_lines) x(
        delivery_batch_size_line_id uuid,qty_attempted_pcs integer
      ) join erp.laundry_delivery_batch_size_lines s
        on s.id=x.delivery_batch_size_line_id;

    if v_custody_outcome='RETURN_UNPROCESSED' then
      perform set_config('app.physical_at',v_physical_at::text,true);
      update erp.laundry_deliveries
      set status='REVERSED',updated_at=clock_timestamp()
      where id=v_delivery.id;
      select min(rv.id::text)::uuid,count(*)::integer
        into v_return_wip_event_id,v_group_count
      from erp.wip_stage_events rv
      join erp.wip_stage_events src
        on src.id=rv.source_id and src.source_type='LAUNDRY_DELIVERY_LINE'
      join erp.laundry_delivery_lines dl
        on dl.id=src.source_id and dl.delivery_id=v_delivery.id
      where rv.source_type='CP6_LAUNDRY_DELIVERY_WIP_REVERSAL';
      if v_group_count<>1 or v_return_wip_event_id is null then
        raise exception 'Return-unprocessed did not create exactly one linked physical WIP inverse';
      end if;
      update erp.laundry_failed_wash_attempts
      set return_wip_event_id=v_return_wip_event_id
      where id=v_failed_wash_attempt_id;
    else
      update erp.laundry_deliveries set updated_at=clock_timestamp()
      where id=v_delivery.id;
    end if;

    update erp.laundry_receipts
    set status='POSTED',updated_at=clock_timestamp()
    where id=v_receipt_id;

    if v_custody_outcome='RETURN_UNPROCESSED' then
      update erp.cutting_groups g
      set status=case
        when exists(
          select 1 from erp.laundry_receipt_lines rl
          join erp.laundry_receipts rh on rh.id=rl.receipt_id and rh.status='POSTED'
          join erp.laundry_delivery_lines dl on dl.id=rl.delivery_line_id
          join erp.laundry_deliveries d on d.id=dl.delivery_id and d.status<>'REVERSED'
          where dl.cutting_group_id=g.id and rl.qty_good_received+rl.qty_bs_laundry>0
        ) then 'RETURNED'
        when exists(
          select 1 from erp.laundry_delivery_lines dl
          join erp.laundry_deliveries d on d.id=dl.delivery_id
          where dl.cutting_group_id=g.id and d.status not in('DRAFT','REVERSED')
        ) then 'LAUNDRY'
        when g.picked_up_at is not null then 'PICKED_UP' else 'CUT' end
      where g.id=v_group_id;
      select * into v_po from erp.production_orders where id=v_delivery.po_id for update;
      if v_po.status not in('ON_HOLD','CANCELLED') then
        update erp.production_orders po set
          status=case
            when exists(select 1 from erp.qc_inspections q
              where q.po_id=po.id and q.status='POSTED') then 'QC'
            when exists(select 1 from erp.laundry_deliveries d
              where d.po_id=po.id and d.status not in('DRAFT','REVERSED')) then 'LAUNDRY'
            when exists(select 1 from erp.cutting_groups g
              where g.po_id=po.id and g.picked_up_at is not null) then 'SEWING'
            else 'CUTTING' end,
          current_stage=case
            when exists(select 1 from erp.qc_inspections q
              where q.po_id=po.id and q.status='POSTED') then 'QC'
            when exists(select 1 from erp.laundry_deliveries d
              where d.po_id=po.id and d.status not in('DRAFT','REVERSED')) then 'LAUNDRY'
            when exists(select 1 from erp.cutting_groups g
              where g.po_id=po.id and g.picked_up_at is not null) then 'SEWING'
            else 'CUTTING' end,
          updated_at=clock_timestamp()
        where po.id=v_po.id;
      end if;
    end if;

    perform erp.sync_laundry_accrual(v_delivery.po_id,(v_physical_at AT TIME ZONE 'Asia/Jakarta')::date);
    if exists(select 1 from erp.fg_lots f where f.po_id=v_delivery.po_id) then
      perform erp.rebuild_po_hpp(
        v_delivery.po_id,'Paid failed-wash service attempt '||v_failed_wash_attempt_id::text
      );
      perform erp.propagate_conversion_hpp_for_po(v_delivery.po_id);
      perform erp.sync_po_hpp_to_gl(v_delivery.po_id,(v_physical_at AT TIME ZONE 'Asia/Jakarta')::date);
    end if;
    insert into erp.audit_logs(
      entity_type,entity_id,action,new_data,changed_by,change_reason
    ) values(
      'laundry_failed_wash_attempts',v_failed_wash_attempt_id,'POST',
      jsonb_build_object(
        'receipt_id',v_receipt_id,'delivery_id',v_delivery.id,
        'custody_outcome',v_custody_outcome,'qty_attempted_pcs',v_total,
        'rate_per_pcs',v_rate,'estimated_cost',round(v_total*v_rate,2),
        'history_deleted',false
      ),v_actor,v_reason
    );
    delete from erp.cp6_laundry_qc_execution_context
    where backend_pid=pg_backend_pid() and transaction_id=txid_current();
    if not found then raise exception 'CP6 execution context cleanup failed'; end if;
    select * into v_receipt from erp.laundry_receipts where id=v_receipt_id;
    select * into v_delivery from erp.laundry_deliveries where id=v_delivery.id;
    v_response:=jsonb_build_object(
      'action',v_action,'failed_wash_attempt_id',v_failed_wash_attempt_id,
      'receipt_id',v_receipt.id,'receipt_number',v_receipt.receipt_number,
      'receipt_status',v_receipt.status,'receipt_row_version',v_receipt.row_version,
      'delivery_id',v_delivery.id,'delivery_status',v_delivery.status,
      'delivery_row_version',v_delivery.row_version,
      'custody_outcome',v_custody_outcome,'qty_attempted_pcs',v_total,
      'rate_per_pcs',v_rate,'actual_cost',round(v_total*v_rate,2),
      'cost_status',case when p_payload->>'price_status'='UNKNOWN' then 'PRICE_UNKNOWN' else 'ESTIMATED_UNBILLED' end,
      'stock_effect',case when v_custody_outcome='RETRY_AT_VENDOR'
        then 'PHYSICAL_STAYS_AT_LAUNDRY' else 'LAUNDRY_TO_SEWING_RETURN' end,
      'hpp_effect',case when p_payload->>'price_status'='UNKNOWN' then 'FAILED_WASH_COST_UNKNOWN_HPP_NOT_FINAL'
        else 'FAILED_WASH_COST_REBUILT_WITHOUT_GOOD_BS_OR_FG' end
    );

  elsif v_action='REVERSE_DELIVERY' then
    if p_expected_version is null or v_delivery_id is null then
      raise exception 'Delivery and expected_version are required';
    end if;
    select min(dl.cutting_group_id::text)::uuid,count(distinct dl.cutting_group_id)::integer
      into v_group_id,v_group_count
    from erp.laundry_delivery_lines dl where dl.delivery_id=v_delivery_id;
    if v_group_count<>1 or v_group_id is null then
      raise exception 'Connected CP6 delivery reversal requires one Potongan';
    end if;
    perform pg_advisory_xact_lock(hashtextextended('CP6FLOW:'||v_group_id::text,0));
    select * into v_delivery from erp.laundry_deliveries where id=v_delivery_id for update;
    if v_delivery.id is null then raise exception 'Laundry delivery not found'; end if;
    if v_delivery.row_version<>p_expected_version then
      raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_delivery.row_version;
    end if;
    perform erp.reverse_laundry_delivery(v_delivery.id,v_reason);
    select * into v_delivery from erp.laundry_deliveries where id=v_delivery.id;
    v_response:=jsonb_build_object(
      'action',v_action,'delivery_id',v_delivery.id,'status',v_delivery.status,
      'row_version',v_delivery.row_version,'history_deleted',false,
      'stock_effect','LAUNDRY_TO_SEWING_REVERSED','hpp_effect','LAUNDRY_ACCRUAL_REBUILT'
    );

  elsif v_action='REVERSE_RECEIPT' then
    if p_expected_version is null or nullif(p_payload->>'receipt_id','') is null then
      raise exception 'Receipt and expected_version are required';
    end if;
    v_receipt_id:=(p_payload->>'receipt_id')::uuid;
    select min(dl.cutting_group_id::text)::uuid,count(distinct dl.cutting_group_id)::integer
      into v_group_id,v_group_count
    from erp.laundry_receipt_lines rl
    join erp.laundry_delivery_lines dl on dl.id=rl.delivery_line_id
    where rl.receipt_id=v_receipt_id;
    if v_group_count<>1 or v_group_id is null then
      raise exception 'Connected CP6 receipt reversal requires one Potongan';
    end if;
    perform pg_advisory_xact_lock(hashtextextended('CP6FLOW:'||v_group_id::text,0));
    select * into v_receipt from erp.laundry_receipts where id=v_receipt_id for update;
    if v_receipt.id is null then raise exception 'Laundry receipt not found'; end if;
    if v_receipt.row_version<>p_expected_version then
      raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_receipt.row_version;
    end if;
    select a.id,a.custody_outcome into v_failed_wash_attempt_id,v_custody_outcome
    from erp.laundry_failed_wash_attempts a where a.receipt_id=v_receipt.id
    for update;
    if v_failed_wash_attempt_id is null then
      perform erp.reverse_laundry_receipt(v_receipt.id,v_reason);
      select * into v_receipt from erp.laundry_receipts where id=v_receipt.id;
      v_response:=jsonb_build_object(
        'action',v_action,'receipt_id',v_receipt.id,'status',v_receipt.status,
        'row_version',v_receipt.row_version,'history_deleted',false,
        'stock_effect','LAUNDRY_RETURN_REVERSED','hpp_effect','LAUNDRY_AND_FG_HPP_REBUILT'
      );
    else
      if v_receipt.status='REVERSED' then
        v_response:=jsonb_build_object(
          'action',v_action,'receipt_id',v_receipt.id,'status',v_receipt.status,
          'row_version',v_receipt.row_version,'history_deleted',false,
          'stock_effect','NO_OP_ALREADY_REVERSED',
          'hpp_effect','NO_OP_ALREADY_REVERSED'
        );
      else
        if v_receipt.status<>'POSTED' then
          raise exception 'Only a POSTED failed-wash service attempt can be reversed';
        end if;
        select * into v_delivery from erp.laundry_deliveries
        where id=v_receipt.delivery_id for update;
        select * into v_po from erp.production_orders
        where id=v_delivery.po_id for update;
        if v_po.status='FINISHED' then
          raise exception 'PO sudah FINISHED. Reopen downstream before reversing failed-wash cost history.';
        end if;
        if exists(
          select 1 from erp.vendor_invoice_items i
          join erp.vendor_invoices h on h.id=i.invoice_id
          where i.receipt_line_id in(
            select l.id from erp.laundry_receipt_lines l where l.receipt_id=v_receipt.id
          ) and h.status<>'REVERSED'
        ) then
          raise exception 'Penerimaan laundry ini sudah masuk invoice vendor. Reverse invoice vendor aktif terlebih dahulu.';
        end if;
        if exists(
          select 1 from erp.qc_inspection_items i
          join erp.qc_inspections h on h.id=i.inspection_id
          where i.source_laundry_receipt_line_id in(
            select l.id from erp.laundry_receipt_lines l where l.receipt_id=v_receipt.id
          ) and h.status<>'REVERSED'
        ) or exists(
          select 1 from erp.laundry_receipt_batch_size_lines x
          join erp.laundry_receipt_lines l on l.id=x.receipt_line_id
          where l.receipt_id=v_receipt.id
        ) then
          raise exception 'Failed-wash service-only receipt unexpectedly owns physical/QC facts; reversal stopped for investigation';
        end if;
        update erp.laundry_receipts
        set status='REVERSED',updated_at=clock_timestamp()
        where id=v_receipt.id;
        -- A RETURN_UNPROCESSED custody fact remains immutable. Reversing the
        -- vendor charge never resurrects the old dispatch; a later physical
        -- handoff is a new delivery with its own time, rate, and lineage.
        update erp.laundry_deliveries set updated_at=clock_timestamp()
        where id=v_delivery.id;
        perform erp.sync_laundry_accrual(v_delivery.po_id,((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date);
        if exists(select 1 from erp.fg_lots f where f.po_id=v_delivery.po_id) then
          perform erp.rebuild_po_hpp(
            v_delivery.po_id,'Failed-wash service cost reversed '||v_failed_wash_attempt_id::text
          );
          perform erp.propagate_conversion_hpp_for_po(v_delivery.po_id);
          perform erp.sync_po_hpp_to_gl(v_delivery.po_id,((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date);
        end if;
        insert into erp.audit_logs(
          entity_type,entity_id,action,new_data,changed_by,change_reason
        ) values(
          'laundry_failed_wash_attempts',v_failed_wash_attempt_id,'REVERSE',
          jsonb_build_object(
            'receipt_id',v_receipt.id,'custody_outcome',v_custody_outcome,
            'physical_return_preserved',v_custody_outcome='RETURN_UNPROCESSED',
            'history_deleted',false
          ),v_actor,v_reason
        );
        select * into v_receipt from erp.laundry_receipts where id=v_receipt.id;
        select * into v_delivery from erp.laundry_deliveries where id=v_delivery.id;
        v_response:=jsonb_build_object(
          'action',v_action,'receipt_id',v_receipt.id,'status',v_receipt.status,
          'row_version',v_receipt.row_version,'delivery_id',v_delivery.id,
          'delivery_status',v_delivery.status,'delivery_row_version',v_delivery.row_version,
          'history_deleted',false,'custody_outcome',v_custody_outcome,
          'stock_effect',case when v_custody_outcome='RETURN_UNPROCESSED'
            then 'PHYSICAL_RETURN_PRESERVED' else 'PHYSICAL_STAYS_AT_LAUNDRY' end,
          'hpp_effect','FAILED_WASH_COST_REVERSED_AND_REPORTS_REBUILT'
        );
      end if;
    end if;

  elsif v_action='POST_FINAL_SKU' then
    if p_expected_version is null or v_group_id is null or v_location_id is null then
      raise exception 'Potongan, destination FG location, and expected_version are required';
    end if;
    if jsonb_typeof(v_lines)<>'array' or jsonb_array_length(v_lines)=0 then
      raise exception 'Final SKU posting requires at least one allocation line';
    end if;
    if exists(
      select 1 from jsonb_to_recordset(v_lines) x(
        final_product_id uuid,qty_good_pcs integer,qty_bs_pcs integer,
        source_laundry_receipt_line_id uuid,
        source_laundry_receipt_batch_size_line_id uuid,notes text
      ) where x.final_product_id is null
        or coalesce(x.qty_good_pcs,0)<0 or coalesce(x.qty_bs_pcs,0)<0
        or coalesce(x.qty_good_pcs,0)+coalesce(x.qty_bs_pcs,0)<=0
        or x.source_laundry_receipt_line_id is null
        or x.source_laundry_receipt_batch_size_line_id is null
    ) then raise exception 'Every connected Final SKU line needs positive quantity and exact receipt/batch/size lineage'; end if;
    if exists(
      select 1 from jsonb_to_recordset(v_lines) x(
        final_product_id uuid,qty_good_pcs integer,qty_bs_pcs integer,
        source_laundry_receipt_line_id uuid,
        source_laundry_receipt_batch_size_line_id uuid,notes text
      ) group by x.final_product_id,x.source_laundry_receipt_line_id
      having count(*)>1
    ) then raise exception 'Duplicate Final SKU/source lines are not allowed'; end if;

    perform 1 from erp.locations l
    where l.id=v_location_id and l.is_active and l.location_type='FG_WAREHOUSE'
    for share;
    if not found then raise exception 'Destination must be an active FG warehouse'; end if;

    perform pg_advisory_xact_lock(hashtextextended('CP6FLOW:'||v_group_id::text,0));
    -- The shared Potongan fence is acquired before receipt headers. A
    -- concurrent reversal cannot change
    -- POSTED -> REVERSED after a child source was checked but before QC/FG was
    -- committed.  Lock every referenced header deterministically, then
    -- re-check the complete exact-source chain while those locks are held.
    perform 1
    from erp.laundry_receipts r
    where r.id in(
      select distinct rl.receipt_id
      from jsonb_to_recordset(v_lines) x(
        final_product_id uuid,qty_good_pcs integer,qty_bs_pcs integer,
        source_laundry_receipt_line_id uuid,
        source_laundry_receipt_batch_size_line_id uuid,notes text
      )
      join erp.laundry_receipt_batch_size_lines sx
        on sx.id=x.source_laundry_receipt_batch_size_line_id
      join erp.laundry_receipt_lines rl
        on rl.id=sx.receipt_line_id
    )
    order by r.id
    for update;
    if(
      select count(*)
      from jsonb_to_recordset(v_lines) x(
        final_product_id uuid,qty_good_pcs integer,qty_bs_pcs integer,
        source_laundry_receipt_line_id uuid,
        source_laundry_receipt_batch_size_line_id uuid,notes text
      )
      join erp.laundry_receipt_batch_size_lines sx
        on sx.id=x.source_laundry_receipt_batch_size_line_id
      join erp.laundry_receipt_lines rl
        on rl.id=sx.receipt_line_id
       and rl.id=x.source_laundry_receipt_line_id
      join erp.laundry_receipts r on r.id=rl.receipt_id and r.status='POSTED'
      join erp.laundry_delivery_lines dl
        on dl.id=rl.delivery_line_id and dl.cutting_group_id=v_group_id
      join erp.laundry_deliveries d
        on d.id=dl.delivery_id and d.status<>'REVERSED'
      join erp.cutting_groups g
        on g.id=v_group_id and g.po_id=d.po_id
    )<>jsonb_array_length(v_lines) then
      raise exception 'Every Final SKU source must belong to the same Potongan and an authoritative POSTED Laundry receipt';
    end if;
    insert into erp.cp6_laundry_qc_execution_context(
      backend_pid,transaction_id,actor_key,action,permission_key,client_request_id,payload
    ) values(
      pg_backend_pid(),txid_current(),erp._idempotency_actor_key(),v_action,
      'production.final_sku.post',p_client_request_id,p_payload
    );
    v_nested:=erp.post_final_sku_allocation_v1(p_payload,p_client_request_id,p_expected_version);
    -- completion_mode is operational/reporting state, not browser-owned
    -- metadata.  The predecessor persists the declaration before returning
    -- the authoritative post-mutation progress.  Reject a lie in either
    -- direction here; the exception rolls the nested QC, FG, BS, HPP,
    -- journal, row-version, and both idempotency envelopes back atomically.
    v_ready_after_qc:=nullif(v_nested->>'ready_for_qc_qty_pcs','')::bigint;
    if v_ready_after_qc is null then
      raise exception 'CP6 Final-SKU writer did not return authoritative ready-for-QC balance';
    end if;
    if ((p_payload->>'completion_mode')='ALL_READY' and v_ready_after_qc<>0)
       or ((p_payload->>'completion_mode')='PARTIAL_SELECTION' and v_ready_after_qc=0) then
      raise exception
        'CP6 completion_mode % conflicts with authoritative ready-for-QC remainder % after atomic posting',
        p_payload->>'completion_mode',v_ready_after_qc;
    end if;
    delete from erp.cp6_laundry_qc_execution_context
    where backend_pid=pg_backend_pid() and transaction_id=txid_current();
    if not found then raise exception 'CP6 execution context cleanup failed'; end if;
    v_qc_id:=nullif(v_nested->>'qc_inspection_id','')::uuid;
    select * into v_qc from erp.qc_inspections where id=v_qc_id;
    v_response:=v_nested||jsonb_build_object(
      'action',v_action,'qc_row_version',v_qc.row_version,
      'stock_effect','FG_GOOD_AND_QC_BS_POSTED',
      'hpp_effect','SERVER_REBUILT_FROM_IMMUTABLE_SNAPSHOTS',
      'browser_formula_used',false
    );

  else
    if p_expected_version is null or v_qc_id is null then
      raise exception 'QC inspection and expected_version are required';
    end if;
    select min(i.cutting_group_id::text)::uuid,count(distinct i.cutting_group_id)::integer
      into v_group_id,v_group_count
    from erp.qc_inspection_items i where i.inspection_id=v_qc_id;
    if v_group_count<>1 or v_group_id is null then
      raise exception 'Connected CP6 Final-SKU reversal requires one Potongan';
    end if;
    perform pg_advisory_xact_lock(hashtextextended('CP6FLOW:'||v_group_id::text,0));
    select * into v_qc from erp.qc_inspections where id=v_qc_id for update;
    if v_qc.id is null then raise exception 'QC inspection not found'; end if;
    if v_qc.row_version<>p_expected_version then
      raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_qc.row_version;
    end if;
    perform erp.reverse_qc(v_qc.id,v_reason);
    select * into v_qc from erp.qc_inspections where id=v_qc.id;
    v_response:=jsonb_build_object(
      'action',v_action,'qc_inspection_id',v_qc.id,'status',v_qc.status,
      'row_version',v_qc.row_version,'history_deleted',false,
      'stock_effect','FG_AND_BS_REVERSED','hpp_effect','HPP_AND_GL_REBUILT'
    );
  end if;

  if v_action in('REVERSE_DELIVERY','REVERSE_RECEIPT','REVERSE_FINAL_SKU') then
    delete from erp.cp6_laundry_qc_execution_context
    where backend_pid=pg_backend_pid() and transaction_id=txid_current()
      and actor_key=erp._idempotency_actor_key() and action=v_action
      and client_request_id=p_client_request_id;
    if not found then raise exception 'CP6 reverse execution context cleanup failed'; end if;
  end if;
  if exists(
    select 1 from erp.cp6_laundry_qc_execution_context c
    where c.backend_pid=pg_backend_pid() and c.transaction_id=txid_current()
  ) then raise exception 'CP6 execution context leaked after action'; end if;
  v_response:=v_response||jsonb_build_object(
    'contract_version','CP6_V2620',
    'client_request_id',p_client_request_id,
    'committed',true
  );
  return erp._idempotency_complete(
    'cp6_laundry_qc_action_v1:'||lower(v_action),p_client_request_id,v_response
  );
end
$function$;
CREATE OR REPLACE FUNCTION erp.validate_laundry_receipt_line()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare
  v_sent integer;
  v_other integer;
  v_receipt_delivery uuid;
  v_line_delivery uuid;
  v_remaining integer;
  v_failed_context_count integer:=0;
  v_failed_qty bigint:=0;
  v_existing_failed_qty bigint;
begin
  select lr.delivery_id into v_receipt_delivery
  from erp.laundry_receipts lr where lr.id=new.receipt_id;
  select ldl.delivery_id,ldl.qty_sent_pcs into v_line_delivery,v_sent
  from erp.laundry_delivery_lines ldl where ldl.id=new.delivery_line_id;
  if v_sent is null then raise exception 'Laundry delivery line not found'; end if;
  if v_receipt_delivery is null or v_receipt_delivery<>v_line_delivery then
    raise exception 'Receipt and receipt line belong to different laundry deliveries';
  end if;
  select coalesce(sum(lrl.qty_good_received+lrl.qty_bs_laundry),0) into v_other
  from erp.laundry_receipt_lines lrl
  join erp.laundry_receipts lr on lr.id=lrl.receipt_id
  where lrl.delivery_line_id=new.delivery_line_id
    and lrl.id<>new.id and lr.status<>'REVERSED';
  if v_other+new.qty_good_received+new.qty_bs_laundry>v_sent then
    raise exception 'Cumulative laundry physical return exceeds quantity sent';
  end if;
  v_remaining:=v_sent-v_other-new.qty_good_received-new.qty_bs_laundry;
  if new.qty_stuck+new.qty_missing>v_remaining then
    raise exception 'STUCK + MISSING exceeds remaining unreturned quantity';
  end if;

  select count(distinct (c.backend_pid,c.transaction_id)),
         coalesce(sum(x.qty_attempted_pcs),0)::bigint
    into v_failed_context_count,v_failed_qty
  from erp.cp6_laundry_qc_execution_context c
  cross join lateral jsonb_to_recordset(c.payload->'lines')
    x(delivery_batch_size_line_id uuid,qty_attempted_pcs integer)
  where c.backend_pid=pg_backend_pid()
    and c.transaction_id=txid_current()
    and c.actor_key=erp._idempotency_actor_key()
    and c.action='POST_FAILED_WASH'
    and c.permission_key='production.laundry.post'
    and erp.has_permission(c.permission_key)
    and (c.payload->>'delivery_id')::uuid=v_receipt_delivery
    and (c.payload->>'wash_process_id')::uuid=new.actual_wash_process_id;

  if v_failed_context_count>0 then
    -- OW-08b (LAU-DEC04): the facade request that says the vendor rate is not known yet stores the attempt with no rate,
    -- no cost and cost status PENDING (never zero); every other zero-output rule of the attempt stays.
    if v_failed_context_count=1 and new.actual_rate_snapshot is null and exists(
      select 1 from erp.cp6_laundry_qc_execution_context c
      where c.backend_pid=pg_backend_pid() and c.transaction_id=txid_current()
        and c.actor_key=erp._idempotency_actor_key() and c.action='POST_FAILED_WASH'
        and c.permission_key='production.laundry.post' and erp.has_permission(c.permission_key)
        and (c.payload->>'delivery_id')::uuid=v_receipt_delivery
        and (c.payload->>'wash_process_id')::uuid=new.actual_wash_process_id
        and c.payload->>'price_status'='UNKNOWN') then
      if v_failed_qty<=0 or new.qty_good_received<>0 or new.qty_bs_laundry<>0
         or new.qty_stuck<>0 or new.qty_missing<>0 or new.actual_cost_status<>'PENDING' then
        raise exception 'Paid failed-wash cost requires one exact zero-output facade context';
      end if;
      new.actual_cost:=null;
      return new;
    end if;
    if v_failed_context_count<>1 or v_failed_qty<=0
       or new.qty_good_received<>0 or new.qty_bs_laundry<>0
       or new.qty_stuck<>0 or new.qty_missing<>0
       or new.actual_rate_snapshot is null or new.actual_rate_snapshot<0
       or new.actual_cost_status not in('PENDING','ESTIMATED') then
      raise exception 'Paid failed-wash cost requires one exact zero-output facade context';
    end if;
    new.actual_cost_status:='ESTIMATED';
    new.actual_cost:=round(v_failed_qty*new.actual_rate_snapshot,2);
    return new;
  end if;

  -- Invoice posting changes an existing attempt to FINAL; reversal restores
  -- its ESTIMATED snapshot. The original Good+BS formula would turn that
  -- restored service cost back into zero, so bind both transitions to the
  -- immutable attempt quantity instead of to physical output.
  select a.qty_attempted_pcs into v_existing_failed_qty
  from erp.laundry_failed_wash_attempts a
  where a.receipt_line_id=new.id;
  -- OW-08b: an attempt recorded with an unknown price leaves PENDING only through its recorded price
  -- (cp7_laundry_unknown_wash.prices_v1, set once by owner/admin); it is never billed or valued before that.
  if v_existing_failed_qty is not null and tg_op='UPDATE' and old.actual_cost_status='PENDING' and old.actual_rate_snapshot is null
     and not exists(select 1 from cp7_laundry_unknown_wash.prices_v1 p
       where p.receipt_line_id=new.id and p.price_status<>'UNKNOWN' and p.rate_per_pcs=new.actual_rate_snapshot
         and new.actual_cost_status='ESTIMATED') then
    raise exception 'CP7_FAILED_WASH_PRICE_UNKNOWN: harga cuci gagal ini belum diketahui; isi dulu di Produksi › Laundry › Harga & tagihan › Harga belum diketahui';
  end if;
  if v_existing_failed_qty is not null then
    if new.qty_good_received<>0 or new.qty_bs_laundry<>0
       or new.qty_stuck<>0 or new.qty_missing<>0
       or new.actual_rate_snapshot is null or new.actual_rate_snapshot<0 then
      raise exception 'Existing paid failed-wash cost lost its zero-output attempt lineage';
    end if;
    if new.actual_cost_status='FINAL' then
      if new.actual_cost is distinct from round(v_existing_failed_qty*new.actual_rate_snapshot,2) then
        raise exception 'Final failed-wash invoice cost must equal immutable attempt quantity times rate';
      end if;
      return new;
    end if;
    if new.actual_cost_status<>'ESTIMATED' then
      raise exception 'Existing paid failed-wash cost must remain ESTIMATED until an exact invoice finalizes it';
    end if;
    new.actual_cost:=round(v_existing_failed_qty*new.actual_rate_snapshot,2);
    return new;
  end if;

  -- Preserve every predecessor physical-receipt rule byte-for-behavior.
  if new.actual_cost_status='FINAL' and new.actual_cost is not null then
    return new;
  end if;
  -- A deferred shipment has no agreed price. The allocation's numeric zero is only its known subtotal.
  if exists(select 1 from erp.bf_laundry_delivery_sources_v1 bf
    where bf.delivery_line_id=new.delivery_line_id and bf.details_pending) then
    new.actual_rate_snapshot:=null;
    new.actual_cost:=null;
    new.actual_cost_status:='PENDING';
    return new;
  end if;
  -- BD: a receipt line of a priced delivery costs the exact shares of its sizes (erp.bd_allocate_receipt_v1), not qty x rate.
  if exists(select 1 from erp.bd_laundry_receipt_allocations_v1 a where a.receipt_line_id=new.id) then
    new.actual_cost:=(select sum(a.amount) from erp.bd_laundry_receipt_allocations_v1 a where a.receipt_line_id=new.id);
    new.actual_cost_status:='ESTIMATED';
    return new;
  end if;
  if new.actual_rate_snapshot is null then
    new.actual_cost:=null;
    if new.actual_cost_status='FINAL' then
      raise exception 'FINAL laundry cost requires actual_cost or actual_rate_snapshot';
    end if;
    new.actual_cost_status:='PENDING';
  else
    new.actual_cost:=(new.qty_good_received+new.qty_bs_laundry)*new.actual_rate_snapshot;
    if new.actual_cost_status='PENDING' then new.actual_cost_status:='ESTIMATED'; end if;
  end if;
  return new;
end
$function$;
CREATE OR REPLACE FUNCTION erp.guard_cp6_laundry_receipt_lineage_on_post_v2620()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare
  r record;
  v_prior bigint;
  v_line_count integer;
begin
  if not(old.status='DRAFT' and new.status='POSTED') then return new; end if;
  if exists(select 1 from erp.laundry_failed_wash_attempts a where a.receipt_id=new.id) then
    select a.* into r
    from erp.laundry_failed_wash_attempts a where a.receipt_id=new.id;
    if (select count(*) from erp.laundry_receipt_lines l where l.receipt_id=new.id)<>1 then
      raise exception 'Failed-wash receipt must contain exactly one canonical cost line';
    end if;
    if exists(
      select 1 from erp.laundry_receipt_batch_size_lines x
      join erp.laundry_receipt_lines l on l.id=x.receipt_line_id
      where l.receipt_id=new.id
    ) then
      raise exception 'Failed-wash service cost must not create physical Good/BS receipt facts';
    end if;
    if exists(
      select 1 from erp.laundry_receipt_lines l
      where l.receipt_id=new.id and(
        l.id<>r.receipt_line_id or l.qty_good_received<>0 or l.qty_bs_laundry<>0
        or l.qty_stuck<>0 or l.qty_missing<>0
        or l.actual_wash_process_id is null
        -- OW-08b (LAU-DEC04): an attempt this stage registered with an unknown vendor price posts with exactly no rate,
        -- no cost and status PENDING (never zero); every other attempt keeps the exact zero-output estimate below.
        or (case when exists(select 1 from cp7_laundry_unknown_wash.prices_v1 ow
            where ow.attempt_id=r.id and ow.receipt_line_id=l.id and ow.price_status='UNKNOWN')
          then l.actual_rate_snapshot is not null or l.actual_cost is not null or l.actual_cost_status<>'PENDING'
          else l.actual_rate_snapshot is null or l.actual_rate_snapshot<0
        or l.actual_cost_status<>'ESTIMATED'
        or l.actual_cost is distinct from round(r.qty_attempted_pcs*l.actual_rate_snapshot,2) end)
      )
    ) then
      raise exception 'Failed-wash canonical cost line is not an exact zero-output estimate';
    end if;
    if (select coalesce(sum(x.qty_attempted_pcs),0)
        from erp.laundry_failed_wash_batch_size_lines x
        where x.attempt_id=r.id)<>r.qty_attempted_pcs then
      raise exception 'Failed-wash attempted size total does not equal its canonical cost quantity';
    end if;
    if exists(
      select 1
      from erp.laundry_failed_wash_batch_size_lines x
      join erp.laundry_delivery_batch_size_lines s
        on s.id=x.delivery_batch_size_line_id
      join erp.laundry_delivery_lines dl on dl.id=s.delivery_line_id
      where x.attempt_id=r.id and(
        dl.delivery_id<>r.delivery_id or x.size_id<>s.size_id
        or x.qty_attempted_pcs>s.qty_sent_pcs
      )
    ) then
      raise exception 'Failed-wash attempted size facts do not belong to the exact delivery capacity';
    end if;
    if r.custody_outcome='RETRY_AT_VENDOR' then
      if r.return_wip_event_id is not null
         or not exists(select 1 from erp.laundry_deliveries d
           where d.id=r.delivery_id and d.status in('SENT','PARTIAL_RETURN')) then
        raise exception 'Retry-at-vendor must preserve active Laundry custody without a WIP return';
      end if;
    else
      if r.return_wip_event_id is null
         or not exists(
           select 1
           from erp.wip_stage_events rv
           join erp.wip_stage_events src
             on src.id=rv.source_id and src.source_type='LAUNDRY_DELIVERY_LINE'
           join erp.laundry_delivery_lines dl
             on dl.id=src.source_id and dl.delivery_id=r.delivery_id
           join erp.laundry_deliveries d on d.id=dl.delivery_id
           where rv.id=r.return_wip_event_id
             and rv.source_type='CP6_LAUNDRY_DELIVERY_WIP_REVERSAL'
             and rv.po_id=d.po_id and rv.cutting_group_id=dl.cutting_group_id
             and rv.stage_from='LAUNDRY' and rv.stage_to='SEWING'
             and rv.qty_pcs=r.qty_attempted_pcs
             and d.status='REVERSED'
         )
         or (select count(*) from erp.laundry_failed_wash_batch_size_lines x
             where x.attempt_id=r.id)<>
            (select count(*) from erp.laundry_delivery_batch_size_lines s
             join erp.laundry_delivery_lines dl on dl.id=s.delivery_line_id
             where dl.delivery_id=r.delivery_id)
         or exists(
           select 1 from erp.laundry_delivery_batch_size_lines s
           join erp.laundry_delivery_lines dl on dl.id=s.delivery_line_id
           left join erp.laundry_failed_wash_batch_size_lines x
             on x.attempt_id=r.id and x.delivery_batch_size_line_id=s.id
           where dl.delivery_id=r.delivery_id
             and x.qty_attempted_pcs is distinct from s.qty_sent_pcs
         ) then
        raise exception 'Return-unprocessed must return the entire exact delivery and bind one immutable WIP inverse';
      end if;
    end if;
    return new;
  end if;
  if not exists(
    select 1 from erp.laundry_receipt_batch_size_lines x
    join erp.laundry_receipt_lines l on l.id=x.receipt_line_id
    where l.receipt_id=new.id
  ) then
    raise exception 'CP6 posted Laundry receipt requires immutable delivery batch/size lineage';
  end if;
  select count(*) into v_line_count
  from erp.laundry_receipt_lines where receipt_id=new.id;
  if v_line_count<>1 then
    raise exception 'CP6 Laundry receipt must contain exactly one authoritative delivery line';
  end if;
  if exists(
    select 1 from erp.laundry_receipt_lines l
    left join(
      select receipt_line_id,
        sum(qty_good_received)::bigint good_qty,
        sum(qty_bs_laundry)::bigint bs_qty
      from erp.laundry_receipt_batch_size_lines group by receipt_line_id
    ) x on x.receipt_line_id=l.id
    where l.receipt_id=new.id and(
      l.qty_good_received is distinct from coalesce(x.good_qty,0)
      or l.qty_bs_laundry is distinct from coalesce(x.bs_qty,0)
      or l.qty_stuck<>0 or l.qty_missing<>0
    )
  ) then
    raise exception 'CP6 receipt aggregate must equal immutable size facts; Stuck is derived from outstanding, never posted repeatedly';
  end if;
  for r in
    select x.delivery_batch_size_line_id,
      sum(x.qty_good_received+x.qty_bs_laundry)::bigint current_qty,
      max(s.qty_sent_pcs)::bigint sent_qty
    from erp.laundry_receipt_batch_size_lines x
    join erp.laundry_delivery_batch_size_lines s on s.id=x.delivery_batch_size_line_id
    join erp.laundry_receipt_lines l on l.id=x.receipt_line_id
    where l.receipt_id=new.id
    group by x.delivery_batch_size_line_id
    order by x.delivery_batch_size_line_id
  loop
    perform 1 from erp.laundry_delivery_batch_size_lines s
    where s.id=r.delivery_batch_size_line_id for update;
    select coalesce(sum(x.qty_good_received+x.qty_bs_laundry),0)::bigint into v_prior
    from erp.laundry_receipt_batch_size_lines x
    join erp.laundry_receipt_lines l on l.id=x.receipt_line_id
    join erp.laundry_receipts h on h.id=l.receipt_id
    where x.delivery_batch_size_line_id=r.delivery_batch_size_line_id
      and h.id<>new.id and h.status='POSTED';
    if v_prior+r.current_qty>r.sent_qty then
      raise exception 'Laundry physical return exceeds immutable batch/size sent quantity. Sent %, prior %, this receipt %',
        r.sent_qty,v_prior,r.current_qty;
    end if;
  end loop;
  return new;
end
$function$;
CREATE OR REPLACE FUNCTION erp.period_blockers_v1(p_through date, p_window_from date)
 RETURNS TABLE(family text, code text, severity text, scope text, impact_date date, reference jsonb, reason text)
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO ''
AS $function$
-- One engine for close, preview and report confidence (S06/B04).
-- Open items (recost, laundry price, payroll due, dated integrity) use every fact dated on or before p_through.
-- Completeness (attendance cells) uses the window [p_window_from, p_through]; a null start means unbounded. Callers
-- pass erp.period_completeness_from_v1(), the first date this engine was responsible for, so a closed date inside
-- the engine's era is re-checked after a later correction (P-01). Before that start only cells that once had a
-- posted record and lost it (reversed, not replaced) are reported.
-- Stock history follows the posting guards' own order (P-04). A current-state check whose defect is scoped by a
-- dated detector is reported as INFO once the detector confirms it; every other failing current-state check blocks
-- every date and names its class (P-03). Unknown check names block (fail closed).
declare
  v_end timestamptz := ((p_through + 1)::timestamp AT TIME ZONE 'Asia/Jakarta');
  v_fg jsonb;
  v_material jsonb;
  v_fg_confirmed boolean;
  v_material_confirmed boolean;
begin
  if p_through is null then raise exception 'PERIOD_BLOCKERS_DATE_REQUIRED'; end if;

  -- RECOST: open queue rows whose PO has a dated fact on or before the date.
  return query
  select 'RECOST'::text,
    case when q.status='FAILED' and q.attempt_count>=3 then 'RECOST_FAILED_EXHAUSTED' else 'RECOST_PENDING' end,
    case when q.status='FAILED' and q.attempt_count>=3 then 'CRITICAL' else 'RECALC' end,
    'AS_OF'::text, f.first_date,
    jsonb_build_object('queue_id',q.id,'po_id',q.entity_id,'po_number',po.po_number,'status',q.status,
      'attempt_count',q.attempt_count,'recalc_from',q.recalc_from,'facts',f.facts),
    format('Hitung ulang biaya PO %s belum selesai (status %s, percobaan %s); PO ini punya fakta pada atau sebelum %s.',
      coalesce(po.po_number,q.entity_id::text),q.status,q.attempt_count,p_through)
  from erp.cost_recalc_queue q
  left join erp.production_orders po on po.id=q.entity_id
  cross join lateral (
    select min(x.d) first_date, jsonb_agg(distinct x.k) facts from (
      select 'RECALC_FROM' k, erp._cp3_business_date(q.recalc_from) d where q.recalc_from is not null and q.recalc_from<v_end
      union all
      select 'CUTTING_MATERIAL', min(erp._cp3_business_date(m.physical_at))
        from erp.material_stock_movements m join erp.cutting_groups cg on cg.id=m.source_id
        where m.source_type in('CUTTING_GROUP','CUTTING_GROUP_RETURN') and cg.po_id=q.entity_id and m.physical_at<v_end
        having count(*)>0
      union all
      select 'CONTRACTOR_MATERIAL', min(erp._cp3_business_date(m.physical_at))
        from erp.material_stock_movements m
        join erp.contractor_material_issue_items ii on ii.id=m.source_id
        join erp.contractor_material_issues cmi on cmi.id=ii.issue_id
        where m.source_type='CONTRACTOR_MATERIAL_ISSUE_ITEM' and cmi.po_id=q.entity_id and m.physical_at<v_end
        having count(*)>0
      union all
      select 'FG_LOT', min(erp._cp3_business_date(fl.produced_at))
        from erp.fg_lots fl where fl.po_id=q.entity_id and fl.produced_at<v_end having count(*)>0
      union all
      select 'PO_JOURNAL', min(je.economic_date)
        from erp.journal_lines jl join erp.journal_entries je on je.id=jl.journal_entry_id
        where jl.po_id=q.entity_id and je.status in('POSTED','REVERSED') and je.economic_date<=p_through
        having count(*)>0
    ) x
  ) f
  where q.entity_type='PO' and q.status in('PENDING','RUNNING','FAILED') and f.first_date is not null;

  -- A PO queue row whose PO has no dated fact at all cannot be scoped to a date: it applies to every date.
  return query
  select 'RECOST'::text,'RECOST_UNSCOPED_ENTITY'::text,
    case when q.status='FAILED' and q.attempt_count>=3 then 'CRITICAL' else 'RECALC' end,'CURRENT_STATE'::text,null::date,
    jsonb_build_object('queue_id',q.id,'entity_type',q.entity_type,'entity_id',q.entity_id,'status',q.status,'attempt_count',q.attempt_count),
    format('Antrean hitung ulang PO %s belum selesai dan PO ini belum punya fakta bertanggal; berlaku untuk semua tanggal.',q.entity_id)
  from erp.cost_recalc_queue q
  where q.entity_type='PO' and q.status in('PENDING','RUNNING','FAILED') and q.recalc_from is null
    and not exists(select 1 from erp.material_stock_movements m join erp.cutting_groups cg on cg.id=m.source_id
      where m.source_type in('CUTTING_GROUP','CUTTING_GROUP_RETURN') and cg.po_id=q.entity_id)
    and not exists(select 1 from erp.material_stock_movements m join erp.contractor_material_issue_items ii on ii.id=m.source_id
      join erp.contractor_material_issues cmi on cmi.id=ii.issue_id
      where m.source_type='CONTRACTOR_MATERIAL_ISSUE_ITEM' and cmi.po_id=q.entity_id)
    and not exists(select 1 from erp.fg_lots fl where fl.po_id=q.entity_id)
    and not exists(select 1 from erp.journal_lines jl join erp.journal_entries je on je.id=jl.journal_entry_id
      where jl.po_id=q.entity_id and je.status in('POSTED','REVERSED'));

  -- A queue row for another entity type cannot be scoped to a date: conservative, every date.
  return query
  select 'RECOST'::text,'RECOST_UNSCOPED_ENTITY'::text,'CRITICAL'::text,'CURRENT_STATE'::text,null::date,
    jsonb_build_object('queue_id',q.id,'entity_type',q.entity_type,'entity_id',q.entity_id,'status',q.status),
    format('Antrean hitung ulang %s %s belum selesai dan tidak dapat dibatasi ke tanggal.',q.entity_type,q.entity_id)
  from erp.cost_recalc_queue q
  where q.entity_type<>'PO' and q.status in('PENDING','RUNNING','FAILED');

  -- FG history per SKU and per lot, in the order the posting guard uses (physical_at, system_created_at, id): every
  -- prefix, not the net per instant (P-04). Computed over the whole history once; a key blocks the dates from its
  -- first negative instant.
  select coalesce(jsonb_agg(z.k),'[]'::jsonb) into v_fg from (
    select jsonb_build_object('level',s.lvl,'product_id',min(s.product_id::text),'lot_id',s.lot_id,
      'location_id',s.location_id,'quality_grade',s.quality_grade,
      'first_negative_at',min(s.physical_at) filter(where s.balance<0),
      'lowest_qty',min(s.balance)) k
    from (
      select 'SKU'::text lvl,m.product_id,null::uuid lot_id,m.location_id,m.quality_grade,m.physical_at,
        sum(m.qty_signed) over(partition by m.product_id,m.location_id,m.quality_grade
          order by m.physical_at,m.system_created_at,m.id rows unbounded preceding) balance
      from erp.fg_stock_movements m
      union all
      select 'LOT'::text,m.product_id,m.lot_id,m.location_id,m.quality_grade,m.physical_at,
        sum(m.qty_signed) over(partition by m.lot_id,m.location_id,m.quality_grade
          order by m.physical_at,m.system_created_at,m.id rows unbounded preceding)
      from erp.fg_stock_movements m where m.lot_id is not null
    ) s
    group by s.lvl,case when s.lvl='SKU' then s.product_id end,s.lot_id,s.location_id,s.quality_grade
    having bool_or(s.balance<0)
  ) z;

  return query
  select 'INTEGRITY'::text,'FG_QTY_NEGATIVE_ASOF'::text,'CRITICAL'::text,'AS_OF'::text,
    erp._cp3_business_date((k->>'first_negative_at')::timestamptz),k,
    format('Stok barang jadi (%s) negatif sejak %s untuk produk %s di lokasi %s.',
      k->>'level',k->>'first_negative_at',k->>'product_id',k->>'location_id')
  from jsonb_array_elements(v_fg) k
  where (k->>'first_negative_at')::timestamptz<v_end;

  -- Material history on the cost engine's effective history and its exact order (reversed pairs excluded, a
  -- transfer-in ordered right after its transfer-out), per material, location and roll.
  select coalesce(jsonb_agg(z.k),'[]'::jsonb) into v_material from (
    with active as (
      select m.*,row_number() over(partition by m.material_id,m.source_id,m.roll_id,m.physical_at,
          abs(m.qty_signed),m.movement_type order by m.system_created_at,m.id) ordinal
      from erp.material_stock_movements m
      where m.source_type='MATERIAL_TRANSFER' and m.reversal_of_id is null
        and not exists(select 1 from erp.material_stock_movements rv where rv.reversal_of_id=m.id)
    ), pairs as (
      select i.id incoming,o.id outgoing,o.system_created_at out_created
      from active i join active o on o.material_id=i.material_id and o.source_id=i.source_id
        and o.roll_id is not distinct from i.roll_id and o.physical_at=i.physical_at
        and o.qty_signed=-i.qty_signed and o.ordinal=i.ordinal
        and o.movement_type='TRANSFER_OUT' and o.qty_signed<0
      where i.movement_type='TRANSFER_IN' and i.qty_signed>0
        and (o.physical_at,o.system_created_at,o.id)<(i.physical_at,i.system_created_at,i.id)
        and o.location_id<>i.location_id
    ), history as (
      select m.material_id,m.location_id,m.roll_id,m.physical_at,
        sum(m.qty_signed) over(partition by m.material_id,m.location_id,m.roll_id
          order by m.physical_at,coalesce(p.out_created,m.system_created_at),coalesce(p.outgoing,m.id),
            (p.outgoing is not null) rows unbounded preceding) balance
      from erp.material_stock_movements m
      left join pairs p on p.incoming=m.id
      where m.reversal_of_id is null
        and not exists(select 1 from erp.material_stock_movements rv where rv.reversal_of_id=m.id)
    )
    select jsonb_build_object('material_id',h.material_id,'location_id',h.location_id,'roll_id',h.roll_id,
      'first_negative_at',min(h.physical_at) filter(where h.balance<0),'lowest_qty',min(h.balance)) k
    from history h
    group by h.material_id,h.location_id,h.roll_id
    having bool_or(h.balance<0)
  ) z;

  return query
  select 'INTEGRITY'::text,'MATERIAL_QTY_NEGATIVE_ASOF'::text,'CRITICAL'::text,'AS_OF'::text,
    erp._cp3_business_date((k->>'first_negative_at')::timestamptz),k,
    format('Stok bahan negatif sejak %s untuk bahan %s.',k->>'first_negative_at',k->>'material_id')
  from jsonb_array_elements(v_material) k
  where (k->>'first_negative_at')::timestamptz<v_end;

  -- Per-key confirmation (P-03): a current-state check scoped by a detector is INFO only when every key failing it
  -- now is a key the detector found; an empty or partial match blocks every date.
  select count(*)>0 and coalesce(bool_and(exists(select 1 from jsonb_array_elements(v_fg) x where x->>'level'='SKU'
      and x->>'product_id'=k.product_id::text and x->>'location_id' is not distinct from k.location_id::text
      and x->>'quality_grade' is not distinct from k.quality_grade)),false)
  into v_fg_confirmed
  from (select m.product_id,m.location_id,m.quality_grade from erp.fg_stock_movements m
        group by m.product_id,m.location_id,m.quality_grade having sum(m.qty_signed)<0) k;
  select count(*)>0 and coalesce(bool_and(exists(select 1 from jsonb_array_elements(v_material) x
      where x->>'material_id'=k.material_id::text and x->>'location_id' is not distinct from k.location_id::text
      and x->>'roll_id' is not distinct from k.roll_id::text)),false)
  into v_material_confirmed
  from (select m.material_id,m.location_id,m.roll_id from erp.material_stock_movements m
        group by m.material_id,m.location_id,m.roll_id having sum(m.qty_signed)<-0.000001) k;

  -- INTEGRITY (current state), classified (P-03). Queue checks are handled per date by RECOST above.
  return query
  with failing as (
    select distinct on (c.check_name) c.check_name,c.src,c.issue_count,c.details from (
      select 'run_v268_financial_report_checks' src,r.check_name,r.severity,r.issue_count,r.details from erp.run_v268_financial_report_checks() r
      union all
      select 'run_v267_financial_truth_checks',r.check_name,r.severity,r.issue_count,r.details from erp.run_v267_financial_truth_checks() r
      union all
      select 'run_integrity_checks',r.check_name,r.severity,r.issue_count,r.details from erp.run_integrity_checks() r
    ) c
    where c.issue_count>0 and c.severity in('CRITICAL','ERROR')
      and c.check_name not in('V268_COST_RECALC_EXHAUSTED','V268_COST_RECALC_PENDING','STALE_RECOST_QUEUE','FAILED_RECOST_QUEUE')
    order by c.check_name,c.src
  ), registry(check_name,check_class,dated_by) as (
    select * from erp.period_integrity_check_registry_v1()
  ), classified as (
    select f.*,coalesce(r.check_class,'UNCLASSIFIED') check_class,r.dated_by,
      case r.dated_by when 'FG_QTY_NEGATIVE_ASOF' then v_fg_confirmed
                      when 'MATERIAL_QTY_NEGATIVE_ASOF' then v_material_confirmed
                      else false end confirmed
    from failing f left join registry r on r.check_name=f.check_name
  )
  select 'INTEGRITY'::text,c.check_name,
    case when c.check_class='DATED_EQUIVALENT' and c.confirmed then 'INFO' else 'CRITICAL' end,
    'CURRENT_STATE'::text,null::date,
    jsonb_build_object('check_name',c.check_name,'issue_count',c.issue_count,'source',c.src,'class',c.check_class,
      'dated_by',c.dated_by,'dated_detector_confirmed',c.confirmed,
      'date_policy',case when c.check_class='DATED_EQUIVALENT' and c.confirmed then 'SCOPED_BY_DATED_DETECTOR'
                         else 'BLOCKS_EVERY_DATE' end),
    case when c.check_class='DATED_EQUIVALENT' and c.confirmed
      then format('%s: dibatasi per tanggal oleh %s.',coalesce(c.details,c.check_name),c.dated_by)
      else coalesce(c.details,c.check_name) end
  from classified c;

  -- INTEGRITY (dated): GL inventory balance negative at any balance date on or before the date.
  return query
  select 'INTEGRITY'::text,'GL_INVENTORY_NEGATIVE_ASOF'::text,'CRITICAL'::text,'AS_OF'::text,min(g.balance_date),
    jsonb_build_object('account',g.mapping_key,'first_negative_date',min(g.balance_date),'lowest_balance',min(g.balance)),
    format('Saldo buku %s negatif sejak %s (terendah %s).',g.mapping_key,min(g.balance_date),min(g.balance))
  from (
    select k.mapping_key,a.balance_date,
      sum(a.debit_total-a.credit_total) over(partition by a.account_id order by a.balance_date) balance
    from erp.account_daily_balances a
    join (values('MATERIAL_INVENTORY'),('WIP'),('FG_INVENTORY')) k(mapping_key) on a.account_id=erp.account_id(k.mapping_key)
    where a.balance_date<=p_through
  ) g
  where g.balance<-0.005
  group by g.mapping_key;

  -- ATTENDANCE (window): eligible worker-days without a current posted record (owner: existing rule, OFF recorded).
  return query
  select 'ATTENDANCE'::text,'ATTENDANCE_CELL_MISSING'::text,'POLICY'::text,'WINDOW'::text,min(x.work_day),
    jsonb_build_object('contractor_id',x.contractor_id,'contractor_name',x.contractor_name,'worker_id',x.worker_id,
      'worker_name',x.worker_name,'missing_days',count(*),'first_missing',min(x.work_day),'last_missing',max(x.work_day),
      'sample_days',(array_agg(x.work_day order by x.work_day))[1:10],'window_from',p_window_from),
    format('Absensi %s (%s) kosong %s hari antara %s dan %s; hari libur dicatat OFF.',
      x.worker_name,x.contractor_name,count(*),min(x.work_day),max(x.work_day))
  from (
    select w.contractor_id,c.contractor_name,w.id worker_id,w.worker_name,gs.d::date as work_day
    from erp.contractor_workers w
    join erp.contractors c on c.id=w.contractor_id
    join erp.worker_employment_periods e on e.worker_id=w.id
    cross join lateral generate_series(
      greatest(e.started_on,coalesce(p_window_from,e.started_on))::timestamp,
      least(coalesce(e.ended_on,p_through),p_through)::timestamp,interval '1 day') gs(d)
    where c.attendance_required and w.pay_scheme in('DAILY','HYBRID')
      and not exists(select 1 from erp.attendance_records a
        where a.worker_id=w.id and a.attendance_date=gs.d::date and coalesce(a.record_lifecycle,'POSTED')='POSTED')
  ) x
  group by x.contractor_id,x.contractor_name,x.worker_id,x.worker_name;

  -- ATTENDANCE (before the window): an eligible worker-day that had a posted record which was later reversed and
  -- never replaced. The date was complete when it was accepted; a later change removed it (P-01).
  return query
  select 'ATTENDANCE'::text,'ATTENDANCE_CELL_REVERSED_UNREPLACED'::text,'POLICY'::text,'AS_OF'::text,min(x.work_day),
    jsonb_build_object('contractor_id',x.contractor_id,'contractor_name',x.contractor_name,'worker_id',x.worker_id,
      'worker_name',x.worker_name,'missing_days',count(*),'first_missing',min(x.work_day),'last_missing',max(x.work_day),
      'sample_days',(array_agg(x.work_day order by x.work_day))[1:10],'window_from',p_window_from),
    format('Absensi %s (%s) pada %s hari antara %s dan %s sudah dibatalkan dan belum dicatat ulang.',
      x.worker_name,x.contractor_name,count(*),min(x.work_day),max(x.work_day))
  from (
    select distinct w.contractor_id,c.contractor_name,w.id worker_id,w.worker_name,r.attendance_date work_day
    from erp.attendance_records r
    join erp.contractor_workers w on w.id=r.worker_id
    join erp.contractors c on c.id=w.contractor_id
    where p_window_from is not null and r.attendance_date<p_window_from and r.attendance_date<=p_through
      and r.record_lifecycle='REVERSED'
      and c.attendance_required and w.pay_scheme in('DAILY','HYBRID')
      and exists(select 1 from erp.worker_employment_periods e where e.worker_id=w.id
        and r.attendance_date between e.started_on and coalesce(e.ended_on,r.attendance_date))
      and not exists(select 1 from erp.attendance_records a
        where a.worker_id=w.id and a.attendance_date=r.attendance_date and coalesce(a.record_lifecycle,'POSTED')='POSTED')
  ) x
  group by x.contractor_id,x.contractor_name,x.worker_id,x.worker_name;

  -- PAYROLL: payroll due on or before the date that is not approved (owner: labour recognised at period_end).
  return query
  select 'PAYROLL'::text,'PAYROLL_NOT_APPROVED'::text,'POLICY'::text,'AS_OF'::text,ps.period_end,
    jsonb_build_object('payroll_id',ps.id,'payroll_number',ps.payroll_number,'contractor_id',ps.contractor_id,
      'period_start',ps.period_start,'period_end',ps.period_end,'status',ps.status),
    format('Payroll %s (%s s/d %s) masih %s; belum disetujui.',ps.payroll_number,ps.period_start,ps.period_end,ps.status)
  from erp.payroll_settlements ps
  where ps.status in('DRAFT','CALCULATED','REVIEW') and ps.period_end<=p_through;

  -- PAYROLL: paid attendance on or before the date that no non-reversed payroll has taken (linkage, not date range).
  return query
  select 'PAYROLL'::text,'PAYROLL_ATTENDANCE_UNCOVERED'::text,'POLICY'::text,'AS_OF'::text,min(ar.attendance_date),
    jsonb_build_object('contractor_id',ar.contractor_id,'worker_id',ar.worker_id,'worker_name',w.worker_name,
      'records',count(*),'first_date',min(ar.attendance_date),'last_date',max(ar.attendance_date)),
    format('Absensi %s: %s hari berbayar antara %s dan %s belum masuk payroll.',w.worker_name,count(*),min(ar.attendance_date),max(ar.attendance_date))
  from erp.attendance_records ar
  join erp.contractor_workers w on w.id=ar.worker_id
  join erp.contractors c on c.id=ar.contractor_id
  where ar.attendance_date<=p_through and coalesce(ar.record_lifecycle,'POSTED')='POSTED'
    and ar.paid_fraction>0 and w.pay_scheme in('DAILY','HYBRID') and c.attendance_required
    and not exists(select 1 from erp.payroll_attendance_items pai join erp.payroll_settlements ps on ps.id=pai.payroll_id
      where pai.attendance_record_id=ar.id and ps.status<>'REVERSED')
  group by ar.contractor_id,ar.worker_id,w.worker_name;

  -- PAYROLL: eligible piece or rework work on or before the date that no non-reversed payroll has taken.
  return query
  select 'PAYROLL'::text,'PAYROLL_WORK_UNCOVERED'::text,'POLICY'::text,'AS_OF'::text,
    min(erp._cp3_business_date(e.eligible_at)),
    jsonb_build_object('contractor_id',e.contractor_id,'lines',count(*),'remaining_qty',sum(e.remaining_qty),
      'remaining_amount',sum(e.remaining_amount),'first_eligible_at',min(e.eligible_at)),
    format('Hasil kerja kontraktor %s: %s baris (%s pcs) pada atau sebelum %s belum masuk payroll.',
      e.contractor_id,count(*),sum(e.remaining_qty),p_through)
  from erp.v_payroll_eligible_work_lines e
  where e.eligible_at<v_end and e.remaining_qty>0
  group by e.contractor_id;

  -- LAUNDRY: sent quantity still costed at an unknown (null) delivery rate on or before the date.
  return query
  select 'LAUNDRY'::text,'LAUNDRY_PRICE_UNKNOWN'::text,'POLICY'::text,'AS_OF'::text,
    erp._cp3_business_date(ld.physical_at),
    jsonb_build_object('delivery_id',ld.id,'delivery_number',ld.delivery_number,'delivery_line_id',ldl.id,
      'po_id',ld.po_id,'uncosted_qty',greatest(ldl.qty_sent_pcs-coalesce(rc.costed_qty,0),0)),
    format('Harga laundry kiriman %s belum diketahui untuk %s pcs; isi estimasi owner.',
      ld.delivery_number,greatest(ldl.qty_sent_pcs-coalesce(rc.costed_qty,0),0))
  from erp.laundry_delivery_lines ldl
  join erp.laundry_deliveries ld on ld.id=ldl.delivery_id
  left join lateral (select sum(lrl.qty_good_received+lrl.qty_bs_laundry) costed_qty
    from erp.laundry_receipt_lines lrl join erp.laundry_receipts lr on lr.id=lrl.receipt_id
    where lrl.delivery_line_id=ldl.id and lr.status='POSTED'
      and (lrl.actual_cost_status in('ESTIMATED','FINAL')
        or (lrl.actual_cost_status='PENDING' and lr.physical_at<v_end and exists(
          select 1 from erp.bf_laundry_delivery_sources_v1 bf
          where bf.delivery_line_id=lrl.delivery_line_id and bf.details_pending)))) rc on true
  where ld.status not in('DRAFT','REVERSED') and ldl.estimated_rate_snapshot is null
    and ld.physical_at<v_end and ldl.qty_sent_pcs-coalesce(rc.costed_qty,0)>0;

  -- BD (LAU-05b, LAU-T12): a component price of a priced delivery still unknown on or before the date, reported here when
  -- LAUNDRY_PRICE_UNKNOWN does not (every piece already returned and costed at the known part only).
  return query
  select 'LAUNDRY'::text,'BD_LAUNDRY_COMPONENT_PRICE_UNKNOWN'::text,'POLICY'::text,'AS_OF'::text,
    erp._cp3_business_date(ld.physical_at),
    jsonb_build_object('delivery_id',ld.id,'delivery_number',ld.delivery_number,'delivery_line_id',bp.delivery_line_id,'po_id',ld.po_id,
      'unknown_charges',(select count(*) from erp.bd_laundry_charge_lines_v1 c where c.delivery_line_id=bp.delivery_line_id and c.rate_status='UNKNOWN')),
    case when exists(select 1 from erp.bf_laundry_delivery_sources_v1 bf
                     where bf.delivery_line_id=bp.delivery_line_id and bf.details_pending)
      then format('Harga laundry kiriman %s belum diketahui; lengkapi kontra bon.',ld.delivery_number)
      else format('Harga komponen laundry kiriman %s belum diketahui; isi harga komponen di halaman harga laundry.',ld.delivery_number)
    end
  from erp.bd_laundry_priced_lines_v1 bp
  join erp.laundry_delivery_lines ldl on ldl.id=bp.delivery_line_id
  join erp.laundry_deliveries ld on ld.id=bp.delivery_id
  left join lateral (select sum(lrl.qty_good_received+lrl.qty_bs_laundry) costed_qty
    from erp.laundry_receipt_lines lrl join erp.laundry_receipts lr on lr.id=lrl.receipt_id
    where lrl.delivery_line_id=ldl.id and lr.status='POSTED'
      and (lrl.actual_cost_status in('ESTIMATED','FINAL')
        or (lrl.actual_cost_status='PENDING' and lr.physical_at<v_end and exists(
          select 1 from erp.bf_laundry_delivery_sources_v1 bf
          where bf.delivery_line_id=lrl.delivery_line_id and bf.details_pending)))) rc on true
  where not bp.total_complete and not erp.bf_delivery_invoiced_v1(bp.delivery_line_id,p_through) and ld.status not in('DRAFT','REVERSED') and ld.physical_at<v_end
    and not(ldl.estimated_rate_snapshot is null and ldl.qty_sent_pcs-coalesce(rc.costed_qty,0)>0);

  -- BD (ALL-W05): laundry work returned before cutover whose value is still unknown (no estimate, not fully billed).
  return query
  select 'LAUNDRY'::text,'BD_OPENING_LAUNDRY_PRICE_UNKNOWN'::text,'POLICY'::text,'AS_OF'::text,u.receipt_date,
    jsonb_build_object('opening_uninvoiced_id',u.id,'document_number',u.document_number,'vendor_id',u.vendor_id,'category',u.category,'qty',u.qty),
    format('Nilai laundry saldo awal %s (%s) belum diketahui; isi estimasi atau posting invoice vendornya.',u.document_number,u.category)
  from erp.bd_opening_laundry_uninvoiced_v1 u
  where u.estimated_amount is null and u.receipt_date<=p_through and not erp.bd_opening_invoiced_v1(u.id);

  return query
  select 'LAUNDRY'::text,'BE_REDYE_PRICE_UNKNOWN'::text,'POLICY'::text,'AS_OF'::text,erp._cp3_business_date(s.sent_at),
    jsonb_build_object('rework_service_id',s.id,'vendor_id',s.vendor_id,'po_id',s.po_id),
    'Harga jasa celup ulang belum diketahui; isi harga sumber sebelum tutup buku.'::text
  from erp.be_redye_services_v1 s join erp.rework_orders r on r.id=s.id
  where r.status<>'CANCELLED' and s.sent_at<v_end and erp.be_redye_rate_v1(s.id) is null;

  -- LAUNDRY: a delivery rate that is not a finite non-negative number is not a known price (P-02).
  return query
  select 'LAUNDRY'::text,'LAUNDRY_PRICE_INVALID'::text,'CRITICAL'::text,'AS_OF'::text,
    erp._cp3_business_date(ld.physical_at),
    jsonb_build_object('delivery_id',ld.id,'delivery_number',ld.delivery_number,'delivery_line_id',ldl.id,
      'po_id',ld.po_id,'rate',ldl.estimated_rate_snapshot::text),
    format('Harga laundry kiriman %s tidak valid (%s); harga harus angka hingga dan tidak negatif.',
      ld.delivery_number,ldl.estimated_rate_snapshot::text)
  from erp.laundry_delivery_lines ldl
  join erp.laundry_deliveries ld on ld.id=ldl.delivery_id
  where ld.status not in('DRAFT','REVERSED') and ld.physical_at<v_end
    and (ldl.estimated_rate_snapshot='NaN'::numeric or ldl.estimated_rate_snapshot<0);

  -- OW-07 (cp7_hpp_close): pocket fabric and attendance cost not yet divided into PO HPP.
  return query select * from cp7_attendance_choice.blockers_v1(p_through);

  -- OW-08b (cp7_laundry_unknown_wash): a failed wash recorded with an unknown vendor price (LAU-DEC04: never zero, HPP not
  -- final, close waits for the price) and the state detector of those attempts.
  return query select * from cp7_laundry_unknown_wash.blockers_v1(p_through);

  -- GRNI: owner allows close with an estimate; reported, never blocking.
  return query
  select 'GRNI'::text,'GRNI_ESTIMATE_OPEN'::text,'INFO'::text,'CURRENT_STATE'::text,
    erp._cp3_business_date(min(g.physical_at)),
    jsonb_build_object('receipts',count(*),'estimated_amount',sum(g.grni_estimated_amount)),
    format('%s penerimaan bahan masih memakai estimasi GRNI (total %s); boleh ditutup dengan estimasi.',count(*),sum(g.grni_estimated_amount))
  from erp.v_material_grni_aging g
  where g.physical_at<v_end
  having count(*)>0;
end
$function$;
CREATE OR REPLACE FUNCTION erp.rebuild_po_hpp(p_po_id uuid, p_reason text DEFAULT 'Recalculate HPP'::text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  v_material numeric(24,6):=0;v_opening_cost numeric(24,6):=0;
  v_material_allocated numeric(24,6):=0;
  v_contractor_material numeric(24,6):=0;
  v_accessory numeric(24,6):=0;
  v_labor numeric(24,6):=0;
  v_commission numeric(24,6):=0;
  v_laundry numeric(24,6):=0;
  v_rework numeric(24,6):=0;
  v_other numeric(24,6):=0;
  v_pocket numeric(24,6):=0;v_pocket_allocated numeric(24,6):=0;v_lot_pocket numeric(24,6):=0;
  v_attendance_hpp numeric(24,6):=0;
  v_shared_attendance_hpp numeric(24,6):=0;
  v_shared_labor numeric(24,6):=0;
  v_shared_commission numeric(24,6):=0;
  v_shared_rework numeric(24,6):=0;
  v_shared_other numeric(24,6):=0;
  v_total_current numeric(24,6):=0;
  v_total_qty integer:=0;
  v_pending boolean:=false;
  r record;
  c record;
  v_old_id uuid;
  v_new_id uuid;
  v_version integer;
  v_lot_accessory numeric(24,6);
  v_lot_cost numeric(24,6);
  v_lot_material numeric(24,6);
  v_pool_material numeric(24,6);
  v_pool_qty numeric(24,6);
  v_batch_id uuid;
  v_state varchar(20);
  v_group_fg_qty numeric(24,6);
  v_group_labor numeric(24,6);
  v_group_commission numeric(24,6);
  v_group_laundry numeric(24,6);
  v_group_rework numeric(24,6);
  v_group_attendance_hpp numeric(24,6);
  v_lot_attendance_hpp numeric(24,6);
  v_lot_labor numeric(24,6);
  v_lot_commission numeric(24,6);
  v_lot_laundry numeric(24,6);
  v_lot_rework numeric(24,6);
  v_lot_other numeric(24,6);
  v_cp6_lineage boolean:=false;
  v_lot_cp6_receipt_laundry numeric(24,6):=0;
  v_lot_cp6_attempt_laundry numeric(24,6):=0;
  v_laundry_allocated numeric(24,6):=0;
  v_labor_allocated numeric(24,6):=0;
  v_commission_allocated numeric(24,6):=0;
  v_rework_allocated numeric(24,6):=0;
  v_attendance_allocated numeric(24,6):=0;
  v_po_source_qty numeric(24,6):=0;
begin
  perform erp.require_internal();
  perform erp.pocket_period_lock_v1();
  select coalesce(sum(erp.pocket_period_amount_v1(d.pool_id,d.preceding_qty,d.sewing_qty)),0) into v_pocket from erp.pocket_period_destinations d where d.event_id is not null and d.po_id=p_po_id;
  -- One lock order covers Draft reservation, post/reversal, late recost, and GL sync.
  perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
  perform pg_advisory_xact_lock(hashtextextended('PO_HPP:'||p_po_id::text,0));

  select coalesce(sum(-msm.qty_signed*msm.unit_cost_snapshot),0) into v_material
  from erp.material_stock_movements msm
  where ((msm.source_type='CUTTING_GROUP' and msm.source_id in (select id from erp.cutting_groups where po_id=p_po_id))
     or (msm.source_type='CUTTING_GROUP_RETURN' and msm.source_id in (select id from erp.cutting_groups where po_id=p_po_id)))
    and not exists(select 1 from erp.material_stock_movements rv where rv.reversal_of_id=msm.id);

  select coalesce(sum(cmii.qty*cmii.unit_cost_snapshot),0) into v_contractor_material
  from erp.contractor_material_issue_items cmii
  join erp.contractor_material_issues cmi on cmi.id=cmii.issue_id
  join erp.materials m on m.id=cmii.material_id
  where cmi.po_id=p_po_id and cmi.status='POSTED' and m.material_type<>'ACCESSORY';

  select
    coalesce(sum(case when wc.component_category='COMMISSION' then wcl.amount_payable else 0 end),0),
    coalesce(sum(case when wc.component_category<>'COMMISSION' then wcl.amount_payable else 0 end),0),
    coalesce(sum(case when wce.cutting_group_id is null and wc.component_category='COMMISSION' then wcl.amount_payable else 0 end),0),
    coalesce(sum(case when wce.cutting_group_id is null and wc.component_category<>'COMMISSION' then wcl.amount_payable else 0 end),0)
  into v_commission,v_labor,v_shared_commission,v_shared_labor
  from erp.work_completion_lines wcl
  join erp.work_completion_events wce on wce.id=wcl.completion_id
  join erp.work_components wc on wc.id=wcl.work_component_id
  where wce.po_id=p_po_id and wce.status='POSTED';

  with dl as (
    select ldl.id,ldl.cutting_group_id,ldl.qty_sent_pcs,ldl.estimated_rate_snapshot,
           coalesce(sum(case when lr.status='POSTED' and (lrl.actual_cost_status in ('ESTIMATED','FINAL')
                 or (lrl.actual_cost_status='PENDING' and bf.details_pending)) then lrl.qty_good_received+lrl.qty_bs_laundry else 0 end),0) as qty_costed_actual,
           -- BD: plus the product-cost variance of posted laundry invoice lines; a fully invoiced source is no longer pending.
           coalesce(sum(case when lr.status='POSTED' and (lrl.actual_cost_status in ('ESTIMATED','FINAL')
                 or (lrl.actual_cost_status='PENDING' and bf.details_pending)) then coalesce(lrl.actual_cost,0)+erp.bd_product_variance_v1(lrl.id) else 0 end),0) as actual_cost,
           bool_or(lr.status='POSTED' and lrl.actual_cost_status in('PENDING','ESTIMATED') and not erp.bd_receipt_invoiced_v1(lrl.id)) as has_pending_receipt
    from erp.laundry_delivery_lines ldl
    join erp.laundry_deliveries ld on ld.id=ldl.delivery_id
    left join erp.laundry_receipt_lines lrl on lrl.delivery_line_id=ldl.id
    left join erp.laundry_receipts lr on lr.id=lrl.receipt_id
        left join erp.bf_laundry_delivery_sources_v1 bf on bf.delivery_line_id=ldl.id
    where ld.po_id=p_po_id and ld.status<>'REVERSED'
    group by ldl.id,ldl.cutting_group_id,ldl.qty_sent_pcs,ldl.estimated_rate_snapshot
  )
  -- BD: uncosted part of a priced line by its exact shares; an unknown component price keeps the HPP pending.
  select coalesce(sum(actual_cost+erp.bd_uncosted_estimate_v1(id,qty_sent_pcs,qty_costed_actual,estimated_rate_snapshot)),0),
         coalesce(bool_or(has_pending_receipt or qty_sent_pcs>qty_costed_actual or not erp.bd_line_complete_v1(id)),false)
  into v_laundry,v_pending from dl;

  select v_laundry+coalesce(sum(rl.actual_cost+erp.bd_product_variance_v1(rl.id)),0)
    into v_laundry
  from erp.laundry_failed_wash_attempts a
  join erp.laundry_receipt_lines rl on rl.id=a.receipt_line_id
  join erp.laundry_receipts rh on rh.id=a.receipt_id and rh.status='POSTED'
  join erp.laundry_deliveries ld on ld.id=a.delivery_id and ld.status='REVERSED'
  where ld.po_id=p_po_id and rl.actual_cost_status in('ESTIMATED','FINAL');

  v_pending:=v_pending or exists(
    select 1
    from erp.laundry_failed_wash_attempts a
    join erp.laundry_receipts rh on rh.id=a.receipt_id and rh.status='POSTED'
    join erp.laundry_receipt_lines rl on rl.id=a.receipt_line_id
    join erp.laundry_deliveries ld on ld.id=a.delivery_id
    where ld.po_id=p_po_id and rl.actual_cost_status='ESTIMATED' and not erp.bd_receipt_invoiced_v1(rl.id)
  );
  -- OW-08b (LAU-DEC04): a failed wash whose vendor price is still unknown keeps this PO's HPP not final.
  v_pending:=v_pending or cp7_laundry_unknown_wash.po_pending_v1(p_po_id);


  select coalesce(sum(rcl.amount_payable),0),
         coalesce(sum(case when bc.cutting_group_id is null then rcl.amount_payable else 0 end),0)
  into v_rework,v_shared_rework
  from erp.rework_component_lines rcl
  join erp.rework_orders ro on ro.id=rcl.rework_order_id
  join erp.bs_cases bc on bc.id=ro.bs_case_id
  where bc.po_id=p_po_id and ro.status<>'CANCELLED' and coalesce(ro.cost_posted,false)=true;

  v_rework:=v_rework+erp.be_redye_po_cost_v1(p_po_id);
  v_pending:=v_pending or exists(select 1 from erp.be_redye_services_v1 bs join erp.rework_orders br on br.id=bs.id
    where bs.po_id=p_po_id and br.status<>'CANCELLED' and erp.be_redye_accrual_v1(p_po_id)<>0)
    or exists(select 1 from erp.be_redye_services_v1 bs join erp.rework_orders br on br.id=bs.id where bs.po_id=p_po_id and br.status<>'CANCELLED' and erp.be_redye_rate_v1(bs.id) is null);
  v_pending:=v_pending or exists(select 1 from erp.initial_import_production_sources ps where ps.po_id=p_po_id and erp.be_pocket_item_pending_v1(ps.opening_item_id));
  select coalesce(sum(adjustment_amount),0),coalesce(sum(case when lot_id is null then adjustment_amount else 0 end),0)
  into v_other,v_shared_other
  from erp.cost_adjustments
  where po_id=p_po_id and component_type='OTHER';

  select
    coalesce(sum(a.allocated_amount),0),
    coalesce(sum(case when a.cutting_group_id is null then a.allocated_amount else 0 end),0)
  into v_attendance_hpp,v_shared_attendance_hpp
  from erp.attendance_hpp_pool_allocations a
  join erp.attendance_hpp_pools hp on hp.id=a.pool_id and hp.status='ACTIVE'
  where a.po_id=p_po_id;

  select coalesce(sum(initial_qty_pcs),0) into v_total_qty
  from erp.fg_lots where po_id=p_po_id and lot_origin='PRODUCTION';
  if v_total_qty<=0 then return; end if;
  v_po_source_qty:=erp.cp6_po_source_qty_v2620c(p_po_id);
  if coalesce(v_po_source_qty,0)<=0 then
    raise exception 'PO source quantity is required before HPP can be allocated';
  end if;

  for r in select id from erp.fg_lots where po_id=p_po_id and lot_origin='PRODUCTION' order by produced_at,id
  loop perform erp.ensure_fg_accessory_cost_snapshot(r.id); end loop;

  select coalesce(sum(facs.total_hpp_cost),0) into v_accessory
  from erp.fg_accessory_cost_snapshots facs join erp.fg_lots fl on fl.id=facs.lot_id
  where fl.po_id=p_po_id and fl.lot_origin='PRODUCTION';

  v_pending:=v_pending or exists(select 1 from erp.initial_import_production_sources s
    join erp.initial_import_cost_origins o on o.opening_item_id=s.opening_item_id where s.po_id=p_po_id
    and erp.material_purchase_invoice_capacity(o.purchase_item_id)>erp.material_purchase_posted_invoice_qty(o.purchase_item_id));
  v_state:=case when v_pending then 'ESTIMATED' when exists (select 1 from erp.cost_adjustments where po_id=p_po_id) then 'ADJUSTED' else 'ACTUAL' end;

  for r in
    select fl.*,coalesce(fl.qc_item_id,(
      select bc.qc_item_id from erp.rework_orders ro
      join erp.bs_cases bc on bc.id=ro.bs_case_id
      where ro.good_fg_lot_id=fl.id
    )) as source_qc_item_id,
      coalesce(fl.cutting_group_id,qi.cutting_group_id) as lineage_group_id
    from erp.fg_lots fl left join erp.qc_inspection_items qi on qi.id=fl.qc_item_id
    where fl.po_id=p_po_id and fl.lot_origin='PRODUCTION'
    order by fl.produced_at,fl.id
  loop
    v_lot_material:=0;v_pool_material:=0;v_pool_qty:=0;v_batch_id:=null;
    v_group_fg_qty:=0;v_group_labor:=0;v_group_commission:=0;v_group_laundry:=0;v_group_rework:=0;v_group_attendance_hpp:=0;
    v_cp6_lineage:=false;v_lot_cp6_receipt_laundry:=0;v_lot_cp6_attempt_laundry:=0;

    if r.lineage_group_id is not null then
      select cutting_batch_id into v_batch_id from erp.cutting_groups where id=r.lineage_group_id;
      if v_batch_id is not null then
        select coalesce(sum(-msm.qty_signed*msm.unit_cost_snapshot),0) into v_pool_material
        from erp.material_stock_movements msm
        where ((msm.source_type='CUTTING_GROUP' and msm.source_id in (select id from erp.cutting_groups where cutting_batch_id=v_batch_id))
           or (msm.source_type='CUTTING_GROUP_RETURN' and msm.source_id in (select id from erp.cutting_groups where cutting_batch_id=v_batch_id)))
          and not exists(select 1 from erp.material_stock_movements rv where rv.reversal_of_id=msm.id);
        select effective_pcs::numeric into v_pool_qty from erp.v_cutting_batch_totals where cutting_batch_id=v_batch_id;
      else
        select coalesce(sum(-msm.qty_signed*msm.unit_cost_snapshot),0) into v_pool_material
        from erp.material_stock_movements msm
        where msm.source_id=r.lineage_group_id and msm.source_type in ('CUTTING_GROUP','CUTTING_GROUP_RETURN')
          and not exists(select 1 from erp.material_stock_movements rv where rv.reversal_of_id=msm.id);
        select total_pcs::numeric into v_pool_qty from erp.v_cutting_group_totals where cutting_group_id=r.lineage_group_id;
      end if;

      select coalesce(sum(fl2.initial_qty_pcs),0)::numeric into v_group_fg_qty
      from erp.fg_lots fl2 where fl2.po_id=p_po_id and fl2.lot_origin='PRODUCTION' and fl2.cutting_group_id=r.lineage_group_id;

      select
        coalesce(sum(case when wc.component_category<>'COMMISSION' then wcl.amount_payable else 0 end),0),
        coalesce(sum(case when wc.component_category='COMMISSION' then wcl.amount_payable else 0 end),0)
      into v_group_labor,v_group_commission
      from erp.work_completion_lines wcl
      join erp.work_completion_events wce on wce.id=wcl.completion_id
      join erp.work_components wc on wc.id=wcl.work_component_id
      where wce.po_id=p_po_id and wce.status='POSTED' and wce.cutting_group_id=r.lineage_group_id;

      with dl as (
        select ldl.id,ldl.qty_sent_pcs,ldl.estimated_rate_snapshot,
               coalesce(sum(case when lr.status='POSTED' and (lrl.actual_cost_status in ('ESTIMATED','FINAL')
                 or (lrl.actual_cost_status='PENDING' and bf.details_pending)) then lrl.qty_good_received+lrl.qty_bs_laundry else 0 end),0) as qty_costed_actual,
               coalesce(sum(case when lr.status='POSTED' and (lrl.actual_cost_status in ('ESTIMATED','FINAL')
                 or (lrl.actual_cost_status='PENDING' and bf.details_pending)) then coalesce(lrl.actual_cost,0)+erp.bd_product_variance_v1(lrl.id) else 0 end),0) as actual_cost
        from erp.laundry_delivery_lines ldl
        join erp.laundry_deliveries ld on ld.id=ldl.delivery_id
        left join erp.laundry_receipt_lines lrl on lrl.delivery_line_id=ldl.id
        left join erp.laundry_receipts lr on lr.id=lrl.receipt_id
        left join erp.bf_laundry_delivery_sources_v1 bf on bf.delivery_line_id=ldl.id
        where ld.po_id=p_po_id and ld.status<>'REVERSED' and ldl.cutting_group_id=r.lineage_group_id
        group by ldl.id,ldl.qty_sent_pcs,ldl.estimated_rate_snapshot
      )
      select coalesce(sum(actual_cost+erp.bd_uncosted_estimate_v1(id,qty_sent_pcs,qty_costed_actual,estimated_rate_snapshot)),0)
      into v_group_laundry from dl;

      select v_group_laundry+coalesce(sum(rl.actual_cost+erp.bd_product_variance_v1(rl.id)),0)
        into v_group_laundry
      from erp.laundry_failed_wash_attempts a
      join erp.laundry_receipt_lines rl on rl.id=a.receipt_line_id
      join erp.laundry_receipts rh on rh.id=a.receipt_id and rh.status='POSTED'
      join erp.laundry_deliveries ld on ld.id=a.delivery_id and ld.status='REVERSED'
      join erp.laundry_delivery_lines ldl on ldl.delivery_id=ld.id
      where ld.po_id=p_po_id and ldl.cutting_group_id=r.lineage_group_id
        and rl.actual_cost_status in('ESTIMATED','FINAL');


      select coalesce(sum(rcl.amount_payable),0) into v_group_rework
      from erp.rework_component_lines rcl
      join erp.rework_orders ro on ro.id=rcl.rework_order_id
      join erp.bs_cases bc on bc.id=ro.bs_case_id
      where bc.po_id=p_po_id and bc.cutting_group_id=r.lineage_group_id and ro.status<>'CANCELLED' and coalesce(ro.cost_posted,false)=true;

      select coalesce(sum(a.allocated_amount),0) into v_group_attendance_hpp
      from erp.attendance_hpp_pool_allocations a
      join erp.attendance_hpp_pools hp on hp.id=a.pool_id and hp.status='ACTIVE'
      where a.po_id=p_po_id and a.cutting_group_id=r.lineage_group_id;
    end if;

    select exists(
      select 1
      from erp.qc_inspection_items qi
      join erp.laundry_receipt_batch_size_lines rx
        on rx.id=qi.source_laundry_receipt_batch_size_line_id
      where qi.id=r.source_qc_item_id
    ) into v_cp6_lineage;

    if v_cp6_lineage then
      select coalesce((case
          when rl.actual_cost_status in('ESTIMATED','FINAL') and rl.actual_cost is not null
            -- BD: a lot from a priced receipt size takes that size's own amount (sizes may be priced differently).
            then coalesce((select ba.amount/nullif(ba.qty,0) from erp.bd_laundry_receipt_allocations_v1 ba where ba.receipt_batch_size_line_id=rx.id),
              rl.actual_cost/nullif(rl.qty_good_received+rl.qty_bs_laundry,0))
              +erp.bd_product_variance_v1(rl.id)/nullif(rl.qty_good_received+rl.qty_bs_laundry,0)
          when rl.actual_cost_status='PENDING' and exists(
            select 1 from erp.bf_laundry_delivery_sources_v1 bf
            where bf.delivery_line_id=rl.delivery_line_id and bf.details_pending)
            then erp.bd_product_variance_v1(rl.id)/nullif(rl.qty_good_received+rl.qty_bs_laundry,0)
          else coalesce(rl.actual_rate_snapshot,dl.estimated_rate_snapshot,0)
        end)*r.initial_qty_pcs,0)
      into v_lot_cp6_receipt_laundry
      from erp.qc_inspection_items qi
      join erp.laundry_receipt_batch_size_lines rx
        on rx.id=qi.source_laundry_receipt_batch_size_line_id
      join erp.laundry_receipt_lines rl on rl.id=rx.receipt_line_id
        and rl.id=qi.source_laundry_receipt_line_id
      join erp.laundry_receipts rh on rh.id=rl.receipt_id and rh.status='POSTED'
      join erp.laundry_delivery_lines dl on dl.id=rl.delivery_line_id
      join erp.laundry_deliveries d on d.id=dl.delivery_id and d.status<>'REVERSED'
      left join erp.laundry_failed_wash_attempts fa on fa.receipt_line_id=rl.id
      where qi.id=r.source_qc_item_id and fa.id is null;
      v_lot_cp6_receipt_laundry:=coalesce(v_lot_cp6_receipt_laundry,0);

      select erp.cp6_lot_failed_wash_cost_v2620e(r.id)
      into v_lot_cp6_attempt_laundry;
    end if;

    if coalesce(v_pool_qty,0)>0 then v_lot_material:=v_pool_material*(r.initial_qty_pcs::numeric/v_pool_qty);
    else v_lot_material:=v_material*(r.initial_qty_pcs::numeric/v_total_qty::numeric); end if;
    v_lot_material:=v_lot_material+v_contractor_material*(r.initial_qty_pcs::numeric/v_po_source_qty);
    v_material_allocated:=v_material_allocated+v_lot_material;

    v_lot_labor:=erp.cp6_lot_work_cost_v2620c(r.id,'LABOR');
    v_lot_commission:=erp.cp6_lot_work_cost_v2620c(r.id,'COMMISSION');
    v_lot_laundry:=case when v_cp6_lineage
      then v_lot_cp6_receipt_laundry+v_lot_cp6_attempt_laundry
      when r.lineage_group_id is not null then v_group_laundry*(r.initial_qty_pcs::numeric/nullif(
        coalesce(nullif((select total_pcs::numeric from erp.v_cutting_group_totals
          where cutting_group_id=r.lineage_group_id),0),v_po_source_qty),0))
      else v_laundry*(r.initial_qty_pcs::numeric/v_po_source_qty) end;
    v_lot_rework:=erp.cp6_lot_rework_cost_v2620c(r.id);
    v_lot_attendance_hpp:=erp.cp6_lot_attendance_cost_v2620c(r.id);
    v_lot_pocket:=erp.pocket_lot_cost_v1(r.id);v_pocket_allocated:=v_pocket_allocated+v_lot_pocket;

    select coalesce(sum(total_hpp_cost),0) into v_lot_accessory from erp.fg_accessory_cost_snapshots where lot_id=r.id;
    select coalesce(sum(adjustment_amount),0) into v_lot_other from erp.cost_adjustments where lot_id=r.id and component_type='OTHER';
    v_lot_other:=v_lot_other+v_shared_other*(r.initial_qty_pcs::numeric/v_po_source_qty);
    v_laundry_allocated:=v_laundry_allocated+v_lot_laundry;
    v_labor_allocated:=v_labor_allocated+v_lot_labor;
    v_commission_allocated:=v_commission_allocated+v_lot_commission;
    v_rework_allocated:=v_rework_allocated+v_lot_rework;
    v_attendance_allocated:=v_attendance_allocated+v_lot_attendance_hpp;
    v_opening_cost:=erp.initial_import_lot_cost_v1(r.id);
    v_lot_cost:=v_opening_cost+v_lot_material+v_lot_labor+v_lot_commission+v_lot_laundry+v_lot_rework+v_lot_attendance_hpp+v_lot_other+v_lot_accessory+v_lot_pocket;
    v_total_current:=v_total_current+v_lot_cost;

    select id into v_old_id from erp.hpp_versions where lot_id=r.id and is_current=true order by version_no desc limit 1;
    select coalesce(max(version_no),0)+1 into v_version from erp.hpp_versions where lot_id=r.id;
    if v_old_id is not null then update erp.hpp_versions set is_current=false where id=v_old_id; end if;

    insert into erp.hpp_versions(lot_id,version_no,cost_state,qty_basis_pcs,total_cost,is_current,supersedes_id,calculation_reason,created_by)
    values (r.id,v_version,v_state,r.initial_qty_pcs,v_lot_cost,true,v_old_id,p_reason,erp.current_app_user_id()) returning id into v_new_id;

    insert into erp.hpp_version_components(hpp_version_id,component_type,description,total_cost,source_type,source_id)
    values
      (v_new_id,'MATERIAL',case when v_batch_id is not null then 'Cutting material by effective batch yield + PO-shared non-accessory contractor material' else 'Cutting/legacy material pool + PO-shared non-accessory contractor material' end,v_lot_material,case when v_batch_id is not null then 'CUTTING_BATCH' else 'PO' end,coalesce(v_batch_id,p_po_id)),
      (v_new_id,'LABOR','Labor allocation: immutable component completion intervals; unfinished remains WIP',v_lot_labor,case when r.lineage_group_id is not null then 'CUTTING_GROUP' else 'PO' end,coalesce(r.lineage_group_id,p_po_id)),
      (v_new_id,'COMMISSION','Commission allocation: immutable component completion intervals; unfinished remains WIP',v_lot_commission,case when r.lineage_group_id is not null then 'CUTTING_GROUP' else 'PO' end,coalesce(r.lineage_group_id,p_po_id)),
      (v_new_id,'LAUNDRY',case when v_cp6_lineage
        then 'CP6 exact receipt/batch-size service lineage; unfinished cost remains WIP'
        else 'Legacy Laundry allocation from same cutting group; PENDING uses estimate' end,
        v_lot_laundry,case when v_cp6_lineage then 'QC_ITEM'
          when r.lineage_group_id is not null then 'CUTTING_GROUP' else 'PO' end,
        case when v_cp6_lineage then r.source_qc_item_id else coalesce(r.lineage_group_id,p_po_id) end),
      (v_new_id,'REWORK','Rework allocation: exact good rework lot and qty-sent source',v_lot_rework,case when r.lineage_group_id is not null then 'CUTTING_GROUP' else 'PO' end,coalesce(r.lineage_group_id,p_po_id)),
      (v_new_id,'LABOR','Attendance HPP: ACTIVE source sewing intervals; unfinished remains WIP',v_lot_attendance_hpp,'ATTENDANCE_HPP_ACTIVE_ALLOCATION',coalesce(r.lineage_group_id,p_po_id)),
      (v_new_id,'OTHER','Kain kantong: pembagian periode selesai dijahit',v_lot_pocket,'POCKET_PERIOD_ALLOCATION',p_po_id),
      (v_new_id,'OTHER','Other/adjustment allocation',v_lot_other,'PO',p_po_id),
      (v_new_id,'OTHER','Saldo fisik sebelum cutover',v_opening_cost,'INITIAL_IMPORT_PRODUCTION',r.id);

    for c in
      select facs.id,facs.total_hpp_cost,ac.category_name,facs.hpp_method
      from erp.fg_accessory_cost_snapshots facs join erp.accessory_categories ac on ac.id=facs.category_id
      where facs.lot_id=r.id order by ac.category_code
    loop
      insert into erp.hpp_version_components(hpp_version_id,component_type,description,total_cost,source_type,source_id)
      values (v_new_id,'ACCESSORY','Accessory category: '||c.category_name||' ['||c.hpp_method||']',c.total_hpp_cost,'FG_ACCESSORY_SNAPSHOT',c.id);
    end loop;

    update erp.fg_stock_movements set unit_hpp_snapshot=(select hpp_per_pcs from erp.hpp_versions where id=v_new_id)
    where lot_id=r.id and movement_type in ('QC_GOOD','REWORK_IN');
  end loop;

  if v_pocket_allocated < -0.005 or v_pocket_allocated>v_pocket+0.005 then raise exception 'Pocket HPP cost conservation failed';end if;
  if v_labor_allocated < -0.005 or v_labor_allocated > v_labor+0.005
     or v_commission_allocated < -0.005 or v_commission_allocated > v_commission+0.005
     or v_rework_allocated < -0.005 or v_rework_allocated > v_rework+0.005
     or v_attendance_allocated < -0.005 or v_attendance_allocated > v_attendance_hpp+0.005 then
    raise exception 'CP6 source-owned HPP allocation violates cost conservation: labor %/%, commission %/%, rework %/%, attendance %/%',
      v_labor_allocated,v_labor,v_commission_allocated,v_commission,
      v_rework_allocated,v_rework,v_attendance_allocated,v_attendance_hpp;
  end if;

  if v_laundry_allocated < -0.005 or v_laundry_allocated > v_laundry+0.005 then
    raise exception 'CP6 Laundry HPP allocation violates cost conservation: accrued %, FG allocated %',
      v_laundry,v_laundry_allocated;
  end if;

  insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)
  values ('production_orders',p_po_id,'RECALCULATE',jsonb_build_object(
    'material_total_issued',v_material+v_contractor_material,'cutting_material_total',v_material,'contractor_nonaccessory_material_total',v_contractor_material,'material_allocated_to_current_fg',v_material_allocated,'material_basis','CUTTING_BATCH_EFFECTIVE_YIELD_PLUS_PO_SHARED_CONTRACTOR_MATERIAL',
    'pocket_fabric',v_pocket,'pocket_allocated_to_fg',v_pocket_allocated,'pocket_remaining_in_wip',v_pocket-v_pocket_allocated,
    'accessory',v_accessory,'labor',v_labor,'attendance_hpp',v_attendance_hpp,'commission',v_commission,'laundry',v_laundry,'rework',v_rework,'other',v_other,
    'laundry_allocated_to_current_fg',v_laundry_allocated,
    'laundry_remaining_in_wip',v_laundry-v_laundry_allocated,
    'labor_allocated_to_fg',v_labor_allocated,'labor_remaining_in_wip',v_labor-v_labor_allocated,
    'commission_allocated_to_fg',v_commission_allocated,'commission_remaining_in_wip',v_commission-v_commission_allocated,
    'rework_allocated_to_fg',v_rework_allocated,'rework_remaining_in_wip',v_rework-v_rework_allocated,
    'attendance_allocated_to_fg',v_attendance_allocated,'attendance_remaining_in_wip',v_attendance_hpp-v_attendance_allocated,
    'po_physical_source_qty',v_po_source_qty,
    'laundry_basis','CP6_EXACT_DELIVERY_SIZE_CUSTODY_INTERVAL_V2620C',
    'total_current_fg_cost',v_total_current,'cost_state',v_state,'nonmaterial_basis','CUTTING_GROUP_LINEAGE_WITH_PO_SHARED_FALLBACK','accessory_basis','GOOD_FG_X_CATEGORY_BOM'),
    erp.current_app_user_id(),p_reason);
end;
$function$;
CREATE OR REPLACE FUNCTION erp.bd_lot_laundry_unknown_v1(p_lot uuid)
 RETURNS boolean
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO ''
AS $function$
  select exists(select 1 from erp.fg_lots be_lot join erp.be_redye_services_v1 be_s on be_s.po_id=be_lot.po_id join erp.rework_orders be_r on be_r.id=be_s.id where be_lot.id=p_lot and be_r.status<>'CANCELLED' and erp.be_redye_rate_v1(be_s.id) is null) or coalesce((select erp.bd_delivery_line_price_unknown_v1(rl.delivery_line_id) from erp.fg_lots l join erp.qc_inspection_items qi on qi.id=l.qc_item_id
      join erp.laundry_receipt_lines rl on rl.id=qi.source_laundry_receipt_line_id where l.id=p_lot),
    exists(select 1 from erp.fg_lots l join erp.laundry_deliveries d on d.po_id=l.po_id and d.status not in('DRAFT','REVERSED')
      join erp.laundry_delivery_lines dl on dl.delivery_id=d.id where l.id=p_lot and erp.bd_delivery_line_price_unknown_v1(dl.id)))
    -- OW-08b (LAU-DEC04): goods of a PO with a failed wash whose vendor price is still unknown.
    or exists(select 1 from erp.fg_lots ow_lot where ow_lot.id=p_lot and cp7_laundry_unknown_wash.po_pending_v1(ow_lot.po_id))
$function$;
CREATE OR REPLACE FUNCTION erp.bd_pending_cost_json_v1(p_vendor uuid, p_money boolean)
 RETURNS jsonb
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO ''
AS $function$
  with unknown_po as(
    select distinct d.po_id from erp.laundry_deliveries d join erp.laundry_delivery_lines dl on dl.delivery_id=d.id
    where d.status not in('DRAFT','REVERSED') and (p_vendor is null or d.vendor_id=p_vendor) and erp.bd_delivery_line_price_unknown_v1(dl.id)
    -- OW-08b: the PO of a failed wash whose vendor price is still unknown.
    union select u.po_id from cp7_laundry_unknown_wash.unknown_v1() u where p_vendor is null or u.vendor_id=p_vendor),
  goods as(
    select l.id,l.lot_number,l.cached_qty_pcs,po.po_number,p.sku,p.product_name,
      (select h.hpp_per_pcs from erp.hpp_versions h where h.lot_id=l.id and h.is_current) hpp,
      (select coalesce(sum(a.qty_pcs),0) from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id
         join erp.sales_headers sh on sh.id=i.sale_id and sh.status='POSTED' where a.lot_id=l.id)::integer sold
    from erp.fg_lots l join unknown_po u on u.po_id=l.po_id join erp.production_orders po on po.id=l.po_id join erp.products p on p.id=l.product_id
    where erp.bd_lot_laundry_unknown_v1(l.id)
    order by po.po_number,l.lot_number limit 100),
  sales as(
    select x.id,x.sale_id,sh.sale_number,to_char(sh.sale_date at time zone 'Asia/Jakarta','YYYY-MM-DD') sale_date,x.qty_pcs,x.recorded_at,x.policy_version,p.sku,p.product_name,l.lot_number,
      not erp.bd_lot_laundry_unknown_v1(x.lot_id) final,
      (select a.unit_hpp_snapshot from erp.sale_stock_allocations a where a.sale_item_id=x.sale_item_id and a.lot_id=x.lot_id limit 1) unit_hpp
    from erp.bd_pending_price_sales_v1 x join erp.sales_headers sh on sh.id=x.sale_id join erp.fg_lots l on l.id=x.lot_id
      join erp.products p on p.id=l.product_id
    where p_vendor is null or exists(select 1 from erp.laundry_deliveries d where d.po_id=l.po_id and d.vendor_id=p_vendor)
    order by x.recorded_at desc,x.id limit 100)
  select jsonb_build_object(
    'goods',coalesce((select jsonb_agg(jsonb_build_object('lot_id',g.id,'lot_number',g.lot_number,'po_number',g.po_number,'sku',g.sku,
        'product_name',g.product_name,'qty_now',g.cached_qty_pcs,'qty_sold',g.sold,'hpp_state','NOT_FINAL',
        'hpp_per_pcs_so_far',case when p_money then g.hpp::numeric(18,2)::text end)) from goods g),'[]'::jsonb),
    'sales',coalesce((select jsonb_agg(jsonb_build_object('id',x.id,'sale_id',x.sale_id,'sale_number',x.sale_number,'sale_date',x.sale_date,
        'sku',x.sku,'product_name',x.product_name,'lot_number',x.lot_number,'qty',x.qty_pcs,'policy_version',x.policy_version::text,
        'recorded_at',to_char(x.recorded_at at time zone 'Asia/Jakarta','YYYY-MM-DD"T"HH24:MI:SS'),'hpp_state',case when x.final then 'RECOSTED' else 'NOT_FINAL' end,
        'unit_hpp_at_sale',case when p_money then x.unit_hpp::numeric(18,2)::text end)) from sales x),'[]'::jsonb))
$function$;
CREATE OR REPLACE FUNCTION erp.bd_save_invoice_draft_v1(p_payload jsonb, p_request uuid)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare v_id uuid;i erp.bd_laundry_invoices_v1%rowtype;v_vendor uuid;v_x jsonb;v_no integer:=0;v_rl record;v_kind text;v_qty integer;v_amount numeric;
  v_rounding numeric;v_open erp.bd_opening_laundry_uninvoiced_v1%rowtype;v_total numeric;v_corrects uuid;v_has_bill boolean;v_has_corr boolean;
  v_redye erp.be_redye_services_v1%rowtype;v_origins uuid[];o erp.bd_laundry_invoices_v1%rowtype;v_discount numeric;v_tax numeric;
begin
  perform erp.require_owner_admin();perform erp.require_permission('finance.hpp.manage');
  perform erp._cp3_assert_closed_json_object(p_payload,array['vendor_id','invoice_number','invoice_date','header_total','lines'],
    array['invoice_id','expected_version','vendor_id','invoice_number','invoice_date','due_date','header_total','discount_amount','tax_amount',
      'rounding_amount','notes','lines','corrects_invoice_id'],'laundry invoice draft');
  v_id:=erp.bd_uuid_v1(p_payload,'invoice_id',false);v_vendor:=erp.bd_uuid_v1(p_payload,'vendor_id',true);
  if not exists(select 1 from erp.laundry_vendors where id=v_vendor) then raise exception 'BD_VENDOR_INACTIVE: vendor laundry tidak dikenal';end if;
  if jsonb_typeof(p_payload->'invoice_date') is distinct from 'string' or p_payload->>'invoice_date'!~'^\d{4}-\d{2}-\d{2}$' then
    raise exception 'BD_FIELD_INVALID: invoice_date wajib tanggal YYYY-MM-DD';end if;
  if p_payload ? 'due_date' and jsonb_typeof(p_payload->'due_date')<>'null' and (jsonb_typeof(p_payload->'due_date')<>'string' or p_payload->>'due_date'!~'^\d{4}-\d{2}-\d{2}$') then
    raise exception 'BD_FIELD_INVALID: due_date wajib tanggal YYYY-MM-DD';end if;
  if jsonb_typeof(p_payload->'lines') is distinct from 'array' or jsonb_array_length(p_payload->'lines') not between 1 and 200 then
    raise exception 'BD_INVOICE_LINES: invoice memuat 1-200 baris';end if;
  v_rounding:=0;
  if p_payload ? 'rounding_amount' and jsonb_typeof(p_payload->'rounding_amount')<>'null' then
    if jsonb_typeof(p_payload->'rounding_amount')<>'string' or p_payload->>'rounding_amount'!~'^-?(0|[1-9][0-9]{0,2})\.[0-9]{2}$' then
      raise exception 'BD_AMOUNT_INVALID: rounding_amount wajib nominal teks bertanda dengan tepat dua desimal, kurang dari 1000';end if;
    v_rounding:=(p_payload->>'rounding_amount')::numeric;
  end if;
  v_discount:=case when p_payload ? 'discount_amount' and jsonb_typeof(p_payload->'discount_amount')<>'null' then erp.bd_amount_v1(p_payload->'discount_amount','discount_amount',false) else 0 end;
  v_tax:=case when p_payload ? 'tax_amount' and jsonb_typeof(p_payload->'tax_amount')<>'null' then erp.bd_amount_v1(p_payload->'tax_amount','tax_amount',false) else 0 end;
  -- Invoice or correction document (owner decision no. 13): correction lines never share a document with billing lines.
  select bool_or(x->>'line_kind'='BILL'),bool_or(x->>'line_kind'='CORRECTION') into v_has_bill,v_has_corr from jsonb_array_elements(p_payload->'lines') x;
  v_corrects:=erp.bd_uuid_v1(p_payload,'corrects_invoice_id',false);
  if coalesce(v_has_bill,false) and (coalesce(v_has_corr,false) or v_corrects is not null) then
    raise exception 'BD_CORRECTION_SEPARATE_DOCUMENT: koreksi dibuat sebagai dokumen koreksi tersendiri yang tertaut ke invoice asal; pisahkan dari baris tagih';end if;
  if coalesce(v_has_corr,false) then
    if v_corrects is null then
      select array_agg(distinct y.id) into v_origins from jsonb_array_elements(p_payload->'lines') x
        join erp.bd_laundry_invoice_lines_v1 b on b.line_kind='BILL' and (b.receipt_line_id=erp.bd_uuid_v1(x,'receipt_line_id',false)
          or b.opening_uninvoiced_id=erp.bd_uuid_v1(x,'opening_uninvoiced_id',false) or b.rework_service_id=erp.bd_uuid_v1(x,'rework_service_id',false))
        join erp.bd_laundry_invoices_v1 y on y.id=b.invoice_id and y.status='POSTED' and y.corrects_invoice_id is null;
      if coalesce(cardinality(v_origins),0)<>1 then
        raise exception 'BD_CORRECTION_ORIGIN_REQUIRED: pilih invoice asal yang dikoreksi (sumber ini ditagih % invoice)',coalesce(cardinality(v_origins),0);end if;
      v_corrects:=v_origins[1];
    end if;
    select * into o from erp.bd_laundry_invoices_v1 where id=v_corrects;
    if o.id is null or o.status<>'POSTED' or o.corrects_invoice_id is not null then
      raise exception 'BD_CORRECTION_ORIGIN_INVALID: invoice asal harus invoice vendor laundry POSTED (bukan dokumen koreksi)';end if;
    if o.vendor_id<>v_vendor then raise exception 'BD_INVOICE_VENDOR: invoice asal milik vendor lain';end if;
    if v_discount<>0 or v_tax<>0 or v_rounding<>0 then
      raise exception 'BD_CORRECTION_NO_DISCOUNT_TAX: dokumen koreksi tidak memuat diskon, pajak, atau pembulatan; nominal koreksi sudah bersih';end if;
    if jsonb_typeof(p_payload->'header_total') is distinct from 'string' or p_payload->>'header_total'!~'^-?(0|[1-9][0-9]{0,15})\.[0-9]{2}$' then
      raise exception 'BD_AMOUNT_INVALID: header_total wajib nominal teks bertanda dengan tepat dua desimal';end if;
    v_total:=(p_payload->>'header_total')::numeric;
    if v_total=0 then raise exception 'BD_AMOUNT_INVALID: total dokumen koreksi tidak boleh nol';end if;
  else
    v_total:=erp.bd_amount_v1(p_payload->'header_total','header_total',true);
  end if;
  if v_id is null then
    insert into erp.bd_laundry_invoices_v1(vendor_id,invoice_number,invoice_date,due_date,status,header_total,corrects_invoice_id,discount_amount,tax_amount,rounding_amount,notes,created_by)
    values(v_vendor,btrim(p_payload->>'invoice_number'),(p_payload->>'invoice_date')::date,(p_payload->>'due_date')::date,'DRAFT',v_total,v_corrects,
      v_discount,v_tax,v_rounding,nullif(btrim(coalesce(p_payload->>'notes','')),''),erp.current_app_user_id()) returning * into i;
  else
    select * into i from erp.bd_laundry_invoices_v1 where id=v_id for update;
    if i.id is null or i.status<>'DRAFT' then raise exception 'BD_INVOICE_NOT_DRAFT: hanya draf invoice yang dapat diubah';end if;
    if jsonb_typeof(p_payload->'expected_version') is distinct from 'string' or p_payload->>'expected_version' is distinct from i.row_version::text then
      raise exception 'STALE_VERSION: draf invoice berubah; muat ulang';end if;
    update erp.bd_laundry_invoices_v1 set vendor_id=v_vendor,invoice_number=btrim(p_payload->>'invoice_number'),invoice_date=(p_payload->>'invoice_date')::date,
      due_date=(p_payload->>'due_date')::date,header_total=v_total,corrects_invoice_id=v_corrects,discount_amount=v_discount,tax_amount=v_tax,
      rounding_amount=v_rounding,notes=nullif(btrim(coalesce(p_payload->>'notes','')),''),row_version=row_version+1
    where id=i.id returning * into i;
    delete from erp.bd_laundry_invoice_lines_v1 where invoice_id=i.id;
  end if;
  for v_x in select value from jsonb_array_elements(p_payload->'lines') loop
    v_no:=v_no+1;
    perform erp._cp3_assert_closed_json_object(v_x,array['line_kind','category','qty','amount'],
      array['line_kind','receipt_line_id','opening_uninvoiced_id','rework_service_id','category','qty','amount','note','wash_process_id'],'invoice line');
    if v_x->>'wash_process_id' is not null
       and (not(v_x ? 'receipt_line_id') or v_x->>'line_kind'<>'BILL' or v_x->>'category' not in('GOOD','BS')) then
      raise exception 'Proses aktual kontra bon harus terkait baris tagih penerimaan fisik';
    end if;
    if (v_x ? 'receipt_line_id')::int+(v_x ? 'opening_uninvoiced_id')::int+(v_x ? 'rework_service_id')::int<>1 then
      raise exception 'BD_INVOICE_SOURCE: setiap baris menunjuk satu sumber, baris penerimaan (receipt_line_id) atau penerimaan saldo awal (opening_uninvoiced_id)';end if;
    v_kind:=v_x->>'line_kind';
    if v_kind not in('BILL','CORRECTION') then raise exception 'BD_INVOICE_LINE_KIND: BILL atau CORRECTION';end if;
    if v_x->>'category' not in('GOOD','BS','FAILED_ATTEMPT') then raise exception 'BD_INVOICE_CATEGORY: GOOD, BS atau FAILED_ATTEMPT';end if;
    if jsonb_typeof(v_x->'qty') is distinct from 'number' or v_x->>'qty'!~'^(0|[1-9][0-9]{0,8})$' then raise exception 'BD_QTY_INVALID: qty wajib bilangan bulat >= 0';end if;
    v_qty:=(v_x->>'qty')::integer;
    if jsonb_typeof(v_x->'amount') is distinct from 'string' or v_x->>'amount'!~'^-?(0|[1-9][0-9]{0,15})\.[0-9]{2}$' then
      raise exception 'BD_AMOUNT_INVALID: amount wajib nominal teks dengan tepat dua desimal';end if;
    v_amount:=(v_x->>'amount')::numeric;
    if v_kind='BILL' and (v_qty<=0 or v_amount<0) then raise exception 'BD_INVOICE_LINE: baris tagih wajib qty > 0 dan nominal >= 0';end if;
    if v_kind='CORRECTION' and (v_qty<>0 or v_amount=0) then raise exception 'BD_INVOICE_LINE: baris koreksi wajib qty 0 dan nominal tidak nol';end if;
    if v_kind='CORRECTION' and sign(v_amount)<>sign(v_total) then
      raise exception 'BD_CORRECTION_MIXED_SIGN: satu dokumen koreksi hanya menaikkan atau hanya menurunkan tagihan';end if;
    if v_x ? 'rework_service_id' then
      select * into v_redye from erp.be_redye_services_v1 where id=erp.bd_uuid_v1(v_x,'rework_service_id',true);
      if v_redye.id is null then raise exception 'BD_INVOICE_SOURCE: jasa celup ulang tidak ditemukan';end if;
      if v_redye.vendor_id<>v_vendor then raise exception 'BD_INVOICE_VENDOR';end if;
      insert into erp.bd_laundry_invoice_lines_v1(invoice_id,line_no,line_kind,rework_service_id,category,qty,amount,note,po_id)
      values(i.id,v_no,v_kind,v_redye.id,v_x->>'category',v_qty,v_amount,nullif(btrim(coalesce(v_x->>'note','')),''),v_redye.po_id);
      continue;
    end if;
    if v_x ? 'opening_uninvoiced_id' then
      select * into v_open from erp.bd_opening_laundry_uninvoiced_v1 where id=erp.bd_uuid_v1(v_x,'opening_uninvoiced_id',true);
      if v_open.id is null then raise exception 'BD_INVOICE_SOURCE: penerimaan laundry saldo awal tidak ditemukan';end if;
      if v_open.vendor_id<>v_vendor then raise exception 'BD_INVOICE_VENDOR: penerimaan saldo awal milik vendor lain';end if;
      if v_open.category<>v_x->>'category' then raise exception 'BD_INVOICE_CATEGORY: penerimaan saldo awal ini berkategori %',v_open.category;end if;
      insert into erp.bd_laundry_invoice_lines_v1(invoice_id,line_no,line_kind,opening_uninvoiced_id,category,qty,amount,note,po_id)
      values(i.id,v_no,v_kind,v_open.id,v_x->>'category',v_qty,v_amount,nullif(btrim(coalesce(v_x->>'note','')),''),v_open.po_id);
      continue;
    end if;
    select rl.id,d.vendor_id,d.po_id,r.status into v_rl from erp.laundry_receipt_lines rl join erp.laundry_receipts r on r.id=rl.receipt_id
      join erp.laundry_delivery_lines dl on dl.id=rl.delivery_line_id join erp.laundry_deliveries d on d.id=dl.delivery_id
      where rl.id=erp.bd_uuid_v1(v_x,'receipt_line_id',true);
    if v_rl.id is null or v_rl.status<>'POSTED' then raise exception 'BD_INVOICE_SOURCE: sumber tagihan wajib baris penerimaan laundry POSTED';end if;
    if v_rl.vendor_id<>v_vendor then raise exception 'BD_INVOICE_VENDOR: baris penerimaan milik vendor lain';end if;
    -- OW-08b: a failed wash whose vendor price is still unknown is not billed before its price is set.
    if exists(select 1 from cp7_laundry_unknown_wash.unknown_v1() u where u.receipt_line_id=v_rl.id) then
      raise exception 'CP7_FAILED_WASH_PRICE_UNKNOWN: harga cuci gagal pada baris penerimaan ini belum diketahui; isi dulu di Produksi › Laundry › Harga & tagihan › Harga belum diketahui';end if;
    insert into erp.bd_laundry_invoice_lines_v1(invoice_id,line_no,line_kind,receipt_line_id,category,qty,amount,note,po_id,actual_wash_process_id)
    values(i.id,v_no,v_kind,v_rl.id,v_x->>'category',v_qty,v_amount,nullif(btrim(coalesce(v_x->>'note','')),''),v_rl.po_id,
      erp.bd_uuid_v1(v_x,'wash_process_id',false));
  end loop;
  if v_corrects is not null then perform erp.bd_check_correction_sources_v1(i.id);end if;
  return erp.bd_invoice_json_v1(i.id);
end;$function$;
CREATE OR REPLACE FUNCTION erp.save_laundry_bd_action_v1(p_action text, p_payload jsonb, p_client_request_id uuid)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare v_action text:=upper(btrim(coalesce(p_action,'')));v_prior erp.bd_requests_v1%rowtype;v_result jsonb;
begin
  if erp.current_app_user_id() is null and session_user not in('postgres','supabase_admin') then raise exception 'BD_AUTH_REQUIRED: login ERP diperlukan';end if;
  if p_client_request_id is null then raise exception 'BD_REQUEST_REQUIRED: id permintaan wajib';end if;
  if jsonb_typeof(p_payload) is distinct from 'object' then raise exception 'BD_PAYLOAD_INVALID: payload wajib objek';end if;
  if v_action not in('SET_REDYE_PRICE','SET_POLICY','SAVE_VENDOR_TERMS','SAVE_COMPONENT','SAVE_COMPONENT_RATE','SAVE_PACKAGE','SAVE_PACKAGE_RATE','SAVE_PROCESS_RATE',
    'SAVE_SCOPED_RATE','SAVE_DYEING_TYPE','SET_DYEING_SKU_LINK','POST_PRICED_DELIVERY','SET_CHARGE_PRICE','SAVE_INVOICE_DRAFT','CANCEL_INVOICE_DRAFT','POST_INVOICE','REVERSE_INVOICE','SET_OPENING_ESTIMATE',
    'APPLY_CLAIM_CREDIT','PAY_VENDOR_DOCUMENT','REVERSE_VENDOR_SETTLEMENT','RECEIVE_VENDOR_REFUND','REVERSE_VENDOR_REFUND','SET_FAILED_WASH_PRICE') then
    raise exception 'BD_ACTION_UNKNOWN: aksi laundry % tidak dikenal',v_action;end if;
  if v_action='SET_REDYE_PRICE' then perform erp.require_owner_admin();perform erp.require_permission('finance.hpp.manage');perform erp.require_permission('warehouse.brand_conversion.post');end if;
  perform pg_advisory_xact_lock(hashtextextended('BDREQ:'||p_client_request_id::text,0));
  -- Recheck live action permissions after waiting for the request lock and BEFORE any cached response.
  -- Inner commands retain their checks. Replays need the same authority as fresh commands.
  if v_action='SET_POLICY' then
    if session_user not in('postgres','supabase_admin') and erp.current_app_role() is distinct from 'OWNER' then
      raise exception 'BD_OWNER_ONLY: pengaturan kebijakan laundry hanya dapat diubah owner';end if;
    perform erp.require_permission('settings.erp.manage');
  elsif v_action='POST_PRICED_DELIVERY' then
    if erp.current_app_user_id() is null then raise exception 'BD_AUTH_REQUIRED: pengguna ERP aktif diperlukan';end if;
    perform erp.require_permission('production.laundry.post');perform erp.require_permission('production.laundry.create');
  elsif v_action in('SAVE_VENDOR_TERMS','SAVE_COMPONENT','SAVE_COMPONENT_RATE','SAVE_PACKAGE','SAVE_PACKAGE_RATE','SAVE_PROCESS_RATE','SAVE_SCOPED_RATE','SAVE_DYEING_TYPE','SET_DYEING_SKU_LINK') then
    perform erp.require_owner_admin();perform erp.require_permission('master.partner.manage');
  else
    perform erp.require_owner_admin();perform erp.require_permission('finance.hpp.manage');
  end if;
  select * into v_prior from erp.bd_requests_v1 where request_id=p_client_request_id;
  if v_prior.request_id is not null then
    if v_prior.action<>v_action or v_prior.payload<>p_payload or v_prior.actor is distinct from erp.current_app_user_id() then
      raise exception 'BD_REQUEST_REUSED: id permintaan sudah dipakai untuk isi lain';end if;
    return v_prior.response||jsonb_build_object('replayed',true);
  end if;
  v_result:=case v_action
    when 'SET_REDYE_PRICE' then erp.save_product_conversion_action_v1('SET_REDYE_PRICE',p_payload,p_client_request_id)
    when 'SET_POLICY' then erp.bd_set_policy_v1(p_payload,p_client_request_id)
    when 'SAVE_DYEING_TYPE' then erp.cp8_save_laundry_dyeing_master_v1(v_action,p_payload)
    when 'SET_DYEING_SKU_LINK' then erp.cp8_save_laundry_dyeing_master_v1(v_action,p_payload)
    when 'POST_PRICED_DELIVERY' then erp.bd_post_priced_delivery_v1(p_payload,p_client_request_id)
    when 'SET_CHARGE_PRICE' then erp.bd_set_charge_price_v1(p_payload,p_client_request_id)
    -- OW-08b: the price of a failed wash recorded with an unknown vendor price (owner/admin + finance.hpp.manage, as above).
    when 'SET_FAILED_WASH_PRICE' then cp7_laundry_unknown_wash.set_price_v1(p_payload,p_client_request_id)
    when 'SAVE_INVOICE_DRAFT' then erp.bd_save_invoice_draft_v1(p_payload,p_client_request_id)
    when 'CANCEL_INVOICE_DRAFT' then erp.bd_cancel_invoice_draft_v1(p_payload,p_client_request_id)
    when 'POST_INVOICE' then erp.bd_post_invoice_v1(p_payload,p_client_request_id)
    when 'REVERSE_INVOICE' then erp.bd_reverse_invoice_v1(p_payload,p_client_request_id)
    when 'SET_OPENING_ESTIMATE' then erp.bd_set_opening_estimate_v1(p_payload,p_client_request_id)
    when 'APPLY_CLAIM_CREDIT' then erp.bd_apply_claim_credit_v1(p_payload,p_client_request_id)
    when 'RECEIVE_VENDOR_REFUND' then cp7_vendor_receivable.refund_v1(p_payload,p_client_request_id)
    when 'REVERSE_VENDOR_REFUND' then cp7_vendor_receivable.reverse_refund_v1(p_payload,p_client_request_id)
    when 'PAY_VENDOR_DOCUMENT' then erp.bd_pay_vendor_document_v1(p_payload,p_client_request_id)
    when 'REVERSE_VENDOR_SETTLEMENT' then erp.bd_reverse_vendor_settlement_v1(p_payload,p_client_request_id)
    else erp.bd_save_master_v1(v_action,p_payload,p_client_request_id) end;
  v_result:=jsonb_build_object('action',v_action,'request_id',p_client_request_id,'status','SAVED')||v_result;
  insert into erp.bd_requests_v1(request_id,action,actor,payload,response) values(p_client_request_id,v_action,erp.current_app_user_id(),p_payload,v_result);
  return v_result;
end;$function$;
CREATE OR REPLACE FUNCTION erp.get_laundry_bd_workspace_v1(p_filters jsonb)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare v_vendor uuid;v_now timestamptz:=statement_timestamp();v_money boolean;v_as_of timestamptz:=statement_timestamp();
  v_invoice_page jsonb;v_receipt_page jsonb;v_invoice_after uuid;v_receipt_after uuid;
begin
  perform erp.require_permission('production.laundry.view');
  if jsonb_typeof(coalesce(p_filters,'{}'::jsonb)) is distinct from 'object' then raise exception 'BD_FILTER_INVALID: filter wajib objek';end if;
  v_vendor:=erp.bd_uuid_v1(coalesce(p_filters,'{}'::jsonb),'vendor_id',false);
  v_money:=erp.has_permission('finance.hpp.view') or erp.has_permission('finance.hpp.manage');
  perform erp._cp3_assert_closed_json_object(coalesce(p_filters,'{}'::jsonb),array[]::text[],
    array['vendor_id','invoice_after','receipt_after','page_as_of'],'BD workspace filter');
  v_invoice_after:=erp.bd_uuid_v1(p_filters,'invoice_after',false);v_receipt_after:=erp.bd_uuid_v1(p_filters,'receipt_after',false);
  if p_filters ? 'page_as_of' then
    if jsonb_typeof(p_filters->'page_as_of') is distinct from 'string' or length(p_filters->>'page_as_of')>40
       or p_filters->>'page_as_of'!~'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$' then
      raise exception 'BD_PAGE_INVALID: waktu daftar tidak valid';end if;
    v_as_of:=(p_filters->>'page_as_of')::timestamptz;
    if v_as_of>v_now then raise exception 'BD_PAGE_INVALID: waktu daftar di masa depan';end if;
  elsif v_invoice_after is not null or v_receipt_after is not null then
    raise exception 'BD_PAGE_INVALID: kelanjutan memerlukan waktu daftar asal';
  end if;
  if v_money then
    v_invoice_page:=erp.bd_invoice_page_v1(v_vendor,v_invoice_after,v_as_of);
    if v_vendor is not null then v_receipt_page:=erp.bd_receipt_page_v1(v_vendor,v_receipt_after,v_as_of);end if;
  end if;
  return jsonb_build_object(
    'redye_services',erp.be_redye_workspace_v1(v_vendor,v_money),
    'filters',coalesce(p_filters,'{}'::jsonb),'money_visible',v_money,'deferred_details_supported',true,
    'vendor_receivable_contract','cp7.vendor-receivable.v1',
    'vendor_receivable_accounts',case when v_money then cp7_vendor_receivable.accounts_v1()end,
    'can_manage_master',erp.current_app_role() in('OWNER','ADMIN') and erp.has_permission('master.partner.manage'),
    'can_set_price',erp.current_app_role() in('OWNER','ADMIN') and erp.has_permission('finance.hpp.manage'),
    'is_owner',erp.current_app_role()='OWNER',
    'policies',(select jsonb_agg(jsonb_build_object('key',replace(policy_key,'_','-'),'status',status,'value',value,'version',version::text,
        'set_at',to_char(set_at at time zone 'Asia/Jakarta','YYYY-MM-DD"T"HH24:MI:SS'),'reason',reason) order by policy_key) from erp.bd_policy_settings_v1),
    'vendors',coalesce((select jsonb_agg(jsonb_build_object('id',v.id,'code',v.vendor_code,'name',v.vendor_name,
        'pricing_mode',coalesce(t.pricing_mode,'RATE'),'pricing_unit',coalesce(t.pricing_unit,'PCS'),
        'bd_priced',t.pricing_mode is distinct from null and (t.pricing_mode<>'RATE' or t.pricing_unit<>'PCS' or t.minimum_charge is not null)
          or exists(select 1 from erp.bd_laundry_scoped_rates_v1 r where r.vendor_id=v.id),
        'minimum_charge',case when v_money then t.minimum_charge::numeric(18,2)::text end,'terms_version',coalesce(t.row_version,0)::text) order by v.vendor_name,v.id)
      from erp.laundry_vendors v left join erp.bd_laundry_vendor_terms_v1 t on t.vendor_id=v.id where v.is_active),'[]'::jsonb),
    'processes',coalesce((select jsonb_agg(jsonb_build_object('id',w.id,'code',w.process_code,'name',w.process_name) order by w.process_name,w.id)
      from erp.wash_processes w where w.is_active),'[]'::jsonb),
    'components',coalesce((select jsonb_agg(jsonb_build_object('id',c.id,'vendor_id',c.vendor_id,'code',c.component_code,'name',c.component_name,
        'is_active',c.is_active,'current',(select jsonb_build_object('status',r.rate_status,'rate',case when v_money then r.rate_per_pcs::numeric(18,2)::text end,
          'reason',r.reason,'version_id',r.id,'from',to_char(r.effective_from at time zone 'Asia/Jakarta','YYYY-MM-DD"T"HH24:MI:SS'))
          from erp.bd_laundry_component_rates_v1 r where r.component_id=c.id and r.effective_from<=v_now and (r.effective_to is null or r.effective_to>v_now)))
        order by c.component_name,c.id)
      from erp.bd_laundry_components_v1 c where v_vendor is null or c.vendor_id=v_vendor),'[]'::jsonb),
    'packages',coalesce((select jsonb_agg(jsonb_build_object('id',p.id,'vendor_id',p.vendor_id,'code',p.package_code,'name',p.package_name,'is_active',p.is_active,
        'component_ids',(select coalesce(jsonb_agg(pc.component_id order by pc.component_id),'[]'::jsonb) from erp.bd_laundry_package_components_v1 pc where pc.package_id=p.id),
        'current_rate',(select case when v_money then r.rate_per_pcs::numeric(18,2)::text end from erp.bd_laundry_package_rates_v1 r
          where r.package_id=p.id and r.effective_from<=v_now and (r.effective_to is null or r.effective_to>v_now))) order by p.package_name,p.id)
      from erp.bd_laundry_packages_v1 p where v_vendor is null or p.vendor_id=v_vendor),'[]'::jsonb),
    'process_rates',coalesce((select jsonb_agg(jsonb_build_object('id',r.id,'vendor_id',r.vendor_id,'wash_process_id',r.wash_process_id,
        'rate',case when v_money then r.rate_per_pcs::numeric(18,2)::text end,'from',to_char(r.effective_from at time zone 'Asia/Jakarta','YYYY-MM-DD"T"HH24:MI:SS'),
        'to',to_char(r.effective_to at time zone 'Asia/Jakarta','YYYY-MM-DD"T"HH24:MI:SS')) order by r.vendor_id,r.wash_process_id,r.effective_from)
      from erp.laundry_vendor_rate_versions r where (v_vendor is null or r.vendor_id=v_vendor) and (r.effective_to is null or r.effective_to>v_now - interval '120 days')),'[]'::jsonb),
    'scoped_rates',coalesce((select jsonb_agg(jsonb_build_object('id',r.id,'vendor_id',r.vendor_id,'wash_process_id',r.wash_process_id,'scope',r.scope,
        'model_id',r.model_id,'size_id',r.size_id,'color_name',r.color_name,'rate',case when v_money then r.rate_per_pcs::numeric(18,2)::text end,
        'from',to_char(r.effective_from at time zone 'Asia/Jakarta','YYYY-MM-DD"T"HH24:MI:SS')) order by r.created_at)
      from erp.bd_laundry_scoped_rates_v1 r where v_vendor is null or r.vendor_id=v_vendor),'[]'::jsonb),
    -- Amounts of a priced delivery only for money readers (quantities, labels and price status for everyone).
    'priced_deliveries',coalesce((select jsonb_agg(case when v_money then x.j else (x.j-'total_known')||jsonb_build_object(
        'charges',(select coalesce(jsonb_agg(c-'unit_rate'-'amount' order by (c->>'line_no')::integer),'[]'::jsonb) from jsonb_array_elements(x.j->'charges') c),
        'sizes',(select coalesce(jsonb_agg(s-'known_amount' order by s->>'size_id'),'[]'::jsonb) from jsonb_array_elements(x.j->'sizes') s)) end
      order by x.at desc) from (
        select erp.bd_priced_line_json_v1(p.delivery_line_id)||jsonb_build_object('delivery_number',d.delivery_number,'status',d.status,
          'physical_local',to_char(d.physical_at at time zone 'Asia/Jakarta','YYYY-MM-DD"T"HH24:MI:SS')) j,d.physical_at at
        from erp.bd_laundry_priced_lines_v1 p join erp.laundry_deliveries d on d.id=p.delivery_id
        where v_vendor is null or p.vendor_id=v_vendor order by d.physical_at desc limit 50) x),'[]'::jsonb),
    -- ALL-W05: laundry work returned before cutover and not yet billed (billed later by an invoice line with opening_uninvoiced_id).
    'opening_uninvoiced',coalesce((select jsonb_agg(jsonb_build_object('id',u.id,'vendor_id',u.vendor_id,'vendor_code',v.vendor_code,
        'document_number',u.document_number,'receipt_date',u.receipt_date,'category',u.category,'qty',u.qty,'billed',erp.bd_opening_billed_v1(u.id),
        'estimate_status',case when u.estimated_amount is null then 'UNKNOWN' else 'KNOWN' end,
        'estimated_amount',case when v_money then u.estimated_amount::text end,'released',case when v_money then erp.bd_opening_released_v1(u.id)::numeric(18,2)::text end,
        'invoiced',erp.bd_opening_invoiced_v1(u.id),'po_number',(select po_number from erp.production_orders where id=u.po_id),
        'dispatch_number',u.dispatch_number,'row_version',u.row_version::text) order by u.receipt_date,u.document_number,u.category)
      from erp.bd_opening_laundry_uninvoiced_v1 u join erp.laundry_vendors v on v.id=u.vendor_id where v_vendor is null or u.vendor_id=v_vendor),'[]'::jsonb),
    -- Money readers only (null otherwise: hidden, never empty): the latest invoices and, for one vendor, the receipt lines it
    -- can still bill (capacity and billed quantity per category), and the accounts the owner may pick in LAU-DEC03/06.
    'invoices',case when v_money then v_invoice_page->'items' end,
    'billable_receipts',case when v_money and v_vendor is not null then v_receipt_page->'items' end,
    'pagination',jsonb_build_object('as_of',to_char(v_as_of at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"'),
      'invoice_next',v_invoice_page->'next_id','receipt_next',v_receipt_page->'next_id'),
    'accounts',case when v_money then coalesce((select jsonb_agg(jsonb_build_object('id',a.id,'code',a.account_code,'name',a.account_name,'type',a.account_type)
        order by a.account_code) from erp.chart_accounts a where a.is_active and a.is_postable and a.account_type in('ASSET','EXPENSE')),'[]'::jsonb) end,
    -- D12: the payment screen of one vendor (money readers only): documents with cash, claim credit and remaining, claim credits,
    -- and the ledger check.
    'payables',case when v_money and v_vendor is not null then erp.bd_vendor_payables_v1(v_vendor) end,
    -- LAU-DEC04 ALLOW_PENDING (owner decision no. 11): goods and sales whose HPP is not final while a laundry price is unknown.
    'pending_cost',erp.bd_pending_cost_json_v1(v_vendor,v_money),
    -- OW-08b: failed washes recorded with an unknown vendor price (waiting first), and their price history.
    'failed_wash_prices',cp7_laundry_unknown_wash.workspace_v1(v_vendor,v_money));
end;$function$;
do $wash_pin$ begin if exists (select from (values ('erp.bd_lot_laundry_unknown_v1(uuid)','992dd3d05771eb2e15c0dc03f2427478123ac23f0300798b62aac9ba9d97adf5'),('erp.bd_pending_cost_json_v1(uuid,boolean)','14779e4a7038cbac376646a0d4d1a8c03343a5e84bc514e29fdadfd7e313e30f'),('erp.bd_save_invoice_draft_v1(jsonb,uuid)','71c4f265e8e0a6d18f3acad0424351a89625f601c15ec4ae3dce69bfc72167f7'),('erp.get_laundry_bd_workspace_v1(jsonb)','c7edefcd1474aa91d41959cef94f205ebff06a6cd52efef288b086b7622675ce'),('erp.guard_cp6_laundry_receipt_lineage_on_post_v2620()','5ca896f857948b86e4b69659b96a98aaab5af10d2342c0730994d6b37208c931'),('erp.period_blockers_v1(date,date)','660b597625786b93f58c4013c29af0ad3c6b02fe4702485bc0ad0f3896dcc6ff'),('erp.rebuild_po_hpp(uuid,text)','4d71f86c412af779d08fff9981adf8975d90234a026f8cbd69593d6ac0eb3736'),('erp.save_laundry_bd_action_v1(text,jsonb,uuid)','43f6b77b82306c46adc252da805bcd351fa7bbadcaaf1f44f283af17372b62be'),('erp.save_laundry_qc_action_v1(text,jsonb,uuid,bigint)','3abfed389022e1e7ae37a03b42ffb761d189180ba281d18dfde608e73f94cff1'),('erp.validate_laundry_receipt_line()','0d925d9b60af6c2c4baee09e0a998213485b1196adfd617171760528de91abf6')) wanted(sig,sha) left join pg_proc p
         on p.oid=to_regprocedure(sig) where p.oid is null or p.proowner<>'postgres'::regrole or encode(sha256(convert_to(pg_get_functiondef(p.oid),'UTF8')),'hex')<>wanted.sha)
         then raise exception 'Deferred wash financial routine differs from its qualified source';end if;end $wash_pin$;
