-- Use the request identity carried by the existing authenticated invoice and document calls.
do $supplier_identity$
declare
    item_ record;
    r_ name;
    f_ record;
    accessor_ record;
    changed_ text;
    roles_ constant name[]:=array['cp7_invoice_read','cp7_invoice_write','cp7_transaction_source_read']::name[];
    memberships_ jsonb;
    owners_ jsonb;
begin
    if session_user <> 'postgres' or current_user <> 'postgres' or current_setting('is_superuser') <> 'off' then
        raise exception 'Expected the managed Enteng Uji installer';
    end if;
    foreach r_ in array roles_ loop
        if pg_has_role('postgres',r_,'SET') or pg_has_role('postgres',r_,'USAGE') or
            not exists(select from pg_roles where rolname=r_ and not (rolcanlogin or rolsuper or rolcreaterole or rolcreatedb) and rolbypassrls=(r_ in ('cp7_invoice_read','cp7_transaction_source_read')))
            or exists(select from unnest(array['anon','authenticated','service_role']) a where pg_has_role(a,r_,'SET')) then
            raise exception 'Expected a private invoice or trace role';
        end if;
    end loop;
    for accessor_ in select * from (values
        ('uid','uuid','9ab5ea099e74ec09e83b1505c51a3647791195aed7c742dcc3f257dfc7d2f300'),
        ('jwt','jsonb','fed2a8ac0349ffaba807c1b574698bfb1348825b8ef5163ad72d8408386f5e3e')
    ) v(method,returns,pin) loop
        if not exists(select from pg_proc p where p.oid=to_regprocedure('cp7_request_context.'||accessor_.method||'()')
            and p.proowner='postgres'::regrole and not p.prosecdef and p.provolatile='s'
            and p.pronargs=0 and p.prorettype::regtype::text=accessor_.returns and p.proconfig=array['search_path=""']::text[]
            and encode(sha256(convert_to(p.prosrc,'UTF8')),'hex')=accessor_.pin
            and not exists(select from unnest(array['anon','authenticated','service_role']) a
               where has_schema_privilege(a,'cp7_request_context','USAGE') or has_function_privilege(a,p.oid,'EXECUTE'))) then
            raise exception 'Unexpected operator identity reader';
        end if;
    end loop;
    select jsonb_agg(to_jsonb(m) order by m.roleid,m.grantor) into memberships_ from pg_auth_members m
        where m.member='postgres'::regrole and (m.roleid::regrole::text)::name=any(roles_);
    select jsonb_object_agg(nspname,jsonb_build_array(nspowner,nspacl::text)) into owners_ from pg_namespace
        where nspname=any(array['cp7_invoice','cp7_supplier_payment_correction','cp7_supplier_payment_create','cp7_transaction_source']);
    grant cp7_invoice_read,cp7_invoice_write,cp7_transaction_source_read to postgres with inherit false, set true granted by postgres;
    grant usage on schema cp7_request_context to cp7_invoice_read,cp7_invoice_write,cp7_transaction_source_read;
    grant execute on function cp7_request_context.uid() to cp7_invoice_read,cp7_invoice_write,cp7_transaction_source_read;
    grant execute on function cp7_request_context.jwt() to cp7_invoice_read;
    for item_ in select * from (values
      ('cp7_invoice.access_now()','cp7_invoice_read','cp7_invoice_read',3,'ea2ead29e52da76ebfefb1723e247388a58d152d0dbe71ee13f2ba988d053dc2'),
      ('cp7_invoice.document_command(text,jsonb,uuid,text)','cp7_invoice_write','cp7_invoice_read',3,'4e5ca9d182885619064f3e10f36a6b50fc37fc6263928b0c20181c7d6bf3d0d6'),
      ('cp7_invoice.reverse_payment_request(jsonb,uuid)','cp7_invoice_write','cp7_invoice_read',3,'c1c7d4a3be01d4456f098e2f282591f7b43df51076496a713182132421714ff7'),
      ('cp7_supplier_payment_correction.command(jsonb,uuid)','cp7_invoice_write','cp7_invoice_read',4,'b0400403a8030ea92710ec5c85fab0d46d98b29a67fd3b86ec2f330e0148b783'),
      ('cp7_supplier_payment_create.command(jsonb,uuid)','cp7_invoice_write','cp7_invoice_read',4,'8cffb704284cba96535135cb93e0a206fec31ed5b9bf8a284319f2a32db850fc'),
      ('cp7_transaction_source.dependencies(jsonb,integer)','cp7_transaction_source_read','cp7_transaction_source_read',1,'354f81ff9255e9b52b47b45fcff69ee5ac854a7150f1a7e4c1037135db699a20')
    ) v(signature,owner_role,schema_owner,calls,pin) loop
        select p.oid,p.prosrc body,to_jsonb(p)-'prosrc' metadata,pg_get_functiondef(p.oid) ddl,
            n.nspname schema_name,has_schema_privilege(p.proowner,n.oid,'CREATE') can_create into strict f_
            from pg_proc p join pg_namespace n on n.oid=p.pronamespace
            where p.oid=to_regprocedure(item_.signature) and pg_get_userbyid(p.proowner)=item_.owner_role
              and pg_get_userbyid(n.nspowner)=item_.schema_owner and not p.prosecdef
              and encode(sha256(convert_to(p.prosrc,'UTF8')),'hex')=item_.pin;
        if regexp_count(f_.body,'\mauth\.(uid|jwt)\(\)',1,'i')<>item_.calls or position('cp7_request_context.' in f_.body)>0
            or exists(select from unnest(array['anon','authenticated','service_role']) a
              where has_schema_privilege(a,f_.schema_name,'USAGE') and has_function_privilege(a,f_.oid,'EXECUTE')) then
            raise exception 'Invoice operator route changed for %',item_.signature;
        end if;
        changed_:=regexp_replace(f_.body,'\mauth\.(uid|jwt)\(\)','cp7_request_context.\1()','gi');
        if not f_.can_create then
            execute format('set local role %I',item_.schema_owner);
            execute format('grant create on schema %I to %I',f_.schema_name,item_.owner_role);
        end if;
        execute format('set local role %I',item_.owner_role);
        execute replace(f_.ddl,f_.body,changed_);
        if not f_.can_create then
            execute format('set local role %I',item_.schema_owner);
            execute format('revoke create on schema %I from %I',f_.schema_name,item_.owner_role);
        end if;
        execute 'reset role';
        if not exists(select from pg_proc p where p.oid=f_.oid and p.prosrc=changed_ and to_jsonb(p)-'prosrc'=f_.metadata) then
            raise exception 'Invoice operator routine metadata changed';
        end if;
    end loop;
    revoke cp7_invoice_read,cp7_invoice_write,cp7_transaction_source_read from postgres granted by postgres restrict;
    if memberships_ is distinct from (select jsonb_agg(to_jsonb(m) order by m.roleid,m.grantor) from pg_auth_members m
        where m.member='postgres'::regrole and (m.roleid::regrole::text)::name=any(roles_))
       or owners_ is distinct from (select jsonb_object_agg(nspname,jsonb_build_array(nspowner,nspacl::text)) from pg_namespace
        where nspname=any(array['cp7_invoice','cp7_supplier_payment_correction','cp7_supplier_payment_create','cp7_transaction_source'])) then
        raise exception 'Supplier operator release changed an existing schema or left installer rights open';
    end if;
end $supplier_identity$;

do $transfer_pins$ begin
 if exists(select from (values ('cp7_invoice.payment_detail(uuid,jsonb)','cp7_invoice_read','f93c3d1afd4e543de91df7b1dca34edd904253cb827d6fa745a5b829546a903c'),('cp7_invoice.reverse_payment_locked(jsonb)','postgres','35759c56e9905ab2057fcd14efa8770c055eb8d775832bb92d0591a6d672643e'),('cp7_receipt_fix.blockers(uuid)','postgres','90292abaf37b0df3ce4adeb87bedd8c42e1f9c21eea04b48a0ccac2a406c8256'),('cp7_supplier_payment_correction.apply(jsonb,uuid)','postgres','9390b2951c38f247e03711205a4d5115ba3b7930018d9a2c4965cafbc1d24c99'),('cp7_transaction_source.resolve(jsonb)','cp7_transaction_source_read','9d0e4d3790a4f7b81baae2e36d0dbe2c7738f038591aaf437030b219e043ad6f'),('erp.post_supplier_payment(uuid)','postgres','52d44754692fe7c96b2094748d11b82c93207bc341c4347743e4bd1502a71359'),('erp.reverse_journal(uuid,text)','postgres','0385dd4941690d4c0600513ad2d225cb18ed37b6179e7b6541fe1cb5e8dee482'),('erp.reverse_supplier_payment(uuid,text)','postgres','d99aa18a8398d9ef1125185b2eef165d5dc6ad3608c956aa8d058e66d26363a1'),('erp.run_v267_financial_truth_checks()','postgres','42d1965bcf625c1333cfc07bf34a7aaf7ddc7f467101dc62456182c8c3c7e226')) e(sig,owner_name,sha)
   left join pg_proc p on p.oid=to_regprocedure(e.sig) where p.oid is null or
    pg_get_userbyid(p.proowner)<>e.owner_name or encode(sha256(convert_to(pg_get_functiondef(p.oid),'UTF8')),'hex')<>e.sha)
 then raise exception 'Supplier transfer payment predecessors changed';end if;
 end $transfer_pins$;

grant "cp7_invoice_read","cp7_procure_write","cp7_transaction_source_read" to postgres with inherit false, set true granted by postgres;
-- OW06 / D17-14(5): one real supplier transfer, explicit receipt allocations.
-- Native payment rows retain the authoritative per-receipt AP subledger. Only
-- the declared current-transaction capability delegates their journals to one
-- aggregate Native journal. No clearing account, browser ERP DML or GUC bypass.
create schema cp7_supplier_transfer authorization postgres;
revoke all on schema cp7_supplier_transfer from public,anon,authenticated,service_role,cp7_capture;

create table cp7_supplier_transfer.requests_v1(
 actor uuid not null,request_id uuid not null,payload jsonb not null,response jsonb,
 primary key(actor,request_id)
);
create table cp7_supplier_transfer.transfers_v1(
 id uuid primary key,supplier_id uuid not null,number text not null unique,
 payment_date timestamptz not null,amount numeric(20,2)not null check(amount>0),
 cash_account_id uuid not null,note text not null check(length(btrim(note))between 5 and 500),
 status text not null check(status in('DRAFT','POSTED','REVERSED')),
 journal_id uuid,actor uuid not null,request_id uuid not null,
 recorded_at timestamptz not null default clock_timestamp(),unique(actor,request_id)
);
-- ERP identifiers deliberately have no cross-schema FK: no extra ERP RI
-- triggers are installed. The complete final-state proof checks every link.
create table cp7_supplier_transfer.allocations_v1(
 transfer_id uuid not null references cp7_supplier_transfer.transfers_v1,
 purchase_id uuid not null,payment_id uuid not null unique,
 amount numeric(20,2)not null check(amount>0),primary key(transfer_id,purchase_id)
);
create table cp7_supplier_transfer.corrections_v1(
 original_id uuid primary key references cp7_supplier_transfer.transfers_v1,
 replacement_id uuid not null unique references cp7_supplier_transfer.transfers_v1,
 actor uuid not null,request_id uuid not null,reason text not null,
 time_neutral_id uuid,effective_inverse_id uuid,
 recorded_at timestamptz not null default clock_timestamp(),
 check(original_id<>replacement_id),
 check((time_neutral_id is null)=(effective_inverse_id is null))
);
create table cp7_supplier_transfer.context_v1(
 backend_pid integer not null,transaction_id bigint not null,actor uuid not null,
 request_id uuid not null,payload jsonb not null,transfer_id uuid,
 phase text not null check(phase in('LOCKED','POST','REVERSE','COMPLETE')),
 primary key(backend_pid,transaction_id)
);
alter table cp7_supplier_transfer.requests_v1 enable row level security;
alter table cp7_supplier_transfer.transfers_v1 enable row level security;
alter table cp7_supplier_transfer.allocations_v1 enable row level security;
alter table cp7_supplier_transfer.corrections_v1 enable row level security;
alter table cp7_supplier_transfer.context_v1 enable row level security;
create policy deny_requests on cp7_supplier_transfer.requests_v1 for all using(false)with check(false);
create policy deny_transfers on cp7_supplier_transfer.transfers_v1 for all using(false)with check(false);
create policy deny_allocations on cp7_supplier_transfer.allocations_v1 for all using(false)with check(false);
create policy deny_corrections on cp7_supplier_transfer.corrections_v1 for all using(false)with check(false);
create policy deny_context on cp7_supplier_transfer.context_v1 for all using(false)with check(false);
revoke all on all tables in schema cp7_supplier_transfer from public,anon,authenticated,service_role,cp7_capture;

create function cp7_supplier_transfer.access_now_v1(p_write boolean)returns jsonb
language plpgsql volatile security definer set search_path=''as $$
declare a jsonb;
begin
 a:=cp7_invoice.payment_access();
 if p_write and a->'reverse_payment'is distinct from'true'::jsonb then
  raise exception using errcode='42501',message='CP7_SUPPLIER_TRANSFER_DENIED';end if;
 return a;
end $$;

create function cp7_supplier_transfer.context_allows_v1(p_transfer uuid,p_phase text)returns boolean
language plpgsql volatile security definer set search_path=''as $$
begin
 return exists(select 1 from cp7_supplier_transfer.context_v1 c
  where c.backend_pid=pg_backend_pid()and c.transaction_id=txid_current()
  and c.actor=auth.uid()and c.transfer_id=p_transfer and c.phase=p_phase
  and exists(select 1 from cp7_supplier_transfer.requests_v1 r
    where r.actor=c.actor and r.request_id=c.request_id and r.payload=c.payload and r.response is null));
end $$;

create function cp7_supplier_transfer.deny_individual_v1(p_payment uuid)returns void
language plpgsql volatile security definer set search_path=''as $$
begin
 if exists(select 1 from cp7_supplier_transfer.allocations_v1 a where a.payment_id=p_payment)then
  raise exception 'CP7_SUPPLIER_TRANSFER_USE_PARENT: pembayaran ini alokasi satu transfer; buka Transfer supplier untuk membatalkan atau mengoreksi seluruh transfer.';
 end if;
end $$;

-- Called only after all original Native posting validations have passed.
create function cp7_supplier_transfer.delegate_post_v1(p_payment uuid,p_cash_coa uuid)returns boolean
language plpgsql volatile security definer set search_path=''as $$
declare a cp7_supplier_transfer.allocations_v1;t cp7_supplier_transfer.transfers_v1;p erp.supplier_payments;
begin
 select *into a from cp7_supplier_transfer.allocations_v1 where payment_id=p_payment;
 if not found then return false;end if;
 perform cp7_supplier_transfer.access_now_v1(true);
 select *into strict t from cp7_supplier_transfer.transfers_v1 where id=a.transfer_id;
 select *into strict p from erp.supplier_payments where id=p_payment;
 if not cp7_supplier_transfer.context_allows_v1(t.id,'POST')or t.status<>'DRAFT'
  or p.status<>'DRAFT'or p.purchase_id<>a.purchase_id or p.amount<>a.amount
  or p.payment_date<>t.payment_date or p.cash_account_id<>t.cash_account_id
  or p_cash_coa is distinct from(select coa_account_id from erp.cash_accounts where id=t.cash_account_id)
  or exists(select 1 from erp.initial_import_prepayment_payments where payment_id=p.id)then
  raise exception using errcode='42501',message='CP7_SUPPLIER_TRANSFER_PRIVATE_POST_REQUIRED';end if;
 return true;
end $$;

-- Native still owns child status, receipt status and its audit row. This helper
-- only reverses the one shared journal once, within the owning parent command.
create function cp7_supplier_transfer.delegate_reverse_v1(p_payment uuid,p_reason text)returns boolean
language plpgsql volatile security definer set search_path=''as $$
declare a cp7_supplier_transfer.allocations_v1;t cp7_supplier_transfer.transfers_v1;j erp.journal_entries;
begin
 select *into a from cp7_supplier_transfer.allocations_v1 where payment_id=p_payment;
 if not found then return false;end if;
 perform cp7_supplier_transfer.access_now_v1(true);
 select *into strict t from cp7_supplier_transfer.transfers_v1 where id=a.transfer_id;
 if not cp7_supplier_transfer.context_allows_v1(t.id,'REVERSE')or t.status<>'POSTED'
  or not exists(select 1 from cp7_supplier_transfer.context_v1 c where c.backend_pid=pg_backend_pid()
   and c.transaction_id=txid_current()and btrim(c.payload->>'reason')=p_reason)then
  raise exception 'CP7_SUPPLIER_TRANSFER_USE_PARENT: balik seluruh Transfer supplier melalui dokumen asal.';end if;
 select *into strict j from erp.journal_entries where id=t.journal_id;
 if j.source_type<>'CP7_SUPPLIER_TRANSFER'or j.source_id<>t.id then raise exception 'CP7_SUPPLIER_TRANSFER_JOURNAL_CHANGED';end if;
 if j.status='POSTED'then perform erp.reverse_journal(j.id,p_reason);
 elsif j.status<>'REVERSED'or(select count(*)from erp.journal_entries where reversal_of_id=j.id and status='POSTED')<>1 then
  raise exception 'CP7_SUPPLIER_TRANSFER_INVERSE_INCOMPLETE';end if;
 return true;
end $$;

create function cp7_supplier_transfer.protect_v1()returns trigger
language plpgsql volatile security definer set search_path=''as $$
declare ident uuid;
begin
 if tg_op in('DELETE','TRUNCATE')then raise exception 'CP7_SUPPLIER_TRANSFER_HISTORY_IMMUTABLE';end if;
 if tg_table_name='transfers_v1'then ident:=new.id;
 elsif tg_table_name='corrections_v1'then ident:=new.replacement_id;
 else ident:=new.transfer_id;end if;
 if tg_table_name='transfers_v1'then
  if tg_op='INSERT'then
   if new.status<>'DRAFT'or new.journal_id is not null or not cp7_supplier_transfer.context_allows_v1(ident,'POST')then
    raise exception 'CP7_SUPPLIER_TRANSFER_PRIVATE_DRAFT_REQUIRED';end if;
  elsif(to_jsonb(new)-array['status','journal_id'])is distinct from(to_jsonb(old)-array['status','journal_id'])
   or not((old.status='DRAFT'and new.status='POSTED'and old.journal_id is null and new.journal_id is not null
     and cp7_supplier_transfer.context_allows_v1(ident,'POST'))
    or(old.status='POSTED'and new.status='REVERSED'and new.journal_id=old.journal_id
     and cp7_supplier_transfer.context_allows_v1(ident,'REVERSE')))then
   raise exception 'CP7_SUPPLIER_TRANSFER_HISTORY_IMMUTABLE';end if;
 elsif tg_op<>'INSERT'or not cp7_supplier_transfer.context_allows_v1(ident,'POST')then
  raise exception 'CP7_SUPPLIER_TRANSFER_HISTORY_IMMUTABLE';
 end if;
 return new;
