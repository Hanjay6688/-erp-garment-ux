-- CP6 BB labour part (ALL-Y02). New objects only.
-- Y02: sewing work, attendance or GOOD/BOM reimbursement earned before cutover but not approved or paid yet. Each
-- entitlement is imported with its detail (component, earned/paid/carried quantity and rate; attendance period, days and
-- rate; category, GOOD quantity and BOM rate) and names the imported CONTRACTOR_PAYABLE document that carries its money,
-- which payroll pays like ALL-Y01 (no second accrual). A component carried at cutover is not a liability yet: once the
-- owner confirms it done after cutover, its quantity enters a payroll as an OPENING_CARRY line, recognized by the ordinary
-- approval (Dr LABOR_COST / Cr CONTRACTOR_PAYABLE) and settled by the ordinary payment. No work completion, sewing
-- terminal, attendance or accessory entitlement row is written for the old period (M:369).

create table erp.bb_payroll_entitlements_v1(
  id uuid primary key default gen_random_uuid(),
  batch_id uuid not null references erp.migration_batches(id),
  source_row_id uuid not null unique references erp.migration_staging_rows(id),
  contractor_id uuid not null references erp.contractors(id),
  kind text not null check(kind in('SEWING_WORK','ATTENDANCE','ACCESSORY_REIMBURSEMENT')),
  document_number text not null check(length(btrim(document_number)) between 1 and 120),
  line_number text not null check(length(btrim(line_number)) between 1 and 60),
  document_date date not null,
  cutover_date date not null,
  balance_id uuid references erp.opening_subledger_balances(id),
  amount numeric(20,2) not null check(amount>=0),
  carry_qty numeric(18,6) not null default 0 check(carry_qty>=0),
  rate numeric(18,2) not null check(rate>=0),
  detail jsonb not null,
  created_at timestamptz not null default statement_timestamp(),
  check(document_date<=cutover_date),
  check((amount>0)=(balance_id is not null)),
  check(kind='SEWING_WORK' or carry_qty=0)
);
create unique index bb_payroll_entitlements_v1_identity on erp.bb_payroll_entitlements_v1(contractor_id,kind,lower(btrim(document_number)),lower(btrim(line_number)));
comment on table erp.bb_payroll_entitlements_v1 is 'BB (ALL-Y02): old earned but unapproved sewing work, attendance or GOOD/BOM reimbursement with its detail; the money is the linked imported CONTRACTOR_PAYABLE document; carried component quantity is paid later through OPENING_CARRY payroll lines.';
alter table erp.bb_payroll_entitlements_v1 enable row level security;
revoke all on erp.bb_payroll_entitlements_v1 from public,anon,authenticated,service_role;

alter table erp.payroll_reimbursements add column opening_carry_entitlement_id uuid references erp.bb_payroll_entitlements_v1(id);
alter table erp.payroll_reimbursements add column opening_carry_qty numeric(18,6);
alter table erp.payroll_reimbursements drop constraint payroll_reimbursements_source_type_check;
alter table erp.payroll_reimbursements add constraint payroll_reimbursements_source_type_check
  check(source_type::text=any(array['MANUAL','ACCESSORY_BOM','OPENING_PAYABLE','OPENING_CARRY']));
alter table erp.payroll_reimbursements add constraint payroll_reimbursements_opening_carry_check
  check((source_type::text='OPENING_CARRY')=(opening_carry_entitlement_id is not null and opening_carry_qty is not null and opening_carry_qty>0));
create unique index payroll_reimbursements_opening_carry_unique on erp.payroll_reimbursements(payroll_id,opening_carry_entitlement_id)
  where opening_carry_entitlement_id is not null;

-- Carried quantity already promised to or paid by a payroll that is not reversed.
CREATE OR REPLACE FUNCTION erp.bb_entitlement_carry_used_v1(p_entitlement uuid,p_except uuid DEFAULT NULL)
 RETURNS numeric LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select coalesce(sum(r.opening_carry_qty),0) from erp.payroll_reimbursements r join erp.payroll_settlements p on p.id=r.payroll_id
  where r.opening_carry_entitlement_id=p_entitlement and p.status<>'REVERSED' and r.id is distinct from p_except
$function$;

CREATE OR REPLACE FUNCTION erp.bb_guard_opening_carry_reimbursement_v1()
 RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path TO ''
