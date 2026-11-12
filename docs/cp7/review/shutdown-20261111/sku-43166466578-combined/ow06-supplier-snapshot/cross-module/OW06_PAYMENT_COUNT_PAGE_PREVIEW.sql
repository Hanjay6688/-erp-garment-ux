CREATE OR REPLACE FUNCTION cp7_invoice.payment_workspace(p_purchase uuid, p_q text, p_offset integer, p_payment uuid)
 RETURNS jsonb
 LANGUAGE plpgsql
 SET search_path TO ''
AS $function$
declare a jsonb;h erp.material_purchase_headers;s erp.suppliers;ap jsonb;rows jsonb;total bigint;q text;
begin
 a:=cp7_invoice.payment_access();q:=btrim(coalesce(p_q,''));
 if p_purchase is null or length(q)>120 or p_offset is null or p_offset not between 0 and 1000000 then raise exception 'CP7_SUPPLIER_PAYMENT_QUERY';end if;
 select * into h from erp.material_purchase_headers where id=p_purchase;
 if not found or h.supplier_id is null then raise exception 'CP7_SUPPLIER_PAYMENT_RECEIPT_NOT_FOUND';end if;
 select * into s from erp.suppliers where id=h.supplier_id;ap:=cp7_invoice.payment_ap(h.id);
 if p_payment is not null then
  if q<>'' then raise exception 'CP7_SUPPLIER_PAYMENT_EXACT_QUERY';end if;
  select ((n-1)/25)*25 into p_offset from(select id,row_number()over(order by payment_date,created_at,id)n from erp.supplier_payments where purchase_id=h.id)x where id=p_payment;
  if p_offset is null or p_offset>1000000 then raise exception 'CP7_SUPPLIER_PAYMENT_NOT_FOUND';end if;
 end if;
 with matching as materialized(select * from erp.supplier_payments where purchase_id=h.id and(q='' or strpos(lower(payment_number),lower(q))>0)),
 page_rows as(select * from matching order by payment_date,created_at,id limit 25 offset p_offset)
 select (select count(*) from matching),coalesce((select jsonb_agg(cp7_invoice.payment_detail(p.id,ap)order by p.payment_date,p.created_at,p.id) from page_rows p),'[]'::jsonb)
 into total,rows;
 if cp7_invoice.payment_access()<>a then raise exception using errcode='42501',message='CP7_SUPPLIER_PAYMENT_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.supplier-payment-read.v1','captured_at',statement_timestamp(),'query',q,'selected_payment_id',p_payment,
  'purchase',jsonb_build_object('id',h.id,'number',h.purchase_number,'status',h.status,'supplier_id',s.id,'supplier_name',s.supplier_name),
  'Native_AP',ap,'capabilities',jsonb_build_object('reverse',a->'reverse_payment'),
  'page',jsonb_build_object('rows',rows,'total',total::text,'offset',p_offset,'limit',25,
   'next_offset',case when p_offset+jsonb_array_length(rows)<total then p_offset+jsonb_array_length(rows)else null end));
end $function$;
CREATE OR REPLACE FUNCTION cp7_supplier_payment_create.workspace(p_query jsonb)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
 SET "TimeZone" TO 'UTC'
AS $function$
declare a jsonb;r jsonb;q text;off integer;rows jsonb;total bigint;
begin
 a:=cp7_invoice.payment_access();
 if jsonb_typeof(p_query)is distinct from'object'or not(p_query?'purchase_id')
  or exists(select 1 from jsonb_object_keys(p_query)x where x not in('purchase_id','bank_q','bank_offset'))
  or jsonb_typeof(p_query->'purchase_id')is distinct from'string'or coalesce(p_query->>'purchase_id','')!~*'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  or(p_query?'bank_q'and jsonb_typeof(p_query->'bank_q')is distinct from'string')
  or(p_query?'bank_offset'and(jsonb_typeof(p_query->'bank_offset')is distinct from'number'or coalesce(p_query->>'bank_offset','')!~'^(0|[1-9][0-9]{0,6})$'))then
  raise exception 'CP7_SUPPLIER_PAYMENT_CREATE_QUERY';end if;
 q:=btrim(coalesce(p_query->>'bank_q',''));off:=coalesce((p_query->>'bank_offset')::integer,0);
 if length(q)>120 or off>1000000 then raise exception 'CP7_SUPPLIER_PAYMENT_CREATE_QUERY';end if;
 r:=cp7_supplier_payment_create.review((p_query->>'purchase_id')::uuid);
 with matching as materialized(select c.* from erp.cash_accounts c join erp.chart_accounts ca on ca.id=c.coa_account_id
  where c.is_active and ca.is_active and ca.is_postable and(q=''or strpos(lower(c.cash_account_code||' '||c.cash_account_name),lower(q))>0)),
 page_rows as(select * from matching order by cash_account_code,id limit 25 offset off)
 select (select count(*) from matching),coalesce((select jsonb_agg(jsonb_build_object('id',c.id,'code',c.cash_account_code,'name',c.cash_account_name,'kind',c.account_kind)order by c.cash_account_code,c.id) from page_rows c),'[]'::jsonb)
 into total,rows;
 if cp7_invoice.payment_access()is distinct from a then raise exception using errcode='42501',message='CP7_SUPPLIER_PAYMENT_ACCESS_CHANGED';end if;
 return r||jsonb_build_object('contract_version','cp7.supplier-payment-create-workspace.v1','captured_at',statement_timestamp(),
  'can_create',a->'reverse_payment','cash_accounts',jsonb_build_object('rows',rows,'total',total::text,'offset',off,'limit',25,
   'next_offset',case when off+jsonb_array_length(rows)<total then off+jsonb_array_length(rows)else null end));
