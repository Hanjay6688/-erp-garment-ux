-- Owning correction command. Original posted quantities/prices are never edited.
-- Every inverse/replacement uses accepted writers in this same transaction.
create schema cp7_note authorization cp7_sales_write;
revoke all on schema cp7_note from public,anon,authenticated,service_role,cp7_capture;
create table cp7_note.requests(
 actor uuid not null,request_id uuid not null,payload jsonb not null,expected_version text not null,
 response jsonb,primary key(actor,request_id)
);
create table cp7_note.revisions(
 id uuid primary key default gen_random_uuid(),root_sale_id uuid not null references erp.sales_headers,
 previous_sale_id uuid not null unique references erp.sales_headers,
 replacement_sale_id uuid not null unique references erp.sales_headers,
 revision bigint not null,actor uuid not null,request_id uuid not null,reason text not null,
 effective_at timestamptz not null,recorded_at timestamptz not null default clock_timestamp(),
 unique(root_sale_id,revision),unique(actor,request_id)
);
create table cp7_note.context(
 backend_pid integer not null,transaction_id bigint not null,actor uuid not null,
 source_sale_id uuid not null,primary key(backend_pid,transaction_id)
);
create table cp7_note.helper_sources(native_signature text primary key,native_definition_sha256 text not null);
create table cp7_note.journal_restatements(
 inverse_journal_id uuid primary key references erp.journal_entries,
 source_journal_id uuid not null unique references erp.journal_entries,
 previous_sale_id uuid not null references erp.sales_headers,
 neutral_journal_id uuid not null unique references erp.journal_entries,
 effective_journal_id uuid not null unique references erp.journal_entries,
 native_economic_date date not null,corrected_economic_date date not null,
 recorded_at timestamptz not null default clock_timestamp()
);
create index note_journal_source on cp7_note.journal_restatements(previous_sale_id);
-- Note replay is reversal plus a fresh use of the same original funding.
-- Native replaces_payment_id is reserved for cash reallocation at the reversal
-- date and explicitly excludes imported advances. Keep note lineage here.
create table cp7_note.payment_replays(
 previous_payment_id uuid primary key references erp.sales_payments,
 replacement_payment_id uuid not null unique references erp.sales_payments,
 correction_id uuid not null references cp7_note.revisions(id)deferrable initially deferred,
 recorded_at timestamptz not null default clock_timestamp()
);
-- postgres is a non-superuser Native business executor on Supabase. Own only
-- this private command's metadata; the low public wrapper obtains no table DML.
alter table cp7_note.requests owner to postgres;
alter table cp7_note.revisions owner to postgres;
alter table cp7_note.context owner to postgres;
alter table cp7_note.helper_sources owner to postgres;
alter table cp7_note.journal_restatements owner to postgres;
alter table cp7_note.payment_replays owner to postgres;
alter table cp7_note.requests enable row level security;
alter table cp7_note.revisions enable row level security;
alter table cp7_note.context enable row level security;
alter table cp7_note.helper_sources enable row level security;
alter table cp7_note.journal_restatements enable row level security;
alter table cp7_note.payment_replays enable row level security;
create policy private_requests on cp7_note.requests for all using(false)with check(false);
create policy private_revisions on cp7_note.revisions for all using(false)with check(false);
create policy private_context on cp7_note.context for all using(false)with check(false);
create policy private_helper_sources on cp7_note.helper_sources for all using(false)with check(false);
create policy private_journal_restatements on cp7_note.journal_restatements for all using(false)with check(false);
create policy private_payment_replays on cp7_note.payment_replays for all using(false)with check(false);
revoke all on all tables in schema cp7_note from public,anon,authenticated,service_role,cp7_capture;

create function cp7_note.immutable_revision()returns trigger
language plpgsql security invoker set search_path=''as $$
begin raise exception 'CP7_NOTE_POSTED_REVISION_IMMUTABLE';end $$;
create trigger immutable_revision before update or delete on cp7_note.revisions
 for each row execute function cp7_note.immutable_revision();
