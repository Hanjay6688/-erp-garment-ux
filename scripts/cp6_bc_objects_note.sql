-- ================================================================ BC mandor note returns, credits, rounding, free lines
-- M:4762/M:3912 (paid mandor note return: receipt linked to the note, credit only for a proven right, settlement checked,
-- capped by the source quantity/amount, never the latest master price), M:4458 ACC-DEC05 (credit, carry or refund after a
-- full/partial settlement: keep the original settlement, block unsupported financial finalization), M:5005 (cumulative
-- credit never above the original amount; a full return reverses it exactly), M:4459 ACC-DEC06 (whole-rupiah rounding only
-- as a separate line), M:4462 ERP-DEC02 (Special free categories: explicit, never inferred from a name or a demo seed).

-- ALL-C02: the lines of an old mandor accessory note behind an imported CONTRACTOR_RECEIVABLE document.
create table erp.bc_opening_note_lines_v1(
  id uuid primary key,
  batch_id uuid not null references erp.migration_batches(id),
  source_row_id uuid not null unique,
  balance_id uuid not null references erp.opening_subledger_balances(id),
  document_number text not null,
  line_number integer not null check(line_number between 1 and 999),
  material_id uuid not null references erp.materials(id),
  qty numeric(18,6) not null check(qty>0),
  line_amount numeric(18,2) not null check(line_amount>=0),
  unique(balance_id,line_number)
);
comment on table erp.bc_opening_note_lines_v1 is 'BC (ALL-C02): the lines (accessory, quantity, source amount) of an old mandor note whose unpaid residual was imported as a CONTRACTOR_RECEIVABLE opening document. A return after cutover is capped by the line quantity and credited at the line''s own amount, never at a current price; the historical settlement stays provenance.';

create table erp.bc_note_roundings_v1(
  id uuid primary key references erp.bc_documents_v1(id),
  issue_id uuid not null references erp.contractor_material_issues(id),
  item_id uuid not null references erp.contractor_material_issue_items(id),
  amount numeric(18,2) not null check(amount<>0 and abs(amount)<1),
  journal_entry_id uuid not null references erp.journal_entries(id)
);

create table erp.bc_free_issue_lines_v1(
  issue_id uuid not null references erp.contractor_material_issues(id),
  material_id uuid not null references erp.materials(id),
  category_id uuid not null references erp.accessory_categories(id),
  policy_version bigint not null,
  primary key(issue_id,material_id)
);
comment on table erp.bc_free_issue_lines_v1 is 'BC (ERP-DEC02): a mandor note line issued free (price 0) because its category is on the owner''s Special free list for a contractor that is Special at the physical time; the policy version is kept. Checked again at posting.';

alter table erp.payroll_reimbursements add column bc_credit_event_id uuid references erp.bc_lot_events_v1(id);
alter table erp.payroll_reimbursements drop constraint payroll_reimbursements_source_type_check;
alter table erp.payroll_reimbursements add constraint payroll_reimbursements_source_type_check
  check(source_type::text=any(array['MANUAL','ACCESSORY_BOM','OPENING_PAYABLE','OPENING_CARRY','BC_RETURN_CARRY']));
alter table erp.payroll_reimbursements add constraint payroll_reimbursements_bc_carry_check
  check((source_type::text='BC_RETURN_CARRY')=(bc_credit_event_id is not null));

alter table erp.bb_opening_credits_v1 drop constraint bb_opening_credits_v1_credit_kind_check;
alter table erp.bb_opening_credits_v1 add constraint bb_opening_credits_v1_credit_kind_check
  check(credit_kind in('CUSTOMER_ALLOWANCE','SUPPLIER_ALLOWANCE','VENDOR_ALLOWANCE','CUSTOMER_CREDIT_APPLY','ACCESSORY_NOTE_RETURN'));

do $rls$
declare t text;
begin
  foreach t in array array['bc_opening_note_lines_v1','bc_note_roundings_v1','bc_free_issue_lines_v1'] loop
    execute format('alter table erp.%I enable row level security',t);
    execute format('revoke all on erp.%I from public,anon,authenticated,service_role',t);
  end loop;
end $rls$;

