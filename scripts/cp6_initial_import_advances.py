"""Opening cash advances retain provenance and settle through real payroll.

Proposal only: installed by the disposable AO/AP trial, never on a hosted DB.
This first advance family is contractor cash advances; supplier/customer/vendor
advances have different accounting contracts and are not admitted by it.
"""
import json
from pathlib import Path

PREDECESSOR = json.loads(Path('docs/evidence/cp6-initial-import-advance-predecessor.json').read_text())['functions']

SCHEMA = r"""
alter table erp.initial_import_financial_sources add column source_kind text not null default 'BALANCE'
 check(source_kind in('BALANCE','CONTRACTOR_CASH_ADVANCE'));
alter table erp.initial_import_financial_sources add constraint initial_import_cash_advance_source
 check(source_kind='BALANCE' or (balance_type='CONTRACTOR_RECEIVABLE' and source_mode='DOCUMENT'));
alter table erp.payroll_deductions add column opening_cash_advance_balance_id uuid
 references erp.opening_subledger_balances(id);
alter table erp.payroll_deductions drop constraint payroll_deductions_deduction_type_check;
alter table erp.payroll_deductions add constraint payroll_deductions_deduction_type_check
 check(deduction_type in('MATERIAL_KASBON','BS_COMPENSATION','PENALTY','OTHER','CASH_ADVANCE'));
alter table erp.payroll_deductions add constraint payroll_cash_advance_source_check check(
 (deduction_type='CASH_ADVANCE' and opening_cash_advance_balance_id is not null
   and contractor_issue_item_id is null and bs_resolution_id is null)
 or (deduction_type<>'CASH_ADVANCE' and opening_cash_advance_balance_id is null));
create index payroll_cash_advance_balance on erp.payroll_deductions(opening_cash_advance_balance_id,payroll_id)
 where opening_cash_advance_balance_id is not null;
create unique index payroll_cash_advance_once on erp.payroll_deductions(payroll_id,opening_cash_advance_balance_id)
 where opening_cash_advance_balance_id is not null;
"""

STATE = r"""CREATE OR REPLACE FUNCTION erp.opening_cash_advance_state_v1(p_balance_id uuid)
RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO '' AS $function$
 select jsonb_build_object('balance_id',b.id,'contractor_id',b.contractor_id,
   'document_number',s.document_number,'document_date',s.document_date,'cutover_date',s.cutover_date,
   'original_amount',s.original_amount::text,'settled_before_cutover',s.settled_before_cutover::text,
   'opening_amount',b.original_amount::text,'settled_amount',b.settled_amount::text,
   'remaining_amount',(b.original_amount-b.settled_amount)::text,
   'reserved_amount',x.reserved::numeric(20,2)::text,
   'available_amount',(b.original_amount-b.settled_amount-x.reserved)::numeric(20,2)::text,
   'status',b.status)
 from erp.opening_subledger_balances b
 join erp.initial_import_financial_sources s on s.opening_item_id=b.opening_item_id
   and s.source_kind='CONTRACTOR_CASH_ADVANCE'
 cross join lateral(select coalesce(sum(d.amount),0) reserved
   from erp.payroll_deductions d join erp.payroll_settlements p on p.id=d.payroll_id
   where d.opening_cash_advance_balance_id=b.id and p.status not in('PAID','REVERSED')) x
 where b.id=p_balance_id;
$function$;
"""