create trigger immutable_journal_restatement before update or delete on cp7_note.journal_restatements
 for each row execute function cp7_note.immutable_revision();
create trigger immutable_payment_replay before update or delete on cp7_note.payment_replays
 for each row execute function cp7_note.immutable_revision();

create function cp7_note.access_now()returns jsonb
language plpgsql volatile security definer set search_path=''as $$
declare a jsonb;k text;
begin
 if auth.uid()is null or coalesce(auth.jwt()->>'role','')<>'authenticated'
  then raise exception using errcode='42501',message='CP7_NOTE_ACCESS_DENIED';end if;
 a:=erp.get_my_access_v1();
 if a->'allowed'is distinct from'true'::jsonb or erp.has_permission('sales.invoice.view')is distinct from true then
  raise exception using errcode='42501',message='CP7_SALES_ACCESS_DENIED';end if;
 if coalesce(a->'profile'->>'role_code','')not in('OWNER','ADMIN')then
  raise exception using errcode='42501',message='CP7_NOTE_OWNER_ADMIN_REQUIRED';end if;
 foreach k in array array['sales.invoice.view','sales.invoice.create','sales.invoice.edit_draft',
  'sales.invoice.post','sales.invoice.reverse','finance.ar.view','finance.hpp.view']loop
  if erp.has_permission(k)is distinct from true then raise exception using errcode='42501',message='CP7_NOTE_ACCESS_DENIED';end if;
 end loop;
 return a;
end $$;
create function cp7_note.require_context()returns void
language plpgsql volatile security definer set search_path=''as $$
begin
 perform cp7_note.access_now();
 if not exists(select 1 from cp7_note.context where backend_pid=pg_backend_pid()
  and transaction_id=txid_current()and actor=auth.uid())then
  raise exception using errcode='42501',message='CP7_NOTE_PRIVATE_CONTEXT_REQUIRED';end if;
end $$;

-- Generic Native reversals keep their accepted current economic date, posting
-- fact and lineage. A source-owned pair moves that exact inverse's economic
-- effect to the original date without changing one Native line or whole-ledger
-- amount. Native post_journal retains its closed-period/open-GL-date rule.
create function cp7_note.restate_reversal(p_source uuid,p_inverse uuid,p_reason text)returns void
language plpgsql volatile security definer set search_path=''as $$
declare original erp.journal_entries%rowtype;inverse erp.journal_entries%rowtype;
 leaf uuid;neutral uuid;effective uuid;lines jsonb;