-- ---------------------------------------------------------------- amounts
-- The item's share of the note's posted receivable: the journal rounds the document total once, so the cents go to the
-- items by cumulative rounding in item id order; the shares add up to the posted amount exactly.
CREATE OR REPLACE FUNCTION erp.bc_note_item_share_v1(p_item uuid)
 RETURNS numeric LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  with i as(select issue_id from erp.contractor_material_issue_items where id=p_item),
  c as(select x.id,sum(coalesce(x.total_receivable,0)) over(order by x.id) cum from erp.contractor_material_issue_items x join i on i.issue_id=x.issue_id)
  select round(c.cum,2)-round(c.cum-coalesce((select total_receivable from erp.contractor_material_issue_items where id=p_item),0),2) from c where c.id=p_item
$function$;

-- Credits (their unpaid part) and roundings that change what the mandor still owes on one note line.
CREATE OR REPLACE FUNCTION erp.bc_note_item_adjustment_v1(p_item uuid)
 RETURNS numeric LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select coalesce((select sum(e.amount_unpaid) from erp.bc_lot_events_v1 e join erp.bc_documents_v1 d on d.id=e.document_id
      join erp.bc_return_lots_v1 l on l.id=e.lot_id where l.note_item_id=p_item and e.event_kind='CREDIT' and d.status='POSTED'),0)
   -coalesce((select sum(r.amount) from erp.bc_note_roundings_v1 r join erp.bc_documents_v1 d on d.id=r.id where r.item_id=p_item and d.status='POSTED'),0)
$function$;

-- What payroll may still collect on the line: the original receivable less credited unpaid parts plus roundings.
-- Without BC activity it is exactly total_receivable (the unchanged rule).
CREATE OR REPLACE FUNCTION erp.bc_note_item_collectible_v1(p_item uuid)
 RETURNS numeric LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select coalesce(total_receivable,0)-erp.bc_note_item_adjustment_v1(p_item) from erp.contractor_material_issue_items where id=p_item
$function$;

CREATE OR REPLACE FUNCTION erp.bc_note_item_allocated_v1(p_item uuid)
 RETURNS numeric LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select coalesce(sum(pd.amount),0) from erp.payroll_deductions pd join erp.payroll_settlements ps on ps.id=pd.payroll_id
  where pd.contractor_issue_item_id=p_item and pd.deduction_type='MATERIAL_KASBON' and ps.status<>'REVERSED'
$function$;