end $$;

create trigger transfer_private_write before insert or update or delete on cp7_supplier_transfer.transfers_v1 for each row execute function cp7_supplier_transfer.protect_v1();
create trigger transfer_no_truncate before truncate on cp7_supplier_transfer.transfers_v1 for each statement execute function cp7_supplier_transfer.protect_v1();
create trigger allocation_private_write before insert or update or delete on cp7_supplier_transfer.allocations_v1 for each row execute function cp7_supplier_transfer.protect_v1();
create trigger allocation_no_truncate before truncate on cp7_supplier_transfer.allocations_v1 for each statement execute function cp7_supplier_transfer.protect_v1();
create trigger correction_private_write before insert or update or delete on cp7_supplier_transfer.corrections_v1 for each row execute function cp7_supplier_transfer.protect_v1();
create trigger correction_no_truncate before truncate on cp7_supplier_transfer.corrections_v1 for each statement execute function cp7_supplier_transfer.protect_v1();

create function cp7_supplier_transfer.review_v1(p_supplier uuid,p_transfer uuid)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare s erp.suppliers;t cp7_supplier_transfer.transfers_v1;ap jsonb;state jsonb;
begin
 perform cp7_supplier_transfer.access_now_v1(false);
 select *into s from erp.suppliers where id=p_supplier;
 if s.id is null then raise exception 'CP7_SUPPLIER_TRANSFER_SUPPLIER_NOT_FOUND';end if;
 if p_transfer is not null then
  select *into t from cp7_supplier_transfer.transfers_v1 where id=p_transfer and supplier_id=p_supplier;
  if not found then raise exception 'CP7_SUPPLIER_TRANSFER_NOT_FOUND';end if;
 end if;
 ap:=public.erp_get_supplier_credit_v1(jsonb_build_object('supplier_id',p_supplier,'page',1))->'purchases';
 state:=jsonb_build_object('supplier',to_jsonb(s),'ap',ap,'transfer',to_jsonb(t),
  'headers',(select coalesce(jsonb_agg(to_jsonb(h)order by h.id),'[]')from erp.material_purchase_headers h where h.supplier_id=p_supplier),
  'payments',(select coalesce(jsonb_agg(to_jsonb(p)order by p.id),'[]')from erp.supplier_payments p join erp.material_purchase_headers h on h.id=p.purchase_id where h.supplier_id=p_supplier),
  'allocations',(select coalesce(jsonb_agg(to_jsonb(a)order by a.purchase_id),'[]')from cp7_supplier_transfer.allocations_v1 a where a.transfer_id=p_transfer),
  'journal',(select to_jsonb(j)from erp.journal_entries j where j.id=t.journal_id),
  'inverse',(select coalesce(jsonb_agg(to_jsonb(j)order by j.id),'[]')from erp.journal_entries j where j.reversal_of_id=t.journal_id),
  'lines',(select coalesce(jsonb_agg(to_jsonb(l)order by l.id),'[]')from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id where j.id=t.journal_id or j.reversal_of_id=t.journal_id));
 return jsonb_build_object('supplier',jsonb_build_object('id',s.id,'name',s.supplier_name),
  'Native_AP',ap,'review_token',md5(state::text));
end $$;

create function cp7_supplier_transfer.detail_v1(p_transfer uuid)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare t cp7_supplier_transfer.transfers_v1;j erp.journal_entries;inv erp.journal_entries;rows jsonb;
begin
 perform cp7_supplier_transfer.access_now_v1(false);
 select *into strict t from cp7_supplier_transfer.transfers_v1 where id=p_transfer;
 perform cp7_supplier_transfer.assert_transfer_v1(t.id);
 select *into strict j from erp.journal_entries where id=t.journal_id;
 select *into inv from erp.journal_entries where reversal_of_id=j.id;
 select jsonb_agg(jsonb_build_object('purchase_id',a.purchase_id,'purchase_number',h.purchase_number,
  'payment_id',a.payment_id,'amount',a.amount::text)order by h.physical_at,h.id)into rows
  from cp7_supplier_transfer.allocations_v1 a join erp.material_purchase_headers h on h.id=a.purchase_id where a.transfer_id=t.id;
 return jsonb_build_object('id',t.id,'number',t.number,'supplier_id',t.supplier_id,'status',t.status,
  'payment_date',t.payment_date,'amount',t.amount::text,'cash_account_id',t.cash_account_id,
  'cash_name',(select cash_account_name from erp.cash_accounts where id=t.cash_account_id),'note',t.note,
  'journal',jsonb_build_object('id',j.id,'number',j.journal_number,'status',j.status,'economic_date',j.economic_date,
   'accounting_date',j.transaction_date,'posting_at',j.posting_at,'period_shifted',j.period_shifted),
  'inverse',case when inv.id is null then null else jsonb_build_object('id',inv.id,'number',inv.journal_number,'status',inv.status,
   'economic_date',inv.economic_date,'accounting_date',inv.transaction_date,'posting_at',inv.posting_at,'period_shifted',inv.period_shifted)end,'allocations',rows,
  'previous_id',(select original_id from cp7_supplier_transfer.corrections_v1 where replacement_id=t.id),
  'replacement_id',(select replacement_id from cp7_supplier_transfer.corrections_v1 where original_id=t.id));
end $$;

create function cp7_supplier_transfer.validate_v1(p jsonb)returns void
language plpgsql immutable security definer set search_path=''as $$
declare a jsonb;keys text[];
begin
 if jsonb_typeof(p)is distinct from'object'or p->>'action'not in('CREATE','CORRECT','REVERSE')then raise exception 'CP7_SUPPLIER_TRANSFER_FIELDS';end if;
 keys:=case when p->>'action'='REVERSE'then array['action','supplier_id','transfer_id','review_token','reason']
  when p->>'action'='CORRECT'then array['action','supplier_id','transfer_id','review_token','reason','amount','cash_account_id','payment_date','allocations']
  else array['action','supplier_id','review_token','reason','amount','cash_account_id','payment_date','allocations']end;
 if not(p?&keys)or(select count(*)from jsonb_object_keys(p))<>cardinality(keys)
  or exists(select 1 from jsonb_each(p)where key<>'allocations'and jsonb_typeof(value)<>'string')
  or coalesce(p->>'supplier_id','')!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  or coalesce(p->>'review_token','')!~'^[a-f0-9]{32}$'or length(btrim(p->>'reason'))not between 5 and 500
  or(p->>'action'<>'CREATE'and coalesce(p->>'transfer_id','')!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')then raise exception 'CP7_SUPPLIER_TRANSFER_FIELDS';end if;
 if p->>'action'='REVERSE'then return;end if;
 if coalesce(p->>'amount','')!~'^(0|[1-9][0-9]{0,17})\.[0-9]{2}$'or(p->>'amount')::numeric<=0
  or coalesce(p->>'cash_account_id','')!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  or coalesce(p->>'payment_date','')!~'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.[0-9]{1,6})?(Z|[+-]\d{2}:\d{2})$'
  or jsonb_typeof(p->'allocations')is distinct from'array'then raise exception 'CP7_SUPPLIER_TRANSFER_FIELDS';end if;
 perform(p->>'payment_date')::timestamptz;
 if jsonb_array_length(p->'allocations')<1 then raise exception 'CP7_SUPPLIER_TRANSFER_ALLOCATIONS_REQUIRED';end if;
 for a in select value from jsonb_array_elements(p->'allocations')loop
  if jsonb_typeof(a)is distinct from'object'or not(a?&array['purchase_id','amount'])
   or(select count(*)from jsonb_object_keys(a))<>2 or exists(select 1 from jsonb_each(a)where jsonb_typeof(value)<>'string')
   or coalesce(a->>'purchase_id','')!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
   or coalesce(a->>'amount','')!~'^(0|[1-9][0-9]{0,17})\.[0-9]{2}$'or(a->>'amount')::numeric<=0 then raise exception 'CP7_SUPPLIER_TRANSFER_FIELDS';end if;
 end loop;
 if(select count(distinct value->>'purchase_id')from jsonb_array_elements(p->'allocations'))<>jsonb_array_length(p->'allocations')then raise exception 'CP7_SUPPLIER_TRANSFER_DUPLICATE_RECEIPT';end if;
 if(select sum((value->>'amount')::numeric)from jsonb_array_elements(p->'allocations'))<>(p->>'amount')::numeric then raise exception 'CP7_SUPPLIER_TRANSFER_ALLOCATION_TOTAL';end if;
end $$;

-- End-state detector and guard. It is also wired into the existing Native
-- financial detector, so old/corrupt facts are checked without a write.
create function cp7_supplier_transfer.valid_transfer_v1(p_transfer uuid)returns boolean
language sql stable security definer set search_path=''as $$
 select exists(select 1 from cp7_supplier_transfer.transfers_v1 t
  join erp.journal_entries j on j.id=t.journal_id join erp.cash_accounts c on c.id=t.cash_account_id
  where t.id=p_transfer and t.status in('POSTED','REVERSED')and j.source_type='CP7_SUPPLIER_TRANSFER'and j.source_id=t.id
   and j.reversal_of_id is null and j.status=t.status and j.economic_date=erp._cp3_business_date(t.payment_date)
   and(select count(*)from erp.journal_entries jj where jj.source_type='CP7_SUPPLIER_TRANSFER'and jj.source_id=t.id)=1
   and(select count(*)from cp7_supplier_transfer.allocations_v1 a where a.transfer_id=t.id)>0
   and(select sum(a.amount)from cp7_supplier_transfer.allocations_v1 a where a.transfer_id=t.id)=t.amount
   and not exists(select 1 from cp7_supplier_transfer.allocations_v1 a
    left join erp.supplier_payments p on p.id=a.payment_id left join erp.material_purchase_headers h on h.id=a.purchase_id
    where a.transfer_id=t.id and(p.id is null or h.id is null or p.purchase_id<>a.purchase_id or h.supplier_id<>t.supplier_id
     or p.status<>t.status or p.amount<>a.amount or p.cash_account_id<>t.cash_account_id or p.payment_date<>t.payment_date
     or exists(select 1 from erp.journal_entries jj where jj.source_type='SUPPLIER_PAYMENT'and jj.source_id=p.id)))
   and(select count(*)from erp.journal_lines l where l.journal_entry_id=j.id)=2
   and exists(select 1 from erp.journal_lines l where l.journal_entry_id=j.id and l.account_id=erp.account_id('AP_SUPPLIER')and l.debit=t.amount and l.credit=0)
   and exists(select 1 from erp.journal_lines l where l.journal_entry_id=j.id and l.account_id=c.coa_account_id and l.debit=0 and l.credit=t.amount)
   and not exists(select 1 from erp.journal_lines l where l.journal_entry_id=j.id
    and(l.customer_id is not null or l.vendor_id is not null or l.contractor_id is not null or l.po_id is not null or l.product_id is not null))
   and(select count(*)from erp.journal_entries v where v.reversal_of_id=j.id)=case when t.status='REVERSED'then 1 else 0 end
   and not exists(select 1 from erp.journal_entries v where v.reversal_of_id=j.id and(v.status<>'POSTED'or v.source_type<>'JOURNAL_REVERSAL'or v.source_id<>j.id
    or(select count(*)from erp.journal_lines l where l.journal_entry_id=v.id)<>2
    or exists(select 1 from erp.journal_lines l where l.journal_entry_id=v.id and not exists(
     select 1 from erp.journal_lines o where o.journal_entry_id=j.id and o.account_id=l.account_id and o.debit=l.credit and o.credit=l.debit
      and(o.customer_id,o.vendor_id,o.contractor_id,o.po_id,o.product_id)is not distinct from(l.customer_id,l.vendor_id,l.contractor_id,l.po_id,l.product_id)))))
 )$$;

create function cp7_supplier_transfer.assert_transfer_v1(p_transfer uuid)returns void
language plpgsql stable security definer set search_path=''as $$
begin
 if cp7_supplier_transfer.valid_transfer_v1(p_transfer)is distinct from true then raise exception 'CP7_SUPPLIER_TRANSFER_FINAL_STATE_INVALID';end if;
end $$;

create function cp7_supplier_transfer.final_guard_v1()returns trigger
language plpgsql volatile security definer set search_path=''as $$
begin
 if tg_table_name='context_v1'then
  if exists(select 1 from cp7_supplier_transfer.context_v1 c where c.backend_pid=new.backend_pid and c.transaction_id=new.transaction_id)then raise exception 'CP7_SUPPLIER_TRANSFER_CONTEXT_OPEN';end if;
 elsif tg_table_name='transfers_v1'then perform cp7_supplier_transfer.assert_transfer_v1(new.id);
 elsif tg_table_name='allocations_v1'then perform cp7_supplier_transfer.assert_transfer_v1(new.transfer_id);
 else
  perform cp7_supplier_transfer.assert_transfer_v1(new.original_id);perform cp7_supplier_transfer.assert_transfer_v1(new.replacement_id);
  if cp7_supplier_transfer.valid_correction_v1(new.original_id)is distinct from true then raise exception 'CP7_SUPPLIER_TRANSFER_CORRECTION_INVALID';end if;
 end if;
 return null;
end $$;
create constraint trigger final_transfer after insert or update on cp7_supplier_transfer.transfers_v1 deferrable initially deferred for each row execute function cp7_supplier_transfer.final_guard_v1();
create constraint trigger final_allocation after insert on cp7_supplier_transfer.allocations_v1 deferrable initially deferred for each row execute function cp7_supplier_transfer.final_guard_v1();
create constraint trigger final_correction after insert on cp7_supplier_transfer.corrections_v1 deferrable initially deferred for each row execute function cp7_supplier_transfer.final_guard_v1();
create constraint trigger closed_context after insert on cp7_supplier_transfer.context_v1 deferrable initially deferred for each row execute function cp7_supplier_transfer.final_guard_v1();

create function cp7_supplier_transfer.apply_v1(p jsonb,p_request uuid)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;r jsonb;old cp7_supplier_transfer.transfers_v1;h erp.material_purchase_headers;
 alloc jsonb;ident uuid;child uuid;journal uuid;inverse erp.journal_entries;original erp.journal_entries;
 neutral uuid;effective uuid;lines jsonb;at timestamptz;cash uuid;item record;old_allocations jsonb;
begin
 a:=cp7_supplier_transfer.access_now_v1(true);perform cp7_supplier_transfer.validate_v1(p);
 if not exists(select 1 from cp7_supplier_transfer.context_v1 c where c.backend_pid=pg_backend_pid()and c.transaction_id=txid_current()
  and c.actor=auth.uid()and c.request_id=p_request and c.payload=p and c.phase='LOCKED')then raise exception using errcode='42501',message='CP7_SUPPLIER_TRANSFER_PRIVATE_COMMAND_REQUIRED';end if;
 if p->>'action'<>'CREATE'then
  select *into old from cp7_supplier_transfer.transfers_v1 where id=(p->>'transfer_id')::uuid for update nowait;
  if old.id is null or old.supplier_id<>(p->>'supplier_id')::uuid or old.status<>'POSTED'then raise exception 'CP7_SUPPLIER_TRANSFER_POSTED_REQUIRED';end if;
  perform cp7_supplier_transfer.assert_transfer_v1(old.id);
 end if;
 -- Legacy writers lock a payment before a receipt and can later need the
 -- global envelope. Do not wait on their rows while holding that envelope.
 perform 1 from erp.supplier_payments s where s.purchase_id in(
   select(value->>'purchase_id')::uuid from jsonb_array_elements(coalesce(p->'allocations','[]'))
   union select x.purchase_id from cp7_supplier_transfer.allocations_v1 x where x.transfer_id=old.id)
   order by s.id for update nowait;
 perform 1 from erp.material_purchase_headers s where s.id in(
   select(value->>'purchase_id')::uuid from jsonb_array_elements(coalesce(p->'allocations','[]'))
   union select x.purchase_id from cp7_supplier_transfer.allocations_v1 x where x.transfer_id=old.id)
   order by s.id for update nowait;
 if cp7_supplier_transfer.access_now_v1(true)is distinct from a then raise exception using errcode='42501',message='CP7_SUPPLIER_TRANSFER_ACCESS_CHANGED';end if;
 r:=cp7_supplier_transfer.review_v1((p->>'supplier_id')::uuid,old.id);
 if r->>'review_token'is distinct from p->>'review_token'then raise exception 'CP7_SUPPLIER_TRANSFER_STALE_REVIEW';end if;
 if p->>'action'='CORRECT'then
  select jsonb_agg(jsonb_build_object('purchase_id',x.purchase_id,'amount',x.amount::text)order by x.purchase_id)into old_allocations from cp7_supplier_transfer.allocations_v1 x where x.transfer_id=old.id;
  select jsonb_agg(value order by value->>'purchase_id')into alloc from jsonb_array_elements(p->'allocations');
  if old_allocations=alloc and old.amount=(p->>'amount')::numeric and old.payment_date=(p->>'payment_date')::timestamptz and old.cash_account_id=(p->>'cash_account_id')::uuid then raise exception 'CP7_SUPPLIER_TRANSFER_CORRECTION_UNCHANGED';end if;
 end if;
 perform cp7_guard.begin_compound('OW06 supplier transfer');
 if old.id is not null then
  update cp7_supplier_transfer.context_v1 set phase='REVERSE',transfer_id=old.id where backend_pid=pg_backend_pid()and transaction_id=txid_current();
  for item in select payment_id from cp7_supplier_transfer.allocations_v1 where transfer_id=old.id order by payment_id loop
   perform erp.reverse_supplier_payment(item.payment_id,btrim(p->>'reason'));
  end loop;
  update cp7_supplier_transfer.transfers_v1 set status='REVERSED'where id=old.id;
  if p->>'action'='CORRECT'then
   select *into strict original from erp.journal_entries where id=old.journal_id;
   select *into strict inverse from erp.journal_entries where reversal_of_id=original.id;
   -- Same economic-date restatement as the existing supplier correction.
   if original.economic_date<>inverse.economic_date then
    select jsonb_agg(jsonb_build_object('account_id',l.account_id,'debit',l.credit,'credit',l.debit,'description',l.description,
     'customer_id',l.customer_id,'vendor_id',l.vendor_id,'contractor_id',l.contractor_id,'po_id',l.po_id,'product_id',l.product_id)order by l.id)into lines from erp.journal_lines l where l.journal_entry_id=inverse.id;
    neutral:=erp.post_journal('CP7_SUPPLIER_TRANSFER_TIME_NEUTRAL',old.id,inverse.economic_date,'Koreksi transfer supplier: waktu pembalikan | '||btrim(p->>'reason'),lines);
    select jsonb_agg(jsonb_build_object('account_id',l.account_id,'debit',l.debit,'credit',l.credit,'description',l.description,
     'customer_id',l.customer_id,'vendor_id',l.vendor_id,'contractor_id',l.contractor_id,'po_id',l.po_id,'product_id',l.product_id)order by l.id)into lines from erp.journal_lines l where l.journal_entry_id=inverse.id;
    effective:=erp.post_journal('CP7_SUPPLIER_TRANSFER_EFFECTIVE',old.id,original.economic_date,'Koreksi transfer supplier: waktu ekonomi asal | '||btrim(p->>'reason'),lines);
   end if;
  end if;
 end if;
 if p->>'action'<>'REVERSE'then
  at:=(p->>'payment_date')::timestamptz;
  if at>statement_timestamp()then raise exception 'CP7_SUPPLIER_TRANSFER_DATE_FUTURE';end if;
  lock table erp.accounting_account_mappings in share mode nowait;
  perform 1 from erp.cash_accounts where id=(p->>'cash_account_id')::uuid for share nowait;
  perform 1 from erp.chart_accounts where id in(
   (select coa_account_id from erp.cash_accounts where id=(p->>'cash_account_id')::uuid),erp.account_id('AP_SUPPLIER'))order by id for share nowait;
  select c.coa_account_id into cash from erp.cash_accounts c join erp.chart_accounts ca on ca.id=c.coa_account_id
   where c.id=(p->>'cash_account_id')::uuid and c.is_active and ca.is_active and ca.is_postable;
  if cash is null then raise exception 'CP7_SUPPLIER_TRANSFER_CASH_ACCOUNT_INACTIVE';end if;
  ident:=gen_random_uuid();
  update cp7_supplier_transfer.context_v1 set phase='POST',transfer_id=ident where backend_pid=pg_backend_pid()and transaction_id=txid_current();
  insert into cp7_supplier_transfer.transfers_v1(id,supplier_id,number,payment_date,amount,cash_account_id,note,status,actor,request_id)
   values(ident,(p->>'supplier_id')::uuid,'TRS-'||replace(p_request::text,'-',''),at,(p->>'amount')::numeric,(p->>'cash_account_id')::uuid,btrim(p->>'reason'),'DRAFT',auth.uid(),p_request);
  for alloc in select value from jsonb_array_elements(p->'allocations')order by value->>'purchase_id'loop
   select *into h from erp.material_purchase_headers where id=(alloc->>'purchase_id')::uuid;
   if h.id is null or h.status<>'POSTED'or h.supplier_id<>(p->>'supplier_id')::uuid then raise exception 'CP7_SUPPLIER_TRANSFER_SAME_SUPPLIER_POSTED_RECEIPTS_REQUIRED';end if;
   if at<h.physical_at then raise exception 'CP7_SUPPLIER_TRANSFER_BEFORE_RECEIPT';end if;
   if(alloc->>'amount')::numeric>round(erp.material_purchase_final_ap_total(h.id),2)-coalesce((select sum(s.amount)from erp.supplier_payments s where s.purchase_id=h.id and s.status='POSTED'),0)then raise exception 'CP7_SUPPLIER_TRANSFER_EXCEEDS_REMAINING';end if;
   child:=gen_random_uuid();
   insert into erp.supplier_payments(id,purchase_id,payment_number,payment_date,amount,cash_account_id,notes,status,created_by)
    values(child,h.id,'TRS-A-'||replace(child::text,'-',''),at,(alloc->>'amount')::numeric,(p->>'cash_account_id')::uuid,btrim(p->>'reason'),'DRAFT',erp.current_app_user_id());
   insert into cp7_supplier_transfer.allocations_v1 values(ident,h.id,child,(alloc->>'amount')::numeric);
   perform erp.post_supplier_payment(child);
  end loop;
  journal:=erp.post_journal('CP7_SUPPLIER_TRANSFER',ident,erp._cp3_business_date(at),'Transfer supplier '||(select number from cp7_supplier_transfer.transfers_v1 where id=ident),
   jsonb_build_array(jsonb_build_object('mapping_key','AP_SUPPLIER','debit',(p->>'amount')::numeric,'credit',0),jsonb_build_object('account_id',cash,'debit',0,'credit',(p->>'amount')::numeric)));
  update cp7_supplier_transfer.transfers_v1 set status='POSTED',journal_id=journal where id=ident;
  if old.id is not null then insert into cp7_supplier_transfer.corrections_v1(original_id,replacement_id,actor,request_id,reason,time_neutral_id,effective_inverse_id)
   values(old.id,ident,auth.uid(),p_request,btrim(p->>'reason'),neutral,effective);end if;
  perform cp7_supplier_transfer.assert_transfer_v1(ident);
 else ident:=old.id;end if;
 if old.id is not null then perform cp7_supplier_transfer.assert_transfer_v1(old.id);end if;
 perform cp7_guard.end_compound();
 if cp7_supplier_transfer.access_now_v1(true)is distinct from a then raise exception using errcode='42501',message='CP7_SUPPLIER_TRANSFER_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.supplier-transfer-outcome.v1','kind','COMMITTED_OUTCOME','action',p->>'action',
  'request_id',p_request,'request_payload',p,'supplier_id',p->>'supplier_id','transfer_id',ident,
  'original_transfer_id',old.id,'status',case when p->>'action'='REVERSE'then'REVERSED'else'POSTED'end);
