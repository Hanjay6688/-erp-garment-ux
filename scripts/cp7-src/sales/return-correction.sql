-- Ordinary customer-return correction. Preserve original physical inputs;
-- admitted Native inverse and replacement run in this one transaction.
create schema cp7_sales_return_correction authorization cp7_sales_read;
revoke all on schema cp7_sales_return_correction from public,anon,authenticated,service_role,cp7_capture;
grant usage on schema cp7_sales_return_correction to postgres,cp7_sales_write;
create table cp7_sales_return_correction.requests(
 actor uuid not null,request_id uuid not null,payload jsonb not null,
 expected_version text not null,response jsonb,primary key(actor,request_id)
);
create table cp7_sales_return_correction.context(
 backend_pid integer not null,transaction_id bigint not null,actor uuid not null,
 request_id uuid not null,sale_id uuid not null,return_id uuid not null,
 primary key(backend_pid,transaction_id)
);
create table cp7_sales_return_correction.links(
 id uuid primary key default gen_random_uuid(),original_id uuid not null unique references erp.sales_returns,
 replacement_id uuid not null unique references erp.sales_returns,sale_id uuid not null references erp.sales_headers,
 actor uuid not null,request_id uuid not null,reason text not null,
 recorded_at timestamptz not null default clock_timestamp(),
 check(original_id<>replacement_id),check(length(btrim(reason))between 5 and 1000),unique(actor,request_id)
);
create table cp7_sales_return_correction.journal_restatements(
 source_journal_id uuid primary key references erp.journal_entries,
 inverse_journal_id uuid not null unique references erp.journal_entries,
 original_return_id uuid not null unique references erp.sales_returns,
 neutral_journal_id uuid not null unique references erp.journal_entries,
 effective_journal_id uuid not null unique references erp.journal_entries,
 native_economic_date date not null,corrected_economic_date date not null,
 recorded_at timestamptz not null default clock_timestamp()
);
create table cp7_sales_return_correction.helper_sources(
 native_signature text primary key,native_definition_sha256 text not null
);
alter table cp7_sales_return_correction.requests owner to postgres;
alter table cp7_sales_return_correction.context owner to postgres;
alter table cp7_sales_return_correction.links owner to postgres;
alter table cp7_sales_return_correction.journal_restatements owner to postgres;
alter table cp7_sales_return_correction.helper_sources owner to postgres;
alter table cp7_sales_return_correction.requests enable row level security;
alter table cp7_sales_return_correction.context enable row level security;
alter table cp7_sales_return_correction.links enable row level security;
alter table cp7_sales_return_correction.journal_restatements enable row level security;
alter table cp7_sales_return_correction.helper_sources enable row level security;
create policy private_requests on cp7_sales_return_correction.requests for all using(false)with check(false);
create policy private_context on cp7_sales_return_correction.context for all using(false)with check(false);
create policy private_links on cp7_sales_return_correction.links for all using(false)with check(false);
create policy private_journals on cp7_sales_return_correction.journal_restatements for all using(false)with check(false);
create policy private_helpers on cp7_sales_return_correction.helper_sources for all using(false)with check(false);
revoke all on all tables in schema cp7_sales_return_correction from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write;

create function cp7_sales_return_correction.access_now()returns jsonb
language plpgsql volatile security definer set search_path=''as $$
declare a jsonb;
begin
 a:=cp7_sales.command_access('RETURN');
 if cp7_sales.command_access('RETURN_REVERSE')is distinct from a or erp.has_permission('finance.hpp.view')is distinct from true then
  raise exception using errcode='42501',message='CP7_RETURN_CORRECTION_DENIED';end if;
 return a;
end $$;
create function cp7_sales_return_correction.require_context()returns void
language plpgsql volatile security definer set search_path=''as $$
begin
 perform cp7_sales_return_correction.access_now();
 if not exists(select 1 from cp7_sales_return_correction.context c where c.backend_pid=pg_backend_pid()
  and c.transaction_id=txid_current()and c.actor=auth.uid()
  and exists(select 1 from cp7_sales.command_context s where s.backend_pid=c.backend_pid
   and s.transaction_id=c.transaction_id and s.actor=c.actor and s.sale_id=c.sale_id and s.action='RETURN_REVERSE'))then
  raise exception using errcode='42501',message='CP7_RETURN_CORRECTION_PRIVATE_CONTEXT_REQUIRED';end if;
end $$;
create function cp7_sales_return_correction.immutable()returns trigger
language plpgsql security invoker set search_path=''as $$
begin raise exception 'CP7_RETURN_CORRECTION_HISTORY_IMMUTABLE';end $$;
create trigger immutable_links before update or delete on cp7_sales_return_correction.links
 for each row execute function cp7_sales_return_correction.immutable();
