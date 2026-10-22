-- Recorded-period comparison and cash ledger projection. No financial writes.
-- OW-09 (owner D17-16): optional entry_q/entry_status/entry_order filter and
-- order the cash entries over the whole period before the page is cut; the
-- echo and the matching sums appear only when one of those keys is sent, so
-- an old query keeps a byte-identical answer.
grant select on erp.cash_accounts,erp.account_daily_balances,erp.journal_entries,erp.journal_lines to cp7_finance_read;
grant execute on function erp.account_id(text) to cp7_finance_read;

create function cp7_finance.analysis(p_query jsonb) returns jsonb
language plpgsql stable security invoker set search_path='' set TimeZone='UTC' set jit=off as $$
declare f date;t date;a date;bf date;bt date;off integer;n integer;current_report jsonb;baseline_report jsonb;
 current_perf jsonb;baseline_perf jsonb;revenue numeric;baseline_revenue numeric;growth numeric; margin_delta numeric;
 cash_ids uuid[];opening numeric;closing numeric;debits numeric;credits numeric;total bigint;rows jsonb;
 eq text;es text;eo text;listed boolean;match_debit numeric;match_credit numeric;
begin
 perform cp7_finance.access_now();
 if jsonb_typeof(p_query) is distinct from 'object' or not p_query ?& array['from','to','as_of','compare_from','compare_to']
  or exists(select 1 from jsonb_object_keys(p_query)k where k not in('from','to','as_of','compare_from','compare_to','offset','limit','entry_q','entry_status','entry_order'))
  or exists(select 1 from jsonb_each(p_query)e where e.key in('entry_q','entry_order') and jsonb_typeof(e.value)<>'string')
  or(p_query?'entry_status' and jsonb_typeof(p_query->'entry_status') not in('string','null'))
  or exists(select 1 from jsonb_each(p_query)e where e.key in('from','to','as_of','compare_from','compare_to') and(jsonb_typeof(e.value)<>'string' or(e.value#>>'{}')!~'^[0-9]{4}-[0-9]{2}-[0-9]{2}$'))
  or exists(select 1 from jsonb_each(p_query)e where e.key in('offset','limit') and(jsonb_typeof(e.value)<>'number' or e.value::text!~'^[0-9]{1,7}$')) then raise exception 'CP7_FINANCE_ANALYSIS_QUERY';end if;
 f:=(p_query->>'from')::date;t:=(p_query->>'to')::date;a:=(p_query->>'as_of')::date;bf:=(p_query->>'compare_from')::date;bt:=(p_query->>'compare_to')::date;
 off:=coalesce((p_query->>'offset')::integer,0);n:=coalesce((p_query->>'limit')::integer,25);
 eq:=btrim(coalesce(p_query->>'entry_q',''));es:=p_query->>'entry_status';eo:=coalesce(p_query->>'entry_order','SOURCE');listed:=p_query?|array['entry_q','entry_status','entry_order'];
 if length(eq)>120 or(es is not null and es not in('POSTED','REVERSED'))or eo not in('SOURCE','LABEL_ASC','LABEL_DESC')then raise exception 'CP7_FINANCE_ANALYSIS_QUERY';end if;
 if f>t or t>a or bf>bt or bt>=f or a>(statement_timestamp() at time zone 'Asia/Jakarta')::date or off not between 0 and 1000000 or n not between 1 and 100 then raise exception 'CP7_FINANCE_ANALYSIS_QUERY';end if;
 -- Both native reports and the ledger below share this stable statement's
 -- snapshot. Baseline readiness belongs to its own cutoff, not today's one.
 current_report:=erp.get_owner_financial_snapshot_v2(f,t,a);
 baseline_report:=erp.get_owner_financial_snapshot_v2(bf,bt,bt);
 if current_report is null or baseline_report is null or octet_length(current_report::text)+octet_length(baseline_report::text)>2000000 then raise exception 'CP7_FINANCE_REPORT_INCOMPLETE';end if;
 current_perf:=current_report->'performance';baseline_perf:=baseline_report->'performance';
 revenue:=(current_perf->>'sales_revenue_gl')::numeric;baseline_revenue:=(baseline_perf->>'sales_revenue_gl')::numeric;
 -- Growth needs a positive base: a net-negative baseline (returns above sales)
 -- would invert the sign. Margin points need positive revenue on both sides.
 growth:=case when baseline_revenue>0 then round((revenue-baseline_revenue)/baseline_revenue*100,4)end;
 -- Aggregate original operands, not rounded row margins or averaged ratios.
 margin_delta:=case when revenue>0 and baseline_revenue>0 then round(((current_perf->>'gross_profit')::numeric/revenue-(baseline_perf->>'gross_profit')::numeric/baseline_revenue)*100,4)end;
 select array_agg(x.id order by x.id) into cash_ids from(select coa_account_id id from erp.cash_accounts union select erp.account_id('CASH'))x;
 select coalesce(sum(b.debit_total-b.credit_total)filter(where b.balance_date<f),0),coalesce(sum(b.debit_total-b.credit_total),0)
 into opening,closing from erp.account_daily_balances b where b.account_id=any(cash_ids) and b.balance_date<=t;
 select coalesce(sum(l.debit),0),coalesce(sum(l.credit),0)
 into debits,credits from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id
 where j.status in('POSTED','REVERSED') and j.transaction_date between f and t and l.account_id=any(cash_ids);
 -- Count, matching sums, order and page all read the same matching set. The
 -- label order is natural (digit runs by value) with the source order and the
 -- unique journal id as tie-breakers.
 with entries as materialized(
  select j.id,j.journal_number,j.source_type,j.source_id,j.reversal_of_id,j.status,j.economic_date,j.transaction_date,j.posting_at,
   sum(l.debit)debit,sum(l.credit)credit,sum(l.debit-l.credit)net
  from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id
  where j.status in('POSTED','REVERSED') and j.transaction_date between f and t and l.account_id=any(cash_ids)
  group by j.id),
 matching as materialized(select e.* from entries e where(es is null or e.status=es)
  and(eq='' or strpos(lower(concat_ws(' ',e.journal_number,e.source_type,e.source_id::text,e.economic_date::text,e.transaction_date::text)),lower(eq))>0)),
 keyed as(select m.*,case when eo<>'SOURCE'then(select coalesce(string_agg(case when nat.part[1]~'^[0-9]'then lpad(length(ltrim(nat.part[1],'0'))::text,10,'0')||ltrim(nat.part[1],'0')else lower(nat.part[1])end,''order by nat.pos),'')
   from regexp_matches(m.journal_number,'[0-9]+|[^0-9]+','g')with ordinality nat(part,pos))end label_key from matching m),
 ordered as materialized(select kd.*,row_number()over(order by case when eo='LABEL_ASC'then kd.label_key end collate "C",case when eo='LABEL_DESC'then kd.label_key end collate "C" desc,
   kd.transaction_date,kd.posting_at,kd.id)rn from keyed kd)
 select(select count(*)from matching),(select coalesce(sum(debit),0)from matching),(select coalesce(sum(credit),0)from matching),
  coalesce((select jsonb_agg(jsonb_build_object('id',x.id,'journal_number',x.journal_number,'source_type',x.source_type,'source_id',x.source_id,'reversal_of_id',x.reversal_of_id,
   'status',x.status,'economic_date',x.economic_date,'transaction_date',x.transaction_date,'posting_at',x.posting_at,'debit',x.debit::text,'credit',x.credit::text,'net',x.net::text)order by x.rn)
   from(select * from ordered order by rn limit n offset off)x),'[]')
 into total,match_debit,match_credit,rows;
 return jsonb_build_object('contract_version','cp7.finance-analysis.v1','captured_at',statement_timestamp(),
  'knowledge_basis','CURRENT_RECORDED_KNOWLEDGE','historical_knowledge','NOT_RECONSTRUCTED',
  'dates',jsonb_build_object('from',f,'to',t,'as_of',a,'compare_from',bf,'compare_to',bt),
  'comparison',jsonb_build_object('basis','NATIVE_OWNER_REPORT_OPERANDS','formula_version','GROWTH_POSITIVE_BASE_AND_GROSS_MARGIN_PP_V2','rounding_scale',4,
   'current',cp7_finance.exact_numbers(current_report),'baseline',cp7_finance.exact_numbers(baseline_report),
   'revenue_growth_pct',growth::text,'gross_margin_change_pp',margin_delta::text),
  'cash',jsonb_build_object('basis','GL_TRANSACTION_DATE_ALL_CONFIGURED_CASH_COA','account_scope','DISTINCT_COA_INCLUDING_INACTIVE_CASH_ACCOUNTS_AND_CASH_MAPPING',
   'opening',opening::text,'closing',closing::text,'debit',debits::text,'credit',credits::text,'net_change',(closing-opening)::text,
   'ledger_net',(debits-credits)::text,'source_difference',(closing-opening-debits+credits)::text,'reconciled',closing-opening=debits-credits,
   'entries',jsonb_build_object('rows',rows,'total',total::text,'offset',off,'limit',n,'next_offset',case when off+jsonb_array_length(rows)<total then off+jsonb_array_length(rows)else null end)
    ||case when listed then jsonb_build_object('list',jsonb_build_object('q',eq,'status',es,'order',eo),
     'sums',jsonb_build_object('debit',match_debit::text,'credit',match_credit::text,'net',(match_debit-match_credit)::text))else'{}'::jsonb end));
end $$;
create function public.erp_cp7_get_finance_analysis_v1(p_query jsonb) returns jsonb
language sql stable security definer set search_path='' as $$select cp7_finance.analysis(p_query)$$;
alter function cp7_finance.analysis(jsonb) owner to cp7_finance_read;
grant create on schema public to cp7_finance_read;
alter function public.erp_cp7_get_finance_analysis_v1(jsonb) owner to cp7_finance_read;
revoke create on schema public from cp7_finance_read;
revoke all on function cp7_finance.analysis(jsonb),public.erp_cp7_get_finance_analysis_v1(jsonb) from public,anon,authenticated,service_role,cp7_capture;
grant execute on function public.erp_cp7_get_finance_analysis_v1(jsonb) to authenticated;