end $$;

create function cp7_supplier_transfer.command_v1(p jsonb,p_request uuid)returns jsonb
language plpgsql volatile security definer set search_path=''as $$
declare a jsonb;s cp7_supplier_transfer.requests_v1;r jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_supplier_transfer.access_now_v1(true);perform cp7_supplier_transfer.validate_v1(p);
 if p_request is null then raise exception 'CP7_SUPPLIER_TRANSFER_FIELDS';end if;
 perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 if cp7_supplier_transfer.access_now_v1(true)is distinct from a then raise exception using errcode='42501',message='CP7_SUPPLIER_TRANSFER_ACCESS_CHANGED';end if;
 insert into cp7_supplier_transfer.requests_v1 values(auth.uid(),p_request,p,null)on conflict do nothing;
 select *into strict s from cp7_supplier_transfer.requests_v1 where actor=auth.uid()and request_id=p_request for update;
 if cp7_supplier_transfer.access_now_v1(true)is distinct from a then raise exception using errcode='42501',message='CP7_SUPPLIER_TRANSFER_ACCESS_CHANGED';end if;
 if s.payload is distinct from p then raise exception 'CP7_SUPPLIER_TRANSFER_REQUEST_CHANGED';end if;
 if s.response is not null then return s.response;end if;
 insert into cp7_supplier_transfer.context_v1 values(pg_backend_pid(),txid_current(),auth.uid(),p_request,p,null,'LOCKED');
 r:=cp7_supplier_transfer.apply_v1(p,p_request);
 delete from cp7_supplier_transfer.context_v1 where backend_pid=pg_backend_pid()and transaction_id=txid_current();
 if cp7_supplier_transfer.access_now_v1(true)is distinct from a then raise exception using errcode='42501',message='CP7_SUPPLIER_TRANSFER_ACCESS_CHANGED';end if;
 update cp7_supplier_transfer.requests_v1 set response=r where actor=auth.uid()and request_id=p_request;
 return r;
end $$;

