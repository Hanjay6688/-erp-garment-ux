-- TEST DOUBLE ONLY. Actual Native qualification must use the complete aligned DB.
create role anon;create role authenticated;create role service_role;
create schema erp;
create table erp.chart_accounts(id uuid primary key,account_code text,account_name text,account_type text,
 normal_balance text,is_active boolean default true,is_postable boolean default true);
create table erp.cash_accounts(id uuid primary key,coa_account_id uuid,cash_account_code text,cash_account_name text,is_active boolean default true);
create table erp.accounting_account_mappings(mapping_key text,account_id uuid);
create table erp.initial_import_prepayments(coa_account_id uuid);
create table erp.journal_entries(id uuid primary key,source_type text,source_id uuid,status text,economic_date date,
 transaction_date date,reversal_of_id uuid);
create table erp.journal_lines(id uuid primary key default gen_random_uuid(),journal_entry_id uuid,account_id uuid,vendor_id uuid,debit numeric(18,2),credit numeric(18,2));
create table erp.bd_laundry_invoices_v1(id uuid primary key,vendor_id uuid,status text,header_total numeric(18,2),
 corrects_invoice_id uuid,invoice_date date,invoice_number text,journal_id uuid,reversal_journal_id uuid);
create table erp.vendor_invoices(id uuid primary key,vendor_id uuid,status text,total_amount numeric(18,2),invoice_date date,invoice_number text,updated_at timestamptz);
create table erp.vendor_payments(id uuid primary key,vendor_invoice_id uuid,payment_number text,payment_date timestamptz,amount numeric(18,2),
 cash_account_id uuid,payment_method text,reference_number text,status text,notes text,created_by uuid);
create table erp.opening_subledger_settlements(id uuid primary key,balance_id uuid,settlement_number text,physical_at timestamptz,amount numeric(18,2),cash_account_id uuid,status text,notes text,created_by uuid);
create table erp.opening_subledger_balances(id uuid primary key,vendor_id uuid,party_type text,direction text,original_amount numeric,settled_amount numeric,status text);
create table erp.bd_claim_credit_applications_v1(id uuid primary key,vendor_id uuid,source_kind text,laundry_claim_id uuid,
 opening_claim_event_id uuid,correction_invoice_id uuid,target_kind text,vendor_payment_id uuid,opening_settlement_id uuid,amount numeric(18,2),applied_date date,reason text,created_by uuid);
create table erp.bd_requests_v1(request_id uuid primary key,action text,actor uuid,payload jsonb,response jsonb);
create function erp.current_app_user_id()returns uuid language sql as $$select nullif(current_setting('app.actor',true),'')::uuid$$;
create function erp.require_owner_admin()returns void language plpgsql as $$begin
 if erp.current_app_user_id()is null or current_setting('app.allowed',true)is distinct from'true'then raise exception 'TEST_ACCESS_DENIED';end if;end$$;
create function erp.require_permission(text)returns void language plpgsql as $$begin perform erp.require_owner_admin();end$$;
create function erp._cp3_assert_closed_json_object(p jsonb,required text[],allowed text[],label text)returns void language plpgsql as $$begin
 if jsonb_typeof(p)is distinct from'object'or exists(select 1 from unnest(required)k where not p?k)
 or exists(select 1 from jsonb_object_keys(p)k where not k=any(allowed))then raise exception 'TEST_CLOSED_PAYLOAD';end if;end$$;
create function erp.bb_parse_date_v1(p text,label text)returns date language plpgsql as $$begin
 if p is null or p!~'^\d{4}-\d{2}-\d{2}$'then raise exception 'TEST_DATE_INVALID';end if;return p::date;end$$;
create function erp.bb_business_today_v1()returns date language sql as $$select current_date$$;
create function erp.bb_physical_at_v1(p date)returns timestamptz language sql as $$select p::timestamp at time zone'Asia/Jakarta'$$;
create function erp._cp3_business_date(p timestamptz)returns date language sql as $$select(p at time zone'Asia/Jakarta')::date$$;
create function erp.account_id(p text)returns uuid language sql as $$select account_id from erp.accounting_account_mappings where mapping_key=p$$;
create function erp.bd_claim_credit_source_v1(k text,p uuid)returns jsonb language sql as $$
 select jsonb_build_object('kind',k,'id',id,'vendor_id',vendor_id,'number',invoice_number,'amount',(-header_total)::text,
 'approved_date',invoice_date,'active',status='POSTED')from erp.bd_laundry_invoices_v1 where id=p$$;
-- The retained router plans its complete CASE. Unused commands are explicit
-- failing doubles, never successful substitutes for untested Native behavior.
do $$declare n text;begin
 foreach n in array array['bd_set_policy_v1','bd_post_priced_delivery_v1','bd_set_charge_price_v1',
 'bd_save_invoice_draft_v1','bd_cancel_invoice_draft_v1','bd_post_invoice_v1','bd_reverse_invoice_v1',
 'bd_set_opening_estimate_v1','bd_apply_claim_credit_v1','bd_pay_vendor_document_v1','bd_reverse_vendor_settlement_v1']loop
 execute format('create function erp.%I(jsonb,uuid)returns jsonb language plpgsql as $body$begin raise exception ''TEST_UNSUPPORTED_NATIVE_COMMAND'';end$body$',n);
 end loop;
end$$;
create function erp.bd_save_master_v1(text,jsonb,uuid)returns jsonb language plpgsql as $$begin raise exception 'TEST_UNSUPPORTED_NATIVE_COMMAND';end$$;
create function erp.post_journal(k text,source uuid,d date,description text,lines jsonb)returns uuid language plpgsql as $$
 declare ident uuid:=gen_random_uuid();r jsonb;total numeric:=0;
 begin
 for r in select *from jsonb_array_elements(lines)loop total:=total+(r->>'debit')::numeric-(r->>'credit')::numeric;end loop;
 if total<>0 then raise exception 'TEST_JOURNAL_UNBALANCED';end if;
 insert into erp.journal_entries values(ident,k,source,'POSTED',d,d,null);
 for r in select *from jsonb_array_elements(lines)loop
 insert into erp.journal_lines(journal_entry_id,account_id,vendor_id,debit,credit)
 values(ident,coalesce((r->>'account_id')::uuid,erp.account_id(r->>'mapping_key')),(r->>'vendor_id')::uuid,(r->>'debit')::numeric,(r->>'credit')::numeric);end loop;
 return ident;end$$;
create function erp.reverse_journal(p uuid,why text)returns uuid language plpgsql as $$
 declare ident uuid:=gen_random_uuid();j erp.journal_entries%rowtype;
 begin select *into strict j from erp.journal_entries where id=p;
 if j.status<>'POSTED'then raise exception 'TEST_JOURNAL_NOT_POSTED';end if;
 insert into erp.journal_entries values(ident,'REVERSAL',j.source_id,'POSTED',current_date,current_date,p);
 insert into erp.journal_lines(journal_entry_id,account_id,vendor_id,debit,credit)
 select ident,account_id,vendor_id,credit,debit from erp.journal_lines where journal_entry_id=p;
 update erp.journal_entries set status='REVERSED'where id=p;return ident;end$$;