GUARD_DEDUCTION = r"""CREATE OR REPLACE FUNCTION erp.guard_opening_cash_advance_deduction_v1()
RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path TO '' AS $function$
declare p erp.payroll_settlements%rowtype;b erp.opening_subledger_balances%rowtype;
 v_reserved numeric;v_earnings numeric;v_deductions numeric;v_id uuid;v_date date;
begin
 if TG_OP='DELETE' then
   if old.opening_cash_advance_balance_id is null then return old;end if;
   v_id:=old.payroll_id;
 else
   if new.opening_cash_advance_balance_id is null and new.deduction_type<>'CASH_ADVANCE'
     and (TG_OP='INSERT' or old.opening_cash_advance_balance_id is null) then return new;end if;
   v_id:=new.payroll_id;
 end if;
 -- Only the controlled writer may reach the typed numeric column. Direct DML
 -- would coerce excess precision before this trigger could inspect the input.
 if current_user<>'postgres' then raise exception 'Alokasi kasbon tunai harus melalui command resmi';end if;
 perform erp.require_internal();
 if TG_OP='UPDATE' and (new.payroll_id<>old.payroll_id
   or new.opening_cash_advance_balance_id is distinct from old.opening_cash_advance_balance_id
   or new.deduction_type is distinct from old.deduction_type) then
   raise exception 'Sumber kasbon payroll tidak dapat dipindah; hapus alokasi draft lalu pilih sumber yang benar';end if;
 select * into p from erp.payroll_settlements where id=v_id for update;
 if p.id is null or p.status not in('DRAFT','CALCULATED','REVIEW') then
   raise exception 'Alokasi kasbon hanya boleh diedit pada payroll draft';end if;
 if TG_OP='DELETE' then
   perform 1 from erp.opening_subledger_balances where id=old.opening_cash_advance_balance_id for update;
   return old;
 end if;
 if new.deduction_type<>'CASH_ADVANCE' or new.opening_cash_advance_balance_id is null
   or new.contractor_issue_item_id is not null or new.bs_resolution_id is not null
   or new.amount is null or new.amount::text in('NaN','Infinity','-Infinity')
   or new.amount<=0 or new.amount<>round(new.amount,2) then
   raise exception 'Alokasi kasbon memerlukan sumber tunai dan nominal positif tepat dua desimal';end if;
 select * into b from erp.opening_subledger_balances where id=new.opening_cash_advance_balance_id for update;
 select s.cutover_date into v_date from erp.initial_import_financial_sources s
   join erp.opening_balance_headers h on h.migration_batch_id=s.batch_id and h.status='POSTED'
   where s.opening_item_id=b.opening_item_id and s.source_kind='CONTRACTOR_CASH_ADVANCE';
 if b.id is null or v_date is null or b.party_type<>'CONTRACTOR' or b.direction<>'RECEIVABLE'
   or b.contractor_id is distinct from p.contractor_id then
   raise exception 'Kasbon tunai harus berasal dari saldo awal sah milik mandor payroll ini';end if;
 select coalesce(sum(d.amount),0) into v_reserved from erp.payroll_deductions d
   join erp.payroll_settlements ps on ps.id=d.payroll_id
   where d.opening_cash_advance_balance_id=b.id and d.id<>new.id and ps.status not in('PAID','REVERSED');
 if new.amount>b.original_amount-b.settled_amount-v_reserved then
   raise exception 'Alokasi melebihi sisa kasbon yang belum dipakai payroll lain';end if;
 select coalesce((select sum(amount) from erp.payroll_work_items where payroll_id=p.id),0)
   +case when c.attendance_required then coalesce((select sum(amount) from erp.payroll_attendance_items where payroll_id=p.id),0) else 0 end
   +coalesce((select sum(amount) from erp.payroll_reimbursements where payroll_id=p.id),0)
   +p.manual_adjustment into v_earnings from erp.contractors c where c.id=p.contractor_id;
 select coalesce(sum(amount),0) into v_deductions from erp.payroll_deductions where payroll_id=p.id and id<>new.id;
 if new.amount>greatest(v_earnings-v_deductions,0) then
   raise exception 'Potongan kasbon melebihi pendapatan payroll; sisanya dibawa ke periode berikutnya';end if;
 return new;
end;$function$;
"""