end $function$;
CREATE OR REPLACE FUNCTION cp7_supplier_payment_correction.workspace(p_query jsonb)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
 SET "TimeZone" TO 'UTC'
AS $function$
declare a jsonb;original erp.supplier_payments;h erp.material_purchase_headers;ap jsonb;d jsonb;
 prev cp7_supplier_payment_correction.links;nxt cp7_supplier_payment_correction.links;
 previous jsonb:='null';following jsonb:='null';q text;off integer;rows jsonb;total bigint;
begin
 a:=cp7_invoice.payment_access();
 if jsonb_typeof(p_query)is distinct from'object'or not(p_query?&array['purchase_id','payment_id'])
  or exists(select 1 from jsonb_object_keys(p_query)x where x not in('purchase_id','payment_id','bank_q','bank_offset'))
  or jsonb_typeof(p_query->'purchase_id')is distinct from'string'or coalesce(p_query->>'purchase_id','')!~*'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  or jsonb_typeof(p_query->'payment_id')is distinct from'string'or coalesce(p_query->>'payment_id','')!~*'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  or(p_query?'bank_q'and jsonb_typeof(p_query->'bank_q')is distinct from'string')
  or(p_query?'bank_offset'and(jsonb_typeof(p_query->'bank_offset')is distinct from'number'or coalesce(p_query->>'bank_offset','')!~'^(0|[1-9][0-9]{0,6})$'))then
  raise exception 'CP7_SUPPLIER_PAYMENT_CORRECTION_QUERY';end if;
 q:=btrim(coalesce(p_query->>'bank_q',''));off:=coalesce((p_query->>'bank_offset')::integer,0);
 if length(q)>120 or off>1000000 then raise exception 'CP7_SUPPLIER_PAYMENT_CORRECTION_QUERY';end if;
 select *into original from erp.supplier_payments where id=(p_query->>'payment_id')::uuid and purchase_id=(p_query->>'purchase_id')::uuid;
 if original.id is null then raise exception 'CP7_SUPPLIER_PAYMENT_NOT_FOUND';end if;
 select *into strict h from erp.material_purchase_headers where id=original.purchase_id;
 ap:=cp7_invoice.payment_ap(h.id);d:=cp7_invoice.payment_detail(original.id,ap);
 select *into prev from cp7_supplier_payment_correction.links where replacement_id=original.id and purchase_id=h.id;
 select *into nxt from cp7_supplier_payment_correction.links where original_id=original.id and purchase_id=h.id;
 if prev.original_id is not null then previous:=jsonb_build_object('link',cp7_supplier_payment_correction.link_value(prev),'document',cp7_invoice.payment_detail(prev.original_id,ap));end if;
 if nxt.original_id is not null then following:=jsonb_build_object('link',cp7_supplier_payment_correction.link_value(nxt),'document',cp7_invoice.payment_detail(nxt.replacement_id,ap));end if;
 with matching as materialized(select c.* from erp.cash_accounts c join erp.chart_accounts ca on ca.id=c.coa_account_id
  where c.is_active and ca.is_active and ca.is_postable and(q=''or strpos(lower(c.cash_account_code||' '||c.cash_account_name),lower(q))>0)),
 page_rows as(select * from matching order by cash_account_code,id limit 25 offset off)
 select (select count(*) from matching),coalesce((select jsonb_agg(jsonb_build_object('id',c.id,'code',c.cash_account_code,'name',c.cash_account_name,'kind',c.account_kind)order by c.cash_account_code,c.id) from page_rows c),'[]'::jsonb)
 into total,rows;
 if cp7_invoice.payment_access()is distinct from a then raise exception using errcode='42501',message='CP7_SUPPLIER_PAYMENT_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.supplier-payment-correction-workspace.v1','captured_at',statement_timestamp(),
  'purchase_id',h.id,'Native_AP',ap,'document',d,'can_correct',a->'reverse_payment',
  'eligible',original.status='POSTED'and h.status='POSTED'and original.cash_account_id is not null
   and not exists(select 1 from erp.initial_import_prepayment_payments where payment_id=original.id)
   and not exists(select 1 from cp7_supplier_payment_correction.links where original_id=original.id),
  'previous',previous,'next',following,'cash_accounts',jsonb_build_object('rows',rows,'total',total::text,'offset',off,'limit',25,
   'next_offset',case when off+jsonb_array_length(rows)<total then off+jsonb_array_length(rows)else null end));
end $function$;