-- The CONTRACTOR_ISSUE movement of the note line a credited return belongs to (its cost is the return's cost).
CREATE OR REPLACE FUNCTION erp.bc_note_return_issue_movement_v1(p_event uuid)
 RETURNS uuid LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select m.id from erp.bc_lot_events_v1 e join erp.bc_return_lots_v1 l on l.id=e.lot_id
  join erp.material_stock_movements m on m.source_type='CONTRACTOR_MATERIAL_ISSUE_ITEM' and m.source_id=l.note_item_id
    and m.movement_type='CONTRACTOR_ISSUE' and m.reversal_of_id is null
  where e.id=p_event order by m.physical_at desc,m.system_created_at desc,m.id desc limit 1
$function$;

CREATE OR REPLACE FUNCTION erp.bc_carry_remaining_v1(p_event uuid)
 RETURNS numeric LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select e.amount_carry-coalesce((select sum(r.amount) from erp.payroll_reimbursements r join erp.payroll_settlements p on p.id=r.payroll_id
    where r.bc_credit_event_id=e.id and r.source_type='BC_RETURN_CARRY' and p.status<>'REVERSED'),0)
  from erp.bc_lot_events_v1 e join erp.bc_documents_v1 d on d.id=e.document_id where e.id=p_event and d.status='POSTED'
$function$;

-- ---------------------------------------------------------------- CREDIT_NOTE_RETURN (ACC-DEC05; ACC-A08, C09, D04; ALL-C02)
-- Credits returned quantity of one mandor lot already inspected in a condition the policy credits. The amount is the
-- cumulative share of the source line (native note: the item's share of the posted document; opening note: the line
-- amount), never a current price. The unpaid part reduces what payroll may still collect; the part already allocated or
-- paid follows the policy (refused, carried to the next payroll as a payable, or refunded in cash). A native note's
-- credited goods return to company stock at the note line's issue cost (inventory back, COGS back); an opening note's
-- credited goods become company custody with value pending (ACC-DEC03), because their old cost is not in the ledger.
CREATE OR REPLACE FUNCTION erp.bc_credit_note_return_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare l erp.bc_return_lots_v1%rowtype;s jsonb;v_policy jsonb;v_cond text:=upper(coalesce(p_payload->>'condition',''));v_qty numeric;
  v_at timestamptz;v_to uuid;v_event uuid;v_item erp.contractor_material_issue_items%rowtype;v_issue erp.contractor_material_issues%rowtype;
  n record;b erp.opening_subledger_balances%rowtype;v_before numeric;v_base numeric;v_line_qty numeric;v_amount numeric;v_unpaid numeric;
  v_rest numeric;v_carry numeric:=0;v_refund numeric:=0;v_cash uuid;v_cash_coa uuid;v_lines jsonb;v_journal uuid;v_move uuid;v_value numeric;
  v_day date;v_child uuid;v_settlement uuid;
begin
  perform erp.require_owner_admin();perform erp.require_permission('finance.contractor_accessory.reverse');
  perform erp._cp3_assert_closed_json_object(p_payload,array['lot_id','condition','qty','physical_at','reason'],
    array['lot_id','condition','qty','physical_at','location_id','cash_account_id','reason','responsible','reference'],'credit payload');
  v_policy:=erp.bc_require_policy_v1('ACC_DEC05','kredit retur nota mandor');
  l:=erp.bc_lock_lot_v1(erp.bc_uuid_v1(p_payload,'lot_id',true));
  if l.owner_kind<>'MANDOR' then raise exception 'BC_NOT_NOTE_RETURN: kredit hanya untuk retur nota mandor';end if;
  if v_cond not in('USABLE','DAMAGED') then raise exception 'BC_CONDITION_INVALID: kredit hanya untuk barang yang sudah diperiksa';end if;
  if not (v_policy->'credit_conditions') ? v_cond then
    raise exception 'BC_CONDITION_NOT_CREDITED: kebijakan ACC-DEC05 tidak mengkredit barang %',case v_cond when 'USABLE' then 'layak' else 'rusak' end;end if;
  v_qty:=erp.bc_parse_qty_v1(l.material_id,p_payload->'qty','qty');
  s:=erp.bc_lot_state_v1(l.id);
  if v_qty>(s->>lower(v_cond))::numeric then
    raise exception 'BC_QTY_EXCEEDS_BUCKET: % yang tersedia % , diminta %',v_cond,((s->>lower(v_cond))::numeric)::numeric(18,6),v_qty;end if;
  v_at:=erp.bc_parse_at_v1(p_payload->>'physical_at','physical_at');
  if v_at<l.received_at then raise exception 'BC_DATE_BEFORE_SOURCE: kredit tidak boleh sebelum barang diterima';end if;
  v_day:=erp._cp3_business_date(v_at);
  -- Cumulative credited quantity of the source line (every lot of it), under the source lock shared with payroll.
  if l.note_item_id is not null then
    select * into v_item from erp.contractor_material_issue_items where id=l.note_item_id;
    perform pg_advisory_xact_lock(hashtextextended('BCNOTE|'||v_item.id::text,0));
    perform pg_advisory_xact_lock(hashtextextended('PAYKASBON|'||v_item.id::text,0));
    select * into v_issue from erp.contractor_material_issues where id=v_item.issue_id for update;
    if v_issue.status<>'POSTED' then raise exception 'BC_NOTE_NOT_POSTED: nota asal tidak lagi disahkan';end if;
    v_base:=erp.bc_note_item_share_v1(v_item.id);v_line_qty:=v_item.qty;
    select coalesce(sum(e.qty),0) into v_before from erp.bc_lot_events_v1 e join erp.bc_documents_v1 d on d.id=e.document_id
      join erp.bc_return_lots_v1 x on x.id=e.lot_id where x.note_item_id=v_item.id and e.event_kind='CREDIT' and d.status='POSTED';
  else
    select * into n from erp.bc_opening_note_lines_v1 where id=l.opening_note_line_id;
    perform pg_advisory_xact_lock(hashtextextended('BCNOTE|'||n.id::text,0));
    select * into b from erp.opening_subledger_balances where id=n.balance_id for update;
    v_base:=n.line_amount;v_line_qty:=n.qty;
    select coalesce(sum(e.qty),0) into v_before from erp.bc_lot_events_v1 e join erp.bc_documents_v1 d on d.id=e.document_id
      join erp.bc_return_lots_v1 x on x.id=e.lot_id where x.opening_note_line_id=n.id and e.event_kind='CREDIT' and d.status='POSTED';
  end if;
  v_amount:=round(v_base*(v_before+v_qty)/v_line_qty,2)-round(v_base*v_before/v_line_qty,2);
  -- The part the mandor still owes and payroll has not taken: that part is credited against the receivable.
  if l.note_item_id is not null then
    v_unpaid:=greatest(least(v_amount,round(erp.bc_note_item_collectible_v1(v_item.id)-erp.bc_note_item_allocated_v1(v_item.id),2)),0);
  else
    v_unpaid:=greatest(least(v_amount,b.original_amount-b.settled_amount-erp.bb_opening_balance_reserved_v1(b.id)),0);
  end if;
  v_rest:=v_amount-v_unpaid;
  if v_rest>0 then
    if v_policy->>'mode'='CREDIT_UNPAID_ONLY' then
      raise exception 'BC_DEC05_PAID_PORTION: % dari kredit % sudah dipotong/dibayar; kebijakan ACC-DEC05 hanya mengkredit sisa yang belum dibayar',v_rest,v_amount;
    elsif v_policy->>'mode'='CREDIT_THEN_CARRY' then v_carry:=v_rest;
    else
      v_refund:=v_rest;
      select id,coa_account_id into v_cash,v_cash_coa from erp.cash_accounts where id=erp.bc_uuid_v1(p_payload,'cash_account_id',false) and is_active;
      if v_cash is null then raise exception 'BC_CASH_ACCOUNT_REQUIRED: pilih rekening kas/bank aktif untuk pengembalian uang';end if;
    end if;
  end if;
  if v_refund=0 and p_payload ? 'cash_account_id' then raise exception 'BC_CASH_ACCOUNT_REQUIRED: rekening kas hanya untuk pengembalian uang';end if;
  perform erp.bc_new_document_v1(p_request,'CREDIT_NOTE_RETURN',v_at,p_payload,jsonb_build_object('ACC_DEC05',erp.bc_policy_version_v1('ACC_DEC05')));
  if l.note_item_id is not null then
    v_to:=erp.bc_location_v1(erp.bc_uuid_v1(p_payload,'location_id',true),case when v_cond='USABLE' then array['MAIN'] else array['DAMAGED'] end,
      case when v_cond='USABLE' then 'gudang untuk barang layak' else 'area rusak' end);
  elsif p_payload ? 'location_id' then raise exception 'BC_LOCATION_INVALID: barang nota saldo awal menjadi titipan bernilai pending, bukan stok';
  end if;
  insert into erp.bc_lot_events_v1(document_id,lot_id,event_kind,condition,qty,event_at,target_location_id,amount,amount_unpaid,amount_carry,amount_refund,cash_account_id)
  values(p_request,l.id,'CREDIT',v_cond,v_qty,v_at,v_to,v_amount,v_unpaid,v_carry,v_refund,v_cash) returning id into v_event;
  if l.note_item_id is not null then
    -- Money: revenue back, receivable down by the unpaid part, the rest carried or refunded.
    if v_amount>0 then
      v_lines:=jsonb_build_array(jsonb_build_object('mapping_key','MATERIAL_RECOVERY','debit',v_amount,'credit',0,'contractor_id',v_issue.contractor_id,'po_id',v_issue.po_id));
      if v_unpaid>0 then v_lines:=v_lines||jsonb_build_array(jsonb_build_object('mapping_key','CONTRACTOR_RECEIVABLE','debit',0,'credit',v_unpaid,'contractor_id',v_issue.contractor_id,'po_id',v_issue.po_id));end if;
      if v_carry>0 then v_lines:=v_lines||jsonb_build_array(jsonb_build_object('mapping_key','CONTRACTOR_PAYABLE','debit',0,'credit',v_carry,'contractor_id',v_issue.contractor_id,'po_id',v_issue.po_id));end if;
      if v_refund>0 then v_lines:=v_lines||jsonb_build_array(jsonb_build_object('account_id',v_cash_coa,'debit',0,'credit',v_refund,'contractor_id',v_issue.contractor_id,'po_id',v_issue.po_id));end if;
      v_journal:=erp.post_journal('BC_NOTE_RETURN_CREDIT',v_event,v_day,'Kredit retur nota mandor '||v_issue.issue_number,v_lines);
      perform erp.bc_link_v1(p_request,'JOURNAL',v_journal);
    end if;
    -- Goods: back to company stock at the issue cost of this note line.
    insert into erp.material_stock_movements(material_id,location_id,movement_type,qty_signed,source_type,source_id,physical_at,created_by,note)
    values(l.material_id,v_to,'ADJUSTMENT',v_qty,'BC_NOTE_RETURN_CREDIT',v_event,v_at,erp.current_app_user_id(),'Retur nota mandor dikreditkan')
    returning id into v_move;
    perform erp.bc_link_v1(p_request,'MOVEMENT',v_move);
    perform erp.recalculate_material_cost(l.material_id);
    select round(qty_signed*coalesce(original_unit_cost_snapshot,unit_cost_snapshot),2) into v_value from erp.material_stock_movements where id=v_move;
    if v_value>0 then
      v_journal:=erp.post_journal('BC_NOTE_RETURN_STOCK',v_event,v_day,'Barang retur nota mandor kembali ke stok',jsonb_build_array(
        jsonb_build_object('mapping_key','MATERIAL_INVENTORY','debit',v_value,'credit',0,'contractor_id',v_issue.contractor_id,'po_id',v_issue.po_id),
        jsonb_build_object('mapping_key','ACCESSORY_RECOVERY_COGS','debit',0,'credit',v_value,'contractor_id',v_issue.contractor_id,'po_id',v_issue.po_id)));
      perform erp.bc_link_v1(p_request,'JOURNAL',v_journal);
    end if;
    perform erp.refresh_contractor_issue_payroll_status(v_item.id);
  else
    if v_unpaid>0 then
      v_settlement:=gen_random_uuid();
      insert into erp.opening_subledger_settlements(id,balance_id,settlement_number,physical_at,amount,cash_account_id,status,notes,created_by)
      values(v_settlement,b.id,'OSS-'||upper(substr(replace(v_settlement::text,'-',''),1,16)),v_at,v_unpaid,null,'DRAFT',btrim(p_payload->>'reason'),erp.current_app_user_id());
      insert into erp.bb_opening_credits_v1(settlement_id,credit_kind,credit_note_number,reason)
      values(v_settlement,'ACCESSORY_NOTE_RETURN','BCA-'||upper(substr(replace(p_request::text,'-',''),1,16)),btrim(p_payload->>'reason'));
      perform erp.post_opening_subledger_settlement(v_settlement);
      perform erp.bc_link_v1(p_request,'SETTLEMENT',v_settlement);
    end if;
    if v_carry+v_refund>0 then
      v_lines:=jsonb_build_array(jsonb_build_object('mapping_key','MATERIAL_RECOVERY','debit',v_carry+v_refund,'credit',0,'contractor_id',b.contractor_id));
      if v_carry>0 then v_lines:=v_lines||jsonb_build_array(jsonb_build_object('mapping_key','CONTRACTOR_PAYABLE','debit',0,'credit',v_carry,'contractor_id',b.contractor_id));end if;
      if v_refund>0 then v_lines:=v_lines||jsonb_build_array(jsonb_build_object('account_id',v_cash_coa,'debit',0,'credit',v_refund,'contractor_id',b.contractor_id));end if;
      v_journal:=erp.post_journal('BC_NOTE_RETURN_CREDIT',v_event,v_day,'Kredit retur nota mandor saldo awal '||n.document_number,v_lines);
      perform erp.bc_link_v1(p_request,'JOURNAL',v_journal);
    end if;
    -- The goods become company custody with value pending (their old cost is not in the ledger).
    insert into erp.bc_return_lots_v1(document_id,source_kind,owner_kind,value_mode,material_id,location_id,qty_received,init_usable,init_damaged,
      received_at,contractor_id,parent_lot_id,parent_event_id,reference)
    values(p_request,'NOTE_RETURN_CREDITED','COMPANY','PENDING',l.material_id,l.location_id,v_qty,case when v_cond='USABLE' then v_qty else 0 end,
      case when v_cond='DAMAGED' then v_qty else 0 end,v_at,l.contractor_id,l.id,v_event,n.document_number) returning id into v_child;
  end if;
  return jsonb_build_object('event_id',v_event,'amount',v_amount::text,'unpaid',v_unpaid::text,'carry',v_carry::text,'refund',v_refund::text,
    'custody_lot_id',v_child,'lot',erp.bc_lot_state_v1(l.id));
end;$function$;

-- The journal lines of an opening note-return credit (a non-cash settlement of the imported CONTRACTOR_RECEIVABLE).
CREATE OR REPLACE FUNCTION erp.bc_opening_note_credit_lines_v1(p_settlement_id uuid)
 RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
declare s erp.opening_subledger_settlements%rowtype;b erp.opening_subledger_balances%rowtype;
begin
  select * into s from erp.opening_subledger_settlements where id=p_settlement_id;
  select * into b from erp.opening_subledger_balances where id=s.balance_id;
  if b.party_type<>'CONTRACTOR' or b.direction<>'RECEIVABLE' then raise exception 'BB_CREDIT_KIND_MISMATCH: kredit retur nota hanya untuk piutang mandor';end if;
  return jsonb_build_array(
    jsonb_build_object('mapping_key','MATERIAL_RECOVERY','debit',s.amount,'credit',0,'contractor_id',b.contractor_id),
    jsonb_build_object('mapping_key','CONTRACTOR_RECEIVABLE','debit',0,'credit',s.amount,'contractor_id',b.contractor_id));
end;$function$;

-- ---------------------------------------------------------------- ALLOCATE_CARRY (ACC-DEC05 CREDIT_THEN_CARRY)
CREATE OR REPLACE FUNCTION erp.bc_allocate_carry_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare e erp.bc_lot_events_v1%rowtype;p erp.payroll_settlements%rowtype;v_amount numeric;v_contractor uuid;v_line uuid;
begin
  perform erp.require_owner_admin();perform erp.require_permission('finance.payroll.view');
  perform erp._cp3_assert_closed_json_object(p_payload,array['event_id','payroll_id','amount','reason'],
    array['event_id','payroll_id','amount','reason','responsible','reference'],'carry payload');
  select * into e from erp.bc_lot_events_v1 where id=erp.bc_uuid_v1(p_payload,'event_id',true);
  if e.id is null or e.event_kind<>'CREDIT' or e.amount_carry<=0 then raise exception 'BC_CARRY_INVALID: kredit tanpa bagian yang dibawa ke payroll';end if;
  perform pg_advisory_xact_lock(hashtextextended('BCCARRY|'||e.id::text,0));
  select * into p from erp.payroll_settlements where id=erp.bc_uuid_v1(p_payload,'payroll_id',true) for update;
  select coalesce(l.contractor_id,(select c.contractor_id from erp.contractor_material_issues c join erp.contractor_material_issue_items i on i.issue_id=c.id where i.id=l.note_item_id))
    into v_contractor from erp.bc_return_lots_v1 l where l.id=e.lot_id;
  if p.id is null or p.contractor_id is distinct from v_contractor or p.status not in('DRAFT','CALCULATED','REVIEW') then
    raise exception 'BC_CARRY_INVALID: pilih payroll draft mandor yang sama';end if;
  if jsonb_typeof(p_payload->'amount') is distinct from 'string' then raise exception 'BB_AMOUNT_INVALID: amount harus nominal tepat dua desimal';end if;
  v_amount:=erp.bb_parse_amount_v1(p_payload->>'amount','amount');
  if v_amount>coalesce(erp.bc_carry_remaining_v1(e.id),0) then
    raise exception 'BC_CARRY_EXCEEDS: sisa kredit yang dibawa % , diminta %',coalesce(erp.bc_carry_remaining_v1(e.id),0),v_amount;end if;
  perform erp.bc_new_document_v1(p_request,'ALLOCATE_CARRY',statement_timestamp(),p_payload);
  insert into erp.payroll_reimbursements(payroll_id,amount,description,source_type,bc_credit_event_id)
  values(p.id,v_amount,'Kredit retur nota aksesori dibawa ke payroll','BC_RETURN_CARRY',e.id) returning id into v_line;
  perform erp.bc_link_v1(p_request,'PAYROLL_LINE',v_line);
  perform erp.recalculate_payroll(p.id);
  return jsonb_build_object('payroll_line_id',v_line,'carry_remaining',erp.bc_carry_remaining_v1(e.id)::text);
end;$function$;

CREATE OR REPLACE FUNCTION erp.bc_guard_carry_reimbursement_v1()
 RETURNS trigger LANGUAGE plpgsql SET search_path TO ''
AS $function$
declare p erp.payroll_settlements%rowtype;
begin
  if tg_op='DELETE' then
    if old.bc_credit_event_id is null then return old;end if;
    select * into p from erp.payroll_settlements where id=old.payroll_id;
    if p.status not in('DRAFT','CALCULATED','REVIEW') then raise exception 'BC_CARRY_LOCKED: kredit yang dibawa hanya dilepas dari payroll draft';end if;
    return old;
  end if;
  if new.bc_credit_event_id is null and new.source_type::text<>'BC_RETURN_CARRY' and (tg_op='INSERT' or old.bc_credit_event_id is null) then return new;end if;
  if current_user<>'postgres' then raise exception 'BC_CARRY_WRITER: kredit retur masuk payroll hanya lewat command resmi';end if;
  if tg_op='UPDATE' and (new.payroll_id<>old.payroll_id or new.bc_credit_event_id is distinct from old.bc_credit_event_id
      or new.source_type is distinct from old.source_type or new.amount<>old.amount) then
    raise exception 'BC_CARRY_LOCKED: baris kredit retur di payroll tidak dapat diubah; lepaskan lalu pilih ulang';end if;
  if new.amount<>round(new.amount,2) or new.amount<=0 then raise exception 'BC_CARRY_INVALID: nominal kredit positif dua desimal';end if;
  return new;
end;$function$;
create trigger trg_bc_carry_reimbursement before insert or update or delete on erp.payroll_reimbursements
  for each row execute function erp.bc_guard_carry_reimbursement_v1();

-- ---------------------------------------------------------------- ROUND_NOTE (ACC-DEC06)
-- One separate rounding line per note to the nearest whole rupiah of what is still collectible; PCS and the original
-- amounts are unchanged. Refused when payroll already took more than the rounded amount of a line.
CREATE OR REPLACE FUNCTION erp.bc_round_note_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_policy jsonb;h erp.contractor_material_issues%rowtype;v_item uuid;v_total numeric;v_round numeric;v_journal uuid;v_day date;
begin
  perform erp.require_owner_admin();perform erp.require_permission('finance.contractor_accessory.reverse');
  perform erp._cp3_assert_closed_json_object(p_payload,array['issue_id','reason'],array['issue_id','reason','responsible','reference'],'rounding payload');
  v_policy:=erp.bc_require_policy_v1('ACC_DEC06','pembulatan rupiah nota mandor');
  select * into h from erp.contractor_material_issues where id=erp.bc_uuid_v1(p_payload,'issue_id',true) for update;
  if h.id is null or h.status<>'POSTED' then raise exception 'BC_NOTE_NOT_POSTED: pembulatan hanya untuk nota yang disahkan';end if;
  perform pg_advisory_xact_lock(hashtextextended('BCNOTE|'||i.id::text,0)) from erp.contractor_material_issue_items i where i.issue_id=h.id order by i.id;
  perform pg_advisory_xact_lock(hashtextextended('PAYKASBON|'||i.id::text,0)) from erp.contractor_material_issue_items i where i.issue_id=h.id order by i.id;
  if exists(select 1 from erp.bc_note_roundings_v1 r join erp.bc_documents_v1 d on d.id=r.id where r.issue_id=h.id and d.status='POSTED') then
    raise exception 'BC_ROUNDING_EXISTS: nota ini sudah dibulatkan; batalkan pembulatan lama dahulu';end if;
  select round(sum(coalesce(total_receivable,0)),2)-sum(erp.bc_note_item_adjustment_v1(id)) into v_total from erp.contractor_material_issue_items where issue_id=h.id;
  v_round:=round(v_total,0)-v_total;
  if v_round=0 then raise exception 'BC_ROUNDING_NONE: sisa tagihan nota sudah rupiah bulat';end if;
  select id into v_item from erp.contractor_material_issue_items where issue_id=h.id order by total_receivable desc nulls last,id limit 1;
  if erp.bc_note_item_allocated_v1(v_item)>erp.bc_note_item_collectible_v1(v_item)+v_round+0.01 then
    raise exception 'BC_ROUNDING_BELOW_PAID: potongan payroll pada nota ini melebihi hasil pembulatan';end if;
  v_day:=erp.bb_business_today_v1();
  perform erp.bc_new_document_v1(p_request,'ROUND_NOTE',statement_timestamp(),p_payload,jsonb_build_object('ACC_DEC06',erp.bc_policy_version_v1('ACC_DEC06')));
  v_journal:=erp.post_journal('BC_NOTE_ROUNDING',p_request,v_day,'Pembulatan rupiah nota mandor '||h.issue_number,
    case when v_round>0 then jsonb_build_array(
      jsonb_build_object('mapping_key','CONTRACTOR_RECEIVABLE','debit',v_round,'credit',0,'contractor_id',h.contractor_id,'po_id',h.po_id),
      jsonb_build_object('account_id',(v_policy->>'gain_account_id')::uuid,'debit',0,'credit',v_round,'contractor_id',h.contractor_id,'po_id',h.po_id))
    else jsonb_build_array(
      jsonb_build_object('account_id',(v_policy->>'loss_account_id')::uuid,'debit',-v_round,'credit',0,'contractor_id',h.contractor_id,'po_id',h.po_id),
      jsonb_build_object('mapping_key','CONTRACTOR_RECEIVABLE','debit',0,'credit',-v_round,'contractor_id',h.contractor_id,'po_id',h.po_id)) end);
  insert into erp.bc_note_roundings_v1(id,issue_id,item_id,amount,journal_entry_id) values(p_request,h.id,v_item,v_round,v_journal);
  perform erp.bc_link_v1(p_request,'JOURNAL',v_journal);
  perform erp.refresh_contractor_issue_payroll_status(v_item);
  return jsonb_build_object('issue_id',h.id,'rounding',v_round::text,'collectible',(v_total+v_round)::text);
end;$function$;

-- ---------------------------------------------------------------- ERP-DEC02 Special free categories
-- Free basis of one accessory for one contractor at one time: the owner's list names the category and the contractor's
-- effective HPP policy is Special. Null when the policy is pending or it does not apply (then the note needs a price).
CREATE OR REPLACE FUNCTION erp.bc_free_basis_v1(p_material uuid,p_contractor uuid,p_at timestamptz)
 RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select jsonb_build_object('category_id',m.accessory_category_id,'policy_version',erp.bc_policy_version_v1('ERP_DEC02')::text)
  from erp.materials m
  where m.id=p_material and m.material_type='ACCESSORY'
    and coalesce(erp.bc_policy_v1('ERP_DEC02')->'special_free_category_ids','[]'::jsonb) ? m.accessory_category_id::text
    and exists(select 1 from erp.contractor_hpp_policy_versions v where v.contractor_id=p_contractor and v.is_special
      and v.effective_from<=p_at and (v.effective_to is null or v.effective_to>p_at))
$function$;

-- ---------------------------------------------------------------- guards on the source note
-- A note with a return lot or a rounding cannot be reversed by the generic note reversal: undo those first (the return
-- movement and credits depend on it).
CREATE OR REPLACE FUNCTION erp.bc_guard_note_reversal_v1()
 RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
begin
  if new.status='REVERSED' and old.status<>'REVERSED' and (exists(select 1 from erp.bc_return_lots_v1 l join erp.bc_documents_v1 d on d.id=l.document_id
        join erp.contractor_material_issue_items i on i.id=l.note_item_id where i.issue_id=new.id and d.status='POSTED')
      or exists(select 1 from erp.bc_note_roundings_v1 r join erp.bc_documents_v1 d on d.id=r.id where r.issue_id=new.id and d.status='POSTED')) then
    raise exception 'BC_NOTE_HAS_RETURNS: nota ini punya retur atau pembulatan aktif; batalkan dahulu lewat Pemakaian & Pengembalian Aksesori';
  end if;
  return new;
end;$function$;
create trigger trg_bc_note_reversal before update of status on erp.contractor_material_issues
  for each row execute function erp.bc_guard_note_reversal_v1();

-- An opening note-return credit is a settlement of the imported receipt made by one BC credit; it is undone only by reversing
-- that BC document (which also returns the custody), never directly through the opening-settlement continuation.
CREATE OR REPLACE FUNCTION erp.bc_guard_note_credit_settlement_v1()
 RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
begin
  if new.status='REVERSED' and old.status<>'REVERSED' and not erp.bc_in_context_v1()
     and exists(select 1 from erp.bb_opening_credits_v1 c where c.settlement_id=new.id and c.credit_kind='ACCESSORY_NOTE_RETURN') then
    raise exception 'BC_CREDIT_SOURCE_REVERSAL: kredit retur nota dibatalkan lewat dokumen Pemakaian & Pengembalian Aksesori-nya';
  end if;
  return new;
end;$function$;
create trigger trg_bc_note_credit_settlement before update of status on erp.opening_subledger_settlements
  for each row execute function erp.bc_guard_note_credit_settlement_v1();