create trigger immutable_journals before update or delete on cp7_sales_return_correction.journal_restatements
 for each row execute function cp7_sales_return_correction.immutable();
create trigger immutable_helpers before update or delete on cp7_sales_return_correction.helper_sources
 for each row execute function cp7_sales_return_correction.immutable();
create trigger immutable_links_truncate before truncate on cp7_sales_return_correction.links
 for each statement execute function cp7_sales_return_correction.immutable();
create trigger immutable_journals_truncate before truncate on cp7_sales_return_correction.journal_restatements
 for each statement execute function cp7_sales_return_correction.immutable();
create trigger immutable_helpers_truncate before truncate on cp7_sales_return_correction.helper_sources
 for each statement execute function cp7_sales_return_correction.immutable();
create function cp7_sales_return_correction.protect_link()returns trigger
language plpgsql volatile security definer set search_path=''as $$
begin
 if new.actor is distinct from auth.uid()or not exists(select 1 from cp7_sales_return_correction.requests q
  where q.actor=new.actor and q.request_id=new.request_id and q.response is null
   and(q.payload->>'sale_id')::uuid=new.sale_id and(q.payload->>'return_id')::uuid=new.original_id)
  or not exists(select 1 from cp7_sales.command_context c where c.backend_pid=pg_backend_pid()
   and c.transaction_id=txid_current()and c.actor=new.actor and c.sale_id=new.sale_id and c.action='RETURN')
  or not exists(select 1 from erp.sales_returns original join erp.sales_returns replacement on replacement.id=new.replacement_id
   where original.id=new.original_id and original.sale_id=new.sale_id and replacement.sale_id=new.sale_id
    and original.status='REVERSED'and replacement.status='POSTED')then
  raise exception 'CP7_RETURN_CORRECTION_LINK_SOURCE_CHANGED';end if;
 return new;
end $$;
create trigger protect_links before insert on cp7_sales_return_correction.links
 for each row execute function cp7_sales_return_correction.protect_link();

create function cp7_sales_return_correction.validate(p jsonb)returns void
language plpgsql immutable security invoker set search_path=''as $$
begin
 if jsonb_typeof(p)is distinct from'object'or not(p?&array['sale_id','return_id','review_token','return_review_token','replacement','change_reason'])
  or(select count(*)from jsonb_object_keys(p))<>6
  or jsonb_typeof(p->'return_review_token')is distinct from'string'
  or coalesce(p->>'return_review_token','')!~'^[a-f0-9]{32}$'
  or jsonb_typeof(p->'replacement')is distinct from'object'
  or not(p->'replacement'?&array['physical_at','notes','items'])
  or(select count(*)from jsonb_object_keys(p->'replacement'))<>3 then raise exception 'CP7_RETURN_CORRECTION_FIELDS';end if;
 perform cp7_sales.validate_return(p-'return_review_token'-'replacement',true);
 perform cp7_sales.validate_return((p-'return_review_token'-'return_id'-'replacement')||(p->'replacement')
  ||jsonb_build_object('return_number','K-'||(p->>'return_id')),false);
end $$;
create function cp7_sales_return_correction.document(p_id uuid)returns jsonb
language sql stable security definer set search_path=''set TimeZone='UTC'as $$
 select jsonb_build_object('id',r.id,'sale_id',r.sale_id,'number',r.return_number,'physical_at',r.physical_at,
  'status',r.status,'notes',r.notes,'items',(select coalesce(jsonb_agg(jsonb_build_object(
   'id',i.id,'allocation_id',i.sale_stock_allocation_id,'product_id',i.product_id,'product_sku',p.sku,
   'lot_id',i.lot_id,'lot_number',fl.lot_number,'location_id',i.location_id,'location_name',l.location_name,
   'qty_pcs',i.qty_pcs::text,'quality_grade',i.quality_grade,'refund_amount',round(i.refund_amount,2)::text,
   'notes',i.notes)order by i.id),'[]')from erp.sales_return_items i
    join erp.products p on p.id=i.product_id join erp.fg_lots fl on fl.id=i.lot_id
    join erp.locations l on l.id=i.location_id where i.return_id=r.id))
 from erp.sales_returns r where r.id=p_id