CHECK_PAYROLL = r"""CREATE OR REPLACE FUNCTION erp.check_opening_cash_advance_payroll_v1(p_payroll_id uuid)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' AS $function$
declare p erp.payroll_settlements%rowtype;r record;v_reserved numeric;v_cash numeric;v_all numeric;
begin
 perform erp.require_internal();
 select * into p from erp.payroll_settlements where id=p_payroll_id for update;
 if p.id is null then raise exception 'Payroll tidak ditemukan';end if;
 select coalesce(sum(amount),0) into v_cash from erp.payroll_deductions
   where payroll_id=p.id and deduction_type='CASH_ADVANCE';
 if v_cash=0 then return;end if;
 select coalesce(sum(amount),0) into v_all from erp.payroll_deductions where payroll_id=p.id;
 if p.deduction_total<>v_all or p.net_payable<0 then
   raise exception 'Hitung ulang payroll: total potongan harus cocok dan tidak boleh melebihi pendapatan';end if;
 for r in select b.*,s.cutover_date,s.source_kind,s.party_id,
     (select sum(d.amount) from erp.payroll_deductions d where d.payroll_id=p.id and d.opening_cash_advance_balance_id=b.id) amount
   from erp.opening_subledger_balances b left join erp.initial_import_financial_sources s on s.opening_item_id=b.opening_item_id
   where exists(select 1 from erp.payroll_deductions d where d.payroll_id=p.id and d.opening_cash_advance_balance_id=b.id)
   order by b.id for update of b loop
   if r.source_kind is distinct from 'CONTRACTOR_CASH_ADVANCE' or r.contractor_id is distinct from p.contractor_id
     or r.party_id is distinct from p.contractor_id or r.party_type<>'CONTRACTOR' or r.direction<>'RECEIVABLE'
     or p.payment_date<r.cutover_date then raise exception 'Sumber mandor/tanggal pembayaran kasbon tidak cocok';end if;
   select coalesce(sum(d.amount),0) into v_reserved from erp.payroll_deductions d
     join erp.payroll_settlements ps on ps.id=d.payroll_id
     where d.opening_cash_advance_balance_id=r.id and d.payroll_id<>p.id and ps.status not in('PAID','REVERSED');
   if r.amount>r.original_amount-r.settled_amount-v_reserved then
     raise exception 'Saldo kasbon berubah atau sudah dialokasikan pada payroll lain';end if;
 end loop;
end;$function$;
"""

GUARD_BALANCE = r"""CREATE OR REPLACE FUNCTION erp.guard_opening_cash_advance_balance_v1()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' AS $function$
declare v_reserved numeric;
begin
 if not exists(select 1 from erp.initial_import_financial_sources s
   where s.opening_item_id=new.opening_item_id and s.source_kind='CONTRACTOR_CASH_ADVANCE') then return new;end if;
 select coalesce(sum(d.amount),0) into v_reserved from erp.payroll_deductions d
   join erp.payroll_settlements p on p.id=d.payroll_id
   where d.opening_cash_advance_balance_id=new.id and p.status not in('PAID','REVERSED');
 if new.original_amount<new.settled_amount+v_reserved then
   raise exception 'Saldo kasbon tidak cukup setelah pembayaran dan alokasi payroll; lepaskan alokasi terlebih dahulu';end if;
 return new;
end;$function$;
"""

SET_ALLOCATION = r"""CREATE OR REPLACE FUNCTION erp.set_opening_cash_advance_payroll_v1(
 p_balance_id uuid,p_payroll_id uuid,p_amount numeric,p_expected_version bigint)
RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' AS $function$
declare p erp.payroll_settlements%rowtype;v_id uuid;
begin
 perform erp.require_owner_admin();
 if p_amount is null or p_amount::text in('NaN','Infinity','-Infinity') or p_amount<0 or p_amount<>round(p_amount,2) then
   raise exception 'Nominal alokasi harus tepat dua desimal; gunakan nol untuk melepaskan alokasi';end if;
 select * into p from erp.payroll_settlements where id=p_payroll_id for update;
 if p.id is null or p.status not in('DRAFT','CALCULATED','REVIEW') then raise exception 'Payroll harus draft';end if;
 if p_expected_version is null or p.row_version<>p_expected_version then raise exception 'STALE_VERSION: payroll berubah';end if;
 if erp.opening_cash_advance_state_v1(p_balance_id) is null then raise exception 'Saldo kasbon tunai tidak ditemukan';end if;
 select id into v_id from erp.payroll_deductions where payroll_id=p.id and opening_cash_advance_balance_id=p_balance_id;
 if p_amount=0 then
   if v_id is null then raise exception 'Alokasi yang akan dilepas tidak ditemukan';end if;
   delete from erp.payroll_deductions where id=v_id;
 elsif v_id is null then
   insert into erp.payroll_deductions(payroll_id,deduction_type,opening_cash_advance_balance_id,amount,notes)
     values(p.id,'CASH_ADVANCE',p_balance_id,p_amount,'Alokasi kasbon tunai saldo awal') returning id into v_id;
 else update erp.payroll_deductions set amount=p_amount where id=v_id;
 end if;
 perform erp.recalculate_payroll(p.id);
 return v_id;
end;$function$;
"""