begin
 perform cp7_note.require_context();
 select source_sale_id into strict leaf from cp7_note.context
  where backend_pid=pg_backend_pid()and transaction_id=txid_current()and actor=auth.uid();
 select *into strict original from erp.journal_entries where id=p_source;
 select *into strict inverse from erp.journal_entries where id=p_inverse;
 if original.status<>'REVERSED'or inverse.status<>'POSTED'
  or inverse.source_type<>'JOURNAL_REVERSAL'or inverse.source_id<>original.id
  or inverse.reversal_of_id is distinct from original.id
  or not(original.source_type='SALE'and original.source_id=leaf
   or original.source_type='SALES_RETURN'and exists(select 1 from erp.sales_returns where id=original.source_id and sale_id=leaf)
   or original.source_type='SALES_PAYMENT'and exists(select 1 from erp.sales_payments where id=original.source_id and sale_id=leaf))then
  raise exception 'CP7_NOTE_JOURNAL_SOURCE_CHANGED';end if;
 if original.economic_date=inverse.economic_date then return;end if;
 -- Undo the inverse only in its current economic period, from its exact lines.
 select jsonb_agg(jsonb_build_object('account_id',j.account_id,'debit',j.credit,'credit',j.debit,
  'description',j.description,'customer_id',j.customer_id,'vendor_id',j.vendor_id,
  'contractor_id',j.contractor_id,'po_id',j.po_id,'product_id',j.product_id)order by j.id)into lines
 from erp.journal_lines j where j.journal_entry_id=inverse.id;
 neutral:=erp.post_journal('NOTE_REVERSAL_TIME_NEUTRAL',inverse.id,inverse.economic_date,
  'Pembetulan nota: pindahkan waktu ekonomi pembalikan | '||p_reason,lines);
 -- Apply the same inverse exactly in the original economic period.
 select jsonb_agg(jsonb_build_object('account_id',j.account_id,'debit',j.debit,'credit',j.credit,
  'description',j.description,'customer_id',j.customer_id,'vendor_id',j.vendor_id,
  'contractor_id',j.contractor_id,'po_id',j.po_id,'product_id',j.product_id)order by j.id)into lines
 from erp.journal_lines j where j.journal_entry_id=inverse.id;
 effective:=erp.post_journal('NOTE_REVERSAL_EFFECTIVE',inverse.id,original.economic_date,
  'Pembetulan nota: waktu ekonomi kejadian asal | '||p_reason,lines);
 insert into cp7_note.journal_restatements values(inverse.id,original.id,leaf,neutral,effective,
  inverse.economic_date,original.economic_date,clock_timestamp());
end $$;