$$;
-- Bind current stock, lot cost and destination state as well as Native invoice
-- children. This token does not claim an arbitrary historical reconstruction.
create function cp7_sales_return_correction.review_token(p_id uuid)returns text
language sql stable security definer set search_path=''as $$
 select md5(jsonb_build_object('return',to_jsonb(r),'sale',cp7_sales.review_token(r.sale_id),
  'items',(select jsonb_agg(to_jsonb(i)order by i.id)from erp.sales_return_items i where i.return_id=r.id),
  'lots',(select jsonb_agg(to_jsonb(l)order by l.id)from erp.fg_lots l where exists(
   select 1 from erp.sales_return_items i where i.return_id=r.id and i.lot_id=l.id)),
  'hpp',(select jsonb_agg(to_jsonb(h)order by h.lot_id,h.id)from erp.hpp_versions h where h.is_current and exists(
   select 1 from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id where i.sale_id=r.sale_id and a.lot_id=h.lot_id)),
  'stock',(select jsonb_agg(to_jsonb(x)order by x.lot_id,x.location_id,x.quality_grade)from(
   select m.lot_id,m.location_id,m.quality_grade,sum(m.qty_signed)qty,max(m.system_created_at)last_recorded_at,count(*)n
   from erp.fg_stock_movements m where exists(select 1 from erp.sale_stock_allocations a
    join erp.sales_items i on i.id=a.sale_item_id where i.sale_id=r.sale_id and a.lot_id=m.lot_id)
   group by m.lot_id,m.location_id,m.quality_grade)x),
  'locations',(select jsonb_agg(to_jsonb(l)order by l.id)from erp.locations l where l.location_type='FG_WAREHOUSE'),
  'journals',(select jsonb_agg(to_jsonb(j)order by j.id)from erp.journal_entries j
   where j.source_type='SALES_RETURN'and j.source_id=r.id))::text)
 from erp.sales_returns r where r.id=p_id
$$;
create function cp7_sales_return_correction.link_value(p cp7_sales_return_correction.links)returns jsonb
language sql stable security definer set search_path=''set TimeZone='UTC'as $$
 select jsonb_build_object('id',p.id,'original_id',p.original_id,'replacement_id',p.replacement_id,'sale_id',p.sale_id,
  'actor_scope_id',p.actor,'request_id',p.request_id,'reason',p.reason,'recorded_at',p.recorded_at,
  'time_restatement',(select jsonb_build_object('source_journal_id',j.source_journal_id,
   'inverse_journal_id',j.inverse_journal_id,'neutral_journal_id',j.neutral_journal_id,
   'effective_journal_id',j.effective_journal_id,'native_economic_date',j.native_economic_date,
   'corrected_economic_date',j.corrected_economic_date)from cp7_sales_return_correction.journal_restatements j
   where j.original_return_id=p.original_id))
$$;
create function cp7_sales_return_correction.restate_reversal(p_source uuid,p_inverse uuid,p_reason text)returns void
language plpgsql volatile security definer set search_path=''as $$
declare original erp.journal_entries;inverse erp.journal_entries;source_return uuid;neutral uuid;effective uuid;lines jsonb;
begin
 perform cp7_sales_return_correction.require_context();
 select return_id into strict source_return from cp7_sales_return_correction.context
  where backend_pid=pg_backend_pid()and transaction_id=txid_current()and actor=auth.uid();
 select *into strict original from erp.journal_entries where id=p_source;
 select *into strict inverse from erp.journal_entries where id=p_inverse;
 if original.status<>'REVERSED'or original.source_type<>'SALES_RETURN'or original.source_id<>source_return
  or inverse.status<>'POSTED'or inverse.source_type<>'JOURNAL_REVERSAL'or inverse.source_id<>original.id
  or inverse.reversal_of_id is distinct from original.id then raise exception 'CP7_RETURN_CORRECTION_JOURNAL_SOURCE_CHANGED';end if;
 if original.economic_date=inverse.economic_date then return;end if;
 select jsonb_agg(jsonb_build_object('account_id',j.account_id,'debit',j.credit,'credit',j.debit,
  'description',j.description,'customer_id',j.customer_id,'vendor_id',j.vendor_id,
  'contractor_id',j.contractor_id,'po_id',j.po_id,'product_id',j.product_id)order by j.id)into lines
 from erp.journal_lines j where j.journal_entry_id=inverse.id;
 neutral:=erp.post_journal('RETURN_CORRECTION_TIME_NEUTRAL',inverse.id,inverse.economic_date,
  'Pembetulan retur: pindahkan waktu ekonomi pembalikan | '||p_reason,lines);
 select jsonb_agg(jsonb_build_object('account_id',j.account_id,'debit',j.debit,'credit',j.credit,
  'description',j.description,'customer_id',j.customer_id,'vendor_id',j.vendor_id,
  'contractor_id',j.contractor_id,'po_id',j.po_id,'product_id',j.product_id)order by j.id)into lines
 from erp.journal_lines j where j.journal_entry_id=inverse.id;
 effective:=erp.post_journal('RETURN_CORRECTION_EFFECTIVE',inverse.id,original.economic_date,
  'Pembetulan retur: waktu ekonomi kejadian asal | '||p_reason,lines);
 insert into cp7_sales_return_correction.journal_restatements values(original.id,inverse.id,source_return,
  neutral,effective,inverse.economic_date,original.economic_date,clock_timestamp());
end $$;

