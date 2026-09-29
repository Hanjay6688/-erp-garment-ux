-- Recorded-period comparison and cash ledger projection. No financial writes.
grant select on erp.cash_accounts,erp.account_daily_balances,erp.journal_entries,erp.journal_lines to cp7_finance_read;
grant execute on function erp.account_id(text) to cp7_finance_read;

create function cp7_finance.analysis(p_query jsonb) returns jsonb
language plpgsql stable security invoker set search_path='' set TimeZone='UTC' as $$
declare f date;t date;a date;bf date;bt date;off integer;n integer;current_report jsonb;baseline_report jsonb;
 current_perf jsonb;baseline_perf jsonb;revenue numeric;baseline_revenue numeric;growth numeric; margin_delta numeric;
 cash_ids uuid[];opening numeric;closing numeric;debits numeric;credits numeric;total bigint;rows jsonb;
begin
 perform cp7_finance.access_now();
 if jsonb_typeof(p_query) is distinct from 'object' or not p_query ?& array['from','to','as_of','compare_from','compare_to']
  or exists(select 1 from jsonb_object_keys(p_query)k where k not in('from','to','as_of','compare_from','compare_to','offset','limit'))
  or exists(select 1 from jsonb_each(p_query)e where e.key in('from','to','as_of','compare_from','compare_to') and(jsonb_typeof(e.value)<>'string' or(e.value#>>'{}')!~'^[0-9]{4}-[0-9]{2}-[0-9]{2}$'))
  or exists(select 1 from jsonb_each(p_query)e where e.key in('offset','limit') and(jsonb_typeof(e.value)<>'number' or e.value::text!~'^[0-9]{1,7}$')) then raise exception 'CP7_FINANCE_ANALYSIS_QUERY';end if;
 f:=(p_query->>'from')::date;t:=(p_query->>'to')::date;a:=(p_query->>'as_of')::date;bf:=(p_query->>'compare_from')::date;bt:=(p_query->>'compare_to')::date;
 off:=coalesce((p_query->>'offset')::integer,0);n:=coalesce((p_query->>'limit')::integer,25);
 if f>t or t>a or bf>bt or bt>=f or a>(statement_timestamp() at time zone 'Asia/Jakarta')::date or off not between 0 and 1000000 or n not between 1 and 100 then raise exception 'CP7_FINANCE_ANALYSIS_QUERY';end if;
 -- Both native reports and the ledger below share this stable statement's
 -- snapshot. Baseline readiness belongs to its own cutoff, not today's one.
 current_report:=erp.get_owner_financial_snapshot_v2(f,t,a);
 baseline_report:=erp.get_owner_financial_snapshot_v2(bf,bt,bt);
 if current_report is null or baseline_report is null or octet_length(current_report::text)+octet_length(baseline_report::text)>2000000 then raise exception 'CP7_FINANCE_REPORT_INCOMPLETE';end if;
 current_perf:=current_report->'performance';baseline_perf:=baseline_report->'performance';
 revenue:=(current_perf->>'sales_revenue_gl')::numeric;baseline_revenue:=(baseline_perf->>'sales_revenue_gl')::numeric;
 growth:=round((revenue-baseline_revenue)/nullif(baseline_revenue,0)*100,4);
 -- Aggregate original operands, not rounded row margins or averaged ratios.
 margin_delta:=round(((current_perf->>'gross_profit')::numeric/nullif(revenue,0)-(baseline_perf->>'gross_profit')::numeric/nullif(baseline_revenue,0))*100,4);
 select array_agg(x.id order by x.id) into cash_ids from(select coa_account_id id from erp.cash_accounts union select erp.account_id('CASH'))x;
 select coalesce(sum(b.debit_total-b.credit_total)filter(where b.balance_date<f),0),coalesce(sum(b.debit_total-b.credit_total),0)
 into opening,closing from erp.account_daily_balances b where b.account_id=any(cash_ids) and b.balance_date<=t;
 select coalesce(sum(l.debit),0),coalesce(sum(l.credit),0),count(distinct j.id)
 into debits,credits,total from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id
 where j.status in('POSTED','REVERSED') and j.transaction_date between f and t and l.account_id=any(cash_ids);
 select coalesce(jsonb_agg(to_jsonb(x) order by x.transaction_date,x.posting_at,x.id),'[]') into rows from(
  select j.id,j.journal_number,j.source_type,j.source_id,j.reversal_of_id,j.status,j.economic_date,j.transaction_date,j.posting_at,
   sum(l.debit)::text debit,sum(l.credit)::text credit,sum(l.debit-l.credit)::text net
  from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id
  where j.status in('POSTED','REVERSED') and j.transaction_date between f and t and l.account_id=any(cash_ids)
  group by j.id order by j.transaction_date,j.posting_at,j.id limit n offset off
 )x;
 return jsonb_build_object('contract_version','cp7.finance-analysis.v1','captured_at',statement_timestamp(),
  'knowledge_basis','CURRENT_RECORDED_KNOWLEDGE','historical_knowledge','NOT_RECONSTRUCTED',
  'dates',jsonb_build_object('from',f,'to',t,'as_of',a,'compare_from',bf,'compare_to',bt),
  'comparison',jsonb_build_object('basis','NATIVE_OWNER_REPORT_OPERANDS','formula_version','GROWTH_BASELINE_AND_GROSS_MARGIN_PP_V1','rounding_scale',4,
   'current',cp7_finance.exact_numbers(current_report),'baseline',cp7_finance.exact_numbers(baseline_report),
   'revenue_growth_pct',growth::text,'gross_margin_change_pp',margin_delta::text),
  'cash',jsonb_build_object('basis','GL_TRANSACTION_DATE_ALL_CONFIGURED_CASH_COA','account_scope','DISTINCT_COA_INCLUDING_INACTIVE_CASH_ACCOUNTS_AND_CASH_MAPPING',
   'opening',opening::text,'closing',closing::text,'debit',debits::text,'credit',credits::text,'net_change',(closing-opening)::text,
   'ledger_net',(debits-credits)::text,'source_difference',(closing-opening-debits+credits)::text,'reconciled',closing-opening=debits-credits,
   'entries',jsonb_build_object('rows',rows,'total',total::text,'offset',off,'limit',n,'next_offset',case when off+jsonb_array_length(rows)<total then off+jsonb_array_length(rows)else null end)));
end $$;
create function public.erp_cp7_get_finance_analysis_v1(p_query jsonb) returns jsonb
language sql stable security definer set search_path='' as $$select cp7_finance.analysis(p_query)$$;
alter function cp7_finance.analysis(jsonb) owner to cp7_finance_read;
grant create on schema public to cp7_finance_read;
alter function public.erp_cp7_get_finance_analysis_v1(jsonb) owner to cp7_finance_read;
revoke create on schema public from cp7_finance_read;
revoke all on function cp7_finance.analysis(jsonb),public.erp_cp7_get_finance_analysis_v1(jsonb) from public,anon,authenticated,service_role,cp7_capture;
grant execute on function public.erp_cp7_get_finance_analysis_v1(jsonb) to authenticated;
