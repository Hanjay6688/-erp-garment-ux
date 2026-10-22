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