-- Original Native helpers remain unchanged. Derive only private admission,
-- helper calls, original physical/HPP inverse date and exact journal timing.
do $derive$
declare signature text;definition text;body text;changed text;name text;
begin
 foreach signature in array array['erp.reverse_fg_movement(uuid,text)',
  'erp._cp3_r4_reverse_journal_internal(uuid,text)','erp.reverse_journal(uuid,text)','erp.reverse_sales_return(uuid,text)']loop
  select pg_get_functiondef(oid),prosrc into strict definition,body from pg_proc where oid=signature::regprocedure;
  name:=split_part(split_part(signature,'.',2),'(',1);
  changed:=regexp_replace(body,'\m[Bb][Ee][Gg][Ii][Nn]\M',E'begin\n perform cp7_sales_return_correction.require_context();');
  if changed=body then raise exception 'CP7_RETURN_CORRECTION_NATIVE_BODY_CHANGED';end if;
  changed:=replace(changed,'erp.reverse_fg_movement(','cp7_sales_return_correction.reverse_fg_movement(');
  changed:=replace(changed,'erp.reverse_journal(','cp7_sales_return_correction.reverse_journal(');
  changed:=replace(changed,'erp._cp3_r4_reverse_journal_internal(','cp7_sales_return_correction._cp3_r4_reverse_journal_internal(');
  if name='reverse_fg_movement'then
   if length(body)-length(replace(body,'clock_timestamp()',''))<>length('clock_timestamp()')then
    raise exception 'CP7_RETURN_CORRECTION_NATIVE_FG_CLOCK_CHANGED';end if;
   changed:=replace(changed,'clock_timestamp()','m.physical_at');
  elsif name='_cp3_r4_reverse_journal_internal'then
   if strpos(body,'RETURN v_new_id;')=0 then raise exception 'CP7_RETURN_CORRECTION_NATIVE_JOURNAL_RETURN_CHANGED';end if;
   changed:=replace(changed,'RETURN v_new_id;',
    'PERFORM cp7_sales_return_correction.restate_reversal(p_journal_entry_id,v_new_id,p_reason); RETURN v_new_id;');
  elsif name='reverse_sales_return'then
   if strpos(body,$$((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date$$)=0 then
    raise exception 'CP7_RETURN_CORRECTION_NATIVE_HPP_CLOCK_CHANGED';end if;
   changed:=replace(changed,$$((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date$$,
    $$((h.physical_at AT TIME ZONE 'Asia/Jakarta'::text))::date$$);
  end if;
  definition:=replace(definition,body,changed);
  definition:=replace(definition,'FUNCTION erp.'||name||'(','FUNCTION cp7_sales_return_correction.'||name||'(');
  execute definition;
  execute format('alter function cp7_sales_return_correction.%I(uuid,text)owner to postgres',name);
  insert into cp7_sales_return_correction.helper_sources values(signature,
   encode(pg_catalog.sha256(convert_to(pg_get_functiondef(signature::regprocedure),'UTF8')),'hex'));
 end loop;
end $derive$;

create function cp7_sales_return_correction.workspace(p jsonb)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;r erp.sales_returns;h erp.sales_headers;eligible boolean;previous cp7_sales_return_correction.links;
 following cp7_sales_return_correction.links;allocations jsonb;current_allocations jsonb;total bigint;off integer;n integer;q text;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 if not cp7_sales.access_now()or erp.has_permission('sales.return.view')is distinct from true then
  raise exception using errcode='42501',message='CP7_RETURN_CORRECTION_READ_DENIED';end if;
 a:=erp.get_my_access_v1();
 if jsonb_typeof(p)is distinct from'object'or not(p?&array['sale_id','return_id'])
  or exists(select 1 from jsonb_object_keys(p)x where x not in('sale_id','return_id','q','offset','limit'))
  or jsonb_typeof(p->'sale_id')is distinct from'string'or jsonb_typeof(p->'return_id')is distinct from'string'
  or coalesce(p->>'sale_id','')!~*'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  or coalesce(p->>'return_id','')!~*'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  or(p?'q'and jsonb_typeof(p->'q')is distinct from'string')
  or exists(select 1 from jsonb_each(p)e where e.key in('offset','limit')and(jsonb_typeof(e.value)<>'number'or e.value::text!~'^[0-9]{1,7}$'))then
  raise exception 'CP7_RETURN_CORRECTION_QUERY';end if;
 off:=coalesce((p->>'offset')::integer,0);n:=coalesce((p->>'limit')::integer,25);q:=btrim(coalesce(p->>'q',''));
 if off not between 0 and 1000000 or n not between 1 and 100 or length(q)>120 then raise exception 'CP7_RETURN_CORRECTION_QUERY';end if;
 select *into r from erp.sales_returns where id=(p->>'return_id')::uuid and sale_id=(p->>'sale_id')::uuid;
 if r.id is null then raise exception 'CP7_RETURN_CORRECTION_NOT_FOUND';end if;
 select *into strict h from erp.sales_headers where id=r.sale_id;
 if(select count(*)from erp.sales_return_items where return_id=r.id)not between 1 and 100 then
  raise exception 'CP7_RETURN_CORRECTION_DOCUMENT_TOO_LARGE';end if;
 eligible:=r.status='POSTED'and h.status in('POSTED','PARTIAL_PAID','PAID')
  and not exists(select 1 from cp7_sales_return_correction.links where original_id=r.id);
 select *into previous from cp7_sales_return_correction.links where replacement_id=r.id and sale_id=h.id;
 select *into following from cp7_sales_return_correction.links where original_id=r.id and sale_id=h.id;
 -- Include this return's own capacity even when fully returned. Peer posted
 -- returns consume capacity; Native quantity/refund/HPP guards still decide.
 with sources as materialized(
  select x.id allocation_id,x.sale_item_id,x.lot_id,fl.lot_number,pr.id product_id,pr.sku product_sku,
   pr.product_name,s.size_code,l.location_name source_location_name,x.qty_pcs allocated_qty,
   coalesce((select sum(i.qty_pcs)from erp.sales_return_items i join erp.sales_returns rh on rh.id=i.return_id
    where i.sale_stock_allocation_id=x.id and rh.sale_id=h.id and rh.status='POSTED'and rh.id<>r.id),0)peer_returned_qty,
   i.qty_pcs sale_item_qty,i.line_total sale_item_net
  from erp.sale_stock_allocations x join erp.sales_items i on i.id=x.sale_item_id
   join erp.products pr on pr.id=i.product_id join erp.sizes s on s.id=pr.size_id
   join erp.fg_lots fl on fl.id=x.lot_id join erp.locations l on l.id=x.location_id where i.sale_id=h.id),
 eligible_rows as materialized(select *from sources where allocated_qty>peer_returned_qty
  and(q=''or strpos(lower(concat_ws(' ',product_sku,product_name,size_code,lot_number)),lower(q))>0)),
 sliced as(select *from eligible_rows order by sale_item_id,lot_id,allocation_id limit n offset off)
 select(select count(*)from eligible_rows),coalesce((select jsonb_agg(jsonb_build_object(
  'allocation_id',allocation_id,'sale_item_id',sale_item_id,'product_id',product_id,'product_sku',product_sku,
  'product_name',product_name,'size_code',size_code,'lot_id',lot_id,'lot_number',lot_number,
  'source_location_name',source_location_name,'allocated_qty',allocated_qty::text,
  'peer_returned_qty',peer_returned_qty::text,'replacement_capacity',(allocated_qty-peer_returned_qty)::text,
  'sale_item_qty',sale_item_qty::text,'sale_item_net',round(sale_item_net,2)::text)
  order by sale_item_id,lot_id,allocation_id)from sliced),'[]'),
 coalesce((select jsonb_agg(jsonb_build_object(
  'allocation_id',s.allocation_id,'sale_item_id',s.sale_item_id,'product_id',s.product_id,'product_sku',s.product_sku,
  'product_name',s.product_name,'size_code',s.size_code,'lot_id',s.lot_id,'lot_number',s.lot_number,
  'source_location_name',s.source_location_name,'allocated_qty',s.allocated_qty::text,
  'peer_returned_qty',s.peer_returned_qty::text,'replacement_capacity',(s.allocated_qty-s.peer_returned_qty)::text,
  'sale_item_qty',s.sale_item_qty::text,'sale_item_net',round(s.sale_item_net,2)::text)
  order by s.sale_item_id,s.lot_id,s.allocation_id)from sources s where exists(
   select 1 from erp.sales_return_items i where i.return_id=r.id and i.sale_stock_allocation_id=s.allocation_id)),'[]')
 into total,allocations,current_allocations;
 if erp.get_my_access_v1()is distinct from a then raise exception using errcode='42501',message='CP7_SALES_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.sales-return-correction-workspace.v1','read_at',clock_timestamp(),
  'source',jsonb_build_object('sale_id',h.id,'row_version',h.row_version::text,'review_token',cp7_sales.review_token(h.id)),
  'document',cp7_sales_return_correction.document(r.id),'return_review_token',cp7_sales_return_correction.review_token(r.id),
  'financial',cp7_sales.header(h,true)->'financial','eligible',eligible,
  'can_correct',eligible and a->'profile'->>'role_code'in('OWNER','ADMIN')
   and erp.has_permission('sales.return.create')and erp.has_permission('sales.return.post')
   and erp.has_permission('sales.return.reverse')and erp.has_permission('finance.hpp.view'),
  'allocations',jsonb_build_object('rows',allocations,'total',total::text,'offset',off,'limit',n,
   'next_offset',case when off+jsonb_array_length(allocations)<total then off+jsonb_array_length(allocations)else null end),
  'current_allocations',current_allocations,
  'previous',case when previous.id is null then null else jsonb_build_object(
   'link',cp7_sales_return_correction.link_value(previous),'document',cp7_sales_return_correction.document(previous.original_id))end,
  'next',case when following.id is null then null else jsonb_build_object(
   'link',cp7_sales_return_correction.link_value(following),'document',cp7_sales_return_correction.document(following.replacement_id))end,
  'production_go',false);
end $$;

create function cp7_sales_return_correction.command(p jsonb,p_request uuid,p_expected text)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;old cp7_sales_return_correction.requests;h erp.sales_headers;r erp.sales_returns;
 replacement uuid;line jsonb;allocation record;origin uuid;movement record;
 link cp7_sales_return_correction.links;result jsonb;resolved jsonb;correction_id uuid:=gen_random_uuid();
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_sales_return_correction.access_now();perform cp7_sales_return_correction.validate(p);
 if p_request is null or p_expected is null or p_expected!~'^[1-9][0-9]{0,18}$'then raise exception 'CP7_RETURN_CORRECTION_REQUEST_REQUIRED';end if;
 insert into cp7_sales_return_correction.requests values(auth.uid(),p_request,p,p_expected,null)on conflict do nothing;
 select *into strict old from cp7_sales_return_correction.requests where actor=auth.uid()and request_id=p_request for update;
 if old.payload is distinct from p or old.expected_version is distinct from p_expected then raise exception 'CP7_RETURN_CORRECTION_REQUEST_CHANGED';end if;
 if cp7_sales_return_correction.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_SALES_ACCESS_CHANGED';end if;
 if old.response is not null then return old.response;end if;
 if exists(select 1 from cp7_sales.command_context where backend_pid=pg_backend_pid()and transaction_id=txid_current())then
  raise exception using errcode='42501',message='CP7_RETURN_CORRECTION_PRIVATE_CONTEXT_REQUIRED';end if;
 -- Preserve Native FG, child, header and allocation lock order.
 perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 perform 1 from erp.sales_payments where sale_id=(p->>'sale_id')::uuid order by id for update;
 perform 1 from erp.sales_returns where sale_id=(p->>'sale_id')::uuid order by id for update;
 select *into h from erp.sales_headers where id=(p->>'sale_id')::uuid for update;
 select *into r from erp.sales_returns where id=(p->>'return_id')::uuid and sale_id=h.id;
 if h.id is null or r.id is null then raise exception 'CP7_RETURN_CORRECTION_NOT_FOUND';end if;
 perform 1 from erp.sales_items where sale_id=h.id order by id for update;
 perform 1 from erp.sale_stock_allocations x where exists(select 1 from erp.sales_items i
  where i.id=x.sale_item_id and i.sale_id=h.id)order by x.id for update;
 perform 1 from erp.sales_return_items i join erp.sales_returns rh on rh.id=i.return_id
  where rh.sale_id=h.id order by i.id for update of i;
 perform 1 from erp.locations where id in(select (value->>'location_id')::uuid from jsonb_array_elements(p->'replacement'->'items'))order by id for share;
 perform 1 from erp.hpp_versions v where v.is_current and exists(select 1 from erp.sale_stock_allocations x
  join erp.sales_items i on i.id=x.sale_item_id where i.sale_id=h.id and x.lot_id=v.lot_id)order by v.id for share;
 if cp7_sales_return_correction.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_SALES_ACCESS_CHANGED';end if;
 if h.row_version::text is distinct from p_expected or cp7_sales.review_token(h.id)is distinct from p->>'review_token'
  or cp7_sales_return_correction.review_token(r.id)is distinct from p->>'return_review_token'then raise exception 'CP7_RETURN_CORRECTION_STALE_REVIEW';end if;
 if r.status<>'POSTED'or h.status not in('POSTED','PARTIAL_PAID','PAID')
  or exists(select 1 from cp7_sales_return_correction.links where original_id=r.id)then raise exception 'CP7_RETURN_CORRECTION_INELIGIBLE';end if;
 if(p->'replacement'->>'physical_at')::timestamptz>statement_timestamp()then raise exception 'CP7_SALES_RETURN_FUTURE_DATE';end if;
 if r.physical_at=(p->'replacement'->>'physical_at')::timestamptz and r.notes is not distinct from p->'replacement'->>'notes'
  and(select jsonb_agg(jsonb_build_object('allocation_id',i.sale_stock_allocation_id,'location_id',i.location_id,
   'qty_pcs',i.qty_pcs::text,'quality_grade',i.quality_grade,'refund_amount',round(i.refund_amount,2)::text,'notes',i.notes)order by i.sale_stock_allocation_id)
   from erp.sales_return_items i where i.return_id=r.id)=(select jsonb_agg(jsonb_build_object(
    'allocation_id',(value->>'allocation_id')::uuid,'location_id',(value->>'location_id')::uuid,
    'qty_pcs',value->>'qty_pcs','quality_grade',value->>'quality_grade','refund_amount',round((value->>'refund_amount')::numeric,2)::text,
    'notes',value->>'notes')order by value->>'allocation_id')from jsonb_array_elements(p->'replacement'->'items'))then
  raise exception 'CP7_RETURN_CORRECTION_UNCHANGED';end if;
 perform set_config('app.change_reason',btrim(p->>'change_reason'),true);
 insert into cp7_sales_return_correction.context values(pg_backend_pid(),txid_current(),auth.uid(),p_request,h.id,r.id);
 insert into cp7_sales.command_context values(pg_backend_pid(),txid_current(),auth.uid(),h.id,'RETURN_REVERSE');
 perform cp7_sales_return_correction.reverse_sales_return(r.id,btrim(p->>'change_reason'));
 -- Exact inverses share the effective original card. No Native row is edited.
 for movement in select m.id,m.reversal_of_id from erp.fg_stock_movements m
  join erp.fg_stock_movements o on o.id=m.reversal_of_id
  join erp.sales_return_items i on i.id=o.source_id and o.source_type='SALES_RETURN_ITEM'
  where i.return_id=r.id and not exists(select 1 from cp7_fg.correction_movements x where x.member_id=m.id)loop
  select coalesce(x.origin_id,movement.reversal_of_id)into origin from(select 1)t
   left join cp7_fg.correction_movements x on x.member_id=movement.reversal_of_id;
  insert into cp7_fg.correction_movements values(movement.id,origin,correction_id,clock_timestamp());
 end loop;
 delete from cp7_sales.command_context where backend_pid=pg_backend_pid()and transaction_id=txid_current();
 delete from cp7_sales_return_correction.context where backend_pid=pg_backend_pid()and transaction_id=txid_current();
 insert into cp7_sales.command_context values(pg_backend_pid(),txid_current(),auth.uid(),h.id,'RETURN');
 insert into erp.sales_returns(return_number,sale_id,customer_id,physical_at,notes,status,created_by)
 values('K-'||p_request::text,h.id,h.customer_id,(p->'replacement'->>'physical_at')::timestamptz,
  p->'replacement'->>'notes','DRAFT',erp.current_app_user_id())returning id into replacement;
 for line in select value from jsonb_array_elements(p->'replacement'->'items')loop
  select x.id,x.lot_id,i.product_id into allocation from erp.sale_stock_allocations x join erp.sales_items i on i.id=x.sale_item_id
   where x.id=(line->>'allocation_id')::uuid and i.sale_id=h.id;
  if not found then raise exception 'CP7_SALES_RETURN_ALLOCATION_CHANGED';end if;
  insert into erp.sales_return_items(return_id,sale_stock_allocation_id,product_id,lot_id,location_id,qty_pcs,quality_grade,refund_amount,notes)
  values(replacement,allocation.id,allocation.product_id,allocation.lot_id,(line->>'location_id')::uuid,
   (line->>'qty_pcs')::integer,line->>'quality_grade',(line->>'refund_amount')::numeric,line->>'notes');
 end loop;
 perform erp.post_sales_return(replacement);
 -- A changed date/destination/grade remains a separate physical row. Only an
 -- identical product/lot/destination/grade/time can share an original card.
 for movement in select m.*from erp.fg_stock_movements m join erp.sales_return_items i
  on i.id=m.source_id and m.source_type='SALES_RETURN_ITEM'where i.return_id=replacement and m.movement_type='SALE_RETURN'loop
  select coalesce(x.origin_id,o.id)into origin from erp.fg_stock_movements o
   join erp.sales_return_items i on i.id=o.source_id and o.source_type='SALES_RETURN_ITEM'
   left join cp7_fg.correction_movements x on x.member_id=o.id
   where i.return_id=r.id and i.sale_stock_allocation_id=(select sale_stock_allocation_id from erp.sales_return_items where id=movement.source_id)
    and o.movement_type='SALE_RETURN'and o.product_id=movement.product_id and o.lot_id is not distinct from movement.lot_id
    and o.location_id=movement.location_id and o.quality_grade=movement.quality_grade and o.physical_at=movement.physical_at
   order by o.book_order,o.id limit 1;
  if origin is not null then insert into cp7_fg.correction_movements values(movement.id,origin,correction_id,clock_timestamp());end if;
 end loop;
 if cp7_sales_return_correction.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_SALES_ACCESS_CHANGED';end if;
 insert into cp7_sales_return_correction.links(id,original_id,replacement_id,sale_id,actor,request_id,reason)
 values(correction_id,r.id,replacement,h.id,auth.uid(),p_request,btrim(p->>'change_reason'))returning *into link;
 delete from cp7_sales.command_context where backend_pid=pg_backend_pid()and transaction_id=txid_current();
 select *into strict h from erp.sales_headers where id=h.id;
 resolved:=public.erp_cp7_resolve_transaction_source_v1(jsonb_build_object('source_type','SALES_RETURN','source_id',replacement));
 if resolved->>'status'is distinct from 'AVAILABLE'or resolved#>>'{document,domain}'is distinct from 'SALE'
  or resolved#>>'{document,id}'is distinct from h.id::text
  or resolved#>>'{document,focus,kind}'is distinct from 'SALES_RETURN'
  or resolved#>>'{document,focus,id}'is distinct from replacement::text
  or resolved#>>'{document,focus,page_offset}'is null then raise exception 'CP7_RETURN_CORRECTION_SOURCE_UNAVAILABLE';end if;
 result:=jsonb_build_object('contract_version','cp7.sales-return-correction.v1','kind','COMMITTED_OUTCOME','action','RETURN_CORRECT',
  'request_id',p_request,'sale_id',h.id,'row_version',h.row_version::text,'status',h.status,
  'original_return_id',r.id,'original_return_status','REVERSED','return_id',replacement,'return_status','POSTED',
  'return_page_offset',(resolved#>>'{document,focus,page_offset}')::integer,
  'link',cp7_sales_return_correction.link_value(link),'production_go',false);
 update cp7_sales_return_correction.requests set response=result where actor=auth.uid()and request_id=p_request;
 return result;
end $$;
create function cp7_sales_return_correction.report_lifecycle(p_from date,p_to date)
returns table(source_id uuid,event_sign integer)
language sql stable security definer set search_path=''as $$
 select original.source_id,e.event_sign from cp7_sales_return_correction.journal_restatements r
 join erp.journal_entries original on original.id=r.source_journal_id
 cross join lateral(values(r.neutral_journal_id,1,'RETURN_CORRECTION_TIME_NEUTRAL'),
  (r.effective_journal_id,-1,'RETURN_CORRECTION_EFFECTIVE'))e(journal_id,event_sign,source_type)
 join erp.journal_entries posted on posted.id=e.journal_id and posted.source_type=e.source_type and posted.source_id=r.inverse_journal_id
 where original.status='REVERSED'and original.source_type='SALES_RETURN'and posted.status='POSTED'
  and posted.transaction_date between p_from and p_to
$$;

alter function cp7_sales_return_correction.access_now()owner to postgres;
alter function cp7_sales_return_correction.require_context()owner to postgres;
alter function cp7_sales_return_correction.immutable()owner to postgres;
alter function cp7_sales_return_correction.protect_link()owner to postgres;
alter function cp7_sales_return_correction.validate(jsonb)owner to postgres;
alter function cp7_sales_return_correction.document(uuid)owner to postgres;
alter function cp7_sales_return_correction.review_token(uuid)owner to postgres;
alter function cp7_sales_return_correction.link_value(cp7_sales_return_correction.links)owner to postgres;
alter function cp7_sales_return_correction.restate_reversal(uuid,uuid,text)owner to postgres;
alter function cp7_sales_return_correction.workspace(jsonb)owner to postgres;
alter function cp7_sales_return_correction.command(jsonb,uuid,text)owner to postgres;
alter function cp7_sales_return_correction.report_lifecycle(date,date)owner to postgres;
grant execute on function cp7_sales.validate_return(jsonb,boolean),cp7_sales.header(erp.sales_headers,boolean)to postgres;
revoke all on all functions in schema cp7_sales_return_correction from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write;
grant execute on function cp7_sales_return_correction.workspace(jsonb)to cp7_sales_read;
grant execute on function cp7_sales_return_correction.command(jsonb,uuid,text)to cp7_sales_write;
create function public.erp_cp7_get_sales_return_correction_v1(p_query jsonb)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_sales_return_correction.workspace(p_query)$$;
create function public.erp_cp7_correct_sales_return_v1(p_payload jsonb,p_request uuid,p_expected text)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_sales_return_correction.command(p_payload,p_request,p_expected)$$;
grant create on schema public to cp7_sales_read,cp7_sales_write;
alter function public.erp_cp7_get_sales_return_correction_v1(jsonb)owner to cp7_sales_read;
alter function public.erp_cp7_correct_sales_return_v1(jsonb,uuid,text)owner to cp7_sales_write;
revoke create on schema public from cp7_sales_read,cp7_sales_write;
revoke all on function public.erp_cp7_get_sales_return_correction_v1(jsonb),public.erp_cp7_correct_sales_return_v1(jsonb,uuid,text)from public,anon,authenticated,service_role;
grant execute on function public.erp_cp7_get_sales_return_correction_v1(jsonb),public.erp_cp7_correct_sales_return_v1(jsonb,uuid,text)to authenticated;