-- Copy the actual accepted Native definitions into this private namespace.
-- Original definitions/owners/ACLs are untouched. Scope physical/HPP inverse
-- dates, exact-line economic reclassification, helper calls and admission.
do $derive$
declare signature text;definition text;body text;changed text;name text;
begin
 foreach signature in array array['erp.reverse_fg_movement(uuid,text)',
  'erp._cp3_r4_reverse_journal_internal(uuid,text)','erp.reverse_journal(uuid,text)',
  'erp.reverse_sale(uuid,text)','erp.reverse_sales_return(uuid,text)','erp.reverse_sales_payment(uuid,text)']loop
  select pg_get_functiondef(oid),prosrc into strict definition,body from pg_proc where oid=signature::regprocedure;
  name:=split_part(split_part(signature,'.',2),'(',1);
  changed:=regexp_replace(body,'\m[Bb][Ee][Gg][Ii][Nn]\M',E'begin\n perform cp7_note.require_context();');
  if changed=body then raise exception 'CP7_NOTE_NATIVE_HELPER_BODY_CHANGED';end if;
  changed:=replace(changed,'erp.reverse_fg_movement(','cp7_note.reverse_fg_movement(');
  changed:=replace(changed,'erp.reverse_journal(','cp7_note.reverse_journal(');
  changed:=replace(changed,'erp._cp3_r4_reverse_journal_internal(','cp7_note._cp3_r4_reverse_journal_internal(');
  if name='reverse_fg_movement'then
   if length(body)-length(replace(body,'clock_timestamp()',''))<>length('clock_timestamp()')then
    raise exception 'CP7_NOTE_NATIVE_FG_CLOCK_CHANGED';end if;
   changed:=replace(changed,'clock_timestamp()','m.physical_at');
  elsif name='_cp3_r4_reverse_journal_internal'then
   if body!~*'\mcurrent_date\M'and strpos(body,'statement_timestamp() AT TIME ZONE')=0
    and strpos(body,'erp._cp3_business_date(current_timestamp)')=0
    and strpos(body,'erp._cp3_business_date(statement_timestamp())')=0 then raise exception 'CP7_NOTE_NATIVE_JOURNAL_CLOCK_CHANGED';end if;
   if strpos(body,'RETURN v_new_id;')=0 then raise exception 'CP7_NOTE_NATIVE_JOURNAL_RETURN_CHANGED';end if;
   changed:=replace(changed,'RETURN v_new_id;',
    'PERFORM cp7_note.restate_reversal(p_journal_entry_id,v_new_id,p_reason); RETURN v_new_id;');
  elsif name in('reverse_sale','reverse_sales_return')then
   if strpos(body,'statement_timestamp() AT TIME ZONE')=0 then raise exception 'CP7_NOTE_NATIVE_HPP_CLOCK_CHANGED';end if;
   changed:=replace(changed,$$((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date$$,
    case when name='reverse_sale'then $$((h.sale_date AT TIME ZONE 'Asia/Jakarta'::text))::date$$
    else $$((h.physical_at AT TIME ZONE 'Asia/Jakarta'::text))::date$$ end);
  end if;
  definition:=replace(definition,body,changed);
  definition:=replace(definition,'FUNCTION erp.'||name||'(','FUNCTION cp7_note.'||name||'(');
  execute definition;
  -- The disposable accepted installer is deliberately not postgres. Private
  -- copies run only under the admitted owning command; pin ownership rather
  -- than inherit the installer identity. Preserve Native security/config.
  execute format('alter function cp7_note.%I(uuid,text)owner to postgres',name);
  insert into cp7_note.helper_sources values(signature,encode(pg_catalog.sha256(convert_to(pg_get_functiondef(signature::regprocedure),'UTF8')),'hex'));
 end loop;
end $derive$;

create function cp7_note.workspace(p_sale uuid)returns jsonb
language plpgsql volatile security definer set search_path=''as $$
declare a jsonb;root uuid;leaf uuid;history jsonb;native jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_note.access_now();
 if p_sale is null then raise exception 'CP7_NOTE_SOURCE_REQUIRED';end if;
 select root_sale_id into root from cp7_note.revisions where replacement_sale_id=p_sale or previous_sale_id=p_sale order by revision desc limit 1;
 root:=coalesce(root,p_sale);
 select replacement_sale_id into leaf from cp7_note.revisions where root_sale_id=root order by revision desc limit 1;
 leaf:=coalesce(leaf,root);
 native:=public.erp_cp7_get_sales_v1(jsonb_build_object('sale_id',leaf,'limit',1,'offset',0));
 select coalesce(jsonb_agg(jsonb_build_object('revision_id',id,'revision',revision::text,
  'previous_sale_id',previous_sale_id,'replacement_sale_id',replacement_sale_id,
  'effective_at',effective_at,'recorded_at',recorded_at,'reason',reason)order by revision),'[]')into history
 from cp7_note.revisions where root_sale_id=root;
 if cp7_note.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_NOTE_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.note-correction-workspace.v1','read_at',clock_timestamp(),
  'root_sale_id',root,'current_sale_id',leaf,'history',history,'current',native,
  'original_note_number',(select sale_number from erp.sales_headers where id=root),'production_go',false);
end $$;

create function cp7_note.command(p_payload jsonb,p_request uuid,p_expected text)returns jsonb
language plpgsql volatile security definer set search_path=''as $$
declare a jsonb;old cp7_note.requests%rowtype;h erp.sales_headers%rowtype;root uuid;leaf uuid;
 revision bigint;replaced uuid;native_request uuid;result jsonb;draft jsonb;line jsonb;payment record;returned record;
 paid jsonb;returns jsonb;returned_lines jsonb;new_payment uuid;new_return uuid;allocation uuid;
 correction_id uuid:=gen_random_uuid();before_movements uuid[];origin record;new_move record;anchor uuid;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_note.access_now();perform cp7_sales.validate_draft(p_payload,true);
 if p_request is null or p_expected is null or p_expected!~'^[1-9][0-9]{0,18}$'then raise exception 'CP7_NOTE_REQUEST_REQUIRED';end if;
 insert into cp7_note.requests values(auth.uid(),p_request,p_payload,p_expected,null)on conflict do nothing;
 select *into strict old from cp7_note.requests where actor=auth.uid()and request_id=p_request for update;
 if old.payload is distinct from p_payload or old.expected_version is distinct from p_expected then raise exception 'CP7_NOTE_REQUEST_CHANGED';end if;
 if cp7_note.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_NOTE_ACCESS_CHANGED';end if;
 if old.response is not null then return old.response;end if;
 perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 perform pg_advisory_xact_lock(hashtextextended('FGBOOK|GLOBAL',0));
 if cp7_note.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_NOTE_ACCESS_CHANGED';end if;
 leaf:=(p_payload->>'sale_id')::uuid;
 perform 1 from erp.sales_payments where sale_id=leaf order by id for update;
 perform 1 from erp.sales_returns where sale_id=leaf order by id for update;
 select *into h from erp.sales_headers where id=leaf for update;
 if h.id is null or h.status not in('POSTED','PARTIAL_PAID','PAID')then raise exception 'CP7_NOTE_ACTIVE_POSTED_ONLY';end if;
 if h.row_version::text<>p_expected or cp7_sales.review_token(h.id)<>p_payload->>'review_token'then raise exception 'CP7_NOTE_REVIEW_CHANGED';end if;
 -- Historical correction keeps the actual original event identity/time.
 if p_payload->>'sale_number'is distinct from h.sale_number
  or(p_payload->>'sale_date')::timestamptz is distinct from h.sale_date
  or(p_payload->>'customer_id')::uuid is distinct from h.customer_id
  or(p_payload->>'source_location_id')::uuid is distinct from h.source_location_id then raise exception 'CP7_NOTE_SOURCE_IDENTITY_CHANGED';end if;
 select root_sale_id into root from cp7_note.revisions where replacement_sale_id=leaf;
 root:=coalesce(root,leaf);
 select coalesce(max(r.revision),0)+1 into revision from cp7_note.revisions r where r.root_sale_id=root;
 if exists(select 1 from cp7_note.revisions where previous_sale_id=leaf)then raise exception 'CP7_NOTE_SOURCE_SUPERSEDED';end if;
 if exists(select 1 from erp.sales_payments where sale_id=leaf and status='DRAFT')
  or exists(select 1 from erp.sales_returns where sale_id=leaf and status='DRAFT')then
  raise exception 'CP7_NOTE_PENDING_CHILD_REVIEW_REQUIRED';end if;
 select coalesce(jsonb_agg(to_jsonb(p)||jsonb_build_object('advance_id',l.advance_id)order by p.payment_date,p.id),'[]')into paid
 from erp.sales_payments p left join erp.initial_import_prepayment_payments l on l.payment_id=p.id
 where p.sale_id=leaf and p.status='POSTED';
 select coalesce(jsonb_agg(to_jsonb(r)||jsonb_build_object('items',
  (select jsonb_agg(to_jsonb(i)||jsonb_build_object('allocation_location_id',x.location_id)order by i.id)
    from erp.sales_return_items i join erp.sale_stock_allocations x on x.id=i.sale_stock_allocation_id where i.return_id=r.id))order by r.physical_at,r.id),'[]')into returns
 from erp.sales_returns r where r.sale_id=leaf and r.status='POSTED';
 select array_agg(m.id)into before_movements from erp.fg_stock_movements m where
  (m.source_type='SALE_ITEM'and exists(select 1 from erp.sales_items i where i.id=m.source_id and i.sale_id=leaf)
   or m.source_type='SALES_RETURN_ITEM'and exists(select 1 from erp.sales_return_items i join erp.sales_returns r on r.id=i.return_id where i.id=m.source_id and r.sale_id=leaf and r.status='POSTED'))
  and m.movement_type in('SALE','SALE_RETURN')and not exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=m.id);
 insert into cp7_note.context values(pg_backend_pid(),txid_current(),auth.uid(),leaf);
 insert into cp7_sales.command_context values(pg_backend_pid(),txid_current(),auth.uid(),leaf,'SALE_REVERSE');
 perform set_config('app.change_reason',p_payload->>'change_reason',true);
 -- Remove active children before reversing the invoice, then restore their
 -- immutable original physical inputs onto its replacement in one command.
 for payment in select *from jsonb_to_recordset(paid)as p(id uuid)loop
  perform cp7_sales.command_access('PAYMENT_REVERSE');perform cp7_note.reverse_sales_payment(payment.id,p_payload->>'change_reason');
 end loop;
 for returned in select *from jsonb_to_recordset(returns)as r(id uuid)loop
  perform cp7_sales.command_access('RETURN_REVERSE');perform cp7_note.reverse_sales_return(returned.id,p_payload->>'change_reason');
 end loop;
 perform cp7_note.reverse_sale(leaf,p_payload->>'change_reason');
 native_request:=md5(auth.uid()::text||':NOTE:'||p_request::text)::uuid;
 draft:=(p_payload-'sale_id'-'review_token'-'change_reason')||jsonb_build_object('sale_number',left((select sale_number from erp.sales_headers where id=root),38)||' · R'||revision::text||'-'||left(p_request::text,8),'reason',p_payload->>'change_reason');
 result:=erp.save_sale_draft_v2(draft,native_request,null);
 replaced:=(result->>'sale_id')::uuid;perform erp.post_sale(replaced);
 for returned in select value from jsonb_array_elements(returns)loop
  perform cp7_sales.command_access('RETURN');
  insert into erp.sales_returns(return_number,sale_id,customer_id,physical_at,notes,status,created_by)
  values(left(returned.value->>'return_number',38)||' · K-'||left(p_request::text,8),replaced,h.customer_id,
   (returned.value->>'physical_at')::timestamptz,returned.value->>'notes','DRAFT',erp.current_app_user_id())returning id into new_return;
  for line in select value from jsonb_array_elements(returned.value->'items')loop
   select x.id into allocation from erp.sale_stock_allocations x join erp.sales_items i on i.id=x.sale_item_id
    where i.sale_id=replaced and i.product_id=(line->>'product_id')::uuid and x.lot_id=(line->>'lot_id')::uuid
     and x.location_id=(line->>'allocation_location_id')::uuid
     and not exists(select 1 from erp.sales_return_items z where z.return_id=new_return and z.sale_stock_allocation_id=x.id)
     and x.qty_pcs>=
      (line->>'qty_pcs')::integer+coalesce((select sum(z.qty_pcs)from erp.sales_return_items z where z.sale_stock_allocation_id=x.id),0)
    order by x.id limit 1;
   if allocation is null then raise exception 'CP7_NOTE_RETURN_ALLOCATION_CHANGED';end if;
   insert into erp.sales_return_items(return_id,sale_stock_allocation_id,product_id,lot_id,location_id,qty_pcs,quality_grade,refund_amount,notes)
   values(new_return,allocation,(line->>'product_id')::uuid,(line->>'lot_id')::uuid,(line->>'location_id')::uuid,
    (line->>'qty_pcs')::integer,line->>'quality_grade',(line->>'refund_amount')::numeric,line->>'notes');
  end loop;
  perform erp.post_sales_return(new_return);
 end loop;
 for payment in select value from jsonb_array_elements(paid)loop
  perform cp7_sales.command_access('PAYMENT');
  insert into erp.sales_payments(sale_id,payment_number,payment_date,amount,cash_account_id,payment_method,reference_number,notes,status,created_by)
  values(replaced,left(payment.value->>'payment_number',38)||' · K-'||left(p_request::text,8),
   (payment.value->>'payment_date')::timestamptz,(payment.value->>'amount')::numeric,(payment.value->>'cash_account_id')::uuid,
   payment.value->>'payment_method',payment.value->>'reference_number',payment.value->>'notes','DRAFT',erp.current_app_user_id())returning id into new_payment;
  if payment.value->>'advance_id'is not null then
   -- Same original wallet and amount. Accepted Native funding validation locks
   -- it, checks its actual remaining amount/customer/source snapshot and dates,
   -- and posts liability/AR rather than cash. No opening balance is edited.
   insert into erp.initial_import_prepayment_payments(payment_id,advance_id,sales_payment_id,payment_snapshot)
   select new_payment,(payment.value->>'advance_id')::uuid,new_payment,to_jsonb(p)-'status'
   from erp.sales_payments p where p.id=new_payment;
  end if;
  perform erp.post_sales_payment(new_payment);
  insert into cp7_note.payment_replays(previous_payment_id,replacement_payment_id,correction_id)
  values((payment.value->>'id')::uuid,new_payment,correction_id);
 end loop;
 -- Collapse compensating movements under their original source card. A newly
 -- added SKU gets its own Native card inserted beside this note's source,
 -- using the accepted move writer. Unrelated manual order is never reset.
 -- Original quantity, recorded clock and posted price are never edited.
 for new_move in select m.*from erp.fg_stock_movements m where m.reversal_of_id=any(coalesce(before_movements,'{}'::uuid[]))
  or m.source_type='SALE_ITEM'and exists(select 1 from erp.sales_items i where i.id=m.source_id and i.sale_id=replaced)
  or exists(select 1 from erp.fg_stock_movements reservation join erp.sales_items i on i.id=reservation.source_id
    where reservation.id=m.reversal_of_id and reservation.source_type='SALE_ITEM'and i.sale_id=replaced)
  or m.source_type='SALES_RETURN_ITEM'and exists(select 1 from erp.sales_return_items i join erp.sales_returns r on r.id=i.return_id where i.id=m.source_id and r.sale_id=replaced)
  order by case when m.movement_type='SALE'and m.reversal_of_id is null then 0
    when m.reversal_of_id is null then 1 else 2 end,m.system_created_at,m.id loop
  anchor:=null;
  if new_move.reversal_of_id is not null then
   select coalesce(l.origin_id,new_move.reversal_of_id)into anchor from(select 1)x left join cp7_fg.correction_movements l on l.member_id=new_move.reversal_of_id;
  elsif new_move.source_type='SALE_ITEM'and exists(select 1 from erp.sales_items where id=new_move.source_id and sale_id=replaced)then
   select coalesce(l.origin_id,m.id)into anchor from erp.fg_stock_movements m join erp.sales_items i on i.id=m.source_id
    left join cp7_fg.correction_movements l on l.member_id=m.id
    where i.sale_id=leaf and m.movement_type='SALE'and m.product_id=new_move.product_id
     and m.location_id=new_move.location_id and m.quality_grade=new_move.quality_grade order by(m.lot_id=new_move.lot_id)desc,m.book_order,m.id limit 1;
   if anchor is null then
    select coalesce(l.origin_id,m.id)into anchor from erp.fg_stock_movements m join erp.sales_items i on i.id=m.source_id
     left join cp7_fg.correction_movements l on l.member_id=m.id
     where i.sale_id=replaced and m.movement_type='SALE'and m.product_id=new_move.product_id
      and m.location_id=new_move.location_id and m.quality_grade=new_move.quality_grade
     order by(m.lot_id=new_move.lot_id)desc,m.book_order,m.id limit 1;
    if anchor=new_move.id then
     select coalesce(l.origin_id,m.id) as origin_id into origin from erp.fg_stock_movements m join erp.sales_items i on i.id=m.source_id
      left join cp7_fg.correction_movements l on l.member_id=m.id
      where i.sale_id=leaf and m.movement_type='SALE'order by m.book_order,m.id limit 1;
     if origin.origin_id is null then raise exception 'CP7_NOTE_ORIGINAL_BOOK_SOURCE_REQUIRED';end if;
     perform erp.move_fg_stock_card_row_to_position(new_move.id,cp7_fg.book_anchor(new_move.id,origin.origin_id,'AFTER'));
    end if;
   end if;
  elsif new_move.source_type='SALES_RETURN_ITEM'then
   select coalesce(l.origin_id,m.id)into anchor from erp.fg_stock_movements m join erp.sales_return_items i on i.id=m.source_id join erp.sales_returns r on r.id=i.return_id
    left join cp7_fg.correction_movements l on l.member_id=m.id where r.sale_id=leaf and m.movement_type='SALE_RETURN'
     and m.product_id=new_move.product_id and m.lot_id is not distinct from new_move.lot_id and m.location_id=new_move.location_id
     and m.quality_grade=new_move.quality_grade and m.physical_at=new_move.physical_at order by m.book_order,m.id limit 1;
  end if;
  if anchor is not null and anchor<>new_move.id then insert into cp7_fg.correction_movements values(new_move.id,anchor,correction_id,clock_timestamp());end if;
 end loop;
 if cp7_note.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_NOTE_ACCESS_CHANGED';end if;
 insert into cp7_note.revisions(id,root_sale_id,previous_sale_id,replacement_sale_id,revision,actor,request_id,reason,effective_at)
 values(correction_id,root,leaf,replaced,revision,auth.uid(),p_request,p_payload->>'change_reason',h.sale_date);
 delete from cp7_sales.command_context where backend_pid=pg_backend_pid()and transaction_id=txid_current();
 delete from cp7_note.context where backend_pid=pg_backend_pid()and transaction_id=txid_current();
 result:=jsonb_build_object('contract_version','cp7.note-correction-outcome.v1','kind','COMMITTED_OUTCOME',
  'action','CORRECT','request_id',p_request,'root_sale_id',root,'previous_sale_id',leaf,
  'sale_id',replaced,'revision_id',correction_id,'revision',revision::text,'effective_at',h.sale_date);
 update cp7_note.requests set response=result where actor=auth.uid()and request_id=p_request;
 return result;
