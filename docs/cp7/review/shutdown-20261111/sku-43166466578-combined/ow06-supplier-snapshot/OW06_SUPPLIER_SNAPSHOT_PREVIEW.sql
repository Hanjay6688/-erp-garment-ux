CREATE OR REPLACE FUNCTION cp7_supplier_transfer.detail_v1(p_transfer uuid)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO ''
 SET "TimeZone" TO 'UTC'
AS $function$
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
end $function$;
CREATE OR REPLACE FUNCTION cp7_supplier_transfer.child_detail_v1(p_payment uuid, p_ap jsonb)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO ''
 SET "TimeZone" TO 'UTC'
AS $function$
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
end $function$;
CREATE OR REPLACE FUNCTION cp7_supplier_transfer.review_v1(p_supplier uuid, p_transfer uuid)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO ''
 SET "TimeZone" TO 'UTC'
AS $function$
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
end $function$;
CREATE OR REPLACE FUNCTION cp7_supplier_transfer.workspace_snapshot_v1(p jsonb, p_authority jsonb)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
 SET search_path TO ''
 SET "TimeZone" TO 'UTC'
AS $function$
declare auth_before jsonb;r jsonb;t cp7_supplier_transfer.transfers_v1;ident uuid;supplier uuid;
 q text;bq text;off integer;boff integer;toff integer;n bigint;bn bigint;tn bigint;rows jsonb;brows jsonb;trows jsonb;ap jsonb;
begin
 auth_before:=p_authority;
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
 with matching as materialized(
  select * from cp7_supplier_transfer.transfers_v1 where supplier_id=supplier
 ), page_rows as(
  select * from matching order by recorded_at desc,id limit 25 offset toff
 )
 select (select count(*) from matching),
  coalesce((select jsonb_agg(jsonb_build_object('id',x.id,'number',x.number,'status',x.status,
    'amount',x.amount::text,'payment_date',x.payment_date)order by x.recorded_at desc,x.id)
   from page_rows x),'[]'::jsonb)
 into tn,trows;
 return jsonb_build_object('contract_version','cp7.supplier-transfer-workspace.v1','captured_at',statement_timestamp(),
  'supplier',r->'supplier','can_write',auth_before->'reverse_payment','review_token',r->'review_token',
  'query',jsonb_build_object('supplier_id',supplier,'transfer_id',ident,'purchase_q',q,'purchase_offset',off,'bank_q',bq,'bank_offset',boff,'transfer_offset',toff),
  'receipts',jsonb_build_object('rows',rows,'total',n::text,'offset',off,'limit',25,'next_offset',case when off+jsonb_array_length(rows)<n then off+jsonb_array_length(rows)else null end),
  'cash_accounts',jsonb_build_object('rows',brows,'total',bn::text,'offset',boff,'limit',25,'next_offset',case when boff+jsonb_array_length(brows)<bn then boff+jsonb_array_length(brows)else null end),
  'transfers',jsonb_build_object('rows',trows,'total',tn::text,'offset',toff,'limit',25,'next_offset',case when toff+jsonb_array_length(trows)<tn then toff+jsonb_array_length(trows)else null end),
  'selected',case when ident is null then null else cp7_supplier_transfer.detail_v1(ident)end);
end $function$;
revoke all on function cp7_supplier_transfer.workspace_snapshot_v1(jsonb,jsonb) from public,anon,authenticated,service_role,cp7_invoice_read;
CREATE OR REPLACE FUNCTION cp7_supplier_transfer.workspace_v1(p jsonb)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
 SET "TimeZone" TO 'UTC'
AS $function$
declare auth_before jsonb; result jsonb;
begin
 auth_before:=cp7_supplier_transfer.access_now_v1(false);
 result:=cp7_supplier_transfer.workspace_snapshot_v1(p,auth_before);
 if cp7_supplier_transfer.access_now_v1(false)is distinct from auth_before then raise exception using errcode='42501',message='CP7_SUPPLIER_TRANSFER_ACCESS_CHANGED';end if;
 return result;
end $function$;
