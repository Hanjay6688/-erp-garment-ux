"""Counted substitutions of eight installed list readers (OW-09, owner decision D17-16).

"Urut/saring seluruh data: berlaku pada seluruh hasil pencarian, termasuk lintas halaman; angka total dan ekspor
mengikuti filter yang sama." Each reader takes optional list keys (search, status or movement type, order and, for the
accessory notes, offset and limit) and applies them to every matching row before the page is cut; count, matching sums
and paging read the same set. The order SOURCE|LABEL_ASC|LABEL_DESC uses a natural label key (digit runs by value,
text runs lower-cased, byte order) with the reader's existing source order, which ends in a unique id, as tie-breaker.
Only when a new key is sent does the answer carry the list echo, so every old call keeps its exact answer. Access
checks, writers, tables and grants are not touched.

The seven CP7 bodies are frozen in scripts/cp7-src (E25j2); every step below is a whole-line substitution of the
installed pg_get_functiondef text whose old text occurs exactly once, and the first step of each reader adds an
in-body comment naming the change. The accessory note reader is the Native CP6 reader the screen already calls.
"""
ANALYSIS='cp7_finance.analysis(jsonb)'
CASH='cp7_sales.cash_workspace(jsonb)'
RETURNS='cp7_sales.return_workspace(jsonb)'
NOTES='cp7_payroll.note_workspace(text,jsonb)'
FG_DOCUMENTS='cp7_fg.adjust_workspace(jsonb)'
FG_CARD='cp7_fg.corrected_ledger(jsonb)'
COUNTS='cp7_material.count_workspace(jsonb)'
ACCESSORY='erp.get_accessory_issue_workspace_v1(jsonb)'
SIGNATURES=(ANALYSIS,CASH,RETURNS,NOTES,FG_DOCUMENTS,FG_CARD,COUNTS,ACCESSORY)
# Verified existing owners: the CP7 bundle's `alter function ... owner to` and the Native owner of the CP6 reader.
OWNERS={ANALYSIS:'cp7_finance_read',CASH:'cp7_sales_read',RETURNS:'cp7_sales_read',NOTES:'cp7_payroll_read',
        FG_DOCUMENTS:'cp7_fg_read',FG_CARD:'cp7_fg_read',COUNTS:'cp7_material_read',ACCESSORY:'postgres'}
PUBLIC={ANALYSIS:'public.erp_cp7_get_finance_analysis_v1(jsonb)',CASH:'public.erp_cp7_get_sales_cash_v1(jsonb)',
        RETURNS:'public.erp_cp7_get_sales_returns_v1(jsonb)',NOTES:'public.erp_cp7_get_nota_workspace_v1(text,jsonb)',
        FG_DOCUMENTS:'public.erp_cp7_get_fg_adjustments_v1(jsonb)',FG_CARD:'public.erp_cp7_get_fg_ledger_v2(jsonb)',
        COUNTS:'public.erp_cp7_get_material_counts_v1(jsonb)',ACCESSORY:'public.erp_get_accessory_issue_workspace_v1(jsonb)'}
MARKER="'LABEL_ASC'"
NATURAL=("(select coalesce(string_agg(case when nat.part[1]~'^[0-9]' then lpad(length(ltrim(nat.part[1],'0'))::text,10,'0')"
         "||ltrim(nat.part[1],'0') else lower(nat.part[1]) end,'' order by nat.pos),'')\n"
         "   from regexp_matches(hk.number,'[0-9]+|[^0-9]+','g') with ordinality nat(part,pos))")