AS $function$
declare p erp.payroll_settlements%rowtype;e erp.bb_payroll_entitlements_v1%rowtype;v_id uuid;
begin
  if TG_OP='DELETE' then
    if old.opening_carry_entitlement_id is null then return old;end if;
    v_id:=old.payroll_id;
  else
    if new.opening_carry_entitlement_id is null and new.source_type::text<>'OPENING_CARRY'
      and (TG_OP='INSERT' or old.opening_carry_entitlement_id is null) then return new;end if;
    v_id:=new.payroll_id;
  end if;
  if current_user<>'postgres' then raise exception 'Y02_CARRY_WRITER: komponen carry masuk payroll hanya lewat command resmi';end if;
  perform erp.require_internal();
  if TG_OP='UPDATE' and (new.payroll_id<>old.payroll_id or new.opening_carry_entitlement_id is distinct from old.opening_carry_entitlement_id
      or new.source_type is distinct from old.source_type) then
    raise exception 'Y02_CARRY_WRITER: sumber carry payroll tidak dapat dipindah; lepaskan lalu pilih ulang';
  end if;
  select * into p from erp.payroll_settlements where id=v_id for update;
  if p.id is null or p.status not in('DRAFT','CALCULATED','REVIEW') then
    raise exception 'Y02_ENTITLEMENT_IN_PAYROLL: komponen carry hanya diatur pada payroll draft';
  end if;
  if TG_OP='DELETE' then return old;end if;
  select * into e from erp.bb_payroll_entitlements_v1 where id=new.opening_carry_entitlement_id for update;
  if e.id is null or e.kind<>'SEWING_WORK' or e.contractor_id is distinct from p.contractor_id then
    raise exception 'Y02_CARRY_WRONG_CONTRACTOR: komponen carry harus milik mandor payroll ini';
  end if;
  if p.period_end<e.cutover_date then raise exception 'Y02_CARRY_BEFORE_CUTOVER: komponen carry diselesaikan sesudah saldo awal';end if;
  if new.opening_carry_qty is null or new.opening_carry_qty<=0 or new.opening_carry_qty<>round(new.opening_carry_qty,6)
    or new.amount<>round(new.opening_carry_qty*e.rate,2) then
    raise exception 'Y02_CARRY_AMOUNT: nominal carry harus jumlah dikali tarif asal';
  end if;
  if new.opening_carry_qty>e.carry_qty-erp.bb_entitlement_carry_used_v1(e.id,new.id) then
    raise exception 'Y02_CARRY_EXCEEDS: komponen carry tersisa %, diminta %',e.carry_qty-erp.bb_entitlement_carry_used_v1(e.id,new.id),new.opening_carry_qty;
  end if;
  return new;
end;$function$;
create trigger trg_bb_opening_carry_reimbursement before insert or update or delete on erp.payroll_reimbursements
  for each row execute function erp.bb_guard_opening_carry_reimbursement_v1();