revoke all on all functions in schema cp7_supplier_transfer from public,anon,authenticated,service_role,cp7_capture;
create function public.erp_cp7_save_supplier_transfer_v1(p_payload jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_supplier_transfer.command_v1(p_payload,p_request)$$;
revoke all on function public.erp_cp7_save_supplier_transfer_v1(jsonb,uuid)from public,anon,authenticated,service_role,cp7_capture;
grant execute on function public.erp_cp7_save_supplier_transfer_v1(jsonb,uuid)to authenticated;
-- Read-only correction detector; used by the commit guard and the existing
-- Native financial checks. Exact economic and book facts stay in Native.
create function cp7_supplier_transfer.valid_correction_v1(p_original uuid)returns boolean
language sql stable security definer set search_path=''as $$
 select exists(select 1 from cp7_supplier_transfer.corrections_v1 c
  join cp7_supplier_transfer.transfers_v1 o on o.id=c.original_id
  join cp7_supplier_transfer.transfers_v1 r on r.id=c.replacement_id
  join erp.journal_entries j on j.id=o.journal_id
  join erp.journal_entries inv on inv.reversal_of_id=j.id
  where c.original_id=p_original and o.status='REVERSED'and o.supplier_id=r.supplier_id
   and r.recorded_at>=o.recorded_at
   and cp7_supplier_transfer.valid_transfer_v1(o.id)and cp7_supplier_transfer.valid_transfer_v1(r.id)
   and case when j.economic_date=inv.economic_date then c.time_neutral_id is null and c.effective_inverse_id is null
   else c.time_neutral_id is not null and c.effective_inverse_id is not null
    and c.time_neutral_id<>c.effective_inverse_id
    and exists(select 1 from erp.journal_entries n where n.id=c.time_neutral_id and n.source_type='CP7_SUPPLIER_TRANSFER_TIME_NEUTRAL'
     and n.source_id=o.id and n.economic_date=inv.economic_date and n.status='POSTED'and n.reversal_of_id is null)
    and exists(select 1 from erp.journal_entries e where e.id=c.effective_inverse_id and e.source_type='CP7_SUPPLIER_TRANSFER_EFFECTIVE'
     and e.source_id=o.id and e.economic_date=j.economic_date and e.status='POSTED'and e.reversal_of_id is null)
    and(select count(*)from erp.journal_lines l where l.journal_entry_id=c.time_neutral_id)=2
    and(select count(*)from erp.journal_lines l where l.journal_entry_id=c.effective_inverse_id)=2
    and not exists(select 1 from erp.journal_lines l where l.journal_entry_id=c.time_neutral_id and not exists(
     select 1 from erp.journal_lines b where b.journal_entry_id=inv.id and b.account_id=l.account_id and b.debit=l.credit and b.credit=l.debit
      and(b.customer_id,b.vendor_id,b.contractor_id,b.po_id,b.product_id)is not distinct from(l.customer_id,l.vendor_id,l.contractor_id,l.po_id,l.product_id)))
    and not exists(select 1 from erp.journal_lines l where l.journal_entry_id=c.effective_inverse_id and not exists(
     select 1 from erp.journal_lines b where b.journal_entry_id=inv.id and b.account_id=l.account_id and b.debit=l.debit and b.credit=l.credit
      and(b.customer_id,b.vendor_id,b.contractor_id,b.po_id,b.product_id)is not distinct from(l.customer_id,l.vendor_id,l.contractor_id,l.po_id,l.product_id)))
   end
 )$$;
revoke all on function cp7_supplier_transfer.valid_correction_v1(uuid)from public,anon,authenticated,service_role,cp7_capture;
create function cp7_supplier_transfer.child_detail_v1(p_payment uuid,p_ap jsonb)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare a cp7_supplier_transfer.allocations_v1;t cp7_supplier_transfer.transfers_v1;p erp.supplier_payments;
 h erp.material_purchase_headers;c erp.cash_accounts;j erp.journal_entries;inv erp.journal_entries;token text;
begin
 perform cp7_supplier_transfer.access_now_v1(false);
 select *into a from cp7_supplier_transfer.allocations_v1 where payment_id=p_payment;
 if not found then return null;end if;
 select *into strict t from cp7_supplier_transfer.transfers_v1 where id=a.transfer_id;
 perform cp7_supplier_transfer.assert_transfer_v1(t.id);
 select *into strict p from erp.supplier_payments where id=p_payment;
 select *into strict h from erp.material_purchase_headers where id=p.purchase_id;
 if(p_ap is not null and p_ap->>'id'is distinct from h.id::text)or(h.status='POSTED'and p_ap is null)then raise exception 'CP7_SUPPLIER_PAYMENT_AP_UNAVAILABLE';end if;
 select *into strict c from erp.cash_accounts where id=t.cash_account_id;
 select *into strict j from erp.journal_entries where id=t.journal_id;
 select *into inv from erp.journal_entries where reversal_of_id=j.id;
 token:=md5(jsonb_build_array(to_jsonb(p),p_ap,cp7_supplier_transfer.review_v1(t.supplier_id,t.id)->>'review_token')::text);
 return jsonb_build_object('id',p.id,'number',p.payment_number,'status',p.status,'payment_date',p.payment_date,
  'amount',p.amount::text,'cash_account_id',p.cash_account_id,'cash_code',c.cash_account_code,'cash_name',c.cash_account_name,
  'journal',jsonb_build_object('id',j.id,'number',j.journal_number,'status',j.status,'economic_date',j.economic_date,
   'accounting_date',j.transaction_date,'posting_at',j.posting_at,'period_shifted',j.period_shifted),
  'inverse',case when inv.id is null then null else jsonb_build_object('id',inv.id,'number',inv.journal_number,'status',inv.status,
   'economic_date',inv.economic_date,'accounting_date',inv.transaction_date,'posting_at',inv.posting_at,'period_shifted',inv.period_shifted)end,
  'review_token',token,'transfer',jsonb_build_object('id',t.id,'number',t.number,'amount',t.amount::text,'status',t.status,
   'allocations_count',(select count(*)::text from cp7_supplier_transfer.allocations_v1 x where x.transfer_id=t.id)));
end $$;

-- The existing GL drill routes to one real receipt allocation, whose screen
-- opens the entire parent transfer. No new guessed UUID or virtual document.
create function cp7_supplier_transfer.source_payment_v1(p_transfer uuid)returns uuid
language plpgsql stable security definer set search_path=''as $$
declare answer uuid;
begin
 perform cp7_invoice.payment_access();
 perform cp7_supplier_transfer.assert_transfer_v1(p_transfer);
 select a.payment_id into answer from cp7_supplier_transfer.allocations_v1 a where a.transfer_id=p_transfer order by a.purchase_id limit 1;
 if answer is null then raise exception 'CP7_TRANSACTION_SOURCE_UNAVAILABLE';end if;
 return answer;
end $$;

create function cp7_supplier_transfer.workspace_v1(p jsonb)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare auth_before jsonb;r jsonb;t cp7_supplier_transfer.transfers_v1;ident uuid;supplier uuid;
 q text;bq text;off integer;boff integer;toff integer;n bigint;bn bigint;tn bigint;rows jsonb;brows jsonb;trows jsonb;ap jsonb;
begin
 auth_before:=cp7_supplier_transfer.access_now_v1(false);
 if jsonb_typeof(p)is distinct from'object'or not(p?'supplier_id')
  or exists(select 1 from jsonb_object_keys(p)x where x not in('supplier_id','transfer_id','purchase_q','purchase_offset','bank_q','bank_offset','transfer_offset'))
  or jsonb_typeof(p->'supplier_id')is distinct from'string'
  or coalesce(p->>'supplier_id','')!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  or(p?'transfer_id'and p->'transfer_id'<>'null'::jsonb and(jsonb_typeof(p->'transfer_id')<>'string'or coalesce(p->>'transfer_id','')!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'))
  or exists(select 1 from jsonb_each(p)where key in('purchase_q','bank_q')and(jsonb_typeof(value)<>'string'or length(value#>>'{}')>120))
  or exists(select 1 from jsonb_each(p)where key in('purchase_offset','bank_offset','transfer_offset')and(jsonb_typeof(value)<>'number'or(value#>>'{}')!~'^(0|[1-9][0-9]{0,5}|1000000)$'))then raise exception 'CP7_SUPPLIER_TRANSFER_QUERY';end if;
 supplier:=(p->>'supplier_id')::uuid;ident:=(p->>'transfer_id')::uuid;
 q:=btrim(coalesce(p->>'purchase_q',''));bq:=btrim(coalesce(p->>'bank_q',''));
 off:=coalesce((p->>'purchase_offset')::integer,0);boff:=coalesce((p->>'bank_offset')::integer,0);toff:=coalesce((p->>'transfer_offset')::integer,0);
 r:=cp7_supplier_transfer.review_v1(supplier,ident);ap:=r->'Native_AP';
 if ident is not null then select *into strict t from cp7_supplier_transfer.transfers_v1 where id=ident;end if;
 with candidates as materialized(
  select h.id,h.purchase_number,h.physical_at,(x.value->>'remaining')::numeric(20,2)remaining,
   case when t.status='POSTED'then coalesce((select a.amount from cp7_supplier_transfer.allocations_v1 a where a.transfer_id=t.id and a.purchase_id=h.id),0)else 0 end::numeric(20,2)released
  from jsonb_array_elements(ap)x join erp.material_purchase_headers h on h.id=(x.value->>'id')::uuid
  where q=''or strpos(lower(h.purchase_number),lower(q))>0
 ), eligible as materialized(select *from candidates where remaining+released>0)
 select(select count(*)from eligible),coalesce((select jsonb_agg(jsonb_build_object('id',x.id,'number',x.purchase_number,
  'physical_at',x.physical_at,'remaining',x.remaining::text,'release_on_correction',x.released::text,
  'payable_after_release',(x.remaining+x.released)::numeric(20,2)::text)order by x.physical_at,x.id)
  from(select *from eligible order by physical_at,id limit 25 offset off)x),'[]')into n,rows;
 with eligible as materialized(select c.*from erp.cash_accounts c join erp.chart_accounts ca on ca.id=c.coa_account_id
  where c.is_active and ca.is_active and ca.is_postable and(bq=''or strpos(lower(c.cash_account_code||' '||c.cash_account_name),lower(bq))>0))
 select(select count(*)from eligible),coalesce((select jsonb_agg(jsonb_build_object('id',x.id,'code',x.cash_account_code,'name',x.cash_account_name)order by x.cash_account_code,x.id)
  from(select *from eligible order by cash_account_code,id limit 25 offset boff)x),'[]')into bn,brows;
 select count(*)into tn from cp7_supplier_transfer.transfers_v1 where supplier_id=supplier;
 select coalesce(jsonb_agg(jsonb_build_object('id',x.id,'number',x.number,'status',x.status,'amount',x.amount::text,'payment_date',x.payment_date)order by x.recorded_at desc,x.id),'[]')into trows
  from(select *from cp7_supplier_transfer.transfers_v1 where supplier_id=supplier order by recorded_at desc,id limit 25 offset toff)x;
 if cp7_supplier_transfer.access_now_v1(false)is distinct from auth_before then raise exception using errcode='42501',message='CP7_SUPPLIER_TRANSFER_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.supplier-transfer-workspace.v1','captured_at',statement_timestamp(),
  'supplier',r->'supplier','can_write',auth_before->'reverse_payment','review_token',r->'review_token',
  'query',jsonb_build_object('supplier_id',supplier,'transfer_id',ident,'purchase_q',q,'purchase_offset',off,'bank_q',bq,'bank_offset',boff,'transfer_offset',toff),
  'receipts',jsonb_build_object('rows',rows,'total',n::text,'offset',off,'limit',25,'next_offset',case when off+jsonb_array_length(rows)<n then off+jsonb_array_length(rows)else null end),
  'cash_accounts',jsonb_build_object('rows',brows,'total',bn::text,'offset',boff,'limit',25,'next_offset',case when boff+jsonb_array_length(brows)<bn then boff+jsonb_array_length(brows)else null end),
  'transfers',jsonb_build_object('rows',trows,'total',tn::text,'offset',toff,'limit',25,'next_offset',case when toff+jsonb_array_length(trows)<tn then toff+jsonb_array_length(trows)else null end),
  'selected',case when ident is null then null else cp7_supplier_transfer.detail_v1(ident)end);
end $$;

revoke all on all functions in schema cp7_supplier_transfer from public,anon,authenticated,service_role,cp7_capture;
-- Existing invoker/definer owners get only their declared narrow helpers.
grant usage on schema cp7_supplier_transfer to cp7_invoice_read,cp7_transaction_source_read;
grant execute on function cp7_supplier_transfer.child_detail_v1(uuid,jsonb)to cp7_invoice_read;
grant execute on function cp7_supplier_transfer.source_payment_v1(uuid)to cp7_transaction_source_read;
create function public.erp_cp7_get_supplier_transfer_v1(p_query jsonb)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_supplier_transfer.workspace_v1(p_query)$$;
revoke all on function public.erp_cp7_get_supplier_transfer_v1(jsonb)from public,anon,authenticated,service_role,cp7_capture;
grant execute on function public.erp_cp7_get_supplier_transfer_v1(jsonb)to authenticated;
CREATE OR REPLACE FUNCTION erp.post_supplier_payment(p_payment_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare p erp.supplier_payments%rowtype;h erp.material_purchase_headers%rowtype;v_cash uuid;v_paid numeric(20,2);v_total numeric(20,2);
begin
  perform erp.require_internal();select * into p from erp.supplier_payments where id=p_payment_id for update;
  if p.id is null or p.status<>'DRAFT' then raise exception 'Supplier payment must be DRAFT'; end if;
  select * into h from erp.material_purchase_headers where id=p.purchase_id for update;
  if h.id is null or h.status<>'POSTED' then raise exception 'Material purchase must be POSTED before payment'; end if;
  select least(erp.material_purchase_payable_total(h.id),
         erp.material_purchase_payable_total(h.id)-erp.bf_supplier_credit_delta_v1(h.id)
         +erp.bf_supplier_credit_delta_v1(h.id,erp._cp3_business_date(p.payment_date)))::numeric(20,2) into v_total;
  select coalesce(sum(amount),0)::numeric(20,2) into v_paid from erp.supplier_payments where purchase_id=h.id and status='POSTED';
  if v_paid+p.amount>v_total then raise exception 'Supplier payment exceeds remaining payable. Net payable %, already paid %, requested %',v_total,v_paid,p.amount; end if;
  v_cash:=erp.initial_prepayment_funding_v1(p.id,'SUPPLIER',h.supplier_id,p.amount,erp._cp3_business_date(p.payment_date),greatest(erp._cp3_business_date(h.physical_at),(select max(i.invoice_date) from erp.material_supplier_invoices i join erp.material_supplier_invoice_lines l on l.invoice_id=i.id join erp.material_purchase_items pi on pi.id=l.purchase_item_id where pi.purchase_id=h.id and i.status='POSTED')));
  if v_cash is null then
  select coa_account_id into v_cash from erp.cash_accounts where id=p.cash_account_id and is_active=true;
  end if;
  if v_cash is null then raise exception 'Active cash/bank account is required'; end if;
  if not cp7_supplier_transfer.delegate_post_v1(p.id,v_cash)then
  perform erp.post_journal('SUPPLIER_PAYMENT',p.id,erp._cp3_business_date(p.payment_date),'Material supplier payment',jsonb_build_array(
    jsonb_build_object('mapping_key','AP_SUPPLIER','debit',p.amount,'credit',0),jsonb_build_object('account_id',v_cash,'debit',0,'credit',p.amount)));
  end if;
  update erp.supplier_payments set status='POSTED' where id=p.id;v_paid:=v_paid+p.amount;
  update erp.material_purchase_headers set payment_status=case when v_paid=round(erp.material_purchase_payable_total(h.id),2) then 'PAID' else 'PARTIAL' end where id=h.id;
end;$function$;
CREATE OR REPLACE FUNCTION erp.reverse_supplier_payment(p_payment_id uuid, p_reason text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  p erp.supplier_payments%rowtype;
  h erp.material_purchase_headers%rowtype;
  v_journal uuid;
  v_paid numeric(20,2);
  v_total numeric(20,2);
begin
  perform erp.require_owner_admin();
  if nullif(trim(p_reason),'') is null then raise exception 'Alasan reversal pembayaran supplier wajib diisi'; end if;
  select * into p from erp.supplier_payments where id=p_payment_id for update;
  if p.id is null then raise exception 'Pembayaran supplier tidak ditemukan'; end if;
  if p.status='REVERSED' then return; end if;
  if p.status<>'POSTED' then raise exception 'Hanya pembayaran supplier yang sudah POSTED yang dapat direverse'; end if;
  select * into h from erp.material_purchase_headers where id=p.purchase_id for update;
  perform 1 from erp.initial_import_prepayments a join erp.initial_import_prepayment_payments l on l.advance_id=a.id where l.payment_id=p.id for update of a;
  if h.id is null then raise exception 'Pembelian sumber pembayaran tidak ditemukan'; end if;

  if not cp7_supplier_transfer.delegate_reverse_v1(p.id,p_reason)then
  select id into v_journal from erp.journal_entries
  where source_type='SUPPLIER_PAYMENT' and source_id=p.id and status='POSTED'
  order by posting_at desc,id desc limit 1;
  if v_journal is null then raise exception 'Jurnal pembayaran supplier tidak ditemukan; reversal dibatalkan agar kas/hutang tidak rusak'; end if;

  if erp.initial_prepayment_account_v1(p.id) is not null then perform erp._cp3_r4_reverse_journal_internal(v_journal,p_reason);else perform erp.reverse_journal(v_journal,p_reason);end if;
  end if;
  update erp.supplier_payments set status='REVERSED' where id=p.id;

  select erp.material_purchase_payable_total(h.id)::numeric(20,2) into v_total;
  select coalesce(sum(amount),0)::numeric(20,2) into v_paid from erp.supplier_payments where purchase_id=h.id and status='POSTED';
  update erp.material_purchase_headers set payment_status=case when v_paid=round(v_total,2) then 'PAID' when v_paid>0 then 'PARTIAL' else 'UNPAID' end where id=h.id;

  insert into erp.audit_logs(entity_type,entity_id,action,changed_by,change_reason)
  values ('supplier_payments',p.id,'REVERSE',erp.current_app_user_id(),p_reason);
end;
$function$;
CREATE OR REPLACE FUNCTION erp.reverse_journal(p_journal_entry_id uuid, p_reason text)
 RETURNS uuid
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare v_source_type text;
begin
  perform cp7_attendance_choice.assert_journal_unowned_v1(p_journal_entry_id);
  perform erp.require_internal();
  if nullif(btrim(p_reason),'') is null then raise exception 'Journal reversal reason is required'; end if;
  select source_type into v_source_type
  from erp.journal_entries where id=p_journal_entry_id for update;
  if v_source_type is null then raise exception 'Journal entry not found'; end if;
  if v_source_type='CP7_SUPPLIER_TRANSFER'and not cp7_supplier_transfer.context_allows_v1(
    (select source_id from erp.journal_entries where id=p_journal_entry_id),'REVERSE')then
    raise exception 'CP7_SUPPLIER_TRANSFER_USE_PARENT: balik Transfer supplier melalui dokumen asal.';end if;
  if v_source_type in('CP7_SUPPLIER_TRANSFER_TIME_NEUTRAL','CP7_SUPPLIER_TRANSFER_EFFECTIVE')then
    raise exception 'CP7_SUPPLIER_TRANSFER_HISTORY_IMMUTABLE';end if;
  if v_source_type in('CP7_CUSTOMER_CREDIT_RECOGNITION','CP7_CUSTOMER_CREDIT_APPLY','CP7_CUSTOMER_CREDIT_REFUND','CP7_CUSTOMER_CREDIT_EVENT_REVERSE')or cp7_credit.is_protected_journal(p_journal_entry_id)then
    raise exception 'CP7_CREDIT_JOURNAL_USE_OWNING_SOURCE_WORKFLOW';
  end if;
  if v_source_type='POCKET_HPP_PERIOD' then raise exception 'Batalkan alokasi kain kantong melalui periode asal';end if;
  if v_source_type='MATERIAL_ADJUSTMENT' and exists(select 1 from erp.pocket_fabric_usage u join erp.journal_entries j on j.source_id=u.adjustment_id where j.id=p_journal_entry_id)
    and not exists(select 1 from erp.pocket_fabric_execution_context c join erp.journal_entries j on j.source_id=c.adjustment_id
      where c.backend_pid=pg_backend_pid() and c.transaction_id=txid_current()
      and c.actor_key=erp._idempotency_actor_key() and j.id=p_journal_entry_id) then
    raise exception 'Batalkan pengurangan kain kantong melalui dokumen asal';end if;
  if v_source_type in('OPENING_PREPAYMENT','PREPAYMENT_EVENT') or (v_source_type in('SUPPLIER_PAYMENT','SALES_PAYMENT','VENDOR_PAYMENT','OPENING_SUBLEDGER_SETTLEMENT')
    and exists(select 1 from erp.initial_import_prepayment_payments l join erp.journal_entries j on j.source_id=l.payment_id where j.id=p_journal_entry_id)) then
    raise exception 'Pembatalan uang muka harus melalui sumber pembayaran atau perubahan tertaut';end if;
  if v_source_type='MATERIAL_ADJUSTMENT_REVALUATION' then
    raise exception 'T_PROTECTED_REVALUATION_JOURNAL_USE_SOURCE_WORKFLOW';
  end if;
  if v_source_type in ('ATTENDANCE_HPP_POOL','PAYROLL_ATTENDANCE_ACCRUAL') then
    raise exception 'Protected journal source type % cannot be reversed through generic reverse_journal. Use the owning attendance HPP pool or payroll cancellation/reversal flow.',v_source_type;
  end if;
  return erp._cp3_r4_reverse_journal_internal(p_journal_entry_id,p_reason);
end
$function$;
set local role "cp7_invoice_read";
grant create on schema "cp7_invoice" to "cp7_invoice_read";
set local role "postgres";
set local role "cp7_invoice_read";
CREATE OR REPLACE FUNCTION cp7_invoice.payment_detail(p_payment uuid, p_ap jsonb)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare p erp.supplier_payments;h erp.material_purchase_headers;c erp.cash_accounts;
 j erp.journal_entries;inverse erp.journal_entries;n bigint;state jsonb;r jsonb;
 previous_zone text:=current_setting('TimeZone');
begin
 perform cp7_invoice.payment_access();
 r:=cp7_supplier_transfer.child_detail_v1(p_payment,p_ap);
 if r is not null then return r;end if;
 -- Hash the full original rows in one stable timezone, restoring the caller's
 -- zone before any Native inverse. No timestamp or dependency is dropped.
 perform set_config('TimeZone','UTC',true);
 select * into p from erp.supplier_payments where id=p_payment;
 if not found then raise exception 'CP7_SUPPLIER_PAYMENT_NOT_FOUND';end if;
 select * into h from erp.material_purchase_headers where id=p.purchase_id;
 if h.id is null or(p_ap is not null and p_ap->>'id' is distinct from h.id::text)
  or(h.status='POSTED' and p_ap is null) then raise exception 'CP7_SUPPLIER_PAYMENT_AP_UNAVAILABLE';end if;
 select * into c from erp.cash_accounts where id=p.cash_account_id;
 select count(*) into n from erp.journal_entries where source_type='SUPPLIER_PAYMENT' and source_id=p.id and reversal_of_id is null;
 if n>1 then raise exception 'CP7_SUPPLIER_PAYMENT_COMPLETE_JOURNAL_REQUIRED';end if;
 select * into j from erp.journal_entries where source_type='SUPPLIER_PAYMENT' and source_id=p.id and reversal_of_id is null;
 if j.id is not null then
  select count(*) into n from erp.journal_entries where reversal_of_id=j.id;
  if n>1 then raise exception 'CP7_SUPPLIER_PAYMENT_COMPLETE_JOURNAL_REQUIRED';end if;
  select * into inverse from erp.journal_entries where reversal_of_id=j.id;
 end if;
 if p.amount<=0 or p.amount<>round(p.amount,2) or p.status not in('DRAFT','POSTED','REVERSED')
  or(p.status='DRAFT' and j.id is not null)
  or(p.status='POSTED' and(j.id is null or j.status<>'POSTED' or inverse.id is not null))
  or(p.status='REVERSED' and(j.id is null or j.status<>'REVERSED' or inverse.id is null or inverse.status<>'POSTED')) then
  raise exception 'CP7_SUPPLIER_PAYMENT_COMPLETE_JOURNAL_REQUIRED';end if;
 state:=jsonb_build_object('payment',to_jsonb(p),'purchase',to_jsonb(h),'cash',to_jsonb(c),'Native_AP',p_ap,
  'journal',to_jsonb(j),'inverse',to_jsonb(inverse),'lines',
  (select coalesce(jsonb_agg(to_jsonb(l)order by l.id),'[]')from erp.journal_lines l where l.journal_entry_id in(j.id,inverse.id)));
 r:=jsonb_build_object('id',p.id,'number',p.payment_number,'status',p.status,'payment_date',p.payment_date,
  'amount',p.amount::numeric(20,2)::text,'cash_account_id',p.cash_account_id,'cash_code',c.cash_account_code,'cash_name',c.cash_account_name,
  'journal',case when j.id is null then null else jsonb_build_object('id',j.id,'number',j.journal_number,'status',j.status,
   'economic_date',j.economic_date,'accounting_date',j.transaction_date,'posting_at',j.posting_at,'period_shifted',j.period_shifted)end,
  'inverse',case when inverse.id is null then null else jsonb_build_object('id',inverse.id,'number',inverse.journal_number,'status',inverse.status,
   'economic_date',inverse.economic_date,'accounting_date',inverse.transaction_date,'posting_at',inverse.posting_at,'period_shifted',inverse.period_shifted)end,
  'review_token',md5(state::text));
 perform set_config('TimeZone',previous_zone,true);return r;
exception when others then perform set_config('TimeZone',previous_zone,true);raise;
end $function$;
set local role "postgres";
set local role "cp7_invoice_read";
revoke create on schema "cp7_invoice" from "cp7_invoice_read";
set local role "postgres";
set local role "cp7_invoice_read";
grant create on schema "cp7_invoice" to "postgres";
set local role "postgres";
CREATE OR REPLACE FUNCTION cp7_invoice.reverse_payment_locked(p_payload jsonb)
 RETURNS uuid
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare a jsonb;p erp.supplier_payments;h erp.material_purchase_headers;d jsonb;journal uuid;inverse uuid;
begin
 a:=cp7_invoice.payment_access();
 perform cp7_supplier_transfer.deny_individual_v1((p_payload->>'payment_id')::uuid);
 if a->'reverse_payment' is distinct from 'true'::jsonb then raise exception using errcode='42501',message='CP7_SUPPLIER_PAYMENT_REVERSE_DENIED';end if;
 select * into p from erp.supplier_payments where id=(p_payload->>'payment_id')::uuid for update;
 if p.id is null or p.purchase_id is distinct from(p_payload->>'purchase_id')::uuid then raise exception 'CP7_SUPPLIER_PAYMENT_NOT_FOUND';end if;
 select * into h from erp.material_purchase_headers where id=p.purchase_id for update;
 perform 1 from erp.initial_import_prepayments x join erp.initial_import_prepayment_payments l on l.advance_id=x.id where l.payment_id=p.id for update of x;
 perform 1 from erp.journal_entries x where x.source_type='SUPPLIER_PAYMENT'and x.source_id=p.id order by x.id for update;
 perform 1 from erp.journal_lines l join erp.journal_entries x on x.id=l.journal_entry_id where x.source_type='SUPPLIER_PAYMENT'and x.source_id=p.id order by l.id for update of l;
 if cp7_invoice.payment_access()<>a then raise exception using errcode='42501',message='CP7_SUPPLIER_PAYMENT_ACCESS_CHANGED';end if;
 if p.status<>'POSTED' or h.status<>'POSTED' then raise exception 'CP7_SUPPLIER_PAYMENT_POSTED_REQUIRED';end if;
 d:=cp7_invoice.payment_detail(p.id,cp7_invoice.payment_ap(h.id));
 if d->>'review_token' is distinct from p_payload->>'review_token' then raise exception 'CP7_SUPPLIER_PAYMENT_STALE_REVIEW';end if;
 journal:=(d->'journal'->>'id')::uuid;
 perform erp.reverse_supplier_payment(p.id,p_payload->>'reason');
 if cp7_invoice.payment_access()<>a then raise exception using errcode='42501',message='CP7_SUPPLIER_PAYMENT_ACCESS_CHANGED';end if;
 select id into inverse from erp.journal_entries where reversal_of_id=journal and status='POSTED';
 if inverse is null or not exists(select 1 from erp.supplier_payments where id=p.id and status='REVERSED')then raise exception 'CP7_SUPPLIER_PAYMENT_INVERSE_INCOMPLETE';end if;
 return inverse;
end $function$;
set local role "cp7_invoice_read";
revoke create on schema "cp7_invoice" from "postgres";
set local role "postgres";
set local role "cp7_invoice_read";
grant create on schema "cp7_supplier_payment_correction" to "postgres";
set local role "postgres";
CREATE OR REPLACE FUNCTION cp7_supplier_payment_correction.apply(p jsonb, p_request uuid)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
 SET "TimeZone" TO 'UTC'
AS $function$
declare a jsonb;original erp.supplier_payments;h erp.material_purchase_headers;ap jsonb;d jsonb;
 o erp.journal_entries;inv erp.journal_entries;lines jsonb;neutral uuid;effective uuid;replacement uuid;link cp7_supplier_payment_correction.links;
begin
 a:=cp7_supplier_payment_correction.access_now();perform cp7_supplier_payment_correction.validate(p);
 perform cp7_supplier_transfer.deny_individual_v1((p->>'payment_id')::uuid);
 if not exists(select 1 from cp7_supplier_payment_correction.context where backend_pid=pg_backend_pid()and transaction_id=txid_current()
  and actor=auth.uid()and request_id=p_request and payload=p)then
  raise exception using errcode='42501',message='CP7_SUPPLIER_PAYMENT_CORRECTION_PRIVATE_CONTEXT_REQUIRED';end if;
 perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 perform 1 from erp.supplier_payments where purchase_id=(p->>'purchase_id')::uuid order by id for update;
 select *into h from erp.material_purchase_headers where id=(p->>'purchase_id')::uuid for update;
 select *into original from erp.supplier_payments where id=(p->>'payment_id')::uuid;
 if h.id is null or original.id is null or original.purchase_id<>h.id then raise exception 'CP7_SUPPLIER_PAYMENT_NOT_FOUND';end if;
 if cp7_supplier_payment_correction.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_SUPPLIER_PAYMENT_ACCESS_CHANGED';end if;
 if original.status<>'POSTED'or h.status<>'POSTED'or original.cash_account_id is null
  or exists(select 1 from erp.initial_import_prepayment_payments where payment_id=original.id)
  or exists(select 1 from cp7_supplier_payment_correction.links where original_id=original.id)then raise exception 'CP7_SUPPLIER_PAYMENT_CORRECTION_ORDINARY_ONLY';end if;
 ap:=cp7_invoice.payment_ap(h.id);d:=cp7_invoice.payment_detail(original.id,ap);
 if d->>'review_token'is distinct from p->>'review_token'then raise exception 'CP7_SUPPLIER_PAYMENT_STALE_REVIEW';end if;
 lock table erp.accounting_account_mappings in share mode;
 perform 1 from erp.cash_accounts where id in(original.cash_account_id,(p->'replacement'->>'cash_account_id')::uuid)order by id for share;
 perform 1 from erp.chart_accounts where id in(select coa_account_id from erp.cash_accounts where id in(original.cash_account_id,(p->'replacement'->>'cash_account_id')::uuid)
  union select account_id from erp.accounting_account_mappings where mapping_key='AP_SUPPLIER')order by id for share;
 if cp7_supplier_payment_correction.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_SUPPLIER_PAYMENT_ACCESS_CHANGED';end if;
 -- A cash/master lock may itself have waited after the first source review.
 -- Rebind the full Native source/AP/journal token to the now-locked rows.
 ap:=cp7_invoice.payment_ap(h.id);d:=cp7_invoice.payment_detail(original.id,ap);
 if d->>'review_token'is distinct from p->>'review_token'then raise exception 'CP7_SUPPLIER_PAYMENT_STALE_REVIEW';end if;
 -- The create path's dating rules: never in the future, and a changed time never
 -- before the goods arrived (money paid earlier is an advance, another document).
 if(p->'replacement'->>'payment_date')::timestamptz>statement_timestamp()then raise exception 'CP7_SUPPLIER_PAYMENT_DATE_FUTURE';end if;
 if(p->'replacement'->>'payment_date')::timestamptz<>original.payment_date and(p->'replacement'->>'payment_date')::timestamptz<h.physical_at then raise exception 'CP7_SUPPLIER_PAYMENT_BEFORE_RECEIPT';end if;
 if(p->'replacement'->>'amount')::numeric=original.amount and(p->'replacement'->>'payment_date')::timestamptz=original.payment_date
  and(p->'replacement'->>'cash_account_id')::uuid=original.cash_account_id then raise exception 'CP7_SUPPLIER_PAYMENT_CORRECTION_UNCHANGED';end if;
 perform erp.reverse_supplier_payment(original.id,btrim(p->>'change_reason'));
 select *into strict o from erp.journal_entries where source_type='SUPPLIER_PAYMENT'and source_id=original.id and reversal_of_id is null;
 select *into strict inv from erp.journal_entries where reversal_of_id=o.id and source_type='JOURNAL_REVERSAL'and source_id=o.id;
 if o.status<>'REVERSED'or inv.status<>'POSTED'then raise exception 'CP7_SUPPLIER_PAYMENT_CORRECTION_JOURNAL_SOURCE_CHANGED';end if;
 if o.economic_date<>inv.economic_date then
  select jsonb_agg(jsonb_build_object('account_id',l.account_id,'debit',l.credit,'credit',l.debit,'description',l.description,
   'customer_id',l.customer_id,'vendor_id',l.vendor_id,'contractor_id',l.contractor_id,'po_id',l.po_id,'product_id',l.product_id)order by l.id)into lines from erp.journal_lines l where l.journal_entry_id=inv.id;
  neutral:=erp.post_journal('SUPPLIER_PAYMENT_CORRECTION_TIME_NEUTRAL',original.id,inv.economic_date,'Koreksi pembayaran supplier: pindahkan waktu pembalikan | '||btrim(p->>'change_reason'),lines);
  select jsonb_agg(jsonb_build_object('account_id',l.account_id,'debit',l.debit,'credit',l.credit,'description',l.description,
   'customer_id',l.customer_id,'vendor_id',l.vendor_id,'contractor_id',l.contractor_id,'po_id',l.po_id,'product_id',l.product_id)order by l.id)into lines from erp.journal_lines l where l.journal_entry_id=inv.id;
  effective:=erp.post_journal('SUPPLIER_PAYMENT_CORRECTION_EFFECTIVE',original.id,o.economic_date,'Koreksi pembayaran supplier: waktu ekonomi asal | '||btrim(p->>'change_reason'),lines);
 end if;
 -- The new row is only a Native DRAFT; Native posting decides AP capacity,
 -- account eligibility, canonical business date and closed-period treatment.
 insert into erp.supplier_payments(purchase_id,payment_number,payment_date,amount,cash_account_id)
  values(h.id,'K-'||replace(p_request::text,'-',''),(p->'replacement'->>'payment_date')::timestamptz,
   (p->'replacement'->>'amount')::numeric,(p->'replacement'->>'cash_account_id')::uuid)returning id into replacement;
 perform erp.post_supplier_payment(replacement);
 if not exists(select 1 from erp.supplier_payments where id=replacement and purchase_id=h.id and status='POSTED')then raise exception 'CP7_SUPPLIER_PAYMENT_CORRECTION_POST_INCOMPLETE';end if;
 if cp7_supplier_payment_correction.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_SUPPLIER_PAYMENT_ACCESS_CHANGED';end if;
 insert into cp7_supplier_payment_correction.links(original_id,replacement_id,purchase_id,actor,request_id,reason,time_neutral_id,effective_inverse_id)
  values(original.id,replacement,h.id,auth.uid(),p_request,btrim(p->>'change_reason'),neutral,effective)returning *into link;
 return jsonb_build_object('contract_version','cp7.supplier-payment-correction.v1','kind','COMMITTED_OUTCOME','action','CORRECT',
  'request_id',p_request,'request_payload',p,'purchase_id',h.id,'original_payment_id',original.id,'payment_id',replacement,
  'original_status','REVERSED','status','POSTED','link',cp7_supplier_payment_correction.link_value(link));
end $function$;
set local role "cp7_invoice_read";
revoke create on schema "cp7_supplier_payment_correction" from "postgres";
set local role "postgres";
CREATE OR REPLACE FUNCTION erp.run_v267_financial_truth_checks()
 RETURNS TABLE(check_name text, severity text, issue_count bigint, details text)
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_catalog', 'information_schema', 'pg_temp'
AS $function$
  select 'V267_GRNI_MAPPING_INVALID','CRITICAL',count(*)::bigint,
         'GRNI_MATERIAL must map to an active CREDIT liability account'
  from erp.accounting_account_mappings m
  join erp.chart_accounts a on a.id=m.account_id
  where m.mapping_key='GRNI_MATERIAL'
    and not(a.account_type='LIABILITY' and a.normal_balance='CREDIT' and a.is_active and a.is_postable)

  union all
  select 'V267_MISSING_GRNI_MAPPING','CRITICAL',case when exists(
    select 1 from erp.accounting_account_mappings where mapping_key='GRNI_MATERIAL'
  ) then 0 else 1 end::bigint,'GRNI mapping is required'

  union all
  select 'V267_ESTIMATED_RECEIPT_MISSING_GRNI_RECLASS','CRITICAL',count(*)::bigint,
         'Posted estimated receipts require an AP-to-GRNI reclassification journal'
  from erp.material_purchase_headers h
  where h.status='POSTED' and erp.material_purchase_grni_total(h.id)>0.005
    and not exists(
      select 1 from erp.journal_entries j
      where (j.source_type='MATERIAL_PURCHASE_GRNI_RECLASS' or (
        j.source_type='OPENING_UNINVOICED_RECEIPT' and exists(select 1 from erp.initial_import_receipt_headers r where r.purchase_id=h.id))) and j.source_id=h.id
        and j.status in('POSTED','REVERSED')
    )

  union all
  select 'V267_POSTED_INVOICE_MISSING_JOURNAL','CRITICAL',count(*)::bigint,
         'Every non-zero posted supplier invoice requires an AP/GRNI journal'
  from erp.material_supplier_invoices h
  where h.status='POSTED'
    and exists(select 1 from erp.material_supplier_invoice_lines l where l.invoice_id=h.id and(l.net_amount<>0 or l.grni_clear_amount_snapshot<>0))
    and not exists(
      select 1 from erp.journal_entries j
      where j.source_type='MATERIAL_SUPPLIER_INVOICE' and j.source_id=h.id and j.status='POSTED'
    )

  union all
  select 'V267_INVOICE_MATCH_OVER_RECEIPT','CRITICAL',count(*)::bigint,
         'Posted supplier-invoice quantity exceeds receipt quantity net of GRNI-backed returns'
  from erp.material_purchase_items i
  where erp.material_purchase_posted_invoice_qty(i.id)>erp.material_purchase_invoice_capacity(i.id)

  union all
  select 'V267_PAYMENT_EXCEEDS_FINAL_AP','CRITICAL',count(*)::bigint,
         'Supplier payment must never consume GRNI or exceed final AP'
  from erp.material_purchase_headers h
  where coalesce((select sum(p.amount) from erp.supplier_payments p where p.purchase_id=h.id and p.status='POSTED'),0)
        >round(erp.material_purchase_final_ap_total(h.id),2)

  union all
  select 'V267_LEGACY_CORRECTION_ON_GRNI','CRITICAL',count(*)::bigint,
         'Legacy price corrections may only touch DIRECT_FINAL receipt items'
  from erp.material_purchase_cost_correction_items ci
  join erp.material_purchase_cost_corrections c on c.id=ci.correction_id
  join erp.material_purchase_items i on i.id=ci.purchase_item_id
  where c.status='POSTED' and i.invoice_match_state<>'DIRECT_FINAL'

  union all
  select 'V267_POSTED_RETURN_MISSING_LIABILITY_SNAPSHOT','CRITICAL',count(*)::bigint,
         'Posted supplier returns require AP/GRNI quantity and amount snapshots'
  from erp.material_supplier_return_items ri
  join erp.material_supplier_returns rh on rh.id=ri.return_id
  where rh.status='POSTED' and(
    ri.ap_relief_qty_snapshot is null or ri.grni_relief_qty_snapshot is null
    or ri.ap_relief_amount_snapshot is null or ri.grni_relief_amount_snapshot is null
  )

  union all
  select 'V267_GRNI_GL_SUBLEDGER_MISMATCH','CRITICAL',case when abs(
    coalesce((select sum(a.credit_total-a.debit_total)
      from erp.account_daily_balances a
      where a.account_id=(select erp.account_id('GRNI_MATERIAL'))),0)
    -coalesce((select sum(round(erp.material_purchase_grni_total(h.id),2))
      from erp.material_purchase_headers h where h.status='POSTED'),0)
  )<>0 then 1 else 0 end::bigint,
  'GRNI general ledger must equal estimated unmatched receipt liability'

  union all
  select 'V267_AP_GL_SUBLEDGER_MISMATCH','CRITICAL',case when abs(
    coalesce((select sum(a.credit_total-a.debit_total)
      from erp.account_daily_balances a
      where a.account_id=(select erp.account_id('AP_SUPPLIER'))),0)
    -coalesce((select sum(greatest(
      round(erp.material_purchase_final_ap_total(h.id),2)
      -coalesce((select sum(p.amount) from erp.supplier_payments p where p.purchase_id=h.id and p.status='POSTED'),0),0
    )) from erp.material_purchase_headers h where h.status='POSTED'),0)
    -coalesce((select sum(b.original_amount-b.settled_amount)
      from erp.opening_subledger_balances b
      join erp.opening_balance_items i on i.id=b.opening_item_id
      join erp.opening_balance_headers oh on oh.id=i.opening_id and oh.status='POSTED'
      where b.party_type='SUPPLIER' and b.direction='PAYABLE'),0)
  )<>0 then 1 else 0 end::bigint,
  'Supplier AP general ledger must equal final-invoice subledger net of payment/returns'

  union all
  select 'V267_BROWSER_ROLE_DIRECT_INVOICE_WRITE','CRITICAL',count(*)::bigint,
         'Supplier invoice aggregate must be writable only through v2 RPCs'
  from information_schema.role_table_grants g
  where g.table_schema='erp' and g.table_name in('material_supplier_invoices','material_supplier_invoice_lines')
    and g.grantee in('PUBLIC','anon','authenticated')
    and g.privilege_type in('INSERT','UPDATE','DELETE')
  union all
  select 'V2620M_SUPPLIER_PAYMENT_EXACT_STATUS','CRITICAL',count(*)::bigint,
    'Supplier payment status and capacity must equal the rounded final liability of each purchase'
  from erp.material_purchase_headers h
  cross join lateral(select round(erp.material_purchase_final_ap_total(h.id),2) payable,
    coalesce((select sum(p.amount) from erp.supplier_payments p
      where p.purchase_id=h.id and p.status='POSTED'),0) paid) x
  where h.status='POSTED' and(
    x.paid<0 or x.paid>x.payable
    or x.paid::text in('NaN','Infinity','-Infinity')
    or x.payable::text in('NaN','Infinity','-Infinity')
    or(h.payment_status='PAID' and x.paid<>x.payable)
    or(h.payment_status='PARTIAL' and not(x.paid>0 and x.paid<x.payable))
    or(h.payment_status='UNPAID' and x.paid<>0))

  union all
  select 'V2620M_OPENING_SUBLEDGER_STATE','CRITICAL',count(*)::bigint,
    'Every posted financial opening requires one source-matched balance, exact settlements, and exact status'
  from erp.opening_balance_items i
  join erp.opening_balance_headers h on h.id=i.opening_id and h.status='POSTED'
  left join erp.opening_subledger_balances b on b.opening_item_id=i.id
  cross join lateral(select coalesce((select c.corrected_amount
      from erp.opening_financial_corrections c where c.opening_item_id=i.id and c.status='POSTED'
      order by c.correction_seq desc limit 1),i.amount) original,
    coalesce((select sum(s.amount) from erp.opening_subledger_settlements s
      where s.balance_id=b.id and s.status='POSTED'),0)
    +coalesce((select sum(d.amount) from erp.payroll_deductions d join erp.payroll_settlements p on p.id=d.payroll_id
      where d.opening_cash_advance_balance_id=b.id and p.status='PAID'),0)
    +coalesce((select sum(r.amount) from erp.payroll_reimbursements r join erp.payroll_settlements p on p.id=r.payroll_id
      where r.opening_payable_balance_id=b.id and p.status='PAID'),0) paid) x
  where i.balance_type in('CUSTOMER_RECEIVABLE','SUPPLIER_PAYABLE','VENDOR_PAYABLE',
    'CONTRACTOR_RECEIVABLE','CONTRACTOR_PAYABLE') and(
    b.id is null or (select count(*) from erp.opening_subledger_balances bx where bx.opening_item_id=i.id)<>1
    or b.original_amount is distinct from x.original
    or b.settled_amount is distinct from x.paid
    or b.original_amount::text in('NaN','Infinity','-Infinity')
    or b.settled_amount::text in('NaN','Infinity','-Infinity')
    or b.original_amount<0 or b.settled_amount<0 or b.settled_amount>b.original_amount
    or b.status is distinct from case when x.paid=x.original then 'SETTLED'
      when x.paid>0 then 'PARTIAL' else 'OPEN' end
    or b.party_type is distinct from split_part(i.balance_type,'_',1)
    or b.direction is distinct from split_part(i.balance_type,'_',2)
    or b.customer_id is distinct from i.customer_id
    or b.supplier_id is distinct from i.supplier_id
    or b.vendor_id is distinct from i.vendor_id
    or b.contractor_id is distinct from i.contractor_id)

  union all
  select 'V2620M_PAYMENT_SOURCE_JOURNAL_MISMATCH','CRITICAL',count(*)::bigint,
    'Each supplier or opening settlement must match its own original and inverse money, accounts, party, and lifecycle'
  from(
    select p.id,p.status,p.amount,p.cash_account_id,'SUPPLIER_PAYMENT'::text source_type,
      (select erp.account_id('AP_SUPPLIER')) balance_account,false incoming,
      null::uuid customer_id,null::uuid vendor_id,null::uuid contractor_id
    from erp.supplier_payments p where not exists(select 1 from cp7_supplier_transfer.allocations_v1 a where a.payment_id=p.id)
    union all
    select t.id,t.status,t.amount,t.cash_account_id,'CP7_SUPPLIER_TRANSFER',
      (select erp.account_id('AP_SUPPLIER')),false,null::uuid,null::uuid,null::uuid
    from cp7_supplier_transfer.transfers_v1 t
    union all
    select s.id,s.status,s.amount,s.cash_account_id,'OPENING_SUBLEDGER_SETTLEMENT',
      erp.account_id(case when b.party_type='CUSTOMER' then 'AR_CUSTOMER'
        when b.party_type='SUPPLIER' then 'AP_SUPPLIER'
        when b.party_type='VENDOR' then 'AP_VENDOR'
        when b.direction='RECEIVABLE' then 'CONTRACTOR_RECEIVABLE' else 'CONTRACTOR_PAYABLE' end),
      b.direction='RECEIVABLE',b.customer_id,b.vendor_id,b.contractor_id
    from erp.opening_subledger_settlements s
    join erp.opening_subledger_balances b on b.id=s.balance_id
  ) x
  left join erp.cash_accounts ca on ca.id=x.cash_account_id
  where x.amount<=0 or x.amount::text in('NaN','Infinity','-Infinity') or (ca.id is null and erp.initial_prepayment_account_v1(x.id) is null and erp.bb_opening_credit_account_v1(x.id) is null)
    or (select count(*) from erp.journal_entries j
      where j.source_type=x.source_type and j.source_id=x.id and j.status in('POSTED','REVERSED'))
      <>case when x.status='DRAFT' then 0 else 1 end
    or exists(
      select 1 from erp.journal_entries j
      where j.source_type=x.source_type and j.source_id=x.id and j.status in('POSTED','REVERSED') and(
        j.status is distinct from x.status
        or (select count(*) from erp.journal_lines l where l.journal_entry_id=j.id)<>2
        or exists(select 1 from erp.journal_lines l where l.journal_entry_id=j.id and(
          l.customer_id is distinct from x.customer_id or l.vendor_id is distinct from x.vendor_id
          or l.contractor_id is distinct from x.contractor_id
          or not((l.account_id=coalesce(erp.initial_prepayment_account_v1(x.id),erp.bb_opening_credit_account_v1(x.id),ca.coa_account_id) and
                l.debit=case when x.incoming then x.amount else 0 end and
                l.credit=case when x.incoming then 0 else x.amount end)
            or (l.account_id=x.balance_account and
                l.debit=case when x.incoming then 0 else x.amount end and
                l.credit=case when x.incoming then x.amount else 0 end))))
        or (select count(*) from erp.journal_entries inv where inv.reversal_of_id=j.id)
          <>case when x.status='REVERSED' then 1 else 0 end
        or exists(select 1 from erp.journal_entries inv where inv.reversal_of_id=j.id and(
          inv.source_type<>'JOURNAL_REVERSAL' or inv.status<>'POSTED'
          or (select count(*) from erp.journal_lines l where l.journal_entry_id=inv.id)<>2
          or exists(select 1 from erp.journal_lines l where l.journal_entry_id=inv.id and(
            l.customer_id is distinct from x.customer_id or l.vendor_id is distinct from x.vendor_id
            or l.contractor_id is distinct from x.contractor_id
            or not((l.account_id=coalesce(erp.initial_prepayment_account_v1(x.id),erp.bb_opening_credit_account_v1(x.id),ca.coa_account_id) and
                  l.credit=case when x.incoming then x.amount else 0 end and
                  l.debit=case when x.incoming then 0 else x.amount end)
              or (l.account_id=x.balance_account and
                  l.credit=case when x.incoming then 0 else x.amount end and
                  l.debit=case when x.incoming then x.amount else 0 end))))))
      ))

  union all
  select 'V2620M_ORPHAN_PAYMENT_JOURNAL','CRITICAL',count(*)::bigint,
    'A supplier payment or opening settlement journal must retain its business source'
  from erp.journal_entries j
  where j.status in('POSTED','REVERSED') and(
    (j.source_type='SUPPLIER_PAYMENT' and not exists(select 1 from erp.supplier_payments p where p.id=j.source_id))
    or(j.source_type='CP7_SUPPLIER_TRANSFER'and not exists(select 1 from cp7_supplier_transfer.transfers_v1 t where t.id=j.source_id and t.journal_id=j.id))
    or(j.source_type in('CP7_SUPPLIER_TRANSFER_TIME_NEUTRAL','CP7_SUPPLIER_TRANSFER_EFFECTIVE')and not exists(
      select 1 from cp7_supplier_transfer.corrections_v1 c where c.original_id=j.source_id and j.id=case when j.source_type='CP7_SUPPLIER_TRANSFER_TIME_NEUTRAL'then c.time_neutral_id else c.effective_inverse_id end))
    or(j.source_type='OPENING_SUBLEDGER_SETTLEMENT' and not exists(
      select 1 from erp.opening_subledger_settlements s where s.id=j.source_id)))

  union all
  select 'V2620P_SUPPLIER_RETURN_MATCH_STATE','CRITICAL',count(*)::bigint,
    'Supplier invoice match and price states must equal posted invoice quantity against current return-adjusted capacity'
  from erp.material_purchase_items i
  cross join lateral(select erp.material_purchase_invoice_capacity(i.id) capacity,
    erp.material_purchase_posted_invoice_qty(i.id) matched) x
  where i.invoice_match_state<>'DIRECT_FINAL' and(
    i.invoice_match_state is distinct from case when x.matched<=0 then 'UNMATCHED'
      when x.matched<x.capacity then 'PARTIAL' else 'MATCHED' end
    or i.price_state is distinct from case when x.matched<=0 then 'ESTIMATED'
      when x.matched<x.capacity then 'PARTIAL' else 'FINAL' end)

  union all
  select 'V2620O_SUPPLIER_RETURN_ALLOCATION','CRITICAL',count(*)::bigint,
    'Posted supplier-return AP/GRNI snapshots must partition each line and AP relief must not exceed invoiced quantity'
  from erp.material_purchase_items i
  where exists(
    select 1
    from erp.material_supplier_return_items ri
    join erp.material_supplier_returns rh on rh.id=ri.return_id
    where ri.purchase_item_id=i.id and rh.status='POSTED' and(
      ri.ap_relief_qty_snapshot is null or ri.grni_relief_qty_snapshot is null
      or ri.ap_relief_amount_snapshot is null or ri.grni_relief_amount_snapshot is null
      or ri.ap_relief_qty_snapshot<0 or ri.grni_relief_qty_snapshot<0
      or ri.ap_relief_qty_snapshot::text in('NaN','Infinity','-Infinity')
      or ri.grni_relief_qty_snapshot::text in('NaN','Infinity','-Infinity')
      or ri.ap_relief_amount_snapshot::text in('NaN','Infinity','-Infinity')
      or ri.grni_relief_amount_snapshot::text in('NaN','Infinity','-Infinity')
      or abs(ri.ap_relief_qty_snapshot+ri.grni_relief_qty_snapshot-ri.qty)>0.000001
      or abs(ri.ap_relief_amount_snapshot
        -ri.ap_relief_qty_snapshot*ri.supplier_credit_unit_price)>0.000001
      or abs(ri.grni_relief_amount_snapshot
        -ri.grni_relief_qty_snapshot*i.unit_price)>0.000001
    )
  ) or coalesce((
    select sum(ri.ap_relief_qty_snapshot)
    from erp.material_supplier_return_items ri
    join erp.material_supplier_returns rh on rh.id=ri.return_id
    where ri.purchase_item_id=i.id and rh.status='POSTED'
  ),0)>case when i.invoice_match_state='DIRECT_FINAL' then i.qty
    else erp.material_purchase_posted_invoice_qty(i.id) end+0.000001
  or i.id in(
    with legacy_capacity as(
      select pi.id purchase_item_id,
        case when pi.invoice_match_state='DIRECT_FINAL' then pi.qty else
          coalesce((
            select sum(il.qty_invoiced)
            from erp.material_supplier_invoice_lines il
            join erp.material_supplier_invoices ih on ih.id=il.invoice_id
            where il.purchase_item_id=pi.id and ih.status='POSTED'
              and not exists(
                select 1 from erp.supplier_cent_posting_facts f
                where f.source_type='MATERIAL_SUPPLIER_INVOICE'
                  and f.source_id=ih.id and f.phase='POST'
              )
          ),0)
        end-coalesce((
          select sum(ri.ap_relief_qty_snapshot)
          from erp.material_supplier_return_items ri
          join erp.material_supplier_returns rh on rh.id=ri.return_id
          where ri.purchase_item_id=pi.id and rh.status='POSTED'
            and not exists(
              select 1 from erp.supplier_cent_posting_facts f
              where f.source_type='MATERIAL_SUPPLIER_RETURN'
                and f.source_id=rh.id and f.phase='POST'
            )
        ),0) opening_capacity
      from erp.material_purchase_items pi
    ), allocation_events as(
      select il.purchase_item_id,f.recorded_at,f.source_id,
        0 event_order,sum(il.qty_invoiced)::numeric delta,'INVOICE'::text event_kind
      from erp.supplier_cent_posting_facts f
      join erp.material_supplier_invoices ih
        on ih.id=f.source_id and ih.status='POSTED'
      join erp.material_supplier_invoice_lines il on il.invoice_id=ih.id
      join erp.material_purchase_items pi on pi.id=il.purchase_item_id
      where f.source_type='MATERIAL_SUPPLIER_INVOICE' and f.phase='POST'
        and pi.invoice_match_state<>'DIRECT_FINAL'
      group by il.purchase_item_id,f.recorded_at,f.source_id
      union all
      select ri.purchase_item_id,f.recorded_at,f.source_id,
        1 event_order,-sum(ri.ap_relief_qty_snapshot)::numeric,'RETURN'::text
      from erp.supplier_cent_posting_facts f
      join erp.material_supplier_returns rh
        on rh.id=f.source_id and rh.status='POSTED'
      join erp.material_supplier_return_items ri on ri.return_id=rh.id
      where f.source_type='MATERIAL_SUPPLIER_RETURN' and f.phase='POST'
      group by ri.purchase_item_id,f.recorded_at,f.source_id
    ), running_capacity as(
      select e.purchase_item_id,e.event_kind,l.opening_capacity+
        sum(e.delta) over(
          partition by e.purchase_item_id
          order by e.recorded_at,e.event_order,e.source_id
          rows between unbounded preceding and current row
        ) capacity_after
      from allocation_events e
      join legacy_capacity l using(purchase_item_id)
    )
    select purchase_item_id from running_capacity
    where event_kind='RETURN' and capacity_after < -0.000001
  )

  union all
  select 'V2620R_SUPPLIER_INVOICE_SOURCE_STATE','CRITICAL',count(*)::bigint,
    'Every posted supplier invoice must reference only posted material receipts'
  from erp.material_supplier_invoices ih
  where ih.status='POSTED' and exists(
    select 1 from erp.material_supplier_invoice_lines il
    join erp.material_purchase_items pi on pi.id=il.purchase_item_id
    join erp.material_purchase_headers ph on ph.id=pi.purchase_id
    where il.invoice_id=ih.id and ph.status<>'POSTED'
  )

  union all
  select 'V2620Y_OPENING_SETTLEMENT_BUSINESS_DATE','CRITICAL',count(*)::bigint,
    'Opening settlement cash and subledger dates must follow the Jakarta physical event'
  from erp.journal_entries j
    join erp.opening_subledger_settlements h on h.id=j.source_id
    where j.source_type='OPENING_SUBLEDGER_SETTLEMENT'
      and j.status in('POSTED','REVERSED') and h.status in('POSTED','REVERSED')
      and j.economic_date is distinct from erp._cp3_business_date(h.physical_at)

  union all
  select 'V2620Y_VENDOR_PAYMENT_BUSINESS_DATE','CRITICAL',count(*)::bigint,
    'Vendor payment cash and AP dates must follow the Jakarta payment event'
  from erp.journal_entries j
    join erp.vendor_payments h on h.id=j.source_id
    where j.source_type='VENDOR_PAYMENT'
      and j.status in('POSTED','REVERSED') and h.status in('POSTED','REVERSED')
      and j.economic_date is distinct from erp._cp3_business_date(h.payment_date)

  union all
  select 'V2620Y_SALES_PAYMENT_BUSINESS_DATE','CRITICAL',count(*)::bigint,
    'Original customer payment cash, AR and immutable fact dates must follow the Jakarta payment event'
  from erp.journal_entries j
    join erp.sales_payments h on h.id=j.source_id
    join erp.sales_payment_posting_facts f on f.payment_id=h.id
    where j.source_type='SALES_PAYMENT'
      and j.status in('POSTED','REVERSED') and h.status in('POSTED','REVERSED')
      and f.replaces_payment_id is null
      and (j.economic_date is distinct from erp._cp3_business_date(f.payment_date)
        or f.journal_economic_date is distinct from erp._cp3_business_date(f.payment_date))

  union all
  select 'V2620W_SCRAP_BUSINESS_DATE','CRITICAL',count(*)::bigint,
    'Paid scrap economic dates must match the canonical Jakarta physical business date'
  from erp.journal_entries j
  join erp.scrap_sales h on h.id=j.source_id
  where j.source_type='SCRAP_SALE' and j.status in('POSTED','REVERSED')
    and h.status in('POSTED','REVERSED')
    and j.economic_date is distinct from erp._cp3_business_date(h.physical_at)

  union all
  select 'V2620V_MISC_FINANCE_BUSINESS_DATE','CRITICAL',count(*)::bigint,
    'Misc finance economic dates must match the canonical Jakarta physical business date'
  from erp.journal_entries j
  join erp.misc_finance_transactions h on h.id=j.source_id
  where j.source_type='MISC_FINANCE' and j.status in('POSTED','REVERSED')
    and h.status in('POSTED','REVERSED')
    and j.economic_date is distinct from erp._cp3_business_date(h.physical_at)

  union all
  select 'V2620U_MATERIAL_ADJUSTMENT_BUSINESS_DATE','CRITICAL',count(*)::bigint,
    'Material adjustment journals must use the canonical Jakarta date of physical_at'
  from erp.journal_entries j
  join erp.material_adjustments h on h.id=j.source_id
  where j.source_type='MATERIAL_ADJUSTMENT' and j.status in('POSTED','REVERSED')
    and h.status in('POSTED','REVERSED')
    and j.economic_date is distinct from erp._cp3_business_date(h.physical_at)

  union all
  select 'V2620U_JOURNAL_REVERSAL_BUSINESS_DATE','CRITICAL',count(*)::bigint,
    'Generic journal reversals must use the canonical Jakarta date of posting_at'
  from erp.journal_entries j
  where j.source_type='JOURNAL_REVERSAL' and j.status='POSTED'
    and j.economic_date is distinct from erp._cp3_business_date(j.posting_at)

  union all
  select 'V2620U_MATERIAL_RECEIPT_BUSINESS_DATE','CRITICAL',count(*)::bigint,
    'Material receipt and GRNI journals must use the canonical Jakarta date of physical_at'
  from erp.journal_entries j
  join erp.material_purchase_headers h on h.id=j.source_id
  where j.source_type in('MATERIAL_PURCHASE','MATERIAL_PURCHASE_GRNI_RECLASS')
    and j.status in('POSTED','REVERSED') and h.status in('POSTED','REVERSED')
    and j.economic_date is distinct from erp._cp3_business_date(h.physical_at)

  union all
  select 'V2620T_JOURNAL_FUTURE_BUSINESS_DATE','CRITICAL',count(*)::bigint,
    'Journal economic dates may not exceed the canonical Jakarta day of the recorded posting instant'
  from erp.journal_entries j
  where j.status in('POSTED','REVERSED')
    and j.economic_date>erp._cp3_business_date(j.posting_at)

  union all
  select 'V2620T_MATERIAL_ADJUSTMENT_REVALUATION','CRITICAL',count(*)::bigint,
    'Material adjustment revaluation must conserve document cents at original and corrected valuation endpoints'
  from erp.material_adjustments h
  cross join lateral(select erp._cp6_material_adjustment_revaluation_state(h.id) s) x
  where h.status in('POSTED','REVERSED')
    and (x.s->'target' is distinct from x.s->'book' or (x.s->>'incomplete_cost')::bigint>0)

  union all
  select 'V2620T_MATERIAL_ADJUSTMENT_FACT_LEDGER','CRITICAL',count(*)::bigint,
    'Append-only material adjustment revaluation facts must match their protected original journal'
  from erp.material_adjustment_revaluation_facts f
  left join erp.journal_entries j on j.id=f.journal_entry_id
  where j.id is null or j.status<>'POSTED' or j.source_type<>'MATERIAL_ADJUSTMENT_REVALUATION'
    or j.source_id is distinct from f.id or j.economic_date is distinct from f.effective_date
    or erp._cp6_supplier_cent_ledger(array[f.journal_entry_id]) is distinct from f.ledger_delta

  union all
  select 'V2620S_SUPPLIER_PAYMENT_BUSINESS_DATE','CRITICAL',count(*)::bigint,
    'Supplier payment original journals must retain the canonical Jakarta business date in every lifecycle state'
  from erp.supplier_payments p
  join erp.journal_entries j on j.source_type='SUPPLIER_PAYMENT' and j.source_id=p.id
    and j.status in('POSTED','REVERSED')
  where p.status in('POSTED','REVERSED')
    and j.economic_date is distinct from erp._cp3_business_date(p.payment_date)

  union all
  select 'V2620N_SUPPLIER_CENT_FACT_LEDGER','CRITICAL',count(*)::bigint,
    'Supplier cent posting and linked inverse must retain their exact source and ledger vector'
  from erp.supplier_cent_posting_facts f
  where f.ledger_delta is distinct from erp._cp6_supplier_cent_ledger(array[f.journal_entry_id,f.adjustment_journal_entry_id])
    or(f.phase='POST' and f.adjustment_journal_entry_id is not null)
    or not exists(select 1 from(
      select 'MATERIAL_PURCHASE_COST_CORRECTION'::text source_type,id,status from erp.material_purchase_cost_corrections
      union all select 'MATERIAL_SUPPLIER_INVOICE',id,status from erp.material_supplier_invoices
      union all select 'MATERIAL_SUPPLIER_RETURN',id,status from erp.material_supplier_returns
    ) s where s.source_type=f.source_type and s.id=f.source_id
      and s.status=case when exists(select 1 from erp.supplier_cent_posting_facts r
        where r.source_type=f.source_type and r.source_id=f.source_id and r.phase='REVERSE') then 'REVERSED' else 'POSTED' end)
    or(f.journal_entry_id is not null and not exists(select 1 from erp.journal_entries j
      where j.id=f.journal_entry_id and(
        (f.phase='POST' and j.source_type=f.source_type and j.source_id=f.source_id)
        or(f.phase='REVERSE' and j.source_type='JOURNAL_REVERSAL' and exists(select 1
          from erp.journal_entries original where original.id=j.reversal_of_id
            and original.source_type=f.source_type and original.source_id=f.source_id)))))
    or(f.adjustment_journal_entry_id is not null and not exists(select 1 from erp.journal_entries j
      where j.id=f.adjustment_journal_entry_id and j.source_type='CENT_INVERSE:'||f.source_type
        and j.source_id=f.source_id))

  union all
  select 'AP_OPENING_RECEIPT_SOURCE_DRIFT','CRITICAL',count(*)::bigint,
    'Imported receipts require an exact posted opening layer and no additional purchase movement'
  from erp.initial_import_receipt_headers rh join erp.material_purchase_headers h on h.id=rh.purchase_id
  where h.status<>'POSTED' or h.supplier_id<>rh.supplier_id or erp._cp3_business_date(h.physical_at)<>rh.cutover_date
    or not exists(select 1 from erp.initial_import_receipt_lines l where l.purchase_id=h.id)
    or exists(select 1 from erp.material_purchase_items pi left join erp.initial_import_receipt_lines l on l.purchase_item_id=pi.id
      left join erp.opening_balance_items oi on oi.id=l.opening_item_id left join erp.opening_balance_headers oh on oh.id=oi.opening_id
      where pi.purchase_id=h.id and (l.purchase_id is distinct from h.id or (l.opening_item_id is not null and oh.status is distinct from 'POSTED')
        or (l.opening_item_id is not null and oi.balance_type is distinct from 'MATERIAL')
        or pi.qty is distinct from coalesce(oi.qty,0)+coalesce((select sum(material_qty) from erp.initial_import_cost_origins where purchase_item_id=pi.id),0)+coalesce((select sum(material_qty) from erp.be_pocket_receipt_origins_v1 where purchase_item_id=pi.id),0)
        or (l.opening_item_id is not null and (pi.material_id is distinct from oi.material_id or erp.bb_receipt_opening_unit_cost_v1(pi.id) is distinct from oi.unit_cost_snapshot
        or oi.location_id is distinct from h.location_id))
        or (l.opening_item_id is not null and (select count(*) from erp.material_stock_movements m where m.source_type='OPENING_BALANCE_ITEM'
          and m.source_id=oi.id and m.movement_type='OPENING' and m.qty_signed=oi.qty)<>1)
        or exists(select 1 from erp.material_stock_movements m where m.source_type='MATERIAL_PURCHASE_ITEM' and m.source_id=pi.id)))
  union all
  select 'AP_OPENING_RECEIPT_JOURNAL_DRIFT','CRITICAL',count(*)::bigint,
    'Imported GRNI opening has exact value, opening equity offset, and cutover date'
  from erp.initial_import_receipt_headers rh
  cross join lateral(select round(sum((qty-erp.bb_receipt_invoiced_qty_v1(id))*unit_price),2) value from erp.material_purchase_items where purchase_id=rh.purchase_id) v
  where (v.value>0 and not exists(select 1 from erp.journal_entries j where j.source_type='OPENING_UNINVOICED_RECEIPT'
    and j.source_id=rh.purchase_id and j.status='POSTED' and j.economic_date=rh.cutover_date
    and erp._cp6_supplier_cent_ledger(array[j.id])=jsonb_build_object((select erp.account_id('OPENING_EQUITY'))::text,v.value,(select erp.account_id('GRNI_MATERIAL'))::text,-v.value)))
    or exists(select 1 from erp.journal_entries j where j.source_id=rh.purchase_id and j.source_type in('MATERIAL_PURCHASE','MATERIAL_PURCHASE_GRNI_RECLASS'))

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
  where d.deduction_type='CASH_ADVANCE' and not cp7_kasbon.linked_ok(d.id) and (s.source_kind is distinct from 'CONTRACTOR_CASH_ADVANCE'
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
        (select erp.account_id('CONTRACTOR_PAYABLE'))::text,d.amount,(select erp.account_id('CONTRACTOR_RECEIVABLE'))::text,-d.amount)
      and not exists(select 1 from erp.journal_lines l where l.journal_entry_id=j.id and l.contractor_id is distinct from p.contractor_id)))
    or((p.status<>'PAID' or d.amount=0) and exists(select 1 from erp.journal_entries j where j.source_type='PAYROLL_CASH_ADVANCE_DEDUCTION'
      and j.source_id=p.id and j.status='POSTED'))

 union all select * from erp.initial_prepayment_checks_v1()
UNION ALL SELECT * FROM erp.pocket_period_checks_v1()
 UNION ALL SELECT * FROM erp.pocket_fabric_checks_v1()
  union all
  select 'OW06_SUPPLIER_TRANSFER_FACTS','CRITICAL',count(*)::bigint,
    'A supplier transfer must retain every exact Native allocation and its one cash journal'
  from cp7_supplier_transfer.transfers_v1 t where not cp7_supplier_transfer.valid_transfer_v1(t.id)
  union all
  select 'OW06_SUPPLIER_TRANSFER_CORRECTION','CRITICAL',count(*)::bigint,
    'Supplier transfer successors must retain exact lineage and economic-date correction journals'
  from cp7_supplier_transfer.corrections_v1 c where not cp7_supplier_transfer.valid_correction_v1(c.original_id)
;

$function$;
set local role "cp7_procure_write";
grant create on schema "cp7_receipt_fix" to "postgres";
set local role "postgres";
CREATE OR REPLACE FUNCTION cp7_receipt_fix.blockers(p_purchase uuid)
 RETURNS jsonb
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO ''
AS $function$
 -- Each blocker names its documents (type and number), so the page can say
 -- exactly what to finish or cancel first. count keeps the blocking rows.
 select coalesce(jsonb_agg(jsonb_build_object('code',code,'count',n,'documents',docs)order by code),'[]')from(
  select code,count(*)::integer n,jsonb_agg(distinct jsonb_build_object('type',kind,'number',number))docs from(
   -- A supplier invoice that also covers other receipts is corrected whole; only
   -- an AP-backed return on another receipt of that invoice blocks the Native reversal.
   select 'CP7_RECEIPT_FIX_SHARED_INVOICE_RETURN_ACTIVE'code,'SUPPLIER_RETURN'kind,rh.return_number::text number from erp.material_supplier_return_items ri
    join erp.material_supplier_returns rh on rh.id=ri.return_id join erp.material_supplier_invoice_lines l on l.purchase_item_id=ri.purchase_item_id
    join erp.material_supplier_invoices v on v.id=l.invoice_id join erp.material_purchase_items i on i.id=ri.purchase_item_id
    where rh.status='POSTED'and coalesce(ri.ap_relief_qty_snapshot,0)>0 and v.status='POSTED'and i.purchase_id<>p_purchase
     and v.id in(select l2.invoice_id from erp.material_supplier_invoice_lines l2 join erp.material_purchase_items i2 on i2.id=l2.purchase_item_id where i2.purchase_id=p_purchase)
   union all select 'CP7_RECEIPT_FIX_PENDING_CHILD_REVIEW_REQUIRED','SUPPLIER_INVOICE',v.invoice_number from erp.material_supplier_invoice_lines l
    join erp.material_supplier_invoices v on v.id=l.invoice_id join erp.material_purchase_items i on i.id=l.purchase_item_id where i.purchase_id=p_purchase and v.status='DRAFT'
   union all select 'CP7_RECEIPT_FIX_PENDING_CHILD_REVIEW_REQUIRED','SUPPLIER_RETURN',s.return_number from erp.material_supplier_return_items x
    join erp.material_supplier_returns s on s.id=x.return_id join erp.material_purchase_items i on i.id=x.purchase_item_id where i.purchase_id=p_purchase and s.status='DRAFT'
   union all select 'CP7_RECEIPT_FIX_PENDING_CHILD_REVIEW_REQUIRED','SUPPLIER_PAYMENT',p.payment_number from erp.supplier_payments p where p.purchase_id=p_purchase and p.status='DRAFT'
   union all select 'CP7_RECEIPT_FIX_PENDING_CHILD_REVIEW_REQUIRED','COST_CORRECTION',k.correction_number from erp.material_purchase_cost_corrections k
    where k.purchase_id=p_purchase and k.status='DRAFT'
   -- An unposted cutting group (Native keeps status CUT with material_issue_posted
   -- false until POST) or draft transfer already binds a roll of this receipt;
   -- GPT's cutting inputs pin that roll too.
   union all select 'CP7_RECEIPT_FIX_DRAFT_ROLL_USE','CUTTING_GROUP',g.group_number from erp.cutting_group_rolls cr
    join erp.cutting_groups g on g.id=cr.cutting_group_id join erp.material_rolls r on r.id=cr.roll_id
    join erp.material_purchase_items i on i.id=r.purchase_item_id where i.purchase_id=p_purchase and not g.material_issue_posted
   union all select 'CP7_RECEIPT_FIX_DRAFT_ROLL_USE','MATERIAL_TRANSFER',t.transfer_number from erp.material_transfer_items ti
    join erp.material_transfers t on t.id=ti.transfer_id join erp.material_rolls r on r.id=ti.roll_id
    join erp.material_purchase_items i on i.id=r.purchase_item_id where i.purchase_id=p_purchase and t.status='DRAFT'
   union all select 'CP7_RECEIPT_FIX_RETURN_ACTIVE','SUPPLIER_RETURN',s.return_number from erp.material_supplier_return_items x
    join erp.material_supplier_returns s on s.id=x.return_id join erp.material_purchase_items i on i.id=x.purchase_item_id
    where i.purchase_id=p_purchase and s.status='POSTED'
   union all select 'CP7_RECEIPT_FIX_COST_CORRECTION_ACTIVE','COST_CORRECTION',k.correction_number from erp.material_purchase_cost_corrections k
    where k.purchase_id=p_purchase and k.status='POSTED'
   -- Moves are append-only: a restored move adds its negative row, so only a
   -- non-zero net per return and receipt pair is still an active credit.
   union all select 'CP7_RECEIPT_FIX_SUPPLIER_CREDIT_ACTIVE','MATERIAL_PURCHASE',o.purchase_number from(select m.source_purchase_id,m.target_purchase_id
     from erp.bf_supplier_credit_moves_v1 m where p_purchase in(m.source_purchase_id,m.target_purchase_id)
     group by m.return_id,m.source_purchase_id,m.target_purchase_id having sum(m.amount)<>0)b
    join erp.material_purchase_headers o on o.id=case when b.source_purchase_id=p_purchase then b.target_purchase_id else b.source_purchase_id end
   union all select 'CP7_RECEIPT_FIX_POCKET_ORIGIN_ACTIVE','POCKET_USE',coalesce(u.document_number,o.usage_id::text)from erp.be_pocket_receipt_origins_v1 o
    join erp.material_purchase_items i on i.id=o.purchase_item_id left join erp.be_pocket_usage_v1 u on u.id=o.usage_id where i.purchase_id=p_purchase
   union all select 'CP7_SUPPLIER_TRANSFER_USE_PARENT','SUPPLIER_TRANSFER',t.number
    from cp7_supplier_transfer.allocations_v1 a join cp7_supplier_transfer.transfers_v1 t on t.id=a.transfer_id
    where a.purchase_id=p_purchase and t.status='POSTED'
   union all select 'CP7_RECEIPT_FIX_OPENING_IMPORT_USE_IMPORT_WORKFLOW','OPENING_IMPORT',h.receipt_number from erp.initial_import_receipt_headers h
    where h.purchase_id=p_purchase
  )x group by code
 )y$function$;
set local role "cp7_procure_write";
revoke create on schema "cp7_receipt_fix" from "postgres";
set local role "postgres";
set local role "cp7_transaction_source_read";
CREATE OR REPLACE FUNCTION cp7_transaction_source.resolve(p jsonb)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
 SET search_path TO ''
 SET "TimeZone" TO 'UTC'
AS $function$
declare a jsonb;kind text;ident uuid;domain text;route text;permission text;
 parent_id uuid;doc jsonb;focus jsonb:='null';hops integer:=0;visited uuid[]:='{}';label text;focus_offset bigint;
begin
 if jsonb_typeof(p)is distinct from'object'or not(p?&array['source_type','source_id'])
  or(select count(*)from jsonb_object_keys(p))<>2 or jsonb_typeof(p->'source_type')is distinct from'string'
  or jsonb_typeof(p->'source_id')is distinct from'string'or p->>'source_type'!~'^[A-Z][A-Z0-9_]{0,79}$'
  or p->>'source_id'!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'then
  raise exception using errcode='22023',message='CP7_TRANSACTION_SOURCE_FIELDS';end if;
 a:=cp7_transaction_source.authority();kind:=p->>'source_type';ident:=(p->>'source_id')::uuid;
 -- Journal inverses point at journals, not at business documents. Follow
 -- only actual immutable journal links; never guess a document from a UUID.
 while kind='JOURNAL_REVERSAL'loop
  if not erp.has_permission('finance.journal.view')or a->'profile'->>'role_code'not in('OWNER','ADMIN')then
   raise exception using errcode='42501',message='CP7_TRANSACTION_SOURCE_ACCESS_DENIED';end if;
  hops:=hops+1;
  if hops>16 or ident=any(visited)then raise exception 'CP7_TRANSACTION_SOURCE_CHAIN_INVALID';end if;
  visited:=array_append(visited,ident);
  select j.source_type,j.source_id into kind,ident from erp.journal_entries j where j.id=ident;
  if not found or ident is null then raise exception 'CP7_TRANSACTION_SOURCE_UNAVAILABLE';end if;
 end loop;
 if kind in('CP7_SUPPLIER_TRANSFER','CP7_SUPPLIER_TRANSFER_TIME_NEUTRAL','CP7_SUPPLIER_TRANSFER_EFFECTIVE')then
  ident:=cp7_supplier_transfer.source_payment_v1(ident);kind:='SUPPLIER_PAYMENT';
 end if;
 -- Economic-date entries belong to the exact ordinary payment correction.
 -- Require both the immutable correction FK and the actual Native journal;
 -- an arbitrary payment UUID cannot masquerade as a correction source.
 if kind in('PAYMENT_CORRECTION_TIME_NEUTRAL','PAYMENT_CORRECTION_EFFECTIVE')then
  if not erp.has_permission('finance.journal.view')or a->'profile'->>'role_code'not in('OWNER','ADMIN')then
   raise exception using errcode='42501',message='CP7_TRANSACTION_SOURCE_ACCESS_DENIED';end if;
  if not exists(select 1 from cp7_payment_correction.links l join erp.journal_entries j
   on j.id=case when kind='PAYMENT_CORRECTION_TIME_NEUTRAL'then l.time_neutral_id else l.effective_inverse_id end
   where l.original_id=ident and j.source_type=kind and j.source_id=ident and j.status='POSTED')then
   raise exception 'CP7_TRANSACTION_SOURCE_UNAVAILABLE';end if;
  kind:='SALES_PAYMENT';
 end if;
 if kind in('SUPPLIER_PAYMENT_CORRECTION_TIME_NEUTRAL','SUPPLIER_PAYMENT_CORRECTION_EFFECTIVE')then
  if not erp.has_permission('finance.journal.view')or a->'profile'->>'role_code'not in('OWNER','ADMIN')then
   raise exception using errcode='42501',message='CP7_TRANSACTION_SOURCE_ACCESS_DENIED';end if;
  if not exists(select 1 from cp7_supplier_payment_correction.links l join erp.journal_entries j
   on j.id=case when kind='SUPPLIER_PAYMENT_CORRECTION_TIME_NEUTRAL'then l.time_neutral_id else l.effective_inverse_id end
   where l.original_id=ident and j.source_type=kind and j.source_id=ident and j.status='POSTED')then
   raise exception 'CP7_TRANSACTION_SOURCE_UNAVAILABLE';end if;
  kind:='SUPPLIER_PAYMENT';
 end if;
 if kind in('RETURN_CORRECTION_TIME_NEUTRAL','RETURN_CORRECTION_EFFECTIVE')then
  if not erp.has_permission('finance.journal.view')or a->'profile'->>'role_code'not in('OWNER','ADMIN')then
   raise exception using errcode='42501',message='CP7_TRANSACTION_SOURCE_ACCESS_DENIED';end if;
  select r.original_return_id into ident from cp7_sales_return_correction.journal_restatements r
   join cp7_sales_return_correction.links l on l.original_id=r.original_return_id
   join erp.journal_entries j on j.id=case when kind='RETURN_CORRECTION_TIME_NEUTRAL'then r.neutral_journal_id else r.effective_journal_id end
   where r.inverse_journal_id=ident and j.source_type=kind and j.source_id=r.inverse_journal_id and j.status='POSTED';
  if not found then raise exception 'CP7_TRANSACTION_SOURCE_UNAVAILABLE';end if;
  kind:='SALES_RETURN';
 end if;
 -- A Native FG inverse references the original movement UUID, not a QC
 -- inspection. Follow that actual immutable link only for the qualified QC
 -- source family. Other FG inverse families stay explicitly unsupported.
 if kind='FG_MOVEMENT_REVERSAL' then
  if not(erp.has_permission('warehouse.stock.view')or erp.has_permission('warehouse.movement.view'))then
   raise exception using errcode='42501',message='CP7_TRANSACTION_SOURCE_ACCESS_DENIED';end if;
  select m.source_type,m.source_id into kind,ident from erp.fg_stock_movements m where m.id=ident and m.reversal_of_id is null;
  if not found or ident is null then raise exception 'CP7_TRANSACTION_SOURCE_UNAVAILABLE';end if;
  if kind<>'QC_ITEM'and not(kind='SALES_RETURN_ITEM'and exists(select 1 from erp.sales_return_items i
   join cp7_sales_return_correction.links l on l.original_id=i.return_id where i.id=ident))then
   return jsonb_build_object('contract_version','cp7.transaction-source.v1','actor_scope_id',cp7_request_context.uid(),'source',p,
    'status','UNSUPPORTED_SOURCE','document',null,'read_at',statement_timestamp(),'business_DML',false);
  end if;
 end if;
 case
 when kind in('MATERIAL_PURCHASE','MATERIAL_PURCHASE_GRNI_RECLASS','MATERIAL_PURCHASE_REVERSAL','MATERIAL_PURCHASE_ITEM','MATERIAL_PURCHASE_ROLL','MATERIAL_SUPPLIER_INVOICE','MATERIAL_SUPPLIER_INVOICE_LINE','SUPPLIER_PAYMENT')then
  domain:='RECEIPT';route:='procurement';permission:='warehouse.procurement.view';
 when kind in('MATERIAL_TRANSFER','MATERIAL_TRANSFER_ITEM')then
  domain:='MATERIAL_TRANSFER';route:='materials-rolls';permission:='warehouse.material.view';
 when kind in('MATERIAL_ADJUSTMENT','MATERIAL_ADJUSTMENT_ITEM')then
  domain:='MATERIAL_COUNT';route:='stock-adjustment';permission:='warehouse.material.view';
 when kind in('FG_ADJUSTMENT','FG_ADJUSTMENT_ITEM')then
  domain:='FG_ADJUSTMENT';route:='stock-adjustment';permission:='warehouse.fg.view';
 when kind in('SALE','SALE_ITEM','SALES_ITEM','SALES_PAYMENT','SALES_RETURN','SALES_RETURN_ITEM')then
  domain:='SALE';route:=case when kind='SALES_PAYMENT'then'sales-payments'when kind in('SALES_RETURN','SALES_RETURN_ITEM')then'sales-returns'else'sales-invoice'end;
  permission:='sales.invoice.view';
 when kind in('MISC_FINANCE','MISC_CORRECTION_TIME_NEUTRAL','MISC_CORRECTION_EFFECTIVE')then
  domain:='MISC_FINANCE';route:='finance-journal';permission:='finance.journal.view';
 when kind in('PAYROLL_ATTENDANCE_ACCRUAL','PAYROLL_EXTRA_ACCRUAL','PAYROLL_MANUAL_REDUCTION','PAYROLL_MATERIAL_DEDUCTION','PAYROLL_CASH_ADVANCE_DEDUCTION','PAYROLL_OTHER_DEDUCTION','PAYROLL_PAYMENT','PAYROLL_INSTALLMENT')then
  domain:='PAYROLL';route:='finance-payroll';permission:='finance.payroll.view';
 when kind in('CONTRACTOR_ACCESSORY_STOCK_COST','CONTRACTOR_MATERIAL_RECEIVABLE','CONTRACTOR_MATERIAL_ISSUE_ITEM')then
  domain:='ACCESSORY_ISSUE';route:='contractor-issue';permission:='finance.contractor_accessory.view';
 when kind in('REWORK_ORDER','REWORK_COMPLETION')then
  domain:='BS_REWORK';route:='bs-rework';permission:='production.bs_rework.view';
 when kind in('QC_INSPECTION','QC_ITEM')then
  domain:='QC';route:='qc';permission:='production.final_sku.view';
 when kind in('LAUNDRY_DELIVERY','LAUNDRY_DELIVERY_LINE','LAUNDRY_DELIVERY_BATCH_SIZE_LINE',
  'LAUNDRY_RECEIPT','LAUNDRY_RECEIPT_LINE','LAUNDRY_RECEIPT_BATCH_SIZE_LINE')then
  domain:='LAUNDRY';route:='laundry';permission:='production.laundry.view';
 when kind in('CUTTING_GROUP','CUTTING_MATERIAL_ISSUE')then
  -- Posted cutting is read by the existing Native ALL distribution queue,
  -- never by the unposted cutting-draft selector. Its current view right is
  -- production.distribution.view; cutting.view alone cannot open that reader.
  domain:='CUTTING';route:='mandor-wip';permission:='production.distribution.view';
 else
  return jsonb_build_object('contract_version','cp7.transaction-source.v1','actor_scope_id',cp7_request_context.uid(),
   'source',p,'status','UNSUPPORTED_SOURCE','document',null,'read_at',statement_timestamp(),'business_DML',false);
 end case;
 -- Check the owner's current view permission before resolving child IDs or
 -- returning any Native document number/version. No finance is returned.
 if not erp.has_permission(permission)or(domain in('MATERIAL_COUNT','FG_ADJUSTMENT')and not erp.has_permission('warehouse.stock.adjust'))
  or(kind in('MATERIAL_SUPPLIER_INVOICE','MATERIAL_SUPPLIER_INVOICE_LINE','SUPPLIER_PAYMENT')and not erp.has_permission('finance.ap.view'))
  or(domain='MISC_FINANCE'and(not erp.has_permission('finance.cash.view')or a->'profile'->>'role_code'not in('OWNER','ADMIN')))
  or(kind='SALES_PAYMENT'and(not erp.has_permission('sales.payment.view')or not erp.has_permission('finance.ar.view')))
  or(kind in('SALES_RETURN','SALES_RETURN_ITEM')and(not erp.has_permission('sales.return.view')or not erp.has_permission('finance.ar.view')))then
  raise exception using errcode='42501',message='CP7_TRANSACTION_SOURCE_ACCESS_DENIED';end if;
 parent_id:=ident;
 case kind
 when'MATERIAL_PURCHASE_ITEM'then select i.purchase_id into parent_id from erp.material_purchase_items i where i.id=ident;
 when'MATERIAL_PURCHASE_ROLL'then select i.purchase_id into parent_id from erp.material_rolls r join erp.material_purchase_items i on i.id=r.purchase_item_id where r.id=ident;
 when'MATERIAL_SUPPLIER_INVOICE'then
  select i.purchase_id into parent_id from erp.material_supplier_invoice_lines l join erp.material_purchase_items i on i.id=l.purchase_item_id where l.invoice_id=ident order by i.purchase_id,l.id limit 1;
  focus:=jsonb_build_object('kind','PURCHASE_INVOICE','id',ident);
 when'MATERIAL_SUPPLIER_INVOICE_LINE'then
  select i.purchase_id,jsonb_build_object('kind','PURCHASE_INVOICE','id',l.invoice_id)into parent_id,focus
   from erp.material_supplier_invoice_lines l join erp.material_purchase_items i on i.id=l.purchase_item_id where l.id=ident;
 when'SUPPLIER_PAYMENT'then
  select s.purchase_id into parent_id from erp.supplier_payments s where s.id=ident;
  focus:=jsonb_build_object('kind','SUPPLIER_PAYMENT','id',ident);
 when'MATERIAL_TRANSFER_ITEM'then select i.transfer_id into parent_id from erp.material_transfer_items i where i.id=ident;
 when'MATERIAL_ADJUSTMENT_ITEM'then select i.adjustment_id into parent_id from erp.material_adjustment_items i where i.id=ident;
 when'FG_ADJUSTMENT_ITEM'then select i.adjustment_id into parent_id from erp.fg_adjustment_items i where i.id=ident;
 when'SALE_ITEM','SALES_ITEM'then select i.sale_id into parent_id from erp.sales_items i where i.id=ident;
 when'SALES_PAYMENT'then
  select i.sale_id into parent_id from erp.sales_payments i where i.id=ident;
  focus:=jsonb_build_object('kind','SALES_PAYMENT','id',ident);
 when'SALES_RETURN'then
  select i.sale_id into parent_id from erp.sales_returns i where i.id=ident;
  focus:=jsonb_build_object('kind','SALES_RETURN','id',ident);
 when'SALES_RETURN_ITEM'then
  select i.sale_id,jsonb_build_object('kind','SALES_RETURN','id',i.id)into parent_id,focus
   from erp.sales_return_items l join erp.sales_returns i on i.id=l.return_id where l.id=ident;
 when'PAYROLL_INSTALLMENT'then
  select i.payroll_id into parent_id from cp7_installment.payments i where i.id=ident;
  focus:=jsonb_build_object('kind','PAYROLL_INSTALLMENT','id',ident);
 when'CONTRACTOR_MATERIAL_ISSUE_ITEM'then
  select i.issue_id into parent_id from erp.contractor_material_issue_items i where i.id=ident;
 when'REWORK_ORDER','REWORK_COMPLETION'then
  select r.bs_case_id into parent_id from erp.rework_orders r where r.id=ident;
  focus:=jsonb_build_object('kind','REWORK_ORDER','id',ident);
 when'QC_ITEM'then
  select i.inspection_id into parent_id from erp.qc_inspection_items i where i.id=ident;
 when'LAUNDRY_DELIVERY_LINE'then
  select l.delivery_id into parent_id from erp.laundry_delivery_lines l where l.id=ident;
 when'LAUNDRY_DELIVERY_BATCH_SIZE_LINE'then
  select l.delivery_id into parent_id from erp.laundry_delivery_batch_size_lines s
   join erp.laundry_delivery_lines l on l.id=s.delivery_line_id where s.id=ident;
 when'LAUNDRY_RECEIPT'then
  select r.delivery_id into parent_id from erp.laundry_receipts r where r.id=ident;
  focus:=jsonb_build_object('kind','LAUNDRY_RECEIPT','id',ident);
 when'LAUNDRY_RECEIPT_LINE'then
  select r.delivery_id,jsonb_build_object('kind','LAUNDRY_RECEIPT','id',r.id)into parent_id,focus
   from erp.laundry_receipt_lines l join erp.laundry_receipts r on r.id=l.receipt_id where l.id=ident;
 when'LAUNDRY_RECEIPT_BATCH_SIZE_LINE'then
  select r.delivery_id,jsonb_build_object('kind','LAUNDRY_RECEIPT','id',r.id)into parent_id,focus
   from erp.laundry_receipt_batch_size_lines s join erp.laundry_receipt_lines l on l.id=s.receipt_line_id
   join erp.laundry_receipts r on r.id=l.receipt_id where s.id=ident;
 else null;
 end case;
 if parent_id is null then raise exception 'CP7_TRANSACTION_SOURCE_UNAVAILABLE';end if;
 case domain
 when'RECEIPT'then select to_jsonb(h),h.purchase_number into doc,label from erp.material_purchase_headers h where h.id=parent_id;
 when'MATERIAL_TRANSFER'then select to_jsonb(h),h.transfer_number into doc,label from erp.material_transfers h where h.id=parent_id;
 when'MATERIAL_COUNT'then select to_jsonb(h),h.adjustment_number into doc,label from erp.material_adjustments h where h.id=parent_id;
 when'FG_ADJUSTMENT'then select to_jsonb(h),h.adjustment_number into doc,label from erp.fg_adjustments h where h.id=parent_id;
 when'SALE'then select to_jsonb(h),h.sale_number into doc,label from erp.sales_headers h where h.id=parent_id;
 when'MISC_FINANCE'then select to_jsonb(h),h.transaction_number into doc,label from erp.misc_finance_transactions h where h.id=parent_id;
 when'PAYROLL'then select to_jsonb(h),h.payroll_number into doc,label from erp.payroll_settlements h where h.id=parent_id;
 when'ACCESSORY_ISSUE'then select to_jsonb(h),h.issue_number into doc,label from erp.contractor_material_issues h where h.id=parent_id;
 when'BS_REWORK'then select to_jsonb(h),h.bs_number into doc,label from erp.bs_cases h where h.id=parent_id;
 when'QC'then select to_jsonb(h),h.inspection_number into doc,label from erp.qc_inspections h where h.id=parent_id;
 when'LAUNDRY'then select to_jsonb(h),h.delivery_number into doc,label from erp.laundry_deliveries h where h.id=parent_id;
 when'CUTTING'then
  select to_jsonb(g),g.group_number into doc,label from erp.cutting_groups g
   join erp.production_orders po on po.id=g.po_id
   join erp.product_models pm on pm.id=po.model_id where g.id=parent_id;
 end case;
 if doc is null or coalesce(label,'')=''then raise exception 'CP7_TRANSACTION_SOURCE_UNAVAILABLE';end if;
 if domain='CUTTING'then
  if doc->'material_issue_posted'is distinct from'true'::jsonb then
   return jsonb_build_object('contract_version','cp7.transaction-source.v1','actor_scope_id',cp7_request_context.uid(),
    'source',p,'status','UNSUPPORTED_SOURCE','document',null,'read_at',statement_timestamp(),'business_DML',false);
  end if;
  focus:=jsonb_build_object('kind','CUTTING_GROUP','id',parent_id,'parent_id',doc->>'po_id');
 end if;
 -- The existing CP6 owner reads complete Native laundry-linked QC only.
 -- Legacy/import outputs are distinct sources, never guessed into this form.
 if domain='QC'and(not exists(select 1 from erp.qc_inspection_items i where i.inspection_id=parent_id)
  or exists(select 1 from erp.qc_inspection_items i where i.inspection_id=parent_id and i.source_laundry_receipt_batch_size_line_id is null))then
  return jsonb_build_object('contract_version','cp7.transaction-source.v1','actor_scope_id',cp7_request_context.uid(),
   'source',p,'status','UNSUPPORTED_SOURCE','document',null,'read_at',statement_timestamp(),'business_DML',false);
 end if;
 -- The unchanged owning Laundry workspace reads batch-linked deliveries.
 -- Receipt numbers are not searched by that reader: use its actual delivery
 -- number and recheck the embedded receipt UUID inside that exact parent.
 if domain='LAUNDRY'and(not exists(select 1 from erp.laundry_delivery_lines l where l.delivery_id=parent_id)
  or exists(select 1 from erp.laundry_delivery_lines l where l.delivery_id=parent_id
   and not exists(select 1 from erp.laundry_delivery_batch_size_lines s where s.delivery_line_id=l.id)))then
  return jsonb_build_object('contract_version','cp7.transaction-source.v1','actor_scope_id',cp7_request_context.uid(),
   'source',p,'status','UNSUPPORTED_SOURCE','document',null,'read_at',statement_timestamp(),'business_DML',false);
 end if;
 -- The current owner is specifically a counted-PCS accessory workspace.
 -- A mixed or fabric issue is a different Native document and cannot be
 -- redirected into that editor merely because its receivable has this kind.
 if domain='ACCESSORY_ISSUE'and exists(
  select 1 from erp.contractor_material_issue_items i
   left join erp.materials m on m.id=i.material_id
   left join erp.uom_definitions u on u.unit_code=m.unit_code
  where i.issue_id=parent_id and(m.material_type is distinct from'ACCESSORY'
   or upper(m.unit_code)is distinct from'PCS'or u.dimension is distinct from'COUNT'))then
  return jsonb_build_object('contract_version','cp7.transaction-source.v1','actor_scope_id',cp7_request_context.uid(),
   'source',p,'status','UNSUPPORTED_SOURCE','document',null,'read_at',statement_timestamp(),'business_DML',false);
 end if;
 -- Match each unchanged owning reader's pagination and exact ordering.
 -- BS uses ALL/BS, no query or pattern, and 50 rows; other children use 25.
 -- The owner re-reads the page and checks both identities; no client scan.
 if focus is not null and focus<>'null'::jsonb then
  case focus->>'kind'
  when'CUTTING_GROUP'then
   -- Exactly Native get_cutting_pickup_queue_v1(ALL,NULL,NULL,100,offset):
   -- all posted groups including picked-up/finished PO history, same inner
   -- joins and cut_at/group_number/id order. No query scan or first-row guess.
   select ((n-1)/100)*100 into focus_offset from(
    select g.id,row_number()over(order by g.cut_at,g.group_number,g.id)n
    from erp.cutting_groups g join erp.production_orders po on po.id=g.po_id
    join erp.product_models pm on pm.id=po.model_id where g.material_issue_posted
   )x where id=parent_id;
  when'LAUNDRY_RECEIPT'then
   -- Embedded child, not an independently paginated list. Zero is the closed
   -- focus position; the owner re-reads and checks this receipt's actual FK.
   if exists(select 1 from erp.laundry_receipts r where r.id=(focus->>'id')::uuid and r.delivery_id=parent_id)then
    focus_offset:=0;
   end if;
  when'SALES_PAYMENT'then
   select ((n-1)/25)*25 into focus_offset from(select id,row_number()over(order by payment_date desc,id)n from erp.sales_payments where sale_id=parent_id)x where id=(focus->>'id')::uuid;
  when'SALES_RETURN'then
   select ((n-1)/25)*25 into focus_offset from(select id,row_number()over(order by physical_at desc,id)n from erp.sales_returns where sale_id=parent_id)x where id=(focus->>'id')::uuid;
  when'PURCHASE_INVOICE'then
   select ((n-1)/25)*25 into focus_offset from(select ih.id,row_number()over(order by ih.received_at desc,ih.id)n from erp.material_supplier_invoices ih where exists(select 1 from erp.material_supplier_invoice_lines l join erp.material_purchase_items i on i.id=l.purchase_item_id where l.invoice_id=ih.id and i.purchase_id=parent_id))x where id=(focus->>'id')::uuid;
  when'SUPPLIER_PAYMENT'then
   select ((n-1)/25)*25 into focus_offset from(select p.id,row_number()over(order by p.payment_date,p.created_at,p.id)n from erp.supplier_payments p where p.purchase_id=parent_id)x where id=(focus->>'id')::uuid;
  when'PAYROLL_INSTALLMENT'then
   -- Match the existing installment source loop, including reversed history.
   select ((n-1)/25)*25 into focus_offset from(select i.id,row_number()over(order by i.payment_date,i.created_at,i.id)n from cp7_installment.payments i where i.payroll_id=parent_id)x where id=(focus->>'id')::uuid;
  when'REWORK_ORDER'then
   -- Native get_bs_resolution_workspace_v1 orders open cases before closed,
   -- then physical_at DESC, bs_number, id. Status comes from the same header;
   -- the Native owning reader remains authoritative for quantities and history.
   select ((n-1)/50)*50 into focus_offset from(select b.id,row_number()over(
    order by(b.status in('RESOLVED','SCRAPPED','WRITTEN_OFF','CANCELLED')),
     b.physical_at desc,b.bs_number,b.id)n from erp.bs_cases b)x where id=parent_id;
  end case;
  if focus_offset is null or focus_offset>1000000 then raise exception 'CP7_TRANSACTION_SOURCE_FOCUS_UNAVAILABLE';end if;
  focus:=focus||jsonb_build_object('page_offset',focus_offset);
 end if;
 if cp7_transaction_source.authority()is distinct from a or not erp.has_permission(permission)then
  raise exception using errcode='42501',message='CP7_TRANSACTION_SOURCE_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.transaction-source.v1','actor_scope_id',cp7_request_context.uid(),'source',p,
  'status','AVAILABLE','document',jsonb_build_object('domain',domain,'route',route,'id',parent_id,'number',label,
   'status',doc->'status','revision',doc->>'row_version','focus',focus),
  'read_at',statement_timestamp(),'business_DML',false);
end $function$;
set local role "postgres";
revoke "cp7_invoice_read","cp7_procure_write","cp7_transaction_source_read" from postgres granted by postgres restrict;
do $transfer_pins$ begin
 if exists(select from (values ('cp7_invoice.payment_detail(uuid,jsonb)','cp7_invoice_read','0152295c74dac6f4688fabbcc9fb115e488956aac9e258826d731412566834b3'),('cp7_invoice.reverse_payment_locked(jsonb)','postgres','4f889d4d76ca93183b6eaef35a6972815f161bc9932ac80969760a9d2651ed8b'),('cp7_receipt_fix.blockers(uuid)','postgres','8f4b0030c1c5918b5b0c88453dea0525199c83c873ae1b9df63631c23a30c016'),('cp7_supplier_payment_correction.apply(jsonb,uuid)','postgres','70105c19a95f2d02697a3da6a546a90bf0550e4e0c9f292b71424bcc00387b49'),('cp7_transaction_source.resolve(jsonb)','cp7_transaction_source_read','e3dc26b53db89538a48b93ff2cfcdc7f750b7e78f57909f14c12a3d0330ebf89'),('erp.post_supplier_payment(uuid)','postgres','3b492112735532d3cb79c81090607ef8d3774c728de7f889623beda60d7d4531'),('erp.reverse_journal(uuid,text)','postgres','ff6ce03777bbe75342055f5f680aa9200fe186df605c78b9e364cc60b2ef9611'),('erp.reverse_supplier_payment(uuid,text)','postgres','bbce8d7a8c271f6abcac89044e9b9b8f808f146492dc2cecab2140386ecc4387'),('erp.run_v267_financial_truth_checks()','postgres','7401b07c6e08b925b62e7c1f5feba1c5cc964115ab6e836873963b6b9cafe1cc')) e(sig,owner_name,sha)
   left join pg_proc p on p.oid=to_regprocedure(e.sig) where p.oid is null or
    pg_get_userbyid(p.proowner)<>e.owner_name or encode(sha256(convert_to(pg_get_functiondef(p.oid),'UTF8')),'hex')<>e.sha)
 then raise exception 'Supplier transfer payment predecessors changed';end if;
 end $transfer_pins$;