end $$;

alter function cp7_note.access_now()owner to postgres;
alter function cp7_note.require_context()owner to postgres;
alter function cp7_note.restate_reversal(uuid,uuid,text)owner to postgres;
alter function cp7_note.immutable_revision()owner to postgres;
alter function cp7_note.workspace(uuid)owner to postgres;
alter function cp7_note.command(jsonb,uuid,text)owner to postgres;
-- Exact private composition only. Reuse the admitted low read wrapper instead
-- of granting postgres every private sales reader. No Native privilege or
-- operational caller privilege changes. Context/lineage are CP7 metadata.
grant usage on schema cp7_note,cp7_fg to postgres;
grant execute on function public.erp_cp7_get_sales_v1(jsonb),cp7_fg.book_anchor(uuid,uuid,text)to postgres;
grant insert,delete on cp7_sales.command_context to postgres;
grant select,insert on cp7_fg.correction_movements to postgres;
revoke all on all functions in schema cp7_note from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write;
grant usage on schema cp7_note to cp7_sales_write;
grant execute on function cp7_note.workspace(uuid),cp7_note.command(jsonb,uuid,text)to cp7_sales_write;
create function public.erp_cp7_get_note_correction_v1(p_sale uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_note.workspace(p_sale)$$;
create function public.erp_cp7_correct_note_v1(p_payload jsonb,p_request uuid,p_expected text)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_note.command(p_payload,p_request,p_expected)$$;
grant create on schema public to cp7_sales_write;
alter function public.erp_cp7_get_note_correction_v1(uuid)owner to cp7_sales_write;
alter function public.erp_cp7_correct_note_v1(jsonb,uuid,text)owner to cp7_sales_write;
revoke create on schema public from cp7_sales_write;
revoke all on function public.erp_cp7_get_note_correction_v1(uuid),public.erp_cp7_correct_note_v1(jsonb,uuid,text)from public,anon,authenticated,service_role;
grant execute on function public.erp_cp7_get_note_correction_v1(uuid),public.erp_cp7_correct_note_v1(jsonb,uuid,text)to authenticated;