CREATE OR REPLACE FUNCTION erp.bb_check_labour_import_row_v1(p_batch uuid,p_row uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' SET DateStyle TO 'ISO, YMD'
AS $function$
declare r erp.migration_staging_rows%rowtype;j jsonb;k text;v_cutover date;v_contractor uuid;v_attendance boolean;v_kind text;v_date date;
  v_earned numeric;v_paid numeric;v_carry numeric;v_rate numeric;v_amount numeric;v_days numeric;v_paid_amount numeric;v_good numeric;
  v_doc_amount numeric;v_doc_total numeric;v_detail jsonb;v_start date;v_end date;
begin
  perform erp.require_owner_admin();
  select * into r from erp.migration_staging_rows where id=p_row and batch_id=p_batch and entity_type='OPENING_PAYROLL_ENTITLEMENT';
  if r.id is null then raise exception 'Baris hak upah tidak ditemukan';end if;
  j:=r.normalized_payload;v_kind:=upper(btrim(coalesce(j->>'kind','')));
  foreach k in array array['kind','contractor_code','document_number','line_number','document_date','rate'] loop
    if nullif(btrim(j->>k),'') is null then raise exception '%: wajib diisi untuk hak upah sebelum saldo awal',k;end if;
  end loop;
  if v_kind not in('SEWING_WORK','ATTENDANCE','ACCESSORY_REIMBURSEMENT') then
    raise exception 'kind: gunakan SEWING_WORK, ATTENDANCE, atau ACCESSORY_REIMBURSEMENT';
  end if;
  select (cutover_at at time zone 'Asia/Jakarta')::date into v_cutover from erp.migration_batches where id=p_batch;
  v_date:=erp.bb_parse_date_v1(j->>'document_date','document_date');
  if v_date>v_cutover then raise exception 'document_date: hak upah harus timbul sebelum saldo awal';end if;
  select id,attendance_required into v_contractor,v_attendance from erp.contractors where contractor_code=j->>'contractor_code' and is_active;
  if v_contractor is null then
    select coalesce(nullif(normalized_payload->>'attendance_required','')::boolean,false) into v_attendance from erp.migration_staging_rows
      where batch_id=p_batch and entity_type='CONTRACTOR' and validation_status='VALID' and normalized_payload->>'contractor_code'=j->>'contractor_code';
    if not found then raise exception 'contractor_code: mandor aktif tidak ditemukan';end if;
  end if;
  v_rate:=erp.bb_parse_amount_v1(j->>'rate','rate',true);
  if v_kind='SEWING_WORK' then
    foreach k in array array['work_component_code','earned_qty','paid_before_qty','carry_qty'] loop
      if nullif(btrim(j->>k),'') is null then raise exception '%: wajib diisi untuk upah jahit',k;end if;
      if k<>'work_component_code' and j->>k !~ '^[0-9]+([.][0-9]{1,6})?$' then raise exception '%: angka nonnegatif maksimal enam desimal',k;end if;
    end loop;
    if not exists(select 1 from erp.work_components where component_code=j->>'work_component_code') then
      raise exception 'work_component_code: komponen kerja tidak ditemukan';
    end if;
    v_earned:=(j->>'earned_qty')::numeric;v_paid:=(j->>'paid_before_qty')::numeric;v_carry:=(j->>'carry_qty')::numeric;
    if v_earned<=0 or v_earned-v_paid-v_carry<0 then
      raise exception 'Y02_EQUATION: jumlah dikerjakan dikurangi dibayar dan carry tidak boleh negatif';
    end if;
    v_amount:=round((v_earned-v_paid-v_carry)*v_rate,2);
    v_detail:=jsonb_build_object('po_number',nullif(btrim(j->>'po_number'),''),'work_component_code',j->>'work_component_code',
      'earned_qty',v_earned,'paid_before_qty',v_paid,'carry_qty',v_carry);
  else
    if j->>'paid_before_amount' is null then raise exception 'paid_before_amount: wajib diisi (0 bila belum dibayar)';end if;
    v_paid_amount:=erp.bb_parse_amount_v1(j->>'paid_before_amount','paid_before_amount',true);
    if v_kind='ATTENDANCE' then
      if not coalesce(v_attendance,false) then
        raise exception 'Y02_ATTENDANCE_NOT_REQUIRED: mandor ini tidak memakai absensi; hak absensi tidak diimpor';
      end if;
      foreach k in array array['worker_name','period_start','period_end','days'] loop
        if nullif(btrim(j->>k),'') is null then raise exception '%: wajib diisi untuk hak absensi',k;end if;
      end loop;
      v_start:=erp.bb_parse_date_v1(j->>'period_start','period_start');v_end:=erp.bb_parse_date_v1(j->>'period_end','period_end');
      if v_start>v_end or v_end>=v_cutover then raise exception 'period_end: periode absensi harus selesai sebelum saldo awal';end if;
      if j->>'days' !~ '^[0-9]+([.][0-9]{1,4})?$' or (j->>'days')::numeric<=0 then raise exception 'days: jumlah hari positif maksimal empat desimal';end if;
      v_days:=(j->>'days')::numeric;v_amount:=round(v_days*v_rate,2)-v_paid_amount;
      v_detail:=jsonb_build_object('worker_name',btrim(j->>'worker_name'),'period_start',v_start,'period_end',v_end,'days',v_days,'paid_before_amount',v_paid_amount);
    else
      foreach k in array array['category_code','good_qty'] loop
        if nullif(btrim(j->>k),'') is null then raise exception '%: wajib diisi untuk reimburse aksesori',k;end if;
      end loop;
      if j->>'good_qty' !~ '^[1-9][0-9]{0,8}$' then raise exception 'good_qty: jumlah GOOD bilangan bulat positif';end if;
      v_good:=(j->>'good_qty')::numeric;v_amount:=round(v_good*v_rate,2)-v_paid_amount;
      v_detail:=jsonb_build_object('category_code',j->>'category_code','good_qty',v_good,'paid_before_amount',v_paid_amount);
    end if;
    if v_amount<0 then raise exception 'Y02_EQUATION: yang sudah dibayar melebihi hak';end if;
  end if;
  -- The money: the CONTRACTOR_PAYABLE document of the same contractor and number in this batch, equal to its entitlements.
  if v_amount>0 then
    select sum(replace(d.normalized_payload->>'amount',',','.')::numeric) into v_doc_amount from erp.migration_staging_rows d
      where d.batch_id=p_batch and d.entity_type='OPENING_BALANCE_ITEM' and upper(d.normalized_payload->>'balance_type')='CONTRACTOR_PAYABLE'
        and d.normalized_payload->>'contractor_code'=j->>'contractor_code'
        and lower(btrim(d.normalized_payload->>'document_number'))=lower(btrim(j->>'document_number'));
    if v_doc_amount is null then
      raise exception 'Y02_DOCUMENT_REQUIRED: hak upah memerlukan dokumen hutang mandor dengan nomor yang sama di batch ini';
    end if;
    select sum(x.amount) into v_doc_total from (select erp.bb_labour_row_amount_v1(p_batch,s.id) amount from erp.migration_staging_rows s
      where s.batch_id=p_batch and s.entity_type='OPENING_PAYROLL_ENTITLEMENT' and s.normalized_payload->>'contractor_code'=j->>'contractor_code'
        and lower(btrim(s.normalized_payload->>'document_number'))=lower(btrim(j->>'document_number'))) x;
    if v_doc_total is distinct from v_doc_amount then
      raise exception 'Y02_EQUATION: jumlah hak upah dokumen % harus sama dengan dokumen hutang %',v_doc_total,v_doc_amount;
    end if;
  end if;
  if exists(select 1 from erp.migration_staging_rows s where s.batch_id=p_batch and s.id<>r.id and s.entity_type='OPENING_PAYROLL_ENTITLEMENT'
      and s.normalized_payload->>'contractor_code'=j->>'contractor_code' and upper(s.normalized_payload->>'kind')=v_kind
      and lower(btrim(s.normalized_payload->>'document_number'))=lower(btrim(j->>'document_number'))
      and lower(btrim(s.normalized_payload->>'line_number'))=lower(btrim(j->>'line_number')))
    or (v_contractor is not null and exists(select 1 from erp.bb_payroll_entitlements_v1 e where e.contractor_id=v_contractor and e.kind=v_kind
      and lower(btrim(e.document_number))=lower(btrim(j->>'document_number')) and lower(btrim(e.line_number))=lower(btrim(j->>'line_number'))
      and e.source_row_id<>r.id)) then
    raise exception 'Y02_DOC_DUPLICATE: hak upah ini sudah tercatat';
  end if;
  -- The old period is not also in the native registers of this contractor (it would be paid twice).
  if v_contractor is not null and (exists(select 1 from erp.work_completion_events w where w.contractor_id=v_contractor
        and erp._cp3_business_date(w.physical_at)<v_cutover and w.status<>'REVERSED')
      or exists(select 1 from erp.attendance_records a where a.contractor_id=v_contractor and a.attendance_date<v_cutover)) then
    raise exception 'Y02_PRE_CUTOVER_NATIVE: mandor ini sudah punya catatan kerja/absensi sebelum saldo awal di ERP; hak lama tidak diimpor dua kali';
  end if;
  return jsonb_build_object('contractor_id',v_contractor,'cutover_date',v_cutover,'document_date',v_date,'kind',v_kind,'amount',v_amount,
    'carry_qty',coalesce(v_carry,0),'rate',v_rate,'detail',v_detail);
end;$function$;

CREATE OR REPLACE FUNCTION erp.bb_labour_row_amount_v1(p_batch uuid,p_row uuid)
 RETURNS numeric LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
declare j jsonb;v_rate numeric;
begin
  select normalized_payload into j from erp.migration_staging_rows where id=p_row and batch_id=p_batch;
  begin
    v_rate:=replace(j->>'rate',',','.')::numeric;
    return case upper(btrim(j->>'kind'))
      when 'SEWING_WORK' then round(((j->>'earned_qty')::numeric-(j->>'paid_before_qty')::numeric-(j->>'carry_qty')::numeric)*v_rate,2)
      when 'ATTENDANCE' then round((j->>'days')::numeric*v_rate,2)-replace(j->>'paid_before_amount',',','.')::numeric
      else round((j->>'good_qty')::numeric*v_rate,2)-replace(j->>'paid_before_amount',',','.')::numeric end;
  exception when others then return null;
  end;
end;$function$;

CREATE OR REPLACE FUNCTION erp.bb_validate_labour_imports_v1(p_batch uuid)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare r record;
begin
  perform erp.require_owner_admin();
  for r in select id from erp.migration_staging_rows where batch_id=p_batch and entity_type='OPENING_PAYROLL_ENTITLEMENT' order by source_row_no loop
    begin
      perform erp.bb_check_labour_import_row_v1(p_batch,r.id);
      update erp.migration_staging_rows set validation_status='VALID',validation_errors='[]' where id=r.id;
    exception when others then
      update erp.migration_staging_rows set validation_status='ERROR',validation_errors=jsonb_build_array(sqlerrm) where id=r.id;
    end;
  end loop;
end;$function$;

CREATE OR REPLACE FUNCTION erp.bb_apply_labour_imports_v1(p_batch uuid)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare r record;j jsonb;c jsonb;v_contractor uuid;v_balance uuid;v_id uuid;
begin
  perform erp.require_owner_admin();
  for r in select * from erp.migration_staging_rows where batch_id=p_batch and entity_type='OPENING_PAYROLL_ENTITLEMENT' and posted_entity_id is null
      order by source_row_no loop
    if r.validation_status<>'VALID' then raise exception 'Hak upah belum lolos pemeriksaan';end if;
    j:=r.normalized_payload;
    perform pg_advisory_xact_lock(hashtextextended('BB_Y02:'||(j->>'contractor_code')||':'||lower(btrim(j->>'document_number')),0));
    c:=erp.bb_check_labour_import_row_v1(p_batch,r.id);
    select id into strict v_contractor from erp.contractors where contractor_code=j->>'contractor_code' and is_active;
    v_balance:=null;
    if (c->>'amount')::numeric>0 then
      select b.id into v_balance from erp.initial_import_financial_sources f join erp.opening_subledger_balances b on b.opening_item_id=f.opening_item_id
        where f.batch_id=p_batch and f.balance_type='CONTRACTOR_PAYABLE' and f.party_id=v_contractor
          and lower(btrim(f.document_number))=lower(btrim(j->>'document_number'));
      if v_balance is null then raise exception 'Y02_DOCUMENT_REQUIRED: dokumen hutang mandor belum dibukukan';end if;
    end if;
    insert into erp.bb_payroll_entitlements_v1(batch_id,source_row_id,contractor_id,kind,document_number,line_number,document_date,cutover_date,
      balance_id,amount,carry_qty,rate,detail)
    values(p_batch,r.id,v_contractor,c->>'kind',btrim(j->>'document_number'),btrim(j->>'line_number'),(c->>'document_date')::date,
      (c->>'cutover_date')::date,v_balance,(c->>'amount')::numeric,(c->>'carry_qty')::numeric,(c->>'rate')::numeric,c->'detail')
    returning id into v_id;
    update erp.migration_staging_rows set posted_entity_id=v_id,posted_entity_type='OPENING_PAYROLL_ENTITLEMENT',posted_at=statement_timestamp(),
      updated_at=statement_timestamp() where id=r.id;
  end loop;
end;$function$;

CREATE OR REPLACE FUNCTION erp.bb_manage_payroll_entitlement_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_op text:=upper(coalesce(nullif(btrim(p_payload->>'operation'),''),''));v_batch uuid:=(p_payload->>'batch_id')::uuid;
  e erp.bb_payroll_entitlements_v1%rowtype;p erp.payroll_settlements%rowtype;v_qty numeric;v_id uuid;
begin
  if v_op<>'ALLOCATE_CARRY' then raise exception 'Y02_OPERATION: operasi tidak dikenal';end if;
  select * into p from erp.payroll_settlements where id=(p_payload->>'payroll_id')::uuid for update;
  select * into e from erp.bb_payroll_entitlements_v1 where id=(p_payload->>'entitlement_id')::uuid for update;
  if e.id is null or e.batch_id is distinct from v_batch then raise exception 'Y02_NOT_IN_BATCH: hak upah bukan milik impor ini';end if;
  if p.id is null or p.status not in('DRAFT','CALCULATED','REVIEW') then raise exception 'Y02_ENTITLEMENT_IN_PAYROLL: payroll harus draft';end if;
  if p_payload->>'expected_payroll_version' is null or p.row_version<>(p_payload->>'expected_payroll_version')::bigint then
    raise exception 'STALE_VERSION: payroll berubah';
  end if;
  if coalesce(p_payload->>'qty','') !~ '^[0-9]+([.][0-9]{1,6})?$' then raise exception 'Y02_CARRY_AMOUNT: jumlah carry maksimal enam desimal; nol untuk melepas';end if;
  v_qty:=(p_payload->>'qty')::numeric;
  select id into v_id from erp.payroll_reimbursements where payroll_id=p.id and opening_carry_entitlement_id=e.id;
  if v_qty=0 then
    if v_id is null then raise exception 'Alokasi yang akan dilepas tidak ditemukan';end if;
    delete from erp.payroll_reimbursements where id=v_id;
  elsif v_id is null then
    insert into erp.payroll_reimbursements(payroll_id,amount,description,source_type,opening_carry_entitlement_id,opening_carry_qty)
    values(p.id,round(v_qty*e.rate,2),'Komponen carry saldo awal '||e.document_number||'/'||e.line_number,'OPENING_CARRY',e.id,v_qty)
    returning id into v_id;
  else
    update erp.payroll_reimbursements set amount=round(v_qty*e.rate,2),opening_carry_qty=v_qty where id=v_id;
  end if;
  perform erp.recalculate_payroll(p.id);
  return jsonb_build_object('operation',v_op,'entitlement_id',e.id,'payroll_id',p.id,'reimbursement_id',v_id,
    'carry_remaining',(e.carry_qty-erp.bb_entitlement_carry_used_v1(e.id))::text);
end;$function$;

CREATE OR REPLACE FUNCTION erp.bb_labour_workspace_v1(p_batch uuid)
 RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select jsonb_build_object('payroll_entitlements',coalesce((select jsonb_agg(jsonb_build_object('id',e.id,'kind',e.kind,
      'contractor_code',c.contractor_code,'contractor_name',c.contractor_name,'document_number',e.document_number,'line_number',e.line_number,
      'document_date',e.document_date,'amount',e.amount::text,'balance_id',e.balance_id,'rate',e.rate::text,'detail',e.detail,
      'carry_qty',e.carry_qty::text,'carry_remaining',(e.carry_qty-erp.bb_entitlement_carry_used_v1(e.id))::text,
      'carry_lines',coalesce((select jsonb_agg(jsonb_build_object('payroll_id',p.id,'payroll_number',p.payroll_number,'status',p.status,
          'row_version',p.row_version::text,'qty',r.opening_carry_qty::text,'amount',r.amount::text) order by p.period_end,p.id)
        from erp.payroll_reimbursements r join erp.payroll_settlements p on p.id=r.payroll_id
        where r.opening_carry_entitlement_id=e.id and p.status<>'REVERSED'),'[]'::jsonb)) order by c.contractor_code,e.document_number,e.line_number)
    from erp.bb_payroll_entitlements_v1 e join erp.contractors c on c.id=e.contractor_id where e.batch_id=p_batch),'[]'::jsonb))
$function$;

CREATE OR REPLACE FUNCTION erp.bb_labour_revision_part_v1(p_batch uuid)
 RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select jsonb_build_object('entitlements',coalesce((select jsonb_agg(to_jsonb(e) order by e.id) from erp.bb_payroll_entitlements_v1 e where e.batch_id=p_batch),'[]'::jsonb),
    'carry_lines',coalesce((select jsonb_agg(to_jsonb(r) order by r.id) from erp.payroll_reimbursements r join erp.bb_payroll_entitlements_v1 e
      on e.id=r.opening_carry_entitlement_id where e.batch_id=p_batch),'[]'::jsonb))
$function$;

do $grants$
declare f text;
begin
  for f in select p.oid::regprocedure::text from pg_proc p join pg_namespace n on n.oid=p.pronamespace
      where n.nspname='erp' and p.proname like 'bb\_%' loop
    execute format('revoke all on function %s from public,anon,authenticated,service_role',f);
  end loop;
end $grants$;
