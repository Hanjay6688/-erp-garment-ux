-- R3-04 (Sol KNOWN-R2-POOL-UI S1, Astra ASTRA-C17-07 remainder; owner D16-1, 16 Okt 2026: "selesain biar gausa
-- sembunyiin"): the attendance HPP pool lifecycle from the connected "HPP & Rekalkulasi" page.
--
-- The accepted Native writers own every business write and are not redefined here:
--   erp.create_attendance_hpp_pool_v1(jsonb,uuid)                DRAFT (optionally correcting a CANCELLED pool)
--   erp.activate_attendance_hpp_pool_v1(uuid,text,uuid,bigint)   ACTIVE: ATTENDANCE_HPP_POOL journal, HPP of the POs rebuilt
--   erp.cancel_attendance_hpp_pool_v1(uuid,text,uuid,bigint)     DRAFT -> VOIDED; ACTIVE -> CANCELLED with the reversal journal
-- (status vocabulary DRAFT/ACTIVE/CANCELLED/VOIDED: attendance_hpp_pools_status_check of v2.6.14c). The read lists the pools
-- newest first (bounded), the attendance payroll periods, the accounting closed-through date and, for a chosen period, the
-- Native preview erp.preview_attendance_hpp_pool_v1 or its refusal as a plain blocker without figures.
-- The command adds what the Native writers do not check themselves:
--   * closed books: a period ending on or before erp.accounting_period_control.closed_through is refused for every action
--     (the Native journal writer would move the posting date instead); the control row is read FOR SHARE, so a close in
--     flight waits for the command and the command waits for a close in flight;
--   * a review token of exactly what the user reviewed (the preview manifest and figures, or the pool row) that must still
--     match after the locks;
--   * the current Owner/Admin right with finance.hpp.view and finance.hpp.manage, checked before and after the locks;
--   * a reason of 5 to 1000 characters, and a stable request id per (actor, request) kept in an insert-only table: the
--     same request replays its first answer, a changed payload under the same id is refused.
-- Every function here is owned by postgres; the two public wrappers are owned by NOLOGIN roles that may execute only their
-- own entry function. No erp object is granted or changed. Uninstall: drop owned by both roles (the schema goes with them).
create role cp7_hpp_pool_read nologin noinherit nosuperuser nocreatedb nocreaterole noreplication;
create role cp7_hpp_pool_write nologin noinherit nosuperuser nocreatedb nocreaterole noreplication;
create schema cp7_hpp_pool authorization cp7_hpp_pool_read;
revoke all on schema cp7_hpp_pool from public,anon,authenticated,service_role,cp7_capture;
grant usage on schema cp7_hpp_pool to postgres,cp7_hpp_pool_write;
create table cp7_hpp_pool.requests(
 actor uuid not null,request_id uuid not null,action text not null check(action in('CREATE','ACTIVATE','CANCEL')),payload jsonb not null,
 response jsonb not null,pool_id uuid not null,app_user uuid not null,recorded_at timestamptz not null default clock_timestamp(),
 primary key(actor,request_id)
);
alter table cp7_hpp_pool.requests owner to postgres;
alter table cp7_hpp_pool.requests enable row level security;
create policy private_requests on cp7_hpp_pool.requests for all using(false)with check(false);
revoke all on all tables in schema cp7_hpp_pool from public,anon,authenticated,service_role,cp7_capture,cp7_hpp_pool_read,cp7_hpp_pool_write;

-- A request row is written once, with its answer, in the transaction of the command; it is never changed or removed.
create function cp7_hpp_pool.immutable()returns trigger
language plpgsql security invoker set search_path=''as $$
begin raise exception 'CP7_HPP_POOL_REQUESTS_IMMUTABLE';end $$;
create trigger requests_immutable before update or delete on cp7_hpp_pool.requests
 for each row execute function cp7_hpp_pool.immutable();
create trigger requests_immutable_truncate before truncate on cp7_hpp_pool.requests
 for each statement execute function cp7_hpp_pool.immutable();

create function cp7_hpp_pool.iso(p_at timestamptz)returns text
language sql stable set search_path=''as $$
 select case when p_at is null then null else to_char(p_at at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"')end$$;

-- What the user reviewed for an existing pool: its whole lifecycle state (any change of status, version or figures changes it).
create function cp7_hpp_pool.pool_token(p_pool erp.attendance_hpp_pools)returns text
language sql stable set search_path=''as $$
 select md5(jsonb_build_array('cp7.hpp-pool-row.v1',(p_pool).id,(p_pool).status,(p_pool).row_version,(p_pool).period_start,(p_pool).period_end,
  (p_pool).source_manifest_sha256,(p_pool).numerator_amount::text,(p_pool).denominator_qty,(p_pool).unit_cost_per_sewn_pcs::text,
  (p_pool).correction_of_pool_id,(p_pool).post_journal_entry_id,(p_pool).cancellation_journal_entry_id)::text)$$;

-- What the user reviewed before a draft: the Native manifest hash and the figures the draft will store.
create function cp7_hpp_pool.preview_token(p_start date,p_end date,p_sha text,p_numerator text,p_denominator bigint,p_unit text)returns text
language sql stable set search_path=''as $$
 select md5(jsonb_build_array('cp7.hpp-pool-preview.v1',p_start,p_end,p_sha,p_numerator,p_denominator,p_unit)::text)$$;

create function cp7_hpp_pool.access_now(p_manage boolean)returns jsonb
language plpgsql volatile security definer set search_path=''as $$
declare v_access jsonb;v_view boolean;v_manage boolean;
begin
 if auth.uid()is null or coalesce(auth.jwt()->>'role','')<>'authenticated'then
  raise exception using errcode='42501',message='CP7_HPP_POOL_DENIED: pool HPP absensi hanya untuk Owner atau Admin yang masuk dengan akunnya sendiri.';end if;
 v_access:=erp.get_my_access_v1();
 v_view:=erp.has_permission('finance.hpp.view');v_manage:=erp.has_permission('finance.hpp.manage');
 if v_access->'allowed'is distinct from'true'::jsonb or coalesce(v_access->'profile'->>'role_code','')not in('OWNER','ADMIN')or not v_view
  or(p_manage and not v_manage)then
  raise exception using errcode='42501',message='CP7_HPP_POOL_DENIED: pool HPP absensi hanya untuk Owner atau Admin; membuat, mengaktifkan, dan membatalkan pool juga perlu hak HPP & Rekalkulasi "Rekalkulasi".';end if;
 return jsonb_build_object('profile',v_access->'profile','view',v_view,'manage',v_manage);
end $$;

-- The Native preview for one exact period, or its refusal as a plain blocker (code and the Native sentence, no figures).
-- It also names the DRAFT/ACTIVE pool that already owns the period and the cancelled pools a replacement may correct.
create function cp7_hpp_pool.preview(p_start date,p_end date,p_closed date)returns jsonb
language plpgsql volatile security definer set search_path=''as $$
declare v_native jsonb;v_message text;v_code text;v_existing jsonb;v_cancelled jsonb;v_pos jsonb;v_po_count integer;v_numerator text;
 v_denominator bigint;v_unit text;v_sha text;v_period_closed boolean;
begin
 v_period_closed:=p_closed is not null and p_end<=p_closed;
 select jsonb_build_object('id',hp.id,'pool_number',hp.pool_number,'status',hp.status)into v_existing
  from erp.attendance_hpp_pools hp where hp.period_start=p_start and hp.period_end=p_end and hp.status in('DRAFT','ACTIVE')
  order by hp.created_at desc,hp.id desc limit 1;
 select coalesce(jsonb_agg(jsonb_build_object('id',cx.id,'pool_number',cx.pool_number)order by cx.created_at desc,cx.id desc),'[]'::jsonb)into v_cancelled
  from(select hp.id,hp.pool_number,hp.created_at from erp.attendance_hpp_pools hp where hp.period_start=p_start and hp.period_end=p_end
   and hp.status='CANCELLED' order by hp.created_at desc,hp.id desc limit 10)cx;
 begin
  v_native:=erp.preview_attendance_hpp_pool_v1(p_start,p_end);
 exception when raise_exception then
  v_message:=sqlerrm;v_native:=null;
 end;
 if v_native is null then
  v_code:=case when v_message like '%lack one explicit HPP policy%'then'MISSING_POLICY'
   when v_message like '%do not reconcile to immutable attendance items%'then'ATTENDANCE_MISMATCH'
   when v_message like '%lack one unambiguous WIP debit line%'then'JOURNAL_UNCLEAR'
   when v_message like 'No eligible normal-Mandor attendance payroll cost%'then'NO_ATTENDANCE_COST'
   when v_message like 'POSITIVE_POOL_ZERO_SEWING_OUTPUT%'then'NO_SEWING_OUTPUT'
   else'OTHER'end;
  return jsonb_build_object('period_start',p_start,'period_end',p_end,'status','BLOCKED','period_closed',v_period_closed,'existing_pool',v_existing,
   'cancelled_pools',v_cancelled,'numerator_amount',null,'denominator_qty',null,'unit_cost_per_sewn_pcs',null,'source_count',null,
   'destination_count',null,'po_count',null,'pos','[]'::jsonb,'manifest_sha256',null,'review_token',null,
   'blocker',jsonb_build_object('code',v_code,'message',left(coalesce(v_message,''),500)),'can_create',false);
 end if;
 if v_native->>'status'is distinct from'READY'or jsonb_typeof(v_native->'manifest')is distinct from'object'then
  raise exception 'CP7_HPP_POOL_PREVIEW_SHAPE';end if;
 v_sha:=v_native->>'manifest_sha256';
 -- Exactly what the Native create stores: numeric(20,2) and numeric(28,12) of the Native preview values.
 v_numerator:=((v_native->>'numerator_amount')::numeric(20,2))::text;
 v_denominator:=(v_native->>'denominator_qty')::bigint;
 v_unit:=((v_native->>'unit_cost_per_sewn_pcs')::numeric(28,12))::text;
 select count(*)::integer,coalesce(jsonb_agg(jsonb_build_object('po_id',py.po_id,'po_number',py.po_number,'sewing_qty',py.qty)order by py.n)filter(where py.n<=20),'[]'::jsonb)
  into v_po_count,v_pos
  from(select pd.po_id,po.po_number,pd.qty,row_number()over(order by po.po_number,pd.po_id)n
   from(select(dx->>'po_id')::uuid po_id,sum((dx->>'sewing_qty')::bigint)::bigint qty from jsonb_array_elements(v_native->'manifest'->'destinations')dx group by 1)pd
   left join erp.production_orders po on po.id=pd.po_id)py;
 return jsonb_build_object('period_start',p_start,'period_end',p_end,'status','READY','period_closed',v_period_closed,'existing_pool',v_existing,
  'cancelled_pools',v_cancelled,'numerator_amount',v_numerator,'denominator_qty',v_denominator,'unit_cost_per_sewn_pcs',v_unit,
  'source_count',jsonb_array_length(v_native->'manifest'->'sources'),'destination_count',jsonb_array_length(v_native->'manifest'->'destinations'),
  'po_count',v_po_count,'pos',v_pos,'manifest_sha256',v_sha,
  'review_token',cp7_hpp_pool.preview_token(p_start,p_end,v_sha,v_numerator,v_denominator,v_unit),'blocker',null,
  'can_create',not v_period_closed and v_existing is null);
end $$;

-- One pool as the screen shows it: figures, cost per PO (bounded), who and why at each step, the correction chain, and the
-- actions the server would accept now (none while the books of its period are closed; a DRAFT whose Native validation
-- fails can only be removed).
create function cp7_hpp_pool.pool_json(p_pool erp.attendance_hpp_pools,p_closed date)returns jsonb
language plpgsql volatile security definer set search_path=''as $$
declare v_alloc jsonb;v_po_count integer;v_sources integer;v_correction jsonb;v_replaced jsonb;v_open boolean;v_stale text;v_actions text[]:='{}';
 v_closed boolean;v_activation text;v_journal text;v_reversal text;
begin
 v_closed:=p_closed is not null and p_pool.period_end<=p_closed;
 select count(*)::integer into v_sources from erp.attendance_hpp_pool_sources ps where ps.pool_id=p_pool.id;
 select count(*)::integer,coalesce(jsonb_agg(jsonb_build_object('po_id',ay.po_id,'po_number',ay.po_number,'sewing_qty',ay.qty,'amount',ay.amount)order by ay.n)
   filter(where ay.n<=20),'[]'::jsonb)
  into v_po_count,v_alloc
  from(select ag.po_id,po.po_number,ag.qty,ag.amount,row_number()over(order by po.po_number,ag.po_id)n
   from(select al.po_id,sum(al.sewing_qty)::bigint qty,sum(al.allocated_amount)::numeric(20,2)::text amount
    from erp.attendance_hpp_pool_allocations al where al.pool_id=p_pool.id group by al.po_id)ag
   left join erp.production_orders po on po.id=ag.po_id)ay;
 select jsonb_build_object('id',hp.id,'pool_number',hp.pool_number,'status',hp.status)into v_correction
  from erp.attendance_hpp_pools hp where hp.id=p_pool.correction_of_pool_id;
 select coalesce(jsonb_agg(jsonb_build_object('id',rx.id,'pool_number',rx.pool_number,'status',rx.status)order by rx.created_at,rx.id),'[]'::jsonb)into v_replaced
  from(select hp.id,hp.pool_number,hp.status,hp.created_at from erp.attendance_hpp_pools hp where hp.correction_of_pool_id=p_pool.id
   order by hp.created_at,hp.id limit 5)rx;
 v_open:=exists(select 1 from erp.attendance_hpp_pools hp where hp.id<>p_pool.id and hp.period_start=p_pool.period_start
  and hp.period_end=p_pool.period_end and hp.status in('DRAFT','ACTIVE'));
 select lg.change_reason into v_activation from erp.audit_logs lg where lg.entity_type='attendance_hpp_pools'and lg.entity_id=p_pool.id
  and lg.new_data->>'lifecycle_action'='ACTIVATE' order by lg.changed_at desc,lg.id desc limit 1;
 select je.journal_number into v_journal from erp.journal_entries je where je.id=p_pool.post_journal_entry_id;
 select je.journal_number into v_reversal from erp.journal_entries je where je.id=p_pool.cancellation_journal_entry_id;
 if p_pool.status='DRAFT'then
  begin
   perform erp.validate_attendance_hpp_pool_v1(p_pool.id);
  exception when raise_exception then v_stale:=left(sqlerrm,500);
  end;
 end if;
 if not v_closed then
  if p_pool.status='DRAFT'then v_actions:=case when v_stale is null then array['ACTIVATE','CANCEL']else array['CANCEL']end;
  elsif p_pool.status='ACTIVE'then v_actions:=array['CANCEL'];
  elsif p_pool.status='CANCELLED'and not v_open then v_actions:=array['REPLACE'];
  end if;
 end if;
 return jsonb_build_object('id',p_pool.id,'pool_number',p_pool.pool_number,'status',p_pool.status,'period_start',p_pool.period_start,
  'period_end',p_pool.period_end,'numerator_amount',p_pool.numerator_amount::text,'denominator_qty',p_pool.denominator_qty,
  'unit_cost_per_sewn_pcs',p_pool.unit_cost_per_sewn_pcs::text,'source_count',v_sources,'po_count',v_po_count,'allocations',v_alloc,
  'correction_of',v_correction,'replaced_by',v_replaced,
  'created_at',cp7_hpp_pool.iso(p_pool.created_at),'created_by',(select u.full_name from erp.app_users u where u.id=p_pool.created_by),
  'reason',p_pool.reason,
  'activated_at',cp7_hpp_pool.iso(p_pool.activated_at),'activated_by',(select u.full_name from erp.app_users u where u.id=p_pool.activated_by),
  'activation_reason',v_activation,
  'cancelled_at',cp7_hpp_pool.iso(p_pool.cancelled_at),'cancelled_by',(select u.full_name from erp.app_users u where u.id=p_pool.cancelled_by),
  'cancellation_reason',p_pool.cancellation_reason,'journal_number',v_journal,'reversal_journal_number',v_reversal,
  'row_version',p_pool.row_version,'review_token',cp7_hpp_pool.pool_token(p_pool),'period_closed',v_closed,
  'stale',v_stale is not null,'stale_message',v_stale,'actions',to_jsonb(v_actions));
end $$;

create function cp7_hpp_pool.workspace(p_offset integer,p_limit integer,p_start date,p_end date)returns jsonb
language plpgsql volatile security definer set search_path=''as $$
declare v_access jsonb;v_closed date;v_total integer;v_pools jsonb:='[]'::jsonb;v_periods jsonb;v_preview jsonb;v_row erp.attendance_hpp_pools;
begin
 v_access:=cp7_hpp_pool.access_now(false);
 if p_offset is null or p_offset<0 or p_offset>1000000 or p_limit is null or p_limit not between 1 and 50
  or(p_start is null)<>(p_end is null)or(p_start is not null and(p_end<p_start or p_end-p_start>366))then
  raise exception 'CP7_HPP_POOL_FIELDS: periode pratinjau harus berisi tanggal mulai dan akhir (akhir tidak sebelum mulai, paling lama 367 hari); halaman paling banyak 50 pool.';end if;
 select c.closed_through into v_closed from erp.accounting_period_control c where c.singleton_id=1;
 select count(*)::integer into v_total from erp.attendance_hpp_pools;
 for v_row in select*from erp.attendance_hpp_pools hp order by hp.created_at desc,hp.id desc offset p_offset limit p_limit loop
  v_pools:=v_pools||jsonb_build_array(cp7_hpp_pool.pool_json(v_row,v_closed));
 end loop;
 -- The 20 latest periods of approved or paid attendance payrolls (the Native pool takes one exact payroll period).
 select coalesce(jsonb_agg(jsonb_build_object('period_start',px.period_start,'period_end',px.period_end,'payroll_count',px.n,
   'pool',(select jsonb_build_object('id',hp.id,'pool_number',hp.pool_number,'status',hp.status)from erp.attendance_hpp_pools hp
     where hp.period_start=px.period_start and hp.period_end=px.period_end and hp.status in('DRAFT','ACTIVE')order by hp.created_at desc,hp.id desc limit 1))
   order by px.period_end desc,px.period_start desc),'[]'::jsonb)into v_periods
  from(select ps.period_start,ps.period_end,count(*)::integer n from erp.payroll_settlements ps
   where ps.status in('APPROVED','PAID')and ps.attendance_total>0 group by ps.period_start,ps.period_end
   order by ps.period_end desc,ps.period_start desc limit 20)px;
 if p_start is not null then v_preview:=cp7_hpp_pool.preview(p_start,p_end,v_closed);end if;
 if cp7_hpp_pool.access_now(false)is distinct from v_access then
  raise exception using errcode='42501',message='CP7_HPP_POOL_ACCESS_CHANGED: hak akses berubah saat data dibaca. Muat ulang halaman.';end if;
 return jsonb_build_object('contract_version','cp7.hpp-pools.v1','business_DML',false,'captured_at',cp7_hpp_pool.iso(statement_timestamp()),
  'offset',p_offset,'limit',p_limit,'total',v_total,
  'next_offset',case when p_offset+jsonb_array_length(v_pools)<v_total then p_offset+jsonb_array_length(v_pools)end,
  'closed_through',v_closed,'can_manage',(v_access->>'manage')::boolean,'pools',v_pools,'periods',v_periods,'preview',v_preview);
end $$;

create function cp7_hpp_pool.command(p_action text,p_payload jsonb,p_request uuid)returns jsonb
language plpgsql volatile security definer set search_path=''as $$
declare v_access jsonb;v_actor uuid;v_user uuid;v_keys text[];v_reason text;v_saved cp7_hpp_pool.requests;v_closed date;v_start date;v_end date;
 v_correction uuid;v_preview jsonb;v_native jsonb;v_pool erp.attendance_hpp_pools;v_target uuid;v_expected text;v_answer jsonb;v_stale text;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 v_access:=cp7_hpp_pool.access_now(true);v_actor:=auth.uid();
 if p_request is null or p_action is null or p_action not in('CREATE','ACTIVATE','CANCEL')or jsonb_typeof(p_payload)is distinct from'object'then
  raise exception 'CP7_HPP_POOL_FIELDS: tindakan harus CREATE, ACTIVATE, atau CANCEL dengan isian lengkap dan nomor permintaan.';end if;
 v_keys:=case when p_action='CREATE'then array['period_start','period_end','correction_of_pool_id','review_token','reason']
  else array['pool_id','review_token','reason']end;
 if not(p_payload?&v_keys)or exists(select 1 from jsonb_object_keys(p_payload)k where k<>all(v_keys))
  or jsonb_typeof(p_payload->'review_token')is distinct from'string'or(p_payload->>'review_token')!~'^[a-f0-9]{32}$'
  or jsonb_typeof(p_payload->'reason')is distinct from'string'or length(btrim(p_payload->>'reason'))not between 5 and 1000 then
  raise exception 'CP7_HPP_POOL_FIELDS: isian tidak lengkap atau ada isian lain; alasan wajib diisi 5 sampai 1000 huruf.';end if;
 if p_action='CREATE'then
  if jsonb_typeof(p_payload->'period_start')is distinct from'string'or jsonb_typeof(p_payload->'period_end')is distinct from'string'
   or(p_payload->>'period_start')!~'^[0-9]{4}-[0-9]{2}-[0-9]{2}$'or(p_payload->>'period_end')!~'^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
   or jsonb_typeof(p_payload->'correction_of_pool_id')not in('string','null')
   or(jsonb_typeof(p_payload->'correction_of_pool_id')='string'
    and(p_payload->>'correction_of_pool_id')!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')then
   raise exception 'CP7_HPP_POOL_FIELDS: periode harus tanggal YYYY-MM-DD; pool yang diganti boleh kosong.';end if;
  begin
   v_start:=(p_payload->>'period_start')::date;v_end:=(p_payload->>'period_end')::date;
  exception when others then raise exception 'CP7_HPP_POOL_FIELDS: tanggal periode tidak ada di kalender.';
  end;
  if to_char(v_start,'YYYY-MM-DD')<>p_payload->>'period_start'or to_char(v_end,'YYYY-MM-DD')<>p_payload->>'period_end'
   or v_end<v_start or v_end-v_start>366 then
   raise exception 'CP7_HPP_POOL_FIELDS: akhir periode tidak boleh sebelum awalnya, paling lama 367 hari.';end if;
  v_correction:=(p_payload->>'correction_of_pool_id')::uuid;
 else
  if jsonb_typeof(p_payload->'pool_id')is distinct from'string'
   or(p_payload->>'pool_id')!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'then
   raise exception 'CP7_HPP_POOL_FIELDS: pool yang dipilih tidak dikenal.';end if;
  v_target:=(p_payload->>'pool_id')::uuid;
 end if;
 v_reason:=btrim(p_payload->>'reason');
 -- One answer per (actor, request): a resend waits for the first and returns its answer.
 perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('cp7.hpp_pool.request:'||v_actor::text||':'||p_request::text,0));
 select*into v_saved from cp7_hpp_pool.requests rq where rq.actor=v_actor and rq.request_id=p_request;
 if found then
  if v_saved.action<>p_action or v_saved.payload<>p_payload then
   raise exception 'CP7_HPP_POOL_REQUEST_CHANGED: nomor permintaan ini sudah dipakai untuk isian lain. Periksa hasil permintaan sebelumnya.';end if;
  if cp7_hpp_pool.access_now(true)is distinct from v_access then
   raise exception using errcode='42501',message='CP7_HPP_POOL_ACCESS_CHANGED: hak akses berubah saat permintaan diproses. Muat ulang halaman.';end if;
  return v_saved.response;
 end if;
 v_user:=erp.current_app_user_id();
 if v_user is null then raise exception using errcode='42501',message='CP7_HPP_POOL_DENIED: pengguna aplikasi tidak aktif.';end if;
 -- The closed-through date under FOR SHARE: a close of the books waits for this command, this command for a close in flight.
 select c.closed_through into v_closed from erp.accounting_period_control c where c.singleton_id=1 for share;
 if p_action='CREATE'then
  if v_closed is not null and v_end<=v_closed then
   raise exception using message=format('CP7_HPP_POOL_PERIOD_CLOSED: pembukuan sudah ditutup sampai %s, sedangkan periode pool ini berakhir %s. Pool periode ini tidak bisa dibuat, diaktifkan, atau dibatalkan. Bila memang perlu dibetulkan, buka kembali periodenya di Keuangan > Laporan & Tutup Buku > tab Tutup Buku, lalu ulangi.',
    to_char(v_closed,'YYYY-MM-DD'),to_char(v_end,'YYYY-MM-DD'));end if;
  -- The Native period lock (the same advisory lock the Native create takes first) before the existence and review checks.
  perform erp._cp3_lock_business_period(v_start,v_end);
  if exists(select 1 from erp.attendance_hpp_pools hp where hp.period_start=v_start and hp.period_end=v_end and hp.status in('DRAFT','ACTIVE'))then
   raise exception 'CP7_HPP_POOL_EXISTS: periode ini sudah punya pool draf atau aktif. Aktifkan atau batalkan pool itu dulu.';end if;
  if v_correction is not null and not exists(select 1 from erp.attendance_hpp_pools hp where hp.id=v_correction and hp.status='CANCELLED'
   and hp.period_start=v_start and hp.period_end=v_end)then
   raise exception 'CP7_HPP_POOL_CORRECTION: pool pengganti hanya boleh mengganti pool yang sudah dibatalkan untuk periode yang sama persis.';end if;
  v_preview:=cp7_hpp_pool.preview(v_start,v_end,v_closed);
  if v_preview->>'status'<>'READY'then
   raise exception using message='CP7_HPP_POOL_NOT_READY: pratinjau periode ini belum siap. '||coalesce(v_preview->'blocker'->>'message','');end if;
  if v_preview->>'review_token'<>p_payload->>'review_token'then
   raise exception 'CP7_HPP_POOL_REVIEW_CHANGED: angka pratinjau berubah sejak diperiksa. Lihat pratinjau terbaru lalu periksa lagi.';end if;
  v_native:=erp.create_attendance_hpp_pool_v1(jsonb_build_object('period_start',p_payload->>'period_start','period_end',p_payload->>'period_end',
   'reason',v_reason)||case when v_correction is null then'{}'::jsonb else jsonb_build_object('correction_of_pool_id',v_correction::text)end,p_request);
  v_target:=(v_native->>'pool_id')::uuid;
  select*into v_pool from erp.attendance_hpp_pools hp where hp.id=v_target;
  if v_pool.id is null or v_pool.status<>'DRAFT'or v_pool.source_manifest_sha256 is distinct from v_preview->>'manifest_sha256'
   or v_pool.correction_of_pool_id is distinct from v_correction then raise exception 'CP7_HPP_POOL_OUTCOME_MISMATCH';end if;
 else
  select*into v_pool from erp.attendance_hpp_pools hp where hp.id=v_target for update;
  if v_pool.id is null then raise exception 'CP7_HPP_POOL_NOT_FOUND: pool tidak ditemukan. Muat ulang daftar pool.';end if;
  if v_closed is not null and v_pool.period_end<=v_closed then
   raise exception using message=format('CP7_HPP_POOL_PERIOD_CLOSED: pembukuan sudah ditutup sampai %s, sedangkan periode pool ini berakhir %s. Pool periode ini tidak bisa dibuat, diaktifkan, atau dibatalkan. Bila memang perlu dibetulkan, buka kembali periodenya di Keuangan > Laporan & Tutup Buku > tab Tutup Buku, lalu ulangi.',
    to_char(v_closed,'YYYY-MM-DD'),to_char(v_pool.period_end,'YYYY-MM-DD'));end if;
  if cp7_hpp_pool.pool_token(v_pool)<>p_payload->>'review_token'then
   raise exception 'CP7_HPP_POOL_REVIEW_CHANGED: pool ini berubah sejak diperiksa (mungkin di tab lain). Muat ulang lalu periksa lagi.';end if;
  if p_action='ACTIVATE'then
   if v_pool.status<>'DRAFT'then raise exception 'CP7_HPP_POOL_STATUS: hanya pool draf yang bisa diaktifkan.';end if;
   begin
    perform erp.validate_attendance_hpp_pool_v1(v_pool.id);
   exception when raise_exception then v_stale:=sqlerrm;
   end;
   if v_stale is not null then
    raise exception using message='CP7_HPP_POOL_SOURCE_CHANGED: data gaji absensi, kebijakan HPP mandor, atau setoran jahit periode ini berubah sejak draf dibuat. Batalkan draf ini lalu buat draf baru. ('||left(v_stale,300)||')';end if;
   perform erp.activate_attendance_hpp_pool_v1(v_pool.id,v_reason,p_request,v_pool.row_version);
   v_expected:='ACTIVE';
  else
   if v_pool.status not in('DRAFT','ACTIVE')then raise exception 'CP7_HPP_POOL_STATUS: hanya pool draf atau aktif yang bisa dibatalkan.';end if;
   v_expected:=case when v_pool.status='DRAFT'then'VOIDED'else'CANCELLED'end;
   perform erp.cancel_attendance_hpp_pool_v1(v_pool.id,v_reason,p_request,v_pool.row_version);
  end if;
  select*into v_pool from erp.attendance_hpp_pools hp where hp.id=v_target;
  if v_pool.status is distinct from v_expected then raise exception 'CP7_HPP_POOL_OUTCOME_MISMATCH';end if;
 end if;
 if cp7_hpp_pool.access_now(true)is distinct from v_access then
  raise exception using errcode='42501',message='CP7_HPP_POOL_ACCESS_CHANGED: hak akses berubah saat permintaan diproses. Muat ulang halaman.';end if;
 v_answer:=jsonb_build_object('contract_version','cp7.hpp-pool-outcome.v1','kind','COMMITTED_OUTCOME','action',p_action,'request_id',p_request,
  'pool_id',v_pool.id,'pool_number',v_pool.pool_number,'status',v_pool.status,'row_version',v_pool.row_version,
  'period_start',v_pool.period_start,'period_end',v_pool.period_end,'correction_of_pool_id',v_pool.correction_of_pool_id,
  'journal_entry_id',v_pool.post_journal_entry_id,'reversal_journal_entry_id',v_pool.cancellation_journal_entry_id);
 insert into cp7_hpp_pool.requests(actor,request_id,action,payload,response,pool_id,app_user)
  values(v_actor,p_request,p_action,p_payload,v_answer,v_pool.id,v_user);
 return v_answer;
end $$;

create function public.erp_cp7_get_hpp_pools_v1(p_offset integer,p_limit integer,p_period_start date,p_period_end date)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_hpp_pool.workspace(p_offset,p_limit,p_period_start,p_period_end)$$;
create function public.erp_cp7_save_hpp_pool_v1(p_action text,p_payload jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_hpp_pool.command(p_action,p_payload,p_request)$$;
alter function cp7_hpp_pool.immutable()owner to postgres;
alter function cp7_hpp_pool.iso(timestamptz)owner to postgres;
alter function cp7_hpp_pool.pool_token(erp.attendance_hpp_pools)owner to postgres;
alter function cp7_hpp_pool.preview_token(date,date,text,text,bigint,text)owner to postgres;
alter function cp7_hpp_pool.access_now(boolean)owner to postgres;
alter function cp7_hpp_pool.preview(date,date,date)owner to postgres;
alter function cp7_hpp_pool.pool_json(erp.attendance_hpp_pools,date)owner to postgres;
alter function cp7_hpp_pool.workspace(integer,integer,date,date)owner to postgres;
alter function cp7_hpp_pool.command(text,jsonb,uuid)owner to postgres;
grant create on schema public to cp7_hpp_pool_read,cp7_hpp_pool_write;
alter function public.erp_cp7_get_hpp_pools_v1(integer,integer,date,date)owner to cp7_hpp_pool_read;
alter function public.erp_cp7_save_hpp_pool_v1(text,jsonb,uuid)owner to cp7_hpp_pool_write;
revoke create on schema public from cp7_hpp_pool_read,cp7_hpp_pool_write;
revoke all on function cp7_hpp_pool.immutable(),cp7_hpp_pool.iso(timestamptz),cp7_hpp_pool.pool_token(erp.attendance_hpp_pools),
 cp7_hpp_pool.preview_token(date,date,text,text,bigint,text),cp7_hpp_pool.access_now(boolean),cp7_hpp_pool.preview(date,date,date),
 cp7_hpp_pool.pool_json(erp.attendance_hpp_pools,date),cp7_hpp_pool.workspace(integer,integer,date,date),cp7_hpp_pool.command(text,jsonb,uuid)
 from public,anon,authenticated,service_role,cp7_capture,cp7_hpp_pool_read,cp7_hpp_pool_write;
grant execute on function cp7_hpp_pool.workspace(integer,integer,date,date)to cp7_hpp_pool_read;
grant execute on function cp7_hpp_pool.command(text,jsonb,uuid)to cp7_hpp_pool_write;
revoke all on function public.erp_cp7_get_hpp_pools_v1(integer,integer,date,date),public.erp_cp7_save_hpp_pool_v1(text,jsonb,uuid)
 from public,anon,authenticated,service_role,cp7_capture;
grant execute on function public.erp_cp7_get_hpp_pools_v1(integer,integer,date,date),public.erp_cp7_save_hpp_pool_v1(text,jsonb,uuid)to authenticated;