TRIGGERS = r"""
create trigger trg_opening_cash_advance_deduction before insert or update or delete on erp.payroll_deductions
 for each row execute function erp.guard_opening_cash_advance_deduction_v1();
create trigger trg_opening_cash_advance_balance before update on erp.opening_subledger_balances
 for each row execute function erp.guard_opening_cash_advance_balance_v1();
"""


def extend_advance_contract(functions):
    def change(identity, old, new, count=1):
        assert functions[identity].count(old)==count,(identity,old,functions[identity].count(old))
        functions[identity]=functions[identity].replace(old,new)
    for identity,definition,*_ in PREDECESSOR:
        assert identity not in functions,identity
        functions[identity]=definition
    functions.update({
      'erp.opening_cash_advance_state_v1(uuid)':STATE,
      'erp.guard_opening_cash_advance_deduction_v1()':GUARD_DEDUCTION,
      'erp.check_opening_cash_advance_payroll_v1(uuid)':CHECK_PAYROLL,
      'erp.guard_opening_cash_advance_balance_v1()':GUARD_BALANCE,
      'erp.set_opening_cash_advance_payroll_v1(uuid,uuid,numeric,bigint)':SET_ALLOCATION,
    })
    identity='erp.initial_import_revision_v1(uuid)'
    old="   'items',coalesce("
    change(identity,old,"""   'advance_balances',coalesce((select jsonb_agg(to_jsonb(bs) order by bs.id)
     from erp.opening_subledger_balances bs join erp.initial_import_financial_sources s on s.opening_item_id=bs.opening_item_id
     where s.batch_id=p_batch_id and s.source_kind='CONTRACTOR_CASH_ADVANCE'),'[]'::jsonb),
   'advance_deductions',coalesce((select jsonb_agg(to_jsonb(d) order by d.id)
     from erp.payroll_deductions d join erp.opening_subledger_balances bs on bs.id=d.opening_cash_advance_balance_id
     join erp.initial_import_financial_sources s on s.opening_item_id=bs.opening_item_id where s.batch_id=p_batch_id),'[]'::jsonb),
   'advance_payrolls',coalesce((select jsonb_agg(to_jsonb(p) order by p.id) from erp.payroll_settlements p
     where exists(select 1 from erp.initial_import_financial_sources s where s.batch_id=p_batch_id
       and s.source_kind='CONTRACTOR_CASH_ADVANCE' and s.party_id=p.contractor_id)),'[]'::jsonb),
"""+old)
    identity='erp.save_initial_import_action_v1(text,jsonb,uuid)'
    change(identity,"('CREATE','SAVE_FILE','VALIDATE','FINALIZE')", "('CREATE','SAVE_FILE','VALIDATE','FINALIZE','ALLOCATE_CASH_ADVANCE')")
    old=" else\n   v_batch:=nullif(p_payload->>'batch_id','')::uuid;"
    change(identity,old,""" elsif v_action='ALLOCATE_CASH_ADVANCE' then
   v_batch:=nullif(p_payload->>'batch_id','')::uuid;
   select * into b from erp.migration_batches where id=v_batch for update;
   if b.id is null or b.status<>'POSTED' then raise exception 'Kasbon harus berasal dari impor yang sudah disahkan';end if;
   perform 1 from erp.payroll_settlements where id=(p_payload->>'payroll_id')::uuid for update;
   perform 1 from erp.opening_subledger_balances where id=(p_payload->>'balance_id')::uuid for update;
   if p_payload->>'expected_revision' is distinct from erp.initial_import_revision_v1(b.id) then
     raise exception 'STALE_VERSION: saldo atau payroll berubah; muat ulang sebelum mengalokasikan';end if;
   if not exists(select 1 from erp.initial_import_financial_sources s join erp.opening_subledger_balances bs on bs.opening_item_id=s.opening_item_id
     where s.batch_id=b.id and s.source_kind='CONTRACTOR_CASH_ADVANCE' and bs.id=(p_payload->>'balance_id')::uuid) then
     raise exception 'Saldo kasbon bukan milik batch ini';end if;
   if coalesce(p_payload->>'amount','') !~ '^[0-9]+([.,][0-9]{1,2})?$' then
     raise exception 'amount: gunakan nominal positif tepat dua desimal atau nol untuk melepas alokasi';end if;
   perform erp.set_opening_cash_advance_payroll_v1((p_payload->>'balance_id')::uuid,
     (p_payload->>'payroll_id')::uuid,replace(p_payload->>'amount',',','.')::numeric,
     (p_payload->>'expected_payroll_version')::bigint);
 else
   v_batch:=nullif(p_payload->>'batch_id','')::uuid;""")
    identity='erp.check_initial_import_financial_source_v1(uuid,uuid,uuid)'
    change(identity," j:=r.normalized_payload;v_type:=upper(j->>'balance_type');", """ j:=r.normalized_payload;v_type:=upper(j->>'balance_type');
 if coalesce(nullif(j->>'source_kind',''),'BALANCE') not in('BALANCE','CONTRACTOR_CASH_ADVANCE') then
   raise exception 'source_kind: gunakan BALANCE atau CONTRACTOR_CASH_ADVANCE';end if;
 if j->>'source_kind'='CONTRACTOR_CASH_ADVANCE' and (v_type is distinct from 'CONTRACTOR_RECEIVABLE'
   or nullif(btrim(j->>'document_number'),'') is null) then
   raise exception 'source_kind: kasbon tunai wajib rincian dokumen CONTRACTOR_RECEIVABLE';end if;
""")
    change(identity,'outstanding_amount)\n   values(', 'outstanding_amount,source_kind)\n   values(')
    change(identity,'v_original,v_paid,v_amount);','v_original,v_paid,v_amount,coalesce(nullif(j->>\'source_kind\',\'\'),\'BALANCE\'));')
    identity='erp.approve_payroll(uuid)'
    change(identity,'  perform erp._cp3_lock_business_period(p.period_start,p.period_end);',
      '  perform erp.check_opening_cash_advance_payroll_v1(p.id);\n  perform erp._cp3_lock_business_period(p.period_start,p.period_end);')
    identity='erp.post_payroll_payment(uuid)'
    change(identity,'  v_other_deduction numeric(20,2):=0;', '  v_other_deduction numeric(20,2):=0;v_cash_advance numeric(20,2):=0;')
    change(identity,'  perform erp._cp3_lock_business_period(p.period_start,p.period_end);',
      '  perform erp.check_opening_cash_advance_payroll_v1(p.id);\n  perform erp._cp3_lock_business_period(p.period_start,p.period_end);')
    change(identity,"deduction_type<>'MATERIAL_KASBON';", "deduction_type not in('MATERIAL_KASBON','CASH_ADVANCE');")
    change(identity,'  if v_other_deduction>0 then', """  select coalesce(sum(amount),0) into v_cash_advance from erp.payroll_deductions
    where payroll_id=p.id and deduction_type='CASH_ADVANCE';
  if v_cash_advance>0 then
    perform erp.post_journal('PAYROLL_CASH_ADVANCE_DEDUCTION',p.id,p.payment_date,'Pelunasan kasbon tunai melalui payroll',jsonb_build_array(
      jsonb_build_object('mapping_key','CONTRACTOR_PAYABLE','debit',v_cash_advance,'credit',0,'contractor_id',p.contractor_id),
      jsonb_build_object('mapping_key','CONTRACTOR_RECEIVABLE','debit',0,'credit',v_cash_advance,'contractor_id',p.contractor_id)));
  end if;
  if v_other_deduction>0 then""")
    old="  update erp.payroll_settlements set status='PAID',settled_at=statement_timestamp(),updated_at=statement_timestamp() where id=p.id;"
    change(identity,old,old+"""
  update erp.opening_subledger_balances b set settled_amount=b.settled_amount+x.amount,
    status=case when b.settled_amount+x.amount=b.original_amount then 'SETTLED' else 'PARTIAL' end,updated_at=statement_timestamp()
  from(select opening_cash_advance_balance_id id,sum(amount) amount from erp.payroll_deductions
    where payroll_id=p.id and deduction_type='CASH_ADVANCE' group by opening_cash_advance_balance_id) x where b.id=x.id;
""")
    identity='erp.reverse_paid_payroll(uuid,text)'
    old='  perform erp._cp3_lock_business_period(p.period_start,p.period_end);'
    change(identity,old,"""  perform 1 from erp.opening_subledger_balances b where exists(select 1 from erp.payroll_deductions d
    where d.payroll_id=p.id and d.opening_cash_advance_balance_id=b.id) order by b.id for update;
"""+old)
    change(identity,"'PAYROLL_MATERIAL_DEDUCTION','PAYROLL_OTHER_DEDUCTION','PAYROLL_PAYMENT')",
      "'PAYROLL_MATERIAL_DEDUCTION','PAYROLL_OTHER_DEDUCTION','PAYROLL_PAYMENT','PAYROLL_CASH_ADVANCE_DEDUCTION')")
    old="  update erp.payroll_settlements set status='REVERSED',settled_at=null,updated_at=statement_timestamp() where id=p.id;"
    change(identity,old,old+"""
  update erp.opening_subledger_balances b set settled_amount=b.settled_amount-x.amount,
    status=case when b.settled_amount-x.amount=b.original_amount then 'SETTLED' when b.settled_amount-x.amount>0 then 'PARTIAL' else 'OPEN' end,
    updated_at=statement_timestamp()
  from(select opening_cash_advance_balance_id id,sum(amount) amount from erp.payroll_deductions
    where payroll_id=p.id and deduction_type='CASH_ADVANCE' group by opening_cash_advance_balance_id) x where b.id=x.id;
""")
    identity='erp.post_opening_subledger_settlement(uuid)'
    old='v_remaining:=b.original_amount-b.settled_amount;'
    change(identity,old,"""v_remaining:=b.original_amount-b.settled_amount;
IF erp.opening_cash_advance_state_v1(b.id) IS NOT NULL THEN
 IF erp._cp3_business_date(s.physical_at)<(erp.opening_cash_advance_state_v1(b.id)->>'cutover_date')::date THEN
   RAISE EXCEPTION 'Pengembalian kasbon harus sejak tanggal saldo awal';END IF;
 v_remaining:=(erp.opening_cash_advance_state_v1(b.id)->>'available_amount')::numeric;
END IF;""")
    identity='erp.run_v267_financial_truth_checks()'
    old="where s.balance_id=b.id and s.status='POSTED'),0) paid) x"
    change(identity,old,"""where s.balance_id=b.id and s.status='POSTED'),0)
    +coalesce((select sum(d.amount) from erp.payroll_deductions d join erp.payroll_settlements p on p.id=d.payroll_id
      where d.opening_cash_advance_balance_id=b.id and p.status='PAID'),0) paid) x""")
    old=';\n\n$function$'
    change(identity,old,"""
  union all
  select 'AP_CASH_ADVANCE_CAPACITY','CRITICAL',count(*)::bigint,
    'Cash advance settlements plus unpaid payroll reservations must not exceed the current opening source'
  from erp.opening_subledger_balances b cross join lateral(select erp.opening_cash_advance_state_v1(b.id) s) x
  where x.s is not null and (x.s->>'available_amount')::numeric<0
  union all
  select 'AP_CASH_ADVANCE_SOURCE','CRITICAL',count(*)::bigint,
    'Cash payroll deductions must reference a posted cash advance belonging to the same contractor'
  from erp.payroll_deductions d join erp.payroll_settlements p on p.id=d.payroll_id
  left join erp.opening_subledger_balances b on b.id=d.opening_cash_advance_balance_id
  left join erp.initial_import_financial_sources s on s.opening_item_id=b.opening_item_id
  where d.deduction_type='CASH_ADVANCE' and (s.source_kind is distinct from 'CONTRACTOR_CASH_ADVANCE'
    or s.party_id is distinct from p.contractor_id or b.contractor_id is distinct from p.contractor_id
    or (p.status='PAID' and p.payment_date<s.cutover_date))
  union all
  select 'AP_CASH_ADVANCE_PAYROLL_JOURNAL','CRITICAL',count(*)::bigint,
    'Cash advance payroll settles receivable/payable once, with exact date and contractor dimensions'
  from erp.payroll_settlements p
  cross join lateral(select coalesce(sum(amount),0) amount from erp.payroll_deductions
    where payroll_id=p.id and deduction_type='CASH_ADVANCE') d
  where (d.amount>0 and p.status='PAID' and not exists(select 1 from erp.journal_entries j
    where j.source_type='PAYROLL_CASH_ADVANCE_DEDUCTION' and j.source_id=p.id and j.status='POSTED'
      and j.economic_date=p.payment_date
      and erp._cp6_supplier_cent_ledger(array[j.id])=jsonb_build_object(
        erp.account_id('CONTRACTOR_PAYABLE')::text,d.amount,erp.account_id('CONTRACTOR_RECEIVABLE')::text,-d.amount)
      and not exists(select 1 from erp.journal_lines l where l.journal_entry_id=j.id and l.contractor_id is distinct from p.contractor_id)))
    or((p.status<>'PAID' or d.amount=0) and exists(select 1 from erp.journal_entries j where j.source_type='PAYROLL_CASH_ADVANCE_DEDUCTION'
      and j.source_id=p.id and j.status='POSTED'))
"""+old)
    identity='erp.get_initial_import_workspace_v1(uuid)'
    old="     'opening_id',(select h.id"
    change(identity,old,"""     'cash_advances',coalesce((select jsonb_agg(erp.opening_cash_advance_state_v1(bs.id)||jsonb_build_object(
       'contractor_code',c.contractor_code,'contractor_name',c.contractor_name,
       'allocations',coalesce((select jsonb_agg(jsonb_build_object('payroll_id',p.id,'payroll_number',p.payroll_number,
         'status',p.status,'row_version',p.row_version::text,'amount',d.amount::text) order by p.period_end,p.id)
         from erp.payroll_deductions d join erp.payroll_settlements p on p.id=d.payroll_id
         where d.opening_cash_advance_balance_id=bs.id and p.status<>'REVERSED'),'[]'::jsonb)) order by s.document_number,bs.id)
       from erp.initial_import_financial_sources s join erp.opening_subledger_balances bs on bs.opening_item_id=s.opening_item_id
       join erp.contractors c on c.id=bs.contractor_id where s.batch_id=b.id and s.source_kind='CONTRACTOR_CASH_ADVANCE'),'[]'::jsonb),
     'advance_payrolls',coalesce((select jsonb_agg(to_jsonb(x) order by x.period_end,x.id) from(
       select p.id,p.payroll_number,p.contractor_id,p.period_end,p.row_version::text,p.net_payable::text
       from erp.payroll_settlements p where p.status in('DRAFT','CALCULATED','REVIEW') and exists(
         select 1 from erp.initial_import_financial_sources s where s.batch_id=b.id
           and s.source_kind='CONTRACTOR_CASH_ADVANCE' and s.party_id=p.contractor_id)
       order by p.period_end,p.id limit 100) x),'[]'::jsonb),
"""+old)
    # LANGUAGE sql validates referenced functions when installed. The native
    # financial checker above now calls this helper, so install it first.
    first='erp.opening_cash_advance_state_v1(uuid)'
    ordered={first:functions[first],**functions}
    functions.clear()
    functions.update(ordered)