STEPS={
 ANALYSIS:(
  ('analysis 1/5',
   " cash_ids uuid[];opening numeric;closing numeric;debits numeric;credits numeric;total bigint;rows jsonb;\n",
   " cash_ids uuid[];opening numeric;closing numeric;debits numeric;credits numeric;total bigint;rows jsonb;\n"
   " -- OW-09 (owner D17-16): optional entry_q/entry_status/entry_order filter and order the cash entries over the\n"
   " -- whole period before the page is cut; the echo and the matching sums appear only when one of those keys is\n"
   " -- sent, so an old query keeps a byte-identical answer.\n"
   " eq text;es text;eo text;listed boolean;match_debit numeric;match_credit numeric;\n"),
  ('analysis 2/5',
   "  or exists(select 1 from jsonb_object_keys(p_query)k where k not in('from','to','as_of','compare_from','compare_to','offset','limit'))\n",
   "  or exists(select 1 from jsonb_object_keys(p_query)k where k not in('from','to','as_of','compare_from','compare_to','offset','limit','entry_q','entry_status','entry_order'))\n"
   "  or exists(select 1 from jsonb_each(p_query)e where e.key in('entry_q','entry_order') and jsonb_typeof(e.value)<>'string')\n"
   "  or(p_query?'entry_status' and jsonb_typeof(p_query->'entry_status') not in('string','null'))\n"),
  ('analysis 3/5',
   " off:=coalesce((p_query->>'offset')::integer,0);n:=coalesce((p_query->>'limit')::integer,25);\n",
   " off:=coalesce((p_query->>'offset')::integer,0);n:=coalesce((p_query->>'limit')::integer,25);\n"
   " eq:=btrim(coalesce(p_query->>'entry_q',''));es:=p_query->>'entry_status';eo:=coalesce(p_query->>'entry_order','SOURCE');listed:=p_query?|array['entry_q','entry_status','entry_order'];\n"
   " if length(eq)>120 or(es is not null and es not in('POSTED','REVERSED'))or eo not in('SOURCE','LABEL_ASC','LABEL_DESC')then raise exception 'CP7_FINANCE_ANALYSIS_QUERY';end if;\n"),
  ('analysis 4/5',
   " select coalesce(sum(l.debit),0),coalesce(sum(l.credit),0),count(distinct j.id)\n"
   " into debits,credits,total from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id\n"
   " where j.status in('POSTED','REVERSED') and j.transaction_date between f and t and l.account_id=any(cash_ids);\n"
   " select coalesce(jsonb_agg(to_jsonb(x) order by x.transaction_date,x.posting_at,x.id),'[]') into rows from(\n"
   "  select j.id,j.journal_number,j.source_type,j.source_id,j.reversal_of_id,j.status,j.economic_date,j.transaction_date,j.posting_at,\n"
   "   sum(l.debit)::text debit,sum(l.credit)::text credit,sum(l.debit-l.credit)::text net\n"
   "  from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id\n"
   "  where j.status in('POSTED','REVERSED') and j.transaction_date between f and t and l.account_id=any(cash_ids)\n"
   "  group by j.id order by j.transaction_date,j.posting_at,j.id limit n offset off\n"
   " )x;\n",
   " select coalesce(sum(l.debit),0),coalesce(sum(l.credit),0)\n"
   " into debits,credits from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id\n"
   " where j.status in('POSTED','REVERSED') and j.transaction_date between f and t and l.account_id=any(cash_ids);\n"
   " -- Count, matching sums, order and page all read the same matching set. The\n"
   " -- label order is natural (digit runs by value) with the source order and the\n"
   " -- unique journal id as tie-breakers.\n"
   " with entries as materialized(\n"
   "  select j.id,j.journal_number,j.source_type,j.source_id,j.reversal_of_id,j.status,j.economic_date,j.transaction_date,j.posting_at,\n"
   "   sum(l.debit)debit,sum(l.credit)credit,sum(l.debit-l.credit)net\n"
   "  from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id\n"
   "  where j.status in('POSTED','REVERSED') and j.transaction_date between f and t and l.account_id=any(cash_ids)\n"
   "  group by j.id),\n"
   " matching as materialized(select e.* from entries e where(es is null or e.status=es)\n"
   "  and(eq='' or strpos(lower(concat_ws(' ',e.journal_number,e.source_type,e.source_id::text,e.economic_date::text,e.transaction_date::text)),lower(eq))>0)),\n"
   " keyed as(select m.*,case when eo<>'SOURCE'then(select coalesce(string_agg(case when nat.part[1]~'^[0-9]'then lpad(length(ltrim(nat.part[1],'0'))::text,10,'0')||ltrim(nat.part[1],'0')else lower(nat.part[1])end,''order by nat.pos),'')\n"
   "   from regexp_matches(m.journal_number,'[0-9]+|[^0-9]+','g')with ordinality nat(part,pos))end label_key from matching m),\n"
   " ordered as materialized(select kd.*,row_number()over(order by case when eo='LABEL_ASC'then kd.label_key end collate \"C\",case when eo='LABEL_DESC'then kd.label_key end collate \"C\" desc,\n"
   "   kd.transaction_date,kd.posting_at,kd.id)rn from keyed kd)\n"
   " select(select count(*)from matching),(select coalesce(sum(debit),0)from matching),(select coalesce(sum(credit),0)from matching),\n"
   "  coalesce((select jsonb_agg(jsonb_build_object('id',x.id,'journal_number',x.journal_number,'source_type',x.source_type,'source_id',x.source_id,'reversal_of_id',x.reversal_of_id,\n"
   "   'status',x.status,'economic_date',x.economic_date,'transaction_date',x.transaction_date,'posting_at',x.posting_at,'debit',x.debit::text,'credit',x.credit::text,'net',x.net::text)order by x.rn)\n"
   "   from(select * from ordered order by rn limit n offset off)x),'[]')\n"
   " into total,match_debit,match_credit,rows;\n"),
  ('analysis 5/5',
   "   'entries',jsonb_build_object('rows',rows,'total',total::text,'offset',off,'limit',n,'next_offset',case when off+jsonb_array_length(rows)<total then off+jsonb_array_length(rows)else null end)));\n",
   "   'entries',jsonb_build_object('rows',rows,'total',total::text,'offset',off,'limit',n,'next_offset',case when off+jsonb_array_length(rows)<total then off+jsonb_array_length(rows)else null end)\n"
   "    ||case when listed then jsonb_build_object('list',jsonb_build_object('q',eq,'status',es,'order',eo),\n"
   "     'sums',jsonb_build_object('debit',match_debit::text,'credit',match_credit::text,'net',(match_debit-match_credit)::text))else'{}'::jsonb end));\n"),
 ),
 CASH:(
  ('cash_workspace 1/3',
   "declare h erp.sales_headers;ident uuid;po integer;pn integer;bo integer;bn integer;q text;payments jsonb;banks jsonb;pt bigint;bt bigint;can_create boolean;\n",
   "declare h erp.sales_headers;ident uuid;po integer;pn integer;bo integer;bn integer;q text;payments jsonb;banks jsonb;pt bigint;bt bigint;can_create boolean;\n"
   " -- OW-09 (owner D17-16): optional payment_q/payment_status/payment_order filter and order the payment history\n"
   " -- of the invoice before the page is cut; the echo appears only when one of those keys is sent (old calls unchanged).\n"
   " pq text;ps text;pord text;listed boolean;\n"),
  ('cash_workspace 2/3',
   "  or exists(select 1 from jsonb_object_keys(p_query) x where x not in('sale_id','payment_offset','payment_limit','bank_q','bank_offset','bank_limit'))\n"
   "  or exists(select 1 from jsonb_each(p_query) e where e.key in('sale_id','bank_q') and jsonb_typeof(e.value)<>'string')\n"
   "  or exists(select 1 from jsonb_each(p_query) e where e.key in('payment_offset','payment_limit','bank_offset','bank_limit') and(jsonb_typeof(e.value)<>'number' or e.value::text!~'^[0-9]{1,7}$')) then raise exception 'CP7_SALES_CASH_QUERY';end if;\n"
   " ident:=(p_query->>'sale_id')::uuid;po:=coalesce((p_query->>'payment_offset')::integer,0);pn:=coalesce((p_query->>'payment_limit')::integer,25);bo:=coalesce((p_query->>'bank_offset')::integer,0);bn:=coalesce((p_query->>'bank_limit')::integer,25);q:=btrim(coalesce(p_query->>'bank_q',''));\n"
   " if ident is null or po not between 0 and 1000000 or bo not between 0 and 1000000 or pn not between 1 and 100 or bn not between 1 and 100 or length(q)>120 then raise exception 'CP7_SALES_CASH_QUERY';end if;\n"
   " select * into h from erp.sales_headers where id=ident;if h.id is null then raise exception 'CP7_SALES_NOT_FOUND';end if;\n"
   " select count(*) into pt from erp.sales_payments where sale_id=ident;\n"
   " select coalesce(jsonb_agg(jsonb_build_object('id',x.id,'number',x.payment_number,'physical_at',x.payment_date,'amount',x.amount::text,'cash_account_id',x.cash_account_id,'cash_account_name',(select cash_account_name from erp.cash_accounts where id=x.cash_account_id),'method',x.payment_method,'reference',x.reference_number,'notes',x.notes,'status',x.status,'replaces_payment_id',x.replaces_payment_id) order by x.payment_date desc,x.id),'[]') into payments\n"
   " from(select * from erp.sales_payments where sale_id=ident order by payment_date desc,id limit pn offset po)x;\n",
   "  or exists(select 1 from jsonb_object_keys(p_query) x where x not in('sale_id','payment_offset','payment_limit','bank_q','bank_offset','bank_limit','payment_q','payment_status','payment_order'))\n"
   "  or exists(select 1 from jsonb_each(p_query) e where e.key in('sale_id','bank_q','payment_q','payment_order') and jsonb_typeof(e.value)<>'string')\n"
   "  or(p_query?'payment_status' and jsonb_typeof(p_query->'payment_status') not in('string','null'))\n"
   "  or exists(select 1 from jsonb_each(p_query) e where e.key in('payment_offset','payment_limit','bank_offset','bank_limit') and(jsonb_typeof(e.value)<>'number' or e.value::text!~'^[0-9]{1,7}$')) then raise exception 'CP7_SALES_CASH_QUERY';end if;\n"
   " ident:=(p_query->>'sale_id')::uuid;po:=coalesce((p_query->>'payment_offset')::integer,0);pn:=coalesce((p_query->>'payment_limit')::integer,25);bo:=coalesce((p_query->>'bank_offset')::integer,0);bn:=coalesce((p_query->>'bank_limit')::integer,25);q:=btrim(coalesce(p_query->>'bank_q',''));\n"
   " pq:=btrim(coalesce(p_query->>'payment_q',''));ps:=p_query->>'payment_status';pord:=coalesce(p_query->>'payment_order','SOURCE');listed:=p_query?|array['payment_q','payment_status','payment_order'];\n"
   " if ident is null or po not between 0 and 1000000 or bo not between 0 and 1000000 or pn not between 1 and 100 or bn not between 1 and 100 or length(q)>120\n"
   "  or length(pq)>120 or(ps is not null and ps not in('DRAFT','POSTED','REVERSED'))or pord not in('SOURCE','LABEL_ASC','LABEL_DESC')then raise exception 'CP7_SALES_CASH_QUERY';end if;\n"
   " select * into h from erp.sales_headers where id=ident;if h.id is null then raise exception 'CP7_SALES_NOT_FOUND';end if;\n"
   " -- Count, order and page read the same matching set; the label order is\n"
   " -- natural with the source order (date desc, id) as tie-breaker.\n"
   " with matching as materialized(select y as doc from erp.sales_payments y where y.sale_id=ident and(ps is null or y.status=ps)\n"
   "   and(pq='' or strpos(lower(concat_ws(' ',y.payment_number,y.reference_number,y.notes,(select ca.cash_account_name from erp.cash_accounts ca where ca.id=y.cash_account_id))),lower(pq))>0)),\n"
   "  keyed as(select mt.doc,case when pord<>'SOURCE'then(select coalesce(string_agg(case when nat.part[1]~'^[0-9]'then lpad(length(ltrim(nat.part[1],'0'))::text,10,'0')||ltrim(nat.part[1],'0')else lower(nat.part[1])end,''order by nat.pos),'')from regexp_matches((mt.doc).payment_number,'[0-9]+|[^0-9]+','g')with ordinality nat(part,pos))end label_key from matching mt),\n"
   "  ordered as materialized(select kd.doc,row_number()over(order by case when pord='LABEL_ASC'then kd.label_key end collate \"C\",case when pord='LABEL_DESC'then kd.label_key end collate \"C\" desc,(kd.doc).payment_date desc,(kd.doc).id)rn from keyed kd)\n"
   " select(select count(*)from matching),coalesce((select jsonb_agg(jsonb_build_object('id',(x.doc).id,'number',(x.doc).payment_number,'physical_at',(x.doc).payment_date,'amount',(x.doc).amount::text,'cash_account_id',(x.doc).cash_account_id,'cash_account_name',(select cash_account_name from erp.cash_accounts where id=(x.doc).cash_account_id),'method',(x.doc).payment_method,'reference',(x.doc).reference_number,'notes',(x.doc).notes,'status',(x.doc).status,'replaces_payment_id',(x.doc).replaces_payment_id) order by x.rn)\n"
   "  from(select * from ordered order by rn limit pn offset po)x),'[]') into pt,payments;\n"),
  ('cash_workspace 3/3',
   "  'payments',jsonb_build_object('rows',payments,'total',pt::text,'offset',po,'limit',pn,'next_offset',case when po+jsonb_array_length(payments)<pt then po+jsonb_array_length(payments) else null end),\n",
   "  'payments',jsonb_build_object('rows',payments,'total',pt::text,'offset',po,'limit',pn,'next_offset',case when po+jsonb_array_length(payments)<pt then po+jsonb_array_length(payments) else null end)\n"
   "   ||case when listed then jsonb_build_object('list',jsonb_build_object('q',pq,'status',ps,'order',pord))else'{}'::jsonb end,\n"),
 ),
 RETURNS:(
  ('return_workspace 1/3',
   "declare h erp.sales_headers;ident uuid;kind text;q text;off integer;n integer;total bigint;rows jsonb;\n",
   "declare h erp.sales_headers;ident uuid;kind text;q text;off integer;n integer;total bigint;rows jsonb;\n"
   " -- OW-09 (owner D17-16): for kind RETURNS, optional history_q (number, notes, SKU, lot, warehouse, line notes),\n"
   " -- history_status and history_order apply to the whole return history before the page is cut; the echo appears\n"
   " -- only when one of those keys is sent, so old calls keep their exact answer.\n"
   " hq text;hs text;ho text;listed boolean;too_large boolean;\n"),
  ('return_workspace 2/3',
   "  or exists(select 1 from jsonb_object_keys(p_query) k where k not in('sale_id','kind','q','offset','limit'))\n"
   "  or exists(select 1 from jsonb_each(p_query) e where e.key in('sale_id','kind','q') and jsonb_typeof(e.value)<>'string')\n"
   "  or exists(select 1 from jsonb_each(p_query) e where e.key in('offset','limit') and(jsonb_typeof(e.value)<>'number' or e.value::text!~'^[0-9]{1,7}$')) then raise exception 'CP7_SALES_RETURN_QUERY';end if;\n"
   " ident:=(p_query->>'sale_id')::uuid;kind:=p_query->>'kind';q:=btrim(coalesce(p_query->>'q',''));off:=coalesce((p_query->>'offset')::integer,0);n:=coalesce((p_query->>'limit')::integer,25);\n"
   " if ident is null or kind is null or kind not in('ALLOCATIONS','RETURNS','LOCATIONS') or off not between 0 and 1000000 or n not between 1 and 100 or length(q)>120 then raise exception 'CP7_SALES_RETURN_QUERY';end if;\n",
   "  or exists(select 1 from jsonb_object_keys(p_query) k where k not in('sale_id','kind','q','offset','limit','history_q','history_status','history_order'))\n"
   "  or exists(select 1 from jsonb_each(p_query) e where e.key in('sale_id','kind','q','history_q','history_order') and jsonb_typeof(e.value)<>'string')\n"
   "  or(p_query?'history_status' and jsonb_typeof(p_query->'history_status') not in('string','null'))\n"
   "  or exists(select 1 from jsonb_each(p_query) e where e.key in('offset','limit') and(jsonb_typeof(e.value)<>'number' or e.value::text!~'^[0-9]{1,7}$')) then raise exception 'CP7_SALES_RETURN_QUERY';end if;\n"
   " ident:=(p_query->>'sale_id')::uuid;kind:=p_query->>'kind';q:=btrim(coalesce(p_query->>'q',''));off:=coalesce((p_query->>'offset')::integer,0);n:=coalesce((p_query->>'limit')::integer,25);\n"
   " hq:=btrim(coalesce(p_query->>'history_q',''));hs:=p_query->>'history_status';ho:=coalesce(p_query->>'history_order','SOURCE');listed:=p_query?|array['history_q','history_status','history_order'];\n"
   " if ident is null or kind is null or kind not in('ALLOCATIONS','RETURNS','LOCATIONS') or off not between 0 and 1000000 or n not between 1 and 100 or length(q)>120\n"
   "  or listed and kind<>'RETURNS' or length(hq)>120 or(hs is not null and hs not in('DRAFT','POSTED','REVERSED'))or ho not in('SOURCE','LABEL_ASC','LABEL_DESC')then raise exception 'CP7_SALES_RETURN_QUERY';end if;\n"),
  ('return_workspace 3/3',
   "  if exists(select 1 from(select id from erp.sales_returns where sale_id=ident and(q='' or strpos(lower(return_number),lower(q))>0) order by physical_at desc,id limit n offset off)x where(select count(*) from erp.sales_return_items i where i.return_id=x.id)>100) then raise exception 'CP7_SALES_RETURN_DOCUMENT_TOO_LARGE';end if;\n"
   "  select count(*) into total from erp.sales_returns where sale_id=ident and(q='' or strpos(lower(return_number),lower(q))>0);\n"
   "  select coalesce(jsonb_agg(jsonb_build_object('id',x.id,'number',x.return_number,'physical_at',x.physical_at,'status',x.status,'notes',x.notes,'line_count',(select count(*)::text from erp.sales_return_items i where i.return_id=x.id),'items',\n"
   "   (select coalesce(jsonb_agg(jsonb_build_object('id',i.id,'allocation_id',i.sale_stock_allocation_id,'product_sku',p.sku,'lot_number',fl.lot_number,'location_id',i.location_id,'location_name',l.location_name,'qty_pcs',i.qty_pcs::text,'quality_grade',i.quality_grade,'refund_amount',i.refund_amount::text,'notes',i.notes) order by i.id),'[]') from erp.sales_return_items i join erp.products p on p.id=i.product_id join erp.fg_lots fl on fl.id=i.lot_id join erp.locations l on l.id=i.location_id where i.return_id=x.id)) order by x.physical_at desc,x.id),'[]') into rows\n"
   "  from(select * from erp.sales_returns where sale_id=ident and(q='' or strpos(lower(return_number),lower(q))>0) order by physical_at desc,id limit n offset off)x;\n"
   " end if;\n"
   " return jsonb_build_object('contract_version','cp7.sales-returns.v1','kind',kind,'sale_id',ident,'row_version',h.row_version::text,'review_token',cp7_sales.review_token(ident),'page',jsonb_build_object('rows',rows,'total',total::text,'offset',off,'limit',n,'next_offset',case when off+jsonb_array_length(rows)<total then off+jsonb_array_length(rows) else null end));\n",
   "  -- Count, order, size guard and page read the same matching history; the\n"
   "  -- label order is natural with the source order (physical_at desc, id) as tie-breaker.\n"
   "  with matching as materialized(select y as doc from erp.sales_returns y where y.sale_id=ident and(q='' or strpos(lower(y.return_number),lower(q))>0)\n"
   "    and(hs is null or y.status=hs)\n"
   "    and(hq='' or strpos(lower(concat_ws(' ',y.return_number,y.notes)),lower(hq))>0\n"
   "     or exists(select 1 from erp.sales_return_items si join erp.products sp on sp.id=si.product_id join erp.fg_lots sl on sl.id=si.lot_id join erp.locations sw on sw.id=si.location_id\n"
   "      where si.return_id=y.id and strpos(lower(concat_ws(' ',sp.sku,sl.lot_number,sw.location_name,si.notes)),lower(hq))>0))),\n"
   "   keyed as(select mt.doc,case when ho<>'SOURCE'then(select coalesce(string_agg(case when nat.part[1]~'^[0-9]'then lpad(length(ltrim(nat.part[1],'0'))::text,10,'0')||ltrim(nat.part[1],'0')else lower(nat.part[1])end,''order by nat.pos),'')from regexp_matches((mt.doc).return_number,'[0-9]+|[^0-9]+','g')with ordinality nat(part,pos))end label_key from matching mt),\n"
   "   ordered as materialized(select kd.doc,row_number()over(order by case when ho='LABEL_ASC'then kd.label_key end collate \"C\",case when ho='LABEL_DESC'then kd.label_key end collate \"C\" desc,(kd.doc).physical_at desc,(kd.doc).id)rn from keyed kd),\n"
   "   sliced as materialized(select * from ordered order by rn limit n offset off)\n"
   "  select(select count(*)from matching),coalesce((select bool_or((select count(*) from erp.sales_return_items i where i.return_id=(z.doc).id)>100)from sliced z),false),\n"
   "   coalesce((select jsonb_agg(jsonb_build_object('id',(x.doc).id,'number',(x.doc).return_number,'physical_at',(x.doc).physical_at,'status',(x.doc).status,'notes',(x.doc).notes,'line_count',(select count(*)::text from erp.sales_return_items i where i.return_id=(x.doc).id),'items',\n"
   "   (select coalesce(jsonb_agg(jsonb_build_object('id',i.id,'allocation_id',i.sale_stock_allocation_id,'product_sku',p.sku,'lot_number',fl.lot_number,'location_id',i.location_id,'location_name',l.location_name,'qty_pcs',i.qty_pcs::text,'quality_grade',i.quality_grade,'refund_amount',i.refund_amount::text,'notes',i.notes) order by i.id),'[]') from erp.sales_return_items i join erp.products p on p.id=i.product_id join erp.fg_lots fl on fl.id=i.lot_id join erp.locations l on l.id=i.location_id where i.return_id=(x.doc).id)) order by x.rn)from sliced x),'[]')\n"
   "  into total,too_large,rows;\n"
   "  if too_large then raise exception 'CP7_SALES_RETURN_DOCUMENT_TOO_LARGE';end if;\n"
   " end if;\n"
   " return jsonb_build_object('contract_version','cp7.sales-returns.v1','kind',kind,'sale_id',ident,'row_version',h.row_version::text,'review_token',cp7_sales.review_token(ident),'page',jsonb_build_object('rows',rows,'total',total::text,'offset',off,'limit',n,'next_offset',case when off+jsonb_array_length(rows)<total then off+jsonb_array_length(rows) else null end)\n"
   "  ||case when listed then jsonb_build_object('list',jsonb_build_object('q',hq,'status',hs,'order',ho))else'{}'::jsonb end);\n"),
 ),
 NOTES:(
  ('note_workspace 1/5',
   "declare a jsonb;w jsonb;rows jsonb;total bigint;n integer;off integer;contractor uuid;ident uuid;q text;\n",
   "declare a jsonb;w jsonb;rows jsonb;total bigint;n integer;off integer;contractor uuid;ident uuid;q text;\n"
   " -- OW-09 (owner D17-16): for section NOTES, optional status and order apply to the whole matching note list\n"
   " -- before the page is cut; the echo appears only when one of those keys is sent, so old calls keep their exact answer.\n"
   " note_status text;note_order text;listed boolean;\n"),
  ('note_workspace 2/5',
   "  or exists(select 1 from jsonb_object_keys(p_query) k where k not in('q','contractor_id','id','limit','offset'))\n"
   "  or exists(select 1 from jsonb_each(p_query) e where e.key in('q','contractor_id','id') and jsonb_typeof(e.value) not in('string','null'))\n",
   "  or exists(select 1 from jsonb_object_keys(p_query) k where k not in('q','contractor_id','id','limit','offset','status','order'))\n"
   "  or exists(select 1 from jsonb_each(p_query) e where e.key in('q','contractor_id','id','status') and jsonb_typeof(e.value) not in('string','null'))\n"
   "  or(p_query?'order' and jsonb_typeof(p_query->'order')<>'string')\n"),
  ('note_workspace 3/5',
   " if length(q)>120 or n not between 1 and 100 or off not between 0 and 1000000 or (ident is not null and p_section<>'NOTES') or(p_section='PAYROLLS' and contractor is null) then raise exception 'CP7_NOTA_QUERY';end if;\n",
   " note_status:=p_query->>'status';note_order:=coalesce(p_query->>'order','SOURCE');listed:=p_query?|array['status','order'];\n"
   " if length(q)>120 or n not between 1 and 100 or off not between 0 and 1000000 or (ident is not null and p_section<>'NOTES') or(p_section='PAYROLLS' and contractor is null)\n"
   "  or listed and p_section<>'NOTES' or(note_status is not null and note_status not in('DRAFT','POSTED','VOID'))or note_order not in('SOURCE','LABEL_ASC','LABEL_DESC') then raise exception 'CP7_NOTA_QUERY';end if;\n"),
  ('note_workspace 4/5',
   "   with filtered as materialized(select h.* from cp7_payroll.notes h join erp.contractors c on c.id=h.contractor_id\n"
   "    where (contractor is null or h.contractor_id=contractor) and(ident is null or h.id=ident) and(q='' or strpos(lower(concat_ws(' ',h.note_number,c.contractor_name,h.notes)),lower(q))>0)),\n"
   "   page as(select * from filtered order by created_at desc,id limit n offset off)\n"
   "   select(select count(*) from filtered),coalesce(jsonb_agg(cp7_payroll.note_document(page::cp7_payroll.notes,(a->>'financial')::boolean) order by created_at desc,id),'[]') into total,rows from page;\n",
   "   -- Count, order and page read the same matching notes; the label order is\n"
   "   -- natural with the source order (created_at desc, id) as tie-breaker.\n"
   "   with filtered as materialized(select h as doc from cp7_payroll.notes h join erp.contractors c on c.id=h.contractor_id\n"
   "    where (contractor is null or h.contractor_id=contractor) and(ident is null or h.id=ident) and(q='' or strpos(lower(concat_ws(' ',h.note_number,c.contractor_name,h.notes)),lower(q))>0)\n"
   "     and(note_status is null or h.status=note_status)),\n"
   "   keyed as(select ft.doc,case when note_order<>'SOURCE'then(select coalesce(string_agg(case when nat.part[1]~'^[0-9]'then lpad(length(ltrim(nat.part[1],'0'))::text,10,'0')||ltrim(nat.part[1],'0')else lower(nat.part[1])end,''order by nat.pos),'')from regexp_matches((ft.doc).note_number,'[0-9]+|[^0-9]+','g')with ordinality nat(part,pos))end label_key from filtered ft),\n"
   "   ordered as materialized(select kd.doc,row_number()over(order by case when note_order='LABEL_ASC'then kd.label_key end collate \"C\",case when note_order='LABEL_DESC'then kd.label_key end collate \"C\" desc,(kd.doc).created_at desc,(kd.doc).id)rn from keyed kd),\n"
   "   page as(select * from ordered order by rn limit n offset off)\n"
   "   select(select count(*) from filtered),coalesce(jsonb_agg(cp7_payroll.note_document(pg.doc,(a->>'financial')::boolean) order by pg.rn),'[]') into total,rows from page pg;\n"),
  ('note_workspace 5/5',
   "  w:=jsonb_build_object('page',jsonb_build_object('rows',rows,'total',total::text,'offset',off,'limit',n,'next_offset',case when off+jsonb_array_length(rows)<total then off+jsonb_array_length(rows) else null end));\n",
   "  w:=jsonb_build_object('page',jsonb_build_object('rows',rows,'total',total::text,'offset',off,'limit',n,'next_offset',case when off+jsonb_array_length(rows)<total then off+jsonb_array_length(rows) else null end)\n"
   "   ||case when listed then jsonb_build_object('list',jsonb_build_object('q',q,'status',note_status,'order',note_order))else'{}'::jsonb end);\n"),
 ),
 FG_DOCUMENTS:(
  ('adjust_workspace 1/3',
   "begin\n"
   " a:=cp7_fg.adjust_access();\n"
   " if jsonb_typeof(p_query) is distinct from 'object' or exists(select 1 from jsonb_object_keys(p_query) k where k not in('q','limit','offset','adjustment_id'))\n"
   "  or exists(select 1 from jsonb_each(p_query) e where e.key in('q','adjustment_id') and jsonb_typeof(e.value) not in('string','null'))\n",
   " -- OW-09 (owner D17-16): optional status and order apply to the whole matching document list before the page\n"
   " -- is cut; the echo appears only when one of those keys is sent, so old calls keep their exact answer.\n"
   " doc_status text;doc_order text;listed boolean;\n"
   "begin\n"
   " a:=cp7_fg.adjust_access();\n"
   " if jsonb_typeof(p_query) is distinct from 'object' or exists(select 1 from jsonb_object_keys(p_query) k where k not in('q','limit','offset','adjustment_id','status','order'))\n"
   "  or exists(select 1 from jsonb_each(p_query) e where e.key in('q','adjustment_id','status') and jsonb_typeof(e.value) not in('string','null'))\n"
   "  or(p_query ? 'order' and jsonb_typeof(p_query->'order')<>'string')\n"),
  ('adjust_workspace 2/3',
   " if length(q)>120 or n not between 1 and 100 or off not between 0 and 1000000 then raise exception 'CP7_FG_ADJUST_QUERY';end if;\n"
   " select count(*) into total from erp.fg_adjustments doc where q='' or strpos(lower(doc.adjustment_number),lower(q))>0;\n"
   " select coalesce(jsonb_agg(cp7_fg.adjust_header(x) order by x.physical_at desc,x.id),'[]') into rows\n"
   " from(select * from erp.fg_adjustments doc where q='' or strpos(lower(doc.adjustment_number),lower(q))>0 order by physical_at desc,id limit n offset off)x;\n",
   " doc_status:=p_query->>'status';doc_order:=coalesce(p_query->>'order','SOURCE');listed:=p_query?|array['status','order'];\n"
   " if length(q)>120 or n not between 1 and 100 or off not between 0 and 1000000\n"
   "  or(doc_status is not null and doc_status not in('DRAFT','POSTED','REVERSED'))or doc_order not in('SOURCE','LABEL_ASC','LABEL_DESC') then raise exception 'CP7_FG_ADJUST_QUERY';end if;\n"
   " -- Count, order and page read the same matching documents; the label order is\n"
   " -- natural with the source order (physical_at desc, id) as tie-breaker.\n"
   " with matching as materialized(select doc from erp.fg_adjustments doc where(q='' or strpos(lower(doc.adjustment_number),lower(q))>0)and(doc_status is null or doc.status=doc_status)),\n"
   "  keyed as(select mt.doc,case when doc_order<>'SOURCE'then(select coalesce(string_agg(case when nat.part[1]~'^[0-9]'then lpad(length(ltrim(nat.part[1],'0'))::text,10,'0')||ltrim(nat.part[1],'0')else lower(nat.part[1])end,''order by nat.pos),'')from regexp_matches((mt.doc).adjustment_number,'[0-9]+|[^0-9]+','g')with ordinality nat(part,pos))end label_key from matching mt),\n"
   "  ordered as materialized(select kd.doc,row_number()over(order by case when doc_order='LABEL_ASC'then kd.label_key end collate \"C\",case when doc_order='LABEL_DESC'then kd.label_key end collate \"C\" desc,(kd.doc).physical_at desc,(kd.doc).id)rn from keyed kd)\n"
   " select(select count(*)from matching),coalesce((select jsonb_agg(cp7_fg.adjust_header(x.doc) order by x.rn)from(select * from ordered order by rn limit n offset off)x),'[]')\n"
   " into total,rows;\n"),
  ('adjust_workspace 3/3',
   "  'page',jsonb_build_object('rows',rows,'total',total::text,'offset',off,'limit',n,'next_offset',case when off+jsonb_array_length(rows)<total then off+jsonb_array_length(rows) else null end),'detail',detail);\n",
   "  'page',jsonb_build_object('rows',rows,'total',total::text,'offset',off,'limit',n,'next_offset',case when off+jsonb_array_length(rows)<total then off+jsonb_array_length(rows) else null end)\n"
   "   ||case when listed then jsonb_build_object('list',jsonb_build_object('q',q,'status',doc_status,'order',doc_order))else'{}'::jsonb end,'detail',detail);\n"),
 ),
 FG_CARD:(
  ('corrected_ledger 1/6',
   "begin\n"
   " if jsonb_typeof(p_query)is distinct from 'object'or exists(select 1 from jsonb_object_keys(p_query)k where k not in('purpose','product_id','lot_id','location_id','quality_grade','q','from','to','offset','limit'))\n",
   " -- OW-09 (owner D17-16): optional movement_type and order apply to the whole searched movement list before the\n"
   " -- page is cut. Balances keep the complete chronological prefix. The echo (with the position's movement types)\n"
   " -- appears only when one of those keys is sent, so old calls keep their exact answer.\n"
   " move_type text;move_order text;listed boolean;move_types jsonb;\n"
   "begin\n"
   " if jsonb_typeof(p_query)is distinct from 'object'or exists(select 1 from jsonb_object_keys(p_query)k where k not in('purpose','product_id','lot_id','location_id','quality_grade','q','from','to','offset','limit','movement_type','order'))\n"
   "  or(p_query ? 'order'and jsonb_typeof(p_query->'order')<>'string')\n"),
  ('corrected_ledger 2/6',
   " from_at:=(p_query->>'from')::timestamptz;to_at:=(p_query->>'to')::timestamptz;\n",
   " from_at:=(p_query->>'from')::timestamptz;to_at:=(p_query->>'to')::timestamptz;\n"
   " move_type:=p_query->>'movement_type';move_order:=coalesce(p_query->>'order','SOURCE');listed:=p_query?|array['movement_type','order'];\n"
   " if(move_type is not null and move_type!~'^[A-Z][A-Z_]{0,39}$')or move_order not in('SOURCE','LABEL_ASC','LABEL_DESC')then raise exception 'CP7_FG_QUERY';end if;\n"),
  ('corrected_ledger 3/6',
   " if a->'can_value'='true'::jsonb then cost:=cp7_fg.lot_value(lid,1);end if;\n",
   " if a->'can_value'='true'::jsonb then cost:=cp7_fg.lot_value(lid,1);end if;\n"
   " -- Count, order and page read the same filtered movements; the label order is\n"
   " -- natural with the chronological order (physical, recorded, id) as tie-breaker.\n"),
  ('corrected_ledger 4/6',
   "  and(q=''or strpos(lower(concat_ws(' ',r->>'source_type',r->>'source_id',r->>'customer_name',r->>'notes',r->>'movement_type',r->>'commercial_sku_at_transaction')),lower(q))>0)),\n"
   " page as(select r from filtered order by(r->>'physical_at')::timestamptz,(r->>'recorded_at')::timestamptz,r->>'id'limit n offset off)\n",
   "  and(q=''or strpos(lower(concat_ws(' ',r->>'source_type',r->>'source_id',r->>'customer_name',r->>'notes',r->>'movement_type',r->>'commercial_sku_at_transaction')),lower(q))>0)\n"
   "  and(move_type is null or r->>'movement_type'=move_type)),\n"
   " keyed as(select fr.r,case when move_order<>'SOURCE'then(select coalesce(string_agg(case when nat.part[1]~'^[0-9]'then lpad(length(ltrim(nat.part[1],'0'))::text,10,'0')||ltrim(nat.part[1],'0')else lower(nat.part[1])end,''order by nat.pos),'')from regexp_matches(concat(fr.r->>'commercial_sku_at_transaction',' ',coalesce(fr.r->>'customer_name',''),' ',fr.r->>'movement_type'),'[0-9]+|[^0-9]+','g')with ordinality nat(part,pos))end label_key from filtered fr),\n"
   " ordered as materialized(select kd.r,row_number()over(order by case when move_order='LABEL_ASC'then kd.label_key end collate \"C\",case when move_order='LABEL_DESC'then kd.label_key end collate \"C\" desc,(kd.r->>'physical_at')::timestamptz,(kd.r->>'recorded_at')::timestamptz,kd.r->>'id')rn from keyed kd),\n"
   " page as(select r,rn from ordered order by rn limit n offset off)\n"),
  ('corrected_ledger 5/6',
   "   order by(r->>'physical_at')::timestamptz,(r->>'recorded_at')::timestamptz,r->>'id'),'[]'),\n",
   "   order by rn),'[]'),\n"),
  ('corrected_ledger 6/6',
   "   from complete where to_at is null or(r->>'physical_at')::timestamptz<to_at)\n"
   " into total,rows,balances from page;\n"
   " return jsonb_build_object('contract_version','cp7.fg-ledger.v2','purpose',purpose,'read_at',statement_timestamp(),'knowledge','CURRENT','financial_captured',a->'can_value',\n"
   "  'position',header,'balances',balances,'balance_basis','COMPLETE_CHRONOLOGICAL_PREFIX_BEFORE_SEARCH_AND_PAGE',\n"
   "  'page',jsonb_build_object('rows',rows,'total',total::text,'offset',off,'limit',n,'next_offset',case when off+jsonb_array_length(rows)<total then off+jsonb_array_length(rows)else null end));\n",
   "   from complete where to_at is null or(r->>'physical_at')::timestamptz<to_at),\n"
   "  (select coalesce(jsonb_agg(kinds.movement_type order by kinds.movement_type collate \"C\"),'[]')from(select distinct r->>'movement_type' movement_type from complete)kinds)\n"
   " into total,rows,balances,move_types from page;\n"
   " return jsonb_build_object('contract_version','cp7.fg-ledger.v2','purpose',purpose,'read_at',statement_timestamp(),'knowledge','CURRENT','financial_captured',a->'can_value',\n"
   "  'position',header,'balances',balances,'balance_basis','COMPLETE_CHRONOLOGICAL_PREFIX_BEFORE_SEARCH_AND_PAGE',\n"
   "  'page',jsonb_build_object('rows',rows,'total',total::text,'offset',off,'limit',n,'next_offset',case when off+jsonb_array_length(rows)<total then off+jsonb_array_length(rows)else null end)\n"
   "   ||case when listed then jsonb_build_object('list',jsonb_build_object('q',q,'movement_type',move_type,'order',move_order,'movement_types',move_types))else'{}'::jsonb end);\n"),
 ),
 COUNTS:(
  ('count_workspace 1/3',
   "begin\n"
   " a:=cp7_material.access_now();\n"
   " if jsonb_typeof(p_query) is distinct from 'object' or exists(select 1 from jsonb_object_keys(p_query) k where k not in('q','limit','offset','adjustment_id'))\n"
   "  or exists(select 1 from jsonb_each(p_query) e where e.key in('q','adjustment_id') and jsonb_typeof(e.value) not in('string','null'))\n",
   " -- OW-09 (owner D17-16): optional status and order apply to the whole matching document list before the page\n"
   " -- is cut; the echo appears only when one of those keys is sent, so old calls keep their exact answer.\n"
   " doc_status text;doc_order text;listed boolean;\n"
   "begin\n"
   " a:=cp7_material.access_now();\n"
   " if jsonb_typeof(p_query) is distinct from 'object' or exists(select 1 from jsonb_object_keys(p_query) k where k not in('q','limit','offset','adjustment_id','status','order'))\n"
   "  or exists(select 1 from jsonb_each(p_query) e where e.key in('q','adjustment_id','status') and jsonb_typeof(e.value) not in('string','null'))\n"
   "  or(p_query ? 'order' and jsonb_typeof(p_query->'order')<>'string')\n"),
  ('count_workspace 2/3',
   " if length(q)>120 or n not between 1 and 100 or off not between 0 and 1000000 then raise exception 'CP7_COUNT_QUERY';end if;\n"
   " select count(*) into total from erp.material_adjustments doc where q='' or strpos(lower(doc.adjustment_number),lower(q))>0;\n"
   " select coalesce(jsonb_agg(cp7_material.count_header(x) order by x.physical_at desc,x.id),'[]') into rows\n"
   " from (select * from erp.material_adjustments doc where q='' or strpos(lower(doc.adjustment_number),lower(q))>0 order by physical_at desc,id limit n offset off) x;\n",
   " doc_status:=p_query->>'status';doc_order:=coalesce(p_query->>'order','SOURCE');listed:=p_query?|array['status','order'];\n"
   " if length(q)>120 or n not between 1 and 100 or off not between 0 and 1000000\n"
   "  or(doc_status is not null and doc_status not in('DRAFT','POSTED','REVERSED'))or doc_order not in('SOURCE','LABEL_ASC','LABEL_DESC') then raise exception 'CP7_COUNT_QUERY';end if;\n"
   " -- Count, order and page read the same matching documents; the label order is\n"
   " -- natural with the source order (physical_at desc, id) as tie-breaker.\n"
   " with matching as materialized(select doc from erp.material_adjustments doc where(q='' or strpos(lower(doc.adjustment_number),lower(q))>0)and(doc_status is null or doc.status=doc_status)),\n"
   "  keyed as(select mt.doc,case when doc_order<>'SOURCE'then(select coalesce(string_agg(case when nat.part[1]~'^[0-9]'then lpad(length(ltrim(nat.part[1],'0'))::text,10,'0')||ltrim(nat.part[1],'0')else lower(nat.part[1])end,''order by nat.pos),'')from regexp_matches((mt.doc).adjustment_number,'[0-9]+|[^0-9]+','g')with ordinality nat(part,pos))end label_key from matching mt),\n"
   "  ordered as materialized(select kd.doc,row_number()over(order by case when doc_order='LABEL_ASC'then kd.label_key end collate \"C\",case when doc_order='LABEL_DESC'then kd.label_key end collate \"C\" desc,(kd.doc).physical_at desc,(kd.doc).id)rn from keyed kd)\n"
   " select(select count(*)from matching),coalesce((select jsonb_agg(cp7_material.count_header(x.doc) order by x.rn)from(select * from ordered order by rn limit n offset off)x),'[]')\n"
   " into total,rows;\n"),
  ('count_workspace 3/3',
   "  'page',jsonb_build_object('rows',rows,'total',total::text,'offset',off,'limit',n,'next_offset',case when off+jsonb_array_length(rows)<total then off+jsonb_array_length(rows) else null end),'detail',detail);\n",
   "  'page',jsonb_build_object('rows',rows,'total',total::text,'offset',off,'limit',n,'next_offset',case when off+jsonb_array_length(rows)<total then off+jsonb_array_length(rows) else null end)\n"
   "   ||case when listed then jsonb_build_object('list',jsonb_build_object('q',q,'status',doc_status,'order',doc_order))else'{}'::jsonb end,'detail',detail);\n"),
 ),
 ACCESSORY:(
  ('accessory declare',
   " v_result jsonb;v_document jsonb;v_material_ids jsonb:=coalesce(p_filters->'material_ids','[]'::jsonb);\n",
   " v_result jsonb;v_document jsonb;v_material_ids jsonb:=coalesce(p_filters->'material_ids','[]'::jsonb);\n"
   " -- OW-09 (owner D17-16): optional history_status, history_order, history_offset and history_limit apply to the\n"
   " -- whole matching note history before the page is cut; history_count follows the same filter. Only when one of\n"
   " -- those keys is sent does the answer carry history_page (offset, limit, next_offset and the list echo), so an\n"
   " -- old call keeps its exact answer.\n"
   " v_listed boolean:=p_filters?|array['history_status','history_order','history_offset','history_limit'];\n"
   " v_history_status text;v_history_order text:='SOURCE';v_history_offset integer:=0;v_history_limit integer:=50;\n"),
  ('accessory keys',
   "'material_query','material_ids'],'accessory workspace filters');",
   "'material_query','material_ids','history_status','history_order','history_offset','history_limit'],'accessory workspace filters');"),
  ('accessory list check',
   " if p_filters?'material_ids' and (jsonb_typeof(p_filters->'material_ids')<>'array' or jsonb_array_length(p_filters->'material_ids')>100) then raise exception 'Daftar aksesori tidak valid';end if;\n",
   " if p_filters?'material_ids' and (jsonb_typeof(p_filters->'material_ids')<>'array' or jsonb_array_length(p_filters->'material_ids')>100) then raise exception 'Daftar aksesori tidak valid';end if;\n"
   " if v_listed then\n"
   "  if (p_filters?'history_status' and jsonb_typeof(p_filters->'history_status') not in('string','null'))\n"
   "   or (p_filters?'history_order' and jsonb_typeof(p_filters->'history_order')<>'string')\n"
   "   or (p_filters?'history_offset' and (jsonb_typeof(p_filters->'history_offset')<>'number' or (p_filters->>'history_offset')!~'^[0-9]{1,7}$'))\n"
   "   or (p_filters?'history_limit' and (jsonb_typeof(p_filters->'history_limit')<>'number' or (p_filters->>'history_limit')!~'^[0-9]{1,2}$')) then raise exception 'Daftar nota tidak valid';end if;\n"
   "  v_history_status:=p_filters->>'history_status';v_history_order:=coalesce(p_filters->>'history_order','SOURCE');\n"
   "  v_history_offset:=coalesce((p_filters->>'history_offset')::integer,0);v_history_limit:=coalesce((p_filters->>'history_limit')::integer,50);\n"
   "  if (v_history_status is not null and v_history_status not in('DRAFT','POSTED','REVERSED')) or v_history_order not in('SOURCE','LABEL_ASC','LABEL_DESC')\n"
   "   or v_history_offset>1000000 or v_history_limit not between 1 and 50 then raise exception 'Daftar nota tidak valid';end if;\n"
   " end if;\n"),
  ('accessory status filter',
   "  where (v_query='' or strpos(lower(concat_ws(' ',h.issue_number,c.contractor_name)),v_query)>0)\n",
   "  where (v_query='' or strpos(lower(concat_ws(' ',h.issue_number,c.contractor_name)),v_query)>0)\n"
   "   and (v_history_status is null or h.status=v_history_status)\n"),
  ('accessory order',
   " ), choices as (\n",
   " ), keyed as (\n"
   "  -- Count and page read the same matching notes; the label order is natural with the source order\n"
   "  -- (business date desc, id) as tie-breaker.\n"
   "  select hk.*,case when v_history_order<>'SOURCE' then "+NATURAL+" end label_key from history hk\n"
   " ), ordered as (\n"
   "  select kd.*,row_number() over(order by case when v_history_order='LABEL_ASC' then kd.label_key end collate \"C\",\n"
   "   case when v_history_order='LABEL_DESC' then kd.label_key end collate \"C\" desc,kd.date desc,kd.id) rn from keyed kd\n"
   " ), choices as (\n"),
  ('accessory page',
   "  'history',coalesce((select jsonb_agg(to_jsonb(x) order by x.date desc,x.id) from(select * from history order by date desc,id limit 50)x),'[]'::jsonb),\n",
   "  'history',case when v_listed then coalesce((select jsonb_agg(to_jsonb(x)-'label_key'-'rn' order by x.rn)\n"
   "    from(select * from ordered order by rn limit v_history_limit offset v_history_offset)x),'[]'::jsonb)\n"
   "   else coalesce((select jsonb_agg(to_jsonb(x) order by x.date desc,x.id) from(select * from history order by date desc,id limit 50)x),'[]'::jsonb) end,\n"),
  ('accessory echo',
   " ) into v_result;\n return v_result;\n",
   " ) into v_result;\n"
   " if v_listed then\n"
   "  v_result:=v_result||jsonb_build_object('history_page',jsonb_build_object('offset',v_history_offset,'limit',v_history_limit,\n"
   "   'next_offset',case when v_history_offset+jsonb_array_length(v_result->'history')<(v_result->>'history_count')::bigint\n"
   "    then v_history_offset+jsonb_array_length(v_result->'history') end,\n"
   "   'list',jsonb_build_object('q',btrim(coalesce(p_filters->>'query','')),'status',v_history_status,'order',v_history_order)));\n"
   " end if;\n"
   " return v_result;\n"),
 ),
}


def once(body,old,new,label):
    if body.count(old)!=1:
        raise ValueError('OW09_PREDECESSOR_SOURCE_CHANGED: '+label)
    return body.replace(old,new,1)


def patched(originals):
    if set(originals)!=set(SIGNATURES)or set(STEPS)!=set(SIGNATURES):raise ValueError('OW09_NATIVE_DELTA_SET_CHANGED')
    result={}
    for sig in SIGNATURES:
        body=originals[sig]
        if MARKER in body or 'OW-09' in body:raise ValueError('OW09_ALREADY_PATCHED: '+sig)
        for label,old,new in STEPS[sig]:body=once(body,old,new,label)
        result[sig]=body
    return result
